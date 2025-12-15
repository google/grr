#!/usr/bin/env python
"""This file contains cache-related utility functions used by GRR."""

from collections.abc import Callable
import functools
import logging
import threading
from typing import Any, TypeVar

from grr_response_core.lib import rdfvalue

WITH_LIMITED_CALL_FREQUENCY_PASS_THROUGH = False

_F = TypeVar("_F", bound=Callable[..., Any])

_FVoid = TypeVar("_FVoid", bound=Callable[..., None])


def WithLimitedCallFrequency(
    min_time_between_calls: rdfvalue.Duration,
) -> Callable[[_F], _F]:
  """Function call rate-limiting decorator.

  This decorator ensures that the wrapped function will be called at most
  once in min_time_between_calls time for the same set of arguments. For all
  excessive calls a previous cached return value will be returned.

  Suppose we use the decorator like this:
  @cache.WithLimitedCallFrequency(rdfvalue.Duration.From(30, rdfvalue.SECONDS))
  def Foo(id):
    ...

  If Foo(42) is called and then Foo(42) is called again within 30 seconds, then
  the second call will simply return the cached return value of the first.

  If Foo(42) is called and then Foo(43) is called within 30 seconds, the
  wrapped function will be properly called in both cases, since these Foo calls
  have different arguments sets.

  If Foo(42) is called and takes a long time to finish, and another
  Foo(42) call is done in another thread, then the latter call will wait for
  the first one to finish and then return the cached result value. I.e. the
  wrapped function will be called just once, thus keeping the guarantee of
  at most 1 run in min_time_between_calls.

  NOTE 1: this function becomes a trivial pass-through and does no caching if
  module-level WITH_LIMITED_CALL_FREQUENCY_PASS_THROUGH variable is set to
  True. This is used in testing.

  NOTE 2: all decorated functions' arguments have to be hashable.

  Args:
    min_time_between_calls: An rdfvalue.Duration specifying the minimal time to
      pass between 2 consecutive function calls with same arguments.

  Returns:
    A Python function decorator.
  """

  def Decorated(f: _F) -> _F:
    """Actual decorator implementation."""

    lock = threading.RLock()
    prev_times = {}
    prev_results = {}
    result_locks = {}
    prev_cleanup_time = rdfvalue.RDFDatetime.Now()

    def CleanUpCache(now: rdfvalue.RDFDatetime, min_time: rdfvalue.Duration):
      """Cleans up the cache from stale entries."""
      nonlocal prev_cleanup_time
      if now < prev_cleanup_time:
        logging.warning(
            "Current timestamp %s is before the previous cache cleaning time"
            " %s, hoping we're inside the test",
            now,
            prev_cleanup_time,
        )
        prev_cleanup_time = now
        return

      if (now - prev_cleanup_time) < min_time:
        return

      for k, prev_time in list(prev_times.items()):
        if prev_time > now:
          # We have a result from the future, hopefully this is a test...
          logging.warning(
              "Deleting cached function result from the future (%s > %s)",
              prev_time,
              now,
          )
          prev_times.pop(k)
          prev_results.pop(k, None)
          result_locks.pop(k, None)
        elif now - prev_time >= min_time:
          prev_times.pop(k)
          prev_results.pop(k, None)
          result_locks.pop(k, None)

      prev_cleanup_time = now

    @functools.wraps(f)
    def Fn(*args, **kwargs):
      """Wrapper around the decorated function."""

      if WITH_LIMITED_CALL_FREQUENCY_PASS_THROUGH:
        # This effectively turns off the caching.
        min_time = rdfvalue.Duration(0)
      else:
        min_time = min_time_between_calls

      key = (args, tuple(sorted(kwargs.items())))
      now = rdfvalue.RDFDatetime.Now()

      with lock:
        CleanUpCache(now, min_time)

        try:
          prev_time = prev_times[key]
          if now - prev_time < min_time:
            return prev_results[key]
        except KeyError:
          prev_time = None

        try:
          result_lock = result_locks[key]
        except KeyError:
          result_lock = threading.RLock()
          result_locks[key] = result_lock

      with result_lock:
        t = prev_times.get(key)

        if t == prev_time:
          result = f(*args, **kwargs)
          with lock:
            prev_times[key] = rdfvalue.RDFDatetime.Now()
            prev_results[key] = result

          return result
        else:
          return prev_results[key]

    def _DebugInternalState():
      return dict(
          prev_times=prev_times,
          prev_results=prev_results,
          result_locks=result_locks,
          prev_cleanup_time=prev_cleanup_time,
      )

    # This is used by the tests to ensure that the internal representation
    # behaves as expected.
    Fn._DebugInternalState = (  # pylint: disable=protected-access
        _DebugInternalState
    )

    return Fn

  return Decorated


