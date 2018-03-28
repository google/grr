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

  def RequestClientApproval(self,
                            client_id,
                            reason=None,
                            requestor=None,
                            email_cc_address=None,
                            approver="approver"):
    """Create an approval request to be sent to approver."""
    if hasattr(client_id, "Basename"):
      client_id = client_id.Basename()

    if not requestor:
      requestor = self.token.username

    if not reason:
      reason = self.token.reason

    requestor = security.ClientApprovalRequestor(
        subject_urn=client_id,
        reason=reason,
        approver=approver,
        email_cc_address=email_cc_address,
        token=access_control.ACLToken(username=requestor))
    return requestor.Request().Basename()

  def GrantClientApproval(self,
                          client_id,
                          reason=None,
                          requestor=None,
                          approver="approver"):
    """Grant an approval from approver to delegate.

    Args:
      client_id: ClientURN
      reason: reason for approval request.
      requestor: username string of the user receiving approval.
      approver: username string of the user granting approval.
    """
    if hasattr(client_id, "Basename"):
      client_id = client_id.Basename()

    self.CreateAdminUser(approver)

    if not requestor:
      requestor = self.token.username

    if not reason:
      reason = self.token.reason

    approver_token = access_control.ACLToken(username=approver)
    grantor = security.ClientApprovalGrantor(
        subject_urn=client_id,
        reason=reason,
        delegate=requestor,
        token=approver_token)
    grantor.Grant()

  def RequestAndGrantClientApproval(self,
                                    client_id,
                                    requestor=None,
                                    reason=None,
                                    approver="approver"):
    """Request and grant client approval for a given client."""

    approval_id = self.RequestClientApproval(
        client_id, requestor=requestor, approver=approver, reason=reason)
    self.GrantClientApproval(
        client_id, requestor=requestor, reason=reason, approver=approver)
    return approval_id

  def RequestHuntApproval(self,
                          hunt_id,
                          requestor=None,
                          reason=None,
                          approver="approver"):
    """Request hunt approval for a given hunt."""

    if not requestor:
      requestor = self.token.username

    if not reason:
      reason = self.token.reason

    token = access_control.ACLToken(username=requestor)
    requestor = security.HuntApprovalRequestor(
        subject_urn=rdfvalue.RDFURN("hunts").Add(hunt_id),
        reason=reason,
        approver=approver,
        token=token)
    return requestor.Request().Basename()

  def GrantHuntApproval(self,
                        hunt_id,
                        requestor=None,
                        reason=None,
                        approver="approver"):
    """Grants an approval for a given hunt."""
    if not requestor:
      requestor = self.token.username

    if not reason:
      reason = self.token.reason

    self.CreateAdminUser(approver)

    approver_token = access_control.ACLToken(username=approver)
    security.HuntApprovalGrantor(
        subject_urn=rdfvalue.RDFURN("hunts").Add(hunt_id),
        reason=reason,
        delegate=requestor,
        token=approver_token).Grant()

  def RequestAndGrantHuntApproval(self,
                                  hunt_id,
                                  requestor=None,
                                  reason=None,
                                  approver="approver"):
    approval_id = self.RequestHuntApproval(
        hunt_id, requestor=requestor, reason=reason, approver=approver)
    self.GrantHuntApproval(
        hunt_id, requestor=requestor, reason=reason, approver=approver)
    return approval_id

  def RequestCronJobApproval(self,
                             cron_job_id,
                             requestor=None,
                             reason=None,
                             approver="approver"):
    """Request cron job approval for a given cron job."""

    if not requestor:
      requestor = self.token.username

    if not reason:
      reason = self.token.reason

    requestor = security.CronJobApprovalRequestor(
        subject_urn=rdfvalue.RDFURN("cron").Add(cron_job_id),
        reason=reason,
        approver=approver,
        token=access_control.ACLToken(username=requestor))
    return requestor.Request().Basename()

  def GrantCronJobApproval(self,
                           cron_job_id,
                           requestor=None,
                           reason=None,
                           approver="approver"):
    """Grants an approval for a given cron job."""
    if not requestor:
      requestor = self.token.username

    if not reason:
      reason = self.token.reason

    self.CreateAdminUser(approver)

    approver_token = access_control.ACLToken(username=approver)
    security.CronJobApprovalGrantor(
        subject_urn=rdfvalue.RDFURN("cron").Add(cron_job_id),
        reason=reason,
        delegate=requestor,
        token=approver_token).Grant()

  def RequestAndGrantCronJobApproval(self,
                                     cron_job_id,
                                     requestor=None,
                                     reason=None,
                                     approver="approver"):
    approval_id = self.RequestCronJobApproval(
        cron_job_id, requestor=requestor, reason=reason, approver=approver)
    self.GrantCronJobApproval(
        cron_job_id, requestor=requestor, reason=reason, approver=approver)
    return approval_id
