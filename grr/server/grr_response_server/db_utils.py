#!/usr/bin/env python
"""Utility functions/decorators for DB implementations."""
from __future__ import absolute_import
from __future__ import division

from __future__ import unicode_literals

import binascii
import functools
import hashlib
import logging
import time

from typing import Text

from grr_response_core.lib import utils
from grr_response_core.lib.rdfvalues import stats as rdf_stats
from grr_response_core.stats import stats_collector_instance
from grr_response_server import db
from grr_response_server import stats_values


def CallLoggedAndAccounted(f):
  """Decorator to log and account for a DB call."""

  @functools.wraps(f)
  def Decorator(*args, **kwargs):
    try:
      start_time = time.time()
      result = f(*args, **kwargs)
      latency = time.time() - start_time

      stats_collector_instance.Get().RecordEvent(
          "db_request_latency", latency, fields=[f.__name__])
      logging.debug("DB request %s SUCCESS (%.3fs)", f.__name__, latency)

      return result
    except db.Error as e:
      stats_collector_instance.Get().IncrementCounter(
          "db_request_errors", fields=[f.__name__, "grr"])
      logging.debug("DB request %s GRR ERROR: %s", f.__name__,
                    utils.SmartStr(e))
      raise
    except Exception as e:
      stats_collector_instance.Get().IncrementCounter(
          "db_request_errors", fields=[f.__name__, "db"])
      logging.debug("DB request %s INTERNAL DB ERROR : %s", f.__name__,
                    utils.SmartStr(e))
      raise

  return Decorator


def ClientIdFromGrrMessage(m):
  if m.queue:
    return m.queue.Split()[0]
  if m.source:
    return m.source.Basename()


def _HexBytesFromUnicode(raw_value):
  """Converts a unicode object to its hex representation (bytes)."""
  return binascii.hexlify(raw_value.encode("utf-8"))


def GenerateStatsEntryId(stats_entry):
  """Returns a unique identifier representing a StatsStoreEntry.

  The id returned (bytes) is the SHA2 hash of all fields in the StatsStoreEntry
  that should uniquely identify it in a database.

  Args:
    stats_entry: StatsStoreEntry for which to generate an id.

  Raises:
    ValueError: If a field-type in the StatsStoreEntry doesn't match
      a known MetricFieldDefinition.FieldType.
  """
  # Convert all field values to hex so they can be unambiguously
  # concatenated in a string. We first convert strings to hex so we can use
  # a separator that is guaranteed to not be present in the separate
  # parts.
  hex_field_values = []
  for field_value in stats_entry.metric_value.fields_values:
    field_type = field_value.field_type
    if field_type == rdf_stats.MetricFieldDefinition.FieldType.INT:
      hex_field_values.append(b"%x" % field_value.int_value)
    elif field_type == rdf_stats.MetricFieldDefinition.FieldType.STR:
      hex_field_values.append(_HexBytesFromUnicode(field_value.str_value))
    else:
      raise ValueError("Unknown field type %s." % field_type)

  # Create an unambiguous string representation of the fields
  # that should form an id.
  variable_length_id = b"%s-%s-%s-%x" % (
      _HexBytesFromUnicode(stats_entry.process_id),
      _HexBytesFromUnicode(stats_entry.metric_name),
      (b":".join(hex_field_values)),
      stats_entry.timestamp.AsMicrosecondsSinceEpoch())

  # Convert to a fixed-length id.
  return hashlib.sha256(variable_length_id).digest()
