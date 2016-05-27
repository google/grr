#!/usr/bin/env python
"""Tests for grr.lib.aff4_objects.security."""

from grr.lib import access_control
from grr.lib import aff4
from grr.lib import config_lib
from grr.lib import flags
from grr.lib import flow
from grr.lib import rdfvalue
from grr.lib import test_lib
from grr.lib import utils
from grr.lib.aff4_objects import security


class ApprovalTest(test_lib.GRRBaseTest):
  """Test for Approval."""

  def setUp(self):
    super(ApprovalTest, self).setUp()
    self.client_id = self.SetupClients(1)[0]
    self.approval_expiration = rdfvalue.Duration(
        "%ds" % config_lib.CONFIG["ACL.token_expiry"])

  def testGetApprovalForObjectRaisesWhenTokenIsNone(self):
    with self.assertRaisesRegexp(access_control.UnauthorizedAccess,
                                 "No token given"):
      security.Approval.GetApprovalForObject(self.client_id, token=None)

  def testGetApprovalForObjectRaisesIfNoApprovals(self):
    with self.assertRaisesRegexp(access_control.UnauthorizedAccess,
                                 "No approvals found"):
      security.Approval.GetApprovalForObject(self.client_id, token=self.token)

  def testGetApprovalForObjectRaisesIfSingleAvailableApprovalExpired(self):
    self.RequestAndGrantClientApproval(self.client_id, token=self.token)

    # Make sure approval is expired by the time we call GetApprovalForObject.
    now = rdfvalue.RDFDatetime().Now()
    with test_lib.FakeTime(now + self.approval_expiration + rdfvalue.Duration(
        "1s")):
      with self.assertRaisesRegexp(access_control.UnauthorizedAccess,
                                   "Requires 2 approvers for access."):
        security.Approval.GetApprovalForObject(self.client_id, token=self.token)

  def testGetApprovalForObjectRaisesIfAllAvailableApprovalsExpired(self):
    # Set up 2 approvals with different reasons.
    token1 = access_control.ACLToken(username=self.token.username,
                                     reason="reason1")
    self.RequestAndGrantClientApproval(self.client_id, token=token1)

    token2 = access_control.ACLToken(username=self.token.username,
                                     reason="reason2")
    self.RequestAndGrantClientApproval(self.client_id, token=token2)

    # Make sure that approvals are expired by the time we call
    # GetApprovalForObject.
    now = rdfvalue.RDFDatetime().Now()
    with test_lib.FakeTime(now + self.approval_expiration + rdfvalue.Duration(
        "1s")):
      with self.assertRaisesRegexp(access_control.UnauthorizedAccess,
                                   "Requires 2 approvers for access."):
        security.Approval.GetApprovalForObject(self.client_id, token=self.token)

  def testGetApprovalForObjectReturnsSingleAvailableApproval(self):
    self.RequestAndGrantClientApproval(self.client_id, token=self.token)

    approved_token = security.Approval.GetApprovalForObject(self.client_id,
                                                            token=self.token)
    self.assertEqual(approved_token.reason, self.token.reason)

  def testGetApprovalForObjectReturnsNonExpiredApprovalFromMany(self):
    token1 = access_control.ACLToken(username=self.token.username,
                                     reason="reason1")
    self.RequestAndGrantClientApproval(self.client_id, token=token1)

    now = rdfvalue.RDFDatetime().Now()
    with test_lib.FakeTime(now + self.approval_expiration, increment=1e-6):
      token2 = access_control.ACLToken(username=self.token.username,
                                       reason="reason2")
      self.RequestAndGrantClientApproval(self.client_id, token=token2)

    # Make sure only the first approval is expired by the time
    # GetApprovalForObject is called.
    with test_lib.FakeTime(now + self.approval_expiration + rdfvalue.Duration(
        "1h")):
      approved_token = security.Approval.GetApprovalForObject(self.client_id,
                                                              token=self.token)
      self.assertEqual(approved_token.reason, token2.reason)

  def testGetApprovalForObjectRaisesIfApprovalsAreOfWrongType(self):
    # Create AFF4Volume object where Approval is expected to be.
    approval_urn = aff4.ROOT_URN.Add("ACL").Add(self.client_id.Path()).Add(
        self.token.username).Add(utils.EncodeReasonString(self.token.reason))
    with aff4.FACTORY.Create(approval_urn,
                             aff4.AFF4Volume,
                             token=self.token) as _:
      pass

    with self.assertRaisesRegexp(access_control.UnauthorizedAccess,
                                 "Couldn't open any of 1 approvals"):
      security.Approval.GetApprovalForObject(self.client_id, token=self.token)


