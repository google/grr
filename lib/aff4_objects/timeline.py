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

"""A timeline AFF4 object implementation."""


import heapq
import struct

from grr.lib import aff4
from grr.lib.aff4_objects import aff4_grr
from grr.lib.aff4_objects import standard
from grr.proto import analysis_pb2


class RDFEvent(aff4.RDFProto):
  _proto = analysis_pb2.Event

  rdf_map = dict(timestamp=aff4.RDFDatetime,
                 stat=standard.StatEntry)


class AFF4Event(aff4.AFF4Object):
  """An AFF4 representation of an Event."""

  class SchemaCls(aff4.AFF4Object.SchemaCls):
    TIMESTAMP = aff4.Attribute("aff4:timeline/timestamp", aff4.RDFDatetime,
                               "The time of this event.", "timestamp")

    # The actual event protobuf
    EVENT = aff4.Attribute("aff4:timeline/event", RDFEvent,
                           "The event protobuf", "event")

  def __init__(self, event):
    # This object is virtualized from the event.
    super(AFF4Event, self).__init__(urn=event.subject, mode="w",
                                    age=aff4.ALL_TIMES)
    self.event = event
    self.Set(self.Schema.TIMESTAMP(event.timestamp))
    self.Set(self.Schema.EVENT(event))

    # Ensure this virtual object is read only.
    self.mode = "r"

  def Flush(self):
    """We are a read only object and we do not write to the data store."""
    pass


class TimelineView(aff4_grr.View):
  """A timeline view."""


class GRRTimeSeries(standard.VFSDirectory):
  """A time series is a sequence of serialized Event protobufs."""

  _behaviours = set()

  class SchemaCls(standard.VFSDirectory.SchemaCls):
    """Attributes of the timeseries object."""
    # Total number of events here
    SIZE = aff4.AFF4Stream.SchemaCls.SIZE

    START = aff4.Attribute("aff4:timeline/start", aff4.RDFDatetime,
                           "The timestamp of the first event in this series")

    END = aff4.Attribute("aff4:timeline/end", aff4.RDFDatetime,
                         "The timestamp of the last event in this series")

    DESCRIPTION = aff4.Attribute("aff4:description", aff4.RDFString,
                                 "This collection's description", "description")

    TIMELINE = aff4.Attribute("aff4:timeline/view", TimelineView,
                              "The columns that will be shown in the timeline.",
                              default="")

  # Should we write new data on Close()?
  dirty = False

  def Initialize(self):
    super(GRRTimeSeries, self).Initialize()
    self.heap = []

  def AddEvent(self, event=None, **kw):
    """Add the event protobuf to the series.

    Args:
       event: An optional event object.
    """
    if event is None:
      event = analysis_pb2.Event(**kw)

    # Push the serialized event proto on the heap to save memory
    heapq.heappush(self.heap, (event.timestamp, event.SerializeToString()))
    self.dirty = True

  # Implement an iterated interface to the events
  def __iter__(self):
    """Iterate over all event protobufs.

    Yields:
      event protobufs in increasing time order.
    Raises:
      RuntimeError: if we are in write mode.
    """
    if self.mode == "w":
      raise RuntimeError("Can not read when in write mode.")

    count = 0
    storage = aff4.FACTORY.Open(self.urn.Add("Storage"), token=self.token)
    while True:
      try:
        length = struct.unpack("<i", storage.Read(4))[0]
        serialized_event = storage.Read(length)
      except struct.error:
        break

      event = analysis_pb2.Event()
      event.ParseFromString(serialized_event)
      event.id = count
      count += 1

      yield event

  def Query(self, filter_string="", filter_obj=None):
    # An empty filter string returns all the children.
    if not filter_string: return self.OpenChildren(mode=self.mode)

    # Parse the query string
    ast = aff4.AFF4QueryParser(filter_string).Parse()

    # Query our own data store
    filter_obj = ast.Compile(aff4.AFF4Filter)

    return filter_obj.Filter(self.OpenChildren(mode=self.mode))

  def Close(self):
    """Flush the events into the image stream."""
    if not self.dirty: return
    storage = aff4.FACTORY.Create(self.urn.Add("Storage"), "AFF4Image",
                                  token=self.token)
    storage.Truncate(0)

    if self.heap:
      first = last = self.heap[0][0]
      # Note our first event and size
      self.Set(self.Schema.SIZE(len(self.heap)))
      self.Set(self.Schema.START(first))

      while self.heap:
        # This pulls the smallest time from the heap
        last, serialized_event = heapq.heappop(self.heap)

        # Write the length and then the data
        storage.Write(struct.pack("<i", len(serialized_event)))
        storage.Write(serialized_event)

      # Note our last event and size
      self.Set(self.Schema.END(last))

      # We are done - flush and close the file.
      storage.Close()

    super(GRRTimeSeries, self).Close()

  def OpenChildren(self, children=None, mode="r"):
    if mode != "r":
      raise IOError("Events are always read only.")

    for event in self:
      result = AFF4Event(event)
      # Allow users to filter events
      if children is not None and str(result.urn) not in children:
        continue

      yield result
