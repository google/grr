#!/usr/bin/env python
"""Typing information for flow arguments.

This contains objects that are used to provide type annotations for flow
parameters. These annotations are used to assist in rendering the UI for
starting flows and for validating arguments.
"""



import re

import logging

from grr.lib import lexer
from grr.lib import objectfilter
from grr.lib import rdfvalue
from grr.lib import registry
from grr.lib import utils


class Error(Exception):
  """Base error class."""


class TypeValueError(Error, ValueError):
  """Value is not valid."""


class UnknownArg(TypeValueError):
  """Raised for unknown flow args."""


class TypeInfoObject(object):
  """Definition of the interface for flow arg typing information."""

  renderer = ""        # The renderer that should be used to render the arg.

  # Some descriptors can delegate to child descriptors to define types of
  # members.
  child_descriptor = None

  __metaclass__ = registry.MetaclassRegistry

  # The delegate type this TypeInfoObject manages.
  _type = None

  def __init__(self, name="", default=None, description="", friendly_name="",
               hidden=False, help=""):
    """Build a TypeInfo type descriptor.

    Args:
      name: The name of the parameter that this Type info corresponds to.
      default: The default value that should be specified if the parameter was
        not set.
      description: A string describing this flow argument.
      friendly_name: A human readable name which may be provided.
      hidden: Should the argument be hidden from the UI.
      help: A synonym for 'description'.
    """
    self.name = name
    self.default = default
    self.description = description or help
    self.hidden = hidden

    if not friendly_name:
      friendly_name = name.replace("_", " ").capitalize()

    self.friendly_name = friendly_name

    # It is generally impossible to check the default value here
    # because this happens before any configuration is loaded (i.e. at
    # import time). Hence default values which depend on the config
    # system cant be tested. We just assume that the default value is
    # sensible since its hard coded in the code.

  def GetType(self):
    """Returns the type class described by this type info."""
    return self._type

  def GetDefault(self):
    """Return the default value for this TypeInfoObject."""
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

  def FromString(self, string):
    return string

  def ToString(self, value):
    return utils.SmartStr(value)

  def Help(self):
    """Returns a helpful string describing this type info."""
    return "%s = %s\n   %s" % (self.name, self.GetDefault(),
                               self.description)


# This will register all classes into this modules's namespace regardless of
# where they are defined. This allows us to decouple the place of definition of
# a class (which might be in a plugin) from its use which will reference this
# module.
TypeInfoObject.classes = globals()


class RDFValueType(TypeInfoObject):
  """An arg which must be an RDFValue."""

  rdfclass = rdfvalue.RDFValue

  def __init__(self, rdfclass=None, **kwargs):
    """An arg which must be an RDFValue.

    Args:
      rdfclass: The RDFValue class that this arg must be.
      **kwargs: Passthrough to base class.
    """
    super(RDFValueType, self).__init__(**kwargs)
    self._type = self.rdfclass = rdfclass

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
      except rdfvalue.InitializeError:
        raise TypeValueError("Value for arg %s should be an %s" % (
            self.name, self.rdfclass.__class__.__name__))

    return value

  def FromString(self, string):
    return self.rdfclass(string)


class Bool(TypeInfoObject):
  """A True or False value."""

  renderer = "BoolFormRenderer"

  _type = bool

  def Validate(self, value):
    if value not in [True, False]:
      raise TypeValueError("Value must be True or False")

    return value

  def FromString(self, string):
    """Parse a bool from a string."""
    if string.lower() in ("false", "no", "n"):
      return False

    if string.lower() in ("true", "yes", "y"):
      return True

    raise TypeValueError("%s is not recognized as a boolean value." % string)


class SemanticEnum(TypeInfoObject):
  """Describe an enum for a Semantic Protobuf."""

  def __init__(self, enum_container=None, **kwargs):
    super(SemanticEnum, self).__init__(**kwargs)
    self.enum_container = enum_container

  def Validate(self, value):
    if (value not in self.enum_container.reverse_enum and
        value not in self.enum_container.enum_dict):
      raise TypeValueError("%s not a valid value for %s" % (
          value, self.enum_container.name))

    return value


class List(TypeInfoObject):
  """A list type. Turns another type into a list of those types."""

  _type = list

  def __init__(self, validator=None, **kwargs):
    self.validator = validator
    super(List, self).__init__(**kwargs)

  def Validate(self, value):
    """Validate a potential list."""
    if isinstance(value, basestring):
      raise TypeValueError("Value must be an iterable not a string.")

    elif not isinstance(value, (list, tuple)):
      raise TypeValueError("%s not a valid List" % utils.SmartStr(value))

    else:
      for val in value:
        # Validate each value in the list validates against our type.
        self.validator.Validate(val)

    return value

  def FromString(self, string):
    result = []
    for x in string.split(","):
      x = x.strip()
      result.append(self.validator.FromString(x))

    return result

  def ToString(self, value):
    return ",".join([self.validator.ToString(x) for x in value])


class InterpolatedList(List):
  """A list of path strings that can contain %% expansions."""
  renderer = "InterpolatedPathRenderer"


