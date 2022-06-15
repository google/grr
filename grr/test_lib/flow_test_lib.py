#!/usr/bin/env python
"""Helper classes for flows-related testing."""

import logging
import sys
from typing import ContextManager, Iterable, Optional, Text, Type, List
from unittest import mock

from grr_response_client.client_actions import standard

from grr_response_core.lib import rdfvalue
from grr_response_core.lib import registry
from grr_response_core.lib.rdfvalues import client as rdf_client
from grr_response_core.lib.rdfvalues import flows as rdf_flows
from grr_response_core.lib.rdfvalues import structs as rdf_structs
from grr_response_core.lib.util import precondition
from grr_response_proto import tests_pb2
from grr_response_server import action_registry
from grr_response_server import data_store
from grr_response_server import events
from grr_response_server import fleetspeak_connector
from grr_response_server import fleetspeak_utils
from grr_response_server import flow
from grr_response_server import flow_base
from grr_response_server import handler_registry
from grr_response_server import message_handlers
from grr_response_server import server_stubs
from grr_response_server import worker_lib
from grr_response_server.rdfvalues import flow_objects as rdf_flow_objects
from grr_response_server.rdfvalues import objects as rdf_objects
from grr.test_lib import action_mocks
from grr.test_lib import client_test_lib
from grr.test_lib import fleetspeak_test_lib
from grr.test_lib import test_lib


class InfiniteFlow(flow_base.FlowBase):
  """Flow that never ends."""

  def Start(self):
    self.CallClient(server_stubs.GetFileStat, next_state="NextState")

  def NextState(self, responses):
    _ = responses
    self.CallClient(server_stubs.GetFileStat, next_state="NextStateAgain")

  def NextStateAgain(self, responses):
    _ = responses
    self.CallClient(server_stubs.GetFileStat, next_state="NextState")


class ClientFlowWithoutCategory(flow_base.FlowBase):
  pass


class ClientFlowWithCategory(flow_base.FlowBase):
  category = "/Test/"


class CPULimitFlow(flow_base.FlowBase):
  """This flow is used to test the cpu limit."""

  def Start(self):
    self.CallClient(
        action_registry.ACTION_STUB_BY_ID["Store"],
        string="Hey!",
        next_state="State1")

  def State1(self, responses):
    del responses
    self.CallClient(
        action_registry.ACTION_STUB_BY_ID["Store"],
        string="Hey!",
        next_state="State2")

  def State2(self, responses):
    del responses
    self.CallClient(
        action_registry.ACTION_STUB_BY_ID["Store"],
        string="Hey!",
        next_state="Done")

  def Done(self, responses):
    pass


class FlowWithOneClientRequest(flow_base.FlowBase):
  """Test flow that does one client request in Start() state."""

  def Start(self):
    self.CallClient(client_test_lib.Test, data=b"test", next_state="End")


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
          standard.ReadBuffer, offset=0, length=100, next_state="Process")


class RaiseOnStart(flow_base.FlowBase):
  """A broken flow that raises in the Start method."""

  def Start(self):
    raise Exception("Broken Start")


class BrokenFlow(flow_base.FlowBase):
  """A flow which does things wrongly."""

  def Start(self):
    """Send a message to an incorrect state."""
    self.CallClient(standard.ReadBuffer, next_state="WrongProcess")


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
    self.CallClient(server_stubs.GetFileStat, next_state="NextState")

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


