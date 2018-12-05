#!/usr/bin/env python
"""Fallback flows for artifacts that couldn't be collected normally.

These flows subclass lib.artifact.ArtifactFallbackCollector.
"""
from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

# pylint: disable=unused-import
from grr_response_core.lib import parser
# pylint: enable=unused-import
from grr_response_core.lib.rdfvalues import artifacts as rdf_artifacts
from grr_response_core.lib.rdfvalues import client_fs as rdf_client_fs
from grr_response_core.lib.rdfvalues import paths as rdf_paths
from grr_response_core.lib.rdfvalues import protodict as rdf_protodict
from grr_response_core.lib.rdfvalues import structs as rdf_structs
from grr_response_proto import flows_pb2
from grr_response_server import flow
from grr_response_server import flow_base
from grr_response_server import server_stubs

FALLBACK_REGISTRY = {
    "WindowsEnvironmentVariableSystemRoot":
        "SystemRootSystemDriveFallbackFlow",
    "WindowsEnvironmentVariableSystemDrive":
        "SystemRootSystemDriveFallbackFlow",
    "WindowsEnvironmentVariableAllUsersProfile":
        "WindowsAllUsersProfileFallbackFlow"
}


class ArtifactFallbackCollectorArgs(rdf_structs.RDFProtoStruct):
  protobuf = flows_pb2.ArtifactFallbackCollectorArgs
  rdf_deps = [
      rdf_artifacts.ArtifactName,
  ]


@flow_base.DualDBFlow
class SystemRootSystemDriveFallbackFlowMixin(object):
  """Flow that attempts to guess systemroot and systemdrive.

  This is the fallback flow for the WindowsEnvironmentVariableSystemRoot and
  WindowsEnvironmentVariableSystemDrive artifacts. These values underpin many
  other artifact values so we want to make an educated guess if we cannot
  collect by normal means.

  This flow supports:
    WindowsEnvironmentVariableSystemRoot
    WindowsEnvironmentVariableSystemDrive
  """

  args_type = ArtifactFallbackCollectorArgs

  def Start(self):
    self.state.success = False
    system_drive_opts = ["C:", "D:"]
    for drive in system_drive_opts:
      pathspec = rdf_paths.PathSpec(
          path=drive, pathtype=rdf_paths.PathSpec.PathType.OS)
      self.CallClient(
          server_stubs.ListDirectory,
          pathspec=pathspec,
          next_state="ProcessFileStats")

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
        self.SendReply(rdf_client_fs.StatEntry(registry_data=data))
        self.state.success = True
        break

  def End(self, responses):
    # If this doesn't work these artifacts are so core to everything that we
    # just want to raise and kill any further collection.
    if not self.state.success:
      raise flow.FlowError("Couldn't guess the system root and drive location")

    super(SystemRootSystemDriveFallbackFlowMixin, self).End(responses)


@flow_base.DualDBFlow
class WindowsAllUsersProfileFallbackFlowMixin(object):
  r"""Flow that provides a default value for the AllUsersProfile registry key.

  Newer versions of Windows will typically not have the
  HKLM\Software\Microsoft\Windows NT\CurrentVersion\ProfileList\AllUsersProfile
  key.

  This flow supports:
    ArtifactFallbackCollectorArgs
  """

  args_type = ArtifactFallbackCollectorArgs

  def Start(self):
    data = rdf_protodict.DataBlob().SetValue("All Users")
    self.SendReply(rdf_client_fs.StatEntry(registry_data=data))
    self.state.success = True
