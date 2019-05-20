#!/usr/bin/env python
"""REL_DB implementation of hunts."""
from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

from grr_response_core.lib import rdfvalue
from grr_response_core.lib import registry
from grr_response_core.lib.util import cache
from grr_response_core.lib.util import precondition
from grr_response_server import access_control
from grr_response_server import data_store
from grr_response_server import flow
from grr_response_server import foreman_rules
from grr_response_server import notification
from grr_response_server.aff4_objects import users as aff4_users
from grr_response_server.rdfvalues import hunt_objects as rdf_hunt_objects
from grr_response_server.rdfvalues import objects as rdf_objects

MIN_CLIENTS_FOR_AVERAGE_THRESHOLDS = 1000


class Error(Exception):
  pass


class UnknownHuntTypeError(Error):
  pass


class OnlyPausedHuntCanBeModifiedError(Error):

  def __init__(self, hunt_obj):
    super(OnlyPausedHuntCanBeModifiedError,
          self).__init__("Hunt %s can't be modified since it's in state %s." %
                         (hunt_obj.hunt_id, hunt_obj.hunt_state))


class OnlyPausedHuntCanBeStartedError(Error):

  def __init__(self, hunt_obj):
    super(OnlyPausedHuntCanBeStartedError,
          self).__init__("Hunt %s can't be started since it's in state %s." %
                         (hunt_obj.hunt_id, hunt_obj.hunt_state))


class OnlyStartedHuntCanBePausedError(Error):

  def __init__(self, hunt_obj):
    super(OnlyStartedHuntCanBePausedError,
          self).__init__("Hunt %s can't be paused since it's in state %s." %
                         (hunt_obj.hunt_id, hunt_obj.hunt_state))


class OnlyStartedOrPausedHuntCanBeStoppedError(Error):

  def __init__(self, hunt_obj):
    super(OnlyStartedOrPausedHuntCanBeStoppedError,
          self).__init__("Hunt %s can't be stopped since it's in state %s." %
                         (hunt_obj.hunt_id, hunt_obj.hunt_state))


class CanStartAtMostOneFlowPerClientError(Error):

  def __init__(self, hunt_id, client_id):
    super(CanStartAtMostOneFlowPerClientError, self).__init__(
        "Variable hunt %s has more than 1 flow for a client %s." %
        (hunt_id, client_id))


class VariableHuntCanNotHaveClientRateError(Error):

  def __init__(self, hunt_id, client_rate):

    super(VariableHuntCanNotHaveClientRateError, self).__init__(
        "Variable hunt %s has must have client_rate=0, instead it's %.2f." %
        (hunt_id, client_rate))


def IsLegacyHunt(hunt_id):
  return hunt_id.startswith("H:")


def HuntIDFromURN(hunt_urn):
  return hunt_urn.Basename().replace("H:", "")


def HuntURNFromID(hunt_id):
  if IsLegacyHunt(hunt_id):
    raise ValueError("Hunt ID is of a legacy type.")
  return rdfvalue.RDFURN("aff4:/hunts/H:%s" % hunt_id)


def StopHuntIfCrashLimitExceeded(hunt_id):
  """Stops the hunt if number of crashes exceeds the limit."""
  hunt_obj = data_store.REL_DB.ReadHuntObject(hunt_id)

  # Do nothing if the hunt is already stopped.
  if hunt_obj.hunt_state == rdf_hunt_objects.Hunt.HuntState.STOPPED:
    return hunt_obj

  if hunt_obj.crash_limit:
    hunt_counters = data_store.REL_DB.ReadHuntCounters(hunt_id)
    if hunt_counters.num_crashed_clients >= hunt_obj.crash_limit:
      # Remove our rules from the forman and cancel all the started flows.
      # Hunt will be hard-stopped and it will be impossible to restart it.
      reason = ("Hunt %s reached the crashes limit of %d "
                "and was stopped.") % (hunt_obj.hunt_id, hunt_obj.crash_limit)
      StopHunt(hunt_obj.hunt_id, reason=reason)

  return hunt_obj


_TIME_BETWEEN_STOP_CHECKS = rdfvalue.Duration("5s")


