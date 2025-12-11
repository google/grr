#!/usr/bin/env python
"""Test classes for ACL-related testing."""

from typing import Optional

from grr_response_core.lib import rdfvalue
from grr_response_proto import objects_pb2
from grr_response_proto.api import user_pb2 as api_user_pb2
from grr_response_server import data_store
from grr_response_server.gui import api_call_context
from grr_response_server.gui.api_plugins import user as api_user
from grr_response_server.rdfvalues import objects as rdf_objects


def CreateUser(username) -> None:
  """Creates a user."""
  data_store.REL_DB.WriteGRRUser(username, canary_mode=True)


def CreateAdminUser(username):
  data_store.REL_DB.WriteGRRUser(
      username, user_type=objects_pb2.GRRUser.UserType.USER_TYPE_ADMIN
  )


def BuildClientApprovalRequest(
    client_id: Optional[str] = None,
    requestor_username: Optional[str] = None,
    reason: Optional[str] = None) -> rdf_objects.ApprovalRequest:
  return rdf_objects.ApprovalRequest(
      approval_type=rdf_objects.ApprovalRequest.ApprovalType
      .APPROVAL_TYPE_CLIENT,
      subject_id=client_id or "C.1234",
      requestor_username=requestor_username or "testuser",
      reason=reason or "foo/test1234",
      expiration_time=rdfvalue.RDFDatetime.Now() +
      rdfvalue.Duration.From(1, rdfvalue.DAYS))


