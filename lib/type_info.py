#!/usr/bin/env python
# Copyright 2012 Google Inc.
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.


"""Typing information for flow arguments.

This contains objects that are used to provide type annotations for flow
parameters. These annotations are used to assist in rendering the UI for
starting flows and for validating arguments.
"""



from google.protobuf import message
from grr.lib import artifact
from grr.lib import utils


class Error(Exception):
  """Base error class."""


class TypeValueError(Error):
  """Value is not valid."""


class NoneNotAllowedTypeValueError(TypeValueError):
  """Value is None where None is not valid."""


class DecodeError(Error):
  """Base error for decoding the type from string."""


class TypeInfoObject(object):
  """Definition of the interface for flow arg typing information."""

  renderer = ""        # The renderer that should be used to render the arg.
  allow_none = False   # Is None allowed as a value.

  def Validate(self, value):
    """Confirm that the value is valid for this type.

    Args:
      value: The value being used to initialize the flow.

    Raises:
      TypeValueError: On value not conforming to type.
    """

  def DecodeString(self, value):
    """Take a value in string form and return a value according to type.

    Args:
      value: A string value for the type, normally from the UI. Not unicode.

    Returns:
      A decoded value of whatever type this object represents.

    Raises:
      DecodeError: On failure to decode or to validate.
    """

  def AllowNone(self):
    return self.allow_none


class Bool(TypeInfoObject):
  """A True or False value."""

  renderer = "BoolFormRenderer"

  def Validate(self, value):
    if value is None:
      if not self.allow_none:
        raise NoneNotAllowedTypeValueError("None is an invalid value here")
    elif value is not True and value is not False:
      raise TypeValueError("Value must be True or False")

  def DecodeString(self, value):
    if self.allow_none and value.lower() in ["none", "auto"]:
      return None
    elif value.lower() == "true":
      return True
    elif value.lower() == "false":
      return False
    else:
      raise DecodeError("Invalid value for True/False %s" % value)


class BoolOrNone(Bool):
  """A Bool field or None."""
  allow_none = True


class ProtoEnum(TypeInfoObject):
  """A ProtoBuf Enum field."""

  renderer = "ProtoEnumFormRenderer"

  def __init__(self, proto, enum_name):
    super(ProtoEnum, self).__init__()
    self.enum_descriptor = proto.DESCRIPTOR.enum_types_by_name[enum_name]

  def Validate(self, value):
    if value is None:
      if not self.allow_none:
        raise NoneNotAllowedTypeValueError("None is an invalid value here")
    else:
      if value not in self.enum_descriptor.values_by_number:
        raise TypeValueError("%s not a valid value for %s" % (
            value, self.enum_descriptor.name))

  def DecodeString(self, value):
    if self.allow_none and value.lower() in ["none", "auto"]:
      return None
    try:
      value = int(value)
      self.Validate(value)
    except (ValueError, TypeValueError):
      raise DecodeError("%s not a valid value for %s" %
                        (value, self.enum_descriptor.name))
    return value


class ProtoEnumOrNone(ProtoEnum):
  """A ProtoBuf Enum field or None."""
  allow_none = True


class Proto(TypeInfoObject):
  """A ProtoBuf type."""

  renderer = "EmptyRenderer"

  def __init__(self, proto=None):
    """Constructor.

    Args:
      proto: Require the protobuf to be an instance of this class. If not set,
      defaults to requiring the arg to be any protobuf.
    """
    super(Proto, self).__init__()
    self.proto = proto or message.Message

  def Validate(self, value):
    if value is None:
      if not self.allow_none:
        raise NoneNotAllowedTypeValueError("None is an invalid value here")
    elif not isinstance(value, self.proto):
      raise TypeValueError("%s not a valid instance of %s" % (
          value, self.proto.DESCRIPTOR.name))

  def DecodeString(self, value):
    if self.allow_none and value.lower() in ["none", "auto"]:
      return None
    # We currently don't support decoding of protobufs from string from the UI.
    raise DecodeError("Invalid value for %s, Decoding unsupported." %
                      self.proto.DESCRIPTOR.name)


