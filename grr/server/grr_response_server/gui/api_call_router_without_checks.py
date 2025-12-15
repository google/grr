#!/usr/bin/env python
"""Implementation of a router class that does no ACL checks."""

from typing import Optional

from grr_response_proto.api import artifact_pb2 as api_artifact_pb2
from grr_response_proto.api import client_pb2 as api_client_pb2
from grr_response_proto.api import config_pb2 as api_config_pb2
from grr_response_proto.api import cron_pb2 as api_cron_pb2
from grr_response_proto.api import flow_pb2 as api_flow_pb2
from grr_response_proto.api import hunt_pb2 as api_hunt_pb2
from grr_response_proto.api import osquery_pb2 as api_osquery_pb2
from grr_response_proto.api import timeline_pb2 as api_timeline_pb2
from grr_response_proto.api import user_pb2 as api_user_pb2
from grr_response_proto.api import vfs_pb2 as api_vfs_pb2
from grr_response_proto.api import yara_pb2 as api_yara_pb2
from grr_response_server.gui import api_call_context
from grr_response_server.gui import api_call_router
from grr_response_server.gui.api_plugins import artifact as api_artifact
from grr_response_server.gui.api_plugins import client as api_client
from grr_response_server.gui.api_plugins import config as api_config
from grr_response_server.gui.api_plugins import cron as api_cron
from grr_response_server.gui.api_plugins import flow as api_flow
from grr_response_server.gui.api_plugins import hunt as api_hunt
from grr_response_server.gui.api_plugins import metadata as api_metadata
from grr_response_server.gui.api_plugins import osquery as api_osquery
from grr_response_server.gui.api_plugins import output_plugin as api_output_plugin
from grr_response_server.gui.api_plugins import reflection as api_reflection
from grr_response_server.gui.api_plugins import signed_commands as api_signed_commands
from grr_response_server.gui.api_plugins import timeline as api_timeline
from grr_response_server.gui.api_plugins import user as api_user
from grr_response_server.gui.api_plugins import vfs as api_vfs
from grr_response_server.gui.api_plugins import yara as api_yara


