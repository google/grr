#!/usr/bin/env python
"""An implementation of linux client builder."""

import fnmatch
import logging
import os
import shutil
import subprocess
import zipfile

from grr_response_client_builder import build
from grr_response_client_builder import build_helpers
from grr_response_core import config
from grr_response_core.lib import config_lib
from grr_response_core.lib import package
from grr_response_core.lib import utils


def _StripLibraries(directory):
  """Strips symbols from libraries bundled with the client."""

  # TODO(user): this is essentially "dh_strip --exclude=ffi" for deb
  # packages, if we can figure out the equivalent for redhat we could get rid
  # of this code.
  matches = []
  for root, _, filenames in os.walk(directory):
    for filename in fnmatch.filter(filenames, "*.so*"):
      # strip dies with errors on ffi libs, leave them alone.
      if "ffi" not in filename:
        matches.append(os.path.join(root, filename))
  cmd = ["strip"]
  cmd.extend(matches)
  subprocess.check_call(cmd)


def _CopyFleetspeakDpkgFiles(package_dir, context=None):
  """Copies Fleetspeak-enabled DPKG files to template directory."""
  if context is None:
    raise ValueError("context can't be None")

  # Copy files needed for dpkg-buildpackage.
  shutil.copytree(
      config_lib.Resource().Filter(
          "install_data/debian/dpkg_client/fleetspeak-debian"),
      os.path.join(package_dir, "debian/fleetspeak-debian.in"))

  # Include the Fleetspeak service config in the template.
  fleetspeak_dir = os.path.join(package_dir, "fleetspeak")
  utils.EnsureDirExists(fleetspeak_dir)
  shutil.copy(
      config.CONFIG.Get(
          "ClientBuilder.fleetspeak_config_path", context=context),
      fleetspeak_dir)


def _CopyBundledFleetspeakFiles(src_dir, package_dir):
  """Copies the bundled fleetspeak installation into the package dir."""
  files = [
      "etc/fleetspeak-client/communicator.txt",
      "lib/systemd/system/fleetspeak-client.service",
      "usr/bin/fleetspeak-client",
  ]
  for filename in files:
    src = os.path.join(src_dir, filename)
    dst = os.path.join(package_dir, "bundled-fleetspeak", filename)
    utils.EnsureDirExists(os.path.dirname(dst))
    shutil.copy(src, dst)


def _MakeZip(input_dir, output_file):
  """Creates a ZIP archive of the files in the input directory.

  Args:
    input_dir: the name of the input directory.
    output_file: the name of the output ZIP archive without extension.
  """

  logging.info("Generating zip template file at %s", output_file)
  zf = zipfile.ZipFile(output_file, "w")
  oldwd = os.getcwd()
  os.chdir(input_dir)
  for path in [
      "debian", "rpmbuild", "fleetspeak", "bundled-fleetspeak", "legacy"
  ]:
    for root, _, files in os.walk(path):
      for f in files:
        zf.write(os.path.join(root, f))
  zf.close()
  os.chdir(oldwd)

# Layout:
#
# - Common:
#   * debian/grr-client: PyInstaller generated files
# - Legacy:
#   * debian/legacy-debian.in: Debian directory
#   * debian/{upstart,systemd,initd}.in: Startup scripts
# - Fleetspeak enabled and bundled:
#   * debian/fleetspeak-debian.in: Debian directory
#   * fleetspeak: Fleetspeak config
# - Fleetspeak bundled only:
#   * bundled-fleetspak: Bundled fleetspeak client binaries


class DebianClientBuilder(build.ClientBuilder):
  """Builder class for the Debian-based client."""

  BUILDER_CONTEXT = "Target:Linux"

  @property
  def package_dir(self):
    return config.CONFIG.Get("PyInstaller.dpkg_root", context=self.context)

  @property
  def fleetspeak_install_dir(self):
    return config.CONFIG.Get(
        "ClientBuilder.fleetspeak_install_dir", context=self.context)

  def MakeExecutableTemplate(self, output_file):
    build_helpers.MakeBuildDirectory(context=self.context)
    build_helpers.CleanDirectory(self.package_dir)
    output_dir = build_helpers.BuildWithPyInstaller(context=self.context)

    _StripLibraries(output_dir)

    _CopyFleetspeakDpkgFiles(self.package_dir, context=self.context)
    _CopyBundledFleetspeakFiles(self.fleetspeak_install_dir, self.package_dir)

    _MakeZip(self.package_dir, output_file)


def _CopyCommonRpmFiles(package_dir, dist_dir):
  """Copies common (fleetspeak and legacy) files into the template folder."""
  # Copy the wrapper script.
  shutil.copy(
      package.ResourcePath("grr-response-core", "install_data/wrapper.sh.in"),
      dist_dir)

  shutil.move(
      os.path.join(package_dir, "debian"), os.path.join(package_dir,
                                                        "rpmbuild"))
  # Copy prelink blacklist file. Without this file, prelink will mangle
  # the GRR binary.
  shutil.copy(
      config_lib.Resource().Filter(
          "install_data/centos/prelink_blacklist.conf.in"),
      os.path.join(package_dir, "rpmbuild/prelink_blacklist.conf.in"))


def _CopyFleetspeakRpmFiles(package_dir, context=None):
  """Copies Fleetspeak-enabled RPM files into the template folder."""
  if context is None:
    raise ValueError("context can't be None")

  utils.EnsureDirExists(os.path.join(package_dir, "fleetspeak/rpmbuild"))

  shutil.copy(
      config_lib.Resource().Filter(
          "install_data/centos/fleetspeak.grr.spec.in"),
      os.path.join(package_dir, "fleetspeak/rpmbuild/grr.spec.in"))

  # Include the Fleetspeak service config in the template.
  fleetspeak_dir = os.path.join(package_dir, "fleetspeak/fleetspeak")
  utils.EnsureDirExists(fleetspeak_dir)
  shutil.copy(
      config.CONFIG.Get(
          "ClientBuilder.fleetspeak_config_path", context=context),
      fleetspeak_dir)


class CentosClientBuilder(build.ClientBuilder):
  """A builder class that produces a client for RPM based distros."""

  BUILDER_CONTEXT = "Target:Linux"

  @property
  def package_dir(self):
    return config.CONFIG.Get("PyInstaller.dpkg_root", context=self.context)

  @property
  def fleetspeak_install_dir(self):
    return config.CONFIG.Get(
        "ClientBuilder.fleetspeak_install_dir", context=self.context)

  def MakeExecutableTemplate(self, output_file):
    build_helpers.MakeBuildDirectory(context=self.context)
    build_helpers.CleanDirectory(self.package_dir)
    output_dir = build_helpers.BuildWithPyInstaller(context=self.context)

    _StripLibraries(output_dir)
    _CopyCommonRpmFiles(self.package_dir, output_dir)
    _CopyFleetspeakRpmFiles(self.package_dir, context=self.context)
    _CopyBundledFleetspeakFiles(self.fleetspeak_install_dir, self.package_dir)

    _MakeZip(self.package_dir, output_file)
