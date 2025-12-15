#!/usr/bin/env python
"""Helper classes for flows-related testing."""

from collections.abc import Iterable, Sequence
import contextlib
import logging
import re
import sys
from typing import Optional, Union
from unittest import mock

from google.protobuf import any_pb2
from grr_response_client import actions
from grr_response_core.lib import rdfvalue
from grr_response_core.lib import registry
from grr_response_core.lib.rdfvalues import client as rdf_client
from grr_response_core.lib.rdfvalues import client_action as rdf_client_action
from grr_response_core.lib.rdfvalues import flows as rdf_flows
from grr_response_core.lib.rdfvalues import protodict as rdf_protodict
from grr_response_core.lib.rdfvalues import structs as rdf_structs
from grr_response_core.lib.util import precondition
from grr_response_proto import flows_pb2
from grr_response_proto import jobs_pb2
from grr_response_proto import output_plugin_pb2
from grr_response_proto import tests_pb2
from grr_response_server import action_registry
from grr_response_server import data_store
from grr_response_server import events
from grr_response_server import flow
from grr_response_server import flow_base
from grr_response_server import flow_responses
from grr_response_server import handler_registry
from grr_response_server import message_handlers
from grr_response_server import server_stubs
from grr_response_server import worker_lib
from grr_response_server.databases import db
from grr_response_server.databases import mem
from grr_response_server.rdfvalues import flow_objects as rdf_flow_objects
from grr_response_server.rdfvalues import mig_flow_objects
from grr_response_server.rdfvalues import objects as rdf_objects
from grr_response_server.rdfvalues import output_plugin as rdf_output_plugin
from grr.test_lib import action_mocks
from grr.test_lib import client_test_lib
from grr.test_lib import fleetspeak_test_lib
from grr.test_lib import test_lib


class InfiniteFlow(flow_base.FlowBase):
  """Flow that never ends."""

  def Start(self):
    self.CallClient(
        server_stubs.GetFileStat,
        request=rdf_client_action.GetFileStatRequest(),
        next_state="NextState",
    )

  def NextState(self, responses):
    _ = responses
    self.CallClient(
        server_stubs.GetFileStat,
        request=rdf_client_action.GetFileStatRequest(),
        next_state="NextStateAgain",
    )

  def NextStateAgain(self, responses):
    _ = responses
    self.CallClient(
        server_stubs.GetFileStat,
        request=rdf_client_action.GetFileStatRequest(),
        next_state="NextState",
    )


class ClientFlowWithoutCategory(flow_base.FlowBase):
  pass


class ClientFlowWithCategory(flow_base.FlowBase):
  category = "/Test/"


class CPULimitFlow(flow_base.FlowBase):
  """This flow is used to test the cpu limit."""

  def Start(self):
    self.CallClient(
        action_registry.ACTION_STUB_BY_ID["Store"],
        request=rdf_protodict.DataBlob(string="Hey!"),
        next_state="State1",
    )

  def State1(self, responses):
    del responses
    self.CallClient(
        action_registry.ACTION_STUB_BY_ID["Store"],
        request=rdf_protodict.DataBlob(string="Hey!"),
        next_state="State2",
    )

  def State2(self, responses):
    del responses
    self.CallClient(
        action_registry.ACTION_STUB_BY_ID["Store"],
        request=rdf_protodict.DataBlob(string="Hey!"),
        next_state="Done",
    )

  def Done(self, responses):
    pass


class CPULimitFlowProto(flow_base.FlowBase):
  """This flow is used to test the cpu limit."""

  def Start(self):
    self.CallClientProto(
        action_registry.ACTION_STUB_BY_ID["Store"],
        jobs_pb2.DataBlob(string="Hey!"),
        next_state="State1",
    )

  def State1(self, responses: flow_responses.Responses[any_pb2.Any]) -> None:
    """First state."""
    del responses
    self.CallClientProto(
        action_registry.ACTION_STUB_BY_ID["Store"],
        jobs_pb2.DataBlob(string="Hey!"),
        next_state="State2",
    )

  def State2(self, responses: flow_responses.Responses[any_pb2.Any]) -> None:
    """Second state."""
    del responses
    self.CallClientProto(
        action_registry.ACTION_STUB_BY_ID["Store"],
        jobs_pb2.DataBlob(string="Hey!"),
        next_state="End",
    )


