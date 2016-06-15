#!/usr/bin/env python
"""This file defines the base classes for Flows.

A Flow is a state machine which executes actions on the
client. Messages are transmitted between the flow object and the
client with their responses introduced into a state handler within the
flow.

The flow can send messages to a client, or launch other child flows. While these
messages are processed, the flow can be suspended indefinitely into the data
store. When replies arrive from the client, or a child flow, the flow is woken
up and the responses are sent to one of the flow state methods.

In order for the flow to be suspended and restored, its state is pickled. Rather
than pickling the entire flow, the preserved state is well defined and can be
found in the flow's "state" attribute. Note that this means that any parameters
assigned to the flow object itself are not preserved across state executions -
only parameters specifically stored in the state are preserved.

In order to actually run the flow, a FlowRunner is used. The flow runner is
responsible for queuing messages to clients, launching child flows etc. The
runner stores internal flow management information inside the flow's state, in a
variable called "context". This context should only be used by the runner itself
and not manipulated by the flow.

Before a flow is allowed to store a parameter in the state object, the parameter
must be registered:

self.state.Register("parameter_name", parameter_name)

The following defaults parameters exist in the flow's state:

self.state.args: The flow's protocol buffer args - an instance of
  self.args_type. If the flow was instantiated using keywords only, a new
  instance of the args is created.

self.state.context: The flow runner's context.

self.state.context.args: The flow runners args. This is an instance of
  FlowRunnerArgs() which may be build from keyword args.
"""


import functools
import operator
import time

from M2Crypto import X509

import logging

from grr.client import actions
from grr.lib import access_control
from grr.lib import aff4
from grr.lib import communicator
from grr.lib import config_lib
from grr.lib import data_store
from grr.lib import flow_runner
from grr.lib import queue_manager
from grr.lib import queues
from grr.lib import rdfvalue
from grr.lib import registry
from grr.lib import stats
from grr.lib import threadpool
from grr.lib import type_info
from grr.lib import utils
from grr.lib.rdfvalues import client as rdf_client
from grr.lib.rdfvalues import flows as rdf_flows
from grr.lib.rdfvalues import protodict as rdf_protodict
from grr.lib.rdfvalues import structs as rdf_structs
from grr.proto import jobs_pb2


class AuditEvent(rdf_structs.RDFProtoStruct):
  protobuf = jobs_pb2.AuditEvent

  def __init__(self, initializer=None, age=None, **kwargs):

    super(AuditEvent, self).__init__(initializer=initializer, age=age, **kwargs)
    if not self.id:
      self.id = utils.PRNG.GetULong()
    if not self.timestamp:
      self.timestamp = rdfvalue.RDFDatetime().Now()


class FlowError(Exception):
  """Raised when we can not retrieve the flow."""

# Flow contexts contain pickled FlowRunnerArgs, which moved from this module to
# flow_runner. This alias allows us to read contexts built with the old loction.
# It should not be used for any other purpose.
#
# TODO(user): Remove once such flows are no longer relevant.
#
# No choice about the name. pylint: disable=invalid-name
FlowRunnerArgs = flow_runner.FlowRunnerArgs

# pylint: enable=invalid-name


class Responses(object):
  """An object encapsulating all the responses to a request.

  This object is normally only instantiated from the flow StateHandler
  decorator.
  """

  def __init__(self,
               request=None,
               responses=None,
               auth_required=True,
               next_states=None):
    self.status = None  # A GrrStatus rdfvalue object.
    self.success = True
    self.next_states = next_states
    self.request = request
    self._auth_required = auth_required
    if request:
      self.request_data = rdf_protodict.Dict(request.data)
    self._responses = []
    self._dropped_responses = []

    if responses:
      # This may not be needed if we can assume that responses are
      # returned in lexical order from the data_store.
      responses.sort(key=operator.attrgetter("response_id"))

      # The iterator that was returned as part of these responses. This should
      # be passed back to actions that expect an iterator.
      self.iterator = None

      # Filter the responses by authorized states
      for msg in responses:
        # Check if the message is authenticated correctly.
        if msg.auth_state == msg.AuthorizationState.DESYNCHRONIZED or (
            self._auth_required and
            msg.auth_state != msg.AuthorizationState.AUTHENTICATED):
          logging.warning("%s: Messages must be authenticated (Auth state %s)",
                          msg.session_id, msg.auth_state)
          self._dropped_responses.append(msg)
          # Skip this message - it is invalid
          continue

        # Check for iterators
        if msg.type == msg.Type.ITERATOR:
          self.iterator = rdf_client.Iterator(msg.payload)
          continue

        # Look for a status message
        if msg.type == msg.Type.STATUS:
          # Our status is set to the first status message that we see in
          # the responses. We ignore all other messages after that.
          self.status = rdf_flows.GrrStatus(msg.payload)

          # Check this to see if the call succeeded
          self.success = self.status.status == self.status.ReturnedStatus.OK

          # Ignore all other messages
          break

        # Use this message
        self._responses.append(msg)

      if self.status is None:
        # This is a special case of de-synchronized messages.
        if self._dropped_responses:
          logging.error("De-synchronized messages detected:\n" + "\n".join(
              [utils.SmartUnicode(x) for x in self._dropped_responses]))

        if responses:
          self._LogFlowState(responses)

        raise FlowError("No valid Status message.")

    # This is the raw message accessible while going through the iterator
    self.message = None

  def __iter__(self):
    """An iterator which returns all the responses in order."""
    old_response_id = None
    action_registry = actions.ActionPlugin.classes
    expected_response_classes = []
    is_client_request = False
    # This is the client request so this response packet was sent by a client.
    if self.request.HasField("request"):
      is_client_request = True
      client_action_name = self.request.request.name
      if client_action_name not in action_registry:
        raise RuntimeError("Got unknown client action: %s." %
                           client_action_name)
      expected_response_classes = action_registry[
          client_action_name].out_rdfvalues

    for message in self._responses:
      self.message = rdf_flows.GrrMessage(message)

      # Handle retransmissions
      if self.message.response_id == old_response_id:
        continue

      else:
        old_response_id = self.message.response_id

      if self.message.type == self.message.Type.MESSAGE:
        if is_client_request:
          # Let's do some verification for requests that came from clients.
          if not expected_response_classes:
            raise RuntimeError("Client action %s does not specify out_rdfvalue."
                               % client_action_name)
          else:
            args_rdf_name = self.message.args_rdf_name
            if not args_rdf_name:
              raise RuntimeError("Deprecated message format received: "
                                 "args_rdf_name is None.")
            elif args_rdf_name not in [
                x.__name__ for x in expected_response_classes
            ]:
              raise RuntimeError("Response type was %s but expected %s for %s."
                                 % (args_rdf_name, expected_response_classes,
                                    client_action_name))

        yield self.message.payload

  def First(self):
    """A convenience method to return the first response."""
    for x in self:
      return x

  def __len__(self):
    return len(self._responses)

  def __nonzero__(self):
    return bool(self._responses)

  def _LogFlowState(self, responses):
    session_id = responses[0].session_id
    token = access_control.ACLToken(username="GRRWorker", reason="Logging")
    token.supervisor = True

    logging.error(
        "No valid Status message.\nState:\n%s\n%s\n%s",
        data_store.DB.ResolvePrefix(
            session_id.Add("state"),
            "flow:", token=token),
        data_store.DB.ResolvePrefix(
            session_id.Add("state/request:%08X" % responses[0].request_id),
            "flow:",
            token=token),
        data_store.DB.ResolvePrefix(queues.FLOWS,
                                    "notify:%s" % session_id,
                                    token=token))


