#!/usr/bin/env python
"""Helpers for testing RRG-related code."""

import contextlib
import hashlib
from typing import Callable, Mapping, Type
from unittest import mock

from google.protobuf import any_pb2
from google.protobuf import message as message_pb2
from grr_response_core.lib import rdfvalue
from grr_response_core.lib.rdfvalues import structs as rdf_structs
from grr_response_proto import flows_pb2
from grr_response_server import data_store
from grr_response_server import fleetspeak_connector
from grr_response_server import flow
from grr_response_server import flow_base
from grr_response_server import sinks
from grr_response_server import worker_lib
from grr_response_server.databases import db
from grr_response_server.databases import db_utils
from grr_response_server.databases import mem as db_mem
from fleetspeak.src.common.proto.fleetspeak import common_pb2
from grr_response_proto import rrg_pb2
from grr_response_proto.rrg import blob_pb2 as rrg_blob_pb2
from grr_response_proto.rrg.action import get_file_contents_pb2 as rrg_get_file_contents_pb2


class Session:
  """Fake Python-only RRG session that aggregates replies and parcels."""

  args: any_pb2.Any

  replies: list[message_pb2.Message]

  def __init__(self, args: any_pb2.Any) -> None:
    self.args = args
    self.replies = list()
    self.parcels = dict()

  def Reply(self, item: message_pb2.Message):
    self.replies.append(item)

  def Send(self, sink: rrg_pb2.Sink, item: message_pb2.Message):
    self.parcels.setdefault(sink, []).append(item)


