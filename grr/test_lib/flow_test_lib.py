#!/usr/bin/env python
"""Helper classes for flows-related testing."""

import logging
import pdb
import sys


from builtins import range  # pylint: disable=redefined-builtin
from future.utils import iteritems

from grr_response_client.client_actions import standard

from grr_response_core.lib import flags
from grr_response_core.lib import rdfvalue
from grr_response_core.lib import registry
from grr_response_core.lib.rdfvalues import client as rdf_client
from grr_response_core.lib.rdfvalues import flows as rdf_flows
from grr_response_core.lib.rdfvalues import protodict as rdf_protodict
from grr_response_core.lib.rdfvalues import structs as rdf_structs
from grr_response_core.lib.util import precondition
from grr_response_proto import tests_pb2
from grr_response_server import aff4
from grr_response_server import data_store
from grr_response_server import events
from grr_response_server import flow
from grr_response_server import handler_registry
from grr_response_server import queue_manager
from grr_response_server import server_stubs
from grr_response_server import worker_lib
from grr_response_server.rdfvalues import flow_objects as rdf_flow_objects
from grr_response_server.rdfvalues import flow_runner as rdf_flow_runner
from grr_response_server.rdfvalues import objects as rdf_objects
from grr.test_lib import action_mocks
from grr.test_lib import client_test_lib

from grr.test_lib import test_lib
from grr.test_lib import worker_test_lib


class AdminOnlyFlow(flow.GRRFlow):
  AUTHORIZED_LABELS = ["admin"]

  # Flow has to have a category otherwise FullAccessControlManager won't
  # let non-supervisor users to run it at all (it will be considered
  # externally inaccessible).
  category = "/Test/"


class ClientFlowWithoutCategory(flow.GRRFlow):
  pass


class ClientFlowWithCategory(flow.GRRFlow):
  category = "/Test/"


class CPULimitFlow(flow.GRRFlow):
  """This flow is used to test the cpu limit."""

  def Start(self):
    self.CallClient(
        server_stubs.ClientActionStub.classes["Store"],
        string="Hey!",
        next_state="State1")

  def State1(self, responses):
    del responses
    self.CallClient(
        server_stubs.ClientActionStub.classes["Store"],
        string="Hey!",
        next_state="State2")

  def State2(self, responses):
    del responses
    self.CallClient(
        server_stubs.ClientActionStub.classes["Store"],
        string="Hey!",
        next_state="Done")

  def Done(self, responses):
    pass


class FlowWithOneClientRequest(flow.GRRFlow):
  """Test flow that does one client request in Start() state."""

  def Start(self):
    self.CallClient(client_test_lib.Test, data="test", next_state="End")


class FlowOrderTest(flow.GRRFlow):
  """Tests ordering of inbound messages."""

  def __init__(self, *args, **kwargs):
    self.messages = []
    flow.GRRFlow.__init__(self, *args, **kwargs)

  def Start(self):
    self.CallClient(client_test_lib.Test, data="test", next_state="Incoming")

  def Incoming(self, responses):
    """Record the message id for testing."""
    self.messages = []

    for r in responses:
      self.messages.append(r.integer)


class SendingFlowArgs(rdf_structs.RDFProtoStruct):
  protobuf = tests_pb2.SendingFlowArgs


class SendingFlow(flow.GRRFlow):
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


class RaiseOnStart(flow.GRRFlow):
  """A broken flow that raises in the Start method."""

  def Start(self):
    raise Exception("Broken Start")


class BrokenFlow(flow.GRRFlow):
  """A flow which does things wrongly."""

  def Start(self):
    """Send a message to an incorrect state."""
    self.CallClient(standard.ReadBuffer, next_state="WrongProcess")


class DummyFlow(flow.GRRFlow):
  """Dummy flow that does nothing."""


class FlowWithOneNestedFlow(flow.GRRFlow):
  """Flow that calls a nested flow."""

  def Start(self):
    self.CallFlow(DummyFlow.__name__, next_state="Done")

  def Done(self, responses=None):
    del responses