class FakeResponses(Responses):
  """An object which emulates the responses.

  This is only used internally to call a state method inline.
  """

  def __init__(self, messages, request_data):
    super(FakeResponses, self).__init__()
    self.success = True
    self._responses = messages or []
    self.request_data = request_data
    self.iterator = None

  def __iter__(self):
    return iter(self._responses)


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
      next_states = set([next_state])
    else:
      next_states = set(next_state)

    @functools.wraps(f)
    def Decorated(self, responses=None, request=None, direct_response=None):
      """A decorator that defines allowed follow up states for a method.

      Args:
        self: The self of the wrapped function.

        responses: The responses for this state.

        request: The request sent out originally.

        direct_response: A final responses object that does not need wrapping
                         again. If given, neither request nor responses is used.

      Returns:
        This calls the state and returns the obtained result.
      """
      if "r" in self.mode:
        pending_termination = self.Get(self.Schema.PENDING_TERMINATION)
        if pending_termination:
          self.Error(pending_termination.reason)
          return

      runner = self.GetRunner()
      next_states = Decorated.next_states

      old_next_states = runner.GetAllowedFollowUpStates()
      try:
        if direct_response is not None:
          runner.SetAllowedFollowUpStates(next_states)
          return f(self, direct_response)

        if isinstance(responses, Responses):
          next_states.update(responses.next_states)
        else:
          # Prepare a responses object for the state method to use:
          responses = Responses(request=request,
                                next_states=next_states,
                                responses=responses,
                                auth_required=auth_required)

          if responses.status:
            runner.SaveResourceUsage(request, responses)

        stats.STATS.IncrementCounter("grr_worker_states_run")
        runner.SetAllowedFollowUpStates(next_states)

        if f.__name__ == "Start":
          stats.STATS.IncrementCounter("flow_starts", fields=[self.Name()])

        # Run the state method (Allow for flexibility in prototypes)
        args = [self, responses]
        res = f(*args[:f.func_code.co_argcount])

        return res
      finally:
        runner.SetAllowedFollowUpStates(old_next_states)

    # Make sure the state function itself knows where its allowed to
    # go (This is used to introspect the state graph).
    Decorated.next_states = next_states

    return Decorated

  return Decorator


class PendingFlowTermination(rdf_structs.RDFProtoStruct):
  """Descriptor of a pending flow termination."""
  protobuf = jobs_pb2.PendingFlowTermination


class EmptyFlowArgs(rdf_structs.RDFProtoStruct):
  """Some flows do not take argumentnts."""
  protobuf = jobs_pb2.EmptyMessage


class Behaviour(object):
  """A Behaviour is a property of a flow.

  Behaviours advertise what kind of flow this is. The flow can only advertise
  predefined behaviours.
  """
  # A constant which defines all the allowed behaviours and their descriptions.
  LEXICON = {}

  def __init__(self, *args):
    self.set = set()
    for arg in args:
      if arg not in self.LEXICON:
        raise ValueError("Behaviour %s not known." % arg)

      self.set.add(str(arg))

  def __add__(self, other):
    other = str(other)

    if other not in self.LEXICON:
      raise ValueError("Behaviour %s not known." % other)

    return self.__class__(other, *list(self.set))

  def __sub__(self, other):
    other = str(other)

    result = self.set.copy()
    result.discard(other)

    return self.__class__(*list(result))

  def __iter__(self):
    return iter(self.set)

  def IsSupported(self, other):
    """Ensure the other Behaviour supports all our Behaviours."""
    if not isinstance(other, self.__class__):
      raise TypeError("Must be called on %s" % self.__class__)

    return self.set.issubset(other.set)


class FlowBehaviour(Behaviour):
  # A constant which defines all the allowed behaviours and their descriptions.
  LEXICON = {
      # What GUI mode should this flow appear in?
      "BASIC": ("Include in the simple UI. This flow is designed "
                "for simpler use."),
      "ADVANCED": ("Include in advanced UI. This flow takes "
                   "more experience to use."),
      "DANGEROUS": "This flow may be dangerous. Only available for Admins",
      "DEBUG": "This flow only appears in debug mode.",

      # Is this a global flow or a client specific flow?
      "Client Flow": "This flow works on a client.",
      "Global Flow": "This flow works without a client.",

      # OS Support.
      "OSX": "This flow works on OSX operating systems.",
      "Windows": "This flow works on Windows operating systems.",
      "Linux": "This flow works on Linux operating systems.",
  }


