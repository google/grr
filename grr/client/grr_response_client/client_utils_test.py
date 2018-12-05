#!/usr/bin/env python
# -*- mode: python; encoding: utf-8 -*-
"""Test client utility functions."""
from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

import hashlib
import imp
import os
import sys

from absl.testing import absltest
import mock

from grr_response_client import client_utils_common
from grr_response_client import client_utils_osx
from grr_response_core.lib import flags
from grr.test_lib import temp
from grr.test_lib import test_lib


def GetVolumePathName(_):
  return "C:\\"


def GetVolumeNameForVolumeMountPoint(_):
  return "\\\\?\\Volume{11111}\\"


class ClientUtilsTest(test_lib.GRRBaseTest):
  """Test the client utils."""

  def testWinSplitPathspec(self):
    """Test windows split pathspec functionality."""

    self.SetupWinEnvironment()

    # We need to import after SetupWinEnvironment or this will fail
    # pylint: disable=g-import-not-at-top
    from grr_response_client import client_utils_windows
    # pylint: enable=g-import-not-at-top

    testdata = [(r"C:\Windows", "\\\\?\\Volume{11111}", "/Windows"),
                (r"C:\\Windows\\", "\\\\?\\Volume{11111}", "/Windows"),
                (r"C:\\", "\\\\?\\Volume{11111}", "/")]

    for filename, expected_device, expected_path in testdata:
      raw_pathspec, path = client_utils_windows.GetRawDevice(filename)

      # Pathspec paths are always absolute and therefore must have a leading /.
      self.assertEqual(expected_device, raw_pathspec.path)
      self.assertEqual(expected_path, path)

  def SetupWinEnvironment(self):
    """Mock windows includes."""

    pywintypes = imp.new_module("pywintypes")
    pywintypes.error = Exception
    sys.modules["pywintypes"] = pywintypes

    winfile = imp.new_module("win32file")
    winfile.GetVolumeNameForVolumeMountPoint = GetVolumeNameForVolumeMountPoint
    winfile.GetVolumePathName = GetVolumePathName
    sys.modules["win32file"] = winfile

    sys.modules["_winreg"] = imp.new_module("_winreg")
    sys.modules["ntsecuritycon"] = imp.new_module("ntsecuritycon")
    sys.modules["win32security"] = imp.new_module("win32security")
    sys.modules["win32api"] = imp.new_module("win32api")
    sys.modules["win32service"] = imp.new_module("win32service")
    sys.modules["win32process"] = imp.new_module("win32process")
    sys.modules["win32serviceutil"] = imp.new_module("win32serviceutil")
    sys.modules["winerror"] = imp.new_module("winerror")

    # Importing process.py pulls in lots of Windows specific stuff.
    # pylint: disable=g-import-not-at-top
    from grr_response_client import windows
    windows.process = None
    # pylint: enable=g-import-not-at-top

  def testExecutionWhiteList(self):
    """Test if unknown commands are filtered correctly."""

    # ls is not allowed
    (stdout, stderr, status, _) = client_utils_common.Execute("ls", ["."])
    self.assertEqual(status, -1)
    self.assertEqual(stdout, "")
    self.assertEqual(stderr, "Execution disallowed by whitelist.")

    # "echo 1" is
    (stdout, stderr, status, _) = client_utils_common.Execute(
        "/bin/echo", ["1"])
    self.assertEqual(status, 0)
    self.assertEqual(stdout, "1\n")
    self.assertEqual(stderr, "")

    # but not "echo 11"
    (stdout, stderr, status, _) = client_utils_common.Execute(
        "/bin/echo", ["11"])
    self.assertEqual(status, -1)
    self.assertEqual(stdout, "")
    self.assertEqual(stderr, "Execution disallowed by whitelist.")

  def AppendTo(self, list_obj, element):
    list_obj.append(element)

  def testExecutionTimeLimit(self):
    """Test if the time limit works."""

    _, _, _, time_used = client_utils_common.Execute("/bin/sleep", ["10"], 0.1)

    # This should take just a bit longer than 0.1 seconds.
    self.assertLess(time_used, 1.0)


