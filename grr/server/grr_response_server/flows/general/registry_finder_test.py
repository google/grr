#!/usr/bin/env python
"""Tests for the RegistryFinder flow."""

import stat

from absl import app

from grr_response_proto import flows_pb2
from grr_response_proto import jobs_pb2
from grr_response_server.databases import db as abstract_db
from grr_response_server.databases import db_test_utils
from grr_response_server.flows.general import mig_registry_finder
from grr_response_server.flows.general import registry_finder as flow_registry_finder
from grr.test_lib import action_mocks
from grr.test_lib import db_test_lib
from grr.test_lib import flow_test_lib
from grr.test_lib import rrg_test_lib
from grr.test_lib import test_lib
from grr.test_lib import vfs_test_lib
from grr_response_proto.rrg import os_pb2 as rrg_os_pb2
from grr_response_proto.rrg import winreg_pb2 as rrg_winreg_pb2


class TestStubbedRegistryFinderFlow(flow_test_lib.FlowTestsBaseclass):
  """Test the RegistryFinder flow."""

  def setUp(self):
    super().setUp()
    registry_stubber = vfs_test_lib.RegistryVFSStubber()
    registry_stubber.Start()
    self.addCleanup(registry_stubber.Stop)

  def _RunRegistryFinder(self, paths=None):
    client_mock = action_mocks.ClientFileFinderWithVFS()

    client_id = self.SetupClient(0)

    session_id = flow_test_lib.StartAndRunFlow(
        flow_registry_finder.RegistryFinder,
        client_mock,
        client_id=client_id,
        creator=self.test_username,
        flow_args=flow_registry_finder.RegistryFinderArgs(
            keys_paths=paths,
            conditions=[],
        ),
    )

    return flow_test_lib.GetFlowResults(client_id, session_id)

  def testRegistryFinder(self):
    # Listing inside a key gives the values.
    results = self._RunRegistryFinder(
        ["HKEY_LOCAL_MACHINE/SOFTWARE/ListingTest/*"]
    )
    self.assertLen(results, 2)
    self.assertCountEqual(
        [x.stat_entry.registry_data.GetValue() for x in results],
        ["Value1", "Value2"],
    )

    # This is a key so we should get back the default value.
    results = self._RunRegistryFinder(
        ["HKEY_LOCAL_MACHINE/SOFTWARE/ListingTest"]
    )

    self.assertLen(results, 1)
    self.assertEqual(
        results[0].stat_entry.registry_data.GetValue(), "DefaultValue"
    )

    # The same should work using a wildcard.
    results = self._RunRegistryFinder(["HKEY_LOCAL_MACHINE/SOFTWARE/*"])

    self.assertTrue(results)
    paths = [x.stat_entry.pathspec.path for x in results]
    expected_path = "/HKEY_LOCAL_MACHINE/SOFTWARE/ListingTest"
    self.assertIn(expected_path, paths)
    idx = paths.index(expected_path)
    self.assertEqual(
        results[idx].stat_entry.registry_data.GetValue(), "DefaultValue"
    )

  def testListingRegistryKeysDoesYieldMTimes(self):
    # Just listing all keys does generate a full stat entry for each of
    # the results.
    results = self._RunRegistryFinder(
        ["HKEY_LOCAL_MACHINE/SOFTWARE/ListingTest/*"]
    )
    results = sorted(results, key=lambda x: x.stat_entry.pathspec.path)

    # We expect 2 results: Value1 and Value2.
    self.assertLen(results, 2)
    self.assertEqual(
        results[0].stat_entry.pathspec.path,
        "/HKEY_LOCAL_MACHINE/SOFTWARE/ListingTest/Value1",
    )
    self.assertEqual(results[0].stat_entry.st_mtime, 110)
    self.assertEqual(
        results[1].stat_entry.pathspec.path,
        "/HKEY_LOCAL_MACHINE/SOFTWARE/ListingTest/Value2",
    )
    self.assertEqual(results[1].stat_entry.st_mtime, 120)

    # Explicitly calling RegistryFinder on a value does that as well.
    results = self._RunRegistryFinder([
        "HKEY_LOCAL_MACHINE/SOFTWARE/ListingTest/Value1",
        "HKEY_LOCAL_MACHINE/SOFTWARE/ListingTest/Value2",
    ])
    results = sorted(results, key=lambda x: x.stat_entry.pathspec.path)

    # We expect 2 results: Value1 and Value2.
    self.assertLen(results, 2)
    self.assertEqual(
        results[0].stat_entry.pathspec.path,
        "/HKEY_LOCAL_MACHINE/SOFTWARE/ListingTest/Value1",
    )
    self.assertEqual(results[0].stat_entry.st_mtime, 110)
    self.assertEqual(
        results[1].stat_entry.pathspec.path,
        "/HKEY_LOCAL_MACHINE/SOFTWARE/ListingTest/Value2",
    )
    self.assertEqual(results[1].stat_entry.st_mtime, 120)

  def testListingRegistryHivesRaises(self):
    with self.assertRaisesRegex(RuntimeError, "is not absolute"):
      self._RunRegistryFinder(["*"])

  @db_test_lib.WithDatabase
  def testRRG_OnlyKey(self, db: abstract_db.Database):
    client_id = db_test_utils.InitializeRRGClient(
        db,
        os_type=rrg_os_pb2.Type.WINDOWS,
    )

    args = flows_pb2.RegistryFinderArgs()
    args.keys_paths.append(r"HKEY_LOCAL_MACHINE\SOFTWARE\Foo")

    flow_id = rrg_test_lib.ExecuteFlow(
        client_id=client_id,
        flow_cls=flow_registry_finder.RegistryFinder,
        flow_args=mig_registry_finder.ToRDFRegistryFinderArgs(args),
        handlers=rrg_test_lib.FakeWinregHandlers({
            rrg_winreg_pb2.LOCAL_MACHINE: {
                "SOFTWARE": {
                    "Foo": {},
                },
            },
        }),
    )

    flow_obj = db.ReadFlowObject(client_id, flow_id)
    self.assertEqual(flow_obj.backtrace, "")
    self.assertEqual(flow_obj.error_message, "")
    self.assertEqual(flow_obj.flow_state, flows_pb2.Flow.FINISHED)

    flow_results = db.ReadFlowResults(client_id, flow_id, offset=0, count=128)
    self.assertLen(flow_results, 1)

    result = flows_pb2.FileFinderResult()
    self.assertTrue(flow_results[0].payload.Unpack(result))

    self.assertEqual(
        result.stat_entry.pathspec.pathtype,
        jobs_pb2.PathSpec.PathType.REGISTRY,
    )
    self.assertEqual(
        result.stat_entry.pathspec.path,
        r"HKEY_LOCAL_MACHINE\SOFTWARE\Foo",
    )
    self.assertEqual(
        result.stat_entry.registry_type,
        jobs_pb2.StatEntry.REG_SZ,
    )
    self.assertEqual(
        result.stat_entry.registry_data.string,
        "",
    )
    self.assertTrue(stat.S_ISDIR(result.stat_entry.st_mode))

  @db_test_lib.WithDatabase
  def testRRG_KeyWithValues(self, db: abstract_db.Database):
    client_id = db_test_utils.InitializeRRGClient(
        db,
        os_type=rrg_os_pb2.Type.WINDOWS,
    )

    args = flows_pb2.RegistryFinderArgs()
    args.keys_paths.append(r"HKEY_LOCAL_MACHINE\SOFTWARE\Foo")

    flow_id = rrg_test_lib.ExecuteFlow(
        client_id=client_id,
        flow_cls=flow_registry_finder.RegistryFinder,
        flow_args=mig_registry_finder.ToRDFRegistryFinderArgs(args),
        handlers=rrg_test_lib.FakeWinregHandlers({
            rrg_winreg_pb2.LOCAL_MACHINE: {
                "SOFTWARE": {
                    "Foo": {
                        "Bar": 42,
                        "Baz": "Lorem ipsum.",
                    },
                },
            },
        }),
    )

    flow_obj = db.ReadFlowObject(client_id, flow_id)
    self.assertEqual(flow_obj.backtrace, "")
    self.assertEqual(flow_obj.error_message, "")
    self.assertEqual(flow_obj.flow_state, flows_pb2.Flow.FINISHED)

    flow_results = db.ReadFlowResults(client_id, flow_id, offset=0, count=128)
    self.assertLen(flow_results, 3)

    results_by_path = {}
    for flow_result in flow_results:
      result = flows_pb2.FileFinderResult()
      self.assertTrue(flow_result.payload.Unpack(result))

      results_by_path[result.stat_entry.pathspec.path] = result

    result = results_by_path[r"HKEY_LOCAL_MACHINE\SOFTWARE\Foo"]
    self.assertEqual(
        result.stat_entry.registry_type,
        jobs_pb2.StatEntry.REG_SZ,
    )
    self.assertEqual(
        result.stat_entry.registry_data.string,
        "",
    )
    self.assertTrue(stat.S_ISDIR(result.stat_entry.st_mode))

    result = results_by_path[r"HKEY_LOCAL_MACHINE\SOFTWARE\Foo\Bar"]
    self.assertEqual(
        result.stat_entry.registry_type,
        jobs_pb2.StatEntry.REG_DWORD,
    )
    self.assertEqual(
        result.stat_entry.registry_data.integer,
        42,
    )
    self.assertFalse(stat.S_ISDIR(result.stat_entry.st_mode))

    result = results_by_path[r"HKEY_LOCAL_MACHINE\SOFTWARE\Foo\Baz"]
    self.assertEqual(
        result.stat_entry.registry_type,
        jobs_pb2.StatEntry.REG_SZ,
    )
    self.assertEqual(
        result.stat_entry.registry_data.string,
        "Lorem ipsum.",
    )
    self.assertFalse(stat.S_ISDIR(result.stat_entry.st_mode))

  @db_test_lib.WithDatabase
  def testRRG_Glob(self, db: abstract_db.Database):
    client_id = db_test_utils.InitializeRRGClient(
        db,
        os_type=rrg_os_pb2.Type.WINDOWS,
    )

    args = flows_pb2.RegistryFinderArgs()
    args.keys_paths.append(r"HKEY_LOCAL_MACHINE\SOFTWARE\*")

    flow_id = rrg_test_lib.ExecuteFlow(
        client_id=client_id,
        flow_cls=flow_registry_finder.RegistryFinder,
        flow_args=mig_registry_finder.ToRDFRegistryFinderArgs(args),
        handlers=rrg_test_lib.FakeWinregHandlers({
            rrg_winreg_pb2.LOCAL_MACHINE: {
                "SOFTWARE": {
                    "Foo": {
                        "Bar": {},
                        "Baz": 42,
                    },
                    "Quux": {
                        "Thud": "Lorem ipsum.",
                        "Norf": "Dolor sit amet.",
                    },
                },
            },
        }),
    )

    flow_obj = db.ReadFlowObject(client_id, flow_id)
    self.assertEqual(flow_obj.backtrace, "")
    self.assertEqual(flow_obj.error_message, "")
    self.assertEqual(flow_obj.flow_state, flows_pb2.Flow.FINISHED)

    flow_results = db.ReadFlowResults(client_id, flow_id, offset=0, count=128)

    results_by_path = {}
    for flow_result in flow_results:
      result = flows_pb2.FileFinderResult()
      self.assertTrue(flow_result.payload.Unpack(result))

      results_by_path[result.stat_entry.pathspec.path] = result

    self.assertIn(r"HKEY_LOCAL_MACHINE\SOFTWARE\Foo", results_by_path)
    self.assertIn(r"HKEY_LOCAL_MACHINE\SOFTWARE\Foo\Baz", results_by_path)
    self.assertIn(r"HKEY_LOCAL_MACHINE\SOFTWARE\Quux", results_by_path)
    self.assertIn(r"HKEY_LOCAL_MACHINE\SOFTWARE\Quux\Thud", results_by_path)
    self.assertIn(r"HKEY_LOCAL_MACHINE\SOFTWARE\Quux\Norf", results_by_path)

    # `HKLM\SOFTWARE\Foo\Bar` is a nested key and so it is not part of the
    # `HKLM\SOFTWARE\Foo` key (that matches the glob).
    self.assertNotIn(r"HKEY_LOCAL_MACHINE\SOFTWARE\Foo\Bar", results_by_path)

  @db_test_lib.WithDatabase
  def testRRG_RecursiveGlob(self, db: abstract_db.Database):
    client_id = db_test_utils.InitializeRRGClient(
        db,
        os_type=rrg_os_pb2.Type.WINDOWS,
    )

    args = flows_pb2.RegistryFinderArgs()
    args.keys_paths.append(r"HKEY_LOCAL_MACHINE\SOFTWARE\**5")

    flow_id = rrg_test_lib.ExecuteFlow(
        client_id=client_id,
        flow_cls=flow_registry_finder.RegistryFinder,
        flow_args=mig_registry_finder.ToRDFRegistryFinderArgs(args),
        handlers=rrg_test_lib.FakeWinregHandlers({
            rrg_winreg_pb2.LOCAL_MACHINE: {
                "SOFTWARE": {
                    "Foo": {
                        "Bar": {
                            "Blarg": b"\xff\x00\x00",
                        },
                        "Baz": 42,
                    },
                    "Quux": {
                        "Thud": "Lorem ipsum.",
                        "Norf": "Dolor sit amet.",
                    },
                },
            },
        }),
    )

    flow_obj = db.ReadFlowObject(client_id, flow_id)
    self.assertEqual(flow_obj.backtrace, "")
    self.assertEqual(flow_obj.error_message, "")
    self.assertEqual(flow_obj.flow_state, flows_pb2.Flow.FINISHED)

    flow_results = db.ReadFlowResults(client_id, flow_id, offset=0, count=128)

    results_by_path = {}
    for flow_result in flow_results:
      result = flows_pb2.FileFinderResult()
      self.assertTrue(flow_result.payload.Unpack(result))

      results_by_path[result.stat_entry.pathspec.path] = result

    self.assertIn(r"HKEY_LOCAL_MACHINE\SOFTWARE\Foo", results_by_path)
    self.assertIn(r"HKEY_LOCAL_MACHINE\SOFTWARE\Foo\Baz", results_by_path)
    self.assertIn(r"HKEY_LOCAL_MACHINE\SOFTWARE\Foo\Bar", results_by_path)
    self.assertIn(r"HKEY_LOCAL_MACHINE\SOFTWARE\Foo\Bar\Blarg", results_by_path)
    self.assertIn(r"HKEY_LOCAL_MACHINE\SOFTWARE\Quux", results_by_path)
    self.assertIn(r"HKEY_LOCAL_MACHINE\SOFTWARE\Quux\Thud", results_by_path)
    self.assertIn(r"HKEY_LOCAL_MACHINE\SOFTWARE\Quux\Norf", results_by_path)

  @db_test_lib.WithDatabase
  def testRRG_Condition_Literal(self, db: abstract_db.Database):
    client_id = db_test_utils.InitializeRRGClient(
        db,
        os_type=rrg_os_pb2.Type.WINDOWS,
    )

    args = flows_pb2.RegistryFinderArgs()
    args.keys_paths.append(r"HKEY_LOCAL_MACHINE\SOFTWARE")

    cond = args.conditions.add()
    cond.condition_type = cond.VALUE_LITERAL_MATCH
    cond.value_literal_match.literal = b"FOO"

    flow_id = rrg_test_lib.ExecuteFlow(
        client_id=client_id,
        flow_cls=flow_registry_finder.RegistryFinder,
        flow_args=mig_registry_finder.ToRDFRegistryFinderArgs(args),
        handlers=rrg_test_lib.FakeWinregHandlers({
            rrg_winreg_pb2.LOCAL_MACHINE: {
                "SOFTWARE": {
                    "FooStr": "FOO",
                    "FooBytes": b"FOO",
                    "BarStr": "BAR",
                    "BarBytes": b"BAR",
                },
            },
        }),
    )

    flow_obj = db.ReadFlowObject(client_id, flow_id)
    self.assertEqual(flow_obj.backtrace, "")
    self.assertEqual(flow_obj.error_message, "")
    self.assertEqual(flow_obj.flow_state, flows_pb2.Flow.FINISHED)

    flow_results = db.ReadFlowResults(client_id, flow_id, offset=0, count=128)

    results_by_path = {}
    for flow_result in flow_results:
      result = flows_pb2.FileFinderResult()
      self.assertTrue(flow_result.payload.Unpack(result))

      results_by_path[result.stat_entry.pathspec.path] = result

    self.assertIn(r"HKEY_LOCAL_MACHINE\SOFTWARE\FooStr", results_by_path)
    self.assertIn(r"HKEY_LOCAL_MACHINE\SOFTWARE\FooBytes", results_by_path)
    self.assertNotIn(r"HKEY_LOCAL_MACHINE\SOFTWARE\BarStr", results_by_path)
    self.assertNotIn(r"HKEY_LOCAL_MACHINE\SOFTWARE\BarBytes", results_by_path)

  @db_test_lib.WithDatabase
  def testRRG_Condition_Regex(self, db: abstract_db.Database):
    client_id = db_test_utils.InitializeRRGClient(
        db,
        os_type=rrg_os_pb2.Type.WINDOWS,
    )

    args = flows_pb2.RegistryFinderArgs()
    args.keys_paths.append(r"HKEY_LOCAL_MACHINE\SOFTWARE")

    cond = args.conditions.add()
    cond.condition_type = cond.VALUE_REGEX_MATCH
    cond.value_regex_match.regex = b"BA[RZ]"

    flow_id = rrg_test_lib.ExecuteFlow(
        client_id=client_id,
        flow_cls=flow_registry_finder.RegistryFinder,
        flow_args=mig_registry_finder.ToRDFRegistryFinderArgs(args),
        handlers=rrg_test_lib.FakeWinregHandlers({
            rrg_winreg_pb2.LOCAL_MACHINE: {
                "SOFTWARE": {
                    "FooStr": "FOO",
                    "FooBytes": b"FOO",
                    "BarStr": "BAR",
                    "BarBytes": b"BAR",
                    "BazStr": "BAZ",
                    "BazBytes": "BAZ",
                },
            },
        }),
    )

    flow_obj = db.ReadFlowObject(client_id, flow_id)
    self.assertEqual(flow_obj.backtrace, "")
    self.assertEqual(flow_obj.error_message, "")
    self.assertEqual(flow_obj.flow_state, flows_pb2.Flow.FINISHED)

    flow_results = db.ReadFlowResults(client_id, flow_id, offset=0, count=128)

    results_by_path = {}
    for flow_result in flow_results:
      result = flows_pb2.FileFinderResult()
      self.assertTrue(flow_result.payload.Unpack(result))

      results_by_path[result.stat_entry.pathspec.path] = result

    self.assertNotIn(r"HKEY_LOCAL_MACHINE\SOFTWARE\FooStr", results_by_path)
    self.assertNotIn(r"HKEY_LOCAL_MACHINE\SOFTWARE\FooBytes", results_by_path)
    self.assertIn(r"HKEY_LOCAL_MACHINE\SOFTWARE\BarStr", results_by_path)
    self.assertIn(r"HKEY_LOCAL_MACHINE\SOFTWARE\BarBytes", results_by_path)
    self.assertIn(r"HKEY_LOCAL_MACHINE\SOFTWARE\BazStr", results_by_path)
    self.assertIn(r"HKEY_LOCAL_MACHINE\SOFTWARE\BazBytes", results_by_path)


def main(argv):
  # Run the full test suite
  test_lib.main(argv)


if __name__ == "__main__":
  app.run(main)
