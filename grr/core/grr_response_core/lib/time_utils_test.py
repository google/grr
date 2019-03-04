#!/usr/bin/env python
"""Tests for time-related utilities."""
from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals


from absl import app
from absl.testing import absltest

from grr_response_core.lib import rdfvalue
from grr_response_core.lib import time_utils
from grr.test_lib import test_lib


class TimeUtilsTest(absltest.TestCase):

  def testInvalidTimeRange(self):
    with self.assertRaisesWithLiteralMatch(ValueError,
                                           "Invalid time-range: 2000 > 1000."):
      time_utils.TimeRange(
          rdfvalue.RDFDatetime(2000), rdfvalue.RDFDatetime(1000))

  def testIncludesTimeRange(self):
    time_range = time_utils.TimeRange(
        rdfvalue.RDFDatetime(1000), rdfvalue.RDFDatetime(2000))
    self.assertFalse(time_range.Includes(rdfvalue.RDFDatetime(500)))
    self.assertTrue(time_range.Includes(rdfvalue.RDFDatetime(1000)))
    self.assertTrue(time_range.Includes(rdfvalue.RDFDatetime(1500)))
    self.assertTrue(time_range.Includes(rdfvalue.RDFDatetime(2000)))
    self.assertFalse(time_range.Includes(rdfvalue.RDFDatetime(2500)))


def main(argv):
  test_lib.main(argv)


if __name__ == "__main__":
  app.run(main)
