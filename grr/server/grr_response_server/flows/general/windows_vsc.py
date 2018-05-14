#!/usr/bin/env python
"""Queries a Windows client for Volume Shadow Copy information."""
from grr.lib.rdfvalues import client as rdf_client
from grr.lib.rdfvalues import paths as rdf_paths
from grr.server.grr_response_server import data_store
from grr.server.grr_response_server import flow
from grr.server.grr_response_server import server_stubs
from grr.server.grr_response_server.flows.general import filesystem


class ListVolumeShadowCopies(flow.GRRFlow):
  """List the Volume Shadow Copies on the client."""

  category = "/Filesystem/"
  behaviours = flow.GRRFlow.behaviours + "BASIC"

  @flow.StateHandler()
  def Start(self, unused_response):
    """Query the client for available Volume Shadow Copies using a WMI query."""
    self.state.shadows = []
    self.state.raw_device = None

    self.CallClient(
        server_stubs.WmiQuery,
        query="SELECT * FROM Win32_ShadowCopy",
        next_state="ListDeviceDirectories")

  @flow.StateHandler()
  def ListDeviceDirectories(self, responses):
    if not responses.success:
      raise flow.FlowError("Unable to query Volume Shadow Copy information.")

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

        aff4path = path_spec.AFF4Path(self.client_id)
        self.state.raw_device = aff4path.Dirname()

        self.state.shadows.append(aff4path)

  @flow.StateHandler()
  def ProcessListDirectory(self, responses):
    """Processes the results of the ListDirectory client action.

    Args:
      responses: a flow Responses object.
    """
    if not responses.success:
      raise flow.FlowError("Unable to list directory.")

    with data_store.DB.GetMutationPool() as pool:
      for response in responses:
        stat_entry = rdf_client.StatEntry(response)
        filesystem.CreateAFF4Object(
            stat_entry, self.client_id, pool, token=self.token)
        self.SendReply(stat_entry)

  @flow.StateHandler()
  def End(self):
    if not self.state.shadows:
      raise flow.FlowError("No Volume Shadow Copies were found.\n"
                           "The volume could have no Volume Shadow Copies "
                           "as Windows versions pre Vista or the Volume "
                           "Shadow Copy Service has been disabled.")
