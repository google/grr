#!/usr/bin/env python
# -*- encoding: utf-8 -*-
from __future__ import absolute_import
from __future__ import division

from __future__ import unicode_literals

from absl.testing import absltest

from grr_response_core.lib.util import text


class AsciifyTest(absltest.TestCase):

  def testAscii(self):
    self.assertEqual(text.Asciify(b"foobar"), "foobar")
    self.assertEqual(text.Asciify(b"+!?#"), "+!?#")

  def testNonAscii(self):
    self.assertEqual(text.Asciify(b"\xff\xfe\xff"), "\\xff\\xfe\\xff")
    self.assertEqual(text.Asciify(b"f\x00\x00bar"), "f\\x00\\x00bar")


class HexifyTest(absltest.TestCase):

  def testEmpty(self):
    self.assertEqual(text.Hexify(b""), "")

  def testEscaped(self):
    self.assertEqual(text.Hexify(b"\xff\xfd\xfa"), "fffdfa")
    self.assertEqual(text.Hexify(b"\x00\x11\x22"), "001122")
    self.assertEqual(text.Hexify(b"\x48\x15\x16\x23\x42"), "4815162342")

  def testAscii(self):
    self.assertEqual(text.Hexify(b"foo"), "666f6f")
    self.assertEqual(text.Hexify(b"bar"), "626172")


if __name__ == "__main__":
  absltest.main()
