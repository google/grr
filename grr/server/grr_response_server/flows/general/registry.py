#!/usr/bin/env python
"""Gather information from the registry on windows."""

from grr_response_core import config
from grr_response_core.lib import artifact_utils
from grr_response_core.lib.rdfvalues import mig_client
from grr_response_core.lib.rdfvalues import paths as rdf_paths
from grr_response_core.path_detection import windows as path_detection_windows
from grr_response_server import data_store
from grr_response_server import flow_base
from grr_response_server.flows.general import collectors
from grr_response_server.flows.general import transfer


class CollectRunKeyBinaries(flow_base.FlowBase):
  """Collect the binaries used by Run and RunOnce keys on the system.

  We use the RunKeys artifact to get RunKey command strings for all users and
  System. This flow guesses file paths from the strings, expands any
  windows system environment variables, and attempts to retrieve the files.
  """
  category = "/Registry/"
  behaviours = flow_base.BEHAVIOUR_BASIC

  def Start(self):
    """Get runkeys via the ArtifactCollectorFlow."""
    self.CallFlow(
        collectors.ArtifactCollectorFlow.__name__,
        artifact_list=["WindowsRunKeys"],
        use_raw_filesystem_access=True,
        next_state=self.ParseRunKeys.__name__)

  def ParseRunKeys(self, responses):
    """Get filenames from the RunKeys and download the files."""
    filenames = []
    client = data_store.REL_DB.ReadClientSnapshot(self.client_id)
    kb = mig_client.ToRDFKnowledgeBase(client.knowledge_base)

    for response in responses:
      runkey = response.registry_data.string

      environ_vars = artifact_utils.GetWindowsEnvironmentVariablesMap(kb)
      path_guesses = path_detection_windows.DetectExecutablePaths([runkey],
                                                                  environ_vars)

      if not path_guesses:
        self.Log("Couldn't guess path for %s", runkey)

      for path in path_guesses:
        filenames.append(
            rdf_paths.PathSpec(
                path=path,
                pathtype=config.CONFIG["Server.raw_filesystem_access_pathtype"])
        )

    if filenames:
      self.CallFlow(
          transfer.MultiGetFile.__name__,
          pathspecs=filenames,
          next_state=self.Done.__name__)

  def Done(self, responses):
    for response in responses:
      self.SendReply(response)
