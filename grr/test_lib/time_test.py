#!/usr/bin/env python
from absl.testing import absltest

from grr_response_core.lib import rdfvalue
from grr.test_lib import time


class StepTest(absltest.TestCase):

  def testTimePassage(self):
    then = rdfvalue.RDFDatetime.Now()
    time.Step()
    now = rdfvalue.RDFDatetime.Now()

    self.assertLess(then, now)


class HumanReadabelToMicrosecondsSinceEpochTest(absltest.TestCase):

  def testWorksCorrectly(self):
    self.assertEqual(
        time.HumanReadableToMicrosecondsSinceEpoch("2017-07-20T18:40:22Z"),
        1500576022000000)

    self.assertEqual(
        time.HumanReadableToMicrosecondsSinceEpoch("2021-02-09T22:34:52Z"),
        1612910092000000)


if __name__ == "__main__":
  absltest.main()
