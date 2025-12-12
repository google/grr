#!/usr/bin/env python
"""A module with RDF value wrappers for timeline protobufs."""

from collections.abc import Iterable, Iterator
import os

from grr_response_core.lib.rdfvalues import structs as rdf_structs
from grr_response_core.lib.util import gzchunked
from grr_response_core.lib.util import statx
from grr_response_proto import timeline_pb2


class TimelineArgs(rdf_structs.RDFProtoStruct):
  """An RDF wrapper class for the timeline arguments message."""

  protobuf = timeline_pb2.TimelineArgs
  rdf_deps = []


class TimelineResult(rdf_structs.RDFProtoStruct):
  """An RDF wrapper class for the timeline result message."""

  protobuf = timeline_pb2.TimelineResult
  rdf_deps = []


class TimelineEntry(rdf_structs.RDFProtoStruct):
  """An RDF wrapper class for the timeline entry message."""

  protobuf = timeline_pb2.TimelineEntry
  rdf_deps = []

  @classmethod
  def FromStat(cls, path: bytes, stat: os.stat_result) -> "TimelineEntry":
    entry = cls()
    entry.path = path

    entry.mode = stat.st_mode
    entry.size = stat.st_size

    entry.dev = stat.st_dev
    entry.ino = stat.st_ino

    entry.uid = stat.st_uid
    entry.gid = stat.st_gid

    entry.atime_ns = stat.st_atime_ns
    entry.mtime_ns = stat.st_mtime_ns
    entry.ctime_ns = stat.st_ctime_ns

    return entry

  @classmethod
  def FromStatx(cls, path: bytes, stat: statx.Result) -> "TimelineEntry":
    entry = cls()
    entry.path = path

    entry.mode = stat.mode
    entry.size = stat.size

    entry.dev = stat.dev
    entry.ino = stat.ino

    entry.uid = stat.uid
    entry.gid = stat.gid

    entry.attributes = stat.attributes

    entry.atime_ns = stat.atime_ns
    entry.btime_ns = stat.btime_ns
    entry.mtime_ns = stat.mtime_ns
    entry.ctime_ns = stat.ctime_ns

    return entry


def SerializeTimelineEntryStream(
    entries: Iterable[timeline_pb2.TimelineEntry],
) -> Iterator[bytes]:
  return gzchunked.Serialize(entry.SerializeToString() for entry in entries)


def DeserializeTimelineEntryStream(
    entries: Iterator[bytes],
) -> Iterator[timeline_pb2.TimelineEntry]:
  for entry in gzchunked.Deserialize(entries):
    parsed_entry = timeline_pb2.TimelineEntry()
    parsed_entry.ParseFromString(entry)
    yield parsed_entry


class TimelineProgress(rdf_structs.RDFProtoStruct):
  """An RDF wrapper class for the timeline progress message."""

  protobuf = timeline_pb2.TimelineProgress
  rdf_deps = []
