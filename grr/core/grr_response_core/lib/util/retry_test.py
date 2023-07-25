#!/usr/bin/env python
import datetime

from absl.testing import absltest

from grr_response_core.lib.util import retry


class OnTest(absltest.TestCase):

  def testNegativeTries(self):
    opts = retry.Opts(
        attempts=-1,
    )

    with self.assertRaisesRegex(ValueError, "number of retries"):
      retry.On((), opts=opts)

  def testImmediateSuccess(self):
    opts = retry.Opts(
        attempts=1,
        sleep=lambda _: None,
    )

    @retry.On((), opts=opts)
    def Func() -> None:
      pass

    Func()  # Should not raise.

  def testRetriedSuccess(self):
    opts = retry.Opts(
        attempts=3,
        sleep=lambda _: None,
    )

    counter = []

    @retry.On(RuntimeError, opts=opts)
    def Func() -> None:
      counter.append(())
      if len(counter) < 3:
        raise RuntimeError()

    Func()  # Should not raise.

  def testRetriedFailure(self):
    opts = retry.Opts(
        attempts=3,
        sleep=lambda _: None,
    )

    counter = []

    @retry.On(RuntimeError, opts=opts)
    def Func() -> None:
      counter.append(())
      if len(counter) < 4:
        raise RuntimeError()

    with self.assertRaises(RuntimeError):
      Func()

  def testBackoff(self):
    delays = []

    opts = retry.Opts(
        attempts=7,
        init_delay=datetime.timedelta(seconds=1),
        backoff=2.0,
        sleep=delays.append,
    )

    @retry.On(RuntimeError, opts=opts)
    def Func() -> None:
      raise RuntimeError()

    with self.assertRaises(RuntimeError):
      Func()

    self.assertEqual(
        delays,
        [
            datetime.timedelta(seconds=1),
            datetime.timedelta(seconds=2),
            datetime.timedelta(seconds=4),
            datetime.timedelta(seconds=8),
            datetime.timedelta(seconds=16),
            datetime.timedelta(seconds=32),
        ],
    )

  def testJitter(self):
    delays = []

    opts = retry.Opts(
        attempts=4,
        init_delay=datetime.timedelta(seconds=1),
        jitter=0.5,
        sleep=delays.append,
    )

    @retry.On(RuntimeError, opts=opts)
    def Func() -> None:
      raise RuntimeError()

    with self.assertRaises(RuntimeError):
      Func()

    self.assertLen(delays, 3)
    self.assertBetween(
        delays[0],
        datetime.timedelta(seconds=0.5),
        datetime.timedelta(seconds=1.5),
    )
    self.assertBetween(
        delays[1],
        datetime.timedelta(seconds=0.5),
        datetime.timedelta(seconds=1.5),
    )
    self.assertBetween(
        delays[2],
        datetime.timedelta(seconds=0.5),
        datetime.timedelta(seconds=1.5),
    )

  def testJitterAndBackoff(self):
    delays = []

    opts = retry.Opts(
        attempts=4,
        init_delay=datetime.timedelta(seconds=1),
        backoff=2.0,
        jitter=0.5,
        sleep=delays.append,
    )

    @retry.On(RuntimeError, opts=opts)
    def Func() -> None:
      raise RuntimeError()

    with self.assertRaises(RuntimeError):
      Func()

    self.assertLen(delays, 3)
    self.assertBetween(
        delays[0],
        datetime.timedelta(seconds=0.5),
        datetime.timedelta(seconds=1.5),
    )
    self.assertBetween(
        delays[1],
        datetime.timedelta(seconds=1.0),
        datetime.timedelta(seconds=4.0),
    )
    self.assertBetween(
        delays[2],
        datetime.timedelta(seconds=2.0),
        datetime.timedelta(seconds=8.0),
    )

  def testInitDelay(self):
    delays = []

    opts = retry.Opts(
        attempts=4,
        init_delay=datetime.timedelta(seconds=42),
        backoff=1.0,
        sleep=delays.append,
    )

    @retry.On(RuntimeError, opts=opts)
    def Func() -> None:
      raise RuntimeError()

    with self.assertRaises(RuntimeError):
      Func()

    self.assertEqual(
        delays,
        [
            datetime.timedelta(seconds=42),
            datetime.timedelta(seconds=42),
            datetime.timedelta(seconds=42),
        ],
    )

  def testMaxDelay(self):
    delays = []

    opts = retry.Opts(
        attempts=6,
        init_delay=datetime.timedelta(seconds=1),
        max_delay=datetime.timedelta(seconds=3),
        backoff=1.5,
        sleep=delays.append,
    )

    @retry.On(RuntimeError, opts=opts)
    def Func() -> None:
      raise RuntimeError()

    with self.assertRaises(RuntimeError):
      Func()

    self.assertEqual(
        delays,
        [
            datetime.timedelta(seconds=1),
            datetime.timedelta(seconds=1.5),
            datetime.timedelta(seconds=2.25),
            datetime.timedelta(seconds=3),
            datetime.timedelta(seconds=3),
        ],
    )

  def testImmediateArgumentsAndResult(self):

    @retry.On(())
    def Func(left: str, right: str) -> int:
      return int(f"{left}{right}")

    self.assertEqual(Func("13", "37"), 1337)

  def testRetriedArgumentAndResult(self):
    opts = retry.Opts(
        attempts=3,
        sleep=lambda _: None,
    )

    counter = []

    @retry.On(RuntimeError, opts=opts)
    def Func(left: str, right: str) -> int:
      counter.append(())
      if len(counter) < 3:
        raise RuntimeError()

      return int(f"{left}{right}")

    self.assertEqual(Func("13", "37"), 1337)

  def testUnexpectedException(self):

    class FooError(Exception):
      pass

    class BarError(Exception):
      pass

    @retry.On((FooError,))
    def Func() -> None:
      raise BarError()

    with self.assertRaises(BarError):
      Func()

  def testMultipleExceptions(self):

    class FooError(Exception):
      pass

    class BarError(Exception):
      pass

    class BazError(Exception):
      pass

    opts = retry.Opts(
        attempts=4,
        sleep=lambda _: None,
    )

    counter = []

    @retry.On((FooError, BarError, BazError), opts=opts)
    def Func() -> None:
      counter.append(())
      if counter == 1:
        raise FooError()
      if counter == 2:
        raise BarError()
      if counter == 3:
        raise BazError()

    Func()  # Should not raise.


