#!/usr/bin/env python
"""Tests for (de)serialization logic."""

from absl.testing import absltest

from grr_response_core.lib import serialization


class BoolConverterTest(absltest.TestCase):

  def testFromHumanReadableTrue(self):
    self.assertIs(serialization.FromHumanReadable(bool, "true"), True)
    self.assertIs(serialization.FromHumanReadable(bool, "True"), True)
    self.assertIs(serialization.FromHumanReadable(bool, "TRUE"), True)
    self.assertIs(serialization.FromHumanReadable(bool, "1"), True)

  def testFromHumanReadableFalse(self):
    self.assertIs(serialization.FromHumanReadable(bool, "false"), False)
    self.assertIs(serialization.FromHumanReadable(bool, "False"), False)
    self.assertIs(serialization.FromHumanReadable(bool, "FALSE"), False)
    self.assertIs(serialization.FromHumanReadable(bool, "0"), False)

  def testFromHumanReadableRaisesOnIncorrectInteger(self):
    with self.assertRaises(ValueError):
      serialization.FromHumanReadable(bool, "2")

  def testFromHumanReadableRaisesOnWeirdInput(self):
    with self.assertRaises(ValueError):
      serialization.FromHumanReadable(bool, "yes")

  def testWireFormat(self):
    self.assertIs(
        serialization.FromWireFormat(bool, serialization.ToWireFormat(True)),
        True,
    )
    self.assertIs(
        serialization.FromWireFormat(bool, serialization.ToWireFormat(False)),
        False,
    )

  def testBytes(self):
    self.assertIs(
        serialization.FromBytes(bool, serialization.ToBytes(True)), True
    )
    self.assertIs(
        serialization.FromBytes(bool, serialization.ToBytes(False)), False
    )

  def testHumanReadable(self):
    self.assertIs(serialization.FromHumanReadable(bool, str(True)), True)
    self.assertIs(serialization.FromHumanReadable(bool, str(False)), False)


if __name__ == "__main__":
  absltest.main()
