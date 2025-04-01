#!/usr/bin/env python
import hashlib
from unittest import mock

from absl.testing import absltest

from google.protobuf import any_pb2
from google.protobuf import wrappers_pb2
from grr_response_core.lib import rdfvalue
from grr_response_core.lib.rdfvalues import flows as rdf_flows
from grr_response_proto import flows_pb2
from grr_response_server import flow_base
from grr_response_server import flow_responses
from grr_response_server import sinks
from grr_response_server.databases import db as abstract_db
from grr_response_server.databases import db_test_utils
from grr_response_server.sinks import test_lib as sinks_test_lib
from grr.test_lib import db_test_lib
from grr.test_lib import rrg_test_lib
from grr.test_lib import testing_startup
from grr_response_proto import rrg_pb2
from grr_response_proto.rrg import blob_pb2 as rrg_blob_pb2
from grr_response_proto.rrg import startup_pb2 as rrg_startup_pb2
from grr_response_proto.rrg.action import get_file_contents_pb2 as rrg_get_file_contents_pb2
from grr_response_proto.rrg.action import get_system_metadata_pb2 as rrg_get_system_metadata_pb2
from grr_response_proto.rrg.action import get_winreg_value_pb2 as rrg_get_winreg_value_pb2
from grr_response_proto.rrg.action import list_winreg_keys_pb2 as rrg_list_winreg_keys_pb2
from grr_response_proto.rrg.action import list_winreg_values_pb2 as rrg_list_winreg_values_pb2


