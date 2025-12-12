#!/usr/bin/env python
"""REL_DB implementation of models_hunts."""

from typing import Optional

from grr_response_core.lib import rdfvalue
from grr_response_core.lib import registry
from grr_response_core.lib.rdfvalues import structs as rdf_structs
from grr_response_core.lib.util import cache
from grr_response_core.lib.util import precondition
from grr_response_proto import hunts_pb2
from grr_response_proto import objects_pb2
from grr_response_server import access_control
from grr_response_server import data_store
from grr_response_server import flow
from grr_response_server import foreman_rules
from grr_response_server import mig_foreman_rules
from grr_response_server import notification
from grr_response_server import output_plugin_registry
from grr_response_server.models import hunts as models_hunts
from grr_response_server.rdfvalues import hunt_objects as rdf_hunt_objects
from grr_response_server.rdfvalues import mig_flow_runner
from grr_response_server.rdfvalues import mig_hunt_objects
from grr_response_server.rdfvalues import mig_output_plugin


MIN_CLIENTS_FOR_AVERAGE_THRESHOLDS = 1000

# fmt: off

CANCELLED_BY_USER = "Cancelled by user"

# /grr/server/grr_response_server/gui/api_plugins/hunt.py)
# fmt: on


class Error(Exception):
  pass


class UnknownHuntTypeError(Error):
  pass


class OnlyPausedHuntCanBeModifiedError(Error):

  def __init__(self, hunt_obj):
    super().__init__(
        f"Hunt {hunt_obj.hunt_id} can't be modified since it's in state"
        f" {hunt_obj.hunt_state}."
    )


class OnlyPausedHuntCanBeStartedError(Error):

  def __init__(self, hunt_obj):
    super().__init__(
        f"Hunt {hunt_obj.hunt_id} can't be started since it's in state"
        f" {hunt_obj.hunt_state}."
    )


class OnlyStartedHuntCanBePausedError(Error):

  def __init__(self, hunt_obj):
    super().__init__(
        f"Hunt {hunt_obj.hunt_id} can't be paused since it's in state"
        f" {hunt_obj.hunt_state}."
    )


class OnlyStartedOrPausedHuntCanBeStoppedError(Error):

  def __init__(self, hunt_obj):
    super().__init__(
        f"Hunt {hunt_obj.hunt_id} can't be stopped since it's in state"
        f" {hunt_obj.hunt_state}."
    )


class CanStartAtMostOneFlowPerClientError(Error):

  def __init__(self, hunt_id, client_id):
    super().__init__(
        f"Variable hunt {hunt_id} has more than 1 flow for a client"
        f" {client_id}."
    )


class VariableHuntCanNotHaveClientRateError(Error):

  def __init__(self, hunt_id, client_rate):

    super().__init__(
        f"Variable hunt {hunt_id} has must have client_rate=0, instead it's"
        f" {client_rate}."
    )


def HuntIDFromURN(hunt_urn):
  return hunt_urn.Basename().replace("H:", "")


def HuntURNFromID(hunt_id):
  return rdfvalue.RDFURN(f"aff4:/hunts/H:{hunt_id}")


def StopHuntIfCrashLimitExceeded(hunt_id):
  """Stops the hunt if number of crashes exceeds the limit."""
  hunt_obj = data_store.REL_DB.ReadHuntObject(hunt_id)
  hunt_obj = mig_hunt_objects.ToRDFHunt(hunt_obj)

  # Do nothing if the hunt is already stopped.
  if hunt_obj.hunt_state == rdf_hunt_objects.Hunt.HuntState.STOPPED:
    return hunt_obj

  if hunt_obj.crash_limit:
    hunt_counters = data_store.REL_DB.ReadHuntCounters(hunt_id)
    if hunt_counters.num_crashed_clients >= hunt_obj.crash_limit:
      # Remove our rules from the forman and cancel all the started flows.
      # Hunt will be hard-stopped and it will be impossible to restart it.
      reason = (
          f"Hunt {hunt_obj.hunt_id} reached the crashes limit of"
          f" {hunt_obj.crash_limit} and was stopped."
      )
      hunt_state_reason = hunts_pb2.Hunt.HuntStateReason.TOTAL_CRASHES_EXCEEDED
      StopHunt(
          hunt_obj.hunt_id,
          hunt_state_reason=hunt_state_reason,
          reason_comment=reason,
      )

  return hunt_obj


_TIME_BETWEEN_STOP_CHECKS = rdfvalue.Duration.From(30, rdfvalue.SECONDS)


