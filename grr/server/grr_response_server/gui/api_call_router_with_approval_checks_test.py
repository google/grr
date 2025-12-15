#!/usr/bin/env python
"""Tests for an ApiCallRouterWithChecks."""

from unittest import mock

from absl import app

from grr_response_proto import api_call_router_pb2
from grr_response_proto import objects_pb2
from grr_response_proto.api import client_pb2 as api_client_pb2
from grr_response_proto.api import cron_pb2 as api_cron_pb2
from grr_response_proto.api import flow_pb2 as api_flow_pb2
from grr_response_proto.api import hunt_pb2 as api_hunt_pb2
from grr_response_proto.api import osquery_pb2 as api_osquery_pb2
from grr_response_proto.api import timeline_pb2 as api_timeline_pb2
from grr_response_proto.api import vfs_pb2 as api_vfs_pb2
from grr_response_server import access_control
from grr_response_server import data_store
from grr_response_server import flow
from grr_response_server.authorization import groups
from grr_response_server.flows.general import osquery
from grr_response_server.flows.general import timeline
from grr_response_server.gui import api_call_context
from grr_response_server.gui import api_call_handler_base
from grr_response_server.gui import api_call_router_with_approval_checks as api_router
from grr.test_lib import flow_test_lib
from grr.test_lib import hunt_test_lib
from grr.test_lib import test_lib


