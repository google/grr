#!/usr/bin/env python
"""This file contains cache-related utility functions used by GRR."""
from __future__ import absolute_import
from __future__ import division

from __future__ import print_function
from __future__ import unicode_literals

import functools
import threading

from grr_response_core.lib import rdfvalue

WITH_LIMITED_CALL_FREQUENCY_PASS_THROUGH = False


def WithLimitedCallFrequency(min_time_between_calls):
  """Function call rate-limiting decorator.

  This decorator ensures that the wrapped function will be called at most
  once in min_time_between_calls time for the same set of arguments. For all
  excessive calls a previous cached return value will be returned.

  Suppose we use the decorator like this:
  @cache.WithLimitedCallFrequency(rdfvalue.Duration("30s"))
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

  def Decorated(f):
    """Actual decorator implementation."""

    lock = threading.RLock()
    prev_times = {}
    prev_results = {}
    result_locks = {}

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
        for k, prev_time in list(prev_times.items()):
          if now - prev_time >= min_time:
            prev_times.pop(k)
            prev_results.pop(k, None)
            result_locks.pop(k, None)

        try:
          # We eliminated all the old entries, so if the key is present
          # in the cache, it means that the data is fresh enough to be used.
          prev_time = prev_times[key]
          return prev_results[key]
        except KeyError:
          prev_time = None
          should_call = True

        if not should_call:
          return prev_results[key]

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

    return Fn

  return Decorated