@cache.WithLimitedCallFrequency(_TIME_BETWEEN_STOP_CHECKS)
def StopHuntIfCPUOrNetworkLimitsExceeded(hunt_id):
  """Stops the hunt if average limites are exceeded."""
  hunt_obj = data_store.REL_DB.ReadHuntObject(hunt_id)
  hunt_obj = mig_hunt_objects.ToRDFHunt(hunt_obj)

  # Do nothing if the hunt is already stopped.
  if hunt_obj.hunt_state == rdf_hunt_objects.Hunt.HuntState.STOPPED:
    return hunt_obj

  hunt_counters = data_store.REL_DB.ReadHuntCounters(hunt_id)

  # Check global hunt network bytes limit first.
  if (
      hunt_obj.total_network_bytes_limit
      and hunt_counters.total_network_bytes_sent
      > hunt_obj.total_network_bytes_limit
  ):
    reason = (
        f"Hunt {hunt_obj.hunt_id} reached the total network bytes sent limit of"
        f" {hunt_obj.total_network_bytes_limit} and was stopped."
    )
    hunt_state_reason = hunts_pb2.Hunt.HuntStateReason.TOTAL_NETWORK_EXCEEDED
    StopHunt(
        hunt_obj.hunt_id,
        hunt_state_reason=hunt_state_reason,
        reason_comment=reason,
    )

  # Check that we have enough clients to apply average limits.
  if hunt_counters.num_clients < MIN_CLIENTS_FOR_AVERAGE_THRESHOLDS:
    return hunt_obj

  # Check average per-client results count limit.
  if hunt_obj.avg_results_per_client_limit:
    avg_results_per_client = (
        hunt_counters.num_results / hunt_counters.num_clients
    )
    if avg_results_per_client > hunt_obj.avg_results_per_client_limit:
      # Stop the hunt since we get too many results per client.
      reason = (
          f"Hunt {hunt_obj.hunt_id} reached the average results per client "
          f"limit of {hunt_obj.avg_results_per_client_limit} and was stopped."
      )
      hunt_state_reason = hunts_pb2.Hunt.HuntStateReason.AVG_RESULTS_EXCEEDED
      StopHunt(
          hunt_obj.hunt_id,
          hunt_state_reason=hunt_state_reason,
          reason_comment=reason,
      )

  # Check average per-client CPU seconds limit.
  if hunt_obj.avg_cpu_seconds_per_client_limit:
    avg_cpu_seconds_per_client = (
        hunt_counters.total_cpu_seconds / hunt_counters.num_clients
    )
    if avg_cpu_seconds_per_client > hunt_obj.avg_cpu_seconds_per_client_limit:
      # Stop the hunt since we use too many CPUs per client.
      reason = (
          f"Hunt {hunt_obj.hunt_id} reached the average CPU seconds per client"
          f" limit of {hunt_obj.avg_cpu_seconds_per_client_limit} and was"
          " stopped."
      )
      hunt_state_reason = hunts_pb2.Hunt.HuntStateReason.AVG_CPU_EXCEEDED
      StopHunt(
          hunt_obj.hunt_id,
          hunt_state_reason=hunt_state_reason,
          reason_comment=reason,
      )

  # Check average per-client network bytes limit.
  if hunt_obj.avg_network_bytes_per_client_limit:
    avg_network_bytes_per_client = (
        hunt_counters.total_network_bytes_sent / hunt_counters.num_clients
    )
    if (
        avg_network_bytes_per_client
        > hunt_obj.avg_network_bytes_per_client_limit
    ):
      # Stop the hunt since we use too many network bytes sent
      # per client.
      reason = (
          f"Hunt {hunt_obj.hunt_id} reached the average network bytes per"
          f" client limit of {hunt_obj.avg_network_bytes_per_client_limit} and"
          " was stopped."
      )
      hunt_state_reason = hunts_pb2.Hunt.HuntStateReason.AVG_NETWORK_EXCEEDED
      StopHunt(
          hunt_obj.hunt_id,
          hunt_state_reason=hunt_state_reason,
          reason_comment=reason,
      )

  return hunt_obj


