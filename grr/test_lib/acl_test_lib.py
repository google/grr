#!/usr/bin/env python
"""Test classes for ACL-related testing."""

from grr.lib import rdfvalue
from grr.server import access_control
from grr.server import aff4

from grr.server.aff4_objects import security
from grr.server.aff4_objects import users


class AclTestMixin(object):
  """Mixing providing ACL-related helper methods."""

  def CreateUser(self, username):
    """Creates a user."""
    user = aff4.FACTORY.Create(
        "aff4:/users/%s" % username, users.GRRUser, token=self.token.SetUID())
    user.Flush()
    return user

  def CreateAdminUser(self, username):
    """Creates a user and makes it an admin."""
    with self.CreateUser(username) as user:
      user.SetLabel("admin", owner="GRR")

  def RequestClientApproval(self, client_id, token=None, approver="approver"):
    """Create an approval request to be sent to approver."""
    requestor = security.ClientApprovalRequestor(
        subject_urn=client_id,
        reason=token.reason,
        approver=approver,
        token=token)
    return requestor.Request()

  def GrantClientApproval(self,
                          client_id,
                          delegate,
                          reason="testing",
                          approver="approver"):
    """Grant an approval from approver to delegate.

    Args:
      client_id: ClientURN
      delegate: username string of the user receiving approval.
      reason: reason for approval request.
      approver: username string of the user granting approval.
    """
    self.CreateAdminUser(approver)

    approver_token = access_control.ACLToken(username=approver)
    grantor = security.ClientApprovalGrantor(
        subject_urn=client_id,
        reason=reason,
        delegate=delegate,
        token=approver_token)
    grantor.Grant()

  def RequestAndGrantClientApproval(self,
                                    client_id,
                                    token=None,
                                    approver="approver"):
    token = token or self.token
    approval_urn = self.RequestClientApproval(
        client_id, token=token, approver=approver)
    self.GrantClientApproval(
        client_id, token.username, reason=token.reason, approver=approver)
    return approval_urn

  def GrantHuntApproval(self, hunt_urn, token=None):
    """Grants an approval for a given hunt."""
    token = token or self.token

    # Create the approval and approve it.
    security.HuntApprovalRequestor(
        subject_urn=hunt_urn,
        reason=token.reason,
        approver="approver",
        token=token).Request()

    self.CreateAdminUser("approver")

    approver_token = access_control.ACLToken(username="approver")
    security.HuntApprovalGrantor(
        subject_urn=hunt_urn,
        reason=token.reason,
        delegate=token.username,
        token=approver_token).Grant()

  def GrantCronJobApproval(self, cron_job_urn, token=None):
    """Grants an approval for a given cron job."""
    token = token or self.token

    # Create cron job approval and approve it.
    security.CronJobApprovalRequestor(
        subject_urn=rdfvalue.RDFURN(cron_job_urn),
        reason=self.token.reason,
        approver="approver",
        token=token).Request()

    self.CreateAdminUser("approver")

    approver_token = access_control.ACLToken(username="approver")
    security.CronJobApprovalGrantor(
        subject_urn=cron_job_urn,
        reason=token.reason,
        delegate=token.username,
        token=approver_token).Grant()
