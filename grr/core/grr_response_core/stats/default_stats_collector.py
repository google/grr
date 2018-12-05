#!/usr/bin/env python
"""Default implementation for a stats-collector."""

from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

import abc
import threading

from future.utils import with_metaclass

from grr_response_core.lib import utils
from grr_response_core.lib.rdfvalues import stats as rdf_stats
from grr_response_core.stats import stats_collector
from grr_response_core.stats import stats_utils


def _FieldsToKey(fields):
  """Converts a list of field values to a metric key."""
  return tuple(fields) if fields else ()


# pytype: disable=ignored-abstractmethod
class _Metric(with_metaclass(abc.ABCMeta, object)):
  """Base class for all the metric objects used by the DefaultStatsCollector.

  See stats_collector for more info.

  Args:
    field_defs: A list of (field-name, field-type) tuples describing the
      dimensions for the metric.
  """

  def __init__(self, field_defs):
    self._field_defs = field_defs
    self._metric_values = {}

  @abc.abstractmethod
  def _DefaultValue(self):
    """Returns the default value of a metric.

    For counters, the default value is 0, for event metrics, the default
    value is a distribution, and for gauges, the default value is 0, 0.0 or
    the empty string depending on the type of the gauge (int, float or str).
    """

  def Get(self, fields=None):
    """Gets the metric value corresponding to the given field values."""
    if not self._field_defs and fields:
      raise ValueError("Metric was registered without fields, "
                       "but following fields were provided: %s." % (fields,))

    if self._field_defs and not fields:
      raise ValueError("Metric was registered with fields (%s), "
                       "but no fields were provided." % self._field_defs)

    if self._field_defs and fields and len(self._field_defs) != len(fields):
      raise ValueError(
          "Metric was registered with %d fields (%s), but "
          "%d fields were provided (%s)." % (len(
              self._field_defs), self._field_defs, len(fields), fields))

    metric_value = self._metric_values.get(_FieldsToKey(fields))
    return self._DefaultValue() if metric_value is None else metric_value

  def ListFieldsValues(self):
    """Returns a list of tuples of all field values used with the metric."""
    return list(self._metric_values) if self._field_defs else []


# pytype: enable=ignored-abstractmethod


class _CounterMetric(_Metric):
  """Simple counter metric (see stats_collector for more info)."""

  def _DefaultValue(self):
    return 0

  def Increment(self, delta, fields=None):
    """Increments counter value by a given delta."""
    if delta < 0:
      raise ValueError(
          "Counter increment should not be < 0 (received: %d)" % delta)

    self._metric_values[_FieldsToKey(fields)] = self.Get(fields=fields) + delta


class _EventMetric(_Metric):
  """_EventMetric provides detailed stats, like averages, distribution, etc.

  See stats_collector for more info.

  Args:
    bins: A list of numbers defining distribution buckets for the metric. If
      empty/None, a default list of buckets is used.
    fields: A list of (field-name, field-type) tuples describing the dimensions
      for the metric.
  """

  def __init__(self, bins, fields):
    super(_EventMetric, self).__init__(fields)
    self._bins = bins or [
        0.0, 0.1, 0.2, 0.3, 0.4, 0.5, 0.75, 1, 1.5, 2, 2.5, 3, 4, 5, 6, 7, 8, 9,
        10, 15, 20, 50, 100
    ]

  def _DefaultValue(self):
    return rdf_stats.Distribution(bins=self._bins)

  def Record(self, value, fields=None):
    """Records the given observation in a distribution."""
    key = _FieldsToKey(fields)
    metric_value = self._metric_values.get(key)
    if metric_value is None:
      metric_value = self._DefaultValue()
      self._metric_values[key] = metric_value
    metric_value.Record(value)


class _GaugeMetric(_Metric):
  """A metric whose value can increase or decrease.

  See stats_collector for more info.

  Args:
    value_type: Type of the gauge (one of int, str or float).
    fields: A list of (field-name, field-type) tuples describing the dimensions
      for the metric.
  """

  def __init__(self, value_type, fields):
    super(_GaugeMetric, self).__init__(fields)
    self._value_type = value_type

  def _DefaultValue(self):
    return self._value_type()

  def Set(self, value, fields=None):
    """Sets the metric's current value."""
    self._metric_values[_FieldsToKey(fields)] = self._value_type(value)

  def SetCallback(self, callback, fields=None):
    """Attaches the given callback to the metric."""
    self._metric_values[_FieldsToKey(fields)] = callback

  def Get(self, fields=None):
    """Returns current metric's value (executing a callback if needed)."""
    result = super(_GaugeMetric, self).Get(fields=fields)
    if callable(result):
      return result()
    else:
      return result


class DefaultStatsCollector(stats_collector.StatsCollector):
  """Default implementation for a stats-collector."""

  def __init__(self, metadata_list):
    self._counter_metrics = {}
    self._gauge_metrics = {}
    self._event_metrics = {}
    # Lock field required by the utils.Synchronized decorator.
    self.lock = threading.RLock()

    super(DefaultStatsCollector, self).__init__(metadata_list)

  def _InitializeMetric(self, metadata):
    """See base class."""
    field_defs = stats_utils.FieldDefinitionTuplesFromProtos(
        metadata.fields_defs)
    if metadata.metric_type == rdf_stats.MetricMetadata.MetricType.COUNTER:
      self._counter_metrics[metadata.varname] = _CounterMetric(field_defs)
    elif metadata.metric_type == rdf_stats.MetricMetadata.MetricType.EVENT:
      self._event_metrics[metadata.varname] = _EventMetric(
          list(metadata.bins), field_defs)
    elif metadata.metric_type == rdf_stats.MetricMetadata.MetricType.GAUGE:
      value_type = stats_utils.PythonTypeFromMetricValueType(
          metadata.value_type)
      self._gauge_metrics[metadata.varname] = _GaugeMetric(
          value_type, field_defs)
    else:
      raise ValueError("Unknown metric type: %s." % metadata.metric_type)

  @utils.Synchronized
  def IncrementCounter(self, metric_name, delta=1, fields=None):
    """See base class."""
    if delta < 0:
      raise ValueError("Invalid increment for counter: %d." % delta)
    self._counter_metrics[metric_name].Increment(delta, fields)

  @utils.Synchronized
  def RecordEvent(self, metric_name, value, fields=None):
    """See base class."""
    self._event_metrics[metric_name].Record(value, fields)

  @utils.Synchronized
  def SetGaugeValue(self, metric_name, value, fields=None):
    """See base class."""
    self._gauge_metrics[metric_name].Set(value, fields)

  @utils.Synchronized
  def SetGaugeCallback(self, metric_name, callback, fields=None):
    """See base class."""
    self._gauge_metrics[metric_name].SetCallback(callback, fields)

  def GetMetricFields(self, metric_name):
    """See base class."""
    return self._GetMetric(metric_name).ListFieldsValues()

  def GetMetricValue(self, metric_name, fields=None):
    """See base class."""
    return self._GetMetric(metric_name).Get(fields)

  def _GetMetric(self, metric_name):
    """Fetches the metric object corresponding to the given name."""
    if metric_name in self._counter_metrics:
      return self._counter_metrics[metric_name]
    elif metric_name in self._event_metrics:
      return self._event_metrics[metric_name]
    elif metric_name in self._gauge_metrics:
      return self._gauge_metrics[metric_name]
    else:
      raise ValueError("Metric %s is not registered." % metric_name)
