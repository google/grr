#!/usr/bin/env python
"""RDFStructs are serialization agnostic, rich data types."""



import cStringIO
import json

from google.protobuf.internal import decoder
from google.protobuf.internal import encoder
from google.protobuf.internal import wire_format

from grr.lib import rdfvalue
from grr.lib import registry
from grr.lib import type_info
from grr.lib import utils

from grr.lib.rdfvalues import structs_parser


# The following are the varint encoding/decoding functions taken from the
# protobuf library. If we end up copying these in here we can remove all
# dependency on the protobuf library. This is tempting...

# These are actually functions and not constants.
# pylint: disable=g-bad-name,protected-access
VarintWriter = encoder._EncodeVarint
SignedVarintWriter = encoder._EncodeSignedVarint

VarintReader = decoder._DecodeVarint
SignedVarintReader = decoder._DecodeSignedVarint
# pylint: enable=g-bad-name,protected-access


class ProtoType(type_info.TypeInfoObject):
  """A specific type descriptor for protobuf fields.

  This is an abstract class - do not instantiate directly.
  """
  # Must be overridden by implementations.
  wire_type = None

  def __init__(self, field_number=None, required=False, **kwargs):
    super(ProtoType, self).__init__(**kwargs)
    self.field_number = field_number
    self.required = required
    if field_number is None:
      raise type_info.TypeValueError("No valid field number specified.")

    # In python Varint encoding is expensive so we want to move as much of the
    # hard work from the Write() methods which are called frequently to the type
    # descriptor constructor which is only called once (during protobuf
    # decleration time). Pre-calculating the tag makes for faster serialization.
    self.tag = self.field_number << 3 | self.wire_type
    tmp = cStringIO.StringIO()
    VarintWriter(tmp.write, self.tag)
    self.tag_data = tmp.getvalue()

  def Write(self, stream, value):
    """Encode the tag and value into the stream."""
    raise NotImplementedError()

  def Read(self, buff, index):
    raise NotImplementedError()

  def Definition(self):
    """Return a string with the definition of this field."""
    return ""

  def ConvertFromWireFormat(self, value):
    """Convert value from the internal type to the real type.

    When data is being parsed, it might be quicker to store it in a different
    format internally. This is because we must parse all data, but only decode
    those fields which are being accessed.

    This function is called when we retrieve a field on access, so we only pay
    the penalty once.

    Args:
      value: A parameter stored in the internal format for this type.

    Returns:
      The decoded parameter.
    """
    return value

  def ConvertToWireFormat(self, value):
    """Convert the parameter into the internal storage format."""
    return value

  def _FormatDescriptionComment(self):
    result = "".join(["\n  // %s\n"%x for x in self.description.splitlines()])
    return result

  def _FormatField(self, proto_type_name, ignore_default=None):
    result = "  optional %s %s = %s" % (proto_type_name,
                                        self.name, self.field_number)

    if self.GetDefault() != ignore_default:
      result += " [default = %s]" % self.GetDefault()

    return result + ";\n"


class ProtoString(ProtoType):
  """A string encoded in a protobuf."""

  wire_type = wire_format.WIRETYPE_LENGTH_DELIMITED

  def Validate(self, value):
    if not isinstance(value, basestring):
      raise type_info.TypeValueError("%s not a valid string" % value)

    # A String means a unicode String. We must be dealing with unicode strings
    # here and the input must be encodable as a unicode object.
    try:
      return unicode(value)
    except UnicodeError:
      raise type_info.TypeValueError("Not a valid unicode string")

  def Write(self, stream, value):
    stream.write(self.tag_data)
    value = value.encode("utf8")
    VarintWriter(stream.write, len(value))
    stream.write(value)

  def Read(self, buff, index):
    length, index = VarintReader(buff, index)
    return buff[index:index+length], index+length

  def ConvertFromWireFormat(self, value):
    """Internally strings are utf8 encoded."""
    return unicode(value, "utf8")

  def ConvertToWireFormat(self, value):
    """Internally strings are utf8 encoded."""
    return value.encode("utf8")

  def Definition(self):
    """Return a string with the definition of this field."""
    return self._FormatDescriptionComment() + self._FormatField(
        "string")


