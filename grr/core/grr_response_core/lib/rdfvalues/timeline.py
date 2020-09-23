#!/usr/bin/env python
# Lint as: python3
"""A module with RDF value wrappers for timeline protobufs."""
from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

import os

from typing import Iterator

from grr_response_core.lib.rdfvalues import structs as rdf_structs
from grr_response_core.lib.util import compatibility
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

    if compatibility.PY2:
      entry.atime_ns = round(stat.st_atime * 1e9)
      entry.mtime_ns = round(stat.st_mtime * 1e9)
      entry.ctime_ns = round(stat.st_ctime * 1e9)
    else:
      # pytype: disable=attribute-error
      entry.atime_ns = stat.st_atime_ns
      entry.mtime_ns = stat.st_mtime_ns
      entry.ctime_ns = stat.st_ctime_ns
      # pytype: enable=attribute-error

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

  @classmethod
  def SerializeStream(
      cls,
      entries: Iterator["TimelineEntry"],
  ) -> Iterator[bytes]:
    return gzchunked.Serialize(_.SerializeToBytes() for _ in entries)

  @classmethod
  def DeserializeStream(
      cls,
      entries: Iterator[bytes],
  ) -> Iterator["TimelineEntry"]:
    return map(cls.FromSerializedBytes, gzchunked.Deserialize(entries))
