#!/usr/bin/env python
"""Test the collector flows."""
import os

from grr.client import vfs
from grr.lib import action_mocks
from grr.lib import aff4
from grr.lib import config_lib
from grr.lib import flags
from grr.lib import flow
from grr.lib import rdfvalue
from grr.lib import test_lib
from grr.lib.checks import checks

# pylint: mode=test

# Load some dpkg data
dpkg_src = os.path.join(config_lib.CONFIG["Test.data_dir"], "dpkg.out")
# Load an sshd_config
sshd_name = "/fs/os/etc/sshd/sshd_config"
sshd_src = os.path.join(config_lib.CONFIG["Test.data_dir"], "sshd_config")


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
        rdfvalue.PathSpec.PathType.OS] = test_lib.FakeTestDataVFSHandler
    self.client_mock = action_mocks.ActionMock("TransferBuffer", "StatFile",
                                               "Find", "HashBuffer",
                                               "ListDirectory",
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
      for session_id in test_lib.TestFlowHelper("CheckRunner", self.client_mock,
                                                token=self.token,
                                                client_id=self.client_id):
        pass
    session = aff4.FACTORY.Open(session_id, token=self.token)
    replies = send_reply
    return session, replies

  def LoadChecks(self):
    """Load the checks, returning the names of the checks that were loaded."""
    config_lib.CONFIG.Set("Checks.max_results", 5)
    check_configs = ("sshd.yaml", "sw.yaml")
    cfg_dir = os.path.join(config_lib.CONFIG["Test.data_dir"], "checks")
    chk_files = [os.path.join(cfg_dir, f) for f in check_configs]
    checks.LoadChecksFromFiles(chk_files)
    return checks.CheckRegistry.checks.keys()

  def testSelectArtifactsForChecks(self):
    self.SetLinuxKB()
    expected = ["DebianPackagesStatus", "SshdConfigFile"]
    results, _ = self.RunFlow()
    self.assertItemsEqual(expected, results.state.artifacts_wanted)

    self.SetWindowsKB()
    expected = ["WMIInstalledSoftware"]
    results, _ = self.RunFlow()
    self.assertItemsEqual(expected, results.state.artifacts_wanted)

  def testCheckHostDataReturnsFindings(self):
    """Test the flow returns results."""
    self.SetLinuxKB()
    expected = {"DebianPackagesStatus": ["Should have data, but doesn't"],
                "SshdConfigFile": ["Ditto"]}
    _, replies = self.RunFlow()
    checks_run = []
    anomalies_found = []
    for _, rslt in replies.args:
      if isinstance(rslt, rdfvalue.CheckResult):
        checks_run.append(rslt.check_id)
        if rslt:  # True if there are anomalies
          anomalies_found.extend([a.ToPrimitiveDict() for a in rslt.anomaly])
    self.assertItemsEqual(["SSHD-CHECK", "SW-CHECK"], checks_run)
    expected = [{"finding": [u"Configured protocols: [2, 1]"],
                 "explanation": u"Found: Sshd allows protocol 1.",
                 "type": "ANALYSIS_ANOMALY"}]
    self.assertEqual(expected, anomalies_found)


def main(argv):
  # Run the full test suite
  test_lib.GrrTestProgram(argv=argv)

if __name__ == "__main__":
  flags.StartMain(main)
