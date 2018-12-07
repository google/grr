#!/usr/bin/env python
"""The MySQL database methods for GRR users and approval handling."""
from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

import MySQLdb

from grr_response_core.lib import rdfvalue
from grr_response_core.lib.util import random
from grr_response_server import db
from grr_response_server.databases import mysql_utils
from grr_response_server.rdfvalues import objects as rdf_objects


def _IntToApprovalID(approval_id):
  return u"%016x" % approval_id


def _ApprovalIDToInt(approval_id):
  return int(approval_id, 16)


def _ResponseToApprovalsWithGrants(response):
  """Converts a generator with approval rows into ApprovalRequest objects."""
  prev_triplet = None
  cur_approval_request = None
  for (approval_id_int, approval_timestamp, approval_request_bytes,
       grantor_username, grant_timestamp) in response:

    cur_triplet = (approval_id_int, approval_timestamp, approval_request_bytes)

    if cur_triplet != prev_triplet:
      prev_triplet = cur_triplet

      if cur_approval_request:
        yield cur_approval_request

      cur_approval_request = mysql_utils.StringToRDFProto(
          rdf_objects.ApprovalRequest, approval_request_bytes)
      cur_approval_request.approval_id = _IntToApprovalID(approval_id_int)
      cur_approval_request.timestamp = mysql_utils.MysqlToRDFDatetime(
          approval_timestamp)

    if grantor_username and grant_timestamp:
      cur_approval_request.grants.append(
          rdf_objects.ApprovalGrant(
              grantor_username=grantor_username,
              timestamp=mysql_utils.MysqlToRDFDatetime(grant_timestamp)))

  if cur_approval_request:
    yield cur_approval_request


