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

import os

class General :
	"""Contains static functions usefull in other classes.
	This class is not ment to be instantiated directly."""

	# class variable storing
	json_decoder_ = None

	def __init__(self) :
		pass

	# searches the directory "path" and all sub-directories for all relevant files
	# "basenames" should be a set() with the basenames of the files to search for
	# those basenames can be of the form "*.extension" to search for all files with that extension
	# returns a dict() with format: [file basename] = file absolute paths
	# NOTE: this method expects path to point to a directory, not a file
	# NOTE: will be called recursively
	@staticmethod
	def findFiles(basenames, path) :
		# stores the final data
		files = dict()

		# standardize "path"
		path = General.standardizePath(path)

		# check if the path is a directory
		if (not os.path.isdir(path)) :
			# it isn't, so bail out
			return(files)

		# grab the contents of the directory pointed by path
		dir_contents = os.listdir(path)

		# stores the names of the directories found
		dir_names = set()

		# loop through each item in the directory, checking all the files in the current directory
		# ends when all files have been checked or all basenames found
		# NOTE: any folders in this directory will be checked after the files, if necessary
		while len(basenames) > 0 and len(dir_contents) > 0 :
			# grab the last item in the list
			cur_item_basename = dir_contents.pop()
			cur_item_path = path + "\\" + cur_item_basename

			# check if the item is a file
			if (os.path.isfile(cur_item_path)) :
				# it is a file
				# get this file's extension
				aux_pos = cur_item_basename.rfind(".")
				if (aux_pos == -1) :
					# this file doesn't have an explicit extension
					cur_item_extension = ""
				else :
					cur_item_extension = cur_item_basename[aux_pos + 1:]

				# check if this file's basename is one of the relevant files
				if (cur_item_basename in basenames) :
					# this file is relevant and it's a specific file
					# add the file to the final data
					files[cur_item_basename] = cur_item_path

					# remove this file from the basenames left to find
					basenames.remove(cur_item_basename)
				elif ("*." + cur_item_extension in basenames) :
					# this file is relevant, but it's not a specific file
					# add the file to the final data
					files[cur_item_basename] = cur_item_path
			else :
				# it isn't a file
				# store this directory's name to be checked later, if necessary
				dir_names.add(cur_item_path)

			# if there are still basenames to be found and the current directory has
			# folders, go through them
			# ends when all folders have been checked or all basenames found
			while len(basenames) > 0 and len(dir_names) > 0 :
				# grab a path to a folder
				cur_item_path = dir_names.pop()

				# call this method recursively to process this item
				found_files = General.findFiles(basenames, cur_item_path)

				# check if any files were found
				if (len(found_files) > 0) :
					# they were
					# loop through each file found
					for found_file_basename in found_files :
						# add this file to this function call's final data
						files[found_file_basename] = found_files[found_file_basename]

		# return the final data
		return(files)

	# executes the necessary adjustments to a path to make it standardized for the program
	# can receive both relative and absolute paths
	# returns the processed path
	@staticmethod
	def standardizePath(path) :
		# change all "/" to "\"
		path = path.replace("/", "\\")

		# check if the path starts with a "\"
		if (path.startswith("\\")) :
			# it does, so remove it
			path = path[1:]

		# check if the path ends with a "\"
		if (path.endswith("\\")) :
			# it does, so remove it
			path = path[:-1]

		# return the processed path
		return(path)

	# opens and reads the contents of a file
	# returns a string with the file's contents or an empty string if it failled
	@staticmethod
	def readFile(file_path) :
		try:
			# get the file's content
			file_object = open(file_path, "r", encoding = "utf-8")
			file_content = file_object.read()
			file_object.close()

			return(file_content)
		except OSError as e:
			# failled to open file
			return(None)

	# opens/creates and writes a string to a file
	# returns True if successful or False otherwise
	@staticmethod
	def writeFile(file_path, mode, contents) :
		try:
			# get the file's content
			file_object = open(file_path, mode, encoding = "utf-8")
			file_content = file_object.write(contents)
			file_object.close()

			return(True)
		except OSError as e:
			# failled to open/write file
			return(False)

	# "moves" a file from 1 location to another
	# returns True if successful or False otherwise
	@staticmethod
	def moveFile(file_cur_path, file_new_path) :
		# check if file_cur_path exists
		if (not os.path.isfile(file_cur_path)) :
			# it doesn't
			# return faillure
			return(False)

		# check if the directory of file_new_path exists
		file_new_dirname = os.path.dirname(file_new_path)
		if (not os.path.isdir(file_new_dirname)) :
			# it doesn't, so create it
			os.makedirs(file_new_dirname)

		try :
			# grab the content of file_cur_path
			file_content = General.readFile(file_cur_path)

			# check if the file's content was successfully acquired
			if (file_content == None) :
				# it wasn't
				return(False)

			# create the new file and copy the content of the existing file to it
			if (not General.writeFile(file_new_path, "w", file_content)) :
				# failled to write to file
				return(False)

			# remove the file_cur_path
			os.remove(file_cur_path)

			# at this point everything went ok
			return(True)
		except OSError as e :
			# failled to delete file
			return(False)

	# opens and decodes the contents of the requested JSON file
	# returns the decoded JSON file's content or an empty dict()
	@staticmethod
	def parseJSON(file_path) :
		# check if the json decoder has been created
		if (General.json_decoder_ == None) :
			# it hasn't
			raise Exception("The JSON decoder object isn't stored in General.json_decoder_.")

		# check if the provided path is a file
		if (not os.path.isfile(file_path)) :
			# it isn't
			return({})

		# grab the content of the json file
		json_string = General.readFile(file_path)

		# check if the file's content was successfully acquired
		if (json_string == None) :
			# it wasn't
			return({})

		# decode json_string and return it
		try :
			return(General.json_decoder_.decode(json_string))
		except  ValueError as e :
			# not a valid JSON file
			return({})
