#!/usr/bin/env python
"""Provides conversion functions to be used during RDFProtoStruct migration."""

from grr_response_core.lib.rdfvalues import stats as rdf_stats
from grr_response_proto import jobs_pb2


def ToProtoDistribution(rdf: rdf_stats.Distribution) -> jobs_pb2.Distribution:
  return rdf.AsPrimitiveProto()


def ToRDFDistribution(proto: jobs_pb2.Distribution) -> rdf_stats.Distribution:
  return rdf_stats.Distribution.FromSerializedBytes(proto.SerializeToString())


def ToProtoMetricFieldDefinition(
    rdf: rdf_stats.MetricFieldDefinition,
) -> jobs_pb2.MetricFieldDefinition:
  return rdf.AsPrimitiveProto()


def ToRDFMetricFieldDefinition(
    proto: jobs_pb2.MetricFieldDefinition,
) -> rdf_stats.MetricFieldDefinition:
  return rdf_stats.MetricFieldDefinition.FromSerializedBytes(
      proto.SerializeToString()
  )


def ToProtoMetricMetadata(
    rdf: rdf_stats.MetricMetadata,
) -> jobs_pb2.MetricMetadata:
  return rdf.AsPrimitiveProto()


def ToRDFMetricMetadata(
    proto: jobs_pb2.MetricMetadata,
) -> rdf_stats.MetricMetadata:
  return rdf_stats.MetricMetadata.FromSerializedBytes(proto.SerializeToString())

