#!/usr/bin/env python
"""Provides conversion functions to be used during RDFProtoStruct migration."""

from grr_response_proto.api import timeline_pb2
from grr_response_server.gui.api_plugins import timeline


def ToProtoApiTimelineBodyOpts(
    rdf: timeline.ApiTimelineBodyOpts,
) -> timeline_pb2.ApiTimelineBodyOpts:
  return rdf.AsPrimitiveProto()


def ToRDFApiTimelineBodyOpts(
    proto: timeline_pb2.ApiTimelineBodyOpts,
) -> timeline.ApiTimelineBodyOpts:
  return timeline.ApiTimelineBodyOpts.FromSerializedBytes(
      proto.SerializeToString()
  )


def ToProtoApiGetCollectedTimelineArgs(
    rdf: timeline.ApiGetCollectedTimelineArgs,
) -> timeline_pb2.ApiGetCollectedTimelineArgs:
  return rdf.AsPrimitiveProto()


def ToRDFApiGetCollectedTimelineArgs(
    proto: timeline_pb2.ApiGetCollectedTimelineArgs,
) -> timeline.ApiGetCollectedTimelineArgs:
  return timeline.ApiGetCollectedTimelineArgs.FromSerializedBytes(
      proto.SerializeToString()
  )


def ToProtoApiGetCollectedHuntTimelinesArgs(
    rdf: timeline.ApiGetCollectedHuntTimelinesArgs,
) -> timeline_pb2.ApiGetCollectedHuntTimelinesArgs:
  return rdf.AsPrimitiveProto()


def ToRDFApiGetCollectedHuntTimelinesArgs(
    proto: timeline_pb2.ApiGetCollectedHuntTimelinesArgs,
) -> timeline.ApiGetCollectedHuntTimelinesArgs:
  return timeline.ApiGetCollectedHuntTimelinesArgs.FromSerializedBytes(
      proto.SerializeToString()
  )
