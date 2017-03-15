############################################################
#															#
# C_Cpp_Dependency_Gen v1.0.0								#
#															#
# Copyright 2017, PedroHenriques							#
# http://www.pedrojhenriques.com							#
# https://github.com/PedroHenriques							#
#															#
# Free to use under the MIT license.						#
# http://www.opensource.org/licenses/mit-license.php		#
#															#
############################################################

import os, re
from classes import General

class DepListBuilder :
	"""Crawler that will scan the dependent files and search for all the #include directives and get there absolute paths."""

	def __init__(self, project_root, config) :
		# instance variable referencing the currently active configurations
		self.config = config

		# instance variable storing the absolute paths that will be used to search for files, when needed
		self.search_paths = list([project_root])

		# instance variable referencing a queue
		# provided by the Application class when one is to be processed
		self.queue = None

		# class variable storing the dependent files processed by the crawlers
		# provided by the Application class when a queue needs to be processed
		self.dep_list = None

		# class variable storing any files that couldn't be found
		# provided by the Application class when a queue needs to be processed
		self.failed_files = None

		# instance variable with data needed to build the dependency lists
		# provided by the Application class when a queue needs to be processed
		self.files = None

		# instance variable storing the basenames for which a valid absolute path could not be built
		# these files will need to be searched in the directories in search_paths
		# format: [absolute path] = set(unknown basenames present in the file)
		self.pending_search = dict()

		# instance variable storing the basenames found by the crawl task
		self.found_files = set()

		# instance variable storing the absolute paths of all files found by the crawl task
		# used to improve performance across multiple dependency list builds by not needing to search
		# for the same file multiple times (unless the file's path changes)
		# format: [file basename] = file's abs path
		self.known_paths = dict()

		# instance variable storing the absolute paths, obtained from the crawl of a file, which absolute paths
		# were found
		# used to improve performance across multiple dependency list builds by not needing to crawl
		# the same file multiple times (unless the file is modified)
		# format: [file basename] = set(abs paths)
		self.file_known_deps = dict()

		# instance variable storing the basenames, obtained from the crawl of a file, which absolute paths
		# couldn't be found
		# used to improve performance across multiple dependency list builds by not needing to crawl
		# the same file multiple times (unless the file is modified)
		# format: [file basename] = set(basenames)
		self.file_unknown_deps = dict()

		# instance variable storing the modify times of each file at the time of their last crawl
		# format: [file basename] = modify time
		self.files_crawl_mtime = dict()

	# main function of this class, responsible for processing a queue of files, crawling each one searching for
	# all the "#include" directives and building the aboslute path for each one
	# all the dependent files found are stored in self.dep_list and all basenames that couldn't be found
	# are stored in self.failed_files
	def run(self) :
		# check if there is a queue
		if (self.queue == None) :
			# there isn't, so bail out
			return

		# going through a new queue
		queue_first_iteration = True

		# build the characters to be used in the regex below, based on the current configuration
		if (self.config["builtin_libs"]) :
			# the language default libraries #includes should be checked
			regex_str = "#include\\s+[<\\\"]([^<>\\\"]+)[>\\\"]"
		else :
			# the language default libraries #includes should not be checked
			regex_str = "#include\\s+[\\\"]([^<>\\\"]+)[\\\"]"

		while len(self.queue) > 0 or len(self.pending_search) > 0 :
			# check if the queue has any items
			if (len(self.queue) > 0) :
				# it has
				# grab a file to check
				file_path = General.General.standardizePath(self.queue.pop())

				# check if path is valid
				if (not os.path.isfile(file_path)) :
					# it isn't
					# add this file to the failed files
					self.addToFailedFiles(file_path, None)

					# move on to next file
					continue

				# get this file's basename
				file_path_basename = os.path.basename(file_path)

				# get any stored data from previous crawls of this file
				dependents_found = self.findInFileKnownDeps(file_path)

				# check if this file has already been crawled and up-to-date information is available
				if (dependents_found != None) :
					# this file has been crawled and the stored information is still up-to-date
					# check if there are any stored basenames which absolute paths couldn't be found
					if (file_path_basename in self.file_unknown_deps) :
						# there are
						# add them to the failed files
						self.addToFailedFiles(file_path, self.file_unknown_deps[file_path_basename].copy())
				else :
					# this file hasn't been crawled, or the file was modified since the last crawl
					dependents_found = set()

					# get the contents of the file in path
					file_content = General.General.readFile(file_path)

					# check if the file's content was successfully acquired
					if (file_content == None) :
						# it wasn't
						continue

					# get this file's directory
					file_path_dirname = General.General.standardizePath(os.path.dirname(file_path))

					# stores all the file basenames which paths couldn't be deduced
					# these will be searched for according to the search_paths config value
					unknown_basenames = set()

					# scan the file's content for all the #include directives
					for re_match in re.finditer(regex_str, file_content, re.I) :
						# stores the absolute path to the file found in this match
						tentative_file_path = ""

						# boolean to know if this match's path is already known
						path_already_known = False

						# get the match string
						re_match_str = General.General.standardizePath(re_match.group(1))

						# get the basename of re_match_str
						re_match_str_basename = os.path.basename(re_match_str)

						try :
							# check if the path to this match is already known
							tentative_file_path = self.findInKnownPaths(set([re_match_str_basename]))[re_match_str_basename]

							# it is
							path_already_known = True
						except KeyError as e :
							# it isn't
							tentative_file_path = ""

						# if the path isn't already known, find it
						if (not path_already_known) :
							# check if it's a path (absolute or relative)
							if ("\\" in re_match_str) :
								# it is
								# check if it's an absolute path
								if (re.match("[a-z]:[\\\\]", re_match_str, re.I) == None) :
									# it isn't, so it's a relative path
									# store the current working directory
									cwd = os.getcwd()

									# change the CWD to the current file's directory
									os.chdir(file_path_dirname)

									# convert the relative path to an aboslute path
									tentative_file_path = os.path.abspath(re_match_str)

									# reset the CWD
									os.chdir(cwd)
								else :
									# it is
									# store the file's absolute path
									tentative_file_path = re_match_str

								# check if the absolute path built exists
								if (not os.path.isfile(tentative_file_path)) :
									# it doesn't
									# this match will have to be searched for in the paths in self.search_paths
									unknown_basenames.add(os.path.basename(tentative_file_path))
									tentative_file_path = ""
							else :
								# it isn't, which means that the #include directive only has the basename of the file
								# check if this file is in the same directory as the crawled file
								tentative_file_path = file_path_dirname + "\\" + re_match_str
								if (not os.path.isfile(tentative_file_path)) :
									# it isn't
									# check if this file was found while searching the project's directory
									tentative_file_path = self.findInFiles(re_match_str)
									if (tentative_file_path == "") :
										# it wasn't
										# this match will have to be searched for in the paths in self.search_paths
										unknown_basenames.add(re_match_str)

						# check if the absolute path for this match was found
						if (tentative_file_path != "") :
							# it was
							# standardize the path
							tentative_file_path = General.General.standardizePath(tentative_file_path)

							# check if the file found is the file currently being crawled
							if (tentative_file_path == file_path) :
								# it is, so ignore it
								continue

							# add the file to the set() of dependents
							dependents_found.add(tentative_file_path)

							# check if this path was already known
							if (not path_already_known) :
								# it wasn't, so add it to the known paths
								self.addToKnownPaths(dict([(os.path.basename(tentative_file_path), tentative_file_path)]))

					# get this file's modify time (the time of this crawl)
					crawl_mtime = os.path.getmtime(file_path)

					# check if there are any matches that need to be searched
					if (len(unknown_basenames) > 0) :
						# there are
						# store them to be searched later
						self.addToPendingSearch(file_path, unknown_basenames)

					# now that this file's crawl task has been completed
					# store the found abs paths as this file's known dependents
					self.addToFileKnownDeps(file_path_basename, dependents_found)

					# store the time of this file's crawl
					self.files_crawl_mtime[file_path_basename] = crawl_mtime

				# add the dependents found to the queue
				self.addToQueue(dependents_found)

				# controls if this file should be added to self.dep_list or not
				add_file = True

				# check if this is the first iteration, which means the file in question is the source file
				if (queue_first_iteration) :
					# reverse the boolean
					queue_first_iteration = False

					# check if the source file should be included in the dependency list
					if (not self.config["include_source"]) :
						# it shouldn't
						add_file = False

				# check if this file should be added to the final data
				# NOTE: the absolute path will be added at this point, regardless of the value of
				# 		the "dependency_path" config -> that config will be used when passing the
				# 		dependency list to the function that builds the dependency file
				if (add_file) :
					# it should
					self.dep_list.append(file_path)
			else :
				# it hasn't
				# deal with any basenames that might be pending search
				self.processPendingSearch()

	# builds the list() with all the paths that will be used to search for dependent files
	# that are being #include with just the file's basename
	# the paths will be stored in self.search_paths
	# the order in which the paths will be added is:
	# 	- project root directory
	# 	- the paths provided in the "search_paths" configuration (in the same order)
	# 	- (if the "builtin_libs" config is True) any paths found inn the PATH environmental variable pointing to a "mingw" directory
	def buildSearchPaths(self) :
		# clear any previous paths, keeping only the project's root directory
		self.search_paths = list([self.search_paths[0]])

		# add all the paths provided in the "search_paths" configuration
		for path in self.config["search_paths"].split(";") :
			self.search_paths.append(path)

		# if the "builtin_libs" configuration is True, try to find the location of the
		# "mingw" folder -> where the language built-in libraries are located
		if (self.config["builtin_libs"]) :
			try :
				# check if PATH environmental variable has any paths to a "mingw" folder
				# and if it has look through all the matches
				for re_match in re.finditer("(([^\\\\/;]+[\\\\/])+mingw([\\\\/][^\\\\/;]+)?)", os.environ["path"], re.I) :
					# add the path to the set
					self.search_paths.append(General.General.standardizePath(re_match.group(1)))
			except KeyError as e :
				# there is no PATH environmental variable, so move on
				pass

		# clear the variables storing the paths of known files, the paths/basenames obtained by
		# crawling each file and the modify times of last crawls
		# since any path built from the search paths might no longer be valid
		self.known_paths.clear()
		self.file_known_deps.clear()
		self.file_unknown_deps.clear()
		self.files_crawl_mtime.clear()

	# searches for the provided basenames in the paths set in search_paths
	# returns a dict() with the found paths in the format: [file basename] = file absolute path
	def findPaths(self, file_basenames) :
		# stores the paths found
		# format: [file basename] = file abs path
		found_paths = dict()

		# loop through the various search paths
		for search_path in self.search_paths :
			# try to find these files
			aux = General.General.findFiles(file_basenames.copy(), search_path)

			# loop through each found file
			for aux_basename in aux :
				# remove this basename from the pending search set()
				file_basenames.remove(aux_basename)

				# add this path to the final data
				found_paths[aux_basename] = aux[aux_basename]

			# check if there are any basenames still pending search
			if (len(file_basenames) == 0) :
				# there aren't
				# exit loop
				break

		# add these paths to the known paths
		self.addToKnownPaths(found_paths)

		# return the paths that were found
		return(found_paths)

	# checks if the provided paths hasn't been found already and adds new files to the queue
	# receives a set() of absolute paths
	def addToQueue(self, file_paths) :
		# loop through each received abs path
		for file_path in file_paths.copy() :
			# get this file's basename
			file_basename = os.path.basename(file_path)

			# check if this file has been found already
			if (file_basename in self.found_files) :
				# it has
				# remove it from the set()
				file_paths.remove(file_path)
			else :
				# it hasn't
				# add this file's basename to the found files
				self.found_files.add(file_basename)

		# add the new files to the queue
		self.queue.update(file_paths)

	# adds the provided basenames to pending_search
	def addToPendingSearch(self, file_path, unknown_basenames) :
		# check if this file has an entry
		if (file_path not in self.pending_search) :
			# it doesn't
			self.pending_search[file_path] = set()

		# add this file's unknown basenames
		self.pending_search[file_path].update(unknown_basenames)

	# adds the provided paths to known_paths
	# receives a dict() with format: [file basename] = file absolute path
	def addToKnownPaths(self, file_paths) :
		# check if any paths were provided
		if (len(file_paths) == 0) :
			# there weren't
			return

		# loop through the paths provided
		for file_basename in file_paths :
			# check if this file is already in the variable
			if (file_basename not in self.known_paths) :
				# it isn't
				# add the path
				self.known_paths[file_basename] = file_paths[file_basename]

	# searches the provided set() of basenames in known_paths
	# returns the corresponding absolute paths for the basenames that are already known
	def findInKnownPaths(self, file_basenames) :
		# stores the paths found
		# format: [file basename] = file's abs path
		found_paths = dict()

		# loop through the provided basenames
		for file_basename in file_basenames :
			# check if the path to this file is already known
			if (file_basename in self.known_paths) :
				# it is
				# check if the path is still valid
				if (os.path.isfile(self.known_paths[file_basename])) :
					# it is
					# add the path to the final data
					found_paths[file_basename] = self.known_paths[file_basename]
				else :
					# it isn't
					# remove it from the known paths, which will cause the path
					# to this file to be searched for again
					del self.known_paths[file_basename]

		# return the paths found
		return(found_paths)

	# adds/updates file_known_deps with the provided set() of absolute paths
	def addToFileKnownDeps(self, file_basename, dependent_paths) :
		# check if this file has an entry in file_known_deps_
		if (file_basename not in self.file_known_deps) :
			# it hasn't
			self.file_known_deps[file_basename] = set()

		# update file_known_deps_
		self.file_known_deps[file_basename].update(dependent_paths)

	# searches file_known_deps for the provided file
	# returns the respective set() of absolute paths if the information is available
	# NOTE: if a file has been crawled but doesn't include any other valid files, an empty set() is returned
	# 		if a file hasn't been crawled or needs to be crawled again, None is returned instead
	def findInFileKnownDeps(self, file_path) :
		# get this file's basename
		file_basename = os.path.basename(file_path)

		# stored the return data
		found_paths = set()

		# check if this file has already been crawled
		if (file_basename in self.file_known_deps) :
			# it has
			# get a copy of the data
			found_paths = self.file_known_deps[file_basename].copy()

		# check if any data was available
		if (len(found_paths) == 0) :
			# there wasn't
			# check if the file has been crawled
			if (file_basename not in self.files_crawl_mtime) :
				# it hasn't
				# return None to signal the file to be crawled again
				return(None)

		# check if this file has been modified since the time of last crawl
		if (os.path.getmtime(file_path) > self.files_crawl_mtime[file_basename]) :
			# it has
			# remove this file's entry from file_known_deps, file_unknown_deps
			# and files_crawl_mtime
			# which will trigger the file to be crawled again
			del self.file_known_deps[file_basename]
			if (file_basename in self.file_unknown_deps) :
				del self.file_unknown_deps[file_basename]
			del self.files_crawl_mtime[file_basename]

			# return None to signal the file to be crawled again
			return(None)

		# stores the basenames of any paths that are no longer valid
		unknown_basenames = set()

		# loop through each path in the set()
		for path in found_paths.copy() :
			# check if this path is valid
			if (not os.path.isfile(path)) :
				# it isn't
				# add this path's basename to be searched later
				unknown_basenames.add(os.path.basename(path))

				# remove this path from the final data
				found_paths.remove(path)

		# check if there are any invalid paths
		if (len(unknown_basenames) == 0) :
			# there aren't, so return the final data
			return(found_paths)

		# at this point there are paths that have become invalid since this file was crawled
		# search in known_paths for these basenames
		aux_paths = self.findInKnownPaths(unknown_basenames)

		# check if any paths were obtained
		if (len(aux_paths) > 0) :
			# yes
			# loop through each one
			for aux_basename in aux_paths :
				# remove this basename from unknown_basenames
				unknown_basenames.remove(aux_basename)

				# add this path to the final data
				found_paths.add(aux_paths[aux_basename])

		# check if there are still any files with unknown paths
		if (len(unknown_basenames) > 0) :
			# there are
			# search for these files in the search paths provided in the configuration
			aux_paths = self.findPaths(unknown_basenames.copy())

			# check if any paths were obtained
			if (len(aux_paths) > 0) :
				# yes
				# loop through each one
				for aux_basename in aux_paths :
					# remove this basename from unknown_basenames
					unknown_basenames.remove(aux_basename)

					# add this path to the final data
					found_paths.add(aux_paths[aux_basename])

		# at this point, the abs paths of the "#include" in this file have changed
		# update file_known_deps
		self.addToFileKnownDeps(file_basename, found_paths)

		# check if there are any basenames that couldn't be found
		if (len(unknown_basenames) > 0) :
			# there are
			# add them to failed_files
			self.addToFailedFiles(file_path, unknown_basenames)

		# return the final data
		return(found_paths)

	# adds an entry in failed_files for the provided file and updates that file's
	# set() of failed matches with the failed_matches provided
	def addToFailedFiles(self, file_path, failed_matches) :
		# check if this file has en entry in the failed files variable
		if (file_path not in self.failed_files) :
			# it doesn't
			self.failed_files[file_path] = set()

		# if any specific matches were provided, upodate this file's set()
		if (failed_matches != None and len(failed_matches) > 0) :
			# update the class variable with these failed matches
			self.failed_files[file_path].update(failed_matches)

	# calls for the search of any basenames pending search
	def processPendingSearch(self) :
		# check if there are any basenames pending search
		if (len(self.pending_search) == 0) :
			# there aren't
			# nothing needs to be done
			return

		# build the set with basenames to search
		unknown_basenames = set()
		for file_path in self.pending_search :
			unknown_basenames.update(self.pending_search[file_path])

		# search for these files in the search paths provided in the configuration
		aux = self.findPaths(unknown_basenames)

		# check if any file was found
		if (len(aux) > 0) :
			# yes
			# add the files found to the queue
			self.addToQueue(set(aux.values()).copy())

			# get a set() with the basenames found
			found_basenames = set(aux.keys())

			# loop through each pending_search entry
			for file_path in set(self.pending_search.keys()).copy() :
				# discover the basenames found
				found_items = self.pending_search[file_path].intersection(found_basenames)

				# check if any items were found
				if (len(found_items) == 0) :
					# there weren't
					continue

				# stores the abs paths for the found items
				known_deps = set()

				# loop through each found item
				for file_basename in found_items :
					# add it to this file's known dependents
					known_deps.add(aux[file_basename])

					# remove it from this file's unknown basenames
					self.pending_search[file_path].remove(file_basename)

				# store the found abs paths as this file's known dependents
				self.addToFileKnownDeps(os.path.basename(file_path), known_deps)

				# check if this file still has any unknown basenames
				if (len(self.pending_search[file_path]) == 0) :
					# it hasn't
					del self.pending_search[file_path]

		# check if there are any basenames that weren't found
		if (len(self.pending_search) > 0) :
			# there are
			# loop through each file
			for file_path in self.pending_search :
				# add them to the failed files
				self.addToFailedFiles(file_path, self.pending_search[file_path])

				# store the found basenames as this file's unknown dependents
				self.file_unknown_deps[os.path.basename(file_path)] = self.pending_search[file_path].copy()

			# clear the pending_search variable, since the program has found the files that could be found
			# and has processed the files that couldn't be found
			self.pending_search.clear()

	# searches the provided basename in self.files (only in the relevant keys of files)
	# returns the corresponding absolute path, if found, or an empty string otherwise
	def findInFiles(self, file_basename) :
		# loop through the relevant keys of files_
		for files_key in set(["source", "relevant"]) :
			# check if this file is in this self.files key
			if (file_basename in self.files[files_key]) :
				# it is
				# return this file's absolute path
				return(self.files[files_key][file_basename])

		# at this point this file's path wasn't found in self.files
		return("")
