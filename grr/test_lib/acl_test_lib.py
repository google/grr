#!/usr/bin/env python
"""Test classes for ACL-related testing."""

from __future__ import annotations

from collections.abc import Sequence

from grr_response_proto import objects_pb2
from grr_response_proto.api import user_pb2 as api_user_pb2
from grr_response_server import data_store
from grr_response_server.gui import api_call_context
from grr_response_server.gui.api_plugins import user as api_user


def CreateUser(username: str) -> None:
  """Creates a user."""
  data_store.REL_DB.WriteGRRUser(username, canary_mode=True)


def CreateAdminUser(username: str) -> None:
  data_store.REL_DB.WriteGRRUser(
      username, user_type=objects_pb2.GRRUser.UserType.USER_TYPE_ADMIN
  )


class AclTestMixin(object):
  """Mixing providing ACL-related helper methods."""

  test_username: str

  def CreateUser(self, username: str) -> None:
    return CreateUser(username)

  def CreateAdminUser(self, username: str) -> None:
    """Creates a user and makes it an admin."""
    return CreateAdminUser(username)

  def RequestClientApproval(
      self,
      client_id: str,
      reason: str = "Running tests",
      requestor: str | None = None,
      email_cc_address: str | None = None,
      approver: str = "approver",
  ) -> str:
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

  def GrantClientApproval(
      self,
      client_id: str,
      requestor: str | None = None,
      approval_id: str | None = None,
      approver: str = "approver",
      admin: bool = True,
  ) -> None:
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

  def RequestAndGrantClientApproval(
      self,
      client_id: str,
      requestor: str | None = None,
      reason: str = "Running tests",
      approver: str = "approver",
      admin: bool = True,
  ) -> str:
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

  def ListClientApprovals(
      self, requestor: str | None = None
  ) -> Sequence[api_user_pb2.ApiClientApproval]:
    requestor = requestor or self.test_username
    handler = api_user.ApiListClientApprovalsHandler()
    return handler.Handle(
        api_user_pb2.ApiListClientApprovalsArgs(),
        context=api_call_context.ApiCallContext(username=requestor),
    ).items

  def RequestHuntApproval(
      self,
      hunt_id: str,
      requestor: str | None = None,
      reason: str = "Running tests",
      email_cc_address: str | None = None,
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

  def GrantHuntApproval(
      self,
      hunt_id: str,
      requestor: str | None = None,
      approval_id: str | None = None,
      approver: str = "approver",
      admin: bool = True,
  ) -> None:
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

  def RequestAndGrantHuntApproval(
      self,
      hunt_id: str,
      requestor: str | None = None,
      reason: str = "test",
      email_cc_address: str | None = None,
      approver: str = "approver",
      admin: bool = True,
  ) -> str:
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

  def ListHuntApprovals(
      self, requestor: str | None = None
  ) -> Sequence[api_user_pb2.ApiHuntApproval]:
    requestor = requestor or self.test_username
    handler = api_user.ApiListHuntApprovalsHandler()
    return handler.Handle(
        api_user_pb2.ApiListHuntApprovalsArgs(),
        context=api_call_context.ApiCallContext(username=requestor),
    ).items
