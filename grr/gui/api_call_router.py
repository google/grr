#!/usr/bin/env python
"""Router classes route API requests to particular handlers."""



import inspect


from grr.gui.api_plugins import artifact as api_artifact
from grr.gui.api_plugins import client as api_client
from grr.gui.api_plugins import config as api_config
from grr.gui.api_plugins import cron as api_cron
from grr.gui.api_plugins import flow as api_flow
from grr.gui.api_plugins import hunt as api_hunt
from grr.gui.api_plugins import reflection as api_reflection
from grr.gui.api_plugins import stats as api_stats
from grr.gui.api_plugins import user as api_user
from grr.gui.api_plugins import vfs as api_vfs

from grr.lib import registry


class Http(object):
  """Decorator that associates URLs with API methods."""

  def __init__(self, method, path):
    self.method = method
    self.path = path

  def __call__(self, func):
    try:
      http_methods = getattr(func, "__http_methods__")
    except AttributeError:
      http_methods = []
      setattr(func, "__http_methods__", http_methods)

    http_methods.append((self.method,
                         self.path,))

    return func


class ArgsType(object):
  """Decorator that specifies the args type of an API method."""

  def __init__(self, args_type):
    self.args_type = args_type

  def __call__(self, func):
    func.__args_type__ = self.args_type
    return func


class ResultType(object):
  """Decorator that specifies the result type of an API method."""

  def __init__(self, result_type):
    self.result_type = result_type

  def __call__(self, func):
    func.__result_type__ = self.result_type
    return func


class ResultBinaryStream(object):
  """Decorator indicating this API methods will produce a binary stream."""

  def __call__(self, func):
    func.__result_type__ = RouterMethodMetadata.BINARY_STREAM_RESULT_TYPE
    return func


class Category(object):
  """Decorator that specifies the category of an API method."""

  def __init__(self, category):
    self.category = category

  def __call__(self, func):
    func.__category__ = self.category
    return func


class RouterMethodMetadata(object):
  """Data object for metadata about router methods."""

  BINARY_STREAM_RESULT_TYPE = "BinaryStream"

  def __init__(self,
               name,
               args_type=None,
               result_type=None,
               category=None,
               http_methods=None):
    self.name = name
    self.args_type = args_type
    self.result_type = result_type
    self.category = category
    self.http_methods = http_methods or set()


