#!/usr/bin/env python
"""Tests for approval_checks module."""
from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

import mock

from grr_response_core.lib import flags
from grr_response_core.lib import rdfvalue
from grr_response_server import access_control
from grr_response_server import data_store
from grr_response_server.authorization import client_approval_auth
from grr_response_server.gui import approval_checks
from grr_response_server.rdfvalues import objects as rdf_objects
from grr.test_lib import acl_test_lib
from grr.test_lib import db_test_lib
from grr.test_lib import test_lib


def _CreateApprovalRequest(approval_type,
                           subject_id,
                           expiration_time=None,
                           grants=None):
  expiration_time = expiration_time or (
      rdfvalue.RDFDatetime.Now() + rdfvalue.Duration("1h"))
  return rdf_objects.ApprovalRequest(
      approval_type=approval_type,
      approval_id="1234",
      subject_id=subject_id,
      requestor_username=u"requestor",
      reason="reason",
      timestamp=rdfvalue.RDFDatetime.Now(),
      expiration_time=expiration_time,
      grants=grants)


class CheckClientApprovalRequestTest(db_test_lib.RelationalDBEnabledMixin,
                                     acl_test_lib.AclTestMixin,
                                     test_lib.GRRBaseTest):

  def _CreateRequest(self, expiration_time=None, grants=None):
    expiration_time = expiration_time or (
        rdfvalue.RDFDatetime.Now() + rdfvalue.Duration("1h"))
    return _CreateApprovalRequest(
        rdf_objects.ApprovalRequest.ApprovalType.APPROVAL_TYPE_CLIENT,
        self.client.client_id,
        expiration_time=expiration_time,
        grants=grants)

  def setUp(self):
    super(CheckClientApprovalRequestTest, self).setUp()
    self.client = self.SetupTestClientObject(0)

  def testRaisesWhenNoGrants(self):
    approval_request = self._CreateRequest(grants=[])

    with self.assertRaisesRegexp(
        access_control.UnauthorizedAccess,
        "Need at least 2 additional approvers for access"):
      approval_checks.CheckApprovalRequest(approval_request)

  def testRaisesWhenJustOneGrant(self):
    approval_request = self._CreateRequest(
        grants=[rdf_objects.ApprovalGrant(grantor_username=u"grantor")])

    with self.assertRaisesRegexp(
        access_control.UnauthorizedAccess,
        "Need at least 1 additional approver for access"):
      approval_checks.CheckApprovalRequest(approval_request)

  def testRaisesIfApprovalExpired(self):
    approval_request = self._CreateRequest(
        expiration_time=rdfvalue.RDFDatetime.Now() - rdfvalue.Duration("1m"),
        grants=[
            rdf_objects.ApprovalGrant(grantor_username=u"grantor1"),
            rdf_objects.ApprovalGrant(grantor_username=u"grantor2")
        ])

    with self.assertRaisesRegexp(access_control.UnauthorizedAccess,
                                 "Approval request is expired"):
      approval_checks.CheckApprovalRequest(approval_request)

  def testReturnsIfApprovalIsNotExpiredAndHasTwoGrants(self):
    approval_request = self._CreateRequest(grants=[
        rdf_objects.ApprovalGrant(grantor_username=u"grantor1"),
        rdf_objects.ApprovalGrant(grantor_username=u"grantor2")
    ])

    approval_checks.CheckApprovalRequest(approval_request)

  @mock.patch(client_approval_auth.__name__ + ".CLIENT_APPROVAL_AUTH_MGR")
  def testWhenAuthMgrActiveReturnsIfClientHasNoLabels(self, mock_mgr):
    approval_request = self._CreateRequest(grants=[
        rdf_objects.ApprovalGrant(grantor_username=u"grantor1"),
        rdf_objects.ApprovalGrant(grantor_username=u"grantor2")
    ])

    # Make sure approval manager is active.
    mock_mgr.IsActive.return_value = True

    approval_checks.CheckApprovalRequest(approval_request)

  @mock.patch(client_approval_auth.__name__ + ".CLIENT_APPROVAL_AUTH_MGR")
  def testWhenAuthMgrActiveChecksApproversForEachClientLabel(self, mock_mgr):
    data_store.REL_DB.AddClientLabels(self.client.client_id, u"GRR",
                                      [u"foo", u"bar"])

    approval_request = self._CreateRequest(grants=[
        rdf_objects.ApprovalGrant(grantor_username=u"grantor1"),
        rdf_objects.ApprovalGrant(grantor_username=u"grantor2")
    ])

    # Make sure approval manager is active.
    mock_mgr.IsActive.return_value = True

    approval_checks.CheckApprovalRequest(approval_request)

    self.assertLen(mock_mgr.CheckApproversForLabel.mock_calls, 2)

    args = mock_mgr.CheckApproversForLabel.mock_calls[0][1]
    self.assertEqual(args,
                     (access_control.ACLToken(username=u"requestor"),
                      rdfvalue.RDFURN(self.client.client_id), u"requestor",
                      set(["grantor1", "grantor2"]), u"bar"))
    args = mock_mgr.CheckApproversForLabel.mock_calls[1][1]
    self.assertEqual(args,
                     (access_control.ACLToken(username=u"requestor"),
                      rdfvalue.RDFURN(self.client.client_id), u"requestor",
                      set(["grantor1", "grantor2"]), u"foo"))

  @mock.patch(client_approval_auth.__name__ + ".CLIENT_APPROVAL_AUTH_MGR")
  def testWhenAuthMgrActiveRaisesIfAuthMgrRaises(self, mock_mgr):
    data_store.REL_DB.AddClientLabels(self.client.client_id, u"GRR", [u"foo"])

    approval_request = self._CreateRequest(grants=[
        rdf_objects.ApprovalGrant(grantor_username=u"grantor1"),
        rdf_objects.ApprovalGrant(grantor_username=u"grantor2")
    ])

    # Make sure approval manager is active.
    mock_mgr.IsActive.return_value = True

    # CheckApproversForLabel should raise.
    error = access_control.UnauthorizedAccess("some error")
    mock_mgr.CheckApproversForLabel.side_effect = error

    with self.assertRaisesRegexp(access_control.UnauthorizedAccess,
                                 "some error"):
      approval_checks.CheckApprovalRequest(approval_request)


