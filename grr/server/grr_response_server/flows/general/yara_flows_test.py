#!/usr/bin/env python
"""Tests for Yara flows."""
from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

import functools
import string

from builtins import range  # pylint: disable=redefined-builtin
import psutil
import yara

from grr_response_client import client_utils
from grr_response_client import process_error
from grr_response_client.client_actions import tempfiles
from grr_response_client.client_actions import yara_actions
from grr_response_core.lib import flags
from grr_response_core.lib import utils
from grr_response_core.lib.rdfvalues import client_fs as rdf_client_fs
from grr_response_core.lib.rdfvalues import rdf_yara
from grr_response_server import aff4
from grr_response_server import data_store
from grr_response_server import db
from grr_response_server import file_store
from grr_response_server.aff4_objects import aff4_grr
from grr_response_server.flows.general import yara_flows
from grr.test_lib import action_mocks
from grr.test_lib import client_test_lib
from grr.test_lib import db_test_lib
from grr.test_lib import flow_test_lib
from grr.test_lib import test_lib

test_yara_signature = """
rule test_rule {
  meta:
    desc = "Just for testing."
  strings:
    $s1 = { 31 32 33 34 }
  condition:
    $s1
}
"""


class FakeMatch(object):

  strings = [(100, "$s1", b"1234"), (200, "$s1", b"1234")]

  def __init__(self, rule_name="test_rule"):
    self.rule = rule_name


class FakeRules(object):

  invocations = []
  rules = ["test_rule"]

  def __getitem__(self, item):
    return self.rules[item]

  def match(self, data=None, timeout=None):  # pylint:disable=invalid-name
    self.invocations.append((data, timeout))
    return []


class TimeoutRules(FakeRules):

  def match(self, data=None, timeout=None):  # pylint:disable=invalid-name
    del data, timeout
    raise yara.TimeoutError("Timed out.")


class TooManyHitsRules(FakeRules):

  def match(self, data=None, timeout=None):  # pylint:disable=invalid-name
    self.invocations.append((data, timeout))
    if len(self.invocations) >= 3:
      raise yara.Error("internal error: 30")
    return [FakeMatch("test_rule_%d" % len(self.invocations))]


def GeneratePattern(seed, length):
  if not b"A" <= seed <= b"Z":
    raise ValueError("Needs an upper case letter as seed")

  res = string.ascii_uppercase[string.ascii_uppercase.find(seed):]
  while len(res) < length:
    res += string.ascii_uppercase
  return res[:length]


class FakeMemoryProcess(object):

  regions_by_pid = {
      101: [],
      102: [(0, b"A" * 98 + b"1234" + b"B" * 50)],
      103: [(0, b"A" * 100), (10000, b"B" * 500)],
      104: [(0, b"A" * 100), (1000, b"X" * 50 + b"1234" + b"X" * 50)],
      105: [(0, GeneratePattern(b"A", 100)), (300, GeneratePattern(b"B", 700))],
      106: [],
      107: [(0, b"A" * 98 + b"1234" + b"B" * 50), (400, b"C" * 50 + b"1234")],
  }

  def __init__(self, pid=None):
    self.pid = pid
    self.regions = self.regions_by_pid[pid]

  def __enter__(self):
    if self.pid in [101, 106]:
      raise process_error.ProcessError("Access Denied.")
    return self

  def __exit__(self, exc_type=None, exc_val=None, exc_tb=None):
    pass

  def ReadBytes(self, address, num_bytes):
    for start, data in self.regions:
      if address >= start and address + num_bytes <= start + len(data):
        offset = address - start
        return data[offset:offset + num_bytes]

  def Regions(self,
              skip_mapped_files=False,
              skip_shared_regions=False,
              skip_executable_regions=False,
              skip_readonly_regions=False):
    del skip_mapped_files
    del skip_shared_regions
    del skip_executable_regions
    del skip_readonly_regions

    for start, data in self.regions:
      yield start, len(data)


