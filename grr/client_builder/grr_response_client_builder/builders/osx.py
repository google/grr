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

from grr_response_client_builder import build
from grr_response_client_builder import build_helpers
from grr_response_core import config
from grr_response_core.lib import package
from grr_response_core.lib import utils


class DarwinClientBuilder(build.ClientBuilder):
  """Builder class for the Mac OS X (Darwin) client."""

  BUILDER_CONTEXT = "Target:Darwin"

  def _SetBuildVars(self):
    self.build_dir = config.CONFIG.Get(
        "PyInstaller.build_dir", context=self.context)
    self.fleetspeak_enabled = config.CONFIG.Get(
        "Client.fleetspeak_enabled", context=self.context)
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
      self.target_binary_dir = os.path.join(
          self.pkg_root,
          config.CONFIG.Get("ClientBuilder.install_dir",
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

  def _MakeBuildDirectory(self):
    build_helpers.MakeBuildDirectory(context=self.context)

    build_helpers.CleanDirectory(self.pkg_root)
    build_helpers.CleanDirectory(self.pkgbuild_out_dir)
    build_helpers.CleanDirectory(self.prodbuild_out_dir)
    self.script_dir = os.path.join(self.build_dir, "scripts")
    build_helpers.CleanDirectory(self.script_dir)

  def _MakeZip(self, output_path):
    """Add a zip to the end of the .xar containing build.yaml.

    The build.yaml is already inside the .xar file, but we can't easily open
    this on linux. To make repacking easier we add a zip to the end of the .xar
    and add in the build.yaml. The repack step will then look at the build.yaml
    and insert the config.yaml. We end up storing the build.yaml twice but it is
    tiny, so this doesn't matter.

    Args:
      output_path: the path to the XAR file to be modified.
    """
    logging.info("Generating zip template file at %s", output_path)
    with zipfile.ZipFile(output_path, mode="a") as zf:
      # Get the build yaml
      # TODO(hanuszczak): YAML, consider using `StringIO` instead.
      build_yaml = io.BytesIO()
      build_helpers.WriteBuildYaml(build_yaml, context=self.context)
      build_yaml.seek(0)
      zf.writestr("build.yaml", build_yaml.read())

  def _InterpolateFiles(self):
    if self.fleetspeak_enabled:
      fleetspeak_template = config.CONFIG.Get(
          "ClientBuilder.fleetspeak_config_path", context=self.context)
      dest_fleetspeak_config = os.path.join(
          self.pkg_fleetspeak_service_dir,
          config.CONFIG.Get(
              "Client.fleetspeak_unsigned_config_fname", context=self.context))
      build_helpers.GenerateFile(
          input_filename=fleetspeak_template,
          output_filename=dest_fleetspeak_config,
          context=self.context)
      build_files_dir = package.ResourcePath(
          "grr-response-core", "install_data/macosx/client/fleetspeak")
    else:
      build_files_dir = package.ResourcePath("grr-response-core",
                                             "install_data/macosx/client")
      build_helpers.GenerateFile(
          input_filename=os.path.join(build_files_dir, "grr.plist.in"),
          output_filename=os.path.join(self.pkg_root, "Library/LaunchDaemons",
                                       self.plist_name),
          context=self.context)

    # We pass in scripts separately with --scripts so they don't go in pkg_root
    build_helpers.GenerateFile(
        input_filename=os.path.join(build_files_dir, "preinstall.sh.in"),
        output_filename=os.path.join(self.script_dir, "preinstall"),
        context=self.context)

    build_helpers.GenerateFile(
        input_filename=os.path.join(build_files_dir, "postinstall.sh.in"),
        output_filename=os.path.join(self.script_dir, "postinstall"),
        context=self.context)
    build_helpers.GenerateFile(
        input_filename=os.path.join(build_files_dir, "Distribution.xml.in"),
        output_filename=os.path.join(self.build_dir, "Distribution.xml"),
        context=self.context)

  def _RenameGRRPyinstallerBinaries(self):
    if self.template_binary_dir != self.target_binary_dir:
      shutil.move(self.template_binary_dir, self.target_binary_dir)
    shutil.move(
        os.path.join(self.target_binary_dir, "grr-client"),
        os.path.join(
            self.target_binary_dir,
            config.CONFIG.Get("Client.binary_name", context=self.context)))

  def _SignGRRPyinstallerBinaries(self):
    cert_name = config.CONFIG.Get(
        "ClientBuilder.signing_cert_name", context=self.context)
    keychain_file = config.CONFIG.Get(
        "ClientBuilder.signing_keychain_file", context=self.context)
    if not cert_name:
      print("No certificate name specified in the config, skipping "
            "binaries signing...")
      return

    print("Signing binaries with keychain: %s" % keychain_file)

    with utils.TempDirectory() as temp_dir:
      # codesign needs the directory name to adhere to a particular
      # naming format.
      bundle_dir = os.path.join(temp_dir,
                                "%s_%s" % (self.client_name, self.version))
      shutil.move(self.target_binary_dir, bundle_dir)
      temp_binary_path = os.path.join(
          bundle_dir,
          config.CONFIG.Get("Client.binary_name", context=self.context))
      subprocess.check_call([
          "codesign", "--verbose", "--deep", "--force", "--sign", cert_name,
          "--keychain", keychain_file, temp_binary_path
      ])
      shutil.move(bundle_dir, self.target_binary_dir)

  def _CreateInstallDirs(self):
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

  def _WriteClientConfig(self):
    # Generate a config file.
    with io.open(
        os.path.join(
            self.target_binary_dir,
            config.CONFIG.Get(
                "ClientBuilder.config_filename", context=self.context)),
        "w") as fd:
      fd.write(
          build_helpers.GetClientConfig(
              ["Client Context"] + self.context, validate=False))

  def _RunCmd(self, command):
    print("Running: %s" % " ".join(command))
    subprocess.check_call(command)

  def _Set755Permissions(self):
    command = ["/bin/chmod", "-R", "755", self.script_dir]
    self._RunCmd(command)
    command = ["/bin/chmod", "-R", "755", self.pkg_root]
    self._RunCmd(command)

  def _RunPkgBuild(self):
    pkg_id = "%s.%s" % (self.pkg_org, self.client_name)
    command = [
        "pkgbuild",
        "--root=%s" % self.pkg_root, "--identifier", pkg_id, "--scripts",
        self.script_dir, "--version", self.version, self.pkgbuild_out_binary
    ]
    self._RunCmd(command)

  def _RunProductBuild(self):
    command = [
        "productbuild", "--distribution",
        os.path.join(self.build_dir, "distribution.xml"), "--package-path",
        self.pkgbuild_out_dir, self.prodbuild_out_binary
    ]
    self._RunCmd(command)

  def _RenamePkgToTemplate(self, output_path):
    print("Copying output to templates location: %s -> %s" %
          (self.prodbuild_out_binary, output_path))
    utils.EnsureDirExists(os.path.dirname(output_path))
    shutil.copyfile(self.prodbuild_out_binary, output_path)

  def _BuildInstallerPkg(self, output_path):
    """Builds a package (.pkg) using PackageMaker."""
    self._CreateInstallDirs()
    self._InterpolateFiles()
    self._RenameGRRPyinstallerBinaries()
    self._SignGRRPyinstallerBinaries()
    self._WriteClientConfig()
    self._Set755Permissions()
    self._RunPkgBuild()
    self._RunProductBuild()
    self._RenamePkgToTemplate(output_path)

  def MakeExecutableTemplate(self, output_path):
    """Create the executable template."""
    self._SetBuildVars()
    self._MakeBuildDirectory()
    build_helpers.BuildWithPyInstaller(context=self.context)
    self._BuildInstallerPkg(output_path)
    self._MakeZip(output_path)
