#!/usr/bin/env python
"""Utility functions/decorators for DB implementations."""

import functools
import logging
import time

from grr.lib import registry
from grr.lib import stats
from grr.lib import utils
from grr.server.grr_response_server import db


def CallLoggedAndAccounted(f):
  """Decorator to log and acoount for a DB call."""

  @functools.wraps(f)
  def Decorator(*args, **kwargs):
    try:
      start_time = time.time()
      result = f(*args, **kwargs)
      latency = time.time() - start_time

      stats.STATS.RecordEvent(
          "db_request_latency", latency, fields=[f.__name__])
      logging.debug("DB request %s SUCCESS (%.3fs)", f.__name__, latency)

      return result
    except db.Error as e:
      stats.STATS.IncrementCounter(
          "db_request_errors", fields=[f.__name__, "grr"])
      logging.debug("DB request %s GRR ERROR: %s", f.__name__,
                    utils.SmartStr(e))
      raise
    except Exception as e:
      stats.STATS.IncrementCounter(
          "db_request_errors", fields=[f.__name__, "db"])
      logging.debug("DB request %s INTERNAL DB ERROR : %s", f.__name__,
                    utils.SmartStr(e))
      raise

  return Decorator


class DBMetricsInit(registry.InitHook):
  """Install database metrics."""

  def RunOnce(self):
    stats.STATS.RegisterEventMetric(
        "db_request_latency", fields=[("call", str)])
    stats.STATS.RegisterCounterMetric(
        "db_request_errors", fields=[("call", str), ("type", str)])