class GRRFlow(aff4.AFF4Volume):
  """A container aff4 object to maintain a flow.

  Flow objects are executed and scheduled by the workers, and extend
  grr.flow.GRRFlow. This object contains the flows object within an AFF4
  container.

  Note: Usually this object can not be created by users using the regular
  aff4.FACTORY.Create() method since it requires elevated permissions. This
  object can instead be created using the flow.GRRFlow.StartFlow() method.

  After creation, access to the flow object can still be obtained through
  the usual aff4.FACTORY.Open() method.

  The GRRFlow object should be extended by flow implementations, adding state
  handling methods (State methods are called with responses and should be
  decorated using the StateHandler() decorator). The mechanics of running the
  flow are separated from the flow itself, using the runner object. Then
  FlowRunner() for the flow can be obtained from the flow.GetRunner(). The
  runner contains all the methods specific to running, scheduling and
  interrogating the flow:


  with aff4.FACTORY.Open(flow_urn, mode="rw") as fd:
    runner = fd.GetRunner()
    runner.ProcessCompletedRequests(messages)

  """

  class SchemaCls(aff4.AFF4Volume.SchemaCls):
    """Attributes specific to GRRFlow."""

    FLOW_STATE = aff4.Attribute("aff4:flow_state",
                                rdf_flows.FlowState,
                                "The current state of this flow.",
                                "FlowState",
                                versioned=False,
                                creates_new_object_version=False)

    NOTIFICATION = aff4.Attribute("aff4:notification", rdf_flows.Notification,
                                  "Notifications for the flow.")

    CLIENT_CRASH = aff4.Attribute("aff4:client_crash",
                                  rdf_client.ClientCrash,
                                  "Client crash details in case of a crash.",
                                  default=None,
                                  creates_new_object_version=False)

    PENDING_TERMINATION = aff4.Attribute("aff4:pending_termination",
                                         PendingFlowTermination,
                                         "If true, this flow will be "
                                         "terminated as soon as any of its "
                                         "states are called.",
                                         creates_new_object_version=False)

  # This is used to arrange flows into a tree view
  category = ""
  friendly_name = None

  # If this is set, the flow is only displayed in the UI if the user has one of
  # the labels given.
  AUTHORIZED_LABELS = []

  __metaclass__ = registry.MetaclassRegistry

  # Should ACLs be enforced on this flow? This implies the user must have full
  # access to the client before they can run this flow.
  ACL_ENFORCED = True

  # Behaviors set attributes of this flow. See FlowBehavior() above.
  behaviours = FlowBehaviour("Client Flow", "ADVANCED")

  # Alternatively we can specify a single semantic protobuf that will be used to
  # provide the args.
  args_type = EmptyFlowArgs

  # This will be populated with an active runner.
  runner = None

  # This will be set to the flow's state. Flows can store information in the
  # state object which will be serialized between state executions.
  state = None

  runner_cls = flow_runner.FlowRunner

  # If True we let the flow handle its own client crashes. Otherwise the flow
  # is killed when the client crashes.
  handles_crashes = False

  def Initialize(self):
    """The initialization method."""
    if "r" in self.mode:
      self.state = self.Get(self.Schema.FLOW_STATE)
      if self.state:
        self.Load()

        # A convenience attribute to allow flows to access their args directly.
        self.args = self.state.get("args")

    if self.state is None:
      self.state = self.Schema.FLOW_STATE()
    elif self.state.errors:
      logging.warning("Failed to read state for %s - forcing read only mode.",
                      self.urn)
      self.mode = "r"

  @classmethod
  def GetDefaultArgs(cls, token=None):
    """Return a useful default args semantic value.

    This should be extended by flows.

    Args:
      token: The ACL token for the user.

    Returns:
      an instance of cls.args_type pre-populated with useful data
    """
    _ = token
    return cls.args_type()

  @classmethod
  def FilterArgsFromSemanticProtobuf(cls, protobuf, kwargs):
    """Assign kwargs to the protobuf, and remove them from the kwargs dict."""
    for descriptor in protobuf.type_infos:
      value = kwargs.pop(descriptor.name, None)
      if value is not None:
        setattr(protobuf, descriptor.name, value)

  def UpdateKillNotification(self):
    # If kill timestamp is set (i.e. if the flow is currently being
    # processed by the worker), delete the old "kill if stuck" notification
    # and schedule a new one, further in the future.
    if (self.runner.schedule_kill_notifications and
        self.runner.context.kill_timestamp):
      with queue_manager.QueueManager(token=self.token) as manager:
        manager.DeleteNotification(
            self.session_id,
            start=self.runner.context.kill_timestamp,
            end=self.runner.context.kill_timestamp + rdfvalue.Duration("1s"))

        stuck_flows_timeout = rdfvalue.Duration(config_lib.CONFIG[
            "Worker.stuck_flows_timeout"])
        self.runner.context.kill_timestamp = (
            rdfvalue.RDFDatetime().Now() + stuck_flows_timeout)
        manager.QueueNotification(session_id=self.session_id,
                                  in_progress=True,
                                  timestamp=self.runner.context.kill_timestamp)

  def HeartBeat(self):
    if self.locked:
      lease_time = config_lib.CONFIG["Worker.flow_lease_time"]
      if self.CheckLease() < lease_time / 2:
        logging.info("%s: Extending Lease", self.session_id)
        self.UpdateLease(lease_time)

        self.UpdateKillNotification()
    else:
      logging.warning("%s is heartbeating while not being locked.", self.urn)

  def WriteState(self):
    if "w" in self.mode:
      if self.state.Empty():
        raise IOError("Trying to write an empty state for flow %s." % self.urn)
      self.Set(self.Schema.FLOW_STATE(self.state))

  def FlushMessages(self):
    """Write all the messages queued in the queue manager."""
    self.GetRunner().FlushMessages()

  def Flush(self, sync=True):
    """Flushes the flow and all its requests to the data_store."""
    # Check for Lock expiration first.
    self.CheckLease()
    self.Save()
    self.WriteState()
    self.Load()
    super(GRRFlow, self).Flush(sync=sync)
    # Writing the messages queued in the queue_manager of the runner always has
    # to be the last thing that happens or we will have a race condition.
    self.FlushMessages()

  def Close(self, sync=True):
    """Flushes the flow and all its requests to the data_store."""
    # Check for Lock expiration first.
    self.CheckLease()
    self.Save()
    self.WriteState()
    super(GRRFlow, self).Close(sync=sync)
    # Writing the messages queued in the queue_manager of the runner always has
    # to be the last thing that happens or we will have a race condition.
    self.FlushMessages()

  def CreateRunner(self, parent_runner=None, runner_args=None, **kw):
    """Make a new runner."""
    self.runner = self.runner_cls(self,
                                  token=self.token,
                                  parent_runner=parent_runner,
                                  runner_args=runner_args,
                                  **kw)

    return self.runner

  def GetRunner(self):
    # If we already created the runner, just reuse it.
    if self.runner:
      return self.runner

    # Otherwise make a new runner.
    self.runner = self.runner_cls(self)
    return self.runner

  @StateHandler()
  def End(self):
    """Final state.

    This method is called prior to destruction of the flow to give
    the flow a chance to clean up.
    """
    if self.runner.output is not None:
      self.Notify("ViewObject", self.runner.output.urn,
                  u"Completed with {0} results".format(len(self.runner.output)))

    else:
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

  def Log(self, format_str, *args):
    """Logs the message using the flow's standard logging.

    Args:
      format_str: Format string
      *args: arguments to the format string
    """
    self.GetRunner().Log(format_str, *args)

  def GetLog(self):
    return self.GetRunner().GetLog()

  def Status(self, format_str, *args):
    """Flows can call this method to set a status message visible to users."""
    self.GetRunner().Status(format_str, *args)

  def Notify(self, message_type, subject, msg):
    """Send a notification to the originating user.

    Args:
       message_type: The type of the message. This allows the UI to format
         a link to the original object e.g. "ViewObject" or "HostInformation"
       subject: The urn of the AFF4 object of interest in this link.
       msg: A free form textual message.
    """
    self.GetRunner().Notify(message_type, subject, msg)

  def Publish(self,
              event_name,
              message=None,
              session_id=None,
              priority=rdf_flows.GrrMessage.Priority.MEDIUM_PRIORITY):
    """Publish a message to an event queue.

    Args:
       event_name: The name of the event to publish to.
       message: An RDFValue instance to publish to the event listeners.
       session_id: The session id to send from, defaults to self.session_id.
       priority: Controls the priority of this message.
    """
    result = message
    logging.debug("Publishing %s to %s", utils.SmartUnicode(message)[:100],
                  event_name)

    # Wrap message in a GrrMessage so it can be queued.
    if not isinstance(message, rdf_flows.GrrMessage):
      result = rdf_flows.GrrMessage(payload=message)

    result.session_id = session_id or self.session_id
    result.auth_state = rdf_flows.GrrMessage.AuthorizationState.AUTHENTICATED
    result.source = self.session_id
    result.priority = priority

    self.runner.Publish(event_name, result)

  # The following methods simply delegate to the runner. They are meant to only
  # be called from within the flow's state handling methods (i.e. a runner
  # should already exist by calling GetRunner() method).
  def CallClient(self,
                 action_name,
                 request=None,
                 next_state=None,
                 request_data=None,
                 **kwargs):
    return self.runner.CallClient(action_name=action_name,
                                  request=request,
                                  next_state=next_state,
                                  request_data=request_data,
                                  **kwargs)

  def CallStateInline(self,
                      messages=None,
                      next_state="",
                      request_data=None,
                      responses=None):
    if responses is None:
      responses = FakeResponses(messages, request_data)

    getattr(self, next_state)(self.runner, direct_response=responses)

  def CallState(self,
                messages=None,
                next_state="",
                request_data=None,
                start_time=None):
    return self.runner.CallState(messages=messages,
                                 next_state=next_state,
                                 request_data=request_data,
                                 start_time=start_time)

  def CallFlow(self, flow_name, next_state=None, request_data=None, **kwargs):
    return self.runner.CallFlow(flow_name,
                                next_state=next_state,
                                request_data=request_data,
                                **kwargs)

  def SendReply(self, response):
    return self.runner.SendReply(response)

  def Error(self, backtrace, client_id=None):
    return self.runner.Error(backtrace, client_id=client_id)

  def Terminate(self):
    return self.runner.Terminate()

  @property
  def session_id(self):
    return self.state.context.session_id

  @property
  def client_id(self):
    return self.state.context.args.client_id

  def Name(self):
    return self.__class__.__name__

  @classmethod
  def StartFlow(cls, args=None, runner_args=None,  # pylint: disable=g-bad-name
                parent_flow=None, _store=None, sync=True, **kwargs):
    """The main factory function for Creating and executing a new flow.

    Args:

      args: An arg protocol buffer which is an instance of the required flow's
        args_type class attribute.

      runner_args: an instance of FlowRunnerArgs() protocol buffer which is used
        to initialize the runner for this flow.

      parent_flow: A parent flow or None if this is a top level flow.
      _store: The data store to use for running this flow (only used for
              testing).

      sync: If True, the Start method of this flow will be called
         inline. Otherwise we schedule the starting of this flow on another
         worker.

      **kwargs: If args or runner_args are not specified, we construct these
        protobufs from these keywords.

    Returns:
      the session id of the flow.

    Raises:
      RuntimeError: Unknown or invalid parameters were provided.
    """

    # Build the runner args from the keywords.
    if runner_args is None:
      runner_args = flow_runner.FlowRunnerArgs()

    cls.FilterArgsFromSemanticProtobuf(runner_args, kwargs)

    # When asked to run a flow in the future this implied it will run
    # asynchronously.
    if runner_args.start_time:
      sync = False

    # Is the required flow a known flow?
    if runner_args.flow_name not in GRRFlow.classes:
      stats.STATS.IncrementCounter("grr_flow_invalid_flow_count")
      raise RuntimeError("Unable to locate flow %s" % runner_args.flow_name)

    # If no token is specified, use the default token.
    if not runner_args.HasField("token"):
      if data_store.default_token is None:
        raise access_control.UnauthorizedAccess("A token must be specified.")

      runner_args.token = data_store.default_token.Copy()

    # Make sure we are allowed to run this flow. If not, we raise here. We
    # respect SUID (supervisor) if it is already set. SUID cannot be set by the
    # user since it isn't part of the ACLToken proto.
    data_store.DB.security_manager.CheckIfCanStartFlow(
        runner_args.token,
        runner_args.flow_name,
        with_client_id=runner_args.client_id)

    flow_cls = GRRFlow.GetPlugin(runner_args.flow_name)
    # If client id was specified and flow doesn't have exemption from ACL
    # checking policy, then check that the user has access to the client
    # where the flow is going to run.
    if flow_cls.ACL_ENFORCED and runner_args.client_id:
      data_store.DB.security_manager.CheckClientAccess(runner_args.token,
                                                       runner_args.client_id)

    # For the flow itself we use a supervisor token.
    token = runner_args.token.SetUID()

    # Extend the expiry time of this token indefinitely. Python on Windows only
    # supports dates up to the year 3000, this number corresponds to July, 2997.
    token.expiry = 32427003069 * rdfvalue.RDFDatetime.converter

    # We create an anonymous AFF4 object first, The runner will then generate
    # the appropriate URN.
    flow_obj = aff4.FACTORY.Create(
        None,
        aff4.AFF4Object.classes.get(runner_args.flow_name),
        token=token)

    # Now parse the flow args into the new object from the keywords.
    if args is None:
      args = flow_obj.args_type()

    cls.FilterArgsFromSemanticProtobuf(args, kwargs)

    # Check that the flow args are valid.
    args.Validate()

    # Store the flow args in the state.
    flow_obj.state.Register("args", args)

    # A convenience attribute to allow flows to access their args directly.
    flow_obj.args = args

    # At this point we should exhaust all the keyword args. If any are left
    # over, we do not know what to do with them so raise.
    if kwargs:
      raise type_info.UnknownArg("Unknown parameters to StartFlow: %s" % kwargs)

    # Create a flow runner to run this flow with.
    if parent_flow:
      parent_runner = parent_flow.runner
    else:
      parent_runner = None

    runner = flow_obj.CreateRunner(parent_runner=parent_runner,
                                   runner_args=runner_args,
                                   _store=_store or data_store.DB)

    logging.info(u"Scheduling %s(%s) on %s", flow_obj.urn,
                 runner_args.flow_name, runner_args.client_id)

    if sync:
      # Just run the first state inline. NOTE: Running synchronously means
      # that this runs on the thread that starts the flow. The advantage is
      # that that Start method can raise any errors immediately.
      flow_obj.Start()
    else:
      # Running Asynchronously: Schedule the start method on another worker.
      runner.CallState(next_state="Start", start_time=runner_args.start_time)

    # The flow does not need to actually remain running.
    if not runner.OutstandingRequests():
      flow_obj.Terminate()

    flow_obj.Close()

    # Publish an audit event, only for top level flows.
    if parent_flow is None:
      Events.PublishEvent("Audit",
                          AuditEvent(user=token.username,
                                     action="RUN_FLOW",
                                     flow_name=runner_args.flow_name,
                                     urn=flow_obj.urn,
                                     client=runner_args.client_id),
                          token=token)

    return flow_obj.urn

  @classmethod
  def MarkForTermination(cls, flow_urn, reason=None, sync=False, token=None):
    """Mark the flow for termination as soon as any of its states are called."""
    # Doing a blind write here using low-level data store API. Accessing
    # the flow via AFF4 is not really possible here, because it forces a state
    # to be written in Close() method.
    data_store.DB.Set(flow_urn,
                      cls.SchemaCls.PENDING_TERMINATION.predicate,
                      PendingFlowTermination(reason=reason),
                      replace=False,
                      sync=sync,
                      token=token)

  @classmethod
  def TerminateFlow(cls,
                    flow_id,
                    reason=None,
                    status=None,
                    token=None,
                    force=False):
    """Terminate a flow.

    Args:
      flow_id: The flow session_id to terminate.
      reason: A reason to log.
      status: Status code used in the generated status message.
      token: The access token to be used for this request.
      force: If True then terminate locked flows hard.

    Raises:
      FlowError: If the flow can not be found.
    """
    if not force:
      flow_obj = aff4.FACTORY.OpenWithLock(flow_id,
                                           aff4_type=GRRFlow,
                                           blocking=True,
                                           token=token)
    else:
      flow_obj = aff4.FACTORY.Open(flow_id,
                                   aff4_type=GRRFlow,
                                   mode="rw",
                                   token=token)

    if not flow_obj:
      raise FlowError("Could not terminate flow %s" % flow_id)

    with flow_obj:
      runner = flow_obj.GetRunner()
      if not runner.IsRunning():
        return

      if token is None:
        token = access_control.ACLToken()

      if reason is None:
        reason = "Manual termination by console."

      # Make sure we are only allowed to terminate this flow, if we are
      # allowed to start it. The fact that we could open the flow object
      # means that we have access to the client (if it's not a global
      # flow).
      data_store.DB.security_manager.CheckIfCanStartFlow(
          token, flow_obj.Name(),
          with_client_id=runner.args.client_id)

      # This calls runner.Terminate to kill the flow
      runner.Error(reason, status=status)

      flow_obj.Log("Terminated by user {0}. Reason: {1}".format(token.username,
                                                                reason))

      # From now on we run with supervisor access
      super_token = token.SetUID()

      # Also terminate its children
      children_to_kill = aff4.FACTORY.MultiOpen(flow_obj.ListChildren(),
                                                token=super_token,
                                                aff4_type=GRRFlow)

      for child_obj in children_to_kill:
        cls.TerminateFlow(child_obj.urn,
                          reason="Parent flow terminated.",
                          token=super_token,
                          force=force)

  @classmethod
  def PrintArgsHelp(cls):
    print cls.GetArgsHelpAsString()

  @classmethod
  def _ClsHelpEpilog(cls):
    return cls.GetArgsHelpAsString()

  @classmethod
  def GetCallingPrototypeAsString(cls):
    """Get a description of the calling prototype for this flow."""
    output = []
    output.append("flow.GRRFlow.StartFlow(client_id=client_id, ")
    output.append("flow_name=\"%s\", " % cls.__name__)
    prototypes = []
    if cls.args_type:
      for type_descriptor in cls.args_type.type_infos:
        if not type_descriptor.hidden:
          prototypes.append("%s=%s" % (type_descriptor.name,
                                       type_descriptor.name))
    output.append(", ".join(prototypes))
    output.append(")")
    return "".join(output)

  @classmethod
  def GetArgs(cls):
    """Get a simplified description of the args for this flow."""
    args = {}
    if cls.args_type:
      for type_descriptor in cls.args_type.type_infos:
        if not type_descriptor.hidden:
          args[type_descriptor.name] = {
              "description": type_descriptor.description,
              "default": type_descriptor.default,
              "type": "",
          }
          if type_descriptor.type:
            args[type_descriptor.name]["type"] = type_descriptor.type.__name__
    return args

  @classmethod
  def GetArgsHelpAsString(cls):
    """Get a string description of the calling prototype for this function."""
    output = ["  Call Spec:", "    %s" % cls.GetCallingPrototypeAsString(), ""]
    arg_list = sorted(cls.GetArgs().items(), key=lambda x: x[0])
    if not arg_list:
      output.append("  Args: None")
    else:
      output.append("  Args:")
      for arg, val in arg_list:
        output.append("    %s" % arg)
        output.append("      description: %s" % val["description"])
        output.append("      type: %s" % val["type"])
        output.append("      default: %s" % val["default"])
        output.append("")
    return "\n".join(output)

  @staticmethod
  def GetFlowRequests(flow_urns, token=None):
    """Returns all outstanding requests for the flows in flow_urns."""
    flow_requests = {}
    flow_request_urns = [flow_urn.Add("state") for flow_urn in flow_urns]

    for flow_urn, values in data_store.DB.MultiResolvePrefix(flow_request_urns,
                                                             "flow:",
                                                             token=token):
      for subject, serialized, _ in values:
        try:
          if "status" in subject:
            msg = rdf_flows.GrrMessage(serialized)
          else:
            msg = rdf_flows.RequestState(serialized)
        except Exception as e:  # pylint: disable=broad-except
          logging.warn("Error while parsing: %s", e)
          continue

        flow_requests.setdefault(flow_urn, []).append(msg)
    return flow_requests


