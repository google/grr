#!/usr/bin/env python
"""The GRR Foreman."""

import logging
from typing import Sequence

from grr_response_core.lib import rdfvalue
from grr_response_proto import jobs_pb2
from grr_response_server import data_store
from grr_response_server import flow
from grr_response_server import foreman_rules
from grr_response_server import hunt
from grr_response_server import message_handlers
from grr_response_server.databases import db
from grr_response_server.rdfvalues import objects as rdf_objects


class Error(Exception):
  pass


class UnknownHuntTypeError(Error):
  pass


# TODO(amoser): Now that Foreman rules are directly stored in the db,
# consider removing this class altogether once the AFF4 Foreman has
# been removed.
class Foreman(object):
  """The foreman starts flows for clients depending on rules."""

  def _IsTaskAlreadyAssigned(self, client_id: str, hunt_id: str) -> bool:
    """Will return True if hunt's task was assigned to this client before."""
    flow_id = hunt_id
    try:
      cur_flow = data_store.REL_DB.ReadFlowObject(client_id, flow_id)
    except db.UnknownFlowError:
      return False

    if cur_flow.parent_hunt_id != hunt_id:
      raise RuntimeError(
          "Cannot start Hunt {} on {} because unrelated {} already exists."
          .format(hunt_id, client_id, cur_flow.long_flow_id)
      )

    return True

  def _RunAction(self, condition: jobs_pb2.ForemanCondition, client_id: str):
    """Run all the actions specified in the condition.

    Args:
      condition: Condition that determines which actions are to be executed.
      client_id: Client id where the condition's actions are to be executed.

    Returns:
      Number of actions started.
    """
    actions_count = 0

    try:
      if self._IsTaskAlreadyAssigned(client_id, condition.hunt_id):
        raise flow.CanNotStartFlowWithExistingIdError(
            client_id, condition.hunt_id
        )

      hunt.StartHuntFlowOnClient(client_id, condition.hunt_id)
      logging.info(
          "Foreman: Started hunt %s on client %s.", condition.hunt_id, client_id
      )
      actions_count += 1

    except flow.CanNotStartFlowWithExistingIdError:
      logging.info(
          "Foreman: ignoring hunt %s on client %s: was started here before",
          condition.hunt_id,
          client_id,
      )

    # There could be all kinds of errors we don't know about when starting the
    # hunt so we catch everything here.
    except Exception as e:  # pylint: disable=broad-except
      logging.exception(
          "Failure running hunt %s on client %s: %s",
          condition.hunt_id,
          client_id,
          e,
      )

    return actions_count

  def _GetLastForemanRunTime(self, client_id: str) -> rdfvalue.RDFDatetime:
    md = data_store.REL_DB.ReadClientMetadata(client_id)
    return rdfvalue.RDFDatetime(md.last_foreman_time)

  def _SetLastForemanRunTime(
      self, client_id: str, latest_rule: rdfvalue.RDFDatetime
  ):
    data_store.REL_DB.WriteClientMetadata(client_id, last_foreman=latest_rule)

  def AssignTasksToClient(self, client_id: str):
    """Examines our rules and starts up flows based on the client.

    Args:
      client_id: Client id of the client for tasks to be assigned.

    Returns:
      Number of assigned tasks.
    """
    proto_rules: Sequence[jobs_pb2.ForemanCondition] = (
        data_store.REL_DB.ReadAllForemanRules()
    )
    if not proto_rules:
      return 0

    last_foreman_run = self._GetLastForemanRunTime(client_id)

    latest_rule_creation_time = max(rule.creation_time for rule in proto_rules)
    latest_rule_creation_time = rdfvalue.RDFDatetime.FromWireFormat(
        latest_rule_creation_time
    )

    if latest_rule_creation_time > last_foreman_run:
      # Update the latest checked rule on the client.
      self._SetLastForemanRunTime(client_id, latest_rule_creation_time)

    relevant_rules = []
    expired_rules = []

    now_micros = rdfvalue.RDFDatetime.Now().AsMicrosecondsSinceEpoch()

    for rule in proto_rules:
      if rule.expiration_time < now_micros:
        expired_rules.append(rule)
      elif rule.creation_time > last_foreman_run:
        relevant_rules.append(rule)

    actions_count = 0
    if relevant_rules:
      client_data = data_store.REL_DB.ReadClientFullInfo(client_id)
      if client_data is None:
        return

      for rule in relevant_rules:
        if foreman_rules.EvaluateForemanCondition(rule, client_data):
          actions_count += self._RunAction(rule, client_id)

    if expired_rules:
      for rule in expired_rules:
        hunt.CompleteHuntIfExpirationTimeReached(rule.hunt_id)
      data_store.REL_DB.RemoveExpiredForemanRules()

    return actions_count


class ForemanMessageHandler(message_handlers.MessageHandler):
  """A handler for Foreman messages."""

  handler_name = "ForemanHandler"

  def ProcessMessages(self, msgs: Sequence[rdf_objects.MessageHandlerRequest]):
    # TODO(amoser): The foreman reads the rules from the database for each
    # client. In the old implementation we used to have a cache. If this is a
    # performance hit, lets consider putting the cache back.

    foreman_obj = Foreman()
    for msg in msgs:
      foreman_obj.AssignTasksToClient(msg.client_id)
