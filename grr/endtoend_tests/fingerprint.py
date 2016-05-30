#!/usr/bin/env python
"""End to end tests for lib.flows.general.fingerprint."""


from grr.endtoend_tests import base
from grr.lib import aff4
from grr.lib.rdfvalues import paths as rdf_paths


class TestFingerprintFileOSLinux(base.AutomatedTest):
  """Tests if Fingerprinting works on Linux."""
  platforms = ["Linux"]
  flow = "FingerprintFile"
  args = {"pathspec": rdf_paths.PathSpec(
      path="/bin/ls", pathtype=rdf_paths.PathSpec.PathType.OS)}
  test_output_path = "/fs/os/bin/ls"

  def CheckFlow(self):
    """Check results of flow."""
    fd = aff4.FACTORY.Open(
        self.client_id.Add(self.test_output_path),
        token=self.token)
    hash_obj = fd.Get(fd.Schema.HASH)
    self.assertNotEqual(hash_obj, None)
    self.assertEqual(len(hash_obj.md5), 16)
    self.assertEqual(len(hash_obj.sha1), 20)
    self.assertEqual(len(hash_obj.sha256), 32)


class TestFingerprintFileOSWindows(TestFingerprintFileOSLinux):
  """Tests if Fingerprinting works on Windows."""
  platforms = ["Windows"]
  args = {"pathspec": rdf_paths.PathSpec(
      path="C:\\Windows\\regedit.exe",
      pathtype=rdf_paths.PathSpec.PathType.OS)}
  test_output_path = "/fs/os/C:/Windows/regedit.exe"