class ProtoBinary(ProtoType, type_info.String):
  """A binary string encoded in a protobuf."""

  wire_type = wire_format.WIRETYPE_LENGTH_DELIMITED

  def Write(self, stream, value):
    stream.write(self.tag_data)
    VarintWriter(stream.write, len(value))
    stream.write(value)

  def Read(self, buff, index):
    length, index = VarintReader(buff, index)
    return buff[index:index+length], index+length

  def Definition(self):
    """Return a string with the definition of this field."""
    return self._FormatDescriptionComment() + self._FormatField(
        "bytes", "")


class ProtoUnsignedInteger(ProtoType, type_info.Integer):
  """An unsigned VarInt encoded in the protobuf."""

  wire_type = wire_format.WIRETYPE_VARINT

  def Write(self, stream, value):
    stream.write(self.tag_data)
    VarintWriter(stream.write, value)

  def Read(self, buff, index):
    return VarintReader(buff, index)

  def Definition(self):
    """Return a string with the definition of this field."""
    return self._FormatDescriptionComment() + self._FormatField("uint64")


class ProtoEnum(ProtoUnsignedInteger):
  """An enum native proto type.

  This is really encoded as an integer but only certain values are allowed.
  """

  def __init__(self, enum_name=None, enum=None, **kwargs):
    super(ProtoEnum, self).__init__(**kwargs)
    if enum_name is None:
      raise type_info.TypeValueError("Enum groups must be given a name.")

    self.enum_name = enum_name
    self.enum = enum or {}
    self.reverse_enum = {}
    for k, v in enum.iteritems():
      if not isinstance(v, (int, long)):
        raise type_info.TypeValueError("Enum values must be integers.")

      if v in self.reverse_enum:
        raise type_info.TypeValueError("Enum values must be unique.")

      self.reverse_enum[v] = k

  def Validate(self, value):
    """Check that value is a valid enum."""
    # None is a valid value - it means the field is not set.
    if value is None:
      return

    int_value = self.enum.get(value)
    if int_value is None:
      raise type_info.TypeValueError(
          "Value %s is not a valid enum value for field %s" % (
              value, self.name))

    return int_value

  def Definition(self):
    """Return a string with the definition of this field."""
    result = self._FormatDescriptionComment()

    result += "  enum %s {\n" % self.enum_name
    for k, v in sorted(self.reverse_enum.items()):
      result += "    %s = %s;\n" % (v, k)

    result += "  }\n"

    result += self._FormatField(self.enum_name)
    return result


class ProtoSignedInteger(ProtoType, type_info.Integer):
  """A signed VarInt encoded in the protobuf.

  Note: signed VarInts are more expensive than unsigned VarInts.
  """

  wire_type = wire_format.WIRETYPE_VARINT

  def Write(self, stream, value):
    stream.write(self.tag_data)
    SignedVarintWriter(stream.write, value)

  def Read(self, buff, index):
    return SignedVarintReader(buff, index)

  def Definition(self):
    """Return a string with the definition of this field."""
    return self._FormatDescriptionComment() + self._FormatField("int64")


