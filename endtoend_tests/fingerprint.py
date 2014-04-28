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
    fp = fd.Get(fd.Schema.FINGERPRINT)
    self.assertNotEqual(fp, None)
    results = list(fp.results)
    self.assertGreater(len(results), 0)

    result = results[0]
    self.assertTrue("md5" in result)
    self.assertEqual(len(result["md5"]), 16)
    self.assertTrue("sha1" in result)
    self.assertEqual(len(result["sha1"]), 20)
    self.assertTrue("sha256" in result)
    self.assertEqual(len(result["sha256"]), 32)


class TestFingerprintFileOSLinux(FingerPrintTestBase,
                                 transfer.TestGetFileOSLinux):
  """Tests if Fingerprinting works on Linux."""


class TestFingerprintFileOSWindows(FingerPrintTestBase,
                                   transfer.TestGetFileOSWindows):
  """Tests if Fingerprinting works on Windows."""


