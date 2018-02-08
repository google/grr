#!/usr/bin/env python
# -*- mode: python; encoding: utf-8 -*-
"""Tests for utility classes."""


import unittest
from grr.lib import flags
from grr.lib import rdfvalue
from grr.test_lib import test_lib

long_string = (
    "迎欢迎\n"
    "Lorem ipsum dolor sit amet, consectetur adipiscing elit. Morbi luctus "
    "ex sed dictum volutpat. Integer maximus, mauris at tincidunt iaculis, "
    "felis magna scelerisque ex, in scelerisque est odio non nunc. "
    "Suspendisse et lobortis augue. Donec faucibus tempor massa, sed dapibus"
    " erat iaculis ut. Vestibulum eu elementum nulla. Nullam scelerisque "
    "hendrerit lorem. Integer vitae semper metus. Suspendisse accumsan "
    "dictum felis. Etiam viverra, felis sed ullamcorper vehicula, libero "
    "nisl tempus dui, a porta lacus erat et erat. Morbi mattis elementum "
    "efficitur. Pellentesque aliquam placerat mauris non accumsan.")


class RDFValueTest(unittest.TestCase):
  """RDFValue tests."""

  def testStr(self):
    """Test RDFValue.__str__."""
    self.assertEqual(str(rdfvalue.RDFBool(True)), "1")
    self.assertEqual(str(rdfvalue.RDFString(long_string)), long_string)

  def testRepr(self):
    """Test RDFValue.__repr__."""
    self.assertEqual(repr(rdfvalue.RDFBool(True)), "<RDFBool('1')>")
    self.assertEqual(
        repr(rdfvalue.RDFString(long_string)),
        "<RDFString('\\xe8\\xbf\\x8e\\xe6\\xac\\xa2\\xe8\\xbf\\x8e\\nLorem "
        "ipsum dolor sit amet, consectetur adipiscing elit. Morbi luctus ex "
        "sed dictum volutp...')>")


def main(argv):
  test_lib.main(argv)


if __name__ == "__main__":
  flags.StartMain(main)
