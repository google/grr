#!/usr/bin/env python
"""Semantic Protobufs are serialization agnostic, rich data types."""

import copy
import struct


# pylint: disable=g-import-not-at-top
try:
  from grr.accelerated import _semantic
except ImportError:
  _semantic = None

from google.protobuf import descriptor_pb2
from google.protobuf import text_format

from grr.lib import rdfvalue
from grr.lib import registry
from grr.lib import type_info
from grr.lib import utils
from grr.lib.rdfvalues import proto2
from grr.proto import semantic_pb2
# pylint: disable=super-init-not-called
# pylint: enable=g-import-not-at-top

# We copy these here to remove dependency on the protobuf library.
TAG_TYPE_BITS = 3  # Number of bits used to hold type info in a proto tag.
TAG_TYPE_MASK = (1 << TAG_TYPE_BITS) - 1  # 0x7

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
_WIRETYPE_MAX = 5


# The following are the varint encoding/decoding functions taken from the
# protobuf library. Placing them in this file allows us to remove dependency on
# the standard protobuf library.

ORD_MAP = dict((chr(x), x) for x in range(0, 256))
CHR_MAP = dict((x, chr(x)) for x in range(0, 256))
HIGH_CHR_MAP = dict((x, chr(0x80 | x)) for x in range(0, 256))

# Some optimizations to get rid of AND operations below since they are really
# slow in Python.
ORD_MAP_AND_0X80 = dict((chr(x), x & 0x80) for x in range(0, 256))
ORD_MAP_AND_0X7F = dict((chr(x), x & 0x7F) for x in range(0, 256))


# This function is HOT.
def ReadTag(buf, pos):
  """Read a tag from the buffer, and return a (tag_bytes, new_pos) tuple."""
  try:
    start = pos
    while ORD_MAP_AND_0X80[buf[pos]]:
      pos += 1
    pos += 1
    return (buf[start:pos], pos)
  except IndexError:
    raise ValueError("Invalid tag")


# This function is HOT.
def VarintEncode(value):
  """Convert an integer to a varint and write it using the write function."""
  result = ""
  if value < 0:
    raise ValueError("Varint can not encode a negative number.")

  bits = value & 0x7f
  value >>= 7

  while value:
    result += HIGH_CHR_MAP[bits]
    bits = value & 0x7f
    value >>= 7

  result += CHR_MAP[bits]

  return result


def SignedVarintEncode(value):
  """Encode a signed integer as a zigzag encoded signed integer."""
  result = ""
  if value < 0:
    value += (1 << 64)

  bits = value & 0x7f
  value >>= 7
  while value:
    result += HIGH_CHR_MAP[bits]
    bits = value & 0x7f
    value >>= 7
  result += CHR_MAP[bits]

  return result


# This function is HOT.
def VarintReader(buf, pos=0):
  """A 64 bit decoder from google.protobuf.internal.decoder."""
  result = 0
  shift = 0
  while 1:
    b = buf[pos]

    result |= (ORD_MAP_AND_0X7F[b] << shift)
    pos += 1
    if not ORD_MAP_AND_0X80[b]:
      return (result, pos)
    shift += 7
    if shift >= 64:
      raise rdfvalue.DecodeError("Too many bytes when decoding varint.")


def SignedVarintReader(buf, pos=0):
  """A Signed 64 bit decoder from google.protobuf.internal.decoder."""
  result = 0
  shift = 0
  while 1:
    b = buf[pos]
    result |= (ORD_MAP_AND_0X7F[b] << shift)
    pos += 1
    if not ORD_MAP_AND_0X80[b]:
      if result > 0x7fffffffffffffff:
        result -= (1 << 64)

      return (result, pos)

    shift += 7
    if shift >= 64:
      raise rdfvalue.DecodeError("Too many bytes when decoding varint.")


def SplitBuffer(buff, index=0, length=None):
  """Parses the buffer as a prototypes.

  Args:
    buff: The buffer to parse.
    index: The position to start parsing.
    length: Optional length to parse until.

  Yields:
    Splits the buffer into tuples of strings:
        (encoded_tag, encoded_length, wire_format).
  """
  buffer_len = length or len(buff)
  while index < buffer_len:
    # data_index is the index where the data begins (i.e. after the tag).
    encoded_tag, data_index = ReadTag(buff, index)

    tag_type = ORD_MAP[encoded_tag[0]] & TAG_TYPE_MASK
    if tag_type == WIRETYPE_VARINT:
      # new_index is the index of the next tag.
      _, new_index = VarintReader(buff, data_index)
      yield (encoded_tag, "", buff[data_index:new_index])
      index = new_index

    elif tag_type == WIRETYPE_FIXED64:
      yield (encoded_tag, "", buff[data_index:data_index+8])
      index = 8 + data_index

    elif tag_type == WIRETYPE_FIXED32:
      yield (encoded_tag, "", buff[data_index:data_index+4])
      index = 4 + data_index

    elif tag_type == WIRETYPE_LENGTH_DELIMITED:
      # Start index of the string.
      length, start = VarintReader(buff, data_index)
      yield (encoded_tag, buff[data_index:start],  # Encoded length.
             buff[start:start+length])  # Raw data of element.
      index = start + length

    else:
      raise rdfvalue.DecodeError("Unexpected Tag.")


