#!/usr/bin/env python
"""(De-)serialization to bytes, wire format, and human readable strings."""

import abc

from grr_response_core.lib import rdfvalue
from grr_response_core.lib.util import precondition


class Converter(metaclass=abc.ABCMeta):
  """Interface for (de-)serializing types to bytes, wire format, and strings."""

  @abc.abstractproperty
  def protobuf_type(self):
    pass

  @abc.abstractmethod
  def FromBytes(self, value: bytes):
    """Deserializes a value from bytes outputted by ToBytes."""

  @abc.abstractmethod
  def ToBytes(self, value) -> bytes:
    """Serializes `value` into bytes which can be parsed with FromBytes."""

  @abc.abstractmethod
  def FromWireFormat(self, value):
    """Deserializes a value from a primitive outputted by ToWireFormat."""

  @abc.abstractmethod
  def ToWireFormat(self, value):
    """Serializes to a primitive which can be parsed with FromWireFormat."""

  @abc.abstractmethod
  def FromHumanReadable(self, string: str):
    """Deserializes a value from a string outputted by str(value)."""


class BoolConverter(Converter):
  """Converter for Python's `bool`."""

  protobuf_type = "unsigned_integer"
  wrapping_type = bool

  def FromBytes(self, value: bytes) -> bool:
    return bool(int(value))

  def ToBytes(self, value: bool) -> bytes:
    return b"1" if value else b"0"

  def FromWireFormat(self, value: int) -> bool:
    precondition.AssertType(value, int)
    return bool(value)

  def ToWireFormat(self, value: bool) -> int:
    return 1 if value else 0

  def FromHumanReadable(self, string: str) -> bool:
    upper_string = string.upper()
    if upper_string == "TRUE" or string == "1":
      return True
    elif upper_string == "FALSE" or string == "0":
      return False
    else:
      raise ValueError("Unparsable boolean string: `%s`" % string)


class RDFValueConverter(Converter):
  """Converter for rdfvalue.RDFValue."""

  def __init__(self, cls):
    super().__init__()
    self._cls = cls

  @property
  def protobuf_type(self):
    return self._cls.protobuf_type

  def FromBytes(self, value: bytes):
    return self._cls.FromSerializedBytes(value)

  def ToBytes(self, value: rdfvalue.RDFValue) -> bytes:
    precondition.AssertType(value, self._cls)
    return value.SerializeToBytes()

  def FromWireFormat(self, value):
    return self._cls.FromWireFormat(value)

  def ToWireFormat(self, value: rdfvalue.RDFValue):
    precondition.AssertType(value, self._cls)
    return value.SerializeToWireFormat()

  def FromHumanReadable(self, string: str) -> rdfvalue.RDFValue:
    if issubclass(self._cls, rdfvalue.RDFPrimitive):
      return self._cls.FromHumanReadable(string)
    else:
      raise ValueError()


def _GetFactory(cls):
  precondition.AssertType(cls, type)
  if issubclass(cls, rdfvalue.RDFValue):
    return RDFValueConverter(cls)
  elif cls is bool:
    return BoolConverter()
  raise ValueError("Unknown class {}".format(cls))


def GetProtobufType(cls):
  """Returns the protobuf type required by structs.py for the given cls."""
  return _GetFactory(cls).protobuf_type


def FromHumanReadable(cls, string: str):
  """Deserializes a value of `cls` from a string outputted by str(value)."""
  precondition.AssertType(string, str)
  return _GetFactory(cls).FromHumanReadable(string)


def ToWireFormat(value):
  """Serializes to a primitive which can be parsed with FromWireFormat."""
  return _GetFactory(type(value)).ToWireFormat(value)


def FromWireFormat(cls, value):
  """Deserializes a value of cls from a primitive outputted by ToWireFormat."""
  return _GetFactory(cls).FromWireFormat(value)


def FromBytes(cls, value: bytes):
  """Deserializes a value of `cls` from bytes outputted by ToBytes."""
  precondition.AssertType(value, bytes)
  return _GetFactory(cls).FromBytes(value)


def ToBytes(value) -> bytes:
  """Serializes `value` into bytes which can be parsed with FromBytes."""
  return _GetFactory(type(value)).ToBytes(value)
