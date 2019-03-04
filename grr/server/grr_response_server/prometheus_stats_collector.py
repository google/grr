#!/usr/bin/env python
"""Prometheus-based statistics collection."""

from __future__ import absolute_import
from __future__ import division

from __future__ import unicode_literals

import collections
import threading

import prometheus_client
import six
from typing import Dict, Text

from grr_response_core.lib import utils
from grr_response_core.lib.rdfvalues import stats as rdf_stats
from grr_response_core.lib.util import compatibility
from grr_response_core.lib.util import precondition
from grr_response_core.stats import stats_collector
from grr_response_core.stats import stats_utils


class _Metric(object):
  """A Metric that wraps a prometheus_client metrics.

  Attributes:
    metadata: An rdf_stats.MetricMetadata instance describing this _Metric.
    fields: A list of (field name, field type) tuples, defining the dimensions
      of this metric.
    metric: The underlying metric, an instance of prometheus_client.Counter,
      Gauge, or Histogram.
  """

  def __init__(self, metadata,
               registry):
    """Instantiates a new _Metric.

    Args:
      metadata: An rdf_stats.MetricMetadata instance describing this _Metric.
      registry: A prometheus_client.Registry instance.

    Raises:
      ValueError: metadata contains an unknown metric_type.
    """
    self.metadata = metadata
    self.fields = stats_utils.FieldDefinitionTuplesFromProtos(
        metadata.fields_defs)
    field_names = [name for name, _ in self.fields]

    if metadata.metric_type == rdf_stats.MetricMetadata.MetricType.COUNTER:
      self.metric = prometheus_client.Counter(
          metadata.varname,
          metadata.docstring,
          labelnames=field_names,
          registry=registry)
    elif metadata.metric_type == rdf_stats.MetricMetadata.MetricType.EVENT:
      bins = metadata.bins or [
          0.0, 0.1, 0.2, 0.3, 0.4, 0.5, 0.75, 1, 1.5, 2, 2.5, 3, 4, 5, 6, 7, 8,
          9, 10, 15, 20, 50, 100
      ]
      self.metric = prometheus_client.Histogram(
          metadata.varname,
          metadata.docstring,
          labelnames=field_names,
          buckets=bins,
          registry=registry)
    elif metadata.metric_type == rdf_stats.MetricMetadata.MetricType.GAUGE:
      self.metric = prometheus_client.Gauge(
          metadata.varname,
          metadata.docstring,
          labelnames=field_names,
          registry=registry)
    else:
      raise ValueError("Unknown metric type: {!r}".format(metadata.metric_type))

  def Validate(self, fields):
    if len(fields or ()) != len(self.fields):
      raise ValueError(
          "Statistic {} was created with {!r} fields, but a value with fields"
          " {!r} was trying to be saved.".format(self.metadata.varname,
                                                 self.fields, fields))

  def ForFields(self, fields):
    self.Validate(fields)
    if fields:
      return self.metric.labels(*fields)
    else:
      return self.metric

  def __repr__(self):
    return "<{} varname={!r} fields={!r} metric={!r}>".format(
        compatibility.GetName(type(self)), self.metadata.varname, self.fields,
        self.metric)


def _DistributionFromHistogram(metric, values_by_suffix):
  """Instantiate a rdf_stats.Distribution from a Prometheus Histogram.

  Prometheus Histogram uses cumulative "buckets" lower or equal to an upper
  bound. At instantiation, +Inf is implicitly appended to the upper bounds.
  The delimiters [0.0, 0.1, 0.2 (, +Inf)] produce the following buckets:
  Bucket "0.0" : -Inf <= values <=  0.0
  Bucket "0.1" : -Inf <= values <=  0.1
  Bucket "0.2" : -Inf <= values <=  0.2
  Bucket "+Inf": -Inf <= values <= +Inf

  Distribution uses exclusive bins greater or equal to a lower bound and
  strictly lower than the next lower bound. At instantiation, -Inf is implicitly
  prepended. The delimiters [(-Inf,) 0.0, 0.1, 0.2] produce the following bins:
  Bin "-Inf": -Inf <= values <  0.0
  Bin "0.0" :  0.0 <= values <  0.1
  Bin "0.1" :  0.1 <= values <  0.2
  Bin "0.2" :  0.2 <= values <= +Inf

  Thus, Histogram buckets can be transformed to Distribution bins, by reading
  in the same order and subtracting the value of the previous bin to remove the
  cumulative sum. There is a slight incompatibility for values equal to bin
  boundaries, because boundaries describe the upper bound for Prometheus and
  the lower bound for our internal implementation.

  Args:
    metric: prometheus_stats_collector.Metric
    values_by_suffix: dict of metric name suffixes and sample values lists

  Returns:
    rdf_stats.Distribution

  Raises:
    ValueError: The Histogram and metadata bin count do not match.
  """
  dist = rdf_stats.Distribution(bins=list(metric.metadata.bins))
  if metric.metadata.bins and len(dist.heights) != len(
      values_by_suffix["_bucket"]):
    raise ValueError(
        "Trying to create Distribution with {} bins, but underlying"
        "Histogram has {} buckets".format(
            len(dist.heights), len(values_by_suffix["_bucket"])))
  dist.heights = values_by_suffix["_bucket"]

  # Remove cumulative sum by subtracting the value of the previous bin
  for i in reversed(range(1, len(dist.heights))):
    dist.heights[i] -= dist.heights[i - 1]

  dist.count = values_by_suffix["_count"][0]
  dist.sum = values_by_suffix["_sum"][0]
  return dist


