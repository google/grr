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
from grr.lib import flow_context
from grr.lib import rdfvalue
from grr.lib import type_info
from grr.lib import utils


class GRRHunt(flow.GRRFlow):
  """The GRR Hunt class."""

  # Some common rules.
  MATCH_WINDOWS = rdfvalue.ForemanAttributeRegex(attribute_name="System",
                                                 attribute_regex="Windows")
  MATCH_LINUX = rdfvalue.ForemanAttributeRegex(attribute_name="System",
                                               attribute_regex="Linux")
  MATCH_DARWIN = rdfvalue.ForemanAttributeRegex(attribute_name="System",
                                                attribute_regex="Darwin")

  # The following args are standard for all hunts.
  hunt_typeinfo = type_info.TypeDescriptorSet(
      type_info.Integer(
          description="Maximum number of clients participating in the hunt.",
          name="client_limit",
          friendly_name="Client Limit",
          default=0),
      type_info.Duration(
          description="Expiry time for the hunt.",
          name="expiry_time",
          friendly_name="Expiry Time",
          default=rdfvalue.Duration("31d")))

  def _GetAFF4Object(self, mode="rw", age=aff4.ALL_TIMES, token=None):
    if mode == "r" and age == aff4.NEWEST_TIME:
      return self.aff4_object
    else:
      return aff4.FACTORY.Create(self.session_id,
                                 "VFSHunt", mode=mode, age=age, token=token)

  def __init__(self, token=None, notification_event=None, **kwargs):
    queue_name = flow_context.DEFAULT_WORKER_QUEUE_NAME

    if token is None:
      raise RuntimeError("You need to supply a token.")

    context = flow_context.HuntFlowContext(client_id=None,
                                           flow_name=self.__class__.__name__,
                                           queue_name=queue_name,
                                           event_id=None,
                                           state=None, token=token,
                                           args=rdfvalue.RDFProtoDict(kwargs))

    self._SetTypedArgs(self.hunt_typeinfo, kwargs)
    super(GRRHunt, self).__init__(context=context, notify_to_user=False,
                                  **kwargs)

    if self.client_limit > 1000:
      # For large hunts, checking client limits creates a high load on the
      # foreman when loading the hunt as rw and therefore we don't allow setting
      # it for large hunts.
      raise RuntimeError("Please specify client_limit <= 1000.")

    self.rules = []
    self.start_time = time.time()
    self.started = False
    self.written_to_datastore = False
    self.next_request_id = 0
    self.notification_event = notification_event
    self.usage_stats = rdfvalue.ClientResourcesStats()

    # This is the URN for the Hunt object we use.
    self.urn = aff4.ROOT_URN.Add("hunts").Add(self.session_id)

    # Hunts run in multiple threads so we need to protect access.
    self.lock = threading.RLock()

  def AddRule(self, rules=None):
    """Adds one more rule for clients that trigger the hunt.

    The hunt will only be triggered on clients that match all the given rules.

    Args:
      rules: A list of ForemanAttributeInteger and ForemanAttributeRegex
             protobufs.

    Raises:
      RuntimeError: When an invalid attribute name was given in a rule.
    """
    timestamp = int(time.time())
    result = rdfvalue.ForemanRule(
        created=timestamp * 1e6,
        description="Hunt %s %s" % (self.context.session_id,
                                    self.__class__.__name__))

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

    result.actions.Append(hunt_id=self.context.session_id,
                          hunt_name=self.__class__.__name__)

    self.rules.append(result)

  def CheckClient(self, client):
    for rule in self.rules:
      if self.CheckRule(client, rule):
        return True
    return False

  def CheckRule(self, client, rule):
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
        if op == rdfvalue.ForemanAttributeInteger.Enum("LESS_THAN"):
          if not value < i.value:
            return False
        elif op == rdfvalue.ForemanAttributeInteger.Enum("GREATER_THAN"):
          if not value > i.value:
            return False
        elif op == rdfvalue.ForemanAttributeInteger.Enum("EQUAL"):
          if not value == i.value:
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

  def WriteToDataStore(self, description=None):
    """Save current hunt object and hunt flow object states."""
    # Write the hunt object. It will be overwritten if the hunt is restarted
    # (Stop() and then Run() are called).
    hunt_obj = self._GetAFF4Object(mode="w", token=self.token)
    hunt_obj.Set(hunt_obj.Schema.CREATOR(self.token.username))
    hunt_obj.Set(hunt_obj.Schema.HUNT_NAME(self.__class__.__name__))
    hunt_obj.Set(hunt_obj.Schema.EXPIRY_TIME(self.expiry_time))
    hunt_obj.Set(hunt_obj.Schema.CLIENT_LIMIT(self.client_limit))

    if self.started:
      hunt_obj.Set(hunt_obj.Schema.STATE(hunt_obj.STATE_STARTED))
    else:
      hunt_obj.Set(hunt_obj.Schema.STATE(hunt_obj.STATE_STOPPED))

    if description:
      hunt_obj.Set(hunt_obj.Schema.DESCRIPTION(description))

    # We don't want to overwrite RDF_FLOW everytime we run/pause the hunt (or
    # we may lose data stored in the overwritten pickled RDF_FLOW object).
    if not self.written_to_datastore:
      self.written_to_datastore = True
      hunt_obj.Set(hunt_obj.Schema.RDF_FLOW(queue=self.session_id, task_id=1,
                                            payload=rdfvalue.Flow(self.Dump())))

    # There is a potential race here where we write the client requests first
    # and pickle the flow later. To avoid this, we have to keep the order and
    # schedule the tasks synchronously.
    hunt_obj.Close(sync=True)

    self.FlushMessages()

  def Run(self, description=None):
    """This uploads the rules to the foreman and, thus, starts the hunt."""
    if self.started:
      return

    self.started = True
    self.WriteToDataStore(description=description)

    for rule in self.rules:
      # Updating created timestamp of the hunt's rules. This will force Foreman
      # to apply the rules and run corresponding actions once more for every
      # client.
      # Updating rules' "expires" and "client_limit" attributes to current
      # values.
      timestamp = time.time()
      rule.created = int(time.time() * 1e6)
      rule.expires = (timestamp + self.expiry_time.seconds) * 1e6
      if self.client_limit:
        rule.actions[0].client_limit = self.client_limit
      else:
        rule.actions[0].client_limit = None

    foreman = aff4.FACTORY.Open("aff4:/foreman", mode="rw", token=self.token,
                                ignore_cache=True)
    foreman_rules = foreman.Get(foreman.Schema.RULES,
                                default=foreman.Schema.RULES())
    foreman_rules.Extend(self.rules)

    foreman.Set(foreman_rules)
    foreman.Close()

  def Pause(self):
    """Pauses the hunt (removes Foreman rules, does not touch expiry time)."""
    if not self.started:
      return

    foreman = aff4.FACTORY.Open("aff4:/foreman", mode="rw", token=self.token,
                                ignore_cache=True)
    aff4_rules = foreman.Get(foreman.Schema.RULES)
    aff4_rules = foreman.Schema.RULES(
        # Remove those rules which fire off this hunt id.
        [r for r in aff4_rules if r.hunt_id != self.session_id])
    foreman.Set(aff4_rules)
    foreman.Close()

    self.started = False
    self.WriteToDataStore()

  def Stop(self):
    """Cancels the hunt (removes Foreman rules, resets expiry time to 0)."""
    # Expire the hunt so the worker can destroy it.
    self.expiry_time = rdfvalue.Duration()
    self.Pause()

  def OutstandingRequests(self):
    if self.start_time + self.expiry_time.seconds > time.time():
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
      hunt_obj = aff4.FACTORY.Create(hunt_id, "VFSHunt",
                                     mode="w", token=token)

    client_urn = hunt_obj.Schema.CLIENTS(client_id)

    hunt_obj.AddAttribute(client_urn)
    hunt_obj.Close()

    request_id = struct.unpack("l", os.urandom(struct.calcsize("l")))[0] % 2**32

    state = rdfvalue.RequestState(id=request_id,
                                  session_id=hunt_id,
                                  client_id=client_id,
                                  next_state="Start")

    # Queue the new request.
    with flow_context.FlowManager(token=token) as flow_manager:
      flow_manager.QueueRequest(hunt_id, state)

      # Send a response.
      msg = rdfvalue.GRRMessage(
          session_id=hunt_id,
          request_id=state.id, response_id=1,
          auth_state=rdfvalue.GRRMessage.Enum("AUTHENTICATED"),
          type=rdfvalue.GRRMessage.Enum("STATUS"),
          payload=rdfvalue.GrrStatus())

      flow_manager.QueueResponse(hunt_id, msg)

      # And notify the worker about it.
      flow_manager.QueueNotification("W", hunt_id)

  def Start(self, responses):
    """Do the real work here."""

  def MarkClientDone(self, client_id):
    """Adds a client_id to the list of completed tasks."""
    self.MarkClient(client_id,
                    aff4.FACTORY.AFF4Object("VFSHunt").SchemaCls.FINISHED)

    if self.notification_event:
      status = rdfvalue.HuntNotification(session_id=self.session_id,
                                         client_id=client_id)
      self.Publish(self.notification_event, status)

  def MarkClientBad(self, client_id):
    """Marks a client as worth investigating."""

    self.MarkClient(client_id,
                    aff4.AFF4Object.classes["VFSHunt"].SchemaCls.BADNESS)

  def LogClientError(self, client_id, log_message=None, backtrace=None):
    """Logs an error for a client."""

    token = access_control.ACLToken("Hunt", "hunting")
    hunt_obj = self._GetAFF4Object(mode="w", age=aff4.NEWEST_TIME, token=token)

    error = hunt_obj.Schema.ERRORS()
    if client_id:
      error.client_id = client_id
    if log_message:
      error.log_message = utils.SmartUnicode(log_message)
    if backtrace:
      error.backtrace = backtrace
    hunt_obj.AddAttribute(error)
    hunt_obj.Close()

  def LogResult(self, client_id, log_message=None, urn=None):
    """Logs a message for a client."""

    token = access_control.ACLToken("Hunt", "hunting")
    hunt_obj = self._GetAFF4Object(mode="w", age=aff4.NEWEST_TIME, token=token)

    log_entry = hunt_obj.Schema.LOG()
    log_entry.client_id = client_id
    if log_message:
      log_entry.log_message = utils.SmartUnicode(log_message)
    if urn:
      log_entry.urn = utils.SmartUnicode(urn)
    hunt_obj.AddAttribute(log_entry)
    hunt_obj.Close()

  def MarkClient(self, client_id, attribute):
    """Adds a client to the list indicated by attribute."""
    token = access_control.ACLToken("Hunt", "hunting")
    hunt_obj = self._GetAFF4Object(mode="w", age=aff4.NEWEST_TIME, token=token)

    client_urn = attribute(client_id)
    hunt_obj.AddAttribute(client_urn)
    hunt_obj.Close()

  def ProcessClientResourcesStats(self, client_id, status):
    """Process status message from a client and update the stats."""
    if not status.child_session_id:
      return

    user_cpu = status.cpu_time_used.user_cpu_time
    system_cpu = status.cpu_time_used.system_cpu_time

    fd = self._GetAFF4Object(mode="w", token=self.token)
    resources = fd.Schema.RESOURCES()
    resources.client_id = client_id
    resources.session_id = status.child_session_id
    resources.cpu_usage.user_cpu_time = user_cpu
    resources.cpu_usage.system_cpu_time = system_cpu
    resources.network_bytes_sent = status.network_bytes_sent
    fd.AddAttribute(resources)
    fd.Close(sync=False)

    self.usage_stats.RegisterResources(resources)

  def Save(self):
    self.lock = None
    super(GRRHunt, self).Save()

  def Load(self):
    self.lock = threading.RLock()
    super(GRRHunt, self).Load()

    if self.aff4_object:
      # Old hunts do not have EXPIRY_TIME and CLIENT_LIMIT set. We have
      # to handle such cases carefully.
      self.expiry_time = self.aff4_object.Get(
          self.aff4_object.Schema.EXPIRY_TIME,
          rdfvalue.Duration(self.expiry_time))
      self.client_limit = self.aff4_object.Get(
          self.aff4_object.Schema.CLIENT_LIMIT,
          rdfvalue.RDFInteger(self.client_limit))

      state = self.aff4_object.Get(self.aff4_object.Schema.STATE)
      if state:
        self.started = (state == self.aff4_object.STATE_STARTED)
