#!/usr/bin/env python
"""A module with utilities for optimized pseudo-random number generation."""
from __future__ import absolute_import
from __future__ import division

from __future__ import unicode_literals

import os
import struct

from typing import Callable
from typing import List

_random_buffer_size = 1024  # type: int
_random_buffer = []  # type: List[int]


def UInt16():
  """Returns a pseudo-random 16-bit unsigned integer."""
  return UInt32() & 0xFFFF


def PositiveUInt16():
  """Returns a pseudo-random 16-bit non-zero unsigned integer."""
  return _Positive(UInt16)


def UInt32():
  """Returns a pseudo-random 32-bit unsigned integer."""
  global _random_buffer

  if not _random_buffer:
    data = os.urandom(struct.calcsize("=L") * _random_buffer_size)
    _random_buffer = list(struct.unpack("=" + "L" * _random_buffer_size, data))

  return _random_buffer.pop()


def PositiveUInt32():
  """Returns a pseudo-random 32-bit non-zero unsigned integer."""
  return _Positive(UInt32)


def UInt64():
  """Returns a pseudo-random 64-bit unsigned integer."""
  return (UInt32() << 32) | UInt32()


def _Positive(rng):
  while True:
    result = rng()
    if result > 0:
      return result
