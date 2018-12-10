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

In order for the flow to be suspended and restored, its state is
stored in a protobuf. Rather than storing the entire flow, the
preserved state is well defined and can be found in the flow's "state"
attribute. Note that this means that any parameters assigned to the
flow object itself are not preserved across state executions - only
parameters specifically stored in the state are preserved.

In order to actually run the flow, a FlowRunner is used. The flow runner is
responsible for queuing messages to clients, launching child flows etc. The
runner stores internal flow management information inside the flow's state, in a
variable called "context". This context should only be used by the runner itself
and not manipulated by the flow.

The flow state is a normal dict (even though only types supported by
the ProtoDict class are supported in the state):

self.state.parameter_name = parameter_name

The following defaults parameters exist in the flow's state:

self.args: The flow's protocol buffer args - an instance of
  self.args_type. If the flow was instantiated using keywords only, a new
  instance of the args is created.

self.context: The flow runner's context.

self.runner_args: The flow runners args. This is an instance of
  FlowRunnerArgs() which may be build from keyword args.

"""
from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

import logging


from future.utils import itervalues
from future.utils import with_metaclass

from grr_response_core.lib import rdfvalue
from grr_response_core.lib import registry
from grr_response_core.lib import type_info
from grr_response_core.lib.rdfvalues import client as rdf_client
from grr_response_core.lib.rdfvalues import events as rdf_events
from grr_response_core.lib.rdfvalues import protodict as rdf_protodict
from grr_response_core.lib.rdfvalues import structs as rdf_structs
from grr_response_core.lib.util import random
from grr_response_core.stats import stats_collector_instance
from grr_response_proto import jobs_pb2
from grr_response_server import access_control
from grr_response_server import aff4
from grr_response_server import data_store
from grr_response_server import data_store_utils
from grr_response_server import events
from grr_response_server import flow_responses
from grr_response_server import flow_runner
from grr_response_server import grr_collections
from grr_response_server import multi_type_collection
from grr_response_server import notification as notification_lib
from grr_response_server import queue_manager
from grr_response_server import sequential_collection
from grr_response_server.rdfvalues import flow_objects as rdf_flow_objects
from grr_response_server.rdfvalues import flow_runner as rdf_flow_runner
from grr_response_server.rdfvalues import objects as rdf_objects


class FlowResultCollection(sequential_collection.GrrMessageCollection):
  """Sequential FlowResultCollection."""


class FlowError(Exception):
  """Raised when we can not retrieve the flow."""


# This is an implementation of an AttributedDict taken from
# http://stackoverflow.com/questions/4984647/accessing-dict-keys-like-an-attribute-in-python
# It works very well but there is a small drawback - there is no way
# to assign an attribute to this dict that does not get serialized. Do
# not inherit from this class, there might be interesting side
# effects.
class AttributedDict(dict):

  def __init__(self, *args, **kwargs):
    super(AttributedDict, self).__init__(*args, **kwargs)
    self.__dict__ = self


class EmptyFlowArgs(rdf_structs.RDFProtoStruct):
  """Some flows do not take argumentnts."""
  protobuf = jobs_pb2.EmptyMessage


# TODO(hanuszczak): Consider refactoring the interface of this class.
class FlowBehaviour(object):
  """A Behaviour is a property of a flow.

  Behaviours advertise what kind of flow this is. The flow can only advertise
  predefined behaviours.
  """

  # A constant which defines all the allowed behaviours and their descriptions.
  LEXICON = {
      # What GUI mode should this flow appear in?
      "BASIC":
          "Include in the simple UI. This flow is designed for simpler use.",
      "ADVANCED":
          "Include in advanced UI. This flow takes more experience to use.",
      "DEBUG":
          "This flow only appears in debug mode.",
  }

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


RESULTS_SUFFIX = "Results"
RESULTS_PER_TYPE_SUFFIX = "ResultsPerType"
LOGS_SUFFIX = "Logs"


def FilterArgsFromSemanticProtobuf(protobuf, kwargs):
  """Assign kwargs to the protobuf, and remove them from the kwargs dict."""
  for descriptor in protobuf.type_infos:
    value = kwargs.pop(descriptor.name, None)
    if value is not None:
      setattr(protobuf, descriptor.name, value)


def GetOutputPluginStates(output_plugins, source=None, token=None):
  """Initializes state for a list of output plugins."""
  output_plugins_states = []
  for plugin_descriptor in output_plugins:
    plugin_class = plugin_descriptor.GetPluginClass()
    try:
      plugin, plugin_state = plugin_class.CreatePluginAndDefaultState(
          source_urn=source, args=plugin_descriptor.plugin_args, token=token)
    except Exception as e:  # pylint: disable=broad-except
      logging.warning("Plugin %s failed to initialize (%s), ignoring it.",
                      plugin, e)
      continue

    # TODO(amoser): Those do not need to be inside the state, they
    # could be part of the plugin descriptor.
    plugin_state["logs"] = []
    plugin_state["errors"] = []

    output_plugins_states.append(
        rdf_flow_runner.OutputPluginState(
            plugin_state=plugin_state, plugin_descriptor=plugin_descriptor))

  return output_plugins_states


def StartAFF4Flow(args=None,
                  runner_args=None,
                  parent_flow=None,
                  sync=True,
                  token=None,
                  **kwargs):
  """The main factory function for creating and executing a new flow.

  Args:
    args: An arg protocol buffer which is an instance of the required flow's
      args_type class attribute.
    runner_args: an instance of FlowRunnerArgs() protocol buffer which is used
      to initialize the runner for this flow.
    parent_flow: A parent flow or None if this is a top level flow.
    sync: If True, the Start method of this flow will be called inline.
      Otherwise we schedule the starting of this flow on another worker.
    token: Security credentials token identifying the user.
    **kwargs: If args or runner_args are not specified, we construct these
      protobufs from these keywords.

  Returns:
    the session id of the flow.

  Raises:
    RuntimeError: Unknown or invalid parameters were provided.
  """
  # Build the runner args from the keywords.
  if runner_args is None:
    runner_args = rdf_flow_runner.FlowRunnerArgs()

  FilterArgsFromSemanticProtobuf(runner_args, kwargs)

  # Is the required flow a known flow?
  try:
    flow_cls = registry.AFF4FlowRegistry.FlowClassByName(runner_args.flow_name)
  except ValueError:
    stats_collector_instance.Get().IncrementCounter(
        "grr_flow_invalid_flow_count")
    raise RuntimeError("Unable to locate flow %s" % runner_args.flow_name)

  # If no token is specified, raise.
  if not token:
    raise access_control.UnauthorizedAccess("A token must be specified.")

  # For the flow itself we use a supervisor token.
  token = token.SetUID()

  # Extend the expiry time of this token indefinitely. Python on Windows only
  # supports dates up to the year 3000.
  token.expiry = rdfvalue.RDFDatetime.FromHumanReadable("2997-01-01")

  if flow_cls.category and not runner_args.client_id:
    raise RuntimeError("Flow with category (user-visible flow) has to be "
                       "started on a client, but runner_args.client_id "
                       "is missing.")

  # We create an anonymous AFF4 object first, The runner will then generate
  # the appropriate URN.
  flow_obj = aff4.FACTORY.Create(None, flow_cls, token=token)

  # Now parse the flow args into the new object from the keywords.
  if args is None:
    args = flow_obj.args_type()

  FilterArgsFromSemanticProtobuf(args, kwargs)

  # Check that the flow args are valid.
  args.Validate()

  # Store the flow args.
  flow_obj.args = args
  flow_obj.runner_args = runner_args

  # At this point we should exhaust all the keyword args. If any are left
  # over, we do not know what to do with them so raise.
  if kwargs:
    raise type_info.UnknownArg(
        "Unknown parameters to StartAFF4Flow: %s" % kwargs)

  # Create a flow runner to run this flow with.
  if parent_flow:
    parent_runner = parent_flow.runner
  else:
    parent_runner = None

  runner = flow_obj.CreateRunner(
      parent_runner=parent_runner, runner_args=runner_args)

  logging.info(u"Scheduling %s(%s) on %s", flow_obj.urn, runner_args.flow_name,
               runner_args.client_id)
  if sync:
    # Just run the first state inline. NOTE: Running synchronously means
    # that this runs on the thread that starts the flow. The advantage is
    # that that Start method can raise any errors immediately.
    flow_obj.Start()
  else:
    # Running Asynchronously: Schedule the start method on another worker.
    runner.CallState(next_state="Start")

  # The flow does not need to actually remain running.
  if not flow_obj.outstanding_requests:
    flow_obj.Terminate()

  flow_obj.Close()

  # Publish an audit event, only for top level flows.
  if parent_flow is None:
    events.Events.PublishEvent(
        "Audit",
        rdf_events.AuditEvent(
            user=token.username,
            action="RUN_FLOW",
            flow_name=runner_args.flow_name,
            urn=flow_obj.urn,
            client=runner_args.client_id),
        token=token)

  return flow_obj.urn


def RandomFlowId():
  """Returns a random flow id encoded as a hex string."""
  return "%08X" % random.PositiveUInt32()


def StartFlow(client_id=None,
              cpu_limit=None,
              creator=None,
              flow_args=None,
              flow_cls=None,
              network_bytes_limit=None,
              original_flow=None,
              output_plugins=None,
              parent_flow_obj=None,
              parent_hunt_id=None,
              **kwargs):
  """The main factory function for creating and executing a new flow.

  Args:
    client_id: ID of the client this flow should run on.
    cpu_limit: CPU limit in seconds for this flow.
    creator: Username that requested this flow.
    flow_args: An arg protocol buffer which is an instance of the required
      flow's args_type class attribute.
    flow_cls: Class of the flow that should be started.
    network_bytes_limit: Limit on the network traffic this flow can generated.
    original_flow: A FlowReference object in case this flow was copied from
      another flow.
    output_plugins: An OutputPluginDescriptor object indicating what output
      plugins should be used for this flow.
    parent_flow_obj: A parent flow object. None if this is a top level flow.
    parent_hunt_id: String identifying parent hunt. Can't be passed together
      with parent_flow_obj.
    **kwargs: If args or runner_args are not specified, we construct these
      protobufs from these keywords.

  Returns:
    the flow id of the new flow.

  Raises:
    ValueError: Unknown or invalid parameters were provided.
  """

  if parent_flow_obj is not None and parent_hunt_id is not None:
    raise ValueError(
        "parent_flow_obj and parent_hunt_id are mutually exclusive.")

  # Is the required flow a known flow?
  try:
    registry.FlowRegistry.FlowClassByName(flow_cls.__name__)
  except ValueError:
    stats_collector_instance.Get().IncrementCounter(
        "grr_flow_invalid_flow_count")
    raise ValueError("Unable to locate flow %s" % flow_cls.__name__)

  if not client_id:
    raise ValueError("Client_id is needed to start a flow.")

  # Now parse the flow args into the new object from the keywords.
  if flow_args is None:
    flow_args = flow_cls.args_type()

  FilterArgsFromSemanticProtobuf(flow_args, kwargs)
  # At this point we should exhaust all the keyword args. If any are left
  # over, we do not know what to do with them so raise.
  if kwargs:
    raise type_info.UnknownArg("Unknown parameters to StartFlow: %s" % kwargs)

  # Check that the flow args are valid.
  flow_args.Validate()

  rdf_flow = rdf_flow_objects.Flow(
      client_id=client_id,
      flow_class_name=flow_cls.__name__,
      args=flow_args,
      create_time=rdfvalue.RDFDatetime.Now(),
      creator=creator,
      output_plugins=output_plugins,
      original_flow=original_flow,
      flow_state="RUNNING")

  rdf_flow.flow_id = RandomFlowId()

  if parent_flow_obj:  # A flow is a nested flow.
    parent_rdf_flow = parent_flow_obj.rdf_flow
    rdf_flow.long_flow_id = "%s/%s" % (parent_rdf_flow.long_flow_id,
                                       rdf_flow.flow_id)
    rdf_flow.parent_flow_id = parent_rdf_flow.flow_id
    rdf_flow.parent_hunt_id = parent_rdf_flow.parent_hunt_id
    rdf_flow.parent_request_id = parent_flow_obj.GetCurrentOutboundId()
    if parent_rdf_flow.creator:
      rdf_flow.creator = parent_rdf_flow.creator
  elif parent_hunt_id:  # A flow is a root-level hunt-induced flow.
    rdf_flow.long_flow_id = "%s/%s" % (client_id, rdf_flow.flow_id)
    rdf_flow.parent_hunt_id = parent_hunt_id
  else:  # A flow is a root-level non-hunt flow.
    rdf_flow.long_flow_id = "%s/%s" % (client_id, rdf_flow.flow_id)

  if output_plugins:
    rdf_flow.output_plugins_states = GetOutputPluginStates(
        output_plugins,
        rdf_flow.long_flow_id,
        token=access_control.ACLToken(username=rdf_flow.creator))

  if network_bytes_limit is not None:
    rdf_flow.network_bytes_limit = network_bytes_limit
  if cpu_limit is not None:
    rdf_flow.cpu_limit = cpu_limit

  logging.info(u"Scheduling %s(%s) on %s", rdf_flow.long_flow_id,
               rdf_flow.flow_class_name, client_id)

  rdf_flow.current_state = "Start"

  flow_obj = flow_cls(rdf_flow)
  # Just run the first state inline. NOTE: Running synchronously means
  # that this runs on the thread that starts the flow. The advantage is
  # that that Start method can raise any errors immediately.
  flow_obj.Start()

  # The flow does not need to actually remain running.
  if not flow_obj.outstanding_requests:
    flow_obj.RunStateMethod("End")
    flow_obj.MarkDone()

  flow_obj.PersistState()

  data_store.REL_DB.WriteFlowObject(flow_obj.rdf_flow)

  if parent_flow_obj is not None:
    # We can optimize here and not write requests/responses to the database
    # since we have to do this for the parent flow at some point anyways.
    parent_flow_obj.MergeQueuedMessages(flow_obj)
  else:
    flow_obj.FlushQueuedMessages()

    # Publish an audit event, only for top level flows.
    # TODO(amoser): split urn field into dedicated strings.
    events.Events.PublishEvent(
        "Audit",
        rdf_events.AuditEvent(
            user=creator,
            action="RUN_FLOW",
            flow_name=rdf_flow.flow_class_name,
            urn=rdf_flow.long_flow_id,
            client=client_id))

  return rdf_flow.flow_id


class FlowBase(with_metaclass(registry.AFF4FlowRegistry, aff4.AFF4Volume)):
  """The base class for Flows and Hunts."""

  # Alternatively we can specify a single semantic protobuf that will be used to
  # provide the args.
  args_type = EmptyFlowArgs

  def Initialize(self):
    # This will be set to the state. Flows and Hunts can store
    # information in the state object which will be serialized between
    # state executions.
    self.state = None

    # This will be populated with an active runner.
    self.runner = None

    self.args = None

  def CreateRunner(self, **kw):
    """Make a new runner."""
    raise NotImplementedError("Cannot call CreateRunner on the base class.")

  def GetRunner(self):
    # If we already created the runner, just reuse it.
    if self.runner:
      return self.runner

    # Otherwise make a new runner.
    return self.CreateRunner()

  def _CheckLeaseAndFlush(self):
    # Check for Lock expiration first.
    self.CheckLease()
    # Flush the results. We might declare ourselves done in Save and
    # the results should be in before that.
    if self.runner:
      self.runner.FlushQueuedReplies()
    self.Save()
    self.WriteState()

  def Flush(self):
    """Flushes the flow/hunt and all its requests to the data_store."""
    self._CheckLeaseAndFlush()
    self.Load()
    super(FlowBase, self).Flush()
    # Writing the messages queued in the queue_manager of the runner always has
    # to be the last thing that happens or we will have a race condition.
    self.FlushMessages()

  def Close(self):
    """Flushes the flow and all its requests to the data_store."""
    self._CheckLeaseAndFlush()
    super(FlowBase, self).Close()
    # Writing the messages queued in the queue_manager of the runner always has
    # to be the last thing that happens or we will have a race condition.
    self.FlushMessages()

  def FlushMessages(self):
    """Write all the messages queued in the queue manager."""
    self.GetRunner().FlushMessages()

  def ShouldSendNotifications(self):
    return self.GetRunner().ShouldSendNotifications()

  def Terminate(self, status=None):
    """Terminates the flow."""

  def End(self, responses):
    """Final state.

    This method is called prior to destruction of the flow to give
    the flow a chance to clean up.

    Args:
      responses: A flow_responses.Responses object.
    """

  def Start(self):
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

  def StartAFF4Flow(self, *args, **kw):
    return StartAFF4Flow(*args, **kw)

  @property
  def session_id(self):
    return self.context.session_id

  @property
  def creator(self):
    return self.context.creator

  def Log(self, format_str, *args):
    """Logs the message using the flow's standard logging.

    Args:
      format_str: Format string
      *args: arguments to the format string
    """
    self.GetRunner().Log(format_str, *args)

  def GetLog(self):
    return self.GetRunner().GetLog()

  # The following methods simply delegate to the runner. They are meant to only
  # be called from within the state handling methods (i.e. a runner
  # should already exist by calling GetRunner() method).
  def CallClient(self,
                 action_cls,
                 request=None,
                 next_state=None,
                 request_data=None,
                 **kwargs):
    return self.runner.CallClient(
        action_cls=action_cls,
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
      responses = flow_responses.FakeResponses(messages, request_data)

    getattr(self, next_state)(responses)

  def CallState(self, next_state="", start_time=None):
    return self.runner.CallState(next_state=next_state, start_time=start_time)

  def CallFlow(self, flow_name, next_state=None, request_data=None, **kwargs):
    return self.runner.CallFlow(
        flow_name, next_state=next_state, request_data=request_data, **kwargs)


class GRRFlow(FlowBase):
  """A container aff4 object to maintain a flow.

  Flow objects are executed and scheduled by the workers, and extend
  grr.flow.GRRFlow. This object contains the flows object within an AFF4
  container.

  Note: Usually this object can not be created by users using the regular
  aff4.FACTORY.Create() method since it requires elevated permissions. This
  object can instead be created using the flow.StartAFF4Flow() method.

  After creation, access to the flow object can still be obtained through
  the usual aff4.FACTORY.Open() method.

  The GRRFlow object should be extended by flow implementations, adding state
  handling methods. The mechanics of running the flow are separated from the
  flow itself, using the runner object. Then FlowRunner() for the flow can be
  obtained from the flow.GetRunner(). The runner contains all the methods
  specific to running, scheduling and interrogating the flow:


  with aff4.FACTORY.Open(flow_urn, mode="rw") as fd:
    runner = fd.GetRunner()
    runner.ProcessCompletedRequests(messages)
  """

  class SchemaCls(aff4.AFF4Volume.SchemaCls):
    """Attributes specific to GRRFlow."""

    FLOW_STATE_DICT = aff4.Attribute(
        "aff4:flow_state_dict",
        rdf_protodict.AttributedDict,
        "The current state of this flow.",
        "FlowStateDict",
        versioned=False,
        creates_new_object_version=False)

    FLOW_ARGS = aff4.Attribute(
        "aff4:flow_args",
        rdf_protodict.EmbeddedRDFValue,
        "The arguments for this flow.",
        "FlowArgs",
        versioned=False,
        creates_new_object_version=False)

    FLOW_CONTEXT = aff4.Attribute(
        "aff4:flow_context",
        rdf_flow_runner.FlowContext,
        "The metadata for this flow.",
        "FlowContext",
        versioned=False,
        creates_new_object_version=False)

    FLOW_RUNNER_ARGS = aff4.Attribute(
        "aff4:flow_runner_args",
        rdf_flow_runner.FlowRunnerArgs,
        "The runner arguments used for this flow.",
        "FlowRunnerArgs",
        versioned=False,
        creates_new_object_version=False)

    CLIENT_CRASH = aff4.Attribute(
        "aff4:client_crash",
        rdf_client.ClientCrash,
        "Client crash details in case of a crash.",
        default=None,
        creates_new_object_version=False)

    PENDING_TERMINATION = aff4.Attribute(
        "aff4:pending_termination",
        rdf_flow_objects.PendingFlowTermination, "If true, this flow will be "
        "terminated as soon as any of its "
        "states are called.",
        creates_new_object_version=False)

  # This is used to arrange flows into a tree view
  category = ""
  friendly_name = None

  # Behaviors set attributes of this flow. See FlowBehavior() above.
  behaviours = FlowBehaviour("ADVANCED")

  def Initialize(self):
    """The initialization method."""
    super(GRRFlow, self).Initialize()
    self._client_version = None
    self._client_os = None
    self._client_knowledge_base = None

    if "r" in self.mode:
      state = self.Get(self.Schema.FLOW_STATE_DICT)
      self.context = self.Get(self.Schema.FLOW_CONTEXT)
      self.runner_args = self.Get(self.Schema.FLOW_RUNNER_ARGS)
      args = self.Get(self.Schema.FLOW_ARGS)
      if args:
        self.args = args.payload

      if state:
        self.state = AttributedDict(state.ToDict())
      else:
        self.state = AttributedDict()

      self.Load()

    if self.state is None:
      self.state = AttributedDict()

  def CreateRunner(self, **kw):
    """Make a new runner."""
    self.runner = flow_runner.FlowRunner(self, token=self.token, **kw)
    return self.runner

  @classmethod
  def GetDefaultArgs(cls, username=None):
    """Returns a useful default args semantic value.

    This should be extended by flows.

    Args:
      username: The username to get the default args for.

    Returns:
      an instance of cls.args_type pre-populated with useful data
    """
    return cls.args_type()

  def NotifyAboutEnd(self):
    """Send out a final notification about the end of this flow."""
    flow_ref = None
    if self.runner_args.client_id:
      flow_ref = rdf_objects.FlowReference(
          client_id=self.client_id, flow_id=self.urn.Basename())

    num_results = len(self.ResultCollection())
    notification_lib.Notify(
        self.creator, rdf_objects.UserNotification.Type.TYPE_FLOW_RUN_COMPLETED,
        "Flow %s completed with %d %s" % (self.__class__.__name__, num_results,
                                          num_results == 1 and "result" or
                                          "results"),
        rdf_objects.ObjectReference(
            reference_type=rdf_objects.ObjectReference.Type.FLOW,
            flow=flow_ref))

  def HeartBeat(self):
    if self.locked:
      lease_time = self.transaction.lease_time
      if self.CheckLease() < lease_time // 2:
        logging.debug("%s: Extending Lease", self.session_id)
        self.UpdateLease(lease_time)

        self.runner.HeartBeat()
    else:
      logging.warning("%s is heartbeating while not being locked.", self.urn)

  def _ValidateState(self):
    if self.context is None:
      raise IOError("Trying to write a flow without context: %s." % self.urn)

  def WriteState(self):
    if "w" in self.mode:
      self._ValidateState()
      self.Set(self.Schema.FLOW_ARGS(self.args))
      self.Set(self.Schema.FLOW_CONTEXT(self.context))
      self.Set(self.Schema.FLOW_RUNNER_ARGS(self.runner_args))
      protodict = rdf_protodict.AttributedDict().FromDict(self.state)
      self.Set(self.Schema.FLOW_STATE_DICT(protodict))

  def SendReply(self, response, tag=None):
    return self.runner.SendReply(response, tag=tag)

  def Error(self, backtrace, client_id=None):
    return self.runner.Error(backtrace, client_id=client_id)

  def Terminate(self, status=None):
    super(GRRFlow, self).Terminate(status=status)
    self.runner.Terminate(status=status)
    if self.GetRunner().ShouldSendNotifications():
      self.NotifyAboutEnd()

  @property
  def client_id(self):
    return self.client_urn.Basename()

  @property
  def client_urn(self):
    return self.runner_args.client_id

  @property
  def client_version(self):
    if self._client_version is None:
      self._client_version = data_store_utils.GetClientVersion(
          self.client_id, token=self.token)

    return self._client_version

  @property
  def client_os(self):
    if self._client_os is None:
      self._client_os = data_store_utils.GetClientOs(
          self.client_id, token=self.token)

    return self._client_os

  @property
  def client_knowledge_base(self):
    if self._client_knowledge_base is None:
      self._client_knowledge_base = data_store_utils.GetClientKnowledgeBase(
          self.client_id, token=self.token)
    return self._client_knowledge_base

  def Name(self):
    return self.__class__.__name__

  @property
  def outstanding_requests(self):
    return self.GetRunner().OutstandingRequests()

  @classmethod
  def MarkForTermination(cls, flow_urn, reason=None, mutation_pool=None):
    """Mark the flow for termination as soon as any of its states are called."""
    # Doing a blind write here using low-level data store API. Accessing
    # the flow via AFF4 is not really possible here, because it forces a state
    # to be written in Close() method.
    if mutation_pool is None:
      raise ValueError("Mutation pool can't be none.")

    mutation_pool.Set(
        flow_urn,
        cls.SchemaCls.PENDING_TERMINATION.predicate,
        rdf_flow_objects.PendingFlowTermination(reason=reason),
        replace=False)

  @classmethod
  def TerminateAFF4Flow(cls, flow_id, reason=None, status=None, token=None):
    """Terminate a flow.

    Args:
      flow_id: The flow session_id to terminate.
      reason: A reason to log.
      status: Status code used in the generated status message.
      token: The access token to be used for this request.

    Raises:
      FlowError: If the flow can not be found.
    """
    flow_obj = aff4.FACTORY.Open(
        flow_id, aff4_type=GRRFlow, mode="rw", token=token)

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

      # This calls runner.Terminate to kill the flow
      runner.Error(reason, status_code=status)

      flow_obj.Log("Terminated by user {0}. Reason: {1}".format(
          token.username, reason))

      # From now on we run with supervisor access
      super_token = token.SetUID()

      # Also terminate its children
      children_to_kill = aff4.FACTORY.MultiOpen(
          flow_obj.ListChildren(), token=super_token, aff4_type=GRRFlow)

      for child_obj in children_to_kill:
        cls.TerminateAFF4Flow(
            child_obj.urn, reason="Parent flow terminated.", token=super_token)

  # All the collections flows use.

  # Results collection.
  @property
  def output_urn(self):
    return self.urn.Add(RESULTS_SUFFIX)

  @classmethod
  def ResultCollectionForFID(cls, flow_id):
    """Returns the ResultCollection for the flow with a given flow_id.

    Args:
      flow_id: The id of the flow, a RDFURN of the form aff4:/flows/F:123456.

    Returns:
      The collection containing the results for the flow identified by the id.
    """
    return sequential_collection.GeneralIndexedCollection(
        flow_id.Add(RESULTS_SUFFIX))

  def ResultCollection(self):
    return self.ResultCollectionForFID(self.session_id)

  # Results collection per type.
  @property
  def multi_type_output_urn(self):
    return self.urn.Add(RESULTS_PER_TYPE_SUFFIX)

  @classmethod
  def TypedResultCollectionForFID(cls, flow_id):
    return multi_type_collection.MultiTypeCollection(
        flow_id.Add(RESULTS_PER_TYPE_SUFFIX))

  def TypedResultCollection(self):
    return self.TypedResultCollectionForFID(self.session_id)

  # Logs collection.
  @property
  def logs_collection_urn(self):
    return self.urn.Add(LOGS_SUFFIX)

  @classmethod
  def LogCollectionForFID(cls, flow_id):
    return grr_collections.LogCollection(flow_id.Add(LOGS_SUFFIX))

  def LogCollection(self):
    return self.LogCollectionForFID(self.session_id)


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
    for cls in itervalues(registry.AFF4FlowRegistry.FLOW_REGISTRY):
      if aff4.issubclass(cls, WellKnownFlow) and cls.well_known_session_id:
        well_known_flow = cls(cls.well_known_session_id, mode="rw", token=token)
        well_known_flows[cls.well_known_session_id.FlowName()] = well_known_flow

    return well_known_flows

  def _SafeProcessMessage(self, *args, **kwargs):
    try:
      self.ProcessMessage(*args, **kwargs)
    except Exception as e:  # pylint: disable=broad-except
      logging.exception("Error in WellKnownFlow.ProcessMessage: %s", e)
      stats_collector_instance.Get().IncrementCounter(
          "well_known_flow_errors", fields=[str(self.session_id)])

  @property
  def session_id(self):
    return self.well_known_session_id

  @property
  def outstanding_requests(self):
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
      for response in manager.FetchResponses(session_id):
        messages.append(response)
      manager.DeleteWellKnownFlowResponses(session_id, messages)

    return messages

  def ProcessResponses(self, responses, thread_pool):
    """For WellKnownFlows we receive these messages directly."""
    for response in responses:
      thread_pool.AddTask(
          target=self._SafeProcessMessage,
          args=(response,),
          name=self.__class__.__name__)

  def ProcessMessages(self, msgs):
    for msg in msgs:
      self.ProcessMessage(msg)
      self.HeartBeat()

  def ProcessMessage(self, msg):
    """This is where messages get processed.

    Override in derived classes.

    Args:
       msg: The GrrMessage sent by the client. Note that this message is not
         authenticated.
    """

  def _ValidateState(self):
    # For normal flows it's a bug to write an empty state, here it's ok.
    pass

  def UpdateKillNotification(self):
    # For WellKnownFlows it doesn't make sense to kill them ever.
    pass