class ApprovalWithReasonTest(test_lib.GRRBaseTest):
  """Test for ApprovalWithReason mixin."""

  def setUp(self):
    super(ApprovalWithReasonTest, self).setUp()
    self.approval_obj = security.AbstractApprovalWithReason()

  def _CreateReason(self, reason, result):
    self.assertEqual(self.approval_obj.CreateReasonHTML(reason), result)

  def testCreateReasonHTML(self):
    self._CreateReason("Nothing happens if no regex set i/1234",
                       "Nothing happens if no regex set i/1234")

    # %{} is used here to tell the config system this is a literal that
    # shouldn't be expanded/filtered.
    with test_lib.ConfigOverrider({
        "Email.link_regex_list": [r"%{(?P<link>(incident|ir|jira)\/\d+)}"]
    }):
      test_pairs = [
          ("Investigating jira/1234 (incident/1234)...incident/bug",
           "Investigating <a href=\"jira/1234\">jira/1234</a> "
           "(<a href=\"incident/1234\">incident/1234</a>)...incident/bug"),
          ("\"jira/1234\" == (incident/1234)",
           "\"<a href=\"jira/1234\">jira/1234</a>\" == "
           "(<a href=\"incident/1234\">incident/1234</a>)"),
          ("Checking /var/lib/i/123/blah file",
           "Checking /var/lib/i/123/blah file")
      ]

      for reason, result in test_pairs:
        self._CreateReason(reason, result)


class ClientApprovalTest(test_lib.GRRBaseTest):
  """Test for client approvals."""

  def testCreatingApprovalCreatesSymlink(self):
    client_id = self.SetupClients(1)[0]

    flow.GRRFlow.StartFlow(client_id=client_id,
                           flow_name="RequestClientApprovalFlow",
                           reason=self.token.reason,
                           subject_urn=client_id,
                           approver="approver",
                           token=self.token)

    fd = aff4.FACTORY.Open(
        "aff4:/users/test/approvals/client/C.1000000000000000/"
        "UnVubmluZyB0ZXN0cw==",
        follow_symlinks=False,
        mode="r",
        token=self.token)
    self.assertEqual(fd.Get(fd.Schema.TYPE), "AFF4Symlink")
    self.assertEqual(
        fd.Get(fd.Schema.SYMLINK_TARGET),
        "aff4:/ACL/C.1000000000000000/test/UnVubmluZyB0ZXN0cw==")


class HuntApprovalTest(test_lib.GRRBaseTest):
  """Test for hunt approvals."""

  def testCreatingApprovalCreatesSymlink(self):
    cron_urn = rdfvalue.RDFURN("aff4:/cron/CronJobName")

    flow.GRRFlow.StartFlow(flow_name="RequestCronJobApprovalFlow",
                           reason=self.token.reason,
                           subject_urn=cron_urn,
                           approver="approver",
                           token=self.token)

    fd = aff4.FACTORY.Open(
        "aff4:/users/test/approvals/cron/CronJobName/UnVubmluZyB0ZXN0cw==",
        follow_symlinks=False,
        mode="r",
        token=self.token)
    self.assertEqual(fd.Get(fd.Schema.TYPE), "AFF4Symlink")
    self.assertEqual(
        fd.Get(fd.Schema.SYMLINK_TARGET),
        "aff4:/ACL/cron/CronJobName/test/UnVubmluZyB0ZXN0cw==")


class CronJobAprrovalTest(test_lib.GRRBaseTest):
  """Test for cron job approvals."""

  def testCreatingApprovalCreatesSymlink(self):
    hunt_urn = rdfvalue.RDFURN("aff4:/hunts/H:ABCD1234")

    flow.GRRFlow.StartFlow(flow_name="RequestHuntApprovalFlow",
                           reason=self.token.reason,
                           subject_urn=hunt_urn,
                           approver="approver",
                           token=self.token)

    fd = aff4.FACTORY.Open(
        "aff4:/users/test/approvals/hunt/H:ABCD1234/UnVubmluZyB0ZXN0cw==",
        follow_symlinks=False,
        mode="r",
        token=self.token)
    self.assertEqual(fd.Get(fd.Schema.TYPE), "AFF4Symlink")
    self.assertEqual(
        fd.Get(fd.Schema.SYMLINK_TARGET),
        "aff4:/ACL/hunts/H:ABCD1234/test/UnVubmluZyB0ZXN0cw==")


def main(argv):
  test_lib.main(argv)


if __name__ == "__main__":
  flags.StartMain(main)
