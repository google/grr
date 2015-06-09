#!/usr/bin/env python
"""This tool builds or repacks the client binaries.

This handles invocations for the build across the supported platforms including
handling Visual Studio, pyinstaller and other packaging mechanisms.
"""

import getpass
import logging
import os
import platform
import time


# pylint: disable=unused-import
from grr.client import client_plugins
# pylint: enable=unused-import

from grr.lib import build
from grr.lib import builders
from grr.lib import config_lib
from grr.lib import flags
from grr.lib import startup
from grr.lib.builders import signing

parser = flags.PARSER

# Guess which arch we should be building based on where we are running.
if platform.architecture()[0] == "32bit":
  default_arch = "i386"
else:
  default_arch = "amd64"

default_platform = platform.system().lower()
parser.add_argument(
    "--platform", choices=["darwin", "linux", "windows"],
    default=default_platform,
    help="The platform to build or repack for. This will default to "
    "the current platform: %s." % platform.system())

parser.add_argument(
    "--arch", choices=["amd64", "i386"],
    default=default_arch,
    help="The architecture to build or repack for.")

parser.add_argument("--sign", action="store_true", default=False,
                    help="Sign executables.")

# Guess which package format we should be building based on where we are
# running.
if default_platform == "linux":
  distro = platform.linux_distribution()[0]
  if distro in ["Ubuntu", "debian"]:
    default_package = "deb"
  elif distro in ["CentOS Linux", "CentOS", "centos", "redhat", "fedora"]:
    default_package = "rpm"
  else:
    default_package = None
elif default_platform == "darwin":
  default_package = "dmg"
elif default_platform == "windows":
  default_package = "exe"

parser.add_argument(
    "--package_format", choices=["deb", "rpm"],
    default=default_package,
    help="The packaging format to use when building a Linux client.")

# Initialize sub parsers and their arguments.
subparsers = parser.add_subparsers(
    title="subcommands", dest="subparser_name", description="valid subcommands")

# Build arguments.
parser_build = subparsers.add_parser(
    "build", help="Build a client from source.")

parser_repack = subparsers.add_parser(
    "repack", help="Repack a zip file into an installer (Only useful when "
    "signing).")

parser_repack.add_argument("--template", default=None,
                           help="The template zip file to repack.")

parser_repack.add_argument("--output", default=None,
                           help="The path to write the output installer.")

parser_repack.add_argument("--outputdir", default="",
                           help="The directory to which we should write the "
                           "output installer. Installers will be named "
                           "automatically from config options. Incompatible"
                           " with --output")

parser_repack.add_argument("--debug_build", action="store_true", default=False,
                           help="Create a debug client.")

parser_repack.add_argument("-p", "--plugins", default=[], nargs="+",
                           help="Additional python files that will be loaded "
                           "as custom plugins.")


parser_deploy = subparsers.add_parser(
    "deploy", help="Build a deployable self installer from a package.")

parser_deploy.add_argument("--template", default=None,
                           help="The template zip file to deploy.")

parser_deploy.add_argument("--templatedir", default="",
                           help="Directory containing template zip files to "
                           "repack. Incompatible with --template")

parser_deploy.add_argument("--output", default=None,
                           help="The path to write the output installer.")

parser_deploy.add_argument("--outputdir", default="",
                           help="The directory to which we should write the "
                           "output installer. Installers will be named "
                           "automatically from config options. Incompatible"
                           " with --output")

parser_deploy.add_argument("-p", "--plugins", default=[], nargs="+",
                           help="Additional python files that will be loaded "
                           "as custom plugins.")

parser_deploy.add_argument("--debug_build", action="store_true", default=False,
                           help="Create a debug client.")

parser_buildanddeploy = subparsers.add_parser(
    "buildanddeploy",
    help="Build and deploy clients for multiple labels and architectures.")

parser_buildanddeploy.add_argument("--templatedir", default="", help="Directory"
                                   "containing template zip files to repack.")

parser_buildanddeploy.add_argument("--debug_build", action="store_true",
                                   default=False, help="Create a debug client.")
args = parser.parse_args()


def GetBuilder(context):
  """Get instance of builder class based on flags."""
  try:
    if "Target:Darwin" in context:
      builder_class = builders.DarwinClientBuilder
    elif "Target:Windows" in context:
      builder_class = builders.WindowsClientBuilder
    elif "Target:LinuxDeb" in context:
      builder_class = builders.LinuxClientBuilder
    elif "Target:LinuxRpm" in context:
      builder_class = builders.CentosClientBuilder
    else:
      parser.error("Bad build context: %s" % context)

  except AttributeError:
    raise RuntimeError("Unable to build for platform %s when running "
                       "on current platform." % args.platform)

  return builder_class(context=context)