def CompleteHuntIfExpirationTimeReached(hunt_id: str) -> rdf_hunt_objects.Hunt:
  """Marks the hunt as complete if it's past its expiry time."""
  # TODO(hanuszczak): This should not set the hunt state to `COMPLETED` but we
  # should have a separate `EXPIRED` state instead and set that.
  hunt_obj = data_store.REL_DB.ReadHuntObject(hunt_id)
  hunt_obj = mig_hunt_objects.ToRDFHunt(hunt_obj)
  if (
      hunt_obj.hunt_state
      not in [
          rdf_hunt_objects.Hunt.HuntState.STOPPED,
          rdf_hunt_objects.Hunt.HuntState.COMPLETED,
      ]
      and hunt_obj.expired
  ):
    StopHunt(
        hunt_obj.hunt_id,
        hunts_pb2.Hunt.HuntStateReason.DEADLINE_REACHED,
        reason_comment="Hunt completed.",
    )

    data_store.REL_DB.UpdateHuntObject(
        hunt_obj.hunt_id, hunt_state=hunts_pb2.Hunt.HuntState.COMPLETED
    )
    hunt_obj = data_store.REL_DB.ReadHuntObject(hunt_obj.hunt_id)
    hunt_obj = mig_hunt_objects.ToRDFHunt(hunt_obj)

  return hunt_obj


def CreateHunt(hunt_obj: hunts_pb2.Hunt):
  """Creates a hunt using a given hunt object."""
  data_store.REL_DB.WriteHuntObject(hunt_obj)

  if hunt_obj.output_plugins:
    proto_plugin_descriptors = []
    rdf_plugin_descriptors = []
    for idx, op in enumerate(hunt_obj.output_plugins):
      try:
        output_plugin_registry.GetPluginClassByName(op.plugin_name)
        proto_plugin_descriptors.append((idx, op))
      except KeyError:
        rdf_plugin_descriptors.append((idx, op))

    for _, desc in proto_plugin_descriptors:
      plugin_cls = output_plugin_registry.GetPluginClassByName(desc.plugin_name)
      if plugin_cls.args_type is not None:
        # `desc.args` is an instance of `any_pb2.Any`.
        pl_args = plugin_cls.args_type()
        pl_args.ParseFromString(desc.args.value)
      else:
        pl_args = None
      # Proto-based plugins are stateless, but we initialize them here to
      # validate their arguments.
      plugin_cls(source_urn=hunt_obj.hunt_id, args=pl_args)

    rdf_plugin_descriptors = [
        (idx, mig_output_plugin.ToRDFOutputPluginDescriptor(op))
        for idx, op in rdf_plugin_descriptors
    ]
    output_plugins_states = flow.GetOutputPluginStates(
        rdf_plugin_descriptors, source=f"hunts/{hunt_obj.hunt_id}"
    )
    output_plugins_states = [
        mig_flow_runner.ToProtoOutputPluginState(state)
        for state in output_plugins_states
    ]
    data_store.REL_DB.WriteHuntOutputPluginsStates(
        hunt_obj.hunt_id, output_plugins_states
    )


def CreateAndStartHunt(flow_name, flow_args, creator, **kwargs):
  """Creates and starts a new hunt."""

  # This interface takes a time when the hunt expires. However, the legacy hunt
  # starting interface took an rdfvalue.DurationSeconds object which was then
  # added to the current time to get the expiry. This check exists to make sure
  # we don't  confuse the two.
  if "duration" in kwargs:
    precondition.AssertType(kwargs["duration"], rdfvalue.Duration)

  hunt_args = rdf_hunt_objects.HuntArguments(
      hunt_type=rdf_hunt_objects.HuntArguments.HuntType.STANDARD,
      standard=rdf_hunt_objects.HuntArgumentsStandard(
          flow_name=flow_name,
          flow_args=rdf_structs.AnyValue.Pack(flow_args),
      ),
  )

  hunt_obj = rdf_hunt_objects.Hunt(
      creator=creator,
      args=hunt_args,
      create_time=rdfvalue.RDFDatetime.Now(),
      **kwargs,
  )
  hunt_obj = mig_hunt_objects.ToProtoHunt(hunt_obj)
  CreateHunt(hunt_obj)
  StartHunt(hunt_obj.hunt_id)

  return hunt_obj.hunt_id


def _ScheduleGenericHunt(hunt_obj: rdf_hunt_objects.Hunt):
  """Adds foreman rules for a generic hunt."""
  # TODO: Migrate foreman conditions to use relation expiration
  # durations instead of absolute timestamps.
  foreman_condition = foreman_rules.ForemanCondition(
      creation_time=rdfvalue.RDFDatetime.Now(),
      expiration_time=hunt_obj.init_start_time + hunt_obj.duration,
      description=f"Hunt {hunt_obj.hunt_id} {hunt_obj.args.hunt_type}",
      client_rule_set=hunt_obj.client_rule_set,
      hunt_id=hunt_obj.hunt_id,
  )

  # Make sure the rule makes sense.
  foreman_condition.Validate()

  proto_foreman_condition = mig_foreman_rules.ToProtoForemanCondition(
      foreman_condition
  )
  data_store.REL_DB.WriteForemanRule(proto_foreman_condition)