class ApiCallRouterWithoutChecks(api_call_router.ApiCallRouterStub):
  """Router that does no ACL checks whatsoever."""

  # Artifacts methods.
  # =================
  #
  def ListArtifacts(
      self,
      args: api_artifact_pb2.ApiListArtifactsArgs,
      context: Optional[api_call_context.ApiCallContext] = None,
  ) -> api_artifact.ApiListArtifactsHandler:
    return api_artifact.ApiListArtifactsHandler()

  def UploadArtifact(
      self,
      args: api_artifact_pb2.ApiUploadArtifactArgs,
      context: Optional[api_call_context.ApiCallContext] = None,
  ) -> api_artifact.ApiUploadArtifactHandler:
    return api_artifact.ApiUploadArtifactHandler()

  def DeleteArtifacts(
      self,
      args: api_artifact_pb2.ApiDeleteArtifactsArgs,
      context: Optional[api_call_context.ApiCallContext] = None,
  ) -> api_artifact.ApiDeleteArtifactsHandler:
    return api_artifact.ApiDeleteArtifactsHandler()

  # Clients methods.
  # ===============
  #
  def SearchClients(self, args, context=None):
    return api_client.ApiSearchClientsHandler()

  def VerifyAccess(
      self,
      args: api_client_pb2.ApiVerifyAccessArgs,
      context: Optional[api_call_context.ApiCallContext] = None,
  ) -> api_client.ApiVerifyAccessHandler:
    return api_client.ApiVerifyAccessHandler()

  def GetClient(
      self,
      args: api_client_pb2.ApiGetClientArgs,
      context: Optional[api_call_context.ApiCallContext] = None,
  ) -> api_client.ApiGetClientHandler:
    return api_client.ApiGetClientHandler()

  def GetClientVersions(
      self,
      args: api_client_pb2.ApiGetClientVersionsArgs,
      context: Optional[api_call_context.ApiCallContext] = None,
  ) -> api_client.ApiGetClientVersionsHandler:
    return api_client.ApiGetClientVersionsHandler()

  def GetClientVersionTimes(
      self,
      args: api_client_pb2.ApiGetClientVersionTimesArgs,
      context: Optional[api_call_context.ApiCallContext] = None,
  ) -> api_client.ApiGetClientVersionTimesHandler:
    return api_client.ApiGetClientVersionTimesHandler()

  def GetClientSnapshots(
      self,
      args: api_client_pb2.ApiGetClientSnapshotsArgs,
      context: Optional[api_call_context.ApiCallContext] = None,
  ) -> api_client.ApiGetClientSnapshotsHandler:
    return api_client.ApiGetClientSnapshotsHandler()

  def GetClientStartupInfos(
      self,
      args: api_client_pb2.ApiGetClientStartupInfosArgs,
      context: Optional[api_call_context.ApiCallContext] = None,
  ) -> api_client.ApiGetClientStartupInfosHandler:
    return api_client.ApiGetClientStartupInfosHandler()

  def InterrogateClient(
      self,
      args: api_client_pb2.ApiInterrogateClientArgs,
      context: Optional[api_call_context.ApiCallContext] = None,
  ) -> api_client.ApiInterrogateClientHandler:
    return api_client.ApiInterrogateClientHandler()

  def GetLastClientIPAddress(
      self,
      args: api_client_pb2.ApiGetLastClientIPAddressArgs,
      context: Optional[api_call_context.ApiCallContext] = None,
  ) -> api_client.ApiGetLastClientIPAddressHandler:
    return api_client.ApiGetLastClientIPAddressHandler()

  def ListClientCrashes(
      self,
      args: api_client_pb2.ApiListClientCrashesArgs,
      context: Optional[api_call_context.ApiCallContext] = None,
  ) -> api_client.ApiListClientCrashesHandler:
    return api_client.ApiListClientCrashesHandler()

  def KillFleetspeak(
      self,
      args: api_client_pb2.ApiKillFleetspeakArgs,
      context: Optional[api_call_context.ApiCallContext] = None,
  ) -> api_client.ApiKillFleetspeakHandler:
    return api_client.ApiKillFleetspeakHandler()

  def RestartFleetspeakGrrService(
      self,
      args: api_client_pb2.ApiRestartFleetspeakGrrServiceArgs,
      context: Optional[api_call_context.ApiCallContext] = None,
  ) -> api_client.ApiRestartFleetspeakGrrServiceHandler:
    return api_client.ApiRestartFleetspeakGrrServiceHandler()

  def DeleteFleetspeakPendingMessages(
      self,
      args: api_client_pb2.ApiDeleteFleetspeakPendingMessagesArgs,
      context: Optional[api_call_context.ApiCallContext] = None,
  ) -> api_client.ApiDeleteFleetspeakPendingMessagesHandler:
    return api_client.ApiDeleteFleetspeakPendingMessagesHandler()

  def GetFleetspeakPendingMessages(
      self,
      args: api_client_pb2.ApiGetFleetspeakPendingMessagesArgs,
      context: Optional[api_call_context.ApiCallContext] = None,
  ) -> api_client.ApiGetFleetspeakPendingMessagesHandler:
    return api_client.ApiGetFleetspeakPendingMessagesHandler()

  def GetFleetspeakPendingMessageCount(
      self,
      args: api_client_pb2.ApiGetFleetspeakPendingMessageCountArgs,
      context: Optional[api_call_context.ApiCallContext] = None,
  ) -> api_client.ApiGetFleetspeakPendingMessageCountHandler:
    return api_client.ApiGetFleetspeakPendingMessageCountHandler()

  # Virtual file system methods.
  # ============================
  #
  def ListFiles(
      self,
      args: api_vfs_pb2.ApiListFilesArgs,
      context: Optional[api_call_context.ApiCallContext] = None,
  ) -> api_vfs.ApiListFilesHandler:
    return api_vfs.ApiListFilesHandler()

  def BrowseFilesystem(
      self,
      args: api_vfs_pb2.ApiBrowseFilesystemArgs,
      context: Optional[api_call_context.ApiCallContext] = None,
  ) -> api_vfs.ApiBrowseFilesystemHandler:
    return api_vfs.ApiBrowseFilesystemHandler()

  def GetVfsFilesArchive(
      self,
      args: api_vfs_pb2.ApiGetVfsFilesArchiveArgs,
      context: Optional[api_call_context.ApiCallContext] = None,
  ) -> api_vfs.ApiGetVfsFilesArchiveHandler:
    return api_vfs.ApiGetVfsFilesArchiveHandler()

  def GetFileDetails(
      self,
      args: api_vfs_pb2.ApiGetFileDetailsArgs,
      context: Optional[api_call_context.ApiCallContext] = None,
  ) -> api_vfs.ApiGetFileDetailsHandler:
    return api_vfs.ApiGetFileDetailsHandler()

  def GetFileText(
      self,
      args: api_vfs_pb2.ApiGetFileTextArgs,
      context: Optional[api_call_context.ApiCallContext] = None,
  ) -> api_vfs.ApiGetFileTextHandler:
    return api_vfs.ApiGetFileTextHandler()

  def GetFileBlob(
      self,
      args: api_vfs_pb2.ApiGetFileBlobArgs,
      context: Optional[api_call_context.ApiCallContext] = None,
  ) -> api_vfs.ApiGetFileBlobHandler:
    return api_vfs.ApiGetFileBlobHandler()

  def GetFileVersionTimes(
      self,
      args: api_vfs_pb2.ApiGetFileVersionTimesArgs,
      context: Optional[api_call_context.ApiCallContext] = None,
  ) -> api_vfs.ApiGetFileVersionTimesHandler:
    return api_vfs.ApiGetFileVersionTimesHandler()

  def GetFileDownloadCommand(
      self,
      args: api_vfs_pb2.ApiGetFileDownloadCommandArgs,
      context: Optional[api_call_context.ApiCallContext] = None,
  ) -> api_vfs.ApiGetFileDownloadCommandHandler:
    return api_vfs.ApiGetFileDownloadCommandHandler()

  def CreateVfsRefreshOperation(
      self,
      args: api_vfs_pb2.ApiCreateVfsRefreshOperationArgs,
      context: Optional[api_call_context.ApiCallContext] = None,
  ) -> api_vfs.ApiCreateVfsRefreshOperationHandler:
    return api_vfs.ApiCreateVfsRefreshOperationHandler()

  def GetVfsRefreshOperationState(
      self,
      args: api_vfs_pb2.ApiGetVfsRefreshOperationStateArgs,
      context: Optional[api_call_context.ApiCallContext] = None,
  ) -> api_vfs.ApiGetVfsRefreshOperationStateHandler:
    return api_vfs.ApiGetVfsRefreshOperationStateHandler()

  def GetVfsTimeline(
      self,
      args: api_vfs_pb2.ApiGetVfsTimelineArgs,
      context: Optional[api_call_context.ApiCallContext] = None,
  ) -> api_vfs.ApiGetVfsTimelineHandler:
    return api_vfs.ApiGetVfsTimelineHandler()

  def GetVfsTimelineAsCsv(
      self,
      args: api_vfs_pb2.ApiGetVfsTimelineAsCsvArgs,
      context: Optional[api_call_context.ApiCallContext] = None,
  ) -> api_vfs.ApiGetVfsTimelineAsCsvHandler:
    return api_vfs.ApiGetVfsTimelineAsCsvHandler()

  def UpdateVfsFileContent(
      self,
      args: api_vfs_pb2.ApiUpdateVfsFileContentArgs,
      context: Optional[api_call_context.ApiCallContext] = None,
  ) -> api_vfs.ApiUpdateVfsFileContentHandler:
    return api_vfs.ApiUpdateVfsFileContentHandler()

  def GetVfsFileContentUpdateState(
      self,
      args: api_vfs_pb2.ApiGetVfsFileContentUpdateStateArgs,
      context: Optional[api_call_context.ApiCallContext] = None,
  ) -> api_vfs.ApiGetVfsFileContentUpdateStateHandler:
    return api_vfs.ApiGetVfsFileContentUpdateStateHandler()

  # Clients labels methods.
  # ======================
  #
  def ListClientsLabels(self, args, context=None):
    return api_client.ApiListClientsLabelsHandler()

  def AddClientsLabels(
      self,
      args: api_client_pb2.ApiAddClientsLabelsArgs,
      context: Optional[api_call_context.ApiCallContext] = None,
  ) -> api_client.ApiAddClientsLabelsHandler:
    return api_client.ApiAddClientsLabelsHandler()

  def RemoveClientsLabels(
      self,
      args: api_client_pb2.ApiRemoveClientsLabelsArgs,
      context: Optional[api_call_context.ApiCallContext] = None,
  ) -> api_client.ApiRemoveClientsLabelsHandler:
    return api_client.ApiRemoveClientsLabelsHandler()

  # Clients flows methods.
  # =====================
  #
  def ListFlows(
      self,
      args: api_flow_pb2.ApiListFlowsArgs,
      context: Optional[api_call_context.ApiCallContext] = None,
  ):
    return api_flow.ApiListFlowsHandler()

  def GetFlow(
      self,
      args: api_flow_pb2.ApiGetFlowArgs,
      context: Optional[api_call_context.ApiCallContext] = None,
  ) -> api_flow.ApiGetFlowHandler:
    return api_flow.ApiGetFlowHandler()

  def CreateFlow(
      self,
      args: api_flow_pb2.ApiCreateFlowArgs,
      context: Optional[api_call_context.ApiCallContext] = None,
  ) -> api_flow.ApiCreateFlowHandler:
    return api_flow.ApiCreateFlowHandler()

  def CancelFlow(
      self,
      args: api_flow_pb2.ApiCancelFlowArgs,
      context: Optional[api_call_context.ApiCallContext] = None,
  ):
    return api_flow.ApiCancelFlowHandler()

  def ListFlowRequests(
      self,
      args: api_flow_pb2.ApiListFlowRequestsArgs,
      context: Optional[api_call_context.ApiCallContext] = None,
  ):
    return api_flow.ApiListFlowRequestsHandler()

  def ListFlowResults(
      self,
      args: api_flow_pb2.ApiListFlowResultsArgs,
      context: Optional[api_call_context.ApiCallContext] = None,
  ) -> api_flow.ApiListFlowResultsHandler:
    return api_flow.ApiListFlowResultsHandler()

  def GetExportedFlowResults(
      self,
      args: api_flow_pb2.ApiGetExportedFlowResultsArgs,
      context: Optional[api_call_context.ApiCallContext] = None,
  ) -> api_flow.ApiGetExportedFlowResultsHandler:
    return api_flow.ApiGetExportedFlowResultsHandler()

  def GetFlowResultsExportCommand(
      self,
      args: api_flow_pb2.ApiGetFlowResultsExportCommandArgs,
      context: Optional[api_call_context.ApiCallContext] = None,
  ) -> api_flow.ApiGetFlowResultsExportCommandHandler:
    return api_flow.ApiGetFlowResultsExportCommandHandler()

  def GetFlowFilesArchive(
      self,
      args: api_flow_pb2.ApiGetFlowFilesArchiveArgs,
      context: Optional[api_call_context.ApiCallContext] = None,
  ) -> api_flow.ApiGetFlowFilesArchiveHandler:
    return api_flow.ApiGetFlowFilesArchiveHandler()

  def ListFlowOutputPlugins(
      self,
      args: api_flow_pb2.ApiListFlowOutputPluginsArgs,
      context: Optional[api_call_context.ApiCallContext] = None,
  ):
    return api_flow.ApiListFlowOutputPluginsHandler()

  def ListFlowOutputPluginLogs(
      self,
      args: api_flow_pb2.ApiListFlowOutputPluginLogsArgs,
      context: Optional[api_call_context.ApiCallContext] = None,
  ):
    return api_flow.ApiListFlowOutputPluginLogsHandler()

  def ListFlowOutputPluginErrors(
      self,
      args: api_flow_pb2.ApiListFlowOutputPluginErrorsArgs,
      context: Optional[api_call_context.ApiCallContext] = None,
  ):
    return api_flow.ApiListFlowOutputPluginErrorsHandler()

  def ListAllFlowOutputPluginLogs(
      self,
      args: api_flow_pb2.ApiListAllFlowOutputPluginLogsArgs,
      context: Optional[api_call_context.ApiCallContext] = None,
  ):
    return api_flow.ApiListAllFlowOutputPluginLogsHandler()

  def ListFlowLogs(
      self,
      args: api_flow_pb2.ApiListFlowLogsArgs,
      context: Optional[api_call_context.ApiCallContext] = None,
  ) -> api_flow.ApiListFlowLogsHandler:
    return api_flow.ApiListFlowLogsHandler()

  def GetCollectedTimeline(
      self,
      args: api_timeline_pb2.ApiGetCollectedTimelineArgs,
      context: Optional[api_call_context.ApiCallContext] = None,
  ) -> api_timeline.ApiGetCollectedTimelineHandler:
    return api_timeline.ApiGetCollectedTimelineHandler()

  def UploadYaraSignature(
      self,
      args: api_yara_pb2.ApiUploadYaraSignatureArgs,
      context: Optional[api_call_context.ApiCallContext] = None,
  ) -> api_yara.ApiUploadYaraSignatureHandler:
    del args, context  # Unused.
    return api_yara.ApiUploadYaraSignatureHandler()

  def ExplainGlobExpression(
      self,
      args: api_flow_pb2.ApiExplainGlobExpressionArgs,
      context: Optional[api_call_context.ApiCallContext] = None,
  ) -> api_flow.ApiExplainGlobExpressionHandler:
    del args, context  # Unused.
    return api_flow.ApiExplainGlobExpressionHandler()

  def ScheduleFlow(
      self,
      args: api_flow_pb2.ApiCreateFlowArgs,
      context: Optional[api_call_context.ApiCallContext] = None,
  ) -> api_flow.ApiScheduleFlowHandler:
    return api_flow.ApiScheduleFlowHandler()

  def ListScheduledFlows(
      self,
      args: api_flow_pb2.ApiListScheduledFlowsArgs,
      context: Optional[api_call_context.ApiCallContext] = None,
  ) -> api_flow.ApiListScheduledFlowsHandler:
    return api_flow.ApiListScheduledFlowsHandler()

  def UnscheduleFlow(
      self,
      args: api_flow_pb2.ApiUnscheduleFlowArgs,
      context: Optional[api_call_context.ApiCallContext] = None,
  ) -> api_flow.ApiUnscheduleFlowHandler:
    return api_flow.ApiUnscheduleFlowHandler()

  def GetOsqueryResults(
      self,
      args: api_osquery_pb2.ApiGetOsqueryResultsArgs,
      context: Optional[api_call_context.ApiCallContext] = None,
  ):
    del args, context  # Unused.
    return api_osquery.ApiGetOsqueryResultsHandler()

  # Signed commands methods.
  # ========================
  #
  def ListSignedCommands(
      self,
      args: Optional[None] = None,
      context: Optional[api_call_context.ApiCallContext] = None,
  ) -> api_signed_commands.ApiListSignedCommandsHandler:
    return api_signed_commands.ApiListSignedCommandsHandler()

  # Cron jobs methods.
  # =================
  #
  def ListCronJobs(
      self,
      args: api_cron_pb2.ApiListCronJobsArgs,
      context: Optional[api_call_context.ApiCallContext] = None,
  ) -> api_cron.ApiListCronJobsHandler:
    return api_cron.ApiListCronJobsHandler()

  def CreateCronJob(
      self,
      args: api_cron_pb2.ApiCreateCronJobArgs,
      context: Optional[api_call_context.ApiCallContext] = None,
  ) -> api_cron.ApiCreateCronJobHandler:
    return api_cron.ApiCreateCronJobHandler()

  def GetCronJob(
      self,
      args: api_cron_pb2.ApiGetCronJobArgs,
      context: Optional[api_call_context.ApiCallContext] = None,
  ) -> api_cron.ApiGetCronJobHandler:
    return api_cron.ApiGetCronJobHandler()

  def ForceRunCronJob(
      self,
      args: api_cron_pb2.ApiForceRunCronJobArgs,
      context: Optional[api_call_context.ApiCallContext] = None,
  ) -> api_cron.ApiForceRunCronJobHandler:
    return api_cron.ApiForceRunCronJobHandler()

  def ModifyCronJob(
      self,
      args: api_cron_pb2.ApiModifyCronJobArgs,
      context: Optional[api_call_context.ApiCallContext] = None,
  ) -> api_cron.ApiModifyCronJobHandler:
    return api_cron.ApiModifyCronJobHandler()

  def ListCronJobRuns(
      self,
      args: api_cron_pb2.ApiListCronJobRunsArgs,
      context: Optional[api_call_context.ApiCallContext] = None,
  ) -> api_cron.ApiListCronJobRunsHandler:
    return api_cron.ApiListCronJobRunsHandler()

  def GetCronJobRun(
      self,
      args: api_cron_pb2.ApiGetCronJobRunArgs,
      context: Optional[api_call_context.ApiCallContext] = None,
  ) -> api_cron.ApiGetCronJobRunHandler:
    return api_cron.ApiGetCronJobRunHandler()

  def DeleteCronJob(
      self,
      args: api_cron_pb2.ApiDeleteCronJobArgs,
      context: Optional[api_call_context.ApiCallContext] = None,
  ) -> api_cron.ApiDeleteCronJobHandler:
    return api_cron.ApiDeleteCronJobHandler()

  # Hunts methods.
  # =============
  #
  def ListHunts(
      self,
      args: api_hunt_pb2.ApiListHuntsArgs,
      context: Optional[api_call_context.ApiCallContext] = None,
  ) -> api_hunt.ApiListHuntsHandler:
    return api_hunt.ApiListHuntsHandler()

  def VerifyHuntAccess(
      self,
      args: api_hunt_pb2.ApiVerifyHuntAccessArgs,
      context: Optional[api_call_context.ApiCallContext] = None,
  ) -> api_hunt.ApiVerifyHuntAccessHandler:
    return api_hunt.ApiVerifyHuntAccessHandler()

  def GetHunt(
      self,
      args: api_hunt_pb2.ApiGetHuntArgs,
      context: Optional[api_call_context.ApiCallContext] = None,
  ) -> api_hunt.ApiGetHuntHandler:
    return api_hunt.ApiGetHuntHandler()

  def ListHuntErrors(
      self,
      args: api_hunt_pb2.ApiListHuntErrorsArgs,
      context: Optional[api_call_context.ApiCallContext] = None,
  ) -> api_hunt.ApiListHuntErrorsHandler:
    return api_hunt.ApiListHuntErrorsHandler()

  def ListHuntLogs(
      self,
      args: api_hunt_pb2.ApiListHuntLogsArgs,
      context: Optional[api_call_context.ApiCallContext] = None,
  ) -> api_hunt.ApiListHuntLogsHandler:
    return api_hunt.ApiListHuntLogsHandler()

  def ListHuntResults(
      self,
      args: api_hunt_pb2.ApiListHuntResultsArgs,
      context: Optional[api_call_context.ApiCallContext] = None,
  ) -> api_hunt.ApiListHuntResultsHandler:
    return api_hunt.ApiListHuntResultsHandler()

  def CountHuntResultsByType(
      self,
      args: api_hunt_pb2.ApiCountHuntResultsByTypeArgs,
      context: Optional[api_call_context.ApiCallContext] = None,
  ) -> api_hunt.ApiCountHuntResultsByTypeHandler:
    return api_hunt.ApiCountHuntResultsByTypeHandler()

  def GetExportedHuntResults(
      self,
      args: api_hunt_pb2.ApiGetExportedHuntResultsArgs,
      context: Optional[api_call_context.ApiCallContext] = None,
  ) -> api_hunt.ApiGetExportedHuntResultsHandler:
    return api_hunt.ApiGetExportedHuntResultsHandler()

  def GetHuntResultsExportCommand(
      self,
      args: api_hunt_pb2.ApiGetHuntResultsExportCommandArgs,
      context: Optional[api_call_context.ApiCallContext] = None,
  ) -> api_hunt.ApiGetHuntResultsExportCommandHandler:
    return api_hunt.ApiGetHuntResultsExportCommandHandler()

  def ListHuntOutputPlugins(
      self,
      args: api_hunt_pb2.ApiListHuntOutputPluginsArgs,
      context: Optional[api_call_context.ApiCallContext] = None,
  ) -> api_hunt.ApiListHuntOutputPluginsHandler:
    return api_hunt.ApiListHuntOutputPluginsHandler()

  def ListHuntOutputPluginLogs(
      self,
      args: api_hunt_pb2.ApiListHuntOutputPluginLogsArgs,
      context: Optional[api_call_context.ApiCallContext] = None,
  ) -> api_hunt.ApiListHuntOutputPluginLogsHandler:
    return api_hunt.ApiListHuntOutputPluginLogsHandler()

  def ListHuntOutputPluginErrors(
      self,
      args: api_hunt_pb2.ApiListHuntOutputPluginErrorsArgs,
      context: Optional[api_call_context.ApiCallContext] = None,
  ) -> api_hunt.ApiListHuntOutputPluginErrorsHandler:
    return api_hunt.ApiListHuntOutputPluginErrorsHandler()

  def ListHuntCrashes(
      self,
      args: api_hunt_pb2.ApiListHuntCrashesArgs,
      context: Optional[api_call_context.ApiCallContext] = None,
  ) -> api_hunt.ApiListHuntCrashesHandler:
    return api_hunt.ApiListHuntCrashesHandler()

  def GetHuntClientCompletionStats(
      self,
      args: api_hunt_pb2.ApiGetHuntClientCompletionStatsArgs,
      context: Optional[api_call_context.ApiCallContext] = None,
  ) -> api_hunt.ApiGetHuntClientCompletionStatsHandler:
    return api_hunt.ApiGetHuntClientCompletionStatsHandler()

  def GetHuntStats(
      self,
      args: api_hunt_pb2.ApiGetHuntStatsArgs,
      context: Optional[api_call_context.ApiCallContext] = None,
  ) -> api_hunt.ApiGetHuntStatsHandler:
    return api_hunt.ApiGetHuntStatsHandler()

  def ListHuntClients(
      self,
      args: api_hunt_pb2.ApiListHuntClientsArgs,
      context: Optional[api_call_context.ApiCallContext] = None,
  ) -> api_hunt.ApiListHuntClientsHandler:
    return api_hunt.ApiListHuntClientsHandler()

  def GetHuntContext(
      self,
      args: api_hunt_pb2.ApiGetHuntContextArgs,
      context: Optional[api_call_context.ApiCallContext] = None,
  ) -> api_hunt.ApiGetHuntContextHandler:
    return api_hunt.ApiGetHuntContextHandler()

  def CreateHunt(
      self,
      args: api_hunt_pb2.ApiCreateHuntArgs,
      context: Optional[api_call_context.ApiCallContext] = None,
  ) -> api_hunt.ApiCreateHuntHandler:
    return api_hunt.ApiCreateHuntHandler()

  def ModifyHunt(
      self,
      args: api_hunt_pb2.ApiModifyHuntArgs,
      context: Optional[api_call_context.ApiCallContext] = None,
  ) -> api_hunt.ApiModifyHuntHandler:
    return api_hunt.ApiModifyHuntHandler()

  def DeleteHunt(
      self,
      args: api_hunt_pb2.ApiDeleteHuntArgs,
      context: Optional[api_call_context.ApiCallContext] = None,
  ) -> api_hunt.ApiDeleteHuntHandler:
    return api_hunt.ApiDeleteHuntHandler()

  def GetHuntFilesArchive(
      self,
      args: api_hunt_pb2.ApiGetHuntFilesArchiveArgs,
      context: Optional[api_call_context.ApiCallContext] = None,
  ) -> api_hunt.ApiGetHuntFilesArchiveHandler:
    return api_hunt.ApiGetHuntFilesArchiveHandler()

  def GetHuntFile(
      self,
      args: api_hunt_pb2.ApiGetHuntFileArgs,
      context: Optional[api_call_context.ApiCallContext] = None,
  ) -> api_hunt.ApiGetHuntFileHandler:
    return api_hunt.ApiGetHuntFileHandler()

  def GetCollectedHuntTimelines(
      self,
      args: api_timeline_pb2.ApiGetCollectedHuntTimelinesArgs,
      context: Optional[api_call_context.ApiCallContext] = None,
  ) -> api_timeline.ApiGetCollectedHuntTimelinesHandler:
    return api_timeline.ApiGetCollectedHuntTimelinesHandler()

  # Approvals methods.
  # =================
  #
  def CreateClientApproval(
      self,
      args: api_user_pb2.ApiCreateClientApprovalArgs,
      context: Optional[api_call_context.ApiCallContext] = None,
  ) -> api_user.ApiCreateClientApprovalHandler:
    return api_user.ApiCreateClientApprovalHandler()

  def GetClientApproval(
      self,
      args: api_user_pb2.ApiGetClientApprovalArgs,
      context: Optional[api_call_context.ApiCallContext] = None,
  ) -> api_user.ApiGetClientApprovalHandler:
    return api_user.ApiGetClientApprovalHandler()

  def GrantClientApproval(
      self,
      args: api_user_pb2.ApiGrantClientApprovalArgs,
      context: Optional[api_call_context.ApiCallContext] = None,
  ) -> api_user.ApiGrantClientApprovalHandler:
    return api_user.ApiGrantClientApprovalHandler()

  def ListClientApprovals(
      self,
      args: api_user_pb2.ApiListClientApprovalsArgs,
      context: Optional[api_call_context.ApiCallContext] = None,
  ) -> api_user.ApiListClientApprovalsHandler:
    return api_user.ApiListClientApprovalsHandler()

  def CreateHuntApproval(
      self,
      args: api_user_pb2.ApiCreateHuntApprovalArgs,
      context: Optional[api_call_context.ApiCallContext] = None,
  ) -> api_user.ApiCreateHuntApprovalHandler:
    return api_user.ApiCreateHuntApprovalHandler()

  def GetHuntApproval(
      self,
      args: api_user_pb2.ApiGetHuntApprovalArgs,
      context: Optional[api_call_context.ApiCallContext] = None,
  ) -> api_user.ApiGetHuntApprovalHandler:
    return api_user.ApiGetHuntApprovalHandler()

  def GrantHuntApproval(
      self,
      args: api_user_pb2.ApiGrantHuntApprovalArgs,
      context: Optional[api_call_context.ApiCallContext] = None,
  ) -> api_user.ApiGrantHuntApprovalHandler:
    return api_user.ApiGrantHuntApprovalHandler()

  def ListHuntApprovals(
      self,
      args: api_user_pb2.ApiListHuntApprovalsArgs,
      context: Optional[api_call_context.ApiCallContext] = None,
  ) -> api_user.ApiListHuntApprovalsHandler:
    return api_user.ApiListHuntApprovalsHandler()

  def CreateCronJobApproval(
      self,
      args: api_user_pb2.ApiCreateCronJobApprovalArgs,
      context: Optional[api_call_context.ApiCallContext] = None,
  ) -> api_user.ApiCreateCronJobApprovalHandler:
    return api_user.ApiCreateCronJobApprovalHandler()

  def GetCronJobApproval(
      self,
      args: api_user_pb2.ApiGetCronJobApprovalArgs,
      context: Optional[api_call_context.ApiCallContext] = None,
  ) -> api_user.ApiGetCronJobApprovalHandler:
    return api_user.ApiGetCronJobApprovalHandler()

  def GrantCronJobApproval(
      self,
      args: api_user_pb2.ApiGrantCronJobApprovalArgs,
      context: Optional[api_call_context.ApiCallContext] = None,
  ) -> api_user.ApiGrantCronJobApprovalHandler:
    return api_user.ApiGrantCronJobApprovalHandler()

  def ListCronJobApprovals(
      self,
      args: api_user_pb2.ApiListCronJobApprovalsArgs,
      context: Optional[api_call_context.ApiCallContext] = None,
  ) -> api_user.ApiListCronJobApprovalsHandler:
    return api_user.ApiListCronJobApprovalsHandler()

  def ListApproverSuggestions(
      self,
      args: api_user_pb2.ApiListApproverSuggestionsArgs,
      context: Optional[api_call_context.ApiCallContext] = None,
  ) -> api_user.ApiListApproverSuggestionsHandler:
    return api_user.ApiListApproverSuggestionsHandler()

  # User settings methods.
  # =====================
  #
  def GetPendingUserNotificationsCount(
      self,
      args: None,
      context: Optional[api_call_context.ApiCallContext] = None,
  ) -> api_user.ApiGetPendingUserNotificationsCountHandler:
    return api_user.ApiGetPendingUserNotificationsCountHandler()

  def ListPendingUserNotifications(
      self,
      args: api_user_pb2.ApiListPendingUserNotificationsArgs,
      context: Optional[api_call_context.ApiCallContext] = None,
  ) -> api_user.ApiListPendingUserNotificationsHandler:
    return api_user.ApiListPendingUserNotificationsHandler()

  def DeletePendingUserNotification(
      self,
      args: api_user_pb2.ApiDeletePendingUserNotificationArgs,
      context: Optional[api_call_context.ApiCallContext] = None,
  ) -> api_user.ApiDeletePendingUserNotificationHandler:
    return api_user.ApiDeletePendingUserNotificationHandler()

  def ListAndResetUserNotifications(
      self,
      args: api_user_pb2.ApiListAndResetUserNotificationsArgs,
      context: Optional[api_call_context.ApiCallContext] = None,
  ) -> api_user.ApiListAndResetUserNotificationsHandler:
    return api_user.ApiListAndResetUserNotificationsHandler()

  def GetGrrUser(
      self,
      args: None,
      context: Optional[api_call_context.ApiCallContext] = None,
  ):
    del args, context  # Unused.
    return api_user.ApiGetOwnGrrUserHandler(is_admin=True)

  def UpdateGrrUser(
      self,
      args: api_user_pb2.ApiGrrUser,
      context: Optional[api_call_context.ApiCallContext] = None,
  ) -> api_user.ApiUpdateGrrUserHandler:
    return api_user.ApiUpdateGrrUserHandler()

  # Config methods.
  # ==============
  #
  def GetConfig(self, args, context=None):
    return api_config.ApiGetConfigHandler()

  def GetConfigOption(
      self,
      args: api_config_pb2.ApiGetConfigOptionArgs,
      context: Optional[api_call_context.ApiCallContext] = None,
  ) -> api_config.ApiGetConfigOptionHandler:
    return api_config.ApiGetConfigOptionHandler()

  def ListGrrBinaries(
      self,
      args: api_config_pb2.ApiListGrrBinariesArgs,
      context: Optional[api_call_context.ApiCallContext] = None,
  ) -> api_config.ApiListGrrBinariesHandler:
    return api_config.ApiListGrrBinariesHandler()

  def GetGrrBinary(
      self,
      args: api_config_pb2.ApiGetGrrBinaryArgs,
      context: Optional[api_call_context.ApiCallContext] = None,
  ) -> api_config.ApiGetGrrBinaryHandler:
    return api_config.ApiGetGrrBinaryHandler()

  def GetGrrBinaryBlob(
      self,
      args: api_config_pb2.ApiGetGrrBinaryBlobArgs,
      context: Optional[api_call_context.ApiCallContext] = None,
  ) -> api_config.ApiGetGrrBinaryBlobHandler:
    return api_config.ApiGetGrrBinaryBlobHandler()

  def GetUiConfig(self, args, context=None):
    return api_config.ApiGetUiConfigHandler()

  # Reflection methods.
  # ==================
  #
  def ListKbFields(self, args, context=None):
    return api_client.ApiListKbFieldsHandler()

  def ListFlowDescriptors(self, args, context=None):
    # TODO(user): move to reflection.py
    return api_flow.ApiListFlowDescriptorsHandler()

  def ListOutputPluginDescriptors(self, args, context=None):
    return api_output_plugin.ApiListOutputPluginDescriptorsHandler()

  def ListApiMethods(self, args, context=None):
    return api_reflection.ApiListApiMethodsHandler(self)

  def GetGrrVersion(
      self,
      args: None,
      context: Optional[api_call_context.ApiCallContext] = None,
  ) -> api_metadata.ApiGetGrrVersionHandler:
    return api_metadata.ApiGetGrrVersionHandler()

  def GetOpenApiDescription(
      self,
      args: None,
      context: Optional[api_call_context.ApiCallContext] = None,
  ) -> api_metadata.ApiGetOpenApiDescriptionHandler:
    return api_metadata.ApiGetOpenApiDescriptionHandler(self)
