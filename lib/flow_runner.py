#!/usr/bin/env python
# Copyright 2011 Google Inc. All Rights Reserved.
"""This file contains a helper class for the flows.

This flow context class provides all the methods for handling flows (i.e.,
calling clients, changing state, ...).

Each flow must have a flow runner before it can be executed. The flow runner is
responsible for queuing messages and maintaining scheduling state (e.g. request
IDs, outstanding requests, quotas etc),

Runners form a tree structure: A top level runner has no parent, but child
runners have a parent. For example, when a flow calls CallFlow(), the runner
creates a new flow (with a child runner) and passes execution to the new
flow. The child flow's runner queues messages on its parent's message
queues. The top level flow runner ends up with all the messages for all its
children in its queues, and then flushes them all at once to the data
stores. The goal is to prevent child flows from sending messages to the data
store before their parent's messages since this will create a race condition
(for example a child's client requests may be answered before the parent). We
also need to ensure that client messages for child flows do not get queued until
the child flow itself has finished running and is pickled into the data store.

The following is a summary of the CallFlow() sequence:

1. The top level flow runner has no parent_runner.

2. The flow calls self.CallFlow() which is delegated to the flow's runner's
   CallFlow() method.

3. The flow runner calls StartFlow(). This creates a child flow and a new flow
   runner. The new runner has as a parent the top level flow.

4. The child flow calls CallClient() which schedules some messages for the
   client. Since its runner has a parent runner, the messages are queued on the
   parent runner's message queues.

5. The child flow completes execution of its Start() method, and its state gets
   pickled and stored in the data store.

6. Execution returns to the parent flow, which may also complete, and serialize
   its state to the data store.

7. At this point the top level flow runner contains in its message queues all
   messages from all child flows. It then syncs all its queues to the data store
   at the same time. This guarantees that client messages from child flows are
   scheduled after the child flow itself is serialized into the data store.


To manage the flow queues, we have a QueueManager object. The Queue manager
abstracts the accesses to the queue by maintaining internal queues of outgoing
messages and providing methods for retrieving requests and responses from the
queues. Each flow runner has a queue manager which is uses to manage the flow's
queues. Child flow runners all share their parent's queue manager.


"""


import threading
import time
import traceback


import logging
from grr.client import actions
from grr.lib import aff4
from grr.lib import data_store
from grr.lib import rdfvalue
from grr.lib import scheduler
from grr.lib import stats
from grr.lib import utils
from grr.lib.rdfvalues import flows


class FlowRunnerError(Exception):
  """Raised when there is an error during state transitions."""


class MoreDataException(Exception):
  """Raised when there is more data available."""


