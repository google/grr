#!/usr/bin/env python
"""A module with foreman rules methods of the Spanner backend."""

from typing import Sequence

from grr_response_core.lib import rdfvalue
from grr_response_proto import jobs_pb2
from grr_response_server.databases import db_utils
from grr_response_server.databases import spanner_utils


class ForemanRulesMixin:
  """A Spanner database mixin with implementation of foreman rules."""

  db: spanner_utils.Database

  @db_utils.CallLogged
  @db_utils.CallAccounted
  def WriteForemanRule(self, rule: jobs_pb2.ForemanCondition) -> None:
    """Writes a foreman rule to the database."""
    row = {
        "HuntId": rule.hunt_id,
        "ExpirationTime": (
            rdfvalue.RDFDatetime()
            .FromMicrosecondsSinceEpoch(rule.expiration_time)
            .AsDatetime()
        ),
        "Payload": rule,
    }
    self.db.InsertOrUpdate(
        table="ForemanRules", row=row, txn_tag="WriteForemanRule"
    )

  @db_utils.CallLogged
  @db_utils.CallAccounted
  def RemoveForemanRule(self, hunt_id: str) -> None:
    """Removes a foreman rule from the database."""
    self.db.Delete(
        table="ForemanRules", key=[hunt_id], txn_tag="RemoveForemanRule"
    )


  @db_utils.CallLogged
  @db_utils.CallAccounted
  def ReadAllForemanRules(self) -> Sequence[jobs_pb2.ForemanCondition]:
    """Reads all foreman rules from the database."""
    result = []

    query = """
    SELECT fr.Payload
    FROM ForemanRules AS fr
    """
    for [payload] in self.db.Query(query, txn_tag="ReadAllForemanRules"):
      rule = jobs_pb2.ForemanCondition()
      rule.ParseFromString(payload)
      result.append(rule)

    return result

  @db_utils.CallLogged
  @db_utils.CallAccounted
  def RemoveExpiredForemanRules(self) -> None:
    """Removes all expired foreman rules from the database."""
    query = """
    DELETE
      FROM ForemanRules@{{FORCE_INDEX=ForemanRulesByExpirationTime}} AS fr
     WHERE fr.ExpirationTime < CURRENT_TIMESTAMP()
    """
    self.db.ParamExecute(query, {}, txn_tag="RemoveExpiredForemanRules")

