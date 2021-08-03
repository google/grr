#!/usr/bin/env python
import encodings.idna  # pylint: disable=unused-import
import errno
import os
import platform
import socket
import unittest
import urllib
import urllib.error
import urllib.request

from absl.testing import absltest

from grr_response_client.unprivileged import sandbox


@unittest.skipIf(platform.system() != "Linux" or os.getuid() != 0,
                 "Skipping Linux-only root test.")
class LinuxSandboxTest(absltest.TestCase):

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
      with open("/etc/shadow", "r"):
        pass

  def testUrlDownload(self):
    with self.assertRaises(urllib.error.URLError):
      with urllib.request.urlopen("https://www.google.com/") as u:
        u.read()
        self.fail("The download shouldn't succeed.")

  def testConnect(self):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
      s.settimeout(5)
      with self.assertRaises(OSError) as e:
        s.connect(("127.0.0.1", 22))
      self.assertEqual(e.exception.errno, errno.ENETUNREACH)

  def testNetworkInterfaces(self):
    with open("/proc/net/dev", "r") as f:
      lines = list(f)
      # 2 lines for header + 1 line for lo interface.
      self.assertLen(lines, 3)


if __name__ == "__main__":
  absltest.main()
