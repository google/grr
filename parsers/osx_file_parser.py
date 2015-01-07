#!/usr/bin/env python
"""Simple parsers for OS X files."""

import cStringIO

import os
import stat

from grr.lib import parsers
from grr.lib import rdfvalue
from grr.parsers import binplist


class OSXUsersParser(parsers.ArtifactFilesParser):
  """Parser for Glob of /Users/*."""

  output_types = ["KnowledgeBaseUser"]
  supported_artifacts = ["OSXUsers"]
  blacklist = ["Shared"]

  def Parse(self, stat_entries, knowledge_base, path_type):
    """Parse the StatEntry objects."""
    _, _ = knowledge_base, path_type

    for stat_entry in stat_entries:
      if stat.S_ISDIR(stat_entry.st_mode):
        homedir = stat_entry.pathspec.path
        username = os.path.basename(homedir)
        if username not in self.blacklist:
          yield rdfvalue.KnowledgeBaseUser(username=username,
                                           homedir=homedir)


class OSXSPHardwareDataTypeParser(parsers.CommandParser):
  """Parser for the Hardware Data from System Profiler."""
  output_types = ["HardwareInfo"]
  supported_artifacts = ["OSXSPHardwareDataType"]

  def Parse(self, cmd, args, stdout, stderr, return_val, time_taken,
            knowledge_base):
    """Parse the system profiler output. We get it in the form of a plist."""
    _ = stderr, time_taken, args, knowledge_base  # Unused
    self.CheckReturn(cmd, return_val)

    serial_number = []
    hardware_list = []
    plist = binplist.readPlist(cStringIO.StringIO(stdout))

    if len(plist) > 1:
      raise parsers.ParseError("SPHardwareDataType plist has too many items.")

    hardware_list = plist[0]["_items"][0]
    serial_number = hardware_list["serial_number"]

    yield rdfvalue.HardwareInfo(serial_number=serial_number)