@db_test_lib.DualDBTest
class TestYaraFlows(flow_test_lib.FlowTestsBaseclass):
  """Tests the Yara flows."""

  def process(self, processes, pid=None):
    if not pid:
      return psutil.Process.old_target()
    for p in processes:
      if p.pid == pid:
        return p
    raise psutil.NoSuchProcess("No process with pid %d." % pid)

  def _RunYaraProcessScan(self,
                          procs,
                          ignore_grr_process=False,
                          include_errors_in_results=False,
                          include_misses_in_results=False,
                          max_results_per_process=0,
                          **kw):
    client_mock = action_mocks.ActionMock(yara_actions.YaraProcessScan)

    with utils.MultiStubber(
        (psutil, "process_iter", lambda: procs),
        (psutil, "Process", functools.partial(self.process, procs)),
        (client_utils, "OpenProcessForMemoryAccess",
         lambda pid: FakeMemoryProcess(pid=pid))):
      session_id = flow_test_lib.TestFlowHelper(
          yara_flows.YaraProcessScan.__name__,
          client_mock,
          yara_signature=test_yara_signature,
          client_id=self.client_id,
          ignore_grr_process=ignore_grr_process,
          include_errors_in_results=include_errors_in_results,
          include_misses_in_results=include_misses_in_results,
          max_results_per_process=max_results_per_process,
          token=self.token,
          **kw)

    res = flow_test_lib.GetFlowResults(self.client_id.Basename(), session_id)
    matches = [r for r in res if isinstance(r, rdf_yara.YaraProcessScanMatch)]
    errors = [r for r in res if isinstance(r, rdf_yara.YaraProcessError)]
    misses = [r for r in res if isinstance(r, rdf_yara.YaraProcessScanMiss)]
    return (matches, errors, misses)

  def setUp(self):
    super(TestYaraFlows, self).setUp()
    self.client_id = self.SetupClient(0)
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

  def testYaraProcessScanWithMissesAndErrors(self):
    matches, errors, misses = self._RunYaraProcessScan(
        self.procs,
        include_misses_in_results=True,
        include_errors_in_results=True)

    self.assertLen(matches, 2)
    self.assertLen(errors, 2)
    self.assertLen(misses, 2)

    for scan_match in matches:
      for match in scan_match.match:
        self.assertEqual(match.rule_name, "test_rule")
        self.assertLen(match.string_matches, 1)
        for string_match in match.string_matches:
          self.assertEqual(string_match.data, b"1234")
          self.assertEqual(string_match.string_id, "$s1")
          self.assertIn(string_match.offset, [98, 1050])

  def testYaraProcessScanWithoutMissesAndErrors(self):
    matches, errors, misses = self._RunYaraProcessScan(self.procs)

    self.assertLen(matches, 2)
    self.assertEmpty(errors)
    self.assertEmpty(misses)

  def testYaraProcessScanWithMissesWithoutErrors(self):
    matches, errors, misses = self._RunYaraProcessScan(
        self.procs, include_misses_in_results=True)

    self.assertLen(matches, 2)
    self.assertEmpty(errors)
    self.assertLen(misses, 2)

  def testYaraProcessScanWithoutMissesWithErrors(self):
    matches, errors, misses = self._RunYaraProcessScan(
        self.procs, include_errors_in_results=True)

    self.assertLen(matches, 2)
    self.assertLen(errors, 2)
    self.assertEmpty(misses)

  def testYaraProcessScanLimitMatches(self):
    proc = client_test_lib.MockWindowsProcess(pid=107, name="proc107.exe")
    matches, _, _ = self._RunYaraProcessScan([proc])
    self.assertLen(matches[0].match, 2)
    matches, _, _ = self._RunYaraProcessScan([proc], max_results_per_process=1)
    self.assertLen(matches[0].match, 1)

  def testScanTimingInformation(self):
    with test_lib.FakeTime(10000, increment=1):
      _, _, misses = self._RunYaraProcessScan(
          self.procs, pids=[105], include_misses_in_results=True)

    self.assertLen(misses, 1)
    miss = misses[0]
    self.assertEqual(miss.scan_time_us, 4 * 1e6)

    with test_lib.FakeTime(10000, increment=1):
      matches, _, _ = self._RunYaraProcessScan(self.procs, pids=[102])

    self.assertLen(matches, 1)
    match = matches[0]
    self.assertEqual(match.scan_time_us, 3 * 1e6)

  def testPIDsRestriction(self):
    matches, errors, misses = self._RunYaraProcessScan(
        self.procs,
        pids=[101, 104, 105],
        include_errors_in_results=True,
        include_misses_in_results=True)

    self.assertLen(matches, 1)
    self.assertLen(errors, 1)
    self.assertLen(misses, 1)

  def testProcessRegex(self):
    matches, errors, misses = self._RunYaraProcessScan(
        self.procs,
        process_regex="10(3|6)",
        include_errors_in_results=True,
        include_misses_in_results=True)

    self.assertEmpty(matches)
    self.assertLen(errors, 1)
    self.assertLen(misses, 1)

  def testPerProcessTimeoutArg(self):
    FakeRules.invocations = []
    with utils.Stubber(rdf_yara.YaraSignature, "GetRules", FakeRules):
      self._RunYaraProcessScan(self.procs, per_process_timeout=50)

    self.assertLen(FakeRules.invocations, 7)
    for invocation in FakeRules.invocations:
      _, limit = invocation
      self.assertGreater(limit, 45)
      self.assertLessEqual(limit, 50)

  def testPerProcessTimeout(self):
    FakeRules.invocations = []
    with utils.Stubber(rdf_yara.YaraSignature, "GetRules", TimeoutRules):
      matches, errors, misses = self._RunYaraProcessScan(
          self.procs,
          per_process_timeout=50,
          include_errors_in_results=True,
          include_misses_in_results=True)

    self.assertEmpty(matches)
    self.assertLen(errors, 6)
    self.assertEmpty(misses)
    for e in errors:
      if e.process.pid in [101, 106]:
        self.assertEqual("Access Denied.", e.error)
      else:
        self.assertIn("Scanning timed out", e.error)

  def testTooManyHitsError(self):
    FakeRules.invocations = []
    with utils.Stubber(rdf_yara.YaraSignature, "GetRules", TooManyHitsRules):
      matches, errors, misses = self._RunYaraProcessScan(
          self.procs,
          include_errors_in_results=True,
          include_misses_in_results=True)

    # The third invocation raises too many hits, make sure we get the
    # first two matches anyways.
    self.assertLen(matches, 2)
    self.assertCountEqual([m.match[0].rule_name for m in matches],
                          ["test_rule_1", "test_rule_2"])
    self.assertLen(errors, 2)
    self.assertLen(misses, 2)

  def testYaraProcessScanChunkingWorks(self):
    FakeRules.invocations = []
    with utils.Stubber(rdf_yara.YaraSignature, "GetRules", FakeRules):
      self._RunYaraProcessScan(self.procs, chunk_size=100, overlap_size=10)

    self.assertLen(FakeRules.invocations, 21)
    for data, _ in FakeRules.invocations:
      self.assertLessEqual(len(data), 100)

  def testMatchSpanningChunks(self):
    # Process 102 has a hit spanning bytes 98-102, let's set the chunk
    # size around that.
    for chunk_size in range(97, 104):
      matches, errors, misses = self._RunYaraProcessScan(
          self.procs,
          chunk_size=chunk_size,
          overlap_size=10,
          pids=[102],
          include_errors_in_results=True,
          include_misses_in_results=True)

      self.assertLen(matches, 1)
      self.assertEmpty(misses)
      self.assertEmpty(errors)

  def testDoubleMatchesAreAvoided(self):
    # Process 102 has a hit going from 98-102. If we set the chunk
    # size a bit larger than that, the hit will be scanned twice. We
    # still expect a single match only.
    matches, _, _ = self._RunYaraProcessScan(
        self.procs, chunk_size=105, overlap_size=10, pids=[102])

    self.assertLen(matches, 1)
    self.assertLen(matches[0].match, 1)

  def _RunProcessDump(self, pids=None, size_limit=None, chunk_size=None):

    procs = self.procs
    with utils.MultiStubber(
        (psutil, "process_iter", lambda: procs),
        (psutil, "Process", functools.partial(self.process, procs)),
        (client_utils, "OpenProcessForMemoryAccess",
         lambda pid: FakeMemoryProcess(pid=pid))):
      client_mock = action_mocks.MultiGetFileClientMock(
          yara_actions.YaraProcessDump, tempfiles.DeleteGRRTempFiles)
      session_id = flow_test_lib.TestFlowHelper(
          yara_flows.YaraDumpProcessMemory.__name__,
          client_mock,
          pids=pids or [105],
          size_limit=size_limit,
          chunk_size=chunk_size,
          client_id=self.client_id,
          ignore_grr_process=True,
          token=self.token)
    return flow_test_lib.GetFlowResults(self.client_id.Basename(), session_id)

  def _ReadFromPathspec(self, pathspec, num_bytes):
    if data_store.AFF4Enabled():
      image = aff4.FACTORY.Open(
          pathspec.AFF4Path(self.client_id), aff4_grr.VFSBlobImage)
      return image.read(num_bytes)
    else:
      fd = file_store.OpenFile(
          db.ClientPath.FromPathSpec(self.client_id.Basename(), pathspec))
      return fd.read(num_bytes)

  def testYaraProcessDump(self):
    results = self._RunProcessDump()

    self.assertLen(results, 3)
    for result in results:
      if isinstance(result, rdf_client_fs.StatEntry):
        self.assertIn("proc105.exe_105", result.pathspec.path)

        data = self._ReadFromPathspec(result.pathspec, 1000)

        self.assertIn(data,
                      [GeneratePattern(b"A", 100),
                       GeneratePattern(b"B", 700)])
      elif isinstance(result, rdf_yara.YaraProcessDumpResponse):
        self.assertLen(result.dumped_processes, 1)
        self.assertEqual(result.dumped_processes[0].process.pid, 105)
      else:
        self.fail("Unexpected result type %s" % type(result))

  def testYaraProcessDumpChunked(self):
    with test_lib.Instrument(FakeMemoryProcess, "ReadBytes") as read_func:
      results = self._RunProcessDump(chunk_size=11)

      # Check that the chunked reads actually happened. Should be 74 reads:
      # 100 / 11 + 700 / 11 = 9.1 + 63.6 -> 10 + 64 reads
      self.assertLen(read_func.args, 74)

    self.assertLen(results, 3)
    for result in results:
      if isinstance(result, rdf_client_fs.StatEntry):
        self.assertIn("proc105.exe_105", result.pathspec.path)

        data = self._ReadFromPathspec(result.pathspec, 1000)

        self.assertIn(data,
                      [GeneratePattern(b"A", 100),
                       GeneratePattern(b"B", 700)])
      elif isinstance(result, rdf_yara.YaraProcessDumpResponse):
        self.assertLen(result.dumped_processes, 1)
        self.assertEqual(result.dumped_processes[0].process.pid, 105)
      else:
        self.fail("Unexpected result type %s" % type(result))

  def testYaraProcessDumpWithLimit(self):
    results = self._RunProcessDump(size_limit=150)

    # Now we should only get one block (+ the YaraProcessDumpResponse), the
    # second is over the limit.
    self.assertLen(results, 2)

    for result in results:
      if isinstance(result, rdf_client_fs.StatEntry):
        self.assertIn("proc105.exe_105", result.pathspec.path)

        data = self._ReadFromPathspec(result.pathspec, 1000)

        self.assertEqual(data, GeneratePattern(b"A", 100))
      elif isinstance(result, rdf_yara.YaraProcessDumpResponse):
        self.assertLen(result.dumped_processes, 1)
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
      flow_test_lib.TestFlowHelper(
          yara_flows.YaraDumpProcessMemory.__name__,
          client_mock,
          client_id=self.client_id,
          ignore_grr_process=True,
          token=self.token)

  def testDumpTimingInformation(self):
    with test_lib.FakeTime(100000, 0.1):
      results = self._RunProcessDump()

    self.assertGreater(len(results), 1)
    self.assertIsInstance(results[0], rdf_yara.YaraProcessDumpResponse)
    self.assertLen(results[0].dumped_processes, 1)
    self.assertEqual(results[0].dumped_processes[0].dump_time_us, 0.1 * 1e6)

  def testScanAndDump(self):
    client_mock = action_mocks.MultiGetFileClientMock(
        yara_actions.YaraProcessScan, yara_actions.YaraProcessDump,
        tempfiles.DeleteGRRTempFiles)

    procs = [p for p in self.procs if p.pid in [102, 103]]

    with utils.MultiStubber(
        (psutil, "process_iter", lambda: procs),
        (psutil, "Process", functools.partial(self.process, procs)),
        (client_utils, "OpenProcessForMemoryAccess",
         lambda pid: FakeMemoryProcess(pid=pid))):
      session_id = flow_test_lib.TestFlowHelper(
          yara_flows.YaraProcessScan.__name__,
          client_mock,
          yara_signature=test_yara_signature,
          client_id=self.client_id,
          token=self.token,
          include_errors_in_results=True,
          include_misses_in_results=True,
          dump_process_on_match=True)

    results = flow_test_lib.GetFlowResults(self.client_id.Basename(),
                                           session_id)

    # 1. Scan result match.
    # 2. Scan result miss.
    # 3. ProcDump response.
    # 4. Stat entry for the dumped file.
    self.assertLen(results, 4)
    self.assertIsInstance(results[0], rdf_yara.YaraProcessScanMatch)
    self.assertIsInstance(results[1], rdf_yara.YaraProcessScanMiss)
    self.assertIsInstance(results[2], rdf_yara.YaraProcessDumpResponse)
    self.assertIsInstance(results[3], rdf_client_fs.StatEntry)

    self.assertLen(results[2].dumped_processes, 1)
    self.assertEqual(results[0].process.pid,
                     results[2].dumped_processes[0].process.pid)
    self.assertIn(
        str(results[2].dumped_processes[0].process.pid),
        results[3].pathspec.path)


def main(argv):
  # Run the full test suite
  test_lib.main(argv)


if __name__ == "__main__":
  flags.StartMain(main)
