#!/usr/bin/env python
# Lint as: python3
"""A module with utilities for optimized pseudo-random number generation."""
from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

import os
import struct

import threading
from typing import Callable, List

_random_buffer_size = 1024  # type: int
_random_buffer = []  # type: List[int]
_mutex = threading.Lock()


def UInt16() -> int:
  """Returns a pseudo-random 16-bit unsigned integer."""
  return UInt32() & 0xFFFF


def PositiveUInt16() -> int:
  """Returns a pseudo-random 16-bit non-zero unsigned integer."""
  return _Positive(UInt16)


def UInt32() -> int:
  """Returns a pseudo-random 32-bit unsigned integer."""
  with _mutex:
    try:
      return _random_buffer.pop()
    except IndexError:
      data = os.urandom(struct.calcsize("=L") * _random_buffer_size)
      _random_buffer.extend(
          struct.unpack("=" + "L" * _random_buffer_size, data))
      return _random_buffer.pop()


def PositiveUInt32() -> int:
  """Returns a pseudo-random 32-bit non-zero unsigned integer."""
  return _Positive(UInt32)


def UInt64() -> int:
  """Returns a pseudo-random 64-bit unsigned integer."""
  return (UInt32() << 32) | UInt32()


def _Positive(rng: Callable[[], int]) -> int:
  while True:
    result = rng()
    if result > 0:
      return result
