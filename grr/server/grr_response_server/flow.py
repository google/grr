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
"""
import enum
import logging
import traceback

from typing import Optional, Sequence

from grr_response_core.lib import rdfvalue
from grr_response_core.lib import registry
from grr_response_core.lib import type_info
from grr_response_core.lib.util import compatibility
from grr_response_core.lib.util import random
from grr_response_core.stats import metrics
from grr_response_server import data_store
from grr_response_server.databases import db
from grr_response_server.rdfvalues import flow_objects as rdf_flow_objects
from grr_response_server.rdfvalues import flow_runner as rdf_flow_runner


GRR_FLOW_INVALID_FLOW_COUNT = metrics.Counter("grr_flow_invalid_flow_count")


class Error(Exception):
  """Base class for this package's exceptions."""


class CanNotStartFlowWithExistingIdError(Error):
  """Raises by StartFlow when trying to start a flow with an existing id."""

  def __init__(self, client_id, flow_id):
    message = ("Flow %s already exists on the client %s." %
               (client_id, flow_id))
    super().__init__(message)

    self.client_id = client_id
    self.flow_id = flow_id


class FlowResourcesExceededError(Error):
  """An error indicating that the flow used too many resources."""


# This is an implementation of an AttributedDict taken from
# http://stackoverflow.com/questions/4984647/accessing-dict-keys-like-an-attribute-in-python
# It works very well but there is a small drawback - there is no way
# to assign an attribute to this dict that does not get serialized. Do
# not inherit from this class, there might be interesting side
# effects.
class AttributedDict(dict):

  def __init__(self, *args, **kwargs):
    super().__init__(*args, **kwargs)
    self.__dict__ = self


def FilterArgsFromSemanticProtobuf(protobuf, kwargs):
  """Assign kwargs to the protobuf, and remove them from the kwargs dict."""
  for descriptor in protobuf.type_infos:
    value = kwargs.pop(descriptor.name, None)
    if value is not None:
      setattr(protobuf, descriptor.name, value)


def GetOutputPluginStates(output_plugins, source=None):
  """Initializes state for a list of output plugins."""
  output_plugins_states = []
  for plugin_descriptor in output_plugins:
    plugin_class = plugin_descriptor.GetPluginClass()
    try:
      _, plugin_state = plugin_class.CreatePluginAndDefaultState(
          source_urn=source, args=plugin_descriptor.plugin_args)
    except Exception as e:  # pylint: disable=broad-except
      raise ValueError("Plugin %s failed to initialize (%s)" %
                       (plugin_class, e))

    # TODO(amoser): Those do not need to be inside the state, they
    # could be part of the plugin descriptor.
    plugin_state["logs"] = []
    plugin_state["errors"] = []

    output_plugins_states.append(
        rdf_flow_runner.OutputPluginState(
            plugin_state=plugin_state, plugin_descriptor=plugin_descriptor))

  return output_plugins_states


def RandomFlowId() -> str:
  """Returns a random flow id encoded as a hex string."""
  return "{:016X}".format(random.Id64())


class _ParentType(enum.Enum):
  """Enum describing what data type led to a flow's creation."""
  ROOT = 0
  FLOW = 1
  HUNT = 2
  SCHEDULED_FLOW = 3


class FlowParent(object):
  """Class describing what data type led to a flow's creation."""

  def __init__(self,
               parent_type: _ParentType,
               parent_id: Optional[str] = None,
               parent_flow_obj=None):
    """Instantiates a FlowParent. Use the class methods instead."""
    self.type = parent_type
    self.id = parent_id
    self.flow_obj = parent_flow_obj

  @property
  def is_flow(self) -> bool:
    """True, if the flow is started as child-flow."""
    return self.type == _ParentType.FLOW

  @property
  def is_hunt(self) -> bool:
    """True, if the flow is started as part of a hunt."""
    return self.type == _ParentType.HUNT

  @property
  def is_root(self) -> bool:
    """True, if the flow is started as top-level flow."""
    return self.type == _ParentType.ROOT

  @property
  def is_scheduled_flow(self) -> bool:
    """True, if the flow is started from a ScheduledFlow."""
    return self.type == _ParentType.SCHEDULED_FLOW

  @classmethod
  def FromFlow(cls, flow_obj) -> "FlowParent":
    """References another flow (flow_base.FlowBase) as parent."""
    return cls(_ParentType.FLOW, flow_obj.rdf_flow.flow_id, flow_obj)

  @classmethod
  def FromHuntID(cls, hunt_id: str) -> "FlowParent":
    """References another hunt as parent by its ID."""
    return cls(_ParentType.HUNT, hunt_id)

  @classmethod
  def FromRoot(cls) -> "FlowParent":
    """References no parent to mark a flow as top-level flow."""
    return cls(_ParentType.ROOT)

  @classmethod
  def FromScheduledFlowID(cls, scheduled_flow_id: str) -> "FlowParent":
    """References a ScheduledFlow as parent by its ID."""
    return cls(_ParentType.SCHEDULED_FLOW, scheduled_flow_id)