def ReadIntoObject(buff, index, value_obj, length=0):
  """Reads all tags until the next end group and store in the value_obj."""
  raw_data = value_obj.GetRawData()
  count = 0

  # Split the buffer into tags and wire_format representations, then collect
  # these into the raw data cache.
  for (encoded_tag, encoded_length,
       encoded_field) in SplitBuffer(buff, index=index, length=length):

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
      raw_data[count] = (None, wire_format, None)

      count += 1

    # Repeated fields are handled especially.
    elif type_info_obj.__class__ is ProtoList:
      value_obj.Get(type_info_obj.name).wrapped_list.append((None, wire_format))

    else:
      # Set the python_format as None so it gets converted lazily on access.
      raw_data[type_info_obj.name] = (None, wire_format, type_info_obj)

# pylint: disable=invalid-name
if _semantic:
  VarintEncode = _semantic.varint_encode
  VarintReader = _semantic.varint_decode
  SplitBuffer = _semantic.split_buffer
# pylint: enable=invalid-name


class ProtoType(type_info.TypeInfoObject):
  """A specific type descriptor for protobuf fields.

  This is an abstract class - do not instantiate directly.
  """
  # Must be overridden by implementations.
  wire_type = None

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

  def __init__(self, field_number=None, required=False, labels=None,
               set_default_on_access=None, **kwargs):
    super(ProtoType, self).__init__(**kwargs)
    self.field_number = field_number
    self.required = required
    if set_default_on_access is not None:
      self.set_default_on_access = set_default_on_access

    self.labels = labels or []
    if field_number is None:
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
    # decleration time). Pre-calculating the tag makes for faster serialization.
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
        self.proto_type_name, self.name, self.field_number,
        self._FormatDefault())

    return result + ";\n"

  def Definition(self):
    """Return a string with the definition of this field."""
    return self._FormatDescriptionComment() + self._FormatField()

  def Format(self, value):
    """A Generator for display lines representing value."""
    yield str(value)

  def Validate(self, value, container=None):
    """Validate the value."""
    _ = container
    return value

  def GetDefault(self, container=None):
    _ = container
    return self.default

  def __str__(self):
    return "<Field %s (%s) of %s: field_number: %s>" % (
        self.name, self.__class__.__name__, self.owner.__name__,
        self.field_number)

  def SetOwner(self, owner):
    self.owner = owner


class ProtoString(ProtoType):
  """A string encoded in a protobuf."""

  wire_type = WIRETYPE_LENGTH_DELIMITED

  # This descriptor describes unicode strings.
  type = rdfvalue.RDFString

  def __init__(self, default=u"", **kwargs):
    # Strings default to "" if not specified.
    super(ProtoString, self).__init__(**kwargs)

    # Ensure the default is a unicode object.
    if default is not None:
      self.default = utils.SmartUnicode(default)

  def GetDefault(self, container=None):
    _ = container
    return self.default

  def Validate(self, value, **_):
    """Validates a python format representation of the value."""
    # We only accept a base string, unicode object or RDFString here.
    if not (value.__class__ is str or value.__class__ is unicode or
            value.__class__ is rdfvalue.RDFString):
      raise type_info.TypeValueError("%s not a valid string" % value)

    if value.__class__ is unicode:
      return value

    # A String means a unicode String. We must be dealing with unicode strings
    # here and the input must be encodable as a unicode object.
    try:
      try:
        return value.__unicode__()
      except AttributeError:
        return unicode(value, "utf8")
    except UnicodeError:
      raise type_info.TypeValueError("Not a valid unicode string")

  def ConvertFromWireFormat(self, value, container=None):
    """Internally strings are utf8 encoded."""
    try:
      return unicode(value[2], "utf8")
    except UnicodeError:
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

  def __init__(self, default="", **kwargs):
    # Byte strings default to "" if not specified.
    super(ProtoBinary, self).__init__(**kwargs)

    # Ensure the default is a string object.
    if default is not None:
      self.default = utils.SmartStr(default)

  def Validate(self, value, **_):
    if value.__class__ is not str:
      raise type_info.TypeValueError("%s not a valid string" % value)

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
    super(ProtoUnsignedInteger, self).__init__(default=default, **kwargs)

  def ConvertFromWireFormat(self, value, container=None):
    return VarintReader(value[2], 0)[0]

  def ConvertToWireFormat(self, value):
    return (self.encoded_tag, "", VarintEncode(value))

  def Validate(self, value, **_):
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
    return (self.encoded_tag, "", SignedVarintEncode(value))


class ProtoFixed32(ProtoUnsignedInteger):
  """A 32 bit fixed unsigned integer.

  The wire format is a 4 byte string, while the python type is a long.
  """
  _size = 4

  proto_type_name = "sfixed32"
  wire_type = WIRETYPE_FIXED32

  def ConvertToWireFormat(self, value):
    return (self.encoded_tag, "", struct.pack("<L", long(value)))

  def ConvertFromWireFormat(self, value, container=None):
    return struct.unpack("<L", value[2])[0]


class ProtoFixed64(ProtoFixed32):
  _size = 8

  proto_type_name = "sfixed64"
  wire_type = WIRETYPE_FIXED64

  def ConvertToWireFormat(self, value):
    return (self.encoded_tag, "", struct.pack("<Q", long(value)))

  def ConvertFromWireFormat(self, value, container=None):
    return struct.unpack("<Q", value[2])[0]


class ProtoFixedU32(ProtoFixed32):
  """A 32 bit fixed unsigned integer.

  The wire format is a 4 byte string, while the python type is a long.
  """
  proto_type_name = "fixed32"

  def ConvertToWireFormat(self, value):
    return (self.encoded_tag, "", struct.pack("<l", long(value)))

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
    return (self.encoded_tag, "", struct.pack("<f", float(value)))

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
    return (self.encoded_tag, "", struct.pack("<d", float(value)))

  def ConvertFromWireFormat(self, value, container=None):
    return struct.unpack("<d", value[2])[0]


