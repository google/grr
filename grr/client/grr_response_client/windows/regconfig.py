#!/usr/bin/env python
"""A registry based configuration parser."""

# NOTE: Running a 32 bit compiled client and 64 bit compiled client on a 64 bit
# system will run both clients on _DIFFERENT_ hives according to the WOW64
# scheme. This means that GRR will appear to have different clients for the same
# system. The clients will not share their config keys if the registry keys they
# use are hooked by WOW64.

from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

import collections
import logging

from future.moves import winreg
from future.moves.urllib import parse as urlparse
from future.utils import iteritems
from typing import Text

from grr_response_core.lib import config_lib
from grr_response_core.lib import utils
from grr_response_core.lib.util import precondition


class RegistryConfigParser(config_lib.GRRConfigParser):
  """A registry based configuration parser.

  This config system simply stores all the parameters as values of type REG_SZ
  in a single key.
  """
  name = "reg"

  def __init__(self, filename=None):
    """We interpret the name as a key name."""
    url = urlparse.urlparse(filename, scheme="file")

    self.filename = url.path.replace("/", "\\")
    self.hive = url.netloc
    self.path = self.filename.lstrip("\\")
    self._root_key = None

    try:
      # Access the key during __init__ to set `self.parsed`, which might be
      # expected by callers. Do not fail instantly though on error.
      self._AccessRootKey()
    except OSError as e:
      logging.debug("Unable to open config registry key: %s", e)

  def _AccessRootKey(self):
    if self._root_key is None:
      # Don't use winreg.KEY_WOW64_64KEY since it breaks on Windows 2000
      self._root_key = winreg.CreateKeyEx(
          getattr(winreg, self.hive), self.path, 0, winreg.KEY_ALL_ACCESS)
      self.parsed = self.path
    return self._root_key

  def RawData(self):
    """Yields the valus in each section."""
    result = collections.OrderedDict()

    i = 0
    while True:
      try:
        name, value, value_type = winreg.EnumValue(self._AccessRootKey(), i)
        # Only support strings here.
        if value_type == winreg.REG_SZ:
          precondition.AssertType(value, Text)
          result[name] = value
      except OSError:
        break

      i += 1

    return result

  def SaveData(self, raw_data):
    logging.info("Writing back configuration to key %s", self.filename)

    # Ensure intermediate directories exist.
    try:
      for key, value in iteritems(raw_data):
        winreg.SetValueEx(self._AccessRootKey(), key, 0, winreg.REG_SZ,
                          utils.SmartStr(value))

    finally:
      # Make sure changes hit the disk.
      winreg.FlushKey(self._AccessRootKey())
