#!/usr/bin/env python
"""Implementation of a router class that does no ACL checks."""
from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

from grr_response_server.gui import api_call_router

from grr_response_server.gui.api_plugins import artifact as api_artifact
from grr_response_server.gui.api_plugins import client as api_client
from grr_response_server.gui.api_plugins import config as api_config
from grr_response_server.gui.api_plugins import cron as api_cron
from grr_response_server.gui.api_plugins import flow as api_flow
from grr_response_server.gui.api_plugins import hunt as api_hunt
from grr_response_server.gui.api_plugins import output_plugin as api_output_plugin
from grr_response_server.gui.api_plugins import reflection as api_reflection
from grr_response_server.gui.api_plugins import stats as api_stats
from grr_response_server.gui.api_plugins import user as api_user
from grr_response_server.gui.api_plugins import vfs as api_vfs


class ApiCallRouterWithoutChecks(api_call_router.ApiCallRouterStub):
  """Router that does no ACL checks whatsoever."""

  # Artifacts methods.
  # =================
  #
  def ListArtifacts(self, args, token=None):
    return api_artifact.ApiListArtifactsHandler()

  def UploadArtifact(self, args, token=None):
    return api_artifact.ApiUploadArtifactHandler()

  def DeleteArtifacts(self, args, token=None):
    return api_artifact.ApiDeleteArtifactsHandler()

  # Clients methods.
  # ===============
  #
  def SearchClients(self, args, token=None):
    return api_client.ApiSearchClientsHandler()

  def GetClient(self, args, token=None):
    return api_client.ApiGetClientHandler()

  def GetClientVersions(self, args, token=None):
    return api_client.ApiGetClientVersionsHandler()

  def GetClientVersionTimes(self, args, token=None):
    return api_client.ApiGetClientVersionTimesHandler()

  def InterrogateClient(self, args, token=None):
    return api_client.ApiInterrogateClientHandler()

  def GetInterrogateOperationState(self, args, token=None):
    return api_client.ApiGetInterrogateOperationStateHandler()

  def GetLastClientIPAddress(self, args, token=None):
    return api_client.ApiGetLastClientIPAddressHandler()

  def ListClientCrashes(self, args, token=None):
    return api_client.ApiListClientCrashesHandler()

  def ListClientActionRequests(self, args, token=None):
    return api_client.ApiListClientActionRequestsHandler()

  def GetClientLoadStats(self, args, token=None):
    return api_client.ApiGetClientLoadStatsHandler()

  # Virtual file system methods.
  # ============================
  #
  def ListFiles(self, args, token=None):
    return api_vfs.ApiListFilesHandler()

  def GetVfsFilesArchive(self, args, token=None):
    return api_vfs.ApiGetVfsFilesArchiveHandler()

  def GetFileDetails(self, args, token=None):
    return api_vfs.ApiGetFileDetailsHandler()

  def GetFileText(self, args, token=None):
    return api_vfs.ApiGetFileTextHandler()

  def GetFileBlob(self, args, token=None):
    return api_vfs.ApiGetFileBlobHandler()

  def GetFileVersionTimes(self, args, token=None):
    return api_vfs.ApiGetFileVersionTimesHandler()

  def GetFileDownloadCommand(self, args, token=None):
    return api_vfs.ApiGetFileDownloadCommandHandler()

  def CreateVfsRefreshOperation(self, args, token=None):
    return api_vfs.ApiCreateVfsRefreshOperationHandler()

  def GetVfsRefreshOperationState(self, args, token=None):
    return api_vfs.ApiGetVfsRefreshOperationStateHandler()

  def GetVfsTimeline(self, args, token=None):
    return api_vfs.ApiGetVfsTimelineHandler()

  def GetVfsTimelineAsCsv(self, args, token=None):
    return api_vfs.ApiGetVfsTimelineAsCsvHandler()

  def UpdateVfsFileContent(self, args, token=None):
    return api_vfs.ApiUpdateVfsFileContentHandler()

  def GetVfsFileContentUpdateState(self, args, token=None):
    return api_vfs.ApiGetVfsFileContentUpdateStateHandler()

  def GetFileDecoders(self, args, token=None):
    return api_vfs.ApiGetFileDecodersHandler()

  def GetDecodedFileBlob(self, args, token=None):
    return api_vfs.ApiGetDecodedFileHandler()

  # Clients labels methods.
  # ======================
  #
  def ListClientsLabels(self, args, token=None):
    return api_client.ApiListClientsLabelsHandler()

  def AddClientsLabels(self, args, token=None):
    return api_client.ApiAddClientsLabelsHandler()

  def RemoveClientsLabels(self, args, token=None):
    return api_client.ApiRemoveClientsLabelsHandler()

  # Clients flows methods.
  # =====================
  #
  def ListFlows(self, args, token=None):
    return api_flow.ApiListFlowsHandler()

  def GetFlow(self, args, token=None):
    return api_flow.ApiGetFlowHandler()

  def CreateFlow(self, args, token=None):
    return api_flow.ApiCreateFlowHandler()

  def CancelFlow(self, args, token=None):
    return api_flow.ApiCancelFlowHandler()

  def ListFlowRequests(self, args, token=None):
    return api_flow.ApiListFlowRequestsHandler()

  def ListFlowResults(self, args, token=None):
    return api_flow.ApiListFlowResultsHandler()

  def GetExportedFlowResults(self, args, token=None):
    return api_flow.ApiGetExportedFlowResultsHandler()

  def GetFlowResultsExportCommand(self, args, token=None):
    return api_flow.ApiGetFlowResultsExportCommandHandler()

  def GetFlowFilesArchive(self, args, token=None):
    return api_flow.ApiGetFlowFilesArchiveHandler()

  def ListFlowOutputPlugins(self, args, token=None):
    return api_flow.ApiListFlowOutputPluginsHandler()

  def ListFlowOutputPluginLogs(self, args, token=None):
    return api_flow.ApiListFlowOutputPluginLogsHandler()

  def ListFlowOutputPluginErrors(self, args, token=None):
    return api_flow.ApiListFlowOutputPluginErrorsHandler()

  def ListFlowLogs(self, args, token=None):
    return api_flow.ApiListFlowLogsHandler()

  # Cron jobs methods.
  # =================
  #
  def ListCronJobs(self, args, token=None):
    return api_cron.ApiListCronJobsHandler()

  def CreateCronJob(self, args, token=None):
    return api_cron.ApiCreateCronJobHandler()

  def GetCronJob(self, args, token=None):
    return api_cron.ApiGetCronJobHandler()

  def ForceRunCronJob(self, args, token=None):
    return api_cron.ApiForceRunCronJobHandler()

  def ModifyCronJob(self, args, token=None):
    return api_cron.ApiModifyCronJobHandler()

  def ListCronJobRuns(self, args, token=None):
    return api_cron.ApiListCronJobRunsHandler()

  def GetCronJobRun(self, args, token=None):
    return api_cron.ApiGetCronJobRunHandler()

  def DeleteCronJob(self, args, token=None):
    return api_cron.ApiDeleteCronJobHandler()

  # Hunts methods.
  # =============
  #
  def ListHunts(self, args, token=None):
    return api_hunt.ApiListHuntsHandler()

  def GetHunt(self, args, token=None):
    return api_hunt.ApiGetHuntHandler()

  def ListHuntErrors(self, args, token=None):
    return api_hunt.ApiListHuntErrorsHandler()

  def ListHuntLogs(self, args, token=None):
    return api_hunt.ApiListHuntLogsHandler()

  def ListHuntResults(self, args, token=None):
    return api_hunt.ApiListHuntResultsHandler()

  def GetExportedHuntResults(self, args, token=None):
    return api_hunt.ApiGetExportedHuntResultsHandler()

  def GetHuntResultsExportCommand(self, args, token=None):
    return api_hunt.ApiGetHuntResultsExportCommandHandler()

  def ListHuntOutputPlugins(self, args, token=None):
    return api_hunt.ApiListHuntOutputPluginsHandler()

  def ListHuntOutputPluginLogs(self, args, token=None):
    return api_hunt.ApiListHuntOutputPluginLogsHandler()

  def ListHuntOutputPluginErrors(self, args, token=None):
    return api_hunt.ApiListHuntOutputPluginErrorsHandler()

  def ListHuntCrashes(self, args, token=None):
    return api_hunt.ApiListHuntCrashesHandler()

  def GetHuntClientCompletionStats(self, args, token=None):
    return api_hunt.ApiGetHuntClientCompletionStatsHandler()

  def GetHuntStats(self, args, token=None):
    return api_hunt.ApiGetHuntStatsHandler()

  def ListHuntClients(self, args, token=None):
    return api_hunt.ApiListHuntClientsHandler()

  def GetHuntContext(self, args, token=None):
    return api_hunt.ApiGetHuntContextHandler()

  def CreateHunt(self, args, token=None):
    return api_hunt.ApiCreateHuntHandler()

  def ModifyHunt(self, args, token=None):
    return api_hunt.ApiModifyHuntHandler()

  def DeleteHunt(self, args, token=None):
    return api_hunt.ApiDeleteHuntHandler()

  def GetHuntFilesArchive(self, args, token=None):
    return api_hunt.ApiGetHuntFilesArchiveHandler()

  def GetHuntFile(self, args, token=None):
    return api_hunt.ApiGetHuntFileHandler()

  # Stats metrics methods.
  # =====================
  #
  def ListStatsStoreMetricsMetadata(self, args, token=None):
    return api_stats.ApiListStatsStoreMetricsMetadataHandler()

  def GetStatsStoreMetric(self, args, token=None):
    return api_stats.ApiGetStatsStoreMetricHandler()

  def ListReports(self, args, token=None):
    return api_stats.ApiListReportsHandler()

  def GetReport(self, args, token=None):
    return api_stats.ApiGetReportHandler()

  # Approvals methods.
  # =================
  #
  def CreateClientApproval(self, args, token=None):
    return api_user.ApiCreateClientApprovalHandler()

  def GetClientApproval(self, args, token=None):
    return api_user.ApiGetClientApprovalHandler()

  def GrantClientApproval(self, args, token=None):
    return api_user.ApiGrantClientApprovalHandler()

  def ListClientApprovals(self, args, token=None):
    return api_user.ApiListClientApprovalsHandler()

  def CreateHuntApproval(self, args, token=None):
    return api_user.ApiCreateHuntApprovalHandler()

  def GetHuntApproval(self, args, token=None):
    return api_user.ApiGetHuntApprovalHandler()

  def GrantHuntApproval(self, args, token=None):
    return api_user.ApiGrantHuntApprovalHandler()

  def ListHuntApprovals(self, args, token=None):
    return api_user.ApiListHuntApprovalsHandler()

  def CreateCronJobApproval(self, args, token=None):
    return api_user.ApiCreateCronJobApprovalHandler()

  def GetCronJobApproval(self, args, token=None):
    return api_user.ApiGetCronJobApprovalHandler()

  def GrantCronJobApproval(self, args, token=None):
    return api_user.ApiGrantCronJobApprovalHandler()

  def ListCronJobApprovals(self, args, token=None):
    return api_user.ApiListCronJobApprovalsHandler()

  def ListApproverSuggestions(self, args, token=None):
    return api_user.ApiListApproverSuggestionsHandler()

  # User settings methods.
  # =====================
  #
  def GetPendingUserNotificationsCount(self, args, token=None):
    return api_user.ApiGetPendingUserNotificationsCountHandler()

  def ListPendingUserNotifications(self, args, token=None):
    return api_user.ApiListPendingUserNotificationsHandler()

  def DeletePendingUserNotification(self, args, token=None):
    return api_user.ApiDeletePendingUserNotificationHandler()

  def ListAndResetUserNotifications(self, args, token=None):
    return api_user.ApiListAndResetUserNotificationsHandler()

  def GetGrrUser(self, args, token=None):
    return api_user.ApiGetOwnGrrUserHandler(
        interface_traits=api_user.ApiGrrUserInterfaceTraits().EnableAll())

  def UpdateGrrUser(self, args, token=None):
    return api_user.ApiUpdateGrrUserHandler()

  # Config methods.
  # ==============
  #
  def GetConfig(self, args, token=None):
    return api_config.ApiGetConfigHandler()

  def GetConfigOption(self, args, token=None):
    return api_config.ApiGetConfigOptionHandler()

  def ListGrrBinaries(self, args, token=None):
    return api_config.ApiListGrrBinariesHandler()

  def GetGrrBinary(self, args, token=None):
    return api_config.ApiGetGrrBinaryHandler()

  def GetGrrBinaryBlob(self, args, token=None):
    return api_config.ApiGetGrrBinaryBlobHandler()

  # Reflection methods.
  # ==================
  #
  def ListKbFields(self, args, token=None):
    return api_client.ApiListKbFieldsHandler()

  def ListFlowDescriptors(self, args, token=None):
    # TODO(user): move to reflection.py
    return api_flow.ApiListFlowDescriptorsHandler()

  def ListAff4AttributeDescriptors(self, args, token=None):
    return api_reflection.ApiListAff4AttributeDescriptorsHandler()

  def GetRDFValueDescriptor(self, args, token=None):
    return api_reflection.ApiGetRDFValueDescriptorHandler()

  def ListRDFValuesDescriptors(self, args, token=None):
    return api_reflection.ApiListRDFValuesDescriptorsHandler()

  def ListOutputPluginDescriptors(self, args, token=None):
    return api_output_plugin.ApiListOutputPluginDescriptorsHandler()

  def ListKnownEncodings(self, args, token=None):
    return api_vfs.ApiListKnownEncodingsHandler()

  def ListApiMethods(self, args, token=None):
    return api_reflection.ApiListApiMethodsHandler(self)