class PrometheusStatsCollector(stats_collector.StatsCollector):
  """Prometheus-based StatsCollector.

  This StatsCollector maps native Counters and Gauges to their Prometheus
  counterparts. Native Events are mapped to Prometheus Histograms.

  Attributes:
    lock: threading.Lock required by the utils.Synchronized decorator.
  """

  def __init__(self, metadata_list, registry=None):
    """Instantiates a new PrometheusStatsCollector.

    Args:
      metadata_list: A list of MetricMetadata objects describing the metrics
        that the StatsCollector will track.
      registry: An instance of prometheus_client.CollectorRegistry. If None, a
        new CollectorRegistry is instantiated. Use prometheus_client.REGISTRY
        for the global default registry.
    """
    self._metrics = {}  # type: Dict[Text, _Metric]

    if registry is None:
      self._registry = prometheus_client.CollectorRegistry(auto_describe=True)
    else:
      self._registry = registry

    self.lock = threading.RLock()

    super(PrometheusStatsCollector, self).__init__(metadata_list)

  def _InitializeMetric(self, metadata):
    self._metrics[metadata.varname] = _Metric(metadata, registry=self._registry)

  @utils.Synchronized
  def IncrementCounter(self, metric_name, delta=1, fields=None):
    metric = self._metrics[metric_name]
    counter = metric.ForFields(fields)  # type: prometheus_client.Counter
    counter.inc(delta)

  @utils.Synchronized
  def RecordEvent(self, metric_name, value, fields=None):
    # TODO(user): decouple validation from implementation.
    # Use validation wrapper approach in StatsCollector (similar to
    # how it's done in REL_DB).
    precondition.AssertType(value, six.integer_types + (float,))

    metric = self._metrics[metric_name]
    histogram = metric.ForFields(fields)  # type: prometheus_client.Histogram
    histogram.observe(value)

  @utils.Synchronized
  def SetGaugeValue(self, metric_name, value, fields=None):
    metric = self._metrics[metric_name]
    gauge = metric.ForFields(fields)  # type: prometheus_client.Gauge
    gauge.set(value)

  @utils.Synchronized
  def SetGaugeCallback(self, metric_name, callback, fields=None):
    metric = self._metrics[metric_name]
    gauge = metric.ForFields(fields)  # type: prometheus_client.Gauge
    gauge.set_function(callback)

  @utils.Synchronized
  def GetMetricFields(self, metric_name):
    metric = self._metrics[metric_name]
    if not metric.fields:
      return []

    field_tuples = set()
    for prom_metric in metric.metric.collect():
      for sample in prom_metric.samples:
        labels = [sample.labels[field_name] for field_name, _ in metric.fields]
        field_tuples.add(tuple(labels))
    return list(field_tuples)

  @utils.Synchronized
  def GetMetricValue(self, metric_name, fields=None):
    metric = self._metrics[metric_name]
    metric_type = metric.metadata.metric_type
    sub_metrics = metric.ForFields(fields).collect()
    samples = [sample for sm in sub_metrics for sample in sm.samples]

    values_by_suffix = collections.defaultdict(list)
    for sample in samples:
      suffix = sample.name.replace(metric_name, "")
      values_by_suffix[suffix].append(sample.value)

    if metric_type == rdf_stats.MetricMetadata.MetricType.EVENT:
      return _DistributionFromHistogram(metric, values_by_suffix)
    elif metric_type == rdf_stats.MetricMetadata.MetricType.COUNTER:
      return values_by_suffix["_total"][0]
    else:
      return samples[-1].value
