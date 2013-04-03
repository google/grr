#!/usr/bin/env python
# Copyright 2012 Google Inc. All Rights Reserved.

"""Get running/installed services."""



from grr.lib import aff4
from grr.lib import flow
from grr.lib import rdfvalue


class EnumerateRunningServices(flow.GRRFlow):
  """Collect running services."""

  category = '/Services/'

  @flow.StateHandler(next_state=['StoreServices'])
  def Start(self):
    """Get running services."""

    self.CallClient('EnumerateRunningServices',
                    next_state='StoreServices')

  @flow.StateHandler()
  def StoreServices(self, responses):
    """Store services in ServiceCollection."""
    services = aff4.FACTORY.Create(
        rdfvalue.RDFURN(self.client_id).Add('analysis/Services'),
        'RDFValueCollection', token=self.token, mode='rw')

    for response in responses:
      services.Add(response)

    services.Close()

    self.service_count = len(services)

  @flow.StateHandler()
  def End(self):
    self.Log('Successfully wrote %d services.', self.service_count)
    urn = aff4.ROOT_URN.Add(self.client_id).Add('analysis/Services')
    self.Notify('ViewObject', urn,
                'Collected %s running services' % self.service_count)
