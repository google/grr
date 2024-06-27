#!/usr/bin/env python
"""Approvals checking logic."""

from grr_response_core import config
from grr_response_core.lib import rdfvalue
from grr_response_proto import objects_pb2
from grr_response_server import access_control
from grr_response_server import data_store
from grr_response_server.authorization import client_approval_auth


def BuildLegacySubject(
    subject_id: str,
    approval_type: objects_pb2.ApprovalRequest.ApprovalType,
) -> str:
  """Builds a legacy AFF4 urn string for a given subject and approval type."""

  if (
      approval_type
      == objects_pb2.ApprovalRequest.ApprovalType.APPROVAL_TYPE_CLIENT
  ):
    return "aff4:/%s" % subject_id
  elif (
      approval_type
      == objects_pb2.ApprovalRequest.ApprovalType.APPROVAL_TYPE_HUNT
  ):
    return "aff4:/hunts/%s" % subject_id
  elif (
      approval_type
      == objects_pb2.ApprovalRequest.ApprovalType.APPROVAL_TYPE_CRON_JOB
  ):
    return "aff4:/cron/%s" % subject_id

  raise ValueError("Invalid approval type.")


def _CheckExpired(approval_request: objects_pb2.ApprovalRequest) -> None:
  if approval_request.expiration_time < int(rdfvalue.RDFDatetime.Now()):
    raise access_control.UnauthorizedAccess(
        "Approval request is expired.",
        subject=BuildLegacySubject(
            approval_request.subject_id, approval_request.approval_type
        ),
    )


def _CheckHasEnoughGrants(approval_request: objects_pb2.ApprovalRequest):
  approvers_required = config.CONFIG["ACL.approvers_required"]
  approvers = set(g.grantor_username for g in approval_request.grants)

  missing = approvers_required - len(approvers)
  if missing > 0:
    msg = "Need at least %d additional approver%s for access." % (
        missing,
        "s" if missing > 1 else "",
    )
    raise access_control.UnauthorizedAccess(
        msg,
        subject=BuildLegacySubject(
            approval_request.subject_id, approval_request.approval_type
        ),
    )


def _CheckHasAdminApprovers(
    approval_request: objects_pb2.ApprovalRequest,
) -> None:
  grantors = set(g.grantor_username for g in approval_request.grants)
  for g in grantors:
    user = data_store.REL_DB.ReadGRRUser(g)
    if user.user_type == objects_pb2.GRRUser.UserType.USER_TYPE_ADMIN:
      return

  raise access_control.UnauthorizedAccess(
      "Need at least 1 admin approver for access.",
      subject=BuildLegacySubject(
          approval_request.subject_id, approval_request.approval_type
      ),
  )


def CheckClientApprovalRequest(
    approval_request: objects_pb2.ApprovalRequest,
) -> None:
  """Checks if a client approval request is granted."""

  _CheckExpired(approval_request)
  _CheckHasEnoughGrants(approval_request)

  if not client_approval_auth.CLIENT_APPROVAL_AUTH_MGR.IsActive():
    return

  approvers = set(g.grantor_username for g in approval_request.grants)

  labels = sorted(
      data_store.REL_DB.ReadClientLabels(approval_request.subject_id),
      key=lambda l: l.name,
  )
  for label in labels:
    client_approval_auth.CLIENT_APPROVAL_AUTH_MGR.CheckApproversForLabel(
        rdfvalue.RDFURN(approval_request.subject_id),
        approval_request.requestor_username,
        approvers,
        label.name,
    )


def CheckHuntApprovalRequest(approval_request) -> None:
  """Checks if a hunt approval request is granted."""

  _CheckExpired(approval_request)
  _CheckHasEnoughGrants(approval_request)
  _CheckHasAdminApprovers(approval_request)


def CheckCronJobApprovalRequest(approval_request) -> None:
  """Checks if a cron job approval request is granted."""

  _CheckExpired(approval_request)
  _CheckHasEnoughGrants(approval_request)
  _CheckHasAdminApprovers(approval_request)


def CheckApprovalRequest(approval_request: objects_pb2.ApprovalRequest):
  """Checks if an approval request is granted."""

  if (
      approval_request.approval_type
      == objects_pb2.ApprovalRequest.ApprovalType.APPROVAL_TYPE_CLIENT
  ):
    return CheckClientApprovalRequest(approval_request)
  elif (
      approval_request.approval_type
      == objects_pb2.ApprovalRequest.ApprovalType.APPROVAL_TYPE_HUNT
  ):
    return CheckHuntApprovalRequest(approval_request)
  elif (
      approval_request.approval_type
      == objects_pb2.ApprovalRequest.ApprovalType.APPROVAL_TYPE_CRON_JOB
  ):
    return CheckCronJobApprovalRequest(approval_request)
  else:
    raise ValueError(
        "Invalid approval type: %s" % approval_request.approval_type
    )
