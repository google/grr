#!/usr/bin/env python
"""A module defining timeline-related utility functions."""

from collections.abc import Iterator

from grr_response_core.lib.util import gzchunked
from grr_response_proto import timeline_pb2


def _ParseTimelineEntryProto(bstr: bytes) -> timeline_pb2.TimelineEntry:
  r = timeline_pb2.TimelineEntry()
  r.ParseFromString(bstr)
  return r


def DeserializeTimelineEntryProtoStream(
    entries: Iterator[bytes],
) -> Iterator[timeline_pb2.TimelineEntry]:
  """Deserializes given gzchunked stream chunks into TimelineEntry protos."""
  return map(_ParseTimelineEntryProto, gzchunked.Deserialize(entries))