class FlowWithOneClientRequest(flow_base.FlowBase):
  """Test flow that does one client request in Start() state."""

  def Start(self):
    self.CallClient(
        client_test_lib.Test,
        request=rdf_protodict.DataBlob(data=b"test"),
        next_state="End",
    )


class SendingFlowArgs(rdf_structs.RDFProtoStruct):
  protobuf = tests_pb2.SendingFlowArgs


class SendingFlow(flow_base.FlowBase):
  """Tests sending messages to clients."""
  args_type = SendingFlowArgs

  # Flow has to have a category otherwise FullAccessControlManager won't
  # let non-supervisor users to run it at all (it will be considered
  # externally inaccessible).
  category = "/Test/"

  def Start(self):
    """Just send a few messages."""
    for unused_i in range(0, self.args.message_count):
      self.CallClient(
          server_stubs.ReadBuffer,
          request=rdf_client.BufferReference(offset=0, length=100),
          next_state="Process",
      )


class RaiseOnStart(flow_base.FlowBase):
  """A broken flow that raises in the Start method."""

  def Start(self):
    raise Exception("Broken Start")


class BrokenFlow(flow_base.FlowBase):
  """A flow which does things wrongly."""

  def Start(self):
    """Send a message to an incorrect state."""
    self.CallClient(server_stubs.ReadBuffer, next_state="WrongProcess")


class DummyFlow(flow_base.FlowBase):
  """Dummy flow that does nothing."""


class DummyFlowProgress(rdf_structs.RDFProtoStruct):
  protobuf = tests_pb2.DummyFlowProgress


class DummyFlowWithProgress(flow_base.FlowBase):
  """Dummy flow that reports its own progress."""
  progress_type = DummyFlowProgress

  def GetProgress(self) -> DummyFlowProgress:
    return DummyFlowProgress(status="Progress.")


class FlowWithOneNestedFlow(flow_base.FlowBase):
  """Flow that calls a nested flow."""

  def Start(self):
    self.CallFlow("DummyFlow", next_state="Done")

  def Done(self, responses=None):
    del responses


class FlowWithTwoLevelsOfNestedFlows(flow_base.FlowBase):
  """Flow that calls a nested flow."""

  def Start(self):
    self.CallFlow("FlowWithOneNestedFlow", next_state="Done")

  def Done(self, responses=None):
    del responses


class DummyFlowWithSingleReply(flow_base.FlowBase):
  """Just emits 1 reply."""

  def Start(self):
    self.CallState(next_state="SendSomething")

  def SendSomething(self, responses=None):
    del responses
    self.SendReply(rdfvalue.RDFString("oh"))


class DummyLogFlow(flow_base.FlowBase):
  """Just emit logs."""

  def Start(self):
    """Log."""
    # TODO(user): Remove this as soon as mixed AFF4/REL_DB hunts are gone.
    # This is needed so that REL_DB flows logic doesn't try to execute
    # all flow states immediately in place (doing this may cause a deadlock
    # when a flow runs inside a hunt, since the flow will try to update
    # an already locked hunt).
    self.CallClient(
        server_stubs.GetFileStat,
        request=rdf_client_action.GetFileStatRequest(),
        next_state="NextState",
    )

  def NextState(self, responses=None):
    del responses
    self.Log("First")
    self.CallFlow(DummyLogFlowChild.__name__, next_state="Done")
    self.Log("Second")

  def Done(self, responses=None):
    del responses
    self.Log("Third")
    self.Log("Fourth")


class DummyLogFlowChild(flow_base.FlowBase):
  """Just emit logs."""

  def Start(self):
    """Log."""
    self.Log("Uno")
    self.CallState(next_state="Done")
    self.Log("Dos")

  def Done(self, responses=None):
    del responses
    self.Log("Tres")
    self.Log("Cuatro")


class EchoLogFlowProto(
    flow_base.FlowBase[
        jobs_pb2.LogMessage,
        flows_pb2.DefaultFlowStore,
        flows_pb2.DefaultFlowProgress,
    ]
):
  """Sends a single log result."""

  args_type = rdf_client.LogMessage
  result_types = (rdf_client.LogMessage,)
  proto_args_type = jobs_pb2.LogMessage
  proto_result_types = (jobs_pb2.LogMessage,)

  def Start(self):
    self.SendReplyProto(
        jobs_pb2.LogMessage(data=f"echo('{self.proto_args.data}')")
    )


