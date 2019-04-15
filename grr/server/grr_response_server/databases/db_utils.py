#!/usr/bin/env python
"""Utility functions/decorators for DB implementations."""
from __future__ import absolute_import
from __future__ import division

from __future__ import unicode_literals

import binascii
import functools
import logging
import time

from typing import Text

from grr_response_core.lib import utils
from grr_response_core.lib.util import precondition
from grr_response_core.stats import stats_collector_instance
from grr_response_server.databases import db


class Error(Exception):
  pass


class FlowIDIsNotAnIntegerError(Error):
  pass


class OutputPluginIDIsNotAnIntegerError(Error):
  pass


class HuntIDIsNotAnIntegerError(Error):
  pass


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
                    utils.SmartUnicode(e))
      raise
    except Exception as e:
      stats_collector_instance.Get().IncrementCounter(
          "db_request_errors", fields=[f.__name__, "db"])
      logging.debug("DB request %s INTERNAL DB ERROR : %s", f.__name__,
                    utils.SmartUnicode(e))
      raise

  return Decorator


def EscapeWildcards(string):
  """Escapes wildcard characters for strings intended to be used with `LIKE`.

  Databases don't automatically escape wildcard characters ('%', '_'), so any
  non-literal string that is passed to `LIKE` and is expected to match literally
  has to be manually escaped.

  Args:
    string: A string to escape.

  Returns:
    An escaped string.
  """
  precondition.AssertType(string, Text)
  return string.replace("%", r"\%").replace("_", r"\_")


def ClientIdFromGrrMessage(m):
  if m.queue:
    return m.queue.Split()[0]
  if m.source:
    return m.source.Basename()


def _HexBytesFromUnicode(raw_value):
  """Converts a unicode object to its hex representation (bytes)."""
  return binascii.hexlify(raw_value.encode("utf-8"))


# GRR Client IDs are strings of the form "C.<16 hex digits>", our F1 schema
# uses uint64 values.
def ClientIDToInt(client_id):
  if client_id[:2] != "C.":
    raise ValueError("Malformed client id received: %s" % client_id)
  return int(client_id[2:], 16)


def IntToClientID(client_id):
  return "C.%016x" % client_id


def FlowIDToInt(flow_id):
  try:
    return int(flow_id or "0", 16)
  except ValueError as e:
    raise FlowIDIsNotAnIntegerError(e)


def IntToFlowID(flow_id):
  return "%08X" % flow_id


def HuntIDToInt(hunt_id):
  """Convert hunt id string to an integer."""
  # TODO(user): This code is only needed for a brief period of time when we
  # allow running new rel-db flows with old aff4-based hunts. In this scenario
  # parent_hunt_id is effectively not used, but it has to be an
  # integer. Stripping "H:" from hunt ids then makes the rel-db happy. Remove
  # this code when hunts are rel-db only.
  if hunt_id.startswith("H:"):
    hunt_id = hunt_id[2:]

  try:
    return int(hunt_id or "0", 16)
  except ValueError as e:
    raise HuntIDIsNotAnIntegerError(e)


def IntToHuntID(hunt_id):
  return "%08X" % hunt_id


def OutputPluginIDToInt(output_plugin_id):
  try:
    return int(output_plugin_id or "0", 16)
  except ValueError as e:
    raise OutputPluginIDIsNotAnIntegerError(e)


def IntToOutputPluginID(output_plugin_id):
  return "%08X" % output_plugin_id


def CronJobRunIDToInt(cron_job_run_id):
  if cron_job_run_id is None:
    return None
  else:
    return int(cron_job_run_id, 16)


def IntToCronJobRunID(cron_job_run_id):
  if cron_job_run_id is None:
    return None
  else:
    return "%08X" % cron_job_run_id


def SecondsToMicros(seconds):
  return int(seconds * 1e6)


def MicrosToSeconds(ms):
  return ms / 1e6
