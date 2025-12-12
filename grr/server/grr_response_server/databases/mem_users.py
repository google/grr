#!/usr/bin/env python
"""The in memory database methods for GRR users and approval handling."""

from collections.abc import Sequence
import os
from typing import Optional

from grr_response_core.lib import rdfvalue
from grr_response_core.lib import utils
from grr_response_core.lib.util import text
from grr_response_proto import flows_pb2
from grr_response_proto import jobs_pb2
from grr_response_proto import objects_pb2
from grr_response_proto import user_pb2
from grr_response_server.databases import db


class InMemoryDBUsersMixin(object):
  """InMemoryDB mixin for GRR users and approval related functions."""

  users: dict[str, objects_pb2.GRRUser]
  notifications_by_username: dict[str, list[objects_pb2.UserNotification]]
  approvals_by_username: dict[str, dict[str, objects_pb2.ApprovalRequest]]
  scheduled_flows: dict[tuple[str, str, str], flows_pb2.ScheduledFlow]

  @utils.Synchronized
  def WriteGRRUser(
      self,
      username: str,
      password: Optional[jobs_pb2.Password] = None,
      ui_mode: Optional["user_pb2.GUISettings.UIMode"] = None,
      canary_mode: Optional[bool] = None,
      user_type: Optional["objects_pb2.GRRUser.UserType"] = None,
      email: Optional[str] = None,
  ) -> None:
    """Writes user object for a user with a given name."""
    u = self.users.setdefault(username, objects_pb2.GRRUser(username=username))
    if password is not None:
      u.password.CopyFrom(password)
    if ui_mode is not None:
      u.ui_mode = ui_mode
    if canary_mode is not None:
      u.canary_mode = canary_mode
    if user_type is not None:
      u.user_type = user_type
    if email is not None:
      u.email = email

  @utils.Synchronized
  def ReadGRRUser(self, username: str) -> objects_pb2.GRRUser:
    """Reads a user object corresponding to a given name."""
    try:
      clone = objects_pb2.GRRUser()
      clone.CopyFrom(self.users[username])
      return clone
    except KeyError:
      raise db.UnknownGRRUserError(username)

  @utils.Synchronized
  def ReadGRRUsers(
      self, offset: int = 0, count: Optional[int] = None
  ) -> Sequence[objects_pb2.GRRUser]:
    """Reads GRR users with optional pagination, sorted by username."""
    if count is None:
      count = len(self.users)

    users = sorted(self.users.values(), key=lambda user: user.username)
    clones = []
    for user in users[offset : offset + count]:
      clone = objects_pb2.GRRUser()
      clone.CopyFrom(user)
      clones.append(clone)
    return clones

  @utils.Synchronized
  def CountGRRUsers(self) -> int:
    """Returns the total count of GRR users."""
    return len(self.users)

  @utils.Synchronized
  def DeleteGRRUser(self, username: str) -> None:
    """Deletes the user and all related metadata with the given username."""
    try:
      del self.approvals_by_username[username]
    except KeyError:
      pass  # No approvals to delete for this user.

    for approvals in self.approvals_by_username.values():
      for approval in approvals.values():
        grants = [g for g in approval.grants if g.grantor_username != username]
        if len(grants) != len(approval.grants):
          # TODO: Replace with `clear()` once upgraded.
          del approval.grants[:]
          for g in grants:
            approval.grants.add().CopyFrom(g)

    try:
      del self.notifications_by_username[username]
    except KeyError:
      pass  # No notifications to delete for this user.

    for sf in list(self.scheduled_flows.values()):
      if sf.creator == username:
        # DeleteScheduledFlow is implemented in the db.Database class.
        self.DeleteScheduledFlow(sf.client_id, username, sf.scheduled_flow_id)  # pytype: disable=attribute-error

    try:
      del self.users[username]
    except KeyError:
      raise db.UnknownGRRUserError(username)

  @utils.Synchronized
  def WriteApprovalRequest(
      self, approval_request: objects_pb2.ApprovalRequest
  ) -> str:
    """Writes an approval request object."""
    approvals_by_id = self.approvals_by_username.setdefault(
        approval_request.requestor_username, {}
    )

    approval_id = text.Hexify(os.urandom(16))
    cloned_request = objects_pb2.ApprovalRequest()
    cloned_request.CopyFrom(approval_request)
    cloned_request.timestamp = (
        rdfvalue.RDFDatetime.Now().AsMicrosecondsSinceEpoch()
    )
    cloned_request.approval_id = approval_id
    approvals_by_id[approval_id] = cloned_request

    return approval_id

  @utils.Synchronized
  def ReadApprovalRequest(
      self, requestor_username: str, approval_id: str
  ) -> objects_pb2.ApprovalRequest:
    """Reads an approval request object with a given id."""
    try:
      res = objects_pb2.ApprovalRequest()
      res.CopyFrom(self.approvals_by_username[requestor_username][approval_id])
      return res
    except KeyError as e:
      raise db.UnknownApprovalRequestError(
          "Can't find approval with id: %s" % approval_id
      ) from e

  @utils.Synchronized
  def ReadApprovalRequests(
      self,
      requestor_username: str,
      approval_type: "objects_pb2.ApprovalRequest.ApprovalType",
      subject_id: Optional[str] = None,
      include_expired: bool = False,
  ) -> Sequence[objects_pb2.ApprovalRequest]:
    """Reads approval requests of a given type for a given user."""
    now = rdfvalue.RDFDatetime.Now().AsMicrosecondsSinceEpoch()

    result = []
    approvals_by_id = self.approvals_by_username.get(requestor_username, {})
    for approval in approvals_by_id.values():
      if approval.approval_type != approval_type:
        continue

      if subject_id and approval.subject_id != subject_id:
        continue

      if not include_expired and approval.expiration_time < now:
        continue

      clone = objects_pb2.ApprovalRequest()
      clone.CopyFrom(approval)
      result.append(clone)

    return result

  @utils.Synchronized
  def GrantApproval(
      self, requestor_username: str, approval_id: str, grantor_username: str
  ) -> None:
    """Grants approval for a given request using given username."""
    try:
      approval = self.approvals_by_username[requestor_username][approval_id]
      grant = objects_pb2.ApprovalGrant(
          grantor_username=grantor_username,
          timestamp=rdfvalue.RDFDatetime.Now().AsMicrosecondsSinceEpoch(),
      )
      approval.grants.add().CopyFrom(grant)
    except KeyError as e:
      raise db.UnknownApprovalRequestError(
          f"Can't find approval with id: {approval_id}"
      ) from e

  @utils.Synchronized
  def WriteUserNotification(self, notification: objects_pb2.UserNotification):
    """Writes a notification for a given user."""
    if notification.username not in self.users:
      raise db.UnknownGRRUserError(notification.username)

    cloned_notification = objects_pb2.UserNotification()
    cloned_notification.CopyFrom(notification)
    if not cloned_notification.timestamp:
      cloned_notification.timestamp = (
          rdfvalue.RDFDatetime.Now().AsMicrosecondsSinceEpoch()
      )

    user_notifications = self.notifications_by_username.setdefault(
        cloned_notification.username, []
    )
    user_notifications.append(cloned_notification)

  @utils.Synchronized
  def ReadUserNotifications(
      self,
      username: str,
      state: Optional["objects_pb2.UserNotification.State"] = None,
      timerange: Optional[
          tuple[rdfvalue.RDFDatetime, rdfvalue.RDFDatetime]
      ] = None,
  ) -> Sequence[objects_pb2.UserNotification]:
    """Reads notifications scheduled for a user within a given timerange."""
    # ReadUserNotifications is implemented in the db.Database class.
    from_time, to_time = self._ParseTimeRange(timerange)  # pytype: disable=attribute-error

    result = []
    from_time_micros = from_time.AsMicrosecondsSinceEpoch()
    to_time_micros = to_time.AsMicrosecondsSinceEpoch()
    for n in self.notifications_by_username.get(username, []):
      if from_time_micros <= n.timestamp <= to_time_micros and (
          state is None or n.state == state
      ):
        clone = objects_pb2.UserNotification()
        clone.CopyFrom(n)
        result.append(clone)

    return sorted(result, key=lambda r: r.timestamp, reverse=True)

  @utils.Synchronized
  def UpdateUserNotifications(
      self,
      username: str,
      timestamps: Sequence[rdfvalue.RDFDatetime],
      state: Optional["objects_pb2.UserNotification.State"] = None,
  ):
    """Updates existing user notification objects."""
    if not timestamps:
      return

    proto_timestamps = [t.AsMicrosecondsSinceEpoch() for t in timestamps]

    for n in self.notifications_by_username.get(username, []):
      if n.timestamp in proto_timestamps:
        n.state = state
