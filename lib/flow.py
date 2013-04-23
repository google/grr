#!/usr/bin/env python
"""This file defines the base classes for Flows.

A Flow is a state machine which executes actions on the
client. Messages are transmitted between the flow object and the
client with their responses introduced into a state handler within the
flow.
"""


import cPickle as pickle
import functools
import operator
import os
import pdb
import re
import struct
import sys
import threading
import time
import traceback


from M2Crypto import RSA
from M2Crypto import X509

from grr.client import conf as flags
import logging
from grr.client import actions

from grr.lib import access_control
from grr.lib import aff4
from grr.lib import communicator
from grr.lib import config_lib
from grr.lib import data_store
from grr.lib import flow_context
from grr.lib import rdfvalue
from grr.lib import registry
from grr.lib import scheduler
# pylint: disable=W0611
from grr.lib import server_stubs
# pylint: enable=W0611
from grr.lib import stats
from grr.lib import threadpool
from grr.lib import type_info
from grr.lib import utils

# Note: Each thread adds about 8mb for stack space.
config_lib.DEFINE_integer("Threadpool.size", 50,
                          "Number of threads in the shared thread pool.")

config_lib.DEFINE_integer("Worker.task_limit", 2000,
                          "Limits the number of tasks a worker retrieves "
                          "every poll")

config_lib.DEFINE_integer("Frontend.throttle_average_interval", 60,
                          "Time interval over which average request rate is "
                          "calculated when throttling is enabled.")

config_lib.DEFINE_list("Frontend.well_known_flows",
                       ["TransferStore", "GetClientStatsAuto"],
                       "Allow these well known flows to run directly on the "
                       "frontend. Other flows are scheduled as normal.")

config_lib.CONFIG.AddOption(type_info.X509PrivateKey(
    name="PrivateKeys.server_key",
    description="Private key for the front end server."))

config_lib.CONFIG.AddOption(type_info.X509CertificateType(
    name="Frontend.certificate",
    description="An X509 certificate for the frontend server."))


class FlowError(Exception):
  """Raised when we can not retrieve the flow."""


class Responses(object):
  """An object encapsulating all the responses to a request.

  This object is normally only instantiated from the flow StateHandler
  decorator.
  """

  def __init__(self, request=None, responses=None, auth_required=True):
    self.status = None    # A GrrStatus rdfvalue object.
    self.success = True
    self.request = request
    self._auth_required = auth_required
    if request:
      self.request_data = rdfvalue.RDFProtoDict(request.data)
    self._responses = []

    if responses:
      # This may not be needed if we can assume that responses are
      # returned in lexical order from the data_store.
      responses.sort(key=operator.attrgetter("response_id"))

      # The iterator that was returned as part of these responses. This should
      # be passed back to actions that expect an iterator.
      self.iterator = rdfvalue.Iterator()

      # Filter the responses by authorized states
      for msg in responses:
        # Check if the message is authenticated correctly.
        if msg.auth_state == msg.DESYNCHRONIZED or (
            self._auth_required and
            msg.auth_state != msg.AUTHENTICATED):
          logging.info("%s: Messages must be authenticated (Auth state %s)",
                       msg.session_id, msg.auth_state)

          # Skip this message - it is invalid
          continue

        # Check for iterators
        if msg.type == msg.ITERATOR:
          self.iterator.ParseFromString(msg.args)
          continue

        # Look for a status message
        if msg.type == msg.STATUS:
          # Our status is set to the first status message that we see in
          # the responses. We ignore all other messages after that.
          self.status = rdfvalue.GrrStatus(msg.args)

          # Check this to see if the call succeeded
          self.success = self.status.status == self.status.OK

          # Ignore all other messages
          break

        # Use this message
        self._responses.append(msg)

      if self.status is None:
        raise FlowError("No valid Status message.")

    # This is the raw message accessible while going through the iterator
    self.message = None

  def __iter__(self):
    """An iterator which returns all the responses in order."""
    old_response_id = None
    for message in self._responses:
      self.message = rdfvalue.GRRMessage(message)

      # Handle retransmissions
      if self.message.response_id == old_response_id:
        continue

      else:
        old_response_id = self.message.response_id

      if self.message.type == self.message.MESSAGE:
        # FIXME(scudette): Deprecate this once the client returns rdfvalue
        # messages.
        if not self.message.args_rdf_name:
          client_action_name = self.request.request.name
          try:
            action_cls = actions.ActionPlugin.classes[client_action_name]
            if not action_cls.out_rdfvalue:
              raise RuntimeError(
                  "Client action %s does not specify out_rdfvalue" %
                  client_action_name)

          except KeyError:
            raise RuntimeError("Unknown client action %s.", client_action_name)

          yield action_cls.out_rdfvalue(self.message.args)

        else:
          # Flows send back RDFValues. These already contain sufficient context.
          yield self.message.payload

  def First(self):
    """A convenience method to return the first response."""
    for x in self:
      return x

  def __len__(self):
    return len(self._responses)

  def __nonzero__(self):
    return bool(self._responses)


def StateHandler(next_state="End", auth_required=True):
  """A convenience decorator for state methods.

  Args:
    next_state: One or more next states possible from here (can be a
                string or a list of strings). If a state attempts to
                redirect to a state other than on this (with
                CallClient) an exception is raised.

    auth_required: Do we require messages to be authenticated? If the
                message is not authenticated we raise.

  Raises:
    RuntimeError: If a next state is not specified.

  Returns:
    A decorator
  """

  if not isinstance(next_state, (basestring, list, tuple)):
    raise RuntimeError("Next state must be a string.")

  def Decorator(f):
    """Initialised Decorator."""
    # Allow next_state to be a single string
    if isinstance(next_state, basestring):
      next_states = [next_state]
    else:
      next_states = next_state

    @functools.wraps(f)
    def Decorated(self, direct_response, request=None, responses=None):
      """A decorator that defines allowed follow up states for a method."""
      if direct_response is not None:
        return f(self, *direct_response)

      # Record the permitted next states so CallClient() can check.
      self.context.next_states = next_states
      # Prepare a responses object for the state method to use:
      responses = Responses(request=request,
                            responses=responses,
                            auth_required=auth_required)

      if responses.status:
        self.context.SaveResourceUsage(request, responses)

      stats.STATS.Increment("grr_worker_states_run")
      # Run the state method (Allow for flexibility in prototypes)
      args = [self, responses]
      res = f(*args[:f.func_code.co_argcount])

      return res

    # Make sure the state function itself knows where its allowed to
    # go (This is used to introspect the state graph).
    Decorated.next_states = next_states

    return Decorated

  return Decorator


def EventHandler(source_restriction=None, auth_required=True,
                 allow_client_access=False):
  """A convenience decorator for Event Handlers.

  Args:
    source_restriction: A regex which will be applied to the source. The source
      of this message indicates who sent the message (e.g. if a client sent it,
      the client_id while if a flow sent it, the flow name).

    auth_required: Do we require messages to be authenticated? If the
                message is not authenticated we raise.

    allow_client_access: If True this event is allowed to handle published
      events from clients.

  Returns:
    A decorator which injects the following keyword args to the handler:

     message: The original raw message RDFValue (useful for checking the
       source).
     event: The decoded RDFValue.
  """

  def Decorator(f):
    """Initialised Decorator."""

    @functools.wraps(f)
    def Decorated(self, msg):
      """A decorator that assists in enforcing EventListener restrictions."""
      if auth_required and msg.auth_state != msg.AUTHENTICATED:
        raise RuntimeError("Message from %s not authenticated." % msg.source)

      if (not allow_client_access and
          aff4.AFF4Object.VFSGRRClient.CLIENT_ID_RE.match(msg.source)):
        raise RuntimeError("Event does not support clients.")

      if (source_restriction and
          not re.match(source_restriction, msg.source)):
        raise RuntimeError("Message source invalid.")

      stats.STATS.Increment("grr_worker_states_run")
      rdf_msg = rdfvalue.GRRMessage(msg)
      res = f(self, message=rdf_msg, event=rdf_msg.payload)
      return res

    return Decorated

  return Decorator