class WhenTest(absltest.TestCase):

  def testImmediateSuccess(self):
    opts = retry.Opts(
        attempts=1,
        sleep=lambda _: None,
    )

    @retry.When(RuntimeError, lambda _: False, opts=opts)
    def Func() -> None:
      pass

    Func()  # Should not raise.

  def testRetriedSuccess(self):
    opts = retry.Opts(
        attempts=3,
        sleep=lambda _: None,
    )

    counter = []

    @retry.When(RuntimeError, lambda _: True, opts=opts)
    def Func() -> None:
      counter.append(())
      if len(counter) < 3:
        raise RuntimeError()

    Func()  # Should not raise.

  def testRetriedFailure(self):
    opts = retry.Opts(
        attempts=3,
        sleep=lambda _: None,
    )

    counter = []

    @retry.When(RuntimeError, lambda _: True, opts=opts)
    def Func() -> None:
      counter.append(())
      if len(counter) < 4:
        raise RuntimeError()

    with self.assertRaises(RuntimeError):
      Func()

  def testNegativePredicate(self):
    opts = retry.Opts(
        attempts=3,
        sleep=lambda _: None,
    )

    counter = []

    @retry.When(RuntimeError, lambda _: False, opts=opts)
    def Func() -> None:
      counter.append(())
      raise RuntimeError()

    with self.assertRaises(RuntimeError):
      Func()

    self.assertLen(counter, 1)

  def testUnexpectedException(self):
    class FooError(Exception):
      pass

    class BarError(Exception):
      pass

    @retry.When(FooError, lambda _: True)
    def Func() -> None:
      raise BarError()

    with self.assertRaises(BarError):
      Func()

  def testMultipleExceptions(self):
    class FooError(Exception):
      pass

    class BarError(Exception):
      pass

    class BazError(Exception):
      pass

    opts = retry.Opts(
        attempts=4,
        sleep=lambda _: None,
    )

    counter = []

    @retry.When((FooError, BarError, BazError), lambda _: True, opts=opts)
    def Func() -> None:
      counter.append(())
      if counter == 1:
        raise FooError()
      if counter == 2:
        raise BarError()
      if counter == 3:
        raise BazError()

    Func()  # Should not raise.


if __name__ == "__main__":
  absltest.main()
