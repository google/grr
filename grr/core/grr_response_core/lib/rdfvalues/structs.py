#!/usr/bin/env python
"""Semantic Protobufs are serialization agnostic, rich data types."""

import base64
from collections import abc
from collections.abc import ByteString, Iterator, Sequence
import copy
import functools
import logging
from typing import Any, Optional, TypeVar

from google.protobuf import message as proto2_message
from google.protobuf import text_format

from google.protobuf import any_pb2
from google.protobuf import wrappers_pb2
from grr_response_core.lib import rdfvalue
from grr_response_core.lib import registry
from grr_response_core.lib import serialization
from grr_response_core.lib import type_info
from grr_response_core.lib import utils
from grr_response_core.lib.rdfvalues import proto2 as rdf_proto2
from grr_response_core.lib.util import precondition
from grr_response_proto import semantic_pb2


class ProtoType(type_info.TypeInfoObject):
  """A specific type descriptor for protobuf fields.

  This is an abstract class - do not instantiate directly.
  """

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

  # Whether the Python representation of this field should be cached on the
  # owning RDFStruct instance.
  should_cache = False

  def __init__(
      self,
      field_number=None,
      required=False,
      labels=None,
      set_default_on_access=None,
      has_presence=True,
      **kwargs,
  ):
    super().__init__(**kwargs)
    # TODO - Without this type hint, pytype thinks that field_number
    # is always None.
    self.field_number: int = field_number  # pyrefly: ignore[bad-assignment]
    self.required = required
    self.has_presence = has_presence
    if set_default_on_access is not None:
      self.set_default_on_access = set_default_on_access

    self.labels = labels or []
    if self.field_number is None:
      raise type_info.TypeValueError("No valid field number specified.")

  def Copy(self, field_number=None):
    """Returns a copy of descriptor, optionally changing the field number."""
    result = copy.copy(self)
    if field_number is not None:
      result.field_number = field_number

    return result

  def HasFieldInProto(self, proto: Any) -> bool:
    if self.has_presence:
      return proto.HasField(self.name)
    return bool(getattr(proto, self.name))

  def GetFromProto(self, proto: Any, container: Any = None) -> Any:
    del container  # Unused.
    return getattr(proto, self.name)

  def SetInProto(self, proto: Any, value: Any) -> None:
    setattr(proto, self.name, value)

  def FlushInProto(self, proto: Any, value: Any) -> None:
    del proto, value  # Unused.

  def ConvertFromEncodedValue(
      self, raw_value: Any, container: Any = None
  ) -> Any:
    del container  # Unused.
    return raw_value

  def ConvertToEncodedValue(self, value: Any) -> Any:
    return value

  def CreateDefaultInProto(self, proto: Any, container: Any = None) -> Any:
    """Creates and attaches the default value directly in proto if supported."""
    del proto, container  # Unused.
    return None

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
    # TODO - This fails for ProtoList.
    return "<Field %s (%s) of %s: field_number: %s>" % (
        self.name,
        self.__class__.__name__,
        self.owner.__name__,  # pyrefly: ignore[missing-attribute]
        self.field_number,
    )

  def SetOwner(self, owner):
    self.owner = owner


class ProtoString(ProtoType):
  """A string encoded in a protobuf."""

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

  def Validate(self, value, **_) -> str:  # pyrefly: ignore[bad-override]
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

  def Validate(self, value, **_):  # pyrefly: ignore[bad-override]
    if not isinstance(value, bytes):
      raise type_info.TypeValueError("Required bytes, got %r" % value)

    return value

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
  """An unsigned integer encoded in the protobuf."""

  # This descriptor describes integers.
  type = rdfvalue.RDFInteger
  proto_type_name = "uint64"

  def __init__(self, default=0, **kwargs):
    # Integers default to 0 if not specified.
    super().__init__(default=default, **kwargs)

  def Validate(self, value, **_):  # pyrefly: ignore[bad-override]
    try:
      return int(value)
    except ValueError:
      raise type_info.TypeValueError("Invalid value %s for Integer" % value)

  def SetInProto(self, proto: Any, value: Any) -> None:
    # Legacy accelerated.c (PyArg_ParseTuple "K") wrapped negative Python ints
    # modulo 2^64 into two's-complement uint64 varints. Preserve this behavior
    # for callers that store pre-1970 values (e.g. NTFS 1601 timestamps) in
    # uint64 fields until those fields are migrated to int64.
    if value < 0:
      value &= 0xFFFFFFFFFFFFFFFF
    setattr(proto, self.name, value)

  def ConvertToEncodedValue(self, value: Any) -> Any:
    # Wrap negative ints mod 2^64 to match legacy accelerated.c uint64 encoding.
    if value < 0:
      value &= 0xFFFFFFFFFFFFFFFF
    return value

  def _FormatDefault(self):
    if self.GetDefault():
      return " [default = %r]" % self.GetDefault()
    else:
      return ""


class ProtoSignedInteger(ProtoUnsignedInteger):
  """A signed integer encoded in the protobuf."""

  proto_type_name = "int64"

  def SetInProto(self, proto: Any, value: Any) -> None:
    setattr(proto, self.name, value)

  def ConvertToEncodedValue(self, value: Any) -> Any:
    return value


class ProtoFixed32(ProtoUnsignedInteger):
  """A 32 bit fixed unsigned integer."""

  proto_type_name = "sfixed32"

  def SetInProto(self, proto: Any, value: Any) -> None:
    setattr(proto, self.name, value)

  def ConvertToEncodedValue(self, value: Any) -> Any:
    return value


class ProtoFixed64(ProtoFixed32):
  proto_type_name = "sfixed64"


class ProtoFixedU32(ProtoFixed32):
  """A 32 bit fixed unsigned integer."""

  proto_type_name = "fixed32"


