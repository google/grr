#!/usr/bin/env python
"""The in memory database methods for GRR users and approval handling."""

import os

from grr.lib import rdfvalue
from grr.lib import utils
from grr.server.grr_response_server import db
from grr.server.grr_response_server.rdfvalues import objects


class InMemoryDBUsersMixin(object):
  """InMemoryDB mixin for GRR users and approval related functions."""

  @utils.Synchronized
  def WriteGRRUser(self,
                   username,
                   password=None,
                   ui_mode=None,
                   canary_mode=None,
                   user_type=None):
    """Writes user object for a user with a given name."""
    u = self.users.setdefault(username, {"username": username})
    if password is not None:
      u["password"] = password
    if ui_mode is not None:
      u["ui_mode"] = ui_mode
    if canary_mode is not None:
      u["canary_mode"] = canary_mode
    if user_type is not None:
      u["user_type"] = user_type

  @utils.Synchronized
  def ReadGRRUser(self, username):
    """Reads a user object corresponding to a given name."""
    try:
      u = self.users[username]
      return objects.GRRUser(
          username=u["username"],
          password=u.get("password"),
          ui_mode=u.get("ui_mode"),
          canary_mode=u.get("canary_mode"),
          user_type=u.get("user_type"))
    except KeyError:
      raise db.UnknownGRRUserError("Can't find user with name: %s" % username)

  @utils.Synchronized
  def ReadAllGRRUsers(self):
    """Reads all GRR users."""
    for u in self.users.values():
      yield objects.GRRUser(
          username=u["username"],
          password=u.get("password"),
          ui_mode=u.get("ui_mode"),
          canary_mode=u.get("canary_mode"),
          user_type=u.get("user_type"))

  @utils.Synchronized
  def WriteApprovalRequest(self, approval_request):
    """Writes an approval request object."""
    approvals = self.approvals_by_username.setdefault(
        approval_request.requestor_username, {})

    approval_id = os.urandom(16).encode("hex")
    cloned_request = approval_request.Copy()
    cloned_request.timestamp = rdfvalue.RDFDatetime.Now()
    cloned_request.approval_id = approval_id
    approvals[approval_id] = cloned_request

    return approval_id

  @utils.Synchronized
  def ReadApprovalRequest(self, requestor_username, approval_id):
    """Reads an approval request object with a given id."""
    try:
      return self.approvals_by_username[requestor_username][approval_id]
    except KeyError:
      raise db.UnknownApprovalRequestError(
          "Can't find approval with id: %s" % approval_id)

  @utils.Synchronized
  def ReadApprovalRequests(self,
                           requestor_username,
                           approval_type,
                           subject_id=None,
                           include_expired=False):
    """Reads approval requests of a given type for a given user."""
    now = rdfvalue.RDFDatetime.Now()
    for approval in self.approvals_by_username.get(requestor_username,
                                                   {}).values():
      if approval.approval_type != approval_type:
        continue

      if subject_id and approval.subject_id != subject_id:
        continue

      if not include_expired and approval.expiration_time < now:
        continue

      yield approval

  @utils.Synchronized
  def GrantApproval(self, requestor_username, approval_id, grantor_username):
    """Grants approval for a given request using given username."""
    try:
      approval = self.approvals_by_username[requestor_username][approval_id]
      approval.grants.append(
          objects.ApprovalGrant(
              grantor_username=grantor_username,
              timestamp=rdfvalue.RDFDatetime.Now()))
    except KeyError:
      raise db.UnknownApprovalRequestError(
          "Can't find approval with id: %s" % approval_id)

  @utils.Synchronized
  def WriteUserNotification(self, notification):
    """Writes a notification for a given user."""
    cloned_notification = notification.Copy()
    if not cloned_notification.timestamp:
      cloned_notification.timestamp = rdfvalue.RDFDatetime.Now()

    self.notifications_by_username.setdefault(cloned_notification.username,
                                              []).append(cloned_notification)

  @utils.Synchronized
  def ReadUserNotifications(self, username, state=None, timerange=None):
    """Reads notifications scheduled for a user within a given timerange."""
    from_time, to_time = self._ParseTimeRange(timerange)

    result = []
    for n in self.notifications_by_username.get(username, []):
      if from_time <= n.timestamp <= to_time and (state is None or
                                                  n.state == state):
        result.append(n.Copy())

    return sorted(result, key=lambda r: r.timestamp, reverse=True)

  @utils.Synchronized
  def UpdateUserNotifications(self, username, timestamps, state=None):
    """Updates existing user notification objects."""
    if not timestamps:
      return

    for n in self.notifications_by_username.get(username, []):
      if n.timestamp in timestamps:
        n.state = state
