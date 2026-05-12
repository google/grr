#!/usr/bin/env python
"""REL_DB implementation of models_hunts."""

from typing import Optional

from grr_response_core.lib import rdfvalue
from grr_response_core.lib import registry
from grr_response_core.lib.util import cache
from grr_response_proto import hunts_pb2
from grr_response_proto import jobs_pb2
from grr_response_proto import objects_pb2
from grr_response_server import access_control
from grr_response_server import data_store
from grr_response_server import flow
from grr_response_server import foreman_rules
from grr_response_server import notification
from grr_response_server import output_plugin_registry
from grr_response_server.models import hunts as models_hunts


MIN_CLIENTS_FOR_AVERAGE_THRESHOLDS = 1000

# fmt: off

CANCELLED_BY_USER = "Cancelled by user"

# /grr/server/grr_response_server/gui/api_plugins/hunt.py)
# fmt: on


class Error(Exception):
  pass


class UnknownHuntTypeError(Error):
  pass


class UnknownOutputPluginError(Error):
  """Raised when an output plugin is not known."""


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


def StopHuntIfCrashLimitExceeded(hunt_id: str) -> hunts_pb2.Hunt:
  """Stops the hunt if number of crashes exceeds the limit."""
  hunt_obj = data_store.REL_DB.ReadHuntObject(hunt_id)

  # Do nothing if the hunt is already stopped.
  if hunt_obj.hunt_state == hunts_pb2.Hunt.HuntState.STOPPED:
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
def StopHuntIfCPUOrNetworkLimitsExceeded(hunt_id: str) -> hunts_pb2.Hunt:
  """Stops the hunt if average limites are exceeded."""
  hunt_obj = data_store.REL_DB.ReadHuntObject(hunt_id)

  # Do nothing if the hunt is already stopped.
  if hunt_obj.hunt_state == hunts_pb2.Hunt.HuntState.STOPPED:
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


def GetExpiryTimeMicros(
    hunt: hunts_pb2.Hunt,
) -> Optional[int]:
  """Returns the expiry time of the hunt in microseconds since epoch."""
  # `init_start_time` is set in RDFDatetime (microseconds),
  # but `duration` is set in DurationSeconds (seconds).
  # We return something equivalent to
  # RDFDatetime.AsMicrosecondsSinceEpoch().
  if hunt.init_start_time:
    return hunt.init_start_time + hunt.duration * 1_000_000

  return None


def IsExpired(hunt: hunts_pb2.Hunt) -> bool:
  """Returns True if the hunt has expired."""
  expiry_time = GetExpiryTimeMicros(hunt)
  if expiry_time is None:
    return False

  now = rdfvalue.RDFDatetime.Now().AsMicrosecondsSinceEpoch()
  return bool(expiry_time < now)


def CompleteHuntIfExpirationTimeReached(hunt_id: str) -> hunts_pb2.Hunt:
  """Marks the hunt as complete if it's past its expiry time."""
  # TODO(hanuszczak): This should not set the hunt state to `COMPLETED` but we
  # should have a separate `EXPIRED` state instead and set that.
  hunt_obj = data_store.REL_DB.ReadHuntObject(hunt_id)

  if hunt_obj.hunt_state not in [
      hunts_pb2.Hunt.HuntState.STOPPED,
      hunts_pb2.Hunt.HuntState.COMPLETED,
  ] and IsExpired(hunt_obj):
    try:
      StopHunt(
          hunt_obj.hunt_id,
          hunts_pb2.Hunt.HuntStateReason.DEADLINE_REACHED,
          reason_comment="Hunt completed.",
      )
    except OnlyStartedOrPausedHuntCanBeStoppedError:
      # This is fine: between our check for the hunt state and the one inside
      # `StopHunt` another thread or process might have already stopped it.
      #
      # We still do the state check here (rather than applying EAFP [1]) despite
      # catching the exception to avoid potential unnecessary database call in-
      # side `StopHunt`.
      #
      # [1]: https://docs.python.org/3/glossary.html#term-EAFP
      pass

    data_store.REL_DB.UpdateHuntObject(
        hunt_obj.hunt_id, hunt_state=hunts_pb2.Hunt.HuntState.COMPLETED
    )
    hunt_obj = data_store.REL_DB.ReadHuntObject(hunt_obj.hunt_id)

  return hunt_obj


