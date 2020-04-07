#!/usr/bin/env python
# Lint as: python3
"""Test Eficheck client actions."""
from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

import os

from absl import app
import mock

from grr_response_client.client_actions import tempfiles
from grr_response_client.client_actions.osx import firmware
from grr_response_core.lib import utils
from grr_response_core.lib.rdfvalues import apple_firmware as rdf_apple_firmware
from grr.test_lib import client_test_lib
from grr.test_lib import test_lib


def MockExecute(unused_cmd, args, **unused_kwds):
  if "--version" in args:
    return (b"v1.14", b"", 0, 5)
  elif "--generate-hashes" in args:
    return (b"Successfully wrote hashes.", b"", 0, 5)
  elif args == ["--save", "-b", "firmware.bin"]:
    return (b"Successfully wrote the image.", b"", 0, 15)
  elif "--show-hashes" in args:
    return (b"00:01:02:12345:abcd-12345", b"", 0, 5)


def FailedMockExecute(unused_cmd, unused_args, **unused_kwds):
  return (b"", b"Unable to find the eficheck binary", -1, 10)


def FailedDumpMockExecute(unused_cmd, args, **unused_kwds):
  if "--version" in args:
    return (b"v1.14", b"", 0, 5)
  else:
    return (b"", b"Unable to dump the binary image", -1, 10)


@mock.patch.multiple(
    "grr_response_client.client_actions.osx"
    ".firmware",
    glob=mock.DEFAULT,
    client_utils_common=mock.DEFAULT)
class TestEficheckCollect(client_test_lib.EmptyActionTest):
  """Test class for GRR-eficheck actions."""

  def testEficheckCollectHashes(self, glob, client_utils_common):
    """Test the basic hash collection action."""

    client_utils_common.Execute = MockExecute
    glob.glob.return_value = ["./MBP142.88Z.F000.B00.123.0.ealf"]

    args = rdf_apple_firmware.EficheckConfig()
    with utils.Stubber(tempfiles, "DeleteGRRTempFile", lambda filename: None):
      result = self.RunAction(firmware.EficheckCollectHashes, args)[0]

    self.assertEqual(result.boot_rom_version, "MBP142.88Z.F000.B00.123.0")
    self.assertEqual(result.eficheck_version, "v1.14")
    self.assertEqual(result.response.stdout, b"00:01:02:12345:abcd-12345")
    self.assertEqual(result.response.stderr, b"")

  def testFailedEficheckCollectHashes(self, glob, client_utils_common):

    client_utils_common.Execute = FailedMockExecute
    glob.glob.return_value = []
    args = rdf_apple_firmware.EficheckConfig()
    result = self.RunAction(firmware.EficheckCollectHashes, args)[0]

    self.assertEqual(result.response.stderr,
                     b"Unable to find the eficheck binary")

  def testEficheckCollectHashesWithExtra(self, glob, client_utils_common):
    """Test the hash collection action when extra unknown files are present."""

    client_utils_common.Execute = MockExecute
    glob.glob.return_value = ["./MBP61.ealf", "$(id).ealf", "`id`.ealf"]

    args = rdf_apple_firmware.EficheckConfig()
    with utils.Stubber(tempfiles, "DeleteGRRTempFile", lambda filename: None):
      results = self.RunAction(firmware.EficheckCollectHashes, args)
    self.assertLen(results, 1)

  def testEficheckDumpImage(self, glob, client_utils_common):
    """Test the basic dump action."""

    client_utils_common.Execute = MockExecute

    args = rdf_apple_firmware.EficheckConfig()
    with utils.Stubber(tempfiles, "GetDefaultGRRTempDirectory", lambda **kw: os.
                       path.abspath(self.temp_dir)):
      result = self.RunAction(firmware.EficheckDumpImage, args)[0]

    self.assertEqual(result.eficheck_version, "v1.14")
    self.assertEqual(result.response.stderr, b"")
    self.assertStartsWith(result.path.path, self.temp_dir)
    self.assertEndsWith(result.path.path, "/firmware.bin")

  def testFailedEficheckDumpImageVersion(self, glob, client_utils_common):
    """Test for failure of the dump action when reading the version."""

    client_utils_common.Execute = FailedMockExecute

    args = rdf_apple_firmware.EficheckConfig()
    result = self.RunAction(firmware.EficheckDumpImage, args)[0]

    self.assertEqual(result.response.stderr,
                     b"Unable to find the eficheck binary")

  def testFailedEficheckDumpImage(self, glob, client_utils_common):
    """Test for failure of the basic dump action."""

    client_utils_common.Execute = FailedDumpMockExecute

    args = rdf_apple_firmware.EficheckConfig()
    result = self.RunAction(firmware.EficheckDumpImage, args)[0]

    self.assertEqual(result.eficheck_version, "v1.14")
    self.assertEqual(result.response.stderr, b"Unable to dump the binary image")


def main(argv):
  test_lib.main(argv)


if __name__ == "__main__":
  app.run(main)
