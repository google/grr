#!/usr/bin/env python
"""Helper classes for flows-related testing."""

import itertools
import logging
import pdb
import traceback

from grr_response_client.client_actions import standard

from grr.lib import flags
from grr.lib import rdfvalue
from grr.lib import registry
from grr.lib.rdfvalues import client as rdf_client
from grr.lib.rdfvalues import flows as rdf_flows
from grr.lib.rdfvalues import objects as rdf_objects
from grr.lib.rdfvalues import protodict as rdf_protodict
from grr.lib.rdfvalues import structs as rdf_structs
from grr_response_proto import tests_pb2
from grr.server.grr_response_server import aff4
from grr.server.grr_response_server import events
from grr.server.grr_response_server import flow
from grr.server.grr_response_server import handler_registry
from grr.server.grr_response_server import queue_manager
from grr.server.grr_response_server import server_stubs
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

  @flow.StateHandler()
  def Start(self):
    self.CallClient(
        server_stubs.ClientActionStub.classes["Store"],
        string="Hey!",
        next_state="State1")

  @flow.StateHandler()
  def State1(self):
    self.CallClient(
        server_stubs.ClientActionStub.classes["Store"],
        string="Hey!",
        next_state="State2")

  @flow.StateHandler()
  def State2(self):
    self.CallClient(
        server_stubs.ClientActionStub.classes["Store"],
        string="Hey!",
        next_state="Done")

  @flow.StateHandler()
  def Done(self, responses):
    pass


class FlowWithOneClientRequest(flow.GRRFlow):
  """Test flow that does one client request in Start() state."""

  @flow.StateHandler()
  def Start(self, unused_message=None):
    self.CallClient(client_test_lib.Test, data="test", next_state="End")


class FlowOrderTest(flow.GRRFlow):
  """Tests ordering of inbound messages."""

  def __init__(self, *args, **kwargs):
    self.messages = []
    flow.GRRFlow.__init__(self, *args, **kwargs)

  @flow.StateHandler()
  def Start(self, unused_message=None):
    self.CallClient(client_test_lib.Test, data="test", next_state="Incoming")

  @flow.StateHandler()
  def Incoming(self, responses):
    """Record the message id for testing."""
    self.messages = []

    for _ in responses:
      self.messages.append(responses.message.response_id)


class SendingFlowArgs(rdf_structs.RDFProtoStruct):
  protobuf = tests_pb2.SendingFlowArgs


class SendingFlow(flow.GRRFlow):
  """Tests sending messages to clients."""
  args_type = SendingFlowArgs

  # Flow has to have a category otherwise FullAccessControlManager won't
  # let non-supervisor users to run it at all (it will be considered
  # externally inaccessible).
  category = "/Test/"

  @flow.StateHandler()
  def Start(self, unused_response=None):
    """Just send a few messages."""
    for unused_i in range(0, self.args.message_count):
      self.CallClient(
          standard.ReadBuffer, offset=0, length=100, next_state="Process")


class RaiseOnStart(flow.GRRFlow):
  """A broken flow that raises in the Start method."""

  @flow.StateHandler()
  def Start(self, unused_message=None):
    raise Exception("Broken Start")


class BrokenFlow(flow.GRRFlow):
  """A flow which does things wrongly."""

  @flow.StateHandler()
  def Start(self, unused_response=None):
    """Send a message to an incorrect state."""
    self.CallClient(standard.ReadBuffer, next_state="WrongProcess")


class DummyFlow(flow.GRRFlow):
  """Dummy flow that does nothing."""


class FlowWithOneNestedFlow(flow.GRRFlow):
  """Flow that calls a nested flow."""

  @flow.StateHandler()
  def Start(self, unused_response=None):
    self.CallFlow(DummyFlow.__name__, next_state="Done")

  @flow.StateHandler()
  def Done(self, unused_response=None):
    pass


class DummyFlowWithSingleReply(flow.GRRFlow):
  """Just emits 1 reply."""

  @flow.StateHandler()
  def Start(self, unused_response=None):
    self.CallState(next_state="SendSomething")

  @flow.StateHandler()
  def SendSomething(self, unused_response=None):
    self.SendReply(rdfvalue.RDFString("oh"))


