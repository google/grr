#!/usr/bin/env python
"""A module with utilities for maintaining compatibility with Python 2 and 3."""

from collections import abc
import os
import shlex
import sys
import time
import types
from typing import Any
from typing import Dict
from typing import List
from typing import Optional
from typing import Text
from typing import Tuple
from typing import Type
from typing import TypeVar
from typing import Union

from grr_response_core.lib.util import precondition

T = TypeVar("T")

# TODO(hanuszczak): According to pytype, `sys.version_info` is a tuple of two
# elements which is not true.
# pytype: disable=attribute-error
PY2 = sys.version_info.major == 2

# pytype: enable=attribute-error


def NativeStr(obj):
  """A compatibility wrapper for returning native string representation.

  Args:
    obj: An object for which we want a string representation.

  Returns:
    A native string representation of given object.
  """
  return str(obj)


def Repr(obj) -> Text:
  """A variant of the `repr` builtin that always returns unicode objects.

  Note that this function does not guarantee that the output is the same in both
  Python versions. In particular, string representations for unicodes are
  prefixed with 'u' in Python 2 but they are not in Python 3.

  Args:
    obj: An object to get the representation for.

  Returns:
    A human-readable representation of given object.
  """
  return "{!r}".format(obj)


def GetName(obj) -> Text:
  """A compatibility wrapper for getting the name of an object or function.

  In Python 2 names are returned as `bytes` (since names can contain only ASCII
  characters) whereas in Python 3 they are `unicode` (since names can contain
  arbitrary unicode characters).

  This function makes this behaviour consistent and always returns the name as
  a unicode string.

  Once support for Python 2 is dropped all invocations of this call can be
  replaced with ordinary `__name__` access.

  Args:
    obj: A type or function object to get the name for.

  Returns:
    Name of the specified object as unicode string.
  """
  precondition.AssertType(obj, (type, types.FunctionType, types.MethodType))

  if PY2:
    return obj.__name__.decode("ascii")
  else:
    return obj.__name__


def SetName(obj, name: Text):
  """A compatibility wrapper for setting object's name.

  See documentation for `GetName` for more information.

  Args:
    obj: A type or function object to set the name for.
    name: A name to set.
  """
  # Not doing type assertion on obj, since it may be a mock object used
  # in tests.
  precondition.AssertType(name, str)

  if PY2:
    obj.__name__ = name.encode("ascii")
  else:
    obj.__name__ = name


def ListAttrs(cls: type) -> List[Text]:
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


def MakeType(name: Text, base_classes: Tuple[Type[Any], ...],
             namespace: Dict[Text, Any]) -> Type[Any]:
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


def FormatTime(fmt: Text, stime: Optional[time.struct_time] = None) -> Text:
  """A compatibility wrapper for the `strftime` function.

  It is guaranteed to always take unicode string as an argument and return an
  unicode string as a result.

  Args:
    fmt: A format string specifying formatting of the output.
    stime: A time representation as returned by `gmtime` or `localtime`.

  Returns:
    A human-readable representation of `stime`.
  """
  precondition.AssertType(fmt, str)
  precondition.AssertOptionalType(stime, time.struct_time)

  # TODO(hanuszczak): https://github.com/google/pytype/issues/127
  # pytype: disable=wrong-arg-types
  # We need this because second parameter is not a keyword argument, so method
  # must be explicitly called with or without it.
  if stime is None:
    strftime = time.strftime
  else:
    strftime = lambda fmt: time.strftime(fmt, stime)

  if PY2:
    return strftime(fmt.encode("ascii")).decode("ascii")
  else:
    return strftime(fmt)
  # pytype: enable=wrong-arg-types


def ShlexSplit(string: Text) -> List[Text]:
  """A wrapper for `shlex.split` that works with unicode objects.

  Args:
    string: A unicode string to split.

  Returns:
    A list of unicode strings representing parts of the input string.
  """
  precondition.AssertType(string, Text)

  if PY2:
    string = string.encode("utf-8")

  parts = shlex.split(string)

  if PY2:
    # TODO(hanuszczak): https://github.com/google/pytype/issues/127
    # pytype: disable=attribute-error
    parts = [part.decode("utf-8") for part in parts]
    # pytype: enable=attribute-error

  return parts


def UnescapeString(string: Text) -> Text:
  """A wrapper for `decode("string_escape")` that works in Python 3.

  Args:
    string: A string with escaped characters to unescape.

  Returns:
    An unescaped version of the input string.
  """
  precondition.AssertType(string, Text)
  return string.encode("utf-8").decode("unicode_escape")


def Environ(variable: Text, default: T) -> Union[Text, T]:
  """A wrapper for `os.environ.get` that works the same way in both Pythons.

  Args:
    variable: A name of the variable to get the value of.
    default: A default value to return in case no value for the given variable
      is set.

  Returns:
    An environment value of the given variable.
  """
  precondition.AssertType(variable, Text)

  value = os.environ.get(variable, default)
  if value is None:
    return default
  if PY2:
    # TODO(hanuszczak): https://github.com/google/pytype/issues/127
    value = value.decode("utf-8")  # pytype: disable=attribute-error
  return value


def UnicodeJson(json: Any) -> Any:
  """Converts given JSON-like Python object to one without byte strings.

  In some cases when a dictionary is deserialized from some Python 2-specific
  source, it will contain byte strings. This function fixes such cases by making
  sure that string objects insite are unicode strings.

  Note that this function will perform a deep copy of the given object.

  Args:
    json: A JSON-like object.

  Returns:
    A JSON object with all byte-strings interpreted as unicode strings.

  Raises:
    TypeError: If given value is not a JSON-like object.
  """
  if isinstance(json, list):
    return list(map(UnicodeJson, json))

  if isinstance(json, dict):
    result = {}
    for key, value in json.items():
      result[UnicodeJson(key)] = UnicodeJson(value)
    return result

  if isinstance(json, bytes):
    return json.decode("utf-8")

  # Only allowed iterables are dictionaries, list and strings.
  if isinstance(json, abc.Iterable) and not isinstance(json, Text):
    raise TypeError("Incorrect JSON object: {!r}".format(json))

  return json
