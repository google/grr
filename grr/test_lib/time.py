#!/usr/bin/env python
"""Test utilities for working with time."""
import sys
import time

import dateutil


def Step() -> None:
  """Ensures passage of time.

  Some tests need to ensure that some amount of time has passed. However, on
  some platforms (Windows in particular) Python has a terribly low system clock
  resolution, in which case two consecutive time checks can return the same
  value.

  This utility waits (by sleeping the minimum amount of time possible), until
  the time actually made a step. Which is not perfect, as unit tests in general
  should not wait, but in this case this time is minimal possible.
  """
  start = time.time()
  while start == time.time():
    time.sleep(sys.float_info.epsilon)


_MICROSECOND_MULTIPLIER = 10**6


def HumanReadableToMicrosecondsSinceEpoch(timestamp: str) -> int:
  """Converts a human readable timestamp into microseconds since epoch.

  Args:
    timestamp: A human readable date time string.

  Returns:
    Number of microseconds since epoch.

  Note: this method is intentionally made testing only, as it relies on
  dateutil.parser guessing the timestamp format. Guessing is expensive
  and generally non-deterministic and should be avoided in production
  code.
  """
  return dateutil.parser.parse(timestamp).timestamp() * _MICROSECOND_MULTIPLIER
