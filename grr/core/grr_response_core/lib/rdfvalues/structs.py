#!/usr/bin/env python
"""Semantic Protobufs are serialization agnostic, rich data types."""

import base64
from collections import abc
from collections.abc import ByteString, Iterator, Sequence
import copy
import functools
import logging
import struct
from typing import Optional, TypeVar, cast

from google.protobuf import any_pb2
from google.protobuf import wrappers_pb2
from google.protobuf import message as proto2_message
from google.protobuf import text_format
from grr_response_core import _semantic
from grr_response_core.lib import rdfvalue
from grr_response_core.lib import registry
from grr_response_core.lib import serialization
from grr_response_core.lib import type_info
from grr_response_core.lib import utils
from grr_response_core.lib.rdfvalues import proto2 as rdf_proto2
from grr_response_core.lib.util import precondition
from grr_response_proto import semantic_pb2


# pylint: disable=invalid-name
VarintEncode = _semantic.varint_encode
VarintReader = _semantic.varint_decode
SplitBuffer = _semantic.split_buffer
# pylint: enable=invalid-name

# These numbers identify the wire type of a protocol buffer value.
# We use the least-significant TAG_TYPE_BITS bits of the varint-encoded
# tag-and-type to store one of these WIRETYPE_* constants.
# These values must match WireType enum in google/protobuf/wire_format.h.
WIRETYPE_VARINT = 0
WIRETYPE_FIXED64 = 1
WIRETYPE_LENGTH_DELIMITED = 2

# We do not support these deprecated wire types any more. Nested protobufs are
# stored using the normal WIRETYPE_LENGTH_DELIMITED tag.
WIRETYPE_START_GROUP = 3
WIRETYPE_END_GROUP = 4

WIRETYPE_FIXED32 = 5


def SignedVarintEncode(value):
  """Encode a signed integer as a signed varint."""
  if value < 0:
    value += 1 << 64

  return VarintEncode(value)


def SignedVarintReader(buf, pos=0):
  """A signed 64 bit decoder for signed varints."""
  result, p = VarintReader(buf, pos)
  if result > 0x7FFFFFFFFFFFFFFF:
    result -= 1 << 64

  return (result, p)


def _GetOrderedEntries(data):
  """Gets entries of `RDFProtoStruct` in a well-defined order.

  Args:
    data: A raw data dictionary of `RDFProtoStruct`.

  Returns:
    Entries of the structured in a well-defined order.
  """

  # Sort struct entries by their field tag.
  def Tag(entry):
    _, wire_format, type_descriptor = entry
    if type_descriptor is not None:
      encoded_tag = type_descriptor.encoded_tag
    elif wire_format is not None:
      encoded_tag = wire_format[0]
    else:
      raise AssertionError(
          "Each entry is expected to have "
          "either a type_descriptor or wire_format."
      )

    return VarintReader(encoded_tag, 0)[0]

  return sorted(data.values(), key=Tag)


def _SerializeEntries(entries):
  """Serializes given triplets of python and wire values and a descriptor."""

  output = []
  for python_format, wire_format, type_descriptor in entries:

    if wire_format is None or (
        python_format and type_descriptor.IsDirty(python_format)
    ):
      wire_format = type_descriptor.ConvertToWireFormat(python_format)

    precondition.AssertIterableType(wire_format, bytes)
    output.extend(wire_format)

  return b"".join(output)


def ReadIntoObject(buff, index, value_obj, length=0):
  """Reads all tags until the next end group and store in the value_obj."""
  raw_data = value_obj.GetRawData()
  count = 0

  # Split the buffer into tags and wire_format representations, then collect
  # these into the raw data cache.
  for encoded_tag, encoded_length, encoded_field in SplitBuffer(
      buff, index=index, length=length
  ):

    type_info_obj = value_obj.type_infos_by_encoded_tag.get(encoded_tag)

    # Internal format to store parsed fields.
    wire_format = (encoded_tag, encoded_length, encoded_field)

    # If the tag is not found we need to skip it. Skipped fields are
    # inaccessible to this actual object, because they have no type info
    # describing them, however they are still stored in the raw data
    # representation because they will be re-serialized back. This way
    # programs which simply read protobufs and write them back do not need to
    # know all the fields, some of which were defined in a later version of
    # the application. In order to avoid having to worry about repeated fields
    # here, we just insert them into the raw data dict with a key which should
    # be unique.
    if type_info_obj is None:
      # Record an unknown field. The key is unique and ensures we do not collide
      # the dict on repeated fields of the encoded tag. Note that this field is
      # not really accessible using Get() and does not have a python format
      # representation. It will be written back using the same wire format it
      # was read with, therefore does not require a type descriptor at all.
      field_nr = VarintReader(encoded_tag, 0)[0] >> 3
      raw_data["_unknown_field_%d" % field_nr] = (None, wire_format, None)

      count += 1

    # Repeated fields are handled especially.
    elif type_info_obj.__class__ is ProtoList:
      value_obj.Get(type_info_obj.name).wrapped_list.append((None, wire_format))

    else:
      # Set the python_format as None so it gets converted lazily on access.
      raw_data[type_info_obj.name] = (None, wire_format, type_info_obj)

  value_obj.SetRawData(raw_data)


class ProtoType(type_info.TypeInfoObject):
  """A specific type descriptor for protobuf fields.

  This is an abstract class - do not instantiate directly.
  """

  # Must be overridden by implementations.
  wire_type: int

  # We cache the serialized version of the tag here so we just need to do a
  # string comparison instead of decoding the tag each time.
  encoded_tag = None

  # The semantic type of the object described by this descriptor.
  type = None

  # The type name according to the .proto domain specific language.
  proto_type_name = "string"

  # A field may be defined but not added to the container immediately. In that
  # case we wait for late binding to resolve the target and then bind the field
  # to the protobuf descriptor set only when its target is resolved.
  late_bound = False

  # The Semantic protobuf class which owns this field descriptor.
  owner = None

  # This flag indicates if the default should be set into the owner protobuf on
  # access.
  set_default_on_access = False

  def __init__(
      self,
      field_number=None,
      required=False,
      labels=None,
      set_default_on_access=None,
      **kwargs,
  ):
    super().__init__(**kwargs)
    # TODO: Without this type hint, pytype thinks that field_number
    # is always None.
    self.field_number: int = field_number
    self.required = required
    if set_default_on_access is not None:
      self.set_default_on_access = set_default_on_access

    self.labels = labels or []
    if self.field_number is None:
      raise type_info.TypeValueError("No valid field number specified.")

    self.CalculateTags()

  def Copy(self, field_number=None):
    """Returns a copy of descriptor, optionally changing the field number."""
    result = copy.copy(self)
    if field_number is not None:
      result.field_number = field_number
      result.CalculateTags()

    return result

  def CalculateTags(self):
    # In python Varint encoding is expensive so we want to move as much of the
    # hard work from the Write() methods which are called frequently to the type
    # descriptor constructor which is only called once (during protobuf
    # declaration time). Pre-calculating the tag makes for faster serialization.
    self.tag = self.field_number << 3 | self.wire_type
    self.encoded_tag = VarintEncode(self.tag)

  def IsDirty(self, unused_python_format):
    """Return and clear the dirty state of the python object."""
    return False

  def ConvertFromWireFormat(self, value, container=None):
    """Convert value from the internal type to the real type.

    When data is being parsed, it might be quicker to store it in a different
    format internally. This is because we must parse all tags, but only decode
    those fields which are being accessed.

    This function is called when we retrieve a field on access, so we only pay
    the penalty once, and cache the result.

    Internally the wire format is a tuple of:
      (encoded_tag, optional_encoded_length, encoded_data)

    All items are strings. For length encoded fields, the
    optional_encoded_length should be the encoded length of encoded_data,
    otherwise it should be the empty string. The idea is that the encoder simply
    concatenates all the wire formats together to form the final message without
    delegating to the field descriptors.

    This function is HOT.

    Args:
      value: A parameter stored in the wire format for this type.
      container: The protobuf that contains this field.

    Returns:
      The parameter encoded in the python format representation.
    """
    raise NotImplementedError

  def ConvertToWireFormat(self, value):
    """Convert the parameter into the internal storage format.

    This function is the inverse of ConvertFromWireFormat(). See the description
    above for the exact layout of the internal wire format.

    This function is HOT.

    Args:
      value: A python format representation of the value as coerced by the
        Validate() method. This is type specific, but always the same.

    Returns:
      The parameter encoded in the wire format representation.
    """
    raise NotImplementedError

  def _FormatDescriptionComment(self):
    result = "".join(["\n  // %s\n" % x for x in self.description.splitlines()])
    return result

  def _FormatDefault(self):
    return " [default = %s]" % self.GetDefault()

  def _FormatField(self):
    result = "  optional %s %s = %s%s" % (
        self.proto_type_name,
        self.name,
        self.field_number,
        self._FormatDefault(),
    )

    return result + ";\n"

  def Definition(self):
    """Return a string with the definition of this field."""
    return self._FormatDescriptionComment() + self._FormatField()

  def Format(self, value) -> Iterator[str]:
    """A Generator for display lines representing value."""
    yield str(value)

  def Validate(self, value, container=None):
    """Validate the value."""
    _ = container
    return value

  def GetDefault(self, container=None):
    _ = container
    return self.default

  def __str__(self) -> str:
    # TODO: This fails for ProtoList.
    return "<Field %s (%s) of %s: field_number: %s>" % (
        self.name,
        self.__class__.__name__,
        self.owner.__name__,
        self.field_number,
    )

  def SetOwner(self, owner):
    self.owner = owner


