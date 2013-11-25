#!/usr/bin/env python
# Copyright 2012 Google Inc. All Rights Reserved.

"""Get running/installed services."""


from grr.lib import aff4
from grr.lib import flow
from grr.lib import rdfvalue
from grr.proto import flows_pb2
from grr.proto import jobs_pb2


class ServiceInformation(rdfvalue.RDFProtoStruct):
  protobuf = jobs_pb2.ServiceInformation


class EnumerateServicesArgs(rdfvalue.RDFProtoStruct):
  protobuf = flows_pb2.EnumerateServicesArgs


# TODO(user): Mostly replaced with WindowsDrivers artifact.  Remove this
# flow once we can also do the binary download with artifacts.
class EnumerateServices(flow.GRRFlow):
  """Enumerated windows services and kernel drivers using WMI.

  Optionally also download the binaries automatically.
  """
  category = "/Services/"

  behaviours = flow.GRRFlow.behaviours + "Windows"
  args_type = EnumerateServicesArgs

  @flow.StateHandler(next_state=["StoreServices", "StoreWMIServices"])
  def Start(self):
    """Setup output collections and issue WMI call."""
    client = aff4.FACTORY.Open(self.client_id, token=self.token)
    system = client.Get(client.Schema.SYSTEM)

    # if system is None we'll try to run the flow anyway since it might work.
    if system == "Windows":
      self.CallClient("WmiQuery", query="Select * from Win32_SystemDriver",
                      next_state="StoreWMIServices")
    else:
      self.CallClient("EnumerateRunningServices", next_state="StoreServices")

  @flow.StateHandler()
  def StoreServices(self, responses):
    """Store services in ServiceCollection."""
    if not responses.success:
      raise flow.FlowError(str(responses.status))

    for response in responses:
      self.SendReply(response)

  @flow.StateHandler(next_state="End")
  def StoreWMIServices(self, responses):
    """This stores the processes."""
    if not responses.success:
      # If we failed with the wmi query we can not continue.
      raise flow.FlowError("Error during WMI query %s" % responses.status)

    paths = []

    for response in responses:
      service_entry = rdfvalue.ServiceInformation()
      service_entry.wmi_information = response
      service_entry.name = response.GetItem("Name")
      service_entry.description = response.GetItem("Description")
      service_entry.state = response.GetItem("State")

      driver_path = response.GetItem("PathName")
      if driver_path:
        paths.append(driver_path)

      self.SendReply(service_entry)

    if paths:
      self.CallFlow("FetchFiles", paths=paths, pathtype=self.args.pathtype,
                    next_state="End")
