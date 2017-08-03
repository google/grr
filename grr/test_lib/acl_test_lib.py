#!/usr/bin/env python
"""Test classes for ACL-related testing."""

from grr.lib import access_control
from grr.lib import aff4
from grr.lib import flow
from grr.lib import rdfvalue

from grr.lib.aff4_objects import security
from grr.lib.aff4_objects import users

from grr.lib.rdfvalues import client as rdf_client


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
      user.SetLabels("admin", owner="GRR")

  def RequestClientApproval(self, client_id, token=None, approver="approver"):
    """Create an approval request to be sent to approver."""
    flow_urn = flow.GRRFlow.StartFlow(
        client_id=client_id,
        flow_name=security.RequestClientApprovalFlow.__name__,
        reason=token.reason,
        subject_urn=rdf_client.ClientURN(client_id),
        approver=approver,
        token=token)
    flow_fd = aff4.FACTORY.Open(
        flow_urn, aff4_type=flow.GRRFlow, token=self.token)
    return flow_fd.state.approval_urn

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
    flow.GRRFlow.StartFlow(
        client_id=client_id,
        flow_name=security.GrantClientApprovalFlow.__name__,
        reason=reason,
        delegate=delegate,
        subject_urn=rdf_client.ClientURN(client_id),
        token=approver_token)

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
    flow.GRRFlow.StartFlow(
        flow_name=security.RequestHuntApprovalFlow.__name__,
        subject_urn=rdfvalue.RDFURN(hunt_urn),
        reason=token.reason,
        approver="approver",
        token=token)

    self.CreateAdminUser("approver")

    approver_token = access_control.ACLToken(username="approver")
    flow.GRRFlow.StartFlow(
        flow_name=security.GrantHuntApprovalFlow.__name__,
        subject_urn=rdfvalue.RDFURN(hunt_urn),
        reason=token.reason,
        delegate=token.username,
        token=approver_token)

  def GrantCronJobApproval(self, cron_job_urn, token=None):
    """Grants an approval for a given cron job."""
    token = token or self.token

    # Create cron job approval and approve it.
    flow.GRRFlow.StartFlow(
        flow_name=security.RequestCronJobApprovalFlow.__name__,
        subject_urn=rdfvalue.RDFURN(cron_job_urn),
        reason=self.token.reason,
        approver="approver",
        token=token)

    self.CreateAdminUser("approver")

    approver_token = access_control.ACLToken(username="approver")
    flow.GRRFlow.StartFlow(
        flow_name=security.GrantCronJobApprovalFlow.__name__,
        subject_urn=rdfvalue.RDFURN(cron_job_urn),
        reason=token.reason,
        delegate=token.username,
        token=approver_token)
