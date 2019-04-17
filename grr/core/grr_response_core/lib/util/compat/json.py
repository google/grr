#!/usr/bin/env python
"""A module with compatibility wrappers for JSON processing."""
from __future__ import absolute_import
from __future__ import division

from __future__ import unicode_literals

import io
import json

from typing import Any
from typing import IO
from typing import Optional
from typing import Text
from typing import Type

from grr_response_core.lib.util import compatibility
from grr_response_core.lib.util import precondition

Decoder = json.JSONDecoder
Encoder = json.JSONEncoder


def Parse(text):
  """Parses a JSON source into a Python object.

  Args:
    text: A JSON source to parse.

  Returns:
    A Python data structure corresponding to the JSON source.
  """
  precondition.AssertType(text, Text)
  return json.loads(text)


def ReadFromFile(filedesc):
  """Reads a Python object from given file descriptor.

  Args:
    filedesc: A descriptor of the file to read the JSON contents from.

  Returns:
    A Python data structure corresponding to the JSON in the given file.
  """
  content = filedesc.read()
  return Parse(content)


def ReadFromPath(filepath):
  """Reads a Python object stored in a JSON under a specified filepath.

  Args:
    filepath: A filepath to the JSON file.

  Returns:
    A Python data structure corresponding to the JSON in the given file.
  """
  with io.open(filepath, mode="r", encoding="utf-8") as filedesc:
    return ReadFromFile(filedesc)


if compatibility.PY2:
  _SEPARATORS = (b",", b": ")
else:
  _SEPARATORS = (",", ": ")


def Dump(obj,
         sort_keys = False,
         encoder = None):
  """Stringifies a Python object into its JSON representation.

  Args:
    obj: A Python object to convert to JSON.
    sort_keys: If True, output dictionaries keys in sorted (ascending) order.
    encoder: An (optional) encoder class to use.

  Returns:
    A JSON representation of the given object.
  """
  # Python 2 json.dumps expects separators as a tuple of bytes, while
  # Python 3 expects them to be a tuple of unicode strings. Pytype
  # is too dumb to infer the result of the if statement that sets
  # _SEPARATORS and complains when running in Python 3 mode.
  text = json.dumps(
      obj,
      indent=2,
      sort_keys=sort_keys,
      ensure_ascii=False,
      cls=encoder,
      separators=_SEPARATORS)  # pytype: disable=wrong-arg-types

  # `text` is an instance of `bytes` if the object to serialize does not contain
  # any unicode characters, otherwise it is `unicode`. See [1] for details.
  #
  # [1]: https://bugs.python.org/issue13769
  if compatibility.PY2 and isinstance(text, bytes):
    text = text.decode("utf-8")  # pytype: disable=attribute-error

  return text
