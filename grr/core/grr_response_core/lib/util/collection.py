#!/usr/bin/env python
"""A module with utility functions for working with collections."""
from __future__ import absolute_import
from __future__ import division

from __future__ import unicode_literals

from typing import Callable, Dict, Iterable, Iterator, List, TypeVar

T = TypeVar("T")
K = TypeVar("K")


def Trim(lst, limit):
  """Trims a given list so that it is not longer than given limit.

  Args:
    lst: A list to trim.
    limit: A maximum number of elements in the list after trimming.

  Returns:
    A suffix of the input list that was trimmed.
  """
  limit = max(0, limit)

  clipping = lst[limit:]
  del lst[limit:]
  return clipping


def Group(items, key):
  """Groups items by given key function.

  Args:
    items: An iterable or an iterator of items.
    key: A function which given each item will return the key.

  Returns:
    A dict with keys being each unique key and values being a list of items of
    that key.
  """
  result = {}

  for item in items:
    result.setdefault(key(item), []).append(item)

  return result


def Batch(items, size):
  """Divide items into batches of specified size.

  In case where number of items is not evenly divisible by the batch size, the
  last batch is going to be shorter.

  Args:
    items: An iterable or an iterator of items.
    size: A size of the returned batches.

  Yields:
    Lists of items with specified size.
  """
  batch = []

  for item in items:
    batch.append(item)
    if len(batch) == size:
      yield batch
      batch = []

  if batch:
    yield batch


def StartsWith(this, that):
  """Checks whether an items of one iterable are a prefix of another.

  Args:
    this: An iterable that needs to be checked.
    that: An iterable of which items must match the prefix of `this`.

  Returns:
    `True` if `that` is a prefix of `this`, `False` otherwise.
  """
  this_iter = iter(this)
  that_iter = iter(that)

  while True:
    try:
      this_value = next(that_iter)
    except StopIteration:
      return True

    try:
      that_value = next(this_iter)
    except StopIteration:
      return False

    if this_value != that_value:
      return False
