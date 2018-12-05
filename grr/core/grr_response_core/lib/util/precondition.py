#!/usr/bin/env python
"""A module with assertion functions for checking preconditions."""
from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

import collections

from future.utils import iteritems


def AssertType(value, expected_type):
  """Ensures that given value has certain type.

  Args:
    value: A value to assert the type for.
    expected_type: An expected type for the given value.

  Raises:
    TypeError: If given value does not have the expected type.
  """
  if not isinstance(value, expected_type):
    message = "Expected type `%r`, but got value `%r` of type `%s`"
    message %= (expected_type, value, type(value))
    raise TypeError(message)


def AssertOptionalType(value, expected_type):
  """Ensures that given value, if not `None`, has certain type.

  Args:
    value: A value or `None` to assert the type for.
    expected_type: An expected type for the given value.

  Raises:
    TypeError: If given value is not `None` and does not have the expected type.
  """
  if value is not None:
    AssertType(value, expected_type)


def AssertIterableType(iterable, expected_item_type):
  """Ensures that given iterable container has certain type.

  Args:
    iterable: An iterable container to assert the type for.
    expected_item_type: An expected type of the container items.

  Raises:
    TypeError: If given container does is not an iterable or its items do not
               have the expected type.
  """
  # We do not consider iterators to be iterables even though Python does. An
  # "iterable" should be a type that can be iterated (that is: an iterator can
  # be constructed for them). Iterators should not be considered to be iterable
  # because it makes no sense to construct an iterator for iterator. The most
  # important practical implication is that act of iterating an iterator drains
  # it whereas act of iterating the iterable does not.
  if isinstance(iterable, collections.Iterator):
    message = "Expected iterable container but got iterator `%s` instead"
    message %= iterable
    raise TypeError(message)

  AssertType(iterable, collections.Iterable)
  for item in iterable:
    AssertType(item, expected_item_type)


def AssertDictType(dct, expected_key_type, expected_value_type):
  """Ensures that given dictionary is actually a dictionary of specified type.

  Args:
    dct: A dictionary to assert the type for.
    expected_key_type: An expected type for dictionary keys.
    expected_value_type: An expected type for dictionary values.

  Raises:
    TypeError: If given dictionary is not really a dictionary or not all its
               keys and values have the expected type.
  """
  AssertType(dct, dict)
  for key, value in iteritems(dct):
    AssertType(key, expected_key_type)
    AssertType(value, expected_value_type)