class ProtoString(ProtoType):
  """A string encoded in a protobuf."""

  wire_type = WIRETYPE_LENGTH_DELIMITED

  # This descriptor describes unicode strings.
  type = rdfvalue.RDFString

  def __init__(self, default="", **kwargs):
    # Strings default to "" if not specified.
    super().__init__(**kwargs)

    # Ensure the default is a unicode object.
    if default is not None:
      self.default = utils.SmartUnicode(default)

  def GetDefault(self, container=None):
    _ = container
    return self.default

  def Validate(self, value, **_) -> str:  # pytype: disable=signature-mismatch  # overriding-parameter-count-checks
    """Validates a python format representation of the value."""
    if isinstance(value, rdfvalue.RDFString):
      # TODO(hanuszczak): Use `str` here.
      return str(value)

    if isinstance(value, str):
      return value

    if isinstance(value, bytes):
      return value.decode("utf-8")

    raise type_info.TypeValueError(
        "Not a valid unicode string: {!r} of type {}".format(
            value, type(value).__name__
        )
    )

  def ConvertFromWireFormat(self, value, container=None):
    """Internally strings are utf8 encoded."""
    try:
      return value[2].decode("utf8")
    except UnicodeDecodeError:
      raise rdfvalue.DecodeError("Unicode decoding error")

  def ConvertToWireFormat(self, value):
    """Internally strings are utf8 encoded."""
    value = value.encode("utf8")
    return (self.encoded_tag, VarintEncode(len(value)), value)

  def Definition(self):
    """Return a string with the definition of this field."""
    return self._FormatDescriptionComment() + self._FormatField()

  def _FormatDefault(self):
    if self.GetDefault():
      return " [default = %r]" % self.GetDefault()
    else:
      return ""

  def Format(self, value):
    yield repr(value)


class ProtoBinary(ProtoType):
  """A binary string encoded in a protobuf."""

  wire_type = WIRETYPE_LENGTH_DELIMITED

  # This descriptor describes strings.
  type = rdfvalue.RDFBytes

  proto_type_name = "bytes"

  def __init__(self, default=b"", **kwargs):
    precondition.AssertType(default, bytes)

    # Byte strings default to "" if not specified.
    super().__init__(**kwargs)

    # Ensure the default is a string object.
    if default is not None:
      self.default = default

  def Validate(self, value, **_):  # pytype: disable=signature-mismatch  # overriding-parameter-count-checks
    if not isinstance(value, bytes):
      raise type_info.TypeValueError("Required bytes, got %r" % value)

    return value

  def ConvertFromWireFormat(self, value, container=None):
    return value[2]

  def ConvertToWireFormat(self, value):
    return (self.encoded_tag, VarintEncode(len(value)), value)

  def Definition(self):
    """Return a string with the definition of this field."""
    return self._FormatDescriptionComment() + self._FormatField()

  def Format(self, value):
    yield repr(value)

  def _FormatDefault(self):
    if self.GetDefault():
      return " [default = %r]" % self.GetDefault()
    else:
      return ""


class ProtoUnsignedInteger(ProtoType):
  """An unsigned VarInt encoded in the protobuf."""

  wire_type = WIRETYPE_VARINT

  # This descriptor describes integers.
  type = rdfvalue.RDFInteger
  proto_type_name = "uint64"

  def __init__(self, default=0, **kwargs):
    # Integers default to 0 if not specified.
    super().__init__(default=default, **kwargs)

  def ConvertFromWireFormat(self, value, container=None):
    return VarintReader(value[2], 0)[0]

  def ConvertToWireFormat(self, value):
    return (self.encoded_tag, b"", VarintEncode(value))

  def Validate(self, value, **_):  # pytype: disable=signature-mismatch  # overriding-parameter-count-checks
    try:
      return int(value)
    except ValueError:
      raise type_info.TypeValueError("Invalid value %s for Integer" % value)

  def _FormatDefault(self):
    if self.GetDefault():
      return " [default = %r]" % self.GetDefault()
    else:
      return ""


class ProtoSignedInteger(ProtoUnsignedInteger):
  """A signed VarInt encoded in the protobuf.

  Note: signed VarInts are more expensive than unsigned VarInts.
  """

  proto_type_name = "int64"

  def ConvertFromWireFormat(self, value, container=None):
    return SignedVarintReader(value[2])[0]

  def ConvertToWireFormat(self, value):
    return (self.encoded_tag, b"", SignedVarintEncode(value))


class ProtoFixed32(ProtoUnsignedInteger):
  """A 32 bit fixed unsigned integer.

  The wire format is a 4 byte string, while the python type is an int.
  """

  _size = 4

  proto_type_name = "sfixed32"
  wire_type = WIRETYPE_FIXED32

  def ConvertToWireFormat(self, value):
    return (self.encoded_tag, b"", struct.pack("<L", int(value)))

  def ConvertFromWireFormat(self, value, container=None):
    return struct.unpack("<L", value[2])[0]


class ProtoFixed64(ProtoFixed32):
  _size = 8

  proto_type_name = "sfixed64"
  wire_type = WIRETYPE_FIXED64

  def ConvertToWireFormat(self, value):
    return (self.encoded_tag, b"", struct.pack("<Q", int(value)))

  def ConvertFromWireFormat(self, value, container=None):
    return struct.unpack("<Q", value[2])[0]


class ProtoFixedU32(ProtoFixed32):
  """A 32 bit fixed unsigned integer.

  The wire format is a 4 byte string, while the python type is an int.
  """

  proto_type_name = "fixed32"

  def ConvertToWireFormat(self, value):
    return (self.encoded_tag, b"", struct.pack("<l", int(value)))

  def ConvertFromWireFormat(self, value, container=None):
    return struct.unpack("<l", value[2])[0]


class ProtoFloat(ProtoFixed32):
  """A float.

  The wire format is a 4 byte string, while the python type is a float.
  """

  proto_type_name = "float"

  def Validate(self, value, **_):
    if not rdfvalue.RDFInteger.IsNumeric(value):
      raise type_info.TypeValueError("Invalid value %s for Float" % value)

    return value

  def ConvertToWireFormat(self, value):
    return (self.encoded_tag, b"", struct.pack("<f", float(value)))

  def ConvertFromWireFormat(self, value, container=None):
    return struct.unpack("<f", value[2])[0]


class ProtoDouble(ProtoFixed64):
  """A double.

  The wire format is a 8 byte string, while the python type is a float.
  """

  proto_type_name = "double"

  def Validate(self, value, **_):
    if not rdfvalue.RDFInteger.IsNumeric(value):
      raise type_info.TypeValueError("Invalid value %s for Integer" % value)

    return value

  def ConvertToWireFormat(self, value):
    return (self.encoded_tag, b"", struct.pack("<d", float(value)))

  def ConvertFromWireFormat(self, value, container=None):
    return struct.unpack("<d", value[2])[0]


