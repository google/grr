#!/usr/bin/env python
"""The MySQL database methods for GRR users and approval handling."""

from collections.abc import Sequence
from typing import Optional

import MySQLdb

from grr_response_core.lib import rdfvalue
from grr_response_core.lib.rdfvalues import mig_crypto
from grr_response_core.lib.util import random
from grr_response_proto import jobs_pb2
from grr_response_proto import objects_pb2
from grr_response_proto import user_pb2
from grr_response_server.databases import db
from grr_response_server.databases import db_utils
from grr_response_server.databases import mysql_utils


def _IntToApprovalID(approval_id):
  return "%016x" % approval_id


def _ApprovalIDToInt(approval_id):
  return int(approval_id, 16)


def _ResponseToApprovalsWithGrants(response):
  """Converts a generator with approval rows into ApprovalRequest objects."""
  prev_triplet = None
  cur_approval_request = None
  for (
      approval_id_int,
      approval_timestamp,
      approval_request_bytes,
      grantor_username,
      grant_timestamp,
  ) in response:
    cur_triplet = (approval_id_int, approval_timestamp, approval_request_bytes)

    if cur_triplet != prev_triplet:
      prev_triplet = cur_triplet

      if cur_approval_request:
        yield cur_approval_request

      cur_approval_request = objects_pb2.ApprovalRequest()
      cur_approval_request.ParseFromString(approval_request_bytes)
      cur_approval_request.approval_id = _IntToApprovalID(approval_id_int)
      cur_approval_request.timestamp = (
          mysql_utils.TimestampToMicrosecondsSinceEpoch(approval_timestamp)
      )

    if grantor_username and grant_timestamp:
      grant = objects_pb2.ApprovalGrant(
          grantor_username=grantor_username,
          timestamp=mysql_utils.TimestampToMicrosecondsSinceEpoch(
              grant_timestamp
          ),
      )
      cur_approval_request.grants.add().CopyFrom(grant)

  if cur_approval_request:
    yield cur_approval_request