class DummyFlowWithSingleReply(flow.GRRFlow):
  """Just emits 1 reply."""

  def Start(self):
    self.CallState(next_state="SendSomething")

  def SendSomething(self, responses=None):
    del responses
    self.SendReply(rdfvalue.RDFString("oh"))


class DummyLogFlow(flow.GRRFlow):
  """Just emit logs."""

  def Start(self):
    """Log."""
    self.Log("First")
    self.CallFlow(DummyLogFlowChild.__name__, next_state="Done")
    self.Log("Second")

  def Done(self, responses=None):
    del responses
    self.Log("Third")
    self.Log("Fourth")


class DummyLogFlowChild(flow.GRRFlow):
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


class WellKnownSessionTest(flow.WellKnownFlow):
  """Tests the well known flow implementation."""
  well_known_session_id = rdfvalue.SessionID(
      queue=rdfvalue.RDFURN("test"), flow_name="TestSessionId")

  messages = []

  def __init__(self, *args, **kwargs):
    flow.WellKnownFlow.__init__(self, *args, **kwargs)

  def ProcessMessage(self, message):
    """Record the message id for testing."""
    self.messages.append(int(message.payload))


class WellKnownSessionTest2(WellKnownSessionTest):
  """Another testing well known flow."""
  well_known_session_id = rdfvalue.SessionID(
      queue=rdfvalue.RDFURN("test"), flow_name="TestSessionId2")


class FlowTestsBaseclass(test_lib.GRRBaseTest):
  """The base class for all flow tests."""

  def FlowSetup(self, name, client_id=None):
    if client_id is None:
      client_id = self.client_id

    session_id = flow.StartAFF4Flow(
        client_id=client_id, flow_name=name, token=self.token)

    return aff4.FACTORY.Open(session_id, mode="rw", token=self.token)

  def SendResponse(self,
                   session_id,
                   data,
                   client_id=None,
                   well_known=False,
                   request_id=None):
    if not isinstance(data, rdfvalue.RDFValue):
      data = rdf_protodict.DataBlob(string=data)
    if well_known:
      request_id, response_id = 0, 12345
    else:
      request_id, response_id = request_id or 1, 1
    with queue_manager.QueueManager(token=self.token) as flow_manager:
      flow_manager.QueueResponse(
          rdf_flows.GrrMessage(
              source=client_id,
              session_id=session_id,
              payload=data,
              request_id=request_id,
              auth_state="AUTHENTICATED",
              response_id=response_id))
      if not well_known:
        # For normal flows we have to send a status as well.
        flow_manager.QueueResponse(
            rdf_flows.GrrMessage(
                source=client_id,
                session_id=session_id,
                payload=rdf_flows.GrrStatus(
                    status=rdf_flows.GrrStatus.ReturnedStatus.OK),
                request_id=request_id,
                response_id=response_id + 1,
                auth_state="AUTHENTICATED",
                type=rdf_flows.GrrMessage.Type.STATUS))

      flow_manager.QueueNotification(
          session_id=session_id, last_status=request_id)
      timestamp = flow_manager.frozen_timestamp

    return timestamp


class CrashClientMock(action_mocks.ActionMock):
  """Client mock that simulates a client crash."""

  def __init__(self, client_id, token):
    self.client_id = client_id
    self.token = token

  def HandleMessage(self, message):
    """Handle client messages."""

    crash_details = rdf_client.ClientCrash(
        client_id=self.client_id,
        session_id=message.session_id,
        crash_message="Client killed during transaction",
        timestamp=rdfvalue.RDFDatetime.Now())

    self.flow_id = message.session_id
    # This is normally done by the FrontEnd when a CLIENT_KILLED message is
    # received.
    events.Events.PublishEvent("ClientCrash", crash_details, token=self.token)
    return []


