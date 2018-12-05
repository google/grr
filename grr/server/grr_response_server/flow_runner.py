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
the child flow itself has finished running and is stored into the data store.

The following is a summary of the CallFlow() sequence:

1. The top level flow runner has no parent_runner.

2. The flow calls self.CallFlow() which is delegated to the flow's runner's
   CallFlow() method.

3. The flow runner calls StartAFF4Flow(). This creates a child flow and a new
flow
   runner. The new runner has as a parent the top level flow.

4. The child flow calls CallClient() which schedules some messages for the
   client. Since its runner has a parent runner, the messages are queued on the
   parent runner's message queues.

5. The child flow completes execution of its Start() method, and its state gets
   stored in the data store.

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
from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

import logging
import threading
import traceback


from grr_response_core.lib import rdfvalue
from grr_response_core.lib import utils
from grr_response_core.lib.rdfvalues import client as rdf_client
from grr_response_core.lib.rdfvalues import flows as rdf_flows
from grr_response_core.lib.rdfvalues import protodict as rdf_protodict
from grr_response_core.stats import stats_collector_instance
# Note: OutputPluginDescriptor is also needed implicitly by FlowRunnerArgs
from grr_response_server import aff4
from grr_response_server import data_store
from grr_response_server import flow_responses
from grr_response_server import grr_collections
from grr_response_server import multi_type_collection
from grr_response_server import notification as notification_lib
from grr_response_server import output_plugin as output_plugin_lib
from grr_response_server import queue_manager
from grr_response_server import sequential_collection
from grr_response_server.aff4_objects import users as aff4_users
from grr_response_server.rdfvalues import flow_runner as rdf_flow_runner
from grr_response_server.rdfvalues import objects as rdf_objects


class FlowRunnerError(Exception):
  """Raised when there is an error during state transitions."""


