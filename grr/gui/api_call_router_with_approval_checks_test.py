#!/usr/bin/env python
"""Tests for an ApiCallRouterWithChecks."""


import mock

from grr import config
from grr_api_client import errors as grr_api_errors

from grr.gui import api_auth_manager
from grr.gui import api_call_handler_base
from grr.gui import api_call_router_with_approval_checks as api_router
from grr.gui import http_api_e2e_test

from grr.gui.api_plugins import client as api_client
from grr.gui.api_plugins import cron as api_cron
from grr.gui.api_plugins import flow as api_flow
from grr.gui.api_plugins import hunt as api_hunt
from grr.gui.api_plugins import user as api_user
from grr.gui.api_plugins import vfs as api_vfs

from grr.lib import flags
from grr.lib import utils

from grr.server import access_control
from grr.server import aff4
from grr.server.aff4_objects import security
from grr.server.aff4_objects import user_managers_test
from grr.server.hunts import implementation
from grr.server.hunts import standard
from grr.server.hunts import standard_test

from grr.test_lib import flow_test_lib
from grr.test_lib import test_lib


class ApiCallRouterWithApprovalChecksTest(test_lib.GRRBaseTest,
                                          standard_test.StandardHuntTestMixin):
  """Tests for an ApiCallRouterWithApprovalChecks."""

  # ACCESS_CHECKED_METHODS is used to identify the methods that are tested
  # for being checked for necessary access rights. This list is used
  # in testAllOtherMethodsAreNotAccessChecked.
  ACCESS_CHECKED_METHODS = []

  def setUp(self):
    super(ApiCallRouterWithApprovalChecksTest, self).setUp()

    self.client_id = test_lib.TEST_CLIENT_ID

    self.delegate_mock = mock.MagicMock()
    self.legacy_manager_mock = mock.MagicMock()

    self.router = api_router.ApiCallRouterWithApprovalChecks(
        delegate=self.delegate_mock, legacy_manager=self.legacy_manager_mock)

  def CheckMethodIsAccessChecked(self,
                                 method,
                                 access_type,
                                 args=None,
                                 token=None):
    token = token or self.token

    # Check that legacy access control manager is called and that the method
    # is then delegated.
    method(args, token=token)
    self.assertTrue(getattr(self.legacy_manager_mock, access_type).called)
    getattr(self.delegate_mock, method.__name__).assert_called_with(
        args, token=token)

    self.delegate_mock.reset_mock()
    self.legacy_manager_mock.reset_mock()

    try:
      # Check that when exception is raised by legacy manager, the delegate
      # method is not called.
      getattr(self.legacy_manager_mock,
              access_type).side_effect = access_control.UnauthorizedAccess("")

      with self.assertRaises(access_control.UnauthorizedAccess):
        method(args, token=token)

      self.assertTrue(getattr(self.legacy_manager_mock, access_type).called)
      self.assertFalse(getattr(self.delegate_mock, method.__name__).called)

    finally:
      getattr(self.legacy_manager_mock, access_type).side_effect = None
      self.delegate_mock.reset_mock()
      self.legacy_manager_mock.reset_mock()

  def CheckMethodIsNotAccessChecked(self, method, args=None, token=None):
    token = token or self.token

    method(args, token=token)

    self.assertFalse(self.legacy_manager_mock.CheckClientAccess.called)
    self.assertFalse(self.legacy_manager_mock.CheckHuntAccess.called)
    self.assertFalse(self.legacy_manager_mock.CheckCronJob.called)
    self.assertFalse(self.legacy_manager_mock.CheckIfCanStartFlow.called)
    self.assertFalse(self.legacy_manager_mock.CheckDataStoreAccess.called)

    getattr(self.delegate_mock, method.__name__).assert_called_with(
        args, token=token)

    self.delegate_mock.reset_mock()
    self.legacy_manager_mock.reset_mock()

  ACCESS_CHECKED_METHODS.extend([
      "InterrogateClient",
      "ListClientCrashes",
      "ListClientActionRequests",
      "GetClientLoadStats"])  # pyformat: disable

  def testClientMethodsAreAccessChecked(self):
    args = api_client.ApiInterrogateClientArgs(client_id=self.client_id)
    self.CheckMethodIsAccessChecked(
        self.router.InterrogateClient, "CheckClientAccess", args=args)

    args = api_client.ApiListClientCrashesArgs(client_id=self.client_id)
    self.CheckMethodIsAccessChecked(
        self.router.ListClientCrashes, "CheckClientAccess", args=args)

    args = api_client.ApiGetClientLoadStatsArgs(client_id=self.client_id)
    self.CheckMethodIsAccessChecked(
        self.router.GetClientLoadStats, "CheckClientAccess", args=args)

  ACCESS_CHECKED_METHODS.extend([
      "ListFiles",
      "GetVfsFilesArchive",
      "GetFileDetails",
      "GetFileText",
      "GetFileBlob",
      "GetFileVersionTimes",
      "GetFileDownloadCommand",
      "CreateVfsRefreshOperation",
      "GetVfsTimeline",
      "GetVfsTimelineAsCsv",
      "UpdateVfsFileContent"
  ])  # pyformat: disable

  def testVfsMethodsAreAccessChecked(self):
    args = api_vfs.ApiListFilesArgs(client_id=self.client_id)
    self.CheckMethodIsAccessChecked(
        self.router.ListFiles, "CheckClientAccess", args=args)

    args = api_vfs.ApiGetVfsFilesArchiveArgs(client_id=self.client_id)
    self.CheckMethodIsAccessChecked(
        self.router.GetVfsFilesArchive, "CheckClientAccess", args=args)

    args = api_vfs.ApiGetFileDetailsArgs(client_id=self.client_id)
    self.CheckMethodIsAccessChecked(
        self.router.GetFileDetails, "CheckClientAccess", args=args)

    args = api_vfs.ApiGetFileTextArgs(client_id=self.client_id)
    self.CheckMethodIsAccessChecked(
        self.router.GetFileText, "CheckClientAccess", args=args)

    args = api_vfs.ApiGetFileBlobArgs(client_id=self.client_id)
    self.CheckMethodIsAccessChecked(
        self.router.GetFileBlob, "CheckClientAccess", args=args)

    args = api_vfs.ApiGetFileVersionTimesArgs(client_id=self.client_id)
    self.CheckMethodIsAccessChecked(
        self.router.GetFileVersionTimes, "CheckClientAccess", args=args)

    args = api_vfs.ApiGetFileDownloadCommandArgs(client_id=self.client_id)
    self.CheckMethodIsAccessChecked(
        self.router.GetFileDownloadCommand, "CheckClientAccess", args=args)

    args = api_vfs.ApiCreateVfsRefreshOperationArgs(client_id=self.client_id)
    self.CheckMethodIsAccessChecked(
        self.router.CreateVfsRefreshOperation, "CheckClientAccess", args=args)

    args = api_vfs.ApiGetVfsTimelineArgs(client_id=self.client_id)
    self.CheckMethodIsAccessChecked(
        self.router.GetVfsTimeline, "CheckClientAccess", args=args)

    args = api_vfs.ApiGetVfsTimelineAsCsvArgs(client_id=self.client_id)
    self.CheckMethodIsAccessChecked(
        self.router.GetVfsTimelineAsCsv, "CheckClientAccess", args=args)

    args = api_vfs.ApiUpdateVfsFileContentArgs(client_id=self.client_id)
    self.CheckMethodIsAccessChecked(
        self.router.UpdateVfsFileContent, "CheckClientAccess", args=args)

  ACCESS_CHECKED_METHODS.extend([
      "ListFlows",
      "GetFlow",
      "CreateFlow",
      "CancelFlow",
      "ListFlowRequests",
      "ListFlowResults",
      "GetExportedFlowResults",
      "GetFlowResultsExportCommand",
      "GetFlowFilesArchive",
      "ListFlowOutputPlugins",
      "ListFlowOutputPluginLogs",
      "ListFlowOutputPluginErrors",
      "ListFlowLogs"
  ])  # pyformat: disable

  def testAllClientFlowsMethodsAreAccessChecked(self):
    args = api_flow.ApiListFlowsArgs(client_id=self.client_id)
    self.CheckMethodIsAccessChecked(
        self.router.ListFlows, "CheckClientAccess", args=args)

    args = api_flow.ApiGetFlowArgs(client_id=self.client_id)
    self.CheckMethodIsAccessChecked(
        self.router.GetFlow, "CheckClientAccess", args=args)

    args = api_flow.ApiCreateFlowArgs(client_id=self.client_id)
    self.CheckMethodIsAccessChecked(
        self.router.CreateFlow, "CheckClientAccess", args=args)
    self.CheckMethodIsAccessChecked(
        self.router.CreateFlow, "CheckIfCanStartFlow", args=args)

    args = api_flow.ApiCancelFlowArgs(client_id=self.client_id)
    self.CheckMethodIsAccessChecked(
        self.router.CancelFlow, "CheckClientAccess", args=args)

    args = api_flow.ApiListFlowRequestsArgs(client_id=self.client_id)
    self.CheckMethodIsAccessChecked(
        self.router.ListFlowRequests, "CheckClientAccess", args=args)

    args = api_flow.ApiListFlowResultsArgs(client_id=self.client_id)
    self.CheckMethodIsAccessChecked(
        self.router.ListFlowResults, "CheckClientAccess", args=args)

    args = api_flow.ApiGetExportedFlowResultsArgs(client_id=self.client_id)
    self.CheckMethodIsAccessChecked(
        self.router.GetExportedFlowResults, "CheckClientAccess", args=args)

    args = api_flow.ApiGetFlowResultsExportCommandArgs(client_id=self.client_id)
    self.CheckMethodIsAccessChecked(
        self.router.GetFlowResultsExportCommand, "CheckClientAccess", args=args)

    args = api_flow.ApiGetFlowFilesArchiveArgs(client_id=self.client_id)
    self.CheckMethodIsAccessChecked(
        self.router.GetFlowFilesArchive, "CheckClientAccess", args=args)

    args = api_flow.ApiListFlowOutputPluginsArgs(client_id=self.client_id)
    self.CheckMethodIsAccessChecked(
        self.router.ListFlowOutputPlugins, "CheckClientAccess", args=args)

    args = api_flow.ApiListFlowOutputPluginLogsArgs(client_id=self.client_id)
    self.CheckMethodIsAccessChecked(
        self.router.ListFlowOutputPluginLogs, "CheckClientAccess", args=args)

    args = api_flow.ApiListFlowOutputPluginErrorsArgs(client_id=self.client_id)
    self.CheckMethodIsAccessChecked(
        self.router.ListFlowOutputPluginErrors, "CheckClientAccess", args=args)

    args = api_flow.ApiListFlowLogsArgs(client_id=self.client_id)
    self.CheckMethodIsAccessChecked(
        self.router.ListFlowLogs, "CheckClientAccess", args=args)

  ACCESS_CHECKED_METHODS.extend([
      "ForceRunCronJob",
      "ModifyCronJob",
      "DeleteCronJob"])  # pyformat: disable

  def testCronJobMethodsAreAccessChecked(self):
    args = api_cron.ApiForceRunCronJobArgs(cron_job_id="TestCronJob")
    self.CheckMethodIsAccessChecked(
        self.router.ForceRunCronJob, "CheckCronJobAccess", args=args)

    args = api_cron.ApiModifyCronJobArgs(cron_job_id="TestCronJob")
    self.CheckMethodIsAccessChecked(
        self.router.ModifyCronJob, "CheckCronJobAccess", args=args)

    args = api_cron.ApiDeleteCronJobArgs(cron_job_id="TestCronJob")
    self.CheckMethodIsAccessChecked(
        self.router.DeleteCronJob, "CheckCronJobAccess", args=args)

  ACCESS_CHECKED_METHODS.extend([
      "ModifyHunt",
      "DeleteHunt",
      "GetHuntFilesArchive",
      "GetHuntFile"])  # pyformat: disable

  def testModifyHuntIsAccessChecked(self):
    args = api_hunt.ApiModifyHuntArgs(hunt_id="H:123456")

    self.CheckMethodIsAccessChecked(
        self.router.ModifyHunt, "CheckHuntAccess", args=args)

  def testDeleteHuntRaisesIfHuntNotFound(self):
    args = api_hunt.ApiDeleteHuntArgs(hunt_id="H:123456")
    with self.assertRaises(api_call_handler_base.ResourceNotFoundError):
      self.router.DeleteHunt(args, token=self.token)

  def testDeleteHuntIsAccessCheckedIfUserIsNotCreator(self):
    hunt = self.CreateHunt()
    args = api_hunt.ApiDeleteHuntArgs(hunt_id=hunt.urn.Basename())

    self.CheckMethodIsAccessChecked(
        self.router.DeleteHunt,
        "CheckHuntAccess",
        args=args,
        token=access_control.ACLToken(username="foo"))

  def testDeleteHuntIsNotAccessCheckedIfUserIsCreator(self):
    hunt = self.CreateHunt()
    args = api_hunt.ApiDeleteHuntArgs(hunt_id=hunt.urn.Basename())

    self.CheckMethodIsNotAccessChecked(self.router.DeleteHunt, args=args)

  def testGetHuntFilesArchiveIsAccessChecked(self):
    args = api_hunt.ApiGetHuntFilesArchiveArgs(hunt_id="H:123456")
    self.CheckMethodIsAccessChecked(
        self.router.GetHuntFilesArchive, "CheckHuntAccess", args=args)

  def testGetHuntFileIsAccessChecked(self):
    args = api_hunt.ApiGetHuntFileArgs(hunt_id="H:123456")
    self.CheckMethodIsAccessChecked(
        self.router.GetHuntFilesArchive, "CheckHuntAccess", args=args)

  ACCESS_CHECKED_METHODS.extend([
      "ListGrrBinaries",
      "GetGrrBinary"])  # pyformat: disable

  def testListGrrBinariesIsAccessChecked(self):
    with self.assertRaises(access_control.UnauthorizedAccess):
      self.router.ListGrrBinaries(None, token=self.token)

    self.CreateAdminUser(self.token.username)
    self.router.ListGrrBinaries(None, token=self.token)

  def testGetGrrBinaryIsAccessChecked(self):
    with self.assertRaises(access_control.UnauthorizedAccess):
      self.router.GetGrrBinary(None, token=self.token)

    self.CreateAdminUser(self.token.username)
    self.router.GetGrrBinary(None, token=self.token)

  ACCESS_CHECKED_METHODS.extend([
      "ListFlowDescriptors",
  ])

  def testListFlowDescriptorsIsAccessChecked(self):
    handler = self.router.ListFlowDescriptors(None, token=self.token)
    # Check that correct security manager got passed into the handler.
    self.assertEqual(handler.legacy_security_manager,
                     self.router.legacy_manager)

  ACCESS_CHECKED_METHODS.extend([
      "GetGrrUser"])  # pyformat: disable

  def testGetGrrUserReturnsFullTraitsForAdminUser(self):
    self.CreateAdminUser(self.token.username)
    handler = self.router.GetGrrUser(None, token=self.token)

    self.assertEqual(handler.interface_traits,
                     api_user.ApiGrrUserInterfaceTraits().EnableAll())

  def testGetGrrUserReturnsRestrictedTraitsForNonAdminUser(self):
    handler = self.router.GetGrrUser(None, token=self.token)

    self.assertNotEqual(handler.interface_traits,
                        api_user.ApiGrrUserInterfaceTraits().EnableAll())

  def testAllOtherMethodsAreNotAccessChecked(self):
    unchecked_methods = (
        set(self.router.__class__.GetAnnotatedMethods().keys()) -
        set(self.ACCESS_CHECKED_METHODS))
    self.assertTrue(unchecked_methods)

    for method_name in unchecked_methods:
      self.CheckMethodIsNotAccessChecked(getattr(self.router, method_name))


class ApiCallRouterWithApprovalChecksE2ETest(http_api_e2e_test.ApiE2ETest):

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