# TODO(user): This is deprecated in favor of EnumNamedValue. Remove as soon
# as there are no hunts with old-style Enum pickled in the state.
class Enum(int):
  """A class that wraps enums.

  Enums are just integers, except when printed they have a name.
  """

  def __new__(cls, val, name=None, description=None):
    instance = super(Enum, cls).__new__(cls, val)
    instance.name = name or str(val)
    instance.description = description

    return instance

  def __eq__(self, other):
    return int(self) == other or self.name == other

  def __str__(self):
    return self.name

  def __unicode__(self):
    return unicode(self.name)


class EnumValue(Enum):
  """Backwards compatibility for stored data.

  This class is necessary for reading data created with GRR server version
  0.2.9-1 and earlier.  It can be removed when we can drop support for this old
  data.
  """
  pass


class EnumNamedValue(rdfvalue.RDFInteger):
  """A class that wraps enums.

  Enums are just integers, except when printed they have a name.
  """

  def __init__(self, initializer=None, name=None, description=None, age=None):
    super(EnumNamedValue, self).__init__(initializer)
    self.name = name or str(initializer)
    self.description = description

  # TODO(user): EnumNamedValue loses some information when serialized.
  # Currently this only matters when it's pickled (usually - as part of
  # FlowState). Find a proper way to Serialize/Deserialize it without losing
  # name/description.
  def __getstate__(self):
    return self.__dict__

  def __setstate__(self, data):
    self.__dict__ = data

  def __eq__(self, other):
    return int(self) == other or self.name == other

  def __str__(self):
    return self.name

  def __unicode__(self):
    return unicode(self.name)


class ProtoEnum(ProtoSignedInteger):
  """An enum native proto type.

  This is really encoded as an integer but only certain values are allowed.
  """

  type = EnumNamedValue

  def __init__(self, default=None, enum_name=None, enum=None,
               enum_descriptions=None, **kwargs):
    super(ProtoEnum, self).__init__(**kwargs)
    if enum_name is None:
      raise type_info.TypeValueError("Enum groups must be given a name.")

    self.enum_name = enum_name
    self.proto_type_name = enum_name
    if isinstance(enum, EnumContainer):
      enum = enum.enum_dict

    for v in enum.itervalues():
      if not (v.__class__ is int or v.__class__ is long):
        raise type_info.TypeValueError("Enum values must be integers.")

    self.enum_container = EnumContainer(
        name=enum_name, descriptions=enum_descriptions, **(enum or {}))
    self.enum = self.enum_container.enum_dict
    self.reverse_enum = self.enum_container.reverse_enum

    # Ensure the default is a valid enum value.
    if default is not None:
      self.default = self.Validate(default)

  def GetDefault(self, container=None):
    _ = container
    return EnumNamedValue(self.default,
                          name=self.reverse_enum.get(self.default))

  def Validate(self, value, **_):
    """Check that value is a valid enum."""
    # None is a valid value - it means the field is not set.
    if value is None:
      return

    # If the value is a string we need to try to convert it to an integer.
    checked_value = value
    if isinstance(value, basestring):
      checked_value = self.enum.get(value)
      if checked_value is None and value.isdigit():
        checked_value = int(value)
      if checked_value is None:
        raise type_info.TypeValueError(
            "Value %s is not a valid enum value for field %s" % (
                value, self.name))

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
    return (self.encoded_tag, "", SignedVarintEncode(int(value)))

  def ConvertFromWireFormat(self, value, container=None):
    value = SignedVarintReader(value[2], 0)[0]
    return EnumNamedValue(value, name=self.reverse_enum.get(value))


class ProtoBoolean(ProtoEnum):
  """A Boolean."""

  type = rdfvalue.RDFBool

  def __init__(self, **kwargs):
    super(ProtoBoolean, self).__init__(
        enum_name="Bool", enum=dict(True=1, False=0), **kwargs)

    self.proto_type_name = "bool"

  def GetDefault(self, container=None):
    """Return boolean value."""
    return rdfvalue.RDFBool(
        super(ProtoBoolean, self).GetDefault(container=container))

  def Validate(self, value, **_):
    """Check that value is a valid enum."""
    if value is None:
      return

    return rdfvalue.RDFBool(
        super(ProtoBoolean, self).Validate(value))

  def ConvertFromWireFormat(self, value, container=None):
    return rdfvalue.RDFBool(
        super(ProtoBoolean, self).ConvertFromWireFormat(value,
                                                        container=container))


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
    super(ProtoEmbedded, self).__init__(**kwargs)

    # Nested can refer to a target RDFProtoStruct by name.
    if isinstance(nested, basestring):
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
          "Only RDFProtoStructs can be nested, not %s" % nested.__name__)

  def ConvertFromWireFormat(self, value, container=None):
    """The wire format is simply a string."""
    result = self.type()
    ReadIntoObject(value[2], 0, result)

    return result

  def ConvertToWireFormat(self, value):
    """Encode the nested protobuf into wire format."""
    output = []
    for entry in value.GetRawData().itervalues():
      python_format, wire_format, type_descriptor = entry

      if wire_format is None or (python_format and
                                 type_descriptor.IsDirty(python_format)):
        wire_format = type_descriptor.ConvertToWireFormat(python_format)

      output.extend(wire_format)

    output = "".join(output)
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
      raise TypeError("Field %s expects a protobuf, but target is %s" %
                      self, target)

    self.late_bound = False

    # The target type is now resolved.
    self.type = target

    # Register us in our owner.
    self.owner.AddDescriptor(self)

  def IsDirty(self, proto):
    """Return and clear the dirty state of the python object."""
    if proto.dirty:
      return True

    for python_format, _, type_descriptor in proto.GetRawData().itervalues():
      if python_format is not None and type_descriptor.IsDirty(python_format):
        proto.dirty = True
        return True

    return False

  def GetDefault(self, container=None):
    """When a nested proto is accessed, default to an empty one."""
    return self.type()

  def Validate(self, value, **_):
    if isinstance(value, basestring):
      raise type_info.TypeValueError(
          "Field %s must be of type %s" % (self.name, self.type.__name__))

    # We may coerce it to the correct type.
    if value.__class__ is not self.type:
      try:
        value = self.type(value)
      except rdfvalue.InitializeError:
        raise type_info.TypeValueError(
            "Field %s must be of type %s" % (self.name, self.type.__name__))

    return value

  def Definition(self):
    """Return a string with the definition of this field."""
    return self._FormatDescriptionComment() + self._FormatField()

  def _FormatField(self):
    result = "  optional %s %s = %s" % (self.proto_type_name,
                                        self.name, self.field_number)
    return result + ";\n"

  def Format(self, value):
    for line in value.Format():
      yield "  %s" % line


