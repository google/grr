#!/usr/bin/env python
"""The MySQL database methods for foreman rule handling."""
from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

from grr_response_core.lib import rdfvalue
from grr_response_server import foreman_rules
from grr_response_server.databases import mysql_utils


class MySQLDBForemanRulesMixin(object):
  """MySQLDB mixin for foreman rules related functions."""

  @mysql_utils.WithTransaction()
  def WriteForemanRule(self, rule, cursor=None):
    query = ("INSERT INTO foreman_rules "
             "(hunt_id, expiration_time, rule) VALUES (%s, %s, %s) "
             "ON DUPLICATE KEY UPDATE expiration_time=%s, rule=%s")

    exp_str = mysql_utils.RDFDatetimeToMysqlString(rule.expiration_time),
    rule_str = rule.SerializeToString()
    cursor.execute(query, [rule.hunt_id, exp_str, rule_str, exp_str, rule_str])

  @mysql_utils.WithTransaction()
  def RemoveForemanRule(self, hunt_id, cursor=None):
    query = "DELETE FROM foreman_rules WHERE hunt_id=%s"
    cursor.execute(query, [hunt_id])

  @mysql_utils.WithTransaction(readonly=True)
  def ReadAllForemanRules(self, cursor=None):
    cursor.execute("SELECT rule FROM foreman_rules")
    res = []
    for rule, in cursor.fetchall():
      res.append(foreman_rules.ForemanCondition.FromSerializedString(rule))
    return res

  @mysql_utils.WithTransaction()
  def RemoveExpiredForemanRules(self, cursor=None):
    now = rdfvalue.RDFDatetime.Now()
    cursor.execute("DELETE FROM foreman_rules WHERE expiration_time < %s",
                   [mysql_utils.RDFDatetimeToMysqlString(now)])
