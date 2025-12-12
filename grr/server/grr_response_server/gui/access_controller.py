#!/usr/bin/env python
"""Access control logic."""

from typing import Callable, Optional, Sequence

from grr_response_core import config
from grr_response_core.lib import rdfvalue
from grr_response_core.lib import registry
from grr_response_core.lib import utils
from grr_response_core.stats import metrics
from grr_response_proto import objects_pb2
from grr_response_server import access_control
from grr_response_server import data_store
from grr_response_server.authorization import client_approval_auth
from grr_response_server.flows import local as flows_local
from grr_response_server.flows.general import administrative
from grr_response_server.gui import api_call_context


APPROVAL_SEARCHES = metrics.Counter(
    "approval_searches", fields=[("reason_presence", str), ("source", str)]
)
RESTRICTED_FLOWS = [
    administrative.ExecutePythonHack,
    administrative.LaunchBinary,
    administrative.UpdateClient,
]

MITIGATION_FLOWS = [] + flows_local.MITIGATION_FLOWS


class AdminAccessChecker:
  """Checks related to user admin access."""

  def CheckIfHasAdminAccess(self, username: str) -> None:
    """Checks whether a given user has admin access."""

    user = data_store.REL_DB.ReadGRRUser(username)
    if user.user_type == objects_pb2.GRRUser.UserType.USER_TYPE_ADMIN:
      return

    raise access_control.UnauthorizedAccess(
        f"No Admin user access for {username}."
    )

  def CheckIfCanStartFlow(self, username: str, flow_name: str) -> None:
    """Checks whether a given user can start a given flow."""
    flow_cls = registry.FlowRegistry.FLOW_REGISTRY.get(flow_name)

    if flow_cls is None or not flow_cls.CanUseViaAPI():
      raise access_control.UnauthorizedAccess(
          "Flow %s can't be started via the API." % flow_name
      )

    if flow_cls in RESTRICTED_FLOWS:
      try:
        self.CheckIfHasAdminAccess(username)
      except access_control.UnauthorizedAccess as e:
        raise access_control.UnauthorizedAccess(
            f"Not enough permissions to access restricted flow {flow_name}"
        ) from e


class MitigationFlowsAccessChecker:
  """Checks if a user has permission to run mitigation flows based on the router params."""

  def CheckIfHasAccessToMitigationFlows(self, username: str) -> None:
    """Checks whether a given user has access to mitigation flows."""
    raise access_control.UnauthorizedAccess(
        f"No access to mitigation flows for {username}."
    )

  def CheckIfHasAccessToFlow(self, username: str, flow_name: str) -> None:
    """Checks whether a given user has access to mitigation flows."""

    flow_cls = registry.FlowRegistry.FLOW_REGISTRY.get(flow_name)
    if flow_cls is None:
      raise access_control.UnauthorizedAccess(
          f"Flow {flow_name} can't be started."
      )

    if flow_cls in MITIGATION_FLOWS:
      try:
        self.CheckIfHasAccessToMitigationFlows(username)
      except access_control.UnauthorizedAccess as e:
        raise access_control.UnauthorizedAccess(
            f"Not enough permissions to access mitigation flow {flow_name}."
        ) from e


