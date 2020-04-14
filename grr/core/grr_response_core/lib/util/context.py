#!/usr/bin/env python
# Lint as: python3
"""A module with utilities for dealing with context managers."""
from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

from typing import ContextManager
from typing import Generic
from typing import Sequence
from typing import TypeVar

_T = TypeVar("_T")


class NullContext(ContextManager[_T], Generic[_T]):
  """A context manager that always yields provided values.

  This class is useful for providing context-like semantics for values that are
  not context managers themselves because they do not need to manage any
  resources but are used as context managers.

  This is a backport of the `contextlib.nullcontext` class introduced in Python
  3.7. Once support for old versions of Python is dropped, all uses of this
  class should be replaced with the one provided by the standard library.
  """

  def __init__(self, value: _T) -> None:
    self._value = value

  def __enter__(self) -> _T:
    return self._value

  def __exit__(self, exc_type, exc_value, traceback):
    del exc_type, exc_value, traceback  # Unused.


class MultiContext(ContextManager[Sequence[_T]], Generic[_T]):
  """A context managers that sequences multiple context managers.

  This is similar to the monadic `sequence` operator: it takes a list of context
  managers, enters each of them and yields list of values that the managers
  yield.

  One possible scenario where this class comes in handy is when one needs to
  open multiple files.
  """

  # TODO: `Collection` would be a better type here, but it is only
  # available in Python 3.6+. Once support for Python 2 is dropped, this can be
  # generalized.
  def __init__(self, managers: Sequence[ContextManager[_T]]) -> None:
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
