#!/usr/bin/env python
"""An implementation of linux client builder."""
import os
import shutil
import zipfile

from grr.lib import build
from grr.lib import config_lib


class LinuxClientBuilder(build.ClientBuilder):
  """Builder class for the Linux client."""

  def __init__(self, context=None):
    super(LinuxClientBuilder, self).__init__(context=context)
    self.context.append("Target:Linux")

  def MakeExecutableTemplate(self):
    self.MakeBuildDirectory()
    self.CleanDirectory(config_lib.CONFIG.Get("PyInstaller.dpkg_root",
                                              context=self.context))
    self.BuildWithPyInstaller()
    self.CopyFiles()
    self.MakeZip()

  def CopyFiles(self):
    """This sets up the template directory."""

    dpkg_dir = config_lib.CONFIG.Get("PyInstaller.dpkg_root",
                                     context=self.context)
    src_dir = config_lib.CONFIG.Get("PyInstaller.build_root_dir",
                                    context=self.context)

    # Copy files needed for dpkg-buildpackage.
    shutil.copytree(
        os.path.join(src_dir, "grr/config/debian/dpkg_client/debian"),
        os.path.join(dpkg_dir, "debian/debian.in"))

    outdir = os.path.join(dpkg_dir, "debian/upstart.in")
    self.EnsureDirExists(outdir)
    shutil.copy(
        os.path.join(src_dir, "grr/config/debian/upstart/grr-client.conf"),
        outdir)

  def MakeZip(self):
    """This builds the template."""

    template_path = config_lib.CONFIG.Get("ClientBuilder.template_path",
                                          context=self.context)
    self.EnsureDirExists(os.path.dirname(template_path))
    zf = zipfile.ZipFile(template_path, "w")
    oldwd = os.getcwd()
    os.chdir(config_lib.CONFIG.Get("PyInstaller.dpkg_root",
                                   context=self.context))
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
    src_dir = config_lib.CONFIG.Get("PyInstaller.build_root_dir",
                                    context=self.context)

    # Copy files needed for rpmbuild.
    shutil.move(
        os.path.join(build_dir, "debian"),
        os.path.join(build_dir, "rpmbuild"))
    shutil.copy(
        os.path.join(src_dir, "grr/config/centos/grr.spec.in"),
        os.path.join(build_dir, "rpmbuild/grr.spec.in"))
    shutil.copy(
        os.path.join(src_dir, "grr/config/centos/grr-client.initd.in"),
        os.path.join(build_dir, "rpmbuild/grr-client.initd.in"))
