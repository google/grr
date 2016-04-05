#!/usr/bin/env python
"""Router classes route API requests to particular handlers."""



import inspect


from grr.gui import api_aff4_object_renderers
from grr.gui.api_plugins import aff4 as api_aff4
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

from grr.lib.aff4_objects import users as aff4_users


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

    http_methods.append((self.method, self.path,))

    return func


class ArgsType(object):
  """Decorator that specifies the args type of an API method."""

  def __init__(self, args_type):
    self.args_type = args_type

  def __call__(self, func):
    func.__args_type__ = self.args_type
    return func


class AdditionalArgsTypes(object):
  """Decorator that specific additional args type of an API method."""

  def __init__(self, additional_args_types):
    self.additional_args_types = additional_args_types

  def __call__(self, func):
    func.__additional_args_types__ = self.additional_args_types
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

  def __init__(self, name, args_type=None, additional_args_types=None,
               result_type=None, category=None, http_methods=None):
    self.name = name
    self.args_type = args_type
    self.additional_args_types = additional_args_types
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
            additional_args_types=getattr(
                cls_method, "__additional_args_types__", None),
            result_type=getattr(cls_method, "__result_type__", None),
            category=getattr(cls_method, "__category__", None),
            http_methods=getattr(cls_method, "__http_methods__", set()))

    return result

  # AFF4 access methods.
  # ===================
  #
  # NOTE: These are likely to be deprecated soon in favor
  # of more narrow-scoped VFS access methods.
  @Category("AFF4")
  @ArgsType(api_aff4.ApiGetAff4ObjectArgs)
  @AdditionalArgsTypes({
      "RDFValueCollection":
      api_aff4_object_renderers.ApiRDFValueCollectionRendererArgs})
  @Http("GET", "/api/aff4/<path:aff4_path>")
  def GetAff4Object(self, args, token=None):
    raise NotImplementedError()

  @Category("AFF4")
  @ArgsType(api_aff4.ApiGetAff4IndexArgs)
  @Http("GET", "/api/aff4-index/<path:aff4_path>")
  def GetAff4Index(self, args, token=None):
    raise NotImplementedError()

  # Artifacts methods.
  # =================
  #
  @Category("Artifacts")
  @ArgsType(api_artifact.ApiListArtifactsArgs)
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
  @ResultType(api_client.ApiClient)
  @Http("GET", "/api/clients/<client_id>")
  def GetClient(self, args, token=None):
    raise NotImplementedError()

  # Virtual file system methods.
  # ===========================
  #
  @Category("Vfs")
  @ArgsType(api_vfs.ApiGetFileDetailsArgs)
  @ResultType(api_vfs.ApiGetFileDetailsResult)
  @Http("GET", "/api/clients/<client_id>/vfs-details/<path:file_path>")
  def GetFileDetails(self, args, token=None):
    raise NotImplementedError()

  @Category("Vfs")
  @ArgsType(api_vfs.ApiGetFileListArgs)
  @ResultType(api_vfs.ApiGetFileListResult)
  @Http("GET", "/api/clients/<client_id>/vfs-index/")
  @Http("GET", "/api/clients/<client_id>/vfs-index/<path:file_path>")
  def GetFileList(self, args, token=None):
    # This method can be called with or without file_path argument and returns
    # the root files for the given client in the latter case.
    # To allow optional url arguments, two url patterns need to be specified.
    raise NotImplementedError()

  @Category("Vfs")
  @ArgsType(api_vfs.ApiGetFileTextArgs)
  @ResultType(api_vfs.ApiGetFileTextResult)
  @Http("GET", "/api/clients/<client_id>/vfs-text/<path:file_path>")
  def GetFileText(self, args, token=None):
    raise NotImplementedError()

  @Category("Vfs")
  @ArgsType(api_vfs.ApiGetFileBlobArgs)
  @ResultType(api_vfs.ApiGetFileBlobResult)
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
  # Note: should be renamed to ListFlows. We should assume by default that
  # flows are client-specific. Global flows should be explicitly called
  # "global".
  @Category("Flows")
  @ArgsType(api_flow.ApiListClientFlowsArgs)
  @ResultType(api_flow.ApiListClientFlowsResult)
  @Http("GET", "/api/clients/<client_id>/flows")
  def ListClientFlows(self, args, token=None):
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
  @Http("GET", "/api/clients/<client_id>/flows/<flow_id>/results")
  def ListFlowResults(self, args, token=None):
    raise NotImplementedError()

  @Category("Flows")
  @ArgsType(api_flow.ApiGetFlowResultsExportCommandArgs)
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
  @Http("GET", "/api/clients/<client_id>/flows/<flow_id>/"
        "output-plugins/<plugin_id>/logs")
  def ListFlowOutputPluginLogs(self, args, token=None):
    raise NotImplementedError()

  @Category("Flows")
  @ArgsType(api_flow.ApiListFlowOutputPluginErrorsArgs)
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
  @Http("GET", "/api/cron-jobs")
  def ListCronJobs(self, args, token=None):
    raise NotImplementedError()

  @Category("Cron")
  @ArgsType(api_cron.ApiCronJob)
  @Http("POST", "/api/cron-jobs")
  def CreateCronJob(self, args, token=None):
    raise NotImplementedError()

  # Hunts methods.
  # =============
  #
  @Category("Hunts")
  @ArgsType(api_hunt.ApiListHuntsArgs)
  @Http("GET", "/api/hunts")
  def ListHunts(self, args, token=None):
    raise NotImplementedError()

  @Category("Hunts")
  @ArgsType(api_hunt.ApiGetHuntArgs)
  @Http("GET", "/api/hunts/<hunt_id>")
  def GetHunt(self, args, token=None):
    raise NotImplementedError()

  @Category("Hunts")
  @ArgsType(api_hunt.ApiListHuntErrorsArgs)
  @Http("GET", "/api/hunts/<hunt_id>/errors")
  def ListHuntErrors(self, args, token=None):
    raise NotImplementedError()

  @Category("Hunts")
  @ArgsType(api_hunt.ApiListHuntLogsArgs)
  # TODO(user): change "log" to "logs"
  @Http("GET", "/api/hunts/<hunt_id>/log")
  def ListHuntLogs(self, args, token=None):
    raise NotImplementedError()

  @Category("Hunts")
  @ArgsType(api_hunt.ApiListHuntResultsArgs)
  @Http("GET", "/api/hunts/<hunt_id>/results")
  def ListHuntResults(self, args, token=None):
    raise NotImplementedError()

  @Category("Hunts")
  @ArgsType(api_hunt.ApiGetHuntResultsExportCommandArgs)
  @Http("GET", "/api/hunts/<hunt_id>/results/export-command")
  def GetHuntResultsExportCommand(self, args, token=None):
    raise NotImplementedError()

  @Category("Hunts")
  @ArgsType(api_hunt.ApiListHuntOutputPluginsArgs)
  @Http("GET", "/api/hunts/<hunt_id>/output-plugins")
  def ListHuntOutputPlugins(self, args, token=None):
    raise NotImplementedError()

  @Category("Hunts")
  @ArgsType(api_hunt.ApiListHuntOutputPluginLogsArgs)
  @Http("GET", "/api/hunts/<hunt_id>/output-plugins/<plugin_id>/logs")
  def ListHuntOutputPluginLogs(self, args, token=None):
    raise NotImplementedError()

  @Category("Hunts")
  @ArgsType(api_hunt.ApiListHuntOutputPluginErrorsArgs)
  @Http("GET", "/api/hunts/<hunt_id>/output-plugins/<plugin_id>/errors")
  def ListHuntOutputPluginErrors(self, args, token=None):
    raise NotImplementedError()

  @Category("Hunts")
  @ArgsType(api_hunt.ApiListHuntCrashesArgs)
  @Http("GET", "/api/hunts/<hunt_id>/crashes")
  def ListHuntCrashes(self, args, token=None):
    raise NotImplementedError()

  @Category("Hunts")
  @ArgsType(api_hunt.ApiGetClientCompletionStatsArgs)
  @Http("GET", "/api/hunts/<hunt_id>/client-completion-stats")
  # TODO(user): maybe rename to GetHuntClientCompletionStats.
  def GetClientCompletionStats(self, args, token=None):
    raise NotImplementedError()

  @Category("Hunts")
  @ArgsType(api_hunt.ApiGetHuntStatsArgs)
  @ResultType(api_hunt.ApiGetHuntStatsResult)
  @Http("GET", "/api/hunts/<hunt_id>/stats")
  def GetHuntStats(self, args, token=None):
    raise NotImplementedError()

  @Category("Hunts")
  @ArgsType(api_hunt.ApiGetHuntClientsArgs)
  @ResultType(api_hunt.ApiGetHuntClientsResult)
  @Http("GET", "/api/hunts/<hunt_id>/clients/<client_status>")
  def GetHuntClients(self, args, token=None):
    raise NotImplementedError()

  @Category("Hunts")
  @ArgsType(api_hunt.ApiGetHuntContextArgs)
  @ResultType(api_hunt.ApiGetHuntContextResult)
  @Http("GET", "/api/hunts/<hunt_id>/context")
  def GetHuntContext(self, args, token=None):
    raise NotImplementedError()

  @Category("Hunts")
  @ArgsType(api_hunt.ApiCreateHuntArgs)
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
  def ListUserClientApprovals(self, args, token=None):
    raise NotImplementedError()

  @Category("User")
  @ArgsType(api_user.ApiListUserHuntApprovalsArgs)
  @Http("GET", "/api/users/me/approvals/hunt")
  def ListUserHuntApprovals(self, args, token=None):
    raise NotImplementedError()

  @Category("User")
  @ArgsType(api_user.ApiListUserCronApprovalsArgs)
  @Http("GET", "/api/users/me/approvals/cron")
  def ListUserCronApprovals(self, args, token=None):
    raise NotImplementedError()

  # User settings methods.
  # =====================
  #
  @Category("User")
  @ResultType(api_user.ApiGetUserInfoResult)
  @Http("GET", "/api/users/me/info")
  def GetUserInfo(self, args, token=None):
    raise NotImplementedError()

  @Category("User")
  @ResultType(api_user.ApiGetPendingUserNotificationsCountResult)
  @Http("GET", "/api/users/me/notifications/pending/count")
  def GetPendingUserNotificationsCount(self, args, token=None):
    raise NotImplementedError()

  @Category("User")
  @ArgsType(api_user.ApiGetPendingUserNotificationsArgs)
  @ResultType(api_user.ApiGetPendingUserNotificationsResult)
  @Http("GET", "/api/users/me/notifications/pending")
  def GetPendingUserNotifications(self, args, token=None):
    raise NotImplementedError()

  @Category("User")
  @ArgsType(api_user.ApiGetAndResetUserNotificationsArgs)
  @ResultType(api_user.ApiGetAndResetUserNotificationsResult)
  @Http("POST", "/api/users/me/notifications")
  def GetAndResetUserNotifications(self, args, token=None):
    raise NotImplementedError()

  @Category("User")
  @Http("GET", "/api/users/me/settings")
  def GetUserSettings(self, args, token=None):
    raise NotImplementedError()

  @Category("User")
  @ArgsType(aff4_users.GUISettings)
  @Http("POST", "/api/users/me/settings")
  def UpdateUserSettings(self, args, token=None):
    raise NotImplementedError()

  # Config methods.
  # ==============
  #
  @Category("Settings")
  @Http("GET", "/api/config")
  def GetConfig(self, args, token=None):
    raise NotImplementedError()

  @Category("Settings")
  @ArgsType(api_config.ApiGetConfigOptionArgs)
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
  @ArgsType(api_flow.ApiStartGetFileOperationArgs)
  # TODO(user): an URL for this one doesn't seem entirely correct. Come up
  # with an URL naming scheme that will separate flows with operations that
  # can be triggered remotely without authorization.
  @Http("POST", "/api/clients/<client_id>/flows/remotegetfile")
  def StartGetFileOperation(self, args, token=None):
    raise NotImplementedError()

  # Note: the difference between GetFlow and GetFlowStatus is that
  # GetFlowStatus doesn't require an approval to work. We should make
  # the name more informative and maybe include "robot" into it.
  @Category("Flows")
  @ArgsType(api_flow.ApiGetFlowStatusArgs)
  @Http("GET", "/api/flows/<client_id>/<flow_id>/status")
  def GetFlowStatus(self, args, token=None):
    raise NotImplementedError()


class DisabledApiCallRouter(ApiCallRouter):
  pass
