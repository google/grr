#!/usr/bin/env python
# -*- encoding: utf-8 -*-
"""Test client utility functions."""
from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

import hashlib
import imp
import io
import os
import platform
import sys
import unittest

from absl import app
from absl.testing import absltest
import mock

from grr_response_client import client_utils
from grr_response_client import client_utils_common
from grr_response_core.lib.rdfvalues import paths as rdf_paths
from grr_response_core.lib.util import filesystem
from grr_response_core.lib.util import temp
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

    sys.modules["winreg"] = imp.new_module("winreg")
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
    self.assertEqual(stdout, b"")
    self.assertEqual(stderr, b"Execution disallowed by whitelist.")

    # "echo 1" is
    (stdout, stderr, status, _) = client_utils_common.Execute(
        "/bin/echo", ["1"])
    self.assertEqual(status, 0)
    self.assertEqual(stdout, b"1\n")
    self.assertEqual(stderr, b"")

    # but not "echo 11"
    (stdout, stderr, status, _) = client_utils_common.Execute(
        "/bin/echo", ["11"])
    self.assertEqual(status, -1)
    self.assertEqual(stdout, b"")
    self.assertEqual(stderr, b"Execution disallowed by whitelist.")

  def AppendTo(self, list_obj, element):
    list_obj.append(element)

  def testExecutionTimeLimit(self):
    """Test if the time limit works."""

    _, _, _, time_used = client_utils_common.Execute("/bin/sleep", ["10"], 0.1)

    # This should take just a bit longer than 0.1 seconds.
    self.assertLess(time_used, 1.0)


@unittest.skipIf(platform.system() != "Darwin", "Skipping macOS only test.")
@mock.patch(
    "grr_response_client.client_utils_osx"
    ".platform.mac_ver",
    return_value=("10.8.1", ("", "", ""), "x86_64"))
class OSXVersionTests(test_lib.GRRBaseTest):

  def testVersionAsIntArray(self, _):
    from grr_response_client import client_utils_osx  # pylint: disable=g-import-not-at-top
    osversion = client_utils_osx.OSXVersion()
    self.assertEqual(osversion.VersionAsMajorMinor(), [10, 8])

  def testVersionString(self, _):
    from grr_response_client import client_utils_osx  # pylint: disable=g-import-not-at-top
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
    hasher.HashBuffer(b"foo")

    hash_object = hasher.GetHashObject()
    self.assertEqual(hash_object.num_bytes, len(b"foo"))  # pylint: disable=g-generic-assert
    self.assertEqual(hash_object.md5, self._GetHash(hashlib.md5, b"foo"))
    self.assertEqual(hash_object.sha1, self._GetHash(hashlib.sha1, b"foo"))
    self.assertEqual(hash_object.sha256, self._GetHash(hashlib.sha256, b"foo"))

  def testHashBufferMultiInput(self):
    hasher = client_utils_common.MultiHasher(["md5", "sha1"])
    hasher.HashBuffer(b"foo")
    hasher.HashBuffer(b"bar")

    hash_object = hasher.GetHashObject()
    self.assertEqual(hash_object.num_bytes, len(b"foobar"))  # pylint: disable=g-generic-assert
    self.assertEqual(hash_object.md5, self._GetHash(hashlib.md5, b"foobar"))
    self.assertEqual(hash_object.sha1, self._GetHash(hashlib.sha1, b"foobar"))
    self.assertFalse(hash_object.sha256)

  def testHashFileWhole(self):
    with temp.AutoTempFilePath() as tmp_path:
      with io.open(tmp_path, "wb") as tmp_file:
        tmp_file.write(b"foobar")

      hasher = client_utils_common.MultiHasher(["md5", "sha1"])
      hasher.HashFilePath(tmp_path, len(b"foobar"))

      hash_object = hasher.GetHashObject()
      self.assertEqual(hash_object.num_bytes, len(b"foobar"))  # pylint: disable=g-generic-assert
      self.assertEqual(hash_object.md5, self._GetHash(hashlib.md5, b"foobar"))
      self.assertEqual(hash_object.sha1, self._GetHash(hashlib.sha1, b"foobar"))
      self.assertFalse(hash_object.sha256)

  def testHashFilePart(self):
    with temp.AutoTempFilePath() as tmp_path:
      with io.open(tmp_path, "wb") as tmp_file:
        tmp_file.write(b"foobar")

      hasher = client_utils_common.MultiHasher(["md5", "sha1"])
      hasher.HashFilePath(tmp_path, len(b"foo"))

      hash_object = hasher.GetHashObject()
      self.assertEqual(hash_object.num_bytes, len(b"foo"))  # pylint: disable=g-generic-assert
      self.assertEqual(hash_object.md5, self._GetHash(hashlib.md5, b"foo"))
      self.assertEqual(hash_object.sha1, self._GetHash(hashlib.sha1, b"foo"))
      self.assertFalse(hash_object.sha256)

  def testHashBufferProgress(self):
    progress = mock.Mock()

    hasher = client_utils_common.MultiHasher(progress=progress)
    hasher.HashBuffer(os.urandom(108))

    self.assertTrue(progress.called)
    self.assertEqual(hasher.GetHashObject().num_bytes, 108)

  def testStatResultFromStatEntry(self):
    stat_obj = os.stat_result([0, 1, 2, 3, 4, 5, 6, 7, 8, 9])
    fs_stat = filesystem.Stat("/foo", stat_obj)
    pathspec = rdf_paths.PathSpec(path="/foo", pathtype="OS")
    stat_entry = client_utils.StatEntryFromStat(
        fs_stat, pathspec, ext_attrs=False)
    self.assertEqual(stat_obj, client_utils.StatResultFromStatEntry(stat_entry))


def main(argv):
  test_lib.main(argv)


if __name__ == "__main__":
  app.run(main)
