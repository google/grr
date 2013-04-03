#!/usr/bin/env python
"""A registry based configuration parser."""

# NOTE: Running a 32 bit compiled client and 64 bit compiled client on a 64 bit
# system will run both clients on _DIFFERENT_ hives according to the WOW64
# scheme. This means that GRR will appear to have different clients for the same
# system. The clients will not share their config keys if the registry keys they
# use are hooked by WOW64.


import exceptions
import urlparse
import _winreg

import logging
from grr.lib import config_lib
from grr.lib import utils


class RegistryConfigParser(config_lib.GRRConfigParser):
  """A registry based configuration parser."""

  name = "reg"
  root_key = None

  def __init__(self, filename=None):
    """We interpret the name as a key name."""
    url = urlparse.urlparse(filename, scheme="file")

    self.filename = url.path.replace("/", "\\")
    self.hive = url.netloc
    self.path = self.filename.lstrip("\\")

    try:
      # Don't use _winreg.KEY_WOW64_64KEY since it breaks on Windows 2000
      self.root_key = _winreg.CreateKeyEx(getattr(_winreg, self.hive),
                                          self.path, 0,
                                          _winreg.KEY_ALL_ACCESS)
      self.parsed = self.path
    except exceptions.WindowsError as e:
      logging.debug("Unable to open config registry key: %s", e)
      return

  def sections(self):
    """Return a list of the sections in this registry."""
    i = 0
    if self.root_key:
      while True:
        try:
          yield _winreg.EnumKey(self.root_key, i)
        except exceptions.WindowsError:
          break

        i += 1

  def items(self, section):
    """Yields the valus in each section."""
    section = _winreg.OpenKey(self.root_key, section, 0, _winreg.KEY_READ)
    i = 0
    while True:
      try:
        name, value, value_type = _winreg.EnumValue(section, i)
        # Only support strings here.
        if value_type == _winreg.REG_SZ:
          yield name, utils.SmartStr(value)
      except exceptions.WindowsError:
        break

      i += 1

  def SaveData(self, raw_data):
    logging.info("Writing back configuration to key %s", self.filename)

    # Ensure intermediate directories exist.
    try:
      for section, data in raw_data.items():
        section_key = _winreg.CreateKeyEx(self.root_key, section)
        try:
          for config_key, config_value in data.items():
            if config_key.startswith("__"): continue

            _winreg.SetValueEx(section_key, config_key, 0, _winreg.REG_SZ,
                               str(config_value))
        finally:
          _winreg.CloseKey(section_key)

    finally:
      # Make sure changes hit the disk.
      _winreg.FlushKey(self.root_key)