def StartHunt(hunt_id) -> rdf_hunt_objects.Hunt:
  """Starts a hunt with a given id."""

  hunt_obj = data_store.REL_DB.ReadHuntObject(hunt_id)
  hunt_obj = mig_hunt_objects.ToRDFHunt(hunt_obj)
  num_hunt_clients = data_store.REL_DB.CountHuntFlows(hunt_id)

  if hunt_obj.hunt_state != hunt_obj.HuntState.PAUSED:
    raise OnlyPausedHuntCanBeStartedError(hunt_obj)

  data_store.REL_DB.UpdateHuntObject(
      hunt_id,
      hunt_state=hunts_pb2.Hunt.HuntState.STARTED,
      start_time=rdfvalue.RDFDatetime.Now(),
      num_clients_at_start_time=num_hunt_clients,
  )
  hunt_obj = data_store.REL_DB.ReadHuntObject(hunt_id)
  hunt_obj = mig_hunt_objects.ToRDFHunt(hunt_obj)

  if hunt_obj.args.hunt_type == hunt_obj.args.HuntType.STANDARD:
    _ScheduleGenericHunt(hunt_obj)
  else:
    raise UnknownHuntTypeError(
        f"Invalid hunt type for hunt {hunt_id}: {hunt_obj.args.hunt_type}"
    )

  return hunt_obj


def PauseHunt(
    hunt_id,
    hunt_state_reason=None,
    reason=None,
) -> rdf_hunt_objects.Hunt:
  """Pauses a hunt with a given id."""

  hunt_obj = data_store.REL_DB.ReadHuntObject(hunt_id)
  hunt_obj = mig_hunt_objects.ToRDFHunt(hunt_obj)
  if hunt_obj.hunt_state != hunt_obj.HuntState.STARTED:
    raise OnlyStartedHuntCanBePausedError(hunt_obj)

  data_store.REL_DB.UpdateHuntObject(
      hunt_id,
      hunt_state=hunts_pb2.Hunt.HuntState.PAUSED,
      hunt_state_reason=hunt_state_reason,
      hunt_state_comment=reason,
  )
  data_store.REL_DB.RemoveForemanRule(hunt_id=hunt_obj.hunt_id)

  hunt_obj = data_store.REL_DB.ReadHuntObject(hunt_id)
  hunt_obj = mig_hunt_objects.ToRDFHunt(hunt_obj)
  return hunt_obj


def StopHunt(
    hunt_id: str,
    hunt_state_reason: Optional[
        hunts_pb2.Hunt.HuntStateReason.ValueType
    ] = None,
    reason_comment: Optional[str] = None,
) -> rdf_hunt_objects.Hunt:
  """Stops a hunt with a given id."""

  hunt_obj = data_store.REL_DB.ReadHuntObject(hunt_id)
  hunt_obj = mig_hunt_objects.ToRDFHunt(hunt_obj)
  if hunt_obj.hunt_state not in [
      hunt_obj.HuntState.STARTED,
      hunt_obj.HuntState.PAUSED,
  ]:
    raise OnlyStartedOrPausedHuntCanBeStoppedError(hunt_obj)

  data_store.REL_DB.UpdateHuntObject(
      hunt_id,
      hunt_state=hunts_pb2.Hunt.HuntState.STOPPED,
      hunt_state_reason=hunt_state_reason,
      hunt_state_comment=reason_comment,
  )
  data_store.REL_DB.RemoveForemanRule(hunt_id=hunt_obj.hunt_id)

  # TODO: Stop matching on string (comment).
  if (
      hunt_state_reason != hunts_pb2.Hunt.HuntStateReason.TRIGGERED_BY_USER
      and reason_comment is not None
      and reason_comment != CANCELLED_BY_USER
      and hunt_obj.creator not in access_control.SYSTEM_USERS
  ):
    notification.Notify(
        hunt_obj.creator,
        objects_pb2.UserNotification.Type.TYPE_HUNT_STOPPED,
        reason_comment,
        objects_pb2.ObjectReference(
            reference_type=objects_pb2.ObjectReference.Type.HUNT,
            hunt=objects_pb2.HuntReference(hunt_id=hunt_obj.hunt_id),
        ),
    )

  hunt_obj = data_store.REL_DB.ReadHuntObject(hunt_id)
  hunt_obj = mig_hunt_objects.ToRDFHunt(hunt_obj)
  return hunt_obj