class MySQLDBUsersMixin(object):
  """MySQLDB mixin for GRR users and approval related functions."""

  @db_utils.CallLogged
  @db_utils.CallAccounted
  @mysql_utils.WithTransaction()
  def WriteGRRUser(
      self,
      username: str,
      password: Optional[jobs_pb2.Password] = None,
      ui_mode: Optional["user_pb2.GUISettings.UIMode"] = None,
      canary_mode: Optional[bool] = None,
      user_type: Optional["objects_pb2.GRRUser.UserType"] = None,
      email: Optional[str] = None,
      cursor: Optional[MySQLdb.cursors.Cursor] = None,
  ) -> None:
    """Writes user object for a user with a given name."""

    values = {"username": username, "username_hash": mysql_utils.Hash(username)}

    if password is not None:
      rdf_password = mig_crypto.ToRDFPassword(password)
      values["password"] = rdf_password.SerializeToBytes()
    if ui_mode is not None:
      values["ui_mode"] = int(ui_mode)
    if canary_mode is not None:
      values["canary_mode"] = bool(canary_mode)
    if user_type is not None:
      values["user_type"] = int(user_type)
    if email is not None:
      values["email"] = email

    query = "INSERT INTO grr_users {cols} VALUES {vals}".format(
        cols=mysql_utils.Columns(values),
        vals=mysql_utils.NamedPlaceholders(values),
    )

    updates = ", ".join("{0} = VALUES({0})".format(col) for col in values)
    query += " ON DUPLICATE KEY UPDATE " + updates

    cursor.execute(query, values)

  def _RowToGRRUser(self, row) -> objects_pb2.GRRUser:
    """Creates a GRR user object from a database result row."""
    username, password, ui_mode, canary_mode, user_type, email = row
    result = objects_pb2.GRRUser(
        username=username,
        ui_mode=ui_mode,
        canary_mode=canary_mode,
        user_type=user_type,
        email=email,
    )

    if password:
      result.password.ParseFromString(password)

    return result

  @db_utils.CallLogged
  @db_utils.CallAccounted
  @mysql_utils.WithTransaction(readonly=True)
  def ReadGRRUser(
      self,
      username: str,
      cursor: Optional[MySQLdb.cursors.Cursor] = None,
  ) -> objects_pb2.GRRUser:
    """Reads a user object corresponding to a given name."""
    cursor.execute(
        "SELECT username, password, ui_mode, canary_mode, user_type, email "
        "FROM grr_users WHERE username_hash = %s",
        [mysql_utils.Hash(username)],
    )

    row = cursor.fetchone()
    if row is None:
      raise db.UnknownGRRUserError(username)

    return self._RowToGRRUser(row)

  @db_utils.CallLogged
  @db_utils.CallAccounted
  @mysql_utils.WithTransaction(readonly=True)
  def ReadGRRUsers(
      self,
      offset: int = 0,
      count: int = None,
      cursor: Optional[MySQLdb.cursors.Cursor] = None,
  ) -> Sequence[objects_pb2.GRRUser]:
    """Reads GRR users with optional pagination, sorted by username."""
    if count is None:
      count = 18446744073709551615  # 2^64-1, as suggested by MySQL docs

    cursor.execute(
        "SELECT username, password, ui_mode, canary_mode, user_type, email "
        "FROM grr_users ORDER BY username ASC "
        "LIMIT %s OFFSET %s",
        [count, offset],
    )
    return [self._RowToGRRUser(row) for row in cursor.fetchall()]

  @db_utils.CallLogged
  @db_utils.CallAccounted
  @mysql_utils.WithTransaction(readonly=True)
  def CountGRRUsers(
      self, cursor: Optional[MySQLdb.cursors.Cursor] = None
  ) -> int:
    """Returns the total count of GRR users."""
    cursor.execute("SELECT COUNT(*) FROM grr_users")
    return cursor.fetchone()[0]

  @db_utils.CallLogged
  @db_utils.CallAccounted
  @mysql_utils.WithTransaction()
  def DeleteGRRUser(
      self, username: str, cursor: Optional[MySQLdb.cursors.Cursor] = None
  ) -> None:
    """Deletes the user and all related metadata with the given username."""
    cursor.execute(
        "DELETE FROM grr_users WHERE username_hash = %s",
        (mysql_utils.Hash(username),),
    )

    if cursor.rowcount == 0:
      raise db.UnknownGRRUserError(username)

  @db_utils.CallLogged
  @db_utils.CallAccounted
  @mysql_utils.WithTransaction()
  def WriteApprovalRequest(
      self,
      approval_request: objects_pb2.ApprovalRequest,
      cursor: Optional[MySQLdb.cursors.Cursor] = None,
  ) -> str:
    """Writes an approval request object."""
    # Copy the approval_request to ensure we don't modify the source object.
    approval_clone = objects_pb2.ApprovalRequest()
    approval_clone.CopyFrom(approval_request)
    # Generate random approval id.
    approval_id_int = random.UInt64()

    grants = approval_clone.grants
    approval_clone.ClearField("grants")

    expiry_time = approval_clone.expiration_time

    args = {
        "username_hash": mysql_utils.Hash(approval_clone.requestor_username),
        "approval_type": int(approval_clone.approval_type),
        "subject_id": approval_clone.subject_id,
        "approval_id": approval_id_int,
        "expiration_time": mysql_utils.MicrosecondsSinceEpochToTimestamp(
            expiry_time
        ),
        "approval_request": approval_clone.SerializeToString(),
    }
    query = """
    INSERT INTO approval_request (username_hash, approval_type,
                                  subject_id, approval_id, expiration_time,
                                  approval_request)
    VALUES (%(username_hash)s, %(approval_type)s,
            %(subject_id)s, %(approval_id)s, FROM_UNIXTIME(%(expiration_time)s),
            %(approval_request)s)
    """
    cursor.execute(query, args)

    for grant in grants:
      self._GrantApproval(
          approval_request.requestor_username,
          approval_id_int,
          grant.grantor_username,
          cursor,
      )

    return _IntToApprovalID(approval_id_int)

  def _GrantApproval(
      self,
      requestor_username: str,
      approval_id: str,
      grantor_username: str,
      cursor: Optional[MySQLdb.cursors.Cursor] = None,
  ) -> None:
    """Grants approval for a given request."""
    grant_args = {
        "username_hash": mysql_utils.Hash(requestor_username),
        "approval_id": approval_id,
        "grantor_username_hash": mysql_utils.Hash(grantor_username),
    }
    grant_query = "INSERT INTO approval_grant {columns} VALUES {values}".format(
        columns=mysql_utils.Columns(grant_args),
        values=mysql_utils.NamedPlaceholders(grant_args),
    )
    cursor.execute(grant_query, grant_args)

  @db_utils.CallLogged
  @db_utils.CallAccounted
  @mysql_utils.WithTransaction()
  def GrantApproval(
      self,
      requestor_username: str,
      approval_id: str,
      grantor_username: str,
      cursor: Optional[MySQLdb.cursors.Cursor] = None,
  ) -> None:
    """Grants approval for a given request using given username."""
    self._GrantApproval(
        requestor_username,
        _ApprovalIDToInt(approval_id),
        grantor_username,
        cursor,
    )

  @db_utils.CallLogged
  @db_utils.CallAccounted
  @mysql_utils.WithTransaction(readonly=True)
  def ReadApprovalRequest(
      self,
      requestor_username: str,
      approval_id: str,
      cursor: Optional[MySQLdb.cursors.Cursor] = None,
  ) -> objects_pb2.ApprovalRequest:
    """Reads an approval request object with a given id."""

    query = """
        SELECT
            ar.approval_id,
            UNIX_TIMESTAMP(ar.timestamp),
            ar.approval_request,
            u.username,
            UNIX_TIMESTAMP(ag.timestamp)
        FROM approval_request ar
        LEFT JOIN approval_grant ag USING (username_hash, approval_id)
        LEFT JOIN grr_users u ON u.username_hash = ag.grantor_username_hash
        WHERE ar.approval_id = %s AND ar.username_hash = %s
        """

    cursor.execute(
        query,
        [_ApprovalIDToInt(approval_id), mysql_utils.Hash(requestor_username)],
    )
    res = cursor.fetchall()
    if not res:
      raise db.UnknownApprovalRequestError(
          "Approval '%s' not found." % approval_id
      )

    approval_id_int, timestamp, approval_request_bytes, _, _ = res[0]

    approval_request = objects_pb2.ApprovalRequest()
    approval_request.ParseFromString(approval_request_bytes)
    approval_request.approval_id = _IntToApprovalID(approval_id_int)
    approval_request.timestamp = mysql_utils.TimestampToMicrosecondsSinceEpoch(
        timestamp
    )

    for _, _, _, grantor_username, timestamp in res:
      if not grantor_username:
        continue

      # Note: serialized approval_request objects are guaranteed to not
      # have any grants.
      grant = objects_pb2.ApprovalGrant(
          grantor_username=grantor_username,
          timestamp=mysql_utils.TimestampToMicrosecondsSinceEpoch(timestamp),
      )
      approval_request.grants.add().CopyFrom(grant)

    return approval_request

  @db_utils.CallLogged
  @db_utils.CallAccounted
  @mysql_utils.WithTransaction(readonly=True)
  def ReadApprovalRequests(
      self,
      requestor_username: str,
      approval_type: "objects_pb2.ApprovalRequest.ApprovalType",
      subject_id: Optional[str] = None,
      include_expired: Optional[bool] = False,
      cursor: Optional[MySQLdb.cursors.Cursor] = None,
  ) -> Sequence[objects_pb2.ApprovalRequest]:
    """Reads approval requests of a given type for a given user."""

    query = """
        SELECT
            ar.approval_id,
            UNIX_TIMESTAMP(ar.timestamp),
            ar.approval_request,
            u.username,
            UNIX_TIMESTAMP(ag.timestamp)
        FROM approval_request ar
        LEFT JOIN approval_grant AS ag USING (username_hash, approval_id)
        LEFT JOIN grr_users u ON u.username_hash = ag.grantor_username_hash
        WHERE ar.username_hash = %s AND ar.approval_type = %s
        """

    args = [mysql_utils.Hash(requestor_username), int(approval_type)]

    if subject_id:
      query += " AND ar.subject_id = %s"
      args.append(subject_id)

    query += " ORDER BY ar.approval_id"

    ret = []
    now = rdfvalue.RDFDatetime.Now().AsMicrosecondsSinceEpoch()
    cursor.execute(query, args)
    for approval_request in _ResponseToApprovalsWithGrants(cursor.fetchall()):
      if include_expired or approval_request.expiration_time >= now:
        ret.append(approval_request)
    return ret

  @db_utils.CallLogged
  @db_utils.CallAccounted
  @mysql_utils.WithTransaction()
  def WriteUserNotification(
      self,
      notification: objects_pb2.UserNotification,
      cursor: Optional[MySQLdb.cursors.Cursor] = None,
  ) -> None:
    """Writes a notification for a given user."""
    # Copy the notification to ensure we don't modify the source object.
    args = {
        "username_hash": mysql_utils.Hash(notification.username),
        "notification_state": int(notification.state),
        "notification": notification.SerializeToString(),
    }
    query = "INSERT INTO user_notification {columns} VALUES {values}".format(
        columns=mysql_utils.Columns(args),
        values=mysql_utils.NamedPlaceholders(args),
    )
    try:
      cursor.execute(query, args)
    except MySQLdb.IntegrityError:
      raise db.UnknownGRRUserError(notification.username)

  @db_utils.CallLogged
  @db_utils.CallAccounted
  @mysql_utils.WithTransaction(readonly=True)
  def ReadUserNotifications(
      self,
      username: str,
      state: Optional["objects_pb2.UserNotification.State"] = None,
      timerange: Optional[
          tuple[rdfvalue.RDFDatetime, rdfvalue.RDFDatetime]
      ] = None,
      cursor: Optional[MySQLdb.cursors.Cursor] = None,
  ) -> Sequence[objects_pb2.UserNotification]:
    """Reads notifications scheduled for a user within a given timerange."""

    query = (
        "SELECT UNIX_TIMESTAMP(timestamp), "
        "       notification_state, notification "
        "FROM user_notification "
        "WHERE username_hash = %s "
    )
    args = [mysql_utils.Hash(username)]

    if state is not None:
      query += "AND notification_state = %s "
      args.append(int(state))

    if timerange is not None:
      time_from, time_to = timerange  # pylint: disable=unpacking-non-sequence

      if time_from is not None:
        query += "AND timestamp >= FROM_UNIXTIME(%s) "
        args.append(mysql_utils.RDFDatetimeToTimestamp(time_from))

      if time_to is not None:
        query += "AND timestamp <= FROM_UNIXTIME(%s) "
        args.append(mysql_utils.RDFDatetimeToTimestamp(time_to))

    query += "ORDER BY timestamp DESC "

    ret = []
    cursor.execute(query, args)

    for timestamp, state, notification_ser in cursor.fetchall():
      n = objects_pb2.UserNotification()
      n.ParseFromString(notification_ser)
      n.timestamp = mysql_utils.TimestampToMicrosecondsSinceEpoch(timestamp)
      n.state = state
      ret.append(n)

    return ret

  @db_utils.CallLogged
  @db_utils.CallAccounted
  @mysql_utils.WithTransaction()
  def UpdateUserNotifications(
      self,
      username: str,
      timestamps: Sequence[rdfvalue.RDFDatetime],
      state: Optional["objects_pb2.UserNotification.State"] = None,
      cursor: Optional[MySQLdb.cursors.Cursor] = None,
  ) -> None:
    """Updates existing user notification objects."""
    if not timestamps:
      return

    query = (
        "UPDATE user_notification "
        "SET notification_state = %s "
        "WHERE username_hash = %s"
        "AND UNIX_TIMESTAMP(timestamp) IN {}"
    ).format(mysql_utils.Placeholders(len(timestamps)))

    args = [
        int(state),
        mysql_utils.Hash(username),
    ] + [mysql_utils.RDFDatetimeToTimestamp(t) for t in timestamps]
    cursor.execute(query, args)
