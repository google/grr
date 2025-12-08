#!/usr/bin/env python
"""A library with user methods of Spanner database implementation."""
import base64
import datetime
import logging
import uuid

from typing import Optional, Sequence, Tuple

from google.api_core.exceptions import NotFound

from google.cloud import spanner as spanner_lib

from grr_response_core.lib import rdfvalue
from grr_response_core.lib.util import iterator
from grr_response_proto import jobs_pb2
from grr_response_proto import objects_pb2
from grr_response_proto import user_pb2
from grr_response_server.databases import db as abstract_db
from grr_response_server.databases import db_utils
from grr_response_server.databases import spanner_utils


class UsersMixin:
  """A Spanner database mixin with implementation of user methods."""

  db: spanner_utils.Database

  @db_utils.CallLogged
  @db_utils.CallAccounted
  def WriteGRRUser(
      self,
      username: str,
      email: Optional[str] = None,
      password: Optional[jobs_pb2.Password] = None,
      user_type: Optional["objects_pb2.GRRUser.UserType"] = None,
      canary_mode: Optional[bool] = None,
      ui_mode: Optional["user_pb2.GUISettings.UIMode"] = None,
  ) -> None:
    """Writes user object for a user with a given name."""
    row = {"Username": username}

    if email is not None:
      row["Email"] = email

    if password is not None:
      row["Password"] = password

    if user_type is not None:
      row["Type"] = int(user_type)

    if ui_mode is not None:
      row["UiMode"] = int(ui_mode)

    if canary_mode is not None:
      row["CanaryMode"] = canary_mode

    self.db.InsertOrUpdate(table="Users", row=row, txn_tag="WriteGRRUser")


  @db_utils.CallLogged
  @db_utils.CallAccounted
  def DeleteGRRUser(self, username: str) -> None:
    """Deletes the user and all related metadata with the given username."""
    keyset = spanner_lib.KeySet(keys=[(username,)])

    def Transaction(txn) -> None:
      try:
        txn.read(table="Users", columns=("Username",), keyset=keyset).one()
      except NotFound:
        raise abstract_db.UnknownGRRUserError(username)

      username_range = spanner_lib.KeyRange(start_closed=[username], end_closed=[username])
      txn.delete(table="ApprovalRequests", keyset=spanner_lib.KeySet(ranges=[username_range]))
      txn.delete(table="Users", keyset=keyset)

    self.db.Transact(Transaction, txn_tag="DeleteGRRUser")


  @db_utils.CallLogged
  @db_utils.CallAccounted
  def ReadGRRUser(self, username: str) -> objects_pb2.GRRUser:
    """Reads a user object corresponding to a given name."""
    cols = ("Email", "Password", "Type", "CanaryMode", "UiMode")
    try:
      row = self.db.Read(table="Users",
                         key=[username],
                         cols=cols,
                         txn_tag="ReadGRRUser")
    except NotFound as error:
      raise abstract_db.UnknownGRRUserError(username) from error

    user = objects_pb2.GRRUser(
        username=username,
        email=row[0],
        user_type=row[2],
        canary_mode=row[3],
        ui_mode=row[4],
    )

    if row[1]:
      pw = jobs_pb2.Password()
      pw.ParseFromString(row[1])
      user.password.CopyFrom(pw)

    return user

  @db_utils.CallLogged
  @db_utils.CallAccounted
  def ReadGRRUsers(
      self,
      offset: int = 0,
      count: Optional[int] = None,
  ) -> Sequence[objects_pb2.GRRUser]:
    """Reads GRR users with optional pagination, sorted by username."""
    if count is None:
      # TODO(b/196379916): We use the same value as F1 implementation does. But
      # a better solution would be to dynamically not ignore the `LIMIT` clause
      # in the query if the count parameter is not provided. This is not trivial
      # as queries have to be provided as docstrings (an utility that does it
      # on the fly has to be created to hack around this limitation).
      count = 2147483647

    users = []

    query = """
      SELECT u.Username, u.Email, u.Password, u.Type, u.CanaryMode, u.UiMode
        FROM Users AS u
       ORDER BY u.Username
       LIMIT {count}
      OFFSET {offset}
    """
    params = {
        "offset": offset,
        "count": count,
    }

    for row in self.db.ParamQuery(query, params, txn_tag="ReadGRRUsers"):
      username, email, password, typ, canary_mode, ui_mode = row

      user = objects_pb2.GRRUser(
          username=username,
          email=email,
          user_type=typ,
          canary_mode=canary_mode,
          ui_mode=ui_mode,
      )

      if password:
        user.password.ParseFromString(password)

      users.append(user)

    return users

  @db_utils.CallLogged
  @db_utils.CallAccounted
  def CountGRRUsers(self) -> int:
    """Returns the total count of GRR users."""
    query = """
      SELECT COUNT(*)
        FROM Users
    """

    (count,) = self.db.QuerySingle(query, txn_tag="CountGRRUsers")
    return count

  @db_utils.CallLogged
  @db_utils.CallAccounted
  def WriteApprovalRequest(self, request: objects_pb2.ApprovalRequest) -> str:
    """Writes an approval request object."""
    approval_id = str(uuid.uuid4())

    row = {
        "Requestor": request.requestor_username,
        "ApprovalId": approval_id,
        "CreationTime": spanner_lib.COMMIT_TIMESTAMP,
        "ExpirationTime": (
            rdfvalue.RDFDatetime()
            .FromMicrosecondsSinceEpoch(request.expiration_time)
            .AsDatetime()
        ),
        "Reason": request.reason,
        "NotifiedUsers": list(request.notified_users),
        "CcEmails": list(request.email_cc_addresses),
    }

    if request.approval_type == _APPROVAL_TYPE_CLIENT:
      row["SubjectClientId"] = request.subject_id
    elif request.approval_type == _APPROVAL_TYPE_HUNT:
      row["SubjectHuntId"] = request.subject_id
    elif request.approval_type == _APPROVAL_TYPE_CRON_JOB:
      row["SubjectCronJobId"] = request.subject_id
    else:
      raise ValueError(f"Unsupported approval type: {request.approval_type}")

    self.db.Insert(
        table="ApprovalRequests", row=row, txn_tag="WriteApprovalRequest"
    )

    return approval_id

  @db_utils.CallLogged
  @db_utils.CallAccounted
  def ReadApprovalRequest(
      self,
      username: str,
      approval_id: str,
  ) -> objects_pb2.ApprovalRequest:
    """Reads an approval request object with a given id."""

    query = """
      SELECT r.SubjectClientId, r.SubjectHuntId, r.SubjectCronJobId,
             r.Reason,
             r.CreationTime, r.ExpirationTime,
             r.NotifiedUsers, r.CcEmails,
             ARRAY(SELECT AS STRUCT g.Grantor,
                                    g.CreationTime
                     FROM ApprovalGrants AS g
                    WHERE g.Requestor = r.Requestor
                      AND g.ApprovalId = r.ApprovalId) AS Grants
        FROM ApprovalRequests AS r
       WHERE r.Requestor = {requestor}
         AND r.ApprovalId = {approval_id}
    """
    params = {
        "requestor": username,
        "approval_id": approval_id,
    }

    try:
      row = self.db.ParamQuerySingle(
          query, params, txn_tag="ReadApprovalRequest"
      )
    except NotFound:
      # TODO: Improve error message of this error class.
      raise abstract_db.UnknownApprovalRequestError(approval_id)

    subject_client_id, subject_hunt_id, subject_cron_job_id, *row = row
    reason, *row = row
    creation_time, expiration_time, *row = row
    notified_users, cc_emails, grants = row

    request = objects_pb2.ApprovalRequest(
        requestor_username=username,
        approval_id=approval_id,
        reason=reason,
        timestamp=RDFDatetime(creation_time).AsMicrosecondsSinceEpoch(),
        expiration_time=RDFDatetime(expiration_time).AsMicrosecondsSinceEpoch(),
        notified_users=notified_users,
        email_cc_addresses=cc_emails,
    )

    if subject_client_id is not None:
      request.subject_id = subject_client_id
      request.approval_type = _APPROVAL_TYPE_CLIENT
    elif subject_hunt_id is not None:
      request.subject_id = subject_hunt_id
      request.approval_type = _APPROVAL_TYPE_HUNT
    elif subject_cron_job_id is not None:
      request.subject_id = subject_cron_job_id
      request.approval_type = _APPROVAL_TYPE_CRON_JOB
    else:
      # This should not happen as the condition to one of these being always
      # set if enforced by the database schema.
      message = "No subject set for approval '%s' of user '%s'"
      logging.error(message, approval_id, username)

    for grantor, creation_time in grants:
      grant = objects_pb2.ApprovalGrant()
      grant.grantor_username = grantor
      grant.timestamp = RDFDatetime(creation_time).AsMicrosecondsSinceEpoch()
      request.grants.add().CopyFrom(grant)

    return request

  @db_utils.CallLogged
  @db_utils.CallAccounted
  def ReadApprovalRequests(
      self,
      username: str,
      typ: "objects_pb2.ApprovalRequest.ApprovalType",
      subject_id: Optional[str] = None,
      include_expired: Optional[bool] = False,
  ) -> Sequence[objects_pb2.ApprovalRequest]:
    """Reads approval requests of a given type for a given user."""
    requests = []

    # We need to use double curly braces for parameters as we also parametrize
    # over index that is substituted using standard Python templating.
    query = """
      SELECT r.ApprovalId,
             r.SubjectClientId, r.SubjectHuntId, r.SubjectCronJobId,
             r.Reason,
             r.CreationTime, r.ExpirationTime,
             r.NotifiedUsers, r.CcEmails,
             ARRAY(SELECT AS STRUCT g.Grantor,
                                    g.CreationTime
                     FROM ApprovalGrants AS g
                    WHERE g.Requestor = r.Requestor
                      AND g.ApprovalId = r.ApprovalId) AS Grants
        FROM ApprovalRequests@{{{{FORCE_INDEX={index}}}}} AS r
       WHERE r.Requestor = {{requestor}}
    """
    params = {
        "requestor": username,
    }

    # By default we use the "by requestor" index but in case a specific subject
    # is given we can also use a more specific index (overridden below).
    index = "ApprovalRequestsByRequestor"

    if typ == _APPROVAL_TYPE_CLIENT:
      query += " AND r.SubjectClientId IS NOT NULL"
      if subject_id is not None:
        query += " AND r.SubjectClientId = {{subject_client_id}}"
        params["subject_client_id"] = subject_id
        index = "ApprovalRequestsByRequestorSubjectClientId"
    elif typ == _APPROVAL_TYPE_HUNT:
      query += " AND r.SubjectHuntId IS NOT NULL"
      if subject_id is not None:
        query += " AND r.SubjectHuntId = {{subject_hunt_id}}"
        params["subject_hunt_id"] = subject_id
        index = "ApprovalRequestsByRequestorSubjectHuntId"
    elif typ == _APPROVAL_TYPE_CRON_JOB:
      query += " AND r.SubjectCronJobId IS NOT NULL"
      if subject_id is not None:
        query += " AND r.SubjectCronJobId = {{subject_cron_job_id}}"
        params["subject_cron_job_id"] = subject_id
        index = "ApprovalRequestsByRequestorSubjectCronJobId"
    else:
      raise ValueError(f"Unsupported approval type: {typ}")

    if not include_expired:
      query += " AND r.ExpirationTime > CURRENT_TIMESTAMP()"

    query = query.format(index=index)

    for row in self.db.ParamQuery(
        query, params, txn_tag="ReadApprovalRequests"
    ):
      approval_id, *row = row
      subject_client_id, subject_hunt_id, subject_cron_job_id, *row = row
      reason, *row = row
      creation_time, expiration_time, *row = row
      notified_users, cc_emails, grants = row

      request = objects_pb2.ApprovalRequest(
          requestor_username=username,
          approval_id=approval_id,
          reason=reason,
          timestamp=RDFDatetime(creation_time).AsMicrosecondsSinceEpoch(),
          expiration_time=RDFDatetime(
              expiration_time
          ).AsMicrosecondsSinceEpoch(),
          notified_users=notified_users,
          email_cc_addresses=cc_emails,
      )

      if subject_client_id is not None:
        request.subject_id = subject_client_id
        request.approval_type = _APPROVAL_TYPE_CLIENT
      elif subject_hunt_id is not None:
        request.subject_id = subject_hunt_id
        request.approval_type = _APPROVAL_TYPE_HUNT
      elif subject_cron_job_id is not None:
        request.subject_id = subject_cron_job_id
        request.approval_type = _APPROVAL_TYPE_CRON_JOB
      else:
        # This should not happen as the condition to one of these being always
        # set if enforced by the database schema.
        message = "No subject set for approval '%s' of user '%s'"
        logging.error(message, approval_id, username)

      for grantor, creation_time in grants:
        grant = objects_pb2.ApprovalGrant()
        grant.grantor_username = grantor
        grant.timestamp = RDFDatetime(creation_time).AsMicrosecondsSinceEpoch()
        request.grants.add().CopyFrom(grant)

      requests.append(request)

    return requests

  @db_utils.CallLogged
  @db_utils.CallAccounted
  def GrantApproval(
      self,
      requestor_username: str,
      approval_id: str,
      grantor_username: str,
  ) -> None:
    """Grants approval for a given request using given username."""
    row = {
        "Requestor": requestor_username,
        "ApprovalId": approval_id,
        "Grantor": grantor_username,
        "GrantId": str(uuid.uuid4()),
        "CreationTime": spanner_lib.COMMIT_TIMESTAMP,
    }

    self.db.Insert(table="ApprovalGrants", row=row, txn_tag="GrantApproval")

  @db_utils.CallLogged
  @db_utils.CallAccounted
  def WriteUserNotification(
      self,
      notification: objects_pb2.UserNotification,
  ) -> None:
    """Writes a notification for a given user."""
    row = {
        "Username": notification.username,
        "NotificationId": str(uuid.uuid4()),
        "Type": int(notification.notification_type),
        "State": int(notification.state),
        "CreationTime": spanner_lib.COMMIT_TIMESTAMP,
        "Message": notification.message,
    }
    if notification.reference:
      row["Reference"] = base64.b64encode(notification.reference.SerializeToString())

    try:
      self.db.Insert(
          table="UserNotifications", row=row, txn_tag="WriteUserNotification"
      )
    except NotFound:
      raise abstract_db.UnknownGRRUserError(notification.username)

  @db_utils.CallLogged
  @db_utils.CallAccounted
  def ReadUserNotifications(
      self,
      username: str,
      state: Optional["objects_pb2.UserNotification.State"] = None,
      timerange: Optional[
          Tuple[Optional[rdfvalue.RDFDatetime], Optional[rdfvalue.RDFDatetime]]
      ] = None,
  ) -> Sequence[objects_pb2.UserNotification]:
    """Reads notifications scheduled for a user within a given timerange."""
    notifications = []

    params = {
        "username": username,
    }
    query = """
      SELECT n.Type, n.State, n.CreationTime,
             n.Message, n.Reference
        FROM UserNotifications AS n
       WHERE n.Username = {username}
    """

    if state is not None:
      params["state"] = int(state)
      query += " AND n.state = {state}"

    if timerange is not None:
      begin_time, end_time = timerange
      if begin_time is not None:
        params["begin_time"] = begin_time.AsDatetime()
        query += " AND n.CreationTime >= {begin_time}"
      if end_time is not None:
        params["end_time"] = end_time.AsDatetime()
        query += " AND n.CreationTime <= {end_time}"

    query += " ORDER BY n.CreationTime DESC"

    for row in self.db.ParamQuery(
        query, params, txn_tag="ReadUserNotifications"
    ):
      typ, state, creation_time, message, reference = row

      notification = objects_pb2.UserNotification(
          username=username,
          notification_type=typ,
          state=state,
          timestamp=RDFDatetime(creation_time).AsMicrosecondsSinceEpoch(),
          message=message,
      )

      if reference:
        notification.reference.ParseFromString(reference)

      notifications.append(notification)

    return notifications

  @db_utils.CallLogged
  @db_utils.CallAccounted
  def UpdateUserNotifications(
      self,
      username: str,
      timestamps: Sequence[rdfvalue.RDFDatetime],
      state: Optional["objects_pb2.UserNotification.State"] = None,
  ):
    """Updates existing user notification objects."""
    # `UNNEST` used in the query does not like empty arrays, so we return early
    # in such cases.
    if not timestamps:
      return

    params = {
        "username": username,
        "state": int(state),
    }

    param_placeholders = ", ".join([f"{{ts{i}}}" for i in range(len(timestamps))])
    for i, timestamp in enumerate(timestamps):
        param_name = f"ts{i}"
        params[param_name] = timestamp.AsDatetime()

    query = f"""
      UPDATE UserNotifications n
         SET n.State = {state}
       WHERE n.Username = '{username}'
         AND n.CreationTime IN ({param_placeholders})
    """

    self.db.ParamExecute(query, params, txn_tag="UpdateUserNotifications")


def _HexApprovalID(approval_id: int) -> str:
  return f"{approval_id:016x}"


def _UnhexApprovalID(approval_id: str) -> int:
  return int(approval_id, base=16)



def RDFDatetime(time: datetime.datetime) -> rdfvalue.RDFDatetime:
  return rdfvalue.RDFDatetime.FromDatetime(time)


_APPROVAL_TYPE_CLIENT = objects_pb2.ApprovalRequest.APPROVAL_TYPE_CLIENT
_APPROVAL_TYPE_HUNT = objects_pb2.ApprovalRequest.APPROVAL_TYPE_HUNT
_APPROVAL_TYPE_CRON_JOB = objects_pb2.ApprovalRequest.APPROVAL_TYPE_CRON_JOB