class ExecuteFlowTest(absltest.TestCase):

  @classmethod
  def setUpClass(cls):
    super().setUpClass()
    testing_startup.TestInit()

  @db_test_lib.WithDatabase
  def testNoRRGCalls(self, db: abstract_db.Database):
    client_id = db_test_utils.InitializeClient(db)

    start_called = False
    end_called = False

    class NoRRGCallsFlow(flow_base.FlowBase):

      def Start(self) -> None:
        nonlocal start_called
        start_called = True

      def End(self) -> None:
        nonlocal end_called
        end_called = True

    flow_id = rrg_test_lib.ExecuteFlow(
        client_id=client_id,
        flow_cls=NoRRGCallsFlow,
        flow_args=rdf_flows.EmptyFlowArgs(),
        handlers={},
    )

    self.assertTrue(start_called)
    self.assertTrue(end_called)

    results = db.ReadFlowResults(client_id, flow_id, offset=0, count=1024)
    self.assertEmpty(results)

  @db_test_lib.WithDatabase
  def testSingleRRGCall(self, db: abstract_db.Database):
    client_id = db_test_utils.InitializeClient(db)
    db.WriteClientRRGStartup(client_id, rrg_startup_pb2.Startup())

    def GetSystemMetadataHandler(
        session: rrg_test_lib.Session,
    ) -> None:
      session.Reply(rrg_get_system_metadata_pb2.Result(version="1.3.3.7"))

    class SingleRRGCallFlow(flow_base.FlowBase):

      def Start(self) -> None:
        self.CallRRG(
            action=rrg_pb2.Action.GET_SYSTEM_METADATA,
            args=rrg_get_system_metadata_pb2.Args(),
            next_state=self._ProcessSystemMetadata.__name__,
        )

      @flow_base.UseProto2AnyResponses
      def _ProcessSystemMetadata(
          self,
          responses: flow_responses.Responses[any_pb2.Any],
      ) -> None:
        assert len(responses) == 1

        result = rrg_get_system_metadata_pb2.Result()
        assert list(responses)[0].Unpack(result)

        self.SendReply(rdfvalue.RDFString(result.version))

    flow_id = rrg_test_lib.ExecuteFlow(
        client_id=client_id,
        flow_cls=SingleRRGCallFlow,
        flow_args=rdf_flows.EmptyFlowArgs(),
        handlers={
            rrg_pb2.Action.GET_SYSTEM_METADATA: GetSystemMetadataHandler,
        },
    )

    results = db.ReadFlowResults(client_id, flow_id, offset=0, count=1024)
    self.assertLen(results, 1)

    result = wrappers_pb2.StringValue()
    self.assertTrue(results[0].payload.Unpack(result))
    self.assertEqual(result.value, "1.3.3.7")

  @db_test_lib.WithDatabase
  def testMultipleRRGCalls(self, db: abstract_db.Database):
    client_id = db_test_utils.InitializeClient(db)
    db.WriteClientRRGStartup(client_id, rrg_startup_pb2.Startup())

    def GetWinregValueHandler(
        session: rrg_test_lib.Session,
    ) -> None:
      args = rrg_get_winreg_value_pb2.Args()
      assert session.args.Unpack(args)

      result = rrg_get_winreg_value_pb2.Result()

      if args.key == "Foo\\Bar":
        result.value.string = "bar"
      elif args.key == "Foo\\Baz":
        result.value.string = "baz"
      elif args.key == "Quux":
        result.value.uint32 = 0x1337
      else:
        raise RuntimeError(f"Unexpected registry key: {args.key}")

      session.Reply(result)

    class MultipleRRGCallsFlow(flow_base.FlowBase):

      def Start(self) -> None:
        self.CallRRG(
            action=rrg_pb2.Action.GET_WINREG_VALUE,
            args=rrg_get_winreg_value_pb2.Args(key="Foo\\Bar"),
            next_state=self._ProcessGetWinregValueFoo.__name__,
        )
        self.CallRRG(
            action=rrg_pb2.Action.GET_WINREG_VALUE,
            args=rrg_get_winreg_value_pb2.Args(key="Foo\\Baz"),
            next_state=self._ProcessGetWinregValueFoo.__name__,
        )
        self.CallRRG(
            action=rrg_pb2.Action.GET_WINREG_VALUE,
            args=rrg_get_winreg_value_pb2.Args(key="Quux"),
            next_state=self._ProcessGetWinregValueQuux.__name__,
        )

      @flow_base.UseProto2AnyResponses
      def _ProcessGetWinregValueFoo(
          self,
          responses: flow_responses.Responses[any_pb2.Any],
      ) -> None:
        assert len(responses) == 1

        result = rrg_get_winreg_value_pb2.Result()
        assert list(responses)[0].Unpack(result)

        self.SendReply(rdfvalue.RDFString(result.value.string))

      @flow_base.UseProto2AnyResponses
      def _ProcessGetWinregValueQuux(
          self,
          responses: flow_responses.Responses[any_pb2.Any],
      ) -> None:
        assert len(responses) == 1

        result = rrg_get_winreg_value_pb2.Result()
        assert list(responses)[0].Unpack(result)

        self.SendReply(rdfvalue.RDFString(f"quux_{result.value.uint32:X}"))

    flow_id = rrg_test_lib.ExecuteFlow(
        client_id=client_id,
        flow_cls=MultipleRRGCallsFlow,
        flow_args=rdf_flows.EmptyFlowArgs(),
        handlers={
            rrg_pb2.Action.GET_WINREG_VALUE: GetWinregValueHandler,
        },
    )
    results = db.ReadFlowResults(client_id, flow_id, offset=0, count=1024)
    self.assertLen(results, 3)

    result_0 = wrappers_pb2.StringValue()
    results[0].payload.Unpack(result_0)
    self.assertEqual(result_0.value, "bar")

    result_1 = wrappers_pb2.StringValue()
    results[1].payload.Unpack(result_1)
    self.assertEqual(result_1.value, "baz")

    result_2 = wrappers_pb2.StringValue()
    results[2].payload.Unpack(result_2)
    self.assertEqual(result_2.value, "quux_1337")

  @db_test_lib.WithDatabase
  def testMultipleSequentialRRGCalls(self, db: abstract_db.Database):
    client_id = db_test_utils.InitializeClient(db)
    db.WriteClientRRGStartup(client_id, rrg_startup_pb2.Startup())

    def ListWinregKeysHandler(
        session: rrg_test_lib.Session,
    ) -> None:
      args = rrg_list_winreg_keys_pb2.Args()
      assert session.args.Unpack(args)

      if args.key != "Foo":
        raise RuntimeError(f"Unexpected registry key: {args.key}")

      result_1 = rrg_list_winreg_keys_pb2.Result()
      result_1.key = args.key
      result_1.subkey = "Bar"
      session.Reply(result_1)

      result_2 = rrg_list_winreg_keys_pb2.Result()
      result_2.key = args.key
      result_2.subkey = "Baz"
      session.Reply(result_2)

    def GetWinregValueHandler(
        session: rrg_test_lib.Session,
    ) -> None:
      args = rrg_get_winreg_value_pb2.Args()
      assert session.args.Unpack(args)

      result = rrg_get_winreg_value_pb2.Result()

      if args.key == "Foo\\Bar":
        result.value.string = "bar"
      elif args.key == "Foo\\Baz":
        result.value.string = "baz"
      else:
        raise RuntimeError(f"Unexpected registry key: {args.key}")

      session.Reply(result)

    class MultipleSequentialRRGCallsFlow(flow_base.FlowBase):

      def Start(self) -> None:
        self.CallRRG(
            action=rrg_pb2.Action.LIST_WINREG_KEYS,
            args=rrg_list_winreg_keys_pb2.Args(key="Foo"),
            next_state=self._ProcessListWinregKeysFoo.__name__,
        )

      @flow_base.UseProto2AnyResponses
      def _ProcessListWinregKeysFoo(
          self,
          responses: flow_responses.Responses[any_pb2.Any],
      ) -> None:
        for response in responses:
          result = rrg_list_winreg_keys_pb2.Result()
          assert response.Unpack(result)

          self.CallRRG(
              action=rrg_pb2.Action.GET_WINREG_VALUE,
              args=rrg_get_winreg_value_pb2.Args(
                  key=f"{result.key}\\{result.subkey}",
              ),
              next_state=self._ProcessGetWinregValue.__name__,
          )

      @flow_base.UseProto2AnyResponses
      def _ProcessGetWinregValue(
          self,
          responses: flow_responses.Responses[any_pb2.Any],
      ) -> None:
        assert len(responses) == 1

        result = rrg_get_winreg_value_pb2.Result()
        assert list(responses)[0].Unpack(result)

        self.SendReply(rdfvalue.RDFString(result.value.string))

    flow_id = rrg_test_lib.ExecuteFlow(
        client_id=client_id,
        flow_cls=MultipleSequentialRRGCallsFlow,
        flow_args=rdf_flows.EmptyFlowArgs(),
        handlers={
            rrg_pb2.Action.LIST_WINREG_KEYS: ListWinregKeysHandler,
            rrg_pb2.Action.GET_WINREG_VALUE: GetWinregValueHandler,
        },
    )
    results = db.ReadFlowResults(client_id, flow_id, offset=0, count=1024)
    self.assertLen(results, 2)

    result_0 = wrappers_pb2.StringValue()
    results[0].payload.Unpack(result_0)
    self.assertEqual(result_0.value, "bar")

    result_1 = wrappers_pb2.StringValue()
    results[1].payload.Unpack(result_1)
    self.assertEqual(result_1.value, "baz")

  @db_test_lib.WithDatabase
  def testNestedFlows(self, db: abstract_db.Database):
    client_id = db_test_utils.InitializeClient(db)
    db.WriteClientRRGStartup(client_id, rrg_startup_pb2.Startup())

    def ListWinregValuesHandler(
        session: rrg_test_lib.Session,
    ) -> None:
      args = rrg_list_winreg_values_pb2.Args()
      assert session.args.Unpack(args)

      if args.key != "Foo":
        raise RuntimeError(f"Unexpected registry key: {args.key}")

      result_1 = rrg_list_winreg_values_pb2.Result()
      result_1.value.string = "bar"
      session.Reply(result_1)

      result_2 = rrg_list_winreg_values_pb2.Result()
      result_2.value.string = "baz"
      session.Reply(result_2)

      result_3 = rrg_list_winreg_values_pb2.Result()
      result_3.value.string = "quux"
      session.Reply(result_3)

    class NestedFlowsParentFlow(flow_base.FlowBase):

      def Start(self) -> None:
        self.CallFlow(
            NestedFlowsChildFlow.__name__,
            next_state=self._ProcessChildFlow.__name__,
        )

      # TODO: Responses from child flows cannot be processed using
      # `UseProto2AnyResponses` methods. Once it is supported this method should
      # be annotated with it.
      def _ProcessChildFlow(
          self,
          responses: flow_responses.Responses[rdfvalue.RDFString],
      ) -> None:
        for response in responses:
          assert isinstance(response, rdfvalue.RDFString)
          self.SendReply(response)

    class NestedFlowsChildFlow(flow_base.FlowBase):

      def Start(self) -> None:
        self.CallRRG(
            action=rrg_pb2.Action.LIST_WINREG_VALUES,
            args=rrg_list_winreg_values_pb2.Args(key="Foo"),
            next_state=self._ProcessListWinregValuesFoo.__name__,
        )

      @flow_base.UseProto2AnyResponses
      def _ProcessListWinregValuesFoo(
          self,
          responses: flow_responses.Responses[any_pb2.Any],
      ) -> None:
        for response in responses:
          result = rrg_list_winreg_values_pb2.Result()
          assert response.Unpack(result)

          self.SendReply(rdfvalue.RDFString(result.value.string))

    flow_id = rrg_test_lib.ExecuteFlow(
        client_id=client_id,
        flow_cls=NestedFlowsParentFlow,
        flow_args=rdf_flows.EmptyFlowArgs(),
        handlers={
            rrg_pb2.Action.LIST_WINREG_VALUES: ListWinregValuesHandler,
        },
    )
    results = db.ReadFlowResults(client_id, flow_id, offset=0, count=1024)
    self.assertLen(results, 3)

    result_0 = wrappers_pb2.StringValue()
    results[0].payload.Unpack(result_0)
    self.assertEqual(result_0.value, "bar")

    result_1 = wrappers_pb2.StringValue()
    results[1].payload.Unpack(result_1)
    self.assertEqual(result_1.value, "baz")

    result_2 = wrappers_pb2.StringValue()
    results[2].payload.Unpack(result_2)
    self.assertEqual(result_2.value, "quux")

  @db_test_lib.WithDatabase
  def testActionError(self, db: abstract_db.Database):
    client_id = db_test_utils.InitializeClient(db)
    db.WriteClientRRGStartup(client_id, rrg_startup_pb2.Startup())

    def GetSystemMetadataHandler(
        session: rrg_test_lib.Session,
    ) -> None:
      del session  # Unused.

      raise RuntimeError("Ala ma kota, a kot ma Alę")

    process_system_metadata_called = False

    class ActionErrorFlow(flow_base.FlowBase):

      def Start(self) -> None:
        self.CallRRG(
            action=rrg_pb2.Action.GET_SYSTEM_METADATA,
            args=rrg_get_system_metadata_pb2.Args(),
            next_state=self._ProcessSystemMetadata.__name__,
        )

      @flow_base.UseProto2AnyResponses
      def _ProcessSystemMetadata(
          self,
          responses: flow_responses.Responses[any_pb2.Any],
      ) -> None:
        assert not responses.success
        assert responses.status is not None
        assert responses.status.error_message == "Ala ma kota, a kot ma Alę"

        nonlocal process_system_metadata_called
        process_system_metadata_called = True

    flow_id = rrg_test_lib.ExecuteFlow(
        client_id=client_id,
        flow_cls=ActionErrorFlow,
        flow_args=rdf_flows.EmptyFlowArgs(),
        handlers={
            rrg_pb2.Action.GET_SYSTEM_METADATA: GetSystemMetadataHandler,
        },
    )

    self.assertTrue(process_system_metadata_called)

    flow_obj = db.ReadFlowObject(client_id, flow_id)
    self.assertEqual(flow_obj.flow_state, flows_pb2.Flow.FlowState.FINISHED)

  @db_test_lib.WithDatabase
  def testStartFlowError(self, db: abstract_db.Database):
    client_id = db_test_utils.InitializeClient(db)

    class StartFlowErrorFlow(flow_base.FlowBase):

      def Start(self) -> None:
        raise flow_base.FlowError("Ala ma kota, a kot ma Alę")

    flow_id = rrg_test_lib.ExecuteFlow(
        client_id=client_id,
        flow_cls=StartFlowErrorFlow,
        flow_args=rdf_flows.EmptyFlowArgs(),
        handlers={},
    )

    flow_obj = db.ReadFlowObject(client_id, flow_id)
    self.assertEqual(flow_obj.flow_state, flows_pb2.Flow.FlowState.ERROR)
    self.assertEqual(flow_obj.error_message, "Ala ma kota, a kot ma Alę")

  @db_test_lib.WithDatabase
  def testNestedFlowError(self, db: abstract_db.Database):
    client_id = db_test_utils.InitializeClient(db)

    process_child_flow_called = False

    class NestedFlowErrorParentFlow(flow_base.FlowBase):

      def Start(self) -> None:
        self.CallFlow(
            NestedFlowErrorChildFlow.__name__,
            next_state=self._ProcessChildFlow.__name__,
        )

      # TODO: Responses from child flows cannot be processed using
      # `UseProto2AnyResponses` methods. Once it is supported this method should
      # be annotated with it.
      def _ProcessChildFlow(
          self,
          responses: flow_responses.Responses[None],
      ) -> None:
        assert not responses.success
        assert responses.status is not None
        # Unfortunately, the flow execution mechanism does not pass correct
        # error message in the status, so we cannot make assertions on that.

        nonlocal process_child_flow_called
        process_child_flow_called = True

    class NestedFlowErrorChildFlow(flow_base.FlowBase):

      def Start(self) -> None:
        self.CallRRG(
            action=rrg_pb2.Action.GET_SYSTEM_METADATA,
            args=rrg_get_system_metadata_pb2.Args(),
            next_state=self._ProcessSystemMetadata.__name__,
        )

      @flow_base.UseProto2AnyResponses
      def _ProcessSystemMetadata(
          self,
          responses: flow_responses.Responses[any_pb2.Any],
      ) -> None:
        raise flow_base.FlowError("Ala ma kota, a kot ma Alę")

    flow_id = rrg_test_lib.ExecuteFlow(
        client_id=client_id,
        flow_cls=NestedFlowErrorParentFlow,
        flow_args=rdf_flows.EmptyFlowArgs(),
        handlers={},
    )

    self.assertTrue(process_child_flow_called)

    # Only the child should have failed, parent flow should finish fine.
    flow_obj = db.ReadFlowObject(client_id, flow_id)
    self.assertEqual(flow_obj.flow_state, flows_pb2.Flow.FlowState.FINISHED)

  @db_test_lib.WithDatabase
  def testMissingHandlerError(self, db: abstract_db.Database):
    client_id = db_test_utils.InitializeClient(db)
    db.WriteClientRRGStartup(client_id, rrg_startup_pb2.Startup())

    class MissingHandlerErrorFlow(flow_base.FlowBase):

      def Start(self) -> None:
        self.CallRRG(
            action=rrg_pb2.Action.GET_SYSTEM_METADATA,
            args=rrg_get_system_metadata_pb2.Args(),
            next_state=self._ProcessSystemMetadata.__name__,
        )

      @flow_base.UseProto2AnyResponses
      def _ProcessSystemMetadata(
          self,
          responses: flow_responses.Responses[any_pb2.Any],
      ) -> None:
        raise NotImplementedError()

    with self.assertRaises(RuntimeError) as context:
      rrg_test_lib.ExecuteFlow(
          client_id=client_id,
          flow_cls=MissingHandlerErrorFlow,
          flow_args=rdf_flows.EmptyFlowArgs(),
          handlers={},
      )

    error = context.exception
    self.assertEqual(str(error), "Missing handler for 'GET_SYSTEM_METADATA'")

  @db_test_lib.WithDatabase
  def testSinks(self, db: abstract_db.Database):
    client_id = db_test_utils.InitializeRRGClient(db)

    def GetFileContentsHandler(
        session: rrg_test_lib.Session,
    ) -> None:
      startup = rrg_startup_pb2.Startup()
      startup.metadata.version.major = 1
      startup.metadata.version.minor = 2
      startup.metadata.version.patch = 3
      session.Send(rrg_pb2.STARTUP, startup)

      blob_1 = rrg_blob_pb2.Blob()
      blob_1.data = b"foo"
      session.Send(rrg_pb2.Sink.BLOB, blob_1)

      result_1 = rrg_get_file_contents_pb2.Result()
      result_1.blob_sha256 = hashlib.sha256(b"foo").digest()
      session.Reply(result_1)

      blob_2 = rrg_blob_pb2.Blob()
      blob_2.data = b"bar"
      session.Send(rrg_pb2.Sink.BLOB, blob_2)

      result_2 = rrg_get_file_contents_pb2.Result()
      result_2.blob_sha256 = hashlib.sha256(b"bar").digest()
      session.Reply(result_2)

    class SinksFlow(flow_base.FlowBase):

      def Start(self):
        self.CallRRG(
            action=rrg_pb2.Action.GET_FILE_CONTENTS,
            args=rrg_get_file_contents_pb2.Args(),
            next_state=self._ProcessGetFileContents.__name__,
        )

      @flow_base.UseProto2AnyResponses
      def _ProcessGetFileContents(
          self,
          responses: flow_responses.Responses[any_pb2.Any],
      ) -> None:
        assert len(responses) == 2

        result = rrg_get_file_contents_pb2.Result()

        assert list(responses)[0].Unpack(result)
        assert result.blob_sha256 == hashlib.sha256(b"foo").digest()

        assert list(responses)[1].Unpack(result)
        assert result.blob_sha256 == hashlib.sha256(b"bar").digest()

    startup_sink = sinks_test_lib.FakeSink()
    blob_sink = sinks_test_lib.FakeSink()

    sink_registry = {
        rrg_pb2.Sink.STARTUP: startup_sink,
        rrg_pb2.Sink.BLOB: blob_sink,
    }
    with mock.patch.object(sinks, "REGISTRY", sink_registry):
      flow_id = rrg_test_lib.ExecuteFlow(
          client_id=client_id,
          flow_cls=SinksFlow,
          flow_args=rdf_flows.EmptyFlowArgs(),
          handlers={
              rrg_pb2.Action.GET_FILE_CONTENTS: GetFileContentsHandler,
          },
      )

    startup_parcels = startup_sink.Parcels(client_id)
    self.assertLen(startup_parcels, 1)

    startup = rrg_startup_pb2.Startup()
    self.assertTrue(startup_parcels[0].payload.Unpack(startup))
    self.assertEqual(startup.metadata.version.major, 1)
    self.assertEqual(startup.metadata.version.minor, 2)
    self.assertEqual(startup.metadata.version.patch, 3)

    blob_parcels = blob_sink.Parcels(client_id)
    self.assertLen(blob_parcels, 2)

    blob = rrg_blob_pb2.Blob()
    blob_parcels[0].payload.Unpack(blob)
    self.assertEqual(blob.data, b"foo")

    blob = rrg_blob_pb2.Blob()
    blob_parcels[1].payload.Unpack(blob)
    self.assertEqual(blob.data, b"bar")

    flow_obj = db.ReadFlowObject(client_id, flow_id)
    self.assertEqual(flow_obj.flow_state, flows_pb2.Flow.FlowState.FINISHED)

  @db_test_lib.WithDatabase
  def testSinksAcceptError(self, db: abstract_db.Database):
    client_id = db_test_utils.InitializeRRGClient(db)

    def GetSystemMetadataHandler(
        session: rrg_test_lib.Session,
    ) -> None:
      session.Send(rrg_pb2.STARTUP, rrg_startup_pb2.Startup())

    class FakeStartupSink(sinks.Sink):

      def Accept(self, client_id: str, parcel: rrg_pb2.Parcel) -> None:
        del client_id, parcel  # Unused.

        raise RuntimeError("Ala ma kota, a kot ma Alę")

    process_get_system_metadata_called = False

    class ParcelsSinkErrorFlow(flow_base.FlowBase):

      def Start(self):
        self.CallRRG(
            action=rrg_pb2.Action.GET_SYSTEM_METADATA,
            args=rrg_get_system_metadata_pb2.Args(),
            next_state=self._ProcessGetSystemMetadata.__name__,
        )

      @flow_base.UseProto2AnyResponses
      def _ProcessGetSystemMetadata(
          self,
          responses: flow_responses.Responses[any_pb2.Any],
      ) -> None:
        assert not responses.success
        assert responses.status is not None
        assert responses.status.error_message == "Ala ma kota, a kot ma Alę"

        nonlocal process_get_system_metadata_called
        process_get_system_metadata_called = True

    sink_registry = {
        rrg_pb2.Sink.STARTUP: FakeStartupSink(),
    }
    with mock.patch.object(sinks, "REGISTRY", sink_registry):
      flow_id = rrg_test_lib.ExecuteFlow(
          client_id=client_id,
          flow_cls=ParcelsSinkErrorFlow,
          flow_args=rdf_flows.EmptyFlowArgs(),
          handlers={
              rrg_pb2.Action.GET_SYSTEM_METADATA: GetSystemMetadataHandler,
          },
      )

    self.assertTrue(process_get_system_metadata_called)

    flow_obj = db.ReadFlowObject(client_id, flow_id)
    self.assertEqual(flow_obj.flow_state, flows_pb2.Flow.FlowState.FINISHED)


