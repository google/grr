#!/usr/bin/env python
"""A timeline AFF4 object implementation."""


import heapq
import StringIO
import struct

from grr.lib import aff4
from grr.lib import rdfvalue
from grr.lib.aff4_objects import collects
# AFF4Filter is defined in aff4 but needs this pylint: disable=unused-import
from grr.lib.aff4_objects import filters
# pylint: enable=unused-import
from grr.lib.aff4_objects import standard
from grr.lib.rdfvalues import structs
from grr.proto import analysis_pb2


class Event(structs.RDFProtoStruct):
  protobuf = analysis_pb2.Event


class AFF4Event(aff4.AFF4Object):
  """An AFF4 representation of an Event."""

  class SchemaCls(aff4.AFF4Object.SchemaCls):
    TIMESTAMP = aff4.Attribute("aff4:timeline/timestamp", rdfvalue.RDFDatetime,
                               "The time of this event.", "timestamp")

    # The actual event protobuf
    EVENT = aff4.Attribute("aff4:timeline/event", Event, "The event protobuf",
                           "event")

  def __init__(self, event):
    # This object is virtualized from the event.
    super(AFF4Event, self).__init__(urn=event.subject,
                                    mode="w",
                                    age=aff4.ALL_TIMES)
    self.event = event
    self.Set(self.Schema.TIMESTAMP(event.timestamp))
    self.Set(self.Schema.EVENT(event))

    # Ensure this virtual object is read only.
    self.mode = "r"

  def Flush(self):
    """We are a read only object and we do not write to the data store."""
    pass


class TimelineView(collects.AFF4CollectionView):
  """A timeline view."""


class GRRTimeSeries(standard.VFSDirectory):
  """A time series is a sequence of serialized Event protobufs."""

  _behaviours = set()

  class SchemaCls(standard.VFSDirectory.SchemaCls):
    """Attributes of the timeseries object."""
    # Total number of events here
    SIZE = aff4.AFF4Stream.SchemaCls.SIZE

    START = aff4.Attribute("aff4:timeline/start", rdfvalue.RDFDatetime,
                           "The timestamp of the first event in this series")

    END = aff4.Attribute("aff4:timeline/end", rdfvalue.RDFDatetime,
                         "The timestamp of the last event in this series")

    DESCRIPTION = aff4.Attribute("aff4:description", rdfvalue.RDFString,
                                 "This collection's description", "description")

    TIMELINE = aff4.Attribute("aff4:timeline/view",
                              TimelineView,
                              "The columns that will be shown in the timeline.",
                              default="")

  # Should we write new data on Close()?
  dirty = False
  size = 0

  def Initialize(self):
    super(GRRTimeSeries, self).Initialize()
    if "r" in self.mode:
      self.size = self.Get(self.Schema.SIZE)

    self.heap = []

  def AddEvent(self, event=None, **kw):
    """Add the event protobuf to the series.

    Args:
       event: An optional event object.
       **kw: additional keyword args.
    """
    if event is None:
      event = analysis_pb2.Event(**kw)

    # Push the serialized event proto on the heap to save memory
    heapq.heappush(self.heap, (event.timestamp, event.SerializeToString()))
    self.dirty = True
    self.size += 1

  def __len__(self):
    return self.size

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

    # If the timeline is small enough we buffer it in memory to make quick
    # iteration possible. This is limited to a size of one GB.
    # Note that this is a hack and is supposed to go away soon as we integrate
    # plaso for timelines.
    if storage.size <= 1024 * 1024 * 1024:
      buf = storage.Read(1024 * 1024 * 1024)
      storage = StringIO.StringIO(buf)
      storage.Read = storage.read

    while True:
      try:
        length = struct.unpack("<i", storage.Read(4))[0]
        serialized_event = storage.Read(length)
      except struct.error:
        break

      event = Event(serialized_event)
      event.id = count
      count += 1

      yield event

  def Query(self, filter_string="", filter_obj=None):
    """Implement the Query interface for the time series."""
    # An empty filter string returns all the children.
    if not filter_string:
      return self.OpenChildren(mode=self.mode)

    # Parse the query string
    ast = aff4.AFF4QueryParser(filter_string).Parse()

    # Query our own data store
    filter_obj = ast.Compile(aff4.AFF4Filter)

    return filter_obj.Filter(self.OpenChildren(mode=self.mode))

  def Close(self):
    """Flush the events into the image stream."""
    if not self.dirty:
      return
    storage = aff4.FACTORY.Create(
        self.urn.Add("Storage"),
        aff4.AFF4Image,
        token=self.token)
    storage.SetChunksize(1024 * 1024)

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

    self.Set(self.Schema.SIZE(self.size))
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