class FlowTestsBaseclass(test_lib.GRRBaseTest):
  """The base class for all flow tests."""

  def setUp(self):
    super().setUp()

    # Set up emulation for an in-memory Fleetspeak service.
    conn_patcher = mock.patch.object(fleetspeak_connector, "CONN")
    mock_conn = conn_patcher.start()
    self.addCleanup(conn_patcher.stop)
    mock_conn.outgoing.InsertMessage.side_effect = (
        lambda msg, **_: fleetspeak_test_lib.StoreMessage(msg))


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
    self._is_fleetspeak_client = fleetspeak_utils.IsFleetspeakEnabledClient(
        client_id)

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

  def PushToStateQueue(self, message, **kw):
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

    data_store.REL_DB.WriteFlowResponses(
        [rdf_flow_objects.FlowResponseForLegacyResponse(message)])

  def Next(self):
    """Emulates execution of a single ClientActionRequest.

    Returns:
       True iff a ClientActionRequest was found for the client.
    """
    if self._is_fleetspeak_client:
      next_task = fleetspeak_test_lib.PopMessage(self.client_id)
      if next_task is None:
        return False
    else:
      request = data_store.REL_DB.LeaseClientActionRequests(
          self.client_id,
          lease_time=rdfvalue.Duration.From(10000, rdfvalue.SECONDS),
          limit=1)
      try:
        next_task = rdf_flow_objects.GRRMessageFromClientActionRequest(
            request[0])
      except IndexError:
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


def TestFlowHelper(flow_urn_or_cls_name,
                   client_mock=None,
                   client_id=None,
                   check_flow_errors=True,
                   creator=None,
                   **kwargs):
  """Build a full test harness: client - worker + start flow.

  Args:
    flow_urn_or_cls_name: RDFURN pointing to existing flow (in this case the
      given flow will be run) or flow class name (in this case flow of the given
      class will be created and run).
    client_mock: Client mock object.
    client_id: Client id of an emulated client.
    check_flow_errors: If True, TestFlowHelper will raise on errors during flow
      execution.
    creator: Username of the flow creator.
    **kwargs: Arbitrary args that will be passed to flow.StartFlow().

  Returns:
    The session id of the flow that was run.
  """
  flow_cls = registry.FlowRegistry.FlowClassByName(flow_urn_or_cls_name)

  return StartAndRunFlow(
      flow_cls,
      creator=creator,
      client_mock=client_mock,
      client_id=client_id,
      check_flow_errors=check_flow_errors,
      flow_args=kwargs.pop("args", None),
      **kwargs)


def StartFlow(flow_cls, client_id=None, flow_args=None, creator=None, **kwargs):
  """Starts (but not runs) a flow."""
  try:
    del kwargs["notify_to_user"]
  except KeyError:
    pass

  return flow.StartFlow(
      flow_cls=flow_cls,
      client_id=client_id,
      flow_args=flow_args,
      creator=creator,
      **kwargs)


def StartAndRunFlow(flow_cls,
                    client_mock=None,
                    client_id=None,
                    check_flow_errors=True,
                    **kwargs):
  """Builds a test harness (client and worker), starts the flow and runs it.

  Args:
    flow_cls: Flow class that will be created and run.
    client_mock: Client mock object.
    client_id: Client id of an emulated client.
    check_flow_errors: If True, raise on errors during flow execution.
    **kwargs: Arbitrary args that will be passed to flow.StartFlow().

  Raises:
    RuntimeError: check_flow_errors was true and the flow raised an error in
    Start().

  Returns:
    The session id of the flow that was run.
  """
  with TestWorker() as worker:
    flow_id = flow.StartFlow(flow_cls=flow_cls, client_id=client_id, **kwargs)

    if check_flow_errors:
      rdf_flow = data_store.REL_DB.ReadFlowObject(client_id, flow_id)
      if rdf_flow.flow_state == rdf_flow.FlowState.ERROR:
        raise RuntimeError(
            "Flow %s on %s raised an error in state %s. \nError message: %s\n%s"
            % (flow_id, client_id, rdf_flow.flow_state, rdf_flow.error_message,
               rdf_flow.backtrace))

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

  def ProcessFlow(self, flow_processing_request):
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
    data_store.REL_DB.UnregisterFlowProcessingHandler(timeout=60)
    self.Shutdown()


