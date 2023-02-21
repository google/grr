#!/usr/bin/env python

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


class UnescapeStringTest(absltest.TestCase):

  def testWhitespace(self):
    self.assertEqual(text.Unescape("\\n"), "\n")
    self.assertEqual(text.Unescape("\\r"), "\r")

  def testQuotemark(self):
    self.assertEqual(text.Unescape("\\'"), "'")
    self.assertEqual(text.Unescape("\\\""), "\"")

  def testMany(self):
    self.assertEqual(text.Unescape("foo\\n\\'bar\\'\nbaz"), "foo\n'bar'\nbaz")


if __name__ == "__main__":
  absltest.main()
