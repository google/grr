#!/usr/bin/env python
"""Test the collector flows."""
import os

from grr import config
from grr.lib import flags
from grr.lib.rdfvalues import client as rdf_client
from grr.server.grr_response_server import aff4
from grr.server.grr_response_server import flow
from grr.server.grr_response_server.checks import checks
from grr.server.grr_response_server.checks import checks_test_lib
from grr.server.grr_response_server.flows.general import checks as flow_checks
from grr.test_lib import action_mocks
from grr.test_lib import flow_test_lib
from grr.test_lib import test_lib
from grr.test_lib import vfs_test_lib

# pylint: mode=test


class TestCheckFlows(flow_test_lib.FlowTestsBaseclass,
                     checks_test_lib.HostCheckTest):

  checks_loaded = False

  def setUp(self):
    super(TestCheckFlows, self).setUp()
    self.client_id = self.SetupClient(0)
    # Only load the checks once.
    if self.checks_loaded is False:
      self.checks_loaded = self.LoadChecks()
    if not self.checks_loaded:
      raise RuntimeError("No checks to test.")
    self.client_mock = action_mocks.FileFinderClientMock()

  def SetLinuxKB(self):
    client = aff4.FACTORY.Open(self.client_id, token=self.token, mode="rw")
    kb = client.Schema.KNOWLEDGE_BASE()
    kb.os = "Linux"
    user = rdf_client.User(username="user1", homedir="/home/user1")
    kb.users = [user]
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
    with test_lib.Instrument(flow.GRRFlow, "SendReply") as send_reply:
      with vfs_test_lib.FakeTestDataVFSOverrider():
        session_id = flow_test_lib.TestFlowHelper(
            flow_checks.CheckRunner.__name__,
            client_mock=self.client_mock,
            client_id=self.client_id,
            token=self.token)
    session = aff4.FACTORY.Open(session_id, token=self.token)
    results = {
        r.check_id: r
        for _, r in send_reply.args
        if isinstance(r, checks.CheckResult)
    }
    return session, results

  def LoadChecks(self):
    """Load the checks, returning the names of the checks that were loaded."""
    checks.CheckRegistry.Clear()
    check_configs = ("sshd.yaml", "sw.yaml", "unix_login.yaml")
    cfg_dir = os.path.join(config.CONFIG["Test.data_dir"], "checks")
    chk_files = [os.path.join(cfg_dir, f) for f in check_configs]
    checks.LoadChecksFromFiles(chk_files)
    return checks.CheckRegistry.checks.keys()

  def testSelectArtifactsForChecks(self):
    self.SetLinuxKB()
    session, _ = self.RunFlow()
    self.assertTrue("DebianPackagesStatus" in session.state.artifacts_wanted)
    self.assertTrue("SshdConfigFile" in session.state.artifacts_wanted)

    self.SetWindowsKB()
    session, _ = self.RunFlow()
    self.assertTrue("WMIInstalledSoftware" in session.state.artifacts_wanted)

  def testCheckFlowSelectsChecks(self):
    """Confirm the flow runs checks for a target machine."""
    self.SetLinuxKB()
    _, results = self.RunFlow()
    expected = ["SHADOW-HASH", "SSHD-CHECK", "SSHD-PERMS", "SW-CHECK"]
    self.assertRanChecks(expected, results)

  def testChecksProcessResultContext(self):
    """Test the flow returns parser results."""
    self.SetLinuxKB()
    _, results = self.RunFlow()

    # Detected by result_context: PARSER
    exp = "Found: Sshd allows protocol 1."
    self.assertCheckDetectedAnom("SSHD-CHECK", results, exp)
    # Detected by result_context: RAW
    exp = "Found: The filesystem supports stat."
    found = ["/etc/ssh/sshd_config"]
    self.assertCheckDetectedAnom("SSHD-PERMS", results, exp, found)
    # Detected by result_context: ANOMALY
    exp = "Found: Unix system account anomalies."
    found = [
        "Accounts with invalid gid.", "Mismatched passwd and shadow files."
    ]
    self.assertCheckDetectedAnom("ODD-PASSWD", results, exp, found)
    # No findings.
    self.assertCheckUndetected("SHADOW-HASH", results)
    self.assertCheckUndetected("SW-CHECK", results)


def main(argv):
  # Run the full test suite
  test_lib.main(argv)


if __name__ == "__main__":
  flags.StartMain(main)
