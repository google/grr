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



import re

import logging

# pylint: disable=W0611
from grr import artifacts
# pylint: enable=W0611

from grr.lib import artifact
from grr.lib import rdfvalue

# Populate the rdfvalues so pylint: disable=W0611
from grr.lib import rdfvalues
# pylint: enable=W0611

from grr.lib import utils
from grr.proto import jobs_pb2


class Error(Exception):
  """Base error class."""


class TypeValueError(Error):
  """Value is not valid."""


class UnknownArg(Error):
  """Raised for unknown flow args."""


class TypeInfoObject(object):
  """Definition of the interface for flow arg typing information."""

  renderer = ""        # The renderer that should be used to render the arg.
  allow_none = False   # Is None allowed as a value.

  # Some descriptors can delegate to child descriptors to define types of
  # members.
  child_descriptor = None

  def __init__(self, name="", default=None, description="", friendly_name="",
               hidden=False):
    """Build a TypeInfo type descriptor.

    Args:
      name: The name of the parameter that this Type info corresponds to.
      default: The default value that should be specified if the parameter was
        not set.
      description: A string describing this flow argument.
      friendly_name: A human readable name which may be provided.
      hidden: Should the argument be hidden from the UI.
    """
    self.name = name
    self.default = default
    self.description = description
    self.hidden = hidden

    if not friendly_name:
      friendly_name = name.replace("_", " ").capitalize()

    self.friendly_name = friendly_name

  def GetDefault(self):
    return self.default

  def Validate(self, value):
    """Confirm that the value is valid for this type.

    Args:
      value: The value being used to initialize the flow.

    Raises:
      TypeValueError: On value not conforming to type.

    Returns:
      A potentially modified value if we can use the provided value to construct
      a valid input.
    """
    return value


class RDFValueType(TypeInfoObject):
  """An arg which must be an RDFValue."""

  def __init__(self, rdfclass=None, **kwargs):
    """An arg which must be an RDFValue.

    Args:
      rdfclass: The RDFValue class that this arg must be.
    """
    super(RDFValueType, self).__init__(**kwargs)
    self.rdfclass = rdfclass

  def GetDefault(self):
    if self.default is None:
      # Just return a new instance of our RDFValue.
      return self.rdfclass()
    else:
      return self.default

  def Validate(self, value):
    """Validate an RDFValue instance.

    Args:
      value: An RDFValue instance or something which may be used to instantiate
        the correct instance.

    Raises:
      TypeValueError: If the value is not a valid RDFValue instance or the
        required type.

    Returns:
      A Valid RDFValue instance.
    """
    # Allow None as a default.
    if value is None:
      return

    if not isinstance(value, self.rdfclass):
      # Try to coerce the type to the correct rdf_class.
      try:
        return self.rdfclass(value)
      except (RuntimeError, TypeError):
        raise TypeValueError("Value for arg %s should be an %s" % (
            self.name, self.rdfclass.__class__.__name__))

    return value


# TODO(user): Deprecate this.
class Any(TypeInfoObject):
  """Any type. No checks are performed."""

  def Validate(self, value):
    return value


class Bool(TypeInfoObject):
  """A True or False value."""

  renderer = "BoolFormRenderer"

  def Validate(self, value):
    if value not in [True, False]:
      raise TypeValueError("Value must be True or False")

    return value


class ProtoEnum(TypeInfoObject):
  """A ProtoBuf Enum field."""

  renderer = "ProtoEnumFormRenderer"

  def __init__(self, proto=None, enum_name=None, **kwargs):
    super(ProtoEnum, self).__init__(**kwargs)
    self.enum_descriptor = proto.DESCRIPTOR.enum_types_by_name[enum_name]

  def Validate(self, value):
    if value not in self.enum_descriptor.values_by_number:
      raise TypeValueError("%s not a valid value for %s" % (
          value, self.enum_descriptor.name))

    return value


class RDFEnum(TypeInfoObject):
  """An RDFValue Enum field."""

  renderer = "RDFEnumFormRenderer"

  def __init__(self, rdfclass=None, enum_name=None, **kwargs):
    super(RDFEnum, self).__init__(**kwargs)
    desc = rdfclass._proto.DESCRIPTOR  # pylint: disable=protected-access
    self.enum_descriptor = desc.enum_types_by_name[enum_name]

  def Validate(self, value):
    if value not in self.enum_descriptor.values_by_number:
      raise TypeValueError("%s not a valid value for %s" % (
          value, self.enum_descriptor.name))

    return value