def WithLimitedCallFrequencyWithoutReturnValue(
    min_time_between_calls: rdfvalue.Duration,
) -> Callable[[_FVoid], _FVoid]:
  """Function call rate-limiting decorator for None-returning functions.

  This decorator ensures that the wrapped function will be called at most
  once in min_time_between_calls time for the same set of arguments. Given
  that the wrapped function is not expected to return a value, all excessive
  calls will be dropped immediately, even if a parallel ongoing
  call for the same set of arguments is in progress in another thread.

  Suppose we use the decorator like this:
  @cache.WithLimitedCallFrequencyWithoutReturnValue(
      rdfvalue.Duration.From(30, rdfvalue.SECONDS))
  def Foo(id):
    ...

  If Foo(42) is called and then Foo(42) is called again within 30 seconds, then
  the second call will simply return immediately.

  If Foo(42) is called and then Foo(43) is called within 30 seconds, the
  wrapped function will be properly called in both cases, since these Foo calls
  have different arguments sets.

  If Foo(42) is called and takes a long time to finish, and another
  Foo(42) call is done in another thread, then the latter call will return
  immediately.

  NOTE 1: this function becomes a trivial pass-through and does no caching if
  module-level WITH_LIMITED_CALL_FREQUENCY_PASS_THROUGH variable is set to
  True. This is used in testing.

  NOTE 2: all decorated functions' arguments have to be hashable.

  Args:
    min_time_between_calls: An rdfvalue.Duration specifying the minimal time to
      pass between 2 consecutive function calls with same arguments.

  Returns:
    A Python function decorator.
  """

  def Decorated(f: _FVoid) -> _FVoid:
    """Actual decorator implementation."""

    lock = threading.RLock()
    prev_times = {}
    in_progress_locks = {}
    prev_cleanup_time = rdfvalue.RDFDatetime.Now()

    def CleanUpCache(now: rdfvalue.RDFDatetime, min_time: rdfvalue.Duration):
      """Cleans up the cache from stale entries."""
      nonlocal prev_cleanup_time
      if now < prev_cleanup_time:
        logging.warning(
            "Current timestamp %s is before the previous cache cleaning time"
            " %s, hoping we're inside the test",
            now,
            prev_cleanup_time,
        )
        prev_cleanup_time = now
        return

      if (now - prev_cleanup_time) < min_time:
        return

      for k, prev_time in list(prev_times.items()):
        if prev_time > now:
          # We have a result from the future, hopefully this is a test...
          logging.warning(
              "Deleting cached function result from the future (%s > %s)",
              prev_time,
              now,
          )
          prev_times.pop(k)
          in_progress_locks.pop(k, None)
        elif now - prev_time >= min_time:
          prev_times.pop(k)
          in_progress_locks.pop(k, None)

      prev_cleanup_time = now

    @functools.wraps(f)
    def Fn(*args, **kwargs):
      """Wrapper around the decorated function."""

      if WITH_LIMITED_CALL_FREQUENCY_PASS_THROUGH:
        # This effectively turns off the caching.
        min_time = rdfvalue.Duration(0)
      else:
        min_time = min_time_between_calls

      key = (args, tuple(sorted(kwargs.items())))
      now = rdfvalue.RDFDatetime.Now()

      with lock:
        CleanUpCache(now, min_time)

        try:
          prev_time = prev_times[key]
          if now - prev_time < min_time:
            return
        except KeyError:
          pass

        try:
          in_progress_lock = in_progress_locks[key]
        except KeyError:
          in_progress_lock = threading.RLock()
          in_progress_locks[key] = in_progress_lock

      if in_progress_lock.acquire(blocking=False):
        try:
          r = f(*args, **kwargs)
          assert r is None, "Wrapped function should have no return value"

          with lock:
            prev_times[key] = rdfvalue.RDFDatetime.Now()
        finally:
          in_progress_lock.release()

    def _DebugInternalState():
      return dict(
          prev_times=prev_times,
          in_progress_locks=in_progress_locks,
          prev_cleanup_time=prev_cleanup_time,
      )

    # This is used by the tests to ensure that the internal representation
    # behaves as expected.
    Fn._DebugInternalState = (  # pylint: disable=protected-access
        _DebugInternalState
    )

    return Fn

  return Decorated
