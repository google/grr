#!/usr/bin/env python
"""Tests for access_control module."""

from typing import Iterable
from unittest import mock

from absl import app

from grr_response_core.lib import rdfvalue
from grr_response_proto import objects_pb2
from grr_response_server import access_control
from grr_response_server import data_store
from grr_response_server.authorization import client_approval_auth
from grr_response_server.gui import access_controller
from grr_response_server.gui import api_call_context
from grr.test_lib import test_lib


def _CreateApprovalRequest(
    approval_type: objects_pb2.ApprovalRequest.ApprovalType,
    subject_id: str,
    expiration_time: rdfvalue.RDFDatetime = None,
    grants: Iterable[objects_pb2.ApprovalGrant] = None,
    username: str = "requestor",
):
  expiration_time = expiration_time or (
      rdfvalue.RDFDatetime.Now() + rdfvalue.Duration.From(1, rdfvalue.HOURS)
  )
  return objects_pb2.ApprovalRequest(
      approval_type=approval_type,
      approval_id="1234",
      subject_id=subject_id,
      requestor_username=username,
      reason="reason",
      timestamp=int(rdfvalue.RDFDatetime.Now()),
      expiration_time=int(expiration_time),
      grants=grants,
  )


class ApprovalChecksTest(test_lib.GRRBaseTest):

  def _CreateRequest(self, expiration_time=None, grants=None):
    expiration_time = expiration_time or (
        rdfvalue.RDFDatetime.Now() + rdfvalue.Duration.From(1, rdfvalue.HOURS)
    )
    return _CreateApprovalRequest(
        objects_pb2.ApprovalRequest.ApprovalType.APPROVAL_TYPE_CLIENT,
        self.client_id,
        expiration_time=expiration_time,
        grants=grants,
    )

  def setUp(self):
    super().setUp()
    self.client_id = self.SetupClient(0)

  def testRaisesWhenNoGrants(self):
    approval_request = self._CreateRequest(grants=[])

    with self.assertRaisesRegex(
        access_control.UnauthorizedAccess,
        "Need at least 2 additional approvers for access",
    ):
      access_controller._CheckHasEnoughGrants(approval_request)

  def testRaisesWhenJustOneGrant(self):
    approval_request = self._CreateRequest(
        grants=[objects_pb2.ApprovalGrant(grantor_username="grantor")]
    )

    with self.assertRaisesRegex(
        access_control.UnauthorizedAccess,
        "Need at least 1 additional approver for access",
    ):
      access_controller._CheckHasEnoughGrants(approval_request)

  def testRaisesIfApprovalExpired(self):
    approval_request = self._CreateRequest(
        expiration_time=rdfvalue.RDFDatetime.Now()
        - rdfvalue.Duration.From(1, rdfvalue.MINUTES),
        grants=[
            objects_pb2.ApprovalGrant(grantor_username="grantor1"),
            objects_pb2.ApprovalGrant(grantor_username="grantor2"),
        ],
    )

    with self.assertRaisesRegex(
        access_control.UnauthorizedAccess, "Approval request is expired"
    ):
      access_controller._CheckExpired(approval_request)

  @mock.patch(client_approval_auth.__name__ + ".CLIENT_APPROVAL_AUTH_MGR")
  def testWhenAuthMgrActiveReturnsIfClientHasNoLabels(self, mock_mgr):
    approval_request = self._CreateRequest(
        grants=[
            objects_pb2.ApprovalGrant(grantor_username="grantor1"),
            objects_pb2.ApprovalGrant(grantor_username="grantor2"),
        ]
    )

    # Make sure approval manager is active.
    mock_mgr.IsActive.return_value = True

    access_controller._CheckApprovalFromClientLabel(approval_request)

  @mock.patch(client_approval_auth.__name__ + ".CLIENT_APPROVAL_AUTH_MGR")
  def testWhenAuthMgrActiveChecksApproversForEachClientLabel(self, mock_mgr):
    data_store.REL_DB.WriteGRRUser("GRR")
    data_store.REL_DB.AddClientLabels(self.client_id, "GRR", ["foo", "bar"])

    approval_request = self._CreateRequest(
        grants=[
            objects_pb2.ApprovalGrant(grantor_username="grantor1"),
            objects_pb2.ApprovalGrant(grantor_username="grantor2"),
        ]
    )

    # Make sure approval manager is active.
    mock_mgr.IsActive.return_value = True

    access_controller._CheckApprovalFromClientLabel(approval_request)

    self.assertLen(mock_mgr.CheckApproversForLabel.mock_calls, 2)

    args = mock_mgr.CheckApproversForLabel.mock_calls[0][1]
    self.assertEqual(
        args,
        (
            rdfvalue.RDFURN(self.client_id),
            "requestor",
            set(["grantor1", "grantor2"]),
            "bar",
        ),
    )
    args = mock_mgr.CheckApproversForLabel.mock_calls[1][1]
    self.assertEqual(
        args,
        (
            rdfvalue.RDFURN(self.client_id),
            "requestor",
            set(["grantor1", "grantor2"]),
            "foo",
        ),
    )

  @mock.patch(client_approval_auth.__name__ + ".CLIENT_APPROVAL_AUTH_MGR")
  def testWhenAuthMgrActiveRaisesIfAuthMgrRaises(self, mock_mgr):
    data_store.REL_DB.WriteGRRUser("GRR")
    data_store.REL_DB.AddClientLabels(self.client_id, "GRR", ["foo"])

    approval_request = self._CreateRequest(
        grants=[
            objects_pb2.ApprovalGrant(grantor_username="grantor1"),
            objects_pb2.ApprovalGrant(grantor_username="grantor2"),
        ]
    )

    # Make sure approval manager is active.
    mock_mgr.IsActive.return_value = True

    # CheckApproversForLabel should raise.
    error = access_control.UnauthorizedAccess("some error")
    mock_mgr.CheckApproversForLabel.side_effect = error

    with self.assertRaisesRegex(
        access_control.UnauthorizedAccess, "some error"
    ):
      access_controller._CheckApprovalFromClientLabel(approval_request)


