#!/usr/bin/env python
"""Test case for security mechanisms to be run inside a sandbox."""

# pylint: mode=test

import os
import socket
import urllib

from absl import flags
from absl.testing import absltest

import winreg

_LOCALHOST_PORT = flags.DEFINE_integer(
    "localhost_port",
    default=-1,
    help="",
)

_REGISTRY_SUB_KEY = flags.DEFINE_string(
    "registry_sub_key",
    default="",
    help="",
)


class SandboxUnprivilegedTest(absltest.TestCase):

  def testWriteFile(self):
    with self.assertRaises(PermissionError):
      with open("C:\\foo.txt", "w"):
        pass

  def testListDir(self):
    with self.assertRaises(PermissionError):
      os.listdir("C:\\")

  def testUrlDownload(self):
    with self.assertRaises(urllib.error.URLError):
      with urllib.request.urlopen("https://www.google.com/") as u:
        print(u.read())
        self.fail("The download shouldn't succeed.")

  def testConnect(self):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
      s.settimeout(5)
      with self.assertRaises(OSError):
        s.connect(("127.0.0.1", _LOCALHOST_PORT.value))

  def testRegistry(self):
    with self.assertRaises(PermissionError):
      key = winreg.OpenKey(
          winreg.HKEY_LOCAL_MACHINE,
          _REGISTRY_SUB_KEY.value,
          access=winreg.KEY_ALL_ACCESS)
      winreg.SetValueEx(key, "foo", 0, winreg.REG_SZ, "bar")


if __name__ == "__main__":
  absltest.main()
