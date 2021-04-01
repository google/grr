#!/usr/bin/env python
from absl.testing import absltest

from grr_response_core.lib.util import retry


class OnTest(absltest.TestCase):

  def testNegativeTries(self):
    opts = retry.Opts()
    opts.attempts = -1

    with self.assertRaisesRegex(ValueError, "number of retries"):
      retry.On((), opts=opts)

  def testImmediateSuccess(self):
    opts = retry.Opts()
    opts.attempts = 1
    opts.sleep = lambda _: None

    @retry.On((), opts=opts)
    def Func() -> None:
      pass

    Func()  # Should not raise.

  def testRetriedSuccess(self):
    opts = retry.Opts()
    opts.attempts = 3
    opts.sleep = lambda _: None

    counter = []

    @retry.On((RuntimeError,), opts=opts)
    def Func() -> None:
      counter.append(())
      if len(counter) < 3:
        raise RuntimeError()

    Func()  # Should not raise.

  def testRetriedFailure(self):
    opts = retry.Opts()
    opts.attempts = 3
    opts.sleep = lambda _: None

    counter = []

    @retry.On((RuntimeError,), opts=opts)
    def Func() -> None:
      counter.append(())
      if len(counter) < 4:
        raise RuntimeError()

    with self.assertRaises(RuntimeError):
      Func()

  def testBackoff(self):
    delays = []

    opts = retry.Opts()
    opts.attempts = 7
    opts.init_delay_secs = 1.0
    opts.backoff = 2.0
    opts.sleep = delays.append

    @retry.On((RuntimeError,), opts=opts)
    def Func() -> None:
      raise RuntimeError()

    with self.assertRaises(RuntimeError):
      Func()

    self.assertEqual(delays, [1.0, 2.0, 4.0, 8.0, 16.0, 32.0])

  def testInitDelay(self):
    delays = []

    opts = retry.Opts()
    opts.attempts = 4
    opts.init_delay_secs = 42.0
    opts.backoff = 1.0
    opts.sleep = delays.append

    @retry.On((RuntimeError,), opts=opts)
    def Func() -> None:
      raise RuntimeError()

    with self.assertRaises(RuntimeError):
      Func()

    self.assertEqual(delays, [42.0, 42.0, 42.0])

  def testMaxDelay(self):
    delays = []

    opts = retry.Opts()
    opts.attempts = 6
    opts.init_delay_secs = 1.0
    opts.max_delay_secs = 3.0
    opts.backoff = 1.5
    opts.sleep = delays.append

    @retry.On((RuntimeError,), opts=opts)
    def Func() -> None:
      raise RuntimeError()

    with self.assertRaises(RuntimeError):
      Func()

    self.assertEqual(delays, [1.0, 1.5, 2.25, 3.0, 3.0])

  def testImmediateArgumentsAndResult(self):

    @retry.On(())
    def Func(left: str, right: str) -> int:
      return int(f"{left}{right}")

    self.assertEqual(Func("13", "37"), 1337)

  def testRetriedArgumentAndResult(self):
    opts = retry.Opts()
    opts.attempts = 3
    opts.sleep = lambda _: None

    counter = []

    @retry.On((RuntimeError,), opts=opts)
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

    opts = retry.Opts()
    opts.attempts = 4
    opts.sleep = lambda _: None

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


if __name__ == "__main__":
  absltest.main()