@cache.WithLimitedCallFrequency(_TIME_BETWEEN_STOP_CHECKS)
def StopHuntIfCPUOrNetworkLimitsExceeded(hunt_id):
  """Stops the hunt if average limites are exceeded."""
  hunt_obj = data_store.REL_DB.ReadHuntObject(hunt_id)

  # Do nothing if the hunt is already stopped.
  if hunt_obj.hunt_state == rdf_hunt_objects.Hunt.HuntState.STOPPED:
    return hunt_obj

  hunt_counters = data_store.REL_DB.ReadHuntCounters(hunt_id)

  # Check global hunt network bytes limit first.
  if (hunt_obj.total_network_bytes_limit and
      hunt_counters.total_network_bytes_sent >
      hunt_obj.total_network_bytes_limit):
    reason = ("Hunt %s reached the total network bytes sent limit of %d and "
              "was stopped.") % (hunt_obj.hunt_id,
                                 hunt_obj.total_network_bytes_limit)
    return StopHunt(hunt_obj.hunt_id, reason=reason)

  # Check that we have enough clients to apply average limits.
  if hunt_counters.num_clients < MIN_CLIENTS_FOR_AVERAGE_THRESHOLDS:
    return hunt_obj

  # Check average per-client results count limit.
  if hunt_obj.avg_results_per_client_limit:
    avg_results_per_client = (
        hunt_counters.num_results / hunt_counters.num_clients)
    if avg_results_per_client > hunt_obj.avg_results_per_client_limit:
      # Stop the hunt since we get too many results per client.
      reason = ("Hunt %s reached the average results per client "
                "limit of %d and was stopped.") % (
                    hunt_obj.hunt_id, hunt_obj.avg_results_per_client_limit)
      return StopHunt(hunt_obj.hunt_id, reason=reason)

  # Check average per-client CPU seconds limit.
  if hunt_obj.avg_cpu_seconds_per_client_limit:
    avg_cpu_seconds_per_client = (
        hunt_counters.total_cpu_seconds / hunt_counters.num_clients)
    if avg_cpu_seconds_per_client > hunt_obj.avg_cpu_seconds_per_client_limit:
      # Stop the hunt since we use too many CPUs per client.
      reason = ("Hunt %s reached the average CPU seconds per client "
                "limit of %d and was stopped.") % (
                    hunt_obj.hunt_id, hunt_obj.avg_cpu_seconds_per_client_limit)
      return StopHunt(hunt_obj.hunt_id, reason=reason)

  # Check average per-client network bytes limit.
  if hunt_obj.avg_network_bytes_per_client_limit:
    avg_network_bytes_per_client = (
        hunt_counters.total_network_bytes_sent / hunt_counters.num_clients)
    if (avg_network_bytes_per_client >
        hunt_obj.avg_network_bytes_per_client_limit):
      # Stop the hunt since we use too many network bytes sent
      # per client.
      reason = ("Hunt %s reached the average network bytes per client "
                "limit of %d and was stopped.") % (
                    hunt_obj.hunt_id,
                    hunt_obj.avg_network_bytes_per_client_limit)
      return StopHunt(hunt_obj.hunt_id, reason=reason)

  return hunt_obj


def CompleteHuntIfExpirationTimeReached(hunt_obj):
  """Marks the hunt as complete if it's past its expiry time."""
  # TODO(hanuszczak): This should not set the hunt state to `COMPLETED` but we
  # should have a sparate `EXPIRED` state instead and set that.
  if (hunt_obj.hunt_state not in [
      rdf_hunt_objects.Hunt.HuntState.STOPPED,
      rdf_hunt_objects.Hunt.HuntState.COMPLETED
  ] and hunt_obj.expired):
    StopHunt(hunt_obj.hunt_id, reason="Hunt completed.")

    data_store.REL_DB.UpdateHuntObject(
        hunt_obj.hunt_id, hunt_state=hunt_obj.HuntState.COMPLETED)
    return data_store.REL_DB.ReadHuntObject(hunt_obj.hunt_id)

  return hunt_obj


def CreateHunt(hunt_obj):
  """Creates a hunt using a given hunt object."""
  data_store.REL_DB.WriteHuntObject(hunt_obj)

  if hunt_obj.HasField("output_plugins"):
    output_plugins_states = flow.GetOutputPluginStates(
        hunt_obj.output_plugins,
        source="hunts/%s" % hunt_obj.hunt_id,
        token=access_control.ACLToken(username=hunt_obj.creator))
    data_store.REL_DB.WriteHuntOutputPluginsStates(hunt_obj.hunt_id,
                                                   output_plugins_states)


def CreateAndStartHunt(flow_name, flow_args, creator, **kwargs):
  """Creates and starts a new hunt."""

  # This interface takes a time when the hunt expires. However, the legacy hunt
  # starting interface took an rdfvalue.Duration object which was then added to
  # the current time to get the expiry. This check exists to make sure we don't
  # confuse the two.
  if "duration" in kwargs:
    precondition.AssertType(kwargs["duration"], rdfvalue.Duration)

  hunt_args = rdf_hunt_objects.HuntArguments(
      hunt_type=rdf_hunt_objects.HuntArguments.HuntType.STANDARD,
      standard=rdf_hunt_objects.HuntArgumentsStandard(
          flow_name=flow_name, flow_args=flow_args))

  hunt_obj = rdf_hunt_objects.Hunt(
      creator=creator,
      args=hunt_args,
      create_time=rdfvalue.RDFDatetime.Now(),
      **kwargs)

  CreateHunt(hunt_obj)
  StartHunt(hunt_obj.hunt_id)

  return hunt_obj.hunt_id