class List(TypeInfoObject):
  """A list type. Turns another type into a list of those types."""

  def __init__(self, validator=None, **kwargs):
    super(List, self).__init__(**kwargs)
    self.validator = validator

  def Validate(self, value):
    if not isinstance(value, (list, tuple)):
      raise TypeValueError("%s not a valid List" % utils.SmartStr(value))
    else:
      for val in value:
        # Validate each value in the list validates against our type.
        self.validator.Validate(val)

    return value


class String(TypeInfoObject):
  """A String type."""
  renderer = "StringFormRenderer"

  def __init__(self, **kwargs):
    defaults = dict(default="")
    defaults.update(kwargs)
    super(String, self).__init__(**defaults)

  def Validate(self, value):
    if not isinstance(value, basestring):
      raise TypeValueError("%s not a valid string" % value)
    return value


class Bytes(String):
  """A Bytes type."""


class NotEmptyString(String):

  renderer = "NotEmptyStringFormRenderer"

  def Validate(self, value):
    super(NotEmptyString, self).Validate(value)
    if not value:
      raise TypeValueError("Empty string is invalid.")
    return value


class RegularExpression(String):
  """A regular expression type."""

  def Validate(self, value):
    try:
      re.compile(value)
    except (re.error, TypeError) as e:
      raise TypeValueError("%s Error: %s." % (value, e))

    return value


class EncryptionKey(String):

  renderer = "EncryptionKeyFormRenderer"

  def __init__(self, length=None, **kwargs):
    self.length = length
    super(EncryptionKey, self).__init__(**kwargs)

  def Validate(self, value):
    try:
      key = value.decode("hex")
    except TypeError:
      raise TypeValueError("Key given is not a hex string.")

    if len(key) != self.length:
      raise TypeValueError("Invalid key length (%d)." % len(value))

    return value


class Number(TypeInfoObject):
  """A Number type."""

  allow_none = False
  renderer = "StringFormRenderer"

  def Validate(self, value):
    if not isinstance(value, (int, long)):
      raise TypeValueError("Invalid value %s for Number" % value)

    return value


class ArtifactList(TypeInfoObject):
  """A list of Artifacts names."""

  renderer = "ArtifactListRenderer"

  def Validate(self, value):
    """Value must be a list of artifact names."""
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

    return value


class MultiSelectList(TypeInfoObject):
  """Abstract type that select from a list of values."""

  def Validate(self, value):
    try:
      iter(value)
    except TypeError:
      raise TypeValueError("%s not a valid iterable" % value)
    for val in value:
      if not isinstance(val, basestring):
        raise TypeValueError("%s not a valid instance string." % val)

    return value


class UserList(MultiSelectList):
  """A list of usernames."""
  renderer = "UserListRenderer"


class TypeDescriptorSet(object):
  """This is a collection of type descriptors.

  This collections is effectively immutable. Add/Remove operations create new
  set instead of modifying existing one.
  """

  def __init__(self, *descriptors):
    self.descriptors = list(descriptors)
    self.descriptor_map = dict([(desc.name, desc) for desc in descriptors])

  def __getitem__(self, item):
    return self.descriptor_map[item]

  def __iter__(self):
    return iter(self.descriptors)

  def __str__(self):
    result = "\n ".join(["%s: %s" % (x.name, x.description)
                         for x in self.descriptors])

    return "<TypeDescriptorSet for %s>\n %s\n</TypeDescriptorSet>\n" % (
        self.__class__.__name__, result)

  def __add__(self, other):
    return self.Add(other)

  def __radd__(self, other):
    return self.Add(other)

  def __iadd__(self, other):
    return self.Add(other)

  def Add(self, other):
    """Returns a copy of this set with a new element added."""
    new_descriptors = []
    for desc in self.descriptors + other.descriptors:
      if desc not in new_descriptors:
        new_descriptors.append(desc)
    return TypeDescriptorSet(*new_descriptors)

  def HasDescriptor(self, descriptor_name):
    """Checks wheter this set has an element with the given name."""
    return descriptor_name in self.descriptor_map.keys()

  def Remove(self, *descriptor_names):
    """Returns a copy of this set without elements with given names."""
    new_descriptor_map = self.descriptor_map.copy()
    for name in descriptor_names:
      del new_descriptor_map[name]
    new_descriptors = [desc for desc in self.descriptors
                       if desc in new_descriptor_map.values()]
    return TypeDescriptorSet(*new_descriptors)

  def ParseArgs(self, args):
    """Parse and validate the args.

    Note we pop all the args we consume here - so if there are any args we dont
    know about, args will not be an empty dict after this. This allows the same
    args to be parsed by several TypeDescriptorSets.

    Args:
      args: A dictionary of arguments that this TypeDescriptorSet might use. If
        this dict does not have a required parameter, we still yield its default
        value.

    Yields:
      A (name, value) tuple of the parsed args.
    """
    for descriptor in self:
      # Get the value from the kwargs or, if not specified, the default.
      value = args.pop(descriptor.name, None)

      if value is None:
        # No need to validate the default value.
        value = descriptor.default
      else:
        try:
          # Validate this value - this should raise if the value provided is not
          # acceptable to the type descriptor.
          value = descriptor.Validate(value)
        except Exception as e:
          logging.error("Invalid value %s for arg %s", value, descriptor.name)
          raise e

      yield descriptor.name, value


