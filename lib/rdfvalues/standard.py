#!/usr/bin/env python
"""Standard RDFValues."""


import re
from grr.lib import rdfvalue
from grr.lib import type_info


class RegularExpression(rdfvalue.RDFString):
  """A semantic regular expression."""

  def ParseFromString(self, value):
    super(RegularExpression, self).ParseFromString(value)

    # Check that this is a valid regex.
    try:
      self._regex = re.compile(str(self), flags=re.I | re.S | re.M)
    except re.error:
      raise type_info.TypeValueError("Not a valid regular expression.")

  def Search(self, text):
    """Search the text for our value."""
    return self._regex.search(text)

  def Match(self, text):
    return self._regex.match(text)

  def FindIter(self, text):
    return self._regex.finditer(text)