def ExecuteFlow(
    client_id: str,
    flow_cls: Type[flow_base.FlowBase],
    flow_args: rdf_structs.RDFProtoStruct,
    handlers: Mapping["rrg_pb2.Action", Callable[[Session], None]],
) -> str:
  """Create and execute flow on the given RRG client.

  Args:
    client_id: Identifier of a RRG client.
    flow_cls: Flow class to execute.
    flow_args: Argument to execute the flow with.
    handlers: Fake action handlers to use for invoking RRG actions.

  Returns:
    Identifier of the launched flow.
  """
  worker = worker_lib.GRRWorker()

  requests: list[rrg_pb2.Request] = []

  class MockFleetspeakOutgoing:
    """`connector.OutgoingConnection` that does not use real network."""

    def InsertMessage(self, message: common_pb2.Message, **kwargs) -> None:
      """Inserts a message to be sent to a Fleetspeak agent."""
      del kwargs  # Unused.

      if message.destination.service_name != "RRG":
        raise RuntimeError(
            f"Unexpected message service: {message.destination.service_name}",
        )
      if message.message_type != "rrg.Request":
        raise RuntimeError(
            f"Unexpected message type: {message.message_type}",
        )

      request = rrg_pb2.Request()
      if not message.data.Unpack(request):
        raise RuntimeError(
            f"Unexpected message request: {message.data}",
        )

      requests.append(request)

  class MockFleetspeakConnector:
    """`connector.ServiceClient` with mocked output channel."""

    def __init__(self):
      self.outgoing = MockFleetspeakOutgoing()

  exit_stack = contextlib.ExitStack()

  # Ideally, we should not really mock anything out but GRR's insistence on
  # using global variables for everything forces us to do so. This is the same
  # thing `fleetspeak_test_lib` does.
  exit_stack.enter_context(
      mock.patch.object(
          target=fleetspeak_connector,
          attribute="CONN",
          new=MockFleetspeakConnector(),
      )
  )

  data_store.REL_DB.RegisterFlowProcessingHandler(worker.ProcessFlow)
  exit_stack.callback(data_store.REL_DB.UnregisterFlowProcessingHandler)

  with exit_stack:
    flow_id = flow.StartFlow(
        client_id=client_id,
        flow_cls=flow_cls,
        flow_args=flow_args,
    )

    # Starting the flow also invokes its `Start` method which may fail for
    # various reasons. Thus, before we start processing any requests, we need to
    # verify that the flow did not fail or terminate immediately if it did.
    flow_obj = data_store.REL_DB.ReadFlowObject(
        client_id=client_id,
        flow_id=flow_id,
    )
    if flow_obj.flow_state == flows_pb2.Flow.FlowState.ERROR:
      return flow_id

    # The outer loop simulates the "on server" processing whereas the inner loop
    # simulates the "on endpoint" processing. This outer loop will finish only
    # after both the "server" and the "endpoint" have no work to do anymore.
    #
    # Note that we want to trigger the outerloop at least once even if there is
    # no work to be carried on the "endpoint" as the `Start` method might have
    # spawned subflows which need to be executed (and these in turn can spawn
    # more flows or invoke agent actions).
    while True:
      # First, we want to process all the requests "sent" to the endpoint using
      # the handlers that are given to us. Note that requests may not belong to
      # the flow we started above but to any of the child flows spawned by it.
      while requests:
        request = requests.pop(0)

        try:
          handler = handlers[request.action]
        except KeyError:
          raise RuntimeError(
              f"Missing handler for {rrg_pb2.Action.Name(request.action)!r}",
          ) from None

        flow_status = flows_pb2.FlowStatus()
        flow_status.client_id = client_id
        flow_status.flow_id = db_utils.IntToFlowID(request.flow_id)
        flow_status.request_id = request.request_id

        session = Session(request.args)

        try:
          handler(session)
        except Exception as error:  # pylint: disable=broad-exception-caught
          flow_status.status = flows_pb2.FlowStatus.ERROR
          flow_status.error_message = str(error)
        else:
          flow_status.status = flows_pb2.FlowStatus.OK

        for sink, parcel_payloads in session.parcels.items():
          for parcel_payload in parcel_payloads:
            parcel = rrg_pb2.Parcel()
            parcel.sink = sink
            parcel.payload.Pack(parcel_payload)

            try:
              sinks.Accept(client_id, parcel)
            except Exception as error:  # pylint: disable=broad-exception-caught
              # We set the error only if no error has been observed so far.
              if flow_status.status == flows_pb2.FlowStatus.OK:
                flow_status.status = flows_pb2.FlowStatus.ERROR
                flow_status.error_message = str(error)

        # Response identifiers start at 1 (for whatever reason) and status is
        # the last one.
        flow_status.response_id = len(session.replies) + 1

        flow_responses = []

        for i, reply in enumerate(session.replies, start=1):
          flow_response = flows_pb2.FlowResponse()
          flow_response.client_id = client_id
          flow_response.flow_id = db_utils.IntToFlowID(request.flow_id)
          flow_response.request_id = request.request_id
          flow_response.response_id = i
          flow_response.any_payload.Pack(reply)

          flow_responses.append(flow_response)

        flow_responses.append(flow_status)

        data_store.REL_DB.WriteFlowResponses(flow_responses)

      # We finished work on the "endpoint" and written all flow responses. Now
      # the worker needs to finish processing all through appropriate flow state
      # methods.
      #
      # The deadline of 10 seconds is arbitrary, it is just what the original
      # `flow_test_lib` uses.
      assert isinstance(data_store.REL_DB, db.DatabaseValidationWrapper)
      assert isinstance(data_store.REL_DB.delegate, db_mem.InMemoryDB)
      data_store.REL_DB.delegate.WaitUntilNoFlowsToProcess(
          timeout=rdfvalue.Duration.From(10, rdfvalue.MINUTES),
      )

      # If we processed all the flows and there is no work to be done on the
      # "endpoint" we are done.
      if not requests:
        break

  return flow_id


def GetFileContentsHandler(
    filesystem: dict[str, bytes],
) -> Callable[[Session], None]:
  """Handler for the `GET_FILE_CONTENTS` action that emulates given filesystem.

  Args:
    filesystem: A mapping from paths to file contents to use.

  Returns:
    A handler that can be supplied to the `ExecuteFlow` helper.
  """

  def Wrapper(session: Session) -> None:
    args = rrg_get_file_contents_pb2.Args()
    if not session.args.Unpack(args):
      raise RuntimeError(f"Invalid session arguments: {session.args}")

    path = args.path.raw_bytes.decode("utf-8")

    try:
      content = filesystem[path]
    except KeyError as error:
      raise RuntimeError(f"Unknown path: {path!r}") from error

    blob = rrg_blob_pb2.Blob()
    if args.length:
      blob.data = content[args.offset : args.offset + args.length]
    else:
      blob.data = content[args.offset :]
    session.Send(rrg_pb2.Sink.BLOB, blob)

    result = rrg_get_file_contents_pb2.Result()
    result.offset = args.offset
    result.length = len(blob.data)
    result.blob_sha256 = hashlib.sha256(blob.data).digest()
    session.Reply(result)

  return Wrapper
