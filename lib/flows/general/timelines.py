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

"""Calculates timelines from the client."""
import time

from grr.lib import aff4
from grr.lib import data_store
from grr.lib import flow
from grr.lib import rdfvalue
from grr.lib import type_info
from grr.lib import utils


class MACTimes(flow.GRRFlow):
  """Calculate the MAC times from objects in the VFS."""

  category = "/Timeline/"

  flow_typeinfo = type_info.TypeDescriptorSet(
      type_info.String(
          description="A path relative to the client to put the output.",
          name="output",
          default="analysis/timeline/{u}-{t}"),

      type_info.String(
          description="An AFF path (relative to the client area of the VFS).",
          name="path",
          default="/fs/"),
      )

  @flow.StateHandler(next_state="CreateTimeline")
  def Start(self):
    """This could take a while so we just schedule for the worker."""
    self.urn = aff4.ROOT_URN.Add(self.client_id).Add(self.path)

    # Create the output collection and get it ready.
    output = self.output.format(t=time.time(), u=self.user)
    self.output = aff4.ROOT_URN.Add(self.client_id).Add(output)
    self.timeline_fd = aff4.FACTORY.Create(self.output, "GRRTimeSeries",
                                           token=self.token)
    self.timeline_fd.Set(
        self.timeline_fd.Schema.DESCRIPTION("Timeline {0}".format(self.path)))

    # Main work done in another process.
    self.CallState(next_state="CreateTimeline")

  @flow.StateHandler()
  def CreateTimeline(self):
    """Populate the timeline with the MAC data."""

    attribute = aff4.Attribute.GetAttributeByName("stat")
    filter_obj = data_store.DB.filter.HasPredicateFilter(attribute)

    for row in data_store.DB.Query([attribute], filter_obj,
                                   subject_prefix=self.urn, token=self.token,
                                   limit=10000000):

      # The source of this event is the directory inode.
      source = rdfvalue.RDFURN(row["subject"][0][0])

      stat = rdfvalue.StatEntry(row[str(attribute)][0][0])
      event = rdfvalue.Event(source=utils.SmartUnicode(source),
                             stat=stat)

        # Add a new event for each MAC time.
      for c in "mac":
        event.timestamp = getattr(stat, "st_%stime" % c) * 1000000
        event.type = "file.%stime" % c

        # We are taking about the file which is a direct child of the source.
        event.subject = utils.SmartUnicode(source)
        self.timeline_fd.AddEvent(event)

  @flow.StateHandler()
  def End(self, unused_responses):
    # Flush the time line object.
    self.timeline_fd.Close()
    self.Notify("ViewObject", self.output,
                "Completed timeline generation.")