def _ScheduleGenericHunt(hunt_obj):
  """Adds foreman rules for a generic hunt."""
  # TODO: Migrate foreman conditions to use relation expiration
  # durations instead of absolute timestamps.
  foreman_condition = foreman_rules.ForemanCondition(
      creation_time=rdfvalue.RDFDatetime.Now(),
      expiration_time=hunt_obj.init_start_time + hunt_obj.duration,
      description="Hunt %s %s" % (hunt_obj.hunt_id, hunt_obj.args.hunt_type),
      client_rule_set=hunt_obj.client_rule_set,
      hunt_id=hunt_obj.hunt_id)

  # Make sure the rule makes sense.
  foreman_condition.Validate()

  data_store.REL_DB.WriteForemanRule(foreman_condition)


def _ScheduleVariableHunt(hunt_obj):
  """Schedules flows for a variable hunt."""
  if hunt_obj.client_rate != 0:
    raise VariableHuntCanNotHaveClientRateError(hunt_obj.hunt_id,
                                                hunt_obj.client_rate)

  seen_clients = set()
  for flow_group in hunt_obj.args.variable.flow_groups:
    for client_id in flow_group.client_ids:
      if client_id in seen_clients:
        raise CanStartAtMostOneFlowPerClientError(hunt_obj.hunt_id, client_id)
      seen_clients.add(client_id)

  now = rdfvalue.RDFDatetime.Now()
  for flow_group in hunt_obj.args.variable.flow_groups:
    flow_cls = registry.FlowRegistry.FlowClassByName(flow_group.flow_name)
    flow_args = flow_group.flow_args if flow_group.HasField(
        "flow_args") else None

    for client_id in flow_group.client_ids:
      flow.StartFlow(
          client_id=client_id,
          creator=hunt_obj.creator,
          cpu_limit=hunt_obj.per_client_cpu_limit,
          network_bytes_limit=hunt_obj.per_client_network_bytes_limit,
          flow_cls=flow_cls,
          flow_args=flow_args,
          # Setting start_at explicitly ensures that flow.StartFlow won't
          # process flow's Start state right away. Only the flow request
          # will be scheduled.
          start_at=now,
          parent_hunt_id=hunt_obj.hunt_id)


def StartHunt(hunt_id):
  """Starts a hunt with a given id."""

  hunt_obj = data_store.REL_DB.ReadHuntObject(hunt_id)
  num_hunt_clients = data_store.REL_DB.CountHuntFlows(hunt_id)

  if hunt_obj.hunt_state != hunt_obj.HuntState.PAUSED:
    raise OnlyPausedHuntCanBeStartedError(hunt_obj)

  data_store.REL_DB.UpdateHuntObject(
      hunt_id,
      hunt_state=hunt_obj.HuntState.STARTED,
      start_time=rdfvalue.RDFDatetime.Now(),
      num_clients_at_start_time=num_hunt_clients,
  )
  hunt_obj = data_store.REL_DB.ReadHuntObject(hunt_id)

  if hunt_obj.args.hunt_type == hunt_obj.args.HuntType.STANDARD:
    _ScheduleGenericHunt(hunt_obj)
  elif hunt_obj.args.hunt_type == hunt_obj.args.HuntType.VARIABLE:
    _ScheduleVariableHunt(hunt_obj)
  else:
    raise UnknownHuntTypeError("Invalid hunt type for hunt %s: %r" %
                               (hunt_id, hunt_obj.args.hunt_type))

  return hunt_obj


def PauseHunt(hunt_id, reason=None):
  """Pauses a hunt with a given id."""

  hunt_obj = data_store.REL_DB.ReadHuntObject(hunt_id)
  if hunt_obj.hunt_state != hunt_obj.HuntState.STARTED:
    raise OnlyStartedHuntCanBePausedError(hunt_obj)

  data_store.REL_DB.UpdateHuntObject(
      hunt_id, hunt_state=hunt_obj.HuntState.PAUSED, hunt_state_comment=reason)
  data_store.REL_DB.RemoveForemanRule(hunt_id=hunt_obj.hunt_id)

  return data_store.REL_DB.ReadHuntObject(hunt_id)


