#!/usr/bin/env python
# Copyright 2012 Google Inc. All Rights Reserved.

"""Get running/installed services."""


import time

from grr.lib import aff4
from grr.lib import flow
from grr.lib import rdfvalue
from grr.proto import flows_pb2
from grr.proto import jobs_pb2


class ServiceInformation(rdfvalue.RDFProtoDict):
  protobuf = jobs_pb2.ServiceInformation


class EnumerateRunningServices(flow.GRRFlow):
  """Collect running services.

  Currently only implemented for OS X, for which running launch daemons are
  collected.
  """
  category = "/Services/"
  behaviours = flow.GRRFlow.behaviours + "OSX" + "BASIC"

  @flow.StateHandler(next_state=["StoreServices"])
  def Start(self):
    """Get running services."""
    client = aff4.FACTORY.Open(self.client_id, token=self.token)
    system = client.Get(client.Schema.SYSTEM)

    # if system is None we'll try to run the flow anyway since it might work.
    if system and system != "Darwin":
      raise flow.FlowError("Not implemented: OS X only")

    self.CallClient("EnumerateRunningServices", next_state="StoreServices")

  @flow.StateHandler()
  def StoreServices(self, responses):
    """Store services in ServiceCollection."""
    if not responses.success:
      raise flow.FlowError(str(responses.status))

    services = aff4.FACTORY.Create(self.client_id.Add("analysis/Services"),
                                   "RDFValueCollection", token=self.token,
                                   mode="rw")

    for response in responses:
      services.Add(response)

    services.Close()

    self.service_count = len(services)

  @flow.StateHandler()
  def End(self):
    self.Log("Successfully wrote %d services.", self.service_count)
    urn = self.client_id.Add("analysis/Services")
    self.Notify("ViewObject", urn,
                "Collected %s running services" % self.service_count)


class EnumerateWindowsServicesArgs(rdfvalue.RDFProtoStruct):
  protobuf = flows_pb2.EnumerateWindowsServicesArgs


class EnumerateWindowsServices(flow.GRRFlow):
  """Enumerated windows services and kernel drivers using WMI.

  Optionally also download the binaries automatically.
  """
  category = "/Services/"

  behaviours = flow.GRRFlow.behaviours + "Windows"
  args_type = EnumerateWindowsServicesArgs

  @flow.StateHandler(next_state="StoreServices")
  def Start(self):
    """Setup output collections and issue WMI call."""
    self.state.Register("collection", None)
    if self.args.output:
      # Create the output collection and get it ready.
      output = self.args.output.format(t=time.time(),
                                       p=self.__class__.__name__,
                                       u=self.state.context.user)
      output = self.client_id.Add(output)
      self.state.collection = aff4.FACTORY.Create(
          output, "RDFValueCollection", mode="w", token=self.token)

    self.CallClient("WmiQuery", query="Select * from Win32_SystemDriver",
                    next_state="StoreServices")

  @flow.StateHandler(next_state="ReceiveStat")
  def StoreServices(self, responses):
    """This stores the processes."""
    if not responses.success:
      # If we failed with the wmi query we can not continue.
      raise flow.FlowError("Error during WMI query %s" % responses.status)

    for response in responses:
      service_entry = rdfvalue.ServiceInformation()
      service_entry.wmi_information = response
      service_entry.name = response.GetItem("Name")
      service_entry.description = response.GetItem("Description")
      service_entry.state = response.GetItem("State")

      driver_path = response.GetItem("PathName")
      if driver_path:
        self.CallFlow("FastGetFile", pathspec=rdfvalue.PathSpec(
            path=driver_path, pathtype=self.args.pathtype),
                      next_state="ReceiveStat",
                      request_data=dict(service=service_entry))
      else:
        # We dont know where the service came frome, just write what we have
        # anyway.
        self.state.collection.Add(service_entry)
        self.SendReply(service_entry)

  @flow.StateHandler()
  def ReceiveStat(self, responses):
    if responses.success and responses.First():
      service_entry = responses.request_data["service"]
      service_entry.binary = responses.First()
      self.state.collection.Add(service_entry)
      self.SendReply(service_entry)

  @flow.StateHandler()
  def End(self):
    self.Notify("ViewObject", self.state.collection.urn, "Listed %d Services" %
                len(self.state.collection))

    if self.state.collection:
      self.state.collection.Close()
