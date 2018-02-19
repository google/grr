#!/usr/bin/env python
"""API E2E tests for an ApiCallRouterWithChecks."""


from grr import config
from grr_api_client import errors as grr_api_errors

from grr.gui import api_auth_manager
from grr.gui import api_call_router_with_approval_checks as api_router
from grr.gui import api_e2e_test_lib

from grr.lib import flags
from grr.lib import utils

from grr.server import aff4
from grr.server.aff4_objects import security
from grr.server.aff4_objects import user_managers_test
from grr.server.hunts import implementation
from grr.server.hunts import standard

from grr.test_lib import flow_test_lib
from grr.test_lib import test_lib


class ApiCallRouterWithApprovalChecksE2ETest(api_e2e_test_lib.ApiE2ETest):

  def setUp(self):
    super(ApiCallRouterWithApprovalChecksE2ETest, self).setUp()

    self.config_overrider = test_lib.ConfigOverrider({
        "API.DefaultRouter": api_router.ApiCallRouterWithApprovalChecks.__name__
    })
    self.config_overrider.Start()

    # Force creation of new APIAuthorizationManager, so that configuration
    # changes are picked up.
    api_auth_manager.APIACLInit.InitApiAuthManager()

  def tearDown(self):
    super(ApiCallRouterWithApprovalChecksE2ETest, self).tearDown()
    self.config_overrider.Stop()

  def ClearCache(self):
    api_router.ApiCallRouterWithApprovalChecks.ClearCache()
    api_auth_manager.APIACLInit.InitApiAuthManager()

  def RevokeClientApproval(self, approval_urn, token, remove_from_cache=True):
    with aff4.FACTORY.Open(
        approval_urn, mode="rw", token=self.token.SetUID()) as approval_request:
      approval_request.DeleteAttribute(approval_request.Schema.APPROVER)

    if remove_from_cache:
      self.ClearCache()

  def CreateHuntApproval(self, hunt_urn, token, admin=False):
    approval_urn = aff4.ROOT_URN.Add("ACL").Add(hunt_urn.Path()).Add(
        token.username).Add(utils.EncodeReasonString(token.reason))

    with aff4.FACTORY.Create(
        approval_urn,
        security.HuntApproval,
        mode="rw",
        token=self.token.SetUID()) as approval_request:
      approval_request.AddAttribute(
          approval_request.Schema.APPROVER("Approver1"))
      approval_request.AddAttribute(
          approval_request.Schema.APPROVER("Approver2"))

    if admin:
      self.CreateAdminUser("Approver1")

  def CreateSampleHunt(self):
    """Creats SampleHunt, writes it to the data store and returns it's id."""

    with implementation.GRRHunt.StartHunt(
        hunt_name=standard.SampleHunt.__name__,
        token=self.token.SetUID()) as hunt:
      return hunt.session_id

  def testSimpleUnauthorizedAccess(self):
    """Tests that simple access requires a token."""
    client_id = "C.%016X" % 0

    self.assertRaises(grr_api_errors.AccessForbiddenError,
                      self.api.Client(client_id).File("fs/os/foo").Get)

  def testApprovalExpiry(self):
    """Tests that approvals expire after the correct time."""

    client_id = "C.%016X" % 0

    self.assertRaises(grr_api_errors.AccessForbiddenError,
                      self.api.Client(client_id).File("fs/os/foo").Get)

    with test_lib.FakeTime(100.0, increment=1e-3):
      self.RequestAndGrantClientApproval(client_id, self.token)

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
      self.assertRaises(grr_api_errors.AccessForbiddenError,
                        self.api.Client(client_id).File("fs/os/foo").Get)

  def testClientApproval(self):
    """Tests that we can create an approval object to access clients."""

    client_id = "C.%016X" % 0

    self.assertRaises(grr_api_errors.AccessForbiddenError,
                      self.api.Client(client_id).File("fs/os/foo").Get)

    approval_urn = self.RequestAndGrantClientApproval(client_id, self.token)
    self.api.Client(client_id).File("fs/os/foo").Get()

    self.RevokeClientApproval(approval_urn, self.token)
    self.assertRaises(grr_api_errors.AccessForbiddenError,
                      self.api.Client(client_id).File("fs/os/foo").Get)

  def testHuntApproval(self):
    """Tests that we can create an approval object to run hunts."""
    hunt_urn = self.CreateSampleHunt()
    self.assertRaises(grr_api_errors.AccessForbiddenError,
                      self.api.Hunt(hunt_urn.Basename()).Start)

    self.CreateHuntApproval(hunt_urn, self.token, admin=False)

    self.assertRaisesRegexp(
        grr_api_errors.AccessForbiddenError,
        "Need at least 1 additional approver with the 'admin' label for access",
        self.api.Hunt(hunt_urn.Basename()).Start)

    self.CreateHuntApproval(hunt_urn, self.token, admin=True)
    self.api.Hunt(hunt_urn.Basename()).Start()

  def testFlowAccess(self):
    """Tests access to flows."""
    client_id = "C." + "a" * 16

    self.assertRaises(
        grr_api_errors.AccessForbiddenError,
        self.api.Client(client_id).CreateFlow,
        name=flow_test_lib.SendingFlow.__name__)

    approval_urn = self.RequestAndGrantClientApproval(client_id, self.token)
    f = self.api.Client(client_id).CreateFlow(
        name=flow_test_lib.SendingFlow.__name__)

    self.RevokeClientApproval(approval_urn, self.token)

    self.assertRaises(grr_api_errors.AccessForbiddenError,
                      self.api.Client(client_id).Flow(f.flow_id).Get)

    self.RequestAndGrantClientApproval(client_id, self.token)
    self.api.Client(client_id).Flow(f.flow_id).Get()

  def testCaches(self):
    """Makes sure that results are cached in the security manager."""

    client_id = "C." + "b" * 16

    approval_urn = self.RequestAndGrantClientApproval(client_id, self.token)

    f = self.api.Client(client_id).CreateFlow(
        name=flow_test_lib.SendingFlow.__name__)

    # Remove the approval from the data store, but it should still exist in the
    # security manager cache.
    self.RevokeClientApproval(approval_urn, self.token, remove_from_cache=False)

    # If this doesn't raise now, all answers were cached.
    self.api.Client(client_id).Flow(f.flow_id).Get()

    self.ClearCache()

    # This must raise now.
    self.assertRaises(grr_api_errors.AccessForbiddenError,
                      self.api.Client(client_id).Flow(f.flow_id).Get)

  def testNonAdminsCanNotStartAdminOnlyFlow(self):
    client_id = self.SetupClient(0).Basename()
    self.RequestAndGrantClientApproval(client_id, token=self.token)

    with self.assertRaises(grr_api_errors.AccessForbiddenError):
      self.api.Client(client_id).CreateFlow(
          name=user_managers_test.AdminOnlyFlow.__name__)

  def testAdminsCanStartAdminOnlyFlow(self):
    client_id = self.SetupClient(0).Basename()
    self.CreateAdminUser(self.token.username)
    self.RequestAndGrantClientApproval(client_id, token=self.token)

    self.api.Client(client_id).CreateFlow(
        name=user_managers_test.AdminOnlyFlow.__name__)

  def testClientFlowWithoutCategoryCanNotBeStartedWithClient(self):
    client_id = self.SetupClient(0).Basename()
    self.RequestAndGrantClientApproval(client_id, token=self.token)

    with self.assertRaises(grr_api_errors.AccessForbiddenError):
      self.api.Client(client_id).CreateFlow(
          name=user_managers_test.ClientFlowWithoutCategory.__name__)

  def testClientFlowWithCategoryCanBeStartedWithClient(self):
    client_id = self.SetupClient(0).Basename()
    self.RequestAndGrantClientApproval(client_id, token=self.token)

    self.api.Client(client_id).CreateFlow(
        name=user_managers_test.ClientFlowWithCategory.__name__)


def main(argv):
  test_lib.main(argv)


if __name__ == "__main__":
  flags.StartMain(main)
