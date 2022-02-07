#!/usr/bin/env python
"""API E2E tests for an ApiCallRouterWithChecks."""

import os

from absl import app

from grr_api_client import errors as grr_api_errors
from grr_response_core import config
from grr_response_core.lib import rdfvalue
from grr_response_server.authorization import groups
from grr_response_server.flows.general import administrative
from grr_response_server.gui import api_auth_manager
from grr_response_server.gui import api_call_router_with_approval_checks as api_router
from grr_response_server.gui import api_integration_test_lib
from grr_response_server.gui import gui_test_lib
from grr.test_lib import flow_test_lib
from grr.test_lib import hunt_test_lib
from grr.test_lib import test_lib


class TestGroupManager(groups.GroupAccessManager):
  """Test group manager with predefined behavior.

  This group manager assumes that a group 'somegroup' has a single
  user 'api_test_robot_user'.
  """

  def __init__(self):
    super()
    self._authorized_groups = {}

  def AuthorizeGroup(self, group, subject):
    self._authorized_groups.setdefault(subject, []).append(group)

  def MemberOfAuthorizedGroup(self, username, subject):
    if (username == "api_test_robot_user" and
        "somegroup" in self._authorized_groups.get(subject, [])):
      return True


class ApiCallRouterWithApprovalChecksE2ETest(
    hunt_test_lib.StandardHuntTestMixin,
    api_integration_test_lib.ApiIntegrationTest):

  def InitRouterConfig(self, router_config):
    router_config_file = os.path.join(self.temp_dir, "api_acls.yaml")
    with open(router_config_file, mode="w", encoding="utf-8") as fd:
      fd.write(router_config)

    config_overrider = test_lib.ConfigOverrider(
        {"API.RouterACLConfigFile": router_config_file})
    config_overrider.Start()
    self.addCleanup(config_overrider.Stop)

    self.ClearCache()

  def InitDefaultRouter(self):
    config_overrider = test_lib.ConfigOverrider({
        "API.DefaultRouter": api_router.ApiCallRouterWithApprovalChecks.__name__
    })
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

  def testUnauthorizedAccessToFileOnClientIsForbidden(self):
    """Tests that simple access requires a token."""
    self.InitDefaultRouter()

    client_id = self.SetupClient(0)
    gui_test_lib.CreateFileVersion(client_id, "fs/os/foo")

    with self.assertRaises(grr_api_errors.AccessForbiddenError):
      self.api.Client(client_id).File("fs/os/foo").Get()

  def testExpiredClientApprovalIsNoLongerValid(self):
    """Tests that approvals expire after the correct time."""
    self.InitDefaultRouter()

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

  def testValidClientApprovalAllowsAccessToEverythingInsideClient(self):
    """Tests that we can create an approval object to access clients."""
    self.InitDefaultRouter()

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

  def testValidHuntApprovalAllowsStartingHunt(self):
    """Tests that we can create an approval object to run hunts."""
    self.InitDefaultRouter()

    hunt_id = self.CreateHunt()
    self.assertRaises(grr_api_errors.AccessForbiddenError,
                      self.api.Hunt(hunt_id).Start)

    self.CreateHuntApproval(hunt_id, self.test_username, admin=False)

    self.assertRaisesRegex(grr_api_errors.AccessForbiddenError,
                           "Need at least 1 admin approver for access",
                           self.api.Hunt(hunt_id).Start)

    self.CreateHuntApproval(hunt_id, self.test_username, admin=True)
    self.api.Hunt(hunt_id).Start()

  def testValidClientApprovalRequiredToStartFlowsOnClient(self):
    """Tests access to flows."""
    self.InitDefaultRouter()

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

  def testApprovalsAreCachedForLimitedTime(self):
    """Makes sure that results are cached in the security manager."""
    self.InitDefaultRouter()

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
    self.InitDefaultRouter()

    client_id = self.SetupClient(0)
    self.RequestAndGrantClientApproval(client_id, requestor=self.test_username)

    with self.assertRaises(grr_api_errors.AccessForbiddenError):
      self.api.Client(client_id).CreateFlow(
          name=flow_test_lib.ClientFlowWithoutCategory.__name__)

  def testClientFlowWithCategoryCanBeStartedWithClient(self):
    self.InitDefaultRouter()

    client_id = self.SetupClient(0)
    self.RequestAndGrantClientApproval(client_id, requestor=self.test_username)

    self.api.Client(client_id).CreateFlow(
        name=flow_test_lib.ClientFlowWithCategory.__name__)

  def testRestrictedFlowCanBeStartedByAdminsWithDefaultConfig(self):
    self.InitDefaultRouter()

    client_id = self.SetupClient(0)
    self.CreateAdminUser(self.test_username)
    self.RequestAndGrantClientApproval(client_id, requestor=self.test_username)

    for flow_name in [
        administrative.LaunchBinary.__name__,
        administrative.ExecutePythonHack.__name__
    ]:
      with self.subTest(flow_name=flow_name):
        self.api.Client(client_id).CreateFlow(name=flow_name)

  def testRestrictedFlowCanNotBeStartedByNonAdminsWithDefaultConfig(self):
    self.InitDefaultRouter()

    client_id = self.SetupClient(0)
    self.RequestAndGrantClientApproval(client_id, requestor=self.test_username)

    for flow_name in [
        administrative.LaunchBinary.__name__,
        administrative.ExecutePythonHack.__name__
    ]:
      with self.subTest(flow_name=flow_name):
        with self.assertRaisesRegex(grr_api_errors.AccessForbiddenError,
                                    "restricted flow"):
          self.api.Client(client_id).CreateFlow(name=flow_name)

  def testAdminAttributeIsIrrelevantOnFlowStartIfConfigOptionToIgnoreItIsSet(
      self):
    self.InitRouterConfig(f"""
router: {api_router.ApiCallRouterWithApprovalChecks.__name__}
router_params:
  ignore_admin_user_attribute: True
users:
  - {self.test_username}
""")

    client_id = self.SetupClient(0)
    self.CreateAdminUser(self.test_username)
    self.RequestAndGrantClientApproval(client_id, requestor=self.test_username)

    for flow_name in [
        administrative.LaunchBinary.__name__,
        administrative.ExecutePythonHack.__name__
    ]:
      with self.subTest(flow_name=flow_name):
        with self.assertRaisesRegex(grr_api_errors.AccessForbiddenError,
                                    "restricted flow"):
          self.api.Client(client_id).CreateFlow(name=flow_name)

  def testUserAllowlistIsCheckedOnFlowStartIfConfigOptionToIgnoreAdminsIsNotSet(
      self):
    self.InitRouterConfig(f"""
router: {api_router.ApiCallRouterWithApprovalChecks.__name__}
router_params:
  restricted_flow_users:
    - {self.test_username}
users:
  - {self.test_username}
""")

    client_id = self.SetupClient(0)
    self.RequestAndGrantClientApproval(client_id, requestor=self.test_username)

    self.api.Client(client_id).CreateFlow(
        name=administrative.LaunchBinary.__name__)

    # Check the negative case.
    self.InitRouterConfig(f"""
router: {api_router.ApiCallRouterWithApprovalChecks.__name__}
router_params:
  restricted_flow_users:
    - someotheruser
users:
  - {self.test_username}
""")

    client_id = self.SetupClient(0)
    self.RequestAndGrantClientApproval(client_id, requestor=self.test_username)

    with self.assertRaisesRegex(grr_api_errors.AccessForbiddenError,
                                "restricted flow"):
      self.api.Client(client_id).CreateFlow(
          name=administrative.LaunchBinary.__name__)

  def testUserAllowlistIsCheckedOnFlowStartIfConfigOptionToIgnoreAdminsIsSet(
      self):
    self.InitRouterConfig(f"""
router: {api_router.ApiCallRouterWithApprovalChecks.__name__}
router_params:
  ignore_admin_user_attribute: True
  restricted_flow_users:
    - {self.test_username}
users:
  - {self.test_username}
""")

    client_id = self.SetupClient(0)
    self.RequestAndGrantClientApproval(client_id, requestor=self.test_username)

    self.api.Client(client_id).CreateFlow(
        name=administrative.LaunchBinary.__name__)

    # Check the negative case.
    self.InitRouterConfig(f"""
router: {api_router.ApiCallRouterWithApprovalChecks.__name__}
router_params:
  ignore_admin_user_attribute: True
  restricted_flow_users:
    - someotheruser
users:
  - {self.test_username}
""")

    client_id = self.SetupClient(0)
    self.RequestAndGrantClientApproval(client_id, requestor=self.test_username)

    with self.assertRaisesRegex(grr_api_errors.AccessForbiddenError,
                                "restricted flow"):
      self.api.Client(client_id).CreateFlow(
          name=administrative.LaunchBinary.__name__)

  def testGroupAllowlistIsCheckedOnFlowStartIfConfigOptionToIgnoreAdminsIsSet(
      self):
    with test_lib.ConfigOverrider(
        {"ACL.group_access_manager_class": TestGroupManager.__name__}):
      self.InitRouterConfig(f"""
  router: {api_router.ApiCallRouterWithApprovalChecks.__name__}
  router_params:
    ignore_admin_user_attribute: True
    restricted_flow_groups:
      - somegroup
  users:
    - {self.test_username}
  """)

      client_id = self.SetupClient(0)
      self.RequestAndGrantClientApproval(
          client_id, requestor=self.test_username)

      self.api.Client(client_id).CreateFlow(
          name=administrative.LaunchBinary.__name__)

      # Check the negative case.
      self.InitRouterConfig(f"""
  router: {api_router.ApiCallRouterWithApprovalChecks.__name__}
  router_params:
    ignore_admin_user_attribute: True
    restricted_flow_users:
      - anothergroup
  users:
    - {self.test_username}
  """)

      client_id = self.SetupClient(0)
      self.RequestAndGrantClientApproval(
          client_id, requestor=self.test_username)

      with self.assertRaisesRegex(grr_api_errors.AccessForbiddenError,
                                  "restricted flow"):
        self.api.Client(client_id).CreateFlow(
            name=administrative.LaunchBinary.__name__)

  def testRestrictedHuntCanBeStartedByAdminsWithDefaultConfig(self):
    self.InitDefaultRouter()

    self.CreateAdminUser(self.test_username)

    for flow_name in [
        administrative.LaunchBinary.__name__,
        administrative.ExecutePythonHack.__name__
    ]:
      with self.subTest(flow_name=flow_name):
        self.api.CreateHunt(flow_name)

  def testRestrictedHuntCanNotBeStartedByNonAdminsWithDefaultConfig(self):
    self.InitDefaultRouter()

    for flow_name in [
        administrative.LaunchBinary.__name__,
        administrative.ExecutePythonHack.__name__
    ]:
      with self.subTest(flow_name=flow_name):
        with self.assertRaisesRegex(grr_api_errors.AccessForbiddenError,
                                    "restricted flow"):
          self.api.CreateHunt(flow_name)

  def testAdminAttributeIsIrrelevantOnHuntCreateIfConfigOptionToIgnoreItIsSet(
      self):
    self.InitRouterConfig(f"""
router: {api_router.ApiCallRouterWithApprovalChecks.__name__}
router_params:
  ignore_admin_user_attribute: True
users:
  - {self.test_username}
""")

    self.CreateAdminUser(self.test_username)

    for flow_name in [
        administrative.LaunchBinary.__name__,
        administrative.ExecutePythonHack.__name__
    ]:
      with self.subTest(flow_name=flow_name):
        with self.assertRaisesRegex(grr_api_errors.AccessForbiddenError,
                                    "restricted flow"):
          self.api.CreateHunt(flow_name)

  def testUserAllowlistIsCheckedOnHuntCreateIfConfigOptionToIgnoreAdminsIsNotSet(
      self):
    self.InitRouterConfig(f"""
router: {api_router.ApiCallRouterWithApprovalChecks.__name__}
router_params:
  restricted_flow_users:
    - {self.test_username}
users:
  - {self.test_username}
""")

    self.api.CreateHunt(administrative.LaunchBinary.__name__)

    # Check the negative case.
    self.InitRouterConfig(f"""
router: {api_router.ApiCallRouterWithApprovalChecks.__name__}
router_params:
  restricted_flow_users:
    - someotheruser
users:
  - {self.test_username}
""")

    with self.assertRaisesRegex(grr_api_errors.AccessForbiddenError,
                                "restricted flow"):
      self.api.CreateHunt(administrative.LaunchBinary.__name__)

  def testUserAllowlistIsCheckedOnHuntCreateIfConfigOptionToIgnoreAdminsIsSet(
      self):
    self.InitRouterConfig(f"""
router: {api_router.ApiCallRouterWithApprovalChecks.__name__}
router_params:
  ignore_admin_user_attribute: True
  restricted_flow_users:
    - {self.test_username}
users:
  - {self.test_username}
""")

    self.api.CreateHunt(administrative.LaunchBinary.__name__)

    # Check the negative case.
    self.InitRouterConfig(f"""
router: {api_router.ApiCallRouterWithApprovalChecks.__name__}
router_params:
  ignore_admin_user_attribute: True
  restricted_flow_users:
    - someotheruser
users:
  - {self.test_username}
""")

    with self.assertRaisesRegex(grr_api_errors.AccessForbiddenError,
                                "restricted flow"):
      self.api.CreateHunt(administrative.LaunchBinary.__name__)

  def testGroupAllowlistIsCheckedOnHuntCreateIfConfigOptionToIgnoreAdminsIsSet(
      self):
    with test_lib.ConfigOverrider(
        {"ACL.group_access_manager_class": TestGroupManager.__name__}):
      self.InitRouterConfig(f"""
  router: {api_router.ApiCallRouterWithApprovalChecks.__name__}
  router_params:
    ignore_admin_user_attribute: True
    restricted_flow_groups:
      - somegroup
  users:
    - {self.test_username}
  """)

      self.api.CreateHunt(administrative.LaunchBinary.__name__)

      # Check the negative case.
      self.InitRouterConfig(f"""
  router: {api_router.ApiCallRouterWithApprovalChecks.__name__}
  router_params:
    ignore_admin_user_attribute: True
    restricted_flow_users:
      - anothergroup
  users:
    - {self.test_username}
  """)

      with self.assertRaisesRegex(grr_api_errors.AccessForbiddenError,
                                  "restricted flow"):
        self.api.CreateHunt(administrative.LaunchBinary.__name__)


def main(argv):
  test_lib.main(argv)


if __name__ == "__main__":
  app.run(main)
