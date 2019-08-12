#!/usr/bin/env python
"""Utilities for handling stats."""

from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

import functools
import time

from past.builtins import long
from typing import Text

from grr_response_core.lib.rdfvalues import stats as rdf_stats
from grr_response_core.lib.util import compatibility


class Timed(object):
  """A decorator that records timing metrics for function calls."""

  def __init__(self, event_metric, fields=None):
    self._event_metric = event_metric
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
        self._event_metric.RecordEvent(total_time, fields=self._fields)

    return Decorated


class Counted(object):
  """A decorator that counts function calls."""

  def __init__(self, counter_metric, fields=None):
    self._counter_metric = counter_metric
    self._fields = fields or []

  def __call__(self, func):

    @functools.wraps(func)
    def Decorated(*args, **kwargs):
      """Calls a decorated function then increments a counter."""
      try:
        return func(*args, **kwargs)
      finally:
        self._counter_metric.Increment(fields=self._fields)

    return Decorated


class SuccessesCounted(object):
  """A decorator that counts function calls that don't raise an exception."""

  def __init__(self, counter_metric, fields=None):
    self._counter_metric = counter_metric
    self._fields = fields or []

  def __call__(self, func):

    @functools.wraps(func)
    def Decorated(*args, **kwargs):
      """Calls a decorated function then increments a counter."""
      result = func(*args, **kwargs)
      self._counter_metric.Increment(fields=self._fields)
      return result

    return Decorated


class ErrorsCounted(object):
  """A decorator that counts function calls that raise an exception."""

  def __init__(self, counter_metric, fields=None):
    self._counter_metric = counter_metric
    self._fields = fields or []

  def __call__(self, func):

    @functools.wraps(func)
    def Decorated(*args, **kwargs):
      """Calls a decorated function then increments a counter."""
      try:
        return func(*args, **kwargs)
      except Exception:  # pylint: disable=broad-except
        self._counter_metric.Increment(fields=self._fields)
        raise

    return Decorated


def FieldDefinitionProtosFromTuples(field_def_tuples):
  """Converts (field-name, type) tuples to MetricFieldDefinition protos."""
  # TODO: This needs fixing for Python 3.
  field_def_protos = []
  for field_name, field_type in field_def_tuples:
    if field_type in (int, long):
      field_type = rdf_stats.MetricFieldDefinition.FieldType.INT
    elif issubclass(field_type, Text):
      field_type = rdf_stats.MetricFieldDefinition.FieldType.STR
    else:
      raise ValueError("Invalid field type: %s" % field_type)
    field_def_protos.append(
        rdf_stats.MetricFieldDefinition(
            field_name=field_name, field_type=field_type))
  return field_def_protos


def FieldDefinitionTuplesFromProtos(field_def_protos):
  """Converts MetricFieldDefinition protos to (field-name, type) tuples."""
  # TODO: This needs fixing for Python 3.
  field_def_tuples = []
  for proto in field_def_protos:
    if proto.field_type == rdf_stats.MetricFieldDefinition.FieldType.INT:
      field_type = int
    elif proto.field_type == rdf_stats.MetricFieldDefinition.FieldType.STR:
      # Use old style str in Python 2 here or the streamz library will break.
      field_type = compatibility.builtins.str
    else:
      raise ValueError("Unknown field type: %s" % proto.field_type)
    field_def_tuples.append((proto.field_name, field_type))
  return field_def_tuples


def MetricValueTypeFromPythonType(python_type):
  """Converts Python types to MetricMetadata.ValueType enum values."""
  if python_type in (int, long):
    return rdf_stats.MetricMetadata.ValueType.INT
  elif python_type == float:
    return rdf_stats.MetricMetadata.ValueType.FLOAT
  else:
    raise ValueError("Invalid value type: %s" % python_type)


def PythonTypeFromMetricValueType(value_type):
  """Converts MetricMetadata.ValueType enums to corresponding Python types."""
  if value_type == rdf_stats.MetricMetadata.ValueType.INT:
    return int
  elif value_type == rdf_stats.MetricMetadata.ValueType.FLOAT:
    return float
  else:
    raise ValueError("Unknown value type: %s" % value_type)
