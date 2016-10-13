#!/usr/bin/env python
"""This tool builds or repacks the client binaries."""

import getpass
import logging
import multiprocessing
import os
import platform
import subprocess
import sys


# pylint: disable=unused-import
from grr.client import client_plugins
# pylint: enable=unused-import

from grr.lib import builders
from grr.lib import config_lib
from grr.lib import flags
from grr.lib import repacking
from grr.lib import startup


class Error(Exception):
  pass


class ErrorDuringRepacking(Error):
  pass

try:
  # pylint: disable=g-import-not-at-top
  from grr.lib.builders import component
except ImportError:
  component = None

parser = flags.PARSER

# Initialize sub parsers and their arguments.
subparsers = parser.add_subparsers(
    title="subcommands", dest="subparser_name", description="valid subcommands")

# build arguments.
parser_build = subparsers.add_parser(
    "build", help="Build a client from source.")

parser_build.add_argument(
    "--output", default=None, help="The path to write the output template.")

# repack arguments
parser_repack = subparsers.add_parser(
    "repack", help="Build installer from a template.")

parser_repack.add_argument(
    "--debug_build",
    action="store_true",
    default=False,
    help="Build a debug installer.")

parser_repack.add_argument(
    "--sign",
    action="store_true",
    default=False,
    help="Sign installer binaries.")

parser_repack.add_argument(
    "--signed_template",
    action="store_true",
    default=False,
    help="Set to true if template was signed with sign_template. This is only "
    "necessary when repacking a windows template many times.")

parser_repack.add_argument(
    "--template",
    default=None,
    required=True,
    help="The template zip file to repack.")

parser_repack.add_argument(
    "--output_dir",
    default="",
    required=True,
    help="The directory to which we should write the "
    "output installer. Installers will be named "
    "automatically from config options.")

# repack_multiple arguments
parser_multi = subparsers.add_parser(
    "repack_multiple", help="Repack multiple templates with multiple configs.")

parser_multi.add_argument(
    "--sign",
    action="store_true",
    default=False,
    help="Sign installer binaries.")

parser_multi.add_argument(
    "--signed_template",
    action="store_true",
    default=False,
    help="Set to true if template was signed with sign_template. This is only "
    "necessary when repacking a windows template many times.")

parser_multi.add_argument(
    "--templates",
    default=None,
    required=True,
    nargs="+",
    help="The list of templates to repack. Use "
    "'--template /some/dir/*.zip' to repack "
    "all templates in a directory.")

parser_multi.add_argument(
    "--repack_configs",
    default=None,
    required=True,
    nargs="+",
    help="The list of repacking configs to apply. Use "
    "'--repack_configs /some/dir/*.yaml' to repack "
    "with all configs in a directory")

parser_multi.add_argument(
    "--output_dir",
    default=None,
    required=True,
    help="The directory where we output our installers.")

parser_signer = subparsers.add_parser(
    "sign_template",
    help="Sign client libraries in a client template."
    "Use this when you are repacking a windows template many times and "
    "need all binaries inside signed.")

parser_signer.add_argument(
    "--template", default=None, required=True, help="Template to sign.")

parser_signer.add_argument(
    "--output_file",
    default=None,
    required=True,
    help="Where to write the new template with signed libs.")

if component:
  parser_build_component = subparsers.add_parser(
      "build_component", help="Build a client component.")

  parser_build_component.add_argument(
      "setup_file", help="Path to the setup.py file for the component.")

  parser_build_component.add_argument(
      "output", help="Path to store the compiled component.")

  parser_build_components = subparsers.add_parser(
      "build_components", help="Builds all client components.")

  parser_build_components.add_argument(
      "--output", default="", help="Path to store the compiled component.")

args = parser.parse_args()


class TemplateBuilder(object):
  """Build client templates."""

  def GetBuilder(self, context):
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
                         "on current platform." % self.platform)

    return builder_class(context=context)

  def GetArch(self):
    if platform.architecture()[0] == "32bit":
      return "i386"
    return "amd64"

  def GetPackageFormat(self):
    if platform.system() == "Linux":
      distro = platform.linux_distribution()[0]
      if distro in ["Ubuntu", "debian"]:
        return "Target:LinuxDeb"
      elif distro in ["CentOS Linux", "CentOS", "centos", "redhat", "fedora"]:
        return "Target:LinuxRpm"
      else:
        raise RuntimeError("Unknown distro, can't determine package format")

  def BuildTemplate(self, context=None, output=None):
    """Find template builder and call it."""
    context = context or []
    context.append("Arch:%s" % self.GetArch())
    # Platform context has common platform settings, Target has template build
    # specific stuff.
    self.platform = platform.system()
    context.extend(["Platform:%s" % self.platform, "Target:%s" % self.platform])
    if "Target:Linux" in context:
      context.append(self.GetPackageFormat())

    template_path = None
    if output:
      template_path = os.path.join(
          output,
          config_lib.CONFIG.Get("PyInstaller.template_filename",
                                context=context))

    builder_obj = self.GetBuilder(context)
    builder_obj.MakeExecutableTemplate(output_file=template_path)


