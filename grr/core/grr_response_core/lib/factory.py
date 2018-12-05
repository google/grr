#!/usr/bin/env python
"""A module with definition of factory."""
from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

from future.utils import iterkeys

from grr_response_core.lib.util import precondition


class Factory(object):
  """An instance factory class.

  This class is an alternative to the metaclass registries and problems that
  they introduce. With factories, all classes have to be explicitly registered
  first so that ensures that all imports are present. They also do not contain
  any Python magic and are far easier to read and debug.

  Factories also make testing much more predictable as by default factories
  have no classes registered. If a need arises, it is very easy to add custom
  instances that are relevant for the test.
  """

  def __init__(self, cls):
    """Initializes the factory.

    Args:
      cls: The type of produced instances.
    """
    self._cls = cls
    self._constructors = {}

  def Register(self, name, constructor):
    """Registers a new constructor in the factory.

    Args:
      name: A name associated with given constructor.
      constructor: A constructor function that creates instances.

    Raises:
      ValueError: If there already is a constructor associated with given name.
    """
    precondition.AssertType(name, unicode)

    if name in self._constructors:
      message = "Duplicated constructors %r and %r for name '%s'"
      message %= (constructor, self._constructors[name], name)
      raise ValueError(message)

    self._constructors[name] = constructor

  def Unregister(self, name):
    """Unregisters a constructor.

    Args:
      name: A name of the constructor to unregister.

    Raises:
      ValueError: If constructor with specified name has never been registered.
    """
    precondition.AssertType(name, unicode)

    try:
      del self._constructors[name]
    except KeyError:
      raise ValueError("Constructor with name '%s' is not registered" % name)

  def Create(self, name):
    """Creates a new instance.

    Args:
      name: A name identifying the constructor to use for instantiation.

    Returns:
      An instance of the type that the factory supports.
    """
    precondition.AssertType(name, unicode)

    try:
      constructor = self._constructors[name]
    except KeyError:
      message = "No constructor for name '%s' has been registered"
      message %= name
      raise ValueError(message)

    instance = constructor()
    if not isinstance(instance, self._cls):
      message = ("Constructor %r for name '%s' returned instance of type %r "
                 "(expected %r)")
      message %= (constructor, name, type(instance), self._cls)
      raise TypeError(message)

    return instance

  def CreateAll(self):
    """Creates instances using all registered constructors."""
    for name in self.Names():
      yield self.Create(name)

  def Names(self):
    """Yields all names that have been registered with this factory."""
    return iterkeys(self._constructors)
