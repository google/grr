#!/usr/bin/env python
"""The MySQL database methods for foreman rule handling."""

from collections.abc import Sequence
from typing import Optional

import MySQLdb

from grr_response_core.lib import rdfvalue
from grr_response_proto import jobs_pb2
from grr_response_server.databases import db_utils
from grr_response_server.databases import mysql_utils


class MySQLDBForemanRulesMixin(object):
  """MySQLDB mixin for foreman rules related functions."""

  @db_utils.CallLogged
  @db_utils.CallAccounted
  @mysql_utils.WithTransaction()
  def WriteForemanRule(
      self,
      rule: jobs_pb2.ForemanCondition,
      cursor: Optional[MySQLdb.cursors.Cursor] = None,
  ) -> None:
    """Writes a foreman rule to the database."""
    assert cursor is not None
    query = (
        "INSERT INTO foreman_rules "
        "  (hunt_id, expiration_time, rule) "
        "VALUES (%(hunt_id)s, FROM_UNIXTIME(%(exp_time)s), %(rule_bytes)s) "
        "ON DUPLICATE KEY UPDATE "
        "  expiration_time=FROM_UNIXTIME(%(exp_time)s), rule=%(rule_bytes)s"
    )

    cursor.execute(
        query,
        {
            "hunt_id": rule.hunt_id,
            "exp_time": mysql_utils.MicrosecondsSinceEpochToTimestamp(
                rule.expiration_time
            ),
            "rule_bytes": rule.SerializeToString(),
        },
    )

  @db_utils.CallLogged
  @db_utils.CallAccounted
  @mysql_utils.WithTransaction()
  def RemoveForemanRule(
      self, hunt_id: str, cursor: Optional[MySQLdb.cursors.Cursor] = None
  ) -> None:
    assert cursor is not None
    query = "DELETE FROM foreman_rules WHERE hunt_id=%s"
    cursor.execute(query, [hunt_id])

  @db_utils.CallLogged
  @db_utils.CallAccounted
  @mysql_utils.WithTransaction(readonly=True)
  def ReadAllForemanRules(
      self, cursor: Optional[MySQLdb.cursors.Cursor] = None
  ) -> Sequence[jobs_pb2.ForemanCondition]:
    assert cursor is not None
    cursor.execute("SELECT rule FROM foreman_rules")
    res = []
    for (rule,) in cursor.fetchall():
      condition = jobs_pb2.ForemanCondition()
      condition.ParseFromString(rule)
      res.append(condition)
    return res

  @db_utils.CallLogged
  @db_utils.CallAccounted
  @mysql_utils.WithTransaction()
  def RemoveExpiredForemanRules(
      self, cursor: Optional[MySQLdb.cursors.Cursor] = None
  ) -> None:
    assert cursor is not None
    now = rdfvalue.RDFDatetime.Now().AsMicrosecondsSinceEpoch()
    cursor.execute(
        "DELETE FROM foreman_rules WHERE expiration_time < FROM_UNIXTIME(%s)",
        [mysql_utils.MicrosecondsSinceEpochToTimestamp(now)],
    )
