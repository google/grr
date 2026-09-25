#!/usr/bin/env python
"""Helpers for testing RRG-related WMI code."""

import abc
import ctypes

from grr_response_proto.rrg.action import query_wmi_pb2 as rrg_query_wmi_pb2


class Type(abc.ABC):
  """Abstract base class for WMI wrappers of _"Automation"_ types.

  These are used to write more idiomatic tests by using type definitions for
  a particular WMI table without worrying about the underlying conversion
  shenanigans [1].

  [1]: https://learn.microsoft.com/en-us/windows/win32/wmisdk/numbers
  """

  @property
  @abc.abstractmethod
  def value(self) -> rrg_query_wmi_pb2.Value:
    ...


class SInt8(Type):
  """Wrapper for `sint8`."""

  def __init__(self, value: int):
    assert -(2**7) <= value < 2**7
    self._value = value

  @property
  def value(self) -> rrg_query_wmi_pb2.Value:
    return rrg_query_wmi_pb2.Value(int=self._value)


class SInt16(Type):
  """Wrapper for `sint16`."""

  def __init__(self, value: int):
    assert -(2**15) <= value < 2**15
    self._value = value

  @property
  def value(self) -> rrg_query_wmi_pb2.Value:
    return rrg_query_wmi_pb2.Value(int=self._value)


class SInt32(Type):
  """Wrapper for `sint32`."""

  def __init__(self, value: int):
    assert -(2**31) <= value < 2**31
    self._value = value

  @property
  def value(self) -> rrg_query_wmi_pb2.Value:
    return rrg_query_wmi_pb2.Value(int=self._value)


class SInt64(Type):
  """Wrapper for `sint64`."""

  def __init__(self, value: int):
    assert -(2**63) <= value < 2**63
    self._value = value

  @property
  def value(self) -> rrg_query_wmi_pb2.Value:
    return rrg_query_wmi_pb2.Value(string=str(self._value))


class Real32(Type):
  """Wrapper for `real32`."""

  def __init__(self, value: float):
    self._value = value

  @property
  def value(self) -> rrg_query_wmi_pb2.Value:
    return rrg_query_wmi_pb2.Value(float=self._value)


class Real64(Type):
  """Wrapper for `real64`."""

  def __init__(self, value: float):
    self._value = value

  @property
  def value(self) -> rrg_query_wmi_pb2.Value:
    return rrg_query_wmi_pb2.Value(double=self._value)


class UInt8(Type):
  """Wrapper for `uint8`."""

  def __init__(self, value: int):
    assert 0 <= value < 2**8
    self._value = value

  @property
  def value(self) -> rrg_query_wmi_pb2.Value:
    return rrg_query_wmi_pb2.Value(uint=self._value)


class UInt16(Type):
  """Wrapper for `uint16`."""

  def __init__(self, value: int):
    assert 0 <= value < 2**16
    self._value = value

  @property
  def value(self) -> rrg_query_wmi_pb2.Value:
    return rrg_query_wmi_pb2.Value(int=self._value)


class UInt32(Type):
  """Wrapper for `uint32`."""

  def __init__(self, value: int):
    assert 0 <= value < 2**32
    self._value = value

  @property
  def value(self) -> rrg_query_wmi_pb2.Value:
    # The whole ceremony below is just a (reinterpreted) cast from `uint32` to
    # `int32`.
    ptr_uint32 = ctypes.pointer(ctypes.c_uint32(self._value))
    ptr_int32 = ctypes.cast(ptr_uint32, ctypes.POINTER(ctypes.c_int32))

    return rrg_query_wmi_pb2.Value(int=ptr_int32.contents.value)


class UInt64(Type):
  """Wrapper for `uint64`."""

  def __init__(self, value: int):
    assert 0 <= value < 2**64
    self._value = value

  @property
  def value(self) -> rrg_query_wmi_pb2.Value:
    return rrg_query_wmi_pb2.Value(string=str(self._value))
