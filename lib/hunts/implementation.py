#!/usr/bin/env python
"""The implementation of hunts.

A hunt is a mechanism for automatically scheduling flows on a selective subset
of clients, managing these flows, collecting and presenting the combined results
of all these flows.

In essence a hunt is just another flow which schedules child flows using
CallFlow(). Replies from these child flows are then collected and stored in the
hunt's AFF4 representation. The main difference between a hunt and a regular
flow is that in hunts responses are processed concurrently and not necessarily
in request order. A hunt process many responses concurrently, while a flow
processes responses in strict request order (in a single thread).

For this reason a hunt has its own runner - the HuntRunner.

"""

import re
import threading
import traceback

import logging

from grr.lib import access_control
from grr.lib import aff4
from grr.lib import data_store
from grr.lib import flow
from grr.lib import flow_runner
from grr.lib import queue_manager
from grr.lib import rdfvalue
from grr.lib import type_info
from grr.lib import utils
from grr.lib.rdfvalues import flows
from grr.proto import flows_pb2


class HuntRunnerArgs(rdfvalue.RDFProtoStruct):
  protobuf = flows_pb2.HuntRunnerArgs

  def Validate(self):
    if self.HasField("regex_rules"):
      self.regex_rules.Validate()

    if self.HasField("integer_rules"):
      self.integer_rules.Validate()


