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

from grr.lib import builders
from grr.lib import config_lib
from grr.lib import flags
from grr.lib import repacking
from grr.lib import startup
from grr.lib.builders import signing

try:
  # pylint: disable=g-import-not-at-top
  from grr.lib.builders import component
except ImportError:
  component = None

parser = flags.PARSER

# Guess which arch we should be building based on where we are running.
if platform.architecture()[0] == "32bit":
  default_arch = "i386"
else:
  default_arch = "amd64"

default_platform = platform.system().lower()
parser.add_argument(
    "--platform",
    choices=["darwin", "linux", "windows"],
    default=default_platform,
    help="The platform to build or repack for. This will default to "
    "the current platform: %s." % platform.system())

parser.add_argument("--arch",
                    choices=["amd64", "i386"],
                    default=default_arch,
                    help="The architecture to build or repack for.")

parser.add_argument("--sign",
                    action="store_true",
                    default=False,
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
    "--package_format",
    choices=["deb", "rpm", "dmg"],
    default=default_package,
    help="The packaging format to use when building a Linux client.")

# Initialize sub parsers and their arguments.
subparsers = parser.add_subparsers(title="subcommands",
                                   dest="subparser_name",
                                   description="valid subcommands")

# Build arguments.
parser_build = subparsers.add_parser("build",
                                     help="Build a client from source.")

parser_build.add_argument("--output",
                          default=None,
                          help="The path to write the output template.")

parser_repack = subparsers.add_parser(
    "repack", help="Build a deployable self installer from a package.")

parser_repack.add_argument("--template",
                           default=None,
                           required=True,
                           help="The template zip file to repack.")

parser_repack.add_argument("--outputdir",
                           default="",
                           required=True,
                           help="The directory to which we should write the "
                           "output installer. Installers will be named "
                           "automatically from config options. Incompatible"
                           " with --output")

parser_buildandrepack = subparsers.add_parser(
    "buildandrepack",
    help="Build and repack clients for multiple labels and architectures.")

parser_buildandrepack.add_argument("--templatedir",
                                   default="",
                                   help="Directory"
                                   "containing template zip files to repack.")

parser_buildandrepack.add_argument("--debug_build",
                                   action="store_true",
                                   default=False,
                                   help="Create a debug client.")

if component:
  parser_build_component = subparsers.add_parser(
      "build_component", help="Build a client component.")

  parser_build_component.add_argument(
      "setup_file",
      help="Path to the setup.py file for the component.")

  parser_build_component.add_argument(
      "output", help="Path to store the compiled component.")

  parser_build_components = subparsers.add_parser(
      "build_components",
      help="Builds all client components.")

  parser_build_components.add_argument(
      "--output",
      default="",
      help="Path to store the compiled component.")

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


def GetSigner(context):
  if args.subparser_name in ["repack", "buildandrepack"]:
    if args.platform == "windows":
      print "Enter passphrase for code signing cert:"
      passwd = getpass.getpass()
      cert = config_lib.CONFIG.Get("ClientBuilder.windows_signing_cert",
                                   context=context)
      key = config_lib.CONFIG.Get("ClientBuilder.windows_signing_key",
                                  context=context)
      app_name = config_lib.CONFIG.Get(
          "ClientBuilder.windows_signing_application_name",
          context=context)
      return signing.WindowsCodeSigner(cert, key, passwd, app_name)
    elif args.platform == "linux" and args.package_format == "rpm":
      pub_keyfile = config_lib.CONFIG.Get(
          "ClientBuilder.rpm_signing_key_public_keyfile",
          context=context)
      gpg_name = config_lib.CONFIG.Get("ClientBuilder.rpm_gpg_name",
                                       context=context)

      print "Enter passphrase for code signing key %s:" % (gpg_name)
      passwd = getpass.getpass()
      return signing.RPMCodeSigner(passwd, pub_keyfile, gpg_name)
    else:
      parser.error("Signing only supported on windows and linux rpms for "
                   "repack, buildandrepack")


def TemplateInputFilename(context):
  """Build template file name from config."""
  if args.templatedir:
    filename = config_lib.CONFIG.Get("PyInstaller.template_filename",
                                     context=context)
    return os.path.join(args.templatedir, filename)
  return None


def BuildAndRepackWindows(signer=None):
  """Run buildandrepack for 32/64 dbg/prod."""
  build_combos = [
      {"arch": "amd64",
       "debug_build": True}, {"arch": "amd64",
                              "debug_build": False}, {"arch": "i386",
                                                      "debug_build": True},
      {"arch": "i386",
       "debug_build": False}
  ]
  timestamp = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
  args.package_format = "exe"

  # TODO(user): Build components here.
  # component.BuildComponents(output_dir=output_dir)

  context_orig = SetOSContextFromArgs([])
  # Take a copy of the context list so we can reset back to clean state for each
  # buildandrepack run
  context = list(context_orig)
  for argset in build_combos:
    for key, value in argset.items():
      setattr(args, key, value)
    context = SetArchContextFromArgs(context)
    context = SetDebugContextFromArgs(context)
    print "Building for: %s" % context
    BuildAndRepack(context, timestamp=timestamp, signer=signer)
    context = list(context_orig)


