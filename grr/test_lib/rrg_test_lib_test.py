#!/usr/bin/env python
import hashlib
import itertools
import stat
from unittest import mock

from absl.testing import absltest

from google.protobuf import any_pb2
from google.protobuf import timestamp_pb2
from google.protobuf import wrappers_pb2
from grr_response_core.lib import rdfvalue
from grr_response_core.lib.rdfvalues import flows as rdf_flows
from grr_response_proto import flows_pb2
from grr_response_server import flow_base
from grr_response_server import flow_responses
from grr_response_server import rrg_stubs
from grr_response_server import sinks
from grr_response_server.databases import db as abstract_db
from grr_response_server.databases import db_test_utils
from grr_response_server.sinks import test_lib as sinks_test_lib
from grr.test_lib import db_test_lib
from grr.test_lib import rrg_test_lib
from grr.test_lib import testing_startup
from grr_response_proto import rrg_pb2
from grr_response_proto.rrg import blob_pb2 as rrg_blob_pb2
from grr_response_proto.rrg import fs_pb2 as rrg_fs_pb2
from grr_response_proto.rrg import startup_pb2 as rrg_startup_pb2
from grr_response_proto.rrg import winreg_pb2 as rrg_winreg_pb2
from grr_response_proto.rrg.action import get_file_contents_pb2 as rrg_get_file_contents_pb2
from grr_response_proto.rrg.action import get_file_metadata_pb2 as rrg_get_file_metadata_pb2
from grr_response_proto.rrg.action import get_file_sha256_pb2 as rrg_get_file_sha256_pb2
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
    client_id = db_test_utils.InitializeRRGClient(db)

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
    client_id = db_test_utils.InitializeRRGClient(db)

    def GetSystemMetadataHandler(
        session: rrg_test_lib.Session,
    ) -> None:
      session.Reply(rrg_get_system_metadata_pb2.Result(version="1.3.3.7"))

    class SingleRRGCallFlow(flow_base.FlowBase):

      def Start(self) -> None:
        rrg_stubs.GetSystemMetadata().Call(self._ProcessSystemMetadata)

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
    client_id = db_test_utils.InitializeRRGClient(db)

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
        action = rrg_stubs.GetWinregValue()

        action.args.key = "Foo\\Bar"
        action.Call(self._ProcessGetWinregValueFoo)

        action.args.key = "Foo\\Baz"
        action.Call(self._ProcessGetWinregValueFoo)

        action.args.key = "Quux"
        action.Call(self._ProcessGetWinregValueQuux)

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
    client_id = db_test_utils.InitializeRRGClient(db)

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
        action = rrg_stubs.ListWinregKeys()
        action.args.key = "Foo"
        action.Call(self._ProcessListWinregKeysFoo)

      @flow_base.UseProto2AnyResponses
      def _ProcessListWinregKeysFoo(
          self,
          responses: flow_responses.Responses[any_pb2.Any],
      ) -> None:
        for response in responses:
          result = rrg_list_winreg_keys_pb2.Result()
          assert response.Unpack(result)

          action = rrg_stubs.GetWinregValue()
          action.args.key = f"{result.key}\\{result.subkey}"
          action.Call(self._ProcessGetWinregValue)

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
    client_id = db_test_utils.InitializeRRGClient(db)

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
        action = rrg_stubs.ListWinregValues()
        action.args.key = "Foo"
        action.Call(self._ProcessListWinregValuesFoo)

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
    client_id = db_test_utils.InitializeRRGClient(db)

    def GetSystemMetadataHandler(
        session: rrg_test_lib.Session,
    ) -> None:
      del session  # Unused.

      raise RuntimeError("Ala ma kota, a kot ma Alę")

    process_system_metadata_called = False

    class ActionErrorFlow(flow_base.FlowBase):

      def Start(self) -> None:
        rrg_stubs.GetSystemMetadata().Call(self._ProcessSystemMetadata)

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
  def testAssertionError(self, db: abstract_db.Database):
    client_id = db_test_utils.InitializeRRGClient(db)

    def GetSystemMetadataHandler(
        session: rrg_test_lib.Session,
    ) -> None:
      del session  # Unused.

      assert False

    process_system_metadata_called = False

    class AssertionErrorFlow(flow_base.FlowBase):

      def Start(self) -> None:
        rrg_stubs.GetSystemMetadata().Call(self._ProcessSystemMetadata)

      @flow_base.UseProto2AnyResponses
      def _ProcessSystemMetadata(
          self,
          responses: flow_responses.Responses[any_pb2.Any],
      ) -> None:
        assert not responses.success
        assert responses.status is not None
        assert "assert False" in responses.status.error_message

        nonlocal process_system_metadata_called
        process_system_metadata_called = True

    flow_id = rrg_test_lib.ExecuteFlow(
        client_id=client_id,
        flow_cls=AssertionErrorFlow,
        flow_args=rdf_flows.EmptyFlowArgs(),
        handlers={
            rrg_pb2.Action.GET_SYSTEM_METADATA: GetSystemMetadataHandler,
        },
    )

    self.assertTrue(process_system_metadata_called)

    flow_obj = db.ReadFlowObject(client_id, flow_id)
    self.assertEqual(flow_obj.flow_state, flows_pb2.Flow.FlowState.FINISHED)

  @db_test_lib.WithDatabase
  def testAssertionErrorWithMessage(self, db: abstract_db.Database):
    client_id = db_test_utils.InitializeRRGClient(db)

    def GetSystemMetadataHandler(
        session: rrg_test_lib.Session,
    ) -> None:
      del session  # Unused.

      raise AssertionError("Ala ma kota, a kot ma Alę")

    process_system_metadata_called = False

    class AssertionErrorWithMessageFlow(flow_base.FlowBase):

      def Start(self) -> None:
        rrg_stubs.GetSystemMetadata().Call(self._ProcessSystemMetadata)

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
        flow_cls=AssertionErrorWithMessageFlow,
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
    client_id = db_test_utils.InitializeRRGClient(db)

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
    client_id = db_test_utils.InitializeRRGClient(db)

    def GetSystemMetadataHandler(
        session: rrg_test_lib.Session,
    ) -> None:
      del session  # Unused.

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
        rrg_stubs.GetSystemMetadata().Call(self._ProcessSystemMetadata)

      @flow_base.UseProto2AnyResponses
      def _ProcessSystemMetadata(
          self,
          responses: flow_responses.Responses[any_pb2.Any],
      ) -> None:
        assert responses.success

        raise flow_base.FlowError("Ala ma kota, a kot ma Alę")

    flow_id = rrg_test_lib.ExecuteFlow(
        client_id=client_id,
        flow_cls=NestedFlowErrorParentFlow,
        flow_args=rdf_flows.EmptyFlowArgs(),
        handlers={
            rrg_pb2.Action.GET_SYSTEM_METADATA: GetSystemMetadataHandler,
        },
    )

    self.assertTrue(process_child_flow_called)

    # Only the child should have failed, parent flow should finish fine.
    flow_obj = db.ReadFlowObject(client_id, flow_id)
    self.assertEqual(flow_obj.flow_state, flows_pb2.Flow.FlowState.FINISHED)

  @db_test_lib.WithDatabase
  def testMissingHandlerError(self, db: abstract_db.Database):
    client_id = db_test_utils.InitializeRRGClient(db)

    class MissingHandlerErrorFlow(flow_base.FlowBase):

      def Start(self) -> None:
        rrg_stubs.GetSystemMetadata().Call(self._ProcessSystemMetadata)

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
        action = rrg_stubs.GetFileContents()
        action.Call(self._ProcessGetFileContents)

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
        rrg_stubs.GetSystemMetadata().Call(self._ProcessGetSystemMetadata)

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

  @db_test_lib.WithDatabase
  def testSessionReplyCopy(self, db: abstract_db.Database):
    client_id = db_test_utils.InitializeRRGClient(db)

    def ListWinregValuesHandler(session: rrg_test_lib.Session) -> None:
      result = rrg_list_winreg_values_pb2.Result()
      result.key = r"SOFTWARE\Foo\Bar"

      result.value.name = "Quux"
      result.value.string = "Lorem ipsum."
      session.Reply(result)

      result.value.name = "Norf"
      result.value.string = "Dolor sit amet."
      session.Reply(result)

    flow_process_done = False

    class SessionReplyCopyFlow(flow_base.FlowBase):

      def Start(self) -> None:
        list_winreg_values = rrg_stubs.ListWinregValues()
        list_winreg_values.Call(self._ProcessListWinregValues)

      @flow_base.UseProto2AnyResponses
      def _ProcessListWinregValues(
          self,
          responses: flow_responses.Responses[any_pb2.Any],
      ) -> None:
        assert len(responses) == 2
        responses = list(responses)

        response_quux = rrg_list_winreg_values_pb2.Result()
        assert responses[0].Unpack(response_quux)
        assert response_quux.key == r"SOFTWARE\Foo\Bar"
        assert response_quux.value.name == "Quux"
        assert response_quux.value.string == "Lorem ipsum."

        response_norf = rrg_list_winreg_values_pb2.Result()
        assert list(responses)[1].Unpack(response_norf)
        assert response_norf.key == r"SOFTWARE\Foo\Bar"
        assert response_norf.value.name == "Norf"
        assert response_norf.value.string == "Dolor sit amet."

        nonlocal flow_process_done
        flow_process_done = True

    flow_id = rrg_test_lib.ExecuteFlow(
        client_id=client_id,
        flow_cls=SessionReplyCopyFlow,
        flow_args=rdf_flows.EmptyFlowArgs(),
        handlers={
            rrg_pb2.Action.LIST_WINREG_VALUES: ListWinregValuesHandler,
        },
    )

    self.assertTrue(flow_process_done)

    flow_obj = db.ReadFlowObject(client_id, flow_id)
    self.assertEqual(flow_obj.error_message, "")
    self.assertEqual(flow_obj.flow_state, flows_pb2.Flow.FINISHED)

  @db_test_lib.WithDatabase
  def testSessionSendCopy(self, db: abstract_db.Database):
    client_id = db_test_utils.InitializeRRGClient(db)

    def GetFileContentsHandler(session: rrg_test_lib.Session) -> None:
      blob = rrg_blob_pb2.Blob()

      blob.data = b"foo"
      session.Send(rrg_pb2.Sink.BLOB, blob)

      blob.data = b"bar"
      session.Send(rrg_pb2.Sink.BLOB, blob)

    class SessionSendCopyFlow(flow_base.FlowBase):

      def Start(self):
        get_file_contents = rrg_stubs.GetFileContents()
        get_file_contents.Call(self._ProcessGetFileContents)

      @flow_base.UseProto2AnyResponses
      def _ProcessGetFileContents(
          self,
          responses: flow_responses.Responses[any_pb2.Any],
      ) -> None:
        assert responses.success

    blob_sink = sinks_test_lib.FakeSink()

    sink_registry = {
        rrg_pb2.Sink.BLOB: blob_sink,
    }
    with mock.patch.object(sinks, "REGISTRY", sink_registry):
      flow_id = rrg_test_lib.ExecuteFlow(
          client_id=client_id,
          flow_cls=SessionSendCopyFlow,
          flow_args=rdf_flows.EmptyFlowArgs(),
          handlers={
              rrg_pb2.Action.GET_FILE_CONTENTS: GetFileContentsHandler,
          },
      )

    blob_parcels = blob_sink.Parcels(client_id)
    self.assertLen(blob_parcels, 2)

    blob = rrg_blob_pb2.Blob()
    blob_parcels[0].payload.Unpack(blob)
    self.assertEqual(blob.data, b"foo")

    blob = rrg_blob_pb2.Blob()
    blob_parcels[1].payload.Unpack(blob)
    self.assertEqual(blob.data, b"bar")

    flow_obj = db.ReadFlowObject(client_id, flow_id)
    self.assertEqual(flow_obj.error_message, "")
    self.assertEqual(flow_obj.flow_state, flows_pb2.Flow.FlowState.FINISHED)

  @db_test_lib.WithDatabase
  def testFilterSimple(self, db: abstract_db.Database):
    client_id = db_test_utils.InitializeRRGClient(db)

    def ListWinregKeysHandler(
        session: rrg_test_lib.Session,
    ) -> None:
      session.Reply(rrg_list_winreg_keys_pb2.Result(key="Bar"))
      session.Reply(rrg_list_winreg_keys_pb2.Result(key="Foo"))
      session.Reply(rrg_list_winreg_keys_pb2.Result(key="Baz"))

    flow_process_done = False

    class FilterSingleFlow(flow_base.FlowBase):

      def Start(self) -> None:
        list_winreg_keys = rrg_stubs.ListWinregKeys()

        key_cond = list_winreg_keys.AddFilter().conditions.add()
        key_cond.string_equal = "Foo"
        key_cond.field.append(
            rrg_list_winreg_keys_pb2.Result.KEY_FIELD_NUMBER,
        )

        list_winreg_keys.Call(self._ProcessListWinregKeys)

      @flow_base.UseProto2AnyResponses
      def _ProcessListWinregKeys(
          self,
          responses: flow_responses.Responses[any_pb2.Any],
      ) -> None:
        assert len(responses) == 1

        response = rrg_list_winreg_keys_pb2.Result()
        assert list(responses)[0].Unpack(response)
        assert response.key == "Foo"

        nonlocal flow_process_done
        flow_process_done = True

    flow_id = rrg_test_lib.ExecuteFlow(
        client_id=client_id,
        flow_cls=FilterSingleFlow,
        flow_args=rdf_flows.EmptyFlowArgs(),
        handlers={
            rrg_pb2.Action.LIST_WINREG_KEYS: ListWinregKeysHandler,
        },
    )

    self.assertTrue(flow_process_done)

    flow_obj = db.ReadFlowObject(client_id, flow_id)
    self.assertEqual(flow_obj.flow_state, flows_pb2.Flow.FINISHED)

  @db_test_lib.WithDatabase
  def testFilterConjunction(self, db: abstract_db.Database):
    client_id = db_test_utils.InitializeRRGClient(db)

    def ListWinregKeysHandler(
        session: rrg_test_lib.Session,
    ) -> None:
      session.Reply(rrg_list_winreg_keys_pb2.Result(key="Foo"))
      session.Reply(rrg_list_winreg_keys_pb2.Result(key="Bar"))
      session.Reply(rrg_list_winreg_keys_pb2.Result(key="Baz"))
      session.Reply(rrg_list_winreg_keys_pb2.Result(key="Norf"))

    flow_process_done = False

    class FilterConjunctionFlow(flow_base.FlowBase):

      def Start(self) -> None:
        list_winreg_keys = rrg_stubs.ListWinregKeys()

        # This condition should match `Foo`, `Bar`, `Baz`.
        key_cond_len3 = list_winreg_keys.AddFilter().conditions.add()
        key_cond_len3.string_match = r"^\w{3}$"
        key_cond_len3.field.append(
            rrg_list_winreg_keys_pb2.Result.KEY_FIELD_NUMBER,
        )

        # This condition should match `Bar`, `Norf`.
        key_cond_r = list_winreg_keys.AddFilter().conditions.add()
        key_cond_r.string_match = ".*r.*"
        key_cond_r.field.append(
            rrg_list_winreg_keys_pb2.Result.KEY_FIELD_NUMBER,
        )

        list_winreg_keys.Call(self._ProcessListWinregKeys)

      @flow_base.UseProto2AnyResponses
      def _ProcessListWinregKeys(
          self,
          responses: flow_responses.Responses[any_pb2.Any],
      ) -> None:
        assert len(responses) == 1

        response = rrg_list_winreg_keys_pb2.Result()
        assert list(responses)[0].Unpack(response)
        assert response.key == "Bar"

        nonlocal flow_process_done
        flow_process_done = True

    flow_id = rrg_test_lib.ExecuteFlow(
        client_id=client_id,
        flow_cls=FilterConjunctionFlow,
        flow_args=rdf_flows.EmptyFlowArgs(),
        handlers={
            rrg_pb2.Action.LIST_WINREG_KEYS: ListWinregKeysHandler,
        },
    )

    self.assertTrue(flow_process_done)

    flow_obj = db.ReadFlowObject(client_id, flow_id)
    self.assertEqual(flow_obj.flow_state, flows_pb2.Flow.FINISHED)

  @db_test_lib.WithDatabase
  def testFilterDisjunction(self, db: abstract_db.Database):
    client_id = db_test_utils.InitializeRRGClient(db)

    def ListWinregKeysHandler(
        session: rrg_test_lib.Session,
    ) -> None:
      session.Reply(rrg_list_winreg_keys_pb2.Result(key="Bar"))
      session.Reply(rrg_list_winreg_keys_pb2.Result(key="Foo"))
      session.Reply(rrg_list_winreg_keys_pb2.Result(key="Baz"))

    flow_process_done = False

    class FilterDisjunctionFlow(flow_base.FlowBase):

      def Start(self) -> None:
        list_winreg_keys = rrg_stubs.ListWinregKeys()

        key_filter = list_winreg_keys.AddFilter()

        key_cond_bar = key_filter.conditions.add()
        key_cond_bar.string_equal = "Bar"
        key_cond_bar.field.append(
            rrg_list_winreg_keys_pb2.Result.KEY_FIELD_NUMBER,
        )

        key_cond_baz = key_filter.conditions.add()
        key_cond_baz.string_equal = "Baz"
        key_cond_baz.field.append(
            rrg_list_winreg_keys_pb2.Result.KEY_FIELD_NUMBER,
        )

        list_winreg_keys.Call(self._ProcessListWinregKeys)

      @flow_base.UseProto2AnyResponses
      def _ProcessListWinregKeys(
          self,
          responses: flow_responses.Responses[any_pb2.Any],
      ) -> None:
        assert len(responses) == 2

        response = rrg_list_winreg_keys_pb2.Result()
        assert list(responses)[0].Unpack(response)
        assert response.key == "Bar"

        response = rrg_list_winreg_keys_pb2.Result()
        assert list(responses)[1].Unpack(response)
        assert response.key == "Baz"

        nonlocal flow_process_done
        flow_process_done = True

    flow_id = rrg_test_lib.ExecuteFlow(
        client_id=client_id,
        flow_cls=FilterDisjunctionFlow,
        flow_args=rdf_flows.EmptyFlowArgs(),
        handlers={
            rrg_pb2.Action.LIST_WINREG_KEYS: ListWinregKeysHandler,
        },
    )

    self.assertTrue(flow_process_done)

    flow_obj = db.ReadFlowObject(client_id, flow_id)
    self.assertEqual(flow_obj.flow_state, flows_pb2.Flow.FINISHED)

  @db_test_lib.WithDatabase
  def testFilterNegation(self, db: abstract_db.Database):
    client_id = db_test_utils.InitializeRRGClient(db)

    def ListWinregKeysHandler(
        session: rrg_test_lib.Session,
    ) -> None:
      session.Reply(rrg_list_winreg_keys_pb2.Result(key="Bar"))
      session.Reply(rrg_list_winreg_keys_pb2.Result(key="Foo"))
      session.Reply(rrg_list_winreg_keys_pb2.Result(key="Baz"))

    flow_process_done = False

    class FilterNegationFlow(flow_base.FlowBase):

      def Start(self) -> None:
        list_winreg_keys = rrg_stubs.ListWinregKeys()

        key_cond = list_winreg_keys.AddFilter().conditions.add()
        key_cond.negated = True
        key_cond.string_equal = "Foo"
        key_cond.field.append(
            rrg_list_winreg_keys_pb2.Result.KEY_FIELD_NUMBER,
        )

        list_winreg_keys.Call(self._ProcessListWinregKeys)

      @flow_base.UseProto2AnyResponses
      def _ProcessListWinregKeys(
          self,
          responses: flow_responses.Responses[any_pb2.Any],
      ) -> None:
        assert len(responses) == 2

        response = rrg_list_winreg_keys_pb2.Result()
        assert list(responses)[0].Unpack(response)
        assert response.key == "Bar"

        response = rrg_list_winreg_keys_pb2.Result()
        assert list(responses)[1].Unpack(response)
        assert response.key == "Baz"

        nonlocal flow_process_done
        flow_process_done = True

    flow_id = rrg_test_lib.ExecuteFlow(
        client_id=client_id,
        flow_cls=FilterNegationFlow,
        flow_args=rdf_flows.EmptyFlowArgs(),
        handlers={
            rrg_pb2.Action.LIST_WINREG_KEYS: ListWinregKeysHandler,
        },
    )

    self.assertTrue(flow_process_done)

    flow_obj = db.ReadFlowObject(client_id, flow_id)
    self.assertEqual(flow_obj.flow_state, flows_pb2.Flow.FINISHED)

  @db_test_lib.WithDatabase
  def testFilterNestedField(self, db: abstract_db.Database):
    client_id = db_test_utils.InitializeRRGClient(db)

    def GetSystemMetadataHandler(
        session: rrg_test_lib.Session,
    ) -> None:
      result = rrg_get_system_metadata_pb2.Result()
      result.install_time.seconds = 1234567890

      session.Reply(result)

    flow_process_done = False

    class FilterNestedFieldFlow(flow_base.FlowBase):

      def Start(self) -> None:
        get_system_metadata = rrg_stubs.GetSystemMetadata()

        install_time_cond = get_system_metadata.AddFilter().conditions.add()
        install_time_cond.int64_equal = 1234567890
        install_time_cond.field.append(
            rrg_get_system_metadata_pb2.Result.INSTALL_TIME_FIELD_NUMBER,
        )
        install_time_cond.field.append(
            timestamp_pb2.Timestamp.SECONDS_FIELD_NUMBER,
        )

        get_system_metadata.Call(self._ProcessGetSystemMetadata)

      @flow_base.UseProto2AnyResponses
      def _ProcessGetSystemMetadata(
          self,
          responses: flow_responses.Responses[any_pb2.Any],
      ) -> None:
        assert len(responses) == 1

        response = rrg_get_system_metadata_pb2.Result()
        assert list(responses)[0].Unpack(response)
        assert response.install_time.seconds == 1234567890

        nonlocal flow_process_done
        flow_process_done = True

    flow_id = rrg_test_lib.ExecuteFlow(
        client_id=client_id,
        flow_cls=FilterNestedFieldFlow,
        flow_args=rdf_flows.EmptyFlowArgs(),
        handlers={
            rrg_pb2.Action.GET_SYSTEM_METADATA: GetSystemMetadataHandler,
        },
    )

    self.assertTrue(flow_process_done)

    flow_obj = db.ReadFlowObject(client_id, flow_id)
    self.assertEqual(flow_obj.flow_state, flows_pb2.Flow.FINISHED)

  @db_test_lib.WithDatabase
  def testFilterStrictTypeCheck(self, db: abstract_db.Database):
    client_id = db_test_utils.InitializeRRGClient(db)

    def ListWinregKeysHandler(
        session: rrg_test_lib.Session,
    ) -> None:
      result = rrg_list_winreg_keys_pb2.Result()
      result.key = "Bar"
      result.modification_time.GetCurrentTime()
      session.Reply(result)

    flow_process_done = False

    class FilterStrictTypeCheckFlow(flow_base.FlowBase):

      def Start(self) -> None:
        list_winreg_keys = rrg_stubs.ListWinregKeys()

        key_cond = list_winreg_keys.AddFilter().conditions.add()
        # `modification_time.seconds` is of type `int64` whereas we use `uint64`
        # operator, so this should fail.
        key_cond.uint64_equal = 1337
        key_cond.field.extend([
            rrg_list_winreg_keys_pb2.Result.MODIFICATION_TIME_FIELD_NUMBER,
            timestamp_pb2.Timestamp.SECONDS_FIELD_NUMBER,
        ])

        list_winreg_keys.Call(self._ProcessListWinregKeys)

      @flow_base.UseProto2AnyResponses
      def _ProcessListWinregKeys(
          self,
          responses: flow_responses.Responses[any_pb2.Any],
      ) -> None:
        assert not responses.success

        nonlocal flow_process_done
        flow_process_done = True

    flow_id = rrg_test_lib.ExecuteFlow(
        client_id=client_id,
        flow_cls=FilterStrictTypeCheckFlow,
        flow_args=rdf_flows.EmptyFlowArgs(),
        handlers={
            rrg_pb2.Action.LIST_WINREG_KEYS: ListWinregKeysHandler,
        },
    )

    self.assertTrue(flow_process_done)

    flow_obj = db.ReadFlowObject(client_id, flow_id)
    self.assertEqual(flow_obj.flow_state, flows_pb2.Flow.FINISHED)


