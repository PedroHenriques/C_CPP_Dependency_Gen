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

import re, time

class Cli :
	"""Processes any command line inputs to the program."""

	def __init__(self, caller_obj) :
		# store the caller object
		self.caller_obj = caller_obj

		# controls whether the outro message has been printed or not
		# NOTE: in a very specific situation, after printing the outro message but before the call to "app.run()" in main.py
		# 		can be concluded if a "KeyboardInterrupt" or "SystemExit" exception fired it would print the outro message again
		self.outro_msg_printed = False

	# prints a message to the screen
	# type:
	# 		0 = error
	# 		1 = normal message
	# 		2 = warning
	def print_msg(self, type, text, show_timestamp) :
		# build the message string
		message = "\n"

		# check if the timestamp should be added to the message
		if (show_timestamp) :
			# it should
			# local variable with the current system date/time
			local_time_aux = time.localtime()

			# add the timestamp, as HH-MM-SS, to the message
			message += "[" + "{0}:{1}:{2}".format(str(local_time_aux.tm_hour), str(local_time_aux.tm_min).zfill(2), str(local_time_aux.tm_sec).zfill(2)) + "] "

		# check which type of message will be printed
		if (type == 0) :
			# error message
			message += "ERROR: " + text
		elif (type == 1) :
			# normal message
			message += text
		elif (type == 2) :
			# warning message
			message += "WARNING: " + text

		# print the message
		print(message)

	# prompts the user for a command to execute and then calls the respective method
	# to process that command
	def askCommand(self) :
		# The value that will be returned by this method
		# 0 = end program | 1 = start running the program
		output = 0

		try :
			# loop untill the user calls the RUN command or one of the program termination commands
			end_scan = False
			while not end_scan :
				# ask the user for a command
				print("\n")
				user_input = input("--> Please type a command: ")

				# get the relevant data from the command given
				# NOTE: 1st pass on the input to grab the command
				# 		Any parameters provided will be processed by the command's method
				re_match = re.fullmatch("^([^\\s]+)(.+)?$", user_input, re.I)

				# check if the input matched the regexp
				if (re_match == None) :
					# it didn't
					# print error message
					self.print_msg(0, "The input provided is not valid.\nType \"help\" for a list of valid commands.", True)

					continue

				# extract the command and parameters
				re_match_groups = re_match.groups("")
				command = re_match_groups[0]
				parameters = re_match_groups[1]

				# try calling a method to process this command
				try :
					# if the method is called, store the return value
					output = getattr(self, "process" + command.capitalize())(parameters)

					# check if this loop should continue
					if (output != 0) :
						# the loop should end
						end_scan = True
				except AttributeError as e :
					# couldn't find a method matching the command given
					# print error message
					self.print_msg(0, "The command " + command + " is not valid.\nType \"help\" for a list of valid commands.", True)

					# continue the loop alive
					output = 0
		except (KeyboardInterrupt, SystemExit) :
			# the user pressed CTRL-C so terminate the program
			output = -1

		return(output)

	# processes the "run" command
	def processRun(self, parameters) :
		# signal this class that it should stop asking for commands and inform
		# the caller object to start running the program
		return(1)

	# processes the "help" command
	def processHelp(self, parameters) :
		# build the help text
		str = "The valid commands are:\n\t- run: starts the scan of the source files and the generation of the dependency files as needed."
		str += "\n\t- config show: shows the current configuration in effect for this project."
		str += "\n\t- config set key=value: changes the configuration with tag \"key\" to the value of \"value\"."
		str += "\n\t- config save: saves the current configuration for this project, which will be loaded and used in the future."
		str += "\n\t- config load: loads this project's configuration if one exists, or the program default configuration otherwise."
		str += "\n\t- config default: changes the current configuration to the program default configuration."
		str += "\n\t- help: shows help information."
		str += "\n\t- exit: exit the program."

		# print the valid commands
		self.print_msg(1, str, False)

		# signal this class to continue asking for commands
		return(0)

	# processes the "config" command
	def processConfig(self, parameters) :
		# split the parameters into the expected parts
		re_match = re.fullmatch("^\\s*([^\\s]+)(.*)$", parameters, re.I)

		# check if the parameters provided are valid
		if (re_match == None) :
			# they aren't
			# print error message
			self.print_msg(0, "The parameters provided to the config command aren't valid.\nType \"help\" for a list of valid syntax.", True)

			# signal this class to continue asking for commands
			return(0)

		# extract the sub-command
		re_match_groups = re_match.groups("")
		sub_command = re_match_groups[0].strip()

		# process the sub-command
		if (sub_command == "show") :
			# stores the message text
			text = "The current configurations in effect for this project are:"

			# get the current configuration
			config_data = self.caller_obj.getConfig()

			# loop through the current configuration
			for config_key in config_data :
				# add this configuration to the message text
				text += "\n\t- " + config_key + " = " + str(config_data[config_key])

			# print the message
			self.print_msg(1, text, True)
		elif (sub_command == "save") :
			# inform the Application class to save the current configuration
			if (self.caller_obj.configSave()) :
				# the operation was successful
				# print message
				self.print_msg(1, "The current configurations were successfully saved.", True)
			else :
				# something went wrong
				# print error message
				self.print_msg(0, "The current configurations couldn't be saved. Please try again.", True)
		elif (sub_command == "load") :
			# inform the Application class to load this project's configuration
			# NOTE: the success message will be printed by configLoad() if this project has a config file
			if (not self.caller_obj.configLoad()) :
				# something went wrong
				# print error message
				self.print_msg(0, "The current project's configuration couldn't be loaded. Please try again.", True)
		elif (sub_command == "set") :
			# extract the configuration tag and new value
			config_data = re_match_groups[1].strip()
			config_data_match = re.fullmatch("^([^\\s=]+)=([^\\s=]+)$", config_data, re.I)

			# check if the regex matched
			if (config_data_match == None) :
				# it didn't
				# print error message
				self.print_msg(0, "The configuration key-value pair provided \"" + config_data + "\" is not valid.\nType \"config show\" for a list of valid configuration keys.", True)

				# signal this class to continue asking for commands
				return(0)

			# get the matching groups
			config_data_match_groups = config_data_match.groups("")

			# store the key and value
			config_key = config_data_match_groups[0]
			config_value = config_data_match_groups[1]

			# check if the "key" is empty
			if (config_key == "") :
				# it is
				# print error message
				self.print_msg(0, "The key for a configuration change can't be empty.", True)

				# signal this class to continue asking for commands
				return(0)

			# inform the Application class to change this configuration's value
			if (self.caller_obj.configSet(config_key, config_value)) :
				# the operation was successful
				# print message
				self.print_msg(1, "The configuration " + config_key + " was successfully changed.\nIn order to preserve this change don't forget to call \"config save\".", True)
			else :
				# something went wrong
				# print error message
				self.print_msg(0, "The configuration " + config_key + " couldn't be changed. Please try again.", True)
		elif (sub_command == "default") :
			# inform the Application class to load the program default configuration
			if (self.caller_obj.configDefault()) :
				# the operation was successful
				# print message
				self.print_msg(1, "The program's default configurations was successfully loaded.", True)
			else :
				# something went wrong
				# print error message
				self.print_msg(0, "The program's default configurations couldn't be loaded. Please try again.", True)
		else :
			# the sub-command is not valid
			# print error message
			self.print_msg(0, "The sub-command " + sub_command + " is not valid.\nType \"help\" for a list of valid syntax.", True)

		# signal this class to continue asking for commands
		return(0)

	# processes the "exit" command
	def processExit(self, parameters) :
		# signal this class that it should stop asking for commands and inform
		# the caller object to terminate the program
		return(-1)
