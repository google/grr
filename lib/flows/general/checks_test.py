#!/usr/bin/env python
"""Test the collector flows."""
import os

from grr.client import vfs
from grr.lib import action_mocks
from grr.lib import aff4
from grr.lib import config_lib
from grr.lib import flags
from grr.lib import flow
from grr.lib import test_lib
from grr.lib.checks import checks
# pylint: disable=unused-import
from grr.lib.flows.general import checks as _
# pylint: enable=unused-import
from grr.lib.rdfvalues import paths as rdf_paths

# pylint: mode=test


class TestCheckFlows(test_lib.FlowTestsBaseclass):

  checks_loaded = False

  def setUp(self, **kwargs):
    super(TestCheckFlows, self).setUp(**kwargs)
    # Only load the checks once.
    if self.checks_loaded is False:
      self.checks_loaded = self.LoadChecks()
    if not self.checks_loaded:
      raise RuntimeError("No checks to test.")
    test_lib.ClientFixture(self.client_id, token=self.token)
    vfs.VFS_HANDLERS[
        rdf_paths.PathSpec.PathType.OS] = test_lib.FakeTestDataVFSHandler
    self.client_mock = action_mocks.ActionMock("TransferBuffer", "StatFile",
                                               "Find", "HashBuffer",
                                               "ListDirectory", "HashFile",
                                               "FingerprintFile")

  def SetLinuxKB(self):
    client = aff4.FACTORY.Open(self.client_id, token=self.token, mode="rw")
    kb = client.Schema.KNOWLEDGE_BASE()
    kb.os = "Linux"
    client.Set(client.Schema.KNOWLEDGE_BASE, kb)
    client.Set(client.Schema.SYSTEM("Linux"))
    client.Set(client.Schema.OS_VERSION("12.04"))
    client.Flush()

  def SetWindowsKB(self):
    client = aff4.FACTORY.Open(self.client_id, token=self.token, mode="rw")
    kb = client.Schema.KNOWLEDGE_BASE()
    kb.os = "Windows"
    client.Set(client.Schema.KNOWLEDGE_BASE, kb)
    client.Set(client.Schema.SYSTEM("Windows"))
    client.Set(client.Schema.OS_VERSION("6.2"))
    client.Flush()

  def RunFlow(self):
    session_id = None
    with test_lib.Instrument(flow.GRRFlow, "SendReply") as send_reply:
      for session_id in test_lib.TestFlowHelper(
          "CheckRunner", client_mock=self.client_mock, client_id=self.client_id,
          token=self.token):
        pass
    session = aff4.FACTORY.Open(session_id, token=self.token)
    replies = send_reply
    return session, replies

  def LoadChecks(self):
    """Load the checks, returning the names of the checks that were loaded."""
    config_lib.CONFIG.Set("Checks.max_results", 5)
    checks.CheckRegistry.Clear()
    check_configs = ("sshd.yaml", "sw.yaml")
    cfg_dir = os.path.join(config_lib.CONFIG["Test.data_dir"], "checks")
    chk_files = [os.path.join(cfg_dir, f) for f in check_configs]
    checks.LoadChecksFromFiles(chk_files)
    return checks.CheckRegistry.checks.keys()

  def testSelectArtifactsForChecks(self):
    self.SetLinuxKB()
    results, _ = self.RunFlow()
    self.assertTrue("DebianPackagesStatus" in results.state.artifacts_wanted)
    self.assertTrue("SshdConfigFile" in results.state.artifacts_wanted)

    self.SetWindowsKB()
    results, _ = self.RunFlow()
    self.assertTrue("WMIInstalledSoftware" in results.state.artifacts_wanted)

  def testCheckHostDataReturnsFindings(self):
    """Test the flow returns results."""
    self.SetLinuxKB()

    # Run the check flow end-to-end.
    checks_run = []
    _, replies = self.RunFlow()

    for _, result in replies.args:
      if isinstance(result, checks.CheckResult):
        checks_run.append(result.check_id)
        if result.check_id == "SSHD-CHECK":  # True if there are anomalies
          sshd_results = [a.ToPrimitiveDict() for a in result.anomaly]
        if result.check_id == "SSHD-PERMS":  # True if there are stat results
          perm_results = [r.ToPrimitiveDict() for r in result.anomaly]
    self.assertTrue("SSHD-CHECK" in checks_run)
    expected = {"explanation": "Found: Sshd allows protocol 1.",
                "finding": ["Configured protocols: 2,1"],
                "type": "ANALYSIS_ANOMALY"}
    self.assertTrue(expected in sshd_results)
    self.assertTrue("SSHD-PERMS" in checks_run)
    self.assertEqual(1, len(perm_results))
    expected = {"explanation": "Found: The filesystem supports stat.",
                "finding": ["/etc/ssh/sshd_config"],
                "type": "ANALYSIS_ANOMALY"}
    self.assertTrue(expected in perm_results)


def main(argv):
  # Run the full test suite
  test_lib.GrrTestProgram(argv=argv)

if __name__ == "__main__":
  flags.StartMain(main)
