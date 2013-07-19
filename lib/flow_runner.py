#!/usr/bin/env python
# Copyright 2011 Google Inc. All Rights Reserved.
"""This file contains a helper class for the flows.

This flow context class provides all the methods for handling flows (i.e.,
calling clients, changing state, ...).
"""


import threading
import time
import traceback


import logging
from grr.client import actions
from grr.lib import config_lib
from grr.lib import data_store
from grr.lib import rdfvalue
from grr.lib import scheduler
from grr.lib import stats
from grr.lib import utils

config_lib.DEFINE_integer("Worker.hunt_ping_interval", 60,
                          "Time interval between hunt's lease extensions.")


class FlowRunnerError(Exception):
  """Raised when there is an error during state transitions."""


class MoreDataException(Exception):
  """Raised when there is more data available."""


class HuntRunner(object):
  """The flow context class for hunts.

  This is essentially the same as a normal context but it processes
  all the requests that arrive regardless of any order such that one client that
  doesn't respond does not make the whole hunt wait.
  """

  process_requests_in_order = False
  flow_manager = None

  def __init__(self, flow_obj, flow_manager=None, _store=None, token=None):
    """Constructor for the HuntRunner.

    Args:
      flow_obj: The flow object this runner will run states for.
      flow_manager: The flow_manager to use.
      _store: An optional data store to use. (Usually only used in tests).
      token: An instance of access_control.ACLToken security token.
    """
    self.token = token or flow_obj.token
    self.data_store = _store or data_store.DB

    self.flow_manager = flow_manager or FlowManager(token=self.token,
                                                    store=self.data_store)
    self.outbound_lock = threading.Lock()
    self.flow_obj = flow_obj
    # Copy some data locally for easier access.
    self.context = self.flow_obj.GetContext()
    self.session_id = self.context.session_id
    self.client_id = self.context.get("client_id", None)

  def SetAllowedFollowUpStates(self, next_states):
    self.next_states = next_states

  def CallState(self, messages=None, next_state="", delay=0):
    """This method is used to schedule a new state on a different worker.

    This is basically the same as CallFlow() except we are calling
    ourselves. The state will be invoked in a later time and receive all the
    messages we send.

    Args:
       messages: A list of rdfvalues to send. If the last one is not a
            GrrStatus, we append an OK Status.
       next_state: The state in this flow to be invoked with the responses.
       delay: Delay the call to the next state by <delay> seconds.

    Raises:
       FlowRunnerError: if the next state is not valid.
    """
    if messages is None:
      messages = []

    # Check if the state is valid
    if not getattr(self.flow_obj, next_state):
      raise FlowRunnerError("Next state %s is invalid.")

    # Queue the response message to the parent flow
    request_state = rdfvalue.RequestState(id=self.GetNextOutboundId(),
                                          session_id=self.session_id,
                                          client_id=self.client_id,
                                          next_state=next_state)

    self.QueueRequest(request_state)

    # Add the status message if needed.
    if not messages or not isinstance(messages[-1], rdfvalue.GrrStatus):
      messages.append(rdfvalue.GrrStatus())

    # Send all the messages
    for i, payload in enumerate(messages):
      if isinstance(payload, rdfvalue.RDFValue):
        msg = rdfvalue.GrrMessage(
            session_id=self.session_id, request_id=request_state.id,
            response_id=1+i,
            auth_state=rdfvalue.GrrMessage.AuthorizationState.AUTHENTICATED,
            payload=payload,
            type=rdfvalue.GrrMessage.Type.MESSAGE)

        if isinstance(payload, rdfvalue.GrrStatus):
          msg.type = rdfvalue.GrrMessage.Type.STATUS

      self.QueueResponse(msg)

    # Notify the worker about it.
    timestamp = None
    if delay:
      timestamp = int((time.time() + delay) * 1e6)
    self.QueueNotification(self.session_id,
                           timestamp=timestamp)

  def ProcessCompletedRequests(self, thread_pool):
    """Go through the list of requests and process the completed ones.

    We take a snapshot in time of all requests and responses for this flow. We
    then process as many completed requests as possible. If responses are not
    quite here we leave it for next time.

    It is safe to call this function as many times as needed. NOTE: We assume
    that the flow queue is locked so another worker is not processing these
    messages while we are. It is safe to insert new messages to the flow:state
    queue.

    Args:
      thread_pool: For regular flows, the messages have to be processed in
                   order. Thus, the thread_pool argument is only used for hunts.
    """
    processing = []
    try:
      # The flow is dead - remove all outstanding requests and responses.
      if not self.IsRunning():
        self.flow_obj.Log("Flow complete.")
        with FlowManager(token=self.token) as flow_manager:
          for request, responses in flow_manager.FetchRequestsAndResponses(
              self.session_id):
            flow_manager.DeleteFlowRequestStates(self.session_id, request,
                                                 responses)

        return

      with FlowManager(token=self.token) as flow_manager:
        for request, responses in flow_manager.FetchRequestsAndResponses(
            self.session_id):
          if request.id == 0:
            continue

          # Are there any responses at all?
          if not responses:
            continue

          if self.process_requests_in_order:

            if request.id > self.context.next_processed_request:
              break

            # Not the request we are looking for
            if request.id < self.context.next_processed_request:
              flow_manager.DeleteFlowRequestStates(self.session_id,
                                                   request, responses)
              continue

            if request.id != self.context.next_processed_request:
              stats.STATS.IncrementCounter("grr_response_out_of_order")
              break

          # Check if the responses are complete (Last response must be a
          # STATUS message).
          if responses[-1].type != rdfvalue.GrrMessage.Type.STATUS:
            continue

          # At this point we process this request - we can remove all requests
          # and responses from the queue.
          flow_manager.DeleteFlowRequestStates(self.session_id,
                                               request, responses)

          # Do we have all the responses here?
          if len(responses) != responses[-1].response_id:
            # If we can retransmit do so. Note, this is different from the
            # automatic retransmission facilitated by the task scheduler (the
            # Task.task_ttl field) which would happen regardless of these.
            if request.transmission_count < 5:
              stats.STATS.IncrementCounter("grr_request_retransmission_count")
              request.transmission_count += 1
              self.ReQueueRequest(request)
            break

          # If we get here its all good - run the flow.
          if self.IsRunning():
            self._Process(request, responses, thread_pool, events=processing)

          # Quit early if we are no longer alive.
          else: break

          self.context.next_processed_request += 1
          self.DecrementOutstandingRequests()

        # Are there any more outstanding requests?
        if not self.flow_obj.OutstandingRequests():
          # Allow the flow to cleanup
          if self.IsRunning():
            try:
              if self.context.get("current_state") != "End":
                self.flow_obj.End(self, None)
            except Exception:   # pylint: disable=broad-except
              # This flow will terminate now
              stats.STATS.IncrementCounter("grr_flow_errors")
              self.Error(traceback.format_exc())

        # This allows the End state to issue further client requests - hence
        # postpone termination.
        if not self.flow_obj.OutstandingRequests():
          stats.STATS.IncrementCounter("grr_flow_completed_count")
          logging.info(
              "Destroying session %s(%s) for client %s",
              self.session_id, self.flow_obj.Name(),
              self.client_id)

          self.Terminate()

    except MoreDataException:
      # We did not read all the requests/responses in this run in order to
      # keep a low memory footprint and have to make another pass.
      self.QueueNotification(self.session_id)

    finally:
      # We wait here until all threads are done processing and we can safely
      # pickle the flow object.
      # We have to Ping() the hunt to extend its' lock lease time. Otherwise
      # if ProcessCompletedRequests() takes too long, the hunt may run out of
      # lease.
      ping_interval = config_lib.CONFIG["Worker.hunt_ping_interval"]
      prev_time = time.time()
      for event in processing:
        while True:
          if time.time() - prev_time > ping_interval:
            self.flow_obj.Ping()
            prev_time = time.time()

          if event.wait(ping_interval):
            break

  def _Process(self, request, responses, thread_pool, events=None):
    event = threading.Event()
    events.append(event)
    # In a hunt, all requests are independent and can be processed
    # in separate threads.
    thread_pool.AddTask(target=self._ProcessSingleRequest,
                        args=(request, responses, event,),
                        name="Hunt processing")

  def _ProcessSingleRequest(self, request, responses, event=None):
    """Completes the request by calling the state method.

    NOTE - we expect the state method to be suitably decorated with a
     StateHandler (otherwise this will raise because the prototypes
     are different)

    Args:
      request: A RequestState protobuf.
      responses: A list of GrrMessages responding to the request.
      event: A threading.Event() instance to signal completion of this request.
    """
    try:
      self.current_state = request.next_state
      client_id = request.client_id or self.client_id
      logging.info("%s Running %s with %d responses from %s",
                   self.session_id, request.next_state,
                   len(responses), client_id)
      getattr(self.flow_obj, request.next_state)(self, direct_response=None,
                                                 request=request,
                                                 responses=responses)
    # We don't know here what exceptions can be thrown in the flow but we have
    # to continue. Thus, we catch everything.
    except Exception:  # pylint: disable=broad-except
      # This flow will terminate now
      stats.STATS.IncrementCounter("grr_flow_errors")
      logging.exception("Flow raised.")

      self.Error(traceback.format_exc(), client_id=client_id)

    finally:
      if event:
        event.set()

  def GetNextOutboundId(self):
    with self.outbound_lock:
      my_id = self.context.next_outbound_id
      self.context.next_outbound_id += 1
    return my_id

  def CallClient(self, action_name, request=None, next_state=None,
                 client_id=None, request_data=None, **kwargs):
    """Calls the client asynchronously.

    This sends a message to the client to invoke an Action. The run
    action may send back many responses. These will be queued by the
    framework until a status message is sent by the client. The status
    message will cause the entire transaction to be committed to the
    specified state.

    Args:
       action_name: The function to call on the client.

       request: The request to send to the client. If not specified (Or None) we
             create a new protobuf using the kwargs.

       next_state: The state in this flow, that responses to this
             message should go to.

       client_id: The request is sent to this client.

       request_data: A dict which will be available in the RequestState
             protobuf. The Responses object maintains a reference to this
             protobuf for use in the execution of the state method. (so you can
             access this data by responses.request). Valid values are
             strings, unicode and protobufs.

    Raises:
       FlowRunnerError: If next_state is not one of the allowed next states.
       RuntimeError: The request passed to the client does not have the correct
                     type.
    """
    if client_id is None:
      client_id = self.client_id

    if client_id is None:
      raise FlowRunnerError("CallClient() is used on a flow which was not "
                            "started with a client.")

    # Retrieve the correct rdfvalue to use for this client action.
    try:
      action = actions.ActionPlugin.classes[action_name]
    except KeyError:
      raise RuntimeError("Client action %s not found." % action_name)

    request_kw = {}
    if action.in_rdfvalue is None:
      if request:
        raise RuntimeError("Client action %s does not expect args." %
                           action_name)
    else:
      if request is None:
        # Create a new rdf request.
        request = action.in_rdfvalue(**kwargs)
      else:
        # Verify that the request type matches the client action requirements.
        if not isinstance(request, action.in_rdfvalue):
          raise RuntimeError("Client action expected %s but got %s" % (
              action.in_rdfvalue, type(request)))

      request_kw["args"] = request.SerializeToString()
      request_kw["args_age"] = int(request.age)
      request_kw["args_rdf_name"] = request.__class__.__name__

    # Check that the next state is allowed
    if next_state is None:
      raise FlowRunnerError("next_state is not specified for CallClient")

    if self.process_requests_in_order and next_state not in self.next_states:
      raise FlowRunnerError("Flow %s: State '%s' called to '%s' which is "
                            "not declared in decorator." % (
                                self.__class__.__name__,
                                self.context.current_state,
                                next_state))

    outbound_id = self.GetNextOutboundId()

    # Create a new request state
    state = rdfvalue.RequestState(
        id=outbound_id,
        session_id=self.session_id,
        next_state=next_state,
        client_id=client_id)

    if request_data is not None:
      state.data = rdfvalue.Dict(request_data)

    # Send the message with the request state
    msg = rdfvalue.GrrMessage(
        session_id=utils.SmartUnicode(self.session_id), name=action_name,
        request_id=outbound_id,
        priority=self.context.priority,
        queue=utils.SmartUnicode(client_id),
        **request_kw)

    cpu_usage = self.context.client_resources.cpu_usage
    if self.context.cpu_limit:
      msg.cpu_limit = max(self.context.cpu_limit - cpu_usage.user_cpu_time -
                          cpu_usage.system_cpu_time, 0)
      if msg.cpu_limit == 0:
        raise FlowRunnerError("CPU limit exceeded.")

    if self.context.network_bytes_limit:
      msg.network_bytes_limit = max(self.context.network_bytes_limit -
                                    self.context.network_bytes_sent, 0)
      if msg.network_bytes_limit == 0:
        raise FlowRunnerError("Network limit exceeded.")

    state.request = msg
    state.ts_id = msg.task_id

    self.QueueRequest(state)

  def CallFlow(self, flow_base_cls, flow_name, next_state=None,
               request_data=None, client_id=None, **kwargs):
    """Creates a new flow and send its responses to a state.

    This creates a new flow. The flow may send back many responses which will be
    queued by the framework until the flow terminates. The final status message
    will cause the entire transaction to be committed to the specified state.

    Args:
       flow_base_cls: The GRRFlow class, used to start the new flow.
       flow_name: The name of the flow to invoke.

       next_state: The state in this flow, that responses to this
       message should go to.

       request_data: Any string provided here will be available in the
             RequestState protobuf. The Responses object maintains a reference
             to this protobuf for use in the execution of the state method. (so
             you can access this data by responses.request). There is no
             format mandated on this data but it may be a serialized protobuf.
       client_id: If given, the flow is started for this client.

       **kwargs: Arguments for the child flow.

    Raises:
       FlowRunnerError: If next_state is not one of the allowed next states.
    """
    if self.process_requests_in_order:
      # Check that the next state is allowed
      if next_state and next_state not in self.next_states:
        raise FlowRunnerError("Flow %s: State '%s' called to '%s' which is "
                              "not declared in decorator." % (
                                  self.__class__.__name__,
                                  self.current_state,
                                  next_state))

    client_id = client_id or self.client_id

    # This looks very much like CallClient() above - we prepare a request state,
    # and add it to our queue - any responses from the child flow will return to
    # the request state and the stated next_state. Note however, that there is
    # no client_id or actual request message here because we directly invoke the
    # child flow rather than queue anything for it.
    state = rdfvalue.RequestState(
        id=self.GetNextOutboundId(),
        session_id=utils.SmartUnicode(self.session_id),
        client_id=client_id,
        next_state=next_state, flow_name=flow_name,
        response_count=0)

    if request_data:
      state.data = rdfvalue.Dict(request_data)

    cpu_limit = self.context.cpu_limit
    network_bytes_limit = self.context.network_bytes_limit

    # Create the new child flow but do not notify the user about it.
    flow_base_cls.StartFlow(
        client_id, flow_name, event_id=self.context.get("event_id"),
        _request_state=state, token=self.token, notify_to_user=False,
        parent_flow=self.flow_obj, _store=self.data_store,
        queue=self.context.queue, cpu_limit=cpu_limit,
        network_bytes_limit=network_bytes_limit, **kwargs)

    self.QueueRequest(state)

  def SendReply(self, response):
    """Allows this flow to send a message to its parent flow.

    If this flow does not have a parent, the message is ignored.

    Args:
      response: An RDFValue() instance to be sent to the parent.

    Raises:
      RuntimeError: If responses is not of the correct type.
    """
    if not isinstance(response, rdfvalue.RDFValue):
      raise RuntimeError("SendReply does not send RDFValue")

    # Only send the reply if we have a parent and if flow's send_replies
    # attribute is True. We have a parent only if we know our parent's request.
    if (self.context.get("request_state") and
        self.context.send_replies):

      request_state = self.context.request_state

      request_state.response_count += 1

      # Make a response message
      msg = rdfvalue.GrrMessage(
          session_id=request_state.session_id,
          request_id=request_state.id,
          response_id=request_state.response_count,
          auth_state=rdfvalue.GrrMessage.AuthorizationState.AUTHENTICATED,
          type=rdfvalue.GrrMessage.Type.MESSAGE,
          args=response.SerializeToString(),
          args_rdf_name=response.__class__.__name__,
          args_age=int(response.age))

      try:
        # queue the response message to the parent flow
        with FlowManager(token=self.token,
                         store=self.data_store) as flow_manager:
          # Queue the response now
          flow_manager.QueueResponse(request_state.session_id, msg)
      except MoreDataException:
        pass

      finally:
        self.QueueNotification(request_state.session_id)

  def FlushMessages(self):
    """Flushes the messages that were queued."""
    # If we were passed a parent flow_manager, the flush will happen after the
    # parent flow is done.
    self.flow_manager.Flush()

  def Error(self, backtrace, client_id=None):
    """Logs an error for a client."""
    logging.error("Hunt Error: %s", backtrace)
    self.flow_obj.LogClientError(client_id, backtrace=backtrace)

  def IsRunning(self):
    return self.context.state == rdfvalue.Flow.State.RUNNING

  def Terminate(self, status=None):
    """Terminates this flow."""
    try:
      # Dequeue existing requests
      with FlowManager(token=self.token,
                       store=self.data_store) as flow_manager:
        flow_manager.DestroyFlowStates(self.session_id)
    except MoreDataException:
      pass

    # This flow might already not be running.
    if self.context.state != rdfvalue.Flow.State.RUNNING:
      return

    if self.context.get("request_state", None):
      logging.debug("Terminating flow %s", self.session_id)

      # Make a response or use the existing one.
      response = status or rdfvalue.GrrStatus()

      client_resources = self.context.client_resources
      user_cpu = client_resources.cpu_usage.user_cpu_time
      sys_cpu = client_resources.cpu_usage.system_cpu_time
      response.cpu_time_used.user_cpu_time = user_cpu
      response.cpu_time_used.system_cpu_time = sys_cpu
      response.network_bytes_sent = self.context.network_bytes_sent
      response.child_session_id = self.session_id

      request_state = self.context.request_state
      request_state.response_count += 1

      # Make a response message
      msg = rdfvalue.GrrMessage(
          session_id=request_state.session_id,
          request_id=request_state.id,
          response_id=request_state.response_count,
          auth_state=rdfvalue.GrrMessage.AuthorizationState.AUTHENTICATED,
          type=rdfvalue.GrrMessage.Type.STATUS,
          args=response.SerializeToString())

      try:
        # queue the response message to the parent flow
        with FlowManager(token=self.token,
                         store=self.data_store) as flow_manager:
          # Queue the response now
          flow_manager.QueueResponse(request_state.session_id, msg)
      finally:
        self.QueueNotification(request_state.session_id)

    # Mark as terminated.
    self.context.state = rdfvalue.Flow.State.TERMINATED
    self.flow_obj.Flush()

  def OutstandingRequests(self):
    """Returns the number of all outstanding requests.

    This is used to determine if the flow needs to be destroyed yet.

    Returns:
       the number of all outstanding requests.
    """
    return self.flow_obj.OutstandingRequests()

  def UpdateProtoResources(self, status):
    """Save cpu and network stats, check limits."""
    user_cpu = status.cpu_time_used.user_cpu_time
    system_cpu = status.cpu_time_used.system_cpu_time
    self.context.client_resources.cpu_usage.user_cpu_time += user_cpu
    self.context.client_resources.cpu_usage.system_cpu_time += system_cpu

    user_cpu_total = self.context.client_resources.cpu_usage.user_cpu_time
    system_cpu_total = self.context.client_resources.cpu_usage.system_cpu_time

    self.context.network_bytes_sent += status.network_bytes_sent

    if self.context.cpu_limit:
      if self.context.cpu_limit < (user_cpu_total + system_cpu_total):
        # We have exceeded our limit, stop this flow.
        raise FlowRunnerError("CPU limit exceeded.")

    if self.context.network_bytes_limit:
      if self.context.network_bytes_limit < self.context.network_bytes_sent:
        # We have exceeded our byte limit, stop this flow.
        raise FlowRunnerError("Network bytes limit exceeded.")

  def SaveResourceUsage(self, request, responses):
    """Update the resource usage of the flow."""
    self.flow_obj.ProcessClientResourcesStats(request.client_id,
                                              responses.status)

    # Do this last since it may raise "CPU limit exceeded".
    self.UpdateProtoResources(responses.status)

  def QueueClientMessage(self, msg):
    self.flow_manager.QueueClientMessage(msg)

  def _QueueRequest(self, request):
    if request.request.name:
      # This message contains a client request as well.
      self.QueueClientMessage(request.request)

    self.flow_manager.QueueRequest(self.session_id, request)

  def IncrementOutstandingRequests(self):
    with self.outbound_lock:
      self.context.outstanding_requests += 1

  def DecrementOutstandingRequests(self):
    with self.outbound_lock:
      self.context.outstanding_requests -= 1

  def QueueRequest(self, request):
    # Remember the new request for later
    self._QueueRequest(request)
    self.IncrementOutstandingRequests()

  def ReQueueRequest(self, request):
    self._QueueRequest(request)

  def QueueResponse(self, response):
    self.flow_manager.QueueResponse(self.session_id, response)

  def QueueNotification(self, session_id, timestamp=None):
    self.flow_manager.QueueNotification(session_id, timestamp=timestamp)


