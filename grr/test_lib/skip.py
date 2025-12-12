#!/usr/bin/env python
"""A module with utility decorators for skipping tests."""

from collections.abc import Callable
import functools
import types
from typing import Any, Union
import unittest


def If(condition: Union[Any, Callable[[], Any]], reason: str):
  """A decorator that skips test evaluation if the condition holds.

  This decorator can be applied either to a test method or a test class (in
  which case, all test methods are going to be skipped if necessary).

  Unlike `unittest.skipIf`, this decorator can also bo provided with a function
  that is not evaluated until the test actually runs. This is useful if the
  condition cannot be determined at the time the module is loaded.

  Args:
    condition: If true, the test is going to be skipped.
    reason: A reason why the test needed to be skipped.

  Returns:
    A decorator that can be applied to test methods or classes.
  """
  if callable(condition):
    return _IfLazy(condition, reason)
  else:
    return unittest.skipIf(condition, reason)


def Unless(condition: Union[Any, Callable[[], Any]], reason: str):
  """A decorator that skips test evaluation if the condition dot not hold.

  See documentation for the `If` decorator for more information.

  Args:
    condition: If false, the test is going to be skipped.
    reason: A reason why the test needed to be skipped.

  Returns:
    A decorator that can be applied to test method or classes.
  """
  if callable(condition):
    return _UnlessLazy(condition, reason)
  else:
    return unittest.skipUnless(condition, reason)


def _IfLazy(condition: Callable[[], Any], reason: str):
  """A decorator that skips test evaluation if the condition holds.

  Args:
    condition: If true, the test is going to be skipped.
    reason: A reason why the test needed to be skipped.

  Returns:
    A decorator that can be applied to test methods or classes.
  """

  def Decorator(test):
    if isinstance(test, type):

      cls_wrapper = type(test.__name__, test.__bases__, dict(test.__dict__))

      def __init__(self, method_name):  # pylint: disable=invalid-name
        super(cls_wrapper, self).__init__(method_name)

        method = getattr(self, method_name)
        setattr(self, method_name, _IfLazy(condition, reason)(method))

      cls_wrapper.__init__ = __init__

      return cls_wrapper

    if isinstance(test, (types.FunctionType, types.MethodType)):

      @functools.wraps(test)
      def MethodWrapper(*args, **kwargs):
        if condition():
          raise unittest.SkipTest(reason)

        return test(*args, **kwargs)

      return MethodWrapper

    raise TypeError("Unexpected test type: {}".format(type(test)))

  return Decorator


def _UnlessLazy(condition: Callable[[], Any], reason: str):
  return _IfLazy(lambda: not condition(), reason)
