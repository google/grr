#!/usr/bin/env python
from absl.testing import absltest

from google.protobuf import any_pb2
from grr_response_core.lib import config_lib
from grr_response_core.lib.rdfvalues import flows as rdf_flows
from grr_response_core.stats import default_stats_collector
from grr_response_core.stats import stats_collector_instance
from grr_response_proto import flows_pb2
from grr_response_server import flow_base
from grr_response_server import flow_responses
from grr_response_server import rrg_stubs
from grr_response_server.databases import db as abstract_db
from grr_response_server.databases import db_test_utils
from grr.test_lib import db_test_lib
from grr.test_lib import rrg_test_lib
from grr_response_proto import rrg_pb2
from grr_response_proto.rrg import fs_pb2 as rrg_fs_pb2
from grr_response_proto.rrg.action import get_file_metadata_pb2 as rrg_get_file_metadata_pb2


class ActionTest(absltest.TestCase):

  @classmethod
  def setUpClass(cls):
    super().setUpClass()

    # TODO: Remove once the "default" instance is actually default.
    stats_collector_instance.Set(
        default_stats_collector.DefaultStatsCollector()
    )

    # TODO: Remove once `Server.disable_rrg_support` config option
    # is no longer needed for calling RRG.
    config_lib.ParseConfigCommandLine()

  @db_test_lib.WithDatabase
  def testCall(self, db: abstract_db.Database):
    client_id = db_test_utils.InitializeRRGClient(db)

    def GetFileMetadataHandler(
        session: rrg_test_lib.Session,
    ):
      args = rrg_get_file_metadata_pb2.Args()
      args.ParseFromString(session.args.value)

      assert len(args.paths) == 1
      assert args.paths[0].raw_bytes == "/foo/bar".encode("utf-8")

      result = rrg_get_file_metadata_pb2.Result()
      result.path.raw_bytes = "/foo/bar".encode("utf-8")
      result.metadata.size = 1337
      session.Reply(result)

    flow_process_done = False

    class CallGetFileMetadataFlow(
        flow_base.FlowBase[
            flows_pb2.EmptyFlowArgs,
            flows_pb2.DefaultFlowStore,
            flows_pb2.DefaultFlowProgress,
        ]
    ):

      def Start(self) -> None:
        action = rrg_stubs.GetFileMetadata()
        action.args.paths.add().raw_bytes = "/foo/bar".encode("utf-8")
        action.Call(self.Process)

      @flow_base.UseProto2AnyResponses
      def Process(
          self,
          responses: flow_responses.Responses[any_pb2.Any],
      ) -> None:
        assert responses.success
        assert len(responses) == 1

        response = rrg_get_file_metadata_pb2.Result()
        response.ParseFromString(list(responses)[0].value)

        assert response.path.raw_bytes == "/foo/bar".encode("utf-8")
        assert response.metadata.size == 1337

        nonlocal flow_process_done
        flow_process_done = True

    flow_id = rrg_test_lib.ExecuteFlow(
        client_id=client_id,
        flow_cls=CallGetFileMetadataFlow,
        flow_args=rdf_flows.EmptyFlowArgs(),
        handlers={
            rrg_pb2.GET_FILE_METADATA: GetFileMetadataHandler,
        },
    )

    flow_obj = db.ReadFlowObject(client_id=client_id, flow_id=flow_id)
    self.assertEqual(flow_obj.flow_state, flows_pb2.Flow.FINISHED)
    self.assertTrue(flow_process_done)

  @db_test_lib.WithDatabase
  def testCall_RequestData(self, db: abstract_db.Database):
    client_id = db_test_utils.InitializeRRGClient(db)

    def GetSystemMetadataHandler(
        session: rrg_test_lib.Session,
    ):
      del session  # Unused.

    flow_process_done = False

    class CallGetSystemMetadataFlow(
        flow_base.FlowBase[
            flows_pb2.EmptyFlowArgs,
            flows_pb2.DefaultFlowStore,
            flows_pb2.DefaultFlowProgress,
        ]
    ):

      def Start(self) -> None:
        action = rrg_stubs.GetSystemMetadata()
        action.context["foo"] = "quux"
        action.context["bar"] = "norf"
        action.Call(self.Process)

      @flow_base.UseProto2AnyResponses
      def Process(
          self,
          responses: flow_responses.Responses[any_pb2.Any],
      ) -> None:
        assert responses.success

        assert responses.request_data["foo"] == "quux"
        assert responses.request_data["bar"] == "norf"

        nonlocal flow_process_done
        flow_process_done = True

    flow_id = rrg_test_lib.ExecuteFlow(
        client_id=client_id,
        flow_cls=CallGetSystemMetadataFlow,
        flow_args=rdf_flows.EmptyFlowArgs(),
        handlers={
            rrg_pb2.GET_SYSTEM_METADATA: GetSystemMetadataHandler,
        },
    )

    flow_obj = db.ReadFlowObject(client_id=client_id, flow_id=flow_id)
    self.assertEqual(flow_obj.flow_state, flows_pb2.Flow.FINISHED)
    self.assertTrue(flow_process_done)

  @db_test_lib.WithDatabase
  def testAddFilter(self, db: abstract_db.Database):
    client_id = db_test_utils.InitializeRRGClient(db)

    def GetFileMetadataHandler(
        session: rrg_test_lib.Session,
    ) -> None:
      result_foo = rrg_get_file_metadata_pb2.Result()
      result_foo.path.raw_bytes = "/foo".encode("utf-8")
      result_foo.metadata.size = 42
      session.Reply(result_foo)

      result_bar = rrg_get_file_metadata_pb2.Result()
      result_bar.path.raw_bytes = "/bar".encode("utf-8")
      result_bar.metadata.size = 1337
      session.Reply(result_bar)

      result_baz = rrg_get_file_metadata_pb2.Result()
      result_baz.path.raw_bytes = "/baz".encode("utf-8")
      result_baz.metadata.size = 1138
      session.Reply(result_baz)

    flow_process_done = False

    class CallGetFileMetadataWithFilterFlow(
        flow_base.FlowBase[
            flows_pb2.EmptyFlowArgs,
            flows_pb2.DefaultFlowStore,
            flows_pb2.DefaultFlowProgress,
        ]
    ):

      def Start(self) -> None:
        action = rrg_stubs.GetFileMetadata()

        path_cond = action.AddFilter().conditions.add()
        path_cond.bytes_match = b"^/ba.*$"
        path_cond.field.append(
            rrg_get_file_metadata_pb2.Result.PATH_FIELD_NUMBER,
        )
        path_cond.field.append(
            rrg_fs_pb2.Path.RAW_BYTES_FIELD_NUMBER,
        )

        action.Call(self.Process)

      @flow_base.UseProto2AnyResponses
      def Process(
          self,
          responses: flow_responses.Responses[any_pb2.Any],
      ) -> None:
        assert responses.success
        assert len(responses) == 2

        response_bar = rrg_get_file_metadata_pb2.Result()
        response_bar.ParseFromString(list(responses)[0].value)
        assert response_bar.path.raw_bytes == "/bar".encode("utf-8")
        assert response_bar.metadata.size == 1337

        response_baz = rrg_get_file_metadata_pb2.Result()
        response_baz.ParseFromString(list(responses)[1].value)
        assert response_baz.path.raw_bytes == "/baz".encode("utf-8")
        assert response_baz.metadata.size == 1138

        nonlocal flow_process_done
        flow_process_done = True

    flow_id = rrg_test_lib.ExecuteFlow(
        client_id=client_id,
        flow_cls=CallGetFileMetadataWithFilterFlow,
        flow_args=rdf_flows.EmptyFlowArgs(),
        handlers={
            rrg_pb2.GET_FILE_METADATA: GetFileMetadataHandler,
        },
    )

    flow_obj = db.ReadFlowObject(client_id=client_id, flow_id=flow_id)
    self.assertEqual(flow_obj.flow_state, flows_pb2.Flow.FINISHED)
    self.assertTrue(flow_process_done)


if __name__ == "__main__":
  absltest.main()
