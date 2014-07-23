#!/usr/bin/env python
"""End to end tests for lib.flows.general.fingerprint."""


from grr.endtoend_tests import base
from grr.lib import aff4
from grr.lib import rdfvalue


class TestFingerprintFileOSLinux(base.AutomatedTest):
  """Tests if Fingerprinting works on Linux."""
  platforms = ["Linux"]
  flow = "FingerprintFile"
  args = {"pathspec": rdfvalue.PathSpec(
      path="/bin/ls",
      pathtype=rdfvalue.PathSpec.PathType.OS)}
  test_output_path = "/fs/os/bin/ls"

  def CheckFlow(self):
    """Check results of flow."""
    fd = aff4.FACTORY.Open(self.client_id.Add(self.test_output_path))
    hash_obj = fd.Get(fd.Schema.HASH)
    self.assertNotEqual(hash_obj, None)
    self.assertEqual(len(hash_obj.md5), 16)
    self.assertEqual(len(hash_obj.sha1), 20)
    self.assertEqual(len(hash_obj.sha256), 32)


class TestFingerprintFileOSWindows(TestFingerprintFileOSLinux):
  """Tests if Fingerprinting works on Windows."""
  platforms = ["Windows"]
  args = {"pathspec": rdfvalue.PathSpec(
      path="C:\\Windows\\regedit.exe",
      pathtype=rdfvalue.PathSpec.PathType.OS)}
  test_output_path = "/fs/os/C:/Windows/regedit.exe"
