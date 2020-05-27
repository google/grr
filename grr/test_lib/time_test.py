#!/usr/bin/env python
# Lint as: python3
from absl.testing import absltest

from grr_response_core.lib import rdfvalue
from grr.test_lib import time


class StepTest(absltest.TestCase):

  def testTimePassage(self):
    then = rdfvalue.RDFDatetime.Now()
    time.Step()
    now = rdfvalue.RDFDatetime.Now()

    self.assertLess(then, now)


if __name__ == "__main__":
  absltest.main()
