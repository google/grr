#!/usr/bin/env python
"""Tests for API client and approvals-related API calls."""

import threading
import time


from grr.lib import flags
from grr.server.grr_response_server.gui import api_auth_manager
from grr.server.grr_response_server.gui import api_call_router_with_approval_checks
from grr.server.grr_response_server.gui import api_e2e_test_lib
from grr.test_lib import db_test_lib
from grr.test_lib import hunt_test_lib
from grr.test_lib import test_lib


@db_test_lib.DualDBTest
class ApiClientLibApprovalsTest(api_e2e_test_lib.ApiE2ETest,
                                hunt_test_lib.StandardHuntTestMixin):

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
          client_id.Basename(),
          requestor=self.token.username,
          approval_id=approval.approval_id,
          approver="foo")

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
      self.GrantHuntApproval(
          h.urn.Basename(),
          requestor=self.token.username,
          approval_id=approval.approval_id,
          approver="approver")

    ProcessApproval()
    threading.Thread(target=ProcessApproval).start()
    result_approval = approval.WaitUntilValid()
    self.assertTrue(result_approval.data.is_valid)


def main(argv):
  test_lib.main(argv)


if __name__ == "__main__":
  flags.StartMain(main)
