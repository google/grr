#!/usr/bin/env python
"""Tests for Yara flows."""

import psutil
import yara

from grr.client.client_actions import yara_actions
from grr.lib import flags
from grr.lib import utils
from grr.lib.rdfvalues import rdf_yara
from grr.server import aff4
from grr.server.flows.general import yara_flows
from grr.test_lib import action_mocks
from grr.test_lib import client_test_lib
from grr.test_lib import flow_test_lib
from grr.test_lib import test_lib

test_yara_signature = """
private rule test_rule {
  meta:
    desc = "Just for testing."
  strings:
    $s1 = { 31 32 33 34 }
  condition:
    $s1
}
"""


class FakeMatch(object):

  strings = [(100, "$s1", "1234"), (200, "$s1", "1234")]
  rule = "test_rule"


class FakeRules(object):

  invocations = None

  def __init__(self, matching_pids=None, timeout_pids=None):
    # Creating a new FakeRule clears the invocation log.
    FakeRules.invocations = []
    self.matching_pids = matching_pids or []
    self.timeout_pids = timeout_pids or []

  def match(self, pid=None, timeout=None):
    self.invocations.append((pid, timeout))
    if pid and pid in self.timeout_pids:
      raise yara.TimeoutError("Timeout")
    if pid and pid in self.matching_pids:
      return [FakeMatch()]

    return []


class TestYaraFlows(flow_test_lib.FlowTestsBaseclass):
  """Tests the Yara flows."""

  def _RunYaraProcessScan(self, procs, rules, ignore_grr_process=False, **kw):
    client_mock = action_mocks.ActionMock(yara_actions.YaraProcessScan)

    with utils.MultiStubber((psutil, "process_iter", lambda: procs),
                            (rdf_yara.YaraSignature, "GetRules",
                             lambda self: rules)):
      for s in flow_test_lib.TestFlowHelper(
          yara_flows.YaraProcessScan.__name__,
          client_mock,
          yara_signature=test_yara_signature,
          client_id=self.client_id,
          ignore_grr_process=ignore_grr_process,
          token=self.token,
          **kw):
        session_id = s

    flow_obj = aff4.FACTORY.Open(session_id)
    self.assertEqual(len(flow_obj.ResultCollection()), 1)
    return flow_obj.ResultCollection()[0]

  def setUp(self):
    super(TestYaraFlows, self).setUp()
    self.rules = FakeRules(matching_pids=[101, 102], timeout_pids=[103, 104])
    self.procs = [
        client_test_lib.MockWindowsProcess(pid=101, name="proc101.exe"),
        client_test_lib.MockWindowsProcess(
            pid=102, name="proc102.exe", ppid=101),
        client_test_lib.MockWindowsProcess(pid=103, name="proc103.exe", ppid=1),
        client_test_lib.MockWindowsProcess(
            pid=104, name="proc104.exe", ppid=103),
        client_test_lib.MockWindowsProcess(pid=105, name="proc105.exe", ppid=1),
        client_test_lib.MockWindowsProcess(
            pid=106, name="proc106.exe", ppid=104)
    ]

  def testYaraProcessScan(self):
    response = self._RunYaraProcessScan(self.procs, self.rules)

    self.assertEqual(len(response.matches), 2)
    self.assertEqual(len(response.misses), 2)
    self.assertEqual(len(response.errors), 2)

    for scan_match in response.matches:
      for match in scan_match.match:
        self.assertEqual(match.rule_name, "test_rule")
        self.assertEqual(len(match.string_matches), 2)
        for string_match in match.string_matches:
          self.assertEqual(string_match.data, "1234")
          self.assertEqual(string_match.string_id, "$s1")
          self.assertIn(string_match.offset, [100, 200])

  def testPIDsRestriction(self):
    response = self._RunYaraProcessScan(
        self.procs, self.rules, pids=[101, 103, 105])

    self.assertEqual(len(response.matches), 1)
    self.assertEqual(len(response.misses), 1)
    self.assertEqual(len(response.errors), 1)

  def testProcessRegex(self):
    response = self._RunYaraProcessScan(
        self.procs, self.rules, process_regex="10(3|5)")

    self.assertEqual(len(response.matches), 0)
    self.assertEqual(len(response.misses), 1)
    self.assertEqual(len(response.errors), 1)

  def testPerProcessTimeout(self):
    self._RunYaraProcessScan(self.procs, self.rules, per_process_timeout=50)

    self.assertEqual(len(FakeRules.invocations), 6)
    for invocation in FakeRules.invocations:
      pid, limit = invocation
      self.assertLessEqual(101, pid)
      self.assertLessEqual(pid, 106)
      self.assertEqual(limit, 50)


def main(argv):
  # Run the full test suite
  test_lib.main(argv)


if __name__ == "__main__":
  flags.StartMain(main)