class GRRGlobalFlow(GRRFlow):
  """A flow that acts globally instead of on a specific client.

  Flows that inherit from this will not be shown in the normal Start New Flows
  UI, but will instead be seen in Admin Flows.
  """

  behaviours = GRRFlow.behaviours + "Global Flow" - "Client Flow"


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
  here.
  """
  # This is the session_id that will be used to register these flows
  well_known_session_id = None

  # Well known flows are not browsable.
  category = None

  @classmethod
  def GetAllWellKnownFlows(cls, token=None):
    """Get instances of all well known flows."""
    well_known_flows = {}
    for cls in GRRFlow.classes.values():
      if aff4.issubclass(cls, WellKnownFlow) and cls.well_known_session_id:
        well_known_flow = cls(cls.well_known_session_id, mode="rw", token=token)
        well_known_flows[cls.well_known_session_id.FlowName()] = well_known_flow

    return well_known_flows

  def _SafeProcessMessage(self, *args, **kwargs):
    try:
      self.ProcessMessage(*args, **kwargs)
    except Exception as e:  # pylint: disable=broad-except
      logging.exception("Error in WellKnownFlow.ProcessMessage: %s", e)
      stats.STATS.IncrementCounter("well_known_flow_errors",
                                   fields=[str(self.session_id)])

  def CallState(self, messages=None, next_state=None, delay=0):
    """Well known flows have no states to call."""
    pass

  @property
  def session_id(self):
    return self.well_known_session_id

  def OutstandingRequests(self):
    # Lie about it to prevent us from being destroyed
    return 1

  def FlushMessages(self):
    """Write all the queued messages."""
    # Well known flows do not write anything as they don't issue client calls
    # and don't have states.
    pass

  def FetchAndRemoveRequestsAndResponses(self, session_id):
    """Removes WellKnownFlow messages from the queue and returns them."""
    messages = []
    with queue_manager.WellKnownQueueManager(token=self.token) as manager:
      for _, responses in manager.FetchRequestsAndResponses(session_id):
        messages.extend(responses)
        manager.DeleteWellKnownFlowResponses(session_id, responses)

    return messages

  def ProcessResponses(self, responses, thread_pool):
    """For WellKnownFlows we receive these messages directly."""
    for response in responses:
      thread_pool.AddTask(target=self._SafeProcessMessage,
                          args=(response,),
                          name=self.__class__.__name__)

  def ProcessMessages(self, msgs):
    for msg in msgs:
      self.ProcessMessage(msg)
      self.HeartBeat()

  def ProcessMessage(self, msg):
    """This is where messages get processed.

    Override in derived classes:

    Args:
       msg: The GrrMessage sent by the client. Note that this
            message is not authenticated.
    """

  def CallClient(self,
                 client_id,
                 action_name,
                 request=None,
                 response_session_id=None,
                 **kwargs):
    """Calls a client action from a well known flow."""

    if client_id is None:
      raise FlowError("CallClient needs a valid client_id.")

    client_id = rdf_client.ClientURN(client_id)

    # Retrieve the correct rdfvalue to use for this client action.
    try:
      action = actions.ActionPlugin.classes[action_name]
    except KeyError:
      raise RuntimeError("Client action %s not found." % action_name)

    if action.in_rdfvalue is None:
      if request:
        raise RuntimeError("Client action %s does not expect args." %
                           action_name)
    else:
      if request is None:
        # Create a new rdf request.
        request = action.in_rdfvalue(**kwargs)
      else:
        # Verify that the request type matches the client action requirements.
        if not isinstance(request, action.in_rdfvalue):
          raise RuntimeError("Client action expected %s but got %s" %
                             (action.in_rdfvalue, type(request)))

    if response_session_id is None:
      cls = GRRFlow.classes["IgnoreResponses"]
      response_session_id = cls.well_known_session_id

    msg = rdf_flows.GrrMessage(
        session_id=utils.SmartUnicode(response_session_id),
        name=action_name,
        request_id=0,
        queue=client_id.Queue(),
        payload=request)

    queue_manager.QueueManager(token=self.token).Schedule(msg)

  def WriteState(self):
    if "w" in self.mode:
      # For normal flows it's a bug to write an empty state, here it's ok.
      self.Set(self.Schema.FLOW_STATE(self.state))

  def UpdateKillNotification(self):
    # For WellKnownFlows it doesn't make sense to kill them ever.
    pass


def EventHandler(source_restriction=False,
                 auth_required=True,
                 allow_client_access=False):
  """A convenience decorator for Event Handlers.

  Args:

    source_restriction: If this is set to True, each time a message is
      received, its source is passed to the method "CheckSource" of
      the event listener. If that method returns True, processing is
      permitted. Otherwise, the message is rejected.

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

      if (not allow_client_access and msg.source and
          rdf_client.ClientURN.Validate(msg.source)):
        raise RuntimeError("Event does not support clients.")

      if source_restriction:
        source_check_method = getattr(self, "CheckSource")
        if not source_check_method:
          raise RuntimeError("CheckSource method not found.")
        if not source_check_method(msg.source):
          raise RuntimeError("Message source invalid.")

      stats.STATS.IncrementCounter("grr_worker_states_run")
      rdf_msg = rdf_flows.GrrMessage(msg)
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

  __metaclass__ = registry.EventRegistry

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


