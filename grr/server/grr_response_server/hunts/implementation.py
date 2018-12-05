#!/usr/bin/env python
"""The implementation of hunts.

A hunt is a mechanism for automatically scheduling flows on a selective subset
of clients, managing these flows, collecting and presenting the combined results
of all these flows.
"""
from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

import logging
import threading
import traceback

from grr_response_core.lib import rdfvalue
from grr_response_core.lib import registry
from grr_response_core.lib import type_info
from grr_response_core.lib import utils
from grr_response_core.lib.rdfvalues import client as rdf_client
from grr_response_core.lib.rdfvalues import client_stats as rdf_client_stats
from grr_response_core.lib.rdfvalues import events as rdf_events
from grr_response_core.lib.rdfvalues import flows as rdf_flows
from grr_response_core.lib.rdfvalues import protodict as rdf_protodict
from grr_response_core.lib.rdfvalues import stats as rdf_stats
from grr_response_core.lib.util import collection
from grr_response_core.lib.util import random
from grr_response_core.stats import stats_collector_instance
from grr_response_server import access_control
from grr_response_server import aff4
from grr_response_server import data_store
from grr_response_server import events as events_lib
from grr_response_server import flow
from grr_response_server import flow_responses
from grr_response_server import flow_runner
from grr_response_server import foreman_rules
from grr_response_server import grr_collections
from grr_response_server import multi_type_collection
from grr_response_server import notification as notification_lib
from grr_response_server import queue_manager
from grr_response_server.aff4_objects import aff4_grr
from grr_response_server.hunts import results as hunts_results
from grr_response_server.rdfvalues import flow_runner as rdf_flow_runner
from grr_response_server.rdfvalues import hunts as rdf_hunts
from grr_response_server.rdfvalues import objects as rdf_objects


class HuntRunnerError(Exception):
  """Raised when there is an error during state transitions."""