def StartFlow(client_id=None,
              cpu_limit=None,
              creator=None,
              flow_args=None,
              flow_cls=None,
              network_bytes_limit=None,
              original_flow=None,
              output_plugins=None,
              start_at=None,
              parent=None,
              runtime_limit=None,
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
    start_at: If specified, flow will be started not immediately, but at a given
      time.
    parent: A FlowParent referencing the parent, or None for top-level flows.
    runtime_limit: Runtime limit as Duration for all ClientActions.
    **kwargs: If args or runner_args are not specified, we construct these
      protobufs from these keywords.
  Returns:
    the flow id of the new flow.

  Raises:
    ValueError: Unknown or invalid parameters were provided.
  """
  # Is the required flow a known flow?
  try:
    registry.FlowRegistry.FlowClassByName(flow_cls.__name__)
  except ValueError:
    GRR_FLOW_INVALID_FLOW_COUNT.Increment()
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
      creator=creator,
      output_plugins=output_plugins,
      original_flow=original_flow,
      flow_state="RUNNING")

  if parent is None:
    parent = FlowParent.FromRoot()

  if parent.is_hunt or parent.is_scheduled_flow:
    # When starting a flow from a hunt or ScheduledFlow, re-use the parent's id
    # to make it easy to find flows. For hunts, every client has a top-level
    # flow with the hunt's id.
    rdf_flow.flow_id = parent.id
  else:  # For new top-level and child flows, assign a random ID.
    rdf_flow.flow_id = RandomFlowId()

  # For better performance, only do conflicting IDs check for top-level flows.
  if not parent.is_flow:
    try:
      data_store.REL_DB.ReadFlowObject(client_id, rdf_flow.flow_id)
      raise CanNotStartFlowWithExistingIdError(client_id, rdf_flow.flow_id)
    except db.UnknownFlowError:
      pass

  if parent.is_flow:  # A flow is a nested flow.
    parent_rdf_flow = parent.flow_obj.rdf_flow
    rdf_flow.long_flow_id = "%s/%s" % (parent_rdf_flow.long_flow_id,
                                       rdf_flow.flow_id)
    rdf_flow.parent_flow_id = parent_rdf_flow.flow_id
    rdf_flow.parent_hunt_id = parent_rdf_flow.parent_hunt_id
    rdf_flow.parent_request_id = parent.flow_obj.GetCurrentOutboundId()
    if parent_rdf_flow.creator:
      rdf_flow.creator = parent_rdf_flow.creator
  elif parent.is_hunt:  # Root-level hunt-induced flow.
    rdf_flow.long_flow_id = "%s/%s" % (client_id, rdf_flow.flow_id)
    rdf_flow.parent_hunt_id = parent.id
  elif parent.is_root or parent.is_scheduled_flow:
    # A flow is a root-level non-hunt flow.
    rdf_flow.long_flow_id = "%s/%s" % (client_id, rdf_flow.flow_id)
  else:
    raise ValueError(f"Unknown flow parent type {parent}")

  if output_plugins:
    rdf_flow.output_plugins_states = GetOutputPluginStates(
        output_plugins, rdf_flow.long_flow_id)

  if network_bytes_limit is not None:
    rdf_flow.network_bytes_limit = network_bytes_limit
  if cpu_limit is not None:
    rdf_flow.cpu_limit = cpu_limit
  if runtime_limit is not None:
    rdf_flow.runtime_limit_us = runtime_limit

  logging.info(u"Starting %s(%s) on %s (%s)", rdf_flow.long_flow_id,
               rdf_flow.flow_class_name, client_id, start_at or "now")

  rdf_flow.current_state = "Start"

  flow_obj = flow_cls(rdf_flow)

  # Prevent a race condition, where a flow is scheduled twice, because one
  # worker inserts the row and another worker silently updates the existing row.
  allow_update = False

  if start_at is None:
    # Store an initial version of the flow straight away. This is needed so the
    # database doesn't raise consistency errors due to missing parent keys when
    # writing logs / errors / results which might happen in Start().
    try:
      data_store.REL_DB.WriteFlowObject(flow_obj.rdf_flow, allow_update=False)
    except db.FlowExistsError:
      raise CanNotStartFlowWithExistingIdError(client_id, rdf_flow.flow_id)

    allow_update = True

    try:
      # Just run the first state inline. NOTE: Running synchronously means
      # that this runs on the thread that starts the flow. The advantage is
      # that that Start method can raise any errors immediately.
      flow_obj.Start()

      # The flow does not need to actually remain running.
      if not flow_obj.outstanding_requests:
        flow_obj.RunStateMethod("End")
        # Additional check for the correct state in case the End method raised
        # and terminated the flow.
        if flow_obj.IsRunning():
          flow_obj.MarkDone()
    except Exception as e:  # pylint: disable=broad-except
      # We catch all exceptions that happen in Start() and mark the flow as
      # failed.
      msg = compatibility.NativeStr(e)
      if compatibility.PY2:
        msg = msg.decode("utf-8", "replace")

      flow_obj.Error(error_message=msg, backtrace=traceback.format_exc())

  else:
    flow_obj.CallState("Start", start_time=start_at)

  flow_obj.PersistState()

  try:
    data_store.REL_DB.WriteFlowObject(
        flow_obj.rdf_flow, allow_update=allow_update)
  except db.FlowExistsError:
    raise CanNotStartFlowWithExistingIdError(client_id, rdf_flow.flow_id)

  if parent.is_flow:
    # We can optimize here and not write requests/responses to the database
    # since we have to do this for the parent flow at some point anyways.
    parent.flow_obj.MergeQueuedMessages(flow_obj)
  else:
    flow_obj.FlushQueuedMessages()

  return rdf_flow.flow_id


def ScheduleFlow(client_id: str, creator: str, flow_name, flow_args,
                 runner_args) -> rdf_flow_objects.ScheduledFlow:
  """Schedules a Flow on the client, to be started upon approval grant."""

  scheduled_flow = rdf_flow_objects.ScheduledFlow(
      client_id=client_id,
      creator=creator,
      scheduled_flow_id=RandomFlowId(),
      flow_name=flow_name,
      flow_args=flow_args,
      runner_args=runner_args,
      create_time=rdfvalue.RDFDatetime.Now())

  data_store.REL_DB.WriteScheduledFlow(scheduled_flow)

  return scheduled_flow


def UnscheduleFlow(client_id: str, creator: str,
                   scheduled_flow_id: str) -> None:
  """Unschedules and deletes a previously scheduled flow."""
  data_store.REL_DB.DeleteScheduledFlow(
      client_id=client_id, creator=creator, scheduled_flow_id=scheduled_flow_id)


def ListScheduledFlows(
    client_id: str, creator: str) -> Sequence[rdf_flow_objects.ScheduledFlow]:
  """Lists all scheduled flows of a user on a client."""
  return data_store.REL_DB.ListScheduledFlows(
      client_id=client_id, creator=creator)


def StartScheduledFlows(client_id: str, creator: str) -> None:
  """Starts all scheduled flows of a user on a client.

  This function delegates to StartFlow() to start the actual flow. If an error
  occurs during StartFlow(), the ScheduledFlow is not deleted, but it is
  updated by writing the `error` field to the database. The exception is NOT
  re-raised and the next ScheduledFlow is attempted to be started.

  Args:
    client_id: The ID of the client of the ScheduledFlows.
    creator: The username of the user who created the ScheduledFlows.

  Raises:
    UnknownClientError: if no client with client_id exists.
    UnknownGRRUserError: if creator does not exist as user.
  """
  # Validate existence of Client and User. Data races are not an issue - no
  # flows get started in any case.
  data_store.REL_DB.ReadClientMetadata(client_id)
  data_store.REL_DB.ReadGRRUser(creator)

  scheduled_flows = ListScheduledFlows(client_id, creator)
  for sf in scheduled_flows:
    try:
      flow_id = _StartScheduledFlow(sf)
      logging.info("Started Flow %s/%s from ScheduledFlow %s", client_id,
                   flow_id, sf.scheduled_flow_id)
    except Exception:  # pylint: disable=broad-except
      logging.exception("Cannot start ScheduledFlow %s %s/%s from %s",
                        sf.flow_name, sf.client_id, sf.scheduled_flow_id,
                        sf.creator)


def _StartScheduledFlow(scheduled_flow: rdf_flow_objects.ScheduledFlow) -> str:
  """Starts a Flow from a ScheduledFlow and deletes the ScheduledFlow."""
  sf = scheduled_flow
  ra = scheduled_flow.runner_args

  try:
    flow_id = StartFlow(
        client_id=sf.client_id,
        creator=sf.creator,
        flow_args=sf.flow_args,
        flow_cls=registry.FlowRegistry.FlowClassByName(sf.flow_name),
        output_plugins=ra.output_plugins,
        start_at=rdfvalue.RDFDatetime.Now(),
        parent=FlowParent.FromScheduledFlowID(sf.scheduled_flow_id),
        cpu_limit=ra.cpu_limit,
        network_bytes_limit=ra.network_bytes_limit,
        # runtime_limit is missing in FlowRunnerArgs.
    )
  except Exception as e:
    scheduled_flow.error = str(e)
    data_store.REL_DB.WriteScheduledFlow(scheduled_flow)
    raise

  data_store.REL_DB.DeleteScheduledFlow(
      client_id=scheduled_flow.client_id,
      creator=scheduled_flow.creator,
      scheduled_flow_id=scheduled_flow.scheduled_flow_id)

  return flow_id
