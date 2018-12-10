#!/usr/bin/env python
"""Test the collector flows."""
from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

import os

from future.utils import iterkeys

from grr_response_core import config
from grr_response_core.lib import flags
from grr_response_core.lib.parsers import config_file
from grr_response_core.lib.parsers import linux_file_parser
from grr_response_core.lib.rdfvalues import client as rdf_client
from grr_response_server.check_lib import checks
from grr_response_server.check_lib import checks_test_lib
from grr_response_server.flows.general import checks as flow_checks
from grr.test_lib import action_mocks
from grr.test_lib import db_test_lib
from grr.test_lib import flow_test_lib
from grr.test_lib import parser_test_lib
from grr.test_lib import test_lib
from grr.test_lib import vfs_test_lib

# pylint: mode=test


@db_test_lib.DualDBTest
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

  def SetupLinuxUser(self):
    user = rdf_client.User(username="user1", homedir="/home/user1")
    return self.SetupClient(0, system="Linux", users=[user], os_version="12.04")

  def SetupWindowsUser(self):
    return self.SetupClient(0, system="Windows", os_version="6.2")

  def RunFlow(self, client_id):
    with vfs_test_lib.FakeTestDataVFSOverrider():
      session_id = flow_test_lib.TestFlowHelper(
          flow_checks.CheckRunner.__name__,
          client_mock=self.client_mock,
          client_id=client_id,
          token=self.token)
    results = flow_test_lib.GetFlowResults(client_id, session_id)
    return session_id, {r.check_id: r for r in results}

  def LoadChecks(self):
    """Load the checks, returning the names of the checks that were loaded."""
    checks.CheckRegistry.Clear()
    check_configs = ("sshd.yaml", "sw.yaml", "unix_login.yaml")
    cfg_dir = os.path.join(config.CONFIG["Test.data_dir"], "checks")
    chk_files = [os.path.join(cfg_dir, f) for f in check_configs]
    checks.LoadChecksFromFiles(chk_files)
    return list(iterkeys(checks.CheckRegistry.checks))

  def testSelectArtifactsForChecks(self):
    client_id = self.SetupLinuxUser()
    session_id, _ = self.RunFlow(client_id)

    state = flow_test_lib.GetFlowState(
        self.client_id, session_id, token=self.token)
    self.assertIn("DebianPackagesStatus", state.artifacts_wanted)
    self.assertIn("SshdConfigFile", state.artifacts_wanted)

    client_id = self.SetupWindowsUser()
    session_id, _ = self.RunFlow(client_id)
    state = flow_test_lib.GetFlowState(
        self.client_id, session_id, token=self.token)
    self.assertIn("WMIInstalledSoftware", state.artifacts_wanted)

  def testCheckFlowSelectsChecks(self):
    """Confirm the flow runs checks for a target machine."""
    client_id = self.SetupLinuxUser()
    _, results = self.RunFlow(client_id)
    expected = ["SHADOW-HASH", "SSHD-CHECK", "SSHD-PERMS", "SW-CHECK"]
    self.assertRanChecks(expected, results)

  @parser_test_lib.WithParser("Sshd", config_file.SshdConfigParser)
  @parser_test_lib.WithParser("Pswd", linux_file_parser.LinuxSystemPasswdParser)
  def testChecksProcessResultContext(self):
    """Test the flow returns parser results."""
    client_id = self.SetupLinuxUser()
    _, results = self.RunFlow(client_id)

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
