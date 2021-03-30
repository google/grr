#!/usr/bin/env python
"""API E2E tests for an ApiCallRouterWithChecks."""
from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

from absl import app

from grr_api_client import errors as grr_api_errors
from grr_response_core import config
from grr_response_core.lib import rdfvalue
from grr_response_core.lib.util import compatibility
from grr_response_server.gui import api_auth_manager
from grr_response_server.gui import api_call_router_with_approval_checks as api_router
from grr_response_server.gui import api_integration_test_lib
from grr_response_server.gui import gui_test_lib
from grr.test_lib import flow_test_lib
from grr.test_lib import hunt_test_lib
from grr.test_lib import test_lib


class ApiCallRouterWithApprovalChecksE2ETest(
    hunt_test_lib.StandardHuntTestMixin,
    api_integration_test_lib.ApiIntegrationTest):

  def setUp(self):
    super().setUp()

    default_router = api_router.ApiCallRouterWithApprovalChecks
    config_overrider = test_lib.ConfigOverrider(
        {"API.DefaultRouter": compatibility.GetName(default_router)})
    config_overrider.Start()
    self.addCleanup(config_overrider.Stop)

    self.ClearCache()

  def ClearCache(self):
    api_router.ApiCallRouterWithApprovalChecks.ClearCache()
    api_auth_manager.InitializeApiAuthManager()

  def CreateHuntApproval(self, hunt_id, requestor, admin=False):
    approval_id = self.RequestHuntApproval(hunt_id, requestor=requestor)
    self.GrantHuntApproval(
        hunt_id,
        approval_id=approval_id,
        requestor=requestor,
        approver=u"Approver1",
        admin=admin)
    self.GrantHuntApproval(
        hunt_id,
        approval_id=approval_id,
        requestor=requestor,
        approver=u"Approver2",
        admin=False)

  def testSimpleUnauthorizedAccess(self):
    """Tests that simple access requires a token."""
    client_id = self.SetupClient(0)
    gui_test_lib.CreateFileVersion(client_id, "fs/os/foo")

    with self.assertRaises(grr_api_errors.AccessForbiddenError):
      self.api.Client(client_id).File("fs/os/foo").Get()

  def testApprovalExpiry(self):
    """Tests that approvals expire after the correct time."""
    client_id = self.SetupClient(0)
    gui_test_lib.CreateFileVersion(client_id, "fs/os/foo")

    with self.assertRaises(grr_api_errors.AccessForbiddenError):
      self.api.Client(client_id).File("fs/os/foo").Get()

    with test_lib.FakeTime(100.0, increment=1e-3):
      self.RequestAndGrantClientApproval(
          client_id, requestor=self.test_username)

      # This should work now.
      self.api.Client(client_id).File("fs/os/foo").Get()

    token_expiry = config.CONFIG["ACL.token_expiry"]

    # Make sure the caches are reset.
    self.ClearCache()

    # This is close to expiry but should still work.
    with test_lib.FakeTime(100.0 + token_expiry - 100.0):
      self.api.Client(client_id).File("fs/os/foo").Get()

    # Make sure the caches are reset.
    self.ClearCache()

    # Past expiry, should fail.
    with test_lib.FakeTime(100.0 + token_expiry + 100.0):
      with self.assertRaises(grr_api_errors.AccessForbiddenError):
        self.api.Client(client_id).File("fs/os/foo").Get()

  def testClientApproval(self):
    """Tests that we can create an approval object to access clients."""
    client_id = self.SetupClient(0)
    gui_test_lib.CreateFileVersion(client_id, "fs/os/foo")

    with self.assertRaises(grr_api_errors.AccessForbiddenError):
      self.api.Client(client_id).File("fs/os/foo").Get()

    self.RequestAndGrantClientApproval(client_id, requestor=self.test_username)
    self.api.Client(client_id).File("fs/os/foo").Get()

    # Move the clocks forward to make sure the approval expires.
    with test_lib.FakeTime(
        rdfvalue.RDFDatetime.Now() + config.CONFIG["ACL.token_expiry"],
        increment=1e-3):
      with self.assertRaises(grr_api_errors.AccessForbiddenError):
        self.api.Client(client_id).File("fs/os/foo").Get()

  def testHuntApproval(self):
    """Tests that we can create an approval object to run hunts."""
    hunt_id = self.CreateHunt()
    self.assertRaises(grr_api_errors.AccessForbiddenError,
                      self.api.Hunt(hunt_id).Start)

    self.CreateHuntApproval(hunt_id, self.test_username, admin=False)

    self.assertRaisesRegex(grr_api_errors.AccessForbiddenError,
                           "Need at least 1 admin approver for access",
                           self.api.Hunt(hunt_id).Start)

    self.CreateHuntApproval(hunt_id, self.test_username, admin=True)
    self.api.Hunt(hunt_id).Start()

  def testFlowAccess(self):
    """Tests access to flows."""
    client_id = self.SetupClient(0)

    self.assertRaises(
        grr_api_errors.AccessForbiddenError,
        self.api.Client(client_id).CreateFlow,
        name=flow_test_lib.SendingFlow.__name__)

    self.RequestAndGrantClientApproval(client_id, requestor=self.test_username)
    f = self.api.Client(client_id).CreateFlow(
        name=flow_test_lib.SendingFlow.__name__)

    # Move the clocks forward to make sure the approval expires.
    with test_lib.FakeTime(
        rdfvalue.RDFDatetime.Now() + config.CONFIG["ACL.token_expiry"],
        increment=1e-3):
      with self.assertRaises(grr_api_errors.AccessForbiddenError):
        self.api.Client(client_id).Flow(f.flow_id).Get()

      self.RequestAndGrantClientApproval(
          client_id, requestor=self.test_username)
      self.api.Client(client_id).Flow(f.flow_id).Get()

  def testCaches(self):
    """Makes sure that results are cached in the security manager."""
    client_id = self.SetupClient(0)

    with test_lib.ConfigOverrider({"ACL.token_expiry": 30}):
      self.RequestAndGrantClientApproval(
          client_id, requestor=self.test_username)

      f = self.api.Client(client_id).CreateFlow(
          name=flow_test_lib.SendingFlow.__name__)

      # Move the clocks past approval expiry time but before cache expiry time.
      with test_lib.FakeTime(rdfvalue.RDFDatetime.Now() +
                             rdfvalue.DurationSeconds("30s")):
        # If this doesn't raise now, all answers were cached.
        self.api.Client(client_id).Flow(f.flow_id).Get()

      with test_lib.FakeTime(
          rdfvalue.RDFDatetime.Now() + rdfvalue.Duration.From(
              api_router.AccessChecker.APPROVAL_CACHE_TIME, rdfvalue.SECONDS)):
        # This must raise now.
        self.assertRaises(grr_api_errors.AccessForbiddenError,
                          self.api.Client(client_id).Flow(f.flow_id).Get)

  def testClientFlowWithoutCategoryCanNotBeStartedWithClient(self):
    client_id = self.SetupClient(0)
    self.RequestAndGrantClientApproval(client_id, requestor=self.test_username)

    with self.assertRaises(grr_api_errors.AccessForbiddenError):
      self.api.Client(client_id).CreateFlow(
          name=flow_test_lib.ClientFlowWithoutCategory.__name__)

  def testClientFlowWithCategoryCanBeStartedWithClient(self):
    client_id = self.SetupClient(0)
    self.RequestAndGrantClientApproval(client_id, requestor=self.test_username)

    self.api.Client(client_id).CreateFlow(
        name=flow_test_lib.ClientFlowWithCategory.__name__)


def main(argv):
  test_lib.main(argv)


if __name__ == "__main__":
  app.run(main)
