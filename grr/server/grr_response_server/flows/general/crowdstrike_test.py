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
from grr_response_core.lib.rdfvalues import paths as rdf_paths
from grr_response_core.lib.rdfvalues import protodict as rdf_protodict
from grr_response_proto import objects_pb2
from grr_response_server import data_store
from grr_response_server import server_stubs
from grr_response_server.databases import db_test_utils
from grr_response_server.flows.general import crowdstrike
from grr.test_lib import action_mocks
from grr.test_lib import flow_test_lib
from grr.test_lib import testing_startup


class GetCrowdStrikeAgentID(flow_test_lib.FlowTestsBaseclass):

  @classmethod
  def setUpClass(cls):
    super().setUpClass()
    testing_startup.TestInit()

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
