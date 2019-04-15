#!/usr/bin/env python
# -*- encoding: utf-8 -*-
from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

from future.builtins import range

from grr_response_core.lib import rdfvalue
from grr_response_server.databases import db
from grr_response_server.rdfvalues import objects as rdf_objects

# Username with UTF-8 characters and maximum length.
EXAMPLE_NAME = "x" + "🧙" * (db.MAX_USERNAME_LENGTH - 2) + "x"


class DatabaseTestUsersMixin(object):
  """An abstract class for testing db.Database implementations.

  This mixin adds methods to test the handling of GRR user and authorization
  data.
  """

  def testFilledGRRUserReadWrite(self):
    d = self.db

    u_expected = rdf_objects.GRRUser(
        username=EXAMPLE_NAME,
        ui_mode="ADVANCED",
        canary_mode=True,
        user_type=rdf_objects.GRRUser.UserType.USER_TYPE_ADMIN)
    # TODO(hanuszczak): Passwords should be required to be unicode strings.
    u_expected.password.SetPassword(b"blah")
    d.WriteGRRUser(
        EXAMPLE_NAME,
        password=u_expected.password,
        ui_mode=u_expected.ui_mode,
        canary_mode=u_expected.canary_mode,
        user_type=u_expected.user_type)

    u = d.ReadGRRUser(EXAMPLE_NAME)
    self.assertEqual(u_expected, u)

  def testEmptyGRRUserReadWrite(self):
    d = self.db

    d.WriteGRRUser("f🧙oo")
    u = d.ReadGRRUser("f🧙oo")
    u_expected = rdf_objects.GRRUser(username="f🧙oo")

    self.assertEqual(u_expected, u)

  def testInsertUserTwice(self):
    d = self.db

    d.WriteGRRUser("f🧙oo")
    d.WriteGRRUser("f🧙oo")
    u = d.ReadGRRUser("f🧙oo")
    u_expected = rdf_objects.GRRUser(username="f🧙oo")

    self.assertEqual(u_expected, u)

  def testUpdateUserTwice(self):
    d = self.db

    d.WriteGRRUser(
        "f🧙oo", user_type=rdf_objects.GRRUser.UserType.USER_TYPE_STANDARD)
    d.WriteGRRUser(
        "f🧙oo", user_type=rdf_objects.GRRUser.UserType.USER_TYPE_ADMIN)
    u = d.ReadGRRUser("f🧙oo")
    u_expected = rdf_objects.GRRUser(
        username="f🧙oo", user_type=rdf_objects.GRRUser.UserType.USER_TYPE_ADMIN)

    self.assertEqual(u_expected, u)

  def testReadingUnknownGRRUserFails(self):
    d = self.db

    with self.assertRaises(db.UnknownGRRUserError) as context:
      d.ReadGRRUser("f🧙oo")

    self.assertEqual(context.exception.username, "f🧙oo")

  def testReadingMultipleGRRUsersEntriesWorks(self):
    d = self.db

    u_foo = rdf_objects.GRRUser(
        username="f🧙oo",
        ui_mode="ADVANCED",
        canary_mode=True,
        user_type=rdf_objects.GRRUser.UserType.USER_TYPE_ADMIN)
    d.WriteGRRUser(
        u_foo.username,
        ui_mode=u_foo.ui_mode,
        canary_mode=u_foo.canary_mode,
        user_type=u_foo.user_type)
    u_bar = rdf_objects.GRRUser(username="bar")
    d.WriteGRRUser(u_bar.username)

    users = d.ReadGRRUsers()
    self.assertEqual(users[0], u_bar)
    self.assertEqual(users[1], u_foo)

  def testReadGRRUsersWithOffset(self):
    self.db.WriteGRRUser("f🧙oo1")
    self.db.WriteGRRUser("f🧙oo0")
    self.db.WriteGRRUser("f🧙oo2")

    users = self.db.ReadGRRUsers(offset=1)
    self.assertLen(users, 2)
    self.assertEqual(users[0].username, "f🧙oo1")
    self.assertEqual(users[1].username, "f🧙oo2")

  def testReadGRRUsersWithCount(self):
    self.db.WriteGRRUser("f🧙oo1")
    self.db.WriteGRRUser("f🧙oo0")
    self.db.WriteGRRUser("f🧙oo2")

    users = self.db.ReadGRRUsers(count=2)
    self.assertLen(users, 2)
    self.assertEqual(users[0].username, "f🧙oo0")
    self.assertEqual(users[1].username, "f🧙oo1")

  def testReadGRRUsersWithCountAndOffset(self):
    self.db.WriteGRRUser("f🧙oo1")
    self.db.WriteGRRUser("f🧙oo0")
    self.db.WriteGRRUser("f🧙oo2")
    self.db.WriteGRRUser("f🧙oo3")

    users = self.db.ReadGRRUsers(count=2, offset=1)
    self.assertLen(users, 2)
    self.assertEqual(users[0].username, "f🧙oo1")
    self.assertEqual(users[1].username, "f🧙oo2")

  def testWritingTooLongUsernameFails(self):
    with self.assertRaises(ValueError):
      self.db.WriteGRRUser("a" * (db.MAX_USERNAME_LENGTH + 1))

  def testDeleteGRRUser(self):
    self.db.WriteGRRUser(EXAMPLE_NAME)
    self.db.DeleteGRRUser(EXAMPLE_NAME)

    with self.assertRaises(db.UnknownGRRUserError):
      self.db.ReadGRRUser(EXAMPLE_NAME)

  def testDeleteUnknownGRRUserFails(self):
    self.db.WriteGRRUser("f🧙oobar")

    with self.assertRaises(db.UnknownGRRUserError):
      self.db.DeleteGRRUser("f🧙oo")

    self.db.ReadGRRUser("f🧙oobar")

  def testDeleteGRRUserDoesNotAffectOthers(self):
    self.db.WriteGRRUser("f🧙oobar")
    self.db.WriteGRRUser("f🧙oo")
    self.db.DeleteGRRUser("f🧙oo")
    self.db.ReadGRRUser("f🧙oobar")

  def testReadWriteApprovalRequestWithEmptyNotifiedUsersEmailsAndGrants(self):
    d = self.db

    d.WriteGRRUser("requestor")

    client_id = "C.0000000050000001"
    approval_request = rdf_objects.ApprovalRequest(
        approval_type=rdf_objects.ApprovalRequest.ApprovalType
        .APPROVAL_TYPE_CLIENT,
        subject_id=client_id,
        requestor_username="requestor",
        reason="some test reason",
        expiration_time=rdfvalue.RDFDatetime.FromSecondsSinceEpoch(42))

    approval_id = d.WriteApprovalRequest(approval_request)
    self.assertTrue(approval_id)

    read_request = d.ReadApprovalRequest("requestor", approval_id)

    # RDF values are terrible and differentiate between empty repeated fields
    # and non-set repeated fields.
    self.assertFalse(read_request.grants)
    read_request.grants = []
    approval_request.grants = []

    # Approval id and timestamp are generated in WriteApprovalRequest so we're
    # filling them into our model object ot make sure that equality check works.
    approval_request.approval_id = read_request.approval_id
    approval_request.timestamp = read_request.timestamp
    self.assertEqual(approval_request, read_request)

  def testReadWriteApprovalRequestsWithFilledInUsersEmailsAndGrants(self):
    d = self.db

    d.WriteGRRUser("user_bar")
    d.WriteGRRUser("user_foo")
    d.WriteGRRUser("requestor")

    client_id = "C.0000000050000001"
    approval_request = rdf_objects.ApprovalRequest(
        approval_type=rdf_objects.ApprovalRequest.ApprovalType
        .APPROVAL_TYPE_CLIENT,
        subject_id=client_id,
        requestor_username="requestor",
        reason="some test reason",
        expiration_time=rdfvalue.RDFDatetime.FromSecondsSinceEpoch(42),
        notified_users=["user1", "user2", "user3"],
        email_cc_addresses=["a@b.com", "c@d.com"])

    approval_id = d.WriteApprovalRequest(approval_request)

    self.db.GrantApproval(
        approval_id=approval_id,
        requestor_username="requestor",
        grantor_username="user_foo")
    self.db.GrantApproval(
        approval_id=approval_id,
        requestor_username="requestor",
        grantor_username="user_bar")

    read_request = d.ReadApprovalRequest("requestor", approval_id)

    self.assertCountEqual(approval_request.notified_users,
                          read_request.notified_users)
    self.assertCountEqual(approval_request.email_cc_addresses,
                          read_request.email_cc_addresses)
    self.assertCountEqual([g.grantor_username for g in read_request.grants],
                          ["user_foo", "user_bar"])

  def testGrantApprovalAddsNewGrantor(self):
    d = self.db

    d.WriteGRRUser("grantor")
    d.WriteGRRUser("requestor")

    client_id = "C.0000000050000001"
    approval_request = rdf_objects.ApprovalRequest(
        approval_type=rdf_objects.ApprovalRequest.ApprovalType
        .APPROVAL_TYPE_CLIENT,
        subject_id=client_id,
        requestor_username="requestor",
        reason="some test reason",
        expiration_time=rdfvalue.RDFDatetime.FromSecondsSinceEpoch(42))
    approval_id = d.WriteApprovalRequest(approval_request)

    read_request = d.ReadApprovalRequest("requestor", approval_id)
    self.assertFalse(read_request.grants)

    d.GrantApproval("requestor", approval_id, "grantor")
    read_request = d.ReadApprovalRequest("requestor", approval_id)
    self.assertLen(read_request.grants, 1)
    self.assertEqual(read_request.grants[0].grantor_username, "grantor")

  def testGrantApprovalAddsMultipleGrantorsWithSameName(self):
    d = self.db

    d.WriteGRRUser("grantor")
    d.WriteGRRUser("requestor")

    client_id = "C.0000000050000001"
    approval_request = rdf_objects.ApprovalRequest(
        approval_type=rdf_objects.ApprovalRequest.ApprovalType
        .APPROVAL_TYPE_CLIENT,
        subject_id=client_id,
        requestor_username="requestor",
        reason="some test reason",
        expiration_time=rdfvalue.RDFDatetime.FromSecondsSinceEpoch(42))
    approval_id = d.WriteApprovalRequest(approval_request)

    for _ in range(3):
      d.GrantApproval("requestor", approval_id, "grantor")

    read_request = d.ReadApprovalRequest("requestor", approval_id)
    self.assertLen(read_request.grants, 3)
    self.assertEqual([g.grantor_username for g in read_request.grants],
                     ["grantor"] * 3)

  def testReadApprovalRequeststReturnsNothingWhenNoApprovals(self):
    d = self.db

    d.WriteGRRUser("requestor")

    approvals = list(
        d.ReadApprovalRequests(
            "requestor",
            rdf_objects.ApprovalRequest.ApprovalType.APPROVAL_TYPE_CLIENT))
    self.assertFalse(approvals)

  def testReadApprovalRequestsReturnsSingleApproval(self):
    client_id = "C.0000000050000001"
    d = self.db

    d.WriteGRRUser("requestor")

    approval_request = rdf_objects.ApprovalRequest(
        approval_type=rdf_objects.ApprovalRequest.ApprovalType
        .APPROVAL_TYPE_CLIENT,
        subject_id=client_id,
        requestor_username="requestor",
        reason="some test reason",
        expiration_time=rdfvalue.RDFDatetime.Now() + rdfvalue.Duration("1d"))
    approval_id = d.WriteApprovalRequest(approval_request)

    approvals = list(
        d.ReadApprovalRequests(
            "requestor",
            rdf_objects.ApprovalRequest.ApprovalType.APPROVAL_TYPE_CLIENT))

    self.assertLen(approvals, 1)
    self.assertEqual(approvals[0].approval_id, approval_id)
    # Make sure that commit timestamp gets written and then read back correctly.
    self.assertIsNotNone(approvals[0].timestamp)

    # RDF values are terrible and differentiate between empty repeated fields
    # and non-set repeated fields.
    self.assertFalse(approvals[0].grants)
    approvals[0].grants = []
    approval_request.grants = []

    # Approval id and timestamp are generated in WriteApprovalRequest so we're
    # filling them into our model object ot make sure that equality check works.
    approval_request.approval_id = approvals[0].approval_id
    approval_request.timestamp = approvals[0].timestamp
    self.assertEqual(approval_request, approvals[0])

  def testReadApprovalRequestsReturnsMultipleApprovals(self):
    d = self.db

    d.WriteGRRUser("requestor")

    expiration_time = rdfvalue.RDFDatetime.Now() + rdfvalue.Duration("1d")

    approval_ids = set()
    for i in range(10):
      approval_request = rdf_objects.ApprovalRequest(
          approval_type=rdf_objects.ApprovalRequest.ApprovalType
          .APPROVAL_TYPE_CLIENT,
          subject_id="C.000000005000000%d" % i,
          requestor_username="requestor",
          reason="some test reason",
          expiration_time=expiration_time)
      approval_ids.add(d.WriteApprovalRequest(approval_request))

    approvals = list(
        d.ReadApprovalRequests(
            "requestor",
            rdf_objects.ApprovalRequest.ApprovalType.APPROVAL_TYPE_CLIENT))

    self.assertLen(approvals, 10)
    self.assertEqual(set(a.approval_id for a in approvals), approval_ids)

  def testReadApprovalRequestsIncludesGrantsIntoSingleApproval(self):
    client_id = "C.0000000050000001"
    d = self.db

    d.WriteGRRUser("grantor1")
    d.WriteGRRUser("grantor2")
    d.WriteGRRUser("requestor")

    approval_request = rdf_objects.ApprovalRequest(
        approval_type=rdf_objects.ApprovalRequest.ApprovalType
        .APPROVAL_TYPE_CLIENT,
        subject_id=client_id,
        requestor_username="requestor",
        reason="some test reason",
        expiration_time=rdfvalue.RDFDatetime.Now() + rdfvalue.Duration("1d"))
    approval_id = d.WriteApprovalRequest(approval_request)

    self.db.GrantApproval(
        approval_id=approval_id,
        requestor_username="requestor",
        grantor_username="grantor1")
    self.db.GrantApproval(
        approval_id=approval_id,
        requestor_username="requestor",
        grantor_username="grantor2")

    approvals = list(
        d.ReadApprovalRequests(
            "requestor",
            rdf_objects.ApprovalRequest.ApprovalType.APPROVAL_TYPE_CLIENT))

    self.assertLen(approvals, 1)
    self.assertEqual(approvals[0].approval_id, approval_id)

    self.assertCountEqual([g.grantor_username for g in approvals[0].grants],
                          ["grantor1", "grantor2"])

  def testReadApprovalRequestsIncludesGrantsIntoMultipleResults(self):
    d = self.db

    d.WriteGRRUser("requestor")

    for i in range(10):
      d.WriteGRRUser("grantor_%d_1" % i)
      d.WriteGRRUser("grantor_%d_2" % i)
      approval_request = rdf_objects.ApprovalRequest(
          approval_type=rdf_objects.ApprovalRequest.ApprovalType
          .APPROVAL_TYPE_CLIENT,
          subject_id="C.00000000000000%d" % i,
          requestor_username="requestor",
          reason="some test reason %d" % i,
          expiration_time=rdfvalue.RDFDatetime.Now() + rdfvalue.Duration("1d"))
      approval_id = d.WriteApprovalRequest(approval_request)

      self.db.GrantApproval(
          approval_id=approval_id,
          requestor_username="requestor",
          grantor_username="grantor_{}_1".format(i))
      self.db.GrantApproval(
          approval_id=approval_id,
          requestor_username="requestor",
          grantor_username="grantor_{}_2".format(i))

    approvals = sorted(
        d.ReadApprovalRequests(
            "requestor",
            rdf_objects.ApprovalRequest.ApprovalType.APPROVAL_TYPE_CLIENT),
        key=lambda a: a.reason)

    self.assertLen(approvals, 10)

    for i, approval in enumerate(approvals):
      self.assertCountEqual(
          [g.grantor_username for g in approval.grants],
          ["grantor_%d_1" % i, "grantor_%d_2" % i])

  def testReadApprovalRequestsFiltersOutExpiredApprovals(self):
    d = self.db

    d.WriteGRRUser("requestor")

    time_future = rdfvalue.RDFDatetime.Now() + rdfvalue.Duration("1d")
    time_past = rdfvalue.RDFDatetime.Now() - rdfvalue.Duration("1d")

    non_expired_approval_ids = set()
    for i in range(10):
      approval_request = rdf_objects.ApprovalRequest(
          approval_type=rdf_objects.ApprovalRequest.ApprovalType
          .APPROVAL_TYPE_CLIENT,
          subject_id="C.000000005000000%d" % i,
          requestor_username="requestor",
          reason="some test reason",
          expiration_time=(time_future if i % 2 == 0 else time_past))

      approval_id = d.WriteApprovalRequest(approval_request)
      if i % 2 == 0:
        non_expired_approval_ids.add(approval_id)

    approvals = list(
        d.ReadApprovalRequests(
            "requestor",
            rdf_objects.ApprovalRequest.ApprovalType.APPROVAL_TYPE_CLIENT))

    self.assertLen(approvals, 5)
    self.assertEqual(
        set(a.approval_id for a in approvals), non_expired_approval_ids)

  def testReadApprovalRequestsKeepsExpiredApprovalsWhenAsked(self):
    d = self.db

    d.WriteGRRUser("requestor")

    time_future = rdfvalue.RDFDatetime.Now() + rdfvalue.Duration("1d")
    time_past = rdfvalue.RDFDatetime.Now() - rdfvalue.Duration("1d")

    approval_ids = set()
    for i in range(10):
      approval_request = rdf_objects.ApprovalRequest(
          approval_type=rdf_objects.ApprovalRequest.ApprovalType
          .APPROVAL_TYPE_CLIENT,
          subject_id="C.000000005000000%d" % i,
          requestor_username="requestor",
          reason="some test reason",
          expiration_time=(time_future if i % 2 == 0 else time_past))

      approval_ids.add(d.WriteApprovalRequest(approval_request))

    approvals = list(
        d.ReadApprovalRequests(
            "requestor",
            rdf_objects.ApprovalRequest.ApprovalType.APPROVAL_TYPE_CLIENT,
            include_expired=True))

    self.assertLen(approvals, 10)
    self.assertEqual(set(a.approval_id for a in approvals), approval_ids)

  def testReadApprovalRequestsForSubjectReturnsNothingWhenNoApprovals(self):
    client_id = "C.0000000050000001"
    d = self.db

    d.WriteGRRUser("requestor")

    approvals = list(
        d.ReadApprovalRequests(
            "requestor",
            rdf_objects.ApprovalRequest.ApprovalType.APPROVAL_TYPE_CLIENT,
            subject_id=client_id))
    self.assertFalse(approvals)

  def testReadApprovalRequestsForSubjectReturnsSingleNonExpiredApproval(self):
    client_id = "C.0000000050000001"
    d = self.db

    d.WriteGRRUser("requestor")

    approval_request = rdf_objects.ApprovalRequest(
        approval_type=rdf_objects.ApprovalRequest.ApprovalType
        .APPROVAL_TYPE_CLIENT,
        subject_id=client_id,
        requestor_username="requestor",
        reason="some test reason",
        expiration_time=rdfvalue.RDFDatetime.Now() + rdfvalue.Duration("1d"))
    approval_id = d.WriteApprovalRequest(approval_request)

    approvals = list(
        d.ReadApprovalRequests(
            "requestor",
            rdf_objects.ApprovalRequest.ApprovalType.APPROVAL_TYPE_CLIENT,
            subject_id=client_id))

    self.assertLen(approvals, 1)
    self.assertEqual(approvals[0].approval_id, approval_id)

    # RDF values are terrible and differentiate between empty repeated fields
    # and non-set repeated fields.
    self.assertFalse(approvals[0].grants)
    approvals[0].grants = []
    approval_request.grants = []

    # Approval id and timestamp are generated in WriteApprovalRequest so we're
    # filling them into our model object ot make sure that equality check works.
    approval_request.approval_id = approvals[0].approval_id
    approval_request.timestamp = approvals[0].timestamp
    self.assertEqual(approval_request, approvals[0])

  def testReadApprovalRequestsForSubjectReturnsManyNonExpiredApproval(self):
    client_id = "C.0000000050000001"
    d = self.db

    d.WriteGRRUser("requestor")

    expiration_time = rdfvalue.RDFDatetime.Now() + rdfvalue.Duration("1d")

    approval_ids = set()
    for _ in range(10):
      approval_request = rdf_objects.ApprovalRequest(
          approval_type=rdf_objects.ApprovalRequest.ApprovalType
          .APPROVAL_TYPE_CLIENT,
          subject_id=client_id,
          requestor_username="requestor",
          reason="some test reason",
          expiration_time=expiration_time)
      approval_ids.add(d.WriteApprovalRequest(approval_request))

    approvals = list(
        d.ReadApprovalRequests(
            "requestor",
            rdf_objects.ApprovalRequest.ApprovalType.APPROVAL_TYPE_CLIENT,
            subject_id=client_id))

    self.assertLen(approvals, 10)
    self.assertEqual(set(a.approval_id for a in approvals), approval_ids)

  def testReadApprovalRequestsForSubjectIncludesGrantsIntoSingleResult(self):
    client_id = "C.0000000050000001"
    d = self.db

    d.WriteGRRUser("grantor1")
    d.WriteGRRUser("grantor2")
    d.WriteGRRUser("requestor")

    approval_request = rdf_objects.ApprovalRequest(
        approval_type=rdf_objects.ApprovalRequest.ApprovalType
        .APPROVAL_TYPE_CLIENT,
        subject_id=client_id,
        requestor_username="requestor",
        reason="some test reason",
        expiration_time=rdfvalue.RDFDatetime.Now() + rdfvalue.Duration("1d"))
    approval_id = d.WriteApprovalRequest(approval_request)

    self.db.GrantApproval(
        requestor_username="requestor",
        approval_id=approval_id,
        grantor_username="grantor1")
    self.db.GrantApproval(
        requestor_username="requestor",
        approval_id=approval_id,
        grantor_username="grantor2")

    approvals = list(
        d.ReadApprovalRequests(
            "requestor",
            rdf_objects.ApprovalRequest.ApprovalType.APPROVAL_TYPE_CLIENT,
            subject_id=client_id))

    self.assertLen(approvals, 1)
    self.assertEqual(approvals[0].approval_id, approval_id)

    self.assertCountEqual([g.grantor_username for g in approvals[0].grants],
                          ["grantor1", "grantor2"])

  def testReadApprovalRequestsForSubjectIncludesGrantsIntoMultipleResults(self):
    client_id = "C.000000000000001"
    d = self.db

    d.WriteGRRUser("requestor")

    for i in range(10):
      d.WriteGRRUser("grantor_%d_1" % i)
      d.WriteGRRUser("grantor_%d_2" % i)
      approval_request = rdf_objects.ApprovalRequest(
          approval_type=rdf_objects.ApprovalRequest.ApprovalType
          .APPROVAL_TYPE_CLIENT,
          subject_id=client_id,
          requestor_username="requestor",
          reason="some test reason %d" % i,
          expiration_time=rdfvalue.RDFDatetime.Now() + rdfvalue.Duration("1d"))
      approval_id = d.WriteApprovalRequest(approval_request)

      self.db.GrantApproval(
          approval_id=approval_id,
          requestor_username="requestor",
          grantor_username="grantor_{}_1".format(i))
      self.db.GrantApproval(
          approval_id=approval_id,
          requestor_username="requestor",
          grantor_username="grantor_{}_2".format(i))

    approvals = sorted(
        d.ReadApprovalRequests(
            "requestor",
            rdf_objects.ApprovalRequest.ApprovalType.APPROVAL_TYPE_CLIENT,
            subject_id=client_id),
        key=lambda a: a.reason)

    self.assertLen(approvals, 10)

    for i, approval in enumerate(approvals):
      self.assertCountEqual(
          [g.grantor_username for g in approval.grants],
          ["grantor_%d_1" % i, "grantor_%d_2" % i])

  def testReadApprovalRequestsForSubjectFiltersOutExpiredApprovals(self):
    client_id = "C.0000000050000001"
    d = self.db

    d.WriteGRRUser("requestor")

    time_future = rdfvalue.RDFDatetime.Now() + rdfvalue.Duration("1d")
    time_past = rdfvalue.RDFDatetime.Now() - rdfvalue.Duration("1d")

    non_expired_approval_ids = set()
    for i in range(10):
      approval_request = rdf_objects.ApprovalRequest(
          approval_type=rdf_objects.ApprovalRequest.ApprovalType
          .APPROVAL_TYPE_CLIENT,
          subject_id=client_id,
          requestor_username="requestor",
          reason="some test reason",
          expiration_time=(time_future if i % 2 == 0 else time_past))

      approval_id = d.WriteApprovalRequest(approval_request)
      if i % 2 == 0:
        non_expired_approval_ids.add(approval_id)

    approvals = list(
        d.ReadApprovalRequests(
            "requestor",
            rdf_objects.ApprovalRequest.ApprovalType.APPROVAL_TYPE_CLIENT,
            subject_id=client_id))

    self.assertLen(approvals, 5)
    self.assertEqual(
        set(a.approval_id for a in approvals), non_expired_approval_ids)

  def testReadApprovalRequestsForSubjectKeepsExpiredApprovalsWhenAsked(self):
    client_id = "C.0000000050000001"
    d = self.db

    d.WriteGRRUser("requestor")

    time_future = rdfvalue.RDFDatetime.Now() + rdfvalue.Duration("1d")
    time_past = rdfvalue.RDFDatetime.Now() - rdfvalue.Duration("1d")

    approval_ids = set()
    for i in range(10):
      approval_request = rdf_objects.ApprovalRequest(
          approval_type=rdf_objects.ApprovalRequest.ApprovalType
          .APPROVAL_TYPE_CLIENT,
          subject_id=client_id,
          requestor_username="requestor",
          reason="some test reason",
          expiration_time=(time_future if i % 2 == 0 else time_past))

      approval_ids.add(d.WriteApprovalRequest(approval_request))

    approvals = list(
        d.ReadApprovalRequests(
            "requestor",
            rdf_objects.ApprovalRequest.ApprovalType.APPROVAL_TYPE_CLIENT,
            subject_id=client_id,
            include_expired=True))

    self.assertLen(approvals, 10)
    self.assertEqual(set(a.approval_id for a in approvals), approval_ids)

  def testNotificationForUnknownUser(self):
    n = rdf_objects.UserNotification(
        username="doesnotexist",
        notification_type=rdf_objects.UserNotification.Type
        .TYPE_CLIENT_INTERROGATED,
        state=rdf_objects.UserNotification.State.STATE_PENDING)
    with self.assertRaises(db.UnknownGRRUserError):
      self.db.WriteUserNotification(n)

  def testNotificationCanBeWrittenAndRead(self):
    d = self.db
    username = "test"
    d.WriteGRRUser(username)

    n = rdf_objects.UserNotification(
        username=username,
        notification_type=rdf_objects.UserNotification.Type
        .TYPE_CLIENT_INTERROGATED,
        state=rdf_objects.UserNotification.State.STATE_PENDING,
        message="blah")
    d.WriteUserNotification(n)

    ns = d.ReadUserNotifications(username)
    self.assertLen(ns, 1)

    ns[0].timestamp = None  # Database generates timestamps, not interesting.
    self.assertEqual(ns[0], n)

  def testMultipleNotificationsCanBeWrittenAndRead(self):
    username = "test"
    self.db.WriteGRRUser(username)

    # pylint: disable=invalid-name
    NotificationType = rdf_objects.UserNotification.Type
    NotificationState = rdf_objects.UserNotification.State
    # pylint: enable=invalid-name

    self.db.WriteUserNotification(
        rdf_objects.UserNotification(
            username=username,
            notification_type=NotificationType.TYPE_CLIENT_INTERROGATED,
            state=NotificationState.STATE_PENDING,
            message="Lorem ipsum."))

    self.db.WriteUserNotification(
        rdf_objects.UserNotification(
            username=username,
            notification_type=NotificationType.TYPE_CLIENT_APPROVAL_REQUESTED,
            state=NotificationState.STATE_NOT_PENDING,
            message="Dolor sit amet."))

    self.db.WriteUserNotification(
        rdf_objects.UserNotification(
            username=username,
            notification_type=NotificationType.TYPE_FLOW_RUN_FAILED,
            state=NotificationState.STATE_PENDING,
            message="Consectetur adipiscing elit."))

    notifications = self.db.ReadUserNotifications(username)

    # TODO(hanuszczak): Database API should guaranee to return notifications
    # ordered by timestamp.
    notifications.sort(key=lambda notification: notification.timestamp)

    self.assertLen(notifications, 3)

    self.assertEqual(notifications[0].username, username)
    self.assertEqual(notifications[0].notification_type,
                     NotificationType.TYPE_CLIENT_INTERROGATED)
    self.assertEqual(notifications[0].state, NotificationState.STATE_PENDING)
    self.assertEqual(notifications[0].message, "Lorem ipsum.")

    self.assertEqual(notifications[1].username, username)
    self.assertEqual(notifications[1].notification_type,
                     NotificationType.TYPE_CLIENT_APPROVAL_REQUESTED)
    self.assertEqual(notifications[1].state,
                     NotificationState.STATE_NOT_PENDING)
    self.assertEqual(notifications[1].message, "Dolor sit amet.")

    self.assertEqual(notifications[2].username, username)
    self.assertEqual(notifications[2].notification_type,
                     NotificationType.TYPE_FLOW_RUN_FAILED)
    self.assertEqual(notifications[2].state, NotificationState.STATE_PENDING)
    self.assertEqual(notifications[2].message, "Consectetur adipiscing elit.")

  def testNotificationTimestampIsGeneratedWhenNotExplicit(self):
    d = self.db
    username = "test"
    d.WriteGRRUser(username)

    n = rdf_objects.UserNotification(
        username=username,
        notification_type=rdf_objects.UserNotification.Type
        .TYPE_CLIENT_INTERROGATED,
        state=rdf_objects.UserNotification.State.STATE_PENDING,
        message="blah")
    d.WriteUserNotification(n)

    ns = d.ReadUserNotifications(username)
    self.assertLen(ns, 1)
    self.assertNotEqual(int(ns[0].timestamp), 0)

    self.assertNotEqual(ns[0], n)
    n.timestamp = ns[0].timestamp
    self.assertEqual(ns[0], n)

  def _SetupUserNotificationTimerangeTest(self, username="test"):
    d = self.db
    d.WriteGRRUser(username)

    ts = []

    ts.append(rdfvalue.RDFDatetime.Now())

    n = rdf_objects.UserNotification(
        username=username,
        notification_type=rdf_objects.UserNotification.Type
        .TYPE_CLIENT_INTERROGATED,
        state=rdf_objects.UserNotification.State.STATE_PENDING,
        message="n0")
    d.WriteUserNotification(n)

    ts.append(rdfvalue.RDFDatetime.Now())

    n = rdf_objects.UserNotification(
        username=username,
        notification_type=rdf_objects.UserNotification.Type
        .TYPE_CLIENT_INTERROGATED,
        state=rdf_objects.UserNotification.State.STATE_PENDING,
        message="n1")
    d.WriteUserNotification(n)

    ts.append(rdfvalue.RDFDatetime.Now())

    return ts

  def testReadUserNotificationsWithEmptyTimerange(self):
    d = self.db
    username = "test"

    self._SetupUserNotificationTimerangeTest()

    ns = d.ReadUserNotifications(username, timerange=(None, None))
    ns = sorted(ns, key=lambda x: x.message)
    self.assertLen(ns, 2)
    self.assertEqual(ns[0].message, "n0")
    self.assertEqual(ns[1].message, "n1")

  def testReadUserNotificationsWithTimerangeWithBothFromTo(self):
    d = self.db
    username = "test"

    ts = self._SetupUserNotificationTimerangeTest()

    ns = d.ReadUserNotifications(username, timerange=(ts[0], ts[1]))
    self.assertLen(ns, 1)
    self.assertEqual(ns[0].message, "n0")

    ns = d.ReadUserNotifications(username, timerange=(ts[0], ts[2]))
    ns = sorted(ns, key=lambda x: x.message)
    self.assertLen(ns, 2)
    self.assertEqual(ns[0].message, "n0")
    self.assertEqual(ns[1].message, "n1")

  def testReadUserNotificationsWithTimerangeWithFromOnly(self):
    d = self.db
    username = "test"

    ts = self._SetupUserNotificationTimerangeTest()

    ns = d.ReadUserNotifications(username, timerange=(ts[1], None))
    self.assertLen(ns, 1)
    self.assertEqual(ns[0].message, "n1")

  def testReadUserNotificationsWithTimerangeWithToOnly(self):
    d = self.db
    username = "test"

    ts = self._SetupUserNotificationTimerangeTest()

    ns = d.ReadUserNotifications(username, timerange=(None, ts[1]))
    self.assertLen(ns, 1)
    self.assertEqual(ns[0].message, "n0")

  def testReadUserNotificationsWithTimerangeEdgeCases(self):
    d = self.db
    username = "test"

    self._SetupUserNotificationTimerangeTest()
    all_ns = d.ReadUserNotifications(username)
    self.assertLen(all_ns, 2)

    for n in all_ns:
      ns = d.ReadUserNotifications(
          username, timerange=(n.timestamp, n.timestamp))
      self.assertLen(ns, 1)
      self.assertEqual(ns[0], n)

    v_from = min(all_ns[0].timestamp, all_ns[1].timestamp)
    v_to = max(all_ns[0].timestamp, all_ns[1].timestamp)

    ns = d.ReadUserNotifications(username, timerange=(v_from, v_to))
    ns = sorted(ns, key=lambda x: x.message)
    self.assertLen(ns, 2)
    self.assertEqual(ns[0].message, "n0")
    self.assertEqual(ns[1].message, "n1")

  def testReadUserNotificationsWithStateFilter(self):
    d = self.db
    username = "test"

    self._SetupUserNotificationTimerangeTest()

    ns = d.ReadUserNotifications(
        username, state=rdf_objects.UserNotification.State.STATE_NOT_PENDING)
    self.assertEmpty(ns)

    ns = d.ReadUserNotifications(
        username, state=rdf_objects.UserNotification.State.STATE_PENDING)
    self.assertLen(ns, 2)

  def testReadUserNotificationsWithStateAndTimerange(self):
    d = self.db
    username = "test"

    ts = self._SetupUserNotificationTimerangeTest()

    ns = d.ReadUserNotifications(
        username,
        timerange=(ts[0], ts[1]),
        state=rdf_objects.UserNotification.State.STATE_NOT_PENDING)
    self.assertEmpty(ns)

    ns = d.ReadUserNotifications(
        username,
        timerange=(ts[0], ts[1]),
        state=rdf_objects.UserNotification.State.STATE_PENDING)
    self.assertLen(ns, 1)
    self.assertEqual(ns[0].message, "n0")

  def testUpdateUserNotificationsUpdatesState(self):
    d = self.db
    username = "test"

    self._SetupUserNotificationTimerangeTest()
    all_ns = d.ReadUserNotifications(username)
    all_ns = sorted(all_ns, key=lambda x: x.message)

    d.UpdateUserNotifications(
        username, [all_ns[0].timestamp],
        state=rdf_objects.UserNotification.State.STATE_NOT_PENDING)

    ns = d.ReadUserNotifications(username)
    ns = sorted(ns, key=lambda x: x.message)
    self.assertEqual(ns[0].state,
                     rdf_objects.UserNotification.State.STATE_NOT_PENDING)
    self.assertEqual(ns[1].state,
                     rdf_objects.UserNotification.State.STATE_PENDING)

  def testDeleteUserDeletesApprovalRequests(self):
    d = self.db
    d.WriteGRRUser("requestor")
    d.WriteGRRUser("grantor")

    client_id = "C.0000000050000001"
    approval_request = rdf_objects.ApprovalRequest(
        approval_type=rdf_objects.ApprovalRequest.ApprovalType
        .APPROVAL_TYPE_CLIENT,
        subject_id=client_id,
        requestor_username="requestor",
        reason="some test reason",
        expiration_time=rdfvalue.RDFDatetime.FromSecondsSinceEpoch(42))

    approval_id = d.WriteApprovalRequest(approval_request)
    self.assertTrue(approval_id)
    d.ReadApprovalRequest("requestor", approval_id)

    d.DeleteGRRUser("requestor")

    with self.assertRaises(db.UnknownApprovalRequestError):
      d.ReadApprovalRequest("requestor", approval_id)

  def testDeleteUserDeletesApprovalGrantsForGrantor(self):
    d = self.db
    d.WriteGRRUser("requestor")
    d.WriteGRRUser("grantor")
    d.WriteGRRUser("grantor2")

    client_id = "C.0000000050000001"
    approval_request = rdf_objects.ApprovalRequest(
        approval_type=rdf_objects.ApprovalRequest.ApprovalType
        .APPROVAL_TYPE_CLIENT,
        subject_id=client_id,
        requestor_username="requestor",
        reason="some test reason",
        expiration_time=rdfvalue.RDFDatetime.FromSecondsSinceEpoch(42),
        notified_users=["user1", "user2", "user3"],
        email_cc_addresses=["a@b.com", "c@d.com"])

    approval_id = d.WriteApprovalRequest(approval_request)

    self.db.GrantApproval(
        requestor_username="requestor",
        approval_id=approval_id,
        grantor_username="grantor")
    self.db.GrantApproval(
        requestor_username="requestor",
        approval_id=approval_id,
        grantor_username="grantor2")

    d.DeleteGRRUser("grantor")
    result = d.ReadApprovalRequest("requestor", approval_id)
    self.assertLen(result.grants, 1)
    self.assertEqual(result.grants[0].grantor_username, "grantor2")

  def testDeleteUserDeletesNotifications(self):
    d = self.db
    username = "test"
    self._SetupUserNotificationTimerangeTest(username)
    self.assertNotEmpty(
        d.ReadUserNotifications(username, timerange=(None, None)))
    d.DeleteGRRUser(username)
    self.assertEmpty(d.ReadUserNotifications(username, timerange=(None, None)))


# This file is a test library and thus does not require a __main__ block.
