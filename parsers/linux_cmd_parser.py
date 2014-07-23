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
      remaining_lines = stdout.splitlines()[i+1:]
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
