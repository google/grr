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
    self.flow_obj.AddAttribute(
        self.flow_obj.Schema.CLIENTS(client_id))
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
        network_bytes_sent=0,
        next_outbound_id=1,
        next_processed_request=1,
        outstanding_requests=0,
        current_state=None,
        start_time=rdfvalue.RDFDatetime().Now(),

        # Hunts are always in the running state.
        state=rdfvalue.Flow.State.RUNNING,
        usage_stats=rdfvalue.ClientResourcesStats(),
        user=self.token.username,
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
    self.context.Register("next_client_due",
                          rdfvalue.RDFDatetime().Now())

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
    self.QueueNotification(self.session_id, timestamp=start_time)


class GRRHunt(flow.GRRFlow):
  """The GRR Hunt class."""

  # Some common rules.
  MATCH_WINDOWS = rdfvalue.ForemanAttributeRegex(attribute_name="System",
                                                 attribute_regex="Windows")
  MATCH_LINUX = rdfvalue.ForemanAttributeRegex(attribute_name="System",
                                               attribute_regex="Linux")
  MATCH_DARWIN = rdfvalue.ForemanAttributeRegex(attribute_name="System",
                                                attribute_regex="Darwin")

  class SchemaCls(flow.GRRFlow.SchemaCls):
    """The schema for hunts.

    This object stores the persistent information for the hunt.
    """

    CLIENTS = aff4.Attribute("aff4:clients", rdfvalue.RDFURN,
                             "The list of clients this hunt was run against.",
                             creates_new_object_version=False)

    CLIENT_COUNT = aff4.Attribute("aff4:client_count", rdfvalue.RDFInteger,
                                  "The total number of clients scheduled.",
                                  versioned=False,
                                  creates_new_object_version=False)

    FINISHED = aff4.Attribute("aff4:finished", rdfvalue.RDFURN,
                              "The list of clients the hunt has completed on.",
                              creates_new_object_version=False)

    ERRORS = aff4.Attribute("aff4:errors", rdfvalue.HuntError,
                            "The list of clients that returned an error.",
                            creates_new_object_version=False)

    LOG = aff4.Attribute("aff4:result_log", rdfvalue.HuntLog,
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

    if "r" in self.mode:
      self.client_count = self.Get(self.Schema.CLIENT_COUNT)

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

    cls._FilterArgsFromSemanticProtobuf(runner_args, kwargs)

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
      cls._FilterArgsFromSemanticProtobuf(args, kwargs)

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

    with hunt_obj.CreateRunner(runner_args=runner_args) as runner:
      # Allow the hunt to do its own initialization.
      runner.RunStateMethod("Start")

    hunt_obj.Flush()

    return hunt_obj

  @classmethod
  def StartClient(cls, hunt_id, client_id):
    """This method is called by the foreman for each client it discovers.

    Note that this function is performance sensitive since it is called by the
    foreman for every client which needs to be scheduled.

    Args:
      hunt_id: The hunt to schedule.
      client_id: The client that should be added to the hunt.
    """
    token = access_control.ACLToken(username="Hunt", reason="hunting")

    # Now we construct a special response which will be sent to the hunt
    # flow. Randomize the request_id so we do not overwrite other messages in
    # the queue.
    state = rdfvalue.RequestState(id=utils.PRNG.GetULong(),
                                  session_id=hunt_id,
                                  client_id=client_id,
                                  next_state="AddClient")

    # Queue the new request.
    with queue_manager.QueueManager(token=token) as flow_manager:
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
      flow_manager.QueueNotification(hunt_id)

  def Run(self):
    """A shortcut method for starting the hunt."""
    with self.GetRunner() as runner:
      runner.Start()

  def Pause(self):
    """A shortcut method for pausing the hunt."""
    with self.GetRunner() as runner:
      runner.Pause()

  def Stop(self):
    """A shortcut method for stopping the hunt."""
    with self.GetRunner() as runner:
      runner.Stop()

  def CallFlow(self, flow_name=None, next_state=None, request_data=None,
               client_id=None, **kwargs):
    """Create a new child flow from a hunt."""
    base_session_id = None
    if client_id:
      # The flow is stored in the hunt namespace,
      base_session_id = self.urn.Add(client_id.Basename())

    # Actually start the new flow.
    child_urn = self.runner.CallFlow(flow_name=flow_name, next_state=next_state,
                                     base_session_id=base_session_id,
                                     client_id=client_id,
                                     request_data=request_data, **kwargs)

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

  @flow.StateHandler()
  def Start(self):
    """This method is called when the hunt is first created.

    Here we do any global initializations of the hunt we might need.
    """

  @flow.StateHandler()
  def End(self):
    """Final state."""

  def MarkClientDone(self, client_id):
    """Adds a client_id to the list of completed tasks."""
    self.MarkClient(client_id, self.SchemaCls.FINISHED)

    if self.state.context.args.notification_event:
      status = rdfvalue.HuntNotification(session_id=self.session_id,
                                         client_id=client_id)
      self.Publish(self.state.context.args.notification_event, status)

  def LogClientError(self, client_id, log_message=None, backtrace=None):
    """Logs an error for a client."""
    error = self.Schema.ERRORS()
    if client_id:
      error.client_id = client_id
    if log_message:
      error.log_message = utils.SmartUnicode(log_message)
    if backtrace:
      error.backtrace = backtrace
    self.AddAttribute(error)

  def LogResult(self, client_id, log_message=None, urn=None):
    """Logs a message for a client."""
    log_entry = self.Schema.LOG()
    log_entry.client_id = client_id
    if log_message:
      log_entry.log_message = utils.SmartUnicode(log_message)
    if urn:
      log_entry.urn = utils.SmartUnicode(urn)
    self.AddAttribute(log_entry)

  def MarkClient(self, client_id, attribute):
    """Adds a client to the list indicated by attribute."""
    self.AddAttribute(attribute(client_id))

  def ProcessClientResourcesStats(self, client_id, status):
    """Process status message from a client and update the stats.

    This method may be implemented in the subclasses. It's called
    once *per every hunt's state per every client*.

    Args:
      client_id: Client id.
      status: Status returned from the client.
    """

  def _Num(self, attribute):
    return len(set(self.GetValuesForAttribute(attribute)))

  def NumClients(self):
    return self._Num(self.Schema.CLIENTS)

  def NumCompleted(self):
    return self._Num(self.Schema.FINISHED)

  def NumOutstanding(self):
    return self.NumClients() - self.NumCompleted()

  def _List(self, attribute):
    items = self.GetValuesForAttribute(attribute)
    if items:
      print len(items), "items:"
      for item in items:
        print item
    else:
      print "Nothing found."

  def ListClients(self):
    self._List(self.Schema.CLIENTS)

  def GetCompletedClients(self):
    return sorted(self.GetValuesForAttribute(self.Schema.FINISHED))

  def ListCompletedClients(self):
    self._List(self.Schema.FINISHED)

  def GetOutstandingClients(self):
    started = self.GetValuesForAttribute(self.Schema.CLIENTS)
    done = self.GetValuesForAttribute(self.Schema.FINISHED)
    return sorted(list(set(started) - set(done)))

  def ListOutstandingClients(self):
    outstanding = self.GetOutstandingClients()
    if not outstanding:
      print "No outstanding clients."
      return

    print len(outstanding), "outstanding clients:"
    for client in outstanding:
      print client

  def GetClientsByStatus(self):
    """Get all the clients in a dict of {status: [client_list]}."""
    completed = set(self.GetCompletedClients())

    return {"COMPLETED": sorted(completed),
            "OUTSTANDING": self.GetOutstandingClients()}

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

  def PrintLog(self, client_id=None):
    if not client_id:
      self._List(self.Schema.LOG)
      return

    for log in self.GetValuesForAttribute(self.Schema.LOG):
      if log.client_id == client_id:
        print log

  def PrintErrors(self, client_id=None):
    if not client_id:
      self._List(self.Schema.ERRORS)
      return

    for error in self.GetValuesForAttribute(self.Schema.ERRORS):
      if error.client_id == client_id:
        print error
