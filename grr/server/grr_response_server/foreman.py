#!/usr/bin/env python
"""The GRR Foreman."""
from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

import logging

from grr_response_core.lib import rdfvalue
from grr_response_core.lib import registry
from grr_response_server import aff4
from grr_response_server import data_store
from grr_response_server import message_handlers


def GetForeman(token=None):
  if data_store.RelationalDBReadEnabled(category="foreman"):
    return Foreman()
  else:
    return aff4.FACTORY.Open("aff4:/foreman", mode="rw", token=token)


# TODO(amoser): Now that Foreman rules are directly stored in the db,
# consider removing this class altogether once the AFF4 Foreman has
# been removed.
class Foreman(object):
  """The foreman starts flows for clients depending on rules."""

  def _CheckIfHuntTaskWasAssigned(self, client_id, hunt_id):
    """Will return True if hunt's task was assigned to this client before."""
    client_urn = rdfvalue.RDFURN(client_id)
    for _ in aff4.FACTORY.Stat([
        client_urn.Add("flows/%s:hunt" % rdfvalue.RDFURN(hunt_id).Basename())
    ]):
      return True

    return False

  def _RunAction(self, rule, client_id):
    """Run all the actions specified in the rule.

    Args:
      rule: Rule which actions are to be executed.
      client_id: Id of a client where rule's actions are to be executed.

    Returns:
      Number of actions started.
    """
    actions_count = 0

    try:
      if self._CheckIfHuntTaskWasAssigned(client_id, rule.hunt_id):
        logging.info(
            "Foreman: ignoring hunt %s on client %s: was started "
            "here before", client_id, rule.hunt_id)
      else:
        logging.info("Foreman: Starting hunt %s on client %s.", rule.hunt_id,
                     client_id)

        flow_cls = registry.AFF4FlowRegistry.FlowClassByName(rule.hunt_name)
        hunt_urn = rdfvalue.RDFURN("aff4:/hunts/%s" % rule.hunt_id)
        flow_cls.StartClients(hunt_urn, [client_id])
        actions_count += 1
    # There could be all kinds of errors we don't know about when starting the
    # hunt so we catch everything here.
    except Exception as e:  # pylint: disable=broad-except
      logging.exception("Failure running foreman action on client %s: %s",
                        rule.hunt_id, e)

    return actions_count

  def _GetLastForemanRunTime(self, client_id):
    md = data_store.REL_DB.ReadClientMetadata(client_id)
    return md.last_foreman_time or rdfvalue.RDFDatetime(0)

  def _SetLastForemanRunTime(self, client_id, latest_rule):
    data_store.REL_DB.WriteClientMetadata(client_id, last_foreman=latest_rule)

  def AssignTasksToClient(self, client_id):
    """Examines our rules and starts up flows based on the client.

    Args:
      client_id: Client id of the client for tasks to be assigned.

    Returns:
      Number of assigned tasks.
    """
    rules = data_store.REL_DB.ReadAllForemanRules()
    if not rules:
      return 0

    last_foreman_run = self._GetLastForemanRunTime(client_id)

    latest_rule_creation_time = max(rule.creation_time for rule in rules)

    if latest_rule_creation_time <= last_foreman_run:
      return 0

    # Update the latest checked rule on the client.
    self._SetLastForemanRunTime(client_id, latest_rule_creation_time)

    relevant_rules = []
    expired_rules = False

    now = rdfvalue.RDFDatetime.Now()

    for rule in rules:
      if rule.expiration_time < now:
        expired_rules = True
        continue
      if rule.creation_time <= last_foreman_run:
        continue

      relevant_rules.append(rule)

    actions_count = 0
    if relevant_rules:
      client_data = data_store.REL_DB.ReadClientFullInfo(client_id)
      if client_data is None:
        return

      for rule in relevant_rules:
        if rule.Evaluate(client_data):
          actions_count += self._RunAction(rule, client_id)

    if expired_rules:
      data_store.REL_DB.RemoveExpiredForemanRules()

    return actions_count


class ForemanMessageHandler(message_handlers.MessageHandler):
  """A handler for Foreman messages."""

  handler_name = "ForemanHandler"

  def ProcessMessages(self, msgs):
    # TODO(amoser): The foreman reads the rules from the database for each
    # client. In the old implementation we used to have a cache. If this is a
    # performance hit, lets consider putting the cache back.

    foreman_obj = Foreman()
    for msg in msgs:
      foreman_obj.AssignTasksToClient(msg.client_id)
