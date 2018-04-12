#!/usr/bin/env python
# -*- mode: python; encoding: utf-8 -*-
import abc

from grr.lib import rdfvalue
from grr.lib.rdfvalues import objects
from grr.server import db


class DatabaseTestUsersMixin(object):
  """An abstract class for testing db.Database implementations.

  This mixin adds methods to test the handling of GRR user and authorization
  data.

  Implementations should override CreateDatabase in order to produce
  a test suite for a particular implementation of db.Database.

  This class does not inherit from `TestCase` to prevent the test runner from
  executing its method. Instead it should be mixed into the actual test classes.
  """
  __metaclass__ = abc.ABCMeta

  @abc.abstractmethod
  def CreateDatabase(self):
    """Create a test database.

    Returns:
      A pair (db, cleanup), where db is an instance of db.Database to be tested
      and cleanup is a function which destroys db, releasing any resources held
      by it.
    """

  def setUp(self):
    self.db, self.cleanup = self.CreateDatabase()

  def tearDown(self):
    if self.cleanup:
      self.cleanup()

  def testFilledGRRUserReadWrite(self):
    d = self.db

    u_expected = objects.GRRUser(
        username="foo",
        ui_mode="ADVANCED",
        canary_mode=True,
        user_type=objects.GRRUser.UserType.USER_TYPE_ADMIN)
    u_expected.password.SetPassword("blah")
    d.WriteGRRUser(
        "foo",
        password=u_expected.password,
        ui_mode=u_expected.ui_mode,
        canary_mode=u_expected.canary_mode,
        user_type=u_expected.user_type)

    u = d.ReadGRRUser("foo")
    self.assertEqual(u_expected, u)

  def testEmptyGRRUserReadWrite(self):
    d = self.db

    d.WriteGRRUser("foo")
    u = d.ReadGRRUser("foo")
    u_expected = objects.GRRUser(username="foo")

    self.assertEqual(u_expected, u)

  def testReadingUnknownGRRUserFails(self):
    d = self.db

    with self.assertRaises(db.UnknownGRRUserError):
      d.ReadGRRUser("foo")

  def testReadingMultipleGRRUsersEntriesWorks(self):
    d = self.db

    u_foo = objects.GRRUser(
        username="foo",
        ui_mode="ADVANCED",
        canary_mode=True,
        user_type=objects.GRRUser.UserType.USER_TYPE_ADMIN)
    d.WriteGRRUser(
        u_foo.username,
        ui_mode=u_foo.ui_mode,
        canary_mode=u_foo.canary_mode,
        user_type=u_foo.user_type)
    u_bar = objects.GRRUser(username="bar")
    d.WriteGRRUser(u_bar.username)

    users = sorted(d.ReadAllGRRUsers(), key=lambda x: x.username)
    self.assertEqual(users[0], u_bar)
    self.assertEqual(users[1], u_foo)

  def testReadWriteApprovalRequestWithEmptyNotifiedUsersEmailsAndGrants(self):
    d = self.db

    # Ensure that the requestor user exists.
    d.WriteGRRUser("requestor")

    client_id = "C.0000000050000001"
    approval_request = objects.ApprovalRequest(
        approval_type=objects.ApprovalRequest.ApprovalType.APPROVAL_TYPE_CLIENT,
        subject_id=client_id,
        requestor_username="requestor",
        reason="some test reason",
        expiration_time=rdfvalue.RDFDatetime(42))

    approval_id = d.WriteApprovalRequest(approval_request)
    self.assertTrue(approval_id)

    read_request = d.ReadApprovalRequest("requestor", approval_id)

    # Approval id and timestamp are generated in WriteApprovalRequest so we're
    # filling them into our model object ot make sure that equality check works.
    approval_request.approval_id = read_request.approval_id
    approval_request.timestamp = read_request.timestamp
    self.assertEqual(approval_request, read_request)

  def testReadWriteApprovalRequestsWithFilledInUsersEmailsAndGrants(self):
    d = self.db

    # Ensure that the requestor user exists.
    d.WriteGRRUser("requestor")

    client_id = "C.0000000050000001"
    approval_request = objects.ApprovalRequest(
        approval_type=objects.ApprovalRequest.ApprovalType.APPROVAL_TYPE_CLIENT,
        subject_id=client_id,
        requestor_username="requestor",
        reason="some test reason",
        expiration_time=rdfvalue.RDFDatetime(42),
        notified_users=["user1", "user2", "user3"],
        email_cc_addresses=["a@b.com", "c@d.com"],
        grants=[
            objects.ApprovalGrant(grantor_username="user_foo"),
            objects.ApprovalGrant(grantor_username="user_bar")
        ])

    approval_id = d.WriteApprovalRequest(approval_request)

    read_request = d.ReadApprovalRequest("requestor", approval_id)

    self.assertEqual(
        sorted(approval_request.notified_users),
        sorted(read_request.notified_users))
    self.assertEqual(
        sorted(approval_request.email_cc_addresses),
        sorted(read_request.email_cc_addresses))
    self.assertEqual(
        sorted(g.grantor_username for g in approval_request.grants),
        sorted(g.grantor_username for g in read_request.grants))

  def testGrantApprovalAddsNewGrantor(self):
    d = self.db

    # Ensure that the requestor user exists.
    d.WriteGRRUser("requestor")

    client_id = "C.0000000050000001"
    approval_request = objects.ApprovalRequest(
        approval_type=objects.ApprovalRequest.ApprovalType.APPROVAL_TYPE_CLIENT,
        subject_id=client_id,
        requestor_username="requestor",
        reason="some test reason",
        expiration_time=rdfvalue.RDFDatetime(42))
    approval_id = d.WriteApprovalRequest(approval_request)

    read_request = d.ReadApprovalRequest("requestor", approval_id)
    self.assertFalse(read_request.grants)

    d.GrantApproval("requestor", approval_id, "grantor")
    read_request = d.ReadApprovalRequest("requestor", approval_id)
    self.assertEqual(len(read_request.grants), 1)
    self.assertEqual(read_request.grants[0].grantor_username, "grantor")

  def testGrantApprovalAddsMultipleGrantorsWithSameName(self):
    d = self.db

    # Ensure that the requestor user exists.
    d.WriteGRRUser("requestor")

    client_id = "C.0000000050000001"
    approval_request = objects.ApprovalRequest(
        approval_type=objects.ApprovalRequest.ApprovalType.APPROVAL_TYPE_CLIENT,
        subject_id=client_id,
        requestor_username="requestor",
        reason="some test reason",
        expiration_time=rdfvalue.RDFDatetime(42))
    approval_id = d.WriteApprovalRequest(approval_request)

    for _ in range(3):
      d.GrantApproval("requestor", approval_id, "grantor")

    read_request = d.ReadApprovalRequest("requestor", approval_id)
    self.assertEqual(len(read_request.grants), 3)
    self.assertEqual([g.grantor_username for g in read_request.grants],
                     ["grantor"] * 3)

  def testReadApprovalRequeststReturnsNothingWhenNoApprovals(self):
    d = self.db

    # Ensure that the requestor user exists.
    d.WriteGRRUser("requestor")

    approvals = list(
        d.ReadApprovalRequests(
            "requestor",
            objects.ApprovalRequest.ApprovalType.APPROVAL_TYPE_CLIENT))
    self.assertFalse(approvals)

  def testReadApprovalRequestsReturnsSingleApproval(self):
    client_id = "C.0000000050000001"
    d = self.db

    # Ensure that the requestor user exists.
    d.WriteGRRUser("requestor")

    approval_request = objects.ApprovalRequest(
        approval_type=objects.ApprovalRequest.ApprovalType.APPROVAL_TYPE_CLIENT,
        subject_id=client_id,
        requestor_username="requestor",
        reason="some test reason",
        expiration_time=rdfvalue.RDFDatetime.Now() + rdfvalue.Duration("1d"))
    approval_id = d.WriteApprovalRequest(approval_request)

    approvals = list(
        d.ReadApprovalRequests(
            "requestor",
            objects.ApprovalRequest.ApprovalType.APPROVAL_TYPE_CLIENT))

    self.assertEqual(len(approvals), 1)
    self.assertEqual(approvals[0].approval_id, approval_id)

    # Approval id and timestamp are generated in WriteApprovalRequest so we're
    # filling them into our model object ot make sure that equality check works.
    approval_request.approval_id = approvals[0].approval_id
    approval_request.timestamp = approvals[0].timestamp
    self.assertEqual(approval_request, approvals[0])

  def testReadApprovalRequestsReturnsMultipleApprovals(self):
    d = self.db

    # Ensure that the requestor user exists.
    d.WriteGRRUser("requestor")

    expiration_time = rdfvalue.RDFDatetime.Now() + rdfvalue.Duration("1d")

    approval_ids = set()
    for i in range(10):
      approval_request = objects.ApprovalRequest(
          approval_type=objects.ApprovalRequest.ApprovalType.
          APPROVAL_TYPE_CLIENT,
          subject_id="C.000000005000000%d" % i,
          requestor_username="requestor",
          reason="some test reason",
          expiration_time=expiration_time)
      approval_ids.add(d.WriteApprovalRequest(approval_request))

    approvals = list(
        d.ReadApprovalRequests(
            "requestor",
            objects.ApprovalRequest.ApprovalType.APPROVAL_TYPE_CLIENT))

    self.assertEqual(len(approvals), 10)
    self.assertEqual(set(a.approval_id for a in approvals), approval_ids)

  def testReadApprovalRequestsIncludesGrantsIntoSingleApproval(self):
    client_id = "C.0000000050000001"
    d = self.db

    # Ensure that the requestor user exists.
    d.WriteGRRUser("requestor")

    approval_request = objects.ApprovalRequest(
        approval_type=objects.ApprovalRequest.ApprovalType.APPROVAL_TYPE_CLIENT,
        subject_id=client_id,
        requestor_username="requestor",
        reason="some test reason",
        grants=[
            objects.ApprovalGrant(grantor_username="grantor1"),
            objects.ApprovalGrant(grantor_username="grantor2")
        ],
        expiration_time=rdfvalue.RDFDatetime.Now() + rdfvalue.Duration("1d"))
    approval_id = d.WriteApprovalRequest(approval_request)

    approvals = list(
        d.ReadApprovalRequests(
            "requestor",
            objects.ApprovalRequest.ApprovalType.APPROVAL_TYPE_CLIENT))

    self.assertEqual(len(approvals), 1)
    self.assertEqual(approvals[0].approval_id, approval_id)

    self.assertEqual(
        sorted(g.grantor_username for g in approvals[0].grants),
        ["grantor1", "grantor2"])

  def testReadApprovalRequestsIncludesGrantsIntoMultipleResults(self):
    d = self.db

    # Ensure that the requestor user exists.
    d.WriteGRRUser("requestor")

    for i in range(10):
      approval_request = objects.ApprovalRequest(
          approval_type=objects.ApprovalRequest.ApprovalType.
          APPROVAL_TYPE_CLIENT,
          subject_id="C.00000000000000%d" % i,
          requestor_username="requestor",
          reason="some test reason %d" % i,
          grants=[
              objects.ApprovalGrant(grantor_username="grantor_%d_1" % i),
              objects.ApprovalGrant(grantor_username="grantor_%d_2" % i)
          ],
          expiration_time=rdfvalue.RDFDatetime.Now() + rdfvalue.Duration("1d"))
      d.WriteApprovalRequest(approval_request)

    approvals = sorted(
        d.ReadApprovalRequests(
            "requestor",
            objects.ApprovalRequest.ApprovalType.APPROVAL_TYPE_CLIENT),
        key=lambda a: a.reason)

    self.assertEqual(len(approvals), 10)

    for i, approval in enumerate(approvals):
      self.assertEqual(
          sorted(g.grantor_username for g in approval.grants),
          ["grantor_%d_1" % i, "grantor_%d_2" % i])

  def testReadApprovalRequestsFiltersOutExpiredApprovals(self):
    d = self.db

    # Ensure that the requestor user exists.
    d.WriteGRRUser("requestor")

    time_future = rdfvalue.RDFDatetime.Now() + rdfvalue.Duration("1d")
    time_past = rdfvalue.RDFDatetime.Now() - rdfvalue.Duration("1d")

    non_expired_approval_ids = set()
    for i in range(10):
      approval_request = objects.ApprovalRequest(
          approval_type=objects.ApprovalRequest.ApprovalType.
          APPROVAL_TYPE_CLIENT,
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
            objects.ApprovalRequest.ApprovalType.APPROVAL_TYPE_CLIENT))

    self.assertEqual(len(approvals), 5)
    self.assertEqual(
        set(a.approval_id for a in approvals), non_expired_approval_ids)

  def testReadApprovalRequestsKeepsExpiredApprovalsWhenAsked(self):
    d = self.db

    # Ensure that the requestor user exists.
    d.WriteGRRUser("requestor")

    time_future = rdfvalue.RDFDatetime.Now() + rdfvalue.Duration("1d")
    time_past = rdfvalue.RDFDatetime.Now() - rdfvalue.Duration("1d")

    approval_ids = set()
    for i in range(10):
      approval_request = objects.ApprovalRequest(
          approval_type=objects.ApprovalRequest.ApprovalType.
          APPROVAL_TYPE_CLIENT,
          subject_id="C.000000005000000%d" % i,
          requestor_username="requestor",
          reason="some test reason",
          expiration_time=(time_future if i % 2 == 0 else time_past))

      approval_ids.add(d.WriteApprovalRequest(approval_request))

    approvals = list(
        d.ReadApprovalRequests(
            "requestor",
            objects.ApprovalRequest.ApprovalType.APPROVAL_TYPE_CLIENT,
            include_expired=True))

    self.assertEqual(len(approvals), 10)
    self.assertEqual(set(a.approval_id for a in approvals), approval_ids)

  def testReadApprovalRequestsForSubjectReturnsNothingWhenNoApprovals(self):
    client_id = "C.0000000050000001"
    d = self.db

    # Ensure that the requestor user exists.
    d.WriteGRRUser("requestor")

    approvals = list(
        d.ReadApprovalRequests(
            "requestor",
            objects.ApprovalRequest.ApprovalType.APPROVAL_TYPE_CLIENT,
            subject_id=client_id))
    self.assertFalse(approvals)

  def testReadApprovalRequestsForSubjectReturnsSingleNonExpiredApproval(self):
    client_id = "C.0000000050000001"
    d = self.db

    # Ensure that the requestor user exists.
    d.WriteGRRUser("requestor")

    approval_request = objects.ApprovalRequest(
        approval_type=objects.ApprovalRequest.ApprovalType.APPROVAL_TYPE_CLIENT,
        subject_id=client_id,
        requestor_username="requestor",
        reason="some test reason",
        expiration_time=rdfvalue.RDFDatetime.Now() + rdfvalue.Duration("1d"))
    approval_id = d.WriteApprovalRequest(approval_request)

    approvals = list(
        d.ReadApprovalRequests(
            "requestor",
            objects.ApprovalRequest.ApprovalType.APPROVAL_TYPE_CLIENT,
            subject_id=client_id))

    self.assertEqual(len(approvals), 1)
    self.assertEqual(approvals[0].approval_id, approval_id)

    # Approval id and timestamp are generated in WriteApprovalRequest so we're
    # filling them into our model object ot make sure that equality check works.
    approval_request.approval_id = approvals[0].approval_id
    approval_request.timestamp = approvals[0].timestamp
    self.assertEqual(approval_request, approvals[0])

  def testReadApprovalRequestsForSubjectReturnsManyNonExpiredApproval(self):
    client_id = "C.0000000050000001"
    d = self.db

    # Ensure that the requestor user exists.
    d.WriteGRRUser("requestor")

    expiration_time = rdfvalue.RDFDatetime.Now() + rdfvalue.Duration("1d")

    approval_ids = set()
    for _ in range(10):
      approval_request = objects.ApprovalRequest(
          approval_type=objects.ApprovalRequest.ApprovalType.
          APPROVAL_TYPE_CLIENT,
          subject_id=client_id,
          requestor_username="requestor",
          reason="some test reason",
          expiration_time=expiration_time)
      approval_ids.add(d.WriteApprovalRequest(approval_request))

    approvals = list(
        d.ReadApprovalRequests(
            "requestor",
            objects.ApprovalRequest.ApprovalType.APPROVAL_TYPE_CLIENT,
            subject_id=client_id))

    self.assertEqual(len(approvals), 10)
    self.assertEqual(set(a.approval_id for a in approvals), approval_ids)

  def testReadApprovalRequestsForSubjectIncludesGrantsIntoSingleResult(self):
    client_id = "C.0000000050000001"
    d = self.db

    # Ensure that the requestor user exists.
    d.WriteGRRUser("requestor")

    approval_request = objects.ApprovalRequest(
        approval_type=objects.ApprovalRequest.ApprovalType.APPROVAL_TYPE_CLIENT,
        subject_id=client_id,
        requestor_username="requestor",
        reason="some test reason",
        grants=[
            objects.ApprovalGrant(grantor_username="grantor1"),
            objects.ApprovalGrant(grantor_username="grantor2")
        ],
        expiration_time=rdfvalue.RDFDatetime.Now() + rdfvalue.Duration("1d"))
    approval_id = d.WriteApprovalRequest(approval_request)

    approvals = list(
        d.ReadApprovalRequests(
            "requestor",
            objects.ApprovalRequest.ApprovalType.APPROVAL_TYPE_CLIENT,
            subject_id=client_id))

    self.assertEqual(len(approvals), 1)
    self.assertEqual(approvals[0].approval_id, approval_id)

    self.assertEqual(
        sorted(g.grantor_username for g in approvals[0].grants),
        ["grantor1", "grantor2"])

  def testReadApprovalRequestsForSubjectIncludesGrantsIntoMultipleResults(self):
    client_id = "C.000000000000001"
    d = self.db

    # Ensure that the requestor user exists.
    d.WriteGRRUser("requestor")

    for i in range(10):
      approval_request = objects.ApprovalRequest(
          approval_type=objects.ApprovalRequest.ApprovalType.
          APPROVAL_TYPE_CLIENT,
          subject_id=client_id,
          requestor_username="requestor",
          reason="some test reason %d" % i,
          grants=[
              objects.ApprovalGrant(grantor_username="grantor_%d_1" % i),
              objects.ApprovalGrant(grantor_username="grantor_%d_2" % i)
          ],
          expiration_time=rdfvalue.RDFDatetime.Now() + rdfvalue.Duration("1d"))
      d.WriteApprovalRequest(approval_request)

    approvals = sorted(
        d.ReadApprovalRequests(
            "requestor",
            objects.ApprovalRequest.ApprovalType.APPROVAL_TYPE_CLIENT,
            subject_id=client_id),
        key=lambda a: a.reason)

    self.assertEqual(len(approvals), 10)

    for i, approval in enumerate(approvals):
      self.assertEqual(
          sorted(g.grantor_username for g in approval.grants),
          ["grantor_%d_1" % i, "grantor_%d_2" % i])

  def testReadApprovalRequestsForSubjectFiltersOutExpiredApprovals(self):
    client_id = "C.0000000050000001"
    d = self.db

    # Ensure that the requestor user exists.
    d.WriteGRRUser("requestor")

    time_future = rdfvalue.RDFDatetime.Now() + rdfvalue.Duration("1d")
    time_past = rdfvalue.RDFDatetime.Now() - rdfvalue.Duration("1d")

    non_expired_approval_ids = set()
    for i in range(10):
      approval_request = objects.ApprovalRequest(
          approval_type=objects.ApprovalRequest.ApprovalType.
          APPROVAL_TYPE_CLIENT,
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
            objects.ApprovalRequest.ApprovalType.APPROVAL_TYPE_CLIENT,
            subject_id=client_id))

    self.assertEqual(len(approvals), 5)
    self.assertEqual(
        set(a.approval_id for a in approvals), non_expired_approval_ids)

  def testReadApprovalRequestsForSubjectKeepsExpiredApprovalsWhenAsked(self):
    client_id = "C.0000000050000001"
    d = self.db

    # Ensure that the requestor user exists.
    d.WriteGRRUser("requestor")

    time_future = rdfvalue.RDFDatetime.Now() + rdfvalue.Duration("1d")
    time_past = rdfvalue.RDFDatetime.Now() - rdfvalue.Duration("1d")

    approval_ids = set()
    for i in range(10):
      approval_request = objects.ApprovalRequest(
          approval_type=objects.ApprovalRequest.ApprovalType.
          APPROVAL_TYPE_CLIENT,
          subject_id=client_id,
          requestor_username="requestor",
          reason="some test reason",
          expiration_time=(time_future if i % 2 == 0 else time_past))

      approval_ids.add(d.WriteApprovalRequest(approval_request))

    approvals = list(
        d.ReadApprovalRequests(
            "requestor",
            objects.ApprovalRequest.ApprovalType.APPROVAL_TYPE_CLIENT,
            subject_id=client_id,
            include_expired=True))

    self.assertEqual(len(approvals), 10)
    self.assertEqual(set(a.approval_id for a in approvals), approval_ids)
