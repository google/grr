#!/usr/bin/env python
"""Utilities for working with WMI queries and their values through RRG."""

import ctypes
from typing import Optional

from grr_response_proto.rrg.action import query_wmi_pb2 as rrg_query_wmi_pb2

# All functions below are used for conversion from WMI type as returned by the
# _"Automation"_ (whatever that exactly is but this is what handles these values
# to RRG) to a type as defined by the specific table [1].
#
# [1]: https://learn.microsoft.com/en-us/windows/win32/wmisdk/numbers


def SInt8(value: rrg_query_wmi_pb2.Value) -> Optional[int]:
  """Returns integer corresponding to a `sint8` column."""
  # From `VT_I2`.
  if not value.HasField("int"):
    return None

  if not (-(2**7) <= value.int < 2**7):
    raise ValueError(f"Out-of-range sint8 value: {value.int}")
  return value.int


def SInt16(value: rrg_query_wmi_pb2.Value) -> Optional[int]:
  """Returns integer corresponding to a `sint16` column."""
  # From `VT_I2`.
  if not value.HasField("int"):
    return None

  if not (-(2**15) <= value.int < 2**15):
    raise ValueError(f"Out-of-range sint16 value: {value.int}")
  return value.int


def SInt32(value: rrg_query_wmi_pb2.Value) -> Optional[int]:
  """Returns integer corresponding to a `sint32` column."""
  # From `VT_I4`.
  if not value.HasField("int"):
    return None

  if not (-(2**31) <= value.int < 2**31):
    raise ValueError(f"Out-of-range sint32 value: {value.int}")
  return value.int


def SInt64(value: rrg_query_wmi_pb2.Value) -> Optional[int]:
  """Returns integer corresponding to a `sint64` column."""
  # From `VT_BSTR`.
  if not value.string:
    return None

  # We use "0" as the `int` call base: this triggers "guess" mode: it will try
  # to parse it as integer literal [1]. This is exactly what we want as 64-bit
  # numbers can be decimal or hexadecimal strings in ANSI C formatting rules
  # (so a subset of what Python supports).
  #
  # [1]: https://docs.python.org/3/reference/lexical_analysis.html#integers
  result = int(value.string, 0)
  if not (-(2**63) <= result < 2**63):
    raise ValueError(f"Out-of-range sint64 value: {result}")
  return result


def Real32(value: rrg_query_wmi_pb2.Value) -> Optional[float]:
  """Returns float corresponding to a `real32` column."""
  # From `VT_R4`.
  if not value.HasField("float"):
    return None

  return value.float


def Real64(value: rrg_query_wmi_pb2.Value) -> Optional[float]:
  """Returns float corresponding to a `real64` column."""
  # From `VT_R8`.
  if not value.HasField("double"):
    return None

  return value.double


def UInt8(value: rrg_query_wmi_pb2.Value) -> Optional[int]:
  """Returns integer corresponding to a `uint8` column."""
  if not value.HasField("uint"):
    return None

  # From `VT_UI1`.
  if not (0 <= value.uint < 2**8):
    raise ValueError(f"Out-of-range uint8 value: {value.uint}")
  return value.uint


def UInt16(value: rrg_query_wmi_pb2.Value) -> Optional[int]:
  """Returns integer corresponding to a `uint16` column."""
  # From `VT_I4`.
  if not value.HasField("int"):
    return None

  if not (0 <= value.int < 2**16):
    raise ValueError(f"Out-of-range uint16 value: {value.int}")
  return value.int


def UInt32(value: rrg_query_wmi_pb2.Value) -> Optional[int]:
  """Returns integer corresponding to a `uint32` column."""
  # From `VT_I4`.
  if not value.HasField("int"):
    return None

  if not (-(2**31) <= value.int < 2**31):
    raise ValueError(f"Out-of-range uint32 value: {value.int}")

  # The whole ceremony below is just a (reinterpreted) cast from `int32` to
  # `uint32`.
  ptr_int32 = ctypes.pointer(ctypes.c_int32(value.int))
  ptr_uint32 = ctypes.cast(ptr_int32, ctypes.POINTER(ctypes.c_uint32))

  return ptr_uint32.contents.value


def UInt64(value: rrg_query_wmi_pb2.Value) -> Optional[int]:
  """Returns integer corresponding to a `uint64` column."""
  # From `VT_BSTR`.
  if not value.string:
    return None

  # We use "0" as the `int` call base: this triggers "guess" mode: it will try
  # to parse it as integer literal [1]. This is exactly what we want as 64-bit
  # numbers can be decimal or hexadecimal strings in ANSI C formatting rules
  # (so a subset of what Python supports).
  #
  # [1]: https://docs.python.org/3/reference/lexical_analysis.html#integers
  result = int(value.string, 0)
  if not (0 <= result < 2**64):
    raise ValueError(f"Out-of-range uint64 value: {result}")
  return result