class ProtoOrNone(Proto):
  """A ProtoBuf or the value None."""
  allow_none = True


class ListProto(Proto):
  """A flow arg which contains a list of a specific protobuf."""

  def Validate(self, value):
    if value is None:
      if not self.allow_none:
        raise NoneNotAllowedTypeValueError("None is an invalid value here")
      return

    try:
      for x in value:
        super(ListProto, self).Validate(x)
    except TypeError:
      raise TypeValueError("Not an iterable.")


class ListProtoOrNone(ListProto):
  """A ListProto which can be None."""
  allow_none = True


class List(TypeInfoObject):
  """A list type. Turns another type into a list of those types."""

  renderer = "EmptyRenderer"   # No UI support.

  def __init__(self, value_type):
    super(List, self).__init__()
    self.value_type = value_type

  def Validate(self, value):
    if value is None:
      if not self.allow_none:
        raise NoneNotAllowedTypeValueError("None is an invalid value here")
    elif not isinstance(value, (list, tuple)):
      raise TypeValueError("%s not a valid List" % utils.SmartStr(value))
    else:
      for val in value:
        # Validate each value in the list validates against our type.
        self.value_type.Validate(val)

  def DecodeString(self, value):
    if self.allow_none and value.lower() in ["none", "auto"]:
      return None
    # We currently don't support decoding of lists from string from the UI.
    raise DecodeError("Invalid value, List Decoding unsupported.")


class ListOrNone(List):
  """A List or the value None."""
  allow_none = True


class String(TypeInfoObject):
  """A String type."""

  allow_none = False
  renderer = "StringFormRenderer"

  def Validate(self, value):
    if value is None:
      if not self.allow_none:
        raise NoneNotAllowedTypeValueError("None is an invalid value here")
    elif not isinstance(value, basestring):
      raise TypeValueError("%s not a valid string" % value)

  def DecodeString(self, value):
    if self.allow_none:
      if value is None or utils.SmartStr(value).lower() in ["none", "auto"]:
        return None
    return utils.SmartUnicode(value)


class StringOrNone(String):
  """A String or the value None."""
  allow_none = True


class Number(TypeInfoObject):
  """A Number type."""

  allow_none = False
  renderer = "StringFormRenderer"

  def Validate(self, value):
    if value is None:
      if not self.allow_none:
        raise NoneNotAllowedTypeValueError("None is an invalid value here")
    elif not isinstance(value, (int, long)):
      raise TypeValueError("Invalid value %s for Number" % value)

  def DecodeString(self, value):
    if self.allow_none and value.lower() in ["none", "auto"]:
      return None
    try:
      value = int(value)
      self.Validate(value)
    except (TypeValueError, ValueError) as e:
      raise DecodeError(e)
    return value


class NumberOrNone(Number):
  """A number or the value None."""
  allow_none = True


class ArtifactList(TypeInfoObject):
  """A list of Artifacts names."""

  renderer = "ArtifactListRenderer"

  def Validate(self, value):
    if value is None:
      if not self.allow_none:
        raise NoneNotAllowedTypeValueError("None is an invalid value here")
    else:
      try:
        iter(value)
      except TypeError:
        raise TypeValueError("%s not a valid iterable for ArtifactList" % value)
      for val in value:
        if not isinstance(val, basestring):
          raise TypeValueError("%s not a valid instance string." % val)
        artifact_cls = artifact.Artifact.classes.get(val)
        if not artifact_cls or not issubclass(artifact_cls, artifact.Artifact):
          raise TypeValueError("%s not a valid Artifact class." % val)

  def DecodeString(self, value):
    """Decode the artifacts from string, they are encoded as comma separated."""
    if self.allow_none and value.lower() in ["none", "auto"]:
      return None

    names = [v.strip() for v in value.split(",")]
    results = []
    for name in names:
      try:
        results.append(name)
      except KeyError:
        raise DecodeError("%s is not a valid Artifact" % name)
    self.Validate(results)
    return results


class ArtifactListOrNone(ArtifactList):
  """An artifact list or the value None."""
  allow_none = True
