#!/usr/bin/env python
# Copyright 2012 Google Inc.
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.


"""Get running/installed services."""



from grr.lib import aff4
from grr.lib import flow


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

    master = aff4.FACTORY.Create(aff4.RDFURN(self.client_id)
                                 .Add('analysis/Services'),
                                 'ServiceCollection',
                                 token=self.token, mode='rw')

    services = master.Schema.SERVICES()

    self.service_count = len(responses)
    for response in responses:
      services.Append(response)

    master.Set(services)
    master.Close()

  @flow.StateHandler()
  def End(self):
    self.Log('Successfully wrote %d services.', self.service_count)
    urn = aff4.ROOT_URN.Add(self.client_id).Add('analysis/Services')
    self.Notify('ViewObject', urn,
                'Collected %s running services' % self.service_count)