@functools.total_ordering
class EnumNamedValue(rdfvalue.RDFPrimitive):
  """A class that wraps enums.

  Enums are just integers, except when printed they have a name.
  """

  protobuf_type = "integer"

  def __init__(
      self, initializer=None, name=None, description=None, labels=None
  ):

    if initializer is None:
      initializer = 0

    if name is None:
      name = str(initializer)

    if labels is None:
      labels = ()

    precondition.AssertType(name, str)
    precondition.AssertOptionalType(description, str)
    precondition.AssertIterableType(labels, int)

    super().__init__((int(initializer), name, description, tuple(labels)))

  @property
  def id(self):
    return self._value[0]

  @property
  def name(self):
    return self._value[1]

  @property
  def description(self):
    return self._value[2]

  @property
  def labels(self):
    return self._value[3]

  # Required, because in Python 3 overriding `__eq__` nullifies `__hash__`.
  def __hash__(self):
    return hash(self.id)

  def __eq__(self, other):
    # `other` needs to be LHS, because future newstr does not properly return
    # NotImplemented on type mismatch.
    return other == self.id or other == self.name

  def __lt__(self, other):
    if isinstance(other, EnumNamedValue):
      return (self.id, self.name) < (other.id, other.name)
    return NotImplemented

  def __str__(self) -> str:
    return self.name

  def __repr__(self):
    return "{}(initializer={!r}, name={!r})".format(
        type(self).__name__, self.id, self.name
    )

  def __int__(self):
    return self.id

  def __index__(self):
    return self.id

  def __bool__(self):
    return bool(self.id)

  def Copy(self):
    return type(self)(self.id, self.name, self.description, self.labels)

  def SerializeToBytes(self) -> bytes:
    return str(self.id).encode("ascii")

  @classmethod
  def FromSerializedBytes(cls, value: bytes):
    precondition.AssertType(value, bytes)

    if value:
      return cls(int(value))
    else:
      return cls(0)

  @classmethod
  def FromHumanReadable(cls, string: str):
    precondition.AssertType(string, str)

    try:
      num = int(string)
    except ValueError:
      num = 0

    return cls(num, name=string)

  @classmethod
  def FromWireFormat(cls, value):
    return cls(initializer=value)

  def SerializeToWireFormat(self):
    return self.id


class ProtoEnum(ProtoSignedInteger):
  """An enum native proto type.

  This is really encoded as an integer but only certain values are allowed.
  """

  type = EnumNamedValue

  def __init__(
      self,
      default=None,
      enum_name=None,
      enum=None,
      enum_descriptions=None,
      enum_labels=None,
      **kwargs,
  ):
    super().__init__(**kwargs)
    if enum_name is None:
      raise type_info.TypeValueError("Enum groups must be given a name.")

    self.enum_name = enum_name
    self.proto_type_name = enum_name
    if isinstance(enum, EnumContainer):
      enum = enum.enum_dict

    for v in enum.values():
      if v.__class__ is not int:
        raise type_info.TypeValueError("Enum values must be integers.")

    self.enum_container = EnumContainer(
        name=enum_name,
        descriptions=enum_descriptions,
        enum_labels=enum_labels,
        values=(enum or {}),
    )
    self.enum = self.enum_container.enum_dict
    self.reverse_enum = self.enum_container.reverse_enum

    # Ensure the default is a valid enum value.
    if default is not None:
      self.default = self.Validate(default)

  def GetDefault(self, container=None):
    _ = container
    return EnumNamedValue(
        self.default, name=self.reverse_enum.get(self.default)
    )

  def Validate(self, value, **_):
    """Check that value is a valid enum."""
    # None is a valid value - it means the field is not set.
    if value is None:
      return

    # If the value is a string we need to try to convert it to an integer.
    checked_value = value
    if isinstance(value, str):
      # NOTE: that when initializing from string, enum values are
      # case-insensitive.
      checked_value = self.enum.get(value.upper())
      if checked_value is None and value.isdigit():
        checked_value = int(value)
      if checked_value is None:
        raise type_info.TypeValueError(
            "Value %s is not a valid enum value for field %s"
            % (value, self.name)
        )

    return EnumNamedValue(checked_value, name=self.reverse_enum.get(value))

  def Definition(self):
    """Return a string with the definition of this field."""
    result = self._FormatDescriptionComment()

    result += "  enum %s {\n" % self.enum_name
    for k, v in sorted(self.reverse_enum.items()):
      result += "    %s = %s;\n" % (v, k)

    result += "  }\n"

    result += self._FormatField()
    return result

  def Format(self, value):
    yield self.reverse_enum.get(value, str(value))

  def ConvertToWireFormat(self, value):
    return (self.encoded_tag, b"", SignedVarintEncode(int(value)))

  def ConvertFromWireFormat(self, value, container=None):
    value = SignedVarintReader(value[2], 0)[0]
    return EnumNamedValue(value, name=self.reverse_enum.get(value))


class ProtoBoolean(ProtoEnum):
  """A Boolean."""

  type = bool

  def __init__(self, **kwargs):
    super().__init__(enum_name="Bool", enum={"True": 1, "False": 0}, **kwargs)

    self.proto_type_name = "bool"

  def GetDefault(self, container=None):
    """Return boolean value."""
    return bool(int(super().GetDefault(container=container)))

  def Validate(self, value, **_):
    """Check that value is a valid enum."""
    if value is None:
      return

    return bool(int(super().Validate(value)))

  def ConvertFromWireFormat(self, value, container=None):
    return bool(int(super().ConvertFromWireFormat(value, container=container)))

  def ConvertToWireFormat(self, value):
    return super().ConvertToWireFormat(bool(value))


class ProtoEmbedded(ProtoType):
  """A field may be embedded as a serialized protobuf.

  Embedding is more efficient than nesting since the emebedded protobuf does not
  need to be parsed at all, if the user does not access any elements in it.

  Embedded protobufs are simply serialized as bytes using the wire format
  WIRETYPE_LENGTH_DELIMITED. Hence the wire format is a simple python string,
  but the python format representation is an RDFProtoStruct.
  """

  wire_type = WIRETYPE_LENGTH_DELIMITED

  # When we access a nested protobuf we automatically create it and assign it to
  # the owner protobuf.
  set_default_on_access = True

  def __init__(self, nested=None, **kwargs):
    super().__init__(**kwargs)

    # Nested can refer to a target RDFProtoStruct by name.
    if isinstance(nested, str):
      self.proto_type_name = nested

      # Try to resolve the type it names
      self.type = rdfvalue.RDFValue.classes.get(nested, None)

      # We do not know about this type yet. Implement Late Binding.
      if self.type is None:
        self.late_bound = True

        # Register a late binding callback.
        rdfvalue.RegisterLateBindingCallback(nested, self.LateBind)

    # Or it can be an subclass of RDFProtoStruct.
    elif issubclass(nested, RDFProtoStruct):
      self.type = nested
      self.proto_type_name = nested.__name__

    else:
      raise type_info.TypeValueError(
          "Only RDFProtoStructs can be nested, not %s" % nested.__name__
      )

  def ConvertFromWireFormat(self, value, container=None):
    """The wire format is simply a string."""
    result = self.type()
    ReadIntoObject(value[2], 0, result)

    return result

  def ConvertToWireFormat(self, value):
    """Encode the nested protobuf into wire format."""
    output = _SerializeEntries(_GetOrderedEntries(value.GetRawData()))
    return (self.encoded_tag, VarintEncode(len(output)), output)

  def LateBind(self, target=None):
    """Late binding callback.

    This method is called on this field descriptor when the target RDFValue
    class is finally defined. It gives the field descriptor an opportunity to
    initialize after the point of definition.

    Args:
      target: The target nested class.

    Raises:
      TypeError: If the target class is not of the expected type.
    """
    if not issubclass(target, RDFProtoStruct):
      raise TypeError(
          "Field %s expects a protobuf, but target is %s" % (self, target)
      )

    self.late_bound = False

    # The target type is now resolved.
    self.type = target

    # Register us in our owner.
    self.owner.AddDescriptor(self)

  def IsDirty(self, proto):
    """Return and clear the dirty state of the python object."""
    if proto.dirty:
      return True

    for python_format, _, type_descriptor in proto.GetRawData().values():
      if python_format is not None and type_descriptor.IsDirty(python_format):
        proto.dirty = True
        return True

    return False

  def GetDefault(self, container=None):
    """When a nested proto is accessed, default to an empty one."""
    return self.type()

  def Validate(self, value, **_):  # pytype: disable=signature-mismatch  # overriding-parameter-count-checks
    if isinstance(value, str):
      raise type_info.TypeValueError(
          "Field %s must be of type %s" % (self.name, self.type.__name__)
      )

    # We may coerce it to the correct type.
    if value.__class__ is not self.type:
      try:
        value = self.type(value)
      except rdfvalue.InitializeError as e:
        raise type_info.TypeValueError(
            "Field %s must be of type %s" % (self.name, self.type.__name__)
        ) from e

    return value

  def Definition(self):
    """Return a string with the definition of this field."""
    return self._FormatDescriptionComment() + self._FormatField()

  def _FormatField(self):
    result = "  optional %s %s = %s" % (
        self.proto_type_name,
        self.name,
        self.field_number,
    )
    return result + ";\n"

  def Format(self, value):
    for line in value.Format():
      yield "  %s" % line


