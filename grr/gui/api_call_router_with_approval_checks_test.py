#!/usr/bin/env python
"""Tests for an ApiCallRouterWithChecks."""




import mock

from grr.gui import api_call_router_with_approval_checks as api_router

from grr.gui.api_plugins import client as api_client
from grr.gui.api_plugins import cron as api_cron
from grr.gui.api_plugins import flow as api_flow
from grr.gui.api_plugins import hunt as api_hunt
from grr.gui.api_plugins import vfs as api_vfs

from grr.lib import access_control
from grr.lib import flags
from grr.lib import test_lib

from grr.lib.rdfvalues import client as rdf_client


class ApiCallRouterWithApprovalChecksWithoutRobotAccessTest(
    test_lib.GRRBaseTest):
  """Tests for an ApiCallRouterWithApprovalChecksWithoutRobotAccess."""

  # ACCESS_CHECKED_METHODS is used to identify the methods that are tested
  # for being checked for necessary access rights. This list is used
  # in testAllOtherMethodsAreNotAccessChecked.
  ACCESS_CHECKED_METHODS = []

  def setUp(self):
    super(ApiCallRouterWithApprovalChecksWithoutRobotAccessTest, self).setUp()

    self.client_id = rdf_client.ClientURN("C.0000111122223333")

    self.delegate_mock = mock.MagicMock()
    self.legacy_manager_mock = mock.MagicMock()

    self.router = api_router.ApiCallRouterWithApprovalChecksWithoutRobotAccess(
        delegate=self.delegate_mock,
        legacy_manager=self.legacy_manager_mock)

  def CheckMethodIsAccessChecked(self, method, access_type, args=None):
    # Check that legacy access control manager is called and that the method
    # is then delegated.
    method(args, token=self.token)
    self.assertTrue(getattr(self.legacy_manager_mock, access_type).called)
    getattr(self.delegate_mock, method.__name__).assert_called_with(
        args, token=self.token)

    self.delegate_mock.reset_mock()
    self.legacy_manager_mock.reset_mock()

    try:
      # Check that when exception is raised by legacy manager, the delegate
      # method is not called.
      getattr(self.legacy_manager_mock,
              access_type).side_effect = access_control.UnauthorizedAccess("")

      with self.assertRaises(access_control.UnauthorizedAccess):
        method(args, token=self.token)

      self.assertTrue(getattr(self.legacy_manager_mock, access_type).called)
      self.assertFalse(getattr(self.delegate_mock, method.__name__).called)

    finally:
      getattr(self.legacy_manager_mock, access_type).side_effect = None
      self.delegate_mock.reset_mock()
      self.legacy_manager_mock.reset_mock()

  def CheckMethodIsNotAccessChecked(self, method, args=None):
    method(args, token=self.token)

    self.assertFalse(self.legacy_manager_mock.CheckClientAccess.called)
    self.assertFalse(self.legacy_manager_mock.CheckHuntAccess.called)
    self.assertFalse(self.legacy_manager_mock.CheckCronJob.called)
    self.assertFalse(self.legacy_manager_mock.CheckIfCanStartFlow.called)
    self.assertFalse(self.legacy_manager_mock.CheckDataStoreAccess.called)

    getattr(self.delegate_mock, method.__name__).assert_called_with(
        args, token=self.token)

    self.delegate_mock.reset_mock()
    self.legacy_manager_mock.reset_mock()

  ACCESS_CHECKED_METHODS.extend([
      "InterrogateClient"])  # pyformat: disable

  def testClientMethodsAreAccessChecked(self):
    args = api_client.ApiInterrogateClientArgs(client_id=self.client_id)
    self.CheckMethodIsAccessChecked(self.router.InterrogateClient,
                                    "CheckClientAccess",
                                    args=args)

  ACCESS_CHECKED_METHODS.extend([
      "CreateVfsRefreshOperation",
      "ListFiles",
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
    self.CheckMethodIsAccessChecked(self.router.ListFiles,
                                    "CheckClientAccess",
                                    args=args)

    args = api_vfs.ApiGetFileDetailsArgs(client_id=self.client_id)
    self.CheckMethodIsAccessChecked(self.router.GetFileDetails,
                                    "CheckClientAccess",
                                    args=args)

    args = api_vfs.ApiGetFileTextArgs(client_id=self.client_id)
    self.CheckMethodIsAccessChecked(self.router.GetFileText,
                                    "CheckClientAccess",
                                    args=args)

    args = api_vfs.ApiGetFileBlobArgs(client_id=self.client_id)
    self.CheckMethodIsAccessChecked(self.router.GetFileBlob,
                                    "CheckClientAccess",
                                    args=args)

    args = api_vfs.ApiGetFileVersionTimesArgs(client_id=self.client_id)
    self.CheckMethodIsAccessChecked(self.router.GetFileVersionTimes,
                                    "CheckClientAccess",
                                    args=args)

    args = api_vfs.ApiGetFileDownloadCommandArgs(client_id=self.client_id)
    self.CheckMethodIsAccessChecked(self.router.GetFileDownloadCommand,
                                    "CheckClientAccess",
                                    args=args)

    args = api_vfs.ApiCreateVfsRefreshOperationArgs(client_id=self.client_id)
    self.CheckMethodIsAccessChecked(self.router.CreateVfsRefreshOperation,
                                    "CheckClientAccess",
                                    args=args)

    args = api_vfs.ApiGetVfsTimelineArgs(client_id=self.client_id)
    self.CheckMethodIsAccessChecked(self.router.GetVfsTimeline,
                                    "CheckClientAccess",
                                    args=args)

    args = api_vfs.ApiGetVfsTimelineAsCsvArgs(client_id=self.client_id)
    self.CheckMethodIsAccessChecked(self.router.GetVfsTimelineAsCsv,
                                    "CheckClientAccess",
                                    args=args)

    args = api_vfs.ApiUpdateVfsFileContentArgs(client_id=self.client_id)
    self.CheckMethodIsAccessChecked(self.router.UpdateVfsFileContent,
                                    "CheckClientAccess",
                                    args=args)

  ACCESS_CHECKED_METHODS.extend([
      "ListFlows",
      "GetFlow",
      "CreateFlow",
      "CancelFlow",
      "ListFlowResults",
      "GetFlowResultsExportCommand",
      "GetFlowFilesArchive",
      "ListFlowOutputPlugins",
      "ListFlowOutputPluginLogs",
      "ListFlowOutputPluginErrors",
      "ListFlowLogs"
  ])  # pyformat: disable

  def testAllClientFlowsMethodsAreAccessChecked(self):
    args = api_flow.ApiListFlowsArgs(client_id=self.client_id)
    self.CheckMethodIsAccessChecked(self.router.ListFlows,
                                    "CheckClientAccess",
                                    args=args)

    args = api_flow.ApiGetFlowArgs(client_id=self.client_id)
    self.CheckMethodIsAccessChecked(self.router.GetFlow,
                                    "CheckClientAccess",
                                    args=args)

    args = api_flow.ApiCreateFlowArgs(client_id=self.client_id)
    self.CheckMethodIsAccessChecked(self.router.CreateFlow,
                                    "CheckClientAccess",
                                    args=args)
    self.CheckMethodIsAccessChecked(self.router.CreateFlow,
                                    "CheckIfCanStartFlow",
                                    args=args)

    args = api_flow.ApiCancelFlowArgs(client_id=self.client_id)
    self.CheckMethodIsAccessChecked(self.router.CancelFlow,
                                    "CheckClientAccess",
                                    args=args)

    args = api_flow.ApiListFlowResultsArgs(client_id=self.client_id)
    self.CheckMethodIsAccessChecked(self.router.ListFlowResults,
                                    "CheckClientAccess",
                                    args=args)

    args = api_flow.ApiGetFlowResultsExportCommandArgs(client_id=self.client_id)
    self.CheckMethodIsAccessChecked(self.router.GetFlowResultsExportCommand,
                                    "CheckClientAccess",
                                    args=args)

    args = api_flow.ApiGetFlowFilesArchiveArgs(client_id=self.client_id)
    self.CheckMethodIsAccessChecked(self.router.GetFlowFilesArchive,
                                    "CheckClientAccess",
                                    args=args)

    args = api_flow.ApiListFlowOutputPluginsArgs(client_id=self.client_id)
    self.CheckMethodIsAccessChecked(self.router.ListFlowOutputPlugins,
                                    "CheckClientAccess",
                                    args=args)

    args = api_flow.ApiListFlowOutputPluginLogsArgs(client_id=self.client_id)
    self.CheckMethodIsAccessChecked(self.router.ListFlowOutputPluginLogs,
                                    "CheckClientAccess",
                                    args=args)

    args = api_flow.ApiListFlowOutputPluginErrorsArgs(client_id=self.client_id)
    self.CheckMethodIsAccessChecked(self.router.ListFlowOutputPluginErrors,
                                    "CheckClientAccess",
                                    args=args)

    args = api_flow.ApiListFlowLogsArgs(client_id=self.client_id)
    self.CheckMethodIsAccessChecked(self.router.ListFlowLogs,
                                    "CheckClientAccess",
                                    args=args)

  ACCESS_CHECKED_METHODS.extend([
      "CreateGlobalFlow"])  # pyformat: disable

  def testAllGlobalFlowsMethodsAreAccessChecked(self):
    args = api_flow.ApiCreateFlowArgs(
        flow=api_flow.ApiFlow(name="ListProcesses"))
    self.CheckMethodIsAccessChecked(self.router.CreateGlobalFlow,
                                    "CheckIfCanStartFlow",
                                    args=args)

  ACCESS_CHECKED_METHODS.extend([
      "DeleteCronJob"])  # pyformat: disable

  def testCronJobMethodsAreAccessChecked(self):
    args = api_cron.ApiDeleteCronJobArgs(cron_job_id="TestCronJob")
    self.CheckMethodIsAccessChecked(self.router.DeleteCronJob,
                                    "CheckCronJobAccess",
                                    args=args)

  ACCESS_CHECKED_METHODS.extend([
      "GetHuntFilesArchive",
      "GetHuntFile"])  # pyformat: disable

  def testGetHuntFilesArchiveIsAccessChecked(self):
    args = api_hunt.ApiGetHuntFilesArchiveArgs(hunt_id="H:123456")
    self.CheckMethodIsAccessChecked(self.router.GetHuntFilesArchive,
                                    "CheckHuntAccess",
                                    args=args)

  def testGetHuntFileIsAccessChecked(self):
    args = api_hunt.ApiGetHuntFileArgs(hunt_id="H:123456")
    self.CheckMethodIsAccessChecked(self.router.GetHuntFilesArchive,
                                    "CheckHuntAccess",
                                    args=args)

  ACCESS_CHECKED_METHODS.extend([
      "StartRobotGetFilesOperation",
      "GetRobotGetFilesOperationState"])  # pyformat: disable

  def testRobotMethodsAreRejected(self):
    with self.assertRaises(access_control.UnauthorizedAccess):
      self.router.StartRobotGetFilesOperation(None, token=self.token)

    with self.assertRaises(access_control.UnauthorizedAccess):
      self.router.GetRobotGetFilesOperationState(None, token=self.token)

  def testAllOtherMethodsAreNotAccessChecked(self):
    unchecked_methods = (set(self.router.__class__.GetAnnotatedMethods().keys())
                         - set(self.ACCESS_CHECKED_METHODS))
    self.assertTrue(unchecked_methods)

    for method_name in unchecked_methods:
      self.CheckMethodIsNotAccessChecked(getattr(self.router, method_name))


class ApiCallRouterWithApprovalChecksWithRobotAccessTest(test_lib.GRRBaseTest):
  """Tests for ApiCallRouterWithApprovalChecksWithRobotAccess."""

  def setUp(self):
    super(ApiCallRouterWithApprovalChecksWithRobotAccessTest, self).setUp()

    self.delegate_mock = mock.MagicMock()
    self.router = api_router.ApiCallRouterWithApprovalChecksWithRobotAccess(
        delegate=self.delegate_mock)

  def testRobotMethodsAreNotChecked(self):
    self.router.StartRobotGetFilesOperation(None, token=self.token)
    self.delegate_mock.StartRobotGetFilesOperation.assert_called_with(
        None, token=self.token)

    self.router.GetRobotGetFilesOperationState(None, token=self.token)
    self.delegate_mock.GetRobotGetFilesOperationState.assert_called_with(
        None, token=self.token)


def main(argv):
  test_lib.main(argv)


if __name__ == "__main__":
  flags.StartMain(main)