class FlowTestsBaseclass(test_lib.GRRBaseTest):
  """The base class for all flow tests."""

  def setUp(self):
    super().setUp()

    # Some tests run with fake time and leak into the last_progress_time. To
    # prevent getting negative durations, we clean up here.
    actions.ActionPlugin.last_progress_time = (
        rdfvalue.RDFDatetime.FromSecondsSinceEpoch(0))

  def assertFlowLoggedRegex(
      self,
      client_id: str,
      flow_id: str,
      regex: Union[str, re.Pattern[str]],
  ) -> None:
    """Asserts that the flow logged a message matching the specified expression.

    Args:
      client_id: An identifier of the client of which flow we make an assertion.
      flow_id: An identifier of the flow on which me make an assertion.
      regex: A regex to match against the flow log messages.
    """
    del self  # Unused.

    assert data_store.REL_DB is not None

    if isinstance(regex, str):
      regex = re.compile(regex, re.IGNORECASE)

    logs = data_store.REL_DB.ReadFlowLogEntries(
        client_id,
        flow_id,
        offset=0,
        count=sys.maxsize,
    )
    for log in logs:
      if regex.search(log.message) is not None:
        return

    message = f"No logs matching {regex!r} for flow '{client_id}/{flow_id}'"
    raise AssertionError(message)


class CrashClientMock(action_mocks.ActionMock):
  """Client mock that simulates a client crash."""

  def __init__(self, client_id=None):
    self.client_id = client_id

  def HandleMessage(self, message):
    """Handle client messages."""

    crash_details = rdf_client.ClientCrash(
        client_id=self.client_id or message.session_id.Split()[0],
        session_id=message.session_id,
        crash_message="Client killed during transaction",
        timestamp=rdfvalue.RDFDatetime.Now())

    self.flow_id = message.session_id
    # This is normally done by the FrontEnd when a CLIENT_KILLED message is
    # received.
    events.Events.PublishEvent(
        "ClientCrash", crash_details, username="GRRFrontEnd")
    return []


class MockClient(object):
  """Simple emulation of the client.

  This implementation operates directly on the server's queue of client
  messages, bypassing the need to actually send the messages through the comms
  library.
  """

  def __init__(self, client_id, client_mock):
    if client_mock is None:
      client_mock = action_mocks.InvalidActionMock()
    else:
      precondition.AssertType(client_mock, action_mocks.ActionMock)

    self.client_id = client_id
    self.client_mock = client_mock

  def _PushHandlerMessage(self, message):
    """Pushes a message that goes to a message handler."""

    # We only accept messages of type MESSAGE.
    if message.type != rdf_flows.GrrMessage.Type.MESSAGE:
      raise ValueError("Unexpected message type: %s" % type(message))

    if not message.session_id:
      raise ValueError("Message without session_id: %s" % message)

    # Assume the message is authenticated and comes from this client.
    message.source = self.client_id

    message.auth_state = "AUTHENTICATED"
    session_id = message.session_id

    handler_name = message_handlers.session_id_map.get(session_id, None)
    if handler_name is None:
      raise ValueError("Unknown well known session id in msg %s" % message)

    logging.info("Running message handler: %s", handler_name)
    handler_cls = handler_registry.handler_name_map.get(handler_name)
    handler_request = rdf_objects.MessageHandlerRequest(
        client_id=self.client_id,
        handler_name=handler_name,
        request_id=message.response_id,
        request=message.payload)

    handler_cls().ProcessMessages([handler_request])

  def PushToStateQueue(self, message: rdf_flows.GrrMessage, **kw):
    """Push given message to the state queue."""
    # Assume the client is authorized
    message.auth_state = rdf_flows.GrrMessage.AuthorizationState.AUTHENTICATED

    # Update kw args
    for k, v in kw.items():
      setattr(message, k, v)

    # Handle well known flows
    if message.request_id == 0:
      self._PushHandlerMessage(message)
      return

    message = rdf_flow_objects.FlowResponseForLegacyResponse(message)
    if isinstance(message, rdf_flow_objects.FlowResponse):
      message = mig_flow_objects.ToProtoFlowResponse(message)
    if isinstance(message, rdf_flow_objects.FlowStatus):
      message = mig_flow_objects.ToProtoFlowStatus(message)
    if isinstance(message, rdf_flow_objects.FlowIterator):
      message = mig_flow_objects.ToProtoFlowIterator(message)
    data_store.REL_DB.WriteFlowResponses([message])

  def Next(self):
    """Emulates execution of a single client action request.

    Returns:
       True if a pending action request was found for the client.
    """
    next_task = fleetspeak_test_lib.PopMessage(self.client_id)
    if next_task is None:
      return False

    try:
      responses = self.client_mock.HandleMessage(next_task)
    except Exception as e:  # pylint: disable=broad-except
      logging.exception("Error %s occurred in client", e)
      responses = [
          self.client_mock.GenerateStatusMessage(
              next_task, 1, status="GENERIC_ERROR")
      ]

    # Now insert those on the flow state queue
    for response in responses:
      self.PushToStateQueue(response)

    return True


