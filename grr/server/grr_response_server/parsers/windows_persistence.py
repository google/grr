#!/usr/bin/env python
"""Parse various Windows persistence mechanisms into PersistenceFiles."""

from grr.lib import parser
from grr.lib.rdfvalues import client as rdf_client
from grr.lib.rdfvalues import paths as rdf_paths
from grr.lib.rdfvalues import standard as rdf_standard
from grr.path_detection import windows as path_detection_windows
from grr.server.grr_response_server import artifact_utils


class WindowsPersistenceMechanismsParser(parser.ArtifactFilesParser):
  """Turn various persistence objects into PersistenceFiles."""
  output_types = ["PersistenceFile"]
  supported_artifacts = ["WindowsPersistenceMechanisms"]
  # Required for environment variable expansion
  knowledgebase_dependencies = ["environ_systemdrive", "environ_systemroot"]

  def _GetFilePaths(self, path, pathtype, kb):
    """Guess windows filenames from a commandline string."""

    environ_vars = artifact_utils.GetWindowsEnvironmentVariablesMap(kb)
    path_guesses = path_detection_windows.DetectExecutablePaths([path],
                                                                environ_vars)

    if not path_guesses:
      # TODO(user): yield a ParserAnomaly object
      return []

    return [
        rdf_paths.PathSpec(path=path, pathtype=pathtype)
        for path in path_guesses
    ]

  def Parse(self, persistence, knowledge_base, download_pathtype):
    """Convert persistence collector output to downloadable rdfvalues."""
    pathspecs = []

    if isinstance(persistence, rdf_client.WindowsServiceInformation):
      if persistence.HasField("binary"):
        pathspecs.append(persistence.binary.pathspec)
      elif persistence.HasField("image_path"):
        pathspecs = self._GetFilePaths(persistence.image_path,
                                       download_pathtype, knowledge_base)
      # TODO(user): handle empty image_path driver default

    if isinstance(
        persistence,
        rdf_client.StatEntry) and persistence.HasField("registry_type"):
      pathspecs = self._GetFilePaths(persistence.registry_data.string,
                                     download_pathtype, knowledge_base)

    for pathspec in pathspecs:
      yield rdf_standard.PersistenceFile(pathspec=pathspec)
