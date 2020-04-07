#!/usr/bin/env python
# Lint as: python3
"""Tests for (de)serialization logic."""

from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

from absl.testing import absltest

from grr_response_core.lib import serialization


class BoolConverterTest(absltest.TestCase):

  def testFromHumanReadableTrue(self):
    self.assertIs(serialization.FromHumanReadable(bool, u"true"), True)
    self.assertIs(serialization.FromHumanReadable(bool, u"True"), True)
    self.assertIs(serialization.FromHumanReadable(bool, u"TRUE"), True)
    self.assertIs(serialization.FromHumanReadable(bool, u"1"), True)

  def testFromHumanReadableFalse(self):
    self.assertIs(serialization.FromHumanReadable(bool, u"false"), False)
    self.assertIs(serialization.FromHumanReadable(bool, u"False"), False)
    self.assertIs(serialization.FromHumanReadable(bool, u"FALSE"), False)
    self.assertIs(serialization.FromHumanReadable(bool, u"0"), False)

  def testFromHumanReadableRaisesOnIncorrectInteger(self):
    with self.assertRaises(ValueError):
      serialization.FromHumanReadable(bool, u"2")

  def testFromHumanReadableRaisesOnWeirdInput(self):
    with self.assertRaises(ValueError):
      serialization.FromHumanReadable(bool, u"yes")

  def testWireFormat(self):
    self.assertIs(
        serialization.FromWireFormat(bool, serialization.ToWireFormat(True)),
        True)
    self.assertIs(
        serialization.FromWireFormat(bool, serialization.ToWireFormat(False)),
        False)

  def testBytes(self):
    self.assertIs(
        serialization.FromBytes(bool, serialization.ToBytes(True)), True)
    self.assertIs(
        serialization.FromBytes(bool, serialization.ToBytes(False)), False)

  def testHumanReadable(self):
    self.assertIs(serialization.FromHumanReadable(bool, str(True)), True)
    self.assertIs(serialization.FromHumanReadable(bool, str(False)), False)


if __name__ == "__main__":
  absltest.main()
