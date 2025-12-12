#!/usr/bin/env python
import binascii
import hashlib
import os

from absl.testing import absltest

from grr_response_client import actions
from grr_response_core.lib import rdfvalue
from grr_response_core.lib.rdfvalues import client as rdf_client
from grr_response_core.lib.rdfvalues import client_action as rdf_client_action
from grr_response_core.lib.rdfvalues import client_fs as rdf_client_fs
from grr_response_core.lib.rdfvalues import flows as rdf_flows
from grr_response_core.lib.rdfvalues import paths as rdf_paths
from grr_response_core.lib.rdfvalues import protodict as rdf_protodict
from grr_response_proto import crowdstrike_pb2
from grr_response_proto import flows_pb2
from grr_response_proto import objects_pb2
from grr_response_proto import signed_commands_pb2
from grr_response_server import data_store
from grr_response_server import server_stubs
from grr_response_server.databases import db as abstract_db
from grr_response_server.databases import db_test_utils
from grr_response_server.flows.general import crowdstrike
from grr.test_lib import action_mocks
from grr.test_lib import db_test_lib
from grr.test_lib import flow_test_lib
from grr.test_lib import rrg_test_lib
from grr.test_lib import testing_startup
from grr_response_proto import rrg_pb2
from grr_response_proto.rrg import os_pb2 as rrg_os_pb2
from grr_response_proto.rrg import winreg_pb2 as rrg_winreg_pb2
from grr_response_proto.rrg.action import execute_signed_command_pb2 as rrg_execute_signed_command_pb2
from grr_response_proto.rrg.action import get_winreg_value_pb2 as rrg_get_winreg_value_pb2