class ProtoDynamicEmbedded(ProtoType):
  """An embedded field which has a dynamic type."""

  wire_type = WIRETYPE_LENGTH_DELIMITED

  set_default_on_access = True

  def __init__(self, dynamic_cb=None, **kwargs):
    """Initialize the type descriptor.

    We call the dynamic_method to know which type should be used to decode the
    embedded bytestream.

    Args:
      dynamic_cb: A callback to be used to return the class to parse the
      embedded data. We pass the callback our container.

      **kwargs: Passthrough.
    """
    super(ProtoDynamicEmbedded, self).__init__(**kwargs)
    self._type = dynamic_cb

  def ConvertFromWireFormat(self, value, container=None):
    """The wire format is simply a string."""
    return self._type(container)(value[2])

  def ConvertToWireFormat(self, value):
    """Encode the nested protobuf into wire format."""
    data = value.SerializeToString()
    return (self.encoded_tag, VarintEncode(len(data)), data)

  def Validate(self, value, container=None):
    required_type = self._type(container)
    if required_type and not isinstance(value, required_type):
      raise ValueError("Expected value of type %s" % required_type)

    return value

  def GetDefault(self, container=None):
    cls = self._type(container or self.owner())
    if cls is not None:
      return cls()

  def Format(self, value):
    for line in value.Format():
      yield "  %s" % line


class RepeatedFieldHelper(object):
  """A helper for the RDFProto to handle repeated fields.

  This helper is intended to only be constructed from the RDFProto class.
  """

  __metaclass__ = registry.MetaclassRegistry

  dirty = False

  def __init__(self, wrapped_list=None, type_descriptor=None, container=None):
    """Constructor.

    Args:
      wrapped_list: The list within the protobuf which we wrap.
      type_descriptor: A type descriptor describing the type of the list
        elements..
      container: The protobuf which contains this repeated field.

    Raises:
      AttributeError: If parameters are not valid.
    """
    if wrapped_list is None:
      self.wrapped_list = []

    elif wrapped_list.__class__ is RepeatedFieldHelper:
      self.wrapped_list = wrapped_list.wrapped_list

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
    return RepeatedFieldHelper(wrapped_list=self.wrapped_list[:],
                               type_descriptor=self.type_descriptor)

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
            "Assignment value must be %s, but %s can not "
            "be coerced. Error: %s" % (self.type_descriptor.proto_type_name,
                                       type(rdf_value), e))

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

  def __getitem__(self, item):
    # Ensure we handle slices as well.
    if item.__class__ is slice:
      result = []
      for i in range(*item.indices(len(self))):
        result.append(self.wrapped_list[i])

      return self.__class__(
          wrapped_list=result, type_descriptor=self.type_descriptor)

    python_format, wire_format = self.wrapped_list[item]
    if python_format is None:
      python_format = self.type_descriptor.ConvertFromWireFormat(
          wire_format, container=self.container)

      self.wrapped_list[item] = (python_format, wire_format)

    return python_format

  def __len__(self):
    return len(self.wrapped_list)

  def __ne__(self, other):
    return not self == other  # pylint: disable=g-comparison-negation

  def __eq__(self, other):
    if len(self) != len(other):
      return False
    for x, y in zip(self, other):
      if x != y:
        return False
    return True

  def __str__(self):
    result = []
    result.append("'%s': [" % self.type_descriptor.name)
    for element in self:
      for line in self.type_descriptor.Format(element):
        result.append(" %s" % line)

    result.append("]")

    return "\n".join(result)

  def __unicode__(self):
    return utils.SmartUnicode(str(self))

  def Validate(self):
    for x in self:
      x.Validate()


