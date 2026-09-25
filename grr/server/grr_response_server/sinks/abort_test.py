#!/usr/bin/env python
from absl.testing import absltest

from google.protobuf import any_pb2
from grr_response_proto import flows_pb2
from grr_response_server import flow
from grr_response_server import flow_base
from grr_response_server import flow_responses
from grr_response_server import rrg_stubs
from grr_response_server.databases import db as abstract_db
from grr_response_server.databases import db_test_utils
from grr_response_server.databases import db_utils
from grr_response_server.sinks import abort as abort_sink
from grr.test_lib import db_test_lib
from grr_response_proto import rrg_pb2
from grr_response_proto.rrg import abort_pb2 as rrg_abort_pb2


class AbortSinkTest(absltest.TestCase):

  @db_test_lib.WithDatabase
  def testAccept(self, db: abstract_db.Database):
    client_id = db_test_utils.InitializeRRGClient(db)

    class AbortSinkTestAcceptFlow(
        flow_base.FlowBase[
            flows_pb2.EmptyFlowArgs,
            flows_pb2.DefaultFlowStore,
            flows_pb2.DefaultFlowProgress,
        ]
    ):

      def Start(self):
        rrg_stubs.GetSystemMetadata().Call(self._ProcessSystemMetadata)  # pyrefly: ignore[bad-argument-type]

      @flow_base.UseProto2AnyResponses  # pyrefly: ignore[bad-argument-type]
      def _ProcessSystemMetadata(
          self,
          responses: flow_responses.Responses[any_pb2.Any],
      ) -> None:
        del responses  # Unused.
        raise NotImplementedError()  # This should never be reached.

    flow_id = flow.StartFlow(
        client_id=client_id,
        flow_cls=AbortSinkTestAcceptFlow,
        proto_flow_args=flows_pb2.EmptyFlowArgs(),
    )

    abort = rrg_abort_pb2.Abort()
    abort.flow_id = db_utils.FlowIDToInt(flow_id)
    abort.request_id = 1
    abort.request_time.GetCurrentTime()
    abort.startup_time.GetCurrentTime()

    parcel = rrg_pb2.Parcel()
    parcel.payload.Pack(abort)

    sink = abort_sink.AbortSink()
    sink.Accept(client_id, parcel)

    flow_obj = db.ReadFlowObject(client_id, flow_id)
    self.assertEqual(flow_obj.flow_state, flows_pb2.Flow.CRASHED)


if __name__ == "__main__":
  absltest.main()