class FlowRunner(object):
  """The flow context class for hunts.

  This is essentially the same as a normal context but it processes
  all the requests that arrive regardless of any order such that one client that
  doesn't respond does not make the whole hunt wait.
  """

  # Normal flows must process responses in order.
  process_requests_in_order = True
  queue_manager = None

  client_id = None

  def __init__(self, flow_obj, parent_runner=None, runner_args=None,
               _store=None, token=None):
    """Constructor for the Flow Runner.

    Args:
      flow_obj: The flow object this runner will run states for.
      parent_runner: The parent runner of this runner.
      runner_args: A FlowRunnerArgs() instance containing initial values. If not
        specified, we use the args from the flow_obj's state.context.
      _store: An optional data store to use. (Usually only used in tests).
      token: An instance of access_control.ACLToken security token.
    """
    self.token = token or flow_obj.token
    self.data_store = _store or data_store.DB
    self.parent_runner = parent_runner

    # If we have a parent runner, we use its queue manager.
    if parent_runner is not None:
      self.queue_manager = parent_runner.queue_manager
    else:
      # Otherwise we use a new queue manager.
      self.queue_manager = QueueManager(token=self.token, store=self.data_store)

    self.outbound_lock = threading.Lock()
    self.flow_obj = flow_obj

    # Initialize from a new runner args proto.
    if runner_args is not None:
      # Flow state does not have a valid context, we need to create one.
      self.context = self.InitializeContext(runner_args)
      self.args = runner_args

      self.context.Register(
          "session_id", self.GetNewSessionID())

    else:
      # Retrieve args from the flow object's context. The flow object is
      # responsible for storing our context, although they do not generally
      # access it directly.
      self.context = self.flow_obj.state.context
      self.args = self.context.args

    # Populate the flow object's urn with the new session id.
    self.flow_obj.urn = self.session_id = self.context.session_id

  def InitializeContext(self, args):
    """Initializes the context of this flow."""
    if args is None:
      args = rdfvalue.FlowRunnerArgs()

    context = flows.DataObject(
        args=args,
        backtrace=None,
        client_resources=rdfvalue.ClientResources(),
        create_time=rdfvalue.RDFDatetime().Now(),
        creator=self.token.username,
        current_state="Start",
        network_bytes_sent=0,
        next_outbound_id=1,
        next_processed_request=1,
        next_states=set(),
        outstanding_requests=0,
        remaining_cpu_quota=args.cpu_limit,
        state=rdfvalue.Flow.State.RUNNING,
        user=self.token.username,

        # Have we sent a notification to the user.
        user_notified=False,
        )

    # Store the context in the flow_obj for next time.
    self.flow_obj.state.Register("context", context)

    return context

  def GetNewSessionID(self):
    """Returns a random session ID for this flow based on the runner args.

    Returns:
      A formatted session id URN.
    """
    # Calculate a new session id based on the flow args. Note that our caller
    # can specify the base path to the session id, but they can not influence
    # the exact session id we pick. This ensures that callers can not engineer a
    # session id clash forcing us to overwrite an existing flow.
    base = self.args.base_session_id
    if base is None:
      base = self.args.client_id or aff4.ROOT_URN
      base = base.Add("flows")

    return rdfvalue.SessionID(base=base, queue=self.args.queue)

  def SetAllowedFollowUpStates(self, next_states):
    self.context.next_states = next_states

  def OutstandingRequests(self):
    """Returns the number of all outstanding requests.

    This is used to determine if the flow needs to be destroyed yet.

    Returns:
       the number of all outstanding requests.
    """
    return self.context.outstanding_requests

  def CallState(self, messages=None, next_state="", request_data=None, delay=0):
    """This method is used to schedule a new state on a different worker.

    This is basically the same as CallFlow() except we are calling
    ourselves. The state will be invoked in a later time and receive all the
    messages we send.

    Args:
       messages: A list of rdfvalues to send. If the last one is not a
            GrrStatus, we append an OK Status.
       next_state: The state in this flow to be invoked with the responses.
       request_data: Any dict provided here will be available in the
             RequestState protobuf. The Responses object maintains a reference
             to this protobuf for use in the execution of the state method. (so
             you can access this data by responses.request).
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
                                          session_id=self.context.session_id,
                                          client_id=self.args.client_id,
                                          next_state=next_state)

    if request_data:
      request_state.data = rdfvalue.Dict().FromDict(request_data)

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
    # First ensure that client messages are all removed. NOTE: We make a new
    # queue manager here because we want only the client messages to be removed
    # ASAP. This must happen before we actually run the flow to ensure the
    # client requests are removed from the client queues.
    with QueueManager(token=self.token) as queue_manager:
      for request, _ in queue_manager.FetchCompletedRequests(self.session_id):
        # Requests which are not destined to clients have no embedded request
        # message.
        if request.HasField("request"):
          queue_manager.DeQueueClientRequest(request.client_id,
                                             request.request.task_id)

    # The flow is dead - remove all outstanding requests and responses.
    if not self.IsRunning():
      self.flow_obj.Log("Flow complete.")
      self.queue_manager.DestroyFlowStates(self.session_id)
      return

    processing = []
    while True:
      try:
        # Here we only care about completed requests - i.e. those requests with
        # responses followed by a status message.
        for request, responses in self.queue_manager.FetchCompletedResponses(
            self.session_id):
          if request.id == 0:
            continue

          if not responses:
            break

          if self.process_requests_in_order:
            # We are missing a needed request - maybe its not completed yet.
            if request.id > self.context.next_processed_request:
              stats.STATS.IncrementCounter("grr_response_out_of_order")
              break

            # Not the request we are looking for - we have seen it before
            # already.
            if request.id < self.context.next_processed_request:
              self.queue_manager.DeleteFlowRequestStates(
                  self.session_id, request)
              continue

          # Do we have all the responses here? This can happen if some of the
          # responses were lost.
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
            self.flow_obj.HeartBeat()
            self._Process(request, responses, thread_pool=thread_pool,
                          events=processing)

          # Quit early if we are no longer alive.
          else: break

          # At this point we have processed this request - we can remove it and
          # its responses from the queue.
          self.queue_manager.DeleteFlowRequestStates(self.session_id, request)
          self.context.next_processed_request += 1
          self.DecrementOutstandingRequests()

        # Are there any more outstanding requests?
        if not self.OutstandingRequests():
          # Allow the flow to cleanup
          if self.IsRunning() and self.context.current_state != "End":
            self.RunStateMethod("End")

        # Rechecking the OutstandingRequests allows the End state (which was
        # called above) to issue further client requests - hence postpone
        # termination.
        if not self.OutstandingRequests():
          stats.STATS.IncrementCounter("grr_flow_completed_count")
          logging.info("Destroying session %s(%s) for client %s",
                       self.session_id, self.flow_obj.Name(),
                       self.args.client_id)

          self.Terminate()

        # We are done here.
        return

      except MoreDataException:
        # We did not read all the requests/responses in this run in order to
        # keep a low memory footprint and have to make another pass.
        self.Flush()
        self.flow_obj.Flush()
        continue

      finally:
        # Join any threads.
        for event in processing:
          event.wait()

  def _Process(self, request, responses, **_):
    """Flows process responses serially in the same thread."""
    self.RunStateMethod(request.next_state, request, responses, event=None)

  def RunStateMethod(self, method, request=None, responses=None, event=None,
                     direct_response=None):
    """Completes the request by calling the state method.

    NOTE - we expect the state method to be suitably decorated with a
     StateHandler (otherwise this will raise because the prototypes
     are different)

    Args:
      method: The name of the state method to call.

      request: A RequestState protobuf.

      responses: A list of GrrMessages responding to the request.

      event: A threading.Event() instance to signal completion of this request.

      direct_response: A flow.Responses() object can be provided to avoid
        creation of one.
    """
    client_id = None
    try:
      self.current_state = method
      if request and responses:
        client_id = request.client_id or self.args.client_id
        logging.debug("%s Running %s with %d responses from %s",
                      self.session_id, method,
                      len(responses), client_id)

      else:
        logging.debug("%s Running state method %s", self.session_id, method)

      # Extend our lease if needed.
      self.flow_obj.HeartBeat()
      getattr(self.flow_obj, method)(direct_response=direct_response,
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
             create a new RDFValue using the kwargs.

       next_state: The state in this flow, that responses to this
             message should go to.

       client_id: The request is sent to this client.

       request_data: A dict which will be available in the RequestState
             protobuf. The Responses object maintains a reference to this
             protobuf for use in the execution of the state method. (so you can
             access this data by responses.request). Valid values are
             strings, unicode and protobufs.

       **kwargs: These args will be used to construct the client action semantic
         protobuf.

    Raises:
       FlowRunnerError: If next_state is not one of the allowed next states.
       RuntimeError: The request passed to the client does not have the correct
                     type.
    """
    if client_id is None:
      client_id = self.args.client_id

    if client_id is None:
      raise FlowRunnerError("CallClient() is used on a flow which was not "
                            "started with a client.")

    # Retrieve the correct rdfvalue to use for this client action.
    try:
      action = actions.ActionPlugin.classes[action_name]
    except KeyError:
      raise RuntimeError("Client action %s not found." % action_name)

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

    # Check that the next state is allowed
    if next_state is None:
      raise FlowRunnerError("next_state is not specified for CallClient")

    if (self.process_requests_in_order and
        next_state not in self.context.next_states):
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
        request_id=outbound_id, priority=self.args.priority,
        queue=client_id, payload=request)

    if self.context.remaining_cpu_quota:
      msg.cpu_limit = int(self.context.remaining_cpu_quota)

    cpu_usage = self.context.client_resources.cpu_usage
    if self.context.args.cpu_limit:
      msg.cpu_limit = max(
          self.context.args.cpu_limit - cpu_usage.user_cpu_time -
          cpu_usage.system_cpu_time, 0)

      if msg.cpu_limit == 0:
        raise FlowRunnerError("CPU limit exceeded.")

    if self.context.args.network_bytes_limit:
      msg.network_bytes_limit = max(self.context.args.network_bytes_limit -
                                    self.context.network_bytes_sent, 0)
      if msg.network_bytes_limit == 0:
        raise FlowRunnerError("Network limit exceeded.")

    state.request = msg

    self.QueueRequest(state)

  def Publish(self, event_name, msg):
    """Sends the message to event listeners."""
    handler_urns = []

    # This is the cache of event names to handlers.
    event_map = self.flow_obj.EventListener.EVENT_NAME_MAP

    if isinstance(event_name, basestring):
      for event_cls in event_map.get(event_name, []):
        if event_cls.well_known_session_id is None:
          logging.error("Well known flow %s has no session_id.",
                        event_cls.__name__)
        else:
          handler_urns.append(event_cls.well_known_session_id)

    else:
      handler_urns.append(event_name)

    # Allow the event name to be either a string or a URN of an event
    # listener.
    if not isinstance(msg, rdfvalue.RDFValue):
      raise ValueError("Can only publish RDFValue instances.")

    # Wrap the message in a GrrMessage if needed.
    if not isinstance(msg, rdfvalue.GrrMessage):
      msg = rdfvalue.GrrMessage(payload=msg)

    # Randomize the response id or events will get overwritten.
    msg.response_id = msg.task_id = msg.GenerateTaskID()
    # Well known flows always listen for request id 0.
    msg.request_id = 0

    # Forward the message to the well known flow's queue.
    for event_urn in handler_urns:
      self.queue_manager.QueueResponse(event_urn, msg)
      self.queue_manager.QueueNotification(event_urn, priority=msg.priority)

  def CallFlow(self, flow_name=None, next_state=None, sync=True,
               request_data=None, client_id=None, base_session_id=None,
               **kwargs):
    """Creates a new flow and send its responses to a state.

    This creates a new flow. The flow may send back many responses which will be
    queued by the framework until the flow terminates. The final status message
    will cause the entire transaction to be committed to the specified state.

    Args:
       flow_name: The name of the flow to invoke.

       next_state: The state in this flow, that responses to this
       message should go to.

       sync: If True start the flow inline on the calling thread, else schedule
         a worker to actually start the child flow.

       request_data: Any dict provided here will be available in the
             RequestState protobuf. The Responses object maintains a reference
             to this protobuf for use in the execution of the state method. (so
             you can access this data by responses.request). There is no
             format mandated on this data but it may be a serialized protobuf.

       client_id: If given, the flow is started for this client.

       base_session_id: A URN which will be used to build a URN.

       **kwargs: Arguments for the child flow.

    Raises:
       FlowRunnerError: If next_state is not one of the allowed next states.

    Returns:
       The URN of the child flow which was created.
    """
    if self.process_requests_in_order:
      # Check that the next state is allowed
      if next_state and next_state not in self.context.next_states:
        raise FlowRunnerError("Flow %s: State '%s' called to '%s' which is "
                              "not declared in decorator." % (
                                  self.__class__.__name__,
                                  self.context.current_state,
                                  next_state))

    client_id = client_id or self.args.client_id

    # This looks very much like CallClient() above - we prepare a request state,
    # and add it to our queue - any responses from the child flow will return to
    # the request state and the stated next_state. Note however, that there is
    # no client_id or actual request message here because we directly invoke the
    # child flow rather than queue anything for it.
    state = rdfvalue.RequestState(
        id=self.GetNextOutboundId(),
        session_id=utils.SmartUnicode(self.session_id),
        client_id=client_id,
        next_state=next_state,
        response_count=0)

    if request_data:
      state.data = rdfvalue.Dict().FromDict(request_data)

    cpu_limit = self.context.args.cpu_limit
    network_bytes_limit = self.context.args.network_bytes_limit

    # Create the new child flow but do not notify the user about it.
    child_urn = self.flow_obj.StartFlow(
        client_id=client_id, flow_name=flow_name,
        base_session_id=base_session_id or self.session_id,
        event_id=self.context.get("event_id"),
        request_state=state, token=self.token, notify_to_user=False,
        parent_flow=self.flow_obj, _store=self.data_store,
        network_bytes_limit=network_bytes_limit, sync=sync,
        queue=self.args.queue, cpu_limit=cpu_limit, **kwargs)

    self.QueueRequest(state)

    return child_urn

  def SendReply(self, response):
    """Allows this flow to send a message to its parent flow.

    If this flow does not have a parent, the message is ignored.

    Args:
      response: An RDFValue() instance to be sent to the parent.

    Raises:
      RuntimeError: If responses is not of the correct type.
    """
    if not isinstance(response, rdfvalue.RDFValue):
      raise RuntimeError("SendReply can only send a Semantic Value")

    # Only send the reply if we have a parent and if flow's send_replies
    # attribute is True. We have a parent only if we know our parent's request.
    if (self.args.HasField("request_state") and
        self.args.send_replies):

      request_state = self.args.request_state

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
        # Queue the response now
        self.queue_manager.QueueResponse(request_state.session_id, msg)
      except MoreDataException:
        pass

  def __enter__(self):
    return self

  def __exit__(self, unused_type, unused_value, unused_traceback):
    """Supports 'with' protocol."""
    self.FlushMessages()

  def FlushMessages(self):
    """Flushes the messages that were queued."""
    # Only flush queues if we are the top level runner.
    if self.parent_runner is None:
      self.queue_manager.Flush()

  def Error(self, backtrace, client_id=None):
    """Kills this flow with an error."""
    client_id = client_id or self.args.client_id
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

      self.Notify(
          "FlowStatus", client_id,
          "Flow (%s) terminated due to error" % self.session_id)

  def IsRunning(self):
    return self.context.state == rdfvalue.Flow.State.RUNNING

  def Terminate(self, status=None):
    """Terminates this flow."""
    try:
      self.queue_manager.DestroyFlowStates(self.session_id)
    except MoreDataException:
      pass

    # This flow might already not be running.
    if self.context.state != rdfvalue.Flow.State.RUNNING:
      return

    if self.args.HasField("request_state"):
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

      request_state = self.args.request_state
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
        # Queue the response now
        self.queue_manager.QueueResponse(request_state.session_id, msg)
      finally:
        self.QueueNotification(request_state.session_id)

    # Mark as terminated.
    self.context.state = rdfvalue.Flow.State.TERMINATED
    self.flow_obj.Flush()

  def UpdateProtoResources(self, status):
    """Save cpu and network stats, check limits."""
    user_cpu = status.cpu_time_used.user_cpu_time
    system_cpu = status.cpu_time_used.system_cpu_time
    self.context.client_resources.cpu_usage.user_cpu_time += user_cpu
    self.context.client_resources.cpu_usage.system_cpu_time += system_cpu

    user_cpu_total = self.context.client_resources.cpu_usage.user_cpu_time
    system_cpu_total = self.context.client_resources.cpu_usage.system_cpu_time

    self.context.network_bytes_sent += status.network_bytes_sent

    if self.context.args.cpu_limit:
      if self.context.args.cpu_limit < (user_cpu_total + system_cpu_total):
        # We have exceeded our limit, stop this flow.
        raise FlowRunnerError("CPU limit exceeded.")

    if self.context.args.network_bytes_limit:
      if (self.context.args.network_bytes_limit <
          self.context.network_bytes_sent):
        # We have exceeded our byte limit, stop this flow.
        raise FlowRunnerError("Network bytes limit exceeded.")

  def SaveResourceUsage(self, request, responses):
    """Method automatically called from the StateHandler to tally resource."""
    _ = request
    status = responses.status
    if status:
      # Do this last since it may raise "CPU limit exceeded".
      self.UpdateProtoResources(status)

  def _QueueRequest(self, request):
    if request.request.name:
      # This message contains a client request as well.
      self.queue_manager.QueueClientMessage(request.request)

    self.queue_manager.QueueRequest(self.session_id, request)

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
    self.queue_manager.QueueResponse(self.session_id, response)

  def QueueNotification(self, session_id, timestamp=None):
    self.queue_manager.QueueNotification(session_id, timestamp=timestamp)

  def SetStatus(self, status):
    self.context.status = status

  def Log(self, format_str, *args):
    """Logs the message using the flow's standard logging.

    Args:
      format_str: Format string
      *args: arguments to the format string
    """
    format_str = utils.SmartUnicode(format_str)

    try:
      # The status message is always in unicode
      status = format_str % args
    except TypeError:
      logging.error("Tried to log a format string with the wrong number "
                    "of arguments: %s", format_str)
      status = format_str

    logging.info("%s: %s", self.session_id, status)

    self.SetStatus(utils.SmartUnicode(status))

    # Add the message to the flow's log attribute
    data_store.DB.Set(self.session_id,
                      aff4.AFF4Object.GRRFlow.SchemaCls.LOG,
                      status, replace=False, sync=False, token=self.token)

  def Status(self, format_str, *args):
    """Flows can call this method to set a status message visible to users."""
    self.Log(format_str, *args)

  def Notify(self, message_type, subject, msg):
    """Send a notification to the originating user.

    Args:
       message_type: The type of the message. This allows the UI to format
         a link to the original object e.g. "ViewObject" or "HostInformation"
       subject: The urn of the AFF4 object of interest in this link.
       msg: A free form textual message.
    """
    if self.args.notify_to_user:
      # Prefix the message with the hostname of the client we are running
      # against.
      if self.args.client_id:
        client_fd = aff4.FACTORY.Open(self.args.client_id, mode="rw",
                                      token=self.token)
        hostname = client_fd.Get(client_fd.Schema.HOSTNAME) or ""
        client_msg = "%s: %s" % (hostname, msg)
      else:
        client_msg = msg

      # Add notification to the User object.
      fd = aff4.FACTORY.Create(aff4.ROOT_URN.Add("users").Add(
          self.context.creator), "GRRUser", mode="rw", token=self.token)

      # Queue notifications to the user.
      fd.Notify(message_type, subject, client_msg, self.session_id)
      fd.Close()

      # Add notifications to the flow.
      notification = rdfvalue.Notification(
          type=message_type, subject=utils.SmartUnicode(subject),
          message=utils.SmartUnicode(msg),
          source=self.session_id,
          timestamp=rdfvalue.RDFDatetime().Now())

      data_store.DB.Set(self.session_id,
                        aff4.AFF4Object.GRRFlow.SchemaCls.NOTIFICATION,
                        notification, replace=False, sync=False,
                        token=self.token)

      # Disable further notifications.
      self.context.user_notified = True

    # Allow the flow to either specify an event name or an event handler URN.
    notification_event = (self.args.notification_event or
                          self.args.notification_urn)
    if notification_event:
      if self.context.state == rdfvalue.Flow.State.ERROR:
        status = rdfvalue.FlowNotification.Status.ERROR

      else:
        status = rdfvalue.FlowNotification.Status.OK

      event = rdfvalue.FlowNotification(
          session_id=self.context.session_id,
          flow_name=self.args.flow_name,
          client_id=self.args.client_id,
          status=status)

      self.flow_obj.Publish(notification_event, message=event)


