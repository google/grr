#!/usr/bin/env python
import re

from absl.testing import absltest

from grr_response_client import actions
from grr_response_core.lib import rdfvalue
from grr_response_core.lib.rdfvalues import flows as rdf_flows
from grr_response_proto import flows_pb2
from grr_response_proto import signed_commands_pb2
from grr_response_server.databases import db as abstract_db
from grr_response_server.databases import db_test_utils
from grr_response_server.flows.general import memsize
from grr.test_lib import action_mocks
from grr.test_lib import db_test_lib
from grr.test_lib import flow_test_lib
from grr.test_lib import rrg_test_lib
from grr.test_lib import testing_startup
from grr_response_proto import rrg_pb2
from grr_response_proto.rrg import os_pb2 as rrg_os_pb2
from grr_response_proto.rrg.action import execute_signed_command_pb2 as rrg_execute_signed_command_pb2
from grr_response_proto.rrg.action import grep_file_contents_pb2 as rrg_grep_file_contents_pb2
from grr_response_proto.rrg.action import query_wmi_pb2 as rrg_query_wmi_pb2


class GetMemorySizeTest(flow_test_lib.FlowTestsBaseclass):

  @classmethod
  def setUpClass(cls):
    super().setUpClass()
    testing_startup.TestInit()

  @db_test_lib.WithDatabase
  def testRRGLinux(self, db: abstract_db.Database):
    client_id = db_test_utils.InitializeRRGClient(
        db,
        os_type=rrg_os_pb2.LINUX,
    )

    def GrepFileContentsHandler(session: rrg_test_lib.Session) -> None:
      args = rrg_grep_file_contents_pb2.Args()
      assert session.args.Unpack(args)

      if args.path.raw_bytes.decode("utf-8") == "/proc/meminfo":
        content = """\
MemTotal:       32567252 kB
MemFree:         5855296 kB
MemAvailable:   17507204 kB
Buffers:          493220 kB
Cached:         13366816 kB
SwapCached:         5108 kB
Active:         13412136 kB
Inactive:        9500632 kB
HugePages_Total:       0
HugePages_Free:        0
VmallocTotal:   34359738367 kB
VmallocUsed:       81648 kB
VmallocChunk:          0 kB
"""
      else:
        raise RuntimeError(f"Unknown path: {args.path!r}")

      for line in content.splitlines():
        for match in re.finditer(args.regex, line):
          result = rrg_grep_file_contents_pb2.Result()
          result.offset = match.start()
          result.content = match[0]
          session.Reply(result)

    flow_id = rrg_test_lib.ExecuteFlow(
        client_id=client_id,
        flow_cls=memsize.GetMemorySize,
        flow_args=rdf_flows.EmptyFlowArgs(),
        handlers={
            rrg_pb2.GREP_FILE_CONTENTS: GrepFileContentsHandler,
        },
    )

    flow_obj = db.ReadFlowObject(client_id, flow_id)
    self.assertEqual(flow_obj.flow_state, flows_pb2.Flow.FINISHED)

    results = db.ReadFlowResults(client_id, flow_id, offset=0, count=1024)
    self.assertLen(results, 1)

    result = flows_pb2.GetMemorySizeResult()
    result.ParseFromString(results[0].payload.value)

    self.assertEqual(result.total_bytes, 32567252 * 1024)

  @db_test_lib.WithDatabase
  def testRRGWindows(self, db: abstract_db.Database):
    client_id = db_test_utils.InitializeRRGClient(
        db,
        os_type=rrg_os_pb2.WINDOWS,
    )

    def QueryWmiHandler(session: rrg_test_lib.Session) -> None:
      args = rrg_query_wmi_pb2.Args()
      assert session.args.Unpack(args)

      if not args.query.strip().startswith("SELECT "):
        raise RuntimeError("Non-`SELECT` WMI query")

      if "Win32_ComputerSystem" not in args.query:
        raise RuntimeError(f"Unexpected WMI query: {args.query!r}")

      result = rrg_query_wmi_pb2.Result()
      result.row["TotalPhysicalMemory"].uint = 34355990528
      session.Reply(result)

    flow_id = rrg_test_lib.ExecuteFlow(
        client_id=client_id,
        flow_cls=memsize.GetMemorySize,
        flow_args=rdf_flows.EmptyFlowArgs(),
        handlers={
            rrg_pb2.QUERY_WMI: QueryWmiHandler,
        },
    )

    flow_obj = db.ReadFlowObject(client_id, flow_id)
    self.assertEqual(flow_obj.flow_state, flows_pb2.Flow.FINISHED)

    results = db.ReadFlowResults(client_id, flow_id, offset=0, count=1024)
    self.assertLen(results, 1)

    result = flows_pb2.GetMemorySizeResult()
    result.ParseFromString(results[0].payload.value)

    self.assertEqual(result.total_bytes, 34355990528)

  @db_test_lib.WithDatabase
  def testRRGMacos(self, db: abstract_db.Database):
    # TODO: Load signed commands from the `.textproto` file to
    # ensure integrity.
    command = rrg_execute_signed_command_pb2.Command()
    command.path.raw_bytes = "/usr/sbin/sysctl".encode("utf-8")
    command.args_signed.append("-n")
    command.args_signed.append("hw.memsize")

    signed_command = signed_commands_pb2.SignedCommand()
    signed_command.id = "sysctl_hw_memsize"
    signed_command.operating_system = signed_commands_pb2.SignedCommand.OS.MACOS
    signed_command.command = command.SerializeToString()
    signed_command.ed25519_signature = b"\x00" * 64
    db.WriteSignedCommand(signed_command)

    client_id = db_test_utils.InitializeRRGClient(
        db,
        os_type=rrg_os_pb2.MACOS,
    )

    def ExecuteSignedCommandHandler(session: rrg_test_lib.Session) -> None:
      args = rrg_execute_signed_command_pb2.Args()
      assert session.args.Unpack(args)

      command = rrg_execute_signed_command_pb2.Command()
      command.ParseFromString(args.command)

      if command.path.raw_bytes != "/usr/sbin/sysctl".encode("utf-8"):
        raise RuntimeError(f"Unexpected command path: {command.path}")

      if command.args_signed != ["-n", "hw.memsize"]:
        raise RuntimeError(f"Unexpected command args: {command.args_signed}")

      result = rrg_execute_signed_command_pb2.Result()
      result.exit_code = 0
      result.stdout = "17179869184\n".encode("ascii")
      session.Reply(result)

    flow_id = rrg_test_lib.ExecuteFlow(
        client_id=client_id,
        flow_cls=memsize.GetMemorySize,
        flow_args=rdf_flows.EmptyFlowArgs(),
        handlers={
            rrg_pb2.EXECUTE_SIGNED_COMMAND: ExecuteSignedCommandHandler,
        },
    )

    flow_obj = db.ReadFlowObject(client_id, flow_id)
    self.assertEqual(flow_obj.flow_state, flows_pb2.Flow.FINISHED)

    results = db.ReadFlowResults(client_id, flow_id, offset=0, count=1024)
    self.assertLen(results, 1)

    result = flows_pb2.GetMemorySizeResult()
    result.ParseFromString(results[0].payload.value)

    self.assertEqual(result.total_bytes, 17179869184)

  @db_test_lib.WithDatabase
  def testLegacy(self, db: abstract_db.Database):
    creator = db_test_utils.InitializeUser(db)
    client_id = db_test_utils.InitializeClient(db)

    class FakeGetMemorySize(actions.ActionPlugin):

      def Run(self, args) -> None:
        del args  # Unused.

        self.SendReply(rdfvalue.RDFInteger(42 * 1024 * 1024 * 1024))

    flow_id = flow_test_lib.StartAndRunFlow(
        memsize.GetMemorySize,
        action_mocks.ActionMock.With({
            "GetMemorySize": FakeGetMemorySize,
        }),
        client_id=client_id,
        creator=creator,
    )

    results = flow_test_lib.GetFlowResults(client_id, flow_id)
    self.assertLen(results, 1)
    self.assertEqual(results[0].total_bytes, 42 * 1024 * 1024 * 1024)


if __name__ == "__main__":
  absltest.main()
