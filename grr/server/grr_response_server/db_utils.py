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
from grr_response_core.stats import stats_collector_instance
from grr_response_server import db


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


def ClientIdFromGrrMessage(m):
  if m.queue:
    return m.queue.Split()[0]
  if m.source:
    return m.source.Basename()


def _HexBytesFromUnicode(raw_value):
  """Converts a unicode object to its hex representation (bytes)."""
  return binascii.hexlify(raw_value.encode("utf-8"))
