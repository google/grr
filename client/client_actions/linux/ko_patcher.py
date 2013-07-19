#!/usr/bin/env python
# Copyright 2012 Google Inc. All Rights Reserved.

"""A kernel module rewriter.

This is a hack that rewrites kernel modules such that they can be loaded on
kernels they were not compiled for.
"""



import os
import platform
import struct
import sys


import logging

from grr.lib import flags


class KernelObjectPatcher(object):
  """The kernel object patching class."""

  ELF_MAGIC = "\x7F\x45\x4C\x46"

  def __init__(self, log=False):
    self.log = log

  def GetSectionOffsets(self, file_data):
    """Returns offsets and lengths of all the sections of this elf file."""

    if file_data[:4] != self.ELF_MAGIC:
      raise RuntimeError("Not an elf file.")

    section_header_offset = struct.unpack("<Q", file_data[40:40+8])[0]
    (section_header_size, num_section_headers,
     string_table) = struct.unpack("<HHH", file_data[58:58+6])

    # Read the string table first.
    start = section_header_offset + string_table * section_header_size
    header_data = file_data[start:start + section_header_size]
    offset, size = struct.unpack("<IIQQQQIIQQ", header_data)[4:6]

    string_data = file_data[offset:offset+size]

    sections = {}

    for start in xrange(section_header_offset,
                        section_header_offset + (
                            num_section_headers * section_header_size),
                        section_header_size):
      header_data = file_data[start: start + section_header_size]

      header = struct.unpack("<IIQQQQIIQQ", header_data)
      name_offset, data_offset, data_size = header[0], header[4], header[5]
      name = string_data[name_offset:string_data.find("\x00", name_offset)]

      if data_size:
        sections[name] = (data_offset, data_size)

    return sections

  def ParseVersionSection(self, version_data):
    """Returns the checksums found for all the imports."""
    checksums = {}
    while version_data:
      act_version = version_data[:0x40]
      version_data = version_data[0x40:]

      function = act_version[8:]
      chksum = act_version[:8]
      checksums[function] = chksum
    return checksums

  def GetImportedVersions(self, file_data, sections):
    if "__versions" not in sections:
      return {}
    start, length = sections["__versions"]
    version_data = file_data[start:start+length]
    return self.ParseVersionSection(version_data)

  def GetModuleVersion(self, file_data, sections):
    info_start, info_length = sections[".modinfo"]
    modinfo = file_data[info_start:info_start + info_length]

    for line in modinfo.split("\x00"):
      if line.startswith("vermagic"):
        return line[len("vermagic") + 1:]
    msg = "Could not find vermagic string."
    logging.info(msg)
    raise RuntimeError(msg)

  def _RewriteModinfo(self, modinfo, obj_kernel_version, this_kernel_version,
                      info_strings=None, to_remove=None):
    new_modinfo = ""
    for line in modinfo.split("\x00"):
      if not line:
        continue
      if to_remove and line.split("=")[0] == to_remove:
        continue
      if info_strings is not None:
        info_strings.add(line.split("=")[0])
      if line.startswith("vermagic"):
        line = line.replace(obj_kernel_version, this_kernel_version)
      new_modinfo += line + "\x00"
    return new_modinfo

  def RewriteModinfo(self, file_data, sections, obj_kernel_version,
                     this_kernel_version):
    """This rewrites the modinfo section and updates the kernel version."""
    info_start, info_length = sections[".modinfo"]
    modinfo = file_data[info_start:info_start + info_length]

    info_strings = set()
    new_modinfo = self._RewriteModinfo(modinfo, obj_kernel_version,
                                       this_kernel_version, info_strings)

    if len(new_modinfo) <= info_length:
      new_modinfo += "\x00" * (info_length - len(new_modinfo))
      return new_modinfo

    logging.info("Rewritten modinfo section is too big.")
    info_strings -= set(["vermagic", "srcversion", "depends"])
    try:
      to_remove = info_strings.pop()
    except KeyError:
      msg = "Could not remove anything from modinfo, giving up."
      logging.info(msg)
      raise RuntimeError(msg)
    logging.info("Will try to remove %s from modinfo.", to_remove)

    return self._RewriteModinfo(modinfo, obj_kernel_version,
                                this_kernel_version, to_remove=to_remove)

  def GetKnownImports(self, needed_versions):
    """Parses the driver directory to find valid import checksums."""
    needed_versions = set(needed_versions)
    found_versions = {}

    driver_path = "/lib/modules/%s/kernel/drivers" % platform.uname()[2]
    num_files = 0
    for (directory, _, files) in os.walk(driver_path):
      for filename in files:
        if filename[-3:] == ".ko":
          try:
            fd = open("%s/%s" % (directory, filename), "rb")
            num_files += 1
            data = fd.read()
            sections = self.GetSectionOffsets(data)
            versions = self.GetImportedVersions(data, sections)
            found_versions.update(versions)
            if set(found_versions.keys()) >= needed_versions:
              logging.info("All imports found, gathered data from %d modules.",
                           num_files)
              return found_versions
          except IOError:
            pass

    missing = needed_versions - set(found_versions.keys())
    msg = "Imports %s could not be found." % ",".join(missing)
    logging.info(msg)
    raise RuntimeError(msg)

  def ReplaceSection(self, file_data, offset, new_section_data):
    result = file_data[:offset]
    result += new_section_data
    result += file_data[offset + len(new_section_data):]
    return result

  def Patch(self, file_data, force_patch=False):
    try:
      sections = self.GetSectionOffsets(file_data)
      obj_version = self.GetModuleVersion(file_data, sections)
      obj_kernel_version = obj_version.split(" ")[0]
      this_kernel_version = platform.uname()[2]
      logging.info("Module version is %s, kernel version is %s.",
                   obj_kernel_version, this_kernel_version)
      if obj_kernel_version == this_kernel_version and not force_patch:
        return file_data

      needed_imports = self.GetImportedVersions(file_data, sections)
      good_imports = self.GetKnownImports(needed_imports)

      rewritten_version_data = ""
      for function in needed_imports.keys():
        if needed_imports[function] == good_imports[function]:
          logging.info("Matching checksum for %s.",
                       function.replace("\x00", ""))
        else:
          logging.info("Checksum mismatch for %s.",
                       function.replace("\x00", ""))
        rewritten_version_data += good_imports[function] + function

      rewritten_modinfo_data = self.RewriteModinfo(
          file_data, sections, obj_kernel_version, this_kernel_version)

      file_data = self.ReplaceSection(file_data, sections["__versions"][0],
                                      rewritten_version_data)
      file_data = self.ReplaceSection(file_data, sections[".modinfo"][0],
                                      rewritten_modinfo_data)
      return file_data

    except (RuntimeError, KeyError) as e:
      logging.info(str(e))
      # Something didn't work, we can just use the data we were sent.
      return file_data


def main(_):
  if len(sys.argv) < 3:
    print "Usage: python %s <kernel_module> <outfile>" % sys.argv[0]
    exit()

  in_fd = open(sys.argv[1], "rb")

  out_data = KernelObjectPatcher(log=True).Patch(in_fd.read(), force_patch=True)

  with open(sys.argv[2], "wb") as out_fd:
    out_fd.write(out_data)

  logging.info("Kernel Object patched.")

if __name__ == "__main__":
  flags.StartMain(main)
