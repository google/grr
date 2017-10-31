#!/usr/bin/env python
"""Tests for Yara flows."""

import functools
import psutil
import yara
import yara_procdump

from grr.client.client_actions import tempfiles
from grr.client.client_actions import yara_actions
from grr.lib import flags
from grr.lib import utils
from grr.lib.rdfvalues import client as rdf_client
from grr.lib.rdfvalues import rdf_yara
from grr.server import aff4
from grr.server import flow
from grr.server.aff4_objects import aff4_grr
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


class FakeMemoryBlock(bytearray):

  def __init__(self, data="", base=0):
    super(FakeMemoryBlock, self).__init__(data)
    self._data = data
    self.size = len(data)
    self.base = base

  def data(self):
    return self._data


class TestYaraFlows(flow_test_lib.FlowTestsBaseclass):
  """Tests the Yara flows."""

  def process(self, processes, pid=None):
    if not pid:
      return psutil.Process.old_target()
    for p in processes:
      if p.pid == pid:
        return p
    raise psutil.NoSuchProcess("No process with pid %d." % pid)

  def _RunYaraProcessScan(self, procs, rules, ignore_grr_process=False, **kw):
    client_mock = action_mocks.ActionMock(yara_actions.YaraProcessScan)

    with utils.MultiStubber(
        (psutil, "process_iter", lambda: procs),
        (psutil, "Process", functools.partial(self.process, procs)),
        (rdf_yara.YaraSignature, "GetRules", lambda self: rules)):
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

  def testScanTimingInformation(self):
    with test_lib.FakeTime(10000, increment=1):
      response = self._RunYaraProcessScan(self.procs, self.rules, pids=[105])

    self.assertEqual(len(response.misses), 1)
    miss = response.misses[0]
    self.assertEqual(miss.scan_time_us, 1 * 1e6)

    with test_lib.FakeTime(10000, increment=1):
      response = self._RunYaraProcessScan(self.procs, self.rules, pids=[101])

    self.assertEqual(len(response.matches), 1)
    match = response.matches[0]
    self.assertEqual(match.scan_time_us, 1 * 1e6)

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

  def _RunProcessDump(self, pids=None, size_limit=None):

    def FakeProcessMemoryIterator(pid=None):  # pylint: disable=invalid-name
      del pid
      mem_blocks = [
          FakeMemoryBlock("A" * 100, 1024),
          FakeMemoryBlock("B" * 100, 2048),
      ]
      for m in mem_blocks:
        yield m

    procs = self.procs
    with utils.MultiStubber(
        (psutil, "process_iter", lambda: procs),
        (psutil, "Process", functools.partial(self.process, procs)),
        (yara_procdump, "process_memory_iterator", FakeProcessMemoryIterator)):
      client_mock = action_mocks.MultiGetFileClientMock(
          yara_actions.YaraProcessDump, tempfiles.DeleteGRRTempFiles)
      for s in flow_test_lib.TestFlowHelper(
          yara_flows.YaraDumpProcessMemory.__name__,
          client_mock,
          pids=pids or [105],
          size_limit=size_limit,
          client_id=self.client_id,
          ignore_grr_process=True,
          token=self.token):
        session_id = s
    flow_obj = aff4.FACTORY.Open(session_id, flow.GRRFlow)
    return flow_obj.ResultCollection()

  def testYaraProcessDump(self):
    results = self._RunProcessDump()

    self.assertEqual(len(results), 3)
    for result in results:
      if isinstance(result, rdf_client.StatEntry):
        self.assertIn("proc105.exe_105", result.pathspec.path)

        image = aff4.FACTORY.Open(
            result.pathspec.AFF4Path(self.client_id), aff4_grr.VFSBlobImage)
        data = image.read(1000)

        self.assertIn(data, ["A" * 100, "B" * 100])
      elif isinstance(result, rdf_yara.YaraProcessDumpResponse):
        self.assertEqual(len(result.dumped_processes), 1)
        self.assertEqual(result.dumped_processes[0].process.pid, 105)
      else:
        self.fail("Unexpected result type %s" % type(result))

  def testYaraProcessDumpWithLimit(self):
    results = self._RunProcessDump(size_limit=150)

    # Now we should only get one block (+ the YaraProcessDumpResponse), the
    # second is over the limit.
    self.assertEqual(len(results), 2)

    for result in results:
      if isinstance(result, rdf_client.StatEntry):
        self.assertIn("proc105.exe_105", result.pathspec.path)

        image = aff4.FACTORY.Open(
            result.pathspec.AFF4Path(self.client_id), aff4_grr.VFSBlobImage)
        data = image.read(1000)

        self.assertEqual(data, "A" * 100)
      elif isinstance(result, rdf_yara.YaraProcessDumpResponse):
        self.assertEqual(len(result.dumped_processes), 1)
        self.assertEqual(result.dumped_processes[0].process.pid, 105)
        self.assertIn("limit exceeded", result.dumped_processes[0].error)
      else:
        self.fail("Unexpected result type %s" % type(result))

  def testYaraProcessDumpByDefaultErrors(self):
    # This tests that not specifying any restrictions on the processes
    # to dump does not dump them all which would return tons of data.
    client_mock = action_mocks.MultiGetFileClientMock(
        yara_actions.YaraProcessDump, tempfiles.DeleteGRRTempFiles)
    with self.assertRaises(ValueError):
      for _ in flow_test_lib.TestFlowHelper(
          yara_flows.YaraDumpProcessMemory.__name__,
          client_mock,
          client_id=self.client_id,
          ignore_grr_process=True,
          token=self.token):
        pass

  def testDumpTimingInformation(self):
    with test_lib.FakeTime(100000, 1):
      results = self._RunProcessDump()

    self.assertGreater(len(results), 1)
    self.assertIsInstance(results[0], rdf_yara.YaraProcessDumpResponse)
    self.assertEqual(len(results[0].dumped_processes), 1)
    self.assertEqual(results[0].dumped_processes[0].dump_time_us, 1 * 1e6)


def main(argv):
  # Run the full test suite
  test_lib.main(argv)


if __name__ == "__main__":
  flags.StartMain(main)
