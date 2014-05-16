#!/usr/bin/env python
"""End to end tests for lib.flows.general.fingerprint."""


from grr.endtoend_tests import transfer
from grr.lib import aff4


class FingerPrintTestBase(object):
  flow = "FingerprintFile"

  def setUp(self):  # pylint: disable=invalid-name
    self.urn = self.client_id.Add(self.output_path)
    self.DeleteUrn(self.urn)

    self.assertRaises(AssertionError, self.CheckFlow)

  def CheckFlow(self):
    """Check results of flow."""
    fd = aff4.FACTORY.Open(self.urn)
    hash_obj = fd.Get(fd.Schema.HASH)
    self.assertNotEqual(hash_obj, None)
    self.assertEqual(len(hash_obj.md5), 16)
    self.assertEqual(len(hash_obj.sha1), 20)
    self.assertEqual(len(hash_obj.sha256), 32)


class TestFingerprintFileOSLinux(FingerPrintTestBase,
                                 transfer.TestGetFileOSLinux):
  """Tests if Fingerprinting works on Linux."""


class TestFingerprintFileOSWindows(FingerPrintTestBase,
                                   transfer.TestGetFileOSWindows):
  """Tests if Fingerprinting works on Windows."""


