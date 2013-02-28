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


"""A simple grep flow."""



import time

from grr.lib import aff4
from grr.lib import flow
from grr.lib import type_info
from grr.lib import utils


class Grep(flow.GRRFlow):
  """This flow greps a file on the client for a pattern or a regex."""

  category = "/Filesystem/"

  XOR_IN_KEY = 37
  XOR_OUT_KEY = 57

  flow_typeinfo = type_info.TypeDescriptorSet(
      type_info.GrepspecType(
          description="The file which will be grepped.",
          name="request"),

      type_info.String(
          description="The output collection.",
          name="output",
          default="analysis/grep/{u}-{t}"),
      )

  @flow.StateHandler(next_state=["StoreResults"])
  def Start(self):
    """Start Grep flow."""
    self.request.xor_in_key = self.XOR_IN_KEY
    self.request.xor_out_key = self.XOR_OUT_KEY

    # For literal matches we xor the search term. In the event we search the
    # memory this stops us matching the GRR client itself.
    if self.request.literal:
      self.request.literal = utils.Xor(self.request.literal,
                                       self.XOR_IN_KEY)

    self.CallClient("Grep", self.request, next_state="StoreResults")

  @flow.StateHandler()
  def StoreResults(self, responses):
    if responses.success:
      output = self.output.format(t=time.time(), u=self.user)
      out_urn = aff4.ROOT_URN.Add(self.client_id).Add(output)

      fd = aff4.FACTORY.Create(out_urn, "GrepResults", mode="rw",
                               token=self.token)

      if self.request.HasField("literal"):
        self.request.literal = utils.Xor(self.request.literal,
                                         self.XOR_IN_KEY)
      fd.Set(fd.Schema.DESCRIPTION("Grep by %s: %s" % (
          self.user, str(self.request))))
      hits = fd.Get(fd.Schema.HITS)

      for response in responses:
        response.data = utils.Xor(response.data,
                                  self.XOR_OUT_KEY)
        response.length = len(response.data)
        hits.Append(response)

      fd.Set(fd.Schema.HITS, hits)
      hit_count = len(hits)
      fd.Close()
      self.Notify("ViewObject", out_urn,
                  u"Grep completed. %d hits" % hit_count)
    else:
      self.Notify("FlowStatus", self.session_id,
                  "Error grepping file: %s." % responses.status)
