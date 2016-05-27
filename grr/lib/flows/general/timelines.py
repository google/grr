#!/usr/bin/env python
# Copyright 2011 Google Inc. All Rights Reserved.
"""Calculates timelines from the client."""
from grr.lib import aff4
from grr.lib import data_store
from grr.lib import flow
from grr.lib import utils
from grr.lib.aff4_objects import timeline
from grr.lib.rdfvalues import client as rdf_client
from grr.lib.rdfvalues import structs as rdf_structs
from grr.proto import flows_pb2


class MACTimesArgs(rdf_structs.RDFProtoStruct):
  protobuf = flows_pb2.MACTimesArgs


class MACTimes(flow.GRRFlow):
  """Calculate the MAC times from objects in the VFS."""

  category = "/Timeline/"
  behaviours = flow.GRRFlow.behaviours + "BASIC"
  args_type = MACTimesArgs

  @flow.StateHandler(next_state="CreateTimeline")
  def Start(self):
    """This could take a while so we just schedule for the worker."""
    self.state.Register("urn", self.client_id.Add(self.args.path))
    if self.runner.output is not None:
      self.runner.output = aff4.FACTORY.Create(self.runner.output.urn,
                                               timeline.GRRTimeSeries,
                                               token=self.token)

      self.runner.output.Set(self.runner.output.Schema.DESCRIPTION(
          "Timeline {0}".format(self.args.path)))

    # Main work done in another process.
    self.CallState(next_state="CreateTimeline")

  def _ListVFSChildren(self, fds):
    """Recursively iterate over all children of the AFF4Objects in fds."""
    child_urns = []
    while 1:
      direct_children = []
      for _, children in aff4.FACTORY.MultiListChildren(fds, token=self.token):
        direct_children.extend(children)

      # Break if there are no children at this level.
      if not direct_children:
        break

      child_urns.extend(direct_children)

      # Now get the next lower level of children.
      fds = direct_children

    return child_urns

  @flow.StateHandler()
  def CreateTimeline(self):
    """Populate the timeline with the MAC data."""
    child_urns = self._ListVFSChildren([self.state.urn])
    attribute = aff4.Attribute.GetAttributeByName("stat")

    for subject, values in data_store.DB.MultiResolvePrefix(child_urns,
                                                            attribute.predicate,
                                                            token=self.token,
                                                            limit=10000000):
      for _, serialized, _ in values:
        stat = rdf_client.StatEntry(serialized)
        event = timeline.Event(source=utils.SmartUnicode(subject), stat=stat)

        # Add a new event for each MAC time if it exists.
        for c in "mac":
          timestamp = getattr(stat, "st_%stime" % c)
          if timestamp is not None:
            event.timestamp = timestamp * 1000000
            event.type = "file.%stime" % c

            # We are taking about the file which is a direct child of the
            # source.
            event.subject = utils.SmartUnicode(subject)
            if self.runner.output is not None:
              self.runner.output.AddEvent(event)
