#!/usr/bin/env python
"""Approvals checking logic."""
from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

from grr_response_core import config
from grr_response_core.lib import rdfvalue
from grr_response_server import access_control
from grr_response_server import data_store
from grr_response_server.authorization import client_approval_auth
from grr_response_server.rdfvalues import objects as rdf_objects


def BuildLegacySubject(subject_id, approval_type):
  """Builds a legacy AFF4 urn string for a given subject and approval type."""
  at = rdf_objects.ApprovalRequest.ApprovalType

  if approval_type == at.APPROVAL_TYPE_CLIENT:
    return "aff4:/%s" % subject_id
  elif approval_type == at.APPROVAL_TYPE_HUNT:
    return "aff4:/hunts/%s" % subject_id
  elif approval_type == at.APPROVAL_TYPE_CRON_JOB:
    return "aff4:/cron/%s" % subject_id

  raise ValueError("Invalid approval type.")


def _CheckExpired(approval_request):
  if approval_request.expiration_time < rdfvalue.RDFDatetime.Now():
    raise access_control.UnauthorizedAccess(
        "Approval request is expired.",
        subject=BuildLegacySubject(approval_request.subject_id,
                                   approval_request.approval_type))


def _CheckHasEnoughGrants(approval_request):
  approvers_required = config.CONFIG["ACL.approvers_required"]
  approvers = set(g.grantor_username for g in approval_request.grants)

  missing = approvers_required - len(approvers)
  if missing > 0:
    msg = ("Need at least %d additional approver%s for access." %
           (missing, "s" if missing > 1 else ""))
    raise access_control.UnauthorizedAccess(
        msg,
        subject=BuildLegacySubject(approval_request.subject_id,
                                   approval_request.approval_type))


def _CheckHasAdminApprovers(approval_request):
  grantors = set(g.grantor_username for g in approval_request.grants)
  for g in grantors:
    user_obj = data_store.REL_DB.ReadGRRUser(g)
    if user_obj.user_type == user_obj.UserType.USER_TYPE_ADMIN:
      return True

  raise access_control.UnauthorizedAccess(
      "Need at least 1 admin approver for access.",
      subject=BuildLegacySubject(approval_request.subject_id,
                                 approval_request.approval_type))


def CheckClientApprovalRequest(approval_request):
  """Checks if a client approval request is granted."""

  _CheckExpired(approval_request)
  _CheckHasEnoughGrants(approval_request)

  if not client_approval_auth.CLIENT_APPROVAL_AUTH_MGR.IsActive():
    return True

  token = access_control.ACLToken(username=approval_request.requestor_username)
  approvers = set(g.grantor_username for g in approval_request.grants)

  labels = sorted(
      data_store.REL_DB.ReadClientLabels(approval_request.subject_id),
      key=lambda l: l.name)
  for label in labels:
    client_approval_auth.CLIENT_APPROVAL_AUTH_MGR.CheckApproversForLabel(
        token, rdfvalue.RDFURN(approval_request.subject_id),
        approval_request.requestor_username, approvers, label.name)

  return True


def CheckHuntApprovalRequest(approval_request):
  """Checks if a hunt approval request is granted."""

  _CheckExpired(approval_request)
  _CheckHasEnoughGrants(approval_request)
  _CheckHasAdminApprovers(approval_request)


def CheckCronJobApprovalRequest(approval_request):
  """Checks if a cron job approval request is granted."""

  _CheckExpired(approval_request)
  _CheckHasEnoughGrants(approval_request)
  _CheckHasAdminApprovers(approval_request)


def CheckApprovalRequest(approval_request):
  """Checks if an approval request is granted."""

  at = rdf_objects.ApprovalRequest.ApprovalType

  if approval_request.approval_type == at.APPROVAL_TYPE_CLIENT:
    return CheckClientApprovalRequest(approval_request)
  elif approval_request.approval_type == at.APPROVAL_TYPE_HUNT:
    return CheckHuntApprovalRequest(approval_request)
  elif approval_request.approval_type == at.APPROVAL_TYPE_CRON_JOB:
    return CheckCronJobApprovalRequest(approval_request)
  else:
    raise ValueError(
        "Invalid approval type: %s" % approval_request.approval_type)
