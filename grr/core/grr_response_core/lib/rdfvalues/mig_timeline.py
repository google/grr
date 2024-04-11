#!/usr/bin/env python
"""Provides conversion functions to be used during RDFProtoStruct migration."""

from grr_response_core.lib.rdfvalues import timeline as rdf_timeline
from grr_response_proto import timeline_pb2


def ToProtoTimelineArgs(
    rdf: rdf_timeline.TimelineArgs,
) -> timeline_pb2.TimelineArgs:
  return rdf.AsPrimitiveProto()


def ToRDFTimelineArgs(
    proto: timeline_pb2.TimelineArgs,
) -> rdf_timeline.TimelineArgs:
  return rdf_timeline.TimelineArgs.FromSerializedBytes(
      proto.SerializeToString()
  )


def ToProtoTimelineResult(
    rdf: rdf_timeline.TimelineResult,
) -> timeline_pb2.TimelineResult:
  return rdf.AsPrimitiveProto()


def ToRDFTimelineResult(
    proto: timeline_pb2.TimelineResult,
) -> rdf_timeline.TimelineResult:
  return rdf_timeline.TimelineResult.FromSerializedBytes(
      proto.SerializeToString()
  )


def ToProtoTimelineEntry(
    rdf: rdf_timeline.TimelineEntry,
) -> timeline_pb2.TimelineEntry:
  return rdf.AsPrimitiveProto()


def ToRDFTimelineEntry(
    proto: timeline_pb2.TimelineEntry,
) -> rdf_timeline.TimelineEntry:
  return rdf_timeline.TimelineEntry.FromSerializedBytes(
      proto.SerializeToString()
  )


def ToProtoTimelineProgress(
    rdf: rdf_timeline.TimelineProgress,
) -> timeline_pb2.TimelineProgress:
  return rdf.AsPrimitiveProto()


def ToRDFTimelineProgress(
    proto: timeline_pb2.TimelineProgress,
) -> rdf_timeline.TimelineProgress:
  return rdf_timeline.TimelineProgress.FromSerializedBytes(
      proto.SerializeToString()
  )
