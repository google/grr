#!/usr/bin/env python
"""A module with utilities for dealing with context managers."""
from collections.abc import Sequence
import contextlib
from typing import Generic, TypeVar

_T = TypeVar("_T")


class MultiContext(
    contextlib.AbstractContextManager[Sequence[_T]], Generic[_T]
):
  """A context managers that sequences multiple context managers.

  This is similar to the monadic `sequence` operator: it takes a list of context
  managers, enters each of them and yields list of values that the managers
  yield.

  One possible scenario where this class comes in handy is when one needs to
  open multiple files.
  """

  def __init__(
      self, managers: Sequence[contextlib.AbstractContextManager[_T]]
  ) -> None:
    self._managers = managers

  def __enter__(self) -> Sequence[_T]:
    values = []
    for manager in self._managers:
      value = manager.__enter__()
      values.append(value)
    return values

  def __exit__(self, exc_type, exc_value, traceback):
    for manager in self._managers:
      manager.__exit__(exc_type, exc_value, traceback)