class ProtoNested(ProtoType):
  """A nested RDFProtoStruct inside the field."""

  wire_type = wire_format.WIRETYPE_START_GROUP

  def __init__(self, nested=None, **kwargs):
    super(ProtoNested, self).__init__(**kwargs)
    if not issubclass(nested, RDFProtoStruct):
      raise type_info.TypeValueError(
          "Only RDFProtoStructs can be nested, not %s" % nested.__name__)

    self._type = nested
    # Pre-calculate the closing tag data.
    self.closing_tag = ((self.field_number << 3) |
                        wire_format.WIRETYPE_END_GROUP)
    tmp = cStringIO.StringIO()
    VarintWriter(tmp.write, self.closing_tag)
    self.closing_tag_data = tmp.getvalue()

  def GetDefault(self):
    """When a nested proto is accessed, default to an empty one."""
    return self._type()

  def Validate(self, value):
    # Must be exactly the correct type.
    if value.__class__ is not self._type:
      raise ValueError("Field %s must be of type %s" % (
          self.name, self._type.__name__))

    return value

  def Write(self, stream, value):
    stream.write(self.tag_data)
    for (v, desc) in value.GetRawData().itervalues():
      desc.Write(stream, v)

    stream.write(self.closing_tag_data)

  @classmethod
  def Skip(cls, encoded_tag, buff, index):
    """Skip the field at index."""
    tag_type = ord(encoded_tag[0]) & wire_format.TAG_TYPE_MASK

    # We dont need to actually understand the data, we just need to figure out
    # where the end of the unknown field is so we can preserve the data. When we
    # write these fields back (With their encoded tag) they should be still
    # valid.
    if tag_type == wire_format.WIRETYPE_VARINT:
      _, index = decoder.ReadTag(buff, index)

    elif tag_type == wire_format.WIRETYPE_FIXED64:
      index += 8

    elif tag_type == wire_format.WIRETYPE_FIXED32:
      index += 4

    elif tag_type == wire_format.WIRETYPE_LENGTH_DELIMITED:
      length, start = VarintReader(buff, index)
      index = start + length

    # Skip an entire nested protobuf - This calls into Skip() recursively.
    elif tag_type == wire_format.WIRETYPE_START_GROUP:
      start = index
      while 1:
        group_encoded_tag, index = decoder.ReadTag(buff, index)
        if (ord(group_encoded_tag[0]) & wire_format.TAG_TYPE_MASK ==
            wire_format.WIRETYPE_END_GROUP):
          break

        # Recursive call to skip the next field.
        index = cls.Skip(group_encoded_tag, buff, index)

    else:
      raise rdfvalue.DecodeError("Unexpected Tag.")

    # The data to be written includes the encoded_tag and the decoded data
    # together.
    return index

  @classmethod
  def ReadIntoObject(cls, buff, index, value_obj):
    """Reads all tags until the next end group and store in the value_obj."""
    raw_data = value_obj.GetRawData()
    buffer_len = len(buff)

    while index < buffer_len:
      encoded_tag, index = decoder.ReadTag(buff, index)
      type_info_obj = value_obj.type_infos_by_encoded_tag.get(encoded_tag)

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
        start = index
        end = cls.Skip(encoded_tag, buff, start)

        # Record a None type descriptor to signify an unknown field.
        raw_data[(encoded_tag, len(raw_data))] = (encoded_tag + buff[start:end],
                                                  None)

        index = end
        continue

      # This represents the end group tag which is an early exit condition in
      # the case of a nested proto.
      if type_info_obj == "EndGroup":
        break

      value, index = type_info_obj.Read(buff, index)

      if type_info_obj.__class__ is ProtoList:
        value_obj.Get(type_info_obj.name).Append(value)
      else:
        raw_data[type_info_obj.name] = (value, type_info_obj)

    return index

  def Read(self, buff, index):
    """Parse a nested protobuf."""
    # Make new instance and parse the data into it.
    result = self._type()

    index = self.ReadIntoObject(buff, index, result)

    return result, index

  def Definition(self):
    """Return a string with the definition of this field."""
    return self._FormatDescriptionComment() + self._FormatField(
        self._type.__name__)

  def _FormatField(self, proto_type_name, ignore_default=None):
    result = "  optional %s %s = %s" % (proto_type_name,
                                        self.name, self.field_number)
    return result + ";\n"


class RepeatedFieldHelper(object):
  """A helper for the RDFProto to handle repeated fields.

  This helper is intended to only be constructed from the RDFProto class.
  """

  __metaclass__ = registry.MetaclassRegistry

  def __init__(self, wrapped_list=None, type_descriptor=None):
    """Constructor.

    Args:
      wrapped_list: The list within the protobuf which we wrap.
      type_descriptor: A type descriptor describing the type of the list
        elements..

    Raises:
      AttributeError: If parameters are not valid.
    """
    if wrapped_list is None:
      self.wrapped_list = []

    elif isinstance(wrapped_list, RepeatedFieldHelper):
      self.wrapped_list = wrapped_list.wrapped_list

    else:
      self.wrapped_list = wrapped_list

    if type_descriptor is None:
      raise AttributeError("type_descriptor not specified.")

    self.type_descriptor = type_descriptor

  def Copy(self):
    return RepeatedFieldHelper(wrapped_list=self.wrapped_list[:],
                               type_descriptor=self.type_descriptor)

  def Append(self, rdf_value=None, **kwargs):
    """Append the value to our internal list."""
    if rdf_value is None:
      rdf_value = self.type_descriptor.GetType()(**kwargs)

    else:
      # Coerce the value to the required type.
      try:
        rdf_value = self.type_descriptor.Validate(rdf_value, **kwargs)
      except (TypeError, ValueError):
        raise ValueError(
            "Assignment value must be %s, but %s can not "
            "be coerced." % (self.type_descriptor, type(rdf_value)))

    self.wrapped_list.append(rdf_value)

    return rdf_value

  def Remove(self, item):
    return self.wrapped_list.remove(item)

  def Extend(self, iterable):
    for i in iterable:
      self.Append(i)

  append = utils.Proxy("Append")
  remove = utils.Proxy("Remove")

  def __getitem__(self, item):
    return self.wrapped_list[item]

  def __len__(self):
    return len(self.wrapped_list)

  def __eq__(self, other):
    for x, y in zip(self, other):
      if x != y:
        return False

    return True

  def __str__(self):
    return "'%s': %s" % (self.type_descriptor.name,
                         self.wrapped_list)