class ProtoDynamicEmbedded(ProtoType):
  """An embedded field which has a dynamic type."""

  wire_type = WIRETYPE_LENGTH_DELIMITED

  set_default_on_access = True

  proto_type_name = "bytes"

  def __init__(self, dynamic_cb=None, **kwargs):
    """Initialize the type descriptor.

    We call the dynamic_method to know which type should be used to decode the
    embedded bytestream.

    Args:
      dynamic_cb: A callback to be used to return the class to parse the
        embedded data. We pass the callback our container.
      **kwargs: Passthrough.
    """
    super().__init__(**kwargs)
    self._type = dynamic_cb

  def ConvertFromWireFormat(self, value, container=None):
    """The wire format is simply a string."""
    return serialization.FromBytes(self._type(container), value[2])

  def ConvertToWireFormat(self, value):
    """Encode the nested protobuf into wire format."""
    data = serialization.ToBytes(value)
    return (self.encoded_tag, VarintEncode(len(data)), data)

  def Validate(self, value, container=None):
    if self._type is None:
      return value

    required_type = self._type(container)
    if required_type and not isinstance(value, required_type):
      raise ValueError(
          "Expected value of type %s, but got %s"
          % (required_type, value.__class__.__name__)
      )

    return value

  def GetDefault(self, container=None):
    # _type can be None if a ProtoDynamicEmbedded field is not initialized.
    if self._type is None:
      return None

    cls = self._type(container or self.owner())
    if cls is not None:
      return cls()

  def Format(self, value):
    yield "  %r" % value

  def _FormatDefault(self):
    return ""


class ProtoDynamicAnyValueEmbedded(ProtoDynamicEmbedded):
  """An embedded dynamic field which that is stored as AnyValue struct."""

  proto_type_name = "google.protobuf.Any"

  WRAPPER_BY_TYPE = {
      "bytes": wrappers_pb2.BytesValue,
      "string": wrappers_pb2.StringValue,
      "integer": wrappers_pb2.Int64Value,
      "unsigned_integer_32": wrappers_pb2.UInt32Value,
      "unsigned_integer": wrappers_pb2.UInt64Value,
  }

  TYPE_BY_WRAPPER = {
      "BytesValue": rdfvalue.RDFBytes,
      "StringValue": rdfvalue.RDFString,
      "Int64Value": rdfvalue.RDFInteger,
      "UInt32Value": rdfvalue.RDFInteger,
      "UInt64Value": rdfvalue.RDFInteger,
  }

  def ConvertFromWireFormat(self, value, container=None):
    """The wire format is an AnyValue message."""
    result = AnyValue()
    ReadIntoObject(value[2], 0, result)
    if self._type is not None:
      converted_value = self._type(container)
    else:
      converted_value = self._TypeFromAnyValue(result)

    # If one of the protobuf library wrapper classes is used, unwrap the value.
    if result.type_url.startswith("type.googleapis.com/google.protobuf."):
      wrapper_cls = self.__class__.WRAPPER_BY_TYPE[
          converted_value.protobuf_type
      ]
      wrapper_value = wrapper_cls()
      wrapper_value.ParseFromString(result.value)
      return converted_value.FromWireFormat(wrapper_value.value)
    else:
      # TODO(user): Type stored in type_url is currently ignored when value
      # is decoded. We should use it to deserialize the value and then check
      # that value type and dynamic type are compatible.
      return converted_value.FromSerializedBytes(result.value)

  def _TypeFromAnyValue(self, anyvalue):
    type_str = anyvalue.type_url.split("/")[-1].split(".")[-1]

    if type_str in self.TYPE_BY_WRAPPER:
      return self.TYPE_BY_WRAPPER[type_str]

    try:
      return rdfvalue.RDFValue.classes[type_str]
    except KeyError:
      raise TypeError("Can't find RDFValue class for type: %s" % type_str)

  def ConvertToWireFormat(self, value):
    """Encode the nested protobuf into wire format."""

    try:
      primitive_protobuf_type = serialization.GetProtobufType(type(value))
    except ValueError:
      primitive_protobuf_type = None

    # Is it a protobuf-based value?
    if hasattr(value.__class__, "protobuf"):
      if value.__class__.protobuf:
        type_name = (
            "type.googleapis.com/grr.%s"
            % value.__class__.protobuf.__name__
        )
      else:
        type_name = value.__class__.__name__
      data = value.SerializeToBytes()
    # Is it a primitive value?
    elif primitive_protobuf_type is not None:
      wrapper_cls = self.__class__.WRAPPER_BY_TYPE[primitive_protobuf_type]
      wrapped_data = wrapper_cls()
      wrapped_data.value = serialization.ToWireFormat(value)

      type_name = (
          "type.googleapis.com/google.protobuf.%s" % wrapper_cls.__name__
      )
      data = wrapped_data.SerializeToString()
    else:
      raise ValueError(
          "Can't convert value %s to a protobuf.Any value." % value
      )

    any_value = AnyValue(type_url=type_name, value=data)
    output = _SerializeEntries(_GetOrderedEntries(any_value.GetRawData()))

    return (self.encoded_tag, VarintEncode(len(output)), output)


class ProtoAnyValue(ProtoType):
  """A raw Protocol Buffers `Any` type without dynamic typing magic."""

  wire_type = WIRETYPE_LENGTH_DELIMITED
  proto_type_name = "google.protobuf.Any"
  set_default_on_access = True

  def GetDefault(self, container=None):
    del container  # Unused.
    return AnyValue()

  def Validate(self, value, container=None):
    del container  # Unused.
    precondition.AssertType(value, AnyValue)

    return value

  def ConvertFromWireFormat(self, value, container=None):
    del container  # Unused.

    return AnyValue.FromSerializedBytes(value[2])

  def ConvertToWireFormat(self, value):
    precondition.AssertType(value, AnyValue)

    data = value.SerializeToBytes()
    return (self.encoded_tag, VarintEncode(len(data)), data)


class RepeatedFieldHelper(abc.Sequence):
  """A helper for the RDFProto to handle repeated fields.

  This helper is intended to only be constructed from the RDFProto class.
  """

  def __init__(self, wrapped_list=None, type_descriptor=None, container=None):
    """Constructor.

    Args:
      wrapped_list: The list within the protobuf which we wrap.
      type_descriptor: A type descriptor describing the type of the list
        elements.
      container: The protobuf which contains this repeated field.

    Raises:
      AttributeError: If parameters are not valid.
    """
    self.dirty = False

    if wrapped_list is None:
      self.wrapped_list = []

    # TODO(user): type checker doesn't respect the check below
    # and doesn't use it to infer the type for wrapped_list.
    elif wrapped_list.__class__ is RepeatedFieldHelper:
      self.wrapped_list = cast(RepeatedFieldHelper, wrapped_list).wrapped_list

    else:
      self.wrapped_list = wrapped_list

    if type_descriptor is None:
      raise AttributeError("type_descriptor not specified.")

    self.type_descriptor = type_descriptor
    self.container = container

  def IsDirty(self):
    """Is this repeated item dirty?

    This is used to invalidate any caches that our owners have of us.

    Returns:
      True if this object is dirty.
    """
    if self.dirty:
      return True

    # If any of the items is dirty we are also dirty.
    for item in self.wrapped_list:
      if self.type_descriptor.IsDirty(item[0]):
        self.dirty = True
        return True

    return False

  def Copy(self):
    return RepeatedFieldHelper(
        wrapped_list=self.wrapped_list[:], type_descriptor=self.type_descriptor
    )

  def Append(self, rdf_value=utils.NotAValue, wire_format=None, **kwargs):
    """Append the value to our internal list."""
    if rdf_value is utils.NotAValue:
      if wire_format is None:
        rdf_value = self.type_descriptor.type(**kwargs)
        self.dirty = True
      else:
        rdf_value = None
    else:
      # Coerce the value to the required type.
      try:
        rdf_value = self.type_descriptor.Validate(rdf_value, **kwargs)
      except (TypeError, ValueError) as e:
        raise type_info.TypeValueError(
            "Assignment value must be %s, but %s can not be coerced. Error: %s"
            % (self.type_descriptor.proto_type_name, type(rdf_value), e)
        )

    self.wrapped_list.append((rdf_value, wire_format))

    return rdf_value

  def Pop(self, item):
    result = self[item]
    self.wrapped_list.pop(item)
    return result

  def Extend(self, iterable):
    for i in iterable:
      self.Append(rdf_value=i)

  append = utils.Proxy("Append")
  remove = utils.Proxy("Remove")
  extend = utils.Proxy("Extend")

  def __getitem__(self, item):
    # Ensure we handle slices as well.
    if item.__class__ is slice:
      result = []
      for i in range(*item.indices(len(self))):
        result.append(self.wrapped_list[i])

      return self.__class__(
          wrapped_list=result, type_descriptor=self.type_descriptor
      )

    python_format, wire_format = self.wrapped_list[item]
    if python_format is None:
      python_format = self.type_descriptor.ConvertFromWireFormat(
          wire_format, container=self.container
      )

      self.wrapped_list[item] = (python_format, wire_format)

    return python_format

  def __len__(self):
    return len(self.wrapped_list)

  def __ne__(self, other):
    return not self == other  # pylint: disable=g-comparison-negation

  def __eq__(self, other):
    if not isinstance(other, Sequence) or isinstance(other, (ByteString, str)):
      return NotImplemented
    if len(self) != len(other):
      return False
    for x, y in zip(self, other):
      if x != y:
        return False
    return True

  def __str__(self) -> str:
    result = ["'%s': [" % self.type_descriptor.name]
    for element in self:
      for line in self.type_descriptor.Format(element):
        result.append(" %s" % line)

    result.append("]")

    return "\n".join(result)

  def __repr__(self):
    # Skip self.container and self.type_descriptor to avoid cyclical output.
    return "<{} {!r}>".format(type(self).__name__, self.wrapped_list)

  def Validate(self):
    for x in self:
      if hasattr(x, "Validate"):
        x.Validate()