def StartFlow(
    flow_cls: type[flow_base.FlowBase],
    client_id: str,
    flow_args: Optional[rdf_structs.RDFStruct] = None,
    creator: Optional[str] = None,
    parent: Optional[flow.FlowParent] = None,
    output_plugins: Optional[
        Sequence[rdf_output_plugin.OutputPluginDescriptor]
    ] = None,
    network_bytes_limit: Optional[int] = None,
    cpu_limit: Optional[int] = None,
) -> str:
  """Starts (but not runs) a flow."""
  return flow.StartFlow(
      flow_cls=flow_cls,
      client_id=client_id,
      flow_args=flow_args,
      creator=creator,
      parent=parent,
      output_plugins=output_plugins,
      network_bytes_limit=network_bytes_limit,
      cpu_limit=cpu_limit,
      start_at=None,  # Start immediately.
  )


def StartAndRunFlow(
    flow_cls: type[flow_base.FlowBase],
    client_mock: Optional[action_mocks.ActionMock] = None,
    client_id: Optional[str] = None,
    creator: Optional[str] = None,
    check_flow_errors: bool = True,
    flow_args: Optional[rdf_structs.RDFStruct] = None,
    output_plugins: Optional[
        Sequence[rdf_output_plugin.OutputPluginDescriptor]
    ] = None,
    proto_output_plugins: Optional[
        Sequence[output_plugin_pb2.OutputPluginDescriptor]
    ] = None,
    network_bytes_limit: Optional[int] = None,
    cpu_limit: Optional[int] = None,
    runtime_limit: Optional[rdfvalue.Duration] = None,
) -> str:
  """Builds a test harness (client and worker), starts the flow and runs it.

  Args:
    flow_cls: Flow class that will be created and run.
    client_mock: Client mock object.
    client_id: Client id of an emulated client.
    creator: Username that requested this flow.
    check_flow_errors: If True, raise on errors during flow execution.
    flow_args: Flow args that will be passed to flow.StartFlow().
    output_plugins: List of output plugins that should be used for this flow.
    proto_output_plugins: List of output plugins that should be used for this
      flow.
    network_bytes_limit: Limit on the network traffic this flow can generated.
    cpu_limit: CPU limit in seconds for this flow.
    runtime_limit: Runtime limit as Duration for all ClientActions.

  Raises:
    RuntimeError: check_flow_errors was true and the flow raised an error in
    Start().

  Returns:
    The flow id of the flow that was run.
  """
  with TestWorker() as worker:
    flow_id = flow.StartFlow(
        flow_cls=flow_cls,
        client_id=client_id,
        creator=creator,
        flow_args=flow_args,
        output_plugins=output_plugins,
        proto_output_plugins=proto_output_plugins,
        network_bytes_limit=network_bytes_limit,
        cpu_limit=cpu_limit,
        runtime_limit=runtime_limit,
        start_at=None,
    )

    if check_flow_errors:
      flow_obj = data_store.REL_DB.ReadFlowObject(client_id, flow_id)
      if flow_obj.flow_state == flows_pb2.Flow.FlowState.ERROR:
        raise RuntimeError(
            "Flow %s on %s raised an error in state %s. \nError message: %s\n%s"
            % (
                flow_id,
                client_id,
                flow_obj.flow_state,
                flow_obj.error_message,
                flow_obj.backtrace,
            )
        )

    RunFlow(
        client_id,
        flow_id,
        client_mock=client_mock,
        check_flow_errors=check_flow_errors,
        worker=worker)
    return flow_id