class ProtoList(ProtoType):
  """A repeated type."""

  def __init__(self, delegate, **kwargs):
    self.delegate = delegate
    if not isinstance(delegate, ProtoType):
      raise AttributeError(
          "Delegate class must derive from ProtoType, not %s" %
          delegate.__class__.__name__)

    self.wire_type = delegate.wire_type

    super(ProtoList, self).__init__(name=delegate.name,
                                    description=delegate.description,
                                    field_number=delegate.field_number)

  def GetDefault(self):
    # By default an empty RepeatedFieldHelper.
    return RepeatedFieldHelper(type_descriptor=self.delegate)

  def Validate(self, value):
    """Check that value is a list of the required type."""
    # Make sure the base class finds the value valid.
    if isinstance(value, list):
      result = RepeatedFieldHelper(type_descriptor=self.delegate)
      result.Extend(value)

    # Assigning from same kind can allow us to skip verification since all
    # elements in a RepeatedFieldHelper already are coerced to the delegate
    # type. In that case we just make a copy.
    elif (isinstance(value, RepeatedFieldHelper) and
          value.type_descriptor.__class__ is self.delegate.__class__):
      result = value.Copy()

    else:
      raise type_info.TypeValueError("Field %s must be a list" % self.name)

    return result

  def Write(self, stream, value):
    for item in value:
      self.delegate.Write(stream, item)

  def Read(self, buff, index):
    return self.delegate.Read(buff, index)


class ProtoRDFValue(ProtoBinary):
  """Serialize arbitrary rdfvalue members.

  Note that these are serialized into a binary field in the protobuf.
  """

  _type = rdfvalue.RDFString

  def __init__(self, rdf_type=None, **kwargs):
    super(ProtoRDFValue, self).__init__(**kwargs)
    if isinstance(rdf_type, basestring):
      self._type = getattr(rdfvalue, rdf_type)
    else:
      self._type = rdf_type

  def Validate(self, value):
    super(ProtoRDFValue, self).Validate(value)
    return self._type(value)

  def Write(self, stream, value):
    stream.write(self.tag_data)

    # Serialize the RDFValue contained in value:
    serialized_value = value.SerializeToString()
    VarintWriter(stream.write, len(serialized_value))
    stream.write(serialized_value)

  def Read(self, buff, index):
    length, index = VarintReader(buff, index)
    result = self._type(buff[index:index+length])
    return result, index+length

  def _FormatField(self, proto_type_name, ignore_default=None):
    result = "  optional %s %s = %s" % (proto_type_name,
                                        self.name, self.field_number)
    return result + ";\n"


class AbstractSerlializer(object):
  """A serializer which parses to/from the intermediate python objects."""

  def SerializeToString(self, value):
    """Serialize the RDFStruct object into a string."""

  def ParseFromString(self, value_obj, string):
    """Parse the string and set attributes in the value_obj."""