def BuildAndRepack(context, signer=None, timestamp=None):
  """Run build and repack to create installers."""
  # ISO 8601 date
  timestamp = timestamp or time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())

  # Output directory like: 2015-02-13T21:48:47-0800/linux_amd64_deb/
  spec = "_".join((args.platform, args.arch, args.package_format))
  output_dir = os.path.join(
      config_lib.CONFIG.Get("ClientBuilder.executables_dir",
                            context=context),
      timestamp,
      spec)

  # If we weren't passed a template, build one
  if args.templatedir:
    template_path = TemplateInputFilename(context)
  else:
    component.BuildComponents(output_dir=output_dir)
    template_path = os.path.join(output_dir,
                                 config_lib.CONFIG.Get(
                                     "PyInstaller.template_filename",
                                     context=context))
    builder_obj = GetBuilder(context)
    builder_obj.MakeExecutableTemplate(output_file=template_path)

  # Get the list of contexts which we should be building.
  context_list = config_lib.CONFIG.Get("ClientBuilder.BuildTargets")

  logging.info("Building installers for: %s", context_list)
  repacked_list = []
  for repackcontext in context_list:

    # Add the settings for this context
    for newcontext in repackcontext.split(","):
      context.append(newcontext)

    try:
      # If the ClientBuilder.target_platforms doesn't match our environment,
      # skip.
      if not config_lib.CONFIG.MatchBuildContext(args.platform,
                                                 args.arch,
                                                 args.package_format,
                                                 context=context):
        continue

      # Make a nicer filename out of the context string.
      context_filename = repackcontext.replace(
          "AllPlatforms Context,", "").replace(",", "_").replace(" ", "_")
      logging.info("Repacking %s as %s with labels: %s",
                   repackcontext,
                   config_lib.CONFIG.Get("Client.name",
                                         context=context),
                   config_lib.CONFIG.Get("Client.labels",
                                         context=context))

      repacking.TemplateRepacker().RepackTemplate(
          template_path,
          os.path.join(output_dir, context_filename),
          signer=signer,
          context=context)

      repacked_list.append(context_filename)
    finally:
      # Remove the custom settings for the next repack
      for newcontext in repackcontext.split(","):
        context.remove(newcontext)

  logging.info("Complete, installers for %s are in %s", repacked_list,
               output_dir)


def Repack(context, signer=None):
  """Reconfigure a client template to match config.

  Args:
    context: config_lib context
    signer: lib.builders.signing.CodeSigner object
  """
  repacking.TemplateRepacker().RepackTemplate(args.template,
                                              args.outputdir,
                                              context=context,
                                              signer=signer)


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
  if args.subparser_name != "build" and getattr(args, "debug_build", None):
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

  # Use basic console output logging so we can see what is happening.
  logger = logging.getLogger()
  handler = logging.StreamHandler()
  handler.setLevel(logging.INFO)
  logger.handlers = [handler]

  context = flags.FLAGS.context
  context = SetContextFromArgs(context)
  signer = None

  if args.sign:
    if not args.templatedir:
      raise RuntimeError("Signing must be performed on the host system since "
                         "that's where the keys are. If you want signed "
                         "binaries you need to build templates in the vagrant "
                         "vms then pass the templatedir here to do the repack "
                         "and sign operation on the host.")

    signer = GetSigner(context)

  if args.subparser_name == "build":
    template_path = None
    if flags.FLAGS.output:
      template_path = os.path.join(flags.FLAGS.output,
                                   config_lib.CONFIG.Get(
                                       "PyInstaller.template_filename",
                                       context=context))

    builder_obj = GetBuilder(context)
    builder_obj.MakeExecutableTemplate(output_file=template_path)
  elif args.subparser_name == "repack":
    # Don't set any context from this machine, it's all in the template.
    context = flags.FLAGS.context
    Repack(context, signer=signer)
  elif args.subparser_name == "buildandrepack":
    if args.platform == "windows":
      # Handle windows differently because we do 32, 64, and debug builds all at
      # once.
      BuildAndRepackWindows(signer=signer)
    else:
      BuildAndRepack(context, signer=signer)
  elif args.subparser_name == "build_components":
    component.BuildComponents(output_dir=flags.FLAGS.output)
  elif args.subparser_name == "build_component":
    component.BuildComponent(flags.FLAGS.setup_file,
                             output_dir=flags.FLAGS.output)


if __name__ == "__main__":
  flags.StartMain(main)
