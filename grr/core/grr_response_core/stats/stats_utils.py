#!/usr/bin/env python
"""Utilities for handling stats."""

from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

import functools
import time

from past.builtins import long

from grr_response_core.lib.rdfvalues import stats as rdf_stats
from grr_response_core.stats import stats_collector_instance


class Timed(object):
  """A decorator that records timing metrics for function calls."""

  def __init__(self, metric_name, fields=None):
    self._metric_name = metric_name
    self._fields = fields or []

  def __call__(self, func):

    @functools.wraps(func)
    def Decorated(*args, **kwargs):
      """Calls a decorated function, timing how long it takes."""
      start_time = time.time()
      try:
        return func(*args, **kwargs)
      finally:
        total_time = time.time() - start_time
        stats_collector_instance.Get().RecordEvent(
            self._metric_name, total_time, fields=self._fields)

    return Decorated


class Counted(object):
  """A decorator that counts function calls."""

  def __init__(self, metric_name, fields=None):
    self._metric_name = metric_name
    self._fields = fields or []

  def __call__(self, func):

    @functools.wraps(func)
    def Decorated(*args, **kwargs):
      """Calls a decorated function then increments a counter."""
      try:
        return func(*args, **kwargs)
      finally:
        stats_collector_instance.Get().IncrementCounter(
            self._metric_name, fields=self._fields)

    return Decorated


class CountingExceptionMixin(object):
  """An exception that increments a counter every time it is raised."""

  # Override with the name of the counter
  counter = None
  # Override with fields set for this counter
  fields = []

  def __init__(self, *args, **kwargs):
    if self.counter:
      stats_collector_instance.Get().IncrementCounter(
          self.counter, fields=self.fields)
    super(CountingExceptionMixin, self).__init__(*args, **kwargs)


def FieldDefinitionProtosFromTuples(field_def_tuples):
  """Converts (field-name, type) tuples to MetricFieldDefinition protos."""
  field_def_protos = []
  for field_name, field_type in field_def_tuples:
    if field_type in (int, long):
      field_type = rdf_stats.MetricFieldDefinition.FieldType.INT
    elif field_type == str:
      field_type = rdf_stats.MetricFieldDefinition.FieldType.STR
    else:
      raise ValueError("Invalid field type: %s" % field_type)
    field_def_protos.append(
        rdf_stats.MetricFieldDefinition(
            field_name=field_name, field_type=field_type))
  return field_def_protos


def FieldDefinitionTuplesFromProtos(field_def_protos):
  """Converts MetricFieldDefinition protos to (field-name, type) tuples."""
  field_def_tuples = []
  for proto in field_def_protos:
    if proto.field_type == rdf_stats.MetricFieldDefinition.FieldType.INT:
      field_type = int
    elif proto.field_type == rdf_stats.MetricFieldDefinition.FieldType.STR:
      field_type = str
    else:
      raise ValueError("Unknown field type: %s" % proto.field_type)
    field_def_tuples.append((proto.field_name, field_type))
  return field_def_tuples


def MetricValueTypeFromPythonType(python_type):
  """Converts Python types to MetricMetadata.ValueType enum values."""
  if python_type in (int, long):
    return rdf_stats.MetricMetadata.ValueType.INT
  elif python_type == str:
    return rdf_stats.MetricMetadata.ValueType.STR
  elif python_type == float:
    return rdf_stats.MetricMetadata.ValueType.FLOAT
  else:
    raise ValueError("Invalid value type: %s" % python_type)


def PythonTypeFromMetricValueType(value_type):
  """Converts MetricMetadata.ValueType enums to corresponding Python types."""
  if value_type == rdf_stats.MetricMetadata.ValueType.INT:
    return int
  elif value_type == rdf_stats.MetricMetadata.ValueType.STR:
    return str
  elif value_type == rdf_stats.MetricMetadata.ValueType.FLOAT:
    return float
  else:
    raise ValueError("Unknown value type: %s" % value_type)


def CreateCounterMetadata(metric_name, fields=None, docstring=None, units=None):
  """Helper function for creating MetricMetadata for counter metrics."""
  return rdf_stats.MetricMetadata(
      varname=metric_name,
      metric_type=rdf_stats.MetricMetadata.MetricType.COUNTER,
      value_type=rdf_stats.MetricMetadata.ValueType.INT,
      fields_defs=FieldDefinitionProtosFromTuples(fields or []),
      docstring=docstring,
      units=units)


def CreateEventMetadata(metric_name,
                        bins=None,
                        fields=None,
                        docstring=None,
                        units=None):
  """Helper function for creating MetricMetadata for event metrics."""
  return rdf_stats.MetricMetadata(
      varname=metric_name,
      bins=bins or [],
      metric_type=rdf_stats.MetricMetadata.MetricType.EVENT,
      value_type=rdf_stats.MetricMetadata.ValueType.DISTRIBUTION,
      fields_defs=FieldDefinitionProtosFromTuples(fields or []),
      docstring=docstring,
      units=units)


def CreateGaugeMetadata(metric_name,
                        value_type,
                        fields=None,
                        docstring=None,
                        units=None):
  """Helper function for creating MetricMetadata for gauge metrics."""
  return rdf_stats.MetricMetadata(
      varname=metric_name,
      metric_type=rdf_stats.MetricMetadata.MetricType.GAUGE,
      value_type=MetricValueTypeFromPythonType(value_type),
      fields_defs=FieldDefinitionProtosFromTuples(fields or []),
      docstring=docstring,
      units=units)
