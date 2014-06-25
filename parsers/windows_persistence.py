#!/usr/bin/env python
"""Parse various Windows persistence mechanisms into PersistenceFiles."""

import re

from grr.lib import artifact_lib
from grr.lib import parsers
from grr.lib import rdfvalue
from grr.lib import utils


class WindowsPersistenceMechanismsParser(parsers.ArtifactFilesParser):
  """Turn various persistence objects into PersistenceFiles."""
  output_types = ["PersistenceFile"]
  supported_artifacts = ["WindowsPersistenceMechanisms"]
  # Required for environment variable expansion
  knowledgebase_dependencies = ["environ_systemdrive", "environ_systemroot"]

  def __init__(self):
    # Service keys have peculiar ways of specifying systemroot, these regexes
    # will be used to convert them to standard expansions.
    self.systemroot_re = re.compile(r"^\\SystemRoot", flags=re.IGNORECASE)
    self.system32_re = re.compile(r"^system32", flags=re.IGNORECASE)
    super(WindowsPersistenceMechanismsParser, self).__init__()

  def _IsExecutableExtension(self, path):
    return path.endswith(("exe", "com", "bat", "dll", "msi", "sys", "scr",
                          "pif"))

  def _GetFilePaths(self, path, pathtype, kb):
    """Guess windows filenames from a commandline string."""
    pathspecs = []
    path_guesses = utils.GuessWindowsFileNameFromString(path)
    path_guesses = filter(self._IsExecutableExtension, path_guesses)
    if not path_guesses:
      # TODO(user): yield a ParserAnomaly object
      return []

    for path in path_guesses:
      path = re.sub(self.systemroot_re, r"%systemroot%",
                    path, count=1)
      path = re.sub(self.system32_re, r"%systemroot%\\system32",
                    path, count=1)
      full_path = artifact_lib.ExpandWindowsEnvironmentVariables(path, kb)
      pathspecs.append(rdfvalue.PathSpec(
          path=full_path, pathtype=pathtype))

    return pathspecs

  def Parse(self, persistence, knowledge_base, download_pathtype):
    """Convert persistence collector output to downloadable rdfvalues."""
    pathspecs = []
    source_urn = None

    if isinstance(persistence, rdfvalue.WindowsServiceInformation):
      if persistence.HasField("registry_key"):
        source_urn = persistence.registry_key
      if persistence.HasField("binary"):
        pathspecs.append(persistence.binary.pathspec)
      elif persistence.HasField("image_path"):
        pathspecs = self._GetFilePaths(persistence.image_path,
                                       download_pathtype, knowledge_base)
      # TODO(user): handle empty image_path driver default

    if isinstance(persistence, rdfvalue.StatEntry) and persistence.HasField(
        "registry_type"):
      pathspecs = self._GetFilePaths(persistence.registry_data.string,
                                     download_pathtype, knowledge_base)
      source_urn = persistence.aff4path

    for pathspec in pathspecs:
      yield rdfvalue.PersistenceFile(pathspec=pathspec,
                                     source_urn=source_urn)