class PathTypeEnum(ProtoEnum):
  """Represent pathspec's pathtypes enum especially."""

  def __init__(self, **kwargs):
    defaults = dict(name="pathtype",
                    description="The type of access for this path.",
                    default=rdfvalue.RDFPathSpec.Enum("OS"),
                    friendly_name="Type",
                    proto=jobs_pb2.Path,
                    enum_name="PathType")

    defaults.update(kwargs)
    super(PathTypeEnum, self).__init__(**defaults)

  def Validate(self, value):
    if value < 0:
      raise ValueError("Path type must be set")

    return super(PathTypeEnum, self).Validate(value)


class RDFURNType(RDFValueType):
  """A URN type."""

  def __init__(self, **kwargs):
    defaults = dict(default=rdfvalue.RDFURN("aff4:/"),
                    rdfclass=rdfvalue.RDFURN)

    defaults.update(kwargs)
    super(RDFURNType, self).__init__(**defaults)


class PathspecType(RDFValueType):
  """A Type for handling pathspecs."""

  # These specify the child descriptors of a pathspec.
  child_descriptor = TypeDescriptorSet(
      String(description="Path to the file.",
             name="path",
             friendly_name="Path",
             default="/"),
      PathTypeEnum())

  def __init__(self, **kwargs):
    defaults = dict(
        default=rdfvalue.RDFPathSpec(
            path="/",
            pathtype=rdfvalue.RDFPathSpec.Enum("OS")),
        name="pathspec",
        rdfclass=rdfvalue.RDFPathSpec)

    defaults.update(kwargs)
    super(PathspecType, self).__init__(**defaults)

  def GetDefault(self):
    if not self.default:
      return None
    return self.default.Copy()


class MemoryPathspecType(PathspecType):
  child_descriptor = TypeDescriptorSet(
      String(description="Path to the memory device file.",
             name="path",
             friendly_name="Memory device path",
             default=r"\\.\pmem"),
      PathTypeEnum(default=rdfvalue.RDFPathSpec.Enum("MEMORY")))


class GrepspecType(RDFValueType):
  """A Type for handling Grep specifications."""

  child_descriptor = TypeDescriptorSet(
      PathspecType(name="target"),
      String(
          description="Search for this regular expression.",
          name="regex",
          friendly_name="Regular Expression",
          default=""),
      Bytes(
          description="Search for this literal expression.",
          name="literal",
          friendly_name="Literal Match",
          default=""),
      Number(
          description="Offset to start searching from.",
          name="start_offset",
          friendly_name="Start",
          default=0),
      Number(
          description="Length to search.",
          name="length",
          friendly_name="Length",
          default=10737418240),
      ProtoEnum(
          description="How many results should be returned?",
          name="mode",
          friendly_name="Search Mode",
          proto=jobs_pb2.GrepRequest,
          enum_name="Mode",
          default=jobs_pb2.GrepRequest.FIRST_HIT),
      Number(
          description="Snippet returns these many bytes before the hit.",
          name="bytes_before",
          friendly_name="Preamble",
          default=0),
      Number(
          description="Snippet returns these many bytes after the hit.",
          name="bytes_after",
          friendly_name="Context",
          default=0),
      )

  def __init__(self, **kwargs):
    defaults = dict(default=rdfvalue.GrepSpec(),
                    name="grepspec",
                    rdfclass=rdfvalue.GrepSpec)

    defaults.update(kwargs)
    super(GrepspecType, self).__init__(**defaults)

  def Validate(self, value):
    if value.target.pathtype < 0:
      raise TypeValueError("GrepSpec has an invalid target PathSpec.")

    return super(GrepspecType, self).Validate(value)