class ProtoList(ProtoType):
  """A repeated type."""

  #         ,     \    /      ,
  #        / \    )\__/(     / \
  #       /   \  (_\  /_)   /   \
  #  ____/_____\__\@  @/___/_____\____
  # |             |\../|              |
  # |              \VV/               |
  # |    WARNING: Here be dragons!    |
  # | When accessing a ProtoList that |
  # | is a field of another RDFValue, |
  # | its unset value is  replaced    |
  # | with its default value: [].     |
  # | Since [] is not None, accessing |
  # | a ProtoList changes its parents |
  # | equality.                       |
  # |_________________________________|
  #  |    /\ /      \\       \ /\    |
  #  |  /   V        ))       V   \  |
  #  |/     `       //        '     \|
  #  `              V                '
  # TODO
  set_default_on_access = True

  def __init__(self, delegate, labels=None, **kwargs):
    self.delegate = delegate
    if not isinstance(delegate, ProtoType):
      raise AttributeError(
          "Delegate class must derive from ProtoType, not %s"
          % delegate.__class__.__name__
      )

    # If our delegate is late bound we must also be late bound. This means that
    # the repeated field is not registered in the owner protobuf just
    # yet. However, we do not actually need to register a late binding callback
    # ourselves, since the delegate field descriptor already did this. We simply
    # wait until the delegate calls our AddDescriptor() method and then we call
    # our own owner's AddDescriptor() method to ensure we re-register.
    self.late_bound = delegate.late_bound

    self.wire_type = delegate.wire_type

    super().__init__(
        name=delegate.name,
        description=delegate.description,
        field_number=delegate.field_number,
        friendly_name=delegate.friendly_name,
        labels=labels,
    )

  def IsDirty(self, value):
    return value.IsDirty()

  def GetDefault(self, container=None):
    # By default an empty RepeatedFieldHelper.
    return RepeatedFieldHelper(
        type_descriptor=self.delegate, container=container
    )

  def Validate(self, value, **_):  # pytype: disable=signature-mismatch  # overriding-parameter-count-checks
    """Check that value is a list of the required type."""
    # Assigning from same kind can allow us to skip verification since all
    # elements in a RepeatedFieldHelper already are coerced to the delegate
    # type. In that case we just make a copy. This only works when the value
    # wraps the same type as us.
    if (
        value.__class__ is RepeatedFieldHelper
        and value.type_descriptor is self.delegate
    ):
      result = value.Copy()

    # Make sure the base class finds the value valid.
    else:
      # The value may be a generator here, so we just iterate over it.
      result = RepeatedFieldHelper(type_descriptor=self.delegate)
      result.Extend(value)

    return result

  def ConvertFromWireFormat(self, value, container=None):
    result = RepeatedFieldHelper(type_descriptor=self.delegate)
    for wire_format in SplitBuffer(value[2]):
      result.wrapped_list.append((None, wire_format))

    return result

  def ConvertToWireFormat(self, value):
    """Convert to the wire format.

    Args:
      value: is of type RepeatedFieldHelper.

    Returns:
      A wire format representation of the value.
    """
    output = _SerializeEntries(
        (python_format, wire_format, value.type_descriptor)
        for (python_format, wire_format) in value.wrapped_list
    )
    return b"", b"", output

  def Format(self, value):
    yield "["

    for element in value:
      for line in self.delegate.Format(element):
        yield " %s" % line

    yield "]"

  def _FormatField(self):
    result = "  repeated %s %s = %s" % (
        self.delegate.proto_type_name,
        self.name,
        self.field_number,
    )

    return result + ";\n"

  def SetOwner(self, owner):
    self.owner = owner
    # We are the owner for the delegate field descriptor.
    self.delegate.SetOwner(self)

  def AddDescriptor(self, field_desc):
    """This method will be called by our delegate during late binding."""
    # Just relay it up to our owner.
    self.late_bound = False
    self.delegate = field_desc
    self.wire_type = self.delegate.wire_type
    self.owner.AddDescriptor(self)


class ProtoRDFValue(ProtoType):
  """Serialize arbitrary rdfvalue members.

  RDFValue members can be serialized in a number of different ways according to
  their preferred protobuf_type member. We map the descriptions in
  protobuf_type into a suitable protobuf serialization for optimal
  serialization. We therefore use a delegate type descriptor to best convert
  from the RDFValue to the wire type. For example, an RDFDatetime is best
  represented as an integer (number of microseconds since the epoch). Hence
  RDFDatetime.SerializeToWireFormat() will return an integer, and the delegate
  will be ProtoUnsignedInteger().

  To convert from the RDFValue python type to the delegate's wire type we
  therefore need to make two conversions:

  1) Our python format is the RDFValue -> intermediate data store format using
  RDFValue.SerializeToWireFormat(). This will produce a python object which is
  the correct python format for the delegate primitive type descriptor.

  2) Use the delegate to obtain the wire format of its own python type
  (i.e. self.delegate.ConvertToWireFormat())

  NOTE: The default value for an RDFValue is None. It is impossible for us to
  know how to instantiate a valid default value without being told by the
  user. This is unlike the default value for strings or ints which are "" and 0
  respectively.
  """

  # We delegate encoding/decoding to a primitive field descriptor based on the
  # semantic type's protobuf_type attribute.
  primitive_desc = None

  # We store our args here so we can use the same args to initialize the
  # delegate descriptor.
  _kwargs = None

  type = None
  wire_type = WIRETYPE_LENGTH_DELIMITED

  _PROTO_DATA_STORE_LOOKUP = dict(
      bytes=ProtoBinary,
      unsigned_integer=ProtoUnsignedInteger,
      unsigned_integer_32=ProtoUnsignedInteger,
      integer=ProtoUnsignedInteger,
      signed_integer=ProtoSignedInteger,
      string=ProtoString,
  )

  def __init__(self, rdf_type=None, default=None, **kwargs):
    super().__init__(**kwargs)
    self._kwargs = kwargs

    if default is not None:
      self.default = default

    if isinstance(rdf_type, str):
      self.original_proto_type_name = self.proto_type_name = rdf_type

      # Try to resolve the type it names
      self.type = rdfvalue.RDFValue.classes.get(rdf_type, None)

      # We do not know about this type yet. Implement Late Binding.
      if self.type is None:
        self.late_bound = True

        # Register a late binding callback.
        rdfvalue.RegisterLateBindingCallback(rdf_type, self.LateBind)

      else:
        # The semantic type was found successfully.
        self._GetPrimitiveEncoder()

    # Or it can be an subclass of RDFValue.
    elif issubclass(rdf_type, rdfvalue.RDFValue):  # pytype: disable=wrong-arg-types
      self.type = rdf_type
      self.original_proto_type_name = self.proto_type_name = rdf_type.__name__
      self._GetPrimitiveEncoder()

    else:
      type_info.TypeValueError("An rdf_type must be specified.")

  def LateBind(self, target=None):
    """Bind the field descriptor to the owner once the target is defined."""
    self.type = target
    self._GetPrimitiveEncoder()

    # Now re-add the descriptor to the owner protobuf.
    self.late_bound = False
    self.owner.AddDescriptor(self)

  def _GetPrimitiveEncoder(self):
    """Finds the primitive encoder according to the type's protobuf_type."""
    # Decide what should the primitive type be for packing the target rdfvalue
    # into the protobuf and create a delegate descriptor to control that.
    primitive_cls = self._PROTO_DATA_STORE_LOOKUP[
        serialization.GetProtobufType(self.type)
    ]
    self.primitive_desc = primitive_cls(**self._kwargs)

    # Our wiretype is the same as the delegate's.
    self.wire_type = self.primitive_desc.wire_type
    self.proto_type_name = self.primitive_desc.proto_type_name

    # Recalculate our tags.
    self.CalculateTags()

  def GetDefault(self, container=None):
    _ = container
    if self.default is None:
      return None

    if self.default.__class__ is not self.type:
      self.default = self.Validate(self.default)
    return self.default

  def IsDirty(self, python_format):
    """Return the dirty state of the python object."""
    return python_format.dirty

  def Definition(self):
    return (
        "\n  // Semantic Type: %s" % self.type.__name__
    ) + self.primitive_desc.Definition()

  def Validate(self, value, **_):  # pytype: disable=signature-mismatch  # overriding-parameter-count-checks
    # Try to coerce into the correct type:
    if value.__class__ is not self.type:
      try:
        value = self.type(value)
      except (rdfvalue.DecodeError, TypeError) as e:
        raise type_info.TypeValueError(e)

    return value

  def ConvertFromWireFormat(self, value, container=None):
    # Wire format should be compatible with the protobuf_type for the
    # rdfvalue. We use the delegate primitive descriptor to perform the
    # conversion.
    value = self.primitive_desc.ConvertFromWireFormat(
        value, container=container
    )

    result = self.type(value)

    return result

  def ConvertToWireFormat(self, value):
    return self.primitive_desc.ConvertToWireFormat(
        value.SerializeToWireFormat()
    )

  def Copy(self, field_number=None):
    """Returns descriptor copy, optionally changing field number."""
    new_args = self._kwargs.copy()
    if field_number is not None:
      new_args["field_number"] = field_number

    return ProtoRDFValue(
        rdf_type=self.original_proto_type_name,
        default=getattr(self, "default", None),
        **new_args,
    )

  def _FormatField(self):
    result = "  optional %s %s = %s" % (
        self.proto_type_name,
        self.name,
        self.field_number,
    )
    return result + ";\n"

  def Format(self, value):
    yield "%s:" % self.type.__name__
    for line in str(value).splitlines():
      yield "  %s" % line

  def __str__(self):
    return "<Field %s (Sem Type: %s) of %s: field_number: %s>" % (
        self.name,
        self.proto_type_name,
        self.owner.__name__,
        self.field_number,
    )


