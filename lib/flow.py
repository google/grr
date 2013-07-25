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
import sys
import time


from M2Crypto import RSA
from M2Crypto import X509

import logging

from grr.client import actions
from grr.lib import access_control
from grr.lib import aff4
from grr.lib import communicator
from grr.lib import config_lib
from grr.lib import data_store
from grr.lib import flow_runner
from grr.lib import rdfvalue
from grr.lib import registry
from grr.lib import scheduler
# pylint: disable=unused-import
from grr.lib import server_stubs
# pylint: enable=unused-import
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

config_lib.DEFINE_integer("Worker.flow_lease_time", 600,
                          "Duration of flow lease time in seconds.")

config_lib.DEFINE_integer("Frontend.throttle_average_interval", 60,
                          "Time interval over which average request rate is "
                          "calculated when throttling is enabled.")

config_lib.DEFINE_list("Frontend.well_known_flows",
                       ["aff4:/flows/W:TransferStore", "aff4:/flows/W:Stats"],
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
      self.request_data = rdfvalue.Dict(request.data)
    self._responses = []
    self._dropped_responses = []

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
        if msg.auth_state == msg.AuthorizationState.DESYNCHRONIZED or (
            self._auth_required and
            msg.auth_state != msg.AuthorizationState.AUTHENTICATED):
          logging.info("%s: Messages must be authenticated (Auth state %s)",
                       msg.session_id, msg.auth_state)
          self._dropped_responses.append(msg)
          # Skip this message - it is invalid
          continue

        # Check for iterators
        if msg.type == msg.Type.ITERATOR:
          self.iterator.ParseFromString(msg.args)
          continue

        # Look for a status message
        if msg.type == msg.Type.STATUS:
          # Our status is set to the first status message that we see in
          # the responses. We ignore all other messages after that.
          self.status = rdfvalue.GrrStatus(msg.args)

          # Check this to see if the call succeeded
          self.success = self.status.status == self.status.ReturnedStatus.OK

          # Ignore all other messages
          break

        # Use this message
        self._responses.append(msg)

      if self.status is None:
        # This is a special case of de-synchronized messages.
        if self._dropped_responses:
          raise FlowError("De-synchronized messages detected:\n" + "\n".join(
              [utils.SmartUnicode(x) for x in self._dropped_responses]))

        raise FlowError("No valid Status message.")

    # This is the raw message accessible while going through the iterator
    self.message = None

  def __iter__(self):
    """An iterator which returns all the responses in order."""
    old_response_id = None
    for message in self._responses:
      self.message = rdfvalue.GrrMessage(message)

      # Handle retransmissions
      if self.message.response_id == old_response_id:
        continue

      else:
        old_response_id = self.message.response_id

      if self.message.type == self.message.Type.MESSAGE:
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
    def Decorated(self, runner, direct_response, request=None,
                  responses=None):
      """A decorator that defines allowed follow up states for a method.

      Args:
        runner: A flowrunner object used to run this flow.
        direct_response: A final responses object that does not need wrapping
                         again. If given, neither request nor responses is used.
        request: The request sent out originally.
        responses: The responses for this state.
      Returns:
        This calls the state and returns the obtained result.
      """
      self.runner = runner
      self.runner.SetAllowedFollowUpStates(next_states)

      if direct_response is not None:
        return f(self, *direct_response)

      # Record the permitted next states so CallClient() can check.
      self.state.context.next_states = next_states
      # Prepare a responses object for the state method to use:
      responses = Responses(request=request,
                            responses=responses,
                            auth_required=auth_required)

      if responses.status:
        self.runner.SaveResourceUsage(request, responses)

      stats.STATS.IncrementCounter("grr_worker_states_run")
      # Run the state method (Allow for flexibility in prototypes)
      args = [self, responses]
      res = f(*args[:f.func_code.co_argcount])

      return res

    # Make sure the state function itself knows where its allowed to
    # go (This is used to introspect the state graph).
    Decorated.next_states = next_states

    return Decorated

  return Decorator


class GRRFlow(aff4.AFF4Volume):
  """A container aff4 object to maintain a flow.

  Flow objects are executed and scheduled by the workers, and extend
  grr.flow.GRRFlow. This object contains the flows object within an AFF4
  container.

  Note: Usually this object can not be created by the regular
  aff4.FACTORY.Create() method since it requires elevated permissions. This
  object can instead be created using the flow.GRRFlow.StartFlow() method.

  After creation, access to the flow object can still be obtained through
  the usual aff4.FACTORY.Open() method.
  """

  class SchemaCls(aff4.AFF4Volume.SchemaCls):
    """Attributes specific to GRRFlow."""

    FLOW_STATE = aff4.Attribute("aff4:flow_state", rdfvalue.FlowState,
                                "The current state of this flow.",
                                "FlowState", versioned=False,
                                creates_new_object_version=False)

    LOG = aff4.Attribute("aff4:log", rdfvalue.RDFString,
                         "Log messages related to the progress of this flow.",
                         creates_new_object_version=False)

    NOTIFICATION = aff4.Attribute("aff4:notification", rdfvalue.Notification,
                                  "Notifications for the flow.")

    CLIENT_CRASH = aff4.Attribute("aff4:client_crash", rdfvalue.ClientCrash,
                                  "Client crash details in case of a crash.",
                                  default=None)

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
      type_info.SemanticEnum(
          description="The priority used for this flow.",
          name="priority",
          enum_container=rdfvalue.GrrMessage.Priority,
          default=rdfvalue.GrrMessage.Priority.MEDIUM_PRIORITY),

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

      type_info.RDFURNType(
          description=("A well known flow session_id of an event listener. An "
                       "event will be published to this listener once the "
                       "flow finishes."),
          name="notification_event",
          friendly_name="Notification Event",
          hidden=True,
          default=None),
      )

  def Initialize(self):
    """The initialization method."""
    if "r" in self.mode:
      self.state, success = self.ReadState()
      if success:
        self.Load()
    else:
      self.state = self.Schema.FLOW_STATE()

  def InitFromArguments(self, **kwargs):
    self._SetTypedArgs(self.state.context, GRRFlow.flow_typeinfo, kwargs)
    if GRRFlow.flow_typeinfo != self.flow_typeinfo:
      self._SetTypedArgs(self.state, self.flow_typeinfo, kwargs)

    if kwargs:
      raise type_info.UnknownArg("%s: Args %s not known" % (
          self.__class__.__name__, kwargs.keys()))

    stats.STATS.IncrementCounter("grr_flows_created")

  def InitializeContext(self, client_id=None, queue=None,
                        event_id=None, cpu_limit=None, network_bytes_limit=None,
                        request_state=None):
    """Initializes the context of this flow.

    Args:
      client_id: The name of the client we are working with.
      queue: The name of the queue that the messages will run
                  with (default is W for general purpose workers).
      event_id: A logging event id for issuing further logs.
      cpu_limit: A limit for the cpu seconds used on the client for this flow.
      network_bytes_limit: Maximum number of bytes to send for this flow.
      request_state: A request state in case this flow has a parent.
    """
    if event_id is None:
      event_id = "%s:console" % self.token.username

    self.state.context.update({
        "client_id": client_id,
        "client_resources": rdfvalue.ClientResources(),
        "cpu_limit": cpu_limit,
        "network_bytes_limit": network_bytes_limit,
        "create_time": rdfvalue.RDFDatetime().Now(),
        "creator": self.token.username,
        "current_state": "Start",
        "event_id": event_id,
        "flow_name": self.__class__.__name__,
        "network_bytes_sent": 0,
        "next_outbound_id": 1,
        "next_processed_request": 1,
        "next_states": [],
        "outstanding_requests": 0,
        "queue": queue,
        "request_state": request_state,
        "session_id": rdfvalue.SessionID(self.urn),
        "state": rdfvalue.Flow.State.RUNNING,
        # Have we sent a notification to the user.
        "user_notified": False,
        "user": self.token.username,
        })

  def GenerateParentFlowURN(self, client_id=None):
    _ = client_id
    return self.session_id

  @classmethod
  def GetNewSessionID(cls, queue, client_id=None, parent_flow_urn=None):
    """Returns a random session ID for this flow.

    Args:
      queue: The queue for this flow.
      client_id: The id of the client this flow should run on.
      parent_flow_urn: This flow's parent's urn if it has one.

    Returns:
      A formatted session id URN.
    """
    if parent_flow_urn:
      base = parent_flow_urn
    else:
      base = client_id or aff4.ROOT_URN
      base = base.Add("flows")

    return rdfvalue.SessionID(base=base, queue=queue)

  def _SetTypedArgs(self, target, type_descriptor, kwargs):
    """Sets our attributes from the type_descriptor."""
    # Parse and validate the args to this flow. This will raise if the args are
    # invalid.
    for name, value in type_descriptor.ParseArgs(kwargs):
      # Make sure we dont trash an internal name.
      if name in target:
        raise AttributeError("Flow arg name already set: %s" % name)

      target.Register(name, value)

  def ReadState(self):
    """Reads the state from the database.

    This returns the stored or a new state and indicates if reading was
    successful by returning an additional flag which can be used to determine
    if the state has to be initialized.

    Returns:
      The state read and a flag indicating success.
    """
    state = self.Get(self.Schema.FLOW_STATE)
    if not state:
      # TODO(user): Maybe we should warn here?
      return self.Schema.FLOW_STATE(), False
    return state, True

  def WriteState(self):
    if not self.state.Empty():
      self.Set(self.Schema.FLOW_STATE(self.state))

  def GetContext(self):
    return self.state.context

  def Flush(self, sync=True):
    """Flushes the flow and all its requests to the data_store."""
    # Check for Lock expiration first.
    self.CheckLease()
    self.Save()
    self.WriteState()
    super(GRRFlow, self).Flush(sync=sync)

  def Close(self, sync=True):
    """Flushes the flow and all its requests to the data_store."""
    # Check for Lock expiration first.
    self.CheckLease()
    self.Save()
    self.WriteState()
    super(GRRFlow, self).Close(sync=sync)

  def Ping(self):
    self.UpdateLease(config_lib.CONFIG["Worker.flow_lease_time"])

  def CreateRunner(self, *args, **kw):
    kw["token"] = self.token
    return flow_runner.FlowRunner(self, *args, **kw)

  @StateHandler()
  def End(self):
    """Final state.

    This method is called prior to destruction of the flow to give
    the flow a chance to clean up.
    """
    if not self.state.context.user_notified:
      # Only send a notification if one hasn't already been sent in this flow.
      self.Notify("FlowStatus", self.client_id,
                  "Flow %s completed" % self.__class__.__name__)

  @StateHandler()
  def Start(self, unused_message=None):
    """The first state of the flow."""
    pass

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
    """Returns an RDFBytes object containing the pickled internal state.

    Returns:
      An RDFBytes object containing the state.
    """
    # Allow the flow author to hook this
    self.Save()
    result = rdfvalue.RDFBytes(pickle.dumps(self.state))
    self.Load()
    return result

  def Log(self, format_str, *args):
    """Logs the message using the flow's standard logging.

    Args:
      format_str: Format string
      *args: arguments to the format string
    """
    format_str = utils.SmartUnicode(format_str)
    logging.info(format_str, *args)

    try:
      # The status message is always in unicode
      status = format_str % args
    except TypeError:
      logging.error("Tried to log a format string with the wrong number "
                    "of arguments: %s", format_str)
      status = format_str

    self.SetStatus(utils.SmartUnicode(status))

    # Add the message to the flow's log attribute
    data_store.DB.Set(self.session_id,
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
    if self.state.context.notify_to_user:
      # Prefix the message with the hostname of the client we are running
      # against.
      if self.client_id:
        client_fd = aff4.FACTORY.Open(self.client_id, mode="rw",
                                      token=self.token)
        hostname = client_fd.Get(client_fd.Schema.HOSTNAME) or ""
        client_msg = "%s: %s" % (hostname, msg)
      else:
        client_msg = msg

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

      data_store.DB.Set(self.session_id,
                        aff4.AFF4Object.GRRFlow.SchemaCls.NOTIFICATION,
                        notification, replace=False, sync=False,
                        token=self.token)
      self.state.user_notified = True

    # TODO(user): This should be using PublishEvent()
    notification_event = self.state.context.get("notification_event")
    if notification_event:
      if self.state.context.state == rdfvalue.Flow.State.ERROR:
        status = rdfvalue.FlowNotification.Status.ERROR

      else:
        status = rdfvalue.FlowNotification.Status.OK

      event = rdfvalue.FlowNotification(
          session_id=utils.SmartUnicode(self.session_id),
          flow_name=self.state.context.flow_name,
          client_id=self.client_id,
          status=status)
      msg = rdfvalue.GrrMessage(
          payload=event,
          session_id=notification_event,
          auth_state=rdfvalue.GrrMessage.AuthorizationState.AUTHENTICATED,
          source=self.__class__.__name__)
      # Randomize the response id or events will get overwritten.
      msg.response_id = msg.task_id

      with flow_runner.WellKnownFlowManager(
          token=self.token) as flow_manager:
        flow_manager.QueueResponse(notification_event, msg)

      # Notify the worker of the pending sessions.
      scheduler.SCHEDULER.NotifyQueue(notification_event, token=self.token)

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
    if not isinstance(message, rdfvalue.GrrMessage):
      result = rdfvalue.GrrMessage(payload=message)

    result.session_id = session_id or self.session_id
    result.auth_state = rdfvalue.GrrMessage.AuthorizationState.AUTHENTICATED
    result.source = self.__class__.__name__

    PublishEvent(event_name, result, token=self.token)

  def CallClient(self, action_name, request=None, next_state=None,
                 request_data=None, **kwargs):
    return self.runner.CallClient(action_name, request, next_state,
                                  request_data, **kwargs)

  def CallState(self, messages=None, next_state="", delay=0):
    return self.runner.CallState(messages=messages, next_state=next_state,
                                 delay=delay)

  def CallFlow(self, flow_name, next_state=None, request_data=None, **kwargs):
    return self.runner.CallFlow(GRRFlow, flow_name, next_state=next_state,
                                request_data=request_data, **kwargs)

  def ProcessCompletedRequests(self, runner, thread_pool):
    return runner.ProcessCompletedRequests(thread_pool)

  def OutstandingRequests(self):
    return self.state.context.outstanding_requests

  def SendReply(self, response):
    return self.runner.SendReply(response)

  def Error(self, backtrace, client_id=None):
    return self.runner.Error(backtrace, client_id=client_id)

  def SetState(self, state):
    self.state.context.state = state

  def SetStatus(self, status):
    self.state.context.status = status

  def Terminate(self):
    return self.runner.Terminate()

  def IsRunning(self):
    return self.state.context.state == rdfvalue.Flow.State.RUNNING

  @property
  def session_id(self):
    return self.state.context.get("session_id", None)

  @session_id.setter
  def session_id(self, session_id):
    self.state.context.session_id = session_id

  @property
  def client_id(self):
    return self.state.context.get("client_id", None)

  @client_id.setter
  def client_id(self, client_id):
    self.state.context.client_id = client_id

  @property
  def backtrace(self):
    return self.state.context.get("backtrace", None)

  @backtrace.setter
  def backtrace(self, bt):
    self.state.context.backtrace = bt

  def Name(self):
    return self.state.context.flow_name

  @classmethod
  def StartFlow(cls, client_id, flow_name,  # pylint: disable=g-bad-name
                queue=rdfvalue.RDFURN("W"),
                event_id=None, token=None, cpu_limit=None,
                network_bytes_limit=None,
                parent_flow=None, _request_state=None,
                _store=None, **kw):
    """Creates and executes a new flow.

    Args:
      client_id: The URL of an existing client or None for well known flows.
      flow_name: The name of the flow to start (from the registry).
      queue: The queue to use for the flow.
      event_id: A logging event id for issuing further logs.
      token: The access token to be used for this request.
      cpu_limit: A limit on the client cpu seconds used by this flow.
      network_bytes_limit: Maximum number of bytes to send for this flow.
      parent_flow: A parent flow or None if this is a top level flow.
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
      stats.STATS.IncrementCounter("grr_flow_invalid_flow_count")
      raise RuntimeError("Unable to locate flow %s" % flow_name)

    if client_id:
      # Ensure the client_id is valid.
      client_id = rdfvalue.ClientURN(client_id)

    # Make sure we are allowed to run this flow.
    data_store.DB.security_manager.CheckFlowAccess(token, flow_name, client_id)

    # From now on we run with supervisor access
    if token is None:
      token = data_store.default_token.Copy()
    else:
      token = token.Copy()

    token.supervisor = True

    # Extend the expiry time of this token indefinitely.
    token.expiry = sys.maxint

    # Strip out any private args so they do not get converted.
    args = dict([(k, v) for k, v in kw.items() if not k.startswith("_")])

    if parent_flow:
      parent_flow_urn = parent_flow.GenerateParentFlowURN(client_id)
    else:
      parent_flow_urn = None

    session_id = flow_cls.GetNewSessionID(queue, client_id,
                                          parent_flow_urn)

    # Only the supervisor can create the containing AFF4 object.
    flow_obj = aff4.FACTORY.Create(session_id, flow_name, token=token)

    flow_obj.InitializeContext(client_id=client_id, queue=queue,
                               event_id=event_id, cpu_limit=cpu_limit,
                               network_bytes_limit=network_bytes_limit,
                               request_state=_request_state)

    flow_obj.InitFromArguments(**args)

    if client_id:
      # Ensure the client is a valid client.
      client_id = rdfvalue.ClientURN(client_id)

      # Add this flow to the client
      client = aff4.FACTORY.Create(client_id, "VFSGRRClient", mode="w",
                                   token=token, force_new_version=False)
      client.AddAttribute(client.Schema.FLOW(flow_obj.session_id))
      client.Flush()

    logging.info("Scheduling %s(%s) on %s: %s", flow_obj.session_id,
                 flow_name, client_id, utils.SmartUnicode(kw))

    # A flow manager maintains an atomic transaction of all messages to be sent
    # as part of a flow state execution. If this flow calls child flows, we
    # still use the same flow manager while running the child flows. However,
    # each flow has its own flow runner. Therefore when we are a child flow we
    # must inherit our parent's flow manager.
    if parent_flow:
      flow_manager = parent_flow.runner.flow_manager
    else:
      flow_manager = None

    runner = flow_runner.FlowRunner(flow_obj, flow_manager=flow_manager,
                                    _store=_store or data_store.DB)
    # Just run the first state. NOTE: The Start method always runs on the thread
    # that starts the flow so it must be very fast, basically just CallClient()
    # CallFlow() or CallState(). If a long delay is needed, this should call
    # CallState() and put the heavy lifting in another state. Similarly it is
    # preferred that any sanity checking of parameters etc be done by the
    # Start() method so the flow invocation can be aborted immediately.
    flow_obj.Start(runner, None)

    # The flow does not need to actually remain running.
    if not flow_obj.OutstandingRequests():
      flow_obj.Terminate()

    flow_obj.Close()

    if parent_flow is None:
      runner.FlushMessages()

    return session_id

  @classmethod
  def TerminateFlow(cls, flow_id, reason=None,  # pylint: disable=g-bad-name
                    token=None, force=False, _store=None):
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
    if not force:
      lock_manager = aff4.FACTORY.OpenWithLock(flow_id, blocking=True,
                                               token=token)
    else:
      lock_manager = aff4.LockContextManager(
          aff4.FACTORY.Open(flow_id, mode="rw", token=token), sync=True)

    with lock_manager as flow_obj:
      if not flow_obj.IsRunning():
        return
      if not flow_obj:
        raise FlowError("Could not terminate flow %s" % flow_id)

      if token is None:
        token = access_control.ACLToken()

      if reason is None:
        reason = "Manual termination by console."

      runner = flow_obj.CreateRunner(token=token, _store=_store)
      runner.Error(reason)
      flow_obj.Log("Terminated by user {0}. Reason: {1}".format(token.username,
                                                                reason))
      # Make sure we are only allowed to terminate this flow, if we are allowed
      # to run it.
      data_store.DB.security_manager.CheckFlowAccess(
          token, flow_obj.__class__.__name__, client_id=flow_obj.client_id)

      # From now on we run with supervisor access
      super_token = token.Copy()
      super_token.supervisor = True

      # Also terminate its children
      for child in flow_obj.ListChildren():
        cls.TerminateFlow(child, reason="Parent flow terminated.",
                          token=super_token, force=force)


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

  # Well known flows are not browsable.
  category = None

  @classmethod
  def GetAllWellKnownFlows(cls, token=None):
    well_known_flows = {}
    for cls in GRRFlow.classes.values():
      if aff4.issubclass(cls, WellKnownFlow) and cls.well_known_session_id:
        well_known_flow = cls(cls.well_known_session_id,
                              mode="rw", token=token)
        well_known_flows[cls.well_known_session_id] = well_known_flow
        well_known_flow.Close()
    return well_known_flows

  def _SafeProcessMessage(self, *args, **kwargs):
    try:
      self.ProcessMessage(*args, **kwargs)
    except Exception as e:  # pylint: disable=broad-except
      logging.exception("Error in WellKnownFlow.ProcessMessage: %s", e)

  def InitFromArguments(self, **kwargs):
    super(WellKnownFlow, self).InitFromArguments(**kwargs)

    # Tag this flow as well known
    self.state.context.state = rdfvalue.Flow.State.WELL_KNOWN
    # Well known flows are not user initiated so the default is no notification.
    self.state.context.notify_to_user = False

  def CallState(self, messages=None, next_state=None, delay=0):
    """Well known flows have no states to call."""
    pass

  @classmethod
  def GetNewSessionID(cls, queue, client_id=None,
                      parent_flow_urn=None):
    # Always return a well known session id for this flow:
    return cls.well_known_session_id

  @property
  def session_id(self):
    return self.well_known_session_id

  @session_id.setter
  def session_id(self, session_id):
    self.well_known_session_id = session_id

  def OutstandingRequests(self):
    # Lie about it to prevent us from being destroyed
    return 1

  def ProcessCompletedRequests(self, thread_pool):
    """For WellKnownFlows we receive these messages directly."""
    try:
      priority = rdfvalue.GrrMessage.Priority.MEDIUM_PRIORITY
      with flow_runner.WellKnownFlowManager(
          token=self.token) as flow_manager:
        for request, responses in flow_manager.FetchRequestsAndResponses(
            self.session_id):
          for msg in responses:
            priority = msg.priority
            thread_pool.AddTask(target=self._SafeProcessMessage,
                                args=(msg,), name=self.__class__.__name__)

          flow_manager.DeleteFlowRequestStates(self.session_id, request,
                                               responses)
    except flow_runner.MoreDataException:
      # There is more data for this flow so we have to tell the worker to
      # fetch more messages later.
      scheduler.SCHEDULER.NotifyQueue(self.state.context.session_id,
                                      priority=priority, token=self.token)

  def ProcessMessage(self, msg):
    """This is where messages get processed.

    Override in derived classes:

    Args:
       msg: The GrrMessage sent by the client. Note that this
            message is not authenticated.
    """


def EventHandler(source_restriction=None, auth_required=True,
                 allow_client_access=False):
  """A convenience decorator for Event Handlers.

  Args:
    source_restriction: A function which will be passed the message's source. If
      the function returns True we permit processing, otherwise the message is
      rejected.

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
      if (auth_required and
          msg.auth_state != msg.AuthorizationState.AUTHENTICATED):
        raise RuntimeError("Message from %s not authenticated." % msg.source)

      if not allow_client_access and rdfvalue.ClientURN.Validate(msg.source):
        raise RuntimeError("Event does not support clients.")

      if source_restriction and not source_restriction(msg.source):
        raise RuntimeError("Message source invalid.")

      stats.STATS.IncrementCounter("grr_worker_states_run")
      rdf_msg = rdfvalue.GrrMessage(msg)
      res = f(self, message=rdf_msg, event=rdf_msg.payload)
      return res

    return Decorated

  return Decorator


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
  if msg.source == rdfvalue.RDFURN("/"):
    raise RuntimeError("Message must have a valid source.")

  if not isinstance(msg, rdfvalue.RDFValue):
    raise ValueError("Can only publish RDFValue instances.")

  # Randomize the response id or events will get overwritten.
  msg.response_id = msg.task_id = rdfvalue.GrrMessage().task_id

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
      with flow_runner.WellKnownFlowManager(token=token) as flow_manager:
        flow_manager.QueueResponse(event_cls.well_known_session_id, msg)

  # Notify all the workers of their pending sessions.
  priorities = dict([(s, msg.priority) for s in sessions_queued])
  scheduler.SCHEDULER.MultiNotifyQueue(sessions_queued, priorities, token=token)


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
        stats.STATS.IncrementCounter("grr_unique_clients")
        raise communicator.UnknownClientCert("Cert not found")

      if rdfvalue.RDFURN(cert.common_name) != rdfvalue.RDFURN(common_name):
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
      # Set the client's cert
      client = aff4.FACTORY.Create(common_name, "VFSGRRClient", mode="w",
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
       a rdfvalue.GrrMessage.AuthorizationState.
    """
    result = rdfvalue.GrrMessage.AuthorizationState.UNAUTHENTICATED
    try:
      if api_version >= 3:
        # New version:
        if cipher.HMAC(response_comms.encrypted) != response_comms.hmac:
          raise communicator.DecryptionError("HMAC does not match.")

        if cipher.signature_verified:
          result = rdfvalue.GrrMessage.AuthorizationState.AUTHENTICATED

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
          stats.STATS.IncrementCounter("grr_rsa_operations")
          # Signature is not verified, we consider the message unauthenticated.
          if remote_public_key.verify(digest, signed_message_list.signature,
                                      cipher.hash_function_name) != 1:
            return rdfvalue.GrrMessage.AuthorizationState.UNAUTHENTICATED

        except RSA.RSAError as e:
          raise communicator.DecryptionError(e)

        result = rdfvalue.GrrMessage.AuthorizationState.AUTHENTICATED

      if result == rdfvalue.GrrMessage.AuthorizationState.AUTHENTICATED:
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
          stats.STATS.IncrementCounter("grr_authenticated_messages")

          # Update the client and server timestamps.
          client.Set(client.Schema.CLOCK, rdfvalue.RDFDatetime(client_time))
          client.Set(client.Schema.PING, rdfvalue.RDFDatetime().Now())

        else:
          # This is likely an old message
          return rdfvalue.GrrMessage.AuthorizationState.DESYNCHRONIZED

        # If we are prepared to live with a slight risk of replay we can
        # remove this.
        client.Flush()

    except communicator.UnknownClientCert:
      pass

    if result != rdfvalue.GrrMessage.AuthorizationState.AUTHENTICATED:
      stats.STATS.IncrementCounter("grr_unauthenticated_messages")

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
    self.well_known_flows = WellKnownFlow.GetAllWellKnownFlows(token=self.token)
    well_known_flow_names = self.well_known_flows.keys()
    for well_known_flow in well_known_flow_names:
      if well_known_flow not in config_lib.CONFIG["Frontend.well_known_flows"]:
        del self.well_known_flows[well_known_flow]

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

    stats.STATS.SetGaugeValue("grr_frontendserver_throttle_setting",
                              str(throttle_bundles_ratio))

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
      stats.STATS.IncrementCounter("grr_frontendserver_handle_throttled_num")
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
      response_message.job.Append(task)
    stats.STATS.IncrementCounter("grr_messages_sent", len(new_tasks))
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
      if msg.type == rdfvalue.GrrMessage.Type.STATUS:
        status = rdfvalue.GrrStatus(msg.args)
        if status.status == rdfvalue.GrrStatus.ReturnedStatus.CLIENT_KILLED:
          # A client crashed while performing an action, fire an event.
          PublishEvent("ClientCrash", rdfvalue.GrrMessage(msg),
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

      with flow_runner.FlowManager(token=self.token,
                                   store=self.data_store) as flow_manager:
        for msg in messages:
          priorities[session_id] = max(priorities.setdefault(session_id, 0),
                                       msg.priority)
          logging.debug("Queueing for the backend: %s", session_id)
          flow_manager.QueueResponse(session_id, msg)

    # Write the session ids that we saw to the worker queue.
    scheduler.SCHEDULER.MultiNotifyQueue(
        sessions_handled, priorities, token=self.token)

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
              msg.session_id, token=self.token)

          stats.STATS.IncrementCounter("grr_well_known_flow_requests")
        else:
          # Message should be queued to be processed in the backend.

          # Well known flows have a response_id==0, but if we queue up the state
          # as that it will overwrite some other message that is queued. So we
          # change it to a random number here.
          msg.response_id = utils.PRNG.GetULong()

          # By setting the request ID to increment with time we maintain rough
          # time order in the queue.
          msg.request_id = int(time.time())

          # Queue the message in the data store.
          result.append(msg)

    return result


def ProcessCompletedRequests(flow_obj, thread_pool, reqs):
  flow_obj.ProcessCompletedRequests(thread_pool, reqs)


class FlowInit(registry.InitHook):
  """Ensures that the Well known flows exist."""

  pre = ["AFF4InitHook", "StatsInit"]

  def RunOnce(self):
    """Exports our vars."""
    # Counters defined here
    stats.STATS.RegisterCounterMetric("grr_flow_completed_count")
    stats.STATS.RegisterCounterMetric("grr_flow_errors")
    stats.STATS.RegisterCounterMetric("grr_flow_invalid_flow_count")
    stats.STATS.RegisterCounterMetric("grr_flows_created")
    stats.STATS.RegisterEventMetric("grr_frontendserver_handle_time")
    stats.STATS.RegisterCounterMetric("grr_messages_sent")
    stats.STATS.RegisterCounterMetric("grr_request_retransmission_count")
    stats.STATS.RegisterCounterMetric("grr_response_out_of_order")
    stats.STATS.RegisterCounterMetric("grr_unique_clients")
    stats.STATS.RegisterCounterMetric("grr_unknown_clients")
    stats.STATS.RegisterCounterMetric("grr_well_known_flow_requests")
    stats.STATS.RegisterCounterMetric("grr_worker_requests_complete")
    stats.STATS.RegisterCounterMetric("grr_worker_requests_issued")
    stats.STATS.RegisterCounterMetric("grr_worker_states_run")
    stats.STATS.RegisterCounterMetric("grr_worker_well_known_flow_requests")
    stats.STATS.RegisterCounterMetric("grr_frontendserver_handle_num")
    stats.STATS.RegisterCounterMetric("grr_frontendserver_handle_throttled_num")
    stats.STATS.RegisterGaugeMetric("grr_frontendserver_throttle_setting", str)