class ApiCallRouter(object):
  """Routers do ACL checks and route API requests to handlers."""

  __metaclass__ = registry.MetaclassRegistry
  __abstract = True  # pylint: disable=g-bad-name

  @classmethod
  def GetAnnotatedMethods(cls):
    """Returns a dictionary of annotated router methods."""

    result = {}

    for i_cls in inspect.getmro(cls):
      for name in dir(i_cls):
        cls_method = getattr(i_cls, name)

        if not callable(cls_method):
          continue

        if not hasattr(cls_method, "__http_methods__"):
          continue

        result[name] = RouterMethodMetadata(
            name=name,
            args_type=getattr(cls_method, "__args_type__", None),
            result_type=getattr(cls_method, "__result_type__", None),
            category=getattr(cls_method, "__category__", None),
            http_methods=getattr(cls_method, "__http_methods__", set()))

    return result

  # Artifacts methods.
  # =================
  #
  @Category("Artifacts")
  @ArgsType(api_artifact.ApiListArtifactsArgs)
  @ResultType(api_artifact.ApiListArtifactsResult)
  @Http("GET", "/api/artifacts")
  def ListArtifacts(self, args, token=None):
    raise NotImplementedError()

  @Category("Artifacts")
  @ArgsType(api_artifact.ApiUploadArtifactArgs)
  @Http("POST", "/api/artifacts/upload")
  def UploadArtifact(self, args, token=None):
    raise NotImplementedError()

  @Category("Artifacts")
  @ArgsType(api_artifact.ApiDeleteArtifactsArgs)
  @Http("POST", "/api/artifacts/delete")
  def DeleteArtifacts(self, args, token=None):
    raise NotImplementedError()

  # Clients methods.
  # ===============
  #
  @Category("Clients")
  @ArgsType(api_client.ApiSearchClientsArgs)
  @ResultType(api_client.ApiSearchClientsResult)
  @Http("GET", "/api/clients")
  def SearchClients(self, args, token=None):
    raise NotImplementedError()

  @Category("Clients")
  @ArgsType(api_client.ApiGetClientArgs)
  @ResultType(api_client.ApiGetClientResult)
  @Http("GET", "/api/clients/<client_id>")
  def GetClient(self, args, token=None):
    raise NotImplementedError()

  @Category("Clients")
  @ArgsType(api_client.ApiGetClientVersionTimesArgs)
  @ResultType(api_client.ApiGetClientVersionTimesResult)
  @Http("GET", "/api/clients/<client_id>/version-times")
  def GetClientVersionTimes(self, args, token=None):
    raise NotImplementedError()

  @Category("Clients")
  @ArgsType(api_client.ApiInterrogateClientArgs)
  @ResultType(api_client.ApiInterrogateClientResult)
  @Http("POST", "/api/clients/<client_id>/actions/interrogate")
  def InterrogateClient(self, args, token=None):
    raise NotImplementedError()

  @Category("Clients")
  @ArgsType(api_client.ApiGetInterrogateOperationStateArgs)
  @ResultType(api_client.ApiGetInterrogateOperationStateResult)
  @Http("GET",
        "/api/clients/<client_id>/actions/interrogate/<path:operation_id>")
  def GetInterrogateOperationState(self, args, token=None):
    raise NotImplementedError()

  @ArgsType(api_client.ApiGetLastClientIPAddressArgs)
  @ResultType(api_client.ApiGetLastClientIPAddressResult)
  @Http("GET", "/api/clients/<client_id>/last-ip")
  def GetLastClientIPAddress(self, args, token=None):
    raise NotImplementedError()

  # Virtual file system methods.
  # ===========================
  #
  @Category("Vfs")
  @ArgsType(api_vfs.ApiListFilesArgs)
  @ResultType(api_vfs.ApiListFilesResult)
  @Http("GET", "/api/clients/<client_id>/vfs-index/")
  @Http("GET", "/api/clients/<client_id>/vfs-index/<path:file_path>")
  def ListFiles(self, args, token=None):
    # This method can be called with or without file_path argument and returns
    # the root files for the given client in the latter case.
    # To allow optional url arguments, two url patterns need to be specified.
    raise NotImplementedError()

  @Category("Vfs")
  @ArgsType(api_vfs.ApiGetFileDetailsArgs)
  @ResultType(api_vfs.ApiGetFileDetailsResult)
  @Http("GET", "/api/clients/<client_id>/vfs-details/<path:file_path>")
  def GetFileDetails(self, args, token=None):
    raise NotImplementedError()

  @Category("Vfs")
  @ArgsType(api_vfs.ApiGetFileTextArgs)
  @ResultType(api_vfs.ApiGetFileTextResult)
  @Http("GET", "/api/clients/<client_id>/vfs-text/<path:file_path>")
  def GetFileText(self, args, token=None):
    raise NotImplementedError()

  @Category("Vfs")
  @ArgsType(api_vfs.ApiGetFileBlobArgs)
  @ResultBinaryStream()
  @Http("GET", "/api/clients/<client_id>/vfs-blob/<path:file_path>")
  def GetFileBlob(self, args, token=None):
    raise NotImplementedError()

  @Category("Vfs")
  @ArgsType(api_vfs.ApiGetFileVersionTimesArgs)
  @ResultType(api_vfs.ApiGetFileVersionTimesResult)
  @Http("GET", "/api/clients/<client_id>/vfs-version-times/<path:file_path>")
  def GetFileVersionTimes(self, args, token=None):
    raise NotImplementedError()

  @Category("Vfs")
  @ArgsType(api_vfs.ApiGetFileDownloadCommandArgs)
  @ResultType(api_vfs.ApiGetFileDownloadCommandResult)
  @Http("GET", "/api/clients/<client_id>/vfs-download-command/<path:file_path>")
  def GetFileDownloadCommand(self, args, token=None):
    raise NotImplementedError()

  @Category("Vfs")
  @ArgsType(api_vfs.ApiCreateVfsRefreshOperationArgs)
  @ResultType(api_vfs.ApiCreateVfsRefreshOperationResult)
  @Http("POST", "/api/clients/<client_id>/vfs-refresh-operations")
  def CreateVfsRefreshOperation(self, args, token=None):
    raise NotImplementedError()

  @Category("Vfs")
  @ArgsType(api_vfs.ApiGetVfsRefreshOperationStateArgs)
  @ResultType(api_vfs.ApiGetVfsRefreshOperationStateResult)
  @Http("GET",
        "/api/clients/<client_id>/vfs-refresh-operations/<path:operation_id>")
  def GetVfsRefreshOperationState(self, args, token=None):
    raise NotImplementedError()

  @Category("Vfs")
  @ArgsType(api_vfs.ApiGetVfsTimelineArgs)
  @ResultType(api_vfs.ApiGetVfsTimelineResult)
  @Http("GET", "/api/clients/<client_id>/vfs-timeline/<path:file_path>")
  def GetVfsTimeline(self, args, token=None):
    raise NotImplementedError()

  @Category("Vfs")
  @ArgsType(api_vfs.ApiGetVfsTimelineAsCsvArgs)
  @ResultBinaryStream()
  @Http("GET", "/api/clients/<client_id>/vfs-timeline-csv/<path:file_path>")
  def GetVfsTimelineAsCsv(self, args, token=None):
    raise NotImplementedError()

  @Category("Vfs")
  @ArgsType(api_vfs.ApiUpdateVfsFileContentArgs)
  @ResultType(api_vfs.ApiUpdateVfsFileContentResult)
  @Http("POST", "/api/clients/<client_id>/vfs-update")
  def UpdateVfsFileContent(self, args, token=None):
    raise NotImplementedError()

  @Category("Vfs")
  @ArgsType(api_vfs.ApiGetVfsFileContentUpdateStateArgs)
  @ResultType(api_vfs.ApiGetVfsFileContentUpdateStateResult)
  @Http("GET", "/api/clients/<client_id>/vfs-update/<path:operation_id>")
  def GetVfsFileContentUpdateState(self, args, token=None):
    raise NotImplementedError()

  # Clients labels methods.
  # ======================
  #
  @Category("Clients")
  @ResultType(api_client.ApiListClientsLabelsResult)
  @Http("GET", "/api/clients/labels")
  def ListClientsLabels(self, args, token=None):
    raise NotImplementedError()

  @Category("Clients")
  @ArgsType(api_client.ApiAddClientsLabelsArgs)
  @Http("POST", "/api/clients/labels/add")
  def AddClientsLabels(self, args, token=None):
    raise NotImplementedError()

  @Category("Clients")
  @ArgsType(api_client.ApiRemoveClientsLabelsArgs)
  @Http("POST", "/api/clients/labels/remove")
  def RemoveClientsLabels(self, args, token=None):
    raise NotImplementedError()

  # Clients flows methods.
  # =====================
  #
  @Category("Flows")
  @ArgsType(api_flow.ApiListFlowsArgs)
  @ResultType(api_flow.ApiListFlowsResult)
  @Http("GET", "/api/clients/<client_id>/flows")
  def ListFlows(self, args, token=None):
    raise NotImplementedError()

  @Category("Flows")
  @ArgsType(api_flow.ApiGetFlowArgs)
  @ResultType(api_flow.ApiFlow)
  @Http("GET", "/api/clients/<client_id>/flows/<flow_id>")
  def GetFlow(self, args, token=None):
    raise NotImplementedError()

  # Note: handles both client and globals flows. It's cleaner to have
  # a separate API for global flows.
  @Category("Flows")
  @ArgsType(api_flow.ApiCreateFlowArgs)
  @ResultType(api_flow.ApiFlow)
  @Http("POST", "/api/clients/<client_id>/flows")
  # TODO(user): deprecate this URL
  @Http("POST", "/api/clients/<client_id>/flows/start")
  def CreateFlow(self, args, token=None):
    raise NotImplementedError()

  @Category("Flows")
  @ArgsType(api_flow.ApiCancelFlowArgs)
  @Http("POST", "/api/clients/<client_id>/flows/<flow_id>/actions/cancel")
  def CancelFlow(self, args, token=None):
    raise NotImplementedError()

  @Category("Flows")
  @ArgsType(api_flow.ApiListFlowResultsArgs)
  @ResultType(api_flow.ApiListFlowResultsResult)
  @Http("GET", "/api/clients/<client_id>/flows/<flow_id>/results")
  def ListFlowResults(self, args, token=None):
    raise NotImplementedError()

  @Category("Flows")
  @ArgsType(api_flow.ApiGetFlowResultsExportCommandArgs)
  @ResultType(api_flow.ApiGetFlowResultsExportCommandResult)
  @Http("GET", "/api/clients/<client_id>/flows/<flow_id>/results/"
        "export-command")
  def GetFlowResultsExportCommand(self, args, token=None):
    raise NotImplementedError()

  @Category("Flows")
  @ArgsType(api_flow.ApiGetFlowFilesArchiveArgs)
  @ResultBinaryStream()
  @Http("GET", "/api/clients/<client_id>/flows/<flow_id>/results/"
        "files-archive")
  def GetFlowFilesArchive(self, args, token=None):
    raise NotImplementedError()

  @Category("Flows")
  @ArgsType(api_flow.ApiListFlowOutputPluginsArgs)
  @ResultType(api_flow.ApiListFlowOutputPluginsResult)
  @Http("GET", "/api/clients/<client_id>/flows/<flow_id>/output-plugins")
  def ListFlowOutputPlugins(self, args, token=None):
    raise NotImplementedError()

  @Category("Flows")
  @ArgsType(api_flow.ApiListFlowOutputPluginLogsArgs)
  @ResultType(api_flow.ApiListFlowOutputPluginLogsResult)
  @Http("GET", "/api/clients/<client_id>/flows/<flow_id>/"
        "output-plugins/<plugin_id>/logs")
  def ListFlowOutputPluginLogs(self, args, token=None):
    raise NotImplementedError()

  @Category("Flows")
  @ArgsType(api_flow.ApiListFlowOutputPluginErrorsArgs)
  @ResultType(api_flow.ApiListFlowOutputPluginErrorsResult)
  @Http("GET", "/api/clients/<client_id>/flows/<flow_id>/"
        "output-plugins/<plugin_id>/errors")
  def ListFlowOutputPluginErrors(self, args, token=None):
    raise NotImplementedError()

  @Category("Flows")
  @ArgsType(api_flow.ApiListFlowLogsArgs)
  @ResultType(api_flow.ApiListFlowLogsResult)
  @Http("GET", "/api/clients/<client_id>/flows/<flow_id>/log")
  def ListFlowLogs(self, args, token=None):
    raise NotImplementedError()

  # Global flows methods.
  # ====================
  #
  @Category("Flows")
  @ArgsType(api_flow.ApiCreateFlowArgs)
  @ResultType(api_flow.ApiFlow)
  @Http("POST", "/api/flows")
  def CreateGlobalFlow(self, args, token=None):
    raise NotImplementedError()

  # Cron jobs methods.
  # =================
  #
  @Category("Cron")
  @ArgsType(api_cron.ApiListCronJobsArgs)
  @ResultType(api_cron.ApiListCronJobsResult)
  @Http("GET", "/api/cron-jobs")
  def ListCronJobs(self, args, token=None):
    raise NotImplementedError()

  @Category("Cron")
  @ArgsType(api_cron.ApiCronJob)
  @ResultType(api_cron.ApiCronJob)
  @Http("POST", "/api/cron-jobs")
  def CreateCronJob(self, args, token=None):
    raise NotImplementedError()

  @Category("Cron")
  @ArgsType(api_cron.ApiDeleteCronJobArgs)
  @Http("POST", "/api/cron-jobs/<cron_job_id>/actions/delete")
  def DeleteCronJob(self, args, token=None):
    raise NotImplementedError()

  # Hunts methods.
  # =============
  #
  @Category("Hunts")
  @ArgsType(api_hunt.ApiListHuntsArgs)
  @ResultType(api_hunt.ApiListHuntsResult)
  @Http("GET", "/api/hunts")
  def ListHunts(self, args, token=None):
    raise NotImplementedError()

  @Category("Hunts")
  @ArgsType(api_hunt.ApiGetHuntArgs)
  @ResultType(api_hunt.ApiHunt)
  @Http("GET", "/api/hunts/<hunt_id>")
  def GetHunt(self, args, token=None):
    raise NotImplementedError()

  @Category("Hunts")
  @ArgsType(api_hunt.ApiListHuntErrorsArgs)
  @ResultType(api_hunt.ApiListHuntErrorsResult)
  @Http("GET", "/api/hunts/<hunt_id>/errors")
  def ListHuntErrors(self, args, token=None):
    raise NotImplementedError()

  @Category("Hunts")
  @ArgsType(api_hunt.ApiListHuntLogsArgs)
  @ResultType(api_hunt.ApiListHuntLogsResult)
  # TODO(user): change "log" to "logs"
  @Http("GET", "/api/hunts/<hunt_id>/log")
  def ListHuntLogs(self, args, token=None):
    raise NotImplementedError()

  @Category("Hunts")
  @ArgsType(api_hunt.ApiListHuntResultsArgs)
  @ResultType(api_hunt.ApiListHuntResultsResult)
  @Http("GET", "/api/hunts/<hunt_id>/results")
  def ListHuntResults(self, args, token=None):
    raise NotImplementedError()

  @Category("Hunts")
  @ArgsType(api_hunt.ApiGetHuntResultsExportCommandArgs)
  @ResultType(api_hunt.ApiGetHuntResultsExportCommandResult)
  @Http("GET", "/api/hunts/<hunt_id>/results/export-command")
  def GetHuntResultsExportCommand(self, args, token=None):
    raise NotImplementedError()

  @Category("Hunts")
  @ArgsType(api_hunt.ApiListHuntOutputPluginsArgs)
  @ResultType(api_hunt.ApiListHuntOutputPluginsResult)
  @Http("GET", "/api/hunts/<hunt_id>/output-plugins")
  def ListHuntOutputPlugins(self, args, token=None):
    raise NotImplementedError()

  @Category("Hunts")
  @ArgsType(api_hunt.ApiListHuntOutputPluginLogsArgs)
  @ResultType(api_hunt.ApiListHuntOutputPluginLogsResult)
  @Http("GET", "/api/hunts/<hunt_id>/output-plugins/<plugin_id>/logs")
  def ListHuntOutputPluginLogs(self, args, token=None):
    raise NotImplementedError()

  @Category("Hunts")
  @ArgsType(api_hunt.ApiListHuntOutputPluginErrorsArgs)
  @ResultType(api_hunt.ApiListHuntOutputPluginErrorsResult)
  @Http("GET", "/api/hunts/<hunt_id>/output-plugins/<plugin_id>/errors")
  def ListHuntOutputPluginErrors(self, args, token=None):
    raise NotImplementedError()

  @Category("Hunts")
  @ArgsType(api_hunt.ApiListHuntCrashesArgs)
  @ResultType(api_hunt.ApiListHuntCrashesResult)
  @Http("GET", "/api/hunts/<hunt_id>/crashes")
  def ListHuntCrashes(self, args, token=None):
    raise NotImplementedError()

  @Category("Hunts")
  @ArgsType(api_hunt.ApiGetHuntClientCompletionStatsArgs)
  @ResultType(api_hunt.ApiGetHuntClientCompletionStatsResult)
  @Http("GET", "/api/hunts/<hunt_id>/client-completion-stats")
  def GetHuntClientCompletionStats(self, args, token=None):
    raise NotImplementedError()

  @Category("Hunts")
  @ArgsType(api_hunt.ApiGetHuntStatsArgs)
  @ResultType(api_hunt.ApiGetHuntStatsResult)
  @Http("GET", "/api/hunts/<hunt_id>/stats")
  def GetHuntStats(self, args, token=None):
    raise NotImplementedError()

  @Category("Hunts")
  @ArgsType(api_hunt.ApiListHuntClientsArgs)
  @ResultType(api_hunt.ApiListHuntClientsResult)
  @Http("GET", "/api/hunts/<hunt_id>/clients/<client_status>")
  def ListHuntClients(self, args, token=None):
    raise NotImplementedError()

  @Category("Hunts")
  @ArgsType(api_hunt.ApiGetHuntContextArgs)
  @ResultType(api_hunt.ApiGetHuntContextResult)
  @Http("GET", "/api/hunts/<hunt_id>/context")
  def GetHuntContext(self, args, token=None):
    raise NotImplementedError()

  @Category("Hunts")
  @ArgsType(api_hunt.ApiCreateHuntArgs)
  @ResultType(api_hunt.ApiHunt)
  @Http("POST", "/api/hunts")
  # TODO(user): deprecate old URL
  @Http("POST", "/api/hunts/create")
  def CreateHunt(self, args, token=None):
    raise NotImplementedError()

  @Category("Hunts")
  @ArgsType(api_hunt.ApiGetHuntFilesArchiveArgs)
  @ResultBinaryStream()
  @Http("GET", "/api/hunts/<hunt_id>/results/files-archive")
  def GetHuntFilesArchive(self, args, token=None):
    raise NotImplementedError()

  @Category("Hunts")
  @ArgsType(api_hunt.ApiGetHuntFileArgs)
  @ResultBinaryStream()
  @Http("GET",
        "/api/hunts/<hunt_id>/results/clients/<client_id>/fs/<path:vfs_path>")
  def GetHuntFile(self, args, token=None):
    raise NotImplementedError()

  # Stats metrics methods.
  # =====================
  #
  @Category("Other")
  @ArgsType(api_stats.ApiListStatsStoreMetricsMetadataArgs)
  @Http("GET", "/api/stats/store/<component>/metadata")
  def ListStatsStoreMetricsMetadata(self, args, token=None):
    raise NotImplementedError()

  @Category("Other")
  @Http("GET", "/api/stats/store/<component>/metrics/<metric_name>")
  @ArgsType(api_stats.ApiGetStatsStoreMetricArgs)
  def GetStatsStoreMetric(self, args, token=None):
    raise NotImplementedError()

  # Approvals methods.
  # =================
  #
  @Category("User")
  @ArgsType(api_user.ApiCreateUserClientApprovalArgs)
  @ResultType(api_user.ApiUserClientApproval)
  @Http("POST", "/api/users/me/approvals/client/<client_id>")
  def CreateUserClientApproval(self, args, token=None):
    raise NotImplementedError()

  @Category("User")
  @ArgsType(api_user.ApiGetUserClientApprovalArgs)
  @ResultType(api_user.ApiUserClientApproval)
  @Http("GET", "/api/users/me/approvals/client/<client_id>/<reason>")
  def GetUserClientApproval(self, args, token=None):
    raise NotImplementedError()

  @Category("User")
  @ArgsType(api_user.ApiListUserClientApprovalsArgs)
  @ResultType(api_user.ApiListUserClientApprovalsResult)
  @Http("GET", "/api/users/me/approvals/client")
  @Http("GET", "/api/users/me/approvals/client/<client_id>")
  def ListUserClientApprovals(self, args, token=None):
    raise NotImplementedError()

  @Category("User")
  @ArgsType(api_user.ApiListUserHuntApprovalsArgs)
  @ResultType(api_user.ApiListUserHuntApprovalsResult)
  @Http("GET", "/api/users/me/approvals/hunt")
  def ListUserHuntApprovals(self, args, token=None):
    raise NotImplementedError()

  @Category("User")
  @ArgsType(api_user.ApiListUserCronApprovalsArgs)
  @ResultType(api_user.ApiListUserCronApprovalsResult)
  @Http("GET", "/api/users/me/approvals/cron")
  def ListUserCronApprovals(self, args, token=None):
    raise NotImplementedError()

  # User settings methods.
  # =====================
  #
  @Category("User")
  @ResultType(api_user.ApiGetPendingUserNotificationsCountResult)
  @Http("GET", "/api/users/me/notifications/pending/count")
  def GetPendingUserNotificationsCount(self, args, token=None):
    raise NotImplementedError()

  @Category("User")
  @ArgsType(api_user.ApiListPendingUserNotificationsArgs)
  @ResultType(api_user.ApiListPendingUserNotificationsResult)
  @Http("GET", "/api/users/me/notifications/pending")
  def ListPendingUserNotifications(self, args, token=None):
    raise NotImplementedError()

  @Category("User")
  @ArgsType(api_user.ApiDeletePendingUserNotificationArgs)
  @Http("DELETE", "/api/users/me/notifications/pending/<timestamp>")
  def DeletePendingUserNotification(self, args, token=None):
    raise NotImplementedError()

  @Category("User")
  @ArgsType(api_user.ApiListAndResetUserNotificationsArgs)
  @ResultType(api_user.ApiListAndResetUserNotificationsResult)
  @Http("POST", "/api/users/me/notifications")
  def ListAndResetUserNotifications(self, args, token=None):
    raise NotImplementedError()

  @Category("User")
  @ResultType(api_user.ApiGrrUser)
  @Http("GET", "/api/users/me")
  def GetGrrUser(self, args, token=None):
    raise NotImplementedError()

  @Category("User")
  @ArgsType(api_user.ApiGrrUser)
  @Http("POST", "/api/users/me")
  def UpdateGrrUser(self, args, token=None):
    raise NotImplementedError()

  @Category("User")
  @ResultType(api_user.ApiListPendingGlobalNotificationsResult)
  @Http("GET", "/api/users/me/notifications/pending/global")
  def ListPendingGlobalNotifications(self, args, token=None):
    raise NotImplementedError()

  @Category("User")
  @ArgsType(api_user.ApiDeletePendingGlobalNotificationArgs)
  @Http("DELETE", "/api/users/me/notifications/pending/global/<type>")
  def DeletePendingGlobalNotification(self, args, token=None):
    raise NotImplementedError()

  # Config methods.
  # ==============
  #
  @Category("Settings")
  @ResultType(api_config.ApiGetConfigResult)
  @Http("GET", "/api/config")
  def GetConfig(self, args, token=None):
    raise NotImplementedError()

  @Category("Settings")
  @ArgsType(api_config.ApiGetConfigOptionArgs)
  @ResultType(api_config.ApiConfigOption)
  @Http("GET", "/api/config/<name>")
  def GetConfigOption(self, args, token=None):
    raise NotImplementedError()

  # Reflection methods.
  # ==================
  #
  @Category("Reflection")
  @ResultType(api_client.ApiListKbFieldsResult)
  @Http("GET", "/api/clients/kb-fields")
  def ListKbFields(self, args, token=None):
    raise NotImplementedError()

  @Category("Reflection")
  @ArgsType(api_flow.ApiListFlowDescriptorsArgs)
  @ResultType(api_flow.ApiListFlowDescriptorsResult)
  @Http("GET", "/api/flows/descriptors")
  def ListFlowDescriptors(self, args, token=None):
    raise NotImplementedError()

  @Category("Reflection")
  @Http("GET", "/api/reflection/aff4/attributes")
  def ListAff4AttributeDescriptors(self, args, token=None):
    raise NotImplementedError()

  @Category("Reflection")
  @ArgsType(api_reflection.ApiGetRDFValueDescriptorArgs)
  @Http("GET", "/api/reflection/rdfvalue/<type>")
  def GetRDFValueDescriptor(self, args, token=None):
    raise NotImplementedError()

  @Category("Reflection")
  @Http("GET", "/api/reflection/rdfvalue/all")
  def ListRDFValuesDescriptors(self, args, token=None):
    raise NotImplementedError()

  # Note: fix the name in ApiOutputPluginsListHandler
  @Category("Reflection")
  @Http("GET", "/api/output-plugins/all")
  def ListOutputPluginDescriptors(self, args, token=None):
    raise NotImplementedError()

  @Category("Reflection")
  @ResultType(api_vfs.ApiListKnownEncodingsResult)
  @Http("GET", "/api/reflection/file-encodings")
  def ListKnownEncodings(self, args, token=None):
    raise NotImplementedError()

  # Documentation methods.
  # =====================
  #
  @Category("Other")
  @Http("GET", "/api/docs")
  def GetDocs(self, args, token=None):
    raise NotImplementedError()

  # Robot methods (methods that provide limited access to the system and
  # are supposed to be triggered by the scripts).
  # ====================================================================
  #
  @Category("Flows")
  @ArgsType(api_flow.ApiStartRobotGetFilesOperationArgs)
  @ResultType(api_flow.ApiStartRobotGetFilesOperationResult)
  @Http("POST", "/api/robot-actions/get-files")
  def StartRobotGetFilesOperation(self, args, token=None):
    raise NotImplementedError()

  @Category("Flows")
  @ArgsType(api_flow.ApiGetRobotGetFilesOperationStateArgs)
  @ResultType(api_flow.ApiGetRobotGetFilesOperationStateResult)
  @Http("GET", "/api/robot-actions/get-files/<path:operation_id>")
  def GetRobotGetFilesOperationState(self, args, token=None):
    raise NotImplementedError()


class DisabledApiCallRouter(ApiCallRouter):
  pass
