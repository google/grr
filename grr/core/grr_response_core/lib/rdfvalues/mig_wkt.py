#!/usr/bin/env python
"""Provides conversion functions to be used during RDFProtoStruct migration."""

from google.protobuf import timestamp_pb2
from grr_response_core.lib.rdfvalues import wkt as rdf_wkt


def ToProtoTimestamp(rdf: rdf_wkt.Timestamp) -> timestamp_pb2.Timestamp:
  return rdf.AsPrimitiveProto()


def ToRDFTimestamp(proto: timestamp_pb2.Timestamp) -> rdf_wkt.Timestamp:
  return rdf_wkt.Timestamp.FromSerializedBytes(proto.SerializeToString())