class QueueManager(object):
  """This class manages the representation of the flow within the data store."""
  # These attributes are related to a flow's internal data structures Requests
  # are protobufs of type RequestState. They have a constant prefix followed by
  # the request number:
  FLOW_REQUEST_PREFIX = "flow:request:"
  FLOW_REQUEST_TEMPLATE = FLOW_REQUEST_PREFIX + "%08X"

  # When a status message is received from the client, we write it with the
  # request using the following template.
  FLOW_STATUS_TEMPLATE = "flow:status:%08X"
  FLOW_STATUS_REGEX = "flow:status:.*"

  # This regex will return all the requests in order
  FLOW_REQUEST_REGEX = FLOW_REQUEST_PREFIX + ".*"

  # Each request may have any number of responses. Responses are kept in their
  # own subject object. The subject name is derived from the session id.
  FLOW_RESPONSE_PREFIX = "flow:response:%08X:"
  FLOW_RESPONSE_TEMPLATE = FLOW_RESPONSE_PREFIX + "%08X"

  # This regex will return all the responses in order
  FLOW_RESPONSE_REGEX = "flow:response:.*"

  request_limit = 1000000
  response_limit = 1000000

  def __init__(self, store=None, sync=True, token=None):
    self.sync = sync
    self.token = token
    if store is None:
      store = data_store.DB

    self.data_store = store

    # We cache all these and write/delete in one operation.
    self.to_write = {}
    self.to_delete = {}

    # A queue of client messages to remove. Keys are client ids, values are
    # lists of task ids.
    self.client_messages_to_delete = {}
    self.new_client_messages = []
    self.client_ids = {}
    self.notifications = {}

  def GetFlowResponseSubject(self, session_id, request_id):
    """The subject used to carry all the responses for a specific request_id."""
    return session_id.Add("state/request:%08X" % request_id)

  def DeQueueClientRequest(self, client_id, task_id):
    """Remove the message from the client queue that this request forms."""
    self.client_messages_to_delete.setdefault(client_id, []).append(task_id)

  def FetchCompletedRequests(self, session_id):
    """Fetch all the requests with a status message queued for them."""
    subject = session_id.Add("state")
    requests = {}
    status = {}

    for predicate, serialized, _ in self.data_store.ResolveRegex(
        subject, [self.FLOW_REQUEST_REGEX, self.FLOW_STATUS_REGEX],
        token=self.token, limit=self.request_limit):

      parts = predicate.split(":", 3)
      request_id = parts[2]
      if parts[1] == "status":
        status[request_id] = serialized
      else:
        requests[request_id] = serialized

    for request_id, serialized in sorted(requests.items()):
      if request_id in status:
        yield (rdfvalue.RequestState(serialized),
               rdfvalue.GrrMessage(status[request_id]))

  def FetchCompletedResponses(self, session_id, limit=10000):
    """Fetch only completed requests and responses up to a limit."""
    response_subjects = {}

    total_size = 0
    for request, status in self.FetchCompletedRequests(session_id):
      # Quit early if there are too many responses.
      total_size += status.response_id
      if total_size > limit:
        break

      response_subject = self.GetFlowResponseSubject(session_id, request.id)
      response_subjects[response_subject] = request

    response_data = self.data_store.MultiResolveRegex(
        response_subjects, self.FLOW_RESPONSE_REGEX, token=self.token)

    for response_urn, request in sorted(response_subjects.items()):
      responses = []
      for _, serialized, _ in response_data.get(response_urn, []):
        responses.append(rdfvalue.GrrMessage(serialized))

      yield (request, sorted(responses, key=lambda msg: msg.response_id))

    # Indicate to the caller that there are more messages.
    if total_size > limit:
      raise MoreDataException()

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
    subject = session_id.Add("state")
    requests = {}

    # Get some requests.
    for predicate, serialized, _ in sorted(self.data_store.ResolveRegex(
        subject, self.FLOW_REQUEST_REGEX, token=self.token,
        limit=self.request_limit)):

      request_id = predicate.split(":", 1)[1]
      requests[str(subject.Add(request_id))] = serialized

    # And the responses for them.
    response_data = self.data_store.MultiResolveRegex(
        requests.keys(), self.FLOW_RESPONSE_REGEX,
        limit=self.response_limit, token=self.token)

    for urn, request_data in sorted(requests.items()):
      request = rdfvalue.RequestState(request_data)
      responses = []
      for _, serialized, _ in response_data.get(urn, []):
        responses.append(rdfvalue.GrrMessage(serialized))

      yield (request, sorted(responses, key=lambda msg: msg.response_id))

    if len(requests) >= self.request_limit:
      raise MoreDataException()

  def DeleteFlowRequestStates(self, session_id, request_state):
    """Deletes the request and all its responses from the flow state queue."""
    queue = self.to_delete.setdefault(session_id.Add("state"), [])
    queue.append(self.FLOW_REQUEST_TEMPLATE % request_state.id)
    queue.append(self.FLOW_STATUS_TEMPLATE % request_state.id)

    if request_state and request_state.HasField("request"):
      if request_state.HasField("request"):
        self.DeQueueClientRequest(request_state.client_id,
                                  request_state.request.task_id)

    # Efficiently drop all responses to this request.
    response_subject = self.GetFlowResponseSubject(session_id, request_state.id)
    self.data_store.DeleteSubject(response_subject, token=self.token)

  def DestroyFlowStates(self, session_id):
    """Deletes all states in this flow and dequeue all client messages."""
    subject = session_id.Add("state")

    for _, serialized, _ in self.data_store.ResolveRegex(
        subject, self.FLOW_REQUEST_REGEX, token=self.token,
        limit=self.request_limit):

      request = rdfvalue.RequestState(serialized)

      # Efficiently drop all responses to this request.
      response_subject = self.GetFlowResponseSubject(session_id, request.id)
      self.data_store.DeleteSubject(response_subject, token=self.token)

      # If the request refers to a client, dequeue client requests.
      if request.HasField("request"):
        self.DeQueueClientRequest(request.client_id, request.request.task_id)

    # Now drop all the requests at once.
    self.data_store.DeleteSubject(subject, token=self.token)

  def Flush(self):
    """Writes the changes in this object to the datastore."""
    for session_id in set(self.to_write) | set(self.to_delete):
      try:
        self.data_store.MultiSet(session_id, self.to_write.get(session_id, {}),
                                 to_delete=self.to_delete.get(session_id, []),
                                 sync=False, token=self.token)
      except data_store.Error:
        pass

    for client_id, messages in self.client_messages_to_delete.iteritems():
      scheduler.SCHEDULER.Delete(client_id, messages, token=self.token)

    if self.new_client_messages:
      scheduler.SCHEDULER.Schedule(self.new_client_messages, token=self.token)

    for session_id, (priority, timestamp) in self.notifications.items():
      scheduler.SCHEDULER.NotifyQueue(
          session_id, timestamp=timestamp, sync=False, token=self.token,
          priority=priority)

    if self.sync:
      self.data_store.Flush()

    self.to_write = {}
    self.to_delete = {}
    self.client_messages_to_delete = {}
    self.client_ids = {}
    self.notifications = {}
    self.new_client_messages = []

  def __enter__(self):
    return self

  def __exit__(self, unused_type, unused_value, unused_traceback):
    """Supports 'with' protocol."""
    self.Flush()

  def QueueResponse(self, session_id, response):
    """Queues the message on the flow's state."""
    # Status messages cause their requests to be marked as complete. This allows
    # us to quickly enumerate all the completed requests - it is essentially an
    # index for completed requests.
    if response.type == rdfvalue.GrrMessage.Type.STATUS:
      subject = session_id.Add("state")
      queue = self.to_write.setdefault(subject, {})
      queue.setdefault(
          self.FLOW_STATUS_TEMPLATE % response.request_id, []).append(
              response.SerializeToString())

    subject = self.GetFlowResponseSubject(session_id, response.request_id)
    queue = self.to_write.setdefault(subject, {})
    queue.setdefault(
        QueueManager.FLOW_RESPONSE_TEMPLATE % (
            response.request_id, response.response_id),
        []).append(response.SerializeToString())

  def QueueRequest(self, session_id, request_state):
    subject = session_id.Add("state")
    queue = self.to_write.setdefault(subject, {})
    queue.setdefault(
        self.FLOW_REQUEST_TEMPLATE % request_state.id, []).append(
            request_state.SerializeToString())

  def QueueClientMessage(self, msg):
    self.new_client_messages.append(msg)

  def QueueNotification(self, session_id, timestamp=None,
                        priority=rdfvalue.GrrMessage.Priority.MEDIUM_PRIORITY):
    if session_id:
      self.notifications[session_id] = (priority, timestamp)


class WellKnownQueueManager(QueueManager):
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
    subject = session_id.Add("state/request:00000000")

    # Get some requests
    for _, serialized, _ in sorted(self.data_store.ResolveRegex(
        subject, self.FLOW_RESPONSE_REGEX, token=self.token,
        limit=self.request_limit)):

      # The predicate format is flow:response:REQUEST_ID:RESPONSE_ID. For well
      # known flows both request_id and response_id are randomized.
      response = rdfvalue.GrrMessage(serialized)

      yield rdfvalue.RequestState(id=0), [response]