class AdminAccessCheckerTest(test_lib.GRRBaseTest):
  """Tests for AdminAccessChecker."""

  def testCheckIfHasAdminAccess_AdminUser(self):
    username = "admin"
    data_store.REL_DB.WriteGRRUser(
        username, user_type=objects_pb2.GRRUser.UserType.USER_TYPE_ADMIN
    )
    checker = access_controller.AdminAccessChecker()
    # Shouldn't raise if it is allowed.
    checker.CheckIfHasAdminAccess(username)

  def testCheckIfHasAdminAccess_NotAdminUser(self):
    username = "not_admin"
    data_store.REL_DB.WriteGRRUser(
        username, user_type=objects_pb2.GRRUser.UserType.USER_TYPE_STANDARD
    )

    checker = access_controller.AdminAccessChecker()
    with self.assertRaisesRegex(
        access_control.UnauthorizedAccess,
        "No Admin user access for not_admin.",
    ):
      checker.CheckIfHasAdminAccess(username)

  def testCheckIfCanStartFlowNotRegistered(self):
    checker = access_controller.AdminAccessChecker()
    with self.assertRaisesRegex(
        access_control.UnauthorizedAccess,
        "Flow NotThere can't be started via the API.",
    ):
      checker.CheckIfCanStartFlow("test_user", "NotThere")

  def testCheckIfCanStartFlow_RestrictedFlow_NormalUser(self):
    data_store.REL_DB.WriteGRRUser("restricted")

    checker = access_controller.AdminAccessChecker()
    with self.assertRaisesRegex(
        access_control.UnauthorizedAccess,
        "Not enough permissions to access restricted flow LaunchBinary",
    ):
      checker.CheckIfCanStartFlow("restricted", "LaunchBinary")

  def testCheckIfCanStartFlow_RestrictedFlow_AdminUser(self):
    checker = access_controller.AdminAccessChecker()
    data_store.REL_DB.WriteGRRUser(
        "admin", user_type=objects_pb2.GRRUser.UserType.USER_TYPE_ADMIN
    )
    # Shouldn't raise if it is allowed.
    checker.CheckIfCanStartFlow("admin", "LaunchBinary")

  def testCheckIfCanStartMultiGetFile(self):
    checker = access_controller.AdminAccessChecker()
    # Shouldn't raise if it is allowed.
    checker.CheckIfCanStartFlow("test_user", "MultiGetFile")


class MitigationFlowsAccessCheckerTest(test_lib.GRRBaseTest):
  """Tests for MitigationFlowsAccessChecker."""

  def testCheckIfHasAccessToFlow_PassesForNonMitigationFlow(self):
    username = "any_user"
    checker = access_controller.MitigationFlowsAccessChecker()

    checker.CheckIfHasAccessToFlow(username, "LaunchBinary")