class MockClient(object):
  """Simple emulation of the client.

  This implementation operates directly on the server's queue of client
  messages, bypassing the need to actually send the messages through the comms
  library.
  """

  def __init__(self, client_id, client_mock, token=None):
    if not isinstance(client_id, rdf_client.ClientURN):
      client_id = rdf_client.ClientURN(client_id)

    if client_mock is None:
      client_mock = action_mocks.InvalidActionMock()
    else:
      precondition.AssertType(client_mock, action_mocks.ActionMock)

    self._mock_task_queue = getattr(client_mock, "mock_task_queue", [])
    self.client_id = client_id
    self.client_mock = client_mock
    self.token = token

    # Well known flows are run on the front end.
    self.well_known_flows = flow.WellKnownFlow.GetAllWellKnownFlows(token=token)

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

    if data_store.RelationalDBReadEnabled("message_handlers"):
      handler_name = queue_manager.session_id_map.get(session_id, None)
      if handler_name is None:
        raise ValueError("Unknown well known session id in msg %s" % message)

      logging.info("Running message handler: %s", handler_name)
      handler_cls = handler_registry.handler_name_map.get(handler_name)
      handler_request = rdf_objects.MessageHandlerRequest(
          client_id=self.client_id.Basename(),
          handler_name=handler_name,
          request_id=message.response_id,
          request=message.payload)

      handler_cls(token=self.token).ProcessMessages([handler_request])
    else:
      logging.info("Running well known flow: %s", session_id)
      self.well_known_flows[session_id.FlowName()].ProcessMessage(message)

  def PushToStateQueue(self, manager, message, **kw):
    """Push given message to the state queue."""
    # Assume the client is authorized
    message.auth_state = rdf_flows.GrrMessage.AuthorizationState.AUTHENTICATED

    # Update kw args
    for k, v in iteritems(kw):
      setattr(message, k, v)

    # Handle well known flows
    if message.request_id == 0:
      self._PushHandlerMessage(message)
      return

    if data_store.RelationalDBFlowsEnabled():
      data_store.REL_DB.WriteFlowResponses(
          [rdf_flow_objects.FlowResponseForLegacyResponse(message)])
    else:
      manager.QueueResponse(message)

  def Next(self):
    """Grab tasks for us from the server's queue."""
    with queue_manager.QueueManager(token=self.token) as manager:
      request_tasks = manager.QueryAndOwn(
          self.client_id.Queue(), limit=1, lease_seconds=10000)

      request_tasks.extend(self._mock_task_queue)
      self._mock_task_queue[:] = []  # Clear the referenced list.

      for message in request_tasks:
        try:
          responses = self.client_mock.HandleMessage(message)
          logging.info("Called client action %s generating %s responses",
                       message.name,
                       len(responses) + 1)
        except Exception as e:  # pylint: disable=broad-except
          logging.exception("Error %s occurred in client", e)
          responses = [
              self.client_mock.GenerateStatusMessage(
                  message, 1, status="GENERIC_ERROR")
          ]

        # Now insert those on the flow state queue
        for response in responses:
          self.PushToStateQueue(manager, response)

        # Additionally schedule a task for the worker
        manager.QueueNotification(session_id=message.session_id)

      return len(request_tasks)


def CheckFlowErrors(total_flows, token=None):
  """Checks that all the flows are complete."""
  for session_id in total_flows:
    try:
      flow_obj = aff4.FACTORY.Open(
          session_id, aff4_type=flow.GRRFlow, mode="r", token=token)
    except IOError:
      continue

    if flow_obj.context.state != rdf_flow_runner.FlowContext.State.TERMINATED:
      if flags.FLAGS.debug:
        pdb.set_trace()
      raise RuntimeError(
          "Flow %s completed in state %s" % (flow_obj.runner_args.flow_name,
                                             flow_obj.context.state))


