#!/usr/bin/env python
"""An implementation of linux client builder."""
import logging
import os
import shutil
import zipfile

from grr.lib import build
from grr.lib import config_lib
from grr.lib import utils


class LinuxClientBuilder(build.ClientBuilder):
  """Builder class for the Linux client."""

  def __init__(self, context=None):
    super(LinuxClientBuilder, self).__init__(context=context)
    self.context.append("Target:Linux")

  def MakeExecutableTemplate(self, output_file=None):
    super(LinuxClientBuilder, self).MakeExecutableTemplate(
        output_file=output_file)
    self.MakeBuildDirectory()
    self.CleanDirectory(config_lib.CONFIG.Get("PyInstaller.dpkg_root",
                                              context=self.context))
    self.BuildWithPyInstaller()
    self.CopyMissingModules()
    self.CopyFiles()
    self.MakeZip(
        config_lib.CONFIG.Get("PyInstaller.dpkg_root",
                              context=self.context),
        self.template_file)

  def CopyFiles(self):
    """This sets up the template directory."""

    dpkg_dir = config_lib.CONFIG.Get("PyInstaller.dpkg_root",
                                     context=self.context)

    # Copy files needed for dpkg-buildpackage.
    shutil.copytree(
        config_lib.Resource().Filter("install_data/debian/dpkg_client/debian"),
        os.path.join(dpkg_dir, "debian/debian.in"))

    # Copy upstart files
    outdir = os.path.join(dpkg_dir, "debian/upstart.in")
    utils.EnsureDirExists(outdir)
    shutil.copy(config_lib.Resource().Filter(
        "install_data/debian/dpkg_client/upstart/grr-client.conf"), outdir)

    # Copy init files
    outdir = os.path.join(dpkg_dir, "debian/initd.in")
    utils.EnsureDirExists(outdir)
    shutil.copy(config_lib.Resource().Filter(
        "install_data/debian/dpkg_client/initd/grr-client"), outdir)

    # Copy systemd files
    outdir = os.path.join(dpkg_dir, "debian/systemd.in")
    utils.EnsureDirExists(outdir)
    shutil.copy(config_lib.Resource().Filter(
        "install_data/systemd/client/grr-client.service"), outdir)

  def MakeZip(self, input_dir, output_file):
    """Creates a ZIP archive of the files in the input directory.

    Args:
      input_dir: the name of the input directory.
      output_file: the name of the output ZIP archive without extension.
    """

    logging.info("Generating zip template file at %s", output_file)
    zf = zipfile.ZipFile(output_file, "w")
    oldwd = os.getcwd()
    os.chdir(input_dir)
    for path in ["debian", "rpmbuild"]:
      for root, _, files in os.walk(path):
        for f in files:
          zf.write(os.path.join(root, f))
    zf.close()
    os.chdir(oldwd)


class CentosClientBuilder(LinuxClientBuilder):
  """A builder class that produces a client for RPM based distros."""

  def CopyFiles(self):
    """This sets up the template directory."""

    build_dir = config_lib.CONFIG.Get("PyInstaller.dpkg_root",
                                      context=self.context)
    # Copy files needed for rpmbuild.
    shutil.move(
        os.path.join(build_dir, "debian"), os.path.join(build_dir, "rpmbuild"))
    shutil.copy(config_lib.Resource().Filter("install_data/centos/grr.spec.in"),
                os.path.join(build_dir, "rpmbuild/grr.spec.in"))
    shutil.copy(
        config_lib.Resource().Filter("install_data/centos/grr-client.initd.in"),
        os.path.join(build_dir, "rpmbuild/grr-client.initd.in"))
