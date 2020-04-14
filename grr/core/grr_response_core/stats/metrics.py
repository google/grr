#!/usr/bin/env python
# Lint as: python3
"""Metric implementations to collect statistics."""
from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

import abc

from grr_response_core.lib.rdfvalues import stats as rdf_stats
from grr_response_core.stats import stats_collector_instance
from grr_response_core.stats import stats_utils


class AbstractMetric(metaclass=abc.ABCMeta):
  """An abstract metric with a name, fields, and values.

  Refer to default_stats_collector._Metric and DefaultStatsCollector to
  see how StatsCollector handles the field definitions and values.

  Attributes:
    name: string containing the global metric name.
  """

  def __init__(self, metadata):
    """Initializes a new metric and registers it with the StatsCollector."""
    self.name = metadata.varname
    stats_collector_instance.RegisterMetric(metadata)

  def GetValue(self, fields=None):
    """Returns the value of a given metric for given field values."""
    return stats_collector_instance.Get().GetMetricValue(
        self.name, fields=fields)

  def GetFields(self):
    """Returns all field values for the given metric."""
    return stats_collector_instance.Get().GetMetricFields(self.name)


class Counter(AbstractMetric):
  """A Counter metric that can be incremented.

  Refer to default_stats_collector._CounterMetric and DefaultStatsCollector to
  see how StatsCollector handles the field definitions and values.
  """

  def __init__(self, name, fields=(), docstring=None, units=None):
    """Initializes a Counter metric and registers it with the StatsCollector."""
    super().__init__(
        rdf_stats.MetricMetadata(
            varname=name,
            metric_type=rdf_stats.MetricMetadata.MetricType.COUNTER,
            value_type=rdf_stats.MetricMetadata.ValueType.INT,
            fields_defs=stats_utils.FieldDefinitionProtosFromTuples(fields),
            docstring=docstring,
            units=units))

  def Increment(self, delta=1, fields=None):
    """Increments a counter metric by a given delta."""
    stats_collector_instance.Get().IncrementCounter(
        self.name, delta, fields=fields)

  def Counted(self, fields=None):
    """Returns a decorator that counts function calls."""
    return stats_utils.Counted(self, fields=fields)

  def SuccessesCounted(self, fields=None):
    """Returns a decorator that counts calls that don't raise an exception."""
    return stats_utils.SuccessesCounted(self, fields=fields)

  def ErrorsCounted(self, fields=None):
    """Returns a decorator that counts calls that raise an exception."""
    return stats_utils.ErrorsCounted(self, fields=fields)


class Gauge(AbstractMetric):
  """A Gauge metric that can be set to a value.

  Refer to default_stats_collector._GaugeMetric and DefaultStatsCollector to
  see how StatsCollector handles the field definitions and values.
  """

  def __init__(self, name, value_type, fields=(), docstring=None, units=None):
    """Initializes a Gauge metric and registers it with the StatsCollector."""
    super().__init__(
        rdf_stats.MetricMetadata(
            varname=name,
            metric_type=rdf_stats.MetricMetadata.MetricType.GAUGE,
            value_type=stats_utils.MetricValueTypeFromPythonType(value_type),
            fields_defs=stats_utils.FieldDefinitionProtosFromTuples(fields),
            docstring=docstring,
            units=units))

  def SetValue(self, value, fields=None):
    """Sets value of a given gauge metric."""
    stats_collector_instance.Get().SetGaugeValue(
        self.name, value, fields=fields)

  def SetCallback(self, callback, fields=None):
    """Attaches a callback to the given gauge metric."""
    stats_collector_instance.Get().SetGaugeCallback(
        self.name, callback, fields=fields)


class Event(AbstractMetric):
  """An Event metric that records timings of events.

  Refer to default_stats_collector._EventMetric and DefaultStatsCollector to
  see how StatsCollector handles the field definitions and values.
  """

  def __init__(self, name, bins=(), fields=(), docstring=None, units=None):
    """Initializes an Event metric and registers it with the StatsCollector."""
    super().__init__(
        rdf_stats.MetricMetadata(
            varname=name,
            bins=bins,
            metric_type=rdf_stats.MetricMetadata.MetricType.EVENT,
            value_type=rdf_stats.MetricMetadata.ValueType.DISTRIBUTION,
            fields_defs=stats_utils.FieldDefinitionProtosFromTuples(fields),
            docstring=docstring,
            units=units))

  def RecordEvent(self, value, fields=None):
    """Records value corresponding to the given event metric."""
    stats_collector_instance.Get().RecordEvent(self.name, value, fields=fields)

  def Timed(self, fields=None):
    """Returns a decorator that records timing metrics for function calls."""
    return stats_utils.Timed(self, fields=fields)