def CreateHunt(hunt_obj: hunts_pb2.Hunt):
  """Creates a hunt using a given hunt object."""
  if hunt_obj.output_plugins:
    proto_plugin_descriptors = []
    for desc in hunt_obj.output_plugins:
      try:
        output_plugin_registry.GetPluginClassByName(desc.plugin_name)
        proto_plugin_descriptors.append(desc)
      except KeyError as exc:
        raise UnknownOutputPluginError(
            f"Output plugin {desc.plugin_name} is not known."
        ) from exc

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

  # TODO - Consider validating the client rule set here.

  # Write to the DB only after the validation passed.
  data_store.REL_DB.WriteHuntObject(hunt_obj)


def CreateAndStartHunt(hunt_obj: hunts_pb2.Hunt):
  """Creates and starts a new hunt."""
  if not hunt_obj.hunt_id:
    hunt_obj.hunt_id = models_hunts.RandomHuntId()

  if not hunt_obj.creator:
    raise ValueError("Hunt creator must be set.")

  if hunt_obj.args.hunt_type == hunts_pb2.HuntArguments.HuntType.VARIABLE:
    raise ValueError("Variable hunts are no longer supported.")

  if not hunt_obj.args.standard.flow_name:
    raise ValueError("Hunt flow name must be set.")

  if not hunt_obj.create_time:
    hunt_obj.create_time = rdfvalue.RDFDatetime.Now().AsMicrosecondsSinceEpoch()

  CreateHunt(hunt_obj)
  StartHunt(hunt_obj.hunt_id)

  return hunt_obj.hunt_id


def _ScheduleGenericHunt(hunt_obj: hunts_pb2.Hunt):
  """Adds foreman rules for a generic hunt."""
  # TODO - Migrate foreman conditions to use relation expiration
  # durations instead of absolute timestamps.
  foreman_condition = jobs_pb2.ForemanCondition(
      creation_time=rdfvalue.RDFDatetime.Now().AsMicrosecondsSinceEpoch(),
      expiration_time=GetExpiryTimeMicros(hunt_obj),
      description=f"Hunt {hunt_obj.hunt_id} {hunt_obj.args.hunt_type}",
      client_rule_set=hunt_obj.client_rule_set,
      hunt_id=hunt_obj.hunt_id,
  )

  # Make sure the rule makes sense.
  foreman_rules.ValidateForemanCondition(foreman_condition)

  data_store.REL_DB.WriteForemanRule(foreman_condition)


def StartHunt(hunt_id: str) -> hunts_pb2.Hunt:
  """Starts a hunt with a given id."""

  hunt_obj = data_store.REL_DB.ReadHuntObject(hunt_id)
  num_hunt_clients = data_store.REL_DB.CountHuntFlows(hunt_id)

  if hunt_obj.hunt_state != hunts_pb2.Hunt.HuntState.PAUSED:
    raise OnlyPausedHuntCanBeStartedError(hunt_obj)

  data_store.REL_DB.UpdateHuntObject(
      hunt_id,
      hunt_state=hunts_pb2.Hunt.HuntState.STARTED,
      start_time=rdfvalue.RDFDatetime.Now(),
      num_clients_at_start_time=num_hunt_clients,
  )
  hunt_obj = data_store.REL_DB.ReadHuntObject(hunt_id)

  if hunt_obj.args.hunt_type == hunts_pb2.HuntArguments.HuntType.STANDARD:
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
) -> hunts_pb2.Hunt:
  """Pauses a hunt with a given id."""

  hunt_obj = data_store.REL_DB.ReadHuntObject(hunt_id)
  if hunt_obj.hunt_state != hunts_pb2.Hunt.HuntState.STARTED:
    raise OnlyStartedHuntCanBePausedError(hunt_obj)

  data_store.REL_DB.UpdateHuntObject(
      hunt_id,
      hunt_state=hunts_pb2.Hunt.HuntState.PAUSED,
      hunt_state_reason=hunt_state_reason,
      hunt_state_comment=reason,
  )
  data_store.REL_DB.RemoveForemanRule(hunt_id=hunt_obj.hunt_id)

  hunt_obj = data_store.REL_DB.ReadHuntObject(hunt_id)
  return hunt_obj