class TestWorker(worker_lib.GRRWorker):
  """The same class as the real worker but logs all processed flows."""

  def __init__(self, *args, **kw):
    super().__init__(*args, **kw)
    self.processed_flows = []

  def ProcessFlow(
      self,
      flow_processing_request: flows_pb2.FlowProcessingRequest,
  ) -> None:
    key = (flow_processing_request.client_id, flow_processing_request.flow_id)
    self.processed_flows.append(key)
    super().ProcessFlow(flow_processing_request)

  def ResetProcessedFlows(self):
    processed_flows = self.processed_flows
    self.processed_flows = []
    return processed_flows

  def __enter__(self):
    data_store.REL_DB.RegisterFlowProcessingHandler(self.ProcessFlow)
    return self

  def __exit__(self, unused_type, unused_value, unused_traceback):
    data_store.REL_DB.UnregisterFlowProcessingHandler(
        timeout=rdfvalue.DurationSeconds(60)
    )
    self.Shutdown()


def RunFlow(client_id,
            flow_id,
            client_mock=None,
            worker=None,
            check_flow_errors=True):
  """Runs the flow given until no further progress can be made."""
  all_processed_flows = set()
  test_worker = None

  client_mock = MockClient(client_id, client_mock)

  try:
    if worker is None:
      test_worker = TestWorker()
      data_store.REL_DB.RegisterFlowProcessingHandler(test_worker.ProcessFlow)
    else:
      test_worker = worker

    # Run the client and worker until nothing changes any more.
    while True:
      client_processed = client_mock.Next()

      assert isinstance(data_store.REL_DB, db.DatabaseValidationWrapper)
      assert isinstance(data_store.REL_DB.delegate, mem.InMemoryDB)
      data_store.REL_DB.delegate.WaitUntilNoFlowsToProcess(
          timeout=rdfvalue.DurationSeconds(10)
      )
      worker_processed = test_worker.ResetProcessedFlows()
      all_processed_flows.update(worker_processed)

      # Exit the loop if no client actions were processed, nothing was processed
      # on the worker and there are no pending flow processing requests.
      if (
          client_processed == 0
          and not worker_processed
          and not data_store.REL_DB.ReadFlowProcessingRequests()
      ):
        break

    if check_flow_errors:
      for client_id, flow_id in all_processed_flows:
        flow_obj = data_store.REL_DB.ReadFlowObject(client_id, flow_id)
        if flow_obj.flow_state != flows_pb2.Flow.FlowState.FINISHED:
          raise RuntimeError(
              "Flow %s on %s completed in state %s (error message: %s %s)"
              % (
                  flow_id,
                  client_id,
                  flow_obj.flow_state,
                  flow_obj.error_message,
                  flow_obj.backtrace,
              )
          )

    return flow_id
  finally:
    if worker is None:
      data_store.REL_DB.UnregisterFlowProcessingHandler(
          timeout=rdfvalue.DurationSeconds(60)
      )
      # Test worker was created if no `worker` was provided.
      assert isinstance(test_worker, TestWorker)
      test_worker.Shutdown()


# TODO(user): Rename into GetFlowResultsPayloads.
def GetFlowResults(client_id, flow_id):
  """Gets flow results for a given flow.

  Args:
    client_id: String with a client id.
    flow_id: String with a flow_id.

  Returns:
    List with flow results payloads.
  """
  results = data_store.REL_DB.ReadFlowResults(client_id, flow_id, 0,
                                              sys.maxsize)
  return [mig_flow_objects.ToRDFFlowResult(r).payload for r in results]


def GetRawFlowResults(client_id: str,
                      flow_id: str) -> Iterable[rdf_flow_objects.FlowResult]:
  """Gets raw flow results for a given flow.

  Args:
    client_id: String with a client id.
    flow_id: String with a flow_id.

  Returns:
    Iterable with FlowResult objects read from the data store.
  """
  return [
      mig_flow_objects.ToRDFFlowResult(r)
      for r in data_store.REL_DB.ReadFlowResults(
          client_id, flow_id, 0, sys.maxsize
      )
  ]


