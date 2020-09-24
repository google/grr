#!/usr/bin/env python
# Lint as: python3
"""Parse various Windows persistence mechanisms into PersistenceFiles."""

from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

from typing import Iterator

from grr_response_core.lib import artifact_utils
from grr_response_core.lib import parsers
from grr_response_core.lib import rdfvalue
from grr_response_core.lib.rdfvalues import client as rdf_client
from grr_response_core.lib.rdfvalues import client_fs as rdf_client_fs
from grr_response_core.lib.rdfvalues import paths as rdf_paths
from grr_response_core.lib.rdfvalues import standard as rdf_standard
from grr_response_core.path_detection import windows as path_detection_windows


class WindowsPersistenceMechanismsParser(
    parsers.SingleResponseParser[rdf_standard.PersistenceFile]):
  """Turn various persistence objects into PersistenceFiles."""
  output_types = [rdf_standard.PersistenceFile]
  supported_artifacts = ["WindowsPersistenceMechanisms"]
  # Required for environment variable expansion
  knowledgebase_dependencies = ["environ_systemdrive", "environ_systemroot"]

  def _GetFilePaths(self, path, kb):
    """Guess windows filenames from a commandline string."""

    environ_vars = artifact_utils.GetWindowsEnvironmentVariablesMap(kb)
    path_guesses = path_detection_windows.DetectExecutablePaths([path],
                                                                environ_vars)

    if not path_guesses:
      # TODO(user): yield a ParserAnomaly object
      return []

    return [
        rdf_paths.PathSpec(
            path=path, pathtype=rdf_paths.PathSpec.PathType.UNSET)
        for path in path_guesses
    ]

  def ParseResponse(
      self,
      knowledge_base: rdf_client.KnowledgeBase,
      response: rdfvalue.RDFValue,
  ) -> Iterator[rdf_standard.PersistenceFile]:
    """Convert persistence collector output to downloadable rdfvalues."""
    pathspecs = []

    if isinstance(response, rdf_client.WindowsServiceInformation):
      if response.HasField("binary"):
        pathspecs.append(response.binary.pathspec)
      elif response.HasField("image_path"):
        pathspecs = self._GetFilePaths(response.image_path, knowledge_base)

    if (isinstance(response, rdf_client_fs.StatEntry) and
        response.HasField("registry_type")):
      pathspecs = self._GetFilePaths(response.registry_data.string,
                                     knowledge_base)

    for pathspec in pathspecs:
      yield rdf_standard.PersistenceFile(pathspec=pathspec)
