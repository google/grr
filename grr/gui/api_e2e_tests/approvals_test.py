#!/usr/bin/env python
"""Tests for API client and approvals-related API calls."""

import threading
import time


from grr.gui import api_auth_manager
from grr.gui import api_call_router_with_approval_checks
from grr.gui import api_e2e_test_lib
from grr.lib import flags
from grr.server import access_control
from grr.server.aff4_objects import security
from grr.server.hunts import standard_test
from grr.test_lib import test_lib


class ApiClientLibApprovalsTest(api_e2e_test_lib.ApiE2ETest,
                                standard_test.StandardHuntTestMixin):

  def setUp(self):
    super(ApiClientLibApprovalsTest, self).setUp()

    cls = (api_call_router_with_approval_checks.ApiCallRouterWithApprovalChecks)
    cls.ClearCache()

    self.config_overrider = test_lib.ConfigOverrider({
        "API.DefaultRouter": cls.__name__
    })
    self.config_overrider.Start()

    # Force creation of new APIAuthorizationManager, so that configuration
    # changes are picked up.
    api_auth_manager.APIACLInit.InitApiAuthManager()

  def tearDown(self):
    super(ApiClientLibApprovalsTest, self).tearDown()
    self.config_overrider.Stop()

  def testCreateClientApproval(self):
    client_id = self.SetupClient(0)

    approval = self.api.Client(client_id.Basename()).CreateApproval(
        reason="blah", notified_users=["foo"])
    self.assertEqual(approval.client_id, client_id.Basename())
    self.assertEqual(approval.data.subject.client_id, client_id.Basename())
    self.assertEqual(approval.data.reason, "blah")
    self.assertFalse(approval.data.is_valid)

  def testWaitUntilClientApprovalValid(self):
    client_id = self.SetupClient(0)

    approval = self.api.Client(client_id.Basename()).CreateApproval(
        reason="blah", notified_users=["foo"])
    self.assertFalse(approval.data.is_valid)

    def ProcessApproval():
      time.sleep(1)
      self.GrantClientApproval(
          client_id, self.token.username, reason="blah", approver="foo")

    threading.Thread(target=ProcessApproval).start()

    result_approval = approval.WaitUntilValid()
    self.assertTrue(result_approval.data.is_valid)

  def testCreateHuntApproval(self):
    h = self.CreateHunt()

    approval = self.api.Hunt(h.urn.Basename()).CreateApproval(
        reason="blah", notified_users=["foo"])
    self.assertEqual(approval.hunt_id, h.urn.Basename())
    self.assertEqual(approval.data.subject.hunt_id, h.urn.Basename())
    self.assertEqual(approval.data.reason, "blah")
    self.assertFalse(approval.data.is_valid)

  def testWaitUntilHuntApprovalValid(self):
    h = self.CreateHunt()

    approval = self.api.Hunt(h.urn.Basename()).CreateApproval(
        reason="blah", notified_users=["approver"])
    self.assertFalse(approval.data.is_valid)

    def ProcessApproval():
      time.sleep(1)
      self.CreateAdminUser("approver")
      approver_token = access_control.ACLToken(username="approver")
      security.HuntApprovalGrantor(
          subject_urn=h.urn,
          reason="blah",
          delegate=self.token.username,
          token=approver_token).Grant()

    ProcessApproval()
    threading.Thread(target=ProcessApproval).start()
    result_approval = approval.WaitUntilValid()
    self.assertTrue(result_approval.data.is_valid)


def main(argv):
  test_lib.main(argv)


if __name__ == "__main__":
  flags.StartMain(main)
