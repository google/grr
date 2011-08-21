#!/usr/bin/env python

# Copyright 2011 Google Inc.
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

"""Debugging flows for the console."""


from grr.lib import flow


class ClientAction(flow.GRRFlow):
  """A Simple flow to execute any client action."""

  def __init__(self, client_id, action=None, args=None, **kwargs):
    """Launch the action on the client.

    Args:
       client_id: The client common name we issue the request.
       action: The name of the action on the client.
       args: A request protobuf to provide to the action.
       kwargs: passthrough.
    """
    self.action = action
    self.args = args
    super(ClientAction, self).__init__(client_id, **kwargs)

  @flow.StateHandler(next_state="Print")
  def Start(self):
    self.CallClient(self.action, self.args, next_state="Print")
    self.args = None

  @flow.StateHandler()
  def Print(self, responses):
    self.responses = responses
