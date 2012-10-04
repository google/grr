#!/usr/bin/env python
# Copyright 2010 Google Inc.
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


"""These are process related flows."""


from grr.lib import aff4
from grr.lib import flow


class ListProcesses(flow.GRRFlow):
  """List running processes on a system."""

  category = "/Processes/"

  @flow.StateHandler(next_state=["StoreProcessList"])
  def Start(self):
    """Start processing."""
    self.CallClient("ListProcesses", next_state="StoreProcessList")

  @flow.StateHandler()
  def StoreProcessList(self, responses):
    """This stores the processes."""

    if not responses.success:
      # Check for error, but continue. Errors are common on client.
      raise flow.FlowError("Error during process listing %s" % responses.status)

    urn = aff4.ROOT_URN.Add(self.client_id).Add("processes")
    process_fd = aff4.FACTORY.Create(urn, "ProcessListing", token=self.token)
    plist = process_fd.Schema.PROCESSES()

    proc_count = len(responses)
    for response in responses:
      plist.Append(response)

    process_fd.AddAttribute(plist)
    process_fd.Close()

    self.Notify("ViewObject", urn, "Listed %d Processes" % proc_count)
