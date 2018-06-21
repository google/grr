#!/usr/bin/env python
"""API E2E tests for an ApiCallRouterWithChecks."""


from grr import config
from grr_api_client import errors as grr_api_errors

from grr.lib import flags
from grr.lib import rdfvalue
from grr.server.grr_response_server.aff4_objects import user_managers

from grr.server.grr_response_server.gui import api_auth_manager
from grr.server.grr_response_server.gui import api_call_router_with_approval_checks as api_router
from grr.server.grr_response_server.gui import api_e2e_test_lib
from grr.server.grr_response_server.gui import gui_test_lib
from grr.server.grr_response_server.hunts import implementation
from grr.server.grr_response_server.hunts import standard

from grr.test_lib import db_test_lib
from grr.test_lib import flow_test_lib
from grr.test_lib import test_lib


@db_test_lib.DualDBTest
class ApiCallRouterWithApprovalChecksE2ETest(api_e2e_test_lib.ApiE2ETest):

  def setUp(self):
    super(ApiCallRouterWithApprovalChecksE2ETest, self).setUp()

    self.config_overrider = test_lib.ConfigOverrider({
        "API.DefaultRouter": api_router.ApiCallRouterWithApprovalChecks.__name__
    })
    self.config_overrider.Start()

    self.ClearCache()

  def tearDown(self):
    super(ApiCallRouterWithApprovalChecksE2ETest, self).tearDown()
    self.config_overrider.Stop()

  def ClearCache(self):
    api_router.ApiCallRouterWithApprovalChecks.ClearCache()
    api_auth_manager.APIACLInit.InitApiAuthManager()

  def CreateHuntApproval(self, hunt_urn, token, admin=False):
    approval_id = self.RequestHuntApproval(
        hunt_urn.Basename(), requestor=token.username)
    self.GrantHuntApproval(
        hunt_urn.Basename(),
        approval_id=approval_id,
        requestor=token.username,
        approver="Approver1",
        admin=admin)
    self.GrantHuntApproval(
        hunt_urn.Basename(),
        approval_id=approval_id,
        requestor=token.username,
        approver="Approver2",
        admin=False)

  def CreateSampleHunt(self):
    """Creats SampleHunt, writes it to the data store and returns it's id."""

    with implementation.GRRHunt.StartHunt(
        hunt_name=standard.SampleHunt.__name__,
        token=self.token.SetUID()) as hunt:
      return hunt.session_id

  def testSimpleUnauthorizedAccess(self):
    """Tests that simple access requires a token."""
    client_id = self.SetupClient(0)
    gui_test_lib.CreateFileVersion(client_id, "fs/os/foo", token=self.token)

    with self.assertRaises(grr_api_errors.AccessForbiddenError):
      self.api.Client(client_id.Basename()).File("fs/os/foo").Get()

  def testApprovalExpiry(self):
    """Tests that approvals expire after the correct time."""
    client_id = self.SetupClient(0)
    gui_test_lib.CreateFileVersion(client_id, "fs/os/foo", token=self.token)

    with self.assertRaises(grr_api_errors.AccessForbiddenError):
      self.api.Client(client_id.Basename()).File("fs/os/foo").Get()

    with test_lib.FakeTime(100.0, increment=1e-3):
      self.RequestAndGrantClientApproval(
          client_id, requestor=self.token.username)

      # This should work now.
      self.api.Client(client_id.Basename()).File("fs/os/foo").Get()

    token_expiry = config.CONFIG["ACL.token_expiry"]

    # Make sure the caches are reset.
    self.ClearCache()

    # This is close to expiry but should still work.
    with test_lib.FakeTime(100.0 + token_expiry - 100.0):
      self.api.Client(client_id.Basename()).File("fs/os/foo").Get()

    # Make sure the caches are reset.
    self.ClearCache()

    # Past expiry, should fail.
    with test_lib.FakeTime(100.0 + token_expiry + 100.0):
      with self.assertRaises(grr_api_errors.AccessForbiddenError):
        self.api.Client(client_id.Basename()).File("fs/os/foo").Get()

  def testClientApproval(self):
    """Tests that we can create an approval object to access clients."""
    client_id = self.SetupClient(0)
    gui_test_lib.CreateFileVersion(client_id, "fs/os/foo", token=self.token)

    with self.assertRaises(grr_api_errors.AccessForbiddenError):
      self.api.Client(client_id.Basename()).File("fs/os/foo").Get()

    self.RequestAndGrantClientApproval(client_id, requestor=self.token.username)
    self.api.Client(client_id.Basename()).File("fs/os/foo").Get()

    # Move the clocks forward to make sure the approval expires.
    with test_lib.FakeTime(
        rdfvalue.RDFDatetime.Now() + config.CONFIG["ACL.token_expiry"],
        increment=1e-3):
      with self.assertRaises(grr_api_errors.AccessForbiddenError):
        self.api.Client(client_id.Basename()).File("fs/os/foo").Get()

  def testHuntApproval(self):
    """Tests that we can create an approval object to run hunts."""
    hunt_urn = self.CreateSampleHunt()
    self.assertRaises(grr_api_errors.AccessForbiddenError,
                      self.api.Hunt(hunt_urn.Basename()).Start)

    self.CreateHuntApproval(hunt_urn, self.token, admin=False)

    self.assertRaisesRegexp(grr_api_errors.AccessForbiddenError,
                            "Need at least 1 admin approver for access",
                            self.api.Hunt(hunt_urn.Basename()).Start)

    self.CreateHuntApproval(hunt_urn, self.token, admin=True)
    self.api.Hunt(hunt_urn.Basename()).Start()

  def testFlowAccess(self):
    """Tests access to flows."""
    client_id = self.SetupClient(0).Basename()

    self.assertRaises(
        grr_api_errors.AccessForbiddenError,
        self.api.Client(client_id).CreateFlow,
        name=flow_test_lib.SendingFlow.__name__)

    self.RequestAndGrantClientApproval(client_id, requestor=self.token.username)
    f = self.api.Client(client_id).CreateFlow(
        name=flow_test_lib.SendingFlow.__name__)

    # Move the clocks forward to make sure the approval expires.
    with test_lib.FakeTime(
        rdfvalue.RDFDatetime.Now() + config.CONFIG["ACL.token_expiry"],
        increment=1e-3):
      with self.assertRaises(grr_api_errors.AccessForbiddenError):
        self.api.Client(client_id).Flow(f.flow_id).Get()

      self.RequestAndGrantClientApproval(
          client_id, requestor=self.token.username)
      self.api.Client(client_id).Flow(f.flow_id).Get()

  def testCaches(self):
    """Makes sure that results are cached in the security manager."""
    client_id = self.SetupClient(0).Basename()

    with test_lib.ConfigOverrider({"ACL.token_expiry": "10"}):
      self.RequestAndGrantClientApproval(
          client_id, requestor=self.token.username)

      f = self.api.Client(client_id).CreateFlow(
          name=flow_test_lib.SendingFlow.__name__)

      # Move the clocks past approval expiry time but before cache expiry time.
      with test_lib.FakeTime(rdfvalue.RDFDatetime.Now() +
                             rdfvalue.Duration("10s")):
        # If this doesn't raise now, all answers were cached.
        self.api.Client(client_id).Flow(f.flow_id).Get()

      with test_lib.FakeTime(
          rdfvalue.RDFDatetime.Now() + rdfvalue.Duration.FromSeconds(
              user_managers.FullAccessControlManager.approval_cache_time)):
        # This must raise now.
        self.assertRaises(grr_api_errors.AccessForbiddenError,
                          self.api.Client(client_id).Flow(f.flow_id).Get)

  def testNonAdminsCanNotStartAdminOnlyFlow(self):
    client_id = self.SetupClient(0).Basename()
    self.RequestAndGrantClientApproval(client_id, requestor=self.token.username)

    with self.assertRaises(grr_api_errors.AccessForbiddenError):
      self.api.Client(client_id).CreateFlow(
          name=flow_test_lib.AdminOnlyFlow.__name__)

  def testAdminsCanStartAdminOnlyFlow(self):
    client_id = self.SetupClient(0).Basename()
    self.CreateAdminUser(self.token.username)
    self.RequestAndGrantClientApproval(client_id, requestor=self.token.username)

    self.api.Client(client_id).CreateFlow(
        name=flow_test_lib.AdminOnlyFlow.__name__)

  def testClientFlowWithoutCategoryCanNotBeStartedWithClient(self):
    client_id = self.SetupClient(0).Basename()
    self.RequestAndGrantClientApproval(client_id, requestor=self.token.username)

    with self.assertRaises(grr_api_errors.AccessForbiddenError):
      self.api.Client(client_id).CreateFlow(
          name=flow_test_lib.ClientFlowWithoutCategory.__name__)

  def testClientFlowWithCategoryCanBeStartedWithClient(self):
    client_id = self.SetupClient(0).Basename()
    self.RequestAndGrantClientApproval(client_id, requestor=self.token.username)

    self.api.Client(client_id).CreateFlow(
        name=flow_test_lib.ClientFlowWithCategory.__name__)


def main(argv):
  test_lib.main(argv)


if __name__ == "__main__":
  flags.StartMain(main)
