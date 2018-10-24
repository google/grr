#!/usr/bin/env python
"""RDFValue instances related to the statistics collection."""
from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

import bisect
import math
import threading

from builtins import zip  # pylint: disable=redefined-builtin

from grr_response_core.lib import utils
from grr_response_core.lib.rdfvalues import client_stats as rdf_client_stats
from grr_response_core.lib.rdfvalues import protodict as rdf_protodict
from grr_response_core.lib.rdfvalues import structs as rdf_structs
from grr_response_proto import analysis_pb2
from grr_response_proto import jobs_pb2


class Distribution(rdf_structs.RDFProtoStruct):
  """Statistics values for events - i.e. things that take time."""

  protobuf = jobs_pb2.Distribution

  def __init__(self, initializer=None, age=None, bins=None):
    if initializer and bins:
      raise ValueError("Either 'initializer' or 'bins' arguments can "
                       "be specified.")

    super(Distribution, self).__init__(initializer=initializer, age=age)
    if bins:
      self.bins = [-float("inf")] + bins
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
    elif self.value_type == self.ValueType.STR:
      return ""
    else:
      return Distribution()


class StatsHistogramBin(rdf_structs.RDFProtoStruct):
  protobuf = jobs_pb2.StatsHistogramBin


class StatsHistogram(rdf_structs.RDFProtoStruct):
  """Histogram with a user-provided set of bins."""
  protobuf = jobs_pb2.StatsHistogram
  rdf_deps = [
      StatsHistogramBin,
  ]

  @classmethod
  def FromBins(cls, bins):
    res = cls()
    for b in bins:
      res.bins.Append(StatsHistogramBin(range_max_value=b))
    return res

  def RegisterValue(self, value):
    """Puts a given value into an appropriate bin."""
    if self.bins:
      for b in self.bins:
        if b.range_max_value > value:
          b.num += 1
          return

      self.bins[-1].num += 1


class RunningStats(rdf_structs.RDFProtoStruct):
  """Class for collecting running stats: mean, stdev and histogram data."""
  protobuf = jobs_pb2.RunningStats
  rdf_deps = [
      StatsHistogram,
  ]

  def RegisterValue(self, value):
    self.num += 1
    self.sum += value
    self.sum_sq += value**2

    self.histogram.RegisterValue(value)

  @property
  def mean(self):
    if self.num == 0:
      return 0
    else:
      return self.sum / self.num

  @property
  def std(self):
    if self.num == 0:
      return 0
    else:
      return math.sqrt(self.sum_sq / self.num - self.mean**2)


class ClientResourcesStats(rdf_structs.RDFProtoStruct):
  """RDF value representing clients' resources usage statistics for hunts."""
  protobuf = jobs_pb2.ClientResourcesStats
  rdf_deps = [
      rdf_client_stats.ClientResources,
      RunningStats,
  ]

  CPU_STATS_BINS = [
      0.1, 0.2, 0.3, 0.4, 0.5, 0.75, 1, 1.5, 2, 2.5, 3, 4, 5, 6, 7, 8, 9, 10,
      15, 20
  ]
  NETWORK_STATS_BINS = [
      16, 32, 64, 128, 256, 512, 1024, 2048, 4096, 8192, 16384, 32768, 65536,
      131072, 262144, 524288, 1048576, 2097152
  ]
  NUM_WORST_PERFORMERS = 10

  def __init__(self, initializer=None, **kwargs):
    super(ClientResourcesStats, self).__init__(
        initializer=initializer, **kwargs)

    self.user_cpu_stats.histogram = StatsHistogram.FromBins(self.CPU_STATS_BINS)
    self.system_cpu_stats.histogram = StatsHistogram.FromBins(
        self.CPU_STATS_BINS)
    self.network_bytes_sent_stats.histogram = StatsHistogram.FromBins(
        self.NETWORK_STATS_BINS)

    self.lock = threading.RLock()

  @utils.Synchronized
  def RegisterResources(self, client_resources):
    """Update stats with info about resources consumed by a single client."""
    self.user_cpu_stats.RegisterValue(client_resources.cpu_usage.user_cpu_time)
    self.system_cpu_stats.RegisterValue(
        client_resources.cpu_usage.system_cpu_time)
    self.network_bytes_sent_stats.RegisterValue(
        client_resources.network_bytes_sent)

    self.worst_performers.Append(client_resources)
    new_worst_performers = sorted(
        self.worst_performers,
        key=lambda s: s.cpu_usage.user_cpu_time + s.cpu_usage.system_cpu_time,
        reverse=True)[:self.NUM_WORST_PERFORMERS]
    self.worst_performers = new_worst_performers


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

  def __nonzero__(self):
    return bool(self.data)

  def __getitem__(self, item):
    return Sample(self.data[item])

  def __iter__(self):
    for x in self.data:
      yield Sample(x)


class GraphFloat(Graph):
  """A Graph that stores sample points as floats."""
  protobuf = analysis_pb2.GraphFloat
  rdf_deps = [
      SampleFloat,
  ]

  def __getitem__(self, item):
    return SampleFloat(self.data[item])

  def __iter__(self):
    for x in self.data:
      yield SampleFloat(x)


class GraphSeries(rdf_protodict.RDFValueArray):
  """A sequence of graphs (e.g. evolving over time)."""
  rdf_type = Graph
