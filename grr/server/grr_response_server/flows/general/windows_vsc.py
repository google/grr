#!/usr/bin/env python
"""Queries a Windows client for Volume Shadow Copy information."""
from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

from grr_response_core.lib.rdfvalues import client_fs as rdf_client_fs
from grr_response_core.lib.rdfvalues import paths as rdf_paths
from grr_response_server import data_store
from grr_response_server import flow
from grr_response_server import flow_base
from grr_response_server import server_stubs
from grr_response_server.flows.general import filesystem


@flow_base.DualDBFlow
class ListVolumeShadowCopiesMixin(object):
  """List the Volume Shadow Copies on the client."""

  category = "/Filesystem/"
  behaviours = flow.GRRFlow.behaviours + "BASIC"

  def Start(self):
    """Query the client for available Volume Shadow Copies using a WMI query."""
    self.CallClient(
        server_stubs.WmiQuery,
        query="SELECT * FROM Win32_ShadowCopy",
        next_state="ListDeviceDirectories")

  def ListDeviceDirectories(self, responses):
    """Flow state that calls ListDirectory action for each shadow copy."""

    if not responses.success:
      raise flow.FlowError("Unable to query Volume Shadow Copy information.")

    shadows_found = False
    for response in responses:
      device_object = response.GetItem("DeviceObject", "")
      global_root = r"\\?\GLOBALROOT\Device"

      if device_object.startswith(global_root):
        # The VSC device path is returned as \\?\GLOBALROOT\Device\
        # HarddiskVolumeShadowCopy1 and need to pass it as
        #  \\.\HarddiskVolumeShadowCopy1 to the ListDirectory flow
        device_object = r"\\." + device_object[len(global_root):]

        path_spec = rdf_paths.PathSpec(
            path=device_object, pathtype=rdf_paths.PathSpec.PathType.OS)

        path_spec.Append(path="/", pathtype=rdf_paths.PathSpec.PathType.TSK)

        self.Log("Listing Volume Shadow Copy device: %s.", device_object)
        self.CallClient(
            server_stubs.ListDirectory,
            pathspec=path_spec,
            next_state="ProcessListDirectory")

        shadows_found = True

    if not shadows_found:
      raise flow.FlowError("No Volume Shadow Copies were found.\n"
                           "The volume could have no Volume Shadow Copies "
                           "as Windows versions pre Vista or the Volume "
                           "Shadow Copy Service has been disabled.")

  def ProcessListDirectory(self, responses):
    """Processes the results of the ListDirectory client action.

    Args:
      responses: a flow Responses object.
    """
    if not responses.success:
      raise flow.FlowError("Unable to list directory.")

    with data_store.DB.GetMutationPool() as pool:
      filesystem.WriteStatEntries(
          [rdf_client_fs.StatEntry(response) for response in responses],
          client_id=self.client_id,
          mutation_pool=pool,
          token=self.token)

    for response in responses:
      self.SendReply(response)
