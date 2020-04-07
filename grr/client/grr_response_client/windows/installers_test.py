#!/usr/bin/env python
# Lint as: python3
from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

import platform
import unittest

from absl.testing import absltest

# pylint: disable=g-import-not-at-top
try:
  import winreg
except ImportError:
  # The import is expected to fail on non-Windows platforms.
  winreg = None

import mock

try:
  from grr_response_client.windows import installers
except ImportError:
  # The import is expected to fail on non-Windows platforms.
  installers = None
# pylint: enable=g-import-not-at-top

_TEST_KEY_PATH = "SOFTWARE\\GRR_InstallerTest"


def _GetAllRegistryKeyValues(key):
  values = {}
  while True:
    try:
      value_name, value, _ = winreg.EnumValue(key, len(values))
      values[value_name] = value
    except OSError:
      return values


@unittest.skipIf(platform.system() != "Windows",
                 "Windows-only functionality being tested.")
class InstallerTest(absltest.TestCase):

  @classmethod
  def setUpClass(cls):
    super(InstallerTest, cls).setUpClass()

    winreg.CreateKeyEx(winreg.HKEY_LOCAL_MACHINE, _TEST_KEY_PATH)

  @classmethod
  def tearDownClass(cls):
    super(InstallerTest, cls).tearDownClass()

    winreg.DeleteKeyEx(winreg.HKEY_LOCAL_MACHINE, _TEST_KEY_PATH,
                       winreg.KEY_ALL_ACCESS, 0)

  @mock.patch.object(installers, "_LEGACY_OPTIONS", frozenset(["bar"]))
  def testDeleteLegacyConfigOptions(self):
    key = winreg.OpenKeyEx(winreg.HKEY_LOCAL_MACHINE, _TEST_KEY_PATH, 0,
                           winreg.KEY_ALL_ACCESS)
    winreg.SetValueEx(key, "foo", 0, winreg.REG_SZ, "foo-value")
    winreg.SetValueEx(key, "bar", 0, winreg.REG_SZ, "bar-value")
    installers._DeleteLegacyConfigOptions(
        "reg://HKEY_LOCAL_MACHINE/{}".format(_TEST_KEY_PATH))
    remaining_values = _GetAllRegistryKeyValues(key)
    self.assertDictEqual(remaining_values, {"foo": "foo-value"})


if __name__ == "__main__":
  absltest.main()