class Events(object):
  """A class that provides event publishing methods."""

  @classmethod
  def PublishEvent(cls, event_name, msg, token=None):
    """Publish the message into all listeners of the event.

    If event_name is a string, we send the message to all event handlers which
    contain this string in their EVENT static member. This allows the event to
    be sent to multiple interested listeners. Alternatively, the event_name can
    specify a single URN of an event listener to receive the message.

    Args:
      event_name: Either a URN of an event listener or an event name.
      msg: The message to send to the event handler.
      token: ACL token.

    Raises:
      ValueError: If the message is invalid. The message must be a Semantic
        Value (instance of RDFValue) or a full GrrMessage.
    """
    cls.PublishMultipleEvents({event_name: [msg]}, token=token)

  @classmethod
  def PublishMultipleEvents(cls, events, token=None):
    """Publish the message into all listeners of the event.

    If event_name is a string, we send the message to all event handlers which
    contain this string in their EVENT static member. This allows the event to
    be sent to multiple interested listeners. Alternatively, the event_name can
    specify a single URN of an event listener to receive the message.

    Args:

      events: A dict with keys being event names and values being lists of
        messages.
      token: ACL token.

    Raises:
      ValueError: If the message is invalid. The message must be a Semantic
        Value (instance of RDFValue) or a full GrrMessage.
    """
    with queue_manager.WellKnownQueueManager(token=token) as manager:
      event_name_map = registry.EventRegistry.EVENT_NAME_MAP
      for event_name, messages in events.iteritems():
        handler_urns = []
        if isinstance(event_name, basestring):
          for event_cls in event_name_map.get(event_name, []):
            if event_cls.well_known_session_id is None:
              logging.error("Well known flow %s has no session_id.",
                            event_cls.__name__)
            else:
              handler_urns.append(event_cls.well_known_session_id)

        else:
          handler_urns.append(event_name)

        for msg in messages:
          # Allow the event name to be either a string or a URN of an event
          # listener.
          if not isinstance(msg, rdfvalue.RDFValue):
            raise ValueError("Can only publish RDFValue instances.")

          # Wrap the message in a GrrMessage if needed.
          if not isinstance(msg, rdf_flows.GrrMessage):
            msg = rdf_flows.GrrMessage(payload=msg)

          # Randomize the response id or events will get overwritten.
          msg.response_id = msg.task_id = msg.GenerateTaskID()
          # Well known flows always listen for request id 0.
          msg.request_id = 0

          # Forward the message to the well known flow's queue.
          for event_urn in handler_urns:
            manager.QueueResponse(event_urn, msg)
            manager.QueueNotification(rdf_flows.GrrNotification(
                session_id=event_urn,
                priority=msg.priority))

  @classmethod
  def PublishEventInline(cls, event_name, msg, token=None):
    """Directly publish the message into all listeners of the event."""

    if not isinstance(msg, rdfvalue.RDFValue):
      raise ValueError("Can only publish RDFValue instances.")

    # Wrap the message in a GrrMessage if needed.
    if not isinstance(msg, rdf_flows.GrrMessage):
      msg = rdf_flows.GrrMessage(payload=msg)

    # Event name must be a string.
    if not isinstance(event_name, basestring):
      raise ValueError("Event name must be a string.")
    event_name_map = registry.EventRegistry.EVENT_NAME_MAP
    for event_cls in event_name_map.get(event_name, []):
      event_obj = event_cls(event_cls.well_known_session_id,
                            mode="rw",
                            token=token)
      event_obj.ProcessMessage(msg)


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
      #
      # TODO(user): remove the dependency loop and resulting use of
      # AFF4Object.classes
      client = aff4.FACTORY.Create(common_name,
                                   aff4.AFF4Object.classes["VFSGRRClient"],
                                   mode="rw",
                                   token=self.token,
                                   ignore_cache=True)
      cert = client.Get(client.Schema.CERT)
      if not cert:
        stats.STATS.IncrementCounter("grr_unique_clients")
        raise communicator.UnknownClientCert("Cert not found")

      if rdfvalue.RDFURN(cert.common_name) != rdfvalue.RDFURN(common_name):
        logging.error("Stored cert mismatch for %s", common_name)
        raise communicator.UnknownClientCert("Stored cert mismatch")

      self.client_cache.Put(common_name, client)
      stats.STATS.SetGaugeValue("grr_frontendserver_client_cache_size",
                                len(self.client_cache))

      return cert.GetPubKey()


