#!/usr/bin/env python
"""A module with utilities for maintaining compatibility with Python 2 and 3."""
from __future__ import absolute_import
from __future__ import division

from __future__ import unicode_literals

import sys
import types

from future.builtins import str
from typing import List
from typing import Text
from typing import Tuple

from grr_response_core.lib.util import precondition


# TODO(hanuszczak): According to pytype, `sys.version_info` is a tuple of two
# elements which is not true.
# pytype: disable=attribute-error
PY2 = sys.version_info.major == 2

# pytype: enable=attribute-error


def GetName(obj):
  """A compatibility wrapper for getting object's name.

  In Python 2 class names are returned as `bytes` (since class names can contain
  only ASCII characters) whereas in Python 3 they are `unicode` (since class
  names can contain arbitrary unicode characters).

  This function makes this behaviour consistent and always returns class name as
  an unicode string.

  Once support for Python 2 is dropped all invocations of this call can be
  replaced with ordinary `__name__` access.

  Args:
    obj: A type or function object to get the name for.

  Returns:
    Name of the specified class as unicode string.
  """
  precondition.AssertType(obj, (type, types.FunctionType))

  if PY2:
    return obj.__name__.decode("ascii")
  else:
    return obj.__name__


def SetName(obj, name):
  """A compatibility wrapper for setting object's name.

  See documentation for `GetName` for more information.

  Args:
    obj: A type or function object to set the name for.
    name: A name to set.
  """
  precondition.AssertType(obj, (type, types.FunctionType))
  precondition.AssertType(name, str)

  if PY2:
    obj.__name__ = name.encode("ascii")
  else:
    obj.__name__ = name


def ListAttrs(cls):
  """A compatibility wrapper for listing class attributes.

  This method solves similar Python 2 compatibility issues for `dir` function as
  `GetName` does for `__name__` invocations. See documentation for `GetName` for
  more details.

  Once support for Python 2 is dropped all invocations of this function should
  be replaced with ordinary `dir` calls.

  Args:
    cls: A class object to list the attributes for.

  Returns:
    A list of attribute names as unicode strings.
  """
  precondition.AssertType(cls, type)

  if PY2:
    # TODO(user): once https://github.com/google/pytype/issues/127 is fixed,
    # pytype should be able to tell that this line is unreachable in py3.
    return [item.decode("ascii") for item in dir(cls)]  # pytype: disable=attribute-error
  else:
    return dir(cls)


def MakeType(name, base_classes, namespace):
  """A compatibility wrapper for the `type` built-in function.

  In Python 2 `type` (used as a type constructor) requires the name argument to
  be a `bytes` object whereas in Python 3 it is required to be an `unicode`
  object. Since class name is human readable text rather than arbitrary stream
  of bytes, the Python 3 behaviour is considered to be the sane one.

  Once support for Python 2 is dropped all invocations of this call can be
  replaced with the `type` built-in.

  Args:
    name: A name of the type to create.
    base_classes: A tuple of base classes that the returned type is supposed to
      derive from.
    namespace: A dictionary of methods and fields that the returned type is
      supposed to contain.

  Returns:
    A new type with specified parameters.
  """
  precondition.AssertType(name, str)

  if PY2:
    name = name.encode("ascii")

  return type(name, base_classes, namespace)
