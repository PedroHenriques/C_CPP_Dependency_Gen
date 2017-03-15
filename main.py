############################################################
#															#
# C_CPP_Dependency_Gen v1.0.0								#
#															#
# Copyright 2017, PedroHenriques							#
# http://www.pedrojhenriques.com							#
# https://github.com/PedroHenriques							#
#															#
# Free to use under the MIT license.						#
# http://www.opensource.org/licenses/mit-license.php		#
#															#
############################################################

import traceback
from classes import Application, Cli

# code that starts the entire application
try :
	# instantiate the application's main class
	app = Application.Application()

	# start the program's core task
	app.run()
except (KeyboardInterrupt, SystemExit) :
	# the user pressed CTRL-C so terminate the program
	# print the outro message
	app.outro_msg()
except Exception as e :
	print("\n")
	traceback.print_exc()
	print("\n")