def StartHunt(args=None, runner_args=None, token=None, **kwargs):
  """This class method creates new hunts."""
  # If no token is specified, raise.
  if not token:
    raise access_control.UnauthorizedAccess("A token must be specified.")

  # Build the runner args from the keywords.
  if runner_args is None:
    runner_args = rdf_hunts.HuntRunnerArgs()

  flow.FilterArgsFromSemanticProtobuf(runner_args, kwargs)

  # Is the required hunt a known hunt?
  hunt_cls = GRRHunt.classes.get(runner_args.hunt_name)
  if not hunt_cls or not aff4.issubclass(hunt_cls, GRRHunt):
    raise RuntimeError("Unable to locate hunt %s" % runner_args.hunt_name)

  # Make a new hunt object and initialize its runner.
  hunt_obj = aff4.FACTORY.Create(None, hunt_cls, mode="w", token=token)

  # Hunt is called using keyword args. We construct an args proto from the
  # kwargs.
  if hunt_obj.args_type and args is None:
    args = hunt_obj.args_type()
    flow.FilterArgsFromSemanticProtobuf(args, kwargs)

  if hunt_obj.args_type and not isinstance(args, hunt_obj.args_type):
    raise RuntimeError("Hunt args must be instance of %s" % hunt_obj.args_type)

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

  event = rdf_events.AuditEvent(
      user=token.username,
      action="HUNT_CREATED",
      urn=hunt_obj.urn,
      flow_name=flow_name,
      description=runner_args.description)
  events_lib.Events.PublishEvent("Audit", event, token=token)

  return hunt_obj


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
          manager.DeQueueClientRequest(request.request)

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
              stats_collector_instance.Get().IncrementCounter(
                  "grr_request_retransmission_count")
              request.transmission_count += 1
              self.QueueRequest(request)
            break

          # If we get here its all good - run the hunt.
          self.hunt_obj.HeartBeat()
          self._Process(
              request, responses, thread_pool=thread_pool, events=processing)

          # At this point we have processed this request - we can remove it and
          # its responses from the queue.
          self.queue_manager.DeleteRequest(request)
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
                     method_name,
                     request=None,
                     responses=None,
                     event=None,
                     direct_response=None):
    """Completes the request by calling the state method.

    Args:
      method_name: The name of the state method to call.
      request: A RequestState protobuf.
      responses: A list of GrrMessages responding to the request.
      event: A threading.Event() instance to signal completion of this request.
      direct_response: A flow.Responses() object can be provided to avoid
        creation of one.
    """
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
      self.hunt_obj.HeartBeat()
      try:
        method = getattr(self.hunt_obj, method_name)
      except AttributeError:
        raise flow_runner.FlowRunnerError(
            "Flow %s has no state method %s" %
            (self.hunt_obj.__class__.__name__, method_name))

      if direct_response:
        method(direct_response)
      elif method_name == "Start":
        method()
      else:
        # Prepare a responses object for the state method to use:
        responses = flow_responses.Responses.FromLegacyResponses(
            request=request, responses=responses)

        if responses.status:
          self.SaveResourceUsage(request.client_id, responses.status)

        stats_collector_instance.Get().IncrementCounter("grr_worker_states_run")

        method(responses)

    # We don't know here what exceptions can be thrown in the flow but we have
    # to continue. Thus, we catch everything.
    except Exception as e:  # pylint: disable=broad-except

      # TODO(user): Deprecate in favor of 'flow_errors'.
      stats_collector_instance.Get().IncrementCounter("grr_flow_errors")

      stats_collector_instance.Get().IncrementCounter(
          "flow_errors", fields=[self.hunt_obj.Name()])
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

  def Publish(self, event_name, msg, delay=0):
    """Sends the message to event listeners."""
    events_lib.Events.PublishEvent(event_name, msg, delay=delay)

  def _GetSubFlowCPULimit(self):
    """Get current CPU limit for subflows."""

    subflow_cpu_limit = None

    if self.runner_args.per_client_cpu_limit:
      subflow_cpu_limit = self.runner_args.per_client_cpu_limit

    if self.runner_args.cpu_limit:
      cpu_usage_data = self.context.client_resources.cpu_usage
      remaining_cpu_quota = (
          self.runner_args.cpu_limit - cpu_usage_data.user_cpu_time -
          cpu_usage_data.system_cpu_time)
      if subflow_cpu_limit is None:
        subflow_cpu_limit = remaining_cpu_quota
      else:
        subflow_cpu_limit = min(subflow_cpu_limit, remaining_cpu_quota)

      if subflow_cpu_limit == 0:
        raise RuntimeError("Out of CPU quota.")

    return subflow_cpu_limit

  def _GetSubFlowNetworkLimit(self):
    """Get current network limit for subflows."""

    subflow_network_limit = None

    if self.runner_args.per_client_network_limit_bytes:
      subflow_network_limit = self.runner_args.per_client_network_limit_bytes

    if self.runner_args.network_bytes_limit:
      remaining_network_quota = (
          self.runner_args.network_bytes_limit -
          self.context.network_bytes_sent)
      if subflow_network_limit is None:
        subflow_network_limit = remaining_network_quota
      else:
        subflow_network_limit = min(subflow_network_limit,
                                    remaining_network_quota)

    return subflow_network_limit

  def _CallFlowLegacy(self,
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

    Returns:
       The URN of the child flow which was created.

    Raises:
       RuntimeError: In case of no cpu quota left to start more clients.
    """
    client_id = client_id or self.runner_args.client_id

    # We prepare a request state, and add it to our queue - any
    # responses from the child flow will return to the request state
    # and the stated next_state. Note however, that there is no
    # client_id or actual request message here because we directly
    # invoke the child flow rather than queue anything for it.
    state = rdf_flow_runner.RequestState(
        id=self.GetNextOutboundId(),
        session_id=utils.SmartUnicode(self.session_id),
        client_id=client_id,
        next_state=next_state,
        response_count=0)

    if request_data:
      state.data = rdf_protodict.Dict().FromDict(request_data)

    # Pass our logs collection urn to the flow object.
    logs_urn = self.hunt_obj.logs_collection_urn

    # If we were called with write_intermediate_results, propagate down to
    # child flows.  This allows write_intermediate_results to be set to True
    # either at the top level parent, or somewhere in the middle of
    # the call chain.
    write_intermediate = kwargs.pop("write_intermediate_results", False)

    # Create the new child flow but do not notify the user about it.
    child_urn = self.hunt_obj.StartAFF4Flow(
        base_session_id=base_session_id or self.session_id,
        client_id=client_id,
        cpu_limit=self._GetSubFlowCPULimit(),
        flow_name=flow_name,
        logs_collection_urn=logs_urn,
        network_bytes_limit=self._GetSubFlowNetworkLimit(),
        notify_to_user=False,
        parent_flow=self.hunt_obj,
        queue=self.runner_args.queue,
        request_state=state,
        sync=False,
        token=self.token,
        write_intermediate_results=write_intermediate,
        **kwargs)

    self.QueueRequest(state)

    return child_urn

  def _CallFlowRelational(self,
                          flow_name=None,
                          args=None,
                          runner_args=None,
                          client_id=None,
                          **kwargs):
    """Creates a new flow and send its responses to a state.

    This creates a new flow. The flow may send back many responses which will be
    queued by the framework until the flow terminates. The final status message
    will cause the entire transaction to be committed to the specified state.

    Args:
       flow_name: The name of the flow to invoke.
       args: Flow arguments.
       runner_args: Flow runner arguments.
       client_id: If given, the flow is started for this client.
       **kwargs: Arguments for the child flow.

    Returns:
       The URN of the child flow which was created.

    Raises:
       RuntimeError: In case of no cpu quota left to start more clients.
    """
    if isinstance(client_id, rdfvalue.RDFURN):
      client_id = client_id.Basename()

    if flow_name is None and runner_args is not None:
      flow_name = runner_args.flow_name

    flow_cls = registry.FlowRegistry.FlowClassByName(flow_name)

    flow_id = flow.StartFlow(
        client_id=client_id,
        creator=self.hunt_obj.creator,
        cpu_limit=self._GetSubFlowCPULimit(),
        network_bytes_limit=self._GetSubFlowNetworkLimit(),
        flow_cls=flow_cls,
        flow_args=args,
        parent_hunt_id=self.hunt_obj.urn.Basename(),
        **kwargs)

    return rdfvalue.RDFURN(client_id).Add("flows").Add(flow_id)

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

    Returns:
       The URN of the child flow which was created.

    Raises:
       RuntimeError: In case of no cpu quota left to start more clients.
    """
    if data_store.RelationalDBFlowsEnabled():
      if request_data is not None:
        raise ValueError("Hunt's CallFlow does not support 'request_data' arg "
                         "when REL_DB is enabled.")

      return self._CallFlowRelational(
          flow_name=flow_name, client_id=client_id, **kwargs)
    else:
      return self._CallFlowLegacy(
          flow_name=flow_name,
          next_state=next_state,
          request_data=request_data,
          client_id=client_id,
          base_session_id=base_session_id,
          **kwargs)

  def FlushQueuedReplies(self):
    # Hunts do not send replies.
    pass

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
      output_plugin_cls = plugin_descriptor.GetPluginClass()
      output_plugin = output_plugin_cls(
          source_urn=self.results_collection_urn,
          args=plugin_descriptor.plugin_args,
          token=self.token)

      # Extend our lease if needed.
      self.hunt_obj.HeartBeat()
      try:
        output_plugin.ProcessResponses(plugin_state, replies)
        output_plugin.Flush(plugin_state)
        output_plugin.UpdateState(plugin_state)

        log_item = output_plugin.OutputPluginBatchProcessingStatus(
            plugin_descriptor=plugin_descriptor,
            status="SUCCESS",
            batch_size=len(replies))
        # Cannot append to lists in AttributedDicts.
        plugin_state["logs"] += [log_item]

        self.Log("Plugin %s successfully processed %d flow replies.",
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
          self.context.network_bytes_sent):
        # We have exceeded our byte limit, stop this flow.
        raise flow_runner.FlowRunnerError("Network bytes limit exceeded.")

  def _QueueRequest(self, request, timestamp=None):
    if request.HasField("request") and request.request.name:
      # This message contains a client request as well.
      self.queue_manager.QueueClientMessage(
          request.request, timestamp=timestamp)

    self.queue_manager.QueueRequest(request, timestamp=timestamp)

  def QueueRequest(self, request, timestamp=None):
    # Remember the new request for later
    self._QueueRequest(request, timestamp=timestamp)

  def QueueResponse(self, response, timestamp=None):
    self.queue_manager.QueueResponse(response, timestamp=timestamp)

  def QueueNotification(self, *args, **kw):
    self.queue_manager.QueueNotification(*args, **kw)

  def Status(self, format_str, *args):
    """Flows can call this method to set a status message visible to users."""
    self.Log(format_str, *args)

  def _AddClient(self, client_id):
    next_client_due = self.hunt_obj.context.next_client_due
    if self.runner_args.client_rate > 0:
      self.hunt_obj.context.next_client_due = (
          next_client_due + 60.0 / self.runner_args.client_rate)
      self.hunt_obj.context.clients_queued_count += 1
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

      # Pause the hunt if we exceed the client limit.
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
        logging.error(
            "Tried to log a format string with the wrong number "
            "of arguments: %s", format_str)

    logging.info("%s: %s", self.session_id, status)

    self.context.status = utils.SmartUnicode(status)

    log_entry = rdf_flows.FlowLog(
        client_id=None,
        urn=self.session_id,
        flow_name=self.hunt_obj.__class__.__name__,
        log_message=status)
    logs_collection_urn = self.hunt_obj.logs_collection_urn
    with data_store.DB.GetMutationPool() as pool:
      grr_collections.LogCollection.StaticAdd(
          logs_collection_urn, log_entry, mutation_pool=pool)

  def Error(self, backtrace, client_id=None):
    """Logs an error for a client but does not terminate the hunt."""
    logging.error("Hunt Error: %s", backtrace)
    self.hunt_obj.LogClientError(client_id, backtrace=backtrace)

  def SaveResourceUsage(self, client_id, status):
    """Update the resource usage of the hunt."""
    # Per client stats.
    self.hunt_obj.ProcessClientResourcesStats(client_id, status)
    # Overall hunt resource usage.
    self.UpdateProtoResources(status)

  def InitializeContext(self, args):
    """Initializes the context of this hunt."""
    if args is None:
      args = rdf_hunts.HuntRunnerArgs()

    context = rdf_hunts.HuntContext(
        create_time=rdfvalue.RDFDatetime.Now(),
        creator=self.token.username,
        expires=args.expiry_time.Expiry(),
        start_time=rdfvalue.RDFDatetime.Now(),
        usage_stats=rdf_stats.ClientResourcesStats())

    return context

  def GetNewSessionID(self, **_):
    """Returns a random integer session ID for this hunt.

    All hunts are created under the aff4:/hunts namespace.

    Returns:
      a formatted session id string.
    """
    return rdfvalue.SessionID(base="aff4:/hunts", queue=self.runner_args.queue)

  def _CreateAuditEvent(self, event_action):
    event = rdf_events.AuditEvent(
        user=self.hunt_obj.token.username,
        action=event_action,
        urn=self.hunt_obj.urn,
        description=self.runner_args.description)
    events_lib.Events.PublishEvent("Audit", event)

  def Start(self):
    """This uploads the rules to the foreman and, thus, starts the hunt."""
    # We are already running.
    if self.hunt_obj.Get(self.hunt_obj.Schema.STATE) == "STARTED":
      return

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
    if data_store.RelationalDBReadEnabled(category="foreman"):
      # Relational DB uses ForemanCondition objects.
      foreman_condition = foreman_rules.ForemanCondition(
          creation_time=rdfvalue.RDFDatetime.Now(),
          expiration_time=self.context.expires,
          description="Hunt %s %s" % (self.session_id,
                                      self.runner_args.hunt_name),
          client_rule_set=self.runner_args.client_rule_set,
          hunt_id=self.session_id.Basename(),
          hunt_name=self.runner_args.hunt_name)

      # Make sure the rule makes sense.
      foreman_condition.Validate()

      data_store.REL_DB.WriteForemanRule(foreman_condition)
    else:
      foreman_rule = foreman_rules.ForemanRule(
          created=rdfvalue.RDFDatetime.Now(),
          expires=self.context.expires,
          description="Hunt %s %s" % (self.session_id,
                                      self.runner_args.hunt_name),
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
          aff4_type=aff4_grr.GRRForeman) as foreman:
        rules = foreman.Get(
            foreman.Schema.RULES, default=foreman.Schema.RULES())
        rules.Append(foreman_rule)
        foreman.Set(rules)

  def _RemoveForemanRule(self):
    """Removes the foreman rule corresponding to this hunt."""
    if data_store.RelationalDBReadEnabled(category="foreman"):
      data_store.REL_DB.RemoveForemanRule(hunt_id=self.session_id.Basename())
      return

    with aff4.FACTORY.Open(
        "aff4:/foreman", mode="rw", token=self.token) as foreman:
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

    self._RemoveForemanRule()

    self.hunt_obj.Set(self.hunt_obj.Schema.STATE("PAUSED"))
    self.hunt_obj.Flush()

    self._CreateAuditEvent("HUNT_PAUSED")

  def Stop(self, reason=None):
    """Cancels the hunt (removes Foreman rules, resets expiry time to 0)."""
    self._RemoveForemanRule()
    self.hunt_obj.Set(self.hunt_obj.Schema.STATE("STOPPED"))
    self.hunt_obj.Flush()

    self._CreateAuditEvent("HUNT_STOPPED")

    if reason:
      notification_lib.Notify(
          self.token.username,
          rdf_objects.UserNotification.Type.TYPE_HUNT_STOPPED, reason,
          rdf_objects.ObjectReference(
              reference_type=rdf_objects.ObjectReference.Type.HUNT,
              hunt=rdf_objects.HuntReference(
                  hunt_id=self.hunt_obj.urn.Basename())))

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
      messages: A list of rdfvalues to send. If the last one is not a GrrStatus,
        we append an OK Status.
      next_state: The state in this hunt to be invoked with the responses.
      client_id: ClientURN to use in scheduled requests.
      request_data: Any dict provided here will be available in the RequestState
        protobuf. The Responses object maintains a reference to this protobuf
        for use in the execution of the state method. (so you can access this
        data by responses.request).
      start_time: Schedule the state at this time. This delays notification and
        messages for processing into the future.

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
    request_state = rdf_flow_runner.RequestState(
        id=random.UInt32(),
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
        raise flow_runner.FlowRunnerError(
            "Bad message %s of type %s." % (payload, type(payload)))

      self.QueueResponse(msg, timestamp=start_time)

    # Notify the worker about it.
    self.QueueNotification(session_id=self.session_id, timestamp=start_time)


class GRRHunt(flow.FlowBase):
  """The GRR Hunt class."""

  MIN_CLIENTS_FOR_AVERAGE_THRESHOLDS = 1000

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
        rdfvalue.RDFString, "The state of a hunt can be "
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

      self.Load()

    if self.state is None:
      self.state = flow.AttributedDict()

  def CreateRunner(self, **kw):
    """Make a new runner."""
    self.runner = HuntRunner(self, token=self.token, **kw)
    return self.runner

  # Collection for results.
  @property
  def results_collection_urn(self):
    return self.urn.Add("Results")

  @classmethod
  def ResultCollectionForHID(cls, hunt_id, token=None):
    """Returns the ResultCollection for the hunt with a given hunt_id.

    Args:
      hunt_id: The id of the hunt, a RDFURN of the form aff4:/hunts/H:123456.
      token: A data store token.

    Returns:
      The collection containing the results for the hunt identified by the id.
    """
    return hunts_results.HuntResultCollection(hunt_id.Add("Results"))

  def ResultCollection(self):
    return self.ResultCollectionForHID(self.session_id)

  # Collection for results by type.
  @property
  def multi_type_output_urn(self):
    return self.urn.Add("ResultsPerType")

  @classmethod
  def TypedResultCollectionForHID(cls, hunt_id):
    return multi_type_collection.MultiTypeCollection(
        hunt_id.Add("ResultsPerType"))

  def TypedResultCollection(self):
    return self.TypedResultCollectionForHID(self.session_id)

  # Collection for logs.
  @property
  def logs_collection_urn(self):
    return self.urn.Add("Logs")

  @classmethod
  def LogCollectionForHID(cls, hunt_id):
    return grr_collections.LogCollection(hunt_id.Add("Logs"))

  def LogCollection(self):
    return self.LogCollectionForHID(self.session_id)

  # Collection for crashes.
  @classmethod
  def CrashCollectionURNForHID(cls, hunt_id):
    return hunt_id.Add("Crashes")

  @classmethod
  def CrashCollectionForHID(cls, hunt_id):
    return grr_collections.CrashCollection(hunt_id.Add("Crashes"))

  def RegisterCrash(self, crash_details):
    hunt_crashes = self.__class__.CrashCollectionForHID(self.urn)
    hunt_crashes_len = hunt_crashes.CalculateLength()

    with data_store.DB.GetMutationPool() as pool:
      hunt_crashes.Add(crash_details, mutation_pool=pool)

    # Account for a crash detail that we've just added.
    if 0 < self.runner_args.crash_limit <= hunt_crashes_len + 1:
      # Remove our rules form the forman and cancel all the started flows.
      # Hunt will be hard-stopped and it will be impossible to restart it.
      reason = ("Hunt %s reached the crashes limit of %d "
                "and was stopped.") % (self.urn.Basename(),
                                       self.runner_args.crash_limit)
      self.Stop(reason=reason)
      self.Log(reason)

  # Collection for clients with errors.
  @property
  def clients_errors_collection_urn(self):
    return self.urn.Add("ErrorClients")

  @classmethod
  def ErrorCollectionForHID(cls, hunt_id):
    return grr_collections.HuntErrorCollection(hunt_id.Add("ErrorClients"))

  # Collection for output plugin status objects.
  @property
  def output_plugins_status_collection_urn(self):
    return self.urn.Add("OutputPluginsStatus")

  @classmethod
  def PluginStatusCollectionForHID(cls, hunt_id):
    return grr_collections.PluginStatusCollection(
        hunt_id.Add("OutputPluginsStatus"))

  # Collection for output plugin status errors.
  @property
  def output_plugins_errors_collection_urn(self):
    return self.urn.Add("OutputPluginsErrors")

  @classmethod
  def PluginErrorCollectionForHID(cls, hunt_id):
    return grr_collections.PluginStatusCollection(
        hunt_id.Add("OutputPluginsErrors"))

  # Collection for clients that reported an error.
  @property
  def clients_with_results_collection_urn(self):
    return self.urn.Add("ClientsWithResults")

  @classmethod
  def ClientsWithResultsCollectionForHID(cls, hunt_id):
    return grr_collections.ClientUrnCollection(
        hunt_id.Add("ClientsWithResults"))

  def ClientsWithResultsCollection(self):
    return self.ClientsWithResultsCollectionForHID(self.session_id)

  # Collection for clients the hunt ran on.
  @property
  def all_clients_collection_urn(self):
    return self.urn.Add("AllClients")

  @classmethod
  def AllClientsCollectionForHID(cls, hunt_id):
    return grr_collections.ClientUrnCollection(hunt_id.Add("AllClients"))

  # Collection for clients that have completed this hunt.
  @property
  def completed_clients_collection_urn(self):
    return self.urn.Add("CompletedClients")

  @classmethod
  def CompletedClientsCollectionForHID(cls, hunt_id):
    return grr_collections.ClientUrnCollection(hunt_id.Add("CompletedClients"))

  @property
  def results_metadata_urn(self):
    return self.urn.Add("ResultsMetadata")

  @property
  def output_plugins_base_urn(self):
    return self.urn.Add("Results")

  @property
  def creator(self):
    return self.context.creator

  def _AddURNToCollection(self, urn, collection_urn):
    with data_store.DB.GetMutationPool() as pool:
      grr_collections.ClientUrnCollection.StaticAdd(
          collection_urn, urn, mutation_pool=pool)

  def _AddHuntErrorToCollection(self, error, collection_urn):
    with data_store.DB.GetMutationPool() as pool:
      grr_collections.HuntErrorCollection.StaticAdd(
          collection_urn, error, mutation_pool=pool)

  def _ClientSymlinkUrn(self, client_id):
    return client_id.Add("flows").Add("%s:hunt" % (self.urn.Basename()))

  def RegisterClient(self, client_urn):
    if self.context.clients_queued_count:
      self.context.clients_queued_count -= 1
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

    symlinks_urns = [
        self._ClientSymlinkUrn(client_id) for client_id in clients_ids
    ]
    deletion_pool.MultiMarkForDeletion(symlinks_urns)

  def RunClient(self, client_id):
    """This method runs the hunt on a specific client.

    Note that this method holds a lock on the hunt object and runs in the main
    thread. It is safe to access any hunt parameters from here.

    Args:
      client_id: The new client assigned to this hunt.
    """

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
        state = rdf_flow_runner.RequestState(
            id=random.UInt32(),
            session_id=hunt_id,
            client_id=client_id,
            next_state="AddClient")

        # Queue the new request.
        flow_manager.QueueRequest(state)

        # Send a response.
        msg = rdf_flows.GrrMessage(
            session_id=hunt_id,
            request_id=state.id,
            response_id=1,
            auth_state=rdf_flows.GrrMessage.AuthorizationState.AUTHENTICATED,
            type=rdf_flows.GrrMessage.Type.STATUS,
            payload=rdf_flows.GrrStatus())

        flow_manager.QueueResponse(msg)

        # And notify the worker about it.
        flow_manager.QueueNotification(session_id=hunt_id)

  def Run(self):
    """A shortcut method for starting the hunt."""
    self.GetRunner().Start()

  def Pause(self):
    """A shortcut method for pausing the hunt."""
    self.GetRunner().Pause()

  def Stop(self, reason=None):
    """A shortcut method for stopping the hunt."""
    self.GetRunner().Stop(reason=reason)

  def StopHuntIfAverageLimitsExceeded(self):
    # Do nothing if the hunt is already stopped.
    state = self.Get(self.Schema.STATE)
    if state == "STOPPED":
      return

    if (self.context.completed_clients_count <
        self.MIN_CLIENTS_FOR_AVERAGE_THRESHOLDS):
      return

    # Check average per-client results count limit.
    if self.runner_args.avg_results_per_client_limit:
      avg_results_per_client = (
          self.context.results_count / self.context.completed_clients_count)
      if (avg_results_per_client >
          self.runner_args.avg_results_per_client_limit):
        # Stop the hunt since we get too many results per client.
        reason = ("Hunt %s reached the average results per client "
                  "limit of %d and was stopped.") % (
                      self.urn.Basename(),
                      self.runner_args.avg_results_per_client_limit)
        self.Stop(reason=reason)

    # Check average per-client CPU seconds limit.
    if self.runner_args.avg_cpu_seconds_per_client_limit:
      avg_cpu_seconds_per_client = (
          (self.context.client_resources.cpu_usage.user_cpu_time +
           self.context.client_resources.cpu_usage.system_cpu_time) /
          self.context.completed_clients_count)
      if (avg_cpu_seconds_per_client >
          self.runner_args.avg_cpu_seconds_per_client_limit):
        # Stop the hunt since we use too many CPUs per client.
        reason = ("Hunt %s reached the average CPU seconds per client "
                  "limit of %d and was stopped.") % (
                      self.urn.Basename(),
                      self.runner_args.avg_cpu_seconds_per_client_limit)
        self.Stop(reason=reason)

    # Check average per-client network bytes limit.
    if self.runner_args.avg_network_bytes_per_client_limit:
      avg_network_bytes_per_client = (
          self.context.network_bytes_sent /
          self.context.completed_clients_count)
      if (avg_network_bytes_per_client >
          self.runner_args.avg_network_bytes_per_client_limit):
        # Stop the hunt since we use too many network bytes sent
        # per client.
        reason = ("Hunt %s reached the average network bytes per client "
                  "limit of %d and was stopped.") % (
                      self.urn.Basename(),
                      self.runner_args.avg_network_bytes_per_client_limit)
        self.Stop(reason=reason)

  def AddResultsToCollection(self, responses, client_id):
    if responses.success:
      with self.lock:
        self.processed_responses = True

        msgs = [
            rdf_flows.GrrMessage(payload=response, source=client_id)
            for response in responses
        ]

        with data_store.DB.GetMutationPool() as pool:
          for msg in msgs:
            hunts_results.HuntResultCollection.StaticAdd(
                self.results_collection_urn, msg, mutation_pool=pool)

          for msg in msgs:
            multi_type_collection.MultiTypeCollection.StaticAdd(
                self.multi_type_output_urn, msg, mutation_pool=pool)

        self.context.completed_clients_count += 1
        if responses:
          self.RegisterClientWithResults(client_id)
          self.context.clients_with_results_count += 1
          self.context.results_count += len(responses)

        self.StopHuntIfAverageLimitsExceeded()

        # Update stats.
        stats_collector_instance.Get().IncrementCounter(
            "hunt_results_added", delta=len(msgs))
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
      hunt_link_urn = client_id.Add("flows").Add(
          "%s:hunt" % (self.urn.Basename()))

      hunt_link = aff4.FACTORY.Create(
          hunt_link_urn, aff4.AFF4Symlink, token=self.token)

      hunt_link.Set(hunt_link.Schema.SYMLINK_TARGET(child_urn))
      hunt_link.Close()

    return child_urn

  def HeartBeat(self):
    if self.locked:
      lease_time = self.transaction.lease_time
      if self.CheckLease() < lease_time // 2:
        logging.debug("%s: Extending Lease", self.session_id)
        self.UpdateLease(lease_time)
    else:
      logging.warning("%s is heartbeating while not being locked.", self.urn)

  def Name(self):
    return self.runner_args.hunt_name

  def SetDescription(self, description=None):
    self.runner_args.description = description or ""

  def Start(self):
    """Initializes this hunt from arguments."""
    with data_store.DB.GetMutationPool() as mutation_pool:
      self.CreateCollections(mutation_pool)

    if not self.runner_args.description:
      self.SetDescription()

  def _SetupOutputPluginState(self):
    state = rdf_protodict.AttributedDict()

    # GenericHunt.output_plugins is deprecated, but we have to support
    # pre-created cron jobs, hence we check in both places.
    # TODO(user): Remove GenericHuntArgs.output_plugins and
    # VariableGenericHuntArgs.output_plugins.
    if self.args and self.args.HasField("output_plugins"):
      plugins_descriptors = self.args.output_plugins
    else:
      plugins_descriptors = self.runner_args.output_plugins

    for index, plugin_descriptor in enumerate(plugins_descriptors):
      plugin_class = plugin_descriptor.GetPluginClass()
      _, plugin_state = plugin_class.CreatePluginAndDefaultState(
          source_urn=self.results_collection_urn,
          args=plugin_descriptor.plugin_args,
          token=self.token)

      state["%s_%d" % (plugin_descriptor.plugin_name, index)] = [
          plugin_descriptor, plugin_state
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

  def MarkClientDone(self, client_id):
    """Adds a client_id to the list of completed tasks."""
    self.RegisterCompletedClient(client_id)

  def LogClientError(self, client_id, log_message=None, backtrace=None):
    """Logs an error for a client."""
    self.RegisterClientError(
        client_id, log_message=log_message, backtrace=backtrace)

  def ProcessClientResourcesStats(self, client_id, status):
    """Process status message from a client and update the stats.

    Args:
      client_id: Client id.
      status: The status object returned from the client.
    """
    if hasattr(status, "child_session_id"):
      flow_path = status.child_session_id
    else:
      flow_path = "aff4:/%s/flows/%s" % (status.client_id, status.flow_id)

    resources = rdf_client_stats.ClientResources()
    resources.client_id = client_id
    resources.session_id = flow_path
    resources.cpu_usage.user_cpu_time = status.cpu_time_used.user_cpu_time
    resources.cpu_usage.system_cpu_time = status.cpu_time_used.system_cpu_time
    resources.network_bytes_sent = status.network_bytes_sent
    self.context.usage_stats.RegisterResources(resources)

  def GetClientsCounts(self):

    collections_dict = dict(
        (urn, col_type(urn))
        for urn, col_type in [(self.all_clients_collection_urn,
                               grr_collections.ClientUrnCollection),
                              (self.completed_clients_collection_urn,
                               grr_collections.ClientUrnCollection),
                              (self.clients_errors_collection_urn,
                               grr_collections.HuntErrorCollection)])

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
    hunt_collection = grr_collections.HuntErrorCollection(
        self.clients_errors_collection_urn)
    errors = hunt_collection.GenerateItems()
    if not client_id:
      return errors
    else:
      return [error for error in errors if error.client_id == client_id]

  def GetClients(self):
    col = self.AllClientsCollectionForHID(self.session_id)
    return set(col.GenerateItems())

  def GetCompletedClients(self):
    col = self.CompletedClientsCollectionForHID(self.session_id)
    return set(col.GenerateItems())

  def GetClientsByStatus(self):
    """Get all the clients in a dict of {status: [client_list]}."""
    started = self.GetClients()
    completed = self.GetCompletedClients()
    outstanding = started - completed

    return {
        "STARTED": started,
        "COMPLETED": completed,
        "OUTSTANDING": outstanding
    }

  def GetClientStates(self, client_list, client_chunk=50):
    """Take in a client list and return dicts with their age and hostname."""
    for client_group in collection.Batch(client_list, client_chunk):
      for fd in aff4.FACTORY.MultiOpen(
          client_group,
          mode="r",
          aff4_type=aff4_grr.VFSGRRClient,
          token=self.token):
        result = {}
        result["age"] = fd.Get(fd.Schema.PING)
        result["hostname"] = fd.Get(fd.Schema.HOSTNAME)
        yield (fd.urn, result)

  def Save(self):
    runner = self.GetRunner()
    if not runner.IsCompleted():
      runner.CheckExpiry()

  def _ValidateState(self):
    if self.context is None:
      raise IOError("Trying to write a hunt without context: %s." % self.urn)

  def WriteState(self):
    if "w" in self.mode:
      self._ValidateState()
      self.Set(self.Schema.HUNT_ARGS(self.args))
      self.Set(self.Schema.HUNT_CONTEXT(self.context))
      self.Set(self.Schema.HUNT_RUNNER_ARGS(self.runner_args))
