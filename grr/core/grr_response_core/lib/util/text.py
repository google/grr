#!/usr/bin/env python
"""Utility functions for working with text representation of objects."""

import binascii

from typing import Text

from grr_response_core.lib.util import precondition


def Asciify(data: bytes) -> Text:
  """Turns given bytes to human-readable ASCII representation.

  All ASCII-representable bytes are turned into proper characters, whereas all
  other characters use escape sequences.

  Args:
    data: A byte sequence to convert.

  Returns:
    A human-readable representation of the given sequence.
  """
  precondition.AssertType(data, bytes)

  return repr(data)[2:-1]


def Hexify(data: bytes) -> Text:
  """Turns given bytes to its hex representation.

  It works just like `binascii.hexlify` but always returns string objects rather
  than bytes. It also fixes the name of this function to avoid awkward "l".

  Args:
    data: A byte sequence to convert.

  Returns:
    A hex representation of the given data.
  """
  precondition.AssertType(data, bytes)
  return binascii.hexlify(data).decode("ascii")


def Unescape(string: str) -> str:
  """Evaluates string with escape sequences.

  Args:
    string: A string with escaped characters to unescape.

  Returns:
    An unescaped version of the input string.
  """
  precondition.AssertType(string, Text)
  return string.encode("utf-8").decode("unicode_escape")