class FlowRunner(HuntRunner):
  """The runner for flows."""

  process_requests_in_order = True

  def CallClient(self, action_name, request=None, next_state=None,
                 request_data=None, client_id=None, **kwargs):
    client_id = client_id or self.client_id
    super(FlowRunner, self).CallClient(
        action_name, request=request,
        next_state=next_state, request_data=request_data,
        client_id=client_id, **kwargs)

  def CallFlow(self, flow_base_cls, flow_name, next_state=None,
               request_data=None, client_id=None, **kwargs):
    client_id = client_id or self.client_id
    super(FlowRunner, self).CallFlow(
        flow_base_cls, flow_name,
        next_state=next_state, request_data=request_data,
        client_id=client_id, **kwargs)

  def _Process(self, request, responses, unused_thread_pool=None, events=None):
    self._ProcessSingleRequest(request, responses, event=None)

  def Error(self, backtrace, client_id=None):
    """Kills this flow with an error."""
    client_id = client_id or self.client_id
    if self.IsRunning():
      # Set an error status
      reply = rdfvalue.GrrStatus()
      reply.status = rdfvalue.GrrStatus.ReturnedStatus.GENERIC_ERROR
      if backtrace:
        reply.error_message = backtrace

      self.Terminate(status=reply)

      self.context.state = rdfvalue.Flow.State.ERROR

      if backtrace:
        logging.error("Error in flow %s (%s). Trace: %s", self.session_id,
                      client_id, backtrace)
        self.context.backtrace = backtrace
      else:
        logging.error("Error in flow %s (%s).", self.session_id,
                      client_id)

      self.flow_obj.Flush()
      self.flow_obj.Notify(
          "FlowStatus", client_id,
          "Flow (%s) terminated due to error" % self.session_id)

  def SaveResourceUsage(self, _, responses):
    status = responses.status
    if status:
      self.UpdateProtoResources(status)


