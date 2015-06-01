#!/usr/bin/env python
"""Fallback flows for artifacts that couldn't be collected normally.

These flows subclass lib.artifact.ArtifactFallbackCollector.
"""

from grr.lib import artifact
from grr.lib import flow
# pylint: disable=unused-import
from grr.lib import parsers
# pylint: enable=unused-import
from grr.lib.rdfvalues import client as rdf_client
from grr.lib.rdfvalues import paths as rdf_paths
from grr.lib.rdfvalues import protodict as rdf_protodict


class SystemRootSystemDriveFallbackFlow(artifact.ArtifactFallbackCollector):
  """Flow that attempts to guess systemroot and systemdrive.

  This is the fallback flow for the SystemRoot and
  SystemDriveEnvironmentVariable artifacts.  These values underpin many other
  artifact values so we want to make an educated guess if we can't collect by
  normal means.
  """
  artifacts = ["SystemRoot", "SystemDriveEnvironmentVariable"]

  @flow.StateHandler(next_state="ProcessFileStats")
  def Start(self):
    self.state.Register("success", False)
    system_drive_opts = ["C:", "D:"]
    for drive in system_drive_opts:
      pathspec = rdf_paths.PathSpec(path=drive,
                                    pathtype=rdf_paths.PathSpec.PathType.OS)
      self.CallClient("ListDirectory", pathspec=pathspec,
                      next_state="ProcessFileStats")

  @flow.StateHandler()
  def ProcessFileStats(self, responses):
    """Extract DataBlob from Stat response."""
    if not responses.success:
      return

    system_root_paths = ["Windows", "WinNT", "WINNT35", "WTSRV", "WINDOWS"]
    for response in responses:
      if response.pathspec.path[4:] in system_root_paths:
        systemdrive = response.pathspec.path[1:3]
        systemroot = "%s\\%s" % (systemdrive, response.pathspec.path[4:])

        # Put the data back into the original format expected for the artifact
        data = rdf_protodict.DataBlob().SetValue(systemroot)
        self.SendReply(rdf_client.StatEntry(registry_data=data))
        self.state.success = True
        break

  @flow.StateHandler()
  def End(self, responses):
    # If this doesn't work these artifacts are so core to everything that we
    # just want to raise and kill any further collection.
    if not self.state.success:
      raise flow.FlowError("Couldn't guess the system root and drive location")

    super(SystemRootSystemDriveFallbackFlow, self).End()