class ApiCallRouterWithApprovalChecksTest(
    test_lib.GRRBaseTest, hunt_test_lib.StandardHuntTestMixin
):
  """Tests for an ApiCallRouterWithApprovalChecks."""

  # ACCESS_CHECKED_METHODS is used to identify the methods that are tested
  # for being checked for necessary access rights. This list is used
  # in testAllOtherMethodsAreNotAccessChecked. It is populated below in batches
  # to group tests.
  ACCESS_CHECKED_METHODS = []

  # APPROVAL_HANDLER_METHODS use approval checks to return the approval status
  # in the response. Simple tests for access rights are not working in these
  # cases as they do not distinguish between access rights to the API and
  # approval status computation.
  APPROVAL_HANDLER_METHODS = [
      "CreateClientApproval",
      "GrantClientApproval",
      "GetClientApproval",
      "ListClientApprovals",
      "CreateHuntApproval",
      "GrantHuntApproval",
      "GetHuntApproval",
      "ListHuntApprovals",
      "CreateCronJobApproval",
      "GrantCronJobApproval",
      "GetCronJobApproval",
      "ListCronJobApprovals",
  ]

  def setUp(self):
    super().setUp()

    self.client_id = test_lib.TEST_CLIENT_ID
    self.context = api_call_context.ApiCallContext("test")

    self.delegate_mock = mock.MagicMock()
    self.admin_checker_mock = mock.MagicMock()
    self.approval_checker_mock = mock.MagicMock()
    self.mitigation_flows_access_checker_mock = mock.MagicMock()

    self.router = api_router.ApiCallRouterWithApprovalChecks(
        params=api_call_router_pb2.ApiCallRouterWithApprovalCheckParams(),
        delegate=self.delegate_mock,
        admin_access_checker=self.admin_checker_mock,
        approval_checker=self.approval_checker_mock,
        mitigation_flows_access_checker=self.mitigation_flows_access_checker_mock,
    )

  def CheckMethodIsAccessChecked(
      self,
      method,
      access_type,
      access_checker_mock=None,
      args=None,
      context=None,
  ):
    context = context or self.context

    if not access_checker_mock:
      access_checker_mock = self.approval_checker_mock

    # Check that legacy access control manager is called and that the method
    # is then delegated.
    method(args, context=context)
    self.assertTrue(getattr(access_checker_mock, access_type).called)
    getattr(self.delegate_mock, method.__name__).assert_called_with(
        args, context=context
    )

    self.delegate_mock.reset_mock()
    access_checker_mock.reset_mock()

    try:
      # Check that when exception is raised by legacy manager, the delegate
      # method is not called.
      getattr(access_checker_mock, access_type).side_effect = (
          access_control.UnauthorizedAccess("")
      )

      with self.assertRaises(access_control.UnauthorizedAccess):
        method(args, context=context)

      self.assertTrue(getattr(access_checker_mock, access_type).called)
      self.assertFalse(getattr(self.delegate_mock, method.__name__).called)

    finally:
      getattr(access_checker_mock, access_type).side_effect = None
      self.delegate_mock.reset_mock()
      access_checker_mock.reset_mock()

  def CheckMethodIsNotAccessChecked(self, method, args=None, context=None):
    context = context or self.context

    method(args, context=context)

    self.assertFalse(self.approval_checker_mock.CheckClientAccess.called)
    self.assertFalse(self.approval_checker_mock.CheckHuntAccess.called)
    self.assertFalse(self.approval_checker_mock.CheckCronJob.called)
    self.assertFalse(self.admin_checker_mock.CheckIfCanStartFlow.called)
    self.assertFalse(self.approval_checker_mock.CheckDataStoreAccess.called)
    self.assertFalse(
        self.mitigation_flows_access_checker_mock.CheckIfHasAccessToFlow.called
    )

    getattr(self.delegate_mock, method.__name__).assert_called_with(
        args, context=context
    )

    self.delegate_mock.reset_mock()
    self.approval_checker_mock.reset_mock()

  ACCESS_CHECKED_METHODS.extend([
      "InterrogateClient",
      "ListClientCrashes",
  ])

  def testClientMethodsAreAccessChecked(self):
    args = api_client_pb2.ApiInterrogateClientArgs(client_id=self.client_id)
    self.CheckMethodIsAccessChecked(
        self.router.InterrogateClient, "CheckClientAccess", args=args
    )

    args = api_client_pb2.ApiListClientCrashesArgs(client_id=self.client_id)
    self.CheckMethodIsAccessChecked(
        self.router.ListClientCrashes, "CheckClientAccess", args=args
    )

  ACCESS_CHECKED_METHODS.extend([
      "VerifyAccess",
      "VerifyHuntAccess",
      "ListFiles",
      "BrowseFilesystem",
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
      "KillFleetspeak",
      "RestartFleetspeakGrrService",
      "DeleteFleetspeakPendingMessages",
      "GetFleetspeakPendingMessages",
      "GetFleetspeakPendingMessageCount",
  ])

  def testVfsMethodsAreAccessChecked(self):
    args = api_vfs_pb2.ApiListFilesArgs(client_id=self.client_id)
    self.CheckMethodIsAccessChecked(
        self.router.ListFiles, "CheckClientAccess", args=args
    )

    args = api_vfs_pb2.ApiBrowseFilesystemArgs(client_id=self.client_id)
    self.CheckMethodIsAccessChecked(
        self.router.BrowseFilesystem, "CheckClientAccess", args=args
    )

    args = api_vfs_pb2.ApiGetVfsFilesArchiveArgs(client_id=self.client_id)
    self.CheckMethodIsAccessChecked(
        self.router.GetVfsFilesArchive, "CheckClientAccess", args=args
    )

    args = api_vfs_pb2.ApiGetFileDetailsArgs(client_id=self.client_id)
    self.CheckMethodIsAccessChecked(
        self.router.GetFileDetails, "CheckClientAccess", args=args
    )

    args = api_vfs_pb2.ApiGetFileTextArgs(client_id=self.client_id)
    self.CheckMethodIsAccessChecked(
        self.router.GetFileText, "CheckClientAccess", args=args
    )

    args = api_vfs_pb2.ApiGetFileBlobArgs(client_id=self.client_id)
    self.CheckMethodIsAccessChecked(
        self.router.GetFileBlob, "CheckClientAccess", args=args
    )

    args = api_vfs_pb2.ApiGetFileVersionTimesArgs(client_id=self.client_id)
    self.CheckMethodIsAccessChecked(
        self.router.GetFileVersionTimes, "CheckClientAccess", args=args
    )

    args = api_vfs_pb2.ApiGetFileDownloadCommandArgs(client_id=self.client_id)
    self.CheckMethodIsAccessChecked(
        self.router.GetFileDownloadCommand, "CheckClientAccess", args=args
    )

    args = api_vfs_pb2.ApiCreateVfsRefreshOperationArgs(
        client_id=self.client_id
    )
    self.CheckMethodIsAccessChecked(
        self.router.CreateVfsRefreshOperation, "CheckClientAccess", args=args
    )

    args = api_vfs_pb2.ApiGetVfsTimelineArgs(client_id=self.client_id)
    self.CheckMethodIsAccessChecked(
        self.router.GetVfsTimeline, "CheckClientAccess", args=args
    )

    args = api_vfs_pb2.ApiGetVfsTimelineAsCsvArgs(client_id=self.client_id)
    self.CheckMethodIsAccessChecked(
        self.router.GetVfsTimelineAsCsv, "CheckClientAccess", args=args
    )

    args = api_vfs_pb2.ApiUpdateVfsFileContentArgs(client_id=self.client_id)
    self.CheckMethodIsAccessChecked(
        self.router.UpdateVfsFileContent, "CheckClientAccess", args=args
    )

  ACCESS_CHECKED_METHODS.extend([
      "GetCollectedTimeline",
  ])

  def testGetCollectedTimelineRaisesIfFlowIsNotFound(self):
    args = api_timeline_pb2.ApiGetCollectedTimelineArgs(
        client_id=self.client_id, flow_id="12345678"
    )
    with self.assertRaises(api_call_handler_base.ResourceNotFoundError):
      self.router.GetCollectedTimeline(args, context=self.context)

  def testGetCollectedTimelineGrantsAccessIfPartOfHunt(self):
    client_id = self.SetupClient(0)
    hunt_id = self.CreateHunt()
    flow_id = flow_test_lib.StartFlow(
        timeline.TimelineFlow,
        client_id=client_id,
        parent=flow.FlowParent.FromHuntID(hunt_id),
    )

    args = api_timeline_pb2.ApiGetCollectedTimelineArgs(
        client_id=client_id, flow_id=flow_id
    )
    self.CheckMethodIsNotAccessChecked(
        self.router.GetCollectedTimeline, args=args
    )

  def testGetCollectedTimelineRefusesAccessIfPartOfHuntButWrongFlow(self):
    client_id = self.SetupClient(0)
    hunt_id = self.CreateHunt()
    flow_id = flow_test_lib.StartFlow(
        flow_test_lib.DummyFlow,
        client_id=client_id,
        parent=flow.FlowParent.FromHuntID(hunt_id),
    )

    args = api_timeline_pb2.ApiGetCollectedTimelineArgs(
        client_id=client_id, flow_id=flow_id
    )
    with self.assertRaises(ValueError):
      self.router.GetCollectedTimeline(args=args, context=self.context)

  def testGetCollectedTimelineRefusesAccessIfWrongFlow(self):
    client_id = self.SetupClient(0)
    flow_id = flow_test_lib.StartFlow(
        flow_test_lib.DummyFlow, client_id=client_id
    )

    args = api_timeline_pb2.ApiGetCollectedTimelineArgs(
        client_id=client_id, flow_id=flow_id
    )
    with self.assertRaises(ValueError):
      self.router.GetCollectedTimeline(args=args, context=self.context)

  def testGetCollectedTimelineChecksClientAccessIfNotPartOfHunt(self):
    client_id = self.SetupClient(0)
    flow_id = flow_test_lib.StartFlow(
        timeline.TimelineFlow, client_id=client_id
    )

    args = api_timeline_pb2.ApiGetCollectedTimelineArgs(
        client_id=client_id, flow_id=flow_id
    )
    self.CheckMethodIsAccessChecked(
        self.router.GetCollectedTimeline, "CheckClientAccess", args=args
    )

  ACCESS_CHECKED_METHODS.extend([
      "GetOsqueryResults",
  ])

  def testGetOsqueryResultsRaisesIfFlowIsNotFound(self):
    args = api_osquery_pb2.ApiGetOsqueryResultsArgs(
        client_id=self.client_id, flow_id="12345678"
    )
    with self.assertRaises(api_call_handler_base.ResourceNotFoundError):
      self.router.GetOsqueryResults(args, context=self.context)

  def testGetOsqueryResultsGrantsAccessIfPartOfHunt(self):
    client_id = self.SetupClient(0)
    hunt_id = self.CreateHunt()
    flow_id = flow_test_lib.StartFlow(
        osquery.OsqueryFlow,
        client_id=client_id,
        parent=flow.FlowParent.FromHuntID(hunt_id),
    )

    args = api_osquery_pb2.ApiGetOsqueryResultsArgs(
        client_id=client_id, flow_id=flow_id
    )
    self.CheckMethodIsNotAccessChecked(self.router.GetOsqueryResults, args=args)

  def testGetOsqueryResultsRefusesAccessIfPartOfHuntButWrongFlow(self):
    client_id = self.SetupClient(0)
    hunt_id = self.CreateHunt()
    flow_id = flow_test_lib.StartFlow(
        flow_test_lib.DummyFlow,
        client_id=client_id,
        parent=flow.FlowParent.FromHuntID(hunt_id),
    )

    args = api_osquery_pb2.ApiGetOsqueryResultsArgs(
        client_id=client_id, flow_id=flow_id
    )
    with self.assertRaises(ValueError):
      self.router.GetOsqueryResults(args=args, context=self.context)

  def testGetOsqueryResultsRefusesAccessIfWrongFlow(self):
    client_id = self.SetupClient(0)
    flow_id = flow_test_lib.StartFlow(
        flow_test_lib.DummyFlow, client_id=client_id
    )

    args = api_osquery_pb2.ApiGetOsqueryResultsArgs(
        client_id=client_id, flow_id=flow_id
    )
    with self.assertRaises(ValueError):
      self.router.GetOsqueryResults(args=args, context=self.context)

  def testGetOsqueryResultsChecksClientAccessIfNotPartOfHunt(self):
    client_id = self.SetupClient(0)
    flow_id = flow_test_lib.StartFlow(osquery.OsqueryFlow, client_id=client_id)

    args = api_osquery_pb2.ApiGetOsqueryResultsArgs(
        client_id=client_id, flow_id=flow_id
    )
    self.CheckMethodIsAccessChecked(
        self.router.GetOsqueryResults, "CheckClientAccess", args=args
    )

  ACCESS_CHECKED_METHODS.extend([
      "ListFlows",
      "CreateFlow",
      "CancelFlow",
      "ListFlowRequests",
      "ListFlowOutputPlugins",
      "ListFlowOutputPluginLogs",
      "ListFlowOutputPluginErrors",
      "ListAllFlowOutputPluginLogs",
      "ListFlowLogs",
      "ScheduleFlow",
  ])

  def testClientFlowsMethodsAreAccessChecked(self):
    args = api_flow_pb2.ApiListFlowsArgs(client_id=self.client_id)
    self.CheckMethodIsAccessChecked(
        self.router.ListFlows, "CheckClientAccess", args=args
    )

    args = api_flow_pb2.ApiCreateFlowArgs(client_id=self.client_id)
    self.CheckMethodIsAccessChecked(
        self.router.CreateFlow, "CheckClientAccess", args=args
    )
    self.CheckMethodIsAccessChecked(
        self.router.CreateFlow,
        "CheckIfCanStartFlow",
        access_checker_mock=self.admin_checker_mock,
        args=args,
    )

    self.CheckMethodIsAccessChecked(
        self.router.CreateFlow,
        "CheckIfHasAccessToFlow",
        access_checker_mock=self.mitigation_flows_access_checker_mock,
        args=args,
    )

    self.CheckMethodIsAccessChecked(
        self.router.ScheduleFlow,
        "CheckIfHasAccessToFlow",
        access_checker_mock=self.mitigation_flows_access_checker_mock,
        args=args,
    )

    args = api_flow_pb2.ApiCancelFlowArgs(client_id=self.client_id)
    self.CheckMethodIsAccessChecked(
        self.router.CancelFlow, "CheckClientAccess", args=args
    )

    args = api_flow_pb2.ApiListFlowRequestsArgs(client_id=self.client_id)
    self.CheckMethodIsAccessChecked(
        self.router.ListFlowRequests, "CheckClientAccess", args=args
    )

    args = api_flow_pb2.ApiListFlowOutputPluginsArgs(client_id=self.client_id)
    self.CheckMethodIsAccessChecked(
        self.router.ListFlowOutputPlugins, "CheckClientAccess", args=args
    )

    args = api_flow_pb2.ApiListFlowOutputPluginLogsArgs(
        client_id=self.client_id
    )
    self.CheckMethodIsAccessChecked(
        self.router.ListFlowOutputPluginLogs, "CheckClientAccess", args=args
    )

    args = api_flow_pb2.ApiListFlowOutputPluginErrorsArgs(
        client_id=self.client_id
    )
    self.CheckMethodIsAccessChecked(
        self.router.ListFlowOutputPluginErrors, "CheckClientAccess", args=args
    )

    args = api_flow_pb2.ApiListAllFlowOutputPluginLogsArgs(
        client_id=self.client_id
    )
    self.CheckMethodIsAccessChecked(
        self.router.ListAllFlowOutputPluginLogs, "CheckClientAccess", args=args
    )

    args = api_flow_pb2.ApiListFlowLogsArgs(client_id=self.client_id)
    self.CheckMethodIsAccessChecked(
        self.router.ListFlowLogs, "CheckClientAccess", args=args
    )

  ACCESS_CHECKED_METHODS.extend([
      "GetFlow",
      "ListFlowResults",
      "GetExportedFlowResults",
      "GetFlowResultsExportCommand",
      "GetFlowFilesArchive",
  ])

  def testHuntFlowExceptionsRaisesRaisesIfFlowIsNotFound(self):
    args = api_flow_pb2.ApiGetFlowArgs(
        client_id=self.client_id, flow_id="12345678"
    )
    with self.assertRaises(api_call_handler_base.ResourceNotFoundError):
      self.router.GetFlow(args, context=self.context)

    args = api_flow_pb2.ApiListFlowResultsArgs(
        client_id=self.client_id, flow_id="12345678"
    )
    with self.assertRaises(api_call_handler_base.ResourceNotFoundError):
      self.router.ListFlowResults(args, context=self.context)

    args = api_flow_pb2.ApiGetExportedFlowResultsArgs(
        client_id=self.client_id, flow_id="12345678"
    )
    with self.assertRaises(api_call_handler_base.ResourceNotFoundError):
      self.router.GetExportedFlowResults(args, context=self.context)

    args = api_flow_pb2.ApiGetFlowResultsExportCommandArgs(
        client_id=self.client_id, flow_id="12345678"
    )
    with self.assertRaises(api_call_handler_base.ResourceNotFoundError):
      self.router.GetFlowResultsExportCommand(args, context=self.context)

    args = api_flow_pb2.ApiGetFlowFilesArchiveArgs(
        client_id=self.client_id, flow_id="12345678"
    )
    with self.assertRaises(api_call_handler_base.ResourceNotFoundError):
      self.router.GetFlowFilesArchive(args, context=self.context)

  def testHuntFlowExceptionsGrantsAccessIfPartOfHunt(self):
    client_id = self.SetupClient(0)
    hunt_id = self.CreateHunt()
    flow_id = flow_test_lib.StartFlow(
        timeline.TimelineFlow,
        client_id=client_id,
        parent=flow.FlowParent.FromHuntID(hunt_id),
    )

    args = api_flow_pb2.ApiGetFlowArgs(
        client_id=self.client_id, flow_id=flow_id
    )
    self.CheckMethodIsNotAccessChecked(self.router.GetFlow, args=args)

    args = api_flow_pb2.ApiListFlowResultsArgs(
        client_id=self.client_id, flow_id=flow_id
    )
    self.CheckMethodIsNotAccessChecked(self.router.ListFlowResults, args=args)

    args = api_flow_pb2.ApiGetExportedFlowResultsArgs(
        client_id=self.client_id, flow_id=flow_id
    )
    self.CheckMethodIsNotAccessChecked(
        self.router.GetExportedFlowResults, args=args
    )

    args = api_flow_pb2.ApiGetFlowResultsExportCommandArgs(
        client_id=self.client_id, flow_id=flow_id
    )
    self.CheckMethodIsNotAccessChecked(
        self.router.GetFlowResultsExportCommand, args=args
    )

    args = api_flow_pb2.ApiGetFlowFilesArchiveArgs(
        client_id=self.client_id, flow_id=flow_id
    )
    self.CheckMethodIsNotAccessChecked(
        self.router.GetFlowFilesArchive, args=args
    )

  def testHuntFlowExceptionsChecksClientAccessIfNotPartOfHunt(self):
    client_id = self.SetupClient(0)
    flow_id = flow_test_lib.StartFlow(
        timeline.TimelineFlow, client_id=client_id
    )

    args = api_flow_pb2.ApiGetFlowArgs(
        client_id=self.client_id, flow_id=flow_id
    )
    self.CheckMethodIsAccessChecked(
        self.router.GetFlow, "CheckClientAccess", args=args
    )

    args = api_flow_pb2.ApiListFlowResultsArgs(
        client_id=self.client_id, flow_id=flow_id
    )
    self.CheckMethodIsAccessChecked(
        self.router.ListFlowResults,
        "CheckClientAccess",
        args=args,
    )

    args = api_flow_pb2.ApiGetExportedFlowResultsArgs(
        client_id=self.client_id, flow_id=flow_id
    )
    self.CheckMethodIsAccessChecked(
        self.router.GetExportedFlowResults,
        "CheckClientAccess",
        args=args,
    )

    args = api_flow_pb2.ApiGetFlowResultsExportCommandArgs(
        client_id=self.client_id, flow_id=flow_id
    )
    self.CheckMethodIsAccessChecked(
        self.router.GetFlowResultsExportCommand,
        "CheckClientAccess",
        args=args,
    )

    args = api_flow_pb2.ApiGetFlowFilesArchiveArgs(
        client_id=self.client_id, flow_id=flow_id
    )
    self.CheckMethodIsAccessChecked(
        self.router.GetFlowFilesArchive,
        "CheckClientAccess",
        args=args,
    )

  ACCESS_CHECKED_METHODS.extend([
      "ForceRunCronJob",
      "ModifyCronJob",
      "DeleteCronJob",
  ])

  def testCronJobMethodsAreAccessChecked(self):
    args = api_cron_pb2.ApiForceRunCronJobArgs(cron_job_id="TestCronJob")
    self.CheckMethodIsAccessChecked(
        self.router.ForceRunCronJob, "CheckCronJobAccess", args=args
    )

    args = api_cron_pb2.ApiModifyCronJobArgs(cron_job_id="TestCronJob")
    self.CheckMethodIsAccessChecked(
        self.router.ModifyCronJob, "CheckCronJobAccess", args=args
    )

    args = api_cron_pb2.ApiDeleteCronJobArgs(cron_job_id="TestCronJob")
    self.CheckMethodIsAccessChecked(
        self.router.DeleteCronJob, "CheckCronJobAccess", args=args
    )

  ACCESS_CHECKED_METHODS.extend([
      "CreateHunt",
      "ModifyHunt",
      "DeleteHunt",
      "GetHuntFilesArchive",
      "GetHuntFile",
  ])

  def testCreatingHuntIsAccessChecked(self):
    args = api_hunt_pb2.ApiCreateHuntArgs(
        flow_name=osquery.OsqueryFlow.__name__
    )
    self.CheckMethodIsAccessChecked(
        self.router.CreateHunt,
        "CheckIfCanStartFlow",
        access_checker_mock=self.admin_checker_mock,
        args=args,
    )
    self.CheckMethodIsAccessChecked(
        self.router.CreateHunt,
        "CheckIfHasAccessToFlow",
        access_checker_mock=self.mitigation_flows_access_checker_mock,
        args=args,
    )

  def testModifyHuntIsAccessChecked(self):
    args = api_hunt_pb2.ApiModifyHuntArgs(hunt_id="H:123456")

    self.CheckMethodIsAccessChecked(
        self.router.ModifyHunt, "CheckHuntAccess", args=args
    )

  def testDeleteHuntRaisesIfHuntNotFound(self):
    args = api_hunt_pb2.ApiDeleteHuntArgs(hunt_id="H:123456")
    with self.assertRaises(api_call_handler_base.ResourceNotFoundError):
      self.router.DeleteHunt(args, context=self.context)

  def testDeleteHuntIsAccessCheckedIfUserIsNotCreator(self):
    hunt_id = self.CreateHunt(creator=self.context.username)
    args = api_hunt_pb2.ApiDeleteHuntArgs(hunt_id=hunt_id)

    self.CheckMethodIsAccessChecked(
        self.router.DeleteHunt,
        "CheckHuntAccess",
        args=args,
        context=api_call_context.ApiCallContext("foo"),
    )

  def testDeleteHuntIsNotAccessCheckedIfUserIsCreator(self):
    hunt_id = self.CreateHunt(creator=self.context.username)
    args = api_hunt_pb2.ApiDeleteHuntArgs(hunt_id=hunt_id)

    self.CheckMethodIsNotAccessChecked(self.router.DeleteHunt, args=args)

  def testGetHuntFilesArchiveIsAccessChecked(self):
    args = api_hunt_pb2.ApiGetHuntFilesArchiveArgs(hunt_id="H:123456")
    self.CheckMethodIsAccessChecked(
        self.router.GetHuntFilesArchive, "CheckHuntAccess", args=args
    )

  def testGetHuntFileIsAccessChecked(self):
    args = api_hunt_pb2.ApiGetHuntFileArgs(hunt_id="H:123456")
    self.CheckMethodIsAccessChecked(
        self.router.GetHuntFilesArchive, "CheckHuntAccess", args=args
    )

  ACCESS_CHECKED_METHODS.extend([
      "ListGrrBinaries",
      "GetGrrBinary",
      "GetGrrBinaryBlob",
  ])

  def testListGrrBinariesIsAccessChecked(self):
    self.CheckMethodIsAccessChecked(
        self.router.ListGrrBinaries,
        "CheckIfHasAdminAccess",
        access_checker_mock=self.admin_checker_mock,
    )

  def testGetGrrBinaryIsAccessChecked(self):
    self.CheckMethodIsAccessChecked(
        self.router.GetGrrBinary,
        "CheckIfHasAdminAccess",
        access_checker_mock=self.admin_checker_mock,
    )

  def testGetGrrBinaryBlobIsAccessChecked(self):
    self.CheckMethodIsAccessChecked(
        self.router.GetGrrBinary,
        "CheckIfHasAdminAccess",
        access_checker_mock=self.admin_checker_mock,
    )

  ACCESS_CHECKED_METHODS.extend([
      "ListFlowDescriptors",
  ])

  def testListFlowDescriptorsIsAccessChecked(self):
    handler = self.router.ListFlowDescriptors(None, context=self.context)
    # Check that router's access_checker's method got passed into the handler.
    self.assertEqual(
        handler.access_check_fn,
        self.router.admin_access_checker.CheckIfCanStartFlow,
    )

  ACCESS_CHECKED_METHODS.extend([
      "GetGrrUser",
  ])

  def testGetGrrUserReturnsAdminStatusWhenWithRestrictedFlowsAccess(self):
    handler = self.router.GetGrrUser(None, context=self.context)

    self.assertTrue(handler.is_admin)

  def testGetGrrUserReturnsNoAdminStatusWhenWithoutRestrictedFlowsAccess(
      self,
  ):
    error = access_control.UnauthorizedAccess("some error")
    self.admin_checker_mock.CheckIfHasAdminAccess.side_effect = error
    handler = self.router.GetGrrUser(None, context=self.context)

    self.assertFalse(handler.is_admin)

  def testAllOtherMethodsAreNotAccessChecked(self):
    unchecked_methods = (
        set(self.router.__class__.GetAnnotatedMethods().keys())
        - set(self.ACCESS_CHECKED_METHODS)
        - set(self.APPROVAL_HANDLER_METHODS)
    )
    self.assertTrue(unchecked_methods)

    for method_name in unchecked_methods:
      self.CheckMethodIsNotAccessChecked(getattr(self.router, method_name))


