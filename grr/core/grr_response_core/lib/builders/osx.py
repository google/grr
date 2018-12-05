#!/usr/bin/env python
"""An implementation of an OSX client builder."""
from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

import io
import logging
import os
import shutil
import subprocess
import zipfile

from grr_response_core import config
from grr_response_core.lib import build
from grr_response_core.lib import flags
from grr_response_core.lib import package
from grr_response_core.lib import utils


class DarwinClientBuilder(build.ClientBuilder):
  """Builder class for the Mac OS X (Darwin) client."""

  def __init__(self, context=None):
    """Initialize the Mac OS X client builder."""
    super(DarwinClientBuilder, self).__init__(context=context)
    self.context.append("Target:Darwin")

  def MakeExecutableTemplate(self, output_file=None):
    """Create the executable template."""
    super(DarwinClientBuilder, self).MakeExecutableTemplate(
        output_file=output_file)
    self.SetBuildVars()
    self.MakeBuildDirectory()
    self.BuildWithPyInstaller()
    self.CopyMissingModules()
    self.BuildInstallerPkg(output_file)
    self.MakeZip(output_file, self.template_file)

  def SetBuildVars(self):
    self.fleetspeak_enabled = config.CONFIG.Get(
        "ClientBuilder.fleetspeak_enabled", context=self.context)
    self.version = config.CONFIG.Get(
        "Source.version_string", context=self.context)
    self.client_name = config.CONFIG.Get("Client.name", context=self.context)
    self.pkg_org = config.CONFIG.Get(
        "ClientBuilder.package_maker_organization", context=self.context)
    self.pkg_name = "%s-%s.pkg" % (self.client_name, self.version)
    self.build_root = config.CONFIG.Get(
        "ClientBuilder.build_root_dir", context=self.context)
    self.plist_name = config.CONFIG.Get(
        "Client.plist_filename", context=self.context)
    self.output_basename = config.CONFIG.Get(
        "ClientBuilder.output_basename", context=self.context)
    self.template_binary_dir = os.path.join(
        config.CONFIG.Get("PyInstaller.distpath", context=self.context),
        "grr-client")
    self.fleetspeak_service_dir = config.CONFIG.Get(
        "ClientBuilder.fleetspeak_service_dir", context=self.context)
    self.pkg_root = os.path.join(self.build_root, "pkg-root")
    if self.fleetspeak_enabled:
      self.target_binary_dir = os.path.join(self.pkg_root,
                                            config.CONFIG.Get(
                                                "ClientBuilder.install_dir",
                                                context=self.context)[1:])
    else:
      self.target_binary_dir = os.path.join(self.pkg_root, "usr/local/lib/",
                                            self.client_name,
                                            self.output_basename)
    self.pkg_fleetspeak_service_dir = os.path.join(
        self.pkg_root, self.fleetspeak_service_dir[1:])
    self.pkgbuild_out_dir = os.path.join(self.build_root, "pkgbuild-out")
    self.pkgbuild_out_binary = os.path.join(self.pkgbuild_out_dir,
                                            self.pkg_name)
    self.prodbuild_out_dir = os.path.join(self.build_root, "prodbuild-out")
    self.prodbuild_out_binary = os.path.join(self.prodbuild_out_dir,
                                             self.pkg_name)

  def MakeZip(self, xar_file, output_file):
    """Add a zip to the end of the .xar containing build.yaml.

    The build.yaml is already inside the .xar file, but we can't easily open
    this on linux. To make repacking easier we add a zip to the end of the .xar
    and add in the build.yaml. The repack step will then look at the build.yaml
    and insert the config.yaml. We end up storing the build.yaml twice but it is
    tiny, so this doesn't matter.

    Args:
      xar_file: the name of the xar file.
      output_file: the name of the output ZIP archive.
    """
    logging.info("Generating zip template file at %s", output_file)
    with zipfile.ZipFile(output_file, mode="a") as zf:
      # Get the build yaml
      # TODO(hanuszczak): YAML, consider using `StringIO` instead.
      build_yaml = io.BytesIO()
      self.WriteBuildYaml(build_yaml)
      build_yaml.seek(0)
      zf.writestr("build.yaml", build_yaml.read())

  def MakeBuildDirectory(self):
    super(DarwinClientBuilder, self).MakeBuildDirectory()
    self.CleanDirectory(self.pkg_root)
    self.CleanDirectory(self.pkgbuild_out_dir)
    self.CleanDirectory(self.prodbuild_out_dir)
    self.script_dir = os.path.join(self.build_dir, "scripts")
    self.CleanDirectory(self.script_dir)

  def InterpolateFiles(self):
    if self.fleetspeak_enabled:
      shutil.copy(flags.FLAGS.fleetspeak_service_config,
                  self.pkg_fleetspeak_service_dir)
      build_files_dir = package.ResourcePath(
          "grr-response-core", "install_data/macosx/client/fleetspeak")
    else:
      build_files_dir = package.ResourcePath("grr-response-core",
                                             "install_data/macosx/client")
      self.GenerateFile(
          input_filename=os.path.join(build_files_dir, "grr.plist.in"),
          output_filename=os.path.join(self.pkg_root, "Library/LaunchDaemons",
                                       self.plist_name))
    # We pass in scripts separately with --scripts so they don't go in pkg_root
    self.GenerateFile(
        input_filename=os.path.join(build_files_dir, "preinstall.sh.in"),
        output_filename=os.path.join(self.script_dir, "preinstall"))

    self.GenerateFile(
        input_filename=os.path.join(build_files_dir, "postinstall.sh.in"),
        output_filename=os.path.join(self.script_dir, "postinstall"))
    self.GenerateFile(
        input_filename=os.path.join(build_files_dir, "Distribution.xml.in"),
        output_filename=os.path.join(self.build_dir, "Distribution.xml"))

  def RenameGRRPyinstallerBinaries(self):
    if self.template_binary_dir != self.target_binary_dir:
      shutil.move(self.template_binary_dir, self.target_binary_dir)
    shutil.move(
        os.path.join(self.target_binary_dir, "grr-client"),
        os.path.join(self.target_binary_dir,
                     config.CONFIG.Get(
                         "Client.binary_name", context=self.context)))

  def SignGRRPyinstallerBinaries(self):
    cert_name = config.CONFIG.Get(
        "ClientBuilder.signing_cert_name", context=self.context)
    keychain_file = config.CONFIG.Get(
        "ClientBuilder.signing_keychain_file", context=self.context)
    if not keychain_file:
      print("No keychain file specified in the config, skipping "
            "binaries signing...")
      return

    print("Signing binaries with keychain: %s" % keychain_file)

    with utils.TempDirectory() as temp_dir:
      # codesign needs the directory name to adhere to a particular
      # naming format.
      bundle_dir = os.path.join(temp_dir, "%s_%s" % (self.client_name,
                                                     self.version))
      shutil.move(self.target_binary_dir, bundle_dir)
      temp_binary_path = os.path.join(bundle_dir,
                                      config.CONFIG.Get(
                                          "Client.binary_name",
                                          context=self.context))
      subprocess.check_call([
          "codesign", "--verbose", "--deep", "--force", "--sign", cert_name,
          "--keychain", keychain_file, temp_binary_path
      ])
      shutil.move(bundle_dir, self.target_binary_dir)

  def CreateInstallDirs(self):
    utils.EnsureDirExists(self.build_dir)
    utils.EnsureDirExists(self.script_dir)
    utils.EnsureDirExists(self.pkg_root)
    if self.fleetspeak_enabled:
      utils.EnsureDirExists(self.pkg_fleetspeak_service_dir)
    else:
      utils.EnsureDirExists(
          os.path.join(self.pkg_root, "Library/LaunchDaemons"))
    utils.EnsureDirExists(os.path.join(self.pkg_root, "usr/local/lib/"))
    utils.EnsureDirExists(self.pkgbuild_out_dir)
    utils.EnsureDirExists(self.prodbuild_out_dir)

  def WriteClientConfig(self):
    repacker = build.ClientRepacker(context=self.context)
    repacker.context = self.context

    # Generate a config file.
    with open(
        os.path.join(self.target_binary_dir,
                     config.CONFIG.Get(
                         "ClientBuilder.config_filename",
                         context=self.context)), "wb") as fd:
      fd.write(
          repacker.GetClientConfig(
              ["Client Context"] + self.context, validate=False))

  def RunCmd(self, command):
    print("Running: %s" % " ".join(command))
    subprocess.check_call(command)

  def Set755Permissions(self):
    command = ["/bin/chmod", "-R", "755", self.script_dir]
    self.RunCmd(command)
    command = ["/bin/chmod", "-R", "755", self.pkg_root]
    self.RunCmd(command)

  def RunPkgBuild(self):
    pkg_id = "%s.%s.%s_%s" % (self.pkg_org, self.client_name, self.client_name,
                              self.version)
    command = [
        "pkgbuild",
        "--root=%s" % self.pkg_root, "--identifier", pkg_id, "--scripts",
        self.script_dir, "--version", self.version, self.pkgbuild_out_binary
    ]
    self.RunCmd(command)

  def RunProductBuild(self):
    command = [
        "productbuild", "--distribution",
        os.path.join(self.build_dir, "distribution.xml"), "--package-path",
        self.pkgbuild_out_dir, self.prodbuild_out_binary
    ]
    self.RunCmd(command)

  def RenamePkgToTemplate(self, output_file):
    print("Copying output to templates location: %s -> %s" %
          (self.prodbuild_out_binary, output_file))
    utils.EnsureDirExists(os.path.dirname(output_file))
    shutil.copyfile(self.prodbuild_out_binary, output_file)

  def BuildInstallerPkg(self, output_file):
    """Builds a package (.pkg) using PackageMaker."""
    self.CreateInstallDirs()
    self.InterpolateFiles()
    self.RenameGRRPyinstallerBinaries()
    self.SignGRRPyinstallerBinaries()
    self.WriteClientConfig()
    self.Set755Permissions()
    self.RunPkgBuild()
    self.RunProductBuild()
    self.RenamePkgToTemplate(output_file)
