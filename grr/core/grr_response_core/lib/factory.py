#!/usr/bin/env python
"""A module with definition of factory."""

from typing import Callable
from typing import Dict
from typing import Generic
from typing import Iterator
from typing import Optional
from typing import Text
from typing import Type
from typing import TypeVar

from grr_response_core.lib.util import precondition


T = TypeVar("T")


class _FactoryEntry(Generic[T]):

  def __init__(self, cls: Type[T], constructor: Callable[[], T]):
    self.cls = cls
    self.constructor = constructor


class Factory(Generic[T]):
  """An instance factory class.

  This class is an alternative to the metaclass registries and problems that
  they introduce. With factories, all classes have to be explicitly registered
  first so that ensures that all imports are present. They also do not contain
  any Python magic and are far easier to read and debug.

  Factories also make testing much more predictable as by default factories
  have no classes registered. If a need arises, it is very easy to add custom
  instances that are relevant for the test.
  """

  def __init__(self, cls: Type[T]):
    """Initializes the factory.

    Args:
      cls: The type of produced instances.
    """
    self._cls: Type[T] = cls
    self._entries: Dict[str, _FactoryEntry[T]] = {}

  def Register(self,
               name: Text,
               cls: Type[T],
               constructor: Optional[Callable[[], T]] = None):
    """Registers a new constructor in the factory.

    Args:
      name: A name associated with given constructor.
      cls: The type to register under the name.
      constructor: Optional, a custom function that creates an instance of the
        cls type. If None, the class constructor is used.

    Raises:
      ValueError: If there already is a constructor associated with given name.
    """
    precondition.AssertType(name, Text)

    if name in self._entries:
      message = "Duplicated constructors %r and %r for name '%s'"
      message %= (constructor, self._entries[name], name)
      raise ValueError(message)

    if constructor is None:
      constructor = cls  # Use class constructor if no custom function is given.

    self._entries[name] = _FactoryEntry(cls, constructor)

  def Unregister(self, name: Text):
    """Unregisters a constructor.

    Args:
      name: A name of the constructor to unregister.

    Raises:
      ValueError: If constructor with specified name has never been registered.
    """
    precondition.AssertType(name, Text)

    try:
      del self._entries[name]
    except KeyError:
      raise ValueError("Constructor with name '%s' is not registered" % name)

  def Create(self, name: Text) -> T:
    """Creates a new instance.

    Args:
      name: A name identifying the constructor to use for instantiation.

    Returns:
      An instance of the type that the factory supports.
    """
    precondition.AssertType(name, Text)

    try:
      constructor = self._entries[name].constructor
    except KeyError:
      message = "No constructor for name '%s' has been registered"
      message %= name
      raise ValueError(message)

    return constructor()

  def CreateAll(self) -> Iterator[T]:
    """Creates instances using all registered constructors."""
    for name in self.Names():
      yield self.Create(name)

  def GetType(self, name: Text) -> Type[T]:
    """Returns the class registered under the given name."""
    try:
      return self._entries[name].cls
    except KeyError:
      raise ValueError(f"No class has been registered for name {name}")

  def GetTypes(self) -> Iterator[Type[T]]:
    """Yields all classes that have been registered."""
    for name in self.Names():
      yield self.GetType(name)

  def Names(self) -> Iterator[Text]:
    """Yields all names that have been registered with this factory."""
    return iter(self._entries.keys())