def UpdateHunt(
    hunt_id,
    client_limit=None,
    client_rate=None,
    duration=None,
) -> rdf_hunt_objects.Hunt:
  """Updates a hunt (it must be paused to be updated)."""

  hunt_obj = data_store.REL_DB.ReadHuntObject(hunt_id)
  hunt_obj = mig_hunt_objects.ToRDFHunt(hunt_obj)
  if hunt_obj.hunt_state != hunt_obj.HuntState.PAUSED:
    raise OnlyPausedHuntCanBeModifiedError(hunt_obj)

  data_store.REL_DB.UpdateHuntObject(
      hunt_id,
      client_limit=client_limit,
      client_rate=client_rate,
      duration=duration,
  )
  hunt_obj = data_store.REL_DB.ReadHuntObject(hunt_id)
  hunt_obj = mig_hunt_objects.ToRDFHunt(hunt_obj)
  return hunt_obj


_TIME_BETWEEN_PAUSE_CHECKS = rdfvalue.Duration.From(5, rdfvalue.SECONDS)


@cache.WithLimitedCallFrequency(_TIME_BETWEEN_PAUSE_CHECKS)
def _GetNumClients(hunt_id):
  return data_store.REL_DB.CountHuntFlows(hunt_id)


def StartHuntFlowOnClient(client_id, hunt_id):
  """Starts a flow corresponding to a given hunt on a given client."""

  hunt_obj = data_store.REL_DB.ReadHuntObject(hunt_id)

  # There may be a little race between foreman rules being removed and
  # foreman scheduling a client on an (already) paused hunt. Making sure
  # we don't lose clients in such a race by accepting clients for paused
  # hunts.
  if not models_hunts.IsHuntSuitableForFlowProcessing(hunt_obj.hunt_state):
    return

  hunt_obj = mig_hunt_objects.ToRDFHunt(hunt_obj)
  if hunt_obj.args.hunt_type == hunt_obj.args.HuntType.STANDARD:
    hunt_args = hunt_obj.args.standard

    if hunt_obj.client_rate > 0:
      # Given that we use caching in _GetNumClients and hunt_obj may be updated
      # in another process, we have to account for cases where num_clients_diff
      # may go below 0.
      num_clients_diff = max(
          0,
          _GetNumClients(hunt_obj.hunt_id) - hunt_obj.num_clients_at_start_time,
      )
      next_client_due_msecs = int(
          num_clients_diff / hunt_obj.client_rate * 60e6
      )

      start_at = rdfvalue.RDFDatetime.FromMicrosecondsSinceEpoch(
          hunt_obj.last_start_time.AsMicrosecondsSinceEpoch()
          + next_client_due_msecs
      )
    else:
      start_at = None

    # TODO(user): remove client_rate support when AFF4 is gone.
    # In REL_DB always work as if client rate is 0.

    flow_cls = registry.FlowRegistry.FlowClassByName(hunt_args.flow_name)
    if hunt_args.HasField("flow_args"):
      flow_args = hunt_args.flow_args.Unpack(flow_cls.args_type)
    else:
      flow_args = None

    flow.StartFlow(
        client_id=client_id,
        creator=hunt_obj.creator,
        cpu_limit=hunt_obj.per_client_cpu_limit,
        network_bytes_limit=hunt_obj.per_client_network_bytes_limit,
        flow_cls=flow_cls,
        flow_args=flow_args,
        start_at=start_at,
        output_plugins=hunt_obj.output_plugins,
        parent=flow.FlowParent.FromHuntID(hunt_id),
    )

    if hunt_obj.client_limit:
      if _GetNumClients(hunt_obj.hunt_id) >= hunt_obj.client_limit:
        try:
          PauseHunt(
              hunt_id,
              hunt_state_reason=rdf_hunt_objects.Hunt.HuntStateReason.TOTAL_CLIENTS_EXCEEDED,
          )
        except OnlyStartedHuntCanBePausedError:
          pass

  else:
    raise UnknownHuntTypeError(
        f"Can't determine hunt type when starting hunt {client_id} on client"
        f" {hunt_id}."
    )