class ProtoList(ProtoType):
  """A repeated type."""

  set_default_on_access = True

  def __init__(self, delegate, labels=None, **kwargs):
    self.delegate = delegate
    if not isinstance(delegate, ProtoType):
      raise AttributeError(
          "Delegate class must derive from ProtoType, not %s" %
          delegate.__class__.__name__)

    # If our delegate is late bound we must also be late bound. This means that
    # the repeated field is not registered in the owner protobuf just
    # yet. However, we do not actually need to register a late binding callback
    # ourselves, since the delegate field descriptor already did this. We simply
    # wait until the delegate calls our AddDescriptor() method and then we call
    # our own owner's AddDescriptor() method to ensure we re-register.
    self.late_bound = delegate.late_bound

    self.wire_type = delegate.wire_type

    super(ProtoList, self).__init__(name=delegate.name,
                                    description=delegate.description,
                                    field_number=delegate.field_number,
                                    friendly_name=delegate.friendly_name,
                                    labels=labels)

  def IsDirty(self, value):
    return value.IsDirty()

  def GetDefault(self, container=None):
    # By default an empty RepeatedFieldHelper.
    return RepeatedFieldHelper(type_descriptor=self.delegate,
                               container=container)

  def Validate(self, value, **_):
    """Check that value is a list of the required type."""
    # Assigning from same kind can allow us to skip verification since all
    # elements in a RepeatedFieldHelper already are coerced to the delegate
    # type. In that case we just make a copy. This only works when the value
    # wraps the same type as us.
    if (value.__class__ is RepeatedFieldHelper and
        value.type_descriptor is self.delegate):
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
    output = []
    for python_format, wire_format in value.wrapped_list:
      if wire_format is None or (python_format and
                                 value.type_descriptor.IsDirty(python_format)):
        wire_format = value.type_descriptor.ConvertToWireFormat(python_format)

      output.extend(wire_format)

    return ("", "", "".join(output))

  def Format(self, value):
    yield "["

    for element in value:
      for line in self.delegate.Format(element):
        yield " %s" % line

    yield "]"

  def _FormatField(self):
    result = "  repeated %s %s = %s" % (
        self.delegate.proto_type_name, self.name, self.field_number)

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


class ProtoRDFValue(ProtoBinary):
  """Serialize arbitrary rdfvalue members.

  RDFValue members can be serialized in a number of different ways according to
  their preferred data_store_type member. We map the descriptions in
  data_store_type into a suitable protobuf serialization for optimal
  serialization. We therefore use a delegate type descriptor to best convert
  from the RDFValue to the wire type. For example, an RDFDatetime is best
  represented as an integer (number of microseconds since the epoch). Hence
  RDFDatetime.SerializeToDataStore() will return an integer, and the delegate
  will be ProtoUnsignedInteger().

  To convert from the RDFValue python type to the delegate's wire type we
  therefore need to make two conversions:

  1) Our python format is the RDFValue -> intermediate data store format using
  RDFValue.SerializeToDataStore(). This will produce a python object which is
  the correct python format for the delegate primitive type descriptor.

  2) Use the delegate to obtain the wire format of its own python type
  (i.e. self.delegate.ConvertToWireFormat())

  NOTE: The default value for an RDFValue is None. It is impossible for us to
  know how to instantiate a valid default value without being told by the
  user. This is unlike the default value for strings or ints which are "" and 0
  respectively.
  """

  # We delegate encoding/decoding to a primitive field descriptor based on the
  # semantic type's data_store_type attribute.
  primitive_desc = None

  # We store our args here so we can use the same args to initialize the
  # delegate descriptor.
  _kwargs = None

  _PROTO_DATA_STORE_LOOKUP = dict(
      bytes=ProtoBinary,
      unsigned_integer=ProtoUnsignedInteger,
      integer=ProtoUnsignedInteger,
      signed_integer=ProtoSignedInteger,
      string=ProtoString)

  def __init__(self, rdf_type=None, default=None, **kwargs):
    super(ProtoRDFValue, self).__init__(default=default, **kwargs)
    self._kwargs = kwargs

    if isinstance(rdf_type, basestring):
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
    elif issubclass(rdf_type, rdfvalue.RDFValue):
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
    """Finds the primitive encoder according to the type's data_store_type."""
    # Decide what should the primitive type be for packing the target rdfvalue
    # into the protobuf and create a delegate descriptor to control that.
    primitive_cls = self._PROTO_DATA_STORE_LOOKUP[self.type.data_store_type]
    self.primitive_desc = primitive_cls(**self._kwargs)

    # Our wiretype is the same as the delegate's.
    self.wire_type = self.primitive_desc.wire_type
    self.proto_type_name = self.primitive_desc.proto_type_name

    # Recalculate our tags.
    self.CalculateTags()

  def GetDefault(self, container=None):
    _ = container
    # We must return an instance of our type. This allows the field to be
    # initialized with a string default.
    if self.default is not None and self.default.__class__ is not self.type:
      return self.Validate(self.default)
    else:
      return self.default

  def IsDirty(self, python_format):
    """Return the dirty state of the python object."""
    return python_format.dirty

  def Definition(self):
    return ("\n  // Semantic Type: %s" %
            self.type.__name__) + self.primitive_desc.Definition()

  def Validate(self, value, **_):
    # Try to coerce into the correct type:
    if value.__class__ is not self.type:
      try:
        value = self.type(value)
      except rdfvalue.DecodeError as e:
        raise type_info.TypeValueError(e)

    return value

  def ConvertFromWireFormat(self, value, container=None):
    # Wire format should be compatible with the data_store_type for the
    # rdfvalue. We use the delegate primitive descriptor to perform the
    # conversion.
    value = self.primitive_desc.ConvertFromWireFormat(
        value, container=container)

    result = self.type(value)

    return result

  def ConvertToWireFormat(self, value):
    return self.primitive_desc.ConvertToWireFormat(value.SerializeToDataStore())

  def Copy(self, field_number=None):
    """Returns descriptor copy, optionally changing field number."""
    new_args = self._kwargs.copy()
    if field_number is not None:
      new_args["field_number"] = field_number

    return ProtoRDFValue(rdf_type=self.original_proto_type_name,
                         default=getattr(self, "default", None),
                         **new_args)

  def _FormatField(self):
    result = "  optional %s %s = %s" % (self.proto_type_name,
                                        self.name, self.field_number)
    return result + ";\n"

  def Format(self, value):
    yield "%s:" % self.type.__name__
    for line in str(value).splitlines():
      yield "  %s" % line

  def __str__(self):
    return "<Field %s (Sem Type: %s) of %s: field_number: %s>" % (
        self.name, self.proto_type_name, self.owner.__name__,
        self.field_number)


