#!/usr/bin/env python
"""A module with utilities for dealing with context managers."""
from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals


class NullContext(object):
  """A context manager that always yields provided values.

  This class is useful for providing context-like semantics for values that are
  not context managers themselves because they do not need to manage any
  resources but are used as context managers.

  This is a backport of the `contextlib.nullcontext` class introduced in Python
  3.7. Once support for old versions of Python is dropped, all uses of this
  class should be replaced with the one provided by the standard library.
  """

  def __init__(self, value):
    self._value = value

  def __enter__(self):
    return self._value

  def __exit__(self, exc_type, exc_value, traceback):
    del exc_type, exc_value, traceback  # Unused.


class MultiContext(object):
  """A context managers that sequences multiple context managers.

  This is similar to the monadic `sequence` operator: it takes a list of context
  managers, enters each of them and yields list of values that the managers
  yield.

  One possible scenario where this class comes in handy is when one needs to
  open multiple files.
  """

  def __init__(self, managers):
    self._managers = managers

  def __enter__(self):
    values = []
    for manager in self._managers:
      value = manager.__enter__()
      values.append(value)
    return values

  def __exit__(self, exc_type, exc_value, traceback):
    for manager in self._managers:
      manager.__exit__(exc_type, exc_value, traceback)
