#!/usr/bin/env python
# Copyright 2011 Google Inc. All Rights Reserved.
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
    self.state.Register("urn", self.client_id.Add(self.state.path))

    # Create the output collection and get it ready.
    output = self.state.output.format(t=time.time(), u=self.state.context.user)
    self.state.output = self.client_id.Add(output)
    self.state.Register("timeline_fd",
                        aff4.FACTORY.Create(self.state.output, "GRRTimeSeries",
                                            token=self.token))
    self.state.timeline_fd.Set(
        self.state.timeline_fd.Schema.DESCRIPTION(
            "Timeline {0}".format(self.state.path)))

    # Main work done in another process.
    self.CallState(next_state="CreateTimeline")

  @flow.StateHandler()
  def CreateTimeline(self):
    """Populate the timeline with the MAC data."""

    attribute = aff4.Attribute.GetAttributeByName("stat")
    filter_obj = data_store.DB.filter.HasPredicateFilter(attribute)

    for row in data_store.DB.Query(
        [attribute], filter_obj,
        subject_prefix=self.state.urn, token=self.token,
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
        self.state.timeline_fd.AddEvent(event)

  @flow.StateHandler()
  def End(self, unused_responses):
    # Flush the time line object.
    self.state.timeline_fd.Close()
    self.Notify("ViewObject", self.state.output,
                "Completed timeline generation.")
