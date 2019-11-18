#!/usr/bin/env python
"""(De-)serialization to bytes, wire format, and human readable strings."""
from __future__ import absolute_import
from __future__ import division

from __future__ import unicode_literals

import abc

from future.builtins import int
from future.utils import with_metaclass

from typing import Text

from grr_response_core.lib import rdfvalue
from grr_response_core.lib.util import precondition


class Converter(with_metaclass(abc.ABCMeta, object)):
  """Interface for (de-)serializing types to bytes, wire format, and strings."""

  @abc.abstractproperty
  def protobuf_type(self):
    pass

  @abc.abstractmethod
  def FromBytes(self, value):
    """Deserializes a value from bytes outputted by ToBytes."""
    pass

  @abc.abstractmethod
  def ToBytes(self, value):
    """Serializes `value` into bytes which can be parsed with FromBytes."""
    pass

  @abc.abstractmethod
  def FromWireFormat(self, value):
    """Deserializes a value from a primitive outputted by ToWireFormat."""
    pass

  @abc.abstractmethod
  def ToWireFormat(self, value):
    """Serializes to a primitive which can be parsed with FromWireFormat."""
    pass

  @abc.abstractmethod
  def FromHumanReadable(self, string):
    """Deserializes a value from a string outputted by str(value)."""
    pass


class BoolConverter(Converter):
  """Converter for Python's `bool`."""
  protobuf_type = "unsigned_integer"
  wrapping_type = bool

  def FromBytes(self, value):
    return bool(int(value))

  def ToBytes(self, value):
    return b"1" if value else b"0"

  def FromWireFormat(self, value):
    precondition.AssertType(value, int)
    return bool(value)

  def ToWireFormat(self, value):
    return 1 if value else 0

  def FromHumanReadable(self, string):
    upper_string = string.upper()
    if upper_string == u"TRUE" or string == u"1":
      return True
    elif upper_string == u"FALSE" or string == u"0":
      return False
    else:
      raise ValueError("Unparsable boolean string: `%s`" % string)


class RDFValueConverter(Converter):
  """Converter for rdfvalue.RDFValue."""

  def __init__(self, cls):
    self._cls = cls

  @property
  def protobuf_type(self):
    return self._cls.protobuf_type

  def FromBytes(self, value):
    return self._cls.FromSerializedBytes(value)

  def ToBytes(self, value):
    precondition.AssertType(value, self._cls)
    return value.SerializeToBytes()

  def FromWireFormat(self, value):
    return self._cls.FromWireFormat(value)

  def ToWireFormat(self, value):
    precondition.AssertType(value, self._cls)
    return value.SerializeToWireFormat()

  def FromHumanReadable(self, string):
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


def FromHumanReadable(cls, string):
  """Deserializes a value of `cls` from a string outputted by str(value)."""
  precondition.AssertType(string, Text)
  return _GetFactory(cls).FromHumanReadable(string)


def ToWireFormat(value):
  """Serializes to a primitive which can be parsed with FromWireFormat."""
  return _GetFactory(type(value)).ToWireFormat(value)


def FromWireFormat(cls, value):
  """Deserializes a value of cls from a primitive outputted by ToWireFormat."""
  return _GetFactory(cls).FromWireFormat(value)


def FromBytes(cls, value):
  """Deserializes a value of `cls` from bytes outputted by ToBytes."""
  precondition.AssertType(value, bytes)
  return _GetFactory(cls).FromBytes(value)


def ToBytes(value):
  """Serializes `value` into bytes which can be parsed with FromBytes."""
  return _GetFactory(type(value)).ToBytes(value)
