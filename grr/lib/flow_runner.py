#!/usr/bin/env python
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
from grr.lib import access_control
from grr.lib import aff4
from grr.lib import data_store
# Note: OutputPluginDescriptor is also needed implicitly by FlowRunnerArgs
from grr.lib import output_plugin as output_plugin_lib
from grr.lib import queue_manager
from grr.lib import rdfvalue
from grr.lib import stats
from grr.lib import utils

from grr.lib.aff4_objects import collects
from grr.lib.aff4_objects import sequential_collection
from grr.lib.aff4_objects import users as aff4_users

from grr.lib.rdfvalues import client as rdf_client
from grr.lib.rdfvalues import flows as rdf_flows
from grr.lib.rdfvalues import protodict as rdf_protodict
from grr.lib.rdfvalues import structs as rdf_structs
from grr.proto import flows_pb2


class FlowRunnerError(Exception):
  """Raised when there is an error during state transitions."""


class FlowRunnerArgs(rdf_structs.RDFProtoStruct):
  """The argument to the flow runner.

  Note that all flows receive these arguments. This object is stored in the
  flows state.context.arg attribute.
  """
  protobuf = flows_pb2.FlowRunnerArgs


class FlowLogCollection(sequential_collection.IndexedSequentialCollection):
  RDF_TYPE = rdf_flows.FlowLog


