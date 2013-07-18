#!/usr/bin/env python
"""RDFValue instances related to the statistics collection."""


import math
import threading

from grr.lib import rdfvalue
from grr.lib import utils
from grr.proto import jobs_pb2


class StatsHistogramBin(rdfvalue.RDFProtoStruct):
  protobuf = jobs_pb2.StatsHistogramBin


class StatsHistogram(rdfvalue.RDFProtoStruct):
  """Histogram with a user-provided set of bins."""
  protobuf = jobs_pb2.StatsHistogram

  def __init__(self, initializer=None, **kwargs):
    if isinstance(initializer, (list, tuple)):
      super(StatsHistogram, self).__init__(initializer=None, **kwargs)
      for histogram_bin in initializer:
        self.bins.Append(StatsHistogramBin(range_max_value=histogram_bin))
    else:
      super(StatsHistogram, self).__init__(initializer=initializer, **kwargs)

  def RegisterValue(self, value):
    """Puts a given value into an appropriate bin."""
    if self.bins:
      for b in self.bins:
        if b.range_max_value > value:
          b.num += 1
          return

      self.bins[-1].num += 1


class RunningStats(rdfvalue.RDFProtoStruct):
  """Class for collecting running stats: mean, stdev and histogram data."""
  protobuf = jobs_pb2.RunningStats

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
      return self.sum / float(self.num)

  @property
  def std(self):
    if self.num == 0:
      return 0
    else:
      return math.sqrt(self.sum_sq / float(self.num) - self.mean**2)


class ClientResourcesStats(rdfvalue.RDFProtoStruct):
  """RDF value representing clients' resources usage statistics for hunts."""
  protobuf = jobs_pb2.ClientResourcesStats

  CPU_STATS_BINS = [0.1, 0.2, 0.3, 0.4, 0.5, 0.75, 1, 1.5, 2, 2.5, 3, 4, 5,
                    6, 7, 8, 9, 10, 15, 20]
  NETWORK_STATS_BINS = [16, 32, 64, 128, 256, 512, 1024, 2048, 4096, 8192,
                        16384, 32768, 65536, 131072, 262144, 524288, 1048576,
                        2097152]
  NUM_WORST_PERFORMERS = 10

  def __init__(self, initializer=None, **kwargs):
    super(ClientResourcesStats, self).__init__(initializer=initializer,
                                               **kwargs)

    self.user_cpu_stats.histogram = self.CPU_STATS_BINS
    self.system_cpu_stats.histogram = self.CPU_STATS_BINS
    self.network_bytes_sent_stats.histogram = self.NETWORK_STATS_BINS

    self.lock = threading.RLock()

  @utils.Synchronized
  def __getstate__(self):
    to_pickle = self.__dict__.copy()
    to_pickle["lock"] = None
    return to_pickle

  def __setstate__(self, state):
    self.__dict__ = state
    self.lock = threading.RLock()

  @utils.Synchronized
  def RegisterResources(self, client_resources):
    """Update stats with info about resources consumed by a single client."""
    self.user_cpu_stats.RegisterValue(
        client_resources.cpu_usage.user_cpu_time)
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
