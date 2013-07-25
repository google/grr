#!/usr/bin/env python
"""The implementation of hunts.

A hunt is a mechanism for automatically scheduling flows on a selective subset
of clients, managing these flows, collecting and presenting the combined results
of all these flows.
"""

import os
import re
import struct
import threading
import time

import logging

from grr.lib import access_control
from grr.lib import aff4
from grr.lib import flow
from grr.lib import flow_runner
from grr.lib import rdfvalue
from grr.lib import type_info
from grr.lib import utils
from grr.lib import worker


class GRRHunt(flow.GRRFlow):
  """The GRR Hunt class."""

  # Some common rules.
  MATCH_WINDOWS = rdfvalue.ForemanAttributeRegex(attribute_name="System",
                                                 attribute_regex="Windows")
  MATCH_LINUX = rdfvalue.ForemanAttributeRegex(attribute_name="System",
                                               attribute_regex="Linux")
  MATCH_DARWIN = rdfvalue.ForemanAttributeRegex(attribute_name="System",
                                                attribute_regex="Darwin")

  STATE_STARTED = "started"
  STATE_STOPPED = "stopped"

  class SchemaCls(flow.GRRFlow.SchemaCls):
    """The schema for hunts.

    This object stores the persistent information for the hunt.
    """

    CLIENTS = aff4.Attribute("aff4:clients", rdfvalue.RDFURN,
                             "The list of clients this hunt was run against.",
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

  # The following args are standard for all hunts.
  hunt_typeinfo = type_info.TypeDescriptorSet(
      type_info.Integer(
          description=("Maximum number of clients participating in the hunt. "
                       "Note that this limit can be overshot by a small number "
                       "of clients if there are multiple workers running. Use "
                       "this only for testing."),
          name="client_limit",
          friendly_name="Client Limit",
          default=0),
      type_info.Duration(
          description="Expiry time for the hunt.",
          name="expiry_time",
          friendly_name="Expiry Time",
          default=rdfvalue.Duration("31d")))

  def Initialize(self):
    super(GRRHunt, self).Initialize()
    # Hunts run in multiple threads so we need to protect access.
    self.lock = threading.RLock()

  def InitFromArguments(self, notification_event=None, description=None,
                        **kwargs):
    """Initializes this hunt object from the arguments given."""

    self.InitializeContext(notification_event=notification_event,
                           description=description)

    self._SetTypedArgs(self.state.context, GRRHunt.hunt_typeinfo, kwargs)
    if GRRHunt.hunt_typeinfo != self.hunt_typeinfo:
      self._SetTypedArgs(self.state, self.hunt_typeinfo, kwargs)

    if kwargs:
      raise type_info.UnknownArg("%s: Args %s not known" % (
          self.__class__.__name__, kwargs.keys()))

    if self.state.context.client_limit > 1000:
      # For large hunts, checking client limits creates a high load on the
      # foreman when loading the hunt as rw and therefore we don't allow setting
      # it for large hunts.
      raise RuntimeError("Please specify client_limit <= 1000.")

  def InitializeContext(self, queue=worker.DEFAULT_WORKER_QUEUE,
                        notification_event=None, description=None):
    """Initializes the context of this hunt."""

    self.state.context.update({
        "client_resources": rdfvalue.ClientResources(),
        "cpu_limit": None,
        "create_time": long(time.time() * 1e6),
        "creator": self.token.username,
        "description": description,
        "hunt_name": self.__class__.__name__,
        "hunt_state": self.STATE_STOPPED,
        "network_bytes_limit": None,
        "network_bytes_sent": 0,
        "next_outbound_id": 1,
        "next_processed_request": 1,
        "notification_event": notification_event,
        "notify_to_user": False,
        "outstanding_requests": 0,
        "queue": queue,
        "rules": [],
        "start_time": time.time(),
        "session_id": rdfvalue.SessionID(self.urn),
        "state": rdfvalue.Flow.State.RUNNING,
        "usage_stats": rdfvalue.ClientResourcesStats(),
        "user": self.token.username,
        })

  def GenerateParentFlowURN(self, client_id=None):
    """Returns a urn which will be used as a parent for the hunts flows URNs.

    Flows executed from HuntFlowContext (i.e. flows issued by a hunt) have
    following urn pattern: aff4:/hunts/[hunt_id]/[client_id]/[flow_id].

    aff4:/hunts/[hunt_id]/[client_id] (an AFF4Volume) is symlinked to
    aff4:/[client_id]/flows/[hunt_id]:hunt/[flow_id].  Therefore it's easy
    to check whether hunt has been already scheduled on a given client
    (by doing Stat on a symlink).

    Args:
      client_id: The client_id this hunt will be run on.

    Returns:
      An RDFURN built using this pattern: aff4:/hunts/[hunt_id]/[client_id] or
      this context's session id if self.client_id is None.
    """
    if client_id:
      hunt_urn = rdfvalue.RDFURN(self.session_id)
      parent_flow_urn = hunt_urn.Add(client_id.Basename())

      hunt_link_urn = client_id.Add("flows").Add(
          "%s:hunt" % (hunt_urn.Basename()))
      hunt_link = aff4.FACTORY.Create(hunt_link_urn, "AFF4Symlink",
                                      token=self.token)
      hunt_link.Set(hunt_link.Schema.SYMLINK_TARGET(parent_flow_urn))
      hunt_link.Close()

      return parent_flow_urn
    else:
      return self.session_id

  def CreateRunner(self, *args, **kw):
    kw["token"] = self.token
    return flow_runner.HuntRunner(self, *args, **kw)

  @classmethod
  def GetNewSessionID(cls, queue=worker.DEFAULT_WORKER_QUEUE):
    """Returns a random integer session ID for this flow.

    Args:
      queue: The queue this hunt should be scheduled on.
    Returns:
      a formatted session id string
    """
    return rdfvalue.SessionID(base="aff4:/hunts", queue=queue)

  @classmethod
  def StartHunt(cls, hunt_name, queue=worker.DEFAULT_WORKER_QUEUE,
                token=None, **args):
    """This class method starts new hunts."""
    try:
      hunt_cls = GRRHunt.classes[hunt_name]
    except KeyError:
      raise RuntimeError("Unable to locate hunt %s" % hunt_name)

    hunt_urn = hunt_cls.GetNewSessionID(queue)
    if "hunt" not in str(hunt_urn):
      raise RuntimeError("%s is not a hunt." % hunt_name)
    hunt_obj = aff4.FACTORY.Create(hunt_urn, hunt_name, mode="rw", token=token)
    hunt_obj.InitializeContext(queue=queue)
    hunt_obj.InitFromArguments(**args)
    hunt_obj.Flush()
    return hunt_obj

  def Name(self):
    return self.state.context.hunt_name

  def AddRule(self, rules=None):
    """Adds one more rule for clients that trigger the hunt.

    The hunt will only be triggered on clients that match all the given rules.

    Args:
      rules: A list of ForemanAttributeInteger and ForemanAttributeRegex
             objects.

    Raises:
      RuntimeError: When an invalid attribute name was given in a rule.
    """
    self.state.context.rules.append(
        self.CreateForemanRule(rules, self.session_id))

  @classmethod
  def CreateForemanRule(cls, rules, session_id):
    """Creates a ForemanRule object from a list of ForemanAttributes."""
    result = rdfvalue.ForemanRule(
        created=rdfvalue.RDFDatetime().Now(),
        description="Hunt %s %s" % (utils.SmartUnicode(session_id),
                                    cls.__name__))

    for rule in rules:
      if rule.attribute_name not in aff4.Attribute.NAMES:
        raise RuntimeError("Unknown attribute name: %s." %
                           rule.attribute_name)

      if isinstance(rule, rdfvalue.ForemanAttributeRegex):
        result.regex_rules.Append(rule)

      elif isinstance(rule, rdfvalue.ForemanAttributeInteger):
        result.integer_rules.Append(rule)

      else:
        raise RuntimeError("Unsupported rules type.")

    result.actions.Append(hunt_id=utils.SmartUnicode(session_id),
                          hunt_name=cls.__name__)
    return result

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

  def WriteToDataStore(self):
    """Save current hunt object and hunt flow object states."""
    self.Flush(sync=True)

  def Run(self):
    """This uploads the rules to the foreman and, thus, starts the hunt."""
    if self.state.context.hunt_state == self.STATE_STARTED:
      return

    self.state.context.hunt_state = self.STATE_STARTED
    self.WriteToDataStore()

    for rule in self.state.context.rules:
      # Updating created timestamp of the hunt's rules. This will force Foreman
      # to apply the rules and run corresponding actions once more for every
      # client.
      # Updating rules' "expires" and "client_limit" attributes to current
      # values.
      timestamp = time.time()
      rule.created = int(time.time() * 1e6)
      rule.expires = (timestamp +
                      self.state.context.expiry_time.seconds) * 1e6
      rule.actions[0].client_limit = self.state.context.client_limit or None

    foreman = aff4.FACTORY.Open("aff4:/foreman", mode="rw", token=self.token,
                                aff4_type="GRRForeman", ignore_cache=True)
    foreman_rules = foreman.Get(foreman.Schema.RULES,
                                default=foreman.Schema.RULES())
    foreman_rules.Extend(self.state.context.rules)

    foreman.Set(foreman_rules)
    foreman.Close()

  def Pause(self):
    """Pauses the hunt (removes Foreman rules, does not touch expiry time)."""
    if self.state.context.hunt_state != self.STATE_STARTED:
      return

    foreman = aff4.FACTORY.Open("aff4:/foreman", mode="rw", token=self.token,
                                ignore_cache=True)
    aff4_rules = foreman.Get(foreman.Schema.RULES)
    aff4_rules = foreman.Schema.RULES(
        # Remove those rules which fire off this hunt id.
        [r for r in aff4_rules if r.hunt_id != self.session_id])
    foreman.Set(aff4_rules)
    foreman.Close()

    self.state.context.hunt_state = self.STATE_STOPPED
    self.WriteToDataStore()

  def Stop(self):
    """Cancels the hunt (removes Foreman rules, resets expiry time to 0)."""
    # Expire the hunt so the worker can destroy it.
    self.state.context.expiry_time = rdfvalue.Duration()
    self.Pause()

  def OutstandingRequests(self):
    if (self.state.context.start_time +
        self.state.context.expiry_time.seconds) > time.time():
      # Lie about it to prevent us from being destroyed.
      return 1
    return 0

  @staticmethod
  def StartClient(hunt_id, client_id, client_limit=None):
    """This method is called by the foreman for each client it discovers."""

    token = access_control.ACLToken("Hunt", "hunting")

    if client_limit:
      hunt_obj = aff4.FACTORY.Open(hunt_id, mode="rw",
                                   age=aff4.ALL_TIMES, token=token)

      clients = list(hunt_obj.GetValuesForAttribute(hunt_obj.Schema.CLIENTS))
      if len(clients) >= client_limit:
        return

      client_urn = hunt_obj.Schema.CLIENTS(client_id)

      if client_urn in clients:
        logging.info("This hunt was already scheduled on %s.", client_id)
        return
    else:
      hunt_obj = aff4.FACTORY.Open(hunt_id, "GRRHunt", mode="w",
                                   ignore_cache=True, token=token)

      client_urn = hunt_obj.Schema.CLIENTS(client_id)

    hunt_obj.AddAttribute(client_urn)
    hunt_obj.Flush()

    request_id = struct.unpack("l", os.urandom(struct.calcsize("l")))[0] % 2**32

    state = rdfvalue.RequestState(id=request_id,
                                  session_id=hunt_id,
                                  client_id=client_id,
                                  next_state="Start")

    # Queue the new request.
    with flow_runner.FlowManager(token=token) as flow_manager:
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

  @flow.StateHandler()
  def Start(self, responses):
    """Do the real work here."""

  @flow.StateHandler()
  def End(self):
    """Final state."""

  def MarkClientDone(self, client_id):
    """Adds a client_id to the list of completed tasks."""
    self.MarkClient(client_id,
                    aff4.FACTORY.AFF4Object("GRRHunt").SchemaCls.FINISHED)

    if self.state.context.notification_event:
      status = rdfvalue.HuntNotification(session_id=self.session_id,
                                         client_id=client_id)
      self.Publish(self.state.context.notification_event, status)

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
    client_urn = attribute(client_id)
    self.AddAttribute(client_urn)

  def ProcessClientResourcesStats(self, client_id, status):
    """Process status message from a client and update the stats.

    Args:
      client_id: Client id.
      status: Status returned from the client.

    This method may be implemented in the subclasses. It's called
    once *per every hunt's state per every client*.
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
