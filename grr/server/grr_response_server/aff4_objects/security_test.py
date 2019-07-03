#!/usr/bin/env python
"""Tests for aff4_objects.security."""
from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals


from absl import app

from grr_response_core.lib import rdfvalue
from grr_response_server import aff4
from grr_response_server.aff4_objects import security
from grr.test_lib import test_lib


class ClientApprovalTest(test_lib.GRRBaseTest):
  """Test for client approvals."""

  def testCreatingApprovalCreatesSymlink(self):
    client_id = self.SetupClient(0)

    security.ClientApprovalRequestor(
        subject_urn=client_id,
        reason=self.token.reason,
        approver="approver",
        token=self.token).Request()

    approval_id = list(
        aff4.FACTORY.ListChildren(
            "aff4:/users/test/approvals/client/C.1000000000000000")
    )[0].Basename()
    self.assertStartsWith(approval_id, "approval:")

    fd = aff4.FACTORY.Open(
        "aff4:/users/test/approvals/client/C.1000000000000000/%s" % approval_id,
        follow_symlinks=False,
        mode="r",
        token=self.token)
    self.assertEqual(fd.Get(fd.Schema.TYPE), "AFF4Symlink")
    self.assertEqual(
        fd.Get(fd.Schema.SYMLINK_TARGET),
        "aff4:/ACL/C.1000000000000000/test/%s" % approval_id)


class CronJobAprrovalTest(test_lib.GRRBaseTest):
  """Test for cron job approvals."""

  def testCreatingApprovalCreatesSymlink(self):
    cron_urn = rdfvalue.RDFURN("aff4:/cron/CronJobName")

    security.CronJobApprovalRequestor(
        reason=self.token.reason,
        subject_urn=cron_urn,
        approver="approver",
        token=self.token).Request()

    approval_id = list(
        aff4.FACTORY.ListChildren(
            "aff4:/users/test/approvals/cron/CronJobName"))[0].Basename()
    self.assertStartsWith(approval_id, "approval:")

    fd = aff4.FACTORY.Open(
        "aff4:/users/test/approvals/cron/CronJobName/%s" % approval_id,
        follow_symlinks=False,
        mode="r",
        token=self.token)
    self.assertEqual(fd.Get(fd.Schema.TYPE), "AFF4Symlink")
    self.assertEqual(
        fd.Get(fd.Schema.SYMLINK_TARGET),
        "aff4:/ACL/cron/CronJobName/test/%s" % approval_id)


class HuntApprovalTest(test_lib.GRRBaseTest):
  """Test for hunt approvals."""

  def testCreatingApprovalCreatesSymlink(self):
    hunt_urn = rdfvalue.RDFURN("aff4:/hunts/H:ABCD1234")

    security.HuntApprovalRequestor(
        reason=self.token.reason,
        subject_urn=hunt_urn,
        approver="approver",
        token=self.token).Request()

    approval_id = list(
        aff4.FACTORY.ListChildren(
            "aff4:/users/test/approvals/hunt/H:ABCD1234"))[0].Basename()
    self.assertStartsWith(approval_id, "approval:")

    fd = aff4.FACTORY.Open(
        "aff4:/users/test/approvals/hunt/H:ABCD1234/%s" % approval_id,
        follow_symlinks=False,
        mode="r",
        token=self.token)
    self.assertEqual(fd.Get(fd.Schema.TYPE), "AFF4Symlink")
    self.assertEqual(
        fd.Get(fd.Schema.SYMLINK_TARGET),
        "aff4:/ACL/hunts/H:ABCD1234/test/%s" % approval_id)


def main(argv):
  test_lib.main(argv)


if __name__ == "__main__":
  app.run(main)
