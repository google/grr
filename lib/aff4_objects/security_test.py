#!/usr/bin/env python
"""Tests for grr.lib.aff4_objects.security."""

from grr.lib import aff4
from grr.lib import flags
from grr.lib import flow
from grr.lib import rdfvalue
from grr.lib import test_lib
from grr.lib.aff4_objects import security


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
        "Email.link_regex_list":
        [r"%{(?P<link>(incident|ir|jira)\/\d+)}"]}):
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
        "UnVubmluZyB0ZXN0cw==", follow_symlinks=False, mode="r",
        token=self.token)
    self.assertEqual(fd.Get(fd.Schema.TYPE), "AFF4Symlink")
    self.assertEqual(fd.Get(fd.Schema.SYMLINK_TARGET),
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
        follow_symlinks=False, mode="r", token=self.token)
    self.assertEqual(fd.Get(fd.Schema.TYPE), "AFF4Symlink")
    self.assertEqual(fd.Get(fd.Schema.SYMLINK_TARGET),
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
        follow_symlinks=False, mode="r", token=self.token)
    self.assertEqual(fd.Get(fd.Schema.TYPE), "AFF4Symlink")
    self.assertEqual(fd.Get(fd.Schema.SYMLINK_TARGET),
                     "aff4:/ACL/hunts/H:ABCD1234/test/UnVubmluZyB0ZXN0cw==")


def main(argv):
  test_lib.main(argv)

if __name__ == "__main__":
  flags.StartMain(main)
