#!/usr/bin/env python
"""Tests for grr.parsers.wmi_parser."""

from absl import app

from grr_response_core.lib.parsers import wmi_parser
from grr.test_lib import test_lib


class BinarySIDToStringSIDTest(test_lib.GRRBaseTest):

  def assertConvertsTo(self, sid, expected_output):
    self.assertEqual(wmi_parser.BinarySIDtoStringSID(sid), expected_output)

  def testEmpty(self):
    self.assertConvertsTo(b"", "")

  def testSimple(self):
    self.assertConvertsTo(b"\x01", "S-1")
    self.assertConvertsTo(b"\x01\x05\x00\x00\x00\x00\x00\x05", "S-1-5")
    self.assertConvertsTo(
        b"\x01\x05\x00\x00\x00\x00\x00\x05\x15\x00\x00\x00", "S-1-5-21"
    )

  def testTruncated(self):
    with self.assertRaises(ValueError):
      wmi_parser.BinarySIDtoStringSID(
          b"\x01\x05\x00\x00\x00\x00\x00\x05\x15\x00\x00"
      )

    with self.assertRaises(ValueError):
      wmi_parser.BinarySIDtoStringSID(
          b"\x01\x05\x00\x00\x00\x00\x00\x05\x15\x00"
      )

  def test5Subauthorities(self):
    self.assertConvertsTo(
        b"\x01\x05\x00\x00\x00\x00\x00\x05\x15\x00\x00\x00\x85\x74\x77\xb9\x7c"
        b"\x0d\x7a\x96\x6f\xbd\x29\x9a\xf4\x01\x00\x00",
        "S-1-5-21-3111613573-2524581244-2586426735-500",
    )

  def testLastAuthorityTruncated(self):
    with self.assertRaises(ValueError):
      wmi_parser.BinarySIDtoStringSID(
          b"\x01\x05\x00\x00\x00\x00\x00\x05\x15\x00\x00\x00\x85\x74\x77\xb9"
          b"\x7c\x0d\x7a\x96\x6f\xbd\x29\x9a\xf4"
      )


def main(argv):
  test_lib.main(argv)


if __name__ == "__main__":
  app.run(main)
