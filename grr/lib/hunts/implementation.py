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

import threading

import logging

from grr.lib import access_control
from grr.lib import aff4
from grr.lib import data_store
from grr.lib import flow
from grr.lib import flow_runner
from grr.lib import output_plugin
from grr.lib import queue_manager
from grr.lib import rdfvalue
from grr.lib import registry
from grr.lib import stats
from grr.lib import type_info
from grr.lib import utils
from grr.lib.aff4_objects import aff4_grr
from grr.lib.aff4_objects import collects as aff4_collections
from grr.lib.aff4_objects import sequential_collection
from grr.lib.hunts import results as hunts_results
from grr.lib.rdfvalues import client as rdf_client
from grr.lib.rdfvalues import flows as rdf_flows
from grr.lib.rdfvalues import hunts
from grr.lib.rdfvalues import protodict as rdf_protodict
from grr.lib.rdfvalues import stats as rdf_stats
from grr.lib.rdfvalues import structs as rdf_structs
from grr.proto import flows_pb2
from grr.server import foreman as rdf_foreman


class HuntRunnerArgs(rdf_structs.RDFProtoStruct):
  protobuf = flows_pb2.HuntRunnerArgs

  def Validate(self):
    if self.HasField("client_rule_set"):
      self.client_rule_set.Validate()


class UrnCollection(sequential_collection.IndexedSequentialCollection):
  RDF_TYPE = rdf_client.ClientURN


class HuntErrorCollection(sequential_collection.IndexedSequentialCollection):
  RDF_TYPE = rdf_flows.HuntError


