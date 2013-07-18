#!/usr/bin/env python
# Copyright 2012 Google Inc. All Rights Reserved.

"""Get running/installed services."""



from grr.lib import aff4
from grr.lib import flow


class EnumerateRunningServices(flow.GRRFlow):
  """Collect running services.

  Currently only implemented for OS X, for which running launch daemons are
  collected.
  """
  category = "/Services/"

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
