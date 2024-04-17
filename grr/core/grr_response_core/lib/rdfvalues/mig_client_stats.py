#!/usr/bin/env python
"""Provides conversion functions to be used during RDFProtoStruct migration."""

from grr_response_core.lib.rdfvalues import client_stats as rdf_client_stats
from grr_response_proto import jobs_pb2


def ToProtoCpuSeconds(rdf: rdf_client_stats.CpuSeconds) -> jobs_pb2.CpuSeconds:
  return rdf.AsPrimitiveProto()


def ToRDFCpuSeconds(proto: jobs_pb2.CpuSeconds) -> rdf_client_stats.CpuSeconds:
  return rdf_client_stats.CpuSeconds.FromSerializedBytes(
      proto.SerializeToString()
  )


def ToProtoCpuSample(rdf: rdf_client_stats.CpuSample) -> jobs_pb2.CpuSample:
  return rdf.AsPrimitiveProto()


def ToRDFCpuSample(proto: jobs_pb2.CpuSample) -> rdf_client_stats.CpuSample:
  return rdf_client_stats.CpuSample.FromSerializedBytes(
      proto.SerializeToString()
  )


def ToProtoIOSample(rdf: rdf_client_stats.IOSample) -> jobs_pb2.IOSample:
  return rdf.AsPrimitiveProto()


def ToRDFIOSample(proto: jobs_pb2.IOSample) -> rdf_client_stats.IOSample:
  return rdf_client_stats.IOSample.FromSerializedBytes(
      proto.SerializeToString()
  )


def ToProtoClientStats(
    rdf: rdf_client_stats.ClientStats,
) -> jobs_pb2.ClientStats:
  return rdf.AsPrimitiveProto()


def ToRDFClientStats(
    proto: jobs_pb2.ClientStats,
) -> rdf_client_stats.ClientStats:
  return rdf_client_stats.ClientStats.FromSerializedBytes(
      proto.SerializeToString()
  )


def ToProtoClientResources(
    rdf: rdf_client_stats.ClientResources,
) -> jobs_pb2.ClientResources:
  return rdf.AsPrimitiveProto()


def ToRDFClientResources(
    proto: jobs_pb2.ClientResources,
) -> rdf_client_stats.ClientResources:
  return rdf_client_stats.ClientResources.FromSerializedBytes(
      proto.SerializeToString()
  )