class DummyLogFlow(flow.GRRFlow):
  """Just emit logs."""

  @flow.StateHandler()
  def Start(self, unused_response=None):
    """Log."""
    self.Log("First")
    self.CallFlow(DummyLogFlowChild.__name__, next_state="Done")
    self.Log("Second")

  @flow.StateHandler()
  def Done(self, unused_response=None):
    self.Log("Third")
    self.Log("Fourth")


class DummyLogFlowChild(flow.GRRFlow):
  """Just emit logs."""

  @flow.StateHandler()
  def Start(self, unused_response=None):
    """Log."""
    self.Log("Uno")
    self.CallState(next_state="Done")
    self.Log("Dos")

  @flow.StateHandler()
  def Done(self, unused_response=None):
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

  __metaclass__ = registry.MetaclassRegistry

  def FlowSetup(self, name, client_id=None):
    if client_id is None:
      client_id = self.client_id

    session_id = flow.GRRFlow.StartFlow(
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


class CrashClientMock(object):

  STATUS_MESSAGE_ENFORCED = False

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

    self.status_message_enforced = getattr(client_mock,
                                           "STATUS_MESSAGE_ENFORCED", True)
    self._mock_task_queue = getattr(client_mock, "mock_task_queue", [])
    self.client_id = client_id
    self.client_mock = client_mock
    self.token = token

    # Well known flows are run on the front end.
    self.well_known_flows = flow.WellKnownFlow.GetAllWellKnownFlows(token=token)
    self.user_cpu_usage = []
    self.system_cpu_usage = []
    self.network_usage = []

  def EnableResourceUsage(self,
                          user_cpu_usage=None,
                          system_cpu_usage=None,
                          network_usage=None):
    if user_cpu_usage:
      self.user_cpu_usage = itertools.cycle(user_cpu_usage)
    if system_cpu_usage:
      self.system_cpu_usage = itertools.cycle(system_cpu_usage)
    if network_usage:
      self.network_usage = itertools.cycle(network_usage)

  def AddResourceUsage(self, status):
    """Register resource usage for a given status."""

    if self.user_cpu_usage or self.system_cpu_usage:
      status.cpu_time_used = rdf_client.CpuSeconds(
          user_cpu_time=self.user_cpu_usage.next(),
          system_cpu_time=self.system_cpu_usage.next())
    if self.network_usage:
      status.network_bytes_sent = self.network_usage.next()

  def PushToStateQueue(self, manager, message, **kw):
    """Push given message to the state queue."""

    # Assume the client is authorized
    message.auth_state = rdf_flows.GrrMessage.AuthorizationState.AUTHENTICATED

    # Update kw args
    for k, v in kw.items():
      setattr(message, k, v)

    # Handle well known flows
    if message.request_id == 0:

      # Well known flows only accept messages of type MESSAGE.
      if message.type == rdf_flows.GrrMessage.Type.MESSAGE:
        # Assume the message is authenticated and comes from this client.
        message.source = self.client_id

        message.auth_state = "AUTHENTICATED"

        session_id = message.session_id
        if session_id:
          handler_name = queue_manager.session_id_map.get(session_id)
          if handler_name:
            logging.info("Running message handler: %s", handler_name)
            handler_cls = handler_registry.handler_name_map.get(handler_name)
            handler_request = rdf_objects.MessageHandlerRequest(
                client_id=self.client_id.Basename(),
                handler_name=handler_name,
                request_id=message.response_id,
                request=message.payload)

            handler_cls(token=self.token).ProcessMessages(handler_request)
          else:
            logging.info("Running well known flow: %s", session_id)
            self.well_known_flows[session_id.FlowName()].ProcessMessage(message)

      return

    manager.QueueResponse(message)

  def Next(self):
    """Grab tasks for us from the server's queue."""
    with queue_manager.QueueManager(token=self.token) as manager:
      request_tasks = manager.QueryAndOwn(
          self.client_id.Queue(), limit=1, lease_seconds=10000)

      request_tasks.extend(self._mock_task_queue)
      self._mock_task_queue[:] = []  # Clear the referenced list.

      for message in request_tasks:
        status = None
        response_id = 1

        # Collect all responses for this message from the client mock
        try:
          if hasattr(self.client_mock, "HandleMessage"):
            responses = self.client_mock.HandleMessage(message)
          else:
            self.client_mock.message = message
            responses = getattr(self.client_mock, message.name)(message.payload)

          if not responses:
            responses = []

          logging.info("Called client action %s generating %s responses",
                       message.name,
                       len(responses) + 1)

          if self.status_message_enforced:
            status = rdf_flows.GrrStatus()
        except Exception as e:  # pylint: disable=broad-except
          logging.exception("Error %s occurred in client", e)

          # Error occurred.
          responses = []
          if self.status_message_enforced:
            error_message = str(e)
            status = rdf_flows.GrrStatus(
                status=rdf_flows.GrrStatus.ReturnedStatus.GENERIC_ERROR)
            # Invalid action mock is usually expected.
            if error_message != "Invalid Action Mock.":
              status.backtrace = traceback.format_exc()
              status.error_message = error_message

        # Now insert those on the flow state queue
        for response in responses:
          if isinstance(response, rdf_flows.GrrStatus):
            msg_type = rdf_flows.GrrMessage.Type.STATUS
            self.AddResourceUsage(response)
            response = rdf_flows.GrrMessage(
                session_id=message.session_id,
                name=message.name,
                response_id=response_id,
                request_id=message.request_id,
                payload=response,
                type=msg_type)
          elif isinstance(response, rdf_client.Iterator):
            msg_type = rdf_flows.GrrMessage.Type.ITERATOR
            response = rdf_flows.GrrMessage(
                session_id=message.session_id,
                name=message.name,
                response_id=response_id,
                request_id=message.request_id,
                payload=response,
                type=msg_type)
          elif not isinstance(response, rdf_flows.GrrMessage):
            msg_type = rdf_flows.GrrMessage.Type.MESSAGE
            response = rdf_flows.GrrMessage(
                session_id=message.session_id,
                name=message.name,
                response_id=response_id,
                request_id=message.request_id,
                payload=response,
                type=msg_type)

          # Next expected response
          response_id = response.response_id + 1
          self.PushToStateQueue(manager, response)

        # Status may only be None if the client reported itself as crashed.
        if status is not None:
          self.AddResourceUsage(status)
          self.PushToStateQueue(
              manager,
              message,
              response_id=response_id,
              payload=status,
              type=rdf_flows.GrrMessage.Type.STATUS)
        else:
          # Status may be None only if status_message_enforced is False.
          if self.status_message_enforced:
            raise RuntimeError("status message can only be None when "
                               "status_message_enforced is False")

        # Additionally schedule a task for the worker
        manager.QueueNotification(
            session_id=message.session_id, priority=message.priority)

      return len(request_tasks)


def CheckFlowErrors(total_flows, token=None):
  # Check that all the flows are complete.
  for session_id in total_flows:
    try:
      flow_obj = aff4.FACTORY.Open(
          session_id, aff4_type=flow.GRRFlow, mode="r", token=token)
    except IOError:
      continue

    if flow_obj.context.state != rdf_flows.FlowContext.State.TERMINATED:
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
                          given flow will be run) or flow class name (in this
                          case flow of the given class will be created and run).
    client_mock: Client mock object.
    client_id: Client id of an emulated client.
    check_flow_errors: If True, TestFlowHelper will raise on errors during flow
                       execution.
    token: Security token.
    sync: Whether StartFlow call should be synchronous or not.
    **kwargs: Arbitrary args that will be passed to flow.GRRFlow.StartFlow().
  Returns:
    The session id of the flow that was run.
  """
  if client_id or client_mock:
    client_mock = MockClient(client_id, client_mock, token=token)

  worker_mock = worker_test_lib.MockWorker(
      check_flow_errors=check_flow_errors, token=token)

  if isinstance(flow_urn_or_cls_name, rdfvalue.RDFURN):
    session_id = flow_urn_or_cls_name
  else:
    # Instantiate the flow:
    session_id = flow.GRRFlow.StartFlow(
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
