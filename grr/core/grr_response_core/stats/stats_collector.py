#!/usr/bin/env python
"""Common logic for objects used to track monitoring-related metrics.

GRR has a notion of statistic metrics. These metrics reflect GRR's state at
any given moment. There are three types of metrics available:

1. Counter. This is an integer metric that can only be incremented and never
decremented. Example: number of handled requests.
2. Gauge. Gauge metrics have a type, they can be either string, integer
or float. Gauge metric may have any value of its type.
3. Event. Event metrics are used to record events that take certain amount of
time. They're stored as latency distributions. Example: request latency.

Metrics may have fields. Fields are used in cases where you would generally
require a dynamically named metric. For example if you have requests coming
from http and rpc sources. You can defined 2 metrics: requests_count_http and
requests_count_rpc or define a single metric with a field "source".

Fields are essentially dimensions. For example,
if a metric "request_count" has no fields, it will be stored as a simple list
of data. I.e.:
request_count: 10 11 12 13 14

If "request_count" metric has a field "source" of type "str", then it will be
stored as a table. I.e. it will store different lists of values for different
values of the source field:
request_count[source=http]: 10 11 12 13 14
request_count[source=rpc]:  0  1  2  4  5

If "request_count" metric has a field "source" of type "str" and a field
"datacenter_index" of type "int", then it will be stored as a 3-dimensional
table. I.e.:
request_count[source=http,datacenter_index=0]: 10 11 12 13 14
request_count[source=rpc,datacenter_index=0]:  0  0  0  2  2
request_count[source=http,datacenter_index=1]: 33 34 45 88 99
request_count[source=rpc,datacenter_index=1]:  0  2  3  4  4
request_count[source=http,datacenter_index=2]: 22 33 44 55 66
request_count[source=rpc,datacenter_index=2]:  10 11 11 20 21

To summarize, for every combination of different field values, a separate row
of statistics data will be collected. Given that it's extremely important
to ensure that every field used in particular metric has a finite number of
possible values.
"""
from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

import abc

from future.utils import with_metaclass


# pytype: disable=ignored-abstractmethod
class StatsCollector(with_metaclass(abc.ABCMeta, object)):
  """Base implementation for a stats-collector.

  Stats-collectors are used to track monitoring-related metrics. By default,
  metrics are effectively single-dimensional. However, one or more named
  dimensions can be specified when defining a metric. Thereafter, the metric
  gets updated by specifying values for each of the dimensions/fields. For
  example, if a counter is initialized with the dimensions
    [("method_name", str), ("response_code", int)],
  an example of how it gets incremented would be:
    collector.IncrementCounter("counter_name", fields=["POST", 200])

  Args:
    metadata_list: A list of MetricMetadata objects describing the metrics that
      the stats-collector will track.

  Raises:
    ValueError: If there are two metrics with the same name in metadata_list.
  """

  def __init__(self, metadata_list):
    self._metadata_dict = {}
    for metadata in metadata_list:
      if metadata.varname in self._metadata_dict:
        raise ValueError("Duplicate metadata for metric %s." % metadata.varname)
      self._InitializeMetric(metadata)
      self._metadata_dict[metadata.varname] = metadata

  @abc.abstractmethod
  def _InitializeMetric(self, metadata):
    """Initializes a metric with the given metadata.

    Args:
      metadata: MetricMetadata for the metric.
    """
    raise NotImplementedError()

  @abc.abstractmethod
  def IncrementCounter(self, metric_name, delta=1, fields=None):
    """Increments a counter metric by a given delta.

    Args:
      metric_name: Name of the metric.
      delta: Delta by which the metric should be incremented.
      fields: Values for this metric's dimensions. Should only be provided if
        the metric was registered with dimensions.

    Raises:
      ValueError: If delta < 0.
    """
    raise NotImplementedError()

  @abc.abstractmethod
  def RecordEvent(self, metric_name, value, fields=None):
    """Records value corresponding to the given event metric.

    Args:
      metric_name: Name of the metric.
      value: Value to be recorded.
      fields: Values for this metric's dimensions. Should only be provided if
        the metric was registered with dimensions.
    """
    raise NotImplementedError()

  @abc.abstractmethod
  def SetGaugeValue(self, metric_name, value, fields=None):
    """Sets value of a given gauge metric.

    Args:
      metric_name: Name of the metric.
      value: New metric value.
      fields: Values for this metric's dimensions. Should only be provided if
        the metric was registered with dimensions.
    """
    raise NotImplementedError()

  @abc.abstractmethod
  def SetGaugeCallback(self, metric_name, callback, fields=None):
    """Attaches a callback to the given gauge metric.

    Args:
      metric_name: Name of the metric.
      callback: Zero argument function that is expected to provide the metric's
        current value (with corresponding field values) every time it is called.
      fields: Values for this metric's dimensions. Should only be provided if
        the metric was registered with dimensions. If provided, the callback
        will only be invoked when caller provides same field values.
    """
    raise NotImplementedError()

  def GetMetricMetadata(self, metric_name):
    """Returns the MetricMetadata for the given metric.

    Args:
      metric_name: Name of the metric.

    Returns:
      MetricMetadata object describing the metric.

    Raises:
      KeyError: if metric is not found.
    """
    return self._metadata_dict[metric_name]

  def GetAllMetricsMetadata(self):
    """Returns a dict mapping all metric names to their MetricMetadata."""
    return self._metadata_dict

  @abc.abstractmethod
  def GetMetricFields(self, metric_name):
    """Returns all field values for the given metric.

    Args:
      metric_name: Name of the metric.

    Returns:
      A list of tuples containing field values that were used for the specified
      metric. For example, if there's a counter metric registered with fields
      ("renderer_type", int) and there were 2 calls to Increment:
        Increment("renderer_type", fields=[1])
        Increment("renderer_type", fields=[2]),
      then GetMetricFields("renderer_type") will return [(1,), (2,)].
    """
    raise NotImplementedError()

  @abc.abstractmethod
  def GetMetricValue(self, metric_name, fields=None):
    """Returns the value of a given metric for given field values.

    Args:
      metric_name: Name of the metric.
      fields: List of values for this metric's dimensions. Should only be
        provided if the metric was registered without any dimensions.

    Returns:
      int for a counter metric.
      int, float, str (depending on the type used to register
        the metric) for a gauge metric.
      Distribution-compatible object for event metric. Distribution-compatible
      means "with an API matching the API of the Distribution object".
    """
    raise NotImplementedError()

# pytype: enable=ignored-abstractmethod