def StopHunt(
    hunt_id: str,
    hunt_state_reason: Optional[
        hunts_pb2.Hunt.HuntStateReason.ValueType
    ] = None,
    reason_comment: Optional[str] = None,
) -> hunts_pb2.Hunt:
  """Stops a hunt with a given id."""

  hunt_obj = data_store.REL_DB.ReadHuntObject(hunt_id)
  if hunt_obj.hunt_state not in [
      hunts_pb2.Hunt.HuntState.STARTED,
      hunts_pb2.Hunt.HuntState.PAUSED,
  ]:
    raise OnlyStartedOrPausedHuntCanBeStoppedError(hunt_obj)

  data_store.REL_DB.UpdateHuntObject(
      hunt_id,
      hunt_state=hunts_pb2.Hunt.HuntState.STOPPED,
      hunt_state_reason=hunt_state_reason,
      hunt_state_comment=reason_comment,
  )
  data_store.REL_DB.RemoveForemanRule(hunt_id=hunt_obj.hunt_id)

  # TODO - Stop matching on string (comment).
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
  return hunt_obj


def UpdateHunt(
    hunt_id,
    client_limit=None,
    client_rate=None,
    duration=None,
) -> hunts_pb2.Hunt:
  """Updates a hunt (it must be paused to be updated)."""

  hunt_obj = data_store.REL_DB.ReadHuntObject(hunt_id)
  if hunt_obj.hunt_state != hunts_pb2.Hunt.HuntState.PAUSED:
    raise OnlyPausedHuntCanBeModifiedError(hunt_obj)

  data_store.REL_DB.UpdateHuntObject(
      hunt_id,
      client_limit=client_limit,
      client_rate=client_rate,
      duration=duration,
  )
  hunt_obj = data_store.REL_DB.ReadHuntObject(hunt_id)
  return hunt_obj


_TIME_BETWEEN_PAUSE_CHECKS = rdfvalue.Duration.From(5, rdfvalue.SECONDS)


@cache.WithLimitedCallFrequency(_TIME_BETWEEN_PAUSE_CHECKS)
def _GetNumClients(hunt_id):
  return data_store.REL_DB.CountHuntFlows(hunt_id)


def StartHuntFlowOnClient(client_id: str, hunt_id: str) -> None:
  """Starts a flow corresponding to a given hunt on a given client."""

  hunt_obj: hunts_pb2.Hunt = data_store.REL_DB.ReadHuntObject(hunt_id)

  # There may be a little race between foreman rules being removed and
  # foreman scheduling a client on an (already) paused hunt. Making sure
  # we don't lose clients in such a race by accepting clients for paused
  # hunts.
  if not models_hunts.IsHuntSuitableForFlowProcessing(hunt_obj.hunt_state):
    return

  if hunt_obj.args.hunt_type != hunts_pb2.HuntArguments.HuntType.STANDARD:
    raise UnknownHuntTypeError(
        f"Can't determine hunt type when starting hunt {client_id} on client"
        f" {hunt_id}."
    )

  if hunt_obj.client_rate > 0:
    # Given that we use caching in _GetNumClients and hunt_obj may be updated
    # in another process, we have to account for cases where num_clients_diff
    # may go below 0.
    num_clients_diff = max(
        0,
        _GetNumClients(hunt_obj.hunt_id) - hunt_obj.num_clients_at_start_time,
    )
    next_client_due_msecs = int(num_clients_diff / hunt_obj.client_rate * 60e6)

    start_at = rdfvalue.RDFDatetime.FromMicrosecondsSinceEpoch(
        hunt_obj.last_start_time + next_client_due_msecs
    )
  else:
    start_at = None

  hunt_args = hunt_obj.args.standard

  flow_cls = registry.FlowRegistry.FlowClassByName(hunt_args.flow_name)
  if hunt_obj.args.standard.HasField("flow_args"):
    flow_args = flow_cls.proto_args_type()
    hunt_obj.args.standard.flow_args.Unpack(flow_args)
  else:
    flow_args = None

  flow.StartFlow(
      client_id=client_id,
      creator=hunt_obj.creator,
      cpu_limit=hunt_obj.per_client_cpu_limit,
      network_bytes_limit=hunt_obj.per_client_network_bytes_limit,
      flow_cls=flow_cls,
      proto_flow_args=flow_args,
      start_at=start_at,
      proto_output_plugins=hunt_obj.output_plugins,
      parent=flow.FlowParent.FromHuntID(hunt_id),
  )

  if hunt_obj.client_limit:
    if _GetNumClients(hunt_obj.hunt_id) >= hunt_obj.client_limit:
      try:
        PauseHunt(
            hunt_id,
            hunt_state_reason=hunts_pb2.Hunt.HuntStateReason.TOTAL_CLIENTS_EXCEEDED,
        )
      except OnlyStartedHuntCanBePausedError:
        pass