class String(TypeInfoObject):
  """A String type."""

  renderer = "StringFormRenderer"

  _type = unicode

  def __init__(self, **kwargs):
    defaults = dict(default="")
    defaults.update(kwargs)
    super(String, self).__init__(**defaults)

  def Validate(self, value):
    if not isinstance(value, basestring):
      raise TypeValueError("%s: %s not a valid string" % (self.name, value))

    # A String means a unicode String. We must be dealing with unicode strings
    # here and the input must be encodable as a unicode object.
    try:
      return unicode(value)
    except UnicodeError:
      raise TypeValueError("Not a valid unicode string")


class Bytes(String):
  """A Bytes type."""

  _type = str

  def Validate(self, value):
    if not isinstance(value, str):
      raise TypeValueError("%s not a valid string" % value)

    return value


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


class EncryptionKey(TypeInfoObject):

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


class Integer(TypeInfoObject):
  """An Integer number type."""
  renderer = "StringFormRenderer"

  _type = long

  def Validate(self, value):
    if not isinstance(value, (int, long)):
      raise TypeValueError("Invalid value %s for Integer" % value)

    return long(value)

  def FromString(self, string):
    try:
      return long(string)
    except ValueError:
      raise TypeValueError("Invalid value %s for Integer" % string)


class Float(Integer):
  """Type info describing a float."""
  _type = float

  def Validate(self, value):
    try:
      value = float(value)
    except ValueError:
      raise TypeValueError("Invalid value %s for Float" % value)

    return value

  def FromString(self, string):
    try:
      return float(string)
    except ValueError:
      raise TypeValueError("Invalid value %s for Float" % string)


class Duration(RDFValueType):
  """Duration in microseconds."""

  def __init__(self, **kwargs):
    defaults = dict(rdfclass=rdfvalue.Duration)

    defaults.update(kwargs)
    super(Duration, self).__init__(**defaults)

  def Validate(self, value):
    if not isinstance(value, rdfvalue.Duration):
      raise TypeValueError("Invalid value %s for Duration" % value)

    return value

  def FromString(self, string):
    try:
      return rdfvalue.Duration(string)
    except ValueError:
      raise TypeValueError("Invalid value %s for Duration" % string)


class Choice(TypeInfoObject):
  """A choice from a set of allowed values."""

  def __init__(self, choices=None, validator=None, **kwargs):
    self.choices = choices
    self.validator = validator or String()
    super(Choice, self).__init__(**kwargs)

  def Validate(self, value):
    self.validator.Validate(value)

    if value not in self.choices:
      raise TypeValueError("%s not a valid instance string." % value)

    return value


class MultiSelectList(TypeInfoObject):
  """Abstract type that select from a list of values."""

  def Validate(self, value):
    """Check that this is a list of strings."""
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
    self.descriptor_names = [x.name for x in descriptors]
    self.descriptor_map = dict([(desc.name, desc) for desc in descriptors])

  def __getitem__(self, item):
    return self.descriptor_map[item]

  def __contains__(self, item):
    return item in self.descriptor_map

  def get(self, item, default=None):  # pylint: disable=g-bad-name
    return self.descriptor_map.get(item, default)

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

  def Append(self, desc):
    """Append the descriptor to this set."""
    if desc not in self.descriptors:
      self.descriptors.append(desc)
      self.descriptor_map[desc.name] = desc
      self.descriptor_names.append(desc.name)

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
        except Exception:
          logging.error("Invalid value %s for arg %s", value, descriptor.name)
          raise

      yield descriptor.name, value


class RDFURNType(RDFValueType):
  """A URN type."""

  def __init__(self, **kwargs):
    defaults = dict(default=rdfvalue.RDFURN("aff4:/"),
                    rdfclass=rdfvalue.RDFURN)

    defaults.update(kwargs)
    super(RDFURNType, self).__init__(**defaults)

  def Validate(self, value):
    # Check this separately since SerializeToString will modify it.
    try:
      if value.scheme != "aff4":
        raise TypeValueError("Bad URN: %s" % value.SerializeToString())
    except AttributeError as e:
      raise TypeValueError("Bad RDFURN: %s" % e)
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

    result = self.default.Copy()

    return result


class FilterString(String):
  """An argument that is a valid filter string parsed by query_parser_cls.

  The class member query_parser_cls should be overriden by derived classes.
  """

  renderer = "StringFormRenderer"

  # A subclass of lexer.Searchparser able to parse textual queries.a
  query_parser_cls = lexer.SearchParser

  def __init__(self, **kwargs):
    if not self.query_parser_cls:
      raise Error("Undefined query parsing class for type %s."
                  % self.__class__.__name__)
    super(FilterString, self).__init__(**kwargs)

  def Validate(self, value):
    query = str(value)
    try:
      self.query_parser_cls(query).Parse()
    except (lexer.ParseError, objectfilter.ParseError), e:
      raise TypeValueError("Malformed filter %s: %s" % (self.name, e))
    return query


# TODO(user): Deprecate this.
class Any(TypeInfoObject):
  """Any type. No checks are performed."""

  def Validate(self, value):
    return value
