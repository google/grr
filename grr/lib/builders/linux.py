#!/usr/bin/env python
"""An implementation of linux client builder."""
import logging
import os
import shutil
import struct
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
    self.PatchUpPyinstaller()
    self.CopyFiles()
    self.MakeZip(
        config_lib.CONFIG.Get("PyInstaller.dpkg_root", context=self.context),
        self.template_file)

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

      # Support 64 bit ELF files.
      if data[:5] == "\x7fELF\x02":

        # Ref: http://en.wikipedia.org/wiki/Executable_and_Linkable_Format
        shr_offset = struct.unpack("<Q", data[0x28:0x28 + 8])[0]
        number_of_sections = struct.unpack("<H", data[0x3c:0x3c + 2])[0]
        size_of_section = struct.unpack("<H", data[0x3a:0x3a + 2])[0]

        # We extend the last section right up to the end of the file.
        last_section_offset = (shr_offset +
                               (number_of_sections - 1) * size_of_section)

        # The file offset where the section starts.
        start_of_section = struct.unpack("<Q", data[
            last_section_offset + 0x18:last_section_offset + 0x18 + 8])[0]

        # Overwrite the size of the section.
        fd.seek(last_section_offset + 0x20)
        fd.write(struct.pack("<Q", size - start_of_section))

      # Also support 32 bit ELF.
      elif data[:5] == "\x7fELF\x01":
        # Ref: http://en.wikipedia.org/wiki/Executable_and_Linkable_Format
        shr_offset = struct.unpack("<I", data[0x20:0x20 + 4])[0]
        number_of_sections = struct.unpack("<H", data[0x30:0x30 + 2])[0]
        size_of_section = struct.unpack("<H", data[0x2e:0x2e + 2])[0]

        # We extend the last section right up to the end of the file.
        last_section_offset = (shr_offset +
                               (number_of_sections - 1) * size_of_section)

        # The file offset where the section starts (Elf32_Shdr.sh_offset).
        start_of_section = struct.unpack("<I", data[
            last_section_offset + 0x10:last_section_offset + 0x10 + 4])[0]

        # Overwrite the size of the section (Elf32_Shdr.sh_size).
        fd.seek(last_section_offset + 0x14)
        fd.write(struct.pack("<I", size - start_of_section))

  def CopyFiles(self):
    """This sets up the template directory."""

    dpkg_dir = config_lib.CONFIG.Get("PyInstaller.dpkg_root",
                                     context=self.context)
    src_dir = os.path.join(config_lib.CONFIG["ClientBuilder.source"],
                           "grr")

    # Copy files needed for dpkg-buildpackage.
    shutil.copytree(
        os.path.join(src_dir, "config/debian/dpkg_client/debian"),
        os.path.join(dpkg_dir, "debian/debian.in"))

    # Copy upstart files
    outdir = os.path.join(dpkg_dir, "debian/upstart.in")
    utils.EnsureDirExists(outdir)
    shutil.copy(
        os.path.join(src_dir, "config/upstart/grr-client.conf"),
        outdir)

    # Copy init files
    outdir = os.path.join(dpkg_dir, "debian/initd.in")
    utils.EnsureDirExists(outdir)
    shutil.copy(
        os.path.join(src_dir, "config/debian/initd/grr-client"),
        outdir)

    # Copy systemd files
    outdir = os.path.join(dpkg_dir, "debian/systemd.in")
    utils.EnsureDirExists(outdir)
    shutil.copy(
        os.path.join(src_dir, "config/systemd/grr-client.service"),
        outdir)

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
    src_dir = os.path.join(config_lib.CONFIG["ClientBuilder.source"],
                           "grr")

    # Copy files needed for rpmbuild.
    shutil.move(
        os.path.join(build_dir, "debian"),
        os.path.join(build_dir, "rpmbuild"))
    shutil.copy(
        os.path.join(src_dir, "config/centos/grr.spec.in"),
        os.path.join(build_dir, "rpmbuild/grr.spec.in"))
    shutil.copy(
        os.path.join(src_dir, "config/centos/grr-client.initd.in"),
        os.path.join(build_dir, "rpmbuild/grr-client.initd.in"))