def TestFlowHelper(flow_urn_or_cls_name,
                   client_mock=None,
                   client_id=None,
                   check_flow_errors=True,
                   token=None,
                   sync=True,
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
    token: Security token.
    sync: Whether StartAFF4Flow call should be synchronous or not.
    **kwargs: Arbitrary args that will be passed to flow.StartAFF4Flow().

  Returns:
    The session id of the flow that was run.
  """

  if data_store.RelationalDBFlowsEnabled():
    flow_cls = registry.FlowRegistry.FlowClassByName(flow_urn_or_cls_name)
    return StartAndRunFlow(
        flow_cls,
        creator=token.username,
        client_mock=client_mock,
        client_id=client_id.Basename(),
        check_flow_errors=check_flow_errors,
        flow_args=kwargs.pop("args", None),
        **kwargs)

  if client_id or client_mock:
    client_mock = MockClient(client_id, client_mock, token=token)

  worker_mock = worker_test_lib.MockWorker(
      check_flow_errors=check_flow_errors, token=token)

  if isinstance(flow_urn_or_cls_name, rdfvalue.RDFURN):
    session_id = flow_urn_or_cls_name
  else:
    # Instantiate the flow:
    session_id = flow.StartAFF4Flow(
        client_id=client_id,
        flow_name=flow_urn_or_cls_name,
        sync=sync,
        token=token,
        **kwargs)

  total_flows = set()
  total_flows.add(session_id)

  # Run the client and worker until nothing changes any more.
  while True:
    if client_mock:
      client_processed = client_mock.Next()
    else:
      client_processed = 0

    flows_run = []
    for flow_run in worker_mock.Next():
      total_flows.add(flow_run)
      flows_run.append(flow_run)

    if client_processed == 0 and not flows_run:
      break

  # We should check for flow errors:
  if check_flow_errors:
    CheckFlowErrors(total_flows, token=token)

  return session_id


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

  Returns:
    The session id of the flow that was run.
  """
  worker = TestWorker(token=True)
  data_store.REL_DB.RegisterFlowProcessingHandler(worker.ProcessFlow)

  flow_id = flow.StartFlow(flow_cls=flow_cls, client_id=client_id, **kwargs)

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
    super(TestWorker, self).__init__(*args, **kw)
    self.processed_flows = []

  def ProcessFlow(self, flow_processing_request):
    key = (flow_processing_request.client_id, flow_processing_request.flow_id)
    self.processed_flows.append(key)
    super(TestWorker, self).ProcessFlow(flow_processing_request)

  def ResetProcessedFlows(self):
    processed_flows = self.processed_flows
    self.processed_flows = []
    return processed_flows


def RunFlow(client_id,
            flow_id,
            client_mock=None,
            worker=None,
            check_flow_errors=True):
  """Runs the flow given until no further progress can be made."""

  all_processed_flows = set()

  if client_id or client_mock:
    client_mock = MockClient(client_id, client_mock)

  if worker is None:
    worker = TestWorker(token=True)
    data_store.REL_DB.RegisterFlowProcessingHandler(worker.ProcessFlow)

  # Run the client and worker until nothing changes any more.
  while True:
    client_processed = client_mock.Next()
    worker_processed = worker.ResetProcessedFlows()
    all_processed_flows.update(worker_processed)

    if client_processed == 0 and not worker_processed:
      break

  if check_flow_errors:
    for client_id, flow_id in all_processed_flows:
      rdf_flow = data_store.REL_DB.ReadFlowObject(client_id, flow_id)
      if rdf_flow.flow_state != rdf_flow.FlowState.FINISHED:
        raise RuntimeError(
            "Flow %s on %s completed in state %s (error message: %s)" %
            (flow_id, client_id, unicode(rdf_flow.flow_state),
             rdf_flow.error_message))

  return flow_id


def GetFlowResults(client_id, flow_id):
  """Gets flow results for a given flow.

  Args:
    client_id: String with a client id or a ClientURN.
    flow_id: String with a flow_id or an URN.

  Returns:
    List with flow results values (i.e. with payloads).
  """
  if isinstance(client_id, rdfvalue.RDFURN):
    client_id = client_id.Basename()

  if isinstance(flow_id, rdfvalue.RDFURN):
    flow_id = flow_id.Basename()

  if not data_store.RelationalDBFlowsEnabled():
    coll = flow.GRRFlow.ResultCollectionForFID(
        rdf_client.ClientURN(client_id).Add("flows").Add(flow_id))
    return list(coll.GenerateItems())
  else:
    results = data_store.REL_DB.ReadFlowResults(client_id, flow_id, 0,
                                                sys.maxsize)
    return [r.payload for r in results]


def GetFlowResultsByTag(client_id, flow_id):
  precondition.AssertType(client_id, unicode)
  precondition.AssertType(flow_id, unicode)

  results = data_store.REL_DB.ReadFlowResults(client_id, flow_id, 0,
                                              sys.maxsize)
  return {r.tag or "": r.payload for r in results}
