#!/usr/bin/env python
"""Tests for approval_checks module."""

from typing import Iterable
from unittest import mock

from absl import app

from grr_response_core.lib import rdfvalue
from grr_response_proto import objects_pb2
from grr_response_server import access_control
from grr_response_server import data_store
from grr_response_server.authorization import client_approval_auth
from grr_response_server.gui import approval_checks
from grr.test_lib import acl_test_lib
from grr.test_lib import test_lib


def _CreateApprovalRequest(
    approval_type: objects_pb2.ApprovalRequest.ApprovalType,
    subject_id: str,
    expiration_time: rdfvalue.RDFDatetime = None,
    grants: Iterable[objects_pb2.ApprovalGrant] = None,
):
  expiration_time = expiration_time or (
      rdfvalue.RDFDatetime.Now() + rdfvalue.Duration.From(1, rdfvalue.HOURS)
  )
  return objects_pb2.ApprovalRequest(
      approval_type=approval_type,
      approval_id="1234",
      subject_id=subject_id,
      requestor_username="requestor",
      reason="reason",
      timestamp=int(rdfvalue.RDFDatetime.Now()),
      expiration_time=int(expiration_time),
      grants=grants,
  )


class CheckClientApprovalRequestTest(
    acl_test_lib.AclTestMixin, test_lib.GRRBaseTest
):

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
      approval_checks.CheckApprovalRequest(approval_request)

  def testRaisesWhenJustOneGrant(self):
    approval_request = self._CreateRequest(
        grants=[objects_pb2.ApprovalGrant(grantor_username="grantor")]
    )

    with self.assertRaisesRegex(
        access_control.UnauthorizedAccess,
        "Need at least 1 additional approver for access",
    ):
      approval_checks.CheckApprovalRequest(approval_request)

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
      approval_checks.CheckApprovalRequest(approval_request)

  def testReturnsIfApprovalIsNotExpiredAndHasTwoGrants(self):
    approval_request = self._CreateRequest(
        grants=[
            objects_pb2.ApprovalGrant(grantor_username="grantor1"),
            objects_pb2.ApprovalGrant(grantor_username="grantor2"),
        ]
    )

    approval_checks.CheckApprovalRequest(approval_request)

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

    approval_checks.CheckApprovalRequest(approval_request)

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

    approval_checks.CheckApprovalRequest(approval_request)

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
      approval_checks.CheckApprovalRequest(approval_request)


class CheckHuntAndCronJobApprovalRequestTestMixin(acl_test_lib.AclTestMixin):

  APPROVAL_TYPE = None

  def _CreateRequest(self, expiration_time=None, grants=None):
    if not self.APPROVAL_TYPE:
      raise ValueError("APPROVAL_TYPE has to be set.")

    return _CreateApprovalRequest(
        self.APPROVAL_TYPE,
        "123456",
        expiration_time=expiration_time,
        grants=grants,
    )

  def setUp(self):
    super().setUp()
    self.CreateUser("grantor1")
    self.CreateUser("grantor2")

  def testRaisesWhenNoGrants(self):
    approval_request = self._CreateRequest(grants=[])

    with self.assertRaisesRegex(
        access_control.UnauthorizedAccess,
        "Need at least 2 additional approvers for access",
    ):
      approval_checks.CheckApprovalRequest(approval_request)

  def testRaisesWhenJustOneGrant(self):
    approval_request = self._CreateRequest(
        grants=[objects_pb2.ApprovalGrant(grantor_username="grantor1")]
    )

    with self.assertRaisesRegex(
        access_control.UnauthorizedAccess,
        "Need at least 1 additional approver for access",
    ):
      approval_checks.CheckApprovalRequest(approval_request)

  def testRaisesWhenNoGrantsFromAdmins(self):
    approval_request = self._CreateRequest(
        grants=[
            objects_pb2.ApprovalGrant(grantor_username="grantor1"),
            objects_pb2.ApprovalGrant(grantor_username="grantor2"),
        ]
    )

    with self.assertRaisesRegex(
        access_control.UnauthorizedAccess,
        "Need at least 1 admin approver for access",
    ):
      approval_checks.CheckApprovalRequest(approval_request)

  def testRaisesIfApprovalExpired(self):
    # Make sure that approval is otherwise valid.
    self.CreateAdminUser("grantor2")

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
      approval_checks.CheckApprovalRequest(approval_request)

  def testReturnsIfApprovalIsNotExpiredAndHasTwoGrantsIncludingAdmin(self):
    self.CreateAdminUser("grantor2")

    approval_request = self._CreateRequest(
        grants=[
            objects_pb2.ApprovalGrant(grantor_username="grantor1"),
            objects_pb2.ApprovalGrant(grantor_username="grantor2"),
        ]
    )

    approval_checks.CheckApprovalRequest(approval_request)


class CheckHuntApprovalRequestTest(
    CheckHuntAndCronJobApprovalRequestTestMixin, test_lib.GRRBaseTest
):
  APPROVAL_TYPE = objects_pb2.ApprovalRequest.ApprovalType.APPROVAL_TYPE_HUNT


class CheckCronJobApprovalRequestTest(
    CheckHuntAndCronJobApprovalRequestTestMixin, test_lib.GRRBaseTest
):
  APPROVAL_TYPE = (
      objects_pb2.ApprovalRequest.ApprovalType.APPROVAL_TYPE_CRON_JOB
  )


if __name__ == "__main__":
  app.run(test_lib.main)