@mock.patch(
    "grr_response_client.client_utils_osx"
    ".platform.mac_ver",
    return_value=("10.8.1", ("", "", ""), "x86_64"))
class OSXVersionTests(test_lib.GRRBaseTest):

  def testVersionAsIntArray(self, _):
    osversion = client_utils_osx.OSXVersion()
    self.assertEqual(osversion.VersionAsMajorMinor(), [10, 8])

  def testVersionString(self, _):
    osversion = client_utils_osx.OSXVersion()
    self.assertEqual(osversion.VersionString(), "10.8.1")


class MultiHasherTest(absltest.TestCase):

  @staticmethod
  def _GetHash(hashfunc, data):
    hasher = hashfunc()
    hasher.update(data)
    return hasher.digest()

  def testHashBufferSingleInput(self):
    hasher = client_utils_common.MultiHasher()
    hasher.HashBuffer("foo")

    hash_object = hasher.GetHashObject()
    self.assertEqual(hash_object.num_bytes, len("foo"))
    self.assertEqual(hash_object.md5, self._GetHash(hashlib.md5, "foo"))
    self.assertEqual(hash_object.sha1, self._GetHash(hashlib.sha1, "foo"))
    self.assertEqual(hash_object.sha256, self._GetHash(hashlib.sha256, "foo"))

  def testHashBufferMultiInput(self):
    hasher = client_utils_common.MultiHasher(["md5", "sha1"])
    hasher.HashBuffer("foo")
    hasher.HashBuffer("bar")

    hash_object = hasher.GetHashObject()
    self.assertEqual(hash_object.num_bytes, len("foobar"))
    self.assertEqual(hash_object.md5, self._GetHash(hashlib.md5, "foobar"))
    self.assertEqual(hash_object.sha1, self._GetHash(hashlib.sha1, "foobar"))
    self.assertFalse(hash_object.sha256)

  def testHashFileWhole(self):
    with temp.AutoTempFilePath() as tmp_path:
      with open(tmp_path, "wb") as tmp_file:
        tmp_file.write("foobar")

      hasher = client_utils_common.MultiHasher(["md5", "sha1"])
      hasher.HashFilePath(tmp_path, len("foobar"))

      hash_object = hasher.GetHashObject()
      self.assertEqual(hash_object.num_bytes, len("foobar"))
      self.assertEqual(hash_object.md5, self._GetHash(hashlib.md5, "foobar"))
      self.assertEqual(hash_object.sha1, self._GetHash(hashlib.sha1, "foobar"))
      self.assertFalse(hash_object.sha256)

  def testHashFilePart(self):
    with temp.AutoTempFilePath() as tmp_path:
      with open(tmp_path, "wb") as tmp_file:
        tmp_file.write("foobar")

      hasher = client_utils_common.MultiHasher(["md5", "sha1"])
      hasher.HashFilePath(tmp_path, len("foo"))

      hash_object = hasher.GetHashObject()
      self.assertEqual(hash_object.num_bytes, len("foo"))
      self.assertEqual(hash_object.md5, self._GetHash(hashlib.md5, "foo"))
      self.assertEqual(hash_object.sha1, self._GetHash(hashlib.sha1, "foo"))
      self.assertFalse(hash_object.sha256)

  def testHashBufferProgress(self):
    progress = mock.Mock()

    hasher = client_utils_common.MultiHasher(progress=progress)
    hasher.HashBuffer(os.urandom(108))

    self.assertTrue(progress.called)
    self.assertEqual(hasher.GetHashObject().num_bytes, 108)


def main(argv):
  test_lib.main(argv)


if __name__ == "__main__":
  flags.StartMain(main)
