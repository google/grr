#!/usr/bin/env python
"""A module with a backport of Python 2 fnmatch logic."""

from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

import re


# NOTE: this is copied from Python 2 source code to ensure compatibility
# with legacy Python 2 clients.
#
# See https://github.com/python/cpython/blob/2.7/Lib/fnmatch.py
#
# Python 3 has a few regex extensions not supported by Python 2. We do send
# regexes to clients, so we have to make sure Python-3-produced regexes
# are recognized by Python 2 clients.
def translate(pat):
  """Translate a shell PATTERN to a regular expression."""

  i, n = 0, len(pat)
  res = ''
  while i < n:
    c = pat[i]
    i = i + 1
    if c == '*':
      res = res + '.*'
    elif c == '?':
      res = res + '.'
    elif c == '[':
      j = i
      if j < n and pat[j] == '!':
        j = j + 1
      if j < n and pat[j] == ']':
        j = j + 1
      while j < n and pat[j] != ']':
        j = j + 1
      if j >= n:
        res = res + '\\['
      else:
        stuff = pat[i:j].replace('\\', '\\\\')
        i = j + 1
        if stuff[0] == '!':
          stuff = '^' + stuff[1:]
        elif stuff[0] == '^':
          stuff = '\\' + stuff
        res = '%s[%s]' % (res, stuff)
    else:
      res = res + re.escape(c)

  # Here the original 2.7 code is changed to put the regular expression
  # flags (?ms) in front. In the original implementation they were appended
  # to the back of the expression.
  return r'(?ms)%s\Z' % res