class PluginStatusCollection(sequential_collection.IndexedSequentialCollection):
  RDF_TYPE = output_plugin.OutputPluginBatchProcessingStatus


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

    OUTPUT_PLUGINS = aff4.Attribute("aff4:output_plugins_state",
                                    rdf_flows.FlowState,
                                    "Pickled output plugins.",
                                    versioned=False)

    OUTPUT_PLUGINS_VERIFICATION_RESULTS = aff4.Attribute(
        "aff4:output_plugins_verification_results",
        output_plugin.OutputPluginVerificationResultsList,
        "Verification results list.",
        versioned=False)


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
      self.CallState(messages=[client_id],
                     next_state="RegisterClient",
                     client_id=client_id,
                     start_time=next_client_due)
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
      client_count = int(self.flow_obj.Get(self.flow_obj.Schema.CLIENT_COUNT,
                                           0))

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
      state = self.flow_obj.Get(self.flow_obj.Schema.STATE)
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
            self.flow_obj.Get(self.flow_obj.Schema.STATE))
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
    logs_collection.Add(rdf_flows.FlowLog(
        client_id=None,
        urn=self.session_id,
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

    context = utils.DataObject(
        args=args,
        backtrace=None,
        client_resources=rdf_client.ClientResources(),
        create_time=rdfvalue.RDFDatetime().Now(),
        creator=self.token.username,
        expires=args.expiry_time.Expiry(),
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
        state=rdf_flows.Flow.State.RUNNING,
        usage_stats=rdf_stats.ClientResourcesStats(),
        remaining_cpu_quota=args.cpu_limit,)

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

    event = flow.AuditEvent(user=self.flow_obj.token.username,
                            action=event_action,
                            urn=self.flow_obj.urn,
                            flow_name=flow_name,
                            description=self.args.description)
    flow.Events.PublishEvent("Audit", event, token=self.flow_obj.token)

  def Start(self):
    """This uploads the rules to the foreman and, thus, starts the hunt."""
    # We are already running.
    if self.flow_obj.Get(self.flow_obj.Schema.STATE) == "STARTED":
      return

    # Check the permissions for the hunt here. Note that self.args.token is the
    # original creators's token, while the aff4 object was created with the
    # caller's token. This check therefore ensures that the caller to this
    # method has permissions to start the hunt (not necessarily the original
    # creator of the hunt).
    data_store.DB.security_manager.CheckHuntAccess(self.flow_obj.token,
                                                   self.session_id)

    # Determine when this hunt will expire.
    self.context.expires = self.args.expiry_time.Expiry()

    # When the next client can be scheduled. Implements gradual client
    # recruitment rate according to the client_rate.
    self.context.next_client_due = rdfvalue.RDFDatetime().Now()

    self._CreateAuditEvent("HUNT_STARTED")

    # Start the hunt.
    self.flow_obj.Set(self.flow_obj.Schema.STATE("STARTED"))
    self.flow_obj.Flush()

    if not self.args.add_foreman_rules:
      return

    # Add a new rule to the foreman
    foreman_rule = rdf_foreman.ForemanRule(
        created=rdfvalue.RDFDatetime().Now(),
        expires=self.context.expires,
        description="Hunt %s %s" % (self.session_id, self.args.hunt_name),
        client_rule_set=self.args.client_rule_set)

    foreman_rule.actions.Append(hunt_id=self.session_id,
                                hunt_name=self.args.hunt_name,
                                client_limit=self.args.client_limit)

    # Make sure the rule makes sense.
    foreman_rule.Validate()

    with aff4.FACTORY.Open("aff4:/foreman",
                           mode="rw",
                           token=self.token,
                           aff4_type=aff4_grr.GRRForeman,
                           ignore_cache=True) as foreman:
      foreman_rules = foreman.Get(foreman.Schema.RULES,
                                  default=foreman.Schema.RULES())
      foreman_rules.Append(foreman_rule)
      foreman.Set(foreman_rules)

  def _RemoveForemanRule(self):
    with aff4.FACTORY.Open("aff4:/foreman",
                           mode="rw",
                           token=self.token,
                           ignore_cache=True) as foreman:
      aff4_rules = foreman.Get(foreman.Schema.RULES)
      aff4_rules = foreman.Schema.RULES(
          # Remove those rules which fire off this hunt id.
          [r for r in aff4_rules if r.hunt_id != self.session_id])
      foreman.Set(aff4_rules)

  def _Complete(self):
    """Marks the hunt as completed."""
    self._RemoveForemanRule()
    if "w" in self.flow_obj.mode:
      self.flow_obj.Set(self.flow_obj.Schema.STATE("COMPLETED"))
      self.flow_obj.Flush()

  def Pause(self):
    """Pauses the hunt (removes Foreman rules, does not touch expiry time)."""
    if not self.IsHuntStarted():
      return

    # Make sure the user is allowed to pause this hunt.
    data_store.DB.security_manager.CheckHuntAccess(self.flow_obj.token,
                                                   self.session_id)

    self._RemoveForemanRule()

    self.flow_obj.Set(self.flow_obj.Schema.STATE("PAUSED"))
    self.flow_obj.Flush()

    self._CreateAuditEvent("HUNT_PAUSED")

  def Stop(self):
    """Cancels the hunt (removes Foreman rules, resets expiry time to 0)."""
    # Make sure the user is allowed to stop this hunt.
    data_store.DB.security_manager.CheckHuntAccess(self.flow_obj.token,
                                                   self.session_id)

    self._RemoveForemanRule()
    self.flow_obj.Set(self.flow_obj.Schema.STATE("STOPPED"))
    self.flow_obj.Flush()

    self._CreateAuditEvent("HUNT_STOPPED")

  def IsCompleted(self):
    return self.flow_obj.Get(self.flow_obj.Schema.STATE) == "COMPLETED"

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

  def IsHuntExpired(self):
    return self.context.expires < rdfvalue.RDFDatetime().Now()

  def IsHuntStarted(self):
    """Is this hunt considered started?

    This method is used to check if new clients should be processed by this
    hunt. Note that child flow responses are always processed (As determined by
    IsRunning() but new clients are not allowed to be scheduled unless the hunt
    should be started.

    Returns:
      If a new client is allowed to be scheduled on this hunt.
    """
    state = self.flow_obj.Get(self.flow_obj.Schema.STATE)
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

  def OutstandingRequests(self):
    # Lie about it to prevent us from being destroyed.
    return 1

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
    request_state = rdf_flows.RequestState(id=utils.PRNG.GetULong(),
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


class GRRHunt(flow.GRRFlow):
  """The GRR Hunt class."""

  class SchemaCls(flow.GRRFlow.SchemaCls):
    """The schema for hunts.

    This object stores the persistent information for the hunt.
    """

    CLIENT_COUNT = aff4.Attribute("aff4:client_count",
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
        default="PAUSED")

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
  def creator(self):
    return self.state.context.creator

  def _AddURNToCollection(self, urn, collection_urn):
    # TODO(user): Change to use StaticAdd once all active hunts are
    # migrated.
    try:
      aff4.FACTORY.Open(collection_urn,
                        UrnCollection,
                        mode="rw",
                        token=self.token).Add(urn)
    except IOError:
      aff4_collections.PackedVersionedCollection.AddToCollection(
          collection_urn, [urn],
          sync=False, token=self.token)

  def _AddHuntErrorToCollection(self, error, collection_urn):
    # TODO(user) Change to use StaticAdd once all active hunts are
    # migrated.
    try:
      aff4.FACTORY.Open(collection_urn,
                        HuntErrorCollection,
                        mode="rw",
                        token=self.token).Add(error)
    except IOError:
      aff4_collections.PackedVersionedCollection.AddToCollection(
          collection_urn, [error],
          sync=False, token=self.token)

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
    error = rdf_flows.HuntError(client_id=client_id, backtrace=backtrace)
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
      runner_args = HuntRunnerArgs()

    cls.FilterArgsFromSemanticProtobuf(runner_args, kwargs)

    # Is the required flow a known flow?
    if (runner_args.hunt_name not in cls.classes or
        not aff4.issubclass(cls.classes[runner_args.hunt_name], GRRHunt)):
      raise RuntimeError("Unable to locate hunt %s" % runner_args.hunt_name)

    # Make a new hunt object and initialize its runner.
    hunt_obj = aff4.FACTORY.Create(None,
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

    event = flow.AuditEvent(user=runner_args.token.username,
                            action="HUNT_CREATED",
                            urn=hunt_obj.urn,
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
        state = rdf_flows.RequestState(id=utils.PRNG.GetULong(),
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

        msgs = [rdf_flows.GrrMessage(payload=response,
                                     source=client_id)
                for response in responses]
        try:
          with aff4.FACTORY.Open(self.state.context.results_collection_urn,
                                 hunts_results.HuntResultCollection,
                                 mode="rw",
                                 token=self.token) as collection:
            for msg in msgs:
              collection.Add(msg)
        except IOError:
          aff4_collections.ResultsOutputCollection.AddToCollection(
              self.state.context.results_collection_urn,
              msgs,
              sync=True,
              token=self.token)

        if responses:
          self.RegisterClientWithResults(client_id)

        # Update stats.
        stats.STATS.IncrementCounter("hunt_results_added", delta=len(msgs))
    else:
      self.LogClientError(client_id,
                          log_message=utils.SmartStr(responses.status))

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
    # We need to pass the logs_collection_urn here rather than in __init__ to
    # wait for the hunt urn to be created.
    child_urn = self.runner.CallFlow(
        flow_name=flow_name,
        next_state=next_state,
        base_session_id=base_session_id,
        client_id=client_id,
        request_data=request_data,
        logs_collection_urn=self.logs_collection_urn,
        **kwargs)

    if client_id:
      # But we also create a symlink to it from the client's namespace.
      hunt_link_urn = client_id.Add("flows").Add("%s:hunt" %
                                                 (self.urn.Basename()))

      hunt_link = aff4.FACTORY.Create(hunt_link_urn,
                                      aff4.AFF4Symlink,
                                      token=self.token)

      hunt_link.Set(hunt_link.Schema.SYMLINK_TARGET(child_urn))
      hunt_link.Close()

    return child_urn

  def Name(self):
    return self.state.context.args.hunt_name

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
    self.state.context.Register("output_plugins_base_urn",
                                self.urn.Add("Results"))

    with aff4.FACTORY.Create(self.state.context.results_metadata_urn,
                             HuntResultsMetadata,
                             mode="rw",
                             token=self.token) as results_metadata:

      state = rdf_flows.FlowState()
      try:
        plugins_descriptors = self.state.args.output_plugins
      except AttributeError:
        plugins_descriptors = []

      for index, plugin_descriptor in enumerate(plugins_descriptors):
        output_base_urn = self.state.context.output_plugins_base_urn.Add(
            plugin_descriptor.plugin_name)

        plugin_class = plugin_descriptor.GetPluginClass()
        plugin_obj = plugin_class(self.state.context.results_collection_urn,
                                  output_base_urn=output_base_urn,
                                  args=plugin_descriptor.plugin_args,
                                  token=self.token)

        state.Register("%s_%d" % (plugin_descriptor.plugin_name, index),
                       (plugin_descriptor, plugin_obj.state))

      results_metadata.Set(results_metadata.Schema.OUTPUT_PLUGINS(state))

    # Create the collection for results.
    with aff4.FACTORY.Create(self.state.context.results_collection_urn,
                             hunts_results.HuntResultCollection,
                             mode="w",
                             token=self.token):
      pass

    # Create the collection for logs.
    with aff4.FACTORY.Create(self.logs_collection_urn,
                             flow_runner.FlowLogCollection,
                             mode="w",
                             token=self.token):
      pass

    # Create the collections for urns.
    for urn in [self.all_clients_collection_urn,
                self.completed_clients_collection_urn,
                self.clients_with_results_collection_urn]:
      with aff4.FACTORY.Create(urn, UrnCollection, mode="w", token=self.token):
        pass

    # Create the collection for errors.
    with aff4.FACTORY.Create(self.clients_errors_collection_urn,
                             HuntErrorCollection,
                             mode="w",
                             token=self.token):
      pass

    # Create the collections for PluginStatus messages.
    for urn in [self.output_plugins_status_collection_urn,
                self.output_plugins_errors_collection_urn]:
      with aff4.FACTORY.Create(urn,
                               PluginStatusCollection,
                               mode="w",
                               token=self.token):
        pass

    if not self.state.context.args.description:
      self.SetDescription()

  @flow.StateHandler()
  def End(self):
    """Final state."""

  def MarkClientDone(self, client_id):
    """Adds a client_id to the list of completed tasks."""
    self.RegisterCompletedClient(client_id)

    if self.state.context.args.notification_event:
      status = hunts.HuntNotification(session_id=self.session_id,
                                      client_id=client_id)
      self.Publish(self.state.context.args.notification_event, status)

  def LogClientError(self, client_id, log_message=None, backtrace=None):
    """Logs an error for a client."""
    self.RegisterClientError(client_id,
                             log_message=log_message,
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
    collections = aff4.FACTORY.MultiOpen([self.all_clients_collection_urn,
                                          self.completed_clients_collection_urn,
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
    completed = set(self._GetCollectionItems(
        self.completed_clients_collection_urn))
    outstanding = started - completed

    return {"STARTED": sorted(started),
            "COMPLETED": sorted(completed),
            "OUTSTANDING": sorted(outstanding)}

  def GetClientStates(self, client_list, client_chunk=50):
    """Take in a client list and return dicts with their age and hostname."""
    for client_group in utils.Grouper(client_list, client_chunk):
      for fd in aff4.FACTORY.MultiOpen(client_group,
                                       mode="r",
                                       aff4_type=aff4_grr.VFSGRRClient,
                                       token=self.token):
        result = {}
        result["age"] = fd.Get(fd.Schema.PING)
        result["hostname"] = fd.Get(fd.Schema.HOSTNAME)
        yield (fd.urn, result)

  def GetLog(self, client_id=None):
    log_vals = aff4.FACTORY.Open(self.logs_collection_urn,
                                 mode="r",
                                 token=self.token)
    if not client_id:
      return log_vals
    else:
      return [val for val in log_vals if val.client_id == client_id]

  def Save(self):
    super(GRRHunt, self).Save()
    runner = self.GetRunner()
    if not runner.IsCompleted():
      runner.CheckExpiry()

  @staticmethod
  def GetAllSubflowUrns(hunt_urn, client_urns, token=None):
    """Lists all subflows for a given hunt for all clients in client_urns."""
    client_ids = [urn.Split()[0] for urn in client_urns]
    client_bases = [hunt_urn.Add(client_id) for client_id in client_ids]

    all_flows = []
    act_flows = client_bases

    while act_flows:
      next_flows = []
      for _, children in aff4.FACTORY.MultiListChildren(act_flows, token=token):
        for flow_urn in children:
          next_flows.append(flow_urn)
      all_flows.extend(next_flows)
      act_flows = next_flows

    return all_flows


class HuntInitHook(registry.InitHook):

  def RunOnce(self):
    """Register standard hunt-related stats."""
    stats.STATS.RegisterCounterMetric("hunt_results_added")
