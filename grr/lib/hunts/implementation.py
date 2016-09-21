#!/usr/bin/env python
"""The implementation of hunts.

A hunt is a mechanism for automatically scheduling flows on a selective subset
of clients, managing these flows, collecting and presenting the combined results
of all these flows.
"""

import threading
import traceback

import logging

from grr.lib import access_control
from grr.lib import aff4
from grr.lib import config_lib
from grr.lib import data_store
from grr.lib import events as events_lib
from grr.lib import flow
from grr.lib import flow_runner
from grr.lib import output_plugin as output_plugin_lib
from grr.lib import queue_manager
from grr.lib import rdfvalue
from grr.lib import registry
from grr.lib import stats
from grr.lib import type_info
from grr.lib import utils
from grr.lib.aff4_objects import aff4_grr
from grr.lib.aff4_objects import multi_type_collection
from grr.lib.aff4_objects import sequential_collection
from grr.lib.hunts import results as hunts_results
from grr.lib.rdfvalues import client as rdf_client
from grr.lib.rdfvalues import flows as rdf_flows
from grr.lib.rdfvalues import hunts as rdf_hunts
from grr.lib.rdfvalues import protodict as rdf_protodict
from grr.lib.rdfvalues import stats as rdf_stats
from grr.server import foreman as rdf_foreman

# TODO(user): Another pickling issue. Remove this asap, this will
# break displaying old hunts though so we will have to keep this
# around for a while.
HuntRunnerArgs = rdf_hunts.HuntRunnerArgs  # pylint: disable=invalid-name


# TODO(user): This name was a bad choice. Leave here for backwards
# compatibility but remove at some point.
class UrnCollection(sequential_collection.IndexedSequentialCollection):
  RDF_TYPE = rdf_client.ClientURN


class ClientUrnCollection(sequential_collection.IndexedSequentialCollection):
  RDF_TYPE = rdf_client.ClientURN


class RDFUrnCollection(sequential_collection.IndexedSequentialCollection):
  RDF_TYPE = rdfvalue.RDFURN


class HuntErrorCollection(sequential_collection.IndexedSequentialCollection):
  RDF_TYPE = rdf_hunts.HuntError


class PluginStatusCollection(sequential_collection.IndexedSequentialCollection):
  RDF_TYPE = output_plugin_lib.OutputPluginBatchProcessingStatus


class HuntRunnerError(Exception):
  """Raised when there is an error during state transitions."""


class HuntResultsMetadata(aff4.AFF4Object):
  """Metadata AFF4 object used by CronHuntOutputFlow."""

  class SchemaCls(aff4.AFF4Object.SchemaCls):
    """AFF4 schema for CronHuntOutputMetadata."""

    NUM_PROCESSED_RESULTS = aff4.Attribute(
        "aff4:num_processed_results",
        rdfvalue.RDFInteger,
        "Number of hunt results already processed by the cron job.",
        versioned=False,
        default=0)

    OUTPUT_PLUGINS = aff4.Attribute(
        "aff4:output_plugins_state_dict",
        rdf_protodict.AttributedDict,
        "Serialized output plugin state.",
        versioned=False)

    OUTPUT_PLUGINS_VERIFICATION_RESULTS = aff4.Attribute(
        "aff4:output_plugins_verification_results",
        output_plugin_lib.OutputPluginVerificationResultsList,
        "Verification results list.",
        versioned=False)


