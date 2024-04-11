#!/usr/bin/env python
"""Provides conversion functions to be used during RDFProtoStruct migration."""

from grr_response_core.lib.rdfvalues import stats as rdf_stats
from grr_response_proto import analysis_pb2
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


def ToProtoStatsHistogramBin(
    rdf: rdf_stats.StatsHistogramBin,
) -> jobs_pb2.StatsHistogramBin:
  return rdf.AsPrimitiveProto()


def ToRDFStatsHistogramBin(
    proto: jobs_pb2.StatsHistogramBin,
) -> rdf_stats.StatsHistogramBin:
  return rdf_stats.StatsHistogramBin.FromSerializedBytes(
      proto.SerializeToString()
  )


def ToProtoStatsHistogram(
    rdf: rdf_stats.StatsHistogram,
) -> jobs_pb2.StatsHistogram:
  return rdf.AsPrimitiveProto()


def ToRDFStatsHistogram(
    proto: jobs_pb2.StatsHistogram,
) -> rdf_stats.StatsHistogram:
  return rdf_stats.StatsHistogram.FromSerializedBytes(proto.SerializeToString())


def ToProtoRunningStats(rdf: rdf_stats.RunningStats) -> jobs_pb2.RunningStats:
  return rdf.AsPrimitiveProto()


def ToRDFRunningStats(proto: jobs_pb2.RunningStats) -> rdf_stats.RunningStats:
  return rdf_stats.RunningStats.FromSerializedBytes(proto.SerializeToString())


def ToProtoClientResourcesStats(
    rdf: rdf_stats.ClientResourcesStats,
) -> jobs_pb2.ClientResourcesStats:
  return rdf.AsPrimitiveProto()


def ToRDFClientResourcesStats(
    proto: jobs_pb2.ClientResourcesStats,
) -> rdf_stats.ClientResourcesStats:
  return rdf_stats.ClientResourcesStats.FromSerializedBytes(
      proto.SerializeToString()
  )


def ToProtoSample(rdf: rdf_stats.Sample) -> analysis_pb2.Sample:
  return rdf.AsPrimitiveProto()


def ToRDFSample(proto: analysis_pb2.Sample) -> rdf_stats.Sample:
  return rdf_stats.Sample.FromSerializedBytes(proto.SerializeToString())


def ToProtoSampleFloat(rdf: rdf_stats.SampleFloat) -> analysis_pb2.SampleFloat:
  return rdf.AsPrimitiveProto()


def ToRDFSampleFloat(proto: analysis_pb2.SampleFloat) -> rdf_stats.SampleFloat:
  return rdf_stats.SampleFloat.FromSerializedBytes(proto.SerializeToString())


def ToProtoGraph(rdf: rdf_stats.Graph) -> analysis_pb2.Graph:
  return rdf.AsPrimitiveProto()


def ToRDFGraph(proto: analysis_pb2.Graph) -> rdf_stats.Graph:
  return rdf_stats.Graph.FromSerializedBytes(proto.SerializeToString())


def ToProtoClientGraphSeries(
    rdf: rdf_stats.ClientGraphSeries,
) -> analysis_pb2.ClientGraphSeries:
  return rdf.AsPrimitiveProto()


def ToRDFClientGraphSeries(
    proto: analysis_pb2.ClientGraphSeries,
) -> rdf_stats.ClientGraphSeries:
  return rdf_stats.ClientGraphSeries.FromSerializedBytes(
      proto.SerializeToString()
  )