class ProtoFloat(ProtoFixed32):
  """A float."""

  proto_type_name = "float"
  should_cache = True

  def Validate(self, value, **_):
    if not rdfvalue.RDFInteger.IsNumeric(value):
      raise type_info.TypeValueError("Invalid value %s for Float" % value)

    return value

  def SetInProto(self, proto: Any, value: Any) -> None:
    setattr(proto, self.name, float(value))

  def ConvertToEncodedValue(self, value: Any) -> Any:
    return float(value)


class ProtoDouble(ProtoFixed64):
  """A double."""

  proto_type_name = "double"

  def Validate(self, value, **_):
    if not rdfvalue.RDFInteger.IsNumeric(value):
      raise type_info.TypeValueError("Invalid value %s for Integer" % value)

    return value

  def SetInProto(self, proto: Any, value: Any) -> None:
    setattr(proto, self.name, float(value))

  def ConvertToEncodedValue(self, value: Any) -> Any:
    return float(value)


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

    for v in enum.values():  # pyrefly: ignore[missing-attribute]
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

  def GetFromProto(self, proto: Any, container: Any = None) -> Any:
    del container  # Unused.
    val = getattr(proto, self.name)
    return EnumNamedValue(val, name=self.reverse_enum.get(val))

  def SetInProto(self, proto: Any, value: Any) -> None:
    setattr(proto, self.name, int(value))

  def ConvertFromEncodedValue(
      self, raw_value: Any, container: Any = None
  ) -> Any:
    del container  # Unused.
    return EnumNamedValue(raw_value, name=self.reverse_enum.get(raw_value))

  def ConvertToEncodedValue(self, value: Any) -> Any:
    return int(value)


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

  def GetFromProto(self, proto: Any, container: Any = None) -> Any:
    del container  # Unused.
    return bool(getattr(proto, self.name))

  def SetInProto(self, proto: Any, value: Any) -> None:
    setattr(proto, self.name, bool(value))

  def ConvertFromEncodedValue(
      self, raw_value: Any, container: Any = None
  ) -> Any:
    del container  # Unused.
    return bool(raw_value)

  def ConvertToEncodedValue(self, value: Any) -> Any:
    return bool(value)