class AbstractSerlializer(object):
  """A serializer which parses to/from the intermediate python objects."""

  def SerializeToString(self, value):
    """Serialize the RDFStruct object into a string."""

  def ParseFromString(self, value_obj, string):
    """Parse the string and set attributes in the value_obj."""


class RDFStructMetaclass(rdfvalue.RDFValueMetaclass):
  """A metaclass which registers new RDFProtoStruct instances."""

  def __init__(cls, name, bases, env_dict):  # pylint: disable=no-self-argument
    super(RDFStructMetaclass, cls).__init__(name, bases, env_dict)

    cls.type_infos = type_info.TypeDescriptorSet()

    # Keep track of the late bound fields.
    cls.late_bound_type_infos = {}

    cls.type_infos_by_field_number = {}
    cls.type_infos_by_encoded_tag = {}

    # Build the class by parsing an existing protobuf class.
    if cls.protobuf is not None:
      proto2.DefineFromProtobuf(cls, cls.protobuf)

    # Pre-populate the class using the type_infos class member.
    if cls.type_description is not None:
      for field_desc in cls.type_description:
        cls.AddDescriptor(field_desc)

    # Allow the class to suppress some fields.
    if cls.suppressions:
      cls.type_infos = cls.type_infos.Remove(*cls.suppressions)

    cls._class_attributes = set(dir(cls))


class RDFStruct(rdfvalue.RDFValue):
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

  __metaclass__ = RDFStructMetaclass

  # This can be populated with a type_info.TypeDescriptorSet() object to
  # initialize the class.
  type_description = None

  # This class can be defined using the protobuf definition language (e.g. a
  # .proto file). If defined here, we parse the .proto file for the message with
  # the exact same class name and add the field descriptions from it.
  definition = None

  # This class can be defined in terms of an existing annotated regular
  # protobuf. See RDFProtoStruct.DefineFromProtobuf().
  protobuf = None

  # This is where the type infos are constructed.
  type_infos = None

  # Mark as dirty each time we modify this object.
  dirty = False

  # Stores the raw data here.
  _data = None

  # A list of fields which will be removed from this class's type descriptor
  # set.
  suppressions = []

  def __init__(self, initializer=None, age=None, **kwargs):
    # Maintain the order so that parsing and serializing a proto does not change
    # the serialized form.
    self._data = {}
    self._age = age

    for arg, value in kwargs.iteritems():
      if not hasattr(self.__class__, arg):
        if arg in self.late_bound_type_infos:
          raise AttributeError(
              "Field %s refers to an as yet undefined Semantic Type." %
              self.late_bound_type_infos[arg])

        raise AttributeError(
            "Proto %s has no field %s" % (self.__class__.__name__, arg))

      # Call setattr to allow the class to define @property psuedo fields which
      # can also be initialized.
      setattr(self, arg, value)

    if initializer is None:
      return

    elif initializer.__class__ is self.__class__:
      self.CopyConstructor(initializer)

    elif initializer.__class__ is str:
      self.ParseFromString(initializer)

    else:
      raise ValueError("%s can not be initialized from %s" % (
          self.__class__.__name__, type(initializer)))

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
    for name, (obj, serialized, t_info) in other.GetRawData().iteritems():
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
    for name, (obj, serialized, t_info) in self._data.iteritems():
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

  def Copy(self):
    """Make an efficient copy of this protobuf."""
    result = self.__class__()
    result.SetRawData(self._CopyRawData())

    # The copy should have the same age as us.
    result.age = self.age

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

  def SerializeToString(self):
    output = []
    for entry in self._data.itervalues():
      python_format, wire_format, type_descriptor = entry

      if wire_format is None or (python_format and
                                 type_descriptor.IsDirty(python_format)):
        wire_format = type_descriptor.ConvertToWireFormat(python_format)

      output.extend(wire_format)

    return "".join(output)

  def ParseFromString(self, string):
    ReadIntoObject(string, 0, self)
    self.dirty = True

  def __eq__(self, other):
    if not isinstance(other, self.__class__):
      return False

    if len(self._data) != len(other.GetRawData()):
      return False

    for field in self._data:
      if self.Get(field) != other.Get(field):
        return False

    return True

  def __ne__(self, other):
    return not self == other  # pylint: disable=g-comparison-negation

  def Format(self):
    """Format a message in a human readable way."""
    yield "message %s {" % self.__class__.__name__

    for k, (python_format, wire_format,
            type_descriptor) in sorted(self.GetRawData().items()):
      if python_format is None:
        python_format = type_descriptor.ConvertFromWireFormat(
            wire_format, container=self)

      # Skip printing of unknown fields.
      if isinstance(k, basestring):
        prefix = utils.SmartStr(k) + " :"
        for line in type_descriptor.Format(python_format):
          yield " %s %s" % (prefix, line)
          prefix = ""

    yield "}"

  def __str__(self):
    return "\n".join(self.Format())

  def __unicode__(self):
    return utils.SmartUnicode(str(self))

  def __dir__(self):
    """Add the virtualized fields to the console's tab completion."""
    return (dir(super(RDFStruct, self)) +
            [x.name for x in self.type_infos])

  def _Set(self, value, type_descriptor):
    """Validate the value and set the attribute with it."""
    attr = type_descriptor.name
    # A value of None means we clear the field.
    if value is None:
      self._data.pop(attr, None)
      return

    # Validate the value and obtain the python format representation.
    value = type_descriptor.Validate(value, container=self)

    # Store the lazy value object.
    self._data[attr] = (value, None, type_descriptor)

    # Make sure to invalidate our parent's cache if needed.
    self.dirty = True

    return value

  def Set(self, attr, value):
    """Sets the attribute in to the value."""
    type_info_obj = self.type_infos.get(attr)

    if type_info_obj is None:
      raise AttributeError("Field %s is not known." % attr)

    return self._Set(value, type_info_obj)

  def Get(self, attr):
    """Retrieve the attribute specified."""
    entry = self._data.get(attr)
    # We dont have this field, try the defaults.
    if entry is None:
      type_descriptor = self.type_infos.get(attr)

      if type_descriptor is None:
        raise AttributeError("'%s' object has no attribute '%s'" % (
            self.__class__.__name__, attr))

      # Assign the default value now.
      default = type_descriptor.GetDefault(container=self)
      if default is None:
        return

      if type_descriptor.set_default_on_access:
        default = self.Set(attr, default)

      return default

    python_format, wire_format, type_descriptor = entry

    # Decode on demand and cache for next time.
    if python_format is None:
      python_format = type_descriptor.ConvertFromWireFormat(
          wire_format, container=self)

      self._data[attr] = (python_format, wire_format, type_descriptor)

    return python_format

  def GetPrimitive(self, attr):
    """Retrieve the primitive used to encode the attribute.

    This method allows to bypass the semantic coercion on semantic fields in
    order to retrieve the primitive protobuf member. This should only even be
    done for invalid protobufs which can not parse the primitive into an object
    type. In other words this is a major hack and should be used sparingly.

    Args:
      attr: The name of the attribute to retrieve.

    Returns:
      A primitive (int, string, etc) encoded in the field.
    """
    entry = self._data.get(attr)
    # We dont have this field, try the defaults.
    if entry is None:
      return ""

    python_format, wire_format, type_descriptor = entry
    if wire_format is None:
      wire_format = type_descriptor.ConvertToWireFormat(python_format)

    return type_descriptor.primitive_desc.ConvertFromWireFormat(
        wire_format)

  def SetPrimitive(self, attr, value):
    """Sets the primitive used to encode an attribute.

    This method allows to bypass the type checking afforded by the regular
    semantic layer when assigning to the field. Using this method sets the
    underlying primitive used to encode the field directly. This is a major hack
    and should be used sparingly because it allows to create invalid protobufs.

    Args:
      attr: The name of the attribute to set.
      value: A primitive (int, string etc) which will be set to this field.

    Raises:
      AttributeError: If the field is not known.
    """
    type_info_obj = self.type_infos.get(attr)

    if type_info_obj is None:
      raise AttributeError("Field %s is not known." % attr)

    value = type_info_obj.primitive_desc.ConvertToWireFormat(value)
    self._data[attr] = (None, value, type_info_obj)

    # Make sure to invalidate our parent's cache if needed.
    self.dirty = True

  @classmethod
  def AddDescriptor(cls, field_desc):
    if not isinstance(field_desc, ProtoType):
      raise type_info.TypeValueError(
          "%s field '%s' should be of type ProtoType" % (
              cls.__name__, field_desc.name))

    cls.type_infos_by_field_number[field_desc.field_number] = field_desc
    cls.type_infos.Append(field_desc)

  def __getstate__(self):
    """Support the pickle protocol."""
    return dict(data=self.SerializeToString())

  def __setstate__(self, data):
    """Support the pickle protocol."""
    self._data = {}
    self.ParseFromString(data["data"])


