#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# The MIT License (MIT)
#
# Copyright (c) 2017 Jakub Bednar
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.
#

import argparse
import os
import os.path
import subprocess
import sys


class CarthageFrameworkDeployer:
	buildFolder = ""
	carthageFolder = ""
	isRelease = False
	frameworksToProcess = []
	frameworksDone = []
	frameworksToCopy = []
	debug = False

	def __init__(self):
		self.checkXcodeBuild()
		self.buildFolder = os.path.join(os.environ["BUILT_PRODUCTS_DIR"], os.environ["FRAMEWORKS_FOLDER_PATH"])
		self.isRelease = os.environ["CONFIGURATION"] == "Release"
		self.loadRequestedFrameworks()
		if self.debug:
			print("Carthage folder: " + self.carthageFolder)
			print("Environment frameworks: " + "\n\t".join(self.frameworksToProcess))

	def usage(self):
		print("Setup this script into a RunScript BuildPhase in your Xcode project. Setup Input Files to point to your root dependecy frameworks")
		print("This utility will use otool -L to automatically detect required dependencies and copy them as well")
		sys.exit(1)

	def checkXcodeBuild(self):
		""" Checks whether we are executed from Xcode build """
		for required in ["BUILT_PRODUCTS_DIR", "FRAMEWORKS_FOLDER_PATH", "CONFIGURATION"]:
			if not required in os.environ:
				print(required + " not in environment. This is not an Xcode build.")
				self.usage()

	def loadRequestedFrameworks(self):
		""" Loads list of frameworks passed to the Xcode build """
		count = int(os.environ["SCRIPT_INPUT_FILE_COUNT"])
		for index in range(count):
			inputParam = os.environ["SCRIPT_INPUT_FILE_" + str(index)]
			path, framework = os.path.split(inputParam)
			if self.carthageFolder == "":
				self.carthageFolder = path
			elif self.carthageFolder != path:
				print("ERROR: There are frameworks from multiple Carthage build folders in InputFiles")
				sys.exit(1)

			self.frameworksToProcess.append(framework)

	def shouldCopyFramework(self, framework):
		""" Determines whether framework should be copied. In Release build we allways copy."""
		if self.isRelease:
			return True

		return not os.path.isdir(os.path.join(self.buildFolder, framework))

	def checkAndAddDependencies(self, framework):
		"""Uses otool -L to list dependencies of given framework. 
		   Dependencies residing in the carthageFolder are added to list of frameworks to process."""
		noExtension = os.path.splitext(framework)[0]
		frameworkPath = os.path.join(self.carthageFolder, framework, noExtension)
		if self.debug:
			print("Running: otool -L " + frameworkPath)

		dependencies = subprocess.check_output(["otool", "-L", frameworkPath])
		# process the dependencies. Slice them by '/' and look for the part that has .framework or .bundle in it
		lines = dependencies.splitlines()
		for line in lines:
			paths = line.split(os.sep)
			for subpath in paths:
				if ".framework" in subpath or ".bundle" in subpath:
					# check whether this framework resides in the Carthage folder
					if os.path.isdir(os.path.join(self.carthageFolder, subpath)):
						self.frameworksToProcess.append(subpath)
						break

	def copyFrameworks(self):
		"""Main function"""
		while len(self.frameworksToProcess) != 0:
			framework = self.frameworksToProcess.pop(0)
			if not framework in self.frameworksDone:
				self.checkAndAddDependencies(framework)
				self.frameworksToCopy.append(framework)
				self.frameworksDone.append(framework)

		# Do we have anything to do?
		if not self.frameworksToCopy:
			print("Nothing to copy. Try clean build if you want your dependencies to be copied again.")
			return
		else:
			print("Copying:\n\t" + "\n\t".join(self.frameworksToCopy))

		# Export environment variables needed by Carthage
		os.environ["SCRIPT_INPUT_FILE_COUNT"] = str(len(self.frameworksToCopy))

		for i, framework in enumerate(self.frameworksToCopy):
			os.environ["SCRIPT_INPUT_FILE_" + str(i)] = os.path.join(self.carthageFolder, framework)

		subprocess.check_call(["carthage", "copy-frameworks"])


if __name__ == "__main__":
	deployer = CarthageFrameworkDeployer()
	deployer.copyFrameworks()