class GetFileContentsHandlerTest(absltest.TestCase):

  @classmethod
  def setUpClass(cls):
    super().setUpClass()
    testing_startup.TestInit()

  @db_test_lib.WithDatabase
  def testSingleFile(self, db: abstract_db.Database):
    client_id = db_test_utils.InitializeRRGClient(db)

    class SingleFileFlow(flow_base.FlowBase):

      def Start(self) -> None:
        args = rrg_get_file_contents_pb2.Args()
        args.path.raw_bytes = "/foo/bar".encode("utf-8")
        self.CallRRG(
            action=rrg_pb2.Action.GET_FILE_CONTENTS,
            args=args,
            next_state=self._ProcessGetFileContents.__name__,
        )

      @flow_base.UseProto2AnyResponses
      def _ProcessGetFileContents(
          self,
          responses: flow_responses.Responses[any_pb2.Any],
      ) -> None:
        assert responses.success
        assert len(responses) == 1

        result = rrg_get_file_contents_pb2.Result()
        assert list(responses)[0].Unpack(result)

        self.SendReply(rdfvalue.RDFBytes(result.blob_sha256))

    blob_sink = sinks_test_lib.FakeSink()

    sink_registry = {
        rrg_pb2.Sink.BLOB: blob_sink,
    }
    with mock.patch.object(sinks, "REGISTRY", sink_registry):
      flow_id = rrg_test_lib.ExecuteFlow(
          client_id=client_id,
          flow_cls=SingleFileFlow,
          flow_args=rdf_flows.EmptyFlowArgs(),
          handlers={
              rrg_pb2.Action.GET_FILE_CONTENTS: (
                  rrg_test_lib.GetFileContentsHandler({
                      "/foo/bar": b"foobar",
                  })
              ),
          },
      )

    blob_parcels = blob_sink.Parcels(client_id)
    self.assertLen(blob_parcels, 1)

    blob = rrg_blob_pb2.Blob()
    blob_parcels[0].payload.Unpack(blob)
    self.assertEqual(blob.data, b"foobar")

    results = db.ReadFlowResults(client_id, flow_id, offset=0, count=1024)
    self.assertLen(results, 1)

    result = wrappers_pb2.BytesValue()
    self.assertTrue(results[0].payload.Unpack(result))
    self.assertEqual(result.value, hashlib.sha256(b"foobar").digest())

  @db_test_lib.WithDatabase
  def testMultipleFiles(self, db: abstract_db.Database):
    client_id = db_test_utils.InitializeRRGClient(db)

    class MultipleFilesFlow(flow_base.FlowBase):

      def Start(self) -> None:
        args = rrg_get_file_contents_pb2.Args()

        args.path.raw_bytes = "/foo/bar".encode("utf-8")
        self.CallRRG(
            action=rrg_pb2.Action.GET_FILE_CONTENTS,
            args=args,
            next_state=self._ProcessGetFileContents.__name__,
        )

        args.path.raw_bytes = "/foo/baz".encode("utf-8")
        self.CallRRG(
            action=rrg_pb2.Action.GET_FILE_CONTENTS,
            args=args,
            next_state=self._ProcessGetFileContents.__name__,
        )

        args.path.raw_bytes = "/foo/quux".encode("utf-8")
        self.CallRRG(
            action=rrg_pb2.Action.GET_FILE_CONTENTS,
            args=args,
            next_state=self._ProcessGetFileContents.__name__,
        )

      @flow_base.UseProto2AnyResponses
      def _ProcessGetFileContents(
          self,
          responses: flow_responses.Responses[any_pb2.Any],
      ) -> None:
        assert responses.success
        assert len(responses) == 1

        result = rrg_get_file_contents_pb2.Result()
        assert list(responses)[0].Unpack(result)

        self.SendReply(rdfvalue.RDFBytes(result.blob_sha256))

    blob_sink = sinks_test_lib.FakeSink()

    sink_registry = {
        rrg_pb2.Sink.BLOB: blob_sink,
    }
    with mock.patch.object(sinks, "REGISTRY", sink_registry):
      flow_id = rrg_test_lib.ExecuteFlow(
          client_id=client_id,
          flow_cls=MultipleFilesFlow,
          flow_args=rdf_flows.EmptyFlowArgs(),
          handlers={
              rrg_pb2.Action.GET_FILE_CONTENTS: (
                  rrg_test_lib.GetFileContentsHandler({
                      "/foo/bar": b"foobar",
                      "/foo/baz": b"foobaz",
                      "/foo/quux": b"fooquux",
                  })
              ),
          },
      )

    blob_parcels = blob_sink.Parcels(client_id)
    self.assertLen(blob_parcels, 3)

    blob = rrg_blob_pb2.Blob()

    self.assertTrue(blob_parcels[0].payload.Unpack(blob))
    self.assertEqual(blob.data, b"foobar")

    self.assertTrue(blob_parcels[1].payload.Unpack(blob))
    self.assertEqual(blob.data, b"foobaz")

    self.assertTrue(blob_parcels[2].payload.Unpack(blob))
    self.assertEqual(blob.data, b"fooquux")

    results = db.ReadFlowResults(client_id, flow_id, offset=0, count=1024)
    self.assertLen(results, 3)

    result = wrappers_pb2.BytesValue()

    self.assertTrue(results[0].payload.Unpack(result))
    self.assertEqual(result.value, hashlib.sha256(b"foobar").digest())

    self.assertTrue(results[1].payload.Unpack(result))
    self.assertEqual(result.value, hashlib.sha256(b"foobaz").digest())

    self.assertTrue(results[2].payload.Unpack(result))
    self.assertEqual(result.value, hashlib.sha256(b"fooquux").digest())

  @db_test_lib.WithDatabase
  def testUnknownPath(self, db: abstract_db.Database):
    client_id = db_test_utils.InitializeRRGClient(db)

    process_get_file_contents_called = False

    class UnknownPathFlow(flow_base.FlowBase):

      def Start(self) -> None:
        args = rrg_get_file_contents_pb2.Args()
        args.path.raw_bytes = "/foo/bar".encode("utf-8")
        self.CallRRG(
            action=rrg_pb2.Action.GET_FILE_CONTENTS,
            args=args,
            next_state=self._ProcessGetFileContents.__name__,
        )

      @flow_base.UseProto2AnyResponses
      def _ProcessGetFileContents(
          self,
          responses: flow_responses.Responses[any_pb2.Any],
      ) -> None:
        assert not responses.success
        assert responses.status is not None
        assert responses.status.error_message == "Unknown path: '/foo/bar'"

        nonlocal process_get_file_contents_called
        process_get_file_contents_called = True

    blob_sink = sinks_test_lib.FakeSink()

    sink_registry = {
        rrg_pb2.Sink.BLOB: blob_sink,
    }
    with mock.patch.object(sinks, "REGISTRY", sink_registry):
      rrg_test_lib.ExecuteFlow(
          client_id=client_id,
          flow_cls=UnknownPathFlow,
          flow_args=rdf_flows.EmptyFlowArgs(),
          handlers={
              rrg_pb2.Action.GET_FILE_CONTENTS: (
                  rrg_test_lib.GetFileContentsHandler({})
              ),
          },
      )

    self.assertTrue(process_get_file_contents_called)


if __name__ == "__main__":
  absltest.main()
