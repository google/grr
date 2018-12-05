#!/usr/bin/env python
"""Typing information for flow arguments.

This contains objects that are used to provide type annotations for flow
parameters. These annotations are used to assist in rendering the UI for
starting flows and for validating arguments.
"""

from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

import logging


from future.utils import itervalues
from future.utils import string_types
from future.utils import with_metaclass
from past.builtins import long

from grr_response_core.lib import rdfvalue
from grr_response_core.lib import registry
from grr_response_core.lib import utils
from grr_response_core.lib.util import precondition


class Error(Exception):
  """Base error class."""


class TypeValueError(Error, ValueError):
  """Value is not valid."""


class UnknownArg(TypeValueError):
  """Raised for unknown flow args."""


class TypeInfoObject(with_metaclass(registry.MetaclassRegistry, object)):
  """Definition of the interface for flow arg typing information."""

  # The delegate type this TypeInfoObject manages.
  _type = None

  def __init__(self,
               name="",
               default=None,
               description="",
               friendly_name="",
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
    return "%s\n   Description: %s\n   Default: %s" % (self.name,
                                                       self.description,
                                                       self.GetDefault())


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
        raise TypeValueError("Value for arg %s should be an %s" %
                             (self.name, self.rdfclass.__name__))

    return value

  def FromString(self, string):
    return self.rdfclass.FromHumanReadable(string)


class RDFStructDictType(TypeInfoObject):
  """An arg which must be a dict that maps into an RDFStruct."""

  rdfclass = rdfvalue.RDFValue

  def __init__(self, rdfclass=None, **kwargs):
    """An arg which must be an RDFStruct.

    Args:
      rdfclass: The RDFStruct subclass that this arg must be.
      **kwargs: Passthrough to base class.
    """
    super(RDFStructDictType, self).__init__(**kwargs)
    self._type = self.rdfclass = rdfclass

  def Validate(self, value):
    """Validate the value.

    Args:
      value: Value is expected to be a dict-like object that a given RDFStruct
        can be initialized from.

    Raises:
      TypeValueError: If the value is not a valid dict-like object that a given
        RDFStruct can be initialized from.

    Returns:
      A valid instance of self.rdfclass or None.
    """
    if value is None:
      return None

    if not isinstance(value, self.rdfclass):
      # Try to coerce the type to the correct rdf_class.
      try:
        r = self.rdfclass()
        r.FromDict(value)
        return r
      except (AttributeError, TypeError, rdfvalue.InitializeError):
        # AttributeError is raised if value contains items that don't
        # belong to the given rdfstruct.
        # TypeError will be raised if value is not a dict-like object.
        raise TypeValueError("Value for arg %s should be an %s" %
                             (self.name, self.rdfclass.__name__))

    return value

  def FromString(self, string):
    return self.rdfclass.FromSerializedString(string)


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
    result = "\n ".join(
        ["%s: %s" % (x.name, x.description) for x in self.descriptors])

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
    return descriptor_name in self.descriptor_map

  def Remove(self, *descriptor_names):
    """Returns a copy of this set without elements with given names."""
    new_descriptor_map = self.descriptor_map.copy()
    for name in descriptor_names:
      new_descriptor_map.pop(name, None)

    new_descriptors = [
        desc for desc in self.descriptors
        if desc in itervalues(new_descriptor_map)
    ]
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


class Bool(TypeInfoObject):
  """A True or False value."""

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


class List(TypeInfoObject):
  """A list type. Turns another type into a list of those types."""

  _type = list

  def __init__(self, validator=None, **kwargs):
    self.validator = validator
    super(List, self).__init__(**kwargs)

  def Validate(self, value):
    """Validate a potential list."""
    if isinstance(value, string_types):
      raise TypeValueError("Value must be an iterable not a string.")

    elif not isinstance(value, (list, tuple)):
      raise TypeValueError("%s not a valid List" % utils.SmartStr(value))

    # Validate each value in the list validates against our type.
    return [self.validator.Validate(val) for val in value]

  def FromString(self, string):
    result = []
    if string:
      for x in string.split(","):
        x = x.strip()
        result.append(self.validator.FromString(x))

    return result

  def ToString(self, value):
    return ",".join([self.validator.ToString(x) for x in value])


class String(TypeInfoObject):
  """A String type."""

  _type = unicode

  def __init__(self, **kwargs):
    defaults = dict(default="")
    defaults.update(kwargs)
    super(String, self).__init__(**defaults)

  def Validate(self, value):
    if not isinstance(value, string_types):
      raise TypeValueError("%s: %s not a valid string" % (self.name, value))

    # A String means a unicode String. We must be dealing with unicode strings
    # here and the input must be encodable as a unicode object.
    try:
      return unicode(value)
    except UnicodeError:
      raise TypeValueError("Not a valid unicode string")

  def ToString(self, value):
    precondition.AssertType(value, unicode)
    return value


class Bytes(String):
  """A Bytes type."""

  _type = bytes

  def Validate(self, value):
    if not isinstance(value, str):
      raise TypeValueError("%s not a valid string" % value)

    return value

  def FromString(self, string):
    precondition.AssertType(string, unicode)
    return string.encode("utf-8")

  def ToString(self, value):
    precondition.AssertType(value, bytes)
    return value.decode("utf-8")


class Integer(TypeInfoObject):
  """An Integer number type."""

  _type = long

  def Validate(self, value):
    if value is None:
      value = 0

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
    except (ValueError, TypeError):
      raise TypeValueError("Invalid value %s for Float" % value)

    return value

  def FromString(self, string):
    try:
      return float(string)
    except (ValueError, TypeError):
      raise TypeValueError("Invalid value %s for Float" % string)


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


class MultiChoice(TypeInfoObject):
  """Choose a list of values from a set of allowed values."""

  def __init__(self, choices=None, validator=None, **kwargs):
    """Create a multichoice object and validate choices.

    Args:
      choices: list of available choices
      validator: validator to use for each of the list *items* the validator for
                 the top level is a list.
      **kwargs: passed through to parent class.
    """
    self.choices = choices
    subvalidator = validator or String()
    self.validator = List(validator=subvalidator)

    # Check the choices match the validator
    for choice in self.choices:
      subvalidator.Validate(choice)
    super(MultiChoice, self).__init__(**kwargs)

  def Validate(self, values):
    self.validator.Validate(values)

    for value in values:
      if value not in self.choices:
        raise TypeValueError("%s not a valid instance string." % value)
    if len(values) != len(set(values)):
      raise TypeValueError("Duplicate choice in: %s." % values)
    return values