class EnumContainer(object):
  """A data class to hold enum objects."""

  def __init__(self, name=None, descriptions=None, **kwargs):
    descriptions = descriptions or {}

    self.enum_dict = {}
    self.reverse_enum = {}
    self.name = name

    for k, v in kwargs.items():
      v = EnumNamedValue(v, name=k, description=descriptions.get(k, None))
      self.enum_dict[k] = v
      self.reverse_enum[v] = k
      setattr(self, k, v)


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

  # By default include standard semantic objects. Additional objects can be
  # added if needed.
  _dependencies = dict(RDFURN=rdfvalue.RDFURN,
                       RDFDatetime=rdfvalue.RDFDatetime)

  def AsPrimitiveProto(self):
    """Return an old style protocol buffer object."""
    if self.protobuf:
      result = self.protobuf()
      result.ParseFromString(self.SerializeToString())
      return result

  def AsDict(self):
    result = {}
    for desc in self.type_infos:
      if self.HasField(desc.name):
        result[desc.name] = self.Get(desc.name)

    return result

  def ToPrimitiveDict(self):
    return self._ToPrimitive(self.AsDict())

  def _ToPrimitive(self, value):
    if isinstance(value, RepeatedFieldHelper):
      return list(self._ToPrimitive(v) for v in value)
    # Hack to avoid dependency loop. Safe because if value is a protodict.Dict,
    # then protodict has already been loaded.
    # TODO(user): remove this hack
    elif "Dict" in rdfvalue.RDFValue.classes and isinstance(
        value, rdfvalue.RDFValue.classes["Dict"]):
      new_val = value.ToDict()
      return dict((k, self._ToPrimitive(v)) for k, v in new_val.items())
    elif isinstance(value, dict):
      return dict((k, self._ToPrimitive(v)) for k, v in value.items())
    elif isinstance(value, RDFProtoStruct):
      return self._ToPrimitive(value.AsDict())
    elif isinstance(value, (Enum, EnumValue, EnumNamedValue)):
      return str(value)
    else:
      return value

  def __nonzero__(self):
    return bool(self._data)

  @classmethod
  def EmitProto(cls):
    """Emits .proto file definitions."""
    result = "message %s {\n" % cls.__name__
    for _, desc in sorted(cls.type_infos_by_field_number.items()):
      result += desc.Definition()

    result += "}\n"
    return result

  PRIMITIVE_TYPE_MAPPING = {
      "string": descriptor_pb2.FieldDescriptorProto.TYPE_STRING,
      "bytes": descriptor_pb2.FieldDescriptorProto.TYPE_BYTES,
      "uint64": descriptor_pb2.FieldDescriptorProto.TYPE_UINT64,
      "int64": descriptor_pb2.FieldDescriptorProto.TYPE_INT32,
      "float": descriptor_pb2.FieldDescriptorProto.TYPE_FLOAT,
      "double": descriptor_pb2.FieldDescriptorProto.TYPE_DOUBLE,
      "bool": descriptor_pb2.FieldDescriptorProto.TYPE_BOOL
  }

  @classmethod
  def EmitProtoFileDescriptor(cls, package_name):
    file_descriptor = descriptor_pb2.FileDescriptorProto()
    file_descriptor.name = cls.__name__.lower() + ".proto"
    file_descriptor.package = package_name

    descriptors = dict()

    message_type = file_descriptor.message_type.add()
    message_type.name = cls.__name__

    for number, desc in sorted(cls.type_infos_by_field_number.items()):
      # Name 'metadata' is reserved to store ExportedMetadata value.
      field = None
      if (isinstance(desc, type_info.ProtoEnum) and
          not isinstance(desc, type_info.ProtoBoolean)):
        field = message_type.field.add()
        field.type = descriptor_pb2.FieldDescriptorProto.TYPE_ENUM
        field.type_name = desc.enum_name

        if desc.enum_name not in [x.name for x in message_type.enum_type]:
          enum_type = message_type.enum_type.add()
          enum_type.name = desc.enum_name
          for key, value in desc.enum.iteritems():
            enum_type_value = enum_type.value.add()
            enum_type_value.name = key
            enum_type_value.number = int(value)

      elif isinstance(desc, type_info.ProtoEmbedded):
        field = message_type.field.add()
        field.type = descriptor_pb2.FieldDescriptorProto.TYPE_MESSAGE

        if hasattr(desc.type, "protobuf"):
          field.type_name = "." + desc.type.protobuf.DESCRIPTOR.full_name
          descriptors[field.type_name] = desc.type.protobuf.DESCRIPTOR

          # Register import of a proto file containing embedded protobuf
          # definition.
          if (desc.type.protobuf.DESCRIPTOR.file.name not in
              file_descriptor.dependency):
            file_descriptor.dependency.append(
                desc.type.protobuf.DESCRIPTOR.file.name)
        else:
          raise NotImplementedError("Can't emit proto descriptor for values "
                                    "with nested non-protobuf-based values.")
      elif isinstance(desc, type_info.ProtoList):
        field = message_type.field.add()
        field.type = descriptor_pb2.FieldDescriptorProto.TYPE_MESSAGE

        if hasattr(desc.type, "protobuf"):
          field.type_name = "." + desc.type.protobuf.DESCRIPTOR.full_name
        else:
          raise NotImplementedError("Can't emit proto descriptor for values "
                                    "with repeated non-protobuf-based values.")
        field.label = descriptor_pb2.FieldDescriptorProto.LABEL_REPEATED
      else:
        field = message_type.field.add()
        field.type = cls.PRIMITIVE_TYPE_MAPPING[desc.proto_type_name]

      if field:
        field.name = desc.name
        field.number = number
        if not field.HasField("label"):
          field.label = descriptor_pb2.FieldDescriptorProto.LABEL_OPTIONAL

    # Find all dependent files.
    files = dict((d.file.name, d.file) for d in descriptors.values())
    while True:
      dependency_added = False

      for fd in files.values():
        for fd_dep in fd.dependencies:
          if fd_dep.name not in files:
            files[fd_dep.name] = fd_dep
            dependency_added = True

      if not dependency_added:
        break

    # Add all dependent files to the pool.
    dependencies = []
    for fd in files.values():
      fd_proto = descriptor_pb2.FileDescriptorProto()
      fd.CopyToProto(fd_proto)
      dependencies.append(fd_proto)

    return file_descriptor, dependencies

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
    tmp = cls.protobuf()  # pylint: disable=not-callable
    text_format.Merge(text, tmp)

    return cls(tmp.SerializeToString())

  @classmethod
  def AddDescriptor(cls, field_desc):
    """Register this descriptor with the Proto Struct."""
    if not isinstance(field_desc, ProtoType):
      raise type_info.TypeValueError(
          "%s field '%s' should be of type ProtoType" % (
              cls.__name__, field_desc.name))

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
          "Field number %s for field %s is not unique in %s" % (
              field_desc.field_number, field_desc.name, cls.__name__))

    # We store an index of the type info by tag values to speed up parsing.
    cls.type_infos_by_field_number[field_desc.field_number] = field_desc
    cls.type_infos_by_encoded_tag[field_desc.encoded_tag] = field_desc

    cls.type_infos.Append(field_desc)
    cls.late_bound_type_infos.pop(field_desc.name, None)

    # Add direct accessors only if the class does not already have them.
    if not hasattr(cls, field_desc.name):
      # This lambda is a class method so pylint: disable=protected-access
      # This is much faster than __setattr__/__getattr__
      setattr(cls, field_desc.name, property(
          lambda self: self.Get(field_desc.name),
          lambda self, x: self._Set(x, field_desc),
          None, field_desc.description))


class SemanticDescriptor(RDFProtoStruct):
  """A semantic protobuf describing the .proto extension."""
  protobuf = semantic_pb2.SemanticDescriptor