class FakeFileHandlersTest(absltest.TestCase):

  @classmethod
  def setUpClass(cls):
    super().setUpClass()
    testing_startup.TestInit()

  @db_test_lib.WithDatabase
  def testRelativePath(self, db: abstract_db.Database):
    client_id = db_test_utils.InitializeRRGClient(db)

    with self.assertRaises(ValueError) as context:
      rrg_test_lib.ExecuteFlow(
          client_id=client_id,
          flow_cls=flow_base.FlowBase,
          flow_args=rdf_flows.EmptyFlowArgs(),
          handlers=rrg_test_lib.FakePosixFileHandlers({
              "foo/bar": b"",
          }),
      )

    error = context.exception
    self.assertEqual(str(error), "Relative path: 'foo/bar'")

  @db_test_lib.WithDatabase
  def testNotDirectory(self, db: abstract_db.Database):
    client_id = db_test_utils.InitializeRRGClient(db)

    with self.assertRaises(ValueError) as context:
      rrg_test_lib.ExecuteFlow(
          client_id=client_id,
          flow_cls=flow_base.FlowBase,
          flow_args=rdf_flows.EmptyFlowArgs(),
          handlers=rrg_test_lib.FakePosixFileHandlers({
              "/foo": b"",
              "/foo/bar": b"",
          }),
      )

    error = context.exception
    self.assertEqual(str(error), "'foo' of '/foo/bar' not a directory")

  @db_test_lib.WithDatabase
  def testGetFileMetadata_SingleFile(self, db: abstract_db.Database):
    client_id = db_test_utils.InitializeRRGClient(db)

    class GetFileMetadataSingleFileFlow(flow_base.FlowBase):

      def Start(self) -> None:
        get_file_metadata = rrg_stubs.GetFileMetadata()
        get_file_metadata.args.paths.add().raw_bytes = "/foo/bar".encode()
        get_file_metadata.Call(self._ProcessGetFileMetadata)

      @flow_base.UseProto2AnyResponses
      def _ProcessGetFileMetadata(
          self,
          responses: flow_responses.Responses[any_pb2.Any],
      ) -> None:
        assert responses.success
        assert len(responses) == 1

        result = rrg_get_file_metadata_pb2.Result()
        assert list(responses)[0].Unpack(result)

        assert result.path.raw_bytes == "/foo/bar".encode()
        assert result.metadata.type == rrg_fs_pb2.FileMetadata.FILE
        assert result.metadata.size == len("Lorem ipsum.")
        assert stat.S_ISREG(result.metadata.unix_mode)
        assert result.metadata.unix_ino
        assert result.metadata.access_time.seconds > 0
        assert result.metadata.modification_time.seconds > 0
        assert result.metadata.creation_time.seconds > 0

    flow_id = rrg_test_lib.ExecuteFlow(
        client_id=client_id,
        flow_cls=GetFileMetadataSingleFileFlow,
        flow_args=rdf_flows.EmptyFlowArgs(),
        handlers=rrg_test_lib.FakePosixFileHandlers({
            "/foo/bar": b"Lorem ipsum.",
        }),
    )

    flow_obj = db.ReadFlowObject(client_id, flow_id)
    self.assertEqual(flow_obj.error_message, "")
    self.assertEqual(flow_obj.flow_state, flows_pb2.Flow.FlowState.FINISHED)

  @db_test_lib.WithDatabase
  def testGetFileMetadata_MultipleFiles(self, db: abstract_db.Database):
    client_id = db_test_utils.InitializeRRGClient(db)

    class GetFileMetadataMultipleFilesFlow(flow_base.FlowBase):

      def Start(self) -> None:
        get_file_metadata = rrg_stubs.GetFileMetadata()
        get_file_metadata.args.paths.add().raw_bytes = "/foo".encode()
        get_file_metadata.args.paths.add().raw_bytes = "/foo/bar".encode()
        get_file_metadata.args.paths.add().raw_bytes = "/foo/baz".encode()
        get_file_metadata.args.paths.add().raw_bytes = "/foo/quux".encode()
        get_file_metadata.Call(self._ProcessGetFileMetadata)

      @flow_base.UseProto2AnyResponses
      def _ProcessGetFileMetadata(
          self,
          responses: flow_responses.Responses[any_pb2.Any],
      ) -> None:
        assert responses.success
        assert len(responses) == 4

        results_by_path = {}
        for response in responses:
          result = rrg_get_file_metadata_pb2.Result()
          assert response.Unpack(result)

          results_by_path[result.path.raw_bytes.decode()] = result

        result_foo = results_by_path["/foo"]
        assert result_foo.metadata.type == rrg_fs_pb2.FileMetadata.DIR
        assert stat.S_ISDIR(result_foo.metadata.unix_mode)
        assert result_foo.metadata.access_time.seconds > 0
        assert result_foo.metadata.modification_time.seconds > 0
        assert result_foo.metadata.creation_time.seconds > 0
        assert result_foo.metadata.unix_ino != 0

        result_bar = results_by_path["/foo/bar"]
        assert result_bar.metadata.type == rrg_fs_pb2.FileMetadata.FILE
        assert stat.S_ISREG(result_bar.metadata.unix_mode)
        assert result_bar.metadata.size == len("Lorem ipsum.")
        assert result_bar.metadata.access_time.seconds > 0
        assert result_bar.metadata.modification_time.seconds > 0
        assert result_bar.metadata.creation_time.seconds > 0
        assert result_bar.metadata.unix_ino != 0

        result_baz = results_by_path["/foo/baz"]
        assert result_baz.metadata.type == rrg_fs_pb2.FileMetadata.FILE
        assert stat.S_ISREG(result_baz.metadata.unix_mode)
        assert result_baz.metadata.size == len("Dolor sit amet.")
        assert result_baz.metadata.access_time.seconds > 0
        assert result_baz.metadata.modification_time.seconds > 0
        assert result_baz.metadata.creation_time.seconds > 0
        assert result_baz.metadata.unix_ino != 0

        result_quux = results_by_path["/foo/quux"]
        assert result_quux.metadata.type == rrg_fs_pb2.FileMetadata.FILE
        assert stat.S_ISREG(result_quux.metadata.unix_mode)
        assert result_quux.metadata.size == 0
        assert result_quux.metadata.access_time.seconds > 0
        assert result_quux.metadata.modification_time.seconds > 0
        assert result_quux.metadata.creation_time.seconds > 0
        assert result_quux.metadata.unix_ino != 0

    flow_id = rrg_test_lib.ExecuteFlow(
        client_id=client_id,
        flow_cls=GetFileMetadataMultipleFilesFlow,
        flow_args=rdf_flows.EmptyFlowArgs(),
        handlers=rrg_test_lib.FakePosixFileHandlers({
            "/foo/bar": b"Lorem ipsum.",
            "/foo/baz": b"Dolor sit amet.",
            "/foo/quux": b"",
        }),
    )

    flow_obj = db.ReadFlowObject(client_id, flow_id)
    self.assertEqual(flow_obj.error_message, "")
    self.assertEqual(flow_obj.flow_state, flows_pb2.Flow.FlowState.FINISHED)

  @db_test_lib.WithDatabase
  def testGetFileMetadata_NotExistingFile(self, db: abstract_db.Database):
    client_id = db_test_utils.InitializeRRGClient(db)

    class GetFileMetadataNotExistingFileFlow(flow_base.FlowBase):

      def Start(self) -> None:
        get_file_metadata = rrg_stubs.GetFileMetadata()
        get_file_metadata.args.paths.add().raw_bytes = "/foo/bar".encode()
        get_file_metadata.args.paths.add().raw_bytes = "/foo/baz".encode()
        get_file_metadata.Call(self._ProcessGetFileMetadata)

      @flow_base.UseProto2AnyResponses
      def _ProcessGetFileMetadata(
          self,
          responses: flow_responses.Responses[any_pb2.Any],
      ) -> None:
        assert responses.success
        assert len(responses) == 1

        result = rrg_get_file_metadata_pb2.Result()
        assert list(responses)[0].Unpack(result)

        assert result.path.raw_bytes == "/foo/baz".encode()

    flow_id = rrg_test_lib.ExecuteFlow(
        client_id=client_id,
        flow_cls=GetFileMetadataNotExistingFileFlow,
        flow_args=rdf_flows.EmptyFlowArgs(),
        handlers=rrg_test_lib.FakePosixFileHandlers({
            "/foo/baz": b"Dolor sit amet.",
        }),
    )

    flow_obj = db.ReadFlowObject(client_id, flow_id)
    self.assertEqual(flow_obj.error_message, "")
    self.assertEqual(flow_obj.flow_state, flows_pb2.Flow.FlowState.FINISHED)

  @db_test_lib.WithDatabase
  def testGetFileMetadata_EmptyDir(self, db: abstract_db.Database):
    client_id = db_test_utils.InitializeRRGClient(db)

    class GetFileMetadataEmptyDirFlow(flow_base.FlowBase):

      def Start(self) -> None:
        get_file_metadata = rrg_stubs.GetFileMetadata()
        get_file_metadata.args.paths.add().raw_bytes = "/foo/bar".encode()
        get_file_metadata.Call(self._ProcessGetFileMetadata)

      @flow_base.UseProto2AnyResponses
      def _ProcessGetFileMetadata(
          self,
          responses: flow_responses.Responses[any_pb2.Any],
      ) -> None:
        assert responses.success
        assert len(responses) == 1

        result = rrg_get_file_metadata_pb2.Result()
        assert list(responses)[0].Unpack(result)

        assert result.path.raw_bytes == "/foo/bar".encode()
        assert result.metadata.type == rrg_fs_pb2.FileMetadata.DIR
        assert stat.S_ISDIR(result.metadata.unix_mode)

    flow_id = rrg_test_lib.ExecuteFlow(
        client_id=client_id,
        flow_cls=GetFileMetadataEmptyDirFlow,
        flow_args=rdf_flows.EmptyFlowArgs(),
        handlers=rrg_test_lib.FakePosixFileHandlers({
            "/foo/bar": {},
        }),
    )

    flow_obj = db.ReadFlowObject(client_id, flow_id)
    self.assertEqual(flow_obj.error_message, "")
    self.assertEqual(flow_obj.flow_state, flows_pb2.Flow.FlowState.FINISHED)

  @db_test_lib.WithDatabase
  def testGetFileMetadata_Symlink(self, db: abstract_db.Database):
    client_id = db_test_utils.InitializeRRGClient(db)

    class GetFileMetadataSymlinkFlow(flow_base.FlowBase):

      def Start(self) -> None:
        get_file_metadata = rrg_stubs.GetFileMetadata()
        get_file_metadata.args.paths.add().raw_bytes = "/foo/symlink".encode()
        get_file_metadata.Call(self._ProcessGetFileMetadata)

      @flow_base.UseProto2AnyResponses
      def _ProcessGetFileMetadata(
          self,
          responses: flow_responses.Responses[any_pb2.Any],
      ) -> None:
        assert responses.success
        assert len(responses) == 1

        result = rrg_get_file_metadata_pb2.Result()
        assert list(responses)[0].Unpack(result)

        assert result.path.raw_bytes == "/foo/symlink".encode()
        assert result.metadata.type == rrg_fs_pb2.FileMetadata.SYMLINK
        assert stat.S_ISLNK(result.metadata.unix_mode)
        assert result.metadata.size == len("/foo/target")
        assert result.symlink.raw_bytes == "/foo/target".encode()

    flow_id = rrg_test_lib.ExecuteFlow(
        client_id=client_id,
        flow_cls=GetFileMetadataSymlinkFlow,
        flow_args=rdf_flows.EmptyFlowArgs(),
        handlers=rrg_test_lib.FakePosixFileHandlers({
            "/foo/symlink": "/foo/target",
            "/foo/target": b"",
        }),
    )

    flow_obj = db.ReadFlowObject(client_id, flow_id)
    self.assertEqual(flow_obj.error_message, "")
    self.assertEqual(flow_obj.flow_state, flows_pb2.Flow.FlowState.FINISHED)

  @db_test_lib.WithDatabase
  def testGetFileMetadata_MaxDepth(self, db: abstract_db.Database):
    client_id = db_test_utils.InitializeRRGClient(db)

    class GetFileMetadataMaxDepthFlow(flow_base.FlowBase):

      def Start(self) -> None:
        get_file_metadata = rrg_stubs.GetFileMetadata()
        get_file_metadata.args.paths.add().raw_bytes = "/".encode()
        get_file_metadata.args.max_depth = 2
        get_file_metadata.Call(self._ProcessGetFileMetadata)

      @flow_base.UseProto2AnyResponses
      def _ProcessGetFileMetadata(
          self,
          responses: flow_responses.Responses[any_pb2.Any],
      ) -> None:
        assert responses.success

        results_by_path = {}
        for response in responses:
          result = rrg_get_file_metadata_pb2.Result()
          assert response.Unpack(result)

          results_by_path[result.path.raw_bytes.decode()] = result

        assert "/" in results_by_path
        assert "/foo" in results_by_path
        assert "/foo/bar" in results_by_path
        assert "/foo/baz" in results_by_path
        assert "/foo/quux" in results_by_path

        assert "/foo/thud/too-deep" not in results_by_path

    flow_id = rrg_test_lib.ExecuteFlow(
        client_id=client_id,
        flow_cls=GetFileMetadataMaxDepthFlow,
        flow_args=rdf_flows.EmptyFlowArgs(),
        handlers=rrg_test_lib.FakePosixFileHandlers({
            "/foo/bar": b"",
            "/foo/baz": b"",
            "/foo/quux": b"",
            "/foo/thud/too-deep": b"",
        }),
    )

    flow_obj = db.ReadFlowObject(client_id, flow_id)
    self.assertEqual(flow_obj.error_message, "")
    self.assertEqual(flow_obj.flow_state, flows_pb2.Flow.FlowState.FINISHED)

  @db_test_lib.WithDatabase
  def testGetFileMetadata_PathPruningRegex(self, db: abstract_db.Database):
    client_id = db_test_utils.InitializeRRGClient(db)

    class GetFileMetadataPathPruningRegexFlow(flow_base.FlowBase):

      def Start(self) -> None:
        get_file_metadata = rrg_stubs.GetFileMetadata()
        get_file_metadata.args.paths.add().raw_bytes = "/foo".encode()
        get_file_metadata.args.max_depth = 128
        get_file_metadata.args.path_pruning_regex = "^/foo(/ba.(/.*)?)?$"
        get_file_metadata.Call(self._ProcessGetFileMetadata)

      @flow_base.UseProto2AnyResponses
      def _ProcessGetFileMetadata(
          self,
          responses: flow_responses.Responses[any_pb2.Any],
      ) -> None:
        assert responses.success

        results_by_path = {}
        for response in responses:
          result = rrg_get_file_metadata_pb2.Result()
          assert response.Unpack(result)

          results_by_path[result.path.raw_bytes.decode()] = result

        assert "/foo" in results_by_path
        assert "/foo/bar" in results_by_path
        assert "/foo/bar/thud" in results_by_path
        assert "/foo/bar/thud/norf" in results_by_path
        assert "/foo/baz" in results_by_path
        assert "/foo/baz/blargh" in results_by_path

        assert "/foo/quux" not in results_by_path

    flow_id = rrg_test_lib.ExecuteFlow(
        client_id=client_id,
        flow_cls=GetFileMetadataPathPruningRegexFlow,
        flow_args=rdf_flows.EmptyFlowArgs(),
        handlers=rrg_test_lib.FakePosixFileHandlers({
            "/foo/bar/thud/norf": b"",
            "/foo/baz/blargh": b"",
            "/foo/quux": b"",
        }),
    )

    flow_obj = db.ReadFlowObject(client_id, flow_id)
    self.assertEqual(flow_obj.error_message, "")
    self.assertEqual(flow_obj.flow_state, flows_pb2.Flow.FlowState.FINISHED)

  @db_test_lib.WithDatabase
  def testGetFileMetadata_ContentsRegex(self, db: abstract_db.Database):
    client_id = db_test_utils.InitializeRRGClient(db)

    class GetFileMetadataContentsRegexFlow(flow_base.FlowBase):

      def Start(self) -> None:
        get_file_metadata = rrg_stubs.GetFileMetadata()
        get_file_metadata.args.paths.add().raw_bytes = "/".encode()
        get_file_metadata.args.max_depth = 1
        get_file_metadata.args.contents_regex = "BA[RZ]"
        get_file_metadata.Call(self._ProcessGetFileMetadata)

      @flow_base.UseProto2AnyResponses
      def _ProcessGetFileMetadata(
          self,
          responses: flow_responses.Responses[any_pb2.Any],
      ) -> None:
        assert responses.success

        results_by_path = {}
        for response in responses:
          result = rrg_get_file_metadata_pb2.Result()
          assert response.Unpack(result)

          results_by_path[result.path.raw_bytes.decode()] = result

        assert "/bar" in results_by_path
        assert "/baz" in results_by_path

        assert "/" not in results_by_path
        assert "/foo" not in results_by_path

    flow_id = rrg_test_lib.ExecuteFlow(
        client_id=client_id,
        flow_cls=GetFileMetadataContentsRegexFlow,
        flow_args=rdf_flows.EmptyFlowArgs(),
        handlers=rrg_test_lib.FakePosixFileHandlers({
            "/foo": b"FOO",
            "/bar": b"BAR",
            "/baz": b"BAZ",
        }),
    )

    flow_obj = db.ReadFlowObject(client_id, flow_id)
    self.assertEqual(flow_obj.error_message, "")
    self.assertEqual(flow_obj.flow_state, flows_pb2.Flow.FlowState.FINISHED)

  @db_test_lib.WithDatabase
  def testGetFileMetadata_Digests(self, db: abstract_db.Database):
    client_id = db_test_utils.InitializeRRGClient(db)

    class GetFileMetadataDigestsFlow(flow_base.FlowBase):

      def Start(self) -> None:
        get_file_metadata = rrg_stubs.GetFileMetadata()
        get_file_metadata.args.paths.add().raw_bytes = "/foo/bar".encode()
        get_file_metadata.args.md5 = True
        get_file_metadata.args.sha1 = True
        get_file_metadata.args.sha256 = True
        get_file_metadata.Call(self._ProcessGetFileMetadata)

      @flow_base.UseProto2AnyResponses
      def _ProcessGetFileMetadata(
          self,
          responses: flow_responses.Responses[any_pb2.Any],
      ) -> None:
        assert responses.success
        assert len(responses) == 1

        result = rrg_get_file_metadata_pb2.Result()
        assert list(responses)[0].Unpack(result)

        assert result.path.raw_bytes == "/foo/bar".encode()
        assert result.md5 == hashlib.md5(b"Lorem ipsum.").digest()
        assert result.sha1 == hashlib.sha1(b"Lorem ipsum.").digest()
        assert result.sha256 == hashlib.sha256(b"Lorem ipsum.").digest()

    flow_id = rrg_test_lib.ExecuteFlow(
        client_id=client_id,
        flow_cls=GetFileMetadataDigestsFlow,
        flow_args=rdf_flows.EmptyFlowArgs(),
        handlers=rrg_test_lib.FakePosixFileHandlers({
            "/foo/bar": b"Lorem ipsum.",
        }),
    )

    flow_obj = db.ReadFlowObject(client_id, flow_id)
    self.assertEqual(flow_obj.error_message, "")
    self.assertEqual(flow_obj.flow_state, flows_pb2.Flow.FlowState.FINISHED)

  @db_test_lib.WithDatabase
  def testGetFileMetadata_Windows(self, db: abstract_db.Database):
    client_id = db_test_utils.InitializeRRGClient(db)

    class GetFileMetadataWindowsFlow(flow_base.FlowBase):

      def Start(self) -> None:
        get_file_metadata = rrg_stubs.GetFileMetadata()
        get_file_metadata.args.paths.add().raw_bytes = "C:\\".encode()
        get_file_metadata.args.max_depth = 2
        get_file_metadata.Call(self._ProcessGetFileMetadata)

      @flow_base.UseProto2AnyResponses
      def _ProcessGetFileMetadata(
          self,
          responses: flow_responses.Responses[any_pb2.Any],
      ) -> None:
        assert responses.success

        results_by_path = {}
        for response in responses:
          result = rrg_get_file_metadata_pb2.Result()
          assert response.Unpack(result)

          results_by_path[result.path.raw_bytes.decode()] = result

        assert "C:\\" in results_by_path
        assert "C:\\Foo" in results_by_path
        assert "C:\\Foo\\Bar" in results_by_path
        assert "C:\\Quux" in results_by_path
        assert "C:\\Quux\\Thud" in results_by_path

        assert "C:\\Foo\\Bar\\Too Deep" not in results_by_path

    flow_id = rrg_test_lib.ExecuteFlow(
        client_id=client_id,
        flow_cls=GetFileMetadataWindowsFlow,
        flow_args=rdf_flows.EmptyFlowArgs(),
        handlers=rrg_test_lib.FakeWindowsFileHandlers({
            "C:\\Foo\\Bar\\Too Deep": b"",
            "C:\\Quux\\Thud": b"",
        }),
    )

    flow_obj = db.ReadFlowObject(client_id, flow_id)
    self.assertEqual(flow_obj.error_message, "")
    self.assertEqual(flow_obj.flow_state, flows_pb2.Flow.FlowState.FINISHED)

  @db_test_lib.WithDatabase
  def testGetFileContents_SingleFile(self, db: abstract_db.Database):
    client_id = db_test_utils.InitializeRRGClient(db)

    class GetFileContentsSingleFileFlow(flow_base.FlowBase):

      def Start(self) -> None:
        action = rrg_stubs.GetFileContents()
        action.args.paths.add().raw_bytes = "/foo/bar".encode("utf-8")
        action.Call(self._ProcessGetFileContents)

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
          flow_cls=GetFileContentsSingleFileFlow,
          flow_args=rdf_flows.EmptyFlowArgs(),
          handlers=rrg_test_lib.FakePosixFileHandlers({
              "/foo/bar": b"foobar",
          }),
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
  def testGetFileContents_MultipleFiles(self, db: abstract_db.Database):
    client_id = db_test_utils.InitializeRRGClient(db)

    class GetFileContentsMultipleFilesFlow(flow_base.FlowBase):

      def Start(self) -> None:
        action = rrg_stubs.GetFileContents()

        action.args.paths.add().raw_bytes = "/foo/bar".encode("utf-8")
        action.args.paths.add().raw_bytes = "/foo/baz".encode("utf-8")
        action.args.paths.add().raw_bytes = "/foo/quux".encode("utf-8")
        action.Call(self._ProcessGetFileContents)

      @flow_base.UseProto2AnyResponses
      def _ProcessGetFileContents(
          self,
          responses: flow_responses.Responses[any_pb2.Any],
      ) -> None:
        assert responses.success

        for response in responses:
          result = rrg_get_file_contents_pb2.Result()
          assert response.Unpack(result)

          self.SendReply(rdfvalue.RDFBytes(result.blob_sha256))

    blob_sink = sinks_test_lib.FakeSink()

    sink_registry = {
        rrg_pb2.Sink.BLOB: blob_sink,
    }
    with mock.patch.object(sinks, "REGISTRY", sink_registry):
      flow_id = rrg_test_lib.ExecuteFlow(
          client_id=client_id,
          flow_cls=GetFileContentsMultipleFilesFlow,
          flow_args=rdf_flows.EmptyFlowArgs(),
          handlers=rrg_test_lib.FakePosixFileHandlers({
              "/foo/bar": b"foobar",
              "/foo/baz": b"foobaz",
              "/foo/quux": b"fooquux",
          }),
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
  def testGetFileContents_Symlink(self, db: abstract_db.Database):
    client_id = db_test_utils.InitializeRRGClient(db)

    class GetFileContentsSymlinkFlow(flow_base.FlowBase):

      def Start(self) -> None:
        action = rrg_stubs.GetFileContents()
        action.args.paths.add().raw_bytes = "/foo/symlink".encode("utf-8")
        action.Call(self._ProcessGetFileContents)

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
          flow_cls=GetFileContentsSymlinkFlow,
          flow_args=rdf_flows.EmptyFlowArgs(),
          handlers=rrg_test_lib.FakePosixFileHandlers({
              "/foo/symlink": "/foo/target",
              "/foo/target": b"bar",
          }),
      )

    blob_parcels = blob_sink.Parcels(client_id)
    self.assertLen(blob_parcels, 1)

    blob = rrg_blob_pb2.Blob()
    blob_parcels[0].payload.Unpack(blob)
    self.assertEqual(blob.data, b"bar")

    results = db.ReadFlowResults(client_id, flow_id, offset=0, count=1024)
    self.assertLen(results, 1)

    result = wrappers_pb2.BytesValue()
    self.assertTrue(results[0].payload.Unpack(result))
    self.assertEqual(result.value, hashlib.sha256(b"bar").digest())

  @db_test_lib.WithDatabase
  def testGetFileContents_EmptyFile(self, db: abstract_db.Database):
    client_id = db_test_utils.InitializeRRGClient(db)

    process_get_file_contents_called = False

    class GetFileContentsEmptyFileFlow(flow_base.FlowBase):

      def Start(self) -> None:
        action = rrg_stubs.GetFileContents()
        action.args.paths.add().raw_bytes = "/foo/bar".encode("utf-8")
        action.Call(self._ProcessGetFileContents)

      @flow_base.UseProto2AnyResponses
      def _ProcessGetFileContents(
          self,
          responses: flow_responses.Responses[any_pb2.Any],
      ) -> None:
        assert responses.success
        assert not responses

        nonlocal process_get_file_contents_called
        process_get_file_contents_called = True

    blob_sink = sinks_test_lib.FakeSink()

    sink_registry = {
        rrg_pb2.Sink.BLOB: blob_sink,
    }
    with mock.patch.object(sinks, "REGISTRY", sink_registry):
      flow_id = rrg_test_lib.ExecuteFlow(
          client_id=client_id,
          flow_cls=GetFileContentsEmptyFileFlow,
          flow_args=rdf_flows.EmptyFlowArgs(),
          handlers=rrg_test_lib.FakePosixFileHandlers({
              "/foo/bar": b"",
          }),
      )

    self.assertEmpty(blob_sink.Parcels(client_id))

    flow_obj = db.ReadFlowObject(client_id, flow_id)
    self.assertEqual(flow_obj.backtrace, "")
    self.assertEqual(flow_obj.error_message, "")
    self.assertEqual(flow_obj.flow_state, flows_pb2.Flow.FlowState.FINISHED)

    self.assertTrue(process_get_file_contents_called)

  @db_test_lib.WithDatabase
  def testGetFileContents_LargeFile(self, db: abstract_db.Database):
    client_id = db_test_utils.InitializeRRGClient(db)

    process_get_file_contents_called = False

    class GetFileContentsLargeFileFlow(flow_base.FlowBase):

      def Start(self) -> None:
        action = rrg_stubs.GetFileContents()
        action.args.paths.add().raw_bytes = "/foo/bar".encode("utf-8")
        action.Call(self._ProcessGetFileContents)

      @flow_base.UseProto2AnyResponses
      def _ProcessGetFileContents(
          self,
          responses_any: flow_responses.Responses[any_pb2.Any],
      ) -> None:
        assert responses_any.success

        # This is a multi-megabyte file so we expect multiple responses.
        assert len(responses_any) > 1

        responses = []

        for response_any in responses_any:
          response = rrg_get_file_contents_pb2.Result()
          response.ParseFromString(response_any.value)

          responses.append(response)

        responses.sort(key=lambda response: response.offset)
        for response, response_next in itertools.pairwise(responses):
          assert response.offset + response.length == response_next.offset

        nonlocal process_get_file_contents_called
        process_get_file_contents_called = True

    blob_sink = sinks_test_lib.FakeSink()

    sink_registry = {
        rrg_pb2.Sink.BLOB: blob_sink,
    }
    with mock.patch.object(sinks, "REGISTRY", sink_registry):
      flow_id = rrg_test_lib.ExecuteFlow(
          client_id=client_id,
          flow_cls=GetFileContentsLargeFileFlow,
          flow_args=rdf_flows.EmptyFlowArgs(),
          handlers=rrg_test_lib.FakePosixFileHandlers({
              "/foo/bar": b"\xff" * 13371337,
          }),
      )

    # This is a multi-megabyte file so we expect multiple blobs.
    self.assertGreater(len(blob_sink.Parcels(client_id)), 1)

    content = b""
    for blob_parcel in blob_sink.Parcels(client_id):
      blob = rrg_blob_pb2.Blob()
      blob_parcel.payload.Unpack(blob)

      content += blob.data

    self.assertEqual(content, b"\xff" * 13371337)

    flow_obj = db.ReadFlowObject(client_id, flow_id)
    self.assertEqual(flow_obj.backtrace, "")
    self.assertEqual(flow_obj.error_message, "")
    self.assertEqual(flow_obj.flow_state, flows_pb2.Flow.FlowState.FINISHED)

    self.assertTrue(process_get_file_contents_called)

  @db_test_lib.WithDatabase
  def testGetFileContents_UnknownPath(self, db: abstract_db.Database):
    client_id = db_test_utils.InitializeRRGClient(db)

    process_get_file_contents_called = False

    class GetFileContentsUnknownPathFlow(flow_base.FlowBase):

      def Start(self) -> None:
        action = rrg_stubs.GetFileContents()
        action.args.paths.add().raw_bytes = "/foo/bar".encode("utf-8")
        action.Call(self._ProcessGetFileContents)

      @flow_base.UseProto2AnyResponses
      def _ProcessGetFileContents(
          self,
          responses: flow_responses.Responses[any_pb2.Any],
      ) -> None:
        assert responses.success
        assert len(responses) == 1

        result = rrg_get_file_contents_pb2.Result()
        assert list(responses)[0].Unpack(result)
        assert result.path.raw_bytes == "/foo/bar".encode("utf-8")
        assert result.error == "open failed"

        nonlocal process_get_file_contents_called
        process_get_file_contents_called = True

    blob_sink = sinks_test_lib.FakeSink()

    sink_registry = {
        rrg_pb2.Sink.BLOB: blob_sink,
    }
    with mock.patch.object(sinks, "REGISTRY", sink_registry):
      rrg_test_lib.ExecuteFlow(
          client_id=client_id,
          flow_cls=GetFileContentsUnknownPathFlow,
          flow_args=rdf_flows.EmptyFlowArgs(),
          handlers=rrg_test_lib.FakePosixFileHandlers({}),
      )

    self.assertTrue(process_get_file_contents_called)

  @db_test_lib.WithDatabase
  def testGetFileSha256(self, db: abstract_db.Database):
    client_id = db_test_utils.InitializeRRGClient(db)

    class GetFileSha256Flow(flow_base.FlowBase):

      def Start(self) -> None:
        get_file_sha256 = rrg_stubs.GetFileSha256()
        get_file_sha256.args.path.raw_bytes = "/foo/bar".encode()
        get_file_sha256.Call(self._ProcessGetFileSha256)

      @flow_base.UseProto2AnyResponses
      def _ProcessGetFileSha256(
          self,
          responses: flow_responses.Responses[any_pb2.Any],
      ) -> None:
        assert responses.success
        assert len(responses) == 1

        result = rrg_get_file_sha256_pb2.Result()
        assert list(responses)[0].Unpack(result)

        assert result.path.raw_bytes == "/foo/bar".encode()
        assert result.offset == 0
        assert result.length == len(b"Lorem ipsum.")
        assert result.sha256 == hashlib.sha256(b"Lorem ipsum.").digest()

    flow_id = rrg_test_lib.ExecuteFlow(
        client_id=client_id,
        flow_cls=GetFileSha256Flow,
        flow_args=rdf_flows.EmptyFlowArgs(),
        handlers=rrg_test_lib.FakePosixFileHandlers({
            "/foo/bar": b"Lorem ipsum.",
        }),
    )

    flow_obj = db.ReadFlowObject(client_id, flow_id)
    self.assertEqual(flow_obj.error_message, "")
    self.assertEqual(flow_obj.flow_state, flows_pb2.Flow.FlowState.FINISHED)

  @db_test_lib.WithDatabase
  def testGetFileSha256_Length(self, db: abstract_db.Database):
    client_id = db_test_utils.InitializeRRGClient(db)

    class GetFileSha256LengthFlow(flow_base.FlowBase):

      def Start(self) -> None:
        get_file_sha256 = rrg_stubs.GetFileSha256()
        get_file_sha256.args.path.raw_bytes = "/foo/bar".encode()
        get_file_sha256.args.length = len(b"Lorem")
        get_file_sha256.Call(self._ProcessGetFileSha256)

      @flow_base.UseProto2AnyResponses
      def _ProcessGetFileSha256(
          self,
          responses: flow_responses.Responses[any_pb2.Any],
      ) -> None:
        assert responses.success
        assert len(responses) == 1

        result = rrg_get_file_sha256_pb2.Result()
        assert list(responses)[0].Unpack(result)

        assert result.path.raw_bytes == "/foo/bar".encode()
        assert result.offset == 0
        assert result.length == len(b"Lorem")
        assert result.sha256 == hashlib.sha256(b"Lorem").digest()

    flow_id = rrg_test_lib.ExecuteFlow(
        client_id=client_id,
        flow_cls=GetFileSha256LengthFlow,
        flow_args=rdf_flows.EmptyFlowArgs(),
        handlers=rrg_test_lib.FakePosixFileHandlers({
            "/foo/bar": b"Lorem ipsum.",
        }),
    )

    flow_obj = db.ReadFlowObject(client_id, flow_id)
    self.assertEqual(flow_obj.error_message, "")
    self.assertEqual(flow_obj.flow_state, flows_pb2.Flow.FlowState.FINISHED)