class FlowRunner(object):
  """The flow context class for hunts.

  This is essentially the same as a normal context but it processes
  all the requests that arrive regardless of any order such that one client that
  doesn't respond does not make the whole hunt wait.
  """

  # If True, kill notifications will be scheduled by the worker when
  # running runner.ProcessCompletedRequests().
  schedule_kill_notifications = True

  # Normal flows must process responses in order.
  process_requests_in_order = True
  queue_manager = None

  client_id = None

  def __init__(self,
               flow_obj,
               parent_runner=None,
               runner_args=None,
               _store=None,
               token=None):
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
      self.queue_manager = queue_manager.QueueManager(token=self.token,
                                                      store=self.data_store)

    self.outbound_lock = threading.Lock()
    self.flow_obj = flow_obj

    # Initialize from a new runner args proto.
    if runner_args is not None:
      # Flow state does not have a valid context, we need to create one.
      self.context = self.InitializeContext(runner_args)
      self.args = runner_args

      self.context.Register("session_id", self.GetNewSessionID())

    else:
      # Retrieve args from the flow object's context. The flow object is
      # responsible for storing our context, although they do not generally
      # access it directly.
      self.context = self.flow_obj.state.context

      self.args = self.context.args

    # Populate the flow object's urn with the new session id.
    self.flow_obj.urn = self.session_id = self.context.session_id

    # Sent replies are cached so that they can be processed by output plugins
    # when the flow is saved.
    self.sent_replies = []

  @property
  def output(self):
    return self.context.output

  @property
  def output_urn(self):
    """Returns urn of the output collection.

    Note that the output collection itself is nullified when flow is terminated,
    so we're keeping the urn separately for further reference.

    Returns:
      URN of the output collection.
    """
    return self.context.output_urn

  @output.setter
  def output(self, value):
    self.context.output = value
    if self.context.output is not None:
      self.context.output_urn = self.context.output.urn

  def _CreateOutputCollection(self, args):
    # Can only really have an output collection if we are using a client.
    if args.client_id and args.output:
      output_name = args.output.format(t=time.time(),
                                       p=self.flow_obj.__class__.__name__,
                                       u=self.token.username)

      return aff4.FACTORY.Create(
          args.client_id.Add(output_name),
          collects.RDFValueCollection,
          token=self.token)

  def _GetLogsCollectionURN(self, logs_collection_urn):
    if self.parent_runner is not None and not logs_collection_urn:
      # We are a child runner, we should have been passed a
      # logs_collection_urn
      raise RuntimeError("Flow: %s has a parent %s but no logs_collection_urn"
                         " set." % (self.flow_obj.urn, self.parent_runner))

    # If we weren't passed a collection urn, create one in our namespace.
    return logs_collection_urn or self.flow_obj.urn.Add("Logs")

  def OpenLogsCollection(self, logs_collection_urn, mode="w"):
    """Open the parent-flow logs collection for writing or create a new one.

    If we receive a logs_collection_urn here it is being passed from the parent
    flow runner into the new runner created by the flow object.

    For a regular flow the call sequence is:
    flow_runner --StartFlow--> flow object --CreateRunner--> (new) flow_runner

    For a hunt the call sequence is:
    hunt_runner --CallFlow--> flow_runner --StartFlow--> flow object
     --CreateRunner--> (new) flow_runner

    Args:
      logs_collection_urn: RDFURN pointing to parent logs collection
      mode: Mode to use for opening, "r", "w", or "rw".
    Returns:
      FlowLogCollection open with mode.
    Raises:
      RuntimeError: on parent missing logs_collection.
    """
    return aff4.FACTORY.Create(
        self._GetLogsCollectionURN(logs_collection_urn),
        FlowLogCollection,
        mode=mode,
        object_exists=True,
        token=self.token)

  def InitializeContext(self, args):
    """Initializes the context of this flow."""
    if args is None:
      args = FlowRunnerArgs()

    output_collection = self._CreateOutputCollection(args)
    # Output collection is nullified when flow is terminated, so we're
    # keeping the urn separately for further reference.
    output_urn = (output_collection is not None) and output_collection.urn

    output_plugins_states = []
    for plugin_descriptor in args.output_plugins:
      if not args.client_id:
        self.Log("Not initializing output plugin %s as flow does not run on "
                 "the client.", plugin_descriptor.plugin_name)
        continue

      if not args.output:
        self.Log("Not initializing output plugin %s as output path pattern is "
                 "not specified in the flow args.",
                 plugin_descriptor.plugin_name)
        continue

      output_path = args.output.format(t=time.time(),
                                       p=(self.flow_obj.__class__.__name__ + "-"
                                          + plugin_descriptor.plugin_name),
                                       u=self.token.username)
      output_base_urn = args.client_id.Add(output_path)

      plugin_class = plugin_descriptor.GetPluginClass()
      plugin = plugin_class(output_urn,
                            args=plugin_descriptor.plugin_args,
                            output_base_urn=output_base_urn,
                            token=self.token)
      try:
        plugin.Initialize()

        plugin.state.Register("logs", [])
        plugin.state.Register("errors", [])

        output_plugins_states.append((plugin_descriptor, plugin.state))
      except Exception as e:  # pylint: disable=broad-except
        self.Log("Plugin %s failed to initialize (%s), ignoring it." %
                 (plugin, e))

    context = utils.DataObject(
        args=args,
        backtrace=None,
        client_resources=rdf_client.ClientResources(),
        create_time=rdfvalue.RDFDatetime().Now(),
        creator=args.creator or self.token.username,
        current_state="Start",
        # If not None, kill-stuck-flow notification is scheduled at the given
        # time.
        kill_timestamp=None,
        network_bytes_sent=0,
        next_outbound_id=1,
        next_processed_request=1,
        next_states=set(),
        output=output_collection,
        output_plugins_states=output_plugins_states,
        output_urn=output_urn,
        outstanding_requests=0,
        remaining_cpu_quota=args.cpu_limit,
        state=rdf_flows.Flow.State.RUNNING,

        # Have we sent a notification to the user.
        user_notified=False,)

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

  def GetAllowedFollowUpStates(self):
    return self.context.next_states

  def SetAllowedFollowUpStates(self, next_states):
    self.context.next_states = next_states

  def OutstandingRequests(self):
    """Returns the number of all outstanding requests.

    This is used to determine if the flow needs to be destroyed yet.

    Returns:
       the number of all outstanding requests.
    """
    return self.context.outstanding_requests

  def CallState(self,
                messages=None,
                next_state="",
                request_data=None,
                start_time=None):
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

       start_time: Start the flow at this time. This Delays notification for
         flow processing into the future. Note that the flow may still be
         processed earlier if there are client responses waiting.

    Raises:
       FlowRunnerError: if the next state is not valid.
    """
    if messages is None:
      messages = []

    # Check if the state is valid
    if not getattr(self.flow_obj, next_state):
      raise FlowRunnerError("Next state %s is invalid.")

    # Queue the response message to the parent flow
    request_state = rdf_flows.RequestState(id=self.GetNextOutboundId(),
                                           session_id=self.context.session_id,
                                           client_id=self.args.client_id,
                                           next_state=next_state)
    if request_data:
      request_state.data = rdf_protodict.Dict().FromDict(request_data)

    self.QueueRequest(request_state, timestamp=start_time)

    # Add the status message if needed.
    if not messages or not isinstance(messages[-1], rdf_flows.GrrStatus):
      messages.append(rdf_flows.GrrStatus())

    # Send all the messages
    for i, payload in enumerate(messages):
      if isinstance(payload, rdfvalue.RDFValue):
        msg = rdf_flows.GrrMessage(
            session_id=self.session_id,
            request_id=request_state.id,
            response_id=1 + i,
            auth_state=rdf_flows.GrrMessage.AuthorizationState.AUTHENTICATED,
            payload=payload,
            type=rdf_flows.GrrMessage.Type.MESSAGE)

        if isinstance(payload, rdf_flows.GrrStatus):
          msg.type = rdf_flows.GrrMessage.Type.STATUS
      else:
        raise FlowRunnerError("Bad message %s of type %s." % (payload,
                                                              type(payload)))

      self.QueueResponse(msg, start_time)

    # Notify the worker about it.
    self.QueueNotification(session_id=self.session_id, timestamp=start_time)

  def ProcessCompletedRequests(self, notification, thread_pool):
    """Go through the list of requests and process the completed ones.

    We take a snapshot in time of all requests and responses for this flow. We
    then process as many completed requests as possible. If responses are not
    quite here we leave it for next time.

    It is safe to call this function as many times as needed. NOTE: We assume
    that the flow queue is locked so another worker is not processing these
    messages while we are. It is safe to insert new messages to the flow:state
    queue.

    Args:
      notification: The notification object that triggered this processing.
      thread_pool: For regular flows, the messages have to be processed in
                   order. Thus, the thread_pool argument is only used for hunts.
    """
    # First ensure that client messages are all removed. NOTE: We make a new
    # queue manager here because we want only the client messages to be removed
    # ASAP. This must happen before we actually run the flow to ensure the
    # client requests are removed from the client queues.
    with queue_manager.QueueManager(token=self.token) as manager:
      for request, _ in manager.FetchCompletedRequests(
          self.session_id,
          timestamp=(0, notification.timestamp)):
        # Requests which are not destined to clients have no embedded request
        # message.
        if request.HasField("request"):
          manager.DeQueueClientRequest(request.client_id,
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
            self.session_id,
            timestamp=(0, notification.timestamp)):

          if request.id == 0:
            continue

          if self.process_requests_in_order:
            if not responses:
              break

            # We are missing a needed request - maybe its not completed yet.
            if request.id > self.context.next_processed_request:
              stats.STATS.IncrementCounter("grr_response_out_of_order")
              break

            # Not the request we are looking for - we have seen it before
            # already.
            if request.id < self.context.next_processed_request:
              self.queue_manager.DeleteFlowRequestStates(self.session_id,
                                                         request)
              continue

          if not responses:
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
            self._Process(request,
                          responses,
                          thread_pool=thread_pool,
                          events=processing)

          # Quit early if we are no longer alive.
          else:
            break

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
          # TODO(user): Deprecate in favor of 'flow_completions' metric.
          stats.STATS.IncrementCounter("grr_flow_completed_count")

          stats.STATS.IncrementCounter("flow_completions",
                                       fields=[self.flow_obj.Name()])
          logging.info("Destroying session %s(%s) for client %s",
                       self.session_id, self.flow_obj.Name(),
                       self.args.client_id)

          self.Terminate()

        # We are done here.
        return

      except queue_manager.MoreDataException:
        # Join any threads.
        for event in processing:
          event.wait()

        # We did not read all the requests/responses in this run in order to
        # keep a low memory footprint and have to make another pass.
        self.FlushMessages()
        self.flow_obj.Flush()
        continue

      finally:
        # Join any threads.
        for event in processing:
          event.wait()

  def _Process(self, request, responses, **_):
    """Flows process responses serially in the same thread."""
    self.RunStateMethod(request.next_state, request, responses, event=None)

  def RunStateMethod(self,
                     method,
                     request=None,
                     responses=None,
                     event=None,
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
      self.context.current_state = method
      if request and responses:
        client_id = request.client_id or self.args.client_id
        logging.debug("%s Running %s with %d responses from %s",
                      self.session_id, method, len(responses), client_id)

      else:
        logging.debug("%s Running state method %s", self.session_id, method)

      # Extend our lease if needed.
      self.flow_obj.HeartBeat()
      try:
        method = getattr(self.flow_obj, method)
      except AttributeError:
        raise FlowRunnerError("Flow %s has no state method %s" %
                              (self.flow_obj.__class__.__name__, method))

      method(direct_response=direct_response,
             request=request,
             responses=responses)

      if self.sent_replies:
        self.ProcessRepliesWithOutputPlugins(self.sent_replies)
        self.sent_replies = []

    # We don't know here what exceptions can be thrown in the flow but we have
    # to continue. Thus, we catch everything.
    except Exception as e:  # pylint: disable=broad-except
      # This flow will terminate now

      # TODO(user): Deprecate in favor of 'flow_errors'.
      stats.STATS.IncrementCounter("grr_flow_errors")

      stats.STATS.IncrementCounter("flow_errors", fields=[self.flow_obj.Name()])
      logging.exception("Flow %s raised %s.", self.session_id, e)

      self.Error(traceback.format_exc(), client_id=client_id)

    finally:
      if event:
        event.set()

  def GetNextOutboundId(self):
    with self.outbound_lock:
      my_id = self.context.next_outbound_id
      self.context.next_outbound_id += 1
    return my_id

  def CallClient(self,
                 action_name,
                 request=None,
                 next_state=None,
                 client_id=None,
                 request_data=None,
                 start_time=None,
                 **kwargs):
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

       client_id: rdf_client.ClientURN to send the request to.

       request_data: A dict which will be available in the RequestState
             protobuf. The Responses object maintains a reference to this
             protobuf for use in the execution of the state method. (so you can
             access this data by responses.request). Valid values are
             strings, unicode and protobufs.

       start_time: Call the client at this time. This Delays the client request
         for into the future.

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

    if not isinstance(client_id, rdf_client.ClientURN):
      # Try turning it into a ClientURN
      client_id = rdf_client.ClientURN(client_id)

    # Retrieve the correct rdfvalue to use for this client action.  This code
    # assumes that windows and OS X implementations of actions with the same
    # name (e.g. EnumerateInterfaces) accept and return the same rdfvalue types
    # as their linux counterparts. Non-linux actions are registered in
    # libs/server_stubs.py
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
          raise RuntimeError("Client action expected %s but got %s" %
                             (action.in_rdfvalue, type(request)))

    outbound_id = self.GetNextOutboundId()

    # Create a new request state
    state = rdf_flows.RequestState(id=outbound_id,
                                   session_id=self.session_id,
                                   next_state=next_state,
                                   client_id=client_id)

    if request_data is not None:
      state.data = rdf_protodict.Dict(request_data)

    # Send the message with the request state
    msg = rdf_flows.GrrMessage(session_id=utils.SmartUnicode(self.session_id),
                               name=action_name,
                               request_id=outbound_id,
                               priority=self.args.priority,
                               require_fastpoll=self.args.require_fastpoll,
                               queue=client_id.Queue(),
                               payload=request)

    if self.context.remaining_cpu_quota:
      msg.cpu_limit = int(self.context.remaining_cpu_quota)

    cpu_usage = self.context.client_resources.cpu_usage
    if self.context.args.cpu_limit:
      msg.cpu_limit = max(self.context.args.cpu_limit - cpu_usage.user_cpu_time
                          - cpu_usage.system_cpu_time, 0)

      if msg.cpu_limit == 0:
        raise FlowRunnerError("CPU limit exceeded.")

    if self.context.args.network_bytes_limit:
      msg.network_bytes_limit = max(self.context.args.network_bytes_limit -
                                    self.context.network_bytes_sent, 0)
      if msg.network_bytes_limit == 0:
        raise FlowRunnerError("Network limit exceeded.")

    state.request = msg

    self.QueueRequest(state, timestamp=start_time)

  def Publish(self, event_name, msg, delay=0):
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
    if not isinstance(msg, rdf_flows.GrrMessage):
      msg = rdf_flows.GrrMessage(payload=msg)

    # Randomize the response id or events will get overwritten.
    msg.response_id = msg.task_id = msg.GenerateTaskID()
    # Well known flows always listen for request id 0.
    msg.request_id = 0

    timestamp = None
    if delay:
      timestamp = (
          rdfvalue.RDFDatetime().Now() + delay).AsMicroSecondsFromEpoch()

    # Forward the message to the well known flow's queue.
    for event_urn in handler_urns:
      self.queue_manager.QueueResponse(event_urn, msg)
      self.queue_manager.QueueNotification(session_id=event_urn,
                                           priority=msg.priority,
                                           timestamp=timestamp)

  def CallFlow(self,
               flow_name=None,
               next_state=None,
               sync=True,
               request_data=None,
               client_id=None,
               base_session_id=None,
               output=None,
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

       output: A relative output name for the child collection. Normally
         subflows do not write their own collections, but this can be specified
         to change this behaviour.

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
                              "not declared in decorator." %
                              (self.__class__.__name__,
                               self.context.current_state, next_state))

    client_id = client_id or self.args.client_id

    # This looks very much like CallClient() above - we prepare a request state,
    # and add it to our queue - any responses from the child flow will return to
    # the request state and the stated next_state. Note however, that there is
    # no client_id or actual request message here because we directly invoke the
    # child flow rather than queue anything for it.
    state = rdf_flows.RequestState(
        id=self.GetNextOutboundId(),
        session_id=utils.SmartUnicode(self.session_id),
        client_id=client_id,
        next_state=next_state,
        response_count=0)

    if request_data:
      state.data = rdf_protodict.Dict().FromDict(request_data)

    # If the urn is passed explicitly (e.g. from the hunt runner) use that,
    # otherwise use the urn from the flow_runner args. If both are None, create
    # a new collection and give the urn to the flow object.
    logs_urn = self._GetLogsCollectionURN(kwargs.pop(
        "logs_collection_urn", None) or self.args.logs_collection_urn)

    # If we were called with write_intermediate_results, propagate down to
    # child flows.  This allows write_intermediate_results to be set to True
    # either at the top level parent, or somewhere in the middle of
    # the call chain.
    write_intermediate = (kwargs.pop("write_intermediate_results", False) or
                          getattr(self.args, "write_intermediate_results",
                                  False))

    # Create the new child flow but do not notify the user about it.
    child_urn = self.flow_obj.StartFlow(
        client_id=client_id,
        flow_name=flow_name,
        base_session_id=base_session_id or self.session_id,
        event_id=self.context.get("event_id"),
        request_state=state,
        token=self.token,
        notify_to_user=False,
        parent_flow=self.flow_obj,
        _store=self.data_store,
        sync=sync,
        output=output,
        queue=self.args.queue,
        write_intermediate_results=write_intermediate,
        logs_collection_urn=logs_urn,
        creator=self.context.creator,
        **kwargs)

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
    if self.args.request_state.session_id and self.args.send_replies:

      request_state = self.args.request_state

      request_state.response_count += 1

      # Make a response message
      msg = rdf_flows.GrrMessage(
          session_id=request_state.session_id,
          request_id=request_state.id,
          response_id=request_state.response_count,
          auth_state=rdf_flows.GrrMessage.AuthorizationState.AUTHENTICATED,
          type=rdf_flows.GrrMessage.Type.MESSAGE,
          payload=response,
          args_rdf_name=response.__class__.__name__,
          args_age=int(response.age))

      # Queue the response now
      self.queue_manager.QueueResponse(request_state.session_id, msg)

      if self.args.write_intermediate_results:
        self.context.output.Add(response)
    else:
      # Only write the reply to the collection if we are the parent flow.  This
      # avoids creating a collection for every intermediate flow result.
      self.context.output.Add(response)

    if self.args.client_id:
      # While wrapping the response in GrrMessage is not strictly necessary for
      # output plugins, GrrMessage.source may be used by these plugins to fetch
      # client's metadata and include it into the exported data.
      self.sent_replies.append(rdf_flows.GrrMessage(payload=response,
                                                    source=self.args.client_id))
    else:
      self.sent_replies.append(response)

  def FlushMessages(self):
    """Flushes the messages that were queued."""
    # Only flush queues if we are the top level runner.
    if self.parent_runner is None:
      self.queue_manager.Flush()

  def Error(self, backtrace, client_id=None, status=None):
    """Kills this flow with an error."""
    client_id = client_id or self.args.client_id
    if self.IsRunning():
      # Set an error status
      reply = rdf_flows.GrrStatus()
      if status is None:
        reply.status = rdf_flows.GrrStatus.ReturnedStatus.GENERIC_ERROR
      else:
        reply.status = status

      if backtrace:
        reply.error_message = backtrace

      self.Terminate(status=reply)

      self.context.state = rdf_flows.Flow.State.ERROR

      if backtrace:
        logging.error("Error in flow %s (%s). Trace: %s", self.session_id,
                      client_id, backtrace)
        self.context.backtrace = backtrace
      else:
        logging.error("Error in flow %s (%s).", self.session_id, client_id)

      self.Notify("FlowStatus", client_id,
                  "Flow (%s) terminated due to error" % self.session_id)

  def GetState(self):
    return self.context.state

  def IsRunning(self):
    return self.context.state == rdf_flows.Flow.State.RUNNING

  def ProcessRepliesWithOutputPlugins(self, replies):
    if not self.args.output_plugins or not replies:
      return

    for plugin_descriptor, plugin_state in self.context.output_plugins_states:
      output_plugin = plugin_descriptor.GetPluginForState(plugin_state)

      # Extend our lease if needed.
      self.flow_obj.HeartBeat()
      try:
        output_plugin.ProcessResponses(replies)
        output_plugin.Flush()

        log_item = output_plugin_lib.OutputPluginBatchProcessingStatus(
            plugin_descriptor=plugin_descriptor,
            status="SUCCESS",
            batch_size=len(replies))
        # Proving default here to make graceful deployment possible.
        # TODO(user): remove default in Q1 2016.
        plugin_state.get("logs", []).append(log_item)

        self.Log("Plugin %s sucessfully processed %d flow replies.",
                 plugin_descriptor, len(replies))
      except Exception as e:  # pylint: disable=broad-except
        error = output_plugin_lib.OutputPluginBatchProcessingStatus(
            plugin_descriptor=plugin_descriptor,
            status="ERROR",
            summary=utils.SmartStr(e),
            batch_size=len(replies))
        # Proving default here to make graceful deployment possible.
        # TODO(user): remove default in Q1 2016.
        plugin_state.get("errors", []).append(error)

        self.Log("Plugin %s failed to process %d replies due to: %s",
                 plugin_descriptor, len(replies), e)

  def Terminate(self, status=None):
    """Terminates this flow."""
    try:
      self.queue_manager.DestroyFlowStates(self.session_id)
    except queue_manager.MoreDataException:
      pass

    # This flow might already not be running.
    if self.context.state != rdf_flows.Flow.State.RUNNING:
      return

    try:
      # Close off the output collection.
      if self.output and len(self.output):
        self.output.Close()
        logging.info("%s flow results written to %s", len(self.output),
                     self.output.urn)
        self.output = None

    except access_control.UnauthorizedAccess:
      # This might fail if the output has a pickled token.
      pass

    if self.args.request_state.session_id:
      logging.debug("Terminating flow %s", self.session_id)

      # Make a response or use the existing one.
      response = status or rdf_flows.GrrStatus()

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
      msg = rdf_flows.GrrMessage(
          session_id=request_state.session_id,
          request_id=request_state.id,
          response_id=request_state.response_count,
          auth_state=rdf_flows.GrrMessage.AuthorizationState.AUTHENTICATED,
          type=rdf_flows.GrrMessage.Type.STATUS,
          payload=response)

      try:
        # Queue the response now
        self.queue_manager.QueueResponse(request_state.session_id, msg)
      finally:
        self.QueueNotification(session_id=request_state.session_id)

    # Mark as terminated.
    self.context.state = rdf_flows.Flow.State.TERMINATED
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

  def _QueueRequest(self, request, timestamp=None):
    if request.HasField("request") and request.request.name:
      # This message contains a client request as well.
      self.queue_manager.QueueClientMessage(request.request,
                                            timestamp=timestamp)

    self.queue_manager.QueueRequest(self.session_id,
                                    request,
                                    timestamp=timestamp)

  def IncrementOutstandingRequests(self):
    with self.outbound_lock:
      self.context.outstanding_requests += 1

  def DecrementOutstandingRequests(self):
    with self.outbound_lock:
      self.context.outstanding_requests -= 1

  def QueueRequest(self, request, timestamp=None):
    # Remember the new request for later
    self._QueueRequest(request, timestamp=timestamp)
    self.IncrementOutstandingRequests()

  def ReQueueRequest(self, request, timestamp=None):
    self._QueueRequest(request, timestamp=timestamp)

  def QueueResponse(self, response, timestamp=None):
    self.queue_manager.QueueResponse(self.session_id,
                                     response,
                                     timestamp=timestamp)

  def QueueNotification(self, *args, **kw):
    self.queue_manager.QueueNotification(*args, **kw)

  def SetStatus(self, status):
    self.context.status = status

  def Log(self, format_str, *args):
    """Logs the message using the flow's standard logging.

    Args:
      format_str: Format string
      *args: arguments to the format string
    Raises:
      RuntimeError: on parent missing logs_collection
    """
    format_str = utils.SmartUnicode(format_str)

    status = format_str
    if args:
      try:
        # The status message is always in unicode
        status = format_str % args
      except TypeError:
        logging.error("Tried to log a format string with the wrong number "
                      "of arguments: %s", format_str)

    logging.info("%s: %s", self.session_id, status)

    self.SetStatus(utils.SmartUnicode(status))

    with self.OpenLogsCollection(self.args.logs_collection_urn,
                                 mode="w") as logs_collection:
      logs_collection.Add(rdf_flows.FlowLog(
          client_id=self.args.client_id,
          urn=self.session_id,
          flow_name=self.flow_obj.__class__.__name__,
          log_message=status))

  def GetLog(self):
    return self.OpenLogsCollection(self.args.logs_collection_urn, mode="r")

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
    user = self.context.creator
    # Don't send notifications to system users.
    if self.args.notify_to_user and user not in aff4_users.GRRUser.SYSTEM_USERS:

      # Prefix the message with the hostname of the client we are running
      # against.
      if self.args.client_id:
        client_fd = aff4.FACTORY.Open(self.args.client_id,
                                      mode="rw",
                                      token=self.token)
        hostname = client_fd.Get(client_fd.Schema.HOSTNAME) or ""
        client_msg = "%s: %s" % (hostname, msg)
      else:
        client_msg = msg

      # Add notification to the User object.
      fd = aff4.FACTORY.Create(
          aff4.ROOT_URN.Add("users").Add(user),
          aff4_users.GRRUser,
          mode="rw",
          token=self.token)

      # Queue notifications to the user.
      fd.Notify(message_type, subject, client_msg, self.session_id)
      fd.Close()

      # Add notifications to the flow.
      notification = rdf_flows.Notification(
          type=message_type,
          subject=utils.SmartUnicode(subject),
          message=utils.SmartUnicode(msg),
          source=self.session_id,
          timestamp=rdfvalue.RDFDatetime().Now())

      data_store.DB.Set(self.session_id,
                        aff4.AFF4Object.GRRFlow.SchemaCls.NOTIFICATION,
                        notification,
                        replace=False,
                        sync=False,
                        token=self.token)

      # Disable further notifications.
      self.context.user_notified = True

    # Allow the flow to either specify an event name or an event handler URN.
    notification_event = (self.args.notification_event or
                          self.args.notification_urn)
    if notification_event:
      if self.context.state == rdf_flows.Flow.State.ERROR:
        status = rdf_flows.FlowNotification.Status.ERROR

      else:
        status = rdf_flows.FlowNotification.Status.OK

      event = rdf_flows.FlowNotification(session_id=self.context.session_id,
                                         flow_name=self.args.flow_name,
                                         client_id=self.args.client_id,
                                         status=status)

      self.flow_obj.Publish(notification_event, message=event)
