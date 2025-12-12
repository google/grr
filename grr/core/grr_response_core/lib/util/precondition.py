#!/usr/bin/env python
"""A module with assertion functions for checking preconditions."""

import collections
from collections import abc
from collections.abc import Sized
import re


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
  if isinstance(iterable, collections.abc.Iterator):
    message = "Expected iterable container but got iterator `%s` instead"
    message %= iterable
    raise TypeError(message)

  AssertType(iterable, abc.Iterable)
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
  AssertType(dct, abc.Mapping)
  for key, value in dct.items():
    AssertType(key, expected_key_type)
    AssertType(value, expected_value_type)


def AssertNotEmpty(typename, value):
  """Raises, if the given value is empty or has no __len__."""
  AssertType(value, Sized)
  if len(value) == 0:  # pylint: disable=g-explicit-length-test
    message = "Expected {} `{}` to be non-empty".format(typename, value)
    raise ValueError(message)


def _ValidateStringId(typename, value):
  AssertType(value, str)
  AssertNotEmpty(typename, value)


def ValidateClientId(client_id):
  """Raises, if the given value is not a valid ClientId string."""
  _ValidateStringId("client_id", client_id)
  # TODO(hanuszczak): Eventually, we should allow only either lower or upper
  # case letters in the client id.
  if re.match(r"^C\.[0-9a-fA-F]{16}$", client_id) is None:
    raise ValueError("Client id has incorrect format: `%s`" % client_id)


def ValidateFlowId(flow_id):
  """Raises, if the given value is not a valid FlowId string."""
  _ValidateStringId("flow_id", flow_id)
  if (
      len(flow_id) not in [8, 16]
      or re.match(r"^[0-9a-fA-F]*$", flow_id) is None
  ):
    raise ValueError("Flow id has incorrect format: `%s`" % flow_id)
