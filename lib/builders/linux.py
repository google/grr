#!/usr/bin/env python
"""An implementation of linux client builder."""
import logging
import os
import shutil
import struct
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
    self.CopyMissingModules()
    self.PatchUpPyinstaller()
    self.CopyFiles()
    self.MakeZip()

  def PatchUpPyinstaller(self):
    """PyInstaller binaries need to be repaired.

    PyInstaller just dumps the packed payload at the end of the ELF binary
    without adjusting the ELF sections. This means that any manipulation of the
    ELF file (e.g. prelinking the file as is commonly done on RedHat machines)
    will strip the payload from the file.

    We fix this by extending the last section to the end of the file so the
    payload is included.
    """
    root = config_lib.CONFIG.Get("PyInstaller.dpkg_root", context=self.context)
    with open(os.path.join(root, "debian/grr-client/grr-client"), "r+b") as fd:
      # Find the size of the file.
      fd.seek(0, 2)
      size = fd.tell()
      fd.seek(0, 0)

      # The headers should fall within the first part.
      data = fd.read(1000000)

      # Only support 64 bit ELF files right now.
      if data[:5] == "\x7fELF\x02":

        # Ref: http://en.wikipedia.org/wiki/Executable_and_Linkable_Format
        shr_offset = struct.unpack("<Q", data[0x28:0x28+8])[0]
        number_of_sections = struct.unpack("<H", data[0x3c:0x3c+2])[0]
        size_of_section = struct.unpack("<H", data[0x3a:0x3a+2])[0]

        # We extend the last section right up to the end of the file.
        last_section_offset = (shr_offset +
                               (number_of_sections - 1) * size_of_section)

        # The file offset where the section starts.
        start_of_section = struct.unpack("<Q", data[
            last_section_offset+0x18:last_section_offset+0x18+8])[0]

        # Overwrite the size of the section.
        fd.seek(last_section_offset+0x20)
        fd.write(struct.pack("<Q", size-start_of_section))

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

    logging.info("Generating zip template file at %s", template_path)


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