class ServerCommunicator(communicator.Communicator):
  """A communicator which stores certificates using AFF4."""

  def __init__(self, certificate, private_key, token=None):
    self.client_cache = utils.FastStore(1000)
    self.token = token
    super(ServerCommunicator, self).__init__(certificate=certificate,
                                             private_key=private_key)
    self.pub_key_cache = ServerPubKeyCache(self.client_cache, token=token)

  def _LoadOurCertificate(self):
    """Loads the server certificate."""
    self.cert = X509.load_cert_string(str(self.certificate))

    # Our common name
    self.common_name = self.pub_key_cache.GetCNFromCert(self.cert)

  def VerifyMessageSignature(self, response_comms, signed_message_list, cipher,
                             api_version):
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
       a rdf_flows.GrrMessage.AuthorizationState.
    """
    result = rdf_flows.GrrMessage.AuthorizationState.UNAUTHENTICATED
    try:
      if cipher.signature_verified:
        result = rdf_flows.GrrMessage.AuthorizationState.AUTHENTICATED

      if result == rdf_flows.GrrMessage.AuthorizationState.AUTHENTICATED:
        client_id = cipher.cipher_metadata.source
        try:
          client = self.client_cache.Get(client_id)
        except KeyError:
          client = aff4.FACTORY.Create(client_id,
                                       aff4.AFF4Object.classes["VFSGRRClient"],
                                       mode="rw",
                                       token=self.token)
          self.client_cache.Put(client_id, client)
          stats.STATS.SetGaugeValue("grr_frontendserver_client_cache_size",
                                    len(self.client_cache))

        ip = response_comms.orig_request.source_ip
        client.Set(client.Schema.CLIENT_IP(ip))

        # The very first packet we see from the client we do not have its clock
        remote_time = client.Get(client.Schema.CLOCK) or 0
        client_time = signed_message_list.timestamp or 0

        # This used to be a strict check here so absolutely no out of
        # order messages would be accepted ever. Turns out that some
        # proxies can send your request with some delay even if the
        # client has already timed out (and sent another request in
        # the meantime, making the first one out of order). In that
        # case we would just kill the whole flow as a
        # precaution. Given the behavior of those proxies, this seems
        # now excessive and we have changed the replay protection to
        # only trigger on messages that are more than one hour old.

        if client_time < long(remote_time - rdfvalue.Duration("1h")):
          logging.warning("Message desynchronized for %s: %s >= %s", client_id,
                          long(remote_time), int(client_time))
          # This is likely an old message
          return rdf_flows.GrrMessage.AuthorizationState.DESYNCHRONIZED

        stats.STATS.IncrementCounter("grr_authenticated_messages")

        # Update the client and server timestamps only if the client
        # time moves forward.
        if client_time > long(remote_time):
          client.Set(client.Schema.CLOCK, rdfvalue.RDFDatetime(client_time))
          client.Set(client.Schema.PING, rdfvalue.RDFDatetime().Now())
        else:
          logging.warning("Out of order message for %s: %s >= %s", client_id,
                          long(remote_time), int(client_time))

        client.Flush(sync=False)

    except communicator.UnknownClientCert:
      pass

    if result != rdf_flows.GrrMessage.AuthorizationState.AUTHENTICATED:
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

  def __init__(self,
               certificate,
               private_key,
               max_queue_size=50,
               message_expiry_time=120,
               max_retransmission_time=10,
               store=None,
               threadpool_prefix="grr_threadpool"):
    # Identify ourselves as the server.
    self.token = access_control.ACLToken(username="GRRFrontEnd",
                                         reason="Implied.")
    self.token.supervisor = True
    self.throttle_callback = lambda: True
    self.SetThrottleBundlesRatio(None)

    # This object manages our crypto.
    self._communicator = ServerCommunicator(certificate=certificate,
                                            private_key=private_key,
                                            token=self.token)

    self.data_store = store or data_store.DB
    self.receive_thread_pool = {}
    self.message_expiry_time = message_expiry_time
    self.max_retransmission_time = max_retransmission_time
    self.max_queue_size = max_queue_size
    self.thread_pool = threadpool.ThreadPool.Factory(
        threadpool_prefix,
        min_threads=2,
        max_threads=config_lib.CONFIG["Threadpool.size"])
    self.thread_pool.Start()

    # Well known flows are run on the front end.
    self.well_known_flows = (
        WellKnownFlow.GetAllWellKnownFlows(token=self.token))
    well_known_flow_names = self.well_known_flows.keys()
    for well_known_flow in well_known_flow_names:
      if well_known_flow not in config_lib.CONFIG["Frontend.well_known_flows"]:
        del self.well_known_flows[well_known_flow]

  def SetThrottleCallBack(self, callback):
    self.throttle_callback = callback

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
      interval = (
          self.handled_bundles[-1] - self.handled_bundles[0]) / float(blen - 1)
    else:
      # TODO(user): this can occasionally return False even when
      # throttle_bundles_ratio is 0, treat it in a generic way.
      return self.throttle_bundles_ratio == 0

    should_throttle = (
        bundle_time - self.last_not_throttled_bundle_time < interval / max(
            0.1e-6, float(self.throttle_bundles_ratio)))

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

    now = time.time()
    if messages:
      # Receive messages in line.
      self.ReceiveMessages(source, messages)

    # We send the client a maximum of self.max_queue_size messages
    required_count = max(0, self.max_queue_size - request_comms.queue_size)
    tasks = []

    message_list = rdf_flows.MessageList()
    if self.UpdateAndCheckIfShouldThrottle(time.time()):
      stats.STATS.IncrementCounter("grr_frontendserver_handle_throttled_num")

    elif self.throttle_callback():
      # Only give the client messages if we are able to receive them in a
      # reasonable time.
      if time.time() - now < 10:
        tasks = self.DrainTaskSchedulerQueueForClient(source, required_count,
                                                      message_list)
    else:
      stats.STATS.IncrementCounter("grr_frontendserver_handle_throttled_num")

    # Encode the message_list in the response_comms using the same API version
    # the client used.
    try:
      self._communicator.EncodeMessages(message_list,
                                        response_comms,
                                        destination=str(source),
                                        timestamp=timestamp,
                                        api_version=request_comms.api_version)
    except communicator.UnknownClientCert:
      # We can not encode messages to the client yet because we do not have the
      # client certificate - return them to the queue so we can try again later.
      queue_manager.QueueManager(token=self.token).Schedule(tasks)
      raise

    return source, len(messages)

  def DrainTaskSchedulerQueueForClient(self, client, max_count,
                                       response_message):
    """Drains the client's Task Scheduler queue.

    1) Get all messages in the client queue.
    2) Sort these into a set of session_ids.
    3) Use data_store.DB.ResolvePrefix() to query all requests.
    4) Delete all responses for retransmitted messages (if needed).

    Args:
       client: The ClientURN object specifying this client.

       max_count: The maximum number of messages we will issue for the
                  client.

       response_message: a MessageList object we fill for with GrrMessages
    Returns:
       The tasks respresenting the messages returned. If we can not send them,
       we can reschedule them for later.
    """
    if max_count <= 0:
      return []

    client = rdf_client.ClientURN(client)

    start_time = time.time()
    # Drain the queue for this client
    new_tasks = queue_manager.QueueManager(token=self.token).QueryAndOwn(
        queue=client.Queue(),
        limit=max_count,
        lease_seconds=self.message_expiry_time)

    initial_ttl = rdf_flows.GrrMessage().task_ttl
    check_before_sending = []
    result = []
    for task in new_tasks:
      if task.task_ttl < initial_ttl - 1:
        # This message has been leased before.
        check_before_sending.append(task)
      else:
        response_message.job.Append(task)
        result.append(task)

    if check_before_sending:
      with queue_manager.QueueManager(token=self.token) as manager:
        status_found = manager.MultiCheckStatus(check_before_sending)

        # All messages that don't have a status yet should be sent again.
        for task in check_before_sending:
          if task not in status_found:
            result.append(task)
          else:
            manager.DeQueueClientRequest(client, task.task_id)

    stats.STATS.IncrementCounter("grr_messages_sent", len(result))
    logging.debug("Drained %d messages for %s in %s seconds.", len(result),
                  client, time.time() - start_time)

    return result

  def ReceiveMessages(self, client_id, messages):
    """Receives and processes the messages from the source.

    For each message we update the request object, and place the
    response in that request's queue. If the request is complete, we
    send a message to the worker.

    Args:
      client_id: The client which sent the messages.
      messages: A list of GrrMessage RDFValues.
    """
    now = time.time()
    with queue_manager.QueueManager(token=self.token,
                                    store=self.data_store) as manager:
      sessions_handled = []
      for session_id, msgs in utils.GroupBy(
          messages, operator.attrgetter("session_id")).iteritems():

        # Remove and handle messages to WellKnownFlows
        unprocessed_msgs = self.HandleWellKnownFlows(msgs)

        if not unprocessed_msgs:
          continue

        # Keep track of all the flows we handled in this request.
        sessions_handled.append(session_id)

        for msg in unprocessed_msgs:
          manager.QueueResponse(session_id, msg)

        for msg in unprocessed_msgs:
          # Messages for well known flows should notify even though they don't
          # have a status.
          if msg.request_id == 0:
            manager.QueueNotification(session_id=msg.session_id,
                                      priority=msg.priority)
            # Those messages are all the same, one notification is enough.
            break
          elif msg.type == rdf_flows.GrrMessage.Type.STATUS:
            # If we receive a status message from the client it means the client
            # has finished processing this request. We therefore can de-queue it
            # from the client queue.
            manager.DeQueueClientRequest(client_id, msg.task_id)
            manager.QueueNotification(session_id=msg.session_id,
                                      priority=msg.priority,
                                      last_status=msg.request_id)

            stat = rdf_flows.GrrStatus(msg.payload)
            if stat.status == rdf_flows.GrrStatus.ReturnedStatus.CLIENT_KILLED:
              # A client crashed while performing an action, fire an event.
              Events.PublishEvent("ClientCrash",
                                  rdf_flows.GrrMessage(msg),
                                  token=self.token)

    logging.debug("Received %s messages in %s sec", len(messages),
                  time.time() - now)

  def HandleWellKnownFlows(self, messages):
    """Hands off messages to well known flows."""
    msgs_by_wkf = {}
    result = []
    for msg in messages:
      # Regular message - queue it.
      if msg.response_id != 0:
        result.append(msg)
        continue

      # Well known flows:
      flow_name = msg.session_id.FlowName()
      if flow_name in self.well_known_flows:
        # This message should be processed directly on the front end.
        msgs_by_wkf.setdefault(flow_name, []).append(msg)

        # TODO(user): Deprecate in favor of 'well_known_flow_requests'
        # metric.
        stats.STATS.IncrementCounter("grr_well_known_flow_requests")

        stats.STATS.IncrementCounter("well_known_flow_requests",
                                     fields=[str(msg.session_id)])
      else:
        # Message should be queued to be processed in the backend.

        # Well known flows have a response_id==0, but if we queue up the state
        # as that it will overwrite some other message that is queued. So we
        # change it to a random number here.
        msg.response_id = utils.PRNG.GetULong()

        # Queue the message in the data store.
        result.append(msg)

    for flow_name, msg_list in msgs_by_wkf.iteritems():
      flow = self.well_known_flows[flow_name]
      flow.ProcessMessages(msg_list)

    return result


def ProcessCompletedRequests(flow_obj, thread_pool, reqs):
  flow_obj.ProcessCompletedRequests(thread_pool, reqs)


class FlowInit(registry.InitHook):
  """Sets up flow-related stats."""

  pre = ["AFF4InitHook"]

  def RunOnce(self):
    # Frontend metrics. These metrics should be used by the code that
    # feeds requests into the frontend.
    stats.STATS.RegisterGaugeMetric("frontend_active_count",
                                    int,
                                    fields=[("source", str)])
    stats.STATS.RegisterGaugeMetric("frontend_max_active_count", int)
    stats.STATS.RegisterCounterMetric("frontend_in_bytes",
                                      fields=[("source", str)])
    stats.STATS.RegisterCounterMetric("frontend_out_bytes",
                                      fields=[("source", str)])
    stats.STATS.RegisterCounterMetric("frontend_request_count",
                                      fields=[("source", str)])
    # Client requests sent to an inactive datacenter. This indicates a
    # misconfiguration.
    stats.STATS.RegisterCounterMetric("frontend_inactive_request_count",
                                      fields=[("source", str)])
    stats.STATS.RegisterEventMetric("frontend_request_latency",
                                    fields=[("source", str)])

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
    stats.STATS.RegisterCounterMetric("grr_worker_states_run")
    stats.STATS.RegisterCounterMetric("grr_worker_well_known_flow_requests")
    stats.STATS.RegisterCounterMetric("grr_frontendserver_handle_num")
    stats.STATS.RegisterCounterMetric("grr_frontendserver_handle_throttled_num")
    stats.STATS.RegisterGaugeMetric("grr_frontendserver_throttle_setting", str)
    stats.STATS.RegisterGaugeMetric("grr_frontendserver_client_cache_size", int)

    # Flow-aware counters
    stats.STATS.RegisterCounterMetric("flow_starts", fields=[("flow", str)])
    stats.STATS.RegisterCounterMetric("flow_errors", fields=[("flow", str)])
    stats.STATS.RegisterCounterMetric("flow_completions",
                                      fields=[("flow", str)])
    stats.STATS.RegisterCounterMetric("well_known_flow_requests",
                                      fields=[("flow", str)])
    stats.STATS.RegisterCounterMetric("well_known_flow_errors",
                                      fields=[("flow", str)])
