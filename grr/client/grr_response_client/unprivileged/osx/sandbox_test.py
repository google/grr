#!/usr/bin/env python
import os
import platform
import socket
import unittest
import urllib
import urllib.error
import urllib.request

from absl.testing import absltest

from grr_response_client.unprivileged import sandbox


@unittest.skipIf(platform.system() != "Darwin" or os.getuid() != 0,
                 "Skipping OSX-only root test.")
class OSXSandboxTest(absltest.TestCase):

  @classmethod
  def setUpClass(cls):
    super().setUpClass()
    sandbox.EnterSandbox("nobody", "nobody")

  def testWriteFile(self):
    with self.assertRaises(PermissionError):
      with open("/etc/foo.txt", "w"):
        pass

  def testReadFile(self):
    with self.assertRaises(PermissionError):
      with open("/etc/sudoers", "r"):
        pass

  def testUrlDownload(self):
    with self.assertRaises(urllib.error.URLError):
      with urllib.request.urlopen("https://www.google.com/") as u:
        u.read()
        self.fail("The download shouldn't succeed.")

  def testConnect(self):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
      s.settimeout(5)
      with self.assertRaises(PermissionError):
        s.connect(("127.0.0.1", 22))


if __name__ == "__main__":
  absltest.main()