class RDFStructMetaclass(rdfvalue.RDFValueMetaclass):
  """A metaclass which registers new RDFProtoStruct instances."""

  _HAS_DYNAMIC_ATTRIBUTES = True  # help out pytype

  def __init__(untyped_cls, name, bases, env_dict):  # pylint: disable=no-self-argument
    super().__init__(name, bases, env_dict)

    # TODO(user):pytype: find a more elegant solution (if possible).
    # cast() doesn't accept forward references and argument annotations
    # like Type["RDFStruct"] are not accepted by the type checker. The
    # biggest caveat here is that RDFStruct is defined *with the help*
    # of RDFStructMetaclass, so its name is not defined at the time
    # this code is evaluated.
    cls: type["RDFStruct"] = untyped_cls
    cls.type_infos = type_info.TypeDescriptorSet()

    # Keep track of the late bound fields.
    cls.late_bound_type_infos = {}

    cls.type_infos_by_field_number = {}
    cls.type_infos_by_encoded_tag = {}

    # Build the class by parsing an existing protobuf class.
    if cls.protobuf is not None:
      registry.RegisterRDFProtoStruct(cls.__name__, cls)
      rdf_proto2.DefineFromWireFormat(cls, cls.protobuf)

    # Pre-populate the class using the type_infos class member.
    if cls.type_description is not None:
      for field_desc in cls.type_description:
        cls.AddDescriptor(field_desc)

    cls._class_attributes = set(dir(cls))  # pylint: disable=protected-access


T = TypeVar("T")