class AclTestMixin(object):
  """Mixing providing ACL-related helper methods."""

  def CreateUser(self, username):
    return CreateUser(username)

  def CreateAdminUser(self, username):
    """Creates a user and makes it an admin."""
    return CreateAdminUser(username)

  def RequestClientApproval(self,
                            client_id,
                            reason="Running tests",
                            requestor=None,
                            email_cc_address=None,
                            approver=u"approver"):
    """Create an approval request to be sent to approver."""
    if not requestor:
      requestor = self.test_username

    self.CreateUser(requestor)
    self.CreateUser(approver)

    args = api_user_pb2.ApiCreateClientApprovalArgs(
        client_id=client_id,
        approval=api_user_pb2.ApiClientApproval(
            reason=reason,
            notified_users=[approver],
            email_cc_addresses=([email_cc_address] if email_cc_address else []),
        ),
    )
    handler = api_user.ApiCreateClientApprovalHandler()
    result = handler.Handle(
        args, context=api_call_context.ApiCallContext(username=requestor))

    return result.id

  def GrantClientApproval(self,
                          client_id,
                          requestor=None,
                          approval_id=None,
                          approver=u"approver",
                          admin=True):
    """Grant an approval from approver to delegate.

    Args:
      client_id: Client id.
      requestor: username string of the user receiving approval.
      approval_id: id of the approval to grant.
      approver: username string of the user granting approval.
      admin: If True, make approver an admin user.

    Raises:
      ValueError: if approval_id is empty.
    """
    if not approval_id:
      raise ValueError("approval_id can't be empty.")

    if not requestor:
      requestor = self.test_username

    self.CreateUser(requestor)
    if admin:
      self.CreateAdminUser(approver)
    else:
      self.CreateUser(approver)

    if not requestor:
      requestor = self.test_username

    args = api_user_pb2.ApiGrantClientApprovalArgs(
        client_id=client_id, username=requestor, approval_id=approval_id
    )
    handler = api_user.ApiGrantClientApprovalHandler()
    handler.Handle(
        args, context=api_call_context.ApiCallContext(username=approver))

  def RequestAndGrantClientApproval(self,
                                    client_id,
                                    requestor=None,
                                    reason="Running tests",
                                    approver=u"approver",
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
    requestor = requestor or self.test_username
    handler = api_user.ApiListClientApprovalsHandler()
    return handler.Handle(
        api_user_pb2.ApiListClientApprovalsArgs(),
        context=api_call_context.ApiCallContext(username=requestor),
    ).items

  def RequestHuntApproval(
      self,
      hunt_id: str,
      requestor: Optional[str] = None,
      reason: str = "Running tests",
      email_cc_address: Optional[list[str]] = None,
      approver: str = "approver",
  ) -> str:
    """Request hunt approval for a given hunt."""

    if not requestor:
      requestor = self.test_username

    self.CreateUser(requestor)
    self.CreateUser(approver)

    args = api_user_pb2.ApiCreateHuntApprovalArgs(
        hunt_id=hunt_id,
        approval=api_user_pb2.ApiHuntApproval(
            reason=reason,
            notified_users=[approver],
            email_cc_addresses=([email_cc_address] if email_cc_address else []),
        ),
    )
    handler = api_user.ApiCreateHuntApprovalHandler()
    result = handler.Handle(
        args, context=api_call_context.ApiCallContext(username=requestor))

    return result.id

  def GrantHuntApproval(self,
                        hunt_id,
                        requestor=None,
                        approval_id=None,
                        approver=u"approver",
                        admin=True):
    """Grants an approval for a given hunt."""

    if not approval_id:
      raise ValueError("approval_id can't be empty.")

    if not requestor:
      requestor = self.test_username

    self.CreateUser(requestor)
    if admin:
      self.CreateAdminUser(approver)
    else:
      self.CreateUser(approver)

    args = api_user_pb2.ApiGrantHuntApprovalArgs(
        hunt_id=hunt_id, username=requestor, approval_id=approval_id
    )
    handler = api_user.ApiGrantHuntApprovalHandler()
    handler.Handle(
        args, context=api_call_context.ApiCallContext(username=approver))

  def RequestAndGrantHuntApproval(self,
                                  hunt_id,
                                  requestor=None,
                                  reason="test",
                                  email_cc_address=None,
                                  approver=u"approver",
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
    requestor = requestor or self.test_username
    handler = api_user.ApiListHuntApprovalsHandler()
    return handler.Handle(
        api_user_pb2.ApiListHuntApprovalsArgs(),
        context=api_call_context.ApiCallContext(username=requestor),
    ).items

  def RequestCronJobApproval(
      self,
      cron_job_id: str,
      requestor: Optional[str] = None,
      reason: str = "Running tests",
      email_cc_address: Optional[list[str]] = None,
      approver: str = "approver",
  ) -> str:
    """Request cron job approval for a given cron job."""

    if not requestor:
      requestor = self.test_username

    self.CreateUser(requestor)
    self.CreateUser(approver)

    args = api_user_pb2.ApiCreateCronJobApprovalArgs(
        cron_job_id=cron_job_id,
        approval=api_user_pb2.ApiCronJobApproval(
            reason=reason,
            notified_users=[approver],
            email_cc_addresses=([email_cc_address] if email_cc_address else []),
        ),
    )
    handler = api_user.ApiCreateCronJobApprovalHandler()
    result = handler.Handle(
        args, context=api_call_context.ApiCallContext(username=requestor))

    return result.id

  def GrantCronJobApproval(self,
                           cron_job_id,
                           requestor=None,
                           approval_id=None,
                           approver="approver",
                           admin=True):
    """Grants an approval for a given cron job."""
    if not requestor:
      requestor = self.test_username

    if not approval_id:
      raise ValueError("approval_id can't be empty.")

    self.CreateUser(requestor)
    if admin:
      self.CreateAdminUser(approver)
    else:
      self.CreateUser(approver)

    args = api_user_pb2.ApiGrantCronJobApprovalArgs(
        cron_job_id=cron_job_id, username=requestor, approval_id=approval_id
    )
    handler = api_user.ApiGrantCronJobApprovalHandler()
    handler.Handle(
        args, context=api_call_context.ApiCallContext(username=approver))

  def RequestAndGrantCronJobApproval(self,
                                     cron_job_id,
                                     requestor=None,
                                     reason="test",
                                     email_cc_address=None,
                                     approver=u"approver",
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
    requestor = requestor or self.test_username
    handler = api_user.ApiListCronJobApprovalsHandler()
    return handler.Handle(
        api_user_pb2.ApiListCronJobApprovalsArgs(),
        context=api_call_context.ApiCallContext(username=requestor),
    ).items
