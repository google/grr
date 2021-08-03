#!/usr/bin/env python
"""A module with agent-specific time utilities."""
import math
import time
from typing import Callable


def Sleep(
    secs: float,
    progress_secs: float = math.inf,
    progress_callback: Callable[[], None] = lambda: None,
) -> None:
  """Suspends current thread execution for the specified amount of time.

  Unlike the built-in `time.sleep` function, this will also ensure that the
  progress callback function is invoked according to the specified intervals.

  This function is useful for suspending the main agent thread but still being
  able to notify the supervisor process about "not being stuck".

  Args:
    secs: The amount of seconds to suspend the current thread for.
    progress_secs: The amount of seconds between progress callback calls.
    progress_callback: A progress function to invoke.
  """
  if secs < 0.0:
    raise ValueError(f"Negative sleep time: {secs}s")
  if progress_secs <= 0.0:
    raise ValueError(f"Non-positive progress frequency: {progress_secs}s")

  while progress_secs <= secs:
    time.sleep(progress_secs)
    secs -= progress_secs

    progress_callback()

  time.sleep(secs)
