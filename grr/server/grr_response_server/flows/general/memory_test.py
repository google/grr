#!/usr/bin/env python
"""Tests for Yara flows."""

from collections.abc import Iterable, Sequence
import contextlib
import functools
import inspect
import os
import platform
import string
from typing import Optional
import unittest
from unittest import mock

from absl import app
import psutil
import yara

from grr_response_client import client_utils
from grr_response_client import process_error
from grr_response_client.client_actions import memory as memory_actions
from grr_response_client.client_actions import tempfiles
from grr_response_core.lib import rdfvalue
from grr_response_core.lib import utils
from grr_response_core.lib.rdfvalues import client_fs as rdf_client_fs
from grr_response_core.lib.rdfvalues import memory as rdf_memory
from grr_response_core.lib.rdfvalues import paths as rdf_paths
from grr_response_proto import flows_pb2
from grr_response_proto import jobs_pb2
from grr_response_server import data_store
from grr_response_server import file_store
from grr_response_server import flow_responses
from grr_response_server.databases import db
from grr_response_server.flows.general import memory
from grr_response_server.rdfvalues import flow_objects as rdf_flow_objects
from grr_response_server.rdfvalues import mig_flow_objects
from grr.test_lib import action_mocks
from grr.test_lib import client_test_lib
from grr.test_lib import flow_test_lib
from grr.test_lib import test_lib
from grr.test_lib import testing_startup


ONE_MIB = 1024 * 1024

