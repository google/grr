#!/usr/bin/env python
import random
import threading
from unittest import mock

from absl.testing import absltest

from grr_response_core.lib import rdfvalue
from grr_response_core.lib.util import cache
from grr.test_lib import test_lib


class WithLimitedCallFrequencyTest(absltest.TestCase):

  def setUp(self):
    super().setUp()
    self.mock_fn = mock.Mock(wraps=lambda *_: random.random())
    self.mock_fn.__name__ = "foo"  # Expected by functools.wraps.

  def testCallsFunctionEveryTimeWhenMinTimeBetweenCallsZero(self):
    decorated = cache.WithLimitedCallFrequency(rdfvalue.Duration(0))(
        self.mock_fn)
    for _ in range(10):
      decorated()

    self.assertEqual(self.mock_fn.call_count, 10)

  def testCallsFunctionOnceInGivenTimeRangeWhenMinTimeBetweenCallsNonZero(self):
    decorated = cache.WithLimitedCallFrequency(
        rdfvalue.Duration.From(30, rdfvalue.SECONDS))(
            self.mock_fn)

    now = rdfvalue.RDFDatetime.Now()
    with test_lib.FakeTime(now):
      r1 = decorated()

    with test_lib.FakeTime(now + rdfvalue.Duration.From(15, rdfvalue.SECONDS)):
      r2 = decorated()

    self.assertEqual(r1, r2)
    self.assertEqual(self.mock_fn.call_count, 1)

    with test_lib.FakeTime(now + rdfvalue.Duration.From(30, rdfvalue.SECONDS)):
      r3 = decorated()

    self.assertNotEqual(r1, r3)
    self.assertEqual(self.mock_fn.call_count, 2)

  def testCachingIsDonePerArguments(self):
    decorated = cache.WithLimitedCallFrequency(
        rdfvalue.Duration.From(30, rdfvalue.SECONDS))(
            self.mock_fn)

    now = rdfvalue.RDFDatetime.Now()
    with test_lib.FakeTime(now):
      r1_a = decorated(1)
      r1_b = decorated(2)

    self.assertNotEqual(r1_a, r1_b)
    self.assertEqual(self.mock_fn.call_count, 2)

    with test_lib.FakeTime(now + rdfvalue.Duration.From(15, rdfvalue.SECONDS)):
      r2_a = decorated(1)
      r2_b = decorated(2)

    self.assertEqual(r1_a, r2_a)
    self.assertEqual(r1_b, r2_b)
    self.assertEqual(self.mock_fn.call_count, 2)

    with test_lib.FakeTime(now + rdfvalue.Duration.From(30, rdfvalue.SECONDS)):
      r3_a = decorated(1)
      r3_b = decorated(2)

    self.assertNotEqual(r1_a, r3_a)
    self.assertNotEqual(r1_b, r3_b)
    self.assertEqual(self.mock_fn.call_count, 4)

  def testDecoratedFunctionIsNotExecutedConcurrently(self):
    event = threading.Event()

    # Can't rely on mock's call_count as it's not thread safe.
    fn_calls = []

    def Fn():
      fn_calls.append(True)
      event.wait()
      return self.mock_fn()

    decorated = cache.WithLimitedCallFrequency(
        rdfvalue.Duration.From(30, rdfvalue.SECONDS))(
            Fn)

    results = []

    def T():
      results.append(decorated())

    threads = []
    for _ in range(10):
      t = threading.Thread(target=T)
      t.start()
      threads.append(t)

    # At this point all threads should be waiting on the function to complete,
    # with only 1 threads actually executing the function. Trigger the event
    # to force that one thread to complete.
    event.set()

    for t in threads:
      t.join()

    self.assertLen(results, len(threads))
    self.assertEqual(set(results), set([results[0]]))
    self.assertLen(fn_calls, 1)

  def testDecoratedFunctionsAreWaitedForPerArguments(self):
    event = threading.Event()

    # Can't rely on mock's call_count as it's not thread safe.
    fn_calls = []

    def Fn(x):
      fn_calls.append(x)
      if x != 42:
        event.wait()
      return x

    decorated = cache.WithLimitedCallFrequency(
        rdfvalue.Duration.From(30, rdfvalue.SECONDS))(
            Fn)

    def T():
      decorated(1)

    t = threading.Thread(target=T)
    t.start()
    try:

      # This should return immediately. There's another function call
      # in progress, but with different arguments, so no locking should occur.
      # I.e. decorated(1) and decorated(42) shouldn't influence each other.
      decorated(42)

    finally:
      event.set()
      t.join()

    self.assertLen(fn_calls, 2)

  def testPropagatesExceptions(self):
    mock_fn = mock.Mock(side_effect=ValueError())
    mock_fn.__name__ = "foo"  # Expected by functools.wraps.

    decorated = cache.WithLimitedCallFrequency(
        rdfvalue.Duration.From(30, rdfvalue.SECONDS))(
            mock_fn)

    with self.assertRaises(ValueError):
      decorated()

  def testExceptionIsNotCached(self):
    mock_fn = mock.Mock(side_effect=ValueError())
    mock_fn.__name__ = "foo"  # Expected by functools.wraps.

    decorated = cache.WithLimitedCallFrequency(
        rdfvalue.Duration.From(30, rdfvalue.SECONDS))(
            mock_fn)

    for _ in range(10):
      with self.assertRaises(ValueError):
        decorated()

    self.assertEqual(mock_fn.call_count, 10)

  # TODO(user): add a test case for a cace when non-hashable arguments are
  # passed.


if __name__ == "__main__":
  absltest.main()
