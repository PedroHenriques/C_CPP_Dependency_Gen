############################################################
#															#
# C_Cpp_Dependency_Gen v1.0.1								#
#															#
# Copyright 2017, PedroHenriques							#
# http://www.pedrojhenriques.com							#
# https://github.com/PedroHenriques							#
#															#
# Free to use under the MIT license.						#
# http://www.opensource.org/licenses/mit-license.php		#
#															#
############################################################

import os, json, re, time, builtins
from classes import Cli, DepListBuilder, General

class Application :
	"""This is the application's main class."""

	# class variable with the valid source file extensions
	src_extensions_ = set(["c", "cpp"])

	# class variable with the file extensions that are relevant as dependents
	# NOTE: this will make the program store their absolute paths when the project's directory tree is scaned
	# 		but any files not included here will still be searched for if they are "#included" in a file
	relevant_extensions_ = set(["h"])

	# class variable with the valid dependency file extension
	dep_extension_ = "d"

	# class variable with the basename of the file that has the dependency template
	dependency_template_basename_ = "dependency_template.txt"

	# class variable with the basename of the file that has the project specific cnfiguration
	project_config_basename_ = "dependency_config.json"

	def __init__(self) :
		# create and store the General class' JSON decoder
		General.General.json_decoder_ = json.JSONDecoder()

		# create an instance of the Cli class
		self.cli_obj = Cli.Cli(self)

		# instance variable to store the program's root directory
		self.program_root = General.General.standardizePath(os.path.dirname(os.path.dirname(__file__)))

		# instance variable to store this project's directory
		self.project_root = General.General.standardizePath(os.getcwd())

		# instance variable to store all the relevant files
		# NOTE: populated in scanSrcFiles()
		self.files = dict()

		# instance variable to store the configuration in effect
		self.config = dict()

		# build a set() with all the relevant files' basenames
		self.relevant_basenames = set(["*.h"])
		self.relevant_basenames.add("*." + Application.dep_extension_)
		self.relevant_basenames.add(Application.dependency_template_basename_)
		for src_extension in Application.src_extensions_ :
			self.relevant_basenames.add("*." + src_extension)

		# show the welcome message
		self.cli_obj.printMsg(1, "# # # # # # # # # # # # # # # # # # # # # # # # #\n\nWelcome to the C/C++ Dependency Generator.\n\nType \"help\" for a list of valid commands.\n\n# # # # # # # # # # # # # # # # # # # # # # # # #", False)

		# check if the program's configuration validation file exists
		config_val_path = os.path.abspath(self.program_root + "\\data\\config_validation.json")
		if (not os.path.isfile(config_val_path)) :
			# the file doesn't exist
			# print error message
			self.cli_obj.printMsg(0, "The program's configuration validation file couldn't be found.", True)

			# failed
			raise KeyboardInterrupt
		else :
			# the file exists
			# decode the JSON file
			self.config_validation = General.General.parseJSON(config_val_path)

		# load the configurations for this project
		if (not self.configLoad()) :
			# the configuration couldn't be loaded
			# print error message
			self.cli_obj.printMsg(0, "No configuration could be loaded.", True)

			# failed
			raise KeyboardInterrupt

		# create an instance of the DepListBuilder class
		self.dep_list_builder_obj = DepListBuilder.DepListBuilder(self.project_root, self.config.copy())

		# build the DepListBuilder's search paths
		self.dep_list_builder_obj.buildSearchPaths()

	# executes the program's core task
	def run(self) :
		# controls the main loop
		run = True

		# check if the configuration is available
		if (len(self.config) == 0) :
			# it isn't
			run = False

		try :
			# main loop
			while run :
				# signal the Cli class to ask the user for commands
				action = self.cli_obj.askCommand()

				# check if the command triggers the termination of the program
				if (action == -1) :
					# it does
					run = False
				# check if the command triggers the start of the scan of source files
				elif (action == 1) :
					# it does
					self.scanSrcFiles()
		except (KeyboardInterrupt, SystemExit) :
			# the user pressed CTRL-C so terminate the program
			# bubble the exception up
			raise

		# at this point the program will terminate, so print the outro message
		self.outroMsg()

	# called when the program terminates to print the outro message
	def outroMsg(self) :
		# check if the outro message has been printed already
		if (not self.cli_obj.outro_msg_printed) :
			# it hasn't
			# print the outro message
			self.cli_obj.printMsg(1, "\n# # # # # # # # # # # # # # # # # # # # # # # # #\n\nThank you for using Pedro Henriques' C/C++ Dependency Generator\n\nFollow this program at https://github.com/PedroHenriques/C_CPP_Dependency_Gen\n\n# # # # # # # # # # # # # # # # # # # # # # # # #", False)

			# flag the outro message as having been printed
			self.cli_obj.outro_msg_printed = True

	# searches for all the relevant files and stores their paths in self.files
	def populateFiles(self) :
		# NOTE: the program assumes there aren't multiple source, header and dependency files with the same
		# 		basename but different paths in the same project
		self.files = dict(source=dict(), relevant=dict(), dependency=dict(), dependency_template="")

		# find all the relevant files
		found_files = General.General.findFiles(self.relevant_basenames.copy(), self.project_root)

		# add the files found to self.files sorted by designation
		for found_file_basename in found_files :
			# get these files' extension
			aux_pos = found_file_basename.rfind(".")
			if (aux_pos == -1) :
				# they don't have an explicit extension
				found_file_extension = ""
			else :
				found_file_extension = found_file_basename[aux_pos + 1:]

			# check if this extension belongs to the source files
			if (found_file_extension in Application.src_extensions_) :
				# it does
				self.files["source"][found_file_basename] = found_files[found_file_basename]
			# check if this extension belongs to the relevant files
			elif (found_file_extension in Application.relevant_extensions_) :
				# it does
				self.files["relevant"][found_file_basename] = found_files[found_file_basename]
			# check if this extension belongs to the dependency files
			elif (found_file_extension == Application.dep_extension_) :
				# it does
				self.files["dependency"][found_file_basename] = found_files[found_file_basename]
			else :
				# check if these files match the rule template
				if (found_file_basename == Application.dependency_template_basename_) :
					# they do
					self.files["dependency_template"] = found_files[found_file_basename]

	# main method that will periodicaly scan the source files and generate
	# the dependency files as needed
	def scanSrcFiles(self) :
		try:
			# stores the list of dependent files of each source file
			# NOTE: all paths will use \ as the directory separator
			dependency_list = dict()

			# stores the modify time of each dependent file that has been checked for each source file
			# this will be used to prevent the rebuild of a file's dependency list every cycle
			# in the cases where the file was modified after the dependency file was generated,
			# but the change didn't affect it's dependent files
			# format: [src_file_basename][file's absolute path] = mtime of last check
			checked_mtimes = dict()

			# used to know whether the loop is in the first iteration or not
			first_iteration = True

			# print message
			self.cli_obj.printMsg(1, "=> Started the scan of the source files.\n=> Press CTRL-C to end the scan.", False)

			while True :
				# find all the relevant files and store them in self.files
				self.populateFiles()

				# check if the Makefile rule template was found
				if (self.files["dependency_template"] == "") :
					# it wasn't
					# print error message
					self.cli_obj.printMsg(0, "Couldn't find the file with name \"" + Application.dependency_template_basename_ + "\", containing the Makefile rule template used to build the dependency files.", True)

					# bail out
					break

				# check if any source files were found
				if (len(self.files["source"]) == 0) :
					# there are no source files
					# sleep before next cycle
					self.startSleep(self.config["sleep_timer"])

					# move to next cycle
					continue

				# cross-reference the source and dependency files found and remove any dependency files that
				# no longer have a matching source file
				removed_files = self.checkFiles()

				# remove from dependency_list any files that are no longer relevant
				for removed_file_basename in removed_files:
					if (removed_file_basename in dependency_list) :
						del dependency_list[removed_file_basename]

				# check if the dependency_list is empty but there are already dependency files generated
				if (len(dependency_list) == 0 and len(self.files["dependency"]) > 0) :
					# there are, so this must be the first iteration of this loop
					# search the existing dependency files and build the dependency lists used to generate them
					dependency_list = self.deduceDependencyLists()

				# loop through each source file
				for src_file_basename in self.files["source"] :
					# grab this source file's name and extension
					aux_pos = src_file_basename.rfind(".")
					src_file_name = src_file_basename[:aux_pos]
					src_file_ext = src_file_basename[aux_pos + 1:]

					# stores the time of last modification of the dependency file
					dependency_file_mtime = -1

					# stores this source file's corresponding dependency file basename
					dep_file_basename = src_file_name + "." + Application.dep_extension_

					# controls whether this source file's dependency list needs to be (re)generated
					build_dep_list = False

					# controls whether this source file's dependency file needs to be (re)generated
					generate = False

					# check if a corresponding dependency file already exists
					if (dep_file_basename not in self.files["dependency"]) :
						# it doesn't, so the dependency file will need to be generated
						generate = True
					else :
						# get the time of last modification of the dependency file
						dependency_file_mtime = os.path.getmtime(self.files["dependency"][dep_file_basename])

						# check if the rule template was changed after the dependency file was generated
						if (os.path.getmtime(self.files["dependency_template"]) > dependency_file_mtime) :
							# it was, so the dependency file will need to be regenerated
							generate = True

					# check if the list of dependent files for this source file has already been built
					if (dep_file_basename not in dependency_list) :
						# it hasn't, so built it
						build_dep_list = True
					elif (first_iteration) :
						# it has and it's the first iteration of the loop
						# always build the dependency list on the first iteration
						# it will be compared to the list used to generate the dependency file below
						build_dep_list = True

						# determine if the items in the dependency list have absolute paths
						items_have_paths = "/" in dependency_list[dep_file_basename][0] or "\\" in dependency_list[dep_file_basename][0]

						# check if its items having or not the absolute paths matches the current config
						if (items_have_paths != self.config["dependency_paths"]) :
							# it doesn't
							# regenerate the dependency file
							generate = True

					# if the dependency list hasn't been flagged to be built
					# check if the source file was modified after the dependency file was generated
					aux_mtime = os.path.getmtime(self.files["source"][src_file_basename])
					if (not build_dep_list and aux_mtime > dependency_file_mtime) :
						# it was
						# check if that change has been validated in previous cycles
						if (src_file_basename not in checked_mtimes or self.files["source"][src_file_basename] not in checked_mtimes[src_file_basename] or aux_mtime > checked_mtimes[src_file_basename][self.files["source"][src_file_basename]]) :
							# it hasn't, so build it
							build_dep_list = True

					# check if this source file is present in checked_mtimes
					if (src_file_basename not in checked_mtimes) :
						# it isn't, so add it
						checked_mtimes[src_file_basename] = dict()

					# keep a record that this file has been checked
					# regardless of whether the dependency file will be (re)generated or not
					checked_mtimes[src_file_basename][self.files["source"][src_file_basename]] = aux_mtime

					# if the dependency list hasn't been flagged to be built
					if (not build_dep_list) :
						# loop through each dependent file
						for dep_file_path in dependency_list[dep_file_basename] :
							# check if this file no longer exists
							if (not os.path.isfile(dep_file_path)) :
								# it doesn't, so build it
								build_dep_list = True
							else :
								# get this file's modify time
								aux_mtime = os.path.getmtime(dep_file_path)

								# check if this file was modified after the dependency file was generated
								if (aux_mtime > dependency_file_mtime) :
									# it was
									# check if that change has been validated in previous cycles
									if (dep_file_path not in checked_mtimes[src_file_basename] or aux_mtime > checked_mtimes[src_file_basename][dep_file_path]) :
										# it hasn't, so build it
										build_dep_list = True

							# check if the dependent list has been flagged for build
							if (build_dep_list) :
								# it has
								# no need to continue checking the rest of the dependent files
								break

							# keep a record that this file has been checked
							# regardless of whether the dependency file will be (re)generated or not
							checked_mtimes[src_file_basename][dep_file_path] = aux_mtime

					# check if the dependency list needs to be (re)built
					if (build_dep_list) :
						# it does
						new_dependency_list = self.buildDependencyList(src_file_basename)

						# make sure the dependency list was generated
						if (len(new_dependency_list) == 0) :
							# it failed
							# keep a record of the dependent file's mtime at the time of this cycle's check
							for dep_file_path in dependency_list[dep_file_basename] :
								# check if this path is still valid
								if (not os.path.isfile(dep_file_path)) :
									# it isn't
									dependency_list[dep_file_basename].remove(dep_file_path)

									# move on to next path
									continue

								#
								checked_mtimes[src_file_basename][dep_file_path] = os.path.getmtime(dep_file_path)

							# move to next source file
							continue

						# keep a record of the dependent file's mtime at the time of this cycle's check
						for new_file_path in new_dependency_list :
							checked_mtimes[src_file_basename][new_file_path] = os.path.getmtime(new_file_path)

					# if at this point nothing has triggered a regenerate of the dependency file
					# but the dependency list was built this cycle, then compare the old dependency list
					# with the one generated this cycle to check if there were changes to it
					if (not generate and build_dep_list) :
						# check if the old list has this item
						if (dep_file_basename not in dependency_list) :
							# it doesn't
							for new_file_path in new_dependency_list :
								# check if this file was modified after the dependency file was generated
								if (os.path.getmtime(new_file_path) > dependency_file_mtime) :
									# it was
									# the dependency file needs to be (re)generated
									generate = True

									# no need to continue checking the rest of items
									break
						else :
							# it does
							# check if the #items in both lists is the same
							if (len(dependency_list[dep_file_basename]) != len(new_dependency_list)) :
								# they aren't
								# the list changed, so flag the dependency file to be regenerated
								generate = True
							else :
								# they are
								# check if the comparison is based on basenames only
								if (first_iteration and not items_have_paths) :
									# it is
									# check if all the files are the same
									for new_file_path in new_dependency_list :
										# check if this file is in the old list
										if (os.path.basename(new_file_path) not in dependency_list[dep_file_basename]) :
											# the file isn't in the old list
											# the list changed, so flag the dependency file to be regenerated
											generate = True

											# no need to continue checking the rest of items
											break
								else :
									# it isn't
									# check if all the files and their paths are the same
									for new_file_path in new_dependency_list :
										# check if this file is in the old list and its path is the same
										if (new_file_path not in dependency_list[dep_file_basename]) :
											# no match -> either the file isn't in the old list or the path changed
											# the list changed, so flag the dependency file to be regenerated
											generate = True

											# no need to continue checking the rest of items
											break

					# check if dependency_list needs to be updated
					if (build_dep_list) :
						# it does
						dependency_list[dep_file_basename] = new_dependency_list

					# check if the dependency file needs to be generated
					if (generate) :
						# it does
						# build the dependency list string
						dependency_list_str = self.buildDependencyListString(dependency_list[dep_file_basename])

						# generate and save this dependency file
						if (dependency_list_str != "" and self.generateDepFile(src_file_basename, dependency_list_str)) :
							# it was successful
							self.cli_obj.printMsg(1, "The dependency file for \"" + src_file_basename + "\" was updated.", True)
						else :
							# it failed
							self.cli_obj.printMsg(0, "The dependency file for \"" + src_file_basename + "\" failed to be updated.", True)

				# no longer in the first iteration of the loop
				first_iteration = False

				# sleep before starting the next cycle
				self.startSleep(self.config["sleep_timer"])
		except (KeyboardInterrupt, SystemExit) :
			# the user pressed CTRL-C to stop the scan task
			# clear any files found in the last iteration of the scan loop
			self.files.clear()

	# builds the string of whitespace separated dependent files, based on the information
	# in the dependency list for that file
	def buildDependencyListString(self, dependency_list) :
		# stores the final data
		dependency_list_str = ""

		# check if the absolute paths of the dependent files should be used
		if (self.config["dependency_paths"]) :
			# they should
			# NOTE: the paths in the Makefile will have "/" as directory separator
			dependency_list_str = " ".join(dependency_list).replace("\\", "/")
		else :
			# they shouldn't
			dependency_list_str = ""
			for dep_list_file_path in dependency_list :
				dependency_list_str += " " + os.path.basename(dep_list_file_path)

		# return the final data
		return(dependency_list_str.strip())

	# makes the program sleep for a certain number of seconds
	def startSleep(self, sleep_time) :
		# wait X second (set in the "sleep_timer" configuration)
		time.sleep(sleep_time)

	# searches existing dependency files and finds the dependency lists used to generate them
	# returns a dict() with the dependency lists
	def deduceDependencyLists(self) :
		# stores the final data
		data = dict()

		# loop through each existing dependency file
		for dep_file_basename in self.files["dependency"] :
			# find this file's name
			dep_file_name = dep_file_basename[:-len(Application.dep_extension_) - 1]

			# find the corresponding source file's basename
			src_file_basename = ""
			for src_ext in Application.src_extensions_ :
				# check if a source file with this basename exists
				if (dep_file_name + "." + src_ext in self.files["source"]) :
					# it does
					src_file_basename = dep_file_name + "." + src_ext

					# no need to continue
					break

			# check if a corresponding source file was found
			# NOTE: this should never happen, since by the time this function is called
			# 		checkFiles() has already run and removed any .d files with no matching source file
			if (src_file_basename == "") :
				# it wasn't, so move on
				continue

			# grab the content of this dependency file
			dep_file_content = General.General.readFile(self.files["dependency"][dep_file_basename])

			# check if the file's content was successfully acquired
			if (dep_file_content == None) :
				# it wasn't
				continue

			# create the regex string, based on the rule template, for this source file
			regex_str = ""
			for line in self.replaceKeywords(src_file_basename, "|!dependents!|").splitlines() :
				# check if this line has the "|!dependents!|" keyword
				if ("|!dependents!|" in line) :
					# it does
					# this will be the regex string
					regex_str = "^" + re.escape(line).replace(re.escape("|!dependents!|"), "([^\\n\\r]+)") + "$"

			# match the regex string to this dependency file
			re_match = re.search(regex_str, dep_file_content, re.I|re.M)

			# check if the match was successful
			if (re_match == None or re_match.group(1) == None) :
				# it wasn't, so move on
				continue

			# stores the paths found
			dep_list = list()

			# standardize each item in the capture group
			for item in re_match.group(1).strip().split(" ") :
				dep_list.append(General.General.standardizePath(item))

			# check if the list is empty
			if (len(dep_list) == 0) :
				# it is, so move on
				continue

			# store the list
			data[dep_file_basename] = dep_list

		# return the final data
		return(data)

	# scan the file given in path for all #include files and then scan all them as well
	# building a list() of files that are included in the original file provided by path
	# returns the list()
	def buildDependencyList(self, src_file_basename) :
		# print start message
		self.cli_obj.printMsg(1, "Started building dependency list for \"" + src_file_basename + "\"", True)

		# get this source file's absolute path
		src_file_path = self.files["source"][src_file_basename]

		# stores the paths to the dependent files
		dep_list = list()

		# stores the paths to the dependent files that couldn't be found
		# format: [file abs path] = set() with the #include matches that couldn't be found
		# 		  if the set() is empty then the file itself couldn't be found
		failed_files = dict()

		# (re)set some of the DepListBuilder's class variables
		self.dep_list_builder_obj.queue = set([src_file_path])
		self.dep_list_builder_obj.found_files.clear()
		self.dep_list_builder_obj.dep_list = dep_list
		self.dep_list_builder_obj.failed_files = failed_files
		self.dep_list_builder_obj.files = self.files.copy()

		# find all dependent files
		# the dependent files found will be stored in dep_list and any files that
		# couldn't be found will be stored in failed_files
		self.dep_list_builder_obj.run()

		# check if any errors occured
		if (len(failed_files) > 0) :
			# yes
			# build the error message
			message = "The list of dependent files for the source file \"" + src_file_path + "\" "

			# check if incomplete lists are to be used
			if (self.config["use_incomplete_list"]) :
				# they are
				message += " is incomplete, because:"
			else:
				# they aren't
				message += "couldn't be generated, because:"

			# loop through the failed files
			for failed_path in failed_files :
				# check if the file wasn't found
				if (len(failed_files[failed_path]) == 0) :
					# it wasn't
					message += "\n\t- the file \"" + failed_path + "\" couldn't be found."
				else :
					# it was
					message += "\n\t- the contents of these #include directives, in " + failed_path + ", couldn't be found:"

					# loop through the #include directives that couldn't be processed
					for failed_match in failed_files[failed_path] :
						message += "\n\t\t- " + failed_match

			# print error messages
			self.cli_obj.printMsg(0, message, True)

			# check if incomplete lists are to be used
			if (not self.config["use_incomplete_list"]) :
				# they aren't
				# empty the dep_list variable
				dep_list.clear()

		# print end message
		self.cli_obj.printMsg(1, "Finished building dependency list for \"" + src_file_basename + "\"", True)

		# return the final data
		return(dep_list)

	# replaces any valid keywords in the rule template by the respective data
	# returns a string which is the rule template after the keywords have been replaced
	def replaceKeywords(self, src_file_basename, dependency_str) :
		# grab the content of the dependency_template.txt file
		dependency_template_str = General.General.readFile(self.files["dependency_template"])

		# check if the file's content was successfully acquired
		if (dependency_template_str == None) :
			# it wasn't
			return("")

		# find the src file's name and extension
		src_file_name = ""
		src_file_ext = ""

		# check if the source file has an explicit extension
		aux_pos = src_file_basename.rfind(".")
		if (aux_pos != -1) :
			# it has
			src_file_name = src_file_basename[:aux_pos]
			src_file_ext = src_file_basename[aux_pos + 1:]
		else :
			# it doesn't
			src_file_name = src_file_basename

		# process the rule template by replacing any valid keywords by their respective data
		dependency_template_str = dependency_template_str.replace("|!dependents!|", dependency_str)
		dependency_template_str = dependency_template_str.replace("|!src_file_basename!|", src_file_basename)
		dependency_template_str = dependency_template_str.replace("|!src_file_name!|", src_file_name)
		dependency_template_str = dependency_template_str.replace("|!src_file_ext!|", src_file_ext)

		# return the final rule template string
		return(dependency_template_str)

	# generate the dependency file's content, based on the rule template, and save the file
	# to the project's directory tree
	# returns True if successful, False otherwise
	# NOTE: all dependent files will be added with a / as the directory separator (better for Makefile)
	def generateDepFile(self, src_file_basename, dependency_str) :
		# replace any valid keywords in the rule template by the respective data
		dependency_template_str = self.replaceKeywords(src_file_basename, dependency_str)

		# check if the final rule template string is empty
		if (dependency_template_str == "") :
			# it is
			# failed to generate the dependency file
			return(False)

		# split the src file's path into the directory, name and extension
		src_file_parts = os.path.split(self.files["source"][src_file_basename])
		src_file_dir = src_file_parts[0]
		src_file_name = ""
		src_file_ext = ""

		# check if the source file has an explicit extension
		aux_pos = src_file_basename.rfind(".")
		if (aux_pos != -1) :
			# it has
			src_file_name = src_file_basename[:aux_pos]
			src_file_ext = src_file_basename[aux_pos + 1:]
		else :
			# it doesn't
			src_file_name = src_file_basename

		# build the dependency file's path
		dependency_path = self.config["dependency_dir"]

		# check if the dependency file should be stored in the same directory as the source file
		if (dependency_path == "") :
			# it should
			dependency_path = src_file_dir

		# write the rule template to the dependency file for this specific source file
		if (not General.General.writeFile(dependency_path + "\\" + src_file_name + ".d", "w", dependency_template_str)) :
			# failed to write to file
			return(False)

		# at this point, everything went OK
		return(True)

	# resets the configuration in effect to the defaults
	# returns True if successful or False is failed
	def configDefault(self) :
		# reset the current configuration
		self.config.clear()

		# check if the program's default configuration file exists
		json_path = os.path.abspath(self.program_root + "\\data\\default_config.json")
		if (not os.path.isfile(json_path)) :
			# the file doesn't exist
			# print error message
			self.cli_obj.printMsg(0, "The program default configuration file couldn't be found.", True)

			# failed
			self.config.clear()
			return(False)
		else :
			# the file exists
			# decode the default config JSON
			self.config = General.General.parseJSON(json_path)

		# check if the config is empty
		if (len(self.config) == 0) :
			# it is
			# print error message
			self.cli_obj.printMsg(0, "The program's default configuration file is empty.", True)

			# failed
			self.config.clear()
			return(False)

		# validate the loaded configuration
		for config_key in self.config_validation :
			# check if this validation passed
			if (not self.configValidate(config_key, None)) :
				# it didn't
				# failed
				self.config.clear()
				return(False)

		# at this point the loading was successful
		return(True)

	# changes the value of a configuration option with tag "key" to the value "value"
	# returns True if successful or False is failed
	def configSet(self, key, value) :
		# check if the key exists in config
		if (key not in self.config) :
			# it doesn't
			# print error message
			self.cli_obj.printMsg(0, "The configuration \"" + key + "\" doesn't exist.", True)

			# return faillure
			return(False)

		# store the current value for this "key"
		cur_value = self.config[key]

		# update config with the new value
		self.config[key] = value

		# validate the new value
		if (not self.configValidate(key, cur_value)) :
			# the new value failed the validation
			# revert back to the old value
			self.config[key] = cur_value

			# return faillure
			return(False)

		# at this point the change is valid
		return(True)

	# creates a JSON file in this project's directory with the current configuration values
	# the file's name is dependency_config.json
	# returns True if successful or False is failed
	def configSave(self) :
		try :
			# build the file's path
			json_path = self.buildProjConfigPath()

			# build the JSON string
			json_string = json.JSONEncoder(indent=4).encode(self.config)

			# write to the JSON file
			if (not General.General.writeFile(json_path, "w", json_string)) :
				# failed to write to file
				return(False)
		except TypeError as e :
			# failed to encode into JSON
			return(False)

		# at this point everything went OK
		return(True)

	# read from a JSON file in this project's directory and set the configuration values
	# if a JSON file can't be found, the default configurations will be loaded
	# returns True if successful or False is failed
	def configLoad(self) :
		# reset the current configuration
		self.config.clear()

		# get the absolute path to this project's config file
		project_config_path = self.findProjConfigFile()

		# check if the current project has a configuration file
		if (project_config_path == "" or not os.path.isfile(project_config_path)) :
			# it doesn't
			# print warning message
			self.cli_obj.printMsg(2, "This project doesn't have a configuration file yet. Use the command \"config save\" to create one.", True)

			# load the program default configuration
			if(not self.configDefault()) :
				# failed to load the default configuration
				self.config.clear()
				return(False)

			# at this point this program's default configuration was successfully loaded
			# print message
			self.cli_obj.printMsg(1, "The program's default configurations was successfully loaded.", True)
		else :
			# it does
			# decode it
			self.config = General.General.parseJSON(project_config_path)

			# check if the config is empty
			if (len(self.config) == 0) :
				# it is
				# print error message
				self.cli_obj.printMsg(0, "This project's configuration file is empty.", True)

				# failed
				self.config.clear()
				return(False)

			# validate the loaded configuration
			for config_key in self.config_validation :
				# check if this validation passed
				if (not self.configValidate(config_key, None)) :
					# it didn't
					# failed
					self.config.clear()
					return(False)

			# at this point this project's configuration was successfully loaded
			# print message
			self.cli_obj.printMsg(1, "The current project's configuration was successfully loaded.", True)

		# at this point the loading was successful
		return(True)

	# validates the value of the specified configuration key
	# uses the file "config_validation.json" for the validation parameters
	# returns True if the validation passed, False otherwise
	def configValidate(self, config_key, cur_value) :
		# check if the config key exists
		if (config_key not in self.config or config_key not in self.config_validation) :
			# it doesn't
			# print error message
			self.cli_obj.printMsg(0, "The configuration \"" + config_key + "\" doesn't exist.", True)

			# return faillure
			return(False)

		# check if this config's value is an instance of String
		# this is mostly for the cases where a new value is being set, using "config set"
		# and all values will be strings at this point
		if (isinstance(self.config[config_key], str)) :
			# it is
			# check if config value starts with a "
			if (self.config[config_key].startswith("\"")) :
				# it does
				# remove it
				self.config[config_key] = self.config[config_key][1:]

			# check if config value ends with a "
			if (self.config[config_key].endswith("\"")) :
				# it does
				# remove it
				self.config[config_key] = self.config[config_key][:-1]

		# check if the desired data type is a boolean
		if (self.config_validation[config_key]["data_type"] == "bool") :
			# it is
			# check if the value is an instance of bool
			if (not isinstance(self.config[config_key], bool)) :
				# it isn't
				# check if the value is "true"
				if (self.config[config_key].lower() == "true") :
					# it is
					self.config[config_key] = True
				# check if the value is "false"
				elif (self.config[config_key].lower() == "false") :
					# it is
					self.config[config_key] = False
				else :
					# the value is not a valid boolean
					# print error message
					self.cli_obj.printMsg(0, "The configuration \"" + config_key + "\" couldn't be converted to a boolean as specified in config_validation.json.", True)

					# return faillure
					return(False)
		else :
			# it isn't
			try :
				# call the built in function to convert to the correct data type
				self.config[config_key] = getattr(builtins, self.config_validation[config_key]["data_type"])(self.config[config_key])
			except AttributeError as e :
				# this data type doesn't exist
				# print error message
				self.cli_obj.printMsg(0, "The configuration \"" + config_key + "\" couldn't be converted using \"" + self.config_validation[config_key]["data_type"] + "\" as specified in config_validation.json.", True)

				# return faillure
				return(False)

		# if changing this config's value, check if the new value is the same as the current one
		if (cur_value != None and self.config[config_key] == cur_value) :
			# the new value is the same as the current one
			# no need to continue validating
			return(True)

		# check if the "min" parameter needs to be checked and if so validate the config value
		if ("min" in self.config_validation[config_key] and self.config[config_key] < self.config_validation[config_key]["min"]) :
			# the config value is below the minimum
			# print error message
			self.cli_obj.printMsg(0, "The value for the configuration \"" + config_key + "\" is below the valid minimum of " + self.config_validation[config_key]["min"], True)

			# return faillure
			return(False)

		# check if the "max" parameter needs to be checked and if so validate the config value
		if ("max" in self.config_validation[config_key] and self.config[config_key] > self.config_validation[config_key]["max"]) :
			# the config value is above the maximum
			# print error message
			self.cli_obj.printMsg(0, "The value for the configuration \"" + config_key + "\" is above the valid maximum of " + self.config_validation[config_key]["max"] + ".", True)

			# return faillure
			return(False)

		# check if the "empty" parameter needs to be checked and if so validate the config value
		if ("empty" in self.config_validation[config_key] and not self.config_validation[config_key]["empty"] and len(self.config[config_key]) == 0) :
			# the config value is empty when it can't be
			# print error message
			self.cli_obj.printMsg(0, "The value for the configuration \"" + config_key + "\" is empty, which is not allowed.", True)

			# return faillure
			return(False)

		# run the config value through any specified callbacks
		if ("callbacks" in self.config_validation[config_key]) :
			# loop through each callback
			for callback in self.config_validation[config_key]["callbacks"] :
				try :
					if (not getattr(self, callback)(config_key)) :
						# the validations performed by this callback failed
						# print error message
						self.cli_obj.printMsg(0, "The value for the configuration \"" + config_key + "\" didn't pass the validation of \"" + callback + "\".", True)

						# return faillure
						return(False)
				except AttributeError as e :
					# this callback doesn't exist
					# print error message
					self.cli_obj.printMsg(0, "The callback \"" + callback + "\", for the configuration \"" + config_key + "\", doesn't exist.", True)

					# return faillure
					return(False)

		# at this point every validation was passed
		return(True)

	# cross-references the source and dependency files and removes any dependency file that
	# no longer has a matching source file
	# expects files to be a dictionary where the files' data is be stored
	# returns a set() with the basename of the file that are no longer available
	def checkFiles(self) :
		# stores the basename of the dependency files that are no longer relevant
		deleted_files = set()

		# loop through the existing dependency files
		for dep_file_basename in self.files["dependency"].copy() :
			# get this dependency file's name
			dep_file_name = dep_file_basename[:dep_file_basename.rfind(".")]

			# loop through the valid source file extensions
			found_src_file = False
			for src_extension in Application.src_extensions_:
				# check if there is a matching source file for this extension
				if (dep_file_name + "." + src_extension in self.files["source"]) :
					# there is
					found_src_file = True

					# no need to check the other extensions
					break

			# check if a source file was found
			if (not found_src_file) :
				# it wasn't
				# add this file to the set() of deleted files
				deleted_files.add(dep_file_basename)

				# delete this file from the project's directory tree
				os.remove(self.files["dependency"][dep_file_basename])

				# remove this file from files["dependency"]
				del self.files["dependency"][dep_file_basename]

		# return the set() of deleted files
		return(deleted_files)

	# checks if the dependency files are located in the correct directory,
	# based on the current "dependency_dir" config value and if needed move them to the correct directory
	# returns True if successful or False otherwise
	def moveDepFiles(self) :
		# controls if any files failed to be moved
		success = True

		# search for the relevant files
		self.populateFiles()

		# loop through each existing dependency file
		for dep_file_basename in self.files["dependency"].copy() :
			# controls whether this dependency file needs to be moved or not
			move_file = False

			# check if the dependency file should be in the same directory as its respective source file
			if (self.config["dependency_dir"] == "") :
				# it should
				# get this dependency file's name
				aux_pos = dep_file_basename.rfind(".")
				if (aux_pos == -1) :
					dep_file_name = dep_file_basename
				else :
					dep_file_name = dep_file_basename[:aux_pos]

				# find this dependency file's source file
				for src_file_ext in Application.src_extensions_ :
					# build the source file's basename
					src_file_basename = dep_file_name + "." + src_file_ext

					# check if this source file basename exists
					if (src_file_basename in self.files["source"]) :
						# it does
						# check if this file is in the correct location
						if (os.path.dirname(self.files["dependency"][dep_file_basename]) != os.path.dirname(self.files["source"][src_file_basename])) :
							# it isn't
							new_path = os.path.dirname(self.files["source"][src_file_basename]) + "\\" + dep_file_basename
							move_file = True

						# no need to looping through the rest of the source extensions
						break
			else :
				# it shouldn't
				# check if this file is in the correct location
				if (os.path.dirname(self.files["dependency"][dep_file_basename]) != self.config["dependency_dir"]) :
					# it isn't
					new_path = self.config["dependency_dir"] + "\\" + dep_file_basename
					move_file = True

			# check if this dependency file needs to be moved
			if (not move_file) :
				# it doesn't, so move to next file
				continue

			# at this point this dependency file needs to be moved from its current location to the correct one
			if (not General.General.moveFile(self.files["dependency"][dep_file_basename], new_path)) :
				# failed to move the file
				success = False

				# print error message
				self.cli_obj.printMsg(0, "The \"" + dep_file_basename + "\" dependency file could not be moved from its current location to the correct location, based on the \"dependency_dir\" configuration value.", True)
			else :
				# moved the file
				# update this dependency file's path in self.files
				self.files["dependency"][dep_file_basename] = new_path

				# print message
				self.cli_obj.printMsg(1, "Moved file \"" + dep_file_basename + "\".", True)

		# return the success boolean
		return(success)

	# checks if the project specific config file is located in the correct directory,
	# based on the current "dependency_dir" config value and if needed move it to the correct directory
	# returns True if successful or False otherwise
	def moveProjConfigFile(self) :
		# get the absolute path to this project's config file
		project_config_path = self.findProjConfigFile()

		# check if the current project has a configuration file
		if (project_config_path != "" and os.path.isfile(project_config_path)) :
			# it does
			# get the absolute path to where the file should be stored
			correct_path = self.buildProjConfigPath()

			# check if the file is located in the correct directory
			if (project_config_path != correct_path) :
				# it isn't
				# move it to the correct directory
				if (not General.General.moveFile(project_config_path, correct_path)) :
					# couldn't move the existing file to the correct directory
					# print error message
					self.cli_obj.printMsg(0, "The existing configuration file for this project couldn't be moved to the correct location, based on the current value of the \"dependency_dir\" configuration.", True)

					# return faillure
					return(False)

				# print message
				self.cli_obj.printMsg(1, "Moved this project's configuration file.", True)

		# at this point everything went OK
		return(True)

	# builds the absolute path where this project's config file should be located at
	# based on the current "dependency_dir" configuration value
	def buildProjConfigPath(self) :
		# check if the "dependency_dir" config value is empty
		if (self.config["dependency_dir"] == "") :
			# it is
			# the project's config file will be stored in the project's root directory
			return(self.project_root + "\\" + Application.project_config_basename_)
		else :
			# it isn't
			# the "dependency_dir" config value is the path where the file will be stored
			return(self.config["dependency_dir"] + "\\" + Application.project_config_basename_)

	# searches for the location of this project's configuration file, in the project's directory
	# returns the file's absolute path if found, or an empty string if not found
	def findProjConfigFile(self) :
		# stores the absolute path to this project's config file
		project_config_path = ""

		# search for this project's config file, if it exists
		found_files = General.General.findFiles(set([Application.project_config_basename_]), self.project_root)

		# check if this project has a configuration file
		if (len(found_files) > 0) :
			# it has
			# get the project's config file absolute path
			if (Application.project_config_basename_ in found_files) :
				project_config_path = found_files[Application.project_config_basename_]

		# return the path
		return(project_config_path)

	# called to validate some configuration keys that contain a path as value
	# returns True if the validation passed, False otherwise
	# NOTE: assumes any relative paths are relative to the project's root directory
	def preparePath(self, config_key) :
		# check if the config_validation has the "path_types" key
		if ("path_types" not in self.config_validation[config_key]) :
			# it doesn't, so the configuration validation file is not valid
			# print error message
			self.cli_obj.printMsg(0, "The configuration \"" + config_key + "\" needs to have information about the \"path_types\", in the config_validation.json file.", True)

			# terminate the program
			raise KeyError

		# standardize the path
		self.config[config_key] = General.General.standardizePath(self.config[config_key])

		# check if the path is empty
		if (self.config[config_key] == "") :
			# it is, so no validation needed
			return(True)

		# check if it's an absolute path
		if (re.match("[a-z]:[\\\\]", self.config[config_key], re.I) == None) :
			# it isn't, so it's a relative path
			# check if this config can be a relative path
			if ("rel" in self.config_validation[config_key]["path_types"]) :
				# it can
				# check if the path is pointing to the project's root
				if (self.config[config_key] == ".") :
					# it is
					self.config[config_key] = self.project_root
				else :
					# it isn't
					# convert the relative path into an absolute path
					self.config[config_key] = self.project_root + "\\" + self.config[config_key]
			else :
				# it can't
				# print error message
				self.cli_obj.printMsg(0, "The configuration \"" + config_key + "\" has a relative path, which is not valid.", True)

				# return faillure
				return(False)
		else :
			# it is
			# check if this config can be an absolute path
			if ("abs" not in self.config_validation[config_key]["path_types"]) :
				# it can't
				# print error message
				self.cli_obj.printMsg(0, "The configuration \"" + config_key + "\" has an absolute path, which is not valid.", True)

				# return faillure
				return(False)

		# at this point the validation passed
		return(True)

	# called when the "dependency_dir" configuration is changed
	# returns True if successful, False otherwise
	def updateFilesLoc(self, config_key) :
		# call the function that moves, if needed, the project's config file
		if (not self.moveProjConfigFile()) :
			# the operation failed
			return(False)

		# call the function that moves, if needed, the dependency files
		if (not self.moveDepFiles()) :
			# the operation failed
			return(False)

		# at this point the validation passed
		return(True)

	# called when the "builtin_libs" or "search_paths" configurations are changed
	# returns True if successful, False otherwise
	def updateSearchPaths(self, config_key) :
		# check if the DepListBuilder instance has been created
		# NOTE: relevant when the initial configuration is loaded on the program's start
		if (hasattr(self, "dep_list_builder_obj")) :
			# it has
			# rebuild the DepListBuilder's search paths
			self.dep_list_builder_obj.buildSearchPaths()

		# this particular operation doesn't return faillure
		return(True)

	# getter for config
	def getConfig(self) :
		return(self.config)
