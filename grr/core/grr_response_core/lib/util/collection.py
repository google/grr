#!/usr/bin/env python
"""A module with utility functions for working with collections."""

import itertools
from typing import Callable, Dict, Iterable, Iterator, List, Tuple, TypeVar

T = TypeVar("T")
K = TypeVar("K")


def Flatten(iterator: Iterable[Iterable[T]]) -> Iterator[T]:
  """Flattens nested iterables into one iterator.

  Examples:
    >>> list(Flatten([[1, 2, 3], [4, 5, 6]]))
    [1, 2, 3, 4, 5, 6]

    >>> list([range(3), range(5), range(3)])
    [0, 1, 2, 0, 1, 2, 3, 4, 0, 1, 2]

  Args:
    iterator: An iterator of iterators to flatten.

  Yields:
    Items yielded by the given iterators.
  """
  for items in iterator:
    for item in items:
      yield item


def Trim(lst: List[T], limit: int) -> List[T]:
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


def Group(items: Iterable[T], key: Callable[[T], K]) -> Dict[K, T]:
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


def Batch(items: Iterable[T], size: int) -> Iterator[List[T]]:
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


def StartsWith(this: Iterable[T], that: Iterable[T]) -> bool:
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


def Unzip(iterable: Iterable[Tuple[K, T]]) -> Tuple[Iterable[K], Iterable[T]]:
  """Unzips specified iterable of pairs to pair of two iterables.

  This function is an inversion of the standard `zip` function and the following
  hold:

    * ∀ l, r. l, r == unzip(zip(l, r))
    * ∀ p. p == zip(unzip(p))

  Examples:
    >>> Unzip([("foo", 1), ("bar", 2), ("baz", 3)])
    (["foo", "bar", "baz"], [1, 2, 3])

  Args:
    iterable: An iterable of pairs to unzip.

  Returns:
    A pair of iterables after unzipping.
  """
  lefts = []
  rights = []

  for left, right in iterable:
    lefts.append(left)
    rights.append(right)

  return lefts, rights


def DictProduct(dictionary: Dict[K, Iterable[T]]) -> Iterator[Dict[K, T]]:
  """Computes a cartesian product of dict with iterable values.

  This utility function, accepts a dictionary with iterable values, computes
  cartesian products of these values and yields dictionaries of expanded values.

  Examples:
    >>> list(DictProduct({"a": [1, 2], "b": [3, 4]}))
    [{"a": 1, "b": 3}, {"a": 1, "b": 4}, {"a": 2, "b": 3}, {"a": 2, "b": 4}]

  Args:
    dictionary: A dictionary with iterable values.

  Yields:
    Dictionaries with values being a result of cartesian product of values of
    the input dictionary.
  """
  keys, values = Unzip(dictionary.items())
  for product_values in itertools.product(*values):
    yield dict(zip(keys, product_values))