class CheckHuntAndCronJobApprovalRequestTestMixin(
    db_test_lib.RelationalDBEnabledMixin, acl_test_lib.AclTestMixin):

  APPROVAL_TYPE = None

  def _CreateRequest(self, expiration_time=None, grants=None):
    if not self.APPROVAL_TYPE:
      raise ValueError("APPROVAL_TYPE has to be set.")

    return _CreateApprovalRequest(
        self.APPROVAL_TYPE,
        "123456",
        expiration_time=expiration_time,
        grants=grants)

  def setUp(self):
    super(CheckHuntAndCronJobApprovalRequestTestMixin, self).setUp()
    self.CreateUser(u"grantor1")
    self.CreateUser(u"grantor2")

  def testRaisesWhenNoGrants(self):
    approval_request = self._CreateRequest(grants=[])

    with self.assertRaisesRegexp(
        access_control.UnauthorizedAccess,
        "Need at least 2 additional approvers for access"):
      approval_checks.CheckApprovalRequest(approval_request)

  def testRaisesWhenJustOneGrant(self):
    approval_request = self._CreateRequest(
        grants=[rdf_objects.ApprovalGrant(grantor_username=u"grantor1")])

    with self.assertRaisesRegexp(
        access_control.UnauthorizedAccess,
        "Need at least 1 additional approver for access"):
      approval_checks.CheckApprovalRequest(approval_request)

  def testRaisesWhenNoGrantsFromAdmins(self):
    approval_request = self._CreateRequest(grants=[
        rdf_objects.ApprovalGrant(grantor_username=u"grantor1"),
        rdf_objects.ApprovalGrant(grantor_username=u"grantor2")
    ])

    with self.assertRaisesRegexp(access_control.UnauthorizedAccess,
                                 "Need at least 1 admin approver for access"):
      approval_checks.CheckApprovalRequest(approval_request)

  def testRaisesIfApprovalExpired(self):
    # Make sure that approval is otherwise valid.
    self.CreateAdminUser(u"grantor2")

    approval_request = self._CreateRequest(
        expiration_time=rdfvalue.RDFDatetime.Now() - rdfvalue.Duration("1m"),
        grants=[
            rdf_objects.ApprovalGrant(grantor_username=u"grantor1"),
            rdf_objects.ApprovalGrant(grantor_username=u"grantor2")
        ])

    with self.assertRaisesRegexp(access_control.UnauthorizedAccess,
                                 "Approval request is expired"):
      approval_checks.CheckApprovalRequest(approval_request)

  def testReturnsIfApprovalIsNotExpiredAndHasTwoGrantsIncludingAdmin(self):
    self.CreateAdminUser(u"grantor2")

    approval_request = self._CreateRequest(grants=[
        rdf_objects.ApprovalGrant(grantor_username=u"grantor1"),
        rdf_objects.ApprovalGrant(grantor_username=u"grantor2")
    ])

    approval_checks.CheckApprovalRequest(approval_request)


class CheckHuntApprovalRequestTest(CheckHuntAndCronJobApprovalRequestTestMixin,
                                   test_lib.GRRBaseTest):
  APPROVAL_TYPE = rdf_objects.ApprovalRequest.ApprovalType.APPROVAL_TYPE_HUNT


class CheckCronJobApprovalRequestTest(
    CheckHuntAndCronJobApprovalRequestTestMixin, test_lib.GRRBaseTest):
  APPROVAL_TYPE = (
      rdf_objects.ApprovalRequest.ApprovalType.APPROVAL_TYPE_CRON_JOB)


if __name__ == "__main__":
  flags.StartMain(test_lib.main)
