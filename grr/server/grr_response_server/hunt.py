#!/usr/bin/env python
"""REL_DB implementation of hunts."""
from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

import sys

from grr_response_core.lib import rdfvalue
from grr_response_core.lib import registry
from grr_response_server import access_control
from grr_response_server import data_store
from grr_response_server import db
from grr_response_server import flow
from grr_response_server import foreman_rules
from grr_response_server import notification
from grr_response_server.aff4_objects import users as aff4_users
from grr_response_server.rdfvalues import flow_objects as rdf_flow_objects
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


def IsLegacyHunt(hunt_id):
  return hunt_id.startswith("H:")


def StopHuntIfAverageLimitsExceeded(hunt_obj):
  """Stops the hunt if average limites are exceeded."""

  # Do nothing if the hunt is already stopped.
  if hunt_obj.hunt_state == rdf_hunt_objects.Hunt.HuntState.STOPPED:
    return hunt_obj

  total_clients = (
      hunt_obj.num_successful_clients + hunt_obj.num_failed_clients +
      hunt_obj.num_crashed_clients)

  if total_clients < MIN_CLIENTS_FOR_AVERAGE_THRESHOLDS:
    return hunt_obj

  # Check average per-client results count limit.
  if hunt_obj.avg_results_per_client_limit:
    avg_results_per_client = (hunt_obj.num_results / total_clients)
    if avg_results_per_client > hunt_obj.avg_results_per_client_limit:
      # Stop the hunt since we get too many results per client.
      reason = ("Hunt %s reached the average results per client "
                "limit of %d and was stopped.") % (
                    hunt_obj.hunt_id, hunt_obj.avg_results_per_client_limit)
      return StopHunt(hunt_obj.hunt_id, reason=reason)

  # Check average per-client CPU seconds limit.
  if hunt_obj.avg_cpu_seconds_per_client_limit:
    avg_cpu_seconds_per_client = (
        (hunt_obj.client_resources_stats.user_cpu_stats.sum +
         hunt_obj.client_resources_stats.system_cpu_stats.sum) / total_clients)
    if avg_cpu_seconds_per_client > hunt_obj.avg_cpu_seconds_per_client_limit:
      # Stop the hunt since we use too many CPUs per client.
      reason = ("Hunt %s reached the average CPU seconds per client "
                "limit of %d and was stopped.") % (
                    hunt_obj.hunt_id, hunt_obj.avg_cpu_seconds_per_client_limit)
      return StopHunt(hunt_obj.hunt_id, reason=reason)

  # Check average per-client network bytes limit.
  if hunt_obj.avg_network_bytes_per_client_limit:
    avg_network_bytes_per_client = (
        hunt_obj.client_resources_stats.network_bytes_sent_stats.sum /
        total_clients)
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

  if (hunt_obj.hunt_state not in [
      rdf_hunt_objects.Hunt.HuntState.STOPPED,
      rdf_hunt_objects.Hunt.HuntState.COMPLETED
  ] and hunt_obj.expiry_time < rdfvalue.RDFDatetime.Now()):
    StopHunt(hunt_obj.hunt_id, reason="Hunt completed.")

    def UpdateFn(h):
      h.hunt_state = h.HuntState.COMPLETED
      return h

    return data_store.REL_DB.UpdateHuntObject(hunt_obj.hunt_id, UpdateFn)

  return hunt_obj


def StartHunt(hunt_id):
  """Starts a hunt with a given id."""

  hunt_obj = data_store.REL_DB.ReadHuntObject(hunt_id)
  output_plugins_states = None
  if hunt_obj.output_plugins and not hunt_obj.output_plugins_states:
    output_plugins_states = flow.GetOutputPluginStates(
        hunt_obj.output_plugins,
        source="hunts/%s" % hunt_obj.hunt_id,
        token=access_control.ACLToken(username=hunt_obj.creator))
    for ops in output_plugins_states:
      ops.plugin_state["success_count"] = 0
      ops.plugin_state["error_count"] = 0

  def UpdateFn(h):
    """Updates given hunt in a transaction."""

    if h.hunt_state != h.HuntState.PAUSED:
      raise OnlyPausedHuntCanBeStartedError(h)

    if (output_plugins_states is not None and
        not hunt_obj.output_plugins_states):
      h.output_plugins_states = output_plugins_states
    h.hunt_state = h.HuntState.STARTED
    h.hunt_state_comment = None
    h.next_client_due = rdfvalue.RDFDatetime.Now()
    return h

  hunt_obj = data_store.REL_DB.UpdateHuntObject(hunt_id, UpdateFn)
  if hunt_obj.hunt_state != hunt_obj.HuntState.STARTED:
    return

  foreman_condition = foreman_rules.ForemanCondition(
      creation_time=rdfvalue.RDFDatetime.Now(),
      expiration_time=hunt_obj.expiry_time,
      description="Hunt %s %s" % (hunt_obj.hunt_id, hunt_obj.args.hunt_type),
      client_rule_set=hunt_obj.client_rule_set,
      hunt_id=hunt_obj.hunt_id)

  # Make sure the rule makes sense.
  foreman_condition.Validate()

  data_store.REL_DB.WriteForemanRule(foreman_condition)

  return hunt_obj


def PauseHunt(hunt_id, reason=None):
  """Pauses a hunt with a given id."""

  def UpdateFn(h):
    if h.hunt_state != h.HuntState.STARTED:
      raise OnlyStartedHuntCanBePausedError(h)

    h.hunt_state = h.HuntState.PAUSED
    if reason is not None:
      h.hunt_state_comment = reason
    else:
      h.hunt_state_comment = None
    return h

  hunt_obj = data_store.REL_DB.UpdateHuntObject(hunt_id, UpdateFn)
  if hunt_obj.hunt_state == hunt_obj.HuntState.PAUSED:
    data_store.REL_DB.RemoveForemanRule(hunt_id=hunt_obj.hunt_id)

  return hunt_obj