class HuntRunner(flow_runner.FlowRunner):
  """The runner for hunts.

  This runner implement some slight differences from the regular flows:

  1) Responses are not precessed in strict request order. Instead they are
     processed concurrently on a thread pool.

  2) Hunt Errors are not fatal and do not generally terminate the hunt. The hunt
     continues running.

  3) Resources are tallied for each client and as a hunt total.
  """

  schedule_kill_notifications = False
  process_requests_in_order = False

  def _AddClient(self, client_id):
    next_client_due = self.flow_obj.state.context.next_client_due
    if self.args.client_rate > 0:
      self.flow_obj.state.context.next_client_due = (
          next_client_due + 60 / self.args.client_rate)
      self.CallState(messages=[client_id], next_state="RegisterClient",
                     client_id=client_id, start_time=next_client_due)
    else:
      self._RegisterAndRunClient(client_id)

  def _RegisterAndRunClient(self, client_id):
    self.flow_obj.RegisterClient(client_id)
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
            self.flow_obj.Get(self.flow_obj.Schema.STATE))
        return

      # Update the client count.
      client_count = int(
          self.flow_obj.Get(self.flow_obj.Schema.CLIENT_COUNT, 0))

      # Stop the hunt if we exceed the client limit.
      if 0 < self.args.client_limit <= client_count:
        # Remove our rules from the foreman so we dont get more clients sent to
        # this hunt. Hunt will be paused.
        self.Pause()

        # Ignore this client since it had gone over the limit.
        return

      # Update the client count.
      self.flow_obj.Set(self.flow_obj.Schema.CLIENT_COUNT(client_count + 1))

      # Add client to list of clients and optionally run it
      # (if client_rate == 0).
      self._AddClient(request.client_id)
      return

    if request.next_state == "RegisterClient":
      self._RegisterAndRunClient(request.client_id)
      return

    event = threading.Event()
    events.append(event)
    # In a hunt, all requests are independent and can be processed
    # in separate threads.
    thread_pool.AddTask(target=self.RunStateMethod,
                        args=(request.next_state, request, responses, event),
                        name="Hunt processing")

  def Log(self, format_str, *args):
    """Logs the message using the flow's standard logging.

    Args:
      format_str: Format string
      *args: arguments to the format string
    Raises:
      RuntimeError: on parent missing logs_collection
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

    logs_collection = self.OpenLogsCollection(self.args.logs_collection_urn)
    logs_collection.Add(
        rdfvalue.FlowLog(client_id=None, urn=self.session_id,
                         flow_name=self.flow_obj.__class__.__name__,
                         log_message=status))
    logs_collection.Flush()

  def Error(self, backtrace, client_id=None):
    """Logs an error for a client but does not terminate the hunt."""
    logging.error("Hunt Error: %s", backtrace)
    self.flow_obj.LogClientError(client_id, backtrace=backtrace)

  def SaveResourceUsage(self, request, responses):
    """Update the resource usage of the hunt."""
    self.flow_obj.ProcessClientResourcesStats(request.client_id,
                                              responses.status)

    # Do this last since it may raise "CPU quota exceeded".
    self.UpdateProtoResources(responses.status)

  def InitializeContext(self, args):
    """Initializes the context of this hunt."""
    if args is None:
      args = HuntRunnerArgs()

    # For large hunts, checking client limits creates a high load on the foreman
    # since it needs to read the hunt object's client list. We therefore don't
    # allow setting it for large hunts. Note that client_limit of 0 means
    # unlimited which is allowed (the foreman then does not need to check the
    # client list)..
    if args.client_limit > 1000:
      raise RuntimeError("Please specify client_limit <= 1000.")

    context = flows.DataObject(
        args=args,
        backtrace=None,
        client_resources=rdfvalue.ClientResources(),
        create_time=rdfvalue.RDFDatetime().Now(),
        creator=self.token.username,
        expires=rdfvalue.RDFDatetime().Now(),
        # If not None, kill-stuck-flow notification is scheduled at the given
        # time.
        kill_timestamp=None,
        network_bytes_sent=0,
        next_client_due=0,
        next_outbound_id=1,
        next_processed_request=1,
        next_states=set(),
        outstanding_requests=0,
        current_state=None,
        start_time=rdfvalue.RDFDatetime().Now(),

        # Hunts are always in the running state.
        state=rdfvalue.Flow.State.RUNNING,
        usage_stats=rdfvalue.ClientResourcesStats(),
        remaining_cpu_quota=args.cpu_limit,
        )

    # Store the context in the flow_obj for next time.
    self.flow_obj.state.Register("context", context)

    return context

  def GetNewSessionID(self, **_):
    """Returns a random integer session ID for this flow.

    All hunts are created under the aff4:/hunts namespace.

    Returns:
      a formatted session id string.
    """
    return rdfvalue.SessionID(base="aff4:/hunts", queue=self.args.queue)

  def _CreateAuditEvent(self, event_action):
    try:
      flow_name = self.flow_obj.args.flow_runner_args.flow_name
    except AttributeError:
      flow_name = ""

    event = rdfvalue.AuditEvent(user=self.flow_obj.token.username,
                                action=event_action, urn=self.flow_obj.urn,
                                flow_name=flow_name,
                                description=self.args.description)
    flow.Events.PublishEvent("Audit", event, token=self.flow_obj.token)

  def Start(self, add_foreman_rules=True):
    """This uploads the rules to the foreman and, thus, starts the hunt."""
    # We are already running.
    if self.flow_obj.Get(self.flow_obj.Schema.STATE) == "STARTED":
      return

    # Check the permissions for the hunt here. Note that self.args.token is the
    # original creators's token, while the aff4 object was created with the
    # caller's token. This check therefore ensures that the caller to this
    # method has permissions to start the hunt (not necessarily the original
    # creator of the hunt).
    data_store.DB.security_manager.CheckHuntAccess(
        self.flow_obj.token, self.session_id)

    # Determine when this hunt will expire.
    self.context.expires = self.args.expiry_time.Expiry()

    # When the next client can be scheduled. Implements gradual client
    # recruitment rate according to the client_rate.
    self.context.next_client_due = rdfvalue.RDFDatetime().Now()

    self._CreateAuditEvent("HUNT_STARTED")

    # Start the hunt.
    self.flow_obj.Set(self.flow_obj.Schema.STATE("STARTED"))
    self.flow_obj.Flush()

    if not add_foreman_rules:
      return

    # Add a new rule to the foreman
    foreman_rule = rdfvalue.ForemanRule(
        created=rdfvalue.RDFDatetime().Now(),
        expires=self.context.expires,
        description="Hunt %s %s" % (self.session_id,
                                    self.args.hunt_name),
        regex_rules=self.args.regex_rules,
        integer_rules=self.args.integer_rules)

    foreman_rule.actions.Append(hunt_id=self.session_id,
                                hunt_name=self.args.hunt_name,
                                client_limit=self.args.client_limit)

    # Make sure the rule makes sense.
    foreman_rule.Validate()

    with aff4.FACTORY.Open("aff4:/foreman", mode="rw", token=self.token,
                           aff4_type="GRRForeman",
                           ignore_cache=True) as foreman:
      foreman_rules = foreman.Get(foreman.Schema.RULES,
                                  default=foreman.Schema.RULES())
      foreman_rules.Append(foreman_rule)
      foreman.Set(foreman_rules)

  def _RemoveForemanRule(self):
    with aff4.FACTORY.Open("aff4:/foreman", mode="rw", token=self.token,
                           ignore_cache=True) as foreman:
      aff4_rules = foreman.Get(foreman.Schema.RULES)
      aff4_rules = foreman.Schema.RULES(
          # Remove those rules which fire off this hunt id.
          [r for r in aff4_rules if r.hunt_id != self.session_id])
      foreman.Set(aff4_rules)

  def Pause(self):
    """Pauses the hunt (removes Foreman rules, does not touch expiry time)."""
    if not self.IsHuntStarted():
      return

    # Make sure the user is allowed to pause this hunt.
    data_store.DB.security_manager.CheckHuntAccess(
        self.flow_obj.token, self.session_id)

    self._RemoveForemanRule()

    self.flow_obj.Set(self.flow_obj.Schema.STATE("PAUSED"))
    self.flow_obj.Flush()

    self._CreateAuditEvent("HUNT_PAUSED")

  def Stop(self):
    """Cancels the hunt (removes Foreman rules, resets expiry time to 0)."""
    # Make sure the user is allowed to stop this hunt.
    data_store.DB.security_manager.CheckHuntAccess(
        self.flow_obj.token, self.session_id)

    # Expire the hunt so the worker can destroy it.
    self.args.expires = rdfvalue.RDFDatetime().Now()
    self._RemoveForemanRule()

    self.flow_obj.Set(self.flow_obj.Schema.STATE("STOPPED"))
    self.flow_obj.Flush()

    self._CreateAuditEvent("HUNT_STOPPED")

  def IsRunning(self):
    """Hunts are always considered to be running.

    Note that consider the hunt itself to always be active, since we might have
    child flows which are still in flight at the moment the hunt is paused or
    stopped. We stull want to receive responses from these flows and process
    them.

    Returns:
      True
    """
    return True

  def IsHuntStarted(self):
    """Is this hunt considered started?

    This method is used to check if new clients should be processed by this
    hunt. Note that child flow responses are always processed (As determined by
    IsRunning() but new clients are not allowed to be scheduled unless the hunt
    should be started.

    Returns:
      If a new client is allowed to be scheduled on this hunt.
    """
    # Hunt is considered running in PAUSED or STARTED states.
    state = self.flow_obj.Get(self.flow_obj.Schema.STATE)
    if state in ["STOPPED", "PAUSED"]:
      return False

    # Hunt has expired.
    if self.context.expires < rdfvalue.RDFDatetime().Now():
      # Stop the hunt due to expiry.
      self.Stop()
      return False

    return True

  def OutstandingRequests(self):
    # Lie about it to prevent us from being destroyed.
    return 1

  def CallState(self, messages=None, next_state="", client_id=None,
                request_data=None, start_time=None):
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
    request_state = rdfvalue.RequestState(id=utils.PRNG.GetULong(),
                                          session_id=self.context.session_id,
                                          client_id=client_id,
                                          next_state=next_state)

    if request_data:
      request_state.data = rdfvalue.Dict().FromDict(request_data)

    self.QueueRequest(request_state, timestamp=start_time)

    # Add the status message if needed.
    if not messages or not isinstance(messages[-1], rdfvalue.GrrStatus):
      messages.append(rdfvalue.GrrStatus())

    # Send all the messages
    for i, payload in enumerate(messages):
      if isinstance(payload, rdfvalue.RDFValue):
        msg = rdfvalue.GrrMessage(
            session_id=self.session_id, request_id=request_state.id,
            response_id=1 + i,
            auth_state=rdfvalue.GrrMessage.AuthorizationState.AUTHENTICATED,
            payload=payload,
            type=rdfvalue.GrrMessage.Type.MESSAGE)

        if isinstance(payload, rdfvalue.GrrStatus):
          msg.type = rdfvalue.GrrMessage.Type.STATUS
      else:
        raise flow_runner.FlowRunnerError("Bad message %s of type %s." %
                                          (payload, type(payload)))

      self.QueueResponse(msg, timestamp=start_time)

    # Add the status message if needed.
    if not messages or not isinstance(messages[-1], rdfvalue.GrrStatus):
      messages.append(rdfvalue.GrrStatus())

    # Notify the worker about it.
    self.QueueNotification(session_id=self.session_id, timestamp=start_time)


class GRRHunt(flow.GRRFlow):
  """The GRR Hunt class."""

  # Some common rules.
  MATCH_WINDOWS = rdfvalue.ForemanAttributeRegex(attribute_name="System",
                                                 attribute_regex="Windows")
  MATCH_LINUX = rdfvalue.ForemanAttributeRegex(attribute_name="System",
                                               attribute_regex="Linux")
  MATCH_DARWIN = rdfvalue.ForemanAttributeRegex(attribute_name="System",
                                                attribute_regex="Darwin")

  RESULTS_QUEUE = rdfvalue.RDFURN("HR")

  class SchemaCls(flow.GRRFlow.SchemaCls):
    """The schema for hunts.

    This object stores the persistent information for the hunt.
    """

    # TODO(user): remove as soon as there are no more active hunts
    # storing client ids and errors in versioned attributes.
    DEPRECATED_CLIENTS = aff4.Attribute("aff4:clients", rdfvalue.RDFURN,
                                        "The list of clients this hunt was "
                                        "run against.",
                                        creates_new_object_version=False)

    CLIENT_COUNT = aff4.Attribute("aff4:client_count", rdfvalue.RDFInteger,
                                  "The total number of clients scheduled.",
                                  versioned=False,
                                  creates_new_object_version=False)

    # TODO(user): remove as soon as there are no more active hunts
    # storing client ids and errors in versioned attributes.
    DEPRECATED_FINISHED = aff4.Attribute(
        "aff4:finished", rdfvalue.RDFURN,
        "The list of clients the hunt has completed on.",
        creates_new_object_version=False)

    # TODO(user): remove as soon as there are no more active hunts
    # storing client ids and errors in versioned attributes.
    DEPRECATED_ERRORS = aff4.Attribute(
        "aff4:errors", rdfvalue.HuntError,
        "The list of clients that returned an error.",
        creates_new_object_version=False)

    # TODO(user): remove as soon as there's no more potential need to
    # migrate old logs
    DEPRECATED_LOG = aff4.Attribute("aff4:result_log", rdfvalue.FlowLog,
                                    "The log entries.",
                                    creates_new_object_version=False)

    # This needs to be kept out the args semantic value since must be updated
    # without taking a lock on the hunt object.
    STATE = aff4.Attribute(
        "aff4:hunt_state", rdfvalue.RDFString,
        "The state of this hunt Can be 'STOPPED', 'STARTED' or 'PAUSED'.",
        versioned=False, lock_protected=False, default="PAUSED")

  args_type = None

  runner_cls = HuntRunner

  def Initialize(self):
    super(GRRHunt, self).Initialize()
    # Hunts run in multiple threads so we need to protect access.
    self.lock = threading.RLock()
    self.processed_responses = False

    if "r" in self.mode:
      self.client_count = self.Get(self.Schema.CLIENT_COUNT)

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

  def _AddObjectToCollection(self, obj, collection_urn):
    with aff4.FACTORY.Create(collection_urn, "PackedVersionedCollection",
                             mode="w", token=self.token) as collection:
      collection.Add(obj)

  def _GetCollectionItems(self, collection_urn):
    collection = aff4.FACTORY.Create(collection_urn,
                                     "PackedVersionedCollection",
                                     mode="r", token=self.token)
    return collection.GenerateItems()

  def RegisterClient(self, client_urn):
    self._AddObjectToCollection(client_urn, self.all_clients_collection_urn)

  def RegisterCompletedClient(self, client_urn):
    self._AddObjectToCollection(client_urn,
                                self.completed_clients_collection_urn)

  def RegisterClientError(self, client_id, log_message=None, backtrace=None):
    error = rdfvalue.HuntError(client_id=client_id,
                               backtrace=backtrace)
    if log_message:
      error.log_message = utils.SmartUnicode(log_message)

    self._AddObjectToCollection(error, self.clients_errors_collection_urn)

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
      runner_args = HuntRunnerArgs()

    cls.FilterArgsFromSemanticProtobuf(runner_args, kwargs)

    # Is the required flow a known flow?
    if (runner_args.hunt_name not in cls.classes and
        not aff4.issubclass(GRRHunt, cls.classes[runner_args.hunt_name])):
      raise RuntimeError("Unable to locate hunt %s" % runner_args.hunt_name)

    # Make a new hunt object and initialize its runner.
    hunt_obj = aff4.FACTORY.Create(None, runner_args.hunt_name,
                                   mode="w", token=runner_args.token)

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

    # Store the hunt args in the state.
    hunt_obj.state.Register("args", args)

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

    event = rdfvalue.AuditEvent(user=runner_args.token.username,
                                action="HUNT_CREATED", urn=hunt_obj.urn,
                                flow_name=flow_name,
                                description=runner_args.description)
    flow.Events.PublishEvent("Audit", event, token=runner_args.token)

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
        state = rdfvalue.RequestState(id=utils.PRNG.GetULong(),
                                      session_id=hunt_id,
                                      client_id=client_id,
                                      next_state="AddClient")

        # Queue the new request.
        flow_manager.QueueRequest(hunt_id, state)

        # Send a response.
        msg = rdfvalue.GrrMessage(
            session_id=hunt_id,
            request_id=state.id, response_id=1,
            auth_state=rdfvalue.GrrMessage.AuthorizationState.AUTHENTICATED,
            type=rdfvalue.GrrMessage.Type.STATUS,
            payload=rdfvalue.GrrStatus())

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
        msgs = [rdfvalue.GrrMessage(payload=response, source=client_id)
                for response in responses]
        # Pass the callback to ensure we heartbeat while writing the
        # results.
        self.state.context.results_collection.AddAll(
            msgs, callback=lambda index, rdf_value: self.HeartBeat())

    else:
      self.LogClientError(client_id, log_message=utils.SmartStr(
          responses.status))

  def Save(self):
    if self.state and self.processed_responses:
      with self.lock:
        fresh_collection = aff4.FACTORY.Open(
            self.state.context.results_collection_urn, mode="rw",
            ignore_cache=True, token=self.token)

        # This is a "defensive programming" approach. Hunt's results collection
        # should never be changed outside of the hunt. But if this happens,
        # it means something is seriously wrong with the system, so we'd better
        # detect it, log it and work around it.
        if len(fresh_collection) != self.state.context.results_collection_len:
          logging.error("Results collection was changed outside of hunt %s. "
                        "Expected %d results, got %d. Will reopen collection "
                        "again, which will lead to %d results being dropped. "
                        "Trace: %s",
                        self.urn,
                        self.state.context.results_collection_len,
                        len(fresh_collection),
                        len(fresh_collection) -
                        self.state.context.results_collection_len,
                        traceback.format_stack())

          self.state.context.results_collection = fresh_collection
          self.state.context.results_collection_len = len(fresh_collection)
        else:
          self.state.context.results_collection.Flush(sync=True)
          self.state.context.results_collection_len = len(
              self.state.context.results_collection)

          # Notify ProcessHuntResultsCronFlow that we got new results.
          data_store.DB.Set(self.RESULTS_QUEUE, self.urn,
                            rdfvalue.RDFDatetime().Now(),
                            replace=True, token=self.token)

    super(GRRHunt, self).Save()

  def CallFlow(self, flow_name=None, next_state=None, request_data=None,
               client_id=None, **kwargs):
    """Create a new child flow from a hunt."""
    base_session_id = None
    if client_id:
      # The flow is stored in the hunt namespace,
      base_session_id = self.urn.Add(client_id.Basename())

    # Actually start the new flow.
    # We need to pass the logs_collection_urn here rather than in __init__ to
    # wait for the hunt urn to be created.
    child_urn = self.runner.CallFlow(
        flow_name=flow_name, next_state=next_state,
        base_session_id=base_session_id, client_id=client_id,
        request_data=request_data, logs_collection_urn=self.logs_collection_urn,
        **kwargs)

    if client_id:
      # But we also create a symlink to it from the client's namespace.
      hunt_link_urn = client_id.Add("flows").Add(
          "%s:hunt" % (self.urn.Basename()))

      hunt_link = aff4.FACTORY.Create(hunt_link_urn, "AFF4Symlink",
                                      token=self.token)

      hunt_link.Set(hunt_link.Schema.SYMLINK_TARGET(child_urn))
      hunt_link.Close()

    return child_urn

  def Name(self):
    return self.state.context.args.hunt_name

  def CheckClient(self, client):
    return self.CheckRulesForClient(client, self.state.context.rules)

  @classmethod
  def CheckRulesForClient(cls, client, rules):
    for rule in rules:
      if cls.CheckRule(client, rule):
        return True

    return False

  @classmethod
  def CheckRule(cls, client, rule):
    try:
      for r in rule.regex_rules:
        if r.path != "/":
          continue

        attribute = aff4.Attribute.NAMES[r.attribute_name]
        value = utils.SmartStr(client.Get(attribute))

        if not re.search(r.attribute_regex, value):
          return False

      for i in rule.integer_rules:
        if i.path != "/":
          continue

        value = int(client.Get(aff4.Attribute.NAMES[i.attribute_name]))
        op = i.operator
        if op == rdfvalue.ForemanAttributeInteger.Operator.LESS_THAN:
          if value >= i.value:
            return False
        elif op == rdfvalue.ForemanAttributeInteger.Operator.GREATER_THAN:
          if value <= i.value:
            return False
        elif op == rdfvalue.ForemanAttributeInteger.Operator.EQUAL:
          if value != i.value:
            return False
        else:
          # Unknown operator.
          return False

      return True

    except (KeyError, ValueError):
      return False

  def TestRules(self):
    """This quickly verifies the ruleset.

    This applies the ruleset to all clients in the db to see how many of them
    would match the current rules.
    """

    root = aff4.FACTORY.Open(aff4.ROOT_URN, token=self.token)
    display_warning = False
    for rule in self.rules:
      for r in rule.regex_rules:
        if r.path != "/":
          display_warning = True
      for r in rule.integer_rules:
        if r.path != "/":
          display_warning = True
    if display_warning:
      logging.info("One or more rules use a relative path under the client, "
                   "this is not supported so your count may be off.")

    all_clients = 0
    num_matching_clients = 0
    matching_clients = []
    for client in root.OpenChildren(chunk_limit=100000):
      if client.Get(client.Schema.TYPE) == "VFSGRRClient":
        all_clients += 1
        if self.CheckClient(client):
          num_matching_clients += 1
          matching_clients.append(utils.SmartUnicode(client.urn))

    logging.info("Out of %d checked clients, %d matched the given rule set.",
                 all_clients, num_matching_clients)
    if matching_clients:
      logging.info("Example matches: %s", str(matching_clients[:3]))

  def SetDescription(self, description=None):
    if description:
      self.state.context.args.description = description
    else:
      try:
        flow_name = self.state.args.flow_runner_args.flow_name
      except AttributeError:
        flow_name = ""
      self.state.context.args.description = flow_name

  @flow.StateHandler()
  def Start(self):
    """Initializes this hunt from arguments."""
    self.state.context.Register("results_metadata_urn",
                                self.urn.Add("ResultsMetadata"))
    self.state.context.Register("results_collection_urn",
                                self.urn.Add("Results"))
    self.state.context.Register("results_collection_len", 0)

    with aff4.FACTORY.Create(
        self.state.context.results_metadata_urn, "HuntResultsMetadata",
        mode="rw", token=self.token) as results_metadata:

      state = rdfvalue.FlowState()
      try:
        plugins = self.state.args.output_plugins
      except AttributeError:
        plugins = []

      for index, plugin in enumerate(plugins):
        plugin_obj = plugin.GetPluginForHunt(self)
        state.Register("%s_%d" % (plugin.plugin_name, index),
                       (plugin, plugin_obj.state))

      results_metadata.Set(results_metadata.Schema.OUTPUT_PLUGINS(state))

    with aff4.FACTORY.Create(
        self.state.context.results_collection_urn, "RDFValueCollection",
        mode="rw", token=self.token) as results_collection:
      results_collection.SetChunksize(1024 * 1024)
      self.state.context.Register("results_collection", results_collection)

    if not self.state.context.args.description:
      self.SetDescription()

  @flow.StateHandler()
  def End(self):
    """Final state."""

  def MarkClientDone(self, client_id):
    """Adds a client_id to the list of completed tasks."""
    self.RegisterCompletedClient(client_id)

    if self.state.context.args.notification_event:
      status = rdfvalue.HuntNotification(session_id=self.session_id,
                                         client_id=client_id)
      self.Publish(self.state.context.args.notification_event, status)

  def LogClientError(self, client_id, log_message=None, backtrace=None):
    """Logs an error for a client."""
    self.RegisterClientError(client_id, log_message=log_message,
                             backtrace=backtrace)

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
        aff4_type="PackedVersionedCollection", mode="r", token=self.token)
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
    completed = set(self._GetCollectionItems(
        self.completed_clients_collection_urn))
    outstanding = started - completed

    return {"COMPLETED": sorted(completed),
            "OUTSTANDING": sorted(outstanding)}

  def GetClientStates(self, client_list, client_chunk=50):
    """Take in a client list and return dicts with their age and hostname."""
    for client_group in utils.Grouper(client_list, client_chunk):
      for fd in aff4.FACTORY.MultiOpen(client_group, mode="r",
                                       aff4_type="VFSGRRClient",
                                       token=self.token):
        result = {}
        result["age"] = fd.Get(fd.Schema.PING)
        result["hostname"] = fd.Get(fd.Schema.HOSTNAME)
        yield (fd.urn, result)

  def GetLog(self, client_id=None):
    log_vals = aff4.FACTORY.Create(
        self.logs_collection_urn, mode="r",
        aff4_type="PackedVersionedCollection", token=self.token)
    if not client_id:
      return log_vals
    else:
      return [val for val in log_vals if val.client_id == client_id]