class ProtoEmbedded(ProtoType):
  """A nested protobuf message field."""

  # When we access a nested protobuf we automatically create it and assign it to
  # the owner protobuf.
  set_default_on_access = True
  should_cache = True

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

    # Or it can be a subclass of RDFProtoStruct.
    elif issubclass(nested, RDFProtoStruct):  # pyrefly: ignore[bad-argument-type]
      self.type = nested
      self.proto_type_name = nested.__name__

    else:
      raise type_info.TypeValueError(
          "Only RDFProtoStructs can be nested, not %s" % nested.__name__
      )

  def GetFromProto(self, proto: Any, container: Any = None) -> Any:
    del container  # Unused.
    return self.type._FromProto(getattr(proto, self.name))  # pylint: disable=protected-access  # pyrefly: ignore[missing-attribute]

  def SetInProto(self, proto: Any, value: Any) -> None:
    value._Flush()  # pylint: disable=protected-access
    sub_proto = getattr(proto, self.name)
    if value._proto is not sub_proto:  # pylint: disable=protected-access
      sub_proto.CopyFrom(value._proto)  # pylint: disable=protected-access

  def FlushInProto(self, proto: Any, value: Any) -> None:
    value._Flush()  # pylint: disable=protected-access
    sub_proto = getattr(proto, self.name)
    if value._proto is not sub_proto:  # pylint: disable=protected-access
      sub_proto.CopyFrom(value._proto)  # pylint: disable=protected-access

  def CreateDefaultInProto(self, proto: Any, container: Any = None) -> Any:
    del container  # Unused.
    sub_proto = getattr(proto, self.name)
    sub_proto.SetInParent()
    return self.type._FromProto(sub_proto)  # pylint: disable=protected-access  # pyrefly: ignore[missing-attribute]

  def ConvertFromEncodedValue(
      self, raw_value: Any, container: Any = None
  ) -> Any:
    del container  # Unused.
    return self.type._FromProto(raw_value)  # pylint: disable=protected-access  # pyrefly: ignore[missing-attribute]

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
    if not issubclass(target, RDFProtoStruct):  # pyrefly: ignore[bad-argument-type]
      raise TypeError(
          "Field %s expects a protobuf, but target is %s" % (self, target)
      )

    self.late_bound = False

    # The target type is now resolved.
    self.type = target

    # Register us in our owner.
    self.owner.AddDescriptor(self)  # pyrefly: ignore[missing-attribute]

  def GetDefault(self, container=None):
    """When a nested proto is accessed, default to an empty one."""
    return self.type()  # pyrefly: ignore[not-callable]

  def Validate(self, value, **_):  # pyrefly: ignore[bad-override]
    if isinstance(value, str):
      raise type_info.TypeValueError(
          "Field %s must be of type %s" % (self.name, self.type.__name__)  # pyrefly: ignore[missing-attribute]
      )

    # We may coerce it to the correct type.
    if value.__class__ is not self.type:
      try:
        value = self.type(value)  # pyrefly: ignore[not-callable]
      except rdfvalue.InitializeError as e:
        raise type_info.TypeValueError(
            "Field %s must be of type %s" % (self.name, self.type.__name__)  # pyrefly: ignore[missing-attribute]
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

  set_default_on_access = True
  should_cache = True

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

  def GetFromProto(self, proto: Any, container: Any = None) -> Any:
    return serialization.FromBytes(
        self._type(container), getattr(proto, self.name)  # pyrefly: ignore[not-callable]
    )

  def SetInProto(self, proto: Any, value: Any) -> None:
    setattr(proto, self.name, serialization.ToBytes(value))

  def FlushInProto(self, proto: Any, value: Any) -> None:
    setattr(proto, self.name, serialization.ToBytes(value))

  def ConvertFromEncodedValue(
      self, raw_value: Any, container: Any = None
  ) -> Any:
    return serialization.FromBytes(self._type(container), raw_value)  # pyrefly: ignore[not-callable]

  def ConvertToEncodedValue(self, value: Any) -> Any:
    return serialization.ToBytes(value)

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

    cls = self._type(container or self.owner())  # pyrefly: ignore[not-callable]
    if cls is not None:
      return cls()

  def Format(self, value):
    yield "  %r" % value

  def _FormatDefault(self):
    return ""


class ProtoDynamicAnyValueEmbedded(ProtoDynamicEmbedded):
  """An embedded dynamic field which is stored as AnyValue struct."""

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

  def _DecodeAnyProto(self, any_proto, container=None):
    if self._type is not None:
      converted_value = self._type(container)
    else:
      converted_value = self._TypeFromAnyValue(any_proto)

    # If one of the protobuf library wrapper classes is used, unwrap the value.
    if any_proto.type_url.startswith("type.googleapis.com/google.protobuf."):
      wrapper_cls = self.__class__.WRAPPER_BY_TYPE[
          converted_value.protobuf_type
      ]
      wrapper_value = wrapper_cls()
      wrapper_value.ParseFromString(any_proto.value)
      return converted_value.FromWireFormat(wrapper_value.value)
    else:
      # TODO(user): Type stored in type_url is currently ignored when value
      # is decoded. We should use it to deserialize the value and then check
      # that value type and dynamic type are compatible.
      return converted_value.FromSerializedBytes(any_proto.value)

  def _EncodeToAnyProto(self, any_proto, value):
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

    any_proto.type_url = type_name
    any_proto.value = data

  def GetFromProto(self, proto: Any, container: Any = None) -> Any:
    return self._DecodeAnyProto(getattr(proto, self.name), container=container)

  def SetInProto(self, proto: Any, value: Any) -> None:
    self._EncodeToAnyProto(getattr(proto, self.name), value)

  def FlushInProto(self, proto: Any, value: Any) -> None:
    self._EncodeToAnyProto(getattr(proto, self.name), value)

  def ConvertFromEncodedValue(
      self, raw_value: Any, container: Any = None
  ) -> Any:
    return self._DecodeAnyProto(raw_value, container=container)

  def _TypeFromAnyValue(self, anyvalue):
    type_str = anyvalue.type_url.split("/")[-1].split(".")[-1]

    if type_str in self.TYPE_BY_WRAPPER:
      return self.TYPE_BY_WRAPPER[type_str]

    try:
      return rdfvalue.RDFValue.classes[type_str]
    except KeyError:
      raise TypeError("Can't find RDFValue class for type: %s" % type_str)


class ProtoAnyValue(ProtoType):
  """A raw Protocol Buffers `Any` type without dynamic typing magic."""

  proto_type_name = "google.protobuf.Any"
  set_default_on_access = True
  should_cache = True

  def GetDefault(self, container=None):
    del container  # Unused.
    return AnyValue()

  def Validate(self, value, container=None):
    del container  # Unused.
    precondition.AssertType(value, AnyValue)

    return value

  def GetFromProto(self, proto: Any, container: Any = None) -> Any:
    del container  # Unused.
    return AnyValue._FromProto(getattr(proto, self.name))  # pylint: disable=protected-access

  def SetInProto(self, proto: Any, value: Any) -> None:
    value._Flush()  # pylint: disable=protected-access
    sub_proto = getattr(proto, self.name)
    if value._proto is not sub_proto:  # pylint: disable=protected-access
      sub_proto.CopyFrom(value._proto)  # pylint: disable=protected-access

  def FlushInProto(self, proto: Any, value: Any) -> None:
    value._Flush()  # pylint: disable=protected-access
    sub_proto = getattr(proto, self.name)
    if value._proto is not sub_proto:  # pylint: disable=protected-access
      sub_proto.CopyFrom(value._proto)  # pylint: disable=protected-access

  def CreateDefaultInProto(self, proto: Any, container: Any = None) -> Any:
    del container  # Unused.
    sub_proto = getattr(proto, self.name)
    sub_proto.SetInParent()
    return AnyValue._FromProto(sub_proto)  # pylint: disable=protected-access

  def ConvertFromEncodedValue(
      self, raw_value: Any, container: Any = None
  ) -> Any:
    del container  # Unused.
    return AnyValue._FromProto(raw_value)  # pylint: disable=protected-access


class RepeatedFieldHelper(abc.Sequence):
  """A helper for the RDFProto to handle repeated fields.

  This helper is intended to only be constructed from the RDFProto class.
  """

  def __init__(
      self,
      wrapped_list=None,
      type_descriptor=None,
      container=None,
      proto_field=None,
  ):
    """Constructor.

    Args:
      wrapped_list: Optional standalone list of Python values (used for slices
        or detached copies).
      type_descriptor: A type descriptor describing the type of the list
        elements.
      container: The protobuf which contains this repeated field.
      proto_field: The underlying protobuf repeated field container.

    Raises:
      AttributeError: If parameters are not valid.
    """
    if type_descriptor is None:
      raise AttributeError("type_descriptor not specified.")

    self.type_descriptor = type_descriptor
    self.container = container
    self._proto_field = proto_field
    self._cache = {}
    self._is_embedded = isinstance(
        type_descriptor, (ProtoEmbedded, ProtoAnyValue)
    )
    self._is_dynamic_any = isinstance(
        type_descriptor, ProtoDynamicAnyValueEmbedded
    )
    self.dirty = False

    if proto_field is not None:
      self._items = None
    elif wrapped_list is None:
      self._items = []
    elif wrapped_list.__class__ is RepeatedFieldHelper:
      self._items = list(wrapped_list)
    else:
      self._items = list(wrapped_list)

  def _Flush(self):
    """Flushes any cached/mutated elements back to the underlying proto."""
    if self._proto_field is None or not self._cache:
      return
    td = self.type_descriptor
    if self._is_embedded:
      for idx, item in self._cache.items():
        item._Flush()  # pylint: disable=protected-access
        sub_proto = self._proto_field[idx]
        if item._proto is not sub_proto:  # pylint: disable=protected-access
          sub_proto.CopyFrom(item._proto)  # pylint: disable=protected-access
    elif self._is_dynamic_any:
      for idx, item in self._cache.items():
        td._EncodeToAnyProto(self._proto_field[idx], item)  # pylint: disable=protected-access
    elif isinstance(td, ProtoDynamicEmbedded):
      for idx, item in self._cache.items():
        self._proto_field[idx] = td.ConvertToEncodedValue(item)
    elif isinstance(td, ProtoRDFValue):
      for idx, item in self._cache.items():
        if item.dirty:
          self._proto_field[idx] = td.ConvertToEncodedValue(item)

  def _AttachToProtoField(self, proto_field):
    """Copies standalone items into proto_field and binds to it."""
    items = list(self) if self._items is None else self._items
    del proto_field[:]
    self._proto_field = proto_field
    self._items = None
    self._cache = {}
    td = self.type_descriptor
    if self._is_embedded:
      for item in items:
        item._Flush()  # pylint: disable=protected-access
        sub_proto = proto_field.add()
        sub_proto.CopyFrom(item._proto)  # pylint: disable=protected-access
    elif self._is_dynamic_any:
      for idx, item in enumerate(items):
        sub_proto = proto_field.add()
        td._EncodeToAnyProto(sub_proto, item)  # pylint: disable=protected-access
        self._cache[idx] = item
    else:
      for idx, item in enumerate(items):
        proto_field.append(td.ConvertToEncodedValue(item))
        if td.should_cache:
          self._cache[idx] = item

  def _Detach(self) -> None:
    """Detaches this helper and its cached items from self._proto_field."""
    if self._proto_field is None:
      return
    self._Flush()
    items = []
    for i in range(len(self._proto_field)):
      val = self[i]
      if self._is_embedded and val._proto is self._proto_field[i]:  # pylint: disable=protected-access
        val._DetachSubtree()  # pylint: disable=protected-access
      items.append(val)
    self._items = items
    self._proto_field = None
    self._cache.clear()

  def Copy(self):
    return RepeatedFieldHelper(
        wrapped_list=list(self),
        type_descriptor=self.type_descriptor,
        container=self.container,
    )

  def Append(self, rdf_value: Any = utils.NotAValue, **kwargs: Any) -> Any:
    """Append the value to our internal list."""
    td = self.type_descriptor
    created_fresh = rdf_value is utils.NotAValue
    if created_fresh:
      if self._proto_field is not None and self._is_embedded:
        cls = AnyValue if isinstance(td, ProtoAnyValue) else td.type
        if not cls._has_custom_init_or_set_raw_data:  # pylint: disable=protected-access
          sub_proto = self._proto_field.add()
          try:
            rdf_value = cls._FromProto(sub_proto)  # pylint: disable=protected-access
            for arg, val in kwargs.items():
              if not hasattr(cls, arg):
                if arg in cls.late_bound_type_infos:  # pyrefly: ignore[missing-attribute]
                  raise AttributeError(
                      "Field %s refers to an as yet undefined Semantic Type."
                      % cls.late_bound_type_infos[arg]  # pyrefly: ignore[missing-attribute]
                  )
                raise AttributeError(
                    "Proto %s has no field %s" % (cls.__name__, arg)
                )
              setattr(rdf_value, arg, val)
          except Exception:
            del self._proto_field[-1]
            raise
          self._cache[len(self._proto_field) - 1] = rdf_value
          self.dirty = True
          return rdf_value
      rdf_value = td.type(**kwargs)
      self.dirty = True
    else:
      # Coerce the value to the required type.
      try:
        rdf_value = td.Validate(rdf_value, **kwargs)
      except (TypeError, ValueError) as e:
        raise type_info.TypeValueError(
            "Assignment value must be %s, but %s can not be coerced. Error: %s"
            % (td.proto_type_name, type(rdf_value), e)
        )

    if self._proto_field is not None:
      idx = len(self._proto_field)
      if self._is_embedded:
        rdf_value._Flush()  # pylint: disable=protected-access
        sub_proto = self._proto_field.add()
        sub_proto.CopyFrom(rdf_value._proto)  # pylint: disable=protected-access
        if created_fresh:
          # Freshly created by Append(**kwargs) (e.g. custom __init__ subclass):
          # cache it so mutations on the returned object flush to sub_proto.
          self._cache[idx] = rdf_value
      elif self._is_dynamic_any:
        sub_proto = self._proto_field.add()
        td._EncodeToAnyProto(sub_proto, rdf_value)  # pylint: disable=protected-access
        self._cache[idx] = rdf_value
      else:
        self._proto_field.append(td.ConvertToEncodedValue(rdf_value))
        if td.should_cache:
          self._cache[idx] = rdf_value
    else:
      self._items.append(rdf_value)  # pyrefly: ignore[missing-attribute]

    self.dirty = True
    return rdf_value

  def Pop(self, item: int) -> Any:
    """Removes and returns the item at the given index."""
    length = len(self)
    idx = length + item if item < 0 else item
    result = self[idx]
    if self._proto_field is not None:
      if self._is_embedded and result._proto is self._proto_field[idx]:  # pylint: disable=protected-access
        result = result.Copy()
      del self._proto_field[idx]
      new_cache = {}
      for k, v in self._cache.items():
        if k < idx:
          new_cache[k] = v
        elif k > idx:
          new_cache[k - 1] = v
      self._cache = new_cache
    else:
      self._items.pop(idx)  # pyrefly: ignore[missing-attribute]
    self.dirty = True
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
      result = [self[i] for i in range(*item.indices(len(self)))]
      return self.__class__(
          wrapped_list=result,
          type_descriptor=self.type_descriptor,
          container=self.container,
      )

    if self._proto_field is None:
      assert self._items is not None
      return self._items[item]

    length = len(self._proto_field)
    idx = length + item if item < 0 else item
    if idx < 0 or idx >= length:
      raise IndexError("list index out of range")

    cached = self._cache.get(idx)
    if cached is not None:
      return cached

    val = self.type_descriptor.ConvertFromEncodedValue(
        self._proto_field[idx], container=self.container
    )
    if self.type_descriptor.should_cache:
      self._cache[idx] = val
    return val

  def __len__(self):
    if self._proto_field is not None:
      return len(self._proto_field)
    return len(self._items)  # pyrefly: ignore[bad-argument-type]

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
    return "<{} {!r}>".format(type(self).__name__, list(self))

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
  # TODO(user)
  set_default_on_access = True
  should_cache = True

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

    super().__init__(
        name=delegate.name,
        description=delegate.description,
        field_number=delegate.field_number,
        friendly_name=delegate.friendly_name,
        labels=labels,
    )

  def HasFieldInProto(self, proto: Any) -> bool:
    return bool(getattr(proto, self.name))

  def GetFromProto(self, proto: Any, container: Any = None) -> Any:
    return RepeatedFieldHelper(
        proto_field=getattr(proto, self.name),
        type_descriptor=self.delegate,
        container=container,
    )

  def CreateDefaultInProto(self, proto: Any, container: Any = None) -> Any:
    return RepeatedFieldHelper(
        proto_field=getattr(proto, self.name),
        type_descriptor=self.delegate,
        container=container,
    )

  def SetInProto(self, proto: Any, value: Any) -> None:
    value._AttachToProtoField(getattr(proto, self.name))  # pylint: disable=protected-access

  def FlushInProto(self, proto: Any, value: Any) -> None:
    del proto  # Unused.
    value._Flush()  # pylint: disable=protected-access

  def GetDefault(self, container=None):
    # By default an empty RepeatedFieldHelper.
    return RepeatedFieldHelper(
        type_descriptor=self.delegate, container=container
    )

  def Validate(self, value: Any, container: Any = None, **_: Any) -> RepeatedFieldHelper:  # pyrefly: ignore[bad-override]
    """Check that value is a list of the required type."""
    if (
        value.__class__ is RepeatedFieldHelper
        and value.type_descriptor is self.delegate
    ):
      result = value.Copy()
      result.container = container
    else:
      # The value may be a generator here, so we just iterate over it.
      result = RepeatedFieldHelper(
          type_descriptor=self.delegate, container=container
      )
      result.Extend(value)

    return result

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
    self.owner.AddDescriptor(self)  # pyrefly: ignore[missing-attribute]


class ProtoRDFValue(ProtoType):
  """Serialize arbitrary rdfvalue members.

  NOTE: The default value for an RDFValue is None. It is impossible for us to
  know how to instantiate a valid default value without being told by the
  user. This is unlike the default value for strings or ints which are "" and 0
  respectively.
  """

  # We delegate metadata to a primitive field descriptor based on the
  # semantic type's protobuf_type attribute.
  primitive_desc = None

  # We store our args here so we can use the same args to initialize the
  # delegate descriptor.
  _kwargs = None

  type = None
  should_cache = True
  _unsigned_mask: Optional[int] = None

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

    # Or it can be a subclass of RDFValue.
    elif issubclass(rdf_type, rdfvalue.RDFValue):  # pyrefly: ignore[bad-argument-type]
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
    self.owner.AddDescriptor(self)  # pyrefly: ignore[missing-attribute]

  def _GetPrimitiveEncoder(self):
    """Finds the primitive encoder according to the type's protobuf_type."""
    if self.type is None:
      raise TypeError("Expected type `type`, got `None`.")
    pb_type = serialization.GetProtobufType(self.type)
    primitive_cls = self._PROTO_DATA_STORE_LOOKUP[pb_type]
    self.primitive_desc = primitive_cls(**self._kwargs)  # pyrefly: ignore[bad-unpacking]
    self.proto_type_name = self.primitive_desc.proto_type_name
    if pb_type == "unsigned_integer":
      self._unsigned_mask = 0xFFFFFFFFFFFFFFFF
    elif pb_type == "unsigned_integer_32":
      self._unsigned_mask = 0xFFFFFFFF
    else:
      self._unsigned_mask = None

  def GetDefault(self, container=None):
    _ = container
    if self.default is None:
      return None

    if self.default.__class__ is not self.type:
      self.default = self.Validate(self.default)
    return self.default

  def Definition(self):
    return (
        "\n  // Semantic Type: %s" % self.type.__name__  # pyrefly: ignore[missing-attribute]
    ) + self.primitive_desc.Definition()  # pyrefly: ignore[missing-attribute]

  def Validate(self, value, **_):  # pyrefly: ignore[bad-override]
    # Try to coerce into the correct type:
    if value.__class__ is not self.type:
      try:
        value = self.type(value)  # pyrefly: ignore[not-callable]
      except (rdfvalue.DecodeError, TypeError) as e:
        raise type_info.TypeValueError(e)

    return value

  def GetFromProto(self, proto: Any, container: Any = None) -> Any:
    del container  # Unused.
    return self.type(getattr(proto, self.name))  # pyrefly: ignore[not-callable]

  def SetInProto(self, proto: Any, value: Any) -> None:
    setattr(proto, self.name, self.ConvertToEncodedValue(value))

  def FlushInProto(self, proto: Any, value: Any) -> None:
    if value.dirty:
      setattr(proto, self.name, self.ConvertToEncodedValue(value))

  def ConvertFromEncodedValue(
      self, raw_value: Any, container: Any = None
  ) -> Any:
    del container  # Unused.
    return self.type(raw_value)  # pyrefly: ignore[not-callable]

  def ConvertToEncodedValue(self, value: Any) -> Any:
    raw = value.SerializeToWireFormat()
    # Legacy accelerated.c wrapped negative Python ints modulo 2^64 / 2^32 for
    # unsigned fields (e.g. NTFS 1601 timestamps in uint64 RDFDatetimeSeconds
    # fields such as StatEntry.st_atime). Keep wrapping here so google.protobuf
    # does not reject negative values until those fields migrate to int64.
    if self._unsigned_mask is not None and raw < 0:
      raw &= self._unsigned_mask
    return raw

  def Copy(self, field_number=None):
    """Returns descriptor copy, optionally changing field number."""
    new_args = self._kwargs.copy()  # pyrefly: ignore[missing-attribute]
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
    yield "%s:" % self.type.__name__  # pyrefly: ignore[missing-attribute]
    for line in str(value).splitlines():
      yield "  %s" % line

  def __str__(self):
    return "<Field %s (Sem Type: %s) of %s: field_number: %s>" % (
        self.name,
        self.proto_type_name,
        self.owner.__name__,  # pyrefly: ignore[missing-attribute]
        self.field_number,
    )


class RDFStructMetaclass(rdfvalue.RDFValueMetaclass):
  """A metaclass which registers new RDFProtoStruct instances."""

  _HAS_DYNAMIC_ATTRIBUTES = True  # help out pytype

  def __init__(untyped_cls, name, bases, env_dict):  # pylint: disable=no-self-argument
    super().__init__(name, bases, env_dict)

    # TODO(user):pytype: find a more elegant solution (if possible).
    cls: type["RDFStruct"] = untyped_cls  # pyrefly: ignore[bad-assignment]
    cls.type_infos = type_info.TypeDescriptorSet()

    # Keep track of the late bound fields.
    cls.late_bound_type_infos = {}

    cls.type_infos_by_field_number = {}

    # Build the class by parsing an existing protobuf class.
    if cls.protobuf is not None:
      registry.RegisterRDFProtoStruct(cls.__name__, cls)
      rdf_proto2.DefineFromWireFormat(cls, cls.protobuf)

    cls._has_custom_init_or_set_raw_data = (
        ("__init__" in env_dict and name not in ("RDFStruct", "RDFProtoStruct"))
        or ("SetRawData" in env_dict and name != "RDFStruct")
        or any(
            getattr(b, "_has_custom_init_or_set_raw_data", False) for b in bases
        )
    )
    cls._class_attributes = set(dir(cls))  # pylint: disable=protected-access


T = TypeVar("T")


class RDFStruct(rdfvalue.RDFValue, metaclass=RDFStructMetaclass):  # pylint: disable=invalid-metaclass
  """An RDFValue object backed by a standard google.protobuf message."""

  # This class must be defined in terms of an existing annotated regular
  # protobuf. See proto2.DefineFromWireFormat().
  protobuf = None

  # This is where the type infos are constructed.
  type_infos: type_info.TypeDescriptorSet = None  # pyrefly: ignore[bad-assignment]

  # Mark as dirty each time we modify this object.
  dirty = False

  # Backing protobuf message and lazy wrapper cache (declared as class
  # attributes so subclasses with custom __setattr__ such as AttributedDict
  # recognize them as internal attributes).
  _proto: Any = None
  _cache: dict[str, Any] = None  # pyrefly: ignore[bad-assignment]
  _prev_hash: Optional[int] = None

  _has_custom_init_or_set_raw_data = False

  def __init__(self, initializer=None, **kwargs):
    super().__init__()
    if self.protobuf is None:
      raise ValueError(
          "%s must define a `protobuf` class attribute."
          % self.__class__.__name__
      )

    self._proto = self.protobuf()  # pylint: disable=not-callable
    self._cache = {}
    self._prev_hash = None

    for arg, value in kwargs.items():
      if not hasattr(self.__class__, arg):
        if arg in self.late_bound_type_infos:  # pyrefly: ignore[missing-attribute]
          raise AttributeError(
              "Field %s refers to an as yet undefined Semantic Type."
              % self.late_bound_type_infos[arg]  # pyrefly: ignore[missing-attribute]
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

  @classmethod
  def _FromProto(cls, proto):
    """Creates an instance wrapping an existing protobuf message."""
    if cls._has_custom_init_or_set_raw_data:
      instance = cls()
      if cls.SetRawData is RDFStruct.SetRawData:
        instance._proto.MergeFrom(proto)  # pylint: disable=protected-access
        instance.SetRawData(instance._proto)  # pylint: disable=protected-access
      else:
        instance.SetRawData(proto)
      return instance

    instance = cls.__new__(cls)
    instance._proto = proto  # pylint: disable=protected-access
    instance._cache = {}  # pylint: disable=protected-access
    instance._prev_hash = None  # pylint: disable=protected-access
    instance.dirty = True
    return instance

  def _Flush(self):
    """Flushes any cached/mutated sub-objects back to self._proto."""
    if not self._cache:
      return
    for attr, value in list(self._cache.items()):
      type_descriptor = self.type_infos.get(attr)
      if type_descriptor is not None:
        type_descriptor.FlushInProto(self._proto, value)

  def CopyConstructor(self, other: Any) -> None:
    """Efficiently copy from other into this object."""
    self.SetRawData(other._CopyRawData())  # pylint: disable=protected-access

  def _DetachSubtree(self) -> None:
    """Detaches self._proto and all cached descendants into standalone copies."""
    new_proto = self._CopyRawData()
    for attr, cached_val in list(self._cache.items()):
      type_descriptor = self.type_infos.get(attr)
      if (
          isinstance(type_descriptor, (ProtoEmbedded, ProtoAnyValue))
          and isinstance(cached_val, RDFStruct)
          and cached_val._proto is getattr(self._proto, attr)  # pylint: disable=protected-access
      ):
        cached_val._DetachSubtree()  # pylint: disable=protected-access
      elif isinstance(cached_val, RepeatedFieldHelper):
        cached_val._Detach()  # pylint: disable=protected-access
    self._proto = new_proto
    self._cache.clear()

  def _DetachCachedEmbedded(self, attr: str, type_descriptor: Any) -> None:
    """Detaches a cached embedded wrapper before its backing submessage is mutated."""
    old_cached = self._cache.pop(attr, None)
    if (
        old_cached is not None
        and isinstance(type_descriptor, (ProtoEmbedded, ProtoAnyValue))
        and old_cached._proto is getattr(self._proto, attr)  # pylint: disable=protected-access
    ):
      old_cached._DetachSubtree()  # pylint: disable=protected-access
    elif isinstance(old_cached, RepeatedFieldHelper):
      old_cached._Detach()  # pylint: disable=protected-access

  def Clear(self):
    """Clear all the fields."""
    for attr in list(self._cache):
      type_descriptor = self.type_infos.get(attr)
      if type_descriptor is not None:
        self._DetachCachedEmbedded(attr, type_descriptor)
    self._proto.Clear()
    self._cache.clear()
    self.dirty = True

  def HasField(self, field_name):
    """Checks if the field exists."""
    if field_name in self._cache:
      return True
    type_descriptor = self.type_infos.get(field_name)
    if type_descriptor is None:
      return False
    return type_descriptor.HasFieldInProto(self._proto)

  def _CopyRawData(self):
    self._Flush()
    assert self.protobuf is not None
    new_proto = self.protobuf()  # pylint: disable=not-callable
    new_proto.CopyFrom(self._proto)
    return new_proto

  def Copy(self: T) -> T:
    """Make an efficient copy of this protobuf."""
    return self.__class__._FromProto(self._CopyRawData())  # pylint: disable=protected-access  # pyrefly: ignore[missing-attribute]

  def __deepcopy__(self, memo):
    del memo  # Unused.
    return self.Copy()

  def GetRawData(self):
    """Retrieves a copy of the underlying protobuf representation."""
    return self._CopyRawData()

  def ListSetFields(self):
    """Iterates over the fields which are actually set.

    Yields:
      a tuple of (type_descriptor, value) for each field which is set.
    """
    for type_descriptor in self.type_infos:
      if self.HasField(type_descriptor.name):
        yield type_descriptor, self.Get(type_descriptor.name)

  def SetRawData(self, data):
    self._proto = data
    self._cache = {}
    self.dirty = True

  def SerializeToBytes(self):
    self._Flush()
    return self._proto.SerializeToString()

  @classmethod
  def FromSerializedBytes(cls, value: bytes):
    precondition.AssertType(value, bytes)
    if cls.protobuf is None:
      raise ValueError(
          "%s must define a `protobuf` class attribute." % cls.__name__
      )
    if cls._has_custom_init_or_set_raw_data:
      instance = cls()
      try:
        instance._proto.MergeFromString(value)  # pylint: disable=protected-access
      except proto2_message.DecodeError as e:
        logging.error(
            "Error parsing %s. %d bytes, extract: %r",
            cls.__name__,
            len(value),
            value[:1000],
        )
        raise rdfvalue.DecodeError(str(e)) from e
      instance.SetRawData(instance._proto)  # pylint: disable=protected-access
      return instance

    proto = cls.protobuf()  # pylint: disable=not-callable
    try:
      proto.ParseFromString(value)
    except proto2_message.DecodeError as e:
      logging.error(
          "Error parsing %s. %d bytes, extract: %r",
          cls.__name__,
          len(value),
          value[:1000],
      )
      raise rdfvalue.DecodeError(str(e)) from e

    return cls._FromProto(proto)

  @classmethod
  def FromWireFormat(cls, value):
    precondition.AssertType(value, bytes)
    return cls.FromSerializedBytes(value)

  __hash__ = None

  def __eq__(self, other):
    if not isinstance(other, self.__class__):
      return NotImplemented

    # Compare all fields set in `self` or `other`, skipping only fields that
    # are unset in both `self` and `other`. This allows RDFStructs to be
    # considered equal when one has a field set to its default value and the
    # other has the field unset.
    fields = set(self._cache) | set(other._cache)  # pylint: disable=protected-access
    for field_desc, _ in self._proto.ListFields():
      fields.add(field_desc.name)
    for field_desc, _ in other._proto.ListFields():  # pylint: disable=protected-access
      fields.add(field_desc.name)

    for field in fields:
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

    fields = set(self._cache)
    for field_desc, _ in self._proto.ListFields():
      fields.add(field_desc.name)

    for k in sorted(fields):
      type_descriptor = self.type_infos.get(k)
      if type_descriptor is None:
        continue
      python_format = self.Get(k, allow_set_default=False)
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
    prev_value = None
    if self._prev_hash is not None:
      prev_value = self.Get(attr, allow_set_default=False)

    # A value of None means we clear the field.
    if value is None:
      self._DetachCachedEmbedded(attr, type_descriptor)
      self._proto.ClearField(attr)
    else:
      # Validate the value and obtain the python format representation.
      value = type_descriptor.Validate(value, container=self)
      if isinstance(type_descriptor, (ProtoEmbedded, ProtoAnyValue)):
        # Flush value before detaching/copying in case value is a submessage
        # inside self._proto.<attr> (e.g. a.nested = a.nested.nested).
        value._Flush()  # pylint: disable=protected-access
        src_proto = value._proto  # pylint: disable=protected-access
        sub_proto = getattr(self._proto, attr)
        if src_proto is not sub_proto:
          tmp_proto = value.protobuf()
          tmp_proto.CopyFrom(src_proto)
          self._DetachCachedEmbedded(attr, type_descriptor)
          sub_proto.CopyFrom(tmp_proto)
        self._cache[attr] = value
      else:
        type_descriptor.SetInProto(self._proto, value)
        if type_descriptor.should_cache:
          self._cache[attr] = value
        else:
          self._cache.pop(attr, None)

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
    cached = self._cache.get(attr)
    if cached is not None:
      return cached

    type_descriptor = self._GetTypeDescriptor(attr)

    if not type_descriptor.HasFieldInProto(self._proto):
      if allow_set_default and type_descriptor.set_default_on_access:
        created = type_descriptor.CreateDefaultInProto(
            self._proto, container=self
        )
        if created is not None:
          if type_descriptor.should_cache:
            self._cache[attr] = created
          self.dirty = True
          return created

      default = type_descriptor.GetDefault(container=self)
      if default is None:
        return None

      # Assign the default value now.
      if allow_set_default and type_descriptor.set_default_on_access:
        default = self._Set(default, type_descriptor)

      return default

    value = type_descriptor.GetFromProto(self._proto, container=self)
    if type_descriptor.should_cache:
      self._cache[attr] = value
    return value

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

    cls.type_infos_by_field_number[field_desc.field_number] = field_desc  # pyrefly: ignore[missing-attribute]
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
  """An RDFStruct which uses standard protobufs for serialization."""

  # TODO(user): if a semantic proto defines a field with the same name as
  # these class variables under some circumstances the proto default value will
  # be set incorrectly.  Figure out a way to make this safe.

  # Must be set to a standard proto2 generated class; we introspect it and
  # extract type descriptors from it.
  protobuf = None

  # Recorded dependencies - used by update_rdf_deps script to update
  # dependencies setting.
  recorded_rdf_deps = None

  def __init__(self, initializer=None, **kwargs):
    super().__init__(initializer, **kwargs)

  def AsPrimitiveProto(self):
    """Return a standard protocol buffer object."""
    if self.protobuf:
      self._Flush()
      result = self.protobuf()
      result.CopyFrom(self._proto)
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
      for k, v in value.ToDict().items():  # pyrefly: ignore[missing-attribute]
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
    return bool(self._cache) or bool(self._proto.ListFields())

  @classmethod
  def EmitProto(cls):
    """Emits .proto file definitions."""
    result = "message %s {\n" % cls.__name__
    for _, desc in sorted(cls.type_infos_by_field_number.items()):  # pyrefly: ignore[missing-attribute]
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
    proto = cls.protobuf()  # pylint: disable=not-callable
    text_format.Parse(text, proto)

    return cls._FromProto(proto)

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
      cls.late_bound_type_infos[field_desc.name] = field_desc  # pyrefly: ignore[missing-attribute]
      return

    # Ensure this field number is unique:
    if field_desc.field_number in cls.type_infos_by_field_number:  # pyrefly: ignore[missing-attribute]
      raise type_info.TypeValueError(
          "Field number %s for field %s is not unique in %s"
          % (field_desc.field_number, field_desc.name, cls.__name__)
      )

    cls.type_infos_by_field_number[field_desc.field_number] = field_desc  # pyrefly: ignore[missing-attribute]

    cls.type_infos.Append(field_desc)
    cls.late_bound_type_infos.pop(field_desc.name, None)  # pyrefly: ignore[missing-attribute]

    # Add direct accessors only if the class does not already have them.
    if not hasattr(cls, field_desc.name):
      # This is much faster than __setattr__/__getattr__.
      setattr(
          cls,
          field_desc.name,
          property(
              lambda self: self.Get(field_desc.name),
              lambda self, x: self._Set(x, field_desc),  # pylint: disable=protected-access
              None,
              field_desc.description,
          ),
      )

  def UnionCast(self):
    union_field_name: Optional[str] = getattr(self, "union_field", None)
    if not union_field_name:
      raise AttributeError("union_field not initialized.")
    union_field = getattr(self, union_field_name)
    cast_field_name = str(union_field).lower()

    set_fields = set(
        type_descriptor.name for type_descriptor, _ in self.ListSetFields()
    )

    union_cases = [
        case.lower()
        for case in self.type_infos[self.union_field].enum_container.enum_dict  # pyrefly: ignore[missing-attribute]
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
    result.type_url = proto2_any.type_url  # pyrefly: ignore[missing-attribute]
    result.value = proto2_any.value  # pyrefly: ignore[missing-attribute]
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
    result.type_url = TypeURL(type(value))  # pyrefly: ignore[missing-attribute]
    result.value = value.SerializeToBytes()  # pyrefly: ignore[missing-attribute]
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
    if cls_type_url != self.type_url:  # pyrefly: ignore[missing-attribute]
      message = "Unpacking value of type '%s' to message of type '%s'."
      logging.warning(message, self.type_url, cls_type_url)  # pyrefly: ignore[missing-attribute]

    return cls.FromSerializedBytes(self.value)  # pyrefly: ignore[missing-attribute]


def TypeURL(cls: type[_V]) -> str:
  if cls.protobuf is None:  # pyrefly: ignore[missing-attribute]
    raise ValueError("protobuf must be set on cls.")
  return f"type.googleapis.com/{cls.protobuf.DESCRIPTOR.full_name}"  # pyrefly: ignore[missing-attribute]