def SpawnProcess(popen_args, signing=None, passwd=None):
  if signing:
    # We send the password via pipe to avoid creating a process with the
    # password as an argument that will get logged on some systems.
    p = subprocess.Popen(popen_args, stdin=subprocess.PIPE)
    p.communicate(input=passwd)
  else:
    p = subprocess.Popen(popen_args)
    p.wait()
  if p.returncode != 0:
    raise ErrorDuringRepacking(" ".join(popen_args))


class MultiTemplateRepacker(object):
  """Helper class for repacking multiple templates and configs.

  This class calls client_build in a separate process for each repacking job.
  This greatly speeds up repacking lots of templates and also avoids the need to
  manage adding and removing different build contexts for each repack.

  This is only really useful if you have lots of repacking config
  customizations, such as many differently labelled clients.
  """

  def GetOutputDir(self, base_dir, config_filename):
    """Add the repack config filename onto the base output directory.

    This allows us to repack lots of different configs to the same installer
    name and still be able to distinguish them.

    Args:
      base_dir: output directory string
      config_filename: the secondary config filename string

    Returns:
      String to be used as output directory for this repack.
    """
    return os.path.join(base_dir,
                        os.path.basename(config_filename.replace(".yaml", "")))

  def RepackTemplates(self,
                      repack_configs,
                      templates,
                      output_dir,
                      config=None,
                      sign=False,
                      signed_template=False):
    """Call repacker in a subprocess."""
    if sign:
      # Doing this here avoids multiple prompting when doing lots of repacking.
      print "Enter passphrase for Windows code signing"
      windows_passwd = getpass.getpass()

      print "Enter passphrase for RPM code signing"
      rpm_passwd = getpass.getpass()
    pool = multiprocessing.Pool(processes=10)
    results = []
    for repack_config in repack_configs:
      for template in templates:
        repack_args = ["grr_client_build"]
        if config:
          repack_args.extend(["--config", config])

        repack_args.extend([
            "--secondary_configs", repack_config, "repack", "--template",
            template, "--output_dir",
            self.GetOutputDir(output_dir, repack_config)
        ])

        # We only sign exes and rpms at the moment. The others will raise if we
        # try to ask for signing.
        signing = False
        passwd = None
        if sign:
          if template.endswith(".exe.zip"):
            passwd = windows_passwd
            signing = True
            repack_args.append("--sign")
            if signed_template:
              repack_args.append("--signed_template")
          elif template.endswith(".rpm.zip"):
            passwd = rpm_passwd
            signing = True
            repack_args.append("--sign")

        print "Calling %s" % " ".join(repack_args)
        results.append(
            pool.apply_async(
                SpawnProcess, (repack_args,),
                dict(
                    signing=signing, passwd=passwd)))

        # Also build debug if it's windows.
        if template.endswith(".exe.zip"):
          debug_args = []
          debug_args.extend(repack_args)
          debug_args.append("--debug_build")
          print "Calling %s" % " ".join(debug_args)
          results.append(
              pool.apply_async(
                  SpawnProcess, (debug_args,),
                  dict(
                      signing=signing, passwd=passwd)))

    try:
      pool.close()
      # Workaround to handle keyboard kills
      # http://stackoverflow.com/questions/1408356/keyboard-interrupts-with-pythons-multiprocessing-pool
      # get will raise if the child raises.
      for result_obj in results:
        result_obj.get(9999)
      pool.join()
    except KeyboardInterrupt:
      print "parent received control-c"
      pool.terminate()
    except ErrorDuringRepacking:
      pool.terminate()
      raise


def main(_):
  """Launch the appropriate builder."""
  # We deliberately use flags.FLAGS.context because startup.py pollutes
  # config_lib.CONFIG.context with the running system context.
  context = flags.FLAGS.context
  context.append("ClientBuilder Context")
  startup.ClientInit()

  # Use basic console output logging so we can see what is happening.
  logger = logging.getLogger()
  handler = logging.StreamHandler()
  handler.setLevel(logging.INFO)
  logger.handlers = [handler]

  if args.subparser_name == "build":
    TemplateBuilder().BuildTemplate(context=context, output=flags.FLAGS.output)
  elif args.subparser_name == "repack":
    if args.debug_build:
      context.append("DebugClientBuild Context")
    result_path = repacking.TemplateRepacker().RepackTemplate(
        args.template,
        args.output_dir,
        context=context,
        sign=args.sign,
        signed_template=args.signed_template)

    if not result_path:
      raise ErrorDuringRepacking(" ".join(sys.argv[:]))
  elif args.subparser_name == "repack_multiple":
    MultiTemplateRepacker().RepackTemplates(
        args.repack_configs,
        args.templates,
        args.output_dir,
        config=args.config,
        sign=args.sign,
        signed_template=args.signed_template)
  elif args.subparser_name == "build_components":
    component.BuildComponents(output_dir=flags.FLAGS.output)
  elif args.subparser_name == "build_component":
    component.BuildComponent(
        flags.FLAGS.setup_file, output_dir=flags.FLAGS.output)
  elif args.subparser_name == "sign_template":
    repacking.TemplateRepacker().SignTemplate(
        args.template, args.output_file, context=context)
    if not os.path.exists(args.output_file):
      raise RuntimeError("Signing failed: output not written")


if __name__ == "__main__":
  flags.StartMain(main)