class MySQLDBUsersMixin(object):
  """MySQLDB mixin for GRR users and approval related functions."""

  @mysql_utils.WithTransaction()
  def WriteGRRUser(self,
                   username,
                   password=None,
                   ui_mode=None,
                   canary_mode=None,
                   user_type=None,
                   cursor=None):
    """Writes user object for a user with a given name."""

    columns = ["username"]
    values = [username]

    if password is not None:
      columns.append("password")
      values.append(password.SerializeToString())
    if ui_mode is not None:
      columns.append("ui_mode")
      values.append(int(ui_mode))
    if canary_mode is not None:
      columns.append("canary_mode")
      # TODO(amoser): This int conversion is dirty but necessary with
      # the current MySQL driver.
      values.append(int(bool(canary_mode)))
    if user_type is not None:
      columns.append("user_type")
      values.append(int(user_type))

    query = "INSERT INTO grr_users ({cols}) VALUES ({vals})".format(
        cols=", ".join(columns), vals=", ".join(["%s"] * len(columns)))

    # Always execute ON DUPLICATE KEY UPDATE username=%s. Although a no-op, the
    # statement is required to allow error-free writing of an existing user
    # with no other fields. See DatabaseTestUsersMixin.testInsertUserTwice.
    updates = ", ".join(["{c} = VALUES ({c})".format(c=col) for col in columns])
    query += "ON DUPLICATE KEY UPDATE " + updates

    cursor.execute(query, values)

  def _RowToGRRUser(self, row):
    """Creates a GRR user object from a database result row."""
    username, password, ui_mode, canary_mode, user_type = row
    result = rdf_objects.GRRUser(
        username=username,
        ui_mode=ui_mode,
        canary_mode=canary_mode,
        user_type=user_type)

    if password:
      result.password.ParseFromString(password)

    return result

  @mysql_utils.WithTransaction(readonly=True)
  def ReadGRRUser(self, username, cursor=None):
    """Reads a user object corresponding to a given name."""
    cursor.execute(
        "SELECT username, password, ui_mode, canary_mode, user_type "
        "FROM grr_users WHERE username=%s", [username])

    row = cursor.fetchone()
    if row is None:
      raise db.UnknownGRRUserError(username)

    return self._RowToGRRUser(row)

  @mysql_utils.WithTransaction(readonly=True)
  def ReadGRRUsers(self, offset=0, count=None, cursor=None):
    """Reads GRR users with optional pagination, sorted by username."""
    if count is None:
      count = 18446744073709551615  # 2^64-1, as suggested by MySQL docs

    cursor.execute(
        "SELECT username, password, ui_mode, canary_mode, user_type "
        "FROM grr_users ORDER BY username ASC "
        "LIMIT %s OFFSET %s", [count, offset])
    return [self._RowToGRRUser(row) for row in cursor.fetchall()]

  @mysql_utils.WithTransaction(readonly=True)
  def CountGRRUsers(self, cursor=None):
    """Returns the total count of GRR users."""
    cursor.execute("SELECT COUNT(*) FROM grr_users")
    return cursor.fetchone()[0]

  @mysql_utils.WithTransaction()
  def DeleteGRRUser(self, username, cursor=None):
    """Deletes the user with the given username."""
    cursor.execute("DELETE FROM grr_users WHERE username = %s", (username,))

    if cursor.rowcount == 0:
      raise db.UnknownGRRUserError(username)

  @mysql_utils.WithTransaction()
  def WriteApprovalRequest(self, approval_request, cursor=None):
    """Writes an approval request object."""
    # Copy the approval_request to ensure we don't modify the source object.
    approval_request = approval_request.Copy()
    # Generate random approval id.
    approval_id_int = random.UInt64()
    now_str = mysql_utils.RDFDatetimeToMysqlString(rdfvalue.RDFDatetime.Now())

    grants = approval_request.grants
    approval_request.grants = None

    query = ("INSERT INTO approval_request (username, approval_type, "
             "subject_id, approval_id, timestamp, expiration_time, "
             "approval_request) VALUES (%s, %s, %s, %s, %s, %s, %s)")

    args = [
        approval_request.requestor_username,
        int(approval_request.approval_type), approval_request.subject_id,
        approval_id_int, now_str,
        mysql_utils.RDFDatetimeToMysqlString(approval_request.expiration_time),
        approval_request.SerializeToString()
    ]
    cursor.execute(query, args)

    for grant in grants:
      grant_query = ("INSERT INTO approval_grant (username, approval_id, "
                     "grantor_username, timestamp) VALUES (%s, %s, %s, %s)")
      grant_args = [
          approval_request.requestor_username, approval_id_int,
          grant.grantor_username, now_str
      ]
      cursor.execute(grant_query, grant_args)

    return _IntToApprovalID(approval_id_int)

  @mysql_utils.WithTransaction()
  def GrantApproval(self,
                    requestor_username,
                    approval_id,
                    grantor_username,
                    cursor=None):
    """Grants approval for a given request using given username."""
    now_str = mysql_utils.RDFDatetimeToMysqlString(rdfvalue.RDFDatetime.Now())
    grant_query = ("INSERT INTO approval_grant (username, approval_id, "
                   "grantor_username, timestamp) VALUES (%s, %s, %s, %s)")
    grant_args = [
        requestor_username,
        _ApprovalIDToInt(approval_id), grantor_username, now_str
    ]
    cursor.execute(grant_query, grant_args)

  @mysql_utils.WithTransaction(readonly=True)
  def ReadApprovalRequest(self, requestor_username, approval_id, cursor=None):
    """Reads an approval request object with a given id."""

    query = ("SELECT approval_request.approval_id, approval_request.timestamp, "
             "approval_request.approval_request, "
             "approval_grant.grantor_username, approval_grant.timestamp "
             "FROM approval_request "
             "LEFT JOIN approval_grant USING (username, approval_id) "
             "WHERE approval_request.approval_id=%s "
             "AND approval_request.username=%s")

    cursor.execute(query, [_ApprovalIDToInt(approval_id), requestor_username])
    res = cursor.fetchall()
    if not res:
      raise db.UnknownApprovalRequestError(
          "Approval '%s' not found." % approval_id)

    approval_id_int, timestamp, approval_request_bytes, _, _ = res[0]

    approval_request = mysql_utils.StringToRDFProto(rdf_objects.ApprovalRequest,
                                                    approval_request_bytes)
    approval_request.approval_id = _IntToApprovalID(approval_id_int)
    approval_request.timestamp = mysql_utils.MysqlToRDFDatetime(timestamp)

    for _, _, _, grantor_username, timestamp in res:
      if not grantor_username:
        continue

      # Note: serialized approval_request objects are guaranteed to not
      # have any grants.
      approval_request.grants.append(
          rdf_objects.ApprovalGrant(
              grantor_username=grantor_username,
              timestamp=mysql_utils.MysqlToRDFDatetime(timestamp)))

    return approval_request

  @mysql_utils.WithTransaction(readonly=True)
  def ReadApprovalRequests(self,
                           requestor_username,
                           approval_type,
                           subject_id=None,
                           include_expired=False,
                           cursor=None):
    """Reads approval requests of a given type for a given user."""

    query = ("SELECT ar.approval_id, ar.timestamp, ar.approval_request, "
             "ag.grantor_username, ag.timestamp "
             "FROM approval_request ar "
             "LEFT JOIN approval_grant AS ag USING (username, approval_id) "
             "WHERE ar.username=%s AND ar.approval_type=%s")

    args = [requestor_username, int(approval_type)]

    if subject_id:
      query += " AND ar.subject_id = %s"
      args.append(subject_id)

    query += " ORDER BY ar.approval_id"

    ret = []
    now = rdfvalue.RDFDatetime.Now()
    cursor.execute(query, args)
    for approval_request in _ResponseToApprovalsWithGrants(cursor.fetchall()):
      if include_expired or approval_request.expiration_time >= now:
        ret.append(approval_request)
    return ret

  @mysql_utils.WithTransaction()
  def WriteUserNotification(self, notification, cursor=None):
    """Writes a notification for a given user."""
    # Copy the notification to ensure we don't modify the source object.
    notification = notification.Copy()

    if not notification.timestamp:
      notification.timestamp = rdfvalue.RDFDatetime.Now()

    query = ("INSERT INTO user_notification (username, timestamp, "
             "notification_state, notification) "
             "VALUES (%s, %s, %s, %s)")

    args = [
        notification.username,
        mysql_utils.RDFDatetimeToMysqlString(notification.timestamp),
        int(notification.state),
        notification.SerializeToString()
    ]
    try:
      cursor.execute(query, args)
    except MySQLdb.IntegrityError:
      raise db.UnknownGRRUserError(notification.username)

  @mysql_utils.WithTransaction(readonly=True)
  def ReadUserNotifications(self,
                            username,
                            state=None,
                            timerange=None,
                            cursor=None):
    """Reads notifications scheduled for a user within a given timerange."""

    query = ("SELECT timestamp, notification_state, notification "
             "FROM user_notification "
             "WHERE username=%s ")
    args = [username]

    if state is not None:
      query += "AND notification_state = %s "
      args.append(int(state))

    if timerange is not None:
      time_from, time_to = timerange  # pylint: disable=unpacking-non-sequence

      if time_from is not None:
        query += "AND timestamp >= %s "
        args.append(mysql_utils.RDFDatetimeToMysqlString(time_from))

      if time_to is not None:
        query += "AND timestamp <= %s "
        args.append(mysql_utils.RDFDatetimeToMysqlString(time_to))

    query += "ORDER BY timestamp DESC "

    ret = []
    cursor.execute(query, args)

    for timestamp, state, notification_ser in cursor.fetchall():
      n = rdf_objects.UserNotification.FromSerializedString(notification_ser)
      n.timestamp = mysql_utils.MysqlToRDFDatetime(timestamp)
      n.state = state
      ret.append(n)

    return ret

  @mysql_utils.WithTransaction()
  def UpdateUserNotifications(self,
                              username,
                              timestamps,
                              state=None,
                              cursor=None):
    """Updates existing user notification objects."""

    query = ("UPDATE user_notification n "
             "SET n.notification_state = %s "
             "WHERE n.username = %s AND n.timestamp IN ({})").format(", ".join(
                 ["%s"] * len(timestamps)))

    args = [
        int(state),
        username,
    ] + [mysql_utils.RDFDatetimeToMysqlString(t) for t in timestamps]
    cursor.execute(query, args)
