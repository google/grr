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
from grr.lib import utils
from grr.proto import analysis_pb2
from grr.proto import jobs_pb2


class MACTimes(flow.GRRFlow):
  """Calculate the MAC times from objects in the VFS."""

  category = "/Timeline/"

  # Maximum depth of recursion.
  MAX_DEPTH = 5

  def __init__(self, path="/", output="analysis/timeline/{u}-{t}",
               **kwargs):
    """This flow builds a timeline for the filesystem on the client.

    Currently only VFSDirectory objects are supported.

    Args:
      path: An AFF4 path (relative to the client area of the VFS).
      output: The path to the output container for this find. Will be created
          under the client. supports format variables {u} and {t} for user and
          time. E.g. /analysis/timeline/{u}-{t}.
    """
    flow.GRRFlow.__init__(self, **kwargs)

    self.urn = aff4.ROOT_URN.Add(self.client_id).Add(path)

    # Create the output collection and get it ready.
    output = output.format(t=time.time(), u=self.user)
    self.output = aff4.ROOT_URN.Add(self.client_id).Add(output)
    self.timeline_fd = aff4.FACTORY.Create(self.output, "GRRTimeSeries",
                                           token=self.token)
    self.timeline_fd.Set(
        self.timeline_fd.Schema.DESCRIPTION("Timeline {0}".format(path)))

  @flow.StateHandler(next_state="CreateTimeline")
  def Start(self):
    """This could take a while so we just schedule for the worker."""

    # Main work done in another process.
    self.CallState(next_state="CreateTimeline")

  @flow.StateHandler()
  def CreateTimeline(self):
    """Populate the timeline with the MAC data."""

    attribute = aff4.Attribute.GetAttributeByName("stat")
    filter_obj = data_store.DB.filter.HasPredicateFilter(attribute)

    for row in data_store.DB.Query([attribute], filter_obj,
                                   subject_prefix=self.urn, token=self.token,
                                   limit=10000):

      # The source of this event is the directory inode.
      source = aff4.RDFURN(row["subject"][0])

      stat = jobs_pb2.StatResponse()
      stat.ParseFromString(row[str(attribute)][0])
      event = analysis_pb2.Event(source=utils.SmartUnicode(source))
      event.stat.MergeFrom(stat)

        # Add a new event for each MAC time.
      for c in "mac":
        event.timestamp = getattr(stat, "st_%stime" % c) * 1000000
        event.type = "file.%stime" % c

        # We are taking about the file which is a direct child of the source.
        event.subject = utils.SmartUnicode(source)
        self.timeline_fd.AddEvent(event)

  def End(self):
    # Flush the time line object.
    self.timeline_fd.Close()
    super(MACTimes, self).End()