def StopHunt(hunt_id, reason=None):
  """Stops a hunt with a given id."""

  def UpdateFn(h):
    if h.hunt_state not in [h.HuntState.STARTED, h.HuntState.PAUSED]:
      raise OnlyStartedOrPausedHuntCanBeStoppedError(h)

    h.hunt_state = h.HuntState.STOPPED
    if reason is not None:
      h.hunt_state_comment = reason
    return h

  # If the hunt was not started or paused, the exception from UpdateFn is
  # guaranteed to be propagated by UpdateHuntObject implementation.
  hunt_obj = data_store.REL_DB.UpdateHuntObject(hunt_id, UpdateFn)
  data_store.REL_DB.RemoveForemanRule(hunt_id=hunt_obj.hunt_id)

  flows = data_store.REL_DB.ReadHuntFlows(hunt_obj.hunt_id, 0, sys.maxsize)
  data_store.REL_DB.UpdateFlows(
      [(f.client_id, f.flow_id) for f in flows],
      pending_termination=rdf_flow_objects.PendingFlowTermination(
          reason="Parent hunt stopped."))

  if (reason is not None and
      hunt_obj.creator not in aff4_users.GRRUser.SYSTEM_USERS):
    notification.Notify(
        hunt_obj.creator, rdf_objects.UserNotification.Type.TYPE_HUNT_STOPPED,
        reason,
        rdf_objects.ObjectReference(
            reference_type=rdf_objects.ObjectReference.Type.HUNT,
            hunt=rdf_objects.HuntReference(hunt_id=hunt_obj.hunt_id)))

  return hunt_obj


def UpdateHunt(hunt_id, client_limit=None, client_rate=None, expiry_time=None):
  """Updates a hunt (it must be paused to be updated)."""

  def UpdateFn(hunt_obj):
    """Update callback used by UpdateHuntObject."""

    if hunt_obj.hunt_state != hunt_obj.HuntState.PAUSED:
      raise OnlyPausedHuntCanBeModifiedError(hunt_obj)

    if client_limit is not None:
      hunt_obj.client_limit = client_limit

    if client_rate is not None:
      hunt_obj.client_rate = client_rate

    if expiry_time is not None:
      hunt_obj.expiry_time = expiry_time

    return hunt_obj

  return data_store.REL_DB.UpdateHuntObject(hunt_id, UpdateFn)


def StartHuntFlowOnClient(client_id, hunt_id):
  """Starts a flow corresponding to a given hunt on a given client."""

  hunt_obj = data_store.REL_DB.ReadHuntObject(hunt_id)
  hunt_obj = CompleteHuntIfExpirationTimeReached(hunt_obj)
  # There may be a little race between foreman rules being removed and
  # foreman scheduling a client on an (already) paused hunt. Making sure
  # we don't lose clients in such a race by accepting clients for paused
  # hunts.
  if hunt_obj.hunt_state not in [
      rdf_hunt_objects.Hunt.HuntState.STARTED,
      rdf_hunt_objects.Hunt.HuntState.PAUSED
  ]:
    return

  if hunt_obj.args.hunt_type == hunt_obj.args.HuntType.STANDARD:
    hunt_args = hunt_obj.args.standard

    def UpdateFn(h):
      # h.num_clients > 0 check ensures that first client will be scheduled
      # immediately and not 60.0 / h.client_rate seconds after the hunt is
      # started.
      if h.client_rate > 0 and h.num_clients > 0:
        h.next_client_due = h.next_client_due + 60.0 / h.client_rate
      h.num_clients += 1
      return h

    hunt_obj = data_store.REL_DB.UpdateHuntObject(hunt_id, UpdateFn)
    start_at = hunt_obj.next_client_due if hunt_obj.client_rate > 0 else None

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

    if hunt_obj.client_limit and hunt_obj.num_clients >= hunt_obj.client_limit:
      PauseHunt(hunt_obj.hunt_id)

  elif hunt_obj.args.hunt_type == hunt_obj.args.HuntType.VARIABLE:
    raise NotImplementedError()
  else:
    raise UnknownHuntTypeError("Can't determine hunt type when starting "
                               "hunt %s on client %s." % (client_id, hunt_id))


def GetHuntOutputPluginLogs(hunt_id, offset, count):
  """Gets hunt's output plugins logs."""

  # TODO(user): this is a simplistic implementation that may return
  # more results than requested. Refactor and improve.
  flows = data_store.REL_DB.ReadHuntFlows(
      hunt_id,
      offset,
      count,
      filter_condition=db.HuntFlowsCondition.FLOWS_WITH_RESULTS_ONLY)
  logs = []
  for f in flows:
    for op_state in f.output_plugins_states:
      logs.extend(op_state.plugin_state["logs"])

  return logs


def GetHuntOutputPluginErrors(hunt_id, offset, count):
  """Gets hunt's output plugins errors."""

  # TODO(user): this is a simplistic implementation that may return
  # more results than requested. Refactor and improve.
  flows = data_store.REL_DB.ReadHuntFlows(
      hunt_id,
      offset,
      count,
      filter_condition=db.HuntFlowsCondition.FLOWS_WITH_RESULTS_ONLY)
  errors = []
  for f in flows:
    for op_state in f.output_plugins_states:
      errors.extend(op_state.plugin_state["errors"])

  return errors
