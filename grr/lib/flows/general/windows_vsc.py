#!/usr/bin/env python
"""Queries a Windows client for Volume Shadow Copy information."""
from grr.lib import aff4
from grr.lib import flow
from grr.lib.flows.general import filesystem
from grr.lib.rdfvalues import client as rdf_client
from grr.lib.rdfvalues import paths as rdf_paths


class ListVolumeShadowCopies(flow.GRRFlow):
  """List the Volume Shadow Copies on the client."""

  category = "/Filesystem/"
  behaviours = flow.GRRFlow.behaviours + "BASIC"

  @flow.StateHandler(next_state="ListDeviceDirectories")
  def Start(self, unused_response):
    """Query the client for available Volume Shadow Copies using a WMI query."""
    self.state.Register("shadows", [])
    self.state.Register("raw_device", None)

    self.CallClient("WmiQuery",
                    query="SELECT * FROM Win32_ShadowCopy",
                    next_state="ListDeviceDirectories")

  @flow.StateHandler(next_state="ProcessListDirectory")
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

        path_spec = rdf_paths.PathSpec(path=device_object,
                                       pathtype=rdf_paths.PathSpec.PathType.OS)

        path_spec.Append(path="/", pathtype=rdf_paths.PathSpec.PathType.TSK)

        self.Log("Listing Volume Shadow Copy device: %s.", device_object)
        self.CallClient("ListDirectory",
                        pathspec=path_spec,
                        next_state="ProcessListDirectory")

        self.state.raw_device = aff4.AFF4Object.VFSGRRClient.PathspecToURN(
            path_spec, self.client_id).Dirname()

        self.state.shadows.append(aff4.AFF4Object.VFSGRRClient.PathspecToURN(
            path_spec, self.client_id))

  @flow.StateHandler()
  def ProcessListDirectory(self, responses):
    """Processes the results of the ListDirectory client action.

    Args:
      responses: a flow Responses object.
    """
    if not responses.success:
      raise flow.FlowError("Unable to list directory.")

    for response in responses:
      stat_entry = rdf_client.StatEntry(response)
      filesystem.CreateAFF4Object(stat_entry,
                                  self.client_id,
                                  self.token,
                                  sync=False)
      self.SendReply(stat_entry)

      aff4.FACTORY.Flush()

  @flow.StateHandler()
  def End(self):
    if not self.state.shadows:
      raise flow.FlowError("No Volume Shadow Copies were found.\n"
                           "The volume could have no Volume Shadow Copies "
                           "as Windows versions pre Vista or the Volume "
                           "Shadow Copy Service has been disabled.")
    else:
      self.Notify("ViewObject", self.state.raw_device,
                  "Completed listing Volume Shadow Copies.")
