#!/usr/bin/env python
"""Provides conversion functions to be used during RDFProtoStruct migration."""

from grr_response_proto.api import stats_pb2
from grr_response_server.gui.api_plugins import stats


def ToProtoApiListReportsResult(
    rdf: stats.ApiListReportsResult,
) -> stats_pb2.ApiListReportsResult:
  return rdf.AsPrimitiveProto()


def ToRDFApiListReportsResult(
    proto: stats_pb2.ApiListReportsResult,
) -> stats.ApiListReportsResult:
  return stats.ApiListReportsResult.FromSerializedBytes(
      proto.SerializeToString()
  )


def ToProtoApiGetReportArgs(
    rdf: stats.ApiGetReportArgs,
) -> stats_pb2.ApiGetReportArgs:
  return rdf.AsPrimitiveProto()


def ToRDFApiGetReportArgs(
    proto: stats_pb2.ApiGetReportArgs,
) -> stats.ApiGetReportArgs:
  return stats.ApiGetReportArgs.FromSerializedBytes(proto.SerializeToString())


def ToProtoFieldValue(rdf: stats.FieldValue) -> stats_pb2.FieldValue:
  return rdf.AsPrimitiveProto()


def ToRDFFieldValue(proto: stats_pb2.FieldValue) -> stats.FieldValue:
  return stats.FieldValue.FromSerializedBytes(proto.SerializeToString())


def ToProtoApiIncrementCounterMetricArgs(
    rdf: stats.ApiIncrementCounterMetricArgs,
) -> stats_pb2.ApiIncrementCounterMetricArgs:
  return rdf.AsPrimitiveProto()


def ToRDFApiIncrementCounterMetricArgs(
    proto: stats_pb2.ApiIncrementCounterMetricArgs,
) -> stats.ApiIncrementCounterMetricArgs:
  return stats.ApiIncrementCounterMetricArgs.FromSerializedBytes(
      proto.SerializeToString()
  )


def ToProtoApiIncrementCounterMetricResult(
    rdf: stats.ApiIncrementCounterMetricResult,
) -> stats_pb2.ApiIncrementCounterMetricResult:
  return rdf.AsPrimitiveProto()


def ToRDFApiIncrementCounterMetricResult(
    proto: stats_pb2.ApiIncrementCounterMetricResult,
) -> stats.ApiIncrementCounterMetricResult:
  return stats.ApiIncrementCounterMetricResult.FromSerializedBytes(
      proto.SerializeToString()
  )
