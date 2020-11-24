#!/usr/bin/env python
# Lint as: python3
"""Tests for an ApiCallRouterWithChecks."""
from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

from absl import app
import mock

from grr_response_server import access_control

from grr_response_server.flows.general import timeline
from grr_response_server.flows.general import osquery
from grr_response_server.gui import api_call_context
from grr_response_server.gui import api_call_handler_base
from grr_response_server.gui import api_call_router_with_approval_checks as api_router
from grr_response_server.gui.api_plugins import client as api_client
from grr_response_server.gui.api_plugins import cron as api_cron
from grr_response_server.gui.api_plugins import flow as api_flow
from grr_response_server.gui.api_plugins import hunt as api_hunt
from grr_response_server.gui.api_plugins import timeline as api_timeline
from grr_response_server.gui.api_plugins import osquery as api_osquery
from grr_response_server.gui.api_plugins import user as api_user
from grr_response_server.gui.api_plugins import vfs as api_vfs

from grr.test_lib import flow_test_lib
from grr.test_lib import hunt_test_lib
from grr.test_lib import test_lib


class ApiCallRouterWithApprovalChecksTest(test_lib.GRRBaseTest,
                                          hunt_test_lib.StandardHuntTestMixin):
  """Tests for an ApiCallRouterWithApprovalChecks."""

  # ACCESS_CHECKED_METHODS is used to identify the methods that are tested
  # for being checked for necessary access rights. This list is used
  # in testAllOtherMethodsAreNotAccessChecked. It is populated below in batches
  # to group tests.
  ACCESS_CHECKED_METHODS = []

  def setUp(self):
    super(ApiCallRouterWithApprovalChecksTest, self).setUp()

    self.client_id = test_lib.TEST_CLIENT_ID
    self.context = api_call_context.ApiCallContext("test")

    self.delegate_mock = mock.MagicMock()
    self.access_checker_mock = mock.MagicMock()

    self.router = api_router.ApiCallRouterWithApprovalChecks(
        delegate=self.delegate_mock, access_checker=self.access_checker_mock)

  def CheckMethodIsAccessChecked(self,
                                 method,
                                 access_type,
                                 args=None,
                                 context=None):
    context = context or self.context

    # Check that legacy access control manager is called and that the method
    # is then delegated.
    method(args, context=context)
    self.assertTrue(getattr(self.access_checker_mock, access_type).called)
    getattr(self.delegate_mock, method.__name__).assert_called_with(
        args, context=context)

    self.delegate_mock.reset_mock()
    self.access_checker_mock.reset_mock()

    try:
      # Check that when exception is raised by legacy manager, the delegate
      # method is not called.
      getattr(self.access_checker_mock,
              access_type).side_effect = access_control.UnauthorizedAccess("")

      with self.assertRaises(access_control.UnauthorizedAccess):
        method(args, context=context)

      self.assertTrue(getattr(self.access_checker_mock, access_type).called)
      self.assertFalse(getattr(self.delegate_mock, method.__name__).called)

    finally:
      getattr(self.access_checker_mock, access_type).side_effect = None
      self.delegate_mock.reset_mock()
      self.access_checker_mock.reset_mock()

  def CheckMethodIsNotAccessChecked(self, method, args=None, context=None):
    context = context or self.context

    method(args, context=context)

    self.assertFalse(self.access_checker_mock.CheckClientAccess.called)
    self.assertFalse(self.access_checker_mock.CheckHuntAccess.called)
    self.assertFalse(self.access_checker_mock.CheckCronJob.called)
    self.assertFalse(self.access_checker_mock.CheckIfCanStartClientFlow.called)
    self.assertFalse(self.access_checker_mock.CheckDataStoreAccess.called)

    getattr(self.delegate_mock, method.__name__).assert_called_with(
        args, context=context)

    self.delegate_mock.reset_mock()
    self.access_checker_mock.reset_mock()

  ACCESS_CHECKED_METHODS.extend([
      "InterrogateClient",
      "ListClientCrashes",
      "ListClientActionRequests",
      "GetClientLoadStats",
  ])

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
      "VerifyAccess",
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
      "UpdateVfsFileContent",
      "GetFileDecoders",
      "GetDecodedFileBlob",
  ])

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
      "GetCollectedTimeline",
  ])

  def testGetCollectedTimelineRaisesIfFlowIsNotFound(self):
    args = api_timeline.ApiGetCollectedTimelineArgs(
        client_id=self.client_id, flow_id="12345678")
    with self.assertRaises(api_call_handler_base.ResourceNotFoundError):
      self.router.GetCollectedTimeline(args, context=self.context)

  def testGetCollectedTimelineGrantsAccessIfPartOfHunt(self):
    client_id = self.SetupClient(0)
    hunt_id = self.CreateHunt()
    flow_id = flow_test_lib.StartFlow(
        timeline.TimelineFlow, client_id=client_id, parent_hunt_id=hunt_id)

    args = api_timeline.ApiGetCollectedTimelineArgs(
        client_id=client_id, flow_id=flow_id)
    self.CheckMethodIsNotAccessChecked(
        self.router.GetCollectedTimeline, args=args)

  def testGetCollectedTimelineRefusesAccessIfPartOfHuntButWrongFlow(self):
    client_id = self.SetupClient(0)
    hunt_id = self.CreateHunt()
    flow_id = flow_test_lib.StartFlow(
        flow_test_lib.DummyFlow, client_id=client_id, parent_hunt_id=hunt_id)

    args = api_timeline.ApiGetCollectedTimelineArgs(
        client_id=client_id, flow_id=flow_id)
    with self.assertRaises(ValueError):
      self.router.GetCollectedTimeline(args=args, context=self.context)

  def testGetCollectedTimelineRefusesAccessIfWrongFlow(self):
    client_id = self.SetupClient(0)
    flow_id = flow_test_lib.StartFlow(
        flow_test_lib.DummyFlow, client_id=client_id)

    args = api_timeline.ApiGetCollectedTimelineArgs(
        client_id=client_id, flow_id=flow_id)
    with self.assertRaises(ValueError):
      self.router.GetCollectedTimeline(args=args, context=self.context)

  def testGetCollectedTimelineChecksClientAccessIfNotPartOfHunt(self):
    client_id = self.SetupClient(0)
    flow_id = flow_test_lib.StartFlow(
        timeline.TimelineFlow, client_id=client_id)

    args = api_timeline.ApiGetCollectedTimelineArgs(
        client_id=client_id, flow_id=flow_id)
    self.CheckMethodIsAccessChecked(
        self.router.GetCollectedTimeline, "CheckClientAccess", args=args)

  ACCESS_CHECKED_METHODS.extend([
      "GetOsqueryResults",
  ])

  def testGetOsqueryResultsRaisesIfFlowIsNotFound(self):
    args = api_osquery.ApiGetOsqueryResultsArgs(
        client_id=self.client_id, flow_id="12345678")
    with self.assertRaises(api_call_handler_base.ResourceNotFoundError):
      self.router.GetOsqueryResults(args, context=self.context)

  def testGetOsqueryResultsGrantsAccessIfPartOfHunt(self):
    client_id = self.SetupClient(0)
    hunt_id = self.CreateHunt()
    flow_id = flow_test_lib.StartFlow(
        osquery.OsqueryFlow, client_id=client_id, parent_hunt_id=hunt_id)

    args = api_osquery.ApiGetOsqueryResultsArgs(
        client_id=client_id, flow_id=flow_id)
    self.CheckMethodIsNotAccessChecked(
        self.router.GetOsqueryResults, args=args)

  def testGetOsqueryResultsRefusesAccessIfPartOfHuntButWrongFlow(self):
    client_id = self.SetupClient(0)
    hunt_id = self.CreateHunt()
    flow_id = flow_test_lib.StartFlow(
        flow_test_lib.DummyFlow, client_id=client_id, parent_hunt_id=hunt_id)

    args = api_osquery.ApiGetOsqueryResultsArgs(
        client_id=client_id, flow_id=flow_id)
    with self.assertRaises(ValueError):
      self.router.GetOsqueryResults(args=args, context=self.context)

  def testGetOsqueryResultsRefusesAccessIfWrongFlow(self):
    client_id = self.SetupClient(0)
    flow_id = flow_test_lib.StartFlow(
        flow_test_lib.DummyFlow, client_id=client_id)

    args = api_osquery.ApiGetOsqueryResultsArgs(
        client_id=client_id, flow_id=flow_id)
    with self.assertRaises(ValueError):
      self.router.GetOsqueryResults(args=args, context=self.context)

  def testGetOsqueryResultsChecksClientAccessIfNotPartOfHunt(self):
    client_id = self.SetupClient(0)
    flow_id = flow_test_lib.StartFlow(
        osquery.OsqueryFlow, client_id=client_id)

    args = api_osquery.ApiGetOsqueryResultsArgs(
        client_id=client_id, flow_id=flow_id)
    self.CheckMethodIsAccessChecked(
        self.router.GetOsqueryResults, "CheckClientAccess", args=args)

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
      "ListFlowLogs",
  ])

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
        self.router.CreateFlow, "CheckIfCanStartClientFlow", args=args)

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
      "DeleteCronJob",
  ])

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
      "GetHuntFile",
  ])

  def testModifyHuntIsAccessChecked(self):
    args = api_hunt.ApiModifyHuntArgs(hunt_id="H:123456")

    self.CheckMethodIsAccessChecked(
        self.router.ModifyHunt, "CheckHuntAccess", args=args)

  def testDeleteHuntRaisesIfHuntNotFound(self):
    args = api_hunt.ApiDeleteHuntArgs(hunt_id="H:123456")
    with self.assertRaises(api_call_handler_base.ResourceNotFoundError):
      self.router.DeleteHunt(args, context=self.context)

  def testDeleteHuntIsAccessCheckedIfUserIsNotCreator(self):
    hunt_id = self.CreateHunt(creator=self.context.username)
    args = api_hunt.ApiDeleteHuntArgs(hunt_id=hunt_id)

    self.CheckMethodIsAccessChecked(
        self.router.DeleteHunt,
        "CheckHuntAccess",
        args=args,
        context=api_call_context.ApiCallContext("foo"))

  def testDeleteHuntIsNotAccessCheckedIfUserIsCreator(self):
    hunt_id = self.CreateHunt(creator=self.context.username)
    args = api_hunt.ApiDeleteHuntArgs(hunt_id=hunt_id)

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
      "GetGrrBinary",
      "GetGrrBinaryBlob",
  ])

  def testListGrrBinariesIsAccessChecked(self):
    self.CheckMethodIsAccessChecked(self.router.ListGrrBinaries,
                                    "CheckIfUserIsAdmin")

  def testGetGrrBinaryIsAccessChecked(self):
    self.CheckMethodIsAccessChecked(self.router.GetGrrBinary,
                                    "CheckIfUserIsAdmin")

  def testGetGrrBinaryBlobIsAccessChecked(self):
    self.CheckMethodIsAccessChecked(self.router.GetGrrBinary,
                                    "CheckIfUserIsAdmin")

  ACCESS_CHECKED_METHODS.extend([
      "ListFlowDescriptors",
  ])

  def testListFlowDescriptorsIsAccessChecked(self):
    handler = self.router.ListFlowDescriptors(None, context=self.context)
    # Check that router's access_checker's method got passed into the handler.
    self.assertEqual(handler.access_check_fn,
                     self.router.access_checker.CheckIfCanStartClientFlow)

  ACCESS_CHECKED_METHODS.extend([
      "GetGrrUser",
  ])

  def testGetGrrUserReturnsFullTraitsForAdminUser(self):
    handler = self.router.GetGrrUser(None, context=self.context)

    self.assertEqual(handler.interface_traits,
                     api_user.ApiGrrUserInterfaceTraits().EnableAll())

  def testGetGrrUserReturnsRestrictedTraitsForNonAdminUser(self):
    error = access_control.UnauthorizedAccess("some error")
    self.access_checker_mock.CheckIfUserIsAdmin.side_effect = error
    handler = self.router.GetGrrUser(None, context=self.context)

    self.assertNotEqual(handler.interface_traits,
                        api_user.ApiGrrUserInterfaceTraits().EnableAll())

  def testAllOtherMethodsAreNotAccessChecked(self):
    unchecked_methods = (
        set(self.router.__class__.GetAnnotatedMethods().keys()) -
        set(self.ACCESS_CHECKED_METHODS))
    self.assertTrue(unchecked_methods)

    for method_name in unchecked_methods:
      self.CheckMethodIsNotAccessChecked(getattr(self.router, method_name))


def main(argv):
  test_lib.main(argv)


if __name__ == "__main__":
  app.run(main)
