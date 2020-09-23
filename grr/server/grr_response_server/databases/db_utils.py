#!/usr/bin/env python
# Lint as: python3
"""Utility functions/decorators for DB implementations."""
from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

import functools
import logging
import time

from typing import Text

from grr_response_core.lib import utils
from grr_response_core.lib.util import precondition
from grr_response_core.stats import metrics
from grr_response_server.databases import db


DB_REQUEST_LATENCY = metrics.Event(
    "db_request_latency",
    fields=[("call", str)],
    bins=[0.05 * 1.2**x for x in range(30)])  # 50ms to ~10 secs
DB_REQUEST_ERRORS = metrics.Counter(
    "db_request_errors", fields=[("call", str), ("type", str)])


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

      DB_REQUEST_LATENCY.RecordEvent(latency, fields=[f.__name__])
      logging.debug("DB request %s SUCCESS (%.3fs)", f.__name__, latency)

      return result
    except db.Error as e:
      DB_REQUEST_ERRORS.Increment(fields=[f.__name__, "grr"])
      logging.debug("DB request %s GRR ERROR: %s", f.__name__,
                    utils.SmartUnicode(e))
      raise
    except Exception as e:
      DB_REQUEST_ERRORS.Increment(fields=[f.__name__, "db"])
      logging.debug("DB request %s INTERNAL DB ERROR : %s", f.__name__,
                    utils.SmartUnicode(e))
      raise

  return Decorator


def EscapeWildcards(string: Text) -> Text:
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


def EscapeBackslashes(string: Text) -> Text:
  """Escapes backslash characters for strings intended to be used with `LIKE`.

  Backslashes work in mysterious ways: sometimes they do need to be escaped,
  sometimes this is being done automatically when passing values. Combined with
  unclear rules of `LIKE`, this can be very confusing.

  https://what.thedailywtf.com/topic/13989/mysql-backslash-escaping

  Args:
    string: A string to escape.

  Returns:
    An escaped string.
  """
  precondition.AssertType(string, Text)
  return string.replace("\\", "\\\\")


def ClientIdFromGrrMessage(m):
  if m.queue:
    return m.queue.Split()[0]
  if m.source:
    return m.source.Basename()


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
  # Stringify legacy IDs (32-bit) to 8 characters to allow string equality
  # comparison, otherwise "11111111" would be != "0000000011111111", but both
  # represent the same actual number 0x11111111.
  if flow_id <= 0xFFFFFFFF:
    return "{:08X}".format(flow_id)
  else:
    return "{:016X}".format(flow_id)


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
  return IntToFlowID(hunt_id)


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
