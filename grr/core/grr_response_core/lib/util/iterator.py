#!/usr/bin/env python
"""A module with utilities for working with iterators."""
from typing import Iterator
from typing import TypeVar

_T = TypeVar("_T")


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
