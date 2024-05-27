#!/usr/bin/env python
"""RDFValue instances related to the statistics collection."""

import bisect

from grr_response_core.lib.rdfvalues import client_stats as rdf_client_stats
from grr_response_core.lib.rdfvalues import structs as rdf_structs
from grr_response_proto import analysis_pb2
from grr_response_proto import jobs_pb2


class Distribution(rdf_structs.RDFProtoStruct):
  """Statistics values for events - i.e. things that take time."""

  protobuf = jobs_pb2.Distribution

  def __init__(self, initializer=None, bins=None):
    if initializer and bins:
      raise ValueError(
          "Either 'initializer' or 'bins' arguments can be specified."
      )

    super().__init__(initializer=initializer)

    if bins:
      self.bins = [-float("inf")] + bins
    else:
      self.bins = []

    self.heights = [0] * len(self.bins)

  def Record(self, value):
    """Records given value."""
    self.sum += value
    self.count += 1

    pos = bisect.bisect(self.bins, value) - 1
    if pos < 0:
      pos = 0
    elif pos == len(self.bins):
      pos = len(self.bins) - 1

    self.heights[pos] += 1

  @property
  def bins_heights(self):
    return dict(zip(self.bins, self.heights))


class MetricFieldDefinition(rdf_structs.RDFProtoStruct):
  """Metric field definition."""

  protobuf = jobs_pb2.MetricFieldDefinition


class MetricMetadata(rdf_structs.RDFProtoStruct):
  """Metric metadata for a particular metric."""

  protobuf = jobs_pb2.MetricMetadata
  rdf_deps = [
      MetricFieldDefinition,
  ]

  def DefaultValue(self):
    if self.value_type == self.ValueType.INT:
      return 0
    elif self.value_type == self.ValueType.FLOAT:
      return 0.0
    elif self.value_type == self.ValueType.DISTRIBUTION:
      return Distribution()
    else:
      raise ValueError("Illegal value type: {!r}".format(self.value_type))


class StatsHistogramBin(rdf_structs.RDFProtoStruct):
  protobuf = jobs_pb2.StatsHistogramBin


class StatsHistogram(rdf_structs.RDFProtoStruct):
  """Histogram with a user-provided set of bins."""

  protobuf = jobs_pb2.StatsHistogram
  rdf_deps = [
      StatsHistogramBin,
  ]


class RunningStats(rdf_structs.RDFProtoStruct):
  """Class for collecting running stats: mean, stddev and histogram data."""

  protobuf = jobs_pb2.RunningStats
  rdf_deps = [
      StatsHistogram,
  ]


class ClientResourcesStats(rdf_structs.RDFProtoStruct):
  """RDF value representing clients' resources usage statistics for hunts."""

  protobuf = jobs_pb2.ClientResourcesStats
  rdf_deps = [
      rdf_client_stats.ClientResources,
      RunningStats,
  ]


class Sample(rdf_structs.RDFProtoStruct):
  """A Graph sample is a single data point."""

  protobuf = analysis_pb2.Sample


class SampleFloat(rdf_structs.RDFProtoStruct):
  """A Graph float data point."""

  protobuf = analysis_pb2.SampleFloat


class Graph(rdf_structs.RDFProtoStruct):
  """A Graph is a collection of sample points."""

  protobuf = analysis_pb2.Graph
  rdf_deps = [
      Sample,
  ]

  def Append(self, **kwargs):
    self.data.Append(**kwargs)

  def __len__(self):
    return len(self.data)

  def __bool__(self):
    return bool(self.data)

  def __getitem__(self, item):
    return Sample(self.data[item])

  def __iter__(self):
    for x in self.data:
      yield Sample(x)


class ClientGraphSeries(rdf_structs.RDFProtoStruct):
  """A collection of graphs for a single client-report type."""

  protobuf = analysis_pb2.ClientGraphSeries
  rdf_deps = [
      Graph,
  ]