def RunFlow(client_id,
            flow_id,
            client_mock=None,
            worker=None,
            check_flow_errors=True):
  """Runs the flow given until no further progress can be made."""
  all_processed_flows = set()

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
      worker_processed = test_worker.ResetProcessedFlows()
      all_processed_flows.update(worker_processed)

      if client_processed == 0 and not worker_processed:
        break

    if check_flow_errors:
      for client_id, flow_id in all_processed_flows:
        rdf_flow = data_store.REL_DB.ReadFlowObject(client_id, flow_id)
        if rdf_flow.flow_state != rdf_flow.FlowState.FINISHED:
          raise RuntimeError(
              "Flow %s on %s completed in state %s (error message: %s %s)" %
              (flow_id, client_id, rdf_flow.flow_state, rdf_flow.error_message,
               rdf_flow.backtrace))

    return flow_id
  finally:
    if worker is None:
      data_store.REL_DB.UnregisterFlowProcessingHandler(timeout=60)
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
  return [r.payload for r in results]


def GetRawFlowResults(client_id: str,
                      flow_id: str) -> Iterable[rdf_flow_objects.FlowResult]:
  """Gets raw flow results for a given flow.

  Args:
    client_id: String with a client id.
    flow_id: String with a flow_id.

  Returns:
    Iterable with FlowResult objects read from the data store.
  """
  return data_store.REL_DB.ReadFlowResults(client_id, flow_id, 0, sys.maxsize)


def GetFlowResultsByTag(client_id, flow_id):
  precondition.AssertType(client_id, Text)
  precondition.AssertType(flow_id, Text)

  results = data_store.REL_DB.ReadFlowResults(client_id, flow_id, 0,
                                              sys.maxsize)
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
  rdf_flow = data_store.REL_DB.ReadFlowObject(client_id, flow_id)
  return rdf_flow.persistent_data


def GetFlowObj(client_id, flow_id):
  rdf_flow = data_store.REL_DB.ReadFlowObject(client_id, flow_id)
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
  data_store.REL_DB.WriteFlowResults([
      rdf_flow_objects.FlowResult(
          client_id=client_id, flow_id=flow_id, tag=tag, payload=payload)
      for payload in payloads
  ])


def FlowProgressOverride(
    flow_cls: Type[flow_base.FlowBase],
    value: rdf_structs.RDFProtoStruct) -> ContextManager[None]:
  """Returns a context manager overriding flow class's progress reporting."""
  return mock.patch.object(flow_cls, "GetProgress", return_value=value)


def FlowResultMetadataOverride(
    flow_cls: Type[flow_base.FlowBase],
    value: rdf_flow_objects.FlowResultMetadata) -> ContextManager[None]:
  """Returns a context manager overriding flow class's result metadata."""
  return mock.patch.object(
      flow_cls,
      flow_base.FlowBase.GetResultMetadata.__name__,
      return_value=value)


def MarkFlowAsFinished(client_id: str, flow_id: str) -> None:
  """Marks the given flow as finished without executing it."""
  flow_obj = data_store.REL_DB.ReadFlowObject(client_id, flow_id)
  flow_obj.flow_state = flow_obj.FlowState.FINISHED
  data_store.REL_DB.WriteFlowObject(flow_obj)


def MarkFlowAsFailed(client_id: str,
                     flow_id: str,
                     error_message: Optional[str] = None) -> None:
  """Marks the given flow as finished without executing it."""
  flow_obj = data_store.REL_DB.ReadFlowObject(client_id, flow_id)
  flow_obj.flow_state = flow_obj.FlowState.ERROR
  if error_message is not None:
    flow_obj.error_message = error_message
  data_store.REL_DB.WriteFlowObject(flow_obj)


def ListAllFlows(client_id: str) -> List[rdf_flow_objects.Flow]:
  """Returns all flows in the given client."""
  return data_store.REL_DB.ReadAllFlowObjects(client_id=client_id)