class RDFStruct(rdfvalue.RDFValue, metaclass=RDFStructMetaclass):  # pylint: disable=invalid-metaclass
  """An RDFValue object which contains fields like a struct.

  Struct members contain values such as integers, strings etc. These are stored
  in an internal data structure.

  A value can be in two states, the wire format is a serialized format closely
  resembling the state it appears on the wire. The Decoded format is the
  representation closely representing an internal python type. The idea is that
  converting from a serialized wire encoding to the wire format is as cheap as
  possible. Similarly converting from a python object to the python
  representation is also very cheap.

  Lazy evaluation occurs when we need to obtain the python representation of a
  decoded field. This allows us to skip the evaluation of complex data.

  For example, suppose we have a protobuf with several "string" fields
  (i.e. unicode objects). The wire format for a "string" field is a UTF8 encoded
  binary string, but the python object is a unicode object.

  Normally when parsing the protobuf we can extract the wire format
  representation very cheaply, but conversion to a unicode object is quite
  expensive. If the user never access the specific field, we can keep the
  internal representation in wire format and not convert it to a unicode object.
  """

  # This can be populated with a type_info.TypeDescriptorSet() object to
  # initialize the class.
  type_description = None

  # This class can be defined using the protobuf definition language (e.g. a
  # .proto file). If defined here, we parse the .proto file for the message with
  # the exact same class name and add the field descriptions from it.
  definition = None

  # This class can be defined in terms of an existing annotated regular
  # protobuf. See RDFProtoStruct.DefineFromWireFormat().
  protobuf = None

  # This is where the type infos are constructed.
  type_infos: type_info.TypeDescriptorSet = None

  # Mark as dirty each time we modify this object.
  dirty = False

  # Stores the raw data here.
  _data = None

  def __init__(self, initializer=None, **kwargs):
    super().__init__()

    # Maintain the order so that parsing and serializing a proto does not change
    # the serialized form.
    self._data = {}
    self._prev_hash = None

    for arg, value in kwargs.items():
      if not hasattr(self.__class__, arg):
        if arg in self.late_bound_type_infos:
          raise AttributeError(
              "Field %s refers to an as yet undefined Semantic Type."
              % self.late_bound_type_infos[arg]
          )

        raise AttributeError(
            "Proto %s has no field %s" % (self.__class__.__name__, arg)
        )

      # Call setattr to allow the class to define @property pseudo fields which
      # can also be initialized.
      setattr(self, arg, value)

    if initializer is None:
      return

    elif initializer.__class__ is self.__class__:
      self.CopyConstructor(initializer)

    else:
      raise ValueError(
          "%s can not be initialized from %s"
          % (self.__class__.__name__, type(initializer))
      )

  def CopyConstructor(self, other):
    """Efficiently copy from other into this object.

    Basic RDFStruct objects are fully represented by their internal raw data. We
    can easily copy it by simply making a direct copy of the wire format of each
    field, and not preserving the python format. On access in the copy the field
    will be re-parsed into a python object.

    Args:
      other: An instance of the same type of this class.
    """
    self._data = {}
    for name, (obj, serialized, t_info) in other.GetRawData().items():
      if serialized is None:
        serialized = t_info.ConvertToWireFormat(obj)

      self._data[name] = (None, serialized, t_info)

  def Clear(self):
    """Clear all the fields."""
    self._data = {}

  def HasField(self, field_name):
    """Checks if the field exists."""
    return field_name in self._data

  def _CopyRawData(self):
    new_raw_data = {}

    # We need to copy all entries in _data. Those entries are tuples of
    # - an object (if it has already been deserialized)
    # - the serialized object (if it has been serialized)
    # - the type_info.
    # To copy this, it's easiest to just copy the serialized object if it
    # exists. We have to make sure though that the object is not a protobuf.
    # If it is, someone else might have changed the subobject and the
    # serialization is not accurate anymore. This is indicated by the dirty
    # flag. Type_infos can be just copied by reference.
    for name, (obj, serialized, t_info) in self._data.items():
      if serialized is None:
        obj = copy.copy(obj)
      else:
        try:
          if t_info.IsDirty(obj):
            obj, serialized = copy.copy(obj), None
          else:
            obj = None
        except AttributeError:
          obj = None

      new_raw_data[name] = (obj, serialized, t_info)
    return new_raw_data

  def Copy(self: T) -> T:
    """Make an efficient copy of this protobuf."""
    result = self.__class__()
    result.SetRawData(self._CopyRawData())
    return result

  def __deepcopy__(self, memo):
    result = self.__class__()
    result.SetRawData(copy.deepcopy(self._data, memo))

    return result

  def GetRawData(self):
    """Retrieves the raw python representation of the object.

    External users should not make use of the internal raw data structures.

    Returns:
      the raw python object representation (a dict).
    """
    return self._data

  def ListSetFields(self):
    """Iterates over the fields which are actually set.

    Yields:
      a tuple of (type_descriptor, value) for each field which is set.
    """
    for type_descriptor in self.type_infos:
      if type_descriptor.name in self._data:
        yield type_descriptor, self.Get(type_descriptor.name)

  def SetRawData(self, data):
    self._data = data
    self.dirty = True

  def SerializeToBytes(self):
    return _SerializeEntries(_GetOrderedEntries(self._data))

  @classmethod
  def FromSerializedBytes(cls, value: bytes):
    precondition.AssertType(value, bytes)
    instance = cls()

    try:
      ReadIntoObject(value, 0, instance)
    except ValueError:
      logging.error(
          "Error in ReadIntoObject. %d bytes, extract: %r",
          len(value),
          value[:1000],
      )
      raise

    instance.dirty = True
    return instance

  @classmethod
  def FromWireFormat(cls, value):
    precondition.AssertType(value, bytes)
    return cls.FromSerializedBytes(value)

  __hash__ = None

  def __eq__(self, other):
    if not isinstance(other, self.__class__):
      return NotImplemented

    # Compare all fields set in `self` or `other`, skipping only fields that
    # are unset in both `self` and `other`. We deliberately check fields that
    # are set in one class and not in the other. This allows RDFStructs to be
    # considered equal, when one has a field set to its default value and the
    # other has the field unset (where .Get implicitly returns the default
    # value then).
    for field in set(self.GetRawData()) | set(other.GetRawData()):

      # Deserializing Protobuf of newer versions can put `_unknown_field_{n}` in
      # _data. This is a special field without type descriptor, thus raising an
      # error in Get(). To follow Protobuf semantics, ignore fields that do not
      # have a type descriptor.
      # pylint: disable=unsupported-membership-test
      if field not in self.type_infos:
        continue

      self_val = self.Get(field, allow_set_default=False)
      other_val = other.Get(field, allow_set_default=False)

      if self_val != other_val:
        return False

    return True

  def __ne__(self, other):
    return not self == other  # pylint: disable=g-comparison-negation

  def Format(self):
    """Format a message in a human readable way."""
    yield "message %s {" % self.__class__.__name__

    for k, (python_format, wire_format, type_descriptor) in sorted(
        self.GetRawData().items()
    ):
      if python_format is None:
        python_format = type_descriptor.ConvertFromWireFormat(
            wire_format, container=self
        )

      # Skip printing of unknown fields.
      if isinstance(k, str):
        prefix = "{} :".format(k)
        for line in type_descriptor.Format(python_format):
          yield " %s %s" % (prefix, line)
          prefix = ""

    yield "}"

  def __str__(self) -> str:
    return "\n".join(self.Format())

  def __dir__(self):
    """Add the virtualized fields to the console's tab completion."""
    return dir(super()) + [x.name for x in self.type_infos]  # pylint: disable=not-an-iterable

  def _Set(self, value, type_descriptor):
    """Validate the value and set the attribute with it."""
    attr = type_descriptor.name
    prev_value = self.Get(attr, allow_set_default=False)

    # A value of None means we clear the field.
    if value is None:
      self._data.pop(attr, None)
    else:
      # Validate the value and obtain the python format representation.
      value = type_descriptor.Validate(value, container=self)

      # Store the lazy value object.
      self._data[attr] = (value, None, type_descriptor)

    # Make sure to invalidate our parent's cache if needed.
    self.dirty = True

    if self._prev_hash is not None and prev_value != self.Get(
        attr, allow_set_default=False
    ):
      try:
        hash(self)  # Recompute hash to raise if hash changed due to mutation.
      except AssertionError as ex:
        raise AssertionError(
            "Cannot set {}.{} to {} with previous value {}! hash() has "
            "changed after it has been used! Usage of RDFStructs as members of "
            "sets or keys of dicts is discouraged. If used anyway, mutating is "
            "prohibited, because it causes the hash to change. Be aware that "
            "accessing unset fields can trigger a mutation.".format(
                type(self).__name__, attr, value, prev_value
            )
        ) from ex
    return value

  def Set(self, attr, value):
    """Sets the attribute in to the value."""
    type_descriptor = self._GetTypeDescriptor(attr)
    return self._Set(value, type_descriptor)

  def _GetTypeDescriptor(self, attr):
    type_descriptor = self.type_infos.get(attr)

    if type_descriptor is None:
      raise AttributeError(
          "'%s' object has no attribute '%s'" % (self.__class__.__name__, attr)
      )

    return type_descriptor

  def Get(self, attr, allow_set_default=True):
    """Retrieve the attribute specified.

    Arguments:
      attr: String of the attribute's name
      allow_set_default: If True and attr is currently unset, permanently modify
        the instance by setting attr to the default value.

    Returns:
      The attribute's value, or the attribute's type's default value, if unset.
    """
    entry = self._data.get(attr)
    # We don't have this field, try the defaults.
    if entry is None:
      type_descriptor = self._GetTypeDescriptor(attr)
      default = type_descriptor.GetDefault(container=self)

      if default is None:
        return

      # Assign the default value now.
      if allow_set_default and type_descriptor.set_default_on_access:
        default = self.Set(attr, default)

      return default

    python_format, wire_format, type_descriptor = entry

    # Decode on demand and cache for next time.
    if python_format is None:
      python_format = type_descriptor.ConvertFromWireFormat(
          wire_format, container=self
      )

      self._data[attr] = (python_format, wire_format, type_descriptor)

    return python_format

  def ClearFieldsWithLabel(self, label, exceptions=None):
    exceptions = exceptions or []
    for desc, value in self.ListSetFields():
      if desc.name not in exceptions and label in desc.labels:
        self.Set(desc.name, None)
      else:
        if hasattr(value, "ClearFieldsWithLabel"):
          value.ClearFieldsWithLabel(label, exceptions=exceptions)

  @classmethod
  def AddDescriptor(cls, field_desc):
    if not isinstance(field_desc, ProtoType):
      raise type_info.TypeValueError(
          "%s field '%s' should be of type ProtoType"
          % (cls.__name__, field_desc.name)
      )

    cls.type_infos_by_field_number[field_desc.field_number] = field_desc
    cls.type_infos.Append(field_desc)


class EnumContainer:
  """A data class to hold enum objects."""

  def __init__(
      self, name=None, descriptions=None, enum_labels=None, values=None
  ):
    descriptions = descriptions or {}
    enum_labels = enum_labels or {}
    values = values or {}

    self.enum_dict = {}
    self.reverse_enum = {}
    self.name = name

    for k, v in values.items():
      v = EnumNamedValue(
          v,
          name=k,
          description=descriptions.get(k, None),
          labels=enum_labels.get(k, None),
      )
      self.enum_dict[k] = v
      self.reverse_enum[v] = k
      setattr(self, k, v)

  def FromInt(self, v):
    return getattr(self, self.reverse_enum[v])

  def FromString(self, v: str) -> Optional[EnumNamedValue]:
    if not v:
      return None
    if v not in self.enum_dict:
      raise ValueError(f"Invalid value {v} for {self.name}.")
    return getattr(self, v)