def GetDeployer(context, signer=None):
  """Get the appropriate client deployer based on the selected flags."""
  # TODO(user): The builder-deployer separation probably can be consolidated
  # into something simpler under the vagrant build system.
  if "Target:Darwin" in context:
    deployer_class = build.DarwinClientDeployer
  elif "Target:Windows" in context:
    deployer_class = build.WindowsClientDeployer
  elif "Target:LinuxDeb" in context:
    deployer_class = build.LinuxClientDeployer
  elif "Target:LinuxRpm" in context:
    deployer_class = build.CentosClientDeployer
  else:
    parser.error("Bad build context: %s" % context)

  return deployer_class(context=context, signer=signer)


def GetSigner(context):
  if args.platform == "windows" and args.subparser_name in ["deploy", "repack",
                                                            "buildanddeploy"]:
    passwd = getpass.getpass()
    cert = config_lib.CONFIG.Get(
        "ClientBuilder.windows_signing_cert", context=context)
    key = config_lib.CONFIG.Get(
        "ClientBuilder.windows_signing_key", context=context)
    app_name = config_lib.CONFIG.Get(
        "ClientBuilder.windows_signing_application_name", context=context)
    return signing.WindowsCodeSigner(cert, key, passwd, app_name)
  else:
    parser.error("Signing only supported on windows for deploy, repack,"
                 " buildanddeploy")


def TemplateInputFilename(context):
  """Build template file name from config."""
  if args.templatedir:
    filename = config_lib.CONFIG.Get("PyInstaller.template_filename",
                                     context=context)
    return os.path.join(args.templatedir, filename)
  return None


def BuildAndDeployWindows(signer=None):
  """Run buildanddeploy for 32/64 dbg/prod."""
  build_combos = [
      {"arch": "amd64", "debug_build": True},
      {"arch": "amd64", "debug_build": False},
      {"arch": "i386", "debug_build": True},
      {"arch": "i386", "debug_build": False}]
  timestamp = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
  args.package_format = "exe"

  context_orig = SetOSContextFromArgs([])
  # Take a copy of the context list so we can reset back to clean state for each
  # buildanddeploy run
  context = list(context_orig)
  for argset in build_combos:
    for key, value in argset.items():
      setattr(args, key, value)
    context = SetArchContextFromArgs(context)
    context = SetDebugContextFromArgs(context)
    print "Building for: %s" % context
    BuildAndDeploy(context, timestamp=timestamp, signer=signer)
    context = list(context_orig)


def BuildAndDeploy(context, signer=None, timestamp=None):
  """Run build and deploy to create installers."""
  # ISO 8601 date
  timestamp = timestamp or time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())

  if args.plugins:
    config_lib.CONFIG.Set("Client.plugins", args.plugins)

  # Output directory like: 2015-02-13T21:48:47-0800/linux_amd64_deb/
  spec = "_".join((args.platform, args.arch, args.package_format))
  output_dir = os.path.join(config_lib.CONFIG.Get(
      "ClientBuilder.executables_path", context=context), timestamp, spec)

  # If we weren't passed a template, build one
  if args.templatedir:
    template_path = TemplateInputFilename(context)
  else:
    template_path = os.path.join(output_dir, config_lib.CONFIG.Get(
        "PyInstaller.template_filename", context=context))
    builder_obj = GetBuilder(context)
    builder_obj.MakeExecutableTemplate(output_file=template_path)

  # Get the list of contexts which we should be building.
  context_list = config_lib.CONFIG.Get("ClientBuilder.BuildTargets")

  logging.info("Building installers for: %s", context_list)
  deployed_list = []
  for deploycontext in context_list:

    # Add the settings for this context
    for newcontext in deploycontext.split(","):
      context.append(newcontext)

    try:
      deployer = GetDeployer(context, signer=signer)

      # If the ClientBuilder.target_platforms doesn't match our environment,
      # skip.
      if not config_lib.CONFIG.MatchBuildContext(args.platform, args.arch,
                                                 args.package_format,
                                                 context=deployer.context):
        continue

      # Make a nicer filename out of the context string.
      context_filename = deploycontext.replace(
          "AllPlatforms Context,", "").replace(",", "_").replace(" ", "_")
      deployed_list.append(context_filename)

      output_filename = os.path.join(
          output_dir, context_filename,
          config_lib.CONFIG.Get("ClientBuilder.output_filename",
                                context=deployer.context))

      logging.info("Deploying %s as %s with labels: %s", deploycontext,
                   config_lib.CONFIG.Get(
                       "Client.name", context=deployer.context),
                   config_lib.CONFIG.Get(
                       "Client.labels", context=deployer.context))

      deployer.MakeDeployableBinary(template_path, output_filename)
    finally:
      # Remove the custom settings for the next deploy
      for newcontext in deploycontext.split(","):
        context.remove(newcontext)

  logging.info("Complete, installers for %s are in %s", deployed_list,
               output_dir)