def GetFlowResultsByTag(client_id, flow_id):
  precondition.AssertType(client_id, str)
  precondition.AssertType(flow_id, str)

  results = data_store.REL_DB.ReadFlowResults(client_id, flow_id, 0,
                                              sys.maxsize)
  results = [mig_flow_objects.ToRDFFlowResult(r) for r in results]
  return {r.tag or "": r.payload for r in results}


def FinishAllFlows(**kwargs):
  """Finishes all running flows on all clients (REL_DB-only)."""
  for client_id_batch in data_store.REL_DB.ReadAllClientIDs():
    for client_id in client_id_batch:
      FinishAllFlowsOnClient(client_id, **kwargs)


def FinishAllFlowsOnClient(client_id, **kwargs):
  """Finishes all running flows on a client."""
  for cur_flow in data_store.REL_DB.ReadAllFlowObjects(client_id=client_id):
    RunFlow(client_id, cur_flow.flow_id, **kwargs)


def GetFlowState(client_id, flow_id):
  proto_flow = data_store.REL_DB.ReadFlowObject(client_id, flow_id)
  rdf_flow = mig_flow_objects.ToRDFFlow(proto_flow)
  return rdf_flow.persistent_data


def GetFlowStore(client_id: str, flow_id: str) -> any_pb2.Any:
  proto_flow = data_store.REL_DB.ReadFlowObject(client_id, flow_id)
  return proto_flow.store


def GetFlowObj(client_id, flow_id):
  proto_flow = data_store.REL_DB.ReadFlowObject(client_id, flow_id)
  rdf_flow = mig_flow_objects.ToRDFFlow(proto_flow)
  return rdf_flow


def GetFlowProgress(client_id, flow_id):
  flow_obj = GetFlowObj(client_id, flow_id)
  flow_cls = registry.FlowRegistry.FlowClassByName(flow_obj.flow_class_name)
  return flow_cls(flow_obj).GetProgress()


def AddResultsToFlow(client_id: str,
                     flow_id: str,
                     payloads: Iterable[rdf_structs.RDFProtoStruct],
                     tag: Optional[str] = None) -> None:
  """Adds results with given payloads to a given flow."""
  data_store.REL_DB.WriteFlowResults(
      [
          mig_flow_objects.ToProtoFlowResult(
              rdf_flow_objects.FlowResult(
                  client_id=client_id, flow_id=flow_id, tag=tag, payload=payload
              )
          )
          for payload in payloads
      ]
  )


def OverrideFlowResultMetadataInFlow(
    client_id: str, flow_id: str, metadata: flows_pb2.FlowResultMetadata
) -> None:
  """Adds flow result metadata to a given flow."""
  flow_obj = data_store.REL_DB.ReadFlowObject(client_id, flow_id)
  flow_obj.result_metadata.CopyFrom(metadata)
  data_store.REL_DB.UpdateFlow(client_id, flow_id, flow_obj)


def FlowProgressOverride(
    flow_cls: type[flow_base.FlowBase], value: rdf_structs.RDFProtoStruct
) -> contextlib.AbstractContextManager[None]:
  """Returns a context manager overriding flow class's progress reporting."""
  return mock.patch.object(flow_cls, "GetProgress", return_value=value)


def MarkFlowAsFinished(client_id: str, flow_id: str) -> None:
  """Marks the given flow as finished without executing it."""
  data_store.REL_DB.UpdateFlow(
      client_id, flow_id, flow_state=flows_pb2.Flow.FlowState.FINISHED
  )


def MarkFlowAsFailed(client_id: str,
                     flow_id: str,
                     error_message: Optional[str] = None) -> None:
  """Marks the given flow as finished without executing it."""
  flow_obj = data_store.REL_DB.ReadFlowObject(client_id, flow_id)
  flow_obj.flow_state = flows_pb2.Flow.FlowState.ERROR
  if not flow_obj.HasField("error_message") and error_message:
    flow_obj.error_message = error_message
  data_store.REL_DB.UpdateFlow(
      client_id,
      flow_id,
      flow_obj,
  )


def ListAllFlows(client_id: str) -> list[flows_pb2.Flow]:
  """Returns all flows in the given client."""
  return data_store.REL_DB.ReadAllFlowObjects(client_id=client_id)
