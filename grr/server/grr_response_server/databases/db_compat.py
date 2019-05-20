#!/usr/bin/env python
"""Temporary glue code for REL_DB flows+AFF4 hunts integration."""

from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

from grr_response_core.lib import rdfvalue
from grr_response_core.lib.rdfvalues import client as rdf_client
from grr_response_core.lib.rdfvalues import client_stats as rdf_client_stats
from grr_response_core.lib.rdfvalues import flows as rdf_flows
from grr_response_core.stats import stats_collector_instance
from grr_response_server import access_control
from grr_response_server import aff4
from grr_response_server import data_store
from grr_response_server import grr_collections
from grr_response_server import hunt
from grr_response_server import multi_type_collection
from grr_response_server.hunts import results as hunts_results
from grr_response_server.rdfvalues import flow_objects as rdf_flow_objects
from grr_response_server.rdfvalues import hunts as rdf_hunts


def IsLegacyHunt(hunt_id):
  return hunt_id.startswith("H:")


def WriteHuntResults(client_id, hunt_id, responses):
  """Writes hunt results from a given client as part of a given hunt."""

  if not hunt.IsLegacyHunt(hunt_id):
    data_store.REL_DB.WriteFlowResults(responses)

    hunt.StopHuntIfCPUOrNetworkLimitsExceeded(hunt_id)
    return

  hunt_id_urn = rdfvalue.RDFURN("hunts").Add(hunt_id)

  msgs = []
  for response in responses:
    if isinstance(response, rdf_flow_objects.FlowStatus):
      continue

    msgs.append(
        rdf_flows.GrrMessage(payload=response.payload, source=client_id))

  with data_store.DB.GetMutationPool() as pool:
    for msg in msgs:
      hunts_results.HuntResultCollection.StaticAdd(
          hunt_id_urn.Add("Results"), msg, mutation_pool=pool)

    for msg in msgs:
      multi_type_collection.MultiTypeCollection.StaticAdd(
          hunt_id_urn.Add("ResultsPerType"), msg, mutation_pool=pool)

  stats_collector_instance.Get().IncrementCounter(
      "hunt_results_added", delta=len(responses))


def _FlowStatusToClientResources(flow_obj, status_msg):
  return rdf_client_stats.ClientResources(
      client_id=flow_obj.client_id,
      session_id=flow_obj.flow_id,
      cpu_usage=rdf_client_stats.CpuSeconds(
          user_cpu_time=status_msg.cpu_time_used.user_cpu_time,
          system_cpu_time=status_msg.cpu_time_used.system_cpu_time),
      network_bytes_sent=status_msg.network_bytes_sent)


def ProcessHuntFlowError(flow_obj,
                         error_message=None,
                         backtrace=None,
                         status_msg=None):
  """Processes error and status message for a given hunt-induced flow."""

  if not hunt.IsLegacyHunt(flow_obj.parent_hunt_id):
    hunt.StopHuntIfCPUOrNetworkLimitsExceeded(flow_obj.parent_hunt_id)
    return

  hunt_urn = rdfvalue.RDFURN("hunts").Add(flow_obj.parent_hunt_id)
  client_urn = rdf_client.ClientURN(flow_obj.client_id)

  error = rdf_hunts.HuntError(client_id=flow_obj.client_id, backtrace=backtrace)
  if error_message is not None:
    error.log_message = error_message
  with data_store.DB.GetMutationPool() as pool:
    grr_collections.HuntErrorCollection.StaticAdd(
        hunt_urn.Add("ErrorClients"), error, mutation_pool=pool)
    grr_collections.ClientUrnCollection.StaticAdd(
        hunt_urn.Add("CompletedClients"), client_urn, mutation_pool=pool)

  if status_msg is not None:
    with aff4.FACTORY.Open(hunt_urn, mode="rw") as fd:
      # Legacy AFF4 code expects token to be set.
      fd.token = access_control.ACLToken(username=fd.creator)
      fd.GetRunner().SaveResourceUsage(flow_obj.client_id, status_msg)


def ProcessHuntFlowDone(flow_obj, status_msg=None):
  """Notifis hunt about a given hunt-induced flow completion."""

  if not hunt.IsLegacyHunt(flow_obj.parent_hunt_id):
    hunt_obj = hunt.StopHuntIfCPUOrNetworkLimitsExceeded(
        flow_obj.parent_hunt_id)
    hunt.CompleteHuntIfExpirationTimeReached(hunt_obj)
    return

  hunt_urn = rdfvalue.RDFURN("hunts").Add(flow_obj.parent_hunt_id)
  client_urn = rdf_client.ClientURN(flow_obj.client_id)

  # Update the counter metrics separately from collections to minimize
  # contention.
  with aff4.FACTORY.Open(hunt_urn, mode="rw") as fd:
    # Legacy AFF4 code expects token to be set.
    fd.token = access_control.ACLToken(username=fd.creator)

    if flow_obj.num_replies_sent:
      fd.context.clients_with_results_count += 1

    fd.context.completed_clients_count += 1
    fd.context.results_count += flow_obj.num_replies_sent

    fd.GetRunner().SaveResourceUsage(flow_obj.client_id, status_msg)

  with aff4.FACTORY.Open(hunt_urn, mode="rw") as fd:
    # Legacy AFF4 code expects token to be set.
    fd.token = access_control.ACLToken(username=fd.creator)

    fd.RegisterCompletedClient(client_urn)
    if flow_obj.num_replies_sent:
      fd.RegisterClientWithResults(client_urn)

    fd.StopHuntIfAverageLimitsExceeded()


def ProcessHuntFlowLog(flow_obj, log_msg):
  """Processes log message from a given hunt-induced flow."""

  if not hunt.IsLegacyHunt(flow_obj.parent_hunt_id):
    return

  hunt_urn = rdfvalue.RDFURN("hunts").Add(flow_obj.parent_hunt_id)
  flow_urn = hunt_urn.Add(flow_obj.flow_id)
  log_entry = rdf_flows.FlowLog(
      client_id=flow_obj.client_id,
      urn=flow_urn,
      flow_name=flow_obj.flow_class_name,
      log_message=log_msg)
  with data_store.DB.GetMutationPool() as pool:
    grr_collections.LogCollection.StaticAdd(
        hunt_urn.Add("Logs"), log_entry, mutation_pool=pool)