class HuntRunner(object):
  """The runner for hunts.

  This runner implements some slight differences from the regular flows:

  1) Responses are not processed in strict request order. Instead they are
     processed concurrently on a thread pool.

  2) Hunt Errors are not fatal and do not generally terminate the hunt. The hunt
     continues running.

  3) Resources are tallied for each client and as a hunt total.
  """

  def __init__(self, hunt_obj, runner_args=None, token=None):
    """Constructor for the Hunt Runner.

    Args:
      hunt_obj: The hunt object this runner will run states for.
      runner_args: A HuntRunnerArgs() instance containing initial values. If not
        specified, we use the runner_args from the hunt_obj.
      token: An instance of access_control.ACLToken security token.
    """
    self.token = token or hunt_obj.token

    self.queue_manager = queue_manager.QueueManager(token=self.token)

    self.outbound_lock = threading.Lock()
    self.hunt_obj = hunt_obj

    # Initialize from a new runner args proto.
    if runner_args is not None:
      self.runner_args = runner_args
      self.session_id = self.GetNewSessionID()
      self.hunt_obj.urn = self.session_id

      # Create a context.
      self.context = self.InitializeContext(runner_args)
      self.hunt_obj.context = self.context
      self.context.session_id = self.session_id

    else:
      # Retrieve args from the hunts object's context. The hunt object is
      # responsible for storing our context, although they do not generally
      # access it directly.
      self.context = self.hunt_obj.context

      self.runner_args = self.hunt_obj.runner_args

    # Populate the hunt object's urn with the session id.
    self.hunt_obj.urn = self.session_id = self.context.session_id

  @property
  def multi_type_output_urn(self):
    return self.hunt_obj.urn.Add(flow_runner.RESULTS_PER_TYPE_SUFFIX)

  @property
  def output_urn(self):
    return self.hunt_obj.urn.Add(flow_runner.RESULTS_SUFFIX)

  def _GetLogsCollectionURN(self):
    return self.hunt_obj.logs_collection_urn

  def OpenLogsCollection(self, mode="w"):
    """Opens the logs collection for writing or creates a new one.

    Args:
      mode: Mode to use for opening, "r", "w", or "rw".
    Returns:
      FlowLogCollection open with mode.
    """
    return aff4.FACTORY.Create(
        self._GetLogsCollectionURN(),
        flow_runner.FlowLogCollection,
        mode=mode,
        object_exists=True,
        token=self.token)

  def HeartBeat(self):
    pass

  def ProcessCompletedRequests(self, notification, thread_pool):
    """Go through the list of requests and process the completed ones.

    We take a snapshot in time of all requests and responses for this hunt. We
    then process as many completed requests as possible. If responses are not
    quite here we leave it for next time.

    Args:
      notification: The notification object that triggered this processing.
      thread_pool: The thread pool to process the responses on.
    """
    # First ensure that client messages are all removed. NOTE: We make a new
    # queue manager here because we want only the client messages to be removed
    # ASAP. This must happen before we actually run the hunt to ensure the
    # client requests are removed from the client queues.
    with queue_manager.QueueManager(token=self.token) as manager:
      for request, _ in manager.FetchCompletedRequests(
          self.session_id, timestamp=(0, notification.timestamp)):
        # Requests which are not destined to clients have no embedded request
        # message.
        if request.HasField("request"):
          manager.DeQueueClientRequest(request.client_id,
                                       request.request.task_id)

    processing = []
    while True:
      try:
        # Here we only care about completed requests - i.e. those requests with
        # responses followed by a status message.
        for request, responses in self.queue_manager.FetchCompletedResponses(
            self.session_id, timestamp=(0, notification.timestamp)):

          if request.id == 0 or not responses:
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

          # If we get here its all good - run the hunt.
          self.hunt_obj.HeartBeat()
          self._Process(
              request, responses, thread_pool=thread_pool, events=processing)

          # At this point we have processed this request - we can remove it and
          # its responses from the queue.
          self.queue_manager.DeleteFlowRequestStates(self.session_id, request)
          self.context.next_processed_request += 1

        # We are done here.
        return

      except queue_manager.MoreDataException:
        # Join any threads.
        for event in processing:
          event.wait()

        # We did not read all the requests/responses in this run in order to
        # keep a low memory footprint and have to make another pass.
        self.FlushMessages()
        self.hunt_obj.Flush()
        continue

      finally:
        # Join any threads.
        for event in processing:
          event.wait()

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
        client_id = request.client_id or self.runner_args.client_id
        logging.debug("%s Running %s with %d responses from %s",
                      self.session_id, method, len(responses), client_id)

      else:
        logging.debug("%s Running state method %s", self.session_id, method)

      # Extend our lease if needed.
      self.hunt_obj.HeartBeat()
      try:
        method = getattr(self.hunt_obj, method)
      except AttributeError:
        raise flow_runner.FlowRunnerError(
            "Flow %s has no state method %s" %
            (self.hunt_obj.__class__.__name__, method))

      method(
          direct_response=direct_response, request=request, responses=responses)

    # We don't know here what exceptions can be thrown in the flow but we have
    # to continue. Thus, we catch everything.
    except Exception as e:  # pylint: disable=broad-except

      # TODO(user): Deprecate in favor of 'flow_errors'.
      stats.STATS.IncrementCounter("grr_flow_errors")

      stats.STATS.IncrementCounter("flow_errors", fields=[self.hunt_obj.Name()])
      logging.exception("Hunt %s raised %s.", self.session_id, e)

      self.Error(traceback.format_exc(), client_id=client_id)

    finally:
      if event:
        event.set()

  def GetNextOutboundId(self):
    with self.outbound_lock:
      my_id = self.context.next_outbound_id
      self.context.next_outbound_id += 1
    return my_id

  # TODO(user): There is a lot of complexity in the hunt runner to
  # support the use case of hunts calling clients directly. This
  # functionality is only used in a single hunt (StatsHunt). If we
  # found a way to collect that information differently, the hunt
  # runner could be made *a lot* simpler.
  def CallClient(self,
                 action_cls,
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
       action_cls: The function to call on the client.

       request: The request to send to the client. If not specified (Or None) we
             create a new RDFValue using the kwargs.

       next_state: The state in this hunt, that responses to this
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
      raise flow_runner.FlowRunnerError(
          "CallClient() is used on a hunt without giving a client_id.")

    if not isinstance(client_id, rdf_client.ClientURN):
      # Try turning it into a ClientURN
      client_id = rdf_client.ClientURN(client_id)

    if action_cls.in_rdfvalue is None:
      if request:
        raise RuntimeError("Client action %s does not expect args." %
                           action_cls.__name__)
    else:
      if request is None:
        # Create a new rdf request.
        request = action_cls.in_rdfvalue(**kwargs)
      else:
        # Verify that the request type matches the client action requirements.
        if not isinstance(request, action_cls.in_rdfvalue):
          raise RuntimeError("Client action expected %s but got %s" %
                             (action_cls.in_rdfvalue, type(request)))

    outbound_id = self.GetNextOutboundId()

    # Create a new request state
    state = rdf_flows.RequestState(
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
        priority=self.runner_args.priority,
        require_fastpoll=self.runner_args.require_fastpoll,
        queue=client_id.Queue(),
        payload=request,
        generate_task_id=True)

    if self.context.remaining_cpu_quota:
      msg.cpu_limit = int(self.context.remaining_cpu_quota)

    cpu_usage = self.context.client_resources.cpu_usage
    if self.runner_args.cpu_limit:
      msg.cpu_limit = max(self.runner_args.cpu_limit - cpu_usage.user_cpu_time -
                          cpu_usage.system_cpu_time, 0)

      if msg.cpu_limit == 0:
        raise flow_runner.FlowRunnerError("CPU limit exceeded.")

    if self.runner_args.network_bytes_limit:
      msg.network_bytes_limit = max(self.runner_args.network_bytes_limit -
                                    self.context.network_bytes_sent, 0)
      if msg.network_bytes_limit == 0:
        raise flow_runner.FlowRunnerError("Network limit exceeded.")

    state.request = msg

    self.QueueRequest(state, timestamp=start_time)

  def Publish(self, event_name, msg, delay=0):
    """Sends the message to event listeners."""
    events_lib.Events.PublishEvent(
        event_name, msg, delay=delay, token=self.token)

  def CallFlow(self,
               flow_name=None,
               next_state=None,
               sync=True,
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

    Returns:
       The URN of the child flow which was created.
    """
    client_id = client_id or self.runner_args.client_id

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

    # Pass our logs collection urn to the flow object.
    logs_urn = self._GetLogsCollectionURN()

    # If we were called with write_intermediate_results, propagate down to
    # child flows.  This allows write_intermediate_results to be set to True
    # either at the top level parent, or somewhere in the middle of
    # the call chain.
    write_intermediate = kwargs.pop("write_intermediate_results", False)

    # Create the new child flow but do not notify the user about it.
    child_urn = self.hunt_obj.StartFlow(
        base_session_id=base_session_id or self.session_id,
        client_id=client_id,
        creator=self.context.creator,
        flow_name=flow_name,
        logs_collection_urn=logs_urn,
        notify_to_user=False,
        parent_flow=self.hunt_obj,
        queue=self.runner_args.queue,
        request_state=state,
        sync=sync,
        token=self.token,
        write_intermediate_results=write_intermediate,
        **kwargs)

    self.QueueRequest(state)

    return child_urn

  def FlushMessages(self):
    """Flushes the messages that were queued."""
    self.queue_manager.Flush()

  def GetState(self):
    return self.context.state

  def ProcessRepliesWithOutputPlugins(self, replies):
    if not self.runner_args.output_plugins or not replies:
      return
    for output_plugin_state in self.context.output_plugins_states:
      plugin_descriptor = output_plugin_state.plugin_descriptor
      plugin_state = output_plugin_state.plugin_state
      output_plugin = plugin_descriptor.GetPluginForState(plugin_state)

      # Extend our lease if needed.
      self.hunt_obj.HeartBeat()
      try:
        output_plugin.ProcessResponses(replies)
        output_plugin.Flush()

        log_item = output_plugin.OutputPluginBatchProcessingStatus(
            plugin_descriptor=plugin_descriptor,
            status="SUCCESS",
            batch_size=len(replies))
        # Cannot append to lists in AttributedDicts.
        plugin_state["logs"] += [log_item]

        self.Log("Plugin %s sucessfully processed %d flow replies.",
                 plugin_descriptor, len(replies))
      except Exception as e:  # pylint: disable=broad-except
        error = output_plugin.OutputPluginBatchProcessingStatus(
            plugin_descriptor=plugin_descriptor,
            status="ERROR",
            summary=utils.SmartStr(e),
            batch_size=len(replies))
        # Cannot append to lists in AttributedDicts.
        plugin_state["errors"] += [error]

        self.Log("Plugin %s failed to process %d replies due to: %s",
                 plugin_descriptor, len(replies), e)

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
        raise flow_runner.FlowRunnerError("CPU limit exceeded.")

    if self.runner_args.network_bytes_limit:
      if (self.runner_args.network_bytes_limit <
          self.runner_args.network_bytes_sent):
        # We have exceeded our byte limit, stop this flow.
        raise flow_runner.FlowRunnerError("Network bytes limit exceeded.")

  def _QueueRequest(self, request, timestamp=None):
    if request.HasField("request") and request.request.name:
      # This message contains a client request as well.
      self.queue_manager.QueueClientMessage(
          request.request, timestamp=timestamp)

    self.queue_manager.QueueRequest(
        self.session_id, request, timestamp=timestamp)

  def QueueRequest(self, request, timestamp=None):
    # Remember the new request for later
    self._QueueRequest(request, timestamp=timestamp)

  def ReQueueRequest(self, request, timestamp=None):
    self._QueueRequest(request, timestamp=timestamp)

  def QueueResponse(self, response, timestamp=None):
    self.queue_manager.QueueResponse(
        self.session_id, response, timestamp=timestamp)

  def QueueNotification(self, *args, **kw):
    self.queue_manager.QueueNotification(*args, **kw)

  def SetStatus(self, status):
    self.context.status = status

  def GetLog(self):
    return self.OpenLogsCollection(mode="r")

  def Status(self, format_str, *args):
    """Flows can call this method to set a status message visible to users."""
    self.Log(format_str, *args)

  def _AddClient(self, client_id):
    next_client_due = self.hunt_obj.context.next_client_due
    if self.runner_args.client_rate > 0:
      self.hunt_obj.context.next_client_due = (
          next_client_due + 60.0 / self.runner_args.client_rate)
      self.CallState(
          messages=[client_id],
          next_state="RegisterClient",
          client_id=client_id,
          start_time=next_client_due)
    else:
      self._RegisterAndRunClient(client_id)

  def _RegisterAndRunClient(self, client_id):
    self.hunt_obj.RegisterClient(client_id)
    self.RunStateMethod("RunClient", direct_response=[client_id])

  def _Process(self, request, responses, thread_pool=None, events=None):
    """Hunts process all responses concurrently in a threadpool."""
    # This function is called and runs within the main processing thread. We do
    # not need to lock the hunt object while running in this method.
    if request.next_state == "AddClient":
      if not self.IsHuntStarted():
        logging.debug(
            "Unable to start client %s on hunt %s which is in state %s",
            request.client_id, self.session_id,
            self.hunt_obj.Get(self.hunt_obj.Schema.STATE))
        return

      # Get the client count.
      client_count = int(
          self.hunt_obj.Get(self.hunt_obj.Schema.CLIENT_COUNT, 0))

      # Stop the hunt if we exceed the client limit.
      if 0 < self.runner_args.client_limit <= client_count:
        # Remove our rules from the foreman so we dont get more clients sent to
        # this hunt. Hunt will be paused.
        self.Pause()

        # Ignore this client since it had gone over the limit.
        return

      # Update the client count.
      self.hunt_obj.Set(self.hunt_obj.Schema.CLIENT_COUNT(client_count + 1))

      # Add client to list of clients and optionally run it
      # (if client_rate == 0).
      self._AddClient(request.client_id)
      return

    if request.next_state == "RegisterClient":
      state = self.hunt_obj.Get(self.hunt_obj.Schema.STATE)
      # This allows the client limit to operate with a client rate. We still
      # want clients to get registered for the hunt at times in the future.
      # After they have been run, hunts only ever go into the paused state by
      # hitting the client limit. If a user stops a hunt, it will go into the
      # "STOPPED" state.
      if state in ["STARTED", "PAUSED"]:
        self._RegisterAndRunClient(request.client_id)
      else:
        logging.debug(
            "Not starting client %s on hunt %s which is not running: %s",
            request.client_id, self.session_id,
            self.hunt_obj.Get(self.hunt_obj.Schema.STATE))
      return

    event = threading.Event()
    events.append(event)
    # In a hunt, all requests are independent and can be processed
    # in separate threads.
    thread_pool.AddTask(
        target=self.RunStateMethod,
        args=(request.next_state, request, responses, event),
        name="Hunt processing")

  def Log(self, format_str, *args):
    """Logs the message using the hunt's standard logging.

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

    log_entry = rdf_flows.FlowLog(
        client_id=None,
        urn=self.session_id,
        flow_name=self.hunt_obj.__class__.__name__,
        log_message=status)
    logs_collection_urn = self._GetLogsCollectionURN()
    flow_runner.FlowLogCollection.StaticAdd(logs_collection_urn, self.token,
                                            log_entry)

  def Error(self, backtrace, client_id=None):
    """Logs an error for a client but does not terminate the hunt."""
    logging.error("Hunt Error: %s", backtrace)
    self.hunt_obj.LogClientError(client_id, backtrace=backtrace)

  def SaveResourceUsage(self, request, responses):
    """Update the resource usage of the hunt."""
    # Per client stats.
    self.hunt_obj.ProcessClientResourcesStats(request.client_id,
                                              responses.status)
    # Overall hunt resource usage.
    self.UpdateProtoResources(responses.status)

  def InitializeContext(self, args):
    """Initializes the context of this hunt."""
    if args is None:
      args = rdf_hunts.HuntRunnerArgs()

    context = rdf_hunts.HuntContext(
        create_time=rdfvalue.RDFDatetime.Now(),
        creator=self.token.username,
        expires=args.expiry_time.Expiry(),
        start_time=rdfvalue.RDFDatetime.Now(),
        usage_stats=rdf_stats.ClientResourcesStats(),
        remaining_cpu_quota=args.cpu_limit,)

    return context

  def GetNewSessionID(self, **_):
    """Returns a random integer session ID for this hunt.

    All hunts are created under the aff4:/hunts namespace.

    Returns:
      a formatted session id string.
    """
    return rdfvalue.SessionID(base="aff4:/hunts", queue=self.runner_args.queue)

  def _CreateAuditEvent(self, event_action):
    event = events_lib.AuditEvent(
        user=self.hunt_obj.token.username,
        action=event_action,
        urn=self.hunt_obj.urn,
        description=self.runner_args.description)
    events_lib.Events.PublishEvent("Audit", event, token=self.hunt_obj.token)

  def Start(self):
    """This uploads the rules to the foreman and, thus, starts the hunt."""
    # We are already running.
    if self.hunt_obj.Get(self.hunt_obj.Schema.STATE) == "STARTED":
      return

    # Check the permissions for the hunt here. Note that
    # self.runner_args.token is the original creators's token, while
    # the aff4 object was created with the caller's token. This check
    # therefore ensures that the caller to this method has permissions
    # to start the hunt (not necessarily the original creator of the
    # hunt).
    data_store.DB.security_manager.CheckHuntAccess(self.hunt_obj.token,
                                                   self.session_id)

    # Determine when this hunt will expire.
    self.context.expires = self.runner_args.expiry_time.Expiry()

    # When the next client can be scheduled. Implements gradual client
    # recruitment rate according to the client_rate.
    self.context.next_client_due = rdfvalue.RDFDatetime.Now()

    self._CreateAuditEvent("HUNT_STARTED")

    # Start the hunt.
    self.hunt_obj.Set(self.hunt_obj.Schema.STATE("STARTED"))
    self.hunt_obj.Flush()

    if self.runner_args.add_foreman_rules:
      self._AddForemanRule()

  def _AddForemanRule(self):
    """Adds a foreman rule for this hunt."""
    foreman_rule = rdf_foreman.ForemanRule(
        created=rdfvalue.RDFDatetime.Now(),
        expires=self.context.expires,
        description="Hunt %s %s" %
        (self.session_id, self.runner_args.hunt_name),
        client_rule_set=self.runner_args.client_rule_set)

    foreman_rule.actions.Append(
        hunt_id=self.session_id,
        hunt_name=self.runner_args.hunt_name,
        client_limit=self.runner_args.client_limit)

    # Make sure the rule makes sense.
    foreman_rule.Validate()

    with aff4.FACTORY.Open(
        "aff4:/foreman",
        mode="rw",
        token=self.token,
        aff4_type=aff4_grr.GRRForeman,
        ignore_cache=True) as foreman:
      foreman_rules = foreman.Get(foreman.Schema.RULES,
                                  default=foreman.Schema.RULES())
      foreman_rules.Append(foreman_rule)
      foreman.Set(foreman_rules)

  def _RemoveForemanRule(self):
    with aff4.FACTORY.Open(
        "aff4:/foreman", mode="rw", token=self.token,
        ignore_cache=True) as foreman:
      aff4_rules = foreman.Get(foreman.Schema.RULES)
      aff4_rules = foreman.Schema.RULES(
          # Remove those rules which fire off this hunt id.
          [r for r in aff4_rules if r.hunt_id != self.session_id])
      foreman.Set(aff4_rules)

  def _Complete(self):
    """Marks the hunt as completed."""
    self._RemoveForemanRule()
    if "w" in self.hunt_obj.mode:
      self.hunt_obj.Set(self.hunt_obj.Schema.STATE("COMPLETED"))
      self.hunt_obj.Flush()

  def Pause(self):
    """Pauses the hunt (removes Foreman rules, does not touch expiry time)."""
    if not self.IsHuntStarted():
      return

    # Make sure the user is allowed to pause this hunt.
    data_store.DB.security_manager.CheckHuntAccess(self.hunt_obj.token,
                                                   self.session_id)

    self._RemoveForemanRule()

    self.hunt_obj.Set(self.hunt_obj.Schema.STATE("PAUSED"))
    self.hunt_obj.Flush()

    self._CreateAuditEvent("HUNT_PAUSED")

  def Stop(self):
    """Cancels the hunt (removes Foreman rules, resets expiry time to 0)."""
    # Make sure the user is allowed to stop this hunt.
    data_store.DB.security_manager.CheckHuntAccess(self.hunt_obj.token,
                                                   self.session_id)

    self._RemoveForemanRule()
    self.hunt_obj.Set(self.hunt_obj.Schema.STATE("STOPPED"))
    self.hunt_obj.Flush()

    self._CreateAuditEvent("HUNT_STOPPED")

  def IsCompleted(self):
    return self.hunt_obj.Get(self.hunt_obj.Schema.STATE) == "COMPLETED"

  def IsHuntExpired(self):
    return self.context.expires < rdfvalue.RDFDatetime.Now()

  def IsHuntStarted(self):
    """Is this hunt considered started?

    This method is used to check if new clients should be processed by
    this hunt. Note that child flow responses are always processed but
    new clients are not allowed to be scheduled unless the hunt is
    started.

    Returns:
      If a new client is allowed to be scheduled on this hunt.

    """
    state = self.hunt_obj.Get(self.hunt_obj.Schema.STATE)
    if state != "STARTED":
      return False

    # Stop the hunt due to expiry.
    if self.CheckExpiry():
      return False

    return True

  def CheckExpiry(self):
    if self.IsHuntExpired():
      self._Complete()
      return True
    return False

  def CallState(self,
                messages=None,
                next_state="",
                client_id=None,
                request_data=None,
                start_time=None):
    """This method is used to asynchronously schedule a new hunt state.

    The state will be invoked in a later time and receive all the messages
    we send.

    Args:
      messages: A list of rdfvalues to send. If the last one is not a
              GrrStatus, we append an OK Status.

      next_state: The state in this hunt to be invoked with the responses.

      client_id: ClientURN to use in scheduled requests.

      request_data: Any dict provided here will be available in the
                    RequestState protobuf. The Responses object maintains a
                    reference to this protobuf for use in the execution of the
                    state method. (so you can access this data by
                    responses.request).

      start_time: Schedule the state at this time. This delays notification
                  and messages for processing into the future.
    Raises:
      ValueError: on arguments error.
    """

    if messages is None:
      messages = []

    if not next_state:
      raise ValueError("next_state can't be empty.")

    # Now we construct a special response which will be sent to the hunt
    # flow. Randomize the request_id so we do not overwrite other messages in
    # the queue.
    request_state = rdf_flows.RequestState(
        id=utils.PRNG.GetULong(),
        session_id=self.context.session_id,
        client_id=client_id,
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
        raise flow_runner.FlowRunnerError("Bad message %s of type %s." %
                                          (payload, type(payload)))

      self.QueueResponse(msg, timestamp=start_time)

    # Add the status message if needed.
    if not messages or not isinstance(messages[-1], rdf_flows.GrrStatus):
      messages.append(rdf_flows.GrrStatus())

    # Notify the worker about it.
    self.QueueNotification(session_id=self.session_id, timestamp=start_time)


class GRRHunt(flow.FlowBase):
  """The GRR Hunt class."""

  class SchemaCls(flow.FlowBase.SchemaCls):
    """The schema for hunts.

    This object stores the persistent information for the hunt.
    """

    HUNT_ARGS = aff4.Attribute(
        "aff4:hunt_args",
        rdf_protodict.EmbeddedRDFValue,
        "The arguments for this hunt.",
        "HuntArgs",
        versioned=False,
        creates_new_object_version=False)

    HUNT_CONTEXT = aff4.Attribute(
        "aff4:hunt_context",
        rdf_hunts.HuntContext,
        "The metadata for this hunt.",
        "HuntContext",
        versioned=False,
        creates_new_object_version=False)

    HUNT_RUNNER_ARGS = aff4.Attribute(
        "aff4:hunt_runner_args",
        rdf_hunts.HuntRunnerArgs,
        "The runner arguments used for this hunt.",
        "HuntRunnerArgs",
        versioned=False,
        creates_new_object_version=False)

    CLIENT_COUNT = aff4.Attribute(
        "aff4:client_count",
        rdfvalue.RDFInteger,
        "The total number of clients scheduled.",
        versioned=False,
        creates_new_object_version=False)

    # This needs to be kept out the args semantic value since must be updated
    # without taking a lock on the hunt object.
    STATE = aff4.Attribute(
        "aff4:hunt_state",
        rdfvalue.RDFString,
        "The state of a hunt can be "
        "'STARTED': running, "
        "'STOPPED': stopped by the user, "
        "'PAUSED': paused due to client limit, "
        "'COMPLETED': hunt has met its expiry time. New hunts are created in"
        " the PAUSED state.",
        versioned=False,
        lock_protected=False,
        creates_new_object_version=False,
        default="PAUSED")

  args_type = None

  def Initialize(self):
    super(GRRHunt, self).Initialize()
    # Hunts run in multiple threads so we need to protect access.
    self.lock = threading.RLock()
    self.processed_responses = False

    if "r" in self.mode:
      self.client_count = self.Get(self.Schema.CLIENT_COUNT)
      self.runner_args = self.Get(self.Schema.HUNT_RUNNER_ARGS)
      self.context = self.Get(self.Schema.HUNT_CONTEXT)

      args = self.Get(self.Schema.HUNT_ARGS)
      if args:
        self.args = args.payload
      else:
        self.args = None

      # TODO(user): Backwards compatibility hack. Remove this once
      # there are no legacy hunts left we still need to display in the UI.
      if self.context is None and self.runner_args is None:
        state_attr = "aff4:flow_state"
        serialized_state = self.synced_attributes[state_attr][0].serialized
        state = rdf_flows.FlowState.FromSerializedString(serialized_state)
        if state is not None:
          self.context = state.context
          self.runner_args = self.context.args
          self.mode = "r"
          self.args = state.args

      self.Load()

    if self.state is None:
      self.state = flow.AttributedDict()

  def CreateRunner(self, **kw):
    """Make a new runner."""
    self.runner = HuntRunner(self, token=self.token, **kw)
    return self.runner

  @property
  def logs_collection_urn(self):
    return self.urn.Add("Logs")

  @property
  def all_clients_collection_urn(self):
    return self.urn.Add("AllClients")

  @property
  def completed_clients_collection_urn(self):
    return self.urn.Add("CompletedClients")

  @property
  def clients_errors_collection_urn(self):
    return self.urn.Add("ErrorClients")

  @property
  def clients_with_results_collection_urn(self):
    return self.urn.Add("ClientsWithResults")

  @property
  def output_plugins_status_collection_urn(self):
    return self.urn.Add("OutputPluginsStatus")

  @property
  def output_plugins_errors_collection_urn(self):
    return self.urn.Add("OutputPluginsErrors")

  @property
  def multi_type_output_urn(self):
    return self.urn.Add("ResultsPerType")

  @property
  def results_metadata_urn(self):
    return self.urn.Add("ResultsMetadata")

  @property
  def results_collection_urn(self):
    return self.urn.Add("Results")

  @property
  def output_plugins_base_urn(self):
    return self.urn.Add("Results")

  @property
  def creator(self):
    return self.context.creator

  def _AddURNToCollection(self, urn, collection_urn):
    ClientUrnCollection.StaticAdd(collection_urn, self.token, urn)

  def _AddHuntErrorToCollection(self, error, collection_urn):
    HuntErrorCollection.StaticAdd(collection_urn, self.token, error)

  def _GetCollectionItems(self, collection_urn):
    collection = aff4.FACTORY.Open(collection_urn, mode="r", token=self.token)
    return collection.GenerateItems()

  def _ClientSymlinkUrn(self, client_id):
    return client_id.Add("flows").Add("%s:hunt" % (self.urn.Basename()))

  def RegisterClient(self, client_urn):
    self._AddURNToCollection(client_urn, self.all_clients_collection_urn)

  def RegisterCompletedClient(self, client_urn):
    self._AddURNToCollection(client_urn, self.completed_clients_collection_urn)

  def RegisterClientWithResults(self, client_urn):
    self._AddURNToCollection(client_urn,
                             self.clients_with_results_collection_urn)

  def RegisterClientError(self, client_id, log_message=None, backtrace=None):
    error = rdf_hunts.HuntError(client_id=client_id, backtrace=backtrace)
    if log_message:
      error.log_message = utils.SmartUnicode(log_message)

    self._AddHuntErrorToCollection(error, self.clients_errors_collection_urn)

  def OnDelete(self, deletion_pool=None):
    super(GRRHunt, self).OnDelete(deletion_pool=deletion_pool)

    # Delete all the symlinks in the clients namespace that point to the flows
    # initiated by this hunt.
    children_urns = deletion_pool.ListChildren(self.urn)
    clients_ids = []
    for urn in children_urns:
      try:
        clients_ids.append(rdf_client.ClientURN(urn.Basename()))
      except type_info.TypeValueError:
        # Ignore children that are not valid clients ids.
        continue

    symlinks_urns = [self._ClientSymlinkUrn(client_id)
                     for client_id in clients_ids]
    deletion_pool.MultiMarkForDeletion(symlinks_urns)

  @flow.StateHandler()
  def RunClient(self, client_id):
    """This method runs the hunt on a specific client.

    Note that this method holds a lock on the hunt object and runs in the main
    thread. It is safe to access any hunt parameters from here.

    Args:
      client_id: The new client assigned to this hunt.
    """

  @classmethod
  def StartHunt(cls, args=None, runner_args=None, **kwargs):
    """This class method creates new hunts."""
    # Build the runner args from the keywords.
    if runner_args is None:
      runner_args = rdf_hunts.HuntRunnerArgs()

    cls.FilterArgsFromSemanticProtobuf(runner_args, kwargs)

    # Is the required flow a known flow?
    if (runner_args.hunt_name not in cls.classes or
        not aff4.issubclass(cls.classes[runner_args.hunt_name], GRRHunt)):
      raise RuntimeError("Unable to locate hunt %s" % runner_args.hunt_name)

    # Make a new hunt object and initialize its runner.
    hunt_obj = aff4.FACTORY.Create(
        None,
        cls.classes[runner_args.hunt_name],
        mode="w",
        token=runner_args.token)

    # Hunt is called using keyword args. We construct an args proto from the
    # kwargs..
    if hunt_obj.args_type and args is None:
      args = hunt_obj.args_type()
      cls.FilterArgsFromSemanticProtobuf(args, kwargs)

    if hunt_obj.args_type and not isinstance(args, hunt_obj.args_type):
      raise RuntimeError("Hunt args must be instance of %s" %
                         hunt_obj.args_type)

    if kwargs:
      raise type_info.UnknownArg("Unknown parameters to StartHunt: %s" % kwargs)

    # Store the hunt args.
    hunt_obj.args = args
    hunt_obj.runner_args = runner_args

    # Hunts are always created in the paused state. The runner method Start
    # should be called to start them.
    hunt_obj.Set(hunt_obj.Schema.STATE("PAUSED"))

    runner = hunt_obj.CreateRunner(runner_args=runner_args)
    # Allow the hunt to do its own initialization.
    runner.RunStateMethod("Start")

    hunt_obj.Flush()

    try:
      flow_name = args.flow_runner_args.flow_name
    except AttributeError:
      flow_name = ""

    event = events_lib.AuditEvent(
        user=runner_args.token.username,
        action="HUNT_CREATED",
        urn=hunt_obj.urn,
        flow_name=flow_name,
        description=runner_args.description)
    events_lib.Events.PublishEvent("Audit", event, token=runner_args.token)

    return hunt_obj

  @classmethod
  def StartClients(cls, hunt_id, client_ids, token=None):
    """This method is called by the foreman for each client it discovers.

    Note that this function is performance sensitive since it is called by the
    foreman for every client which needs to be scheduled.

    Args:
      hunt_id: The hunt to schedule.
      client_ids: List of clients that should be added to the hunt.
      token: An optional access token to use.
    """
    token = token or access_control.ACLToken(username="Hunt", reason="hunting")

    with queue_manager.QueueManager(token=token) as flow_manager:
      for client_id in client_ids:
        # Now we construct a special response which will be sent to the hunt
        # flow. Randomize the request_id so we do not overwrite other messages
        # in the queue.
        state = rdf_flows.RequestState(
            id=utils.PRNG.GetULong(),
            session_id=hunt_id,
            client_id=client_id,
            next_state="AddClient")

        # Queue the new request.
        flow_manager.QueueRequest(hunt_id, state)

        # Send a response.
        msg = rdf_flows.GrrMessage(
            session_id=hunt_id,
            request_id=state.id,
            response_id=1,
            auth_state=rdf_flows.GrrMessage.AuthorizationState.AUTHENTICATED,
            type=rdf_flows.GrrMessage.Type.STATUS,
            payload=rdf_flows.GrrStatus())

        flow_manager.QueueResponse(hunt_id, msg)

        # And notify the worker about it.
        flow_manager.QueueNotification(session_id=hunt_id)

  def Run(self):
    """A shortcut method for starting the hunt."""
    self.GetRunner().Start()

  def Pause(self):
    """A shortcut method for pausing the hunt."""
    self.GetRunner().Pause()

  def Stop(self):
    """A shortcut method for stopping the hunt."""
    self.GetRunner().Stop()

  def AddResultsToCollection(self, responses, client_id):
    if responses.success:
      with self.lock:
        self.processed_responses = True

        msgs = [rdf_flows.GrrMessage(
            payload=response, source=client_id) for response in responses]

        for msg in msgs:
          hunts_results.HuntResultCollection.StaticAdd(
              self.results_collection_urn, self.token, msg)

        for msg in msgs:
          multi_type_collection.MultiTypeCollection.StaticAdd(
              self.multi_type_output_urn, self.token, msg)

        if responses:
          self.RegisterClientWithResults(client_id)

        # Update stats.
        stats.STATS.IncrementCounter("hunt_results_added", delta=len(msgs))
    else:
      self.LogClientError(
          client_id, log_message=utils.SmartStr(responses.status))

  def CallFlow(self,
               flow_name=None,
               next_state=None,
               request_data=None,
               client_id=None,
               **kwargs):
    """Create a new child flow from a hunt."""
    base_session_id = None
    if client_id:
      # The flow is stored in the hunt namespace,
      base_session_id = self.urn.Add(client_id.Basename())

    # Actually start the new flow.
    child_urn = self.runner.CallFlow(
        flow_name=flow_name,
        next_state=next_state,
        base_session_id=base_session_id,
        client_id=client_id,
        request_data=request_data,
        **kwargs)

    if client_id:
      # But we also create a symlink to it from the client's namespace.
      hunt_link_urn = client_id.Add("flows").Add("%s:hunt" %
                                                 (self.urn.Basename()))

      hunt_link = aff4.FACTORY.Create(
          hunt_link_urn, aff4.AFF4Symlink, token=self.token)

      hunt_link.Set(hunt_link.Schema.SYMLINK_TARGET(child_urn))
      hunt_link.Close()

    return child_urn

  def HeartBeat(self):
    if self.locked:
      lease_time = config_lib.CONFIG["Worker.flow_lease_time"]
      if self.CheckLease() < lease_time / 2:
        logging.info("%s: Extending Lease", self.session_id)
        self.UpdateLease(lease_time)
    else:
      logging.warning("%s is heartbeating while not being locked.", self.urn)

  def Name(self):
    return self.runner_args.hunt_name

  def SetDescription(self, description=None):
    self.runner_args.description = description or ""

  @flow.StateHandler()
  def Start(self):
    """Initializes this hunt from arguments."""

    with data_store.DB.GetMutationPool(token=self.token) as mutation_pool:
      self.CreateCollections(mutation_pool)

    if not self.runner_args.description:
      self.SetDescription()

  def _SetupOutputPluginState(self):
    state = rdf_protodict.AttributedDict()
    try:
      plugins_descriptors = self.args.output_plugins
    except AttributeError:
      plugins_descriptors = []

    for index, plugin_descriptor in enumerate(plugins_descriptors):
      output_base_urn = self.output_plugins_base_urn.Add(
          plugin_descriptor.plugin_name)

      plugin_class = plugin_descriptor.GetPluginClass()
      plugin_obj = plugin_class(
          self.results_collection_urn,
          output_base_urn=output_base_urn,
          args=plugin_descriptor.plugin_args,
          token=self.token)

      state["%s_%d" % (plugin_descriptor.plugin_name, index)] = [
          plugin_descriptor, plugin_obj.state
      ]

    return state

  def CreateCollections(self, mutation_pool):
    with aff4.FACTORY.Create(
        self.results_metadata_urn,
        HuntResultsMetadata,
        mutation_pool=mutation_pool,
        mode="rw",
        token=self.token) as results_metadata:

      state = self._SetupOutputPluginState()
      results_metadata.Set(results_metadata.Schema.OUTPUT_PLUGINS(state))

    for urn, collection_type in [
        # Collection for results.
        (self.results_collection_urn, hunts_results.HuntResultCollection),

        # Collection for per-type results.
        (self.multi_type_output_urn, multi_type_collection.MultiTypeCollection),

        # Collection for logs.
        (self.logs_collection_urn, flow_runner.FlowLogCollection),

        # Collections for urns.
        (self.all_clients_collection_urn, ClientUrnCollection),
        (self.completed_clients_collection_urn, ClientUrnCollection),
        (self.clients_with_results_collection_urn, ClientUrnCollection),

        # Collection for errors.
        (self.clients_errors_collection_urn, HuntErrorCollection),

        # Collections for PluginStatus messages.
        (self.output_plugins_status_collection_urn, PluginStatusCollection),
        (self.output_plugins_errors_collection_urn, PluginStatusCollection),
    ]:
      with aff4.FACTORY.Create(
          urn,
          collection_type,
          mutation_pool=mutation_pool,
          mode="w",
          token=self.token):
        pass

  def MarkClientDone(self, client_id):
    """Adds a client_id to the list of completed tasks."""
    self.RegisterCompletedClient(client_id)

    if self.runner_args.notification_event:
      status = rdf_hunts.HuntNotification(
          session_id=self.session_id, client_id=client_id)
      self.Publish(self.runner_args.notification_event, status)

  def LogClientError(self, client_id, log_message=None, backtrace=None):
    """Logs an error for a client."""
    self.RegisterClientError(
        client_id, log_message=log_message, backtrace=backtrace)

  def ProcessClientResourcesStats(self, client_id, status):
    """Process status message from a client and update the stats.

    This method may be implemented in the subclasses. It's called
    once *per every hunt's state per every client*.

    Args:
      client_id: Client id.
      status: Status returned from the client.
    """

  def GetClientsCounts(self):
    collections = aff4.FACTORY.MultiOpen(
        [self.all_clients_collection_urn, self.completed_clients_collection_urn,
         self.clients_errors_collection_urn],
        mode="r",
        token=self.token)

    collections_dict = dict((coll.urn, coll) for coll in collections)

    def CollectionLen(collection_urn):
      if collection_urn in collections_dict:
        return collections_dict[collection_urn].CalculateLength()
      else:
        return 0

    all_clients_count = CollectionLen(self.all_clients_collection_urn)
    completed_clients_count = CollectionLen(
        self.completed_clients_collection_urn)
    clients_errors_count = CollectionLen(self.clients_errors_collection_urn)

    return all_clients_count, completed_clients_count, clients_errors_count

  def GetClientsErrors(self, client_id=None):
    errors = self._GetCollectionItems(self.clients_errors_collection_urn)
    if not client_id:
      return errors
    else:
      return [error for error in errors if error.client_id == client_id]

  def GetClients(self):
    return set(self._GetCollectionItems(self.all_clients_collection_urn))

  def GetClientsByStatus(self):
    """Get all the clients in a dict of {status: [client_list]}."""
    started = set(self._GetCollectionItems(self.all_clients_collection_urn))
    completed = set(
        self._GetCollectionItems(self.completed_clients_collection_urn))
    outstanding = started - completed

    return {"STARTED": started,
            "COMPLETED": completed,
            "OUTSTANDING": outstanding}

  def GetClientStates(self, client_list, client_chunk=50):
    """Take in a client list and return dicts with their age and hostname."""
    for client_group in utils.Grouper(client_list, client_chunk):
      for fd in aff4.FACTORY.MultiOpen(
          client_group,
          mode="r",
          aff4_type=aff4_grr.VFSGRRClient,
          token=self.token):
        result = {}
        result["age"] = fd.Get(fd.Schema.PING)
        result["hostname"] = fd.Get(fd.Schema.HOSTNAME)
        yield (fd.urn, result)

  def GetLog(self, client_id=None):
    log_vals = aff4.FACTORY.Open(
        self.logs_collection_urn, mode="r", token=self.token)
    if not client_id:
      return log_vals
    else:
      return [val for val in log_vals if val.client_id == client_id]

  def Save(self):
    runner = self.GetRunner()
    if not runner.IsCompleted():
      runner.CheckExpiry()

  @staticmethod
  def GetAllSubflowUrns(hunt_urn, client_urns, top_level_only=False,
                        token=None):
    """Lists all subflows for a given hunt for all clients in client_urns."""
    client_ids = [urn.Split()[0] for urn in client_urns]
    client_bases = [hunt_urn.Add(client_id) for client_id in client_ids]

    all_flows = []
    act_flows = client_bases

    while act_flows:
      next_flows = []
      for _, children in aff4.FACTORY.MultiListChildren(act_flows, token=token):
        for flow_urn in children:
          if flow_urn.Basename() != flow_runner.RESULTS_PER_TYPE_SUFFIX:
            next_flows.append(flow_urn)
      all_flows.extend(next_flows)
      act_flows = next_flows

      if top_level_only:
        break

    return all_flows

  def _ValidateState(self):
    if self.context is None:
      raise IOError("Trying to write a hunt without context: %s." % self.urn)

  def WriteState(self):
    if "w" in self.mode:
      self._ValidateState()
      self.Set(self.Schema.HUNT_ARGS(self.args))
      self.Set(self.Schema.HUNT_CONTEXT(self.context))
      self.Set(self.Schema.HUNT_RUNNER_ARGS(self.runner_args))


class HuntInitHook(registry.InitHook):

  def RunOnce(self):
    """Register standard hunt-related stats."""
    stats.STATS.RegisterCounterMetric("hunt_results_added")