class GetCrowdStrikeAgentID(flow_test_lib.FlowTestsBaseclass):

  @classmethod
  def setUpClass(cls):
    super().setUpClass()
    testing_startup.TestInit()

  @db_test_lib.WithDatabase
  def testRRGLinux(self, db: abstract_db.Database) -> None:
    command = rrg_execute_signed_command_pb2.Command()
    command.path.raw_bytes = b"/opt/CrowdStrike/falconctl"
    command.args_signed.extend(["-g", "--cid", "--aid"])

    signed_command = signed_commands_pb2.SignedCommand()
    signed_command.id = "crowdstrike_falconctl_get_cid_aid"
    signed_command.operating_system = signed_commands_pb2.SignedCommand.LINUX
    signed_command.command = command.SerializeToString()
    signed_command.ed25519_signature = b"\x00" * 64
    db.WriteSignedCommand(signed_command)

    agent_id = os.urandom(16)
    agent_id_hex = binascii.hexlify(agent_id).decode("ascii")

    client_id = db_test_utils.InitializeRRGClient(db, os_type=rrg_os_pb2.LINUX)

    def ExecuteSignedCommandHandler(session: rrg_test_lib.Session) -> None:
      args = rrg_execute_signed_command_pb2.Args()
      assert session.args.Unpack(args)

      command = rrg_execute_signed_command_pb2.Command()
      command.ParseFromString(args.command)

      if command.path.raw_bytes != b"/opt/CrowdStrike/falconctl":
        raise RuntimeError(f"Unexpected falconctl path: {command.path}")
      if command.args_signed != ["-g", "--cid", "--aid"]:
        raise RuntimeError(f"Unexpected falconctl args: {command.args}")

      result = rrg_execute_signed_command_pb2.Result()
      result.exit_code = 0
      result.stdout = f'cid="4815162342",aid="{agent_id_hex}"'.encode("ascii")
      session.Reply(result)

    flow_id = rrg_test_lib.ExecuteFlow(
        client_id=client_id,
        flow_cls=crowdstrike.GetCrowdStrikeAgentID,
        flow_args=rdf_flows.EmptyFlowArgs(),
        handlers={
            rrg_pb2.Action.EXECUTE_SIGNED_COMMAND: ExecuteSignedCommandHandler,
        },
    )

    flow_obj = db.ReadFlowObject(client_id, flow_id)
    self.assertEqual(flow_obj.error_message, "")
    self.assertEqual(flow_obj.flow_state, flows_pb2.Flow.FINISHED)

    flow_results = db.ReadFlowResults(client_id, flow_id, offset=0, count=128)
    self.assertLen(flow_results, 1)

    result = crowdstrike_pb2.GetCrowdstrikeAgentIdResult()
    self.assertTrue(flow_results[0].payload.Unpack(result))

    self.assertEqual(result.agent_id, agent_id_hex)

  @db_test_lib.WithDatabase
  def testRRGLinux_MalformedOutput(self, db: abstract_db.Database) -> None:
    command = rrg_execute_signed_command_pb2.Command()
    command.path.raw_bytes = b"/opt/CrowdStrike/falconctl"
    command.args_signed.extend(["-g", "--cid", "--aid"])

    signed_command = signed_commands_pb2.SignedCommand()
    signed_command.id = "crowdstrike_falconctl_get_cid_aid"
    signed_command.operating_system = signed_commands_pb2.SignedCommand.LINUX
    signed_command.command = command.SerializeToString()
    signed_command.ed25519_signature = b"\x00" * 64
    db.WriteSignedCommand(signed_command)

    client_id = db_test_utils.InitializeRRGClient(db, os_type=rrg_os_pb2.LINUX)

    def ExecuteSignedCommandHandler(session: rrg_test_lib.Session) -> None:
      args = rrg_execute_signed_command_pb2.Args()
      assert session.args.Unpack(args)

      command = rrg_execute_signed_command_pb2.Command()
      command.ParseFromString(args.command)

      if command.path.raw_bytes != b"/opt/CrowdStrike/falconctl":
        raise RuntimeError(f"Unexpected falconctl path: {command.path}")
      if command.args_signed != ["-g", "--cid", "--aid"]:
        raise RuntimeError(f"Unexpected falconctl args: {command.args}")

      result = rrg_execute_signed_command_pb2.Result()
      result.exit_code = 0
      result.stdout = 'cid="4815162342"'.encode("ascii")
      session.Reply(result)

    flow_id = rrg_test_lib.ExecuteFlow(
        client_id=client_id,
        flow_cls=crowdstrike.GetCrowdStrikeAgentID,
        flow_args=rdf_flows.EmptyFlowArgs(),
        handlers={
            rrg_pb2.Action.EXECUTE_SIGNED_COMMAND: ExecuteSignedCommandHandler,
        },
    )

    flow_obj = db.ReadFlowObject(client_id, flow_id)
    self.assertEqual(flow_obj.error_message, "")
    self.assertEqual(flow_obj.flow_state, flows_pb2.Flow.FINISHED)

    flow_results = db.ReadFlowResults(client_id, flow_id, offset=0, count=128)
    self.assertEmpty(flow_results)

    self.assertFlowLoggedRegex(
        client_id,
        flow_id,
        "malformed `falconctl` output",
    )

  def testLinux(self):
    assert data_store.REL_DB is not None

    agent_id = os.urandom(16)
    agent_id_hex = binascii.hexlify(agent_id).decode("ascii")

    client_id = db_test_utils.InitializeClient(data_store.REL_DB)

    client_snapshot = objects_pb2.ClientSnapshot()
    client_snapshot.client_id = client_id
    client_snapshot.knowledge_base.os = "Linux"
    data_store.REL_DB.WriteClientSnapshot(client_snapshot)

    class ExecuteCommandMock(actions.ActionPlugin):
      in_rdfvalue = rdf_client_action.ExecuteRequest
      out_rdfvalues = [rdf_client_action.ExecuteResponse]

      def Run(self, args: rdf_client_action.ExecuteRequest) -> None:
        del args  # Unused.

        stdout = f'cid="4815162342",aid="{agent_id_hex}"'

        result = rdf_client_action.ExecuteResponse()
        result.stdout = stdout.encode("ascii")
        self.SendReply(result)

    flow_id = flow_test_lib.StartAndRunFlow(
        crowdstrike.GetCrowdStrikeAgentID,
        client_mock=action_mocks.ActionMock.With({
            server_stubs.ExecuteCommand.__name__: ExecuteCommandMock,
        }),
        client_id=client_id,
    )

    results = flow_test_lib.GetFlowResults(client_id, flow_id)
    self.assertLen(results, 1)

    result = results[0]
    self.assertIsInstance(result, crowdstrike.GetCrowdstrikeAgentIdResult)
    self.assertEqual(result.agent_id, agent_id_hex)

  def testLinuxMalformedOutput(self):
    assert data_store.REL_DB is not None

    client_id = db_test_utils.InitializeClient(data_store.REL_DB)

    client_snapshot = objects_pb2.ClientSnapshot()
    client_snapshot.client_id = client_id
    client_snapshot.knowledge_base.os = "Linux"
    data_store.REL_DB.WriteClientSnapshot(client_snapshot)

    class ExecuteCommandMock(actions.ActionPlugin):
      in_rdfvalue = rdf_client_action.ExecuteRequest
      out_rdfvalues = [rdf_client_action.ExecuteResponse]

      def Run(self, args: rdf_client_action.ExecuteRequest) -> None:
        del args  # Unused.

        stdout = 'cid="4815162342"'

        result = rdf_client_action.ExecuteResponse()
        result.stdout = stdout.encode("ascii")
        self.SendReply(result)

    flow_id = flow_test_lib.StartAndRunFlow(
        crowdstrike.GetCrowdStrikeAgentID,
        client_mock=action_mocks.ActionMock.With({
            server_stubs.ExecuteCommand.__name__: ExecuteCommandMock,
        }),
        client_id=client_id,
    )

    results = flow_test_lib.GetFlowResults(client_id, flow_id)
    self.assertEmpty(results)

    self.assertFlowLoggedRegex(
        client_id,
        flow_id,
        "malformed `falconctl` output",
    )

  @db_test_lib.WithDatabase
  def testRRGWindows(self, db: abstract_db.Database) -> None:
    agent_id = os.urandom(16)
    agent_id_hex = binascii.hexlify(agent_id).decode("ascii")

    client_id = db_test_utils.InitializeRRGClient(
        db,
        os_type=rrg_os_pb2.WINDOWS,
    )

    def GetWinregValueHandler(session: rrg_test_lib.Session) -> None:
      args = rrg_get_winreg_value_pb2.Args()
      assert session.args.Unpack(args)

      if args.root != rrg_winreg_pb2.LOCAL_MACHINE:
        raise RuntimeError(f"Unexpected root: {args.root}")
      if args.key != r"SYSTEM\CurrentControlSet\Services\CSAgent\Sim":
        raise RuntimeError(f"Unexpected key: {args.key}")
      if args.name != "AG":
        raise RuntimeError(f"Unexpected value name: {args.name}")

      result = rrg_get_winreg_value_pb2.Result()
      result.root = rrg_winreg_pb2.LOCAL_MACHINE
      result.key = r"SYSTEM\CurrentControlSet\Services\CSAgent\Sim"
      result.value.name = "AG"
      result.value.bytes = agent_id
      session.Reply(result)

    flow_id = rrg_test_lib.ExecuteFlow(
        client_id=client_id,
        flow_cls=crowdstrike.GetCrowdStrikeAgentID,
        flow_args=rdf_flows.EmptyFlowArgs(),
        handlers={
            rrg_pb2.Action.GET_WINREG_VALUE: GetWinregValueHandler,
        },
    )

    flow_obj = db.ReadFlowObject(client_id, flow_id)
    self.assertEqual(flow_obj.error_message, "")
    self.assertEqual(flow_obj.flow_state, flows_pb2.Flow.FINISHED)

    flow_results = db.ReadFlowResults(client_id, flow_id, offset=0, count=128)
    self.assertLen(flow_results, 1)

    result = crowdstrike_pb2.GetCrowdstrikeAgentIdResult()
    self.assertTrue(flow_results[0].payload.Unpack(result))

    self.assertEqual(result.agent_id, agent_id_hex)

  def testWindows(self):
    assert data_store.REL_DB is not None

    agent_id = os.urandom(16)
    agent_id_hex = binascii.hexlify(agent_id).decode("ascii")

    client_id = db_test_utils.InitializeClient(data_store.REL_DB)

    client_snapshot = objects_pb2.ClientSnapshot()
    client_snapshot.client_id = client_id
    client_snapshot.knowledge_base.os = "Windows"
    data_store.REL_DB.WriteClientSnapshot(client_snapshot)

    class GetFileStatMock(actions.ActionPlugin):
      in_rdfvalue = rdf_client_action.GetFileStatRequest
      out_rdfvalues = [rdf_client_fs.StatEntry]

      def Run(self, args: rdf_client_action.GetFileStatRequest) -> None:
        del args  # Unused.

        result = rdf_client_fs.StatEntry()
        result.registry_data.data = agent_id
        self.SendReply(result)

    flow_id = flow_test_lib.StartAndRunFlow(
        crowdstrike.GetCrowdStrikeAgentID,
        client_mock=action_mocks.ActionMock.With({
            server_stubs.GetFileStat.__name__: GetFileStatMock,
        }),
        client_id=client_id,
    )

    results = flow_test_lib.GetFlowResults(client_id, flow_id)
    self.assertLen(results, 1)

    result = results[0]
    self.assertIsInstance(result, crowdstrike.GetCrowdstrikeAgentIdResult)
    self.assertEqual(result.agent_id, agent_id_hex)

  @db_test_lib.WithDatabase
  def testRRGMacOS(self, db: abstract_db.Database) -> None:
    agent_id = os.urandom(16)
    agent_id_hex = binascii.hexlify(agent_id).decode("ascii")

    client_id = db_test_utils.InitializeRRGClient(db, os_type=rrg_os_pb2.MACOS)

    flow_id = rrg_test_lib.ExecuteFlow(
        client_id=client_id,
        flow_cls=crowdstrike.GetCrowdStrikeAgentID,
        flow_args=rdf_flows.EmptyFlowArgs(),
        handlers=rrg_test_lib.FakePosixFileHandlers({
            "/Library/Application Support/CrowdStrike/Falcon/registry.base":
            # The file seems to be 40 bytes long, we replicate that.
            agent_id + os.urandom(24),
        }),
    )

    flow_obj = db.ReadFlowObject(client_id, flow_id)
    self.assertEqual(flow_obj.error_message, "")
    self.assertEqual(flow_obj.flow_state, flows_pb2.Flow.FINISHED)

    flow_results = db.ReadFlowResults(client_id, flow_id, offset=0, count=128)
    self.assertLen(flow_results, 1)

    result = crowdstrike_pb2.GetCrowdstrikeAgentIdResult()
    self.assertTrue(flow_results[0].payload.Unpack(result))

    self.assertEqual(result.agent_id, agent_id_hex)

  def testMacOS(self):
    assert data_store.REL_DB is not None

    agent_id = os.urandom(16)
    agent_id_hex = binascii.hexlify(agent_id).decode("ascii")

    client_id = db_test_utils.InitializeClient(data_store.REL_DB)

    client_snapshot = objects_pb2.ClientSnapshot()
    client_snapshot.client_id = client_id
    client_snapshot.knowledge_base.os = "Darwin"
    data_store.REL_DB.WriteClientSnapshot(client_snapshot)

    class TransferBufferMock(actions.ActionPlugin):
      in_rdfvalue = rdf_client.BufferReference
      out_rdfvalues = [rdf_client.BufferReference]

      TRANSFER_STORE = rdfvalue.SessionID(flow_name="TransferStore")

      def Run(self, args: rdf_client.BufferReference) -> None:
        del args  # Unused.

        blob = rdf_protodict.DataBlob()
        blob.data = agent_id
        self.SendReply(blob, session_id=self.TRANSFER_STORE)

        result = rdf_client.BufferReference()
        result.offset = 0
        result.length = len(blob.data)
        result.data = hashlib.sha256(blob.data).digest()
        result.pathspec.pathtype = rdf_paths.PathSpec.PathType.OS
        result.pathspec.path = r"/Library/CS/registry.base"
        self.SendReply(result)

    flow_id = flow_test_lib.StartAndRunFlow(
        crowdstrike.GetCrowdStrikeAgentID,
        client_mock=action_mocks.ActionMock.With({
            server_stubs.TransferBuffer.__name__: TransferBufferMock,
        }),
        client_id=client_id,
    )

    results = flow_test_lib.GetFlowResults(client_id, flow_id)
    self.assertLen(results, 1)

    result = results[0]
    self.assertIsInstance(result, crowdstrike.GetCrowdstrikeAgentIdResult)
    self.assertEqual(result.agent_id, agent_id_hex)


if __name__ == "__main__":
  absltest.main()