class ApprovalCheckParamsAdminAccessCheckerTest(test_lib.GRRBaseTest):
  """Tests for the ApprovalCheckParamsAdminAccessChecker."""

  def testCheckHasAdminAccess_AdminUser(self):
    username = "admin"
    data_store.REL_DB.WriteGRRUser(
        username, user_type=objects_pb2.GRRUser.UserType.USER_TYPE_ADMIN
    )
    checker = api_router.ApprovalCheckParamsAdminAccessChecker(
        params=api_call_router_pb2.ApiCallRouterWithApprovalCheckParams()
    )
    checker.CheckIfHasAdminAccess(username)

  @mock.patch(groups.__name__ + ".CreateGroupAccessManager")
  def testCheckHasAdminAccess_RouterParamsAdminUser(self, _):
    username = "admin"
    data_store.REL_DB.WriteGRRUser(
        username, user_type=objects_pb2.GRRUser.UserType.USER_TYPE_STANDARD
    )

    params = api_call_router_pb2.ApiCallRouterWithApprovalCheckParams(
        ignore_admin_user_attribute=True, admin_users=[username]
    )
    checker = api_router.ApprovalCheckParamsAdminAccessChecker(params=params)
    checker.CheckIfHasAdminAccess(username)

  @mock.patch(groups.__name__ + ".CreateGroupAccessManager")
  def testCheckHasAdminAccess_RouterParamsAdminGroup(self, mock_access_mngr):
    group = "admin-group"
    username = "admin-group-member"
    data_store.REL_DB.WriteGRRUser(
        username, user_type=objects_pb2.GRRUser.UserType.USER_TYPE_STANDARD
    )

    params = api_call_router_pb2.ApiCallRouterWithApprovalCheckParams(
        ignore_admin_user_attribute=True, admin_groups=[group]
    )
    checker = api_router.ApprovalCheckParamsAdminAccessChecker(params=params)
    # We are not testing the access manager implementation here, so only ensure
    # it is called with the right arguments.
    mock_access_mngr.return_value.AuthorizeGroup.assert_called_with(
        group, "admin-access"
    )
    mock_access_mngr.return_value.MemberOfAuthorizedGroup.return_value = True

    checker.CheckIfHasAdminAccess(username)
    mock_access_mngr.return_value.MemberOfAuthorizedGroup.assert_called_with(
        username, "admin-access"
    )

  @mock.patch(groups.__name__ + ".CreateGroupAccessManager")
  def testCheckHasAdminAccess_NotAdminUserRaises(self, mock_access_mngr):
    username = "not_admin"
    data_store.REL_DB.WriteGRRUser(
        username, user_type=objects_pb2.GRRUser.UserType.USER_TYPE_STANDARD
    )
    checker = api_router.ApprovalCheckParamsAdminAccessChecker(
        params=api_call_router_pb2.ApiCallRouterWithApprovalCheckParams(
            ignore_admin_user_attribute=False, admin_users=[]
        )
    )
    mock_access_mngr.return_value.MemberOfAuthorizedGroup.return_value = False
    with self.assertRaisesRegex(
        access_control.UnauthorizedAccess,
        "No Admin user access for not_admin.",
    ):
      checker.CheckIfHasAdminAccess(username)


