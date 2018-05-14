#!/usr/bin/env python
"""Test classes for ACL-related testing."""

from grr.lib.rdfvalues import objects as rdf_objects

from grr.server.grr_response_server import access_control

from grr.server.grr_response_server import aff4
from grr.server.grr_response_server import data_store
from grr.server.grr_response_server.aff4_objects import users

from grr.server.grr_response_server.gui.api_plugins import user as api_user


def CreateUser(username):
  """Creates a user."""
  if data_store.RelationalDBReadEnabled():
    data_store.REL_DB.WriteGRRUser(username)

  user = aff4.FACTORY.Create("aff4:/users/%s" % username, users.GRRUser)
  user.Flush()
  return user


class AclTestMixin(object):
  """Mixing providing ACL-related helper methods."""

  def CreateUser(self, username):
    return CreateUser(username)

  def CreateAdminUser(self, username):
    """Creates a user and makes it an admin."""
    if data_store.RelationalDBReadEnabled():
      data_store.REL_DB.WriteGRRUser(
          username, user_type=rdf_objects.GRRUser.UserType.USER_TYPE_ADMIN)

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

    self.CreateUser(requestor)
    self.CreateUser(approver)

    args = api_user.ApiCreateClientApprovalArgs(
        client_id=client_id,
        approval=api_user.ApiClientApproval(
            reason=reason,
            notified_users=[approver],
            email_cc_addresses=([email_cc_address]
                                if email_cc_address else [])))
    handler = api_user.ApiCreateClientApprovalHandler()
    result = handler.Handle(
        args, token=access_control.ACLToken(username=requestor))

    return result.id

  def GrantClientApproval(self,
                          client_id,
                          requestor=None,
                          approval_id=None,
                          approver="approver",
                          admin=True):
    """Grant an approval from approver to delegate.

    Args:
      client_id: ClientURN
      requestor: username string of the user receiving approval.
      approval_id: id of the approval to grant.
      approver: username string of the user granting approval.
      admin: If True, make approver an admin user.
    Raises:
      ValueError: if approval_id is empty.
    """
    if not approval_id:
      raise ValueError("approval_id can't be empty.")

    if hasattr(client_id, "Basename"):
      client_id = client_id.Basename()

    if not requestor:
      requestor = self.token.username

    self.CreateUser(requestor)
    if admin:
      self.CreateAdminUser(approver)
    else:
      self.CreateUser(approver)

    if not requestor:
      requestor = self.token.username

    args = api_user.ApiGrantClientApprovalArgs(
        client_id=client_id, username=requestor, approval_id=approval_id)
    handler = api_user.ApiGrantClientApprovalHandler()
    handler.Handle(args, token=access_control.ACLToken(username=approver))

  def RequestAndGrantClientApproval(self,
                                    client_id,
                                    requestor=None,
                                    reason=None,
                                    approver="approver",
                                    admin=True):
    """Request and grant client approval for a given client."""

    approval_id = self.RequestClientApproval(
        client_id, requestor=requestor, approver=approver, reason=reason)
    self.GrantClientApproval(
        client_id,
        requestor=requestor,
        approval_id=approval_id,
        approver=approver,
        admin=admin)
    return approval_id

  def ListClientApprovals(self, requestor=None):
    requestor = requestor or self.token.username
    handler = api_user.ApiListClientApprovalsHandler()
    return handler.Handle(
        api_user.ApiListClientApprovalsArgs(),
        token=access_control.ACLToken(username=requestor)).items

  def RequestHuntApproval(self,
                          hunt_id,
                          requestor=None,
                          reason=None,
                          email_cc_address=None,
                          approver="approver"):
    """Request hunt approval for a given hunt."""

    if not requestor:
      requestor = self.token.username

    if not reason:
      reason = self.token.reason

    self.CreateUser(requestor)
    self.CreateUser(approver)

    args = api_user.ApiCreateHuntApprovalArgs(
        hunt_id=hunt_id,
        approval=api_user.ApiHuntApproval(
            reason=reason,
            notified_users=[approver],
            email_cc_addresses=([email_cc_address]
                                if email_cc_address else [])))
    handler = api_user.ApiCreateHuntApprovalHandler()
    result = handler.Handle(
        args, token=access_control.ACLToken(username=requestor))

    return result.id

  def GrantHuntApproval(self,
                        hunt_id,
                        requestor=None,
                        approval_id=None,
                        approver="approver",
                        admin=True):
    """Grants an approval for a given hunt."""

    if not approval_id:
      raise ValueError("approval_id can't be empty.")

    if not requestor:
      requestor = self.token.username

    self.CreateUser(requestor)
    if admin:
      self.CreateAdminUser(approver)
    else:
      self.CreateUser(approver)

    args = api_user.ApiGrantHuntApprovalArgs(
        hunt_id=hunt_id, username=requestor, approval_id=approval_id)
    handler = api_user.ApiGrantHuntApprovalHandler()
    handler.Handle(args, token=access_control.ACLToken(username=approver))

  def RequestAndGrantHuntApproval(self,
                                  hunt_id,
                                  requestor=None,
                                  reason=None,
                                  email_cc_address=None,
                                  approver="approver",
                                  admin=True):
    """Requests and grants hunt approval for a given hunt."""

    approval_id = self.RequestHuntApproval(
        hunt_id,
        requestor=requestor,
        reason=reason,
        email_cc_address=email_cc_address,
        approver=approver)
    self.GrantHuntApproval(
        hunt_id,
        requestor=requestor,
        approval_id=approval_id,
        approver=approver,
        admin=admin)
    return approval_id

  def ListHuntApprovals(self, requestor=None):
    requestor = requestor or self.token.username
    handler = api_user.ApiListHuntApprovalsHandler()
    return handler.Handle(
        api_user.ApiListHuntApprovalsArgs(),
        token=access_control.ACLToken(username=requestor)).items

  def RequestCronJobApproval(self,
                             cron_job_id,
                             requestor=None,
                             reason=None,
                             email_cc_address=None,
                             approver="approver"):
    """Request cron job approval for a given cron job."""

    if not requestor:
      requestor = self.token.username

    if not reason:
      reason = self.token.reason

    self.CreateUser(requestor)
    self.CreateUser(approver)

    args = api_user.ApiCreateCronJobApprovalArgs(
        cron_job_id=cron_job_id,
        approval=api_user.ApiCronJobApproval(
            reason=reason,
            notified_users=[approver],
            email_cc_addresses=([email_cc_address]
                                if email_cc_address else [])))
    handler = api_user.ApiCreateCronJobApprovalHandler()
    result = handler.Handle(
        args, token=access_control.ACLToken(username=requestor))

    return result.id

  def GrantCronJobApproval(self,
                           cron_job_id,
                           requestor=None,
                           approval_id=None,
                           approver="approver",
                           admin=True):
    """Grants an approval for a given cron job."""
    if not requestor:
      requestor = self.token.username

    if not approval_id:
      raise ValueError("approval_id can't be empty.")

    self.CreateUser(requestor)
    if admin:
      self.CreateAdminUser(approver)
    else:
      self.CreateUser(approver)

    args = api_user.ApiGrantCronJobApprovalArgs(
        cron_job_id=cron_job_id, username=requestor, approval_id=approval_id)
    handler = api_user.ApiGrantCronJobApprovalHandler()
    handler.Handle(args, token=access_control.ACLToken(username=approver))

  def RequestAndGrantCronJobApproval(self,
                                     cron_job_id,
                                     requestor=None,
                                     reason=None,
                                     email_cc_address=None,
                                     approver="approver",
                                     admin=True):
    """Requests and grants an approval for a given cron job."""
    approval_id = self.RequestCronJobApproval(
        cron_job_id,
        requestor=requestor,
        reason=reason,
        email_cc_address=email_cc_address,
        approver=approver)
    self.GrantCronJobApproval(
        cron_job_id,
        requestor=requestor,
        approval_id=approval_id,
        approver=approver,
        admin=admin)
    return approval_id

  def ListCronJobApprovals(self, requestor=None):
    requestor = requestor or self.token.username
    handler = api_user.ApiListCronJobApprovalsHandler()
    return handler.Handle(
        api_user.ApiListCronJobApprovalsArgs(),
        token=access_control.ACLToken(username=requestor)).items