class JsonSerlializer(AbstractSerlializer):
  """A serializer based on Json."""

  def _SerializedToIntermediateForm(self, data):
    """Convert to an intermediate form suitable for JSON encoding.

    Since JSON is unable to encode arbitrary data, we need to convert the data
    into something which is valid JSON.

    Args:
      data: An arbitrary data from the RDFStruct's internal form.

    Returns:
      This function returns a valid JSON serializable object, which can, in turn
    be reversed using the _ParseFromIntermediateForm() method.

    Raises:
      ValueError: If data can not be suitably encoded.
    """
    # These types can be serialized by json.
    if isinstance(data, (int, long, unicode)):
      return data

    # We encode an RDFStruct as a dict.
    elif isinstance(data, rdfvalue.RDFStruct):
      result = dict(__n=data.__class__.__name__)
      for (v, desc) in data.GetRawData().itervalues():
        result[desc.field_number] = self._SerializedToIntermediateForm(v)

      return result

    # A RepeatedFieldHelper is serialized as a list of objects.
    elif isinstance(data, RepeatedFieldHelper):
      return [self._SerializedToIntermediateForm(x) for x in data]

    # A byte string must be encoded for json since it can not encode arbitrary
    # binary data.
    elif isinstance(data, str):
      return data.encode("base64")

    # Should never get here.
    raise ValueError("Unable to serialize internal type %s" % data)

  def SerializeToString(self, data):
    """Convert the internal data structure to json compatible form."""
    return json.dumps(self._SerializedToIntermediateForm(data))

  def _ParseFromIntermediateForm(self, data):
    result = {}

    for k, v in data.iteritems():
      if isinstance(v, (int, long, unicode)):
        result[k] = v
      elif isinstance(v, dict):
        rdfvalue_class = self.classes.get(v["t"])
        # Just ignore RDFValues we dont understand.
        if rdfvalue_class is not None:
          tmp = result[k] = rdfvalue_class()
          tmp.SetRawData(self._ParseFromIntermediateForm(v["d"]))

      elif isinstance(v, str):
        result[k] = v.decode("base64")

    return result

  def ParseFromString(self, value_obj, string):
    value_obj.SetRawData(self._ParseFromIntermediateForm(json.loads(string)))


class RDFStructMetaclass(registry.MetaclassRegistry):

  def __init__(cls, name, bases, env_dict):
    super(RDFStructMetaclass, cls).__init__(name, bases, env_dict)

    cls._fields = set()
    cls.type_infos_by_field_number = {}
    cls.type_infos_by_encoded_tag = {}

    # Pre-populate the class using the type_infos class member.
    if cls.type_infos is not None:
      for field_desc in cls.type_infos:
        cls.AddDescriptor(field_desc)

    # Pre-populate the class using the proto definition.
    if cls.definition is not None:
      structs_parser.ParseFromProto(cls.definition, parse_class=cls)

    cls._class_attributes = set(dir(cls))


class RDFStruct(rdfvalue.RDFValue):
  """An RDFValue object which contains fields like a struct."""

  __metaclass__ = RDFStructMetaclass

  # This can be populated with a type_info.TypeDescriptorSet() object to
  # initialize the class.
  type_infos = None

  # This class can be defined using the protobuf definition language (e.g. a
  # .proto file). If defined here, we parse the .proto file for the message with
  # the exact same class name and add the field descriptions from it.
  definition = None

  _fields = None
  _data = None

  # This is the serializer which will be used by this class. It can be
  # interchanged or overriden as required.
  _serializer = JsonSerlializer()

  def __init__(self, initializer=None, **kwargs):
    self._data = {}

    for arg, value in kwargs.iteritems():
      self.Set(arg, value)

    if initializer is None:
      return

    elif initializer.__class__ == self.__class__:
      self.ParseFromString(initializer.SerializeToString())

    elif isinstance(initializer, basestring):
      self.ParseFromString(initializer)

    else:
      raise ValueError("%s can not be initialized from %s" % (
          self.__class__.__name__, type(initializer)))

  def GetRawData(self):
    """Retrieves the raw python representation of the object.

    This is normally only used by serializers which are tightly coupled with the
    raw data representation. External users should not make use of the internal
    raw data structures.

    Returns:
      the raw python object representation (a dict).
    """
    return self._data

  def SetRawData(self, data):
    self._data = data

  def SerializeToString(self):
    return self._serializer.SerializeToString(self)

  def ParseFromString(self, string):
    self._serializer.ParseFromString(self, string)

  def __eq__(self, other):
    return (isinstance(other, self.__class__) and
            self._data == other.GetRawData())

  def __ne__(self, other):
    return not self == other

  def __str__(self):
    return unicode(self._data)

  def __dir__(self):
    """Add the virtualized fields to the console's tab completion."""
    return (dir(super(RDFStruct, self)) +
            [x.name for x in self.type_infos])

  def Set(self, attr, value):
    """Sets the attribute in to the value."""
    type_info_obj = self.type_infos.get(attr)

    # Access to our own object attributes:
    if type_info_obj is None:
      raise AttributeError("Type %s is not known." % attr)

    value = type_info_obj.Validate(value)
    value = type_info_obj.ConvertToWireFormat(value)
    self._data[attr] = (value, type_info_obj)

    return value

  def Get(self, attr):
    """Retrieve the attribute specified."""
    entry = self._data.get(attr)
    if entry is None:
      type_info_obj = self.type_infos.get(attr)

      if type_info_obj is None:
        raise AttributeError("'%s' object has no attribute '%s'" % (
            self.__class__.__name__, attr))

      # Assign the default value now.
      default = type_info_obj.GetDefault()
      if default is None:
        return

      return self.Set(attr, default)

    value, type_info_obj = entry
    if type_info_obj.__class__ is ProtoString:
      value = value.decode("utf8")

    return value

  @classmethod
  def AddDescriptor(cls, field_desc):
    if not isinstance(field_desc, ProtoType):
      raise type_info.TypeValueError(
          "%s field '%s' should be of type ProtoType" % (
              cls.__name__, field_desc.name))

    cls._fields.add(field_desc.name)
    cls.type_infos_by_field_number[field_desc.field_number] = field_desc
    cls.type_infos.Append(field_desc)


