#!/usr/bin/env python
"""Simple parsers for the output of linux commands."""


import re

from grr.lib import parsers
from grr.lib import rdfvalue


class DpkgCmdParser(parsers.CommandParser):
  """Parser for dpkg output. Yields SoftwarePackage rdfvalues."""

  output_types = ["SoftwarePackage"]
  supported_artifacts = ["DebianPackagesList"]

  def Parse(self, cmd, args, stdout, stderr, return_val, time_taken,
            knowledge_base):
    """Parse the dpkg output."""
    _ = stderr, time_taken, args, knowledge_base  # Unused.
    self.CheckReturn(cmd, return_val)
    column_lengths = []
    i = 0
    for i, line in enumerate(stdout.splitlines()):
      if line.startswith("+++-"):
        # This is a special header line that determines column size.
        for col in line.split("-")[1:]:
          if not re.match("=*", col):
            raise parsers.ParseError("Invalid header parsing for %s at line "
                                     "%s" % (cmd, i))
          column_lengths.append(len(col))
        break

    if column_lengths:
      remaining_lines = stdout.splitlines()[i + 1:]
      for i, line in enumerate(remaining_lines):
        cols = line.split(None, len(column_lengths))
        # Installed, Name, Version, Architecture, Description
        status, name, version, arch, desc = cols
        # Status is potentially 3 columns, but always at least two, desired and
        # actual state. We only care about actual state.
        if status[1] == "i":
          status = rdfvalue.SoftwarePackage.InstallState.INSTALLED
        else:
          status = rdfvalue.SoftwarePackage.InstallState.UNKNOWN
        yield rdfvalue.SoftwarePackage(name=name, description=desc,
                                       version=version, architecture=arch,
                                       install_state=status)


class DmidecodeCmdParser(parsers.CommandParser):
  """Parser for dmidecode output. Yields HardwareInfo rdfvalues."""

  output_types = ["HardwareInfo"]
  supported_artifacts = ["LinuxHardwareInfo"]

  def Parse(self, cmd, args, stdout, stderr, return_val, time_taken,
            knowledge_base):
    """Parse the dmidecode output. All data is parsed into a dictionary."""
    _ = stderr, time_taken, args, knowledge_base  # Unused.
    self.CheckReturn(cmd, return_val)
    output = iter(stdout.splitlines())
    system_information = []
    serial_number = ""
    system_manufacturer = ""

    system_info = re.compile(r"\s*System Information")
    for line in output:
      if system_info.match(line):
        # Collect all System Information until we hit a blank line.
        while line:
          system_information.append(line)
          line = output.next()
        break

    system_re = re.compile(r"\s*Manufacturer: ([0-9a-zA-Z-]*)")
    serial_re = re.compile(r"\s*Serial Number: ([0-9a-zA-Z-]*)")
    for line in system_information:
      match_sn = serial_re.match(line)
      match_manf = system_re.match(line)
      if match_sn:
        serial_number = match_sn.groups()[0].strip()
      elif match_manf:
        system_manufacturer = match_manf.groups()[0].strip()

    return rdfvalue.HardwareInfo(serial_number=serial_number,
                                 system_manufacturer=system_manufacturer)


class UserParser(parsers.GenericResponseParser):
  """Convert User to KnowledgeBaseUser for backwards compatibility."""

  output_types = ["KnowledgeBaseUser"]
  supported_artifacts = ["LinuxUserProfiles"]

  def Parse(self, user, knowledge_base):
    _ = knowledge_base
    if isinstance(user, rdfvalue.User):
      yield user.ToKnowledgeBaseUser()
    else:
      yield user