class ApprovalChecker:
  """Relational DB-based access checker implementation."""

  APPROVAL_CACHE_SECONDS = 60

  def __init__(self, admin_access_checker: AdminAccessChecker):
    self._admin_access_checker = admin_access_checker

    self.acl_cache = utils.AgeBasedCache(
        max_size=10000, max_age=self.APPROVAL_CACHE_SECONDS
    )

  def _GetCachedApproval(
      self,
      username: str,
      subject_id: str,
      approval_type: objects_pb2.ApprovalRequest.ApprovalType,
  ) -> Optional[objects_pb2.ApprovalRequest]:
    """Checks access to a given subject by a given user."""
    cache_key = (username, subject_id, approval_type)
    try:
      approval = self.acl_cache.Get(cache_key)
      APPROVAL_SEARCHES.Increment(fields=["-", "cache"])
      return approval
    except KeyError:
      APPROVAL_SEARCHES.Increment(fields=["-", "reldb"])

  def _PutApprovalInCache(self, approval: objects_pb2.ApprovalRequest) -> None:
    cache_key = (
        approval.requestor_username,
        approval.subject_id,
        approval.approval_type,
    )
    self.acl_cache.Put(cache_key, approval)

  def GetAndCheckApproval(
      self,
      username: str,
      subject_id: str,
      approval_type: objects_pb2.ApprovalRequest.ApprovalType,
      approval_checks: Sequence[Callable[[objects_pb2.ApprovalRequest], None]],
  ) -> Optional[objects_pb2.ApprovalRequest]:
    """Returns an approval if available.

    Args:
      username: The username of the user to check.
      subject_id: The subject ID of the approval to check.
      approval_type: The type of the approval to check.
      approval_checks: A list of checks to run against each approval.

    Returns:
      A cached approval if available, or the first approval from the db that
      passes all checks.

    Raises:
      access_control.UnauthorizedAccess: If no approval is found that passes all
      checks.
    """
    if approval := self._GetCachedApproval(username, subject_id, approval_type):
      return approval

    approvals = data_store.REL_DB.ReadApprovalRequests(
        username,
        approval_type,
        subject_id=subject_id,
        include_expired=False,
    )
    return self.CheckApprovals(
        approvals,
        approval_checks=approval_checks,
        error_subject=_BuildLegacySubject(subject_id, approval_type),
    )

  def CheckApprovals(
      self,
      approvals: Sequence[objects_pb2.ApprovalRequest],
      approval_checks: Sequence[Callable[[objects_pb2.ApprovalRequest], None]],
      error_subject: str,
  ) -> Optional[objects_pb2.ApprovalRequest]:
    """Checks a list of approvals against given checks and raises if any of the checks fail.

    Args:
      approvals: A list of approvals to check.
      approval_checks: A list of checks to run against each approval.
      error_subject: The subject to use for the error message if any of the
        checks fail.

    Returns:
      The first approval that passes all checks.

    Raises:
      access_control.UnauthorizedAccess: If none of the approvals pass all
      checks.
    """
    errors = []
    for approval in approvals:
      try:
        for check in approval_checks:
          check(approval)

        self._PutApprovalInCache(approval)
        return approval
      except access_control.UnauthorizedAccess as e:
        errors.append(e)

    if errors:
      raise access_control.UnauthorizedAccess(
          " ".join(str(e) for e in errors),
          subject=error_subject,
      )
    raise access_control.UnauthorizedAccess(
        "No approval found.",
        subject=error_subject,
    )

  def CheckClientApprovals(
      self, client_id: str, approvals: Sequence[objects_pb2.ApprovalRequest]
  ) -> Optional[objects_pb2.ApprovalRequest]:
    return self.CheckApprovals(
        approvals,
        approval_checks=[
            _CheckExpired,
            _CheckHasEnoughGrants,
            _CheckApprovalFromClientLabel,
        ],
        error_subject=_BuildLegacySubject(
            client_id,
            objects_pb2.ApprovalRequest.ApprovalType.APPROVAL_TYPE_CLIENT,
        ),
    )

  def CheckClientAccess(
      self, context: api_call_context.ApiCallContext, client_id: str
  ) -> None:
    """Checks whether a given user can access given client."""
    context.approval = self.GetAndCheckApproval(
        context.username,
        client_id,
        objects_pb2.ApprovalRequest.ApprovalType.APPROVAL_TYPE_CLIENT,
        [_CheckExpired, _CheckHasEnoughGrants, _CheckApprovalFromClientLabel],
    )

  def CheckCronJobApprovals(
      self, cron_job_id: str, approvals: Sequence[objects_pb2.ApprovalRequest]
  ) -> Optional[objects_pb2.ApprovalRequest]:
    return self.CheckApprovals(
        approvals,
        approval_checks=[
            _CheckExpired,
            _CheckHasEnoughGrants,
            self._CheckHasAdminApprovers,
        ],
        error_subject=_BuildLegacySubject(
            cron_job_id,
            objects_pb2.ApprovalRequest.ApprovalType.APPROVAL_TYPE_CRON_JOB,
        ),
    )

  def CheckCronJobAccess(
      self, context: api_call_context.ApiCallContext, cron_job_id: str
  ) -> None:
    """Checks whether a given user can access given cron job."""
    context.approval = self.GetAndCheckApproval(
        context.username,
        cron_job_id,
        objects_pb2.ApprovalRequest.ApprovalType.APPROVAL_TYPE_CRON_JOB,
        [_CheckExpired, _CheckHasEnoughGrants, self._CheckHasAdminApprovers],
    )

  def CheckHuntApprovals(
      self, hunt_id: str, approvals: Sequence[objects_pb2.ApprovalRequest]
  ) -> Optional[objects_pb2.ApprovalRequest]:
    return self.CheckApprovals(
        approvals,
        approval_checks=[
            _CheckExpired,
            _CheckHasEnoughGrants,
            self._CheckHasAdminApprovers,
        ],
        error_subject=_BuildLegacySubject(
            hunt_id, objects_pb2.ApprovalRequest.ApprovalType.APPROVAL_TYPE_HUNT
        ),
    )

  def CheckHuntAccess(
      self, context: api_call_context.ApiCallContext, hunt_id: str
  ) -> None:
    """Checks whether a given user can access given hunt."""
    context.approval = self.GetAndCheckApproval(
        context.username,
        hunt_id,
        objects_pb2.ApprovalRequest.ApprovalType.APPROVAL_TYPE_HUNT,
        [_CheckExpired, _CheckHasEnoughGrants, self._CheckHasAdminApprovers],
    )

  def _CheckHasAdminApprovers(
      self,
      approval_request: objects_pb2.ApprovalRequest,
  ) -> None:
    """Checks that there is at least one admin approver for the given request."""
    grantors = set(g.grantor_username for g in approval_request.grants)
    for g in grantors:
      try:
        self._admin_access_checker.CheckIfHasAdminAccess(g)
      except access_control.UnauthorizedAccess:
        continue
      else:
        return
    raise access_control.UnauthorizedAccess(
        "Need at least 1 admin approver for access.",
        subject=_BuildLegacySubject(
            approval_request.subject_id, approval_request.approval_type
        ),
    )


def _CheckApprovalFromClientLabel(
    approval_request: objects_pb2.ApprovalRequest,
) -> None:
  """Checks if a client approval request is granted."""
  assert client_approval_auth.CLIENT_APPROVAL_AUTH_MGR is not None

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


def _CheckHasEnoughGrants(approval_request: objects_pb2.ApprovalRequest):
  num_approvers_required = config.CONFIG["ACL.approvers_required"]
  approvers = set(g.grantor_username for g in approval_request.grants)

  missing = num_approvers_required - len(approvers)
  if missing > 0:
    msg = "Need at least %d additional approver%s for access." % (
        missing,
        "s" if missing > 1 else "",
    )
    raise access_control.UnauthorizedAccess(
        msg,
        subject=_BuildLegacySubject(
            approval_request.subject_id, approval_request.approval_type
        ),
    )


def _CheckExpired(approval_request: objects_pb2.ApprovalRequest) -> None:
  if approval_request.expiration_time < int(rdfvalue.RDFDatetime.Now()):
    raise access_control.UnauthorizedAccess(
        "Approval request is expired.",
        subject=_BuildLegacySubject(
            approval_request.subject_id, approval_request.approval_type
        ),
    )


def _BuildLegacySubject(
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