class ApprovalCheckerTest(test_lib.GRRBaseTest):
  """Tests for AccessChecker."""

  def setUp(self):
    super().setUp()
    self.context = api_call_context.ApiCallContext("test")
    self.admin_access_checker = mock.MagicMock(
        spec=access_controller.AdminAccessChecker
    )
    self.checker = access_controller.ApprovalChecker(self.admin_access_checker)

  def testCachedApproval(self):
    username = "test"
    subject_id = "C.1234"
    approval_type = (
        objects_pb2.ApprovalRequest.ApprovalType.APPROVAL_TYPE_CLIENT
    )
    approval = _CreateApprovalRequest(
        approval_type, subject_id, username=username
    )

    cached = self.checker._GetCachedApproval(
        username, subject_id, approval_type
    )
    self.assertIsNone(cached)

    self.checker._PutApprovalInCache(approval)
    cached = self.checker._GetCachedApproval(
        username, subject_id, approval_type
    )
    self.assertEqual(approval, cached)

  def testCheckApprovals_NoChecksPasses(self):
    approvals = [
        _CreateApprovalRequest(
            objects_pb2.ApprovalRequest.ApprovalType.APPROVAL_TYPE_CLIENT,
            subject_id="1234",
        )
    ]
    self.checker.CheckApprovals(
        approvals,
        approval_checks=[],
        error_subject="my subject",
    )

  def testCheckApprovals_NoApprovalsRaises(self):
    with self.assertRaisesRegex(
        access_control.UnauthorizedAccess,
        "No approval found",
    ):
      self.checker.CheckApprovals(
          approvals=[],
          approval_checks=[],
          error_subject="test",
      )

  def testCheckApprovals_SuccessfulApprovalCheckspass(self):
    approval = _CreateApprovalRequest(
        objects_pb2.ApprovalRequest.ApprovalType.APPROVAL_TYPE_CLIENT,
        subject_id="1234",
    )

    called_checks = []

    def _CheckSuccessfulOne(approval):
      called_checks.append(("one", approval.subject_id))
      del approval
      return

    def _CheckSuccessfulTwo(approval):
      called_checks.append(("two", approval.subject_id))
      del approval
      return

    self.checker.CheckApprovals(
        approvals=[approval],
        approval_checks=[_CheckSuccessfulOne, _CheckSuccessfulTwo],
        error_subject="my subject",
    )
    self.assertCountEqual(
        called_checks,
        [("one", approval.subject_id), ("two", approval.subject_id)],
    )

  def testCheckApprovals_RaisesIfCheckFails(self):
    approvals = [
        _CreateApprovalRequest(
            objects_pb2.ApprovalRequest.ApprovalType.APPROVAL_TYPE_CLIENT,
            subject_id="1234",
        )
    ]

    def _FailingCheck(approval):
      del approval
      raise access_control.UnauthorizedAccess("some error")

    with self.assertRaisesRegex(
        access_control.UnauthorizedAccess,
        "some error",
    ):
      self.checker.CheckApprovals(
          approvals,
          approval_checks=[_FailingCheck],
          error_subject="my subject",
      )

  def testCheckHasAdminApprovers_NoApprovers(self):
    approval = _CreateApprovalRequest(
        objects_pb2.ApprovalRequest.ApprovalType.APPROVAL_TYPE_CLIENT,
        subject_id="1234",
    )
    with self.assertRaisesRegex(
        access_control.UnauthorizedAccess,
        "Need at least 1 admin approver for access",
    ):
      self.checker._CheckHasAdminApprovers(approval)

  def testCheckHasAdminApprovers_AdminApprovers(self):
    self.admin_access_checker.CheckIfHasAdminAccess.return_value = None

    approval = _CreateApprovalRequest(
        objects_pb2.ApprovalRequest.ApprovalType.APPROVAL_TYPE_CLIENT,
        subject_id="1234",
        grants=[
            objects_pb2.ApprovalGrant(grantor_username="admin1"),
            objects_pb2.ApprovalGrant(grantor_username="admin2"),
        ],
    )
    self.checker._CheckHasAdminApprovers(approval)

  def testCheckHasAdminApprovers_NotAdminApprovers(self):
    self.admin_access_checker.CheckIfHasAdminAccess.side_effect = (
        access_control.UnauthorizedAccess("not an admin")
    )

    approval = _CreateApprovalRequest(
        objects_pb2.ApprovalRequest.ApprovalType.APPROVAL_TYPE_CLIENT,
        subject_id="1234",
        grants=[
            objects_pb2.ApprovalGrant(grantor_username="no_admin1"),
            objects_pb2.ApprovalGrant(grantor_username="no_admin2"),
        ],
    )
    with self.assertRaisesRegex(
        access_control.UnauthorizedAccess,
        "Need at least 1 admin approver for access",
    ):
      self.checker._CheckHasAdminApprovers(approval)


if __name__ == "__main__":
  app.run(test_lib.main)
