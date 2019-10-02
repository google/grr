#!/usr/bin/env python
"""Utility functions for working with text representation of objects."""
from __future__ import absolute_import
from __future__ import division

from __future__ import unicode_literals

import binascii

from typing import Text

from grr_response_core.lib.util import compatibility
from grr_response_core.lib.util import precondition


def Asciify(data):
  """Turns given bytes to human-readable ASCII representation.

  All ASCII-representable bytes are turned into proper characters, whereas all
  other characters use escape sequences.

  Args:
    data: A byte sequence to convert.

  Returns:
    A human-readable representation of the given sequence.
  """
  precondition.AssertType(data, bytes)

  if compatibility.PY2:
    return repr(data).decode("utf-8")[1:-1]  # pytype: disable=attribute-error
  else:
    return repr(data)[2:-1]


def Hexify(data):
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
