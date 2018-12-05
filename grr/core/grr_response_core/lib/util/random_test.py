#!/usr/bin/env python
from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

import io
import os

from absl.testing import absltest
from future.builtins import range
import mock

from grr_response_core.lib.util import random


def WithUrandom(func):
  return mock.patch.object(os, "urandom", side_effect=func)


def WithRandomBuffer(values):
  return mock.patch.object(random, "_random_buffer", list(reversed(values)))


class UInt16Test(absltest.TestCase):

  @WithRandomBuffer([])
  @WithUrandom(lambda count: b"\x00" * count)
  def testMin(self, urandom):
    del urandom  # Unused.

    for _ in range(10000):
      if random.UInt16() != 0:
        self.assertEqual(random.UInt16(), 0)

  @WithRandomBuffer([])
  @WithUrandom(lambda count: b"\xff" * count)
  def testMax(self, urandom):
    del urandom  # Unused.

    for _ in range(10000):
      self.assertEqual(random.UInt16(), 2**16 - 1)

  @WithRandomBuffer([0xDEADDEAD, 0xBEEFBEEF])
  def testSpecific(self):
    self.assertEqual(random.UInt16(), 0xDEAD)
    self.assertEqual(random.UInt16(), 0xBEEF)


class PositiveUInt16Test(absltest.TestCase):

  @WithRandomBuffer([])
  @WithUrandom(io.BytesIO(b"\x00" * 10 * 1024 + b"\xff" * 10 * 1024).read)
  def testPositive(self, urandom):
    del urandom  # Unused.

    for _ in range(10):
      self.assertGreater(random.PositiveUInt16(), 0)


class UInt32Test(absltest.TestCase):

  @WithRandomBuffer([])
  @WithUrandom(lambda count: b"\x00" * count)
  def testMin(self, urandom):
    del urandom  # Unused.

    for _ in range(10000):
      self.assertEqual(random.UInt32(), 0)

  @WithRandomBuffer([])
  @WithUrandom(lambda count: b"\xff" * count)
  def testMax(self, urandom):
    del urandom  # Unused.

    for _ in range(10000):
      self.assertEqual(random.UInt32(), 2**32 - 1)

  @WithRandomBuffer([0xDEADBEEF, 0xBADDCAFE])
  def testSpecific(self):
    self.assertEqual(random.UInt32(), 0xDEADBEEF)
    self.assertEqual(random.UInt32(), 0xBADDCAFE)


class PositiveUInt32Test(absltest.TestCase):

  @WithRandomBuffer([])
  @WithUrandom(io.BytesIO(b"\x00" * 10 * 1024 + b"\xff" * 10 * 1024).read)
  def testPositive(self, urandom):
    del urandom  # Unused.

    for _ in range(10):
      self.assertGreater(random.PositiveUInt32(), 0)


class UInt64Test(absltest.TestCase):

  @WithRandomBuffer([])
  @WithUrandom(lambda count: b"\x00" * count)
  def testMin(self, urandom):
    del urandom  # Unused.

    for _ in range(10000):
      self.assertEqual(random.UInt64(), 0)

  @WithRandomBuffer([])
  @WithUrandom(lambda count: b"\xff" * count)
  def testMax(self, urandom):
    del urandom  # Unused.

    for _ in range(10000):
      self.assertEqual(random.UInt64(), 2**64 - 1)

  @WithRandomBuffer([0xDEADC0DE, 0xDEADB33F])
  def testSpecific(self):
    self.assertEqual(random.UInt64(), 0xDEADC0DEDEADB33F)


if __name__ == "__main__":
  absltest.main()