def StopHunt(hunt_id, reason=None):
  """Stops a hunt with a given id."""

  hunt_obj = data_store.REL_DB.ReadHuntObject(hunt_id)
  if hunt_obj.hunt_state not in [
      hunt_obj.HuntState.STARTED, hunt_obj.HuntState.PAUSED
  ]:
    raise OnlyStartedOrPausedHuntCanBeStoppedError(hunt_obj)

  data_store.REL_DB.UpdateHuntObject(
      hunt_id, hunt_state=hunt_obj.HuntState.STOPPED, hunt_state_comment=reason)
  data_store.REL_DB.RemoveForemanRule(hunt_id=hunt_obj.hunt_id)

  if (reason is not None and
      hunt_obj.creator not in aff4_users.GRRUser.SYSTEM_USERS):
    notification.Notify(
        hunt_obj.creator, rdf_objects.UserNotification.Type.TYPE_HUNT_STOPPED,
        reason,
        rdf_objects.ObjectReference(
            reference_type=rdf_objects.ObjectReference.Type.HUNT,
            hunt=rdf_objects.HuntReference(hunt_id=hunt_obj.hunt_id)))

  return data_store.REL_DB.ReadHuntObject(hunt_id)


def UpdateHunt(hunt_id, client_limit=None, client_rate=None, duration=None):
  """Updates a hunt (it must be paused to be updated)."""

  hunt_obj = data_store.REL_DB.ReadHuntObject(hunt_id)
  if hunt_obj.hunt_state != hunt_obj.HuntState.PAUSED:
    raise OnlyPausedHuntCanBeModifiedError(hunt_obj)

  data_store.REL_DB.UpdateHuntObject(
      hunt_id,
      client_limit=client_limit,
      client_rate=client_rate,
      duration=duration)
  return data_store.REL_DB.ReadHuntObject(hunt_id)


_TIME_BETWEEN_PAUSE_CHECKS = rdfvalue.Duration("5s")


@cache.WithLimitedCallFrequency(_TIME_BETWEEN_PAUSE_CHECKS)
def _GetNumClients(hunt_id):
  return data_store.REL_DB.CountHuntFlows(hunt_id)


def StartHuntFlowOnClient(client_id, hunt_id):
  """Starts a flow corresponding to a given hunt on a given client."""

  hunt_obj = data_store.REL_DB.ReadHuntObject(hunt_id)
  hunt_obj = CompleteHuntIfExpirationTimeReached(hunt_obj)
  # There may be a little race between foreman rules being removed and
  # foreman scheduling a client on an (already) paused hunt. Making sure
  # we don't lose clients in such a race by accepting clients for paused
  # hunts.
  if not rdf_hunt_objects.IsHuntSuitableForFlowProcessing(hunt_obj.hunt_state):
    return

  if hunt_obj.args.hunt_type == hunt_obj.args.HuntType.STANDARD:
    hunt_args = hunt_obj.args.standard

    if hunt_obj.client_rate > 0:
      # Given that we use caching in _GetNumClients and hunt_obj may be updated
      # in another process, we have to account for cases where num_clients_diff
      # may go below 0.
      num_clients_diff = max(
          0,
          _GetNumClients(hunt_obj.hunt_id) - hunt_obj.num_clients_at_start_time)
      next_client_due_msecs = int(num_clients_diff / hunt_obj.client_rate *
                                  60e6)

      start_at = rdfvalue.RDFDatetime.FromMicrosecondsSinceEpoch(
          hunt_obj.last_start_time.AsMicrosecondsSinceEpoch() +
          next_client_due_msecs)
    else:
      start_at = None

    # TODO(user): remove client_rate support when AFF4 is gone.
    # In REL_DB always work as if client rate is 0.

    flow_cls = registry.FlowRegistry.FlowClassByName(hunt_args.flow_name)
    flow_args = hunt_args.flow_args if hunt_args.HasField("flow_args") else None
    flow.StartFlow(
        client_id=client_id,
        creator=hunt_obj.creator,
        cpu_limit=hunt_obj.per_client_cpu_limit,
        network_bytes_limit=hunt_obj.per_client_network_bytes_limit,
        flow_cls=flow_cls,
        flow_args=flow_args,
        start_at=start_at,
        parent_hunt_id=hunt_id)

    if hunt_obj.client_limit:
      if _GetNumClients(hunt_obj.hunt_id) >= hunt_obj.client_limit:
        try:
          PauseHunt(hunt_id)
        except OnlyStartedHuntCanBePausedError:
          pass

  elif hunt_obj.args.hunt_type == hunt_obj.args.HuntType.VARIABLE:
    raise NotImplementedError()
  else:
    raise UnknownHuntTypeError("Can't determine hunt type when starting "
                               "hunt %s on client %s." % (client_id, hunt_id))