class FindSpecType(RDFValueType):
  """A Find spec type."""

  child_descriptor = TypeDescriptorSet(
      PathspecType(),
      String(
          description="Search for this regular expression.",
          name="path_regex",
          friendly_name="Path Regular Expression",
          default=""),
      String(
          description="Search for this regular expression in the data.",
          name="data_regex",
          friendly_name="Data Regular Expression",
          default=""),
      Bool(
          description="Should we cross devices?",
          name="cross_devs",
          friendly_name="Cross Devices",
          default=False),
      Number(
          description="Maximum recursion depth.",
          name="max_depth",
          friendly_name="Depth",
          default=5),
      )

  def __init__(self, **kwargs):
    defaults = dict(name="findspec",
                    rdfclass=rdfvalue.RDFFindSpec)

    defaults.update(kwargs)
    super(FindSpecType, self).__init__(**defaults)

  def Validate(self, value):
    """Validates the passed in protobuf for sanity."""
    value = super(FindSpecType, self).Validate(value)

    # Check the regexes are valid.
    try:
      if value.data_regex:
        re.compile(value.data_regex)

      if value.path_regex:
        re.compile(value.path_regex)
    except re.error, e:
      raise TypeValueError("Invalid regex for FindFiles. Err: {0}".format(e))

    return value


class InstallDriverRequestType(RDFValueType):
  """A type for the InstallDriverRequest."""

  # There is no point showing this in the GUI since the user would have to
  # provide an encrypted blob so we set this to the empty set.
  child_descriptor = TypeDescriptorSet()

  def __init__(self, **kwargs):
    defaults = dict(name="driver_installer",
                    rdfclass=rdfvalue.InstallDriverRequest)

    defaults.update(kwargs)
    super(InstallDriverRequestType, self).__init__(**defaults)

  def GetDefault(self):
    if not self.default:
      return None
    return self.default.Copy()


class GenericProtoDictType(RDFValueType):

  def __init__(self, **kwargs):
    defaults = dict(default=rdfvalue.RDFProtoDict(),
                    rdfclass=rdfvalue.RDFProtoDict)

    defaults.update(kwargs)
    super(GenericProtoDictType, self).__init__(**defaults)


class VolatilityRequestType(RDFValueType):
  """A type for the Volatility request."""

  child_descriptor = TypeDescriptorSet(
      String(
          description="Profile to use.",
          name="profile",
          friendly_name="Volatility profile",
          default=""),
      GenericProtoDictType(
          description="Volatility Arguments.",
          name="args"),
      MemoryPathspecType(
          description="Path to the device.",
          default=rdfvalue.RDFPathSpec(
              path=r"\\.\pmem",
              pathtype=rdfvalue.RDFPathSpec.Enum("MEMORY")),
          name="device",
          )
      )

  def __init__(self, **kwargs):
    default_request = rdfvalue.VolatilityRequest()
    default_request.device.path = r"\\.\pmem"
    default_request.device.pathtype = rdfvalue.RDFPathSpec.Enum("MEMORY")

    defaults = dict(name="request",
                    default=default_request,
                    rdfclass=rdfvalue.VolatilityRequest)

    defaults.update(kwargs)
    super(VolatilityRequestType, self).__init__(**defaults)


class ForemanAttributeRegexType(RDFValueType):
  """A Type for handling the ForemanAttributeRegex."""

  child_descriptor = TypeDescriptorSet(
      String(
          name="path",
          description=("A relative path under the client for which "
                       "the attribute applies"),
          default="/"),

      String(
          name="attribute_name",
          description="The attribute to match",
          default="System"),

      RegularExpression(
          name="attribute_regex",
          description="Regular expression to apply to an attribute",
          default=".*"),
      )

  def __init__(self, **kwargs):
    defaults = dict(name="foreman_attributes",
                    rdfclass=rdfvalue.ForemanAttributeRegex)

    defaults.update(kwargs)
    super(ForemanAttributeRegexType, self).__init__(**defaults)


class ForemanAttributeIntegerType(RDFValueType):
  """A type for handling the ForemanAttributeInteger."""

  child_descriptor = TypeDescriptorSet(
      String(
          name="path",
          description=("A relative path under the client for which "
                       "the attribute applies"),
          default="/"),

      String(
          name="attribute_name",
          description="The attribute to match.",
          default="Version"),

      ProtoEnum(
          name="operator",
          description="Comparison operator to apply to integer value",
          proto=jobs_pb2.ForemanAttributeInteger,
          enum_name="Operator",
          default=rdfvalue.ForemanAttributeInteger.Enum("EQUAL")),

      Number(
          name="value",
          description="Value to compare to",
          default=0),
      )

  def __init__(self, **kwargs):
    defaults = dict(name="foreman_attributes",
                    rdfclass=rdfvalue.ForemanAttributeInteger)

    defaults.update(kwargs)
    super(ForemanAttributeIntegerType, self).__init__(**defaults)