class FakeWinregHandlersTest(absltest.TestCase):

  @classmethod
  def setUpClass(cls):
    super().setUpClass()
    testing_startup.TestInit()

  @db_test_lib.WithDatabase
  def testGetWinregValue(self, db: abstract_db.Database):
    client_id = db_test_utils.InitializeRRGClient(db)

    class GetWinregValueFlow(flow_base.FlowBase):

      def Start(self) -> None:
        get_winreg_value = rrg_stubs.GetWinregValue()
        get_winreg_value.args.root = rrg_winreg_pb2.LOCAL_MACHINE
        get_winreg_value.args.key = r"SOFTWARE\Foo"
        get_winreg_value.args.name = "Bar"
        get_winreg_value.Call(self._ProcessGetWinregValue)

      @flow_base.UseProto2AnyResponses
      def _ProcessGetWinregValue(
          self,
          responses: flow_responses.Responses[any_pb2.Any],
      ) -> None:
        assert responses.success
        assert len(responses) == 1

        result = rrg_get_winreg_value_pb2.Result()
        assert list(responses)[0].Unpack(result)

        assert result.root == rrg_winreg_pb2.LOCAL_MACHINE
        assert result.key == r"SOFTWARE\Foo"
        assert result.value.name == "Bar"
        assert result.value.uint32 == 42

    flow_id = rrg_test_lib.ExecuteFlow(
        client_id=client_id,
        flow_cls=GetWinregValueFlow,
        flow_args=rdf_flows.EmptyFlowArgs(),
        handlers=rrg_test_lib.FakeWinregHandlers({
            rrg_winreg_pb2.LOCAL_MACHINE: {
                "SOFTWARE": {
                    "Foo": {
                        "Bar": 42,
                        "Baz": 1337,
                    },
                },
            },
        }),
    )

    flow_obj = db.ReadFlowObject(client_id, flow_id)
    self.assertEqual(flow_obj.backtrace, "")
    self.assertEqual(flow_obj.error_message, "")
    self.assertEqual(flow_obj.flow_state, flows_pb2.Flow.FlowState.FINISHED)

  @db_test_lib.WithDatabase
  def testGetWinregValue_NotExistingKey(self, db: abstract_db.Database):
    client_id = db_test_utils.InitializeRRGClient(db)

    class GetWinregValueNotExistingKeyFlow(flow_base.FlowBase):

      def Start(self) -> None:
        get_winreg_value = rrg_stubs.GetWinregValue()
        get_winreg_value.args.root = rrg_winreg_pb2.LOCAL_MACHINE
        get_winreg_value.args.key = r"SOFTWARE\Foo"
        get_winreg_value.args.name = "Bar"
        get_winreg_value.Call(self._ProcessGetWinregValue)

      @flow_base.UseProto2AnyResponses
      def _ProcessGetWinregValue(
          self,
          responses: flow_responses.Responses[any_pb2.Any],
      ) -> None:
        assert not responses.success

    flow_id = rrg_test_lib.ExecuteFlow(
        client_id=client_id,
        flow_cls=GetWinregValueNotExistingKeyFlow,
        flow_args=rdf_flows.EmptyFlowArgs(),
        handlers=rrg_test_lib.FakeWinregHandlers({
            rrg_winreg_pb2.LOCAL_MACHINE: {
                "SOFTWARE": {},
            },
        }),
    )

    flow_obj = db.ReadFlowObject(client_id, flow_id)
    self.assertEqual(flow_obj.backtrace, "")
    self.assertEqual(flow_obj.error_message, "")
    self.assertEqual(flow_obj.flow_state, flows_pb2.Flow.FlowState.FINISHED)

  @db_test_lib.WithDatabase
  def testGetWinregValue_DefaultValue(self, db: abstract_db.Database):
    client_id = db_test_utils.InitializeRRGClient(db)

    class GetWinregValueDefaultValueFlow(flow_base.FlowBase):

      def Start(self) -> None:
        get_winreg_value = rrg_stubs.GetWinregValue()
        get_winreg_value.args.root = rrg_winreg_pb2.LOCAL_MACHINE
        get_winreg_value.args.key = r"SOFTWARE\Foo\Bar"
        get_winreg_value.Call(self._ProcessGetWinregValue)

      @flow_base.UseProto2AnyResponses
      def _ProcessGetWinregValue(
          self,
          responses: flow_responses.Responses[any_pb2.Any],
      ) -> None:
        assert responses.success
        assert len(responses) == 1

        result = rrg_get_winreg_value_pb2.Result()
        assert list(responses)[0].Unpack(result)

        assert result.root == rrg_winreg_pb2.LOCAL_MACHINE
        assert result.key == r"SOFTWARE\Foo\Bar"
        assert result.value.name == ""  # pylint: disable=g-explicit-bool-comparison
        assert result.value.string == ""  # pylint: disable=g-explicit-bool-comparison

    flow_id = rrg_test_lib.ExecuteFlow(
        client_id=client_id,
        flow_cls=GetWinregValueDefaultValueFlow,
        flow_args=rdf_flows.EmptyFlowArgs(),
        handlers=rrg_test_lib.FakeWinregHandlers({
            rrg_winreg_pb2.LOCAL_MACHINE: {
                "SOFTWARE": {
                    "Foo": {
                        "Bar": {},
                    },
                },
            },
        }),
    )

    flow_obj = db.ReadFlowObject(client_id, flow_id)
    self.assertEqual(flow_obj.backtrace, "")
    self.assertEqual(flow_obj.error_message, "")
    self.assertEqual(flow_obj.flow_state, flows_pb2.Flow.FlowState.FINISHED)

  @db_test_lib.WithDatabase
  def testListWinregValues(self, db: abstract_db.Database):
    client_id = db_test_utils.InitializeRRGClient(db)

    class ListWinregValuesFlow(flow_base.FlowBase):

      def Start(self) -> None:
        list_winreg_values = rrg_stubs.ListWinregValues()
        list_winreg_values.args.root = rrg_winreg_pb2.LOCAL_MACHINE
        list_winreg_values.args.key = r"SOFTWARE\Foo"
        list_winreg_values.Call(self._ProcessListWinregValues)

      @flow_base.UseProto2AnyResponses
      def _ProcessListWinregValues(
          self,
          responses: flow_responses.Responses[any_pb2.Any],
      ) -> None:
        assert responses.success
        assert len(responses) == 3

        results_by_value_name = {}
        for response in responses:
          result = rrg_list_winreg_values_pb2.Result()
          assert response.Unpack(result)

          results_by_value_name[result.value.name] = result

        result_default = results_by_value_name[""]
        assert result_default.root == rrg_winreg_pb2.LOCAL_MACHINE
        assert result_default.key == r"SOFTWARE\Foo"
        assert result_default.value.string == ""  # pylint: disable=g-explicit-bool-comparison

        result_bar = results_by_value_name["Bar"]
        assert result_bar.root == rrg_winreg_pb2.LOCAL_MACHINE
        assert result_bar.key == r"SOFTWARE\Foo"
        assert result_bar.value.uint32 == 42

        result_baz = results_by_value_name["Baz"]
        assert result_baz.root == rrg_winreg_pb2.LOCAL_MACHINE
        assert result_baz.key == r"SOFTWARE\Foo"
        assert result_baz.value.uint32 == 1337

    flow_id = rrg_test_lib.ExecuteFlow(
        client_id=client_id,
        flow_cls=ListWinregValuesFlow,
        flow_args=rdf_flows.EmptyFlowArgs(),
        handlers=rrg_test_lib.FakeWinregHandlers({
            rrg_winreg_pb2.LOCAL_MACHINE: {
                "SOFTWARE": {
                    "Foo": {
                        "Bar": 42,
                        "Baz": 1337,
                    },
                },
            },
        }),
    )

    flow_obj = db.ReadFlowObject(client_id, flow_id)
    self.assertEqual(flow_obj.backtrace, "")
    self.assertEqual(flow_obj.error_message, "")
    self.assertEqual(flow_obj.flow_state, flows_pb2.Flow.FlowState.FINISHED)

  @db_test_lib.WithDatabase
  def testListWinregValues_MaxDepth(self, db: abstract_db.Database):
    client_id = db_test_utils.InitializeRRGClient(db)

    class ListWinregValuesMaxDepthFlow(flow_base.FlowBase):

      def Start(self) -> None:
        list_winreg_values = rrg_stubs.ListWinregValues()
        list_winreg_values.args.root = rrg_winreg_pb2.LOCAL_MACHINE
        list_winreg_values.args.key = r"SOFTWARE"
        list_winreg_values.args.max_depth = 1
        list_winreg_values.Call(self._ProcessListWinregValues)

      @flow_base.UseProto2AnyResponses
      def _ProcessListWinregValues(
          self,
          responses: flow_responses.Responses[any_pb2.Any],
      ) -> None:
        assert responses.success
        assert len(responses) == 3

        results_by_key_value_name = {}
        for response in responses:
          result = rrg_list_winreg_values_pb2.Result()
          assert response.Unpack(result)

          results_by_key_value_name[(result.key, result.value.name)] = result

        result = results_by_key_value_name[(r"SOFTWARE", "")]
        assert result.root == rrg_winreg_pb2.LOCAL_MACHINE
        assert result.value.string == ""  # pylint: disable=g-explicit-bool-comparison

        result = results_by_key_value_name[(r"SOFTWARE\Foo", "")]
        assert result.root == rrg_winreg_pb2.LOCAL_MACHINE
        assert result.value.string == ""  # pylint: disable=g-explicit-bool-comparison

        result = results_by_key_value_name[(r"SOFTWARE\Foo", "Bar")]
        assert result.root == rrg_winreg_pb2.LOCAL_MACHINE
        assert result.value.uint32 == 42

        # Depth 2, should not be included.
        assert (r"SOFTWARE\Foo\Baz", "") not in results_by_key_value_name
        assert (r"SOFTWARE\Foo\Baz", "Quux") not in results_by_key_value_name

    flow_id = rrg_test_lib.ExecuteFlow(
        client_id=client_id,
        flow_cls=ListWinregValuesMaxDepthFlow,
        flow_args=rdf_flows.EmptyFlowArgs(),
        handlers=rrg_test_lib.FakeWinregHandlers({
            rrg_winreg_pb2.LOCAL_MACHINE: {
                "SOFTWARE": {
                    "Foo": {
                        "Bar": 42,
                        "Baz": {
                            "Quux": 1337,
                        },
                    },
                },
            },
        }),
    )

    flow_obj = db.ReadFlowObject(client_id, flow_id)
    self.assertEqual(flow_obj.backtrace, "")
    self.assertEqual(flow_obj.error_message, "")
    self.assertEqual(flow_obj.flow_state, flows_pb2.Flow.FlowState.FINISHED)

  @db_test_lib.WithDatabase
  def testListWinregValues_NotExistingKey(self, db: abstract_db.Database):
    client_id = db_test_utils.InitializeRRGClient(db)

    class ListWinregValuesNotExistingKeyFlow(flow_base.FlowBase):

      def Start(self) -> None:
        list_winreg_values = rrg_stubs.ListWinregValues()
        list_winreg_values.args.root = rrg_winreg_pb2.LOCAL_MACHINE
        list_winreg_values.args.key = r"SOFTWARE\Foo\Bar"
        list_winreg_values.Call(self._ProcessListWinregValues)

      @flow_base.UseProto2AnyResponses
      def _ProcessListWinregValues(
          self,
          responses: flow_responses.Responses[any_pb2.Any],
      ) -> None:
        assert not responses.success

    flow_id = rrg_test_lib.ExecuteFlow(
        client_id=client_id,
        flow_cls=ListWinregValuesNotExistingKeyFlow,
        flow_args=rdf_flows.EmptyFlowArgs(),
        handlers=rrg_test_lib.FakeWinregHandlers({
            rrg_winreg_pb2.LOCAL_MACHINE: {
                "SOFTWARE": {},
            },
        }),
    )

    flow_obj = db.ReadFlowObject(client_id, flow_id)
    self.assertEqual(flow_obj.backtrace, "")
    self.assertEqual(flow_obj.error_message, "")
    self.assertEqual(flow_obj.flow_state, flows_pb2.Flow.FlowState.FINISHED)

  @db_test_lib.WithDatabase
  def testListWinregValues_CustomDefaultValue(self, db: abstract_db.Database):
    client_id = db_test_utils.InitializeRRGClient(db)

    class ListWinregValuesCustomDefaultValueFlow(flow_base.FlowBase):

      def Start(self) -> None:
        list_winreg_values = rrg_stubs.ListWinregValues()
        list_winreg_values.args.root = rrg_winreg_pb2.LOCAL_MACHINE
        list_winreg_values.args.key = r"SOFTWARE\Foo\Bar"
        list_winreg_values.Call(self._ProcessListWinregValues)

      @flow_base.UseProto2AnyResponses
      def _ProcessListWinregValues(
          self,
          responses: flow_responses.Responses[any_pb2.Any],
      ) -> None:
        assert responses.success
        assert len(responses) == 1

        result = rrg_list_winreg_values_pb2.Result()
        assert list(responses)[0].Unpack(result)

        assert result.root == rrg_winreg_pb2.LOCAL_MACHINE
        assert result.key == r"SOFTWARE\Foo\Bar"
        assert result.value.name == ""  # pylint: disable=g-explicit-bool-comparison
        assert result.value.uint32 == 42

    flow_id = rrg_test_lib.ExecuteFlow(
        client_id=client_id,
        flow_cls=ListWinregValuesCustomDefaultValueFlow,
        flow_args=rdf_flows.EmptyFlowArgs(),
        handlers=rrg_test_lib.FakeWinregHandlers({
            rrg_winreg_pb2.LOCAL_MACHINE: {
                "SOFTWARE": {
                    "Foo": {
                        "Bar": {
                            "": 42,
                        },
                    },
                },
            },
        }),
    )

    flow_obj = db.ReadFlowObject(client_id, flow_id)
    self.assertEqual(flow_obj.backtrace, "")
    self.assertEqual(flow_obj.error_message, "")
    self.assertEqual(flow_obj.flow_state, flows_pb2.Flow.FlowState.FINISHED)

  @db_test_lib.WithDatabase
  def testListWinregKeys(self, db: abstract_db.Database):
    client_id = db_test_utils.InitializeRRGClient(db)

    class ListWinregKeysFlow(flow_base.FlowBase):

      def Start(self) -> None:
        list_winreg_keys = rrg_stubs.ListWinregKeys()
        list_winreg_keys.args.root = rrg_winreg_pb2.LOCAL_MACHINE
        list_winreg_keys.args.key = r"SOFTWARE\Foo"
        list_winreg_keys.Call(self._ProcessListWinregKeys)

      @flow_base.UseProto2AnyResponses
      def _ProcessListWinregKeys(
          self,
          responses: flow_responses.Responses[any_pb2.Any],
      ) -> None:
        assert responses.success
        assert len(responses) == 2

        results_by_subkey = {}
        for response in responses:
          result = rrg_list_winreg_keys_pb2.Result()
          assert response.Unpack(result)

          results_by_subkey[result.subkey] = result

        assert "Bar" in results_by_subkey
        assert "Baz" in results_by_subkey
        assert "Quux" not in results_by_subkey
        assert "Baz\\Norf" not in results_by_subkey

        assert results_by_subkey["Bar"].root == rrg_winreg_pb2.LOCAL_MACHINE
        assert results_by_subkey["Bar"].key == r"SOFTWARE\Foo"

        assert results_by_subkey["Baz"].root == rrg_winreg_pb2.LOCAL_MACHINE
        assert results_by_subkey["Baz"].key == r"SOFTWARE\Foo"

    flow_id = rrg_test_lib.ExecuteFlow(
        client_id=client_id,
        flow_cls=ListWinregKeysFlow,
        flow_args=rdf_flows.EmptyFlowArgs(),
        handlers=rrg_test_lib.FakeWinregHandlers({
            rrg_winreg_pb2.LOCAL_MACHINE: {
                "SOFTWARE": {
                    "Foo": {
                        "Quux": 42,
                        "Bar": {},
                        "Baz": {
                            "Norf": {},
                        },
                    },
                },
            },
        }),
    )

    flow_obj = db.ReadFlowObject(client_id, flow_id)
    self.assertEqual(flow_obj.backtrace, "")
    self.assertEqual(flow_obj.error_message, "")
    self.assertEqual(flow_obj.flow_state, flows_pb2.Flow.FlowState.FINISHED)

  @db_test_lib.WithDatabase
  def testListWinregKeys_MaxDepth(self, db: abstract_db.Database):
    client_id = db_test_utils.InitializeRRGClient(db)

    class ListWinregKeysMaxDepthFlow(flow_base.FlowBase):

      def Start(self) -> None:
        list_winreg_keys = rrg_stubs.ListWinregKeys()
        list_winreg_keys.args.root = rrg_winreg_pb2.LOCAL_MACHINE
        list_winreg_keys.args.key = r"SOFTWARE"
        list_winreg_keys.args.max_depth = 2
        list_winreg_keys.Call(self._ProcessListWinregKeys)

      @flow_base.UseProto2AnyResponses
      def _ProcessListWinregKeys(
          self,
          responses: flow_responses.Responses[any_pb2.Any],
      ) -> None:
        assert responses.success
        assert len(responses) == 3

        results_by_subkey = {}
        for response in responses:
          result = rrg_list_winreg_keys_pb2.Result()
          assert response.Unpack(result)

          results_by_subkey[result.subkey] = result

        assert "Foo" in results_by_subkey
        assert "Foo\\Bar" in results_by_subkey
        assert "Foo\\Baz" in results_by_subkey

        assert "Foo\\Bar\\Quux" not in results_by_subkey
        assert "Foo\\Bar\\Quux\\Thud" not in results_by_subkey
        assert "Foo\\Bar\\Norf" not in results_by_subkey
        assert "Foo\\Baz\\Blargh" not in results_by_subkey

    flow_id = rrg_test_lib.ExecuteFlow(
        client_id=client_id,
        flow_cls=ListWinregKeysMaxDepthFlow,
        flow_args=rdf_flows.EmptyFlowArgs(),
        handlers=rrg_test_lib.FakeWinregHandlers({
            rrg_winreg_pb2.LOCAL_MACHINE: {
                "SOFTWARE": {
                    "Foo": {
                        "Bar": {
                            "Quux": {},
                            "Norf": {
                                "Thud": {},
                            },
                        },
                        "Baz": {
                            "Blargh": 1337,
                        },
                    },
                },
            },
        }),
    )

    flow_obj = db.ReadFlowObject(client_id, flow_id)
    self.assertEqual(flow_obj.backtrace, "")
    self.assertEqual(flow_obj.error_message, "")
    self.assertEqual(flow_obj.flow_state, flows_pb2.Flow.FlowState.FINISHED)

  @db_test_lib.WithDatabase
  def testListWinregKeys_NotExistingKey(self, db: abstract_db.Database):
    client_id = db_test_utils.InitializeRRGClient(db)

    class ListWinregKeysNotExistingKeyFlow(flow_base.FlowBase):

      def Start(self) -> None:
        list_winreg_keys = rrg_stubs.ListWinregKeys()
        list_winreg_keys.args.root = rrg_winreg_pb2.LOCAL_MACHINE
        list_winreg_keys.args.key = r"SOFTWARE\Foo\Bar"
        list_winreg_keys.Call(self._ProcessListWinregKeys)

      @flow_base.UseProto2AnyResponses
      def _ProcessListWinregKeys(
          self,
          responses: flow_responses.Responses[any_pb2.Any],
      ) -> None:
        assert not responses.success

    flow_id = rrg_test_lib.ExecuteFlow(
        client_id=client_id,
        flow_cls=ListWinregKeysNotExistingKeyFlow,
        flow_args=rdf_flows.EmptyFlowArgs(),
        handlers=rrg_test_lib.FakeWinregHandlers({
            rrg_winreg_pb2.LOCAL_MACHINE: {
                "SOFTWARE": {},
            },
        }),
    )

    flow_obj = db.ReadFlowObject(client_id, flow_id)
    self.assertEqual(flow_obj.backtrace, "")
    self.assertEqual(flow_obj.error_message, "")
    self.assertEqual(flow_obj.flow_state, flows_pb2.Flow.FlowState.FINISHED)


if __name__ == "__main__":
  absltest.main()
