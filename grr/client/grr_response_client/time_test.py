#!/usr/bin/env python
import time as stdtime
from typing import List
from unittest import mock

from absl.testing import absltest

from grr_response_client import time


class SleepTest(absltest.TestCase):

  def setUp(self):
    super().setUp()

    self.sleeps: List[float] = []

    sleep_patcher = mock.patch.object(stdtime, "sleep", self.sleeps.append)
    sleep_patcher.start()
    self.addCleanup(sleep_patcher.stop)

  def testNegative(self):
    with self.assertRaisesRegex(ValueError, "Negative"):
      time.Sleep(-1.0)

  def testNonPositiveProgress(self):
    with self.assertRaisesRegex(ValueError, "Non-positive"):
      time.Sleep(1.0, progress_secs=0.0)

  def testZero(self):
    time.Sleep(0.0)
    self.assertEqual(sum(self.sleeps), 0.0)

  def testNoProgress(self):
    time.Sleep(42.0)
    self.assertEqual(sum(self.sleeps), 42.0)

  def testProgressCalled(self):
    func_counter = 0

    def Func() -> None:
      nonlocal func_counter
      func_counter += 1

    time.Sleep(42.0, progress_secs=1.0, progress_callback=Func)
    self.assertEqual(func_counter, 42)
    self.assertEqual(sum(self.sleeps), 42.0)

  def testProgressNotCalled(self):
    func_counter = 0

    def Func() -> None:
      nonlocal func_counter
      func_counter += 1

    time.Sleep(42.0, progress_secs=108.0, progress_callback=Func)
    self.assertEqual(func_counter, 0)
    self.assertEqual(sum(self.sleeps), 42.0)


if __name__ == "__main__":
  absltest.main()