class ProtocolBufferSerializer(AbstractSerlializer):
  """A serializer based on protocol buffers."""

  def SerializeToString(self, data):
    """Serialize the RDFProtoStruct object into a string."""
    stream = cStringIO.StringIO()
    for (v, desc) in data.GetRawData().itervalues():
      # If a desc is not known this is an unknown field, we just dump the data
      # verbatim into the stream.
      if desc is None:
        stream.write(v)

      else:
        desc.Write(stream, v)

    return stream.getvalue()

  def ParseFromString(self, value_obj, string):
    ProtoNested.ReadIntoObject(string, 0, value_obj)


class RDFProtoStruct(RDFStruct):
  """An RDFStruct which uses protobufs for serialization.

  This implementation is faster than the standard protobuf library.
  """
  _serializer = ProtocolBufferSerializer()

  shortest_encoded_tag = 0
  longest_encoded_tag = 0

  @classmethod
  def EmitProto(cls):
    """Emits .proto file definitions."""
    result = "message %s {\n" % cls.__name__
    for _, desc in sorted(cls.type_infos_by_field_number.items()):
      result += desc.Definition()

    result += "}\n"
    return result

  def __str__(self):
    return ""

  @classmethod
  def AddDescriptor(cls, field_desc):
    """Register this descriptor with the Proto Struct."""
    if not isinstance(field_desc, ProtoType):
      raise type_info.TypeValueError(
          "%s field '%s' should be of type ProtoType" % (
              cls.__name__, field_desc.name))

    cls._fields.add(field_desc.name)

    # Ensure this field number is unique:
    if field_desc.field_number in cls.type_infos_by_field_number:
      raise type_info.TypeValueError(
          "Field number %s for field %s is not unique in %s" % (
              field_desc.field_number, field_desc.name, cls.__name__))

    # We store an index of the type info by tag values to speed up parsing.
    tag = (field_desc.field_number << 3) | field_desc.wire_type
    cls.type_infos_by_field_number[field_desc.field_number] = field_desc
    cls.type_infos_by_encoded_tag[field_desc.tag_data] = field_desc

    # Add the corresponding end group tag for nested fields.
    if field_desc.wire_type == wire_format.WIRETYPE_START_GROUP:
      tag = (field_desc.field_number << 3) | wire_format.WIRETYPE_END_GROUP
      tmp = cStringIO.StringIO()
      VarintWriter(tmp.write, tag)
      closing_tag_data = tmp.getvalue()
      cls.type_infos_by_encoded_tag[closing_tag_data] = "EndGroup"

    if cls.type_infos is None:
      cls.type_infos = type_info.TypeDescriptorSet()

    cls.type_infos.Append(field_desc)

    # This is much faster than __setattr__/__getattr__
    setattr(cls, field_desc.name, property(
        lambda self: self.Get(field_desc.name),
        lambda self, x: self.Set(field_desc.name, x),
        None, field_desc.description))
