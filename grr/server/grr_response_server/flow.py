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

from google.protobuf import any_pb2
from google.protobuf import message as pb_message
from grr_response_core.lib import rdfvalue
from grr_response_core.lib import registry
from grr_response_core.lib.util import random
from grr_response_core.stats import metrics
from grr_response_proto import flows_pb2
from grr_response_proto import objects_pb2
from grr_response_proto import output_plugin_pb2
from grr_response_server import data_store
from grr_response_server import output_plugin_registry
from grr_response_server.databases import db
from grr_response_server.rdfvalues import flow_objects as rdf_flow_objects


GRR_FLOW_INVALID_FLOW_COUNT = metrics.Counter("grr_flow_invalid_flow_count")


class Error(Exception):
  """Base class for this package's exceptions."""


class CanNotStartFlowWithExistingIdError(Error):
  """Raises by StartFlow when trying to start a flow with an existing id."""

  def __init__(self, client_id, flow_id):
    message = f"Flow {flow_id} already exists on the client {client_id}."
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

  def __init__(
      self,
      parent_type: _ParentType,
      parent_id: Optional[str] = None,
      parent_flow_obj=None,
  ):
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
    return cls(_ParentType.FLOW, flow_obj.flow_id, flow_obj)

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


def StartFlow(
    client_id: Optional[str] = None,
    cpu_limit: Optional[int] = None,
    creator: Optional[str] = None,
    proto_flow_args: Optional[pb_message.Message] = None,
    flow_cls=None,
    network_bytes_limit: Optional[int] = None,
    original_flow: Optional[objects_pb2.FlowReference] = None,
    proto_output_plugins: Optional[
        Sequence[output_plugin_pb2.OutputPluginDescriptor]
    ] = None,
    # We use a timestamp in the past as a default value here to, by default,
    # start the flow on the worker immediately. Instead of using `None`, which
    # would schedule the flow for execution immediately in the current binary
    # (this code can be executed in the AdminUI or Frontend too). Using a
    # value here forces the flow to be schedule for execution, which only the
    # worker picks up.
    start_at: Optional[rdfvalue.RDFDatetime] = rdfvalue.RDFDatetime(0),
    parent: Optional[FlowParent] = None,
    runtime_limit: Optional[rdfvalue.Duration] = None,
    disable_rrg_support: bool = False,
) -> str:
  """The main factory function for creating and executing a new flow.

  Args:
    client_id: ID of the client this flow should run on.
    cpu_limit: CPU limit in seconds for this flow.
    creator: Username that requested this flow.
    proto_flow_args: An arg protocol buffer which is an instance of the required
      flow's args_type class attribute.
    flow_cls: Class of the flow that should be started.
    network_bytes_limit: Limit on the network traffic this flow can generated.
    original_flow: A FlowReference object in case this flow was copied from
      another flow.
    proto_output_plugins: Sequence of OutputPluginDescriptor objects indicating
      what output plugins should be used for this flow.
    start_at: If specified, flow will be started not immediately, but at a given
      time.
    parent: A FlowParent referencing the parent, or None for top-level flows.
    runtime_limit: Runtime limit as Duration for all ClientActions.
    disable_rrg_support: Whether to completely disable usage of RRG actions.

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

  # In some cases, the caller will pass an instance of `EmptyFlowArgs` instead
  # of `None` to indicate "no arguments". To avoid the type mismatch error, we
  # also explicitly instantiate the proto_args_type when it's EmptyFlowArgs.
  if not proto_flow_args or isinstance(
      proto_flow_args, flows_pb2.EmptyFlowArgs
  ):
    proto_flow_args = flow_cls.proto_args_type()

  if not isinstance(proto_flow_args, flow_cls.proto_args_type):
    raise TypeError(
        f"Flow args must be of type {flow_cls.proto_args_type}, got"
        f" {type(proto_flow_args)} with contents: {proto_flow_args!r}."
    )

  # Check that the flow args are valid.
  flow_cls.ValidateArgs(proto_flow_args)

  proto_flow = flows_pb2.Flow(
      client_id=client_id,
      flow_class_name=flow_cls.__name__,
      creator=creator,
      flow_state=flows_pb2.Flow.FlowState.RUNNING,
      disable_rrg_support=disable_rrg_support,
  )
  proto_flow.args.Pack(proto_flow_args)

  if original_flow:
    proto_flow.original_flow.CopyFrom(original_flow)

  if parent is None:
    parent = FlowParent.FromRoot()

  if parent.is_hunt or parent.is_scheduled_flow:
    # When starting a flow from a hunt or ScheduledFlow, re-use the parent's id
    # to make it easy to find flows. For hunts, every client has a top-level
    # flow with the hunt's id.
    proto_flow.flow_id = parent.id
  else:  # For new top-level and child flows, assign a random ID.
    proto_flow.flow_id = RandomFlowId()

  # For better performance, only do conflicting IDs check for top-level flows.
  if not parent.is_flow:
    try:
      data_store.REL_DB.ReadFlowObject(client_id, proto_flow.flow_id)
      raise CanNotStartFlowWithExistingIdError(client_id, proto_flow.flow_id)
    except db.UnknownFlowError:
      pass

  if parent.is_flow:  # Nested flow.
    parent_flow = parent.flow_obj
    proto_flow.long_flow_id = "%s/%s" % (
        parent_flow.long_flow_id,
        proto_flow.flow_id,
    )
    proto_flow.parent_flow_id = parent_flow.flow_id
    proto_flow.parent_hunt_id = parent_flow.parent_hunt_id
    proto_flow.parent_request_id = parent.flow_obj.GetCurrentOutboundId()
    if parent_flow.creator:
      proto_flow.creator = parent_flow.creator
  elif parent.is_hunt:  # Root-level hunt-induced flow.
    proto_flow.long_flow_id = "%s/%s" % (client_id, proto_flow.flow_id)
    proto_flow.parent_hunt_id = parent.id
  elif parent.is_root or parent.is_scheduled_flow:
    # A flow is a root-level non-hunt flow.
    proto_flow.long_flow_id = "%s/%s" % (client_id, proto_flow.flow_id)
  else:
    raise ValueError(f"Unknown flow parent type {parent}")

  if proto_output_plugins:
    proto_flow.output_plugins.extend(proto_output_plugins)

    for op in proto_output_plugins:
      try:
        plugin_cls = output_plugin_registry.GetPluginClassByName(op.plugin_name)
      except KeyError as exc:
        raise ValueError(f"Unknown plugin {op.plugin_name}") from exc

      if plugin_cls.args_type is not None:
        pl_args = plugin_cls.args_type()
        pl_args.ParseFromString(op.args.value)
      else:
        pl_args = None

      # Proto-based plugins are stateless, but we initialize them here to
      # validate their arguments.
      plugin_cls(source_urn=proto_flow.long_flow_id, args=pl_args)

  if network_bytes_limit is not None:
    proto_flow.network_bytes_limit = network_bytes_limit
  if cpu_limit is not None:
    proto_flow.cpu_limit = cpu_limit
  if runtime_limit is not None:
    proto_flow.runtime_limit_us = runtime_limit.SerializeToWireFormat()

  logging.info(
      "Starting %s(%s) on %s (%s)",
      proto_flow.long_flow_id,
      proto_flow.flow_class_name,
      client_id,
      start_at or "now",
  )

  proto_flow.current_state = "Start"

  flow_obj = flow_cls(proto_flow=proto_flow)

  # Prevent a race condition, where a flow is scheduled twice, because one
  # worker inserts the row and another worker silently updates the existing row.
  allow_update = False

  if start_at is None:
    # Store an initial version of the flow straight away. This is needed so the
    # database doesn't raise consistency errors due to missing parent keys when
    # writing logs / errors / results which might happen in Start().
    try:
      # Avoid relying on FlowBase to keep the reference to the proto_flow.
      # Just retrieve the object and write it to the DB.
      proto_flow = flow_obj.proto_flow_object
      data_store.REL_DB.WriteFlowObject(proto_flow, allow_update=False)
    except db.FlowExistsError:
      raise CanNotStartFlowWithExistingIdError(
          client_id, proto_flow.flow_id
      ) from None

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
      msg = str(e)

      flow_obj.Error(error_message=msg, backtrace=traceback.format_exc())

  else:
    flow_obj.CallStateProto("Start", start_time=start_at)

  flow_obj.PersistState()

  try:
    # Avoid relying on FlowBase to keep the reference to the proto_flow.
    # Just retrieve the object and write it to the DB.
    proto_flow = flow_obj.proto_flow_object
    data_store.REL_DB.WriteFlowObject(proto_flow, allow_update=allow_update)
  except db.FlowExistsError:
    raise CanNotStartFlowWithExistingIdError(
        client_id, proto_flow.flow_id
    ) from None

  if parent.is_flow:
    # We can optimize here and not write requests/responses to the database
    # since we have to do this for the parent flow at some point anyways.
    parent.flow_obj.MergeQueuedMessages(flow_obj)
  else:
    flow_obj.FlushQueuedMessages()

  return proto_flow.flow_id


def ScheduleFlow(
    client_id: str,
    creator: str,
    flow_name: str,
    flow_args: any_pb2.Any,
    runner_args: flows_pb2.FlowRunnerArgs,
) -> flows_pb2.ScheduledFlow:
  """Schedules a Flow on the client, to be started upon approval grant."""
  scheduled_flow = flows_pb2.ScheduledFlow()
  scheduled_flow.client_id = client_id
  scheduled_flow.creator = creator
  scheduled_flow.scheduled_flow_id = RandomFlowId()
  scheduled_flow.flow_name = flow_name
  scheduled_flow.flow_args.CopyFrom(flow_args)
  scheduled_flow.runner_args.CopyFrom(runner_args)
  scheduled_flow.create_time = int(rdfvalue.RDFDatetime.Now())

  data_store.REL_DB.WriteScheduledFlow(scheduled_flow)
  return scheduled_flow


def UnscheduleFlow(
    client_id: str,
    creator: str,
    scheduled_flow_id: str,
) -> None:
  """Unschedules and deletes a previously scheduled flow."""
  data_store.REL_DB.DeleteScheduledFlow(
      client_id=client_id, creator=creator, scheduled_flow_id=scheduled_flow_id
  )


def ListScheduledFlows(
    client_id: str,
    creator: str,
) -> Sequence[rdf_flow_objects.ScheduledFlow]:
  """Lists all scheduled flows of a user on a client."""
  return data_store.REL_DB.ListScheduledFlows(
      client_id=client_id, creator=creator
  )


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
      logging.info(
          "Started Flow %s/%s from ScheduledFlow %s",
          client_id,
          flow_id,
          sf.scheduled_flow_id,
      )
    except Exception:  # pylint: disable=broad-except
      logging.exception(
          "Cannot start ScheduledFlow %s %s/%s from %s",
          sf.flow_name,
          sf.client_id,
          sf.scheduled_flow_id,
          sf.creator,
      )


def _StartScheduledFlow(scheduled_flow: flows_pb2.ScheduledFlow) -> str:
  """Starts a Flow from a ScheduledFlow and deletes the ScheduledFlow."""
  flow_cls = registry.FlowRegistry.FlowClassByName(scheduled_flow.flow_name)
  unpacked_args = flow_cls.proto_args_type()
  unpacked_args.ParseFromString(scheduled_flow.flow_args.value)

  try:
    flow_id = StartFlow(
        client_id=scheduled_flow.client_id,
        creator=scheduled_flow.creator,
        proto_flow_args=unpacked_args,
        flow_cls=flow_cls,
        proto_output_plugins=scheduled_flow.runner_args.output_plugins,
        start_at=rdfvalue.RDFDatetime.Now(),
        parent=FlowParent.FromScheduledFlowID(scheduled_flow.scheduled_flow_id),
        cpu_limit=scheduled_flow.runner_args.cpu_limit,
        network_bytes_limit=scheduled_flow.runner_args.network_bytes_limit,
        # runtime_limit is missing in FlowRunnerArgs.
    )
  except Exception as e:
    scheduled_flow.error = str(e)
    data_store.REL_DB.WriteScheduledFlow(scheduled_flow)
    raise

  data_store.REL_DB.DeleteScheduledFlow(
      client_id=scheduled_flow.client_id,
      creator=scheduled_flow.creator,
      scheduled_flow_id=scheduled_flow.scheduled_flow_id,
  )

  return flow_id
