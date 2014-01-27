#!/usr/bin/env python
"""Simple parsers for OS X files."""

import os
import stat

from grr.lib import parsers
from grr.lib import rdfvalue


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


