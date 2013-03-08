#!/usr/bin/env python
"""This tool builds or repacks the client binaries.

This handles invocations for the build across the supported platforms including
handling Visual Studio, pyinstaller and other packaging mechanisms.
"""

import os
import platform
import sys
import time

# pylint: disable=W0611
from grr.client import client_plugins
# pylint: enable=W0611

from grr.client import conf

from grr.lib import build
from grr.lib import config_lib
from grr.lib import registry
from grr.lib import type_info

parser = conf.PARSER

if "32 bit" in sys.version:
  default_arch = "i386"
else:
  default_arch = "amd64"

config_lib.DEFINE_choice("ClientBuilder.arch", default=default_arch,
                         choices=["i386", "amd64"],
                         help="The architecture to build or repack for.")

parser.add_argument(
    "--platform", choices=["darwin", "linux", "windows"],
    default=platform.system().lower(),
    help="The platform to build or repack for. This will default to "
    "the current platform: %s." % platform.system())

config_lib.DEFINE_option(type_info.PathTypeInfo(
    name="ClientBuilder.source", must_exist=True,
    default=os.path.normpath(__file__ + "/../../.."),
    help="The location of the source files."))

config_lib.DEFINE_option(type_info.PathTypeInfo(
    name="ClientBuilder.executables_dir",
    default="%(ClientBuilder.source)/grr/executables",
    help="The directory that contains the executables."))

# Initialize sub parsers and their arguments.
subparsers = parser.add_subparsers(
    title="subcommands", dest="subparser_name", description="valid subcommands")

# Build arguments.
parser_build = subparsers.add_parser(
    "build", help="Build a client from source.")

subparsers.add_parser(
    "deploy", help="Build a deployable self installer from a template.")

config_lib.DEFINE_string(
    name="ClientBuilder.build_time",
    default=time.ctime(),
    help="Time of build to embed into binary.")

config_lib.DEFINE_string(
    name="ClientBuilder.platform",
    default="%(platform|flags)",
    help="The platform to build for (comes from --platform).")

config_lib.DEFINE_string(
    "ClientBuilder.packagemaker",
    default=("/Developer/Applications/Utilities/PackageMaker.app/Contents"
             "/MacOS/PackageMaker"),
    help="Location of the PackageMaker executable.")

config_lib.DEFINE_option(type_info.PathTypeInfo(
    name="ClientBuildWindows.vs_dir", must_exist=True,
    default=r"%{C:\Program Files (x86)\Microsoft Visual Studio 10.0}",
    help="Location of the main Visual Studio directory."))

args = parser.parse_args()


def main(_):
  """Launch the appropriate builder."""
  config_lib.CONFIG.SetEnv("Environment.component", "ClientBuilder")

  registry.Init()

  if args.platform == "darwin":
    builder = build.DarwinClientBuilder()
  elif args.platform == "windows":
    builder = build.WindowsClientBuilder()
  elif args.platform == "linux":
    builder = build.LinuxClientbuilder()

  if args.subparser_name == "build":
    builder.MakeExecutableTemplate()

  elif args.subparser_name == "deploy":
    builder.MakeDeployableBinary(config_lib.CONFIG["ClientBuilder.output"])

  else:
    parser.error("Unsupported build platform: %s" % args.platform)


if __name__ == "__main__":
  conf.StartMain(main)