class RDFProtoStruct(RDFStruct):
  """An RDFStruct which uses protobufs for serialization.

  This implementation is faster than the standard protobuf library.
  """

  # TODO(user): if a semantic proto defines a field with the same name as
  # these class variables under some circumstances the proto default value will
  # be set incorrectly.  Figure out a way to make this safe.

  shortest_encoded_tag = 0
  longest_encoded_tag = 0

  # If set to a standard proto2 generated class, we introspect it and extract
  # type descriptors from it. This allows this implementation to use an
  # annotated .proto file to define semantic types.
  protobuf = None

  # This mapping is used to provide concrete implementations for semantic types
  # annotated in the .proto file. This is a dict with keys being the semantic
  # names, and values being the concrete implementations for these types.

  # All RDFValue classes used by this proto have to be specified here.

  # Recorded dependencies - used by update_rdf_deps script to update
  # dependencies setting.
  recorded_rdf_deps = None

  def __init__(self, initializer=None, **kwargs):
    super().__init__(initializer, **kwargs)

  def AsPrimitiveProto(self):
    """Return an old style protocol buffer object."""
    if self.protobuf:
      result = self.protobuf()
      result.ParseFromString(self.SerializeToBytes())
      return result

  def AsDict(self):
    result = {}
    for desc in self.type_infos:
      if self.HasField(desc.name):
        result[desc.name] = self.Get(desc.name)

    return result

  def FromDict(self, dictionary):
    """Initializes itself from a given dictionary."""
    dynamic_fields = []

    for key, value in dictionary.items():
      field_type_info = self.type_infos.get(key)
      if isinstance(field_type_info, ProtoEmbedded):
        nested_value = field_type_info.GetDefault(container=self)
        nested_value.FromDict(value)
        self.Set(key, nested_value)
      elif isinstance(field_type_info, ProtoList):
        if isinstance(field_type_info.delegate, ProtoEmbedded):
          nested_values = []
          for v in value:
            nested_value = field_type_info.delegate.GetDefault(container=self)
            nested_value.FromDict(v)
            nested_values.append(nested_value)

          self.Set(key, nested_values)
        else:
          self.Set(key, value)
      elif isinstance(field_type_info, ProtoDynamicEmbedded):
        dynamic_fields.append(field_type_info)
      elif field_type_info.proto_type_name == "bytes":
        self.Set(key, base64.decodebytes((value or "").encode("ascii")))
      else:
        self.Set(key, value)

    # Process dynamic fields after all other fields, because most probably
    # their class is determined by one of the previously set fields.
    for dynamic_field in dynamic_fields:
      nested_value = dynamic_field.GetDefault(container=self)
      if nested_value is None:
        raise RuntimeError(
            "Can't initialize dynamic field %s, probably some "
            "necessary fields weren't supplied."
            % dynamic_field.name
        )
      nested_value.FromDict(dictionary[dynamic_field.name])
      self.Set(dynamic_field.name, nested_value)

  def ToPrimitiveDict(self, stringify_leaf_fields=False):
    return self._ToPrimitive(self.AsDict(), stringify_leaf_fields)

  def _ToPrimitive(self, value, stringify_leaf_fields):
    if isinstance(value, RepeatedFieldHelper):
      return list(self._ToPrimitive(v, stringify_leaf_fields) for v in value)
    # Hack to avoid dependency loop. Safe because if value is a protodict.Dict,
    # then protodict has already been loaded.
    # TODO(user): remove this hack
    elif "Dict" in rdfvalue.RDFValue.classes and isinstance(
        value, rdfvalue.RDFValue.classes["Dict"]
    ):
      primitive_dict = {}
      # TODO(user):pytype: get rid of a dependency loop described above and
      # do a proper type check.
      for k, v in value.ToDict().items():  # pytype: disable=attribute-error
        primitive_dict[k] = self._ToPrimitive(v, stringify_leaf_fields)
      return primitive_dict
    elif isinstance(value, dict):
      primitive_dict = {}
      for k, v in value.items():
        primitive_dict[k] = self._ToPrimitive(v, stringify_leaf_fields)
      return primitive_dict
    elif isinstance(value, RDFProtoStruct):
      return self._ToPrimitive(value.AsDict(), stringify_leaf_fields)
    elif isinstance(value, (EnumNamedValue)):
      return str(value)
    elif isinstance(value, rdfvalue.RDFBytes):
      return base64.b64encode(value.SerializeToBytes()).decode("ascii")
    else:
      if stringify_leaf_fields:
        if isinstance(value, bytes):
          return base64.b64encode(value).decode("ascii")
        else:
          return str(value)
      else:
        return value

  def __bool__(self):
    return bool(self._data)

  @classmethod
  def EmitProto(cls):
    """Emits .proto file definitions."""
    result = "message %s {\n" % cls.__name__
    for _, desc in sorted(cls.type_infos_by_field_number.items()):
      result += desc.Definition()

    result += "}\n"
    return result

  def Validate(self):
    """Validates the semantic protobuf for internal consistency.

    Derived classes can override this method to ensure the proto is sane
    (e.g. required fields, or any arbitrary condition). This method is called
    prior to serialization. Note that it is not necessary to validate fields
    against their semantic types - it is impossible to set fields which are
    invalid. This function is more intended to validate the entire protobuf for
    internal consistency.

    Raises:
      type_info.TypeValueError if the proto is invalid.
    """

  @classmethod
  def FromTextFormat(cls, text):
    """Parse this object from a text representation."""
    if cls.protobuf is None:
      raise ValueError("protobuf must be set on cls.")
    tmp = cls.protobuf()  # pylint: disable=not-callable
    text_format.Merge(text, tmp)

    return cls.FromSerializedBytes(tmp.SerializeToString())

  @classmethod
  def AddDescriptor(cls, field_desc):
    """Register this descriptor with the Proto Struct."""
    if not isinstance(field_desc, ProtoType):
      raise type_info.TypeValueError(
          "%s field '%s' should be of type ProtoType"
          % (cls.__name__, field_desc.name)
      )

    # Ensure the field descriptor knows the class that owns it.
    field_desc.SetOwner(cls)

    # If the field is late bound we do not really add it to the descriptor set
    # yet. We must wait for the LateBindingPlaceHolder() to add it later.
    if field_desc.late_bound:
      # Keep track of unbound fields.
      cls.late_bound_type_infos[field_desc.name] = field_desc
      return

    # Ensure this field number is unique:
    if field_desc.field_number in cls.type_infos_by_field_number:
      raise type_info.TypeValueError(
          "Field number %s for field %s is not unique in %s"
          % (field_desc.field_number, field_desc.name, cls.__name__)
      )

    # We store an index of the type info by tag values to speed up parsing.
    cls.type_infos_by_field_number[field_desc.field_number] = field_desc
    cls.type_infos_by_encoded_tag[field_desc.encoded_tag] = field_desc

    cls.type_infos.Append(field_desc)
    cls.late_bound_type_infos.pop(field_desc.name, None)

    # Add direct accessors only if the class does not already have them.
    if not hasattr(cls, field_desc.name):
      # This lambda is a class method so pylint: disable=protected-access
      # This is much faster than __setattr__/__getattr__
      setattr(
          cls,
          field_desc.name,
          property(
              lambda self: self.Get(field_desc.name),
              lambda self, x: self._Set(x, field_desc),
              None,
              field_desc.description,
          ),
      )

  def UnionCast(self):
    union_field = getattr(self, self.union_field)
    cast_field_name = str(union_field).lower()

    set_fields = set(
        type_descriptor.name for type_descriptor, _ in self.ListSetFields()
    )

    union_cases = [
        case.lower()
        for case in self.type_infos[self.union_field].enum_container.enum_dict
    ]

    mismatched_union_cases = set_fields.intersection(union_cases).difference(
        [cast_field_name]
    )

    if mismatched_union_cases:
      raise ValueError(
          "Inconsistent union proto data. Expected only %r "
          "to be set, %r are also set."
          % (cast_field_name, list(mismatched_union_cases))
      )

    try:
      return getattr(self, cast_field_name)
    except AttributeError:
      raise AttributeError("union_field not initialized.")


class SemanticDescriptor(RDFProtoStruct):
  """A semantic protobuf describing the .proto extension."""

  protobuf = semantic_pb2.SemanticDescriptor


_V = TypeVar("_V", bound=rdfvalue.RDFValue)


class AnyValue(RDFProtoStruct):
  """Protobuf with arbitrary serialized proto and its type."""

  protobuf = any_pb2.Any
  allow_custom_class_name = True

  @classmethod
  def FromProto2(cls, proto2_any: any_pb2.Any) -> "AnyValue":
    """Converts a proto2 `Any` message to the RDF wrapper."""
    result = cls()
    result.type_url = proto2_any.type_url
    result.value = proto2_any.value
    return result

  @classmethod
  def PackProto2(cls, message: proto2_message.Message) -> "AnyValue":
    """Packs the given proto2 message into the `Any` RDF wrapper.

    Args:
      message: A message to pack.

    Returns:
      An instance of RD wrapper for `Any` with packaged message.
    """
    proto2_any = any_pb2.Any()
    proto2_any.Pack(message)

    return cls.FromProto2(proto2_any)

  @classmethod
  def Pack(cls, value: RDFProtoStruct) -> "AnyValue":
    """Packs given RDF value into the `Any` RDF wrapper.

    Args:
      value: An RDF value to pack.

    Returns:
      An instance of RDF wrapper for `Any` with packed message.
    """
    result = cls()
    result.type_url = TypeURL(type(value))
    result.value = value.SerializeToBytes()
    return result

  def Unpack(self, cls: type[_V]) -> _V:
    """Unpacks `Any` into an instance of the specified RDF class.

    Args:
      cls: A class into instance of which the value should be unpacked into.

    Returns:
      An instance of the specified class.
    """
    # Because messages can get renamed, unpacking into an unexpected type is not
    # necessarily an error, but it still worth to log it as it might be helpful
    # in identifying issues.
    cls_type_url = TypeURL(cls)
    if cls_type_url != self.type_url:
      message = "Unpacking value of type '%s' to message of type '%s'."
      logging.warning(message, self.type_url, cls_type_url)

    return cls.FromSerializedBytes(self.value)


def TypeURL(cls: type[_V]) -> str:
  if cls.protobuf is None:
    raise ValueError("protobuf must be set on cls.")
  return f"type.googleapis.com/{cls.protobuf.DESCRIPTOR.full_name}"