class GRRFlow(object):
  """A GRRFlow class.

  Flows exist on the server to maintain session state. A flow is a
  state machine with each state being called when a new message is
  received.

  Do not instantiate flows directly. Flows are usually launched from
  FACTORY.StartFlow().
  """

  # This is used to arrange flows into a tree view
  category = ""

  # If this is set, the flow is only displayed in the UI if the user has one of
  # the labels given.
  AUTHORIZED_LABELS = []

  __metaclass__ = registry.MetaclassRegistry

  # Should ACLs be enforced on this flow? This implies the user must have full
  # access to the client before they can run this flow.
  ACL_ENFORCED = True

  # A list of type descriptor for this flow. The Flow constructor accept all
  # these args the these type descriptors themselves implement the required
  # validation. Therefore the flow constructor should take no real args (other
  # than **kwargs) and instead specify all required parameters as a list of
  # TypeInfoObject instances.

  # The following args are standard for all flows.
  flow_typeinfo = type_info.TypeDescriptorSet(
      type_info.RDFEnum(
          description="The priority used for this flow.",
          name="priority",
          rdfclass=rdfvalue.GRRMessage,
          enum_name="Priority",
          default=rdfvalue.GRRMessage.Enum("MEDIUM_PRIORITY")),

      type_info.Bool(
          description="Should a notification be sent to the initiator.",
          name="notify_to_user",
          friendly_name="Notify at Completion",
          default=True),

      type_info.Bool(
          description="Should send replies back to the parent flow or not.",
          name="send_replies",
          friendly_name="Send Replies",
          hidden=True,
          default=True),

      type_info.String(
          description=("A well known flow session_id of an event listener. An "
                       "event will be published to this listener once the "
                       "flow finishes."),
          name="notification_event",
          friendly_name="Notification Event",
          hidden=True,
          default=None),
      )

  # Should we notify to the user about the progress of this flow?
  def __init__(self, context=None, **kwargs):
    """Constructor for the Flow.

    Args:
      context: A FlowContext object that will save the state for this flow.

    Raises:
      RuntimeError: No context object was passed to this flow.
      AttributeError: If some of the args are invalid.
    """
    if context is None:
      raise RuntimeError("No context given for flow %s." %
                         self.__class__.__name__)

    self.context = context
    self.context.SetFlowObj(self)
    self._user_notified = False   # Have we sent a notification to the user.

    self._SetTypedArgs(self.flow_typeinfo, kwargs)
    if GRRFlow.flow_typeinfo != self.flow_typeinfo:
      self._SetTypedArgs(GRRFlow.flow_typeinfo, kwargs)

    if kwargs:
      raise type_info.UnknownArg("%s: Args %s not known" % (
          self.__class__.__name__, kwargs.keys()))

    stats.STATS.Increment("grr_flows_created")

  def _SetTypedArgs(self, type_descriptor, kwargs):
    """Sets our attributes from the type_descriptor."""
    # Parse and validate the args to this flow. This will raise if the args are
    # invalid.
    for name, value in type_descriptor.ParseArgs(kwargs):
      # Make sure we dont trash an internal name.
      if getattr(self, name, None) is not None:
        raise AttributeError("Flow arg name can not be the same "
                             "as an internal flow attribute: %s" % name)

      setattr(self, name, value)

  # Set up some proxy methods to allow easy access to the context.
  def GetFlowArgs(self):
    return self.context.GetFlowArgs()

  def CallClient(self, action_name, request=None, next_state=None,
                 request_data=None, **kwargs):
    return self.context.CallClient(action_name, request, next_state,
                                   request_data, **kwargs)

  def CallState(self, messages=None, next_state="", delay=0):
    return self.context.CallState(messages=messages, next_state=next_state,
                                  delay=delay)

  def CallFlow(self, flow_name, next_state=None, request_data=None, **kwargs):
    return self.context.CallFlow(FACTORY, flow_name, next_state, request_data,
                                 **kwargs)

  def FlushMessages(self):
    return self.context.FlushMessages()

  def ProcessCompletedRequests(self, unused_thread_pool):
    return self.context.ProcessCompletedRequests(unused_thread_pool)

  def OutstandingRequests(self):
    return self.context.OutstandingRequests()

  def SendReply(self, response):
    return self.context.SendReply(response)

  def Error(self, backtrace, client_id=None):
    return self.context.Error(backtrace, client_id=client_id)

  def SetState(self, state):
    return self.context.SetState(state)

  def Terminate(self):
    return self.context.Terminate()

  def IsRunning(self):
    return self.context.IsRunning()

  @property
  def data_store(self):
    return self.context.data_store

  @data_store.setter
  def data_store(self, datastore):
    self.context.data_store = datastore

  @property
  def session_id(self):
    return self.context.session_id

  @session_id.setter
  def session_id(self, session_id):
    self.context.session_id = session_id
    self.context.rdf_flow.session_id = session_id

  @property
  def client_id(self):
    return self.context.client_id

  @client_id.setter
  def client_id(self, client_id):
    self.context.client_id = client_id

  @property
  def user(self):
    return self.context.user

  @user.setter
  def user(self, user):
    self.context.user = user

  @property
  def aff4_object(self):
    return self.rdf_flow.aff4_object

  @property
  def rdf_flow(self):
    return self.context.rdf_flow

  @rdf_flow.setter
  def rdf_flow(self, rdf_flow):
    self.context.rdf_flow = rdf_flow

  @property
  def token(self):
    return self.context.token

  def Start(self, unused_message=None):
    """The first state of the flow."""
    pass

  @StateHandler()
  def End(self):
    """Final state.

    This method is called prior to destruction of the flow to give
    the flow a chance to clean up.
    """
    if not self._user_notified:
      # Only send a notification if one hasn't already been sent in this flow.
      self.Notify("FlowStatus", self.client_id,
                  "Flow %s completed" % self.__class__.__name__)

  def Load(self):
    """Loads the flow from storage.

    This hook point is called after retrieval from storage and prior to state
    execution.
    """

  def Save(self):
    """Saves the flow to disk.

    This hook point is called before we get dumped to storage. Note that for
    efficiency we do not generally get serialized on every state transition but
    we may be serialized on any transition.

    If we want to hold something which should only exist while running and not
    in serialized form (e.g. database handle), we can override the Load() and
    Save() methods to remove the object during Save() and recreate it during
    Load().
    """

  def Dump(self):
    """Returns an rdfvalue Flow object with ourselves in it.

    Returns:
      an rdfvalue.Flow object.
    """
    # Allow the flow author to hook this
    self.Save()

    result = self.rdf_flow
    result.pickle = ""
    result.pickle = pickle.dumps(self)

    self.Load()

    return result

  def Log(self, format_str, *args):
    """Logs the message using the flow's standard logging.

    Args:
      format_str: Format string
      *args: arguments to the format string
    """
    logging.info(format_str, *args)

    try:
      # The status message is always in unicode
      status = format_str % args
    except TypeError:
      logging.error("Tried to log a format string with the wrong number "
                    "of arguments: %s", format_str)
      status = format_str

    self.context.SetStatus(utils.SmartUnicode(status))

    # Add the message to the flow's log attribute
    self.data_store.Set(self.session_id,
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
    if self.notify_to_user:
      # Prefix the message with the hostname of the client we are running
      # against.
      if self.client_id:
        client_fd = aff4.FACTORY.Open(self.client_id, mode="rw",
                                      token=self.token)
        hostname = client_fd.Get(client_fd.Schema.HOSTNAME) or ""
        client_msg = "%s: %s" % (hostname, msg)

      # Add notification to the User object.
      fd = aff4.FACTORY.Create(aff4.ROOT_URN.Add("users").Add(
          self.token.username), "GRRUser", mode="rw", token=self.token)

      # Queue notifications to the user.
      fd.Notify(message_type, subject, client_msg, self.session_id)
      fd.Close()

      # Add notifications to the flow.
      notification = rdfvalue.Notification(
          type=message_type, subject=utils.SmartUnicode(subject),
          message=utils.SmartUnicode(msg),
          source=utils.SmartUnicode(self.session_id),
          timestamp=long(time.time() * 1e6))

      self.data_store.Set(self.session_id,
                          aff4.AFF4Object.GRRFlow.SchemaCls.NOTIFICATION,
                          notification, replace=False, sync=False,
                          token=self.token)
      self._user_notified = True

    # TODO(user): This should be using PublishEvent()
    if self.notification_event:
      if self.rdf_flow.state == rdfvalue.Flow.Enum("ERROR"):
        status = rdfvalue.FlowNotification.Enum("ERROR")
      else:
        status = rdfvalue.FlowNotification.Enum("OK")

      event = rdfvalue.FlowNotification(
          session_id=utils.SmartUnicode(self.session_id),
          flow_name=self.__class__.__name__,
          client_id=self.client_id,
          status=status)
      msg = rdfvalue.GRRMessage(
          payload=event,
          session_id=self.notification_event,
          auth_state=rdfvalue.GRRMessage.Enum("AUTHENTICATED"),
          source=self.__class__.__name__)
      # Randomize the response id or events will get overwritten.
      msg.response_id = msg.task_id

      with flow_context.WellKnownFlowManager(
          token=self.token) as flow_manager:
        flow_manager.QueueResponse(self.notification_event, msg)

      # Notify the worker of the pending sessions.
      queue = scheduler.SCHEDULER.QueueNameFromURN(self.notification_event)
      scheduler.SCHEDULER.NotifyQueue(queue, self.notification_event,
                                      token=self.token)

  def Publish(self, event_name, message=None, session_id=None):
    """Publish a message to a queue.

    Args:
       event_name: The name of the event to publish to.
       message: An RDFValue instance to publish to the event listeners.
       session_id: The session id to send from, defaults to self.session_id.
    """
    result = message

    # TODO(user): Lets not support publishing of protobufs since we
    # want to deprecate them.
    if not isinstance(message, rdfvalue.GRRMessage):
      result = rdfvalue.GRRMessage(payload=message)

    result.session_id = session_id or self.session_id
    result.auth_state = rdfvalue.GRRMessage.Enum("AUTHENTICATED")
    result.source = self.__class__.__name__

    PublishEvent(event_name, result, token=self.token)


class WellKnownFlow(GRRFlow):
  """A flow with a well known session_id.

  Since clients always need to communicate with a flow, it is
  impossible for them to asynchronously begin communication with the
  server because normally the flow's session ID is randomly
  generated. Sometimes we want the client to communicate with the
  server spontaneously - so it needs a well known session ID.

  This base class defines such flows with a well known
  session_id. Clients can communicate with these flows by themselves
  without prior arrangement.

  Note that necessarily well known flows do not have any state and
  therefore do not need state handlers. In this regard a WellKnownFlow
  is basically an RPC mechanism - if you need to respond with a
  complex sequence of actions you will need to spawn a new flow from
  here..
  """
  # This is the session_id that will be used to register these flows
  well_known_session_id = None

  # Well known flows are not browsable
  category = None

  def _SafeProcessMessage(self, *args, **kwargs):
    try:
      self.ProcessMessage(*args, **kwargs)
    except Exception as e:  # pylint: disable=broad-except
      logging.error("Error in WellKnownFlow.ProcessMessage: %s", e)

  def __init__(self, *args, **kwargs):
    GRRFlow.__init__(self, *args, **kwargs)

    # Tag this flow as well known
    self.SetState(rdfvalue.Flow.Enum("WELL_KNOWN"))
    self.session_id = self.well_known_session_id
    # Well known flows are not user initiated so the default is no notification.
    self.notify_to_user = False

  def CallState(self, messages=None, next_state=None, delay=0):
    """Well known flows have no states to call."""
    pass

  def _GetNewSessionID(self, unused_queue_name):
    # Always return a well known session id for this flow:
    return self.well_known_session_id

  def OutstandingRequests(self):
    # Lie about it to prevent us from being destroyed
    return 1

  def ProcessCompletedRequests(self, thread_pool):
    """For WellKnownFlows we receive these messages directly."""
    try:
      priority = rdfvalue.GRRMessage.Enum("MEDIUM_PRIORITY")
      with flow_context.WellKnownFlowManager(
          token=self.token, store=self.data_store) as flow_manager:
        for request, responses in flow_manager.FetchRequestsAndResponses(
            self.session_id):
          for msg in responses:
            priority = msg.priority
            thread_pool.AddTask(target=self._SafeProcessMessage,
                                args=(msg,), name=self.__class__.__name__)

          flow_manager.DeleteFlowRequestStates(self.session_id, request,
                                               responses)
    except flow_context.MoreDataException:
      # There is more data for this flow so we have to tell the worker to
      # fetch more messages later.
      scheduler.SCHEDULER.NotifyQueue(self.context.queue_name, self.session_id,
                                      priority=priority, token=self.token)

  def ProcessMessage(self, msg):
    """This is where messages get processed.

    Override in derived classes:

    Args:
       msg: The GrrMessage sent by the client. Note that this
            message is not authenticated.
    """


class EventListener(WellKnownFlow):
  """Base Class for all Event Listeners.

  Event listeners are simply well known flows which extend the EventListener
  class. Registration for an event simply means that the event name is specified
  in the EVENTS constant.

  We will process any messages which are sent to any of the events
  specified. Events are just string names.
  """
  EVENTS = []

  @EventHandler(auth_required=True)
  def ProcessMessage(self, message=None, event=None):
    """Handler for the event.

    NOTE: The message could arrive from any source, and could be
    unauthenticated. Since the EventListener is just a WellKnownFlow, the
    message could also arrive from a malicious client!

    It is therefore essential to verify the source of the event. This can be a
    flow session id, or an entity such as the FrontEnd, or the Worker.

    Args:
      message: A GrrMessage instance which was sent to the event listener.
      event: The decoded event object.
    """


def PublishEvent(event_name, msg, token=None):
  """Publish the message into all listeners of the event."""
  if not msg.source:
    raise RuntimeError("Message must have a valid source.")

  if not isinstance(msg, rdfvalue.RDFValue):
    raise ValueError("Can only publish RDFValue instances.")

  # Randomize the response id or events will get overwritten.
  msg.response_id = msg.task_id = rdfvalue.GRRMessage().task_id

  sessions_queued = []
  for event_cls in EventListener.classes.values():
    if (aff4.issubclass(event_cls, EventListener) and
        event_name in getattr(event_cls, "EVENTS", [])):

      if event_cls.well_known_session_id is None:
        logging.error("Well known flow %s has no session_id.",
                      event_cls.__name__)
      else:
        sessions_queued.append(event_cls.well_known_session_id)

      # Forward the message to the well known flow's queue.
      with flow_context.WellKnownFlowManager(token=token) as flow_manager:
        flow_manager.QueueResponse(event_cls.well_known_session_id, msg)

  # Notify all the workers of their pending sessions.
  for queue, session_ids in utils.GroupBy(
      sessions_queued, scheduler.SCHEDULER.QueueNameFromURN):
    scheduler.SCHEDULER.MultiNotifyQueue(
        queue, session_ids, [msg.priority] * len(session_ids), token=token)


class FlowFactory(object):
  """A factory for flow objects.

  This class also presents some useful utility functions for managing
  flows.
  """

  def __init__(self):
    self.outstanding_flows = set()

  #  _parameters are private so pylint: disable=C6409
  def StartFlow(self, client_id, flow_name,
                queue_name=flow_context.DEFAULT_WORKER_QUEUE_NAME,
                event_id=None, token=None, priority=None, cpu_limit=None,
                notification_event=None, parent_context=None,
                _request_state=None, _store=None, **kw):
    """Creates and executes a new flow.

    Args:
      client_id: The URL of an existing client or None for well known flows.
      flow_name: The name of the flow to start (from the registry).
      queue_name: The name of the queue to invoke the flow.
      event_id: A logging event id for issuing further logs.
      token: The access token to be used for this request.
      priority: The priority of the started flow.
      cpu_limit: A limit on the client cpu seconds used by this flow.
      notification_event: The session_id of an event to be published when the
                          flow completes.
      parent_context: The context of the parent flow or None if this is a top
                      level flow.
      _request_state: A parent flow's request state (Used internally only).
      _store: The data store to use for running this flow (only used for
              testing).
      **kw: flow specific keywords to be passed to the constructor.

    Returns:
      the session id of the flow.

    Raises:
      IOError: If the client_id is invalid.
    """
    try:
      flow_cls = GRRFlow.classes[flow_name]
    except KeyError:
      stats.STATS.Increment("grr_flow_invalid_flow_count")
      raise RuntimeError("Unable to locate flow %s" % flow_name)

    # Make sure we are allowed to run this flow.
    data_store.DB.security_manager.CheckAccess(token, [aff4.ROOT_URN.Add(
        client_id or "").Add(flow_name)], "x")

    # From now on we run with supervisor access
    if token is None:
      token = data_store.default_token.Copy()
    else:
      token = token.Copy()

    token.supervisor = True

    # Extend the expiry time of this token indefinitely.
    token.expiry = sys.maxint

    # Only the supervisor can create the containing AFF4 object.
    aff4_flow_obj = aff4.FACTORY.Create(None, "GRRFlow", token=token)

    # Strip out any private args so they do not get converted.
    args = dict([(k, v) for k, v in kw.items() if not k.startswith("_")])

    context = flow_context.FlowContext(client_id=client_id,
                                       flow_name=flow_cls.__name__,
                                       queue_name=queue_name, args=args,
                                       parent_context=parent_context,
                                       event_id=event_id, _store=_store,
                                       state=_request_state, token=token,
                                       priority=priority, cpu_limit=cpu_limit)

    flow_obj = flow_cls(context=context, notification_event=notification_event,
                        **kw)

    if client_id:
      # This client may exist already but we create it anyway.
      client = aff4.FACTORY.Create(client_id, "VFSGRRClient", token=token)

      # Add this flow to the client
      client.AddAttribute(client.Schema.FLOW(flow_obj.session_id))
      client.Flush()

    logging.info("Scheduling %s(%s) on %s: %s", flow_obj.session_id,
                 flow_name, client_id, kw)
    # Just run the first state. NOTE: The Start method always runs on the thread
    # that starts the flow so it must be very fast, basically just CallClient()
    # CallFlow() or CallState(). If a long delay is needed, this should call
    # CallState() and put the heavy lifting in another state. Similarly it is
    # preferred that any sanity checking of parameters etc be done by the
    # Start() method so the flow invocation can be aborted immediately.
    flow_obj.Start(None)

    # The flow does not need to actually remain running.
    if not flow_obj.OutstandingRequests():
      flow_obj.Terminate()

    # Flows always have task id 1.
    flow_obj.rdf_flow.ts_id = 1
    aff4_flow_obj.SetFlowObj(flow_obj)

    aff4_flow_obj.Close()

    # TODO(user): This needs to return an RDFURN object not a string.
    return str(aff4_flow_obj.urn)

  def ListFlow(self, client_id, limit=1000, token=None):
    """Fetches the flow based on session_id.

    Args:
      client_id: Id of the client to retrieve tasks for.
      limit: Max number of flows to retrieve.
      token: The access token to be used for this request.

    Returns:
      A list of flow RDFValues.
    """
    tasks = scheduler.SCHEDULER.Query(queue=client_id, limit=limit, token=token)
    return [t for t in tasks
            if t.payload.state != rdfvalue.Flow.Enum("TERMINATED")]

  def FetchFlow(self, session_id, sync=True, lock=True, token=None):
    """Fetches the flow based on session_id.

    This also grabs a lock on the flow. We might block here for some
    time.

    Args:
      session_id: Session id for the flow.
      sync: be synchronous - if we cant get the lock on a flow we wait
            until we do. If False we raise a LockError()
      lock: Should we lock the flow.
      token: The access token to be used for this request.

    Returns:
      A flow rdfvalue.

    Raises:
      LockError: If we are asynchronous and can not obtain the lock.
    """
    try:
      aff4_flow = aff4.FACTORY.Open(session_id, required_type="GRRFlow",
                                    age=aff4.NEWEST_TIME, token=token,
                                    ignore_cache=True)
    except IOError as e:
      logging.error("Flow %s can not be opened: %s", session_id, str(e))
      if lock:
        raise LockError(session_id)
      return None

    rdf_flow = aff4_flow.GetRDFFlow()
    if rdf_flow is None:
      logging.error("Flow %s has no pickled object.", session_id)
      return None
    rdf_flow.aff4_object = aff4_flow
    rdf_flow.ts_id = 1
    # NOTE: If flow is terminated do not lock it.
    if not lock or rdf_flow.state == rdfvalue.Flow.Enum("TERMINATED"):
      return rdf_flow

    # Try to grab the lock on the flow
    while True:
      flow_tasks = scheduler.SCHEDULER.QueryAndOwn(
          queue=session_id, limit=1,
          lease_seconds=1200, token=token)
      self.outstanding_flows.add(session_id)

      if flow_tasks: break

      # We can not wait - just raise now
      if not sync: raise LockError(session_id)
      logging.info("Waiting for flow %s", session_id)
      time.sleep(1)

    # We have to fetch the flow once more, because it could change while
    # we were waiting for the lock.
    try:
      aff4_flow = aff4.FACTORY.Open(session_id, required_type="GRRFlow",
                                    age=aff4.NEWEST_TIME, token=token,
                                    ignore_cache=True)
    except IOError as e:
      logging.error("Flow %s can not be opened: %s", session_id, str(e))
      return None

    rdf_flow = aff4_flow.GetRDFFlow()
    rdf_flow.aff4_object = aff4_flow
    rdf_flow.ts_id = 1
    logging.info("Got flow %s %s", session_id, rdf_flow.name)

    return rdf_flow

  def ReturnFlow(self, rdf_flow, token=None):
    """Returns the flow when we are done with it.

    If the flow is marked as terminated we can delete it now.

    Args:
      rdf_flow: An rdfvalue flow object.
      token: The access token to be used for this request.
    """
    self.outstanding_flows.discard(rdf_flow.session_id)

    # Is this flow still alive?
    if rdf_flow.state != rdfvalue.Flow.Enum("TERMINATED"):
      logging.info("Returning flow %s", rdf_flow.session_id)

      if rdf_flow.aff4_object:
        aff4_type = rdf_flow.aff4_object.Get(rdf_flow.aff4_object.Schema.TYPE)
      else:
        aff4_type = "GRRFlow"

      aff4_flow = aff4.FACTORY.Create(rdf_flow.session_id, aff4_type, mode="w",
                                      token=token)
      # TODO(user): this is a hack. We're doing this because we do know
      # that the flow object already exists (as it was started by StartFlow).
      # Therefore there's no need for Create() to add TYPE attribute.
      setattr(aff4_flow, "_new_version", False)
      aff4_flow.Set(aff4_flow.Schema.RDF_FLOW,
                    rdfvalue.GRRMessage(queue=rdf_flow.session_id,
                                        task_id=1, payload=rdf_flow))
      aff4_flow.Close()
    else:
      logging.info("Deleting flow %s", rdf_flow.session_id)
      self.DeleteFlow(rdf_flow, token=token)

  def TerminateFlow(self, flow_id, reason=None, token=None, force=False,
                    _store=None):
    """Terminate a flow.

    Args:
      flow_id: The flow session_id to terminate.
      reason: A reason to log.
      token: The access token to be used for this request.
      force: If True then terminate locked flows hard.
      _store: The data store to use for running this flow (only used for
         testing)

    Raises:
      FlowError: If the flow can not be found.
    """
    rdf_flow = self.FetchFlow(flow_id, sync=False,
                              lock=not force, token=token)

    if rdf_flow.state != rdfvalue.Flow.Enum("RUNNING"):
      return

    flow_obj = self.LoadFlow(rdf_flow)
    if not flow_obj:
      raise FlowError("Could not terminate flow %s" % flow_id)

    # Override the data store for testing.
    if _store:
      flow_obj.data_store = _store

    if token is None:
      token = access_control.ACLToken()

    if reason is None:
      reason = "Manual termination by console."

    flow_obj.Error(reason)
    flow_obj.Log("Terminated by user {0}. Reason: {1}".format(token.username,
                                                              reason))
    # Make sure we are only allowed to terminate this flow, if we are allowed to
    # run it.
    data_store.DB.security_manager.CheckAccess(token, [aff4.ROOT_URN.Add(
        flow_obj.client_id).Add(flow_obj.__class__.__name__)], "x")

    # From now on we run with supervisor access
    super_token = access_control.ACLToken()
    super_token.supervisor = True

    # Also terminate its children
    for child in rdf_flow.children:
      self.TerminateFlow(child, reason=None, token=super_token, force=force)

    self.ReturnFlow(flow_obj.rdf_flow, token=super_token)

  def DeleteFlow(self, rdf_flow, token=None):
    """Deletes the flow from the Task Scheduler."""
    rdf_flow.state = rdfvalue.Flow.Enum("TERMINATED")

    if rdf_flow.aff4_object:
      aff4_type = rdf_flow.aff4_object.Get(rdf_flow.aff4_object.Schema.TYPE)
    else:
      aff4_type = "GRRFlow"

    aff4_flow = aff4.FACTORY.Create(rdf_flow.session_id, aff4_type, mode="w",
                                    token=token)
    # TODO(user): this is a hack. We're doing this because we do know
    # that the flow object already exists (as it was started by StartFlow).
    # Therefore there's no need for Create() to add TYPE attribute.
    setattr(aff4_flow, "_new_version", False)
    aff4_flow.Set(aff4_flow.Schema.RDF_FLOW,
                  rdfvalue.GRRMessage(queue=rdf_flow.session_id,
                                      task_id=1, payload=rdf_flow))
    aff4_flow.Close()

  def LoadFlow(self, rdf_flow, forced_token=None):
    """Restores the flow stored in rdf_flow.

    We might want to make this more flexible down the track
    (e.g. autoload new flows to avoid having to restart workers.)

    Args:
      rdf_flow: The flow rdfvalue.
      forced_token: If not None, this token will override the previously
                    pickled flow's token
    Returns:
      A complete flow object.

    Raises:
      FlowError: if we are unable to restore this flow.
    """
    if rdf_flow is None: return

    try:
      result = pickle.loads(rdf_flow.pickle)
      result.data_store = data_store.DB
      result.context.outbound_lock = threading.Lock()
      result.context.flow_manager = flow_context.FlowManager(
          token=result.context.token,
          store=data_store.DB)
      if forced_token:
        result.context.token = forced_token

      # Restore the rdf_flow here
      result.rdf_flow = rdf_flow

      # Allow the flow to hook the load operation.
      result.Load()
    # If we can not unpickle this for whatever reason we cant do anything about
    # it - just convert all exceptions to a FlowError and let our callers deal
    # with it..
    except Exception as e:
      msg = "Unable to handle Flow %s: %s" % (rdf_flow.name, e)
      logging.error(msg)
      raise FlowError(msg)

    return result

  def GetFlowObj(self, session_id, token=None):
    return self.LoadFlow(self.FetchFlow(
        session_id, lock=False, token=token), forced_token=token)

  def QueryFlows(self, session_ids, token=None):
    """This queries multiple flows at once.

    This method works like FetchFlow above but there is no locking.
    That means that you can open multiple flows at once for reading but
    you cannot lease them with this function.

    Args:
      session_ids: A list of session ids to get.
      token: The access token to be used for this request.
    Returns:
      A list of rdfvalue flow objects.
    """
    result = scheduler.SCHEDULER.MultiQuery(session_ids,
                                            token=token)
    return [r[0][1].payload for r in result.values()]

  def GetFlowObjs(self, session_ids, token=None):
    rdf_flows = self.QueryFlows(session_ids, token=token)
    result = []
    for pb in rdf_flows:
      try:
        result.append(self.LoadFlow(pb, forced_token=token))
      except FlowError as e:
        logging.error("Can't load Flow %s: %s", pb.name, e)

    return result


class ServerPubKeyCache(communicator.PubKeyCache):
  """A public key cache used by servers getting the key from the AFF4 client."""

  def __init__(self, client_cache, token=None):
    self.client_cache = client_cache
    self.token = token

  def GetRSAPublicKey(self, common_name="Server"):
    """Retrieves the public key for the common_name from data_store.

    This maintains a cache of key pairs or loads them instead from
    data_store.

    Args:
      common_name: The common_name of the key we need.

    Returns:
      A valid rsa public key.

    Raises:
       communicator.UnknownClientCert: cert not found - this will cause the
       client to re-enroll thereby updating our certificate store.
    """
    # We dont want a unicode object here
    common_name = str(common_name)
    try:
      client = self.client_cache.Get(common_name)
      cert = client.Get(client.Schema.CERT)
      return cert.GetPubKey()

    except (KeyError, AttributeError):
      # Fetch the client's cert - We will be updating its clock attribute.
      client = aff4.FACTORY.Create(common_name, "VFSGRRClient", mode="rw",
                                   token=self.token, ignore_cache=True)
      cert = client.Get(client.Schema.CERT)
      if not cert:
        stats.STATS.Increment("grr_unique_clients")
        raise communicator.UnknownClientCert("Cert not found")

      if cert.common_name != common_name:
        logging.error("Stored cert mismatch for %s", common_name)
        raise communicator.UnknownClientCert("Stored cert mismatch")

      self.client_cache.Put(common_name, client)

      return cert.GetPubKey()


class ServerCommunicator(communicator.Communicator):
  """A communicator which stores certificates using AFF4."""

  def __init__(self, certificate, private_key, token=None):
    self.client_cache = utils.FastStore(1000)
    self.token = token
    super(ServerCommunicator, self).__init__(certificate=certificate,
                                             private_key=private_key)
    self.pub_key_cache = ServerPubKeyCache(self.client_cache, token=token)

  def GetCipher(self, common_name="Server"):
    # This ensures the client is cached
    client = self.client_cache.Get(common_name)
    cipher = client.Get(client.Schema.CIPHER)
    if cipher:
      return cipher

    raise KeyError("Cipher not found.")

  def SetCipher(self, common_name, cipher):
    try:
      client = self.client_cache.Get(common_name)
    except KeyError:
      # Fetch the client's cert
      client = aff4.FACTORY.Create(common_name, "VFSGRRClient",
                                   token=self.token, ignore_cache=True)
      self.client_cache.Put(common_name, client)

    client.Set(client.Schema.CIPHER(cipher))

  def _LoadOurCertificate(self):
    """Loads the server certificate."""
    self.cert = X509.load_cert_string(str(self.certificate))

    # Our common name
    self.common_name = self.pub_key_cache.GetCNFromCert(self.cert)

  def VerifyMessageSignature(self, response_comms, signed_message_list,
                             cipher, api_version):
    """Verifies the message list signature.

    In the server we check that the timestamp is later than the ping timestamp
    stored with the client. This ensures that client responses can not be
    replayed.

    Args:
       response_comms: The raw response_comms rdfvalue.
       signed_message_list: The SignedMessageList rdfvalue from the server.
       cipher: The cipher object that should be used to verify the message.
       api_version: The api version we should use.

    Returns:
       a rdfvalue.GRRMessage.AuthorizationState.
    """
    result = rdfvalue.GRRMessage.Enum("UNAUTHENTICATED")
    try:
      if api_version >= 3:
        # New version:
        if cipher.HMAC(response_comms.encrypted) != response_comms.hmac:
          raise communicator.DecryptionError("HMAC does not match.")

        if cipher.signature_verified:
          result = rdfvalue.GRRMessage.Enum("AUTHENTICATED")

      else:
        # Fake the metadata
        cipher.cipher_metadata = rdfvalue.CipherMetadata(
            source=signed_message_list.source)

        # Verify the incoming message.
        digest = cipher.hash_function(
            signed_message_list.message_list).digest()

        remote_public_key = self.pub_key_cache.GetRSAPublicKey(
            common_name=signed_message_list.source)

        try:
          stats.STATS.Increment("grr_rsa_operations")
          # Signature is not verified, we consider the message unauthenticated.
          if remote_public_key.verify(digest, signed_message_list.signature,
                                      cipher.hash_function_name) != 1:
            return rdfvalue.GRRMessage.Enum("UNAUTHENTICATED")

        except RSA.RSAError as e:
          raise communicator.DecryptionError(e)

        result = rdfvalue.GRRMessage.Enum("AUTHENTICATED")

      if result == rdfvalue.GRRMessage.Enum("AUTHENTICATED"):
        try:
          client = self.client_cache.Get(cipher.cipher_metadata.source)
        except KeyError:
          client = aff4.FACTORY.Create(cipher.cipher_metadata.source,
                                       "VFSGRRClient", mode="rw",
                                       token=self.token)
          self.client_cache.Put(cipher.cipher_metadata.source, client)

        ip = response_comms.orig_request.source_ip
        client.Set(client.Schema.CLIENT_IP(ip))

        # The very first packet we see from the client we do not have its clock
        remote_time = client.Get(client.Schema.CLOCK) or 0
        client_time = signed_message_list.timestamp
        if client_time > long(remote_time):
          stats.STATS.Increment("grr_authenticated_messages")

          # Update the client and server timestamps.
          client.Set(client.Schema.CLOCK, rdfvalue.RDFDatetime(client_time))
          client.Set(client.Schema.PING, rdfvalue.RDFDatetime())

        else:
          # This is likely an old message
          return rdfvalue.GRRMessage.Enum("DESYNCHRONIZED")

        # If we are prepared to live with a slight risk of replay we can
        # remove this.
        client.Flush()

    except communicator.UnknownClientCert:
      pass

    if result != rdfvalue.GRRMessage.Enum("AUTHENTICATED"):
      stats.STATS.Increment("grr_unauthenticated_messages")

    return result


class FrontEndServer(object):
  """This is the front end server.

  This class interfaces clients into the GRR backend system. We process message
  bundles to and from the client, without caring how message bundles are
  transmitted to the client.

  - receives an encrypted message parcel from clients.
  - Decrypts messages from this.
  - schedules the messages to their relevant queues.
  - Collects the messages from the client queue
  - Bundles and encrypts the messages for the client.
  """

  def __init__(self, certificate, private_key, max_queue_size=50,
               message_expiry_time=120, max_retransmission_time=10, store=None,
               threadpool_prefix="grr_threadpool"):
    # Identify ourselves as the server.
    self.token = access_control.ACLToken("FrontEndServer", "Implied.")
    self.token.supervisor = True

    self.SetThrottleBundlesRatio(None)

    # This object manages our crypto.
    self._communicator = ServerCommunicator(
        certificate=certificate, private_key=private_key, token=self.token)

    self.data_store = store or data_store.DB
    self.receive_thread_pool = {}
    self.message_expiry_time = message_expiry_time
    self.max_retransmission_time = max_retransmission_time
    self.max_queue_size = max_queue_size
    self.thread_pool = threadpool.ThreadPool.Factory(
        threadpool_prefix, config_lib.CONFIG["Threadpool.size"])
    self.thread_pool.Start()

    # Well known flows are run on the front end.
    self.well_known_flows = {}
    for name, cls in GRRFlow.classes.items():
      if (aff4.issubclass(cls, WellKnownFlow) and
          cls.well_known_session_id and
          name in config_lib.CONFIG["Frontend.well_known_flows"]):
        context = flow_context.FlowContext(flow_name=name, token=self.token)
        self.well_known_flows[
            cls.well_known_session_id] = cls(context)

  def SetThrottleBundlesRatio(self, throttle_bundles_ratio):
    """Sets throttling ration.

    Throttling ratio is a value between 0 and 1 which determines
    which percentage of requests from clients will get proper responses.
    I.e. 0.3 means that only 30% of clients will get new tasks scheduled for
    them when HandleMessageBundles() method is called.

    Args:
      throttle_bundles_ratio: throttling ratio.
    """
    self.throttle_bundles_ratio = throttle_bundles_ratio
    if throttle_bundles_ratio is None:
      self.handled_bundles = []
      self.last_not_throttled_bundle_time = 0

    stats.STATS.Set("grr_frontendserver_throttle_setting",
                    throttle_bundles_ratio)

  def UpdateAndCheckIfShouldThrottle(self, bundle_time):
    """Update throttling data and check if request should be throttled.

    When throttling is enabled (self.throttle_bundles_ratio is not None)
    request times are stored. In order to detect whether particular
    request should be throttled, we do the following:
    1. Calculate the average interval between requests over last minute.
    2. Check that [time since last non-throttled request] is less than
       [average interval] / [throttle ratio].

    Args:
      bundle_time: time of the request.

    Returns:
      True if the request should be throttled, False otherwise.
    """
    if self.throttle_bundles_ratio is None:
      return False

    self.handled_bundles.append(bundle_time)
    oldest_limit = bundle_time - config_lib.CONFIG[
        "Frontend.throttle_average_interval"]

    try:
      oldest_index = next(i for i, v in enumerate(self.handled_bundles)
                          if v > oldest_limit)
      self.handled_bundles = self.handled_bundles[oldest_index:]
    except StopIteration:
      self.handled_bundles = []

    blen = len(self.handled_bundles)
    if blen > 1:
      interval = (self.handled_bundles[-1] -
                  self.handled_bundles[0]) / float(blen - 1)
    else:
      # TODO(user): this can occasionally return False even when
      # throttle_bundles_ratio is 0, treat it in a generic way.
      return self.throttle_bundles_ratio == 0

    should_throttle = (bundle_time - self.last_not_throttled_bundle_time <
                       interval / max(0.1e-6,
                                      float(self.throttle_bundles_ratio)))

    if not should_throttle:
      self.last_not_throttled_bundle_time = bundle_time

    return should_throttle

  @stats.Counted("grr_frontendserver_handle_num")
  @stats.Timed("grr_frontendserver_handle_time")
  @stats.TimespanAvg("grr_frontendserver_handle_time_running_avg")
  def HandleMessageBundles(self, request_comms, response_comms):
    """Processes a queue of messages as passed from the client.

    We basically dispatch all the GrrMessages in the queue to the task scheduler
    for backend processing. We then retrieve from the TS the messages destined
    for this client.

    Args:
       request_comms: A ClientCommunication rdfvalue with messages sent by the
       client. source should be set to the client CN.

       response_comms: A ClientCommunication rdfvalue of jobs destined to this
       client.

    Returns:
       tuple of (source, message_count) where message_count is the number of
       messages received from the client with common name source.
    """
    messages, source, timestamp = self._communicator.DecodeMessages(
        request_comms)

    self.thread_pool.AddTask(
        target=self.ReceiveMessages, args=(messages,),
        name="ReceiveMessages")

    # We send the client a maximum of self.max_queue_size messages
    required_count = max(0, self.max_queue_size - request_comms.queue_size)

    message_list = rdfvalue.MessageList()
    if self.UpdateAndCheckIfShouldThrottle(time.time()):
      tasks = []
      stats.STATS.Increment("grr_frontendserver_handle_throttled_num")
    else:
      tasks = self.DrainTaskSchedulerQueueForClient(source, required_count,
                                                    message_list)

    # Encode the message_list in the response_comms using the same API version
    # the client used.
    try:
      self._communicator.EncodeMessages(
          message_list, response_comms, destination=str(source),
          timestamp=timestamp, api_version=request_comms.api_version)
    except communicator.UnknownClientCert:
      # We can not encode messages to the client yet because we do not have the
      # client certificate - return them to the queue so we can try again later.
      scheduler.SCHEDULER.Schedule(tasks, token=self.token)
      raise

    return source, len(messages)

  def DrainTaskSchedulerQueueForClient(self, client_name, max_count,
                                       response_message):
    """Drains the client's Task Scheduler queue.

    1) Get all messages in the client queue.
    2) Sort these into a set of session_ids.
    3) Use data_store.DB.ResolveRegex() to query all requests.
    4) Delete all responses for retransmitted messages (if needed).

    Args:
       client_name: CN of client (also TS queue name)

       max_count: The maximum number of messages we will issue for the
                  client.

       response_message: a MessageList object we fill for with GrrMessages
    Returns:
       The tasks respresenting the messages returned. If we can not send them,
       we can reschedule them for later.
    """
    if max_count <= 0:
      return []

    # Drain the queue for this client:
    new_tasks = scheduler.SCHEDULER.QueryAndOwn(
        queue=client_name,
        limit=max_count, token=self.token,
        lease_seconds=self.message_expiry_time)

    for task in new_tasks:
      response_message.job.Append(task.payload)
    stats.STATS.Add("grr_messages_sent", len(new_tasks))
    return new_tasks

  def ReceiveMessages(self, messages):
    """Receives and processes the messages from the source.

    For each message we update the request object, and place the
    response in that request's queue. If the request is complete, we
    send a message to the worker.

    Args:
      messages: A list of GrrMessage RDFValues.
    """

    for msg in messages:
      # Support old clients without fully qualified session ids.
      if not msg.session_id.startswith("aff4"):
        msg.session_id = "aff4:/flows/" + msg.session_id

      if msg.type == rdfvalue.GRRMessage.Enum("STATUS"):
        status = rdfvalue.GrrStatus(msg.args)
        if status.status == rdfvalue.GrrStatus.Enum("CLIENT_KILLED"):
          # A client crashed while performing an action, fire an event.
          PublishEvent("ClientCrash", rdfvalue.GRRMessage(msg),
                       token=self.token)

    sessions_handled = []
    priorities = {}
    for session_id, messages in utils.GroupBy(
        messages, operator.attrgetter("session_id")):

      # Remove and handle messages to WellKnownFlows
      messages = self.HandleWellKnownFlows(messages)
      if not messages: continue

      # Keep track of all the flows we handled in this request.
      sessions_handled.append(session_id)

      with flow_context.FlowManager(token=self.token,
                                    store=self.data_store) as flow_manager:
        for msg in messages:
          priorities[session_id] = max(priorities.setdefault(session_id, 0),
                                       msg.priority)
          flow_manager.QueueResponse(session_id, msg)

    # Write the session ids that we saw to the worker queue. (One round trip per
    # worker queue).
    for queue, session_ids in utils.GroupBy(
        sessions_handled, scheduler.SCHEDULER.QueueNameFromURN):

      scheduler.SCHEDULER.MultiNotifyQueue(
          queue, session_ids,
          [priorities[session_id] for session_id in session_ids],
          token=self.token)

  def HandleWellKnownFlows(self, messages):
    """Hands off messages to well known flows."""
    result = []
    for msg in messages:
      # Regular message - queue it.
      if msg.response_id != 0:
        result.append(msg)

      # Well known flows:
      else:
        if msg.session_id in self.well_known_flows:
          # This message should be processed directly on the front end.
          flow = self.well_known_flows[msg.session_id]
          flow.ProcessMessage(msg)

          # Remove the notification from the well known flows.
          scheduler.SCHEDULER.DeleteNotification(
              scheduler.SCHEDULER.QueueNameFromURN(msg.session_id),
              msg.session_id, token=self.token)

          stats.STATS.Increment("grr_well_known_flow_requests")
        else:
          # Message should be queued to be processed in the backend.

          # Well known flows have a response_id==0, but if we queue up the state
          # as that it will overwrite some other message that is queued. So we
          # change it to a random number here.
          msg.response_id = struct.unpack("<I", os.urandom(4))[0]

          # By setting the request ID to increment with time we maintain rough
          # time order in the queue.
          msg.request_id = int(time.time())

          # Queue the message in the data store.
          result.append(msg)

    return result

  def GetQueueName(self, session_id):
    # Session id has to be of the form queue_name:number
    try:
      queue_name, _ = session_id.split(":", 1)
    except ValueError:
      logging.error("Message has invalid session id %s",
                    session_id)
      raise RuntimeError("Message has invalid session_id")

    return queue_name


class LockError(FlowError):
  """Raised when we fail to grab a lock on the flow object."""


def ProcessCompletedRequests(flow_obj, thread_pool, reqs):
  flow_obj.ProcessCompletedRequests(thread_pool, reqs)


class GRRWorker(object):
  """A GRR worker."""

  # time to wait before polling when no jobs are currently in the
  # task scheduler (sec)
  POLLING_INTERVAL = 2
  SHORT_POLLING_INTERVAL = 0.3
  SHORT_POLL_TIME = 30

  # A class global threadpool to be used for all workers.
  thread_pool = None

  # This is a timed cache of locked flows. If this worker encounters a lock
  # failure on a flow, it will not attempt to grab this flow until the timeout.
  queued_flows = None

  def __init__(self, queue_name=None, threadpool_prefix="grr_threadpool",
               threadpool_size=0, token=None):
    """Constructor.

    Args:
      queue_name: The name of the queue we use to fetch new messages
      from.
      threadpool_prefix: A name for the thread pool used by this worker.
      threadpool_size: The number of workers to start in this thread pool.
      token: The token to use for the worker.

    Raises:
      RuntimeError: If the token is not provided.
    """
    self.queue_name = queue_name
    self.queued_flows = utils.TimeBasedCache(max_size=1000)

    if token is None:
      raise RuntimeError("A valid ACLToken is required.")

    # Make the thread pool a global so it can be reused for all workers.
    if GRRWorker.thread_pool is None:
      if threadpool_size == 0:
        threadpool_size = config_lib.CONFIG["Threadpool.size"]

      GRRWorker.thread_pool = threadpool.ThreadPool.Factory(threadpool_prefix,
                                                            threadpool_size)
      GRRWorker.thread_pool.Start()

    self.token = token
    self.last_active = 0

    # Well known flows are just instantiated.
    self.well_known_flows = {}
    for name, cls in GRRFlow.classes.items():
      if aff4.issubclass(cls, WellKnownFlow) and cls.well_known_session_id:
        context = flow_context.FlowContext(flow_name=name, token=self.token)
        well_known_flow = self.well_known_flows[
            cls.well_known_session_id] = cls(context=context)

        rdf_flow = well_known_flow.Dump()
        aff4_flow = aff4.FACTORY.Create(rdf_flow.session_id, "GRRFlow",
                                        mode="w", token=token)
        aff4_flow.Set(aff4_flow.Schema.RDF_FLOW,
                      rdfvalue.GRRMessage(queue=rdf_flow.session_id,
                                          task_id=1, payload=rdf_flow))
        aff4_flow.Close()

  def Run(self):
    """Event loop."""
    try:
      while 1:
        processed = self.RunOnce()

        if processed == 0:

          if time.time() - self.last_active > self.SHORT_POLL_TIME:
            interval = self.POLLING_INTERVAL
          else:
            interval = self.SHORT_POLLING_INTERVAL

          logging.debug("Waiting for new jobs %s Secs", interval)
          time.sleep(interval)
        else:
          self.last_active = time.time()

    except KeyboardInterrupt:
      logging.info("Caught interrupt, exiting.")
      self.thread_pool.Join()

  def RunOnce(self):
    """Processes one set of messages from Task Scheduler.

    The worker processes new jobs from the task master. For each job
    we retrieve the session from the Task Scheduler.

    Returns:
        Total number of messages processed by this call.
    """
    sessions_available = scheduler.SCHEDULER.GetSessionsFromQueue(
        self.queue_name, self.token)

    # Filter out session ids we already tried to lock but failed.
    sessions_available = [session for session in sessions_available
                          if session not in self.queued_flows]

    try:
      processed = self.ProcessMessages(sessions_available)
    # We need to keep going no matter what.
    except Exception as e:    # pylint: disable=W0703
      logging.error("Error processing message %s. %s.", e,
                    traceback.format_exc())

      if flags.FLAGS.debug:
        pdb.post_mortem()

    return processed

  def ProcessMessages(self, active_sessions):
    """Processes all the flows in the messages.

    Precondition: All tasks come from the same queue (self.queue_name).

    Note that the server actually completes the requests in the
    flow when receiving the messages from the client. We do not really
    look at the messages here at all any more - we just work from the
    completed messages in the flow RDFValue.

    Args:
        active_sessions: The list of sessions which had messages received.
    Returns:
        The number of processed flows.
    """
    processed = 0
    for session_id in active_sessions:
      if session_id not in self.queued_flows:
        processed += 1
        self.queued_flows.Put(session_id, 1)
        self.thread_pool.AddTask(target=self._ProcessMessages,
                                 args=(session_id,),
                                 name=self.__class__.__name__)
    return processed

  def _ProcessMessages(self, session_id):
    """Does the real work with a single flow."""

    rdf_flow = None
    # Take a lease on the flow:
    try:
      rdf_flow = FACTORY.FetchFlow(session_id, lock=True, sync=False,
                                   token=self.token)

      # If we get here, we now own the flow, so we can remove the notification
      # for it from the worker queue.
      scheduler.SCHEDULER.DeleteNotification(
          scheduler.SCHEDULER.QueueNameFromURN(session_id),
          session_id, token=self.token)

    except LockError:
      # Another worker is dealing with this flow right now, we just skip it.
      return

    try:
      flow_obj = None

      # We still need to take a lock on the well known flow in the datastore,
      # but we can run a local instance.
      if session_id in self.well_known_flows:
        self.well_known_flows[session_id].ProcessCompletedRequests(
            self.thread_pool)

      else:
        # Flow did not exist.
        if rdf_flow is None:
          return

        # Unpickle the flow and have it process its messages.
        flow_obj = FACTORY.LoadFlow(rdf_flow)
        flow_obj.ProcessCompletedRequests(self.thread_pool)

        # Re-serialize the flow
        flow_obj.Dump()
        flow_obj.FlushMessages()

      # Everything went well -> session can be run again.
      self.queued_flows.ExpireObject(session_id)

    except FlowError as e:
      # Something went wrong - log it
      if rdf_flow:
        rdf_flow.state = rdfvalue.Flow.Enum("ERROR")
        if not rdf_flow.backtrace:
          rdf_flow.backtrace = traceback.format_exc()

      if flow_obj:
        logging.error("Flow %s: %s", flow_obj, e)
      else:
        logging.error("Flow %s: %s", session_id, e)

    finally:
      if rdf_flow:
        # Unlock this flow
        FACTORY.ReturnFlow(rdf_flow, token=self.token)


class GRREnroler(GRRWorker):
  """A GRR enroler.

  Subclassed here so that log messages arrive from the right class.
  """


# These are globally available handles to factories
# pylint: disable=W0603
# pylint: disable=C6409


class FlowInit(registry.InitHook):
  """Ensures that the Well known flows exist."""

  pre = ["AFF4InitHook", "StatsInit"]

  def Run(self):
    # Make global handlers
    global FACTORY

    FACTORY = FlowFactory()

  def RunOnce(self):
    """Exports our vars."""
    # Counters defined here
    stats.STATS.RegisterVar("grr_flow_completed_count")
    stats.STATS.RegisterVar("grr_flow_errors")
    stats.STATS.RegisterVar("grr_flow_invalid_flow_count")
    stats.STATS.RegisterVar("grr_flows_created")
    stats.STATS.RegisterMap("grr_frontendserver_handle_time", "times",
                            precision=0)
    stats.STATS.RegisterTimespanAvg(
        "grr_frontendserver_handle_time_running_avg", 60)
    stats.STATS.RegisterVar("grr_messages_sent")
    stats.STATS.RegisterVar("grr_request_retransmissions_count")
    stats.STATS.RegisterVar("grr_response_out_of_order")
    stats.STATS.RegisterVar("grr_unique_clients")
    stats.STATS.RegisterVar("grr_unknown_clients")
    stats.STATS.RegisterVar("grr_well_known_flow_requests")
    stats.STATS.RegisterVar("grr_worker_flows_pickled")
    stats.STATS.RegisterVar("grr_worker_requests_complete")
    stats.STATS.RegisterVar("grr_worker_requests_issued")
    stats.STATS.RegisterVar("grr_worker_states_run")
    stats.STATS.RegisterVar("grr_worker_well_known_flow_requests")
    stats.STATS.RegisterVar("grr_frontendserver_handle_num")
    stats.STATS.RegisterVar("grr_frontendserver_handle_throttled_num")
    stats.STATS.RegisterVar("grr_frontendserver_throttle_setting")

# A global factory that can be used to create new flows
FACTORY = None

# pylint: enable=W0603
# pylint: enable=C6409
