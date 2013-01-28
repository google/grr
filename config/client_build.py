#!/usr/bin/env python
# Copyright 2012 Google Inc.
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""This tool builds or repacks the client binaries.

This handles invocations for the build across the supported platforms including
handling Visual Studio, pyinstaller and other packaging mechanisms.
"""



import argparse
import os
import platform
import sys
import time

from distutils import sysconfig

from grr.lib import build
from grr.lib import config_lib

parser = argparse.ArgumentParser(description="Build client binaries.")

if "32 bit" in sys.version:
  default_arch = "i386"
else:
  default_arch = "amd64"

parser.add_argument(
    "--arch", default=default_arch, choices=["i386", "amd64"],
    help="The architecture to build or repack for. This will default to: "
    "amd64.")

parser.add_argument(
    "-c", "--configuration",
    help="The configuration file.")

parser.add_argument(
    "--platform", choices=["Darwin", "Linux", "Windows"],
    default=platform.system(),
    help="The platform to build or repack for. This will default to "
    "the current platform: %s." % platform.system())

parser.add_argument(
    "--source", default="grr",
    help="The location of the source files.")

parser.add_argument(
    "--executables_dir", default=os.path.join("grr", "executables"),
    help="The directory that contains the executables.")

# Initialize sub parsers and their arguments.
subparsers = parser.add_subparsers(
    title="subcommands", dest="subparser_name", description="valid subcommands")

# Build arguments.
parser_build = subparsers.add_parser(
    "build", help="Build a client from source.")

parser_build.add_argument(
    "--build_dir", default=os.getcwd(), help="The directory we build in.")

parser_build.add_argument(
    "--build_time", default=time.ctime(),
    help="Time of build to embed into binary.")

parser_build.add_argument(
    "--installer_type", default="vbs", choices=["bat", "vbs"],
    help="The installer type.")

parser.add_argument(
    "--packagemaker",
    default=("/Developer/Applications/Utilities/PackageMaker.app/Contents"
             "/MacOS/PackageMaker"),
    help="Location of the PackageMaker executable.")

parser_build.add_argument(
    "--pyinstaller",
    default=os.path.join(sysconfig.PREFIX, "pyinstaller", "pyinstaller.py"),
    help="Location of the pyinstaller.py script.")

parser_build.add_argument(
    "--vs_dir",
    default=r"C:\Program Files (x86)\Microsoft Visual Studio 10.0",
    help="Location of the main Visual Studio directory.")

args = parser.parse_args()


def main():
  if not os.path.exists(args.source):
    parser.error("No such source: %s" % args.source)

  build_files_dir = os.path.join(args.source, "config")

  if not os.path.exists(build_files_dir):
    parser.error("No such build files directory: %s" % build_files_dir)

  if args.subparser_name == "build":
    args.configuration = args.configuration or os.path.join(
        build_files_dir, "client_build.conf")
    config = config_lib.ConfigManager()
    config.Initialize(args.configuration)

    if not os.path.exists(args.pyinstaller):
      parser.error("No such pyinstaller: %s" % args.pyinstaller)

    if args.platform == "Darwin":
      if not os.path.exists(args.packagemaker):
        parser.error("No such packagemaker: %s" % args.packagemaker)

      client_builder = build.DarwinClientBuilder(
          args.source, build_files_dir, args.build_dir, args.build_time,
          args.pyinstaller, config, args.arch, args.packagemaker)

    elif args.platform == "Windows":
      if not os.path.exists(args.vs_dir):
        parser.error("No such vs_dir: %s" % args.vs_dir)

      client_builder = build.WindowsClientBuilder(
          args.source, build_files_dir, args.build_dir, args.build_time,
          args.pyinstaller, config, args.arch, args.executables_dir,
          args.vs_dir, args.installer_type)

    else:
      parser.error("Unsupported build platform: %s" % args.platform)

    client_builder.Build()


if __name__ == "__main__":
  main()
