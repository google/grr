#!/usr/bin/env python
# Lint as: python3
# -*- encoding: utf-8 -*-
"""Test client utility functions."""
from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

import hashlib
import io
import os
import platform
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


class IsExecutionAllowedTest(absltest.TestCase):

  def setUp(self):
    super().setUp()
    self.is_execution_allowed = client_utils_common.IsExecutionAllowed

  def testAllowsOnlyConfiguredCommands(self):
    with test_lib.ConfigOverrider({
        "Client.allowed_commands": ["/usr/bin/foo"],
    }):
      self.assertTrue(self.is_execution_allowed("/usr/bin/foo", []))
      self.assertFalse(self.is_execution_allowed("/usr/bin/bar", []))

  def testAllowsOnlyConfiguredCommandsWithArgs(self):
    with test_lib.ConfigOverrider({
        "Client.allowed_commands": [
            "/bin/foo --bar --baz",
            "/bin/foo --quux",
        ],
    }):
      self.assertTrue(self.is_execution_allowed("/bin/foo", ["--bar", "--baz"]))
      self.assertTrue(self.is_execution_allowed("/bin/foo", ["--quux"]))
      self.assertFalse(self.is_execution_allowed("/bin/foo", ["--norf"]))

  def testAllowsOnlyConfiguredCommandsWithSimpleQuotes(self):
    with test_lib.ConfigOverrider({
        "Client.allowed_commands": ["'foo bar' 'baz quux'"],
    }):
      self.assertTrue(self.is_execution_allowed("foo bar", ["baz quux"]))
      self.assertFalse(self.is_execution_allowed("foo bar", ["baz", "quux"]))
      self.assertFalse(self.is_execution_allowed("foo", ["bar", "baz quux"]))
      self.assertFalse(self.is_execution_allowed("foo", ["bar", "baz", "quux"]))

  def testAllowsOnlyConfiguredCommandsWithComplexQuotes(self):
    with test_lib.ConfigOverrider({
        "Client.allowed_commands": [
            "'/foo bar/\"quux norf\"/thud' -x '1 3 3 7' -y \"42\"",
        ],
    }):
      command = "/foo bar/\"quux norf\"/thud"
      args = ["-x", "1 3 3 7", "-y", "42"]
      self.assertTrue(self.is_execution_allowed(command, args))


class ClientUtilsTest(test_lib.GRRBaseTest):
  """Test the client utils."""

  @unittest.skipIf(platform.system() != "Windows", "Windows only test.")
  def testWinSplitPathspec(self):
    # pylint: disable=g-import-not-at-top
    from grr_response_client import client_utils_windows
    # pylint: enable=g-import-not-at-top
    raw_pathspec, path = client_utils_windows.GetRawDevice("C:\\")
    self.assertStartsWith(raw_pathspec.path, "\\\\?\\Volume{")
    self.assertEqual("/", path)

  def testExecutionAllowlist(self):
    """Test if unknown commands are filtered correctly."""

    # ls is not allowed
    if platform.system() == "Windows":
      cmd = "dir", []
    else:
      cmd = "ls", ["."]
    (stdout, stderr, status, _) = client_utils_common.Execute(*cmd)
    self.assertEqual(status, -1)
    self.assertEqual(stdout, b"")
    self.assertEqual(stderr, b"Execution disallowed by allowlist.")

    # "echo 1" is
    if platform.system() == "Windows":
      cmd = "cmd.exe", ["/C", "echo 1"]
    else:
      cmd = "/bin/echo", ["1"]
    (stdout, stderr, status, _) = client_utils_common.Execute(*cmd)
    self.assertEqual(status, 0)
    self.assertEqual(stdout, "1{}".format(os.linesep).encode("utf-8"))
    self.assertEqual(stderr, b"")

    # but not "echo 11"
    if platform.system() == "Windows":
      cmd = "cmd.exe", ["/C", "echo 11"]
    else:
      cmd = "/bin/echo", ["11"]
    (stdout, stderr, status, _) = client_utils_common.Execute(*cmd)
    self.assertEqual(status, -1)
    self.assertEqual(stdout, b"")
    self.assertEqual(stderr, b"Execution disallowed by allowlist.")

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