class FlowRunner(object):
  """The flow context class for hunts.

  This is essentially the same as a normal context but it processes
  all the requests that arrive regardless of any order such that one client that
  doesn't respond does not make the whole hunt wait.
  """

  # The queue manager retries to work on requests it could not
  # complete after this many seconds.
  notification_retry_interval = 30

  # Flows who got stuck in the worker for more than this time (in
  # seconds) are forcibly terminated.
  stuck_flows_timeout = 60 * 60 * 6

  def __init__(self, flow_obj, parent_runner=None, runner_args=None,
               token=None):
    """Constructor for the Flow Runner.

    Args:
      flow_obj: The flow object this runner will run states for.
      parent_runner: The parent runner of this runner.
      runner_args: A FlowRunnerArgs() instance containing initial values. If not
        specified, we use the runner_args from the flow_obj.
      token: An instance of access_control.ACLToken security token.
    """
    self.token = token or flow_obj.token
    self.parent_runner = parent_runner

    # If we have a parent runner, we use its queue manager.
    if parent_runner is not None:
      self.queue_manager = parent_runner.queue_manager
    else:
      # Otherwise we use a new queue manager.
      self.queue_manager = queue_manager.QueueManager(token=self.token)
      self.queue_manager.FreezeTimestamp()

    self.queued_replies = []

    self.outbound_lock = threading.Lock()
    self.flow_obj = flow_obj

    # Initialize from a new runner args proto.
    if runner_args is not None:
      self.runner_args = runner_args
      self.session_id = self.GetNewSessionID()
      self.flow_obj.urn = self.session_id

      # Flow state does not have a valid context, we need to create one.
      self.context = self.InitializeContext(runner_args)
      self.flow_obj.context = self.context
      self.context.session_id = self.session_id

    else:
      # Retrieve args from the flow object's context. The flow object is
      # responsible for storing our context, although they do not generally
      # access it directly.
      self.context = self.flow_obj.context

      self.runner_args = self.flow_obj.runner_args

    # Populate the flow object's urn with the session id.
    self.flow_obj.urn = self.session_id = self.context.session_id

    # Sent replies are cached so that they can be processed by output plugins
    # when the flow is saved.
    self.sent_replies = []

  def IsWritingResults(self):
    return (not self.parent_runner or
            self.runner_args.write_intermediate_results)

  def _GetLogCollectionURN(self, logs_collection_urn):
    if self.parent_runner is not None and not logs_collection_urn:
      # We are a child runner, we should have been passed a
      # logs_collection_urn
      raise ValueError("Flow: %s has a parent %s but no logs_collection_urn"
                       " set." % (self.flow_obj.urn, self.parent_runner))

    # If we weren't passed a collection urn, create one in our namespace.
    return logs_collection_urn or self.flow_obj.logs_collection_urn

  def OpenLogCollection(self, logs_collection_urn):
    """Open the parent-flow logs collection for writing or create a new one.

    If we receive a logs_collection_urn here it is being passed from the parent
    flow runner into the new runner created by the flow object.

    For a regular flow the call sequence is:
    flow_runner --StartAFF4Flow--> flow object --CreateRunner--> (new)
    flow_runner

    For a hunt the call sequence is:
    hunt_runner --CallFlow--> flow_runner --StartAFF4Flow--> flow object
     --CreateRunner--> (new) flow_runner

    Args:
      logs_collection_urn: RDFURN pointing to parent logs collection

    Returns:
      The LogCollection.
    Raises:
      ValueError: on parent missing logs_collection.
    """
    return grr_collections.LogCollection(
        self._GetLogCollectionURN(logs_collection_urn))

  def InitializeContext(self, args):
    """Initializes the context of this flow."""
    if args is None:
      args = rdf_flow_runner.FlowRunnerArgs()

    output_plugins_states = []
    for plugin_descriptor in args.output_plugins:
      if not args.client_id:
        self.Log(
            "Not initializing output plugin %s as flow does not run on "
            "the client.", plugin_descriptor.plugin_name)
        continue

      plugin_class = plugin_descriptor.GetPluginClass()
      try:
        plugin, plugin_state = plugin_class.CreatePluginAndDefaultState(
            source_urn=self.flow_obj.output_urn,
            args=plugin_descriptor.plugin_args,
            token=self.token)
        # TODO(amoser): Those do not need to be inside the state, they
        # could be part of the plugin descriptor.
        plugin_state["logs"] = []
        plugin_state["errors"] = []

        output_plugins_states.append(
            rdf_flow_runner.OutputPluginState(
                plugin_state=plugin_state, plugin_descriptor=plugin_descriptor))
      except Exception as e:  # pylint: disable=broad-except
        logging.exception("Plugin %s failed to initialize (%s), ignoring it.",
                          plugin, e)

    parent_creator = None
    if self.parent_runner:
      parent_creator = self.parent_runner.context.creator

    context = rdf_flow_runner.FlowContext(
        create_time=rdfvalue.RDFDatetime.Now(),
        creator=parent_creator or self.token.username,
        current_state="Start",
        output_plugins_states=output_plugins_states,
        state=rdf_flow_runner.FlowContext.State.RUNNING,
    )

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
    base = self.runner_args.base_session_id
    if base is None:
      base = self.runner_args.client_id or aff4.ROOT_URN
      base = base.Add("flows")

    return rdfvalue.SessionID(base=base, queue=self.runner_args.queue)

  def OutstandingRequests(self):
    """Returns the number of all outstanding requests.

    This is used to determine if the flow needs to be destroyed yet.

    Returns:
       the number of all outstanding requests.
    """
    return self.context.outstanding_requests

  def CallState(self, next_state="", start_time=None):
    """This method is used to schedule a new state on a different worker.

    This is basically the same as CallFlow() except we are calling
    ourselves. The state will be invoked at a later time.

    Args:
       next_state: The state in this flow to be invoked.
       start_time: Start the flow at this time. This delays notification for
         flow processing into the future. Note that the flow may still be
         processed earlier if there are client responses waiting.

    Raises:
       FlowRunnerError: if the next state is not valid.
    """
    # Check if the state is valid
    if not getattr(self.flow_obj, next_state):
      raise FlowRunnerError("Next state %s is invalid." % next_state)

    # Queue the response message to the parent flow
    request_state = rdf_flow_runner.RequestState(
        id=self.GetNextOutboundId(),
        session_id=self.context.session_id,
        client_id=self.runner_args.client_id,
        next_state=next_state)

    self.QueueRequest(request_state, timestamp=start_time)

    # Send a fake reply.
    msg = rdf_flows.GrrMessage(
        session_id=self.session_id,
        request_id=request_state.id,
        response_id=1,
        auth_state=rdf_flows.GrrMessage.AuthorizationState.AUTHENTICATED,
        payload=rdf_flows.GrrStatus(),
        type=rdf_flows.GrrMessage.Type.STATUS)
    self.QueueResponse(msg, start_time)

    # Notify the worker about it.
    self.QueueNotification(session_id=self.session_id, timestamp=start_time)

  def ScheduleKillNotification(self):
    """Schedules a kill notification for this flow."""
    # Create a notification for the flow in the future that
    # indicates that this flow is in progess. We'll delete this
    # notification when we're done with processing completed
    # requests. If we're stuck for some reason, the notification
    # will be delivered later and the stuck flow will get
    # terminated.
    kill_timestamp = (rdfvalue.RDFDatetime().Now() + self.stuck_flows_timeout)
    with queue_manager.QueueManager(token=self.token) as manager:
      manager.QueueNotification(
          session_id=self.session_id,
          in_progress=True,
          timestamp=kill_timestamp)

    # kill_timestamp may get updated via flow.HeartBeat() calls, so we
    # have to store it in the context.
    self.context.kill_timestamp = kill_timestamp

  def HeartBeat(self):
    # If kill timestamp is set (i.e. if the flow is currently being
    # processed by the worker), delete the old "kill if stuck" notification
    # and schedule a new one, further in the future.
    if self.context.kill_timestamp:
      with queue_manager.QueueManager(token=self.token) as manager:
        manager.DeleteNotification(
            self.session_id,
            start=self.context.kill_timestamp,
            end=self.context.kill_timestamp + rdfvalue.Duration("1s"))

        self.context.kill_timestamp = (
            rdfvalue.RDFDatetime().Now() + self.stuck_flows_timeout)
        manager.QueueNotification(
            session_id=self.session_id,
            in_progress=True,
            timestamp=self.context.kill_timestamp)

  def FinalizeProcessCompletedRequests(self, notification):
    # Delete kill notification as the flow got processed and is not
    # stuck.
    with queue_manager.QueueManager(token=self.token) as manager:
      manager.DeleteNotification(
          self.session_id,
          start=self.context.kill_timestamp,
          end=self.context.kill_timestamp)
      self.context.kill_timestamp = None

      # If a flow raises in one state, the remaining states will not
      # be processed. This is indistinguishable from an incomplete
      # state due to missing responses / status so we need to check
      # here if the flow is still running before rescheduling.
      if (self.IsRunning() and notification.last_status and
          (self.context.next_processed_request <= notification.last_status)):
        logging.debug("Had to reschedule a notification: %s", notification)
        # We have received a notification for a specific request but
        # could not process that request. This might be a race
        # condition in the data store so we reschedule the
        # notification in the future.
        delay = self.notification_retry_interval
        notification.ttl -= 1
        if notification.ttl:
          manager.QueueNotification(
              notification, timestamp=notification.timestamp + delay)

  def ProcessCompletedRequests(self, notification, unused_thread_pool=None):
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
    """
    self.ScheduleKillNotification()
    try:
      self._ProcessCompletedRequests(notification)
    finally:
      self.FinalizeProcessCompletedRequests(notification)

  def _ProcessCompletedRequests(self, notification):
    """Does the actual processing of the completed requests."""
    # First ensure that client messages are all removed. NOTE: We make a new
    # queue manager here because we want only the client messages to be removed
    # ASAP. This must happen before we actually run the flow to ensure the
    # client requests are removed from the client queues.
    with queue_manager.QueueManager(token=self.token) as manager:
      for request, _ in manager.FetchCompletedRequests(
          self.session_id, timestamp=(0, notification.timestamp)):
        # Requests which are not destined to clients have no embedded request
        # message.
        if request.HasField("request"):
          manager.DeQueueClientRequest(request.request)

    # The flow is dead - remove all outstanding requests and responses.
    if not self.IsRunning():
      self.queue_manager.DestroyFlowStates(self.session_id)
      return

    processing = []
    while True:
      try:
        # Here we only care about completed requests - i.e. those requests with
        # responses followed by a status message.
        for request, responses in self.queue_manager.FetchCompletedResponses(
            self.session_id, timestamp=(0, notification.timestamp)):

          if request.id == 0:
            continue

          if not responses:
            break

          # We are missing a needed request - maybe its not completed yet.
          if request.id > self.context.next_processed_request:
            stats_collector_instance.Get().IncrementCounter(
                "grr_response_out_of_order")
            break

          # Not the request we are looking for - we have seen it before
          # already.
          if request.id < self.context.next_processed_request:
            self.queue_manager.DeleteRequest(request)
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
              stats_collector_instance.Get().IncrementCounter(
                  "grr_request_retransmission_count")
              request.transmission_count += 1
              self.ReQueueRequest(request)
            break

          # If we get here its all good - run the flow.
          if self.IsRunning():
            self.flow_obj.HeartBeat()
            self.RunStateMethod(request.next_state, request, responses)

          # Quit early if we are no longer alive.
          else:
            break

          # At this point we have processed this request - we can remove it and
          # its responses from the queue.
          self.queue_manager.DeleteRequest(request)
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
          stats_collector_instance.Get().IncrementCounter(
              "grr_flow_completed_count")

          stats_collector_instance.Get().IncrementCounter(
              "flow_completions", fields=[self.flow_obj.Name()])
          logging.debug(
              "Destroying session %s(%s) for client %s", self.session_id,
              self.flow_obj.Name(), self.runner_args.client_id)

          self.flow_obj.Terminate()

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

  def _TerminationPending(self):
    if "r" in self.flow_obj.mode:
      pending_termination = self.flow_obj.Get(
          self.flow_obj.Schema.PENDING_TERMINATION)
      if pending_termination:
        self.Error(pending_termination.reason)
        return True
    return False

  def RunStateMethod(self, method_name, request=None, responses=None):
    """Completes the request by calling the state method.

    Args:
      method_name: The name of the state method to call.
      request: A RequestState protobuf.
      responses: A list of GrrMessages responding to the request.
    """
    if self._TerminationPending():
      return

    client_id = None
    try:
      self.context.current_state = method_name
      if request and responses:
        client_id = request.client_id or self.runner_args.client_id
        logging.debug("%s Running %s with %d responses from %s",
                      self.session_id, method_name, len(responses), client_id)

      else:
        logging.debug("%s Running state method %s", self.session_id,
                      method_name)

      # Extend our lease if needed.
      self.flow_obj.HeartBeat()
      try:
        method = getattr(self.flow_obj, method_name)
      except AttributeError:
        raise FlowRunnerError("Flow %s has no state method %s" %
                              (self.flow_obj.__class__.__name__, method_name))

      # Prepare a responses object for the state method to use:
      responses = flow_responses.Responses.FromLegacyResponses(
          request=request, responses=responses)

      self.SaveResourceUsage(responses.status)

      stats_collector_instance.Get().IncrementCounter("grr_worker_states_run")

      if method_name == "Start":
        stats_collector_instance.Get().IncrementCounter(
            "flow_starts", fields=[self.flow_obj.Name()])
        method()
      else:
        method(responses)

      if self.sent_replies:
        self.ProcessRepliesWithOutputPlugins(self.sent_replies)
        self.sent_replies = []

    # We don't know here what exceptions can be thrown in the flow but we have
    # to continue. Thus, we catch everything.
    except Exception as e:  # pylint: disable=broad-except
      # This flow will terminate now

      # TODO(user): Deprecate in favor of 'flow_errors'.
      stats_collector_instance.Get().IncrementCounter("grr_flow_errors")

      stats_collector_instance.Get().IncrementCounter(
          "flow_errors", fields=[self.flow_obj.Name()])
      logging.exception("Flow %s raised %s.", self.session_id, e)

      self.Error(traceback.format_exc(), client_id=client_id)

  def GetNextOutboundId(self):
    with self.outbound_lock:
      my_id = self.context.next_outbound_id
      self.context.next_outbound_id += 1
    return my_id

  def CallClient(self,
                 action_cls,
                 request=None,
                 next_state=None,
                 request_data=None,
                 **kwargs):
    """Calls the client asynchronously.

    This sends a message to the client to invoke an Action. The run
    action may send back many responses. These will be queued by the
    framework until a status message is sent by the client. The status
    message will cause the entire transaction to be committed to the
    specified state.

    Args:
       action_cls: The function to call on the client.
       request: The request to send to the client. If not specified (Or None) we
         create a new RDFValue using the kwargs.
       next_state: The state in this flow, that responses to this message should
         go to.
       request_data: A dict which will be available in the RequestState
         protobuf. The Responses object maintains a reference to this protobuf
         for use in the execution of the state method. (so you can access this
         data by responses.request). Valid values are strings, unicode and
         protobufs.
       **kwargs: These args will be used to construct the client action semantic
         protobuf.

    Raises:
       FlowRunnerError: If called on a flow that doesn't run on a single client.
       ValueError: The request passed to the client does not have the correct
                     type.
    """
    client_id = self.runner_args.client_id
    if client_id is None:
      raise FlowRunnerError("CallClient() is used on a flow which was not "
                            "started with a client.")

    if not isinstance(client_id, rdf_client.ClientURN):
      # Try turning it into a ClientURN
      client_id = rdf_client.ClientURN(client_id)

    if action_cls.in_rdfvalue is None:
      if request:
        raise ValueError(
            "Client action %s does not expect args." % action_cls.__name__)
    else:
      if request is None:
        # Create a new rdf request.
        request = action_cls.in_rdfvalue(**kwargs)
      else:
        # Verify that the request type matches the client action requirements.
        if not isinstance(request, action_cls.in_rdfvalue):
          raise ValueError("Client action expected %s but got %s" %
                           (action_cls.in_rdfvalue, type(request)))

    outbound_id = self.GetNextOutboundId()

    # Create a new request state
    state = rdf_flow_runner.RequestState(
        id=outbound_id,
        session_id=self.session_id,
        next_state=next_state,
        client_id=client_id)

    if request_data is not None:
      state.data = rdf_protodict.Dict(request_data)

    # Send the message with the request state
    msg = rdf_flows.GrrMessage(
        session_id=utils.SmartUnicode(self.session_id),
        name=action_cls.__name__,
        request_id=outbound_id,
        require_fastpoll=self.runner_args.require_fastpoll,
        queue=client_id.Queue(),
        payload=request,
        generate_task_id=True)

    cpu_usage = self.context.client_resources.cpu_usage
    if self.runner_args.cpu_limit:
      msg.cpu_limit = max(
          self.runner_args.cpu_limit - cpu_usage.user_cpu_time -
          cpu_usage.system_cpu_time, 0)

      if msg.cpu_limit == 0:
        raise FlowRunnerError("CPU limit exceeded.")

    if self.runner_args.network_bytes_limit:
      msg.network_bytes_limit = max(
          self.runner_args.network_bytes_limit -
          self.context.network_bytes_sent, 0)
      if msg.network_bytes_limit == 0:
        raise FlowRunnerError("Network limit exceeded.")

    state.request = msg
    self.QueueRequest(state)

  def CallFlow(self,
               flow_name=None,
               next_state=None,
               request_data=None,
               client_id=None,
               base_session_id=None,
               **kwargs):
    """Creates a new flow and send its responses to a state.

    This creates a new flow. The flow may send back many responses which will be
    queued by the framework until the flow terminates. The final status message
    will cause the entire transaction to be committed to the specified state.

    Args:
       flow_name: The name of the flow to invoke.
       next_state: The state in this flow, that responses to this message should
         go to.
       request_data: Any dict provided here will be available in the
         RequestState protobuf. The Responses object maintains a reference to
         this protobuf for use in the execution of the state method. (so you can
         access this data by responses.request). There is no format mandated on
         this data but it may be a serialized protobuf.
       client_id: If given, the flow is started for this client.
       base_session_id: A URN which will be used to build a URN.
       **kwargs: Arguments for the child flow.

    Raises:
       FlowRunnerError: If next_state is not one of the allowed next states.

    Returns:
       The URN of the child flow which was created.
    """
    client_id = client_id or self.runner_args.client_id

    # This looks very much like CallClient() above - we prepare a request state,
    # and add it to our queue - any responses from the child flow will return to
    # the request state and the stated next_state. Note however, that there is
    # no client_id or actual request message here because we directly invoke the
    # child flow rather than queue anything for it.
    state = rdf_flow_runner.RequestState(
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
    logs_urn = self._GetLogCollectionURN(
        kwargs.pop("logs_collection_urn", None) or
        self.runner_args.logs_collection_urn)

    # If we were called with write_intermediate_results, propagate down to
    # child flows.  This allows write_intermediate_results to be set to True
    # either at the top level parent, or somewhere in the middle of
    # the call chain.
    write_intermediate = (
        kwargs.pop("write_intermediate_results", False) or
        self.runner_args.write_intermediate_results)

    # Create the new child flow but do not notify the user about it.
    child_urn = self.flow_obj.StartAFF4Flow(
        client_id=client_id,
        flow_name=flow_name,
        base_session_id=base_session_id or self.session_id,
        request_state=state,
        token=self.token,
        notify_to_user=False,
        parent_flow=self.flow_obj,
        queue=self.runner_args.queue,
        write_intermediate_results=write_intermediate,
        logs_collection_urn=logs_urn,
        sync=True,
        **kwargs)

    self.QueueRequest(state)

    return child_urn

  def SendReply(self, response, tag=None):
    """Allows this flow to send a message to its parent flow.

    If this flow does not have a parent, the message is ignored.

    Args:
      response: An RDFValue() instance to be sent to the parent.
      tag: If specified, tag the result with the following tag. NOTE: supported
        in REL_DB implementation only.

    Raises:
      ValueError: If responses is not of the correct type.
    """
    del tag

    if not isinstance(response, rdfvalue.RDFValue):
      raise ValueError("SendReply can only send a Semantic Value")

    # Only send the reply if we have a parent, indicated by knowing our parent's
    # request state.
    if self.runner_args.request_state.session_id:

      request_state = self.runner_args.request_state

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
      self.queue_manager.QueueResponse(msg)

      if self.runner_args.write_intermediate_results:
        self.QueueReplyForResultCollection(response)

    else:
      # Only write the reply to the collection if we are the parent flow.
      self.QueueReplyForResultCollection(response)

  def FlushQueuedReplies(self):
    if self.queued_replies:
      with data_store.DB.GetMutationPool() as pool:
        for response in self.queued_replies:
          sequential_collection.GeneralIndexedCollection.StaticAdd(
              self.flow_obj.output_urn, response, mutation_pool=pool)
          multi_type_collection.MultiTypeCollection.StaticAdd(
              self.flow_obj.multi_type_output_urn, response, mutation_pool=pool)
      self.queued_replies = []

  def FlushMessages(self):
    """Flushes the messages that were queued."""
    # Only flush queues if we are the top level runner.
    if self.parent_runner is None:
      self.queue_manager.Flush()

  def Error(self, backtrace, client_id=None, status_code=None):
    """Terminates this flow with an error."""
    try:
      self.queue_manager.DestroyFlowStates(self.session_id)
    except queue_manager.MoreDataException:
      pass

    if not self.IsRunning():
      return

    # Set an error status
    reply = rdf_flows.GrrStatus()
    if status_code is None:
      reply.status = rdf_flows.GrrStatus.ReturnedStatus.GENERIC_ERROR
    else:
      reply.status = status_code

    client_id = client_id or self.runner_args.client_id

    if backtrace:
      reply.error_message = backtrace
      logging.error("Error in flow %s (%s). Trace: %s", self.session_id,
                    client_id, backtrace)
      self.context.backtrace = backtrace
    else:
      logging.error("Error in flow %s (%s).", self.session_id, client_id)

    self._SendTerminationMessage(reply)

    self.context.state = rdf_flow_runner.FlowContext.State.ERROR

    if self.ShouldSendNotifications():
      flow_ref = None
      if client_id:
        flow_ref = rdf_objects.FlowReference(
            client_id=client_id.Basename(), flow_id=self.session_id.Basename())
      notification_lib.Notify(
          self.token.username,
          rdf_objects.UserNotification.Type.TYPE_FLOW_RUN_FAILED,
          "Flow (%s) terminated due to error" % self.session_id,
          rdf_objects.ObjectReference(
              reference_type=rdf_objects.ObjectReference.Type.FLOW,
              flow=flow_ref))

    self.flow_obj.Flush()

  def GetState(self):
    return self.context.state

  def IsRunning(self):
    return self.context.state == rdf_flow_runner.FlowContext.State.RUNNING

  def ShouldSendNotifications(self):
    return (self.runner_args.notify_to_user and
            self.context.creator not in aff4_users.GRRUser.SYSTEM_USERS)

  def ProcessRepliesWithOutputPlugins(self, replies):
    """Processes replies with output plugins."""
    for output_plugin_state in self.context.output_plugins_states:
      plugin_descriptor = output_plugin_state.plugin_descriptor
      output_plugin_cls = plugin_descriptor.GetPluginClass()
      output_plugin = output_plugin_cls(
          source_urn=self.flow_obj.urn,
          args=plugin_descriptor.plugin_args,
          token=self.token)

      # Extend our lease if needed.
      self.flow_obj.HeartBeat()
      try:
        output_plugin.ProcessResponses(output_plugin_state.plugin_state,
                                       replies)
        output_plugin.Flush(output_plugin_state.plugin_state)
        output_plugin.UpdateState(output_plugin_state.plugin_state)

        log_item = output_plugin_lib.OutputPluginBatchProcessingStatus(
            plugin_descriptor=plugin_descriptor,
            status="SUCCESS",
            batch_size=len(replies))
        output_plugin_state.Log(log_item)

        self.Log("Plugin %s successfully processed %d flow replies.",
                 plugin_descriptor, len(replies))
      except Exception as e:  # pylint: disable=broad-except
        error = output_plugin_lib.OutputPluginBatchProcessingStatus(
            plugin_descriptor=plugin_descriptor,
            status="ERROR",
            summary=utils.SmartUnicode(e),
            batch_size=len(replies))
        output_plugin_state.Error(error)

        self.Log("Plugin %s failed to process %d replies due to: %s",
                 plugin_descriptor, len(replies), e)

  def _SendTerminationMessage(self, status=None):
    """This notifies the parent flow of our termination."""
    if not self.runner_args.request_state.session_id:
      # No parent flow, nothing to do here.
      return

    if status is None:
      status = rdf_flows.GrrStatus()

    client_resources = self.context.client_resources
    user_cpu = client_resources.cpu_usage.user_cpu_time
    sys_cpu = client_resources.cpu_usage.system_cpu_time
    status.cpu_time_used.user_cpu_time = user_cpu
    status.cpu_time_used.system_cpu_time = sys_cpu
    status.network_bytes_sent = self.context.network_bytes_sent
    status.child_session_id = self.session_id

    request_state = self.runner_args.request_state
    request_state.response_count += 1

    # Make a response message
    msg = rdf_flows.GrrMessage(
        session_id=request_state.session_id,
        request_id=request_state.id,
        response_id=request_state.response_count,
        auth_state=rdf_flows.GrrMessage.AuthorizationState.AUTHENTICATED,
        type=rdf_flows.GrrMessage.Type.STATUS,
        payload=status)

    # Queue the response now
    self.queue_manager.QueueResponse(msg)
    self.QueueNotification(session_id=request_state.session_id)

  def Terminate(self, status=None):
    """Terminates this flow."""
    try:
      self.queue_manager.DestroyFlowStates(self.session_id)
    except queue_manager.MoreDataException:
      pass

    # This flow might already not be running.
    if not self.IsRunning():
      return

    self._SendTerminationMessage(status=status)

    # Mark as terminated.
    self.context.state = rdf_flow_runner.FlowContext.State.TERMINATED
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

    if self.runner_args.cpu_limit:
      if self.runner_args.cpu_limit < (user_cpu_total + system_cpu_total):
        # We have exceeded our limit, stop this flow.
        raise FlowRunnerError("CPU limit exceeded.")

    if self.runner_args.network_bytes_limit:
      if (self.runner_args.network_bytes_limit <
          self.context.network_bytes_sent):
        # We have exceeded our byte limit, stop this flow.
        raise FlowRunnerError("Network bytes limit exceeded.")

  def SaveResourceUsage(self, status):
    """Method to tally resources."""
    if status:
      self.UpdateProtoResources(status)

  def _QueueRequest(self, request, timestamp=None):
    if request.HasField("request") and request.request.name:
      # This message contains a client request as well.
      self.queue_manager.QueueClientMessage(
          request.request, timestamp=timestamp)

    self.queue_manager.QueueRequest(request, timestamp=timestamp)

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
    self.queue_manager.QueueResponse(response, timestamp=timestamp)

  def QueueNotification(self, *args, **kw):
    self.queue_manager.QueueNotification(*args, **kw)

  def QueueReplyForResultCollection(self, response):
    self.queued_replies.append(response)

    if self.runner_args.client_id:
      # While wrapping the response in GrrMessage is not strictly necessary for
      # output plugins, GrrMessage.source may be used by these plugins to fetch
      # client's metadata and include it into the exported data.
      self.sent_replies.append(
          rdf_flows.GrrMessage(
              payload=response, source=self.runner_args.client_id))
    else:
      self.sent_replies.append(response)

  def Log(self, format_str, *args):
    """Logs the message using the flow's standard logging.

    Args:
      format_str: Format string
      *args: arguments to the format string

    Raises:
      ValueError: on parent missing logs_collection
    """
    format_str = utils.SmartUnicode(format_str)

    status = format_str
    if args:
      try:
        # The status message is always in unicode
        status = format_str % args
      except TypeError:
        logging.error(
            "Tried to log a format string with the wrong number "
            "of arguments: %s", format_str)

    logging.info("%s: %s", self.session_id, status)

    self.context.status = utils.SmartUnicode(status)

    log_entry = rdf_flows.FlowLog(
        client_id=self.runner_args.client_id,
        urn=self.session_id,
        flow_name=self.flow_obj.__class__.__name__,
        log_message=status)
    logs_collection_urn = self._GetLogCollectionURN(
        self.runner_args.logs_collection_urn)
    with data_store.DB.GetMutationPool() as pool:
      grr_collections.LogCollection.StaticAdd(
          logs_collection_urn, log_entry, mutation_pool=pool)

  def GetLog(self):
    return self.OpenLogCollection(self.runner_args.logs_collection_urn)
