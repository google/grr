#!/usr/bin/env python
"""A module with utilities for working with iterators."""

from collections.abc import Iterator
from typing import Optional, TypeVar

_T = TypeVar("_T")


class NoYieldsError(ValueError):
  """An error raised when assuming single item on empty iterators."""


class TooManyYieldsError(ValueError):
  """An error raised when assuming single item on multi-yield iterators."""


def AssumeSingle(items: Iterator[_T]) -> _T:
  """Retrieves a result from a single-yield iterator.

  Args:
    items: An iterator that is expected to yield a single value.

  Returns:
    The only value this iterator yields.

  Raises:
    NoYieldsError: If `iterator` yields no items (instead of one).
    TooManyYieldsError: If `iterator` yields many items (instead of one).
  """
  try:
    result = next(items)
  except StopIteration:
    raise NoYieldsError()

  try:
    next(items)
    raise TooManyYieldsError()
  except StopIteration:
    pass

  return result


class Counted(Iterator[_T]):
  """An iterator wrapper that counts number of iterated items."""

  def __init__(self, inner: Iterator[_T]) -> None:
    """Initializes the wrapper.

    Args:
      inner: An iterator to wrap.
    """
    super().__init__()

    self._inner: Iterator[_T] = inner
    self._count: int = 0

  def __iter__(self) -> Iterator[_T]:
    return self

  def __next__(self) -> _T:
    item = next(self._inner)
    self._count += 1

    return item

  @property
  def count(self) -> int:
    """Retrieves the number of iterated items of the wrapped iterator."""
    return self._count

  def Reset(self) -> None:
    """Resets the counter."""
    self._count = 0


class Lookahead(Iterator[_T]):
  """An iterator wrapper that allows to peek at items without consuming them."""

  def __init__(self, inner: Iterator[_T]) -> None:
    """Initializes the wrapper.

    Args:
      inner: An iterator to wrap.
    """
    super().__init__()

    self._inner: Iterator[_T] = inner

    self._item: Optional[_T] = None
    self._done: bool = False

    self._Pull()

  def __iter__(self) -> Iterator[_T]:
    return self

  def __next__(self) -> _T:
    if self.done:
      raise StopIteration()

    # Because of the `self.done` check, `result` is guaranteed to be set to some
    # value pulled from the iterator. Ideally, we would like to assert that it
    # is not `None` but this is not possible as some iterators might yield it as
    # a completely legitimate value.
    result = self.item

    self._Pull()

    return result

  @property
  def item(self) -> _T:
    """Retrieves the current item from the iterator."""
    if self.done:
      raise ValueError("No more items available")

    return self._item

  @property
  def done(self) -> bool:
    """Checks whether the iterator has already yielded all items."""
    return self._done

  def _Pull(self) -> None:
    """Pulls the next item from the iterator."""
    try:
      self._item = next(self._inner)
    except StopIteration:
      self._done = True