def Deploy(context, signer=None):
  """Reconfigure a client template to match config.

  Args:
    context: config_lib context
    signer: lib.builders.signing.CodeSigner object
  """
  if args.plugins:
    config_lib.CONFIG.Set("Client.plugins", args.plugins)

  deployer = GetDeployer(context, signer=signer)
  template_path = (args.template or TemplateInputFilename(deployer.context) or
                   config_lib.CONFIG.Get("ClientBuilder.template_path",
                                         context=deployer.context))

  # If neither output filename or output directory is specified,
  # use the default location from the config file.
  output = None
  if args.output:
    output = args.output
  elif args.outputdir:
    # If output filename isn't specified, write to args.outputdir with a
    # .deployed extension so we can distinguish it from repacked binaries.
    filename = ".".join(
        (config_lib.CONFIG.Get("ClientBuilder.output_filename",
                               context=deployer.context), "deployed"))
    output = os.path.join(args.outputdir, filename)

  deployer.MakeDeployableBinary(template_path, output)


def Repack(context, signer=None):
  """Turn a template into an installer.

  Args:
    context: config_lib context
    signer: lib.builders.signing.CodeSigner object
  """
  if args.plugins:
    config_lib.CONFIG.Set("Client.plugins", args.plugins)

  deployer = GetDeployer(context, signer=signer)
  output_filename = os.path.join(
      args.outputdir, config_lib.CONFIG.Get(
          "ClientBuilder.output_filename", context=deployer.context))

  deployer.RepackInstaller(open(args.template, "rb").read(), args.output or
                           output_filename)


def SetOSContextFromArgs(context):
  """Set OS context sections based on args."""
  context.append("ClientBuilder Context")
  if args.platform == "darwin":
    context = ["Platform:Darwin", "Target:Darwin"] + context
  elif args.platform == "windows":
    context = ["Platform:Windows", "Target:Windows"] + context
  elif args.platform == "linux":
    context = ["Platform:Linux", "Target:Linux"] + context
    if args.package_format == "deb":
      context = ["Target:LinuxDeb"] + context
    elif args.package_format == "rpm":
      context = ["Target:LinuxRpm"] + context
    else:
      parser.error("Couldn't guess packaging format for: %s" %
                   platform.linux_distribution()[0])
  else:
    parser.error("Unsupported build platform: %s" % args.platform)
  return context


def SetArchContextFromArgs(context):
  if args.arch == "amd64":
    context.append("Arch:amd64")
  else:
    context.append("Arch:i386")
  return context


def SetDebugContextFromArgs(context):
  if args.subparser_name != "build" and args.debug_build:
    context += ["DebugClientBuild Context"]
  return context


def SetContextFromArgs(context):
  context = SetArchContextFromArgs(context)
  context = SetDebugContextFromArgs(context)
  return SetOSContextFromArgs(context)


def main(_):
  """Launch the appropriate builder."""
  config_lib.CONFIG.AddContext(
      "ClientBuilder Context",
      "Context applied when we run the client builder script.")

  startup.ClientInit()

  # Make sure we have all the secondary configs since they may be set under the
  # ClientBuilder Context
  for secondconfig in config_lib.CONFIG["ConfigIncludes"]:
    config_lib.CONFIG.LoadSecondaryConfig(secondconfig)

  # Use basic console output logging so we can see what is happening.
  logger = logging.getLogger()
  handler = logging.StreamHandler()
  handler.setLevel(logging.INFO)
  logger.handlers = [handler]

  context = flags.FLAGS.context
  context = SetContextFromArgs(context)
  signer = None
  if args.sign:
    signer = GetSigner(context)

  if args.subparser_name == "build":
    builder_obj = GetBuilder(context)
    builder_obj.MakeExecutableTemplate()
  elif args.subparser_name == "repack":
    Repack(context, signer=signer)
  elif args.subparser_name == "deploy":
    Deploy(context, signer=signer)
  elif args.subparser_name == "buildanddeploy":
    if args.platform == "windows":
      # Handle windows differently because we do 32, 64, and debug builds all at
      # once.
      BuildAndDeployWindows(signer=signer)
    else:
      BuildAndDeploy(context, signer=signer)


if __name__ == "__main__":
  flags.StartMain(main)