_TEST_YARA_SIGNATURE = """
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
  def __init__(self, rule_name="test_rule"):
    self.rule = rule_name

  @property
  def strings(self):
    r1 = mock.Mock()
    r1.identifier = "$s1"
    r1.instances = [mock.Mock()]
    r1.instances[0].offset = 100
    r1.instances[0].matched_data = b"1234"
    r1.instances[0].matched_length = 4

    r2 = mock.Mock()
    r2.identifier = "$s1"
    r2.instances = [mock.Mock()]
    r2.instances[0].offset = 200
    r2.instances[0].matched_data = b"1234"
    r2.instances[0].matched_length = 4
    return [r1, r2]


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

  ascii_uppercase = b"".join(_.encode("ascii") for _ in string.ascii_uppercase)

  res = ascii_uppercase[ascii_uppercase.find(seed) :]
  while len(res) < length:
    res += ascii_uppercase
  return res[:length]


class FakeRegion(object):

  def __init__(
      self,
      start=0,
      data=b"",
      is_executable=False,
      is_writable=False,
      is_readable=True,
  ):
    self.start = start
    self.data = data
    self.is_executable = is_executable
    self.is_writable = is_writable
    self.is_readable = is_readable

  @property
  def size(self):
    return len(self.data)

  @property
  def end(self):
    return self.start + self.size


class FakeMemoryProcess(object):

  regions_by_pid = {
      101: [],
      102: [FakeRegion(0, b"A" * 98 + b"1234" + b"B" * 50)],
      103: [FakeRegion(0, b"A" * 100), FakeRegion(10000, b"B" * 500)],
      104: [
          FakeRegion(0, b"A" * 100),
          FakeRegion(1000, b"X" * 50 + b"1234" + b"X" * 50),
      ],
      105: [
          FakeRegion(0, GeneratePattern(b"A", 100)),
          FakeRegion(300, GeneratePattern(b"B", 700)),
      ],
      106: [],
      107: [
          FakeRegion(0, b"A" * 98 + b"1234" + b"B" * 50),
          FakeRegion(400, b"C" * 50 + b"1234"),
      ],
      108: [
          FakeRegion(0, b"A" * 100, is_executable=True, is_writable=True),
          FakeRegion(1000, b"X" * 50 + b"1234" + b"X" * 50),
      ],
      109: [
          FakeRegion(0, b"A" * 100),
          FakeRegion(100, b"B"),
          FakeRegion(101, b"X" * 50 + b"1234" + b"X" * 50),
      ],
      110: [
          FakeRegion(0, b"A" * 100),
          FakeRegion(1000, b"X" * ONE_MIB + b"1234" + b"X" * ONE_MIB),
          FakeRegion(3000000, b"A" * 100),
      ],
  }

  def __init__(self, pid=None, tmp_dir=None):
    self.pid = pid
    self.regions = self.regions_by_pid[pid]
    self._tmp_dir = tmp_dir
    self._file_descriptor = None

  def __enter__(self):
    if self.pid in [101, 106]:
      raise process_error.ProcessError("Access Denied.")
    return self

  def __exit__(self, exc_type=None, exc_val=None, exc_tb=None):
    if self._file_descriptor is not None:
      os.close(self._file_descriptor)

  def ReadBytes(self, address, num_bytes):
    for region in self.regions:
      if address >= region.start and address + num_bytes <= region.end:
        offset = address - region.start
        return region.data[offset : offset + num_bytes]

  def Regions(
      self,
      skip_mapped_files=False,
      skip_shared_regions=False,
      skip_executable_regions=False,
      skip_readonly_regions=False,
  ):
    del skip_mapped_files
    del skip_shared_regions
    del skip_executable_regions
    del skip_readonly_regions

    for region in self.regions:
      yield rdf_memory.ProcessMemoryRegion(
          start=region.start,
          size=region.size,
          is_executable=region.is_executable,
          is_writable=region.is_writable,
          is_readable=region.is_readable,
      )

  @property
  def serialized_file_descriptor(self):
    if self._file_descriptor is not None:
      return self._file_descriptor
    memory_path = self._WriteMemoryToFile()
    self._file_descriptor = os.open(memory_path, os.O_RDONLY)
    return self._file_descriptor

  def _WriteMemoryToFile(self) -> str:
    memory_path = os.path.join(self._tmp_dir, str(self.pid))
    prev_region = None
    with open(memory_path, "wb") as f:
      for region in self.regions:
        if prev_region is None:
          prev_end = 0
        else:
          prev_end = prev_region.end
        assert region.start >= prev_end
        f.write(b"\x00" * (region.start - prev_end))
        f.write(region.data)
        prev_region = region
    return memory_path


class BaseYaraFlowsTest(flow_test_lib.FlowTestsBaseclass):
  """Tests the Yara flows."""

  NO_MATCH_PIDS = (101, 103, 105, 106)
  MATCH_PID_1_REGION = 102
  MATCH_PID_2_REGIONS = 108
  MATCH_BIG_REGIONS = 110

  def process(self, processes, pid=None):
    for stack_frame in inspect.stack():
      # grr_response_client/unprivileged/communication.py needs a real process.
      if (
          "unprivileged" in stack_frame.filename
          and "communication.py" in stack_frame.filename
      ):
        return psutil.Process.old_target(pid=pid)  # pytype: disable=attribute-error
    if not pid:
      return psutil.Process.old_target()  # pytype: disable=attribute-error
    for p in processes:
      if p.pid == pid:
        return p
    raise psutil.NoSuchProcess("No process with pid %d." % pid)

  def _RunYaraProcessScan(
      self,
      procs: Sequence[client_test_lib.MockWindowsProcess],
      action_mock: Optional[action_mocks.ActionMock] = None,
      ignore_grr_process: bool = False,
      include_errors_in_results: rdf_memory.YaraProcessScanRequest.ErrorPolicy = "NO_ERRORS",
      include_misses_in_results: bool = False,
      max_results_per_process: int = 0,
      pids: Optional[Sequence[int]] = None,
      process_regex: Optional[str] = None,
      per_process_timeout: Optional[int] = None,
      overlap_size: Optional[int] = None,
      chunk_size: Optional[int] = None,
      scan_runtime_limit_us: Optional[rdfvalue.Duration] = None,
      runtime_limit: Optional[rdfvalue.Duration] = None,
  ):
    if action_mock is None:
      client_mock = action_mocks.ActionMock(memory_actions.YaraProcessScan)
    else:
      client_mock = action_mock

    with utils.MultiStubber(
        (psutil, "process_iter", lambda: procs),
        (psutil, "Process", functools.partial(self.process, procs)),
        (
            client_utils,
            "OpenProcessForMemoryAccess",
            lambda pid: FakeMemoryProcess(pid=pid, tmp_dir=self._tmp_dir),
        ),
    ):
      session_id = flow_test_lib.StartAndRunFlow(
          memory.YaraProcessScan,
          client_mock,
          client_id=self.client_id,
          flow_args=rdf_memory.YaraProcessScanRequest(
              yara_signature=_TEST_YARA_SIGNATURE,
              ignore_grr_process=ignore_grr_process,
              include_errors_in_results=include_errors_in_results,
              include_misses_in_results=include_misses_in_results,
              max_results_per_process=max_results_per_process,
              pids=pids,
              process_regex=process_regex,
              per_process_timeout=per_process_timeout,
              overlap_size=overlap_size,
              chunk_size=chunk_size,
              scan_runtime_limit_us=scan_runtime_limit_us,
          ),
          runtime_limit=runtime_limit,
          creator=self.test_username,
      )

    res = flow_test_lib.GetFlowResults(self.client_id, session_id)
    matches = [r for r in res if isinstance(r, rdf_memory.YaraProcessScanMatch)]
    errors = [r for r in res if isinstance(r, rdf_memory.ProcessMemoryError)]
    misses = [r for r in res if isinstance(r, rdf_memory.YaraProcessScanMiss)]
    return matches, errors, misses

  def setUp(self):
    super().setUp()

    stack = contextlib.ExitStack()
    self.addCleanup(stack.close)
    self._tmp_dir = stack.enter_context(utils.TempDirectory())

    self.client_id = self.SetupClient(0)
    self.procs = [
        client_test_lib.MockWindowsProcess(pid=101, name="proc101.exe"),
        client_test_lib.MockWindowsProcess(
            pid=102, name="proc102.exe", ppid=101
        ),
        client_test_lib.MockWindowsProcess(pid=103, name="proc103.exe", ppid=1),
        client_test_lib.MockWindowsProcess(
            pid=104, name="proc104.exe", ppid=103
        ),
        client_test_lib.MockWindowsProcess(pid=105, name="proc105.exe", ppid=1),
        client_test_lib.MockWindowsProcess(
            pid=106, name="proc106.exe", ppid=104
        ),
        client_test_lib.MockWindowsProcess(pid=108, name="proc108.exe"),
        client_test_lib.MockWindowsProcess(pid=109, name="proc109.exe"),
        client_test_lib.MockWindowsProcess(pid=110, name="proc110.exe"),
    ]


class YaraFlowsTest(BaseYaraFlowsTest):
  """Tests the Yara flows."""

  def testIncludePrivilegedErrors(self):
    procs = [p for p in self.procs if p.pid in [101, 106]]
    matches, errors, misses = self._RunYaraProcessScan(
        procs,
        include_misses_in_results=True,
        include_errors_in_results="ALL_ERRORS",
    )

    self.assertLen(matches, 0)
    self.assertLen(errors, 2)
    self.assertLen(misses, 0)

  def testIgnorePrivilegedErrors(self):
    procs = [p for p in self.procs if p.pid in [101, 106]]
    matches, errors, misses = self._RunYaraProcessScan(
        procs,
        include_misses_in_results=True,
        include_errors_in_results="CRITICAL_ERRORS",
    )

    self.assertLen(matches, 0)
    self.assertLen(errors, 0)
    self.assertLen(misses, 0)

  def testYaraProcessScanWithMissesAndErrors(self):
    procs = [
        p for p in self.procs if p.pid in [101, 102, 103, 104, 105, 106, 107]
    ]
    with test_lib.FakeTime(
        rdfvalue.RDFDatetime.FromMicrosecondsSinceEpoch(123456789)
    ):
      matches, errors, misses = self._RunYaraProcessScan(
          procs,
          include_misses_in_results=True,
          include_errors_in_results="ALL_ERRORS",
      )

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

  @mock.patch.object(memory, "_YARA_SIGNATURE_SHARD_SIZE", 1 << 30)
  def testYaraProcessScan_SingleSignatureShard(self):
    action_mock = action_mocks.ActionMock(memory_actions.YaraProcessScan)
    procs = [
        p for p in self.procs if p.pid in [101, 102, 103, 104, 105, 106, 107]
    ]
    scan_params = {
        "include_misses_in_results": True,
        "include_errors_in_results": "ALL_ERRORS",
        "max_results_per_process": 0,
        "ignore_grr_process": False,
    }
    with test_lib.FakeTime(
        rdfvalue.RDFDatetime.FromMicrosecondsSinceEpoch(123456789)
    ):
      matches, errors, misses = self._RunYaraProcessScan(
          procs, action_mock=action_mock, **scan_params
      )

    # Verify scan results.
    self.assertLen(matches, 2)
    self.assertLen(errors, 2)
    self.assertLen(misses, 2)
    self.assertEqual(matches[0].match[0].rule_name, "test_rule")
    self.assertEqual(matches[0].match[0].string_matches[0].data, b"1234")

    flow = data_store.REL_DB.ReadAllFlowObjects(
        self.client_id, include_child_flows=False
    )[0]
    # We expect to have sent 1 YaraProcessScanRequest to the client.
    self.assertEqual(flow.next_outbound_id, 2)
    self.assertEqual(
        action_mock.recorded_messages[0].session_id.Basename(), flow.flow_id
    )
    scan_requests = action_mock.recorded_args["YaraProcessScan"]
    expected_request = rdf_memory.YaraProcessScanRequest(
        signature_shard=rdf_memory.YaraSignatureShard(
            index=0, payload=_TEST_YARA_SIGNATURE.encode("utf-8")
        ),
        num_signature_shards=1,
        **scan_params,
    )
    self.assertListEqual(scan_requests, [expected_request])

  @mock.patch.object(memory, "_YARA_SIGNATURE_SHARD_SIZE", 30)
  def testYaraProcessScan_MultipleSignatureShards(self):
    action_mock = action_mocks.ActionMock(memory_actions.YaraProcessScan)
    procs = [
        p for p in self.procs if p.pid in [101, 102, 103, 104, 105, 106, 107]
    ]
    scan_params = {
        "include_misses_in_results": True,
        "include_errors_in_results": "ALL_ERRORS",
        "max_results_per_process": 0,
        "ignore_grr_process": False,
    }
    with test_lib.FakeTime(
        rdfvalue.RDFDatetime.FromMicrosecondsSinceEpoch(123456789)
    ):
      matches, errors, misses = self._RunYaraProcessScan(
          procs, action_mock=action_mock, **scan_params
      )

    # Verify scan results.
    self.assertLen(matches, 2)
    self.assertLen(errors, 2)
    self.assertLen(misses, 2)
    self.assertEqual(matches[0].match[0].rule_name, "test_rule")
    self.assertEqual(matches[0].match[0].string_matches[0].data, b"1234")

    flow = data_store.REL_DB.ReadAllFlowObjects(
        self.client_id, include_child_flows=False
    )[0]
    # We expect to have sent 4 YaraProcessScanRequests to the client.
    self.assertEqual(flow.next_outbound_id, 5)
    scan_requests = action_mock.recorded_args["YaraProcessScan"]
    signature_bytes = _TEST_YARA_SIGNATURE.encode("utf-8")
    expected_requests = [
        rdf_memory.YaraProcessScanRequest(
            signature_shard=rdf_memory.YaraSignatureShard(
                index=0, payload=signature_bytes[0:30]
            ),
            num_signature_shards=4,
            **scan_params,
        ),
        rdf_memory.YaraProcessScanRequest(
            signature_shard=rdf_memory.YaraSignatureShard(
                index=1, payload=signature_bytes[30:60]
            ),
            num_signature_shards=4,
            **scan_params,
        ),
        rdf_memory.YaraProcessScanRequest(
            signature_shard=rdf_memory.YaraSignatureShard(
                index=2, payload=signature_bytes[60:90]
            ),
            num_signature_shards=4,
            **scan_params,
        ),
        rdf_memory.YaraProcessScanRequest(
            signature_shard=rdf_memory.YaraSignatureShard(
                index=3, payload=signature_bytes[90:]
            ),
            num_signature_shards=4,
            **scan_params,
        ),
    ]
    self.assertCountEqual(scan_requests, expected_requests)

  def testYaraProcessScanWithoutMissesAndErrors(self):
    procs = [
        p for p in self.procs if p.pid in [101, 102, 103, 104, 105, 106, 107]
    ]
    matches, errors, misses = self._RunYaraProcessScan(procs)

    self.assertLen(matches, 2)
    self.assertEmpty(errors)
    self.assertEmpty(misses)

  def testYaraProcessScanWithMissesWithoutErrors(self):
    procs = [
        p for p in self.procs if p.pid in [101, 102, 103, 104, 105, 106, 107]
    ]
    matches, errors, misses = self._RunYaraProcessScan(
        procs, include_misses_in_results=True
    )

    self.assertLen(matches, 2)
    self.assertEmpty(errors)
    self.assertLen(misses, 2)

  def testYaraProcessScanWithoutMissesWithErrors(self):
    procs = [
        p for p in self.procs if p.pid in [101, 102, 103, 104, 105, 106, 107]
    ]
    matches, errors, misses = self._RunYaraProcessScan(
        procs, include_errors_in_results="ALL_ERRORS"
    )

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
    before = rdfvalue.RDFDatetime.Now()
    _, _, misses = self._RunYaraProcessScan(
        self.procs, pids=[105], include_misses_in_results=True
    )
    after = rdfvalue.RDFDatetime.Now()

    self.assertLen(misses, 1)
    miss = misses[0]
    self.assertBetween(
        miss.scan_time_us,
        minv=0,
        maxv=(after - before).ToInt(rdfvalue.MICROSECONDS),
    )

    before = rdfvalue.RDFDatetime.Now()
    matches, _, _ = self._RunYaraProcessScan(self.procs, pids=[102])
    after = rdfvalue.RDFDatetime.Now()

    self.assertLen(matches, 1)
    match = matches[0]
    self.assertBetween(
        match.scan_time_us,
        minv=0,
        maxv=(after - before).ToInt(rdfvalue.MICROSECONDS),
    )

  def testScanResponseChunking(self):
    procs = [
        p for p in self.procs if p.pid in [101, 102, 103, 104, 105, 106, 107]
    ]
    with mock.patch.object(
        memory_actions.YaraProcessScan, "_RESULTS_PER_RESPONSE", new=2
    ):
      with test_lib.Instrument(
          memory_actions.YaraProcessScan, "SendReply"
      ) as sr:
        matches, errors, misses = self._RunYaraProcessScan(
            procs,
            include_misses_in_results=True,
            include_errors_in_results="ALL_ERRORS",
        )
        # 6 results, 2 results per message -> 3 messages. The fourth message is
        # the status.
        self.assertEqual(sr.call_count, 4)

    self.assertLen(matches, 2)
    self.assertLen(errors, 2)
    self.assertLen(misses, 2)

  def testPIDsRestriction(self):
    matches, errors, misses = self._RunYaraProcessScan(
        self.procs,
        pids=[101, 104, 105],
        include_errors_in_results="ALL_ERRORS",
        include_misses_in_results=True,
    )

    self.assertLen(matches, 1)
    self.assertLen(errors, 1)
    self.assertLen(misses, 1)

  def testProcessRegex(self):
    matches, errors, misses = self._RunYaraProcessScan(
        self.procs,
        process_regex="10(3|6)",
        include_errors_in_results="ALL_ERRORS",
        include_misses_in_results=True,
    )

    self.assertEmpty(matches)
    self.assertLen(errors, 1)
    self.assertLen(misses, 1)

  def testPerProcessTimeoutArg(self):
    FakeRules.invocations = []
    procs = [
        p for p in self.procs if p.pid in [101, 102, 103, 104, 105, 106, 107]
    ]
    with mock.patch.object(yara, "compile", lambda source: FakeRules()):
      self._RunYaraProcessScan(procs, per_process_timeout=50)

    self.assertLen(FakeRules.invocations, 7)
    for invocation in FakeRules.invocations:
      _, limit = invocation
      self.assertGreater(limit, 45)
      self.assertLessEqual(limit, 50)

  def testPerProcessTimeout(self):
    FakeRules.invocations = []
    procs = [
        p for p in self.procs if p.pid in [101, 102, 103, 104, 105, 106, 107]
    ]
    with mock.patch.object(yara, "compile", lambda source: TimeoutRules()):
      matches, errors, misses = self._RunYaraProcessScan(
          procs,
          per_process_timeout=50,
          include_errors_in_results="ALL_ERRORS",
          include_misses_in_results=True,
      )

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
    procs = [
        p for p in self.procs if p.pid in [101, 102, 103, 104, 105, 106, 107]
    ]
    with mock.patch.object(yara, "compile", lambda source: TooManyHitsRules()):
      matches, errors, misses = self._RunYaraProcessScan(
          procs,
          include_errors_in_results="ALL_ERRORS",
          include_misses_in_results=True,
      )

    # The third invocation raises too many hits, make sure we get the
    # first two matches anyways.
    self.assertLen(matches, 2)
    self.assertCountEqual(
        [m.match[0].rule_name for m in matches], ["test_rule_1", "test_rule_2"]
    )
    self.assertLen(errors, 2)
    self.assertLen(misses, 2)

  def testYaraProcessScanChunkingWorks(self):
    FakeRules.invocations = []
    procs = [
        p for p in self.procs if p.pid in [101, 102, 103, 104, 105, 106, 107]
    ]
    with mock.patch.object(yara, "compile", lambda source: FakeRules()):
      self._RunYaraProcessScan(procs, chunk_size=100, overlap_size=10)

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
          include_errors_in_results="ALL_ERRORS",
          include_misses_in_results=True,
      )

      self.assertLen(matches, 1)
      self.assertEmpty(misses)
      self.assertEmpty(errors)

  def testDoubleMatchesAreAvoided(self):
    # Process 102 has a hit going from 98-102. If we set the chunk
    # size a bit larger than that, the hit will be scanned twice. We
    # still expect a single match only.
    matches, _, _ = self._RunYaraProcessScan(
        self.procs, chunk_size=105, overlap_size=10, pids=[102]
    )

    self.assertLen(matches, 1)
    self.assertLen(matches[0].match, 1)

  def _RunProcessDump(self, pids=None, size_limit=None, chunk_size=None):

    procs = self.procs
    with utils.MultiStubber(
        (psutil, "process_iter", lambda: procs),
        (psutil, "Process", functools.partial(self.process, procs)),
        (
            client_utils,
            "OpenProcessForMemoryAccess",
            lambda pid: FakeMemoryProcess(pid=pid, tmp_dir=self._tmp_dir),
        ),
    ):
      client_mock = action_mocks.MultiGetFileClientMock(
          memory_actions.YaraProcessDump, tempfiles.DeleteGRRTempFiles
      )
      session_id = flow_test_lib.StartAndRunFlow(
          memory.DumpProcessMemory,
          client_mock,
          client_id=self.client_id,
          flow_args=rdf_memory.YaraProcessDumpArgs(
              size_limit=size_limit,
              pids=pids or [105],
              chunk_size=chunk_size,
              ignore_grr_process=True,
          ),
          creator=self.test_username,
      )
    return flow_test_lib.GetFlowResults(self.client_id, session_id)

  def _ReadFromPathspec(self, pathspec, num_bytes):
    fd = file_store.OpenFile(
        db.ClientPath.FromPathSpec(self.client_id, pathspec)
    )
    return fd.read(num_bytes)

  def testProcessDump(self):
    results = self._RunProcessDump()

    self.assertLen(results, 3)
    for result in results:
      if isinstance(result, rdf_client_fs.StatEntry):
        self.assertIn("proc105.exe_105", result.pathspec.path)

        data = self._ReadFromPathspec(result.pathspec, 1000)

        self.assertIn(
            data, [GeneratePattern(b"A", 100), GeneratePattern(b"B", 700)]
        )
      elif isinstance(result, rdf_memory.YaraProcessDumpResponse):
        self.assertLen(result.dumped_processes, 1)
        self.assertEqual(result.dumped_processes[0].process.pid, 105)
      else:
        self.fail("Unexpected result type %s" % type(result))

  def testProcessDumpChunked(self):
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

        self.assertIn(
            data, [GeneratePattern(b"A", 100), GeneratePattern(b"B", 700)]
        )
      elif isinstance(result, rdf_memory.YaraProcessDumpResponse):
        self.assertLen(result.dumped_processes, 1)
        self.assertEqual(result.dumped_processes[0].process.pid, 105)
      else:
        self.fail("Unexpected result type %s" % type(result))

  def testProcessDumpWithLimit(self):
    results = self._RunProcessDump(size_limit=100)

    # Now we should only get one block (+ the YaraProcessDumpResponse), the
    # second is over the limit.
    self.assertLen(results, 2)

    for result in results:
      if isinstance(result, rdf_client_fs.StatEntry):
        self.assertIn("proc105.exe_105", result.pathspec.path)

        data = self._ReadFromPathspec(result.pathspec, 1000)

        self.assertEqual(data, GeneratePattern(b"A", 100))
      elif isinstance(result, rdf_memory.YaraProcessDumpResponse):
        self.assertLen(result.dumped_processes, 1)
        self.assertEqual(result.dumped_processes[0].process.pid, 105)
        self.assertIn("limit exceeded", result.dumped_processes[0].error)
      else:
        self.fail("Unexpected result type %s" % type(result))

  def testProcessDumpPartiallyDumpsMemory(self):
    results = self._RunProcessDump(size_limit=20)
    self.assertLen(results, 2)
    process = results[0].dumped_processes[0]
    self.assertLen(process.memory_regions, 1)
    self.assertEqual(process.memory_regions[0].size, 100)
    self.assertEqual(process.memory_regions[0].dumped_size, 20)
    self.assertEqual(results[1].st_size, 20)

  def testProcessDumpByDefaultErrors(self):
    # This tests that not specifying any restrictions on the processes
    # to dump does not dump them all which would return tons of data.
    client_mock = action_mocks.MultiGetFileClientMock(
        memory_actions.YaraProcessDump, tempfiles.DeleteGRRTempFiles
    )
    flow_id = flow_test_lib.StartAndRunFlow(
        memory.DumpProcessMemory,
        client_mock,
        client_id=self.client_id,
        check_flow_errors=False,
        creator=self.test_username,
        flow_args=rdf_memory.YaraProcessDumpArgs(
            ignore_grr_process=True,
        ),
    )
    flow_obj = data_store.REL_DB.ReadFlowObject(self.client_id, flow_id)
    self.assertEqual(flow_obj.error_message, "No processes to dump specified.")

  def testDumpTimingInformation(self):
    with test_lib.FakeTime(100000, 0.1):
      results = self._RunProcessDump()

    self.assertGreater(len(results), 1)
    self.assertIsInstance(results[0], rdf_memory.YaraProcessDumpResponse)
    self.assertLen(results[0].dumped_processes, 1)
    self.assertGreater(results[0].dumped_processes[0].dump_time_us, 0)

  def testSucceedsWhenUnderRuntimeLimit(self):
    procs = [p for p in self.procs if p.pid in [102]]
    matches, _, _ = self._RunYaraProcessScan(
        procs, runtime_limit=rdfvalue.Duration.From(20, rdfvalue.SECONDS)
    )
    self.assertLen(matches, 1)

  def testPropagatesScanRuntimeLimit(self):
    procs = [p for p in self.procs if p.pid in [102]]
    runtime_limits = []

    def Run(yps, args):
      del args  # Unused.
      runtime_limits.append(yps.message.runtime_limit_us)

    with mock.patch.object(memory_actions.YaraProcessScan, "Run", Run):
      self._RunYaraProcessScan(
          procs,
          scan_runtime_limit_us=rdfvalue.Duration.From(5, rdfvalue.SECONDS),
      )

      self.assertLen(runtime_limits, 1)
      self.assertEqual(
          runtime_limits[0], rdfvalue.Duration.From(5, rdfvalue.SECONDS)
      )

  def testFailsWithExceededScanRuntimeLimit(self):
    procs = [p for p in self.procs if p.pid in [102]]

    with self.assertRaisesRegex(RuntimeError, r"Runtime limit exceeded"):
      self._RunYaraProcessScan(
          procs,
          scan_runtime_limit_us=rdfvalue.Duration.From(
              1, rdfvalue.MICROSECONDS
          ),
      )

  def testScanAndDump(self):
    client_mock = action_mocks.MultiGetFileClientMock(
        memory_actions.YaraProcessScan,
        memory_actions.YaraProcessDump,
        tempfiles.DeleteGRRTempFiles,
    )

    procs = [p for p in self.procs if p.pid in [102, 103]]

    with mock.patch.object(file_store.EXTERNAL_FILE_STORE, "AddFiles") as efs:
      with utils.MultiStubber(
          (psutil, "process_iter", lambda: procs),
          (psutil, "Process", functools.partial(self.process, procs)),
          (
              client_utils,
              "OpenProcessForMemoryAccess",
              lambda pid: FakeMemoryProcess(pid=pid, tmp_dir=self._tmp_dir),
          ),
      ):
        session_id = flow_test_lib.StartAndRunFlow(
            memory.YaraProcessScan,
            client_mock,
            client_id=self.client_id,
            creator=self.test_username,
            flow_args=rdf_memory.YaraProcessScanRequest(
                yara_signature=_TEST_YARA_SIGNATURE,
                include_errors_in_results="ALL_ERRORS",
                include_misses_in_results=True,
                dump_process_on_match=True,
            ),
        )

    # Process dumps are not pushed to external file stores.
    self.assertEqual(efs.call_count, 0)

    results = flow_test_lib.GetFlowResults(self.client_id, session_id)

    # 1. Scan result match.
    # 2. Scan result miss.
    # 3. ProcDump response.
    # 4. Stat entry for the dumped file.
    self.assertLen(results, 4)
    self.assertIsInstance(results[0], rdf_memory.YaraProcessScanMatch)
    self.assertIsInstance(results[1], rdf_memory.YaraProcessScanMiss)
    self.assertIsInstance(results[2], rdf_memory.YaraProcessDumpResponse)
    self.assertIsInstance(results[3], rdf_client_fs.StatEntry)

    self.assertLen(results[2].dumped_processes, 1)
    self.assertEqual(
        results[0].process.pid, results[2].dumped_processes[0].process.pid
    )

    self.assertLen(results[2].dumped_processes[0].memory_regions, 1)

    # TODO: Fix PathSpec.__eq__, then compare PathSpecs here.
    self.assertEqual(
        results[2].dumped_processes[0].memory_regions[0].file.CollapsePath(),
        results[3].pathspec.CollapsePath(),
    )

  def testScanAndDumpPopulatesMemoryRegions(self):
    client_mock = action_mocks.MultiGetFileClientMock(
        memory_actions.YaraProcessScan,
        memory_actions.YaraProcessDump,
        tempfiles.DeleteGRRTempFiles,
    )

    procs = [p for p in self.procs if p.pid in [108]]

    with utils.MultiStubber(
        (psutil, "process_iter", lambda: procs),
        (psutil, "Process", functools.partial(self.process, procs)),
        (
            client_utils,
            "OpenProcessForMemoryAccess",
            lambda pid: FakeMemoryProcess(pid=pid, tmp_dir=self._tmp_dir),
        ),
    ):
      session_id = flow_test_lib.StartAndRunFlow(
          memory.YaraProcessScan,
          client_mock,
          client_id=self.client_id,
          creator=self.test_username,
          flow_args=rdf_memory.YaraProcessScanRequest(
              yara_signature=_TEST_YARA_SIGNATURE,
              include_errors_in_results="ALL_ERRORS",
              include_misses_in_results=True,
              dump_process_on_match=True,
          ),
      )

    results = flow_test_lib.GetFlowResults(self.client_id, session_id)
    dumps = [
        r for r in results if isinstance(r, rdf_memory.YaraProcessDumpResponse)
    ]

    self.assertLen(dumps, 1)
    self.assertLen(dumps[0].dumped_processes, 1)
    self.assertLen(dumps[0].dumped_processes[0].memory_regions, 2)
    regions = dumps[0].dumped_processes[0].memory_regions

    self.assertEqual(regions[0].start, 0)
    self.assertEqual(regions[0].size, 100)
    self.assertEqual(regions[0].dumped_size, 100)
    self.assertEqual(regions[0].is_executable, True)
    self.assertEqual(regions[0].is_writable, True)
    self.assertIsNotNone(regions[0].file)
    self.assertEqual(regions[1].start, 1000)
    self.assertEqual(regions[1].size, 104)
    self.assertEqual(regions[1].dumped_size, 104)
    self.assertEqual(regions[1].is_executable, False)
    self.assertEqual(regions[1].is_writable, False)
    self.assertIsNotNone(regions[1].file)

  def testScanAndDumpPrioritizesRegionsWithMatch(self):
    client_mock = action_mocks.MultiGetFileClientMock(
        memory_actions.YaraProcessScan,
        memory_actions.YaraProcessDump,
        tempfiles.DeleteGRRTempFiles,
    )

    procs = [p for p in self.procs if p.pid in [109]]

    with utils.MultiStubber(
        (psutil, "process_iter", lambda: procs),
        (psutil, "Process", functools.partial(self.process, procs)),
        (
            client_utils,
            "OpenProcessForMemoryAccess",
            lambda pid: FakeMemoryProcess(pid=pid, tmp_dir=self._tmp_dir),
        ),
    ):
      session_id = flow_test_lib.StartAndRunFlow(
          memory.YaraProcessScan,
          client_mock,
          client_id=self.client_id,
          creator=self.test_username,
          flow_args=rdf_memory.YaraProcessScanRequest(
              yara_signature=_TEST_YARA_SIGNATURE,
              include_errors_in_results="ALL_ERRORS",
              include_misses_in_results=True,
              dump_process_on_match=True,
              # Size of first and third region.
              process_dump_size_limit=100 + 104,
          ),
      )

    results = flow_test_lib.GetFlowResults(self.client_id, session_id)
    dumps = [
        r for r in results if isinstance(r, rdf_memory.YaraProcessDumpResponse)
    ]

    self.assertLen(dumps, 1)
    self.assertLen(dumps[0].dumped_processes, 1)
    self.assertLen(dumps[0].dumped_processes[0].memory_regions, 2)
    regions = dumps[0].dumped_processes[0].memory_regions

    # Dump should skip the second region, because the first and third fill the
    # size limit.
    self.assertEqual(regions[0].start, 0)
    self.assertEqual(regions[0].dumped_size, 100)
    self.assertIsNotNone(regions[0].file)
    self.assertEqual(regions[1].start, 101)
    self.assertEqual(regions[1].dumped_size, 104)
    self.assertIsNotNone(regions[1].file)

  def testPathSpecCasingIsCorrected(self):
    flow = memory.DumpProcessMemory(rdf_flow_objects.Flow())
    flow.SendReplyProto = mock.Mock(spec=flow.SendReplyProto)

    request = rdf_flow_objects.FlowRequest(
        request_data={
            "YaraProcessDumpResponse": rdf_memory.YaraProcessDumpResponse(
                dumped_processes=[
                    rdf_memory.YaraProcessDumpInformation(
                        memory_regions=[
                            rdf_memory.ProcessMemoryRegion(
                                start=1,
                                size=1,
                                file=rdf_paths.PathSpec.Temp(
                                    path="/C:/grr/x_1_0_1.tmp"
                                ),
                            ),
                            rdf_memory.ProcessMemoryRegion(
                                start=1,
                                size=1,
                                file=rdf_paths.PathSpec.Temp(
                                    path="/C:/GRR/x_1_1_2.tmp"
                                ),
                            ),
                        ]
                    )
                ]
            )
        }
    )

    flow_responses_any = []
    for path in ["/C:/Grr/x_1_0_1.tmp", "/C:/Grr/x_1_1_2.tmp"]:
      res = flows_pb2.FlowResponse()
      res.any_payload.Pack(
          jobs_pb2.StatEntry(
              pathspec=jobs_pb2.PathSpec(
                  path=path, pathtype=jobs_pb2.PathSpec.PathType.TMPFILE
              )
          )
      )
      flow_responses_any.append(mig_flow_objects.ToRDFFlowResponse(res))
    flow_responses_any.append(rdf_flow_objects.FlowStatus(status="OK"))
    responses = flow_responses.Responses.FromResponsesProto2Any(
        flow_responses_any, request
    )

    flow.ProcessMemoryRegions(responses)
    flow.SendReplyProto.assert_any_call(
        flows_pb2.YaraProcessDumpResponse(
            dumped_processes=[
                flows_pb2.YaraProcessDumpInformation(
                    memory_regions=[
                        flows_pb2.ProcessMemoryRegion(
                            start=1,
                            size=1,
                            file=jobs_pb2.PathSpec(
                                path="/C:/Grr/x_1_0_1.tmp",
                                pathtype=jobs_pb2.PathSpec.PathType.TMPFILE,
                            ),
                        ),
                        flows_pb2.ProcessMemoryRegion(
                            start=1,
                            size=1,
                            file=jobs_pb2.PathSpec(
                                path="/C:/Grr/x_1_1_2.tmp",
                                pathtype=jobs_pb2.PathSpec.PathType.TMPFILE,
                            ),
                        ),
                    ]
                )
            ]
        )
    )


@unittest.skipIf(
    platform.system() != "Linux",
    "FakeMemoryProcess.serialized_file_descriptor works only on Linux.",
)
class YaraFlowsUnprivilegedTest(YaraFlowsTest):

  def setUp(self):
    super().setUp()
    stack = contextlib.ExitStack()
    self.addCleanup(stack.close)
    stack.enter_context(
        test_lib.ConfigOverrider({"Client.use_memory_sandboxing": True})
    )
    # Use smaller batch size to exercise the batching logic.
    stack.enter_context(
        mock.patch.object(
            memory_actions.BatchedUnprivilegedYaraWrapper, "BATCH_SIZE", 2
        )
    )

  # Tracking of time works differently in unprivileged mode.
  # (There isn't one call to RDFDatetime.Now() per chunk due to batching).
  def testScanTimingInformation(self):
    before = rdfvalue.RDFDatetime.Now()
    _, _, misses = self._RunYaraProcessScan(
        self.procs, pids=[105], include_misses_in_results=True
    )
    after = rdfvalue.RDFDatetime.Now()

    self.assertLen(misses, 1)
    miss = misses[0]
    self.assertBetween(
        miss.scan_time_us,
        minv=0,
        maxv=(after - before).ToInt(rdfvalue.MICROSECONDS),
    )

    before = rdfvalue.RDFDatetime.Now()
    matches, _, _ = self._RunYaraProcessScan(self.procs, pids=[102])
    after = rdfvalue.RDFDatetime.Now()

    self.assertLen(matches, 1)
    match = matches[0]
    self.assertBetween(
        match.scan_time_us,
        minv=0,
        maxv=(after - before).ToInt(rdfvalue.MICROSECONDS),
    )

  # The following tests don't work with sandboxing, because they mock
  # yara.compile, which is executed in the unprivileged process.

  def testPerProcessTimeout(self):
    pass

  def testPerProcessTimeoutArg(self):
    pass

  def testTooManyHitsError(self):
    pass

  def testYaraProcessScanChunkingWorks(self):
    pass


class YaraProcessScanTest(flow_test_lib.FlowTestsBaseclass):

  @classmethod
  def setUpClass(cls):
    super(YaraProcessScanTest, cls).setUpClass()
    testing_startup.TestInit()

  def setUp(self):
    super().setUp()
    self.client_id = self.SetupClient(0)

  def testYaraSignatureReferenceDeliversFullSignatureToClient(self):
    signature = "rule foo { condition: true };"

    blob = signature.encode("utf-8")
    blob_id = data_store.BLOBS.WriteBlobWithUnknownHash(blob)

    data_store.REL_DB.WriteGRRUser(username="foobarski")
    data_store.REL_DB.WriteYaraSignatureReference(blob_id, username="foobarski")

    args = rdf_memory.YaraProcessScanRequest()
    args.yara_signature_blob_id = bytes(blob_id)

    shards = []

    class FakeYaraProcessScan(action_mocks.ActionMock):

      def YaraProcessScan(
          self,
          args: rdf_memory.YaraProcessScanRequest,
      ) -> Iterable[rdf_memory.YaraProcessScanResponse]:
        shards.append(args.signature_shard)
        return []

    self._YaraProcessScan(args, action_mock=FakeYaraProcessScan())

    payloads = [_.payload for _ in sorted(shards, key=lambda _: _.index)]
    self.assertEqual(b"".join(payloads).decode("utf-8"), signature)

  def testYaraSignatureReferenceIncorrect(self):
    data = "This is very c0nfidential and should not leak to the client."
    blob_id = data_store.BLOBS.WriteBlobWithUnknownHash(data.encode("utf-8"))

    args = rdf_memory.YaraProcessScanRequest()
    args.yara_signature_blob_id = bytes(blob_id)

    with self.assertRaisesRegex(RuntimeError, "signature reference"):
      self._YaraProcessScan(args)

  def testYaraSignatureReferenceNotExisting(self):
    args = rdf_memory.YaraProcessScanRequest()
    args.yara_signature_blob_id = os.urandom(32)

    with self.assertRaisesRegex(RuntimeError, "signature reference"):
      self._YaraProcessScan(args)

  def testYaraSignatureAndSignatureReference(self):
    signature = "rule foo { condition: true };"

    blob = signature.encode("utf-8")
    blob_id = data_store.BLOBS.WriteBlobWithUnknownHash(blob)

    data_store.REL_DB.WriteGRRUser(username="foobarski")
    data_store.REL_DB.WriteYaraSignatureReference(blob_id, username="foobarski")

    args = rdf_memory.YaraProcessScanRequest()
    args.yara_signature = signature
    args.yara_signature_blob_id = bytes(blob_id)

    with self.assertRaisesRegex(RuntimeError, "can't be used together"):
      self._YaraProcessScan(args)

  def _YaraProcessScan(
      self,
      args: rdf_memory.YaraProcessScanRequest,
      action_mock: Optional[action_mocks.ActionMock] = None,
  ) -> None:
    if action_mock is None:
      action_mock = action_mocks.ActionMock()

    flow_test_lib.StartAndRunFlow(
        memory.YaraProcessScan,
        action_mock,
        client_id=self.client_id,
        creator=self.test_username,
        flow_args=args,
    )

    flow_test_lib.FinishAllFlowsOnClient(self.client_id)


def main(argv):
  # Run the full test suite
  test_lib.main(argv)


if __name__ == "__main__":
  app.run(main)