class ApprovalCheckParamsMitigationFlowsAccessCheckerTest(test_lib.GRRBaseTest):
  """Tests for the ApprovalCheckParamsMitigationFlowsAccessChecker."""

  @mock.patch(groups.__name__ + ".CreateGroupAccessManager")
  def testCheckHasAccessToMitigationFlows_Passes_RouterParamsMitigationFlowsUser(
      self, _
  ):
    username = "mitigation-flow-user"

    params = api_call_router_pb2.ApiCallRouterWithApprovalCheckParams(
        mitigation_flows_users=[username]
    )
    checker = api_router.ApprovalCheckParamsMitigationFlowsAccessChecker(
        params=params
    )
    checker.CheckIfHasAccessToMitigationFlows(username)

  @mock.patch(groups.__name__ + ".CreateGroupAccessManager")
  def testCheckHasAccessToMitigationFlows_Passes_RouterParamsMitigationFlowsGroup(
      self, mock_access_mngr
  ):
    group = "mitigation-flow-group"
    username = "mitigation-flow-group-member"

    params = api_call_router_pb2.ApiCallRouterWithApprovalCheckParams(
        mitigation_flows_groups=[group]
    )
    checker = api_router.ApprovalCheckParamsMitigationFlowsAccessChecker(
        params=params
    )
    # We are not testing the access manager implementation here, so only ensure
    # it is called with the right arguments.
    mock_access_mngr.return_value.AuthorizeGroup.assert_called_with(
        group, "mitigation-flows-access"
    )
    mock_access_mngr.return_value.MemberOfAuthorizedGroup.return_value = True

    checker.CheckIfHasAccessToMitigationFlows(username)
    mock_access_mngr.return_value.MemberOfAuthorizedGroup.assert_called_with(
        username, "mitigation-flows-access"
    )

  @mock.patch(groups.__name__ + ".CreateGroupAccessManager")
  def testCheckHasAccessToMitigationFlows_Raises_NotMitigationFlowUserRaises(
      self, mock_access_mngr
  ):
    username = "not-mitigation-flow-user"

    checker = api_router.ApprovalCheckParamsMitigationFlowsAccessChecker(
        params=api_call_router_pb2.ApiCallRouterWithApprovalCheckParams(
            mitigation_flows_users=[]
        )
    )
    mock_access_mngr.return_value.MemberOfAuthorizedGroup.return_value = False
    with self.assertRaisesRegex(
        access_control.UnauthorizedAccess,
        "No access to mitigation flows for not-mitigation-flow-user.",
    ):
      checker.CheckIfHasAccessToMitigationFlows(username)


def main(argv):
  test_lib.main(argv)


if __name__ == "__main__":
  app.run(main)