class FlowManager(object):
  """This class manages the representation of the flow within the data store."""
  # These attributes are related to a flow's internal data structures
  # Requests are protobufs of type RequestState. They have a column
  # prefix followed by the request number:
  FLOW_REQUEST_PREFIX = "flow:request:"
  FLOW_REQUEST_TEMPLATE = FLOW_REQUEST_PREFIX + "%08X"

  # This regex will return all messages (requests or responses) in this flow
  # state.
  FLOW_MESSAGE_REGEX = "flow:.*"

  # This regex will return all the requests in order
  FLOW_REQUEST_REGEX = FLOW_REQUEST_PREFIX + ".*"

  # Each request may have any number of responses. These attributes
  # are GrrMessage protobufs. Their attribute consists of a prefix,
  # followed by the request number, followed by the response number.
  FLOW_RESPONSE_PREFIX = "flow:response:%08X:"
  FLOW_RESPONSE_TEMPLATE = FLOW_RESPONSE_PREFIX + "%08X"

  # This regex will return all the responses in order
  FLOW_RESPONSE_REGEX = "flow:response:.*"

  # This is the subject name of flow state variables. We need to be
  # able to lock these independently from the actual flow.
  FLOW_TASK_TEMPLATE = "%s"
  FLOW_STATE_TEMPLATE = "%s/state"

  FLOW_TASK_REGEX = "task:.*"

  request_limit = 10000
  response_limit = 100000

  def __init__(self, store=None, sync=True, token=None):
    self.sync = sync
    self.token = token
    if store is None:
      store = data_store.DB

    self.data_store = store

    # We cache all these and write/delete in one operation.
    self.to_write = {}
    self.to_delete = {}
    self.client_messages_to_delete = {}
    self.new_client_messages = []
    self.client_ids = {}
    self.notifications = []

  def FetchRequestsAndResponses(self, session_id):
    """Fetches all outstanding requests and responses for this flow.

    We first cache all requests and responses for this flow in memory to
    prevent round trips.

    Args:
      session_id: The session_id to get the requests/responses for.

    Yields:
      an tuple (request protobufs, list of responses messages) in ascending
      order of request ids.

    Raises:
      MoreDataException: When there is more data available than read by the
                         limited query.
    """
    subject = self.FLOW_STATE_TEMPLATE % session_id
    state_map = {0: {"REQUEST_STATE": rdfvalue.RequestState(id=0)}}
    max_request_id = "00000000"

    request_count = 0
    response_count = 0
    # Get some requests
    for predicate, serialized, _ in sorted(self.data_store.ResolveRegex(
        subject, self.FLOW_REQUEST_REGEX, token=self.token,
        limit=self.request_limit)):

      components = predicate.split(":")
      max_request_id = components[2]

      request = rdfvalue.RequestState(serialized)

      meta_data = state_map.setdefault(request.id, {})
      meta_data["REQUEST_STATE"] = request
      request_count += 1

    # Now get some responses
    for predicate, serialized, _ in sorted(self.data_store.ResolveRegex(
        subject, self.FLOW_RESPONSE_REGEX, token=self.token,
        limit=self.response_limit)):
      response_count += 1

      components = predicate.split(":")
      if components[2] > max_request_id:
        break

      response = rdfvalue.GrrMessage(serialized)
      if response.request_id in state_map:
        meta_data = state_map.setdefault(response.request_id, {})
        responses = meta_data.setdefault("RESPONSES", [])
        responses.append(response)

    for request_id in sorted(state_map):
      try:
        metadata = state_map[request_id]

        yield (metadata["REQUEST_STATE"], metadata.get("RESPONSES", []))
      except KeyError:
        pass

    if (request_count >= self.request_limit or
        response_count >= self.response_limit):
      raise MoreDataException()

  def DeleteFlowRequestStates(self, session_id, request_state, responses):
    """Deletes the request and all its responses from the flow state queue."""

    queue = self.to_delete.setdefault(session_id, [])
    if request_state and request_state.HasField("client_id"):
      queue.append(self.FLOW_REQUEST_TEMPLATE % request_state.id)

      # Remove the message from the client queue that this request forms.
      self.client_messages_to_delete.setdefault(session_id, []).append(
          request_state.ts_id)
      self.client_ids[session_id] = request_state.client_id

    # Delete all the responses by their response id.
    for response in responses:
      queue.append(self.FLOW_RESPONSE_TEMPLATE % (
          response.request_id, response.response_id))

  def DestroyFlowStates(self, session_id):
    """Deletes all states in this flow and dequeue all client messages."""
    for request_state, _ in self.FetchRequestsAndResponses(session_id):
      if request_state.HasField("client_id"):
        self.client_messages_to_delete.setdefault(session_id, []).append(
            request_state.ts_id)
        self.client_ids[session_id] = request_state.client_id

    subject = self.FLOW_STATE_TEMPLATE % session_id
    self.data_store.DeleteSubject(subject, token=self.token)

  def Flush(self):
    """Writes the changes in this object to the datastore."""
    for session_id in set(self.to_write) | set(self.to_delete):
      try:
        subject = self.FLOW_STATE_TEMPLATE % session_id
        self.data_store.MultiSet(subject, self.to_write.get(session_id, {}),
                                 to_delete=self.to_delete.get(session_id, []),
                                 sync=False, token=self.token)
      except data_store.Error:
        pass

    for session_id in self.client_messages_to_delete:
      scheduler.SCHEDULER.Delete(
          self.client_ids[session_id],
          self.client_messages_to_delete[session_id],
          token=self.token)

    scheduler.SCHEDULER.Schedule(self.new_client_messages, token=self.token)

    for session_id, timestamp in self.notifications:
      scheduler.SCHEDULER.NotifyQueue(
          session_id, timestamp=timestamp, sync=False, token=self.token)

    if self.sync:
      self.data_store.Flush()

    self.to_write = {}
    self.to_delete = {}
    self.client_messages_to_delete = {}
    self.client_ids = {}
    self.notifications = []
    self.new_client_messages = []

  def __enter__(self):
    return self

  def __exit__(self, unused_type, unused_value, unused_traceback):
    """Supports 'with' protocol."""
    self.Flush()

  def QueueResponse(self, session_id, response):
    """Queues the message on the flow's state."""
    queue = self.to_write.setdefault(session_id, {})
    queue.setdefault(
        FlowManager.FLOW_RESPONSE_TEMPLATE % (
            response.request_id, response.response_id),
        []).append(response.SerializeToString())

  def QueueRequest(self, session_id, request_state):
    queue = self.to_write.setdefault(session_id, {})
    queue.setdefault(
        self.FLOW_REQUEST_TEMPLATE % request_state.id, []).append(
            request_state.SerializeToString())

  def QueueClientMessage(self, msg):
    self.new_client_messages.append(msg)

  def QueueNotification(self, session_id, timestamp=None):
    self.notifications.append((session_id, timestamp))


class WellKnownFlowManager(FlowManager):
  """A flow manager for well known flows."""

  def FetchRequestsAndResponses(self, session_id):
    """Well known flows do not have real requests.

    This manages retrieving all the responses without requiring corresponding
    requests.

    Args:
      session_id: The session_id to get the requests/responses for.

    Yields:
      A tuple of request (None) and responses.
    """
    subject = self.FLOW_STATE_TEMPLATE % session_id

    # Get some requests
    for _, serialized, _ in sorted(self.data_store.ResolveRegex(
        subject, self.FLOW_RESPONSE_REGEX, token=self.token,
        limit=self.request_limit)):

      # The predicate format is flow:response:REQUEST_ID:RESPONSE_ID. For well
      # known flows both request_id and response_id are randomized.
      response = rdfvalue.GrrMessage(serialized)

      yield None, [response]
