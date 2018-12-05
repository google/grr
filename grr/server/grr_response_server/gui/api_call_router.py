#!/usr/bin/env python
"""Router classes route API requests to particular handlers."""
from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

import inspect
import re


from future.utils import with_metaclass

from grr_response_core.lib import registry
from grr_response_core.lib.util import compatibility
from grr_response_core.lib.util import precondition
from grr_response_server.gui import api_value_renderers
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


class Http(object):
  """Decorator that associates URLs with API methods."""

  def __init__(self, method, path, strip_root_types=True):
    self.method = method
    self.path = path
    self.strip_root_types = strip_root_types

  def __call__(self, func):
    try:
      http_methods = getattr(func, "__http_methods__")
    except AttributeError:
      http_methods = []
      setattr(func, "__http_methods__", http_methods)

    http_methods.append((self.method, self.path,
                         dict(strip_root_types=self.strip_root_types)))

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


class NoAuditLogRequired(object):
  """Decorator indicating that this API method should not be logged."""

  def __call__(self, func):
    func.__no_audit_log_required__ = True
    return func


class RouterMethodMetadata(object):
  """Data object for metadata about router methods."""

  BINARY_STREAM_RESULT_TYPE = "BinaryStream"

  def __init__(self,
               name,
               doc=None,
               args_type=None,
               result_type=None,
               category=None,
               http_methods=None,
               no_audit_log_required=False):
    precondition.AssertType(name, unicode)

    self.name = name
    self.doc = doc
    self.args_type = args_type
    self.result_type = result_type
    self.category = category
    self.http_methods = http_methods or set()
    self.no_audit_log_required = no_audit_log_required

  _RULE_REGEX = re.compile("<([a-zA-Z0-9:_]+)")

  def GetQueryParamsNames(self):
    """This extracts all parameters from URL paths for logging.

    This extracts the name of all parameters that are sent inside the
    URL path for the given route. For example the path
    /api/clients/<client_id>/last-ip would return ["client_id"].

    Some URL paths contain annotated parameters - for example paths as
    in /api/clients/<client_id>/vfs-index/<path:file_path>. Those
    annotations will be stripped off by this function and just the
    plain parameter name will be returned.

    Returns:
      A list of extracted parameters.
    """
    result = []
    for unused_method, path, unused_params in self.http_methods or []:
      for arg in re.findall(self._RULE_REGEX, path):
        if ":" in arg:
          arg = arg[arg.find(":") + 1:]
        result.append(arg)
    return result


class ApiCallRouter(with_metaclass(registry.MetaclassRegistry, object)):
  """Routers do ACL checks and route API requests to handlers."""
  __abstract = True  # pylint: disable=g-bad-name

  # If router is configurable, RDFValue class of its configuration
  # structure should be specified here. Params of this type will
  # be initialized from the routers configuration file (defined
  # by API.RouterACLConfigFile) and passed into the constructor
  # using "params" keyword argument.
  params_type = None

  def __init__(self, params=None):
    """Constructor. Accepts optional router parameters.

    Args:
      params: None, or an RDFValue instance of params_type.
    """
    super(ApiCallRouter, self).__init__()
    _ = params

  @classmethod
  def GetAnnotatedMethods(cls):
    """Returns a dictionary of annotated router methods."""

    result = {}

    # We want methods with the highest call-order to be processed last,
    # so that their annotations have precedence.
    for i_cls in reversed(inspect.getmro(cls)):
      for name in compatibility.ListAttrs(i_cls):
        cls_method = getattr(i_cls, name)

        if not callable(cls_method):
          continue

        if not hasattr(cls_method, "__http_methods__"):
          continue

        result[name] = RouterMethodMetadata(
            name=name,
            doc=cls_method.__doc__,
            args_type=getattr(cls_method, "__args_type__", None),
            result_type=getattr(cls_method, "__result_type__", None),
            category=getattr(cls_method, "__category__", None),
            http_methods=getattr(cls_method, "__http_methods__", set()),
            no_audit_log_required=getattr(cls_method,
                                          "__no_audit_log_required__", False))

    return result


class ApiCallRouterStub(ApiCallRouter):
  """Default router stub with methods definitions only."""

  # Artifacts methods.
  # =================
  #
  @Category("Artifacts")
  @ArgsType(api_artifact.ApiListArtifactsArgs)
  @ResultType(api_artifact.ApiListArtifactsResult)
  @Http("GET", "/api/artifacts")
  @NoAuditLogRequired()
  def ListArtifacts(self, args, token=None):
    """List available artifacts definitions."""

    raise NotImplementedError()

  @Category("Artifacts")
  @ArgsType(api_artifact.ApiUploadArtifactArgs)
  @Http("POST", "/api/artifacts")
  @NoAuditLogRequired()
  def UploadArtifact(self, args, token=None):
    """Upload new artifact definition."""

    raise NotImplementedError()

  @Category("Artifacts")
  @ArgsType(api_artifact.ApiDeleteArtifactsArgs)
  @Http("DELETE", "/api/artifacts")
  @NoAuditLogRequired()
  def DeleteArtifacts(self, args, token=None):
    """Delete one of previously uploaded artifacts."""

    raise NotImplementedError()

  # Clients methods.
  # ===============
  #
  @Category("Clients")
  @ArgsType(api_client.ApiSearchClientsArgs)
  @ResultType(api_client.ApiSearchClientsResult)
  @Http("GET", "/api/clients")
  def SearchClients(self, args, token=None):
    """Search for clients using a search query."""

    raise NotImplementedError()

  @Category("Clients")
  @ArgsType(api_client.ApiGetClientArgs)
  @ResultType(api_client.ApiClient)
  @Http("GET", "/api/clients/<client_id>", strip_root_types=False)
  def GetClient(self, args, token=None):
    """Get client with a given client id."""

    raise NotImplementedError()

  @Category("Clients")
  @ArgsType(api_client.ApiGetClientVersionsArgs)
  @ResultType(api_client.ApiGetClientVersionsResult)
  @Http("GET", "/api/clients/<client_id>/versions")
  def GetClientVersions(self, args, token=None):
    """Get different client versions in a given time range."""

    raise NotImplementedError()

  @Category("Clients")
  @ArgsType(api_client.ApiGetClientVersionTimesArgs)
  @ResultType(api_client.ApiGetClientVersionTimesResult)
  @Http("GET", "/api/clients/<client_id>/version-times")
  def GetClientVersionTimes(self, args, token=None):
    """List available version-times of a client object with a given id."""

    raise NotImplementedError()

  @Category("Clients")
  @ArgsType(api_client.ApiInterrogateClientArgs)
  @ResultType(api_client.ApiInterrogateClientResult)
  @Http("POST", "/api/clients/<client_id>/actions/interrogate")
  def InterrogateClient(self, args, token=None):
    """Inititate client interrogation."""

    raise NotImplementedError()

  @Category("Clients")
  @ArgsType(api_client.ApiGetInterrogateOperationStateArgs)
  @ResultType(api_client.ApiGetInterrogateOperationStateResult)
  @Http("GET",
        "/api/clients/<client_id>/actions/interrogate/<path:operation_id>")
  def GetInterrogateOperationState(self, args, token=None):
    """Get state of a previously started interrogation."""

    raise NotImplementedError()

  @ArgsType(api_client.ApiGetLastClientIPAddressArgs)
  @ResultType(api_client.ApiGetLastClientIPAddressResult)
  @Http("GET", "/api/clients/<client_id>/last-ip")
  @NoAuditLogRequired()
  def GetLastClientIPAddress(self, args, token=None):
    """Get last known client IP address."""

    raise NotImplementedError()

  @Category("Clients")
  @ArgsType(api_client.ApiListClientCrashesArgs)
  @ResultType(api_client.ApiListClientCrashesResult)
  @Http("GET", "/api/clients/<client_id>/crashes")
  def ListClientCrashes(self, args, token=None):
    """List crashes of a given client."""

    raise NotImplementedError()

  @Category("Clients")
  @ArgsType(api_client.ApiListClientActionRequestsArgs)
  @ResultType(api_client.ApiListClientActionRequestsResult)
  @Http("GET", "/api/clients/<client_id>/action-requests")
  def ListClientActionRequests(self, args, token=None):
    """List pending action requests for a given client."""

    raise NotImplementedError()

  @Category("Clients")
  @ArgsType(api_client.ApiGetClientLoadStatsArgs)
  @ResultType(api_client.ApiGetClientLoadStatsResult)
  @Http("GET", "/api/clients/<client_id>/load-stats/<metric>")
  def GetClientLoadStats(self, args, token=None):
    """Get client load statistics (CPI and IO)."""

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
    """List files in a given VFS directory of a given client."""

    # This method can be called with or without file_path argument and returns
    # the root files for the given client in the latter case.
    # To allow optional url arguments, two url patterns need to be specified.
    raise NotImplementedError()

  @Category("Vfs")
  @ArgsType(api_vfs.ApiGetVfsFilesArchiveArgs)
  @ResultBinaryStream()
  @Http("GET", "/api/clients/<client_id>/vfs-files-archive/")
  @Http("GET", "/api/clients/<client_id>/vfs-files-archive/<path:file_path>")
  def GetVfsFilesArchive(self, args, token=None):
    """Get archive with files collected and stored in the VFS of a client."""

    # This method can be called with or without file_path argument.
    #
    # If file_path is given, this method will recursively download all the
    # files within a given directory which have been collected from this
    # client.
    #
    # If file_path is omitted, this method will download all the files
    # which have been collected from this client.
    #
    # Note: this method downloads only the most recent versions of the
    # files.

    raise NotImplementedError()

  @Category("Vfs")
  @ArgsType(api_vfs.ApiGetFileDetailsArgs)
  @ResultType(api_vfs.ApiGetFileDetailsResult)
  @Http("GET", "/api/clients/<client_id>/vfs-details/<path:file_path>")
  def GetFileDetails(self, args, token=None):
    """Get details of a VFS file on a given client."""

    raise NotImplementedError()

  @Category("Vfs")
  @ArgsType(api_vfs.ApiGetFileTextArgs)
  @ResultType(api_vfs.ApiGetFileTextResult)
  @Http("GET", "/api/clients/<client_id>/vfs-text/<path:file_path>")
  def GetFileText(self, args, token=None):
    """Get text file contents of a VFS file on a given client."""

    raise NotImplementedError()

  @Category("Vfs")
  @ArgsType(api_vfs.ApiGetFileBlobArgs)
  @ResultBinaryStream()
  @Http("GET", "/api/clients/<client_id>/vfs-blob/<path:file_path>")
  def GetFileBlob(self, args, token=None):
    """Get byte contents of a VFS file on a given client."""

    raise NotImplementedError()

  @Category("Vfs")
  @ArgsType(api_vfs.ApiGetFileVersionTimesArgs)
  @ResultType(api_vfs.ApiGetFileVersionTimesResult)
  @Http("GET", "/api/clients/<client_id>/vfs-version-times/<path:file_path>")
  def GetFileVersionTimes(self, args, token=None):
    """Get available version times of a VFS file on a given client."""

    raise NotImplementedError()

  @Category("Vfs")
  @ArgsType(api_vfs.ApiGetFileDownloadCommandArgs)
  @ResultType(api_vfs.ApiGetFileDownloadCommandResult)
  @Http("GET", "/api/clients/<client_id>/vfs-download-command/<path:file_path>")
  def GetFileDownloadCommand(self, args, token=None):
    """Get a command line that downloads given VFS file."""

    raise NotImplementedError()

  @Category("Vfs")
  @ArgsType(api_vfs.ApiCreateVfsRefreshOperationArgs)
  @ResultType(api_vfs.ApiCreateVfsRefreshOperationResult)
  @Http("POST", "/api/clients/<client_id>/vfs-refresh-operations")
  def CreateVfsRefreshOperation(self, args, token=None):
    """Start VFS refresh operation (refreshes a given VFS folder)."""

    raise NotImplementedError()

  @Category("Vfs")
  @ArgsType(api_vfs.ApiGetVfsRefreshOperationStateArgs)
  @ResultType(api_vfs.ApiGetVfsRefreshOperationStateResult)
  @Http("GET",
        "/api/clients/<client_id>/vfs-refresh-operations/<path:operation_id>")
  def GetVfsRefreshOperationState(self, args, token=None):
    """Get state of a previously started VFS refresh operation."""

    raise NotImplementedError()

  @Category("Vfs")
  @ArgsType(api_vfs.ApiGetVfsTimelineArgs)
  @ResultType(api_vfs.ApiGetVfsTimelineResult)
  @Http("GET", "/api/clients/<client_id>/vfs-timeline/<path:file_path>")
  def GetVfsTimeline(self, args, token=None):
    """Get event timeline of VFS events for a given VFS path."""

    raise NotImplementedError()

  @Category("Vfs")
  @ArgsType(api_vfs.ApiGetVfsTimelineAsCsvArgs)
  @ResultBinaryStream()
  @Http("GET", "/api/clients/<client_id>/vfs-timeline-csv/<path:file_path>")
  def GetVfsTimelineAsCsv(self, args, token=None):
    """Get event timeline of VFS evetns for a given VFS path in CSV format."""

    raise NotImplementedError()

  @Category("Vfs")
  @ArgsType(api_vfs.ApiUpdateVfsFileContentArgs)
  @ResultType(api_vfs.ApiUpdateVfsFileContentResult)
  @Http("POST", "/api/clients/<client_id>/vfs-update")
  def UpdateVfsFileContent(self, args, token=None):
    """Create request for a new snapshot of the file."""

    raise NotImplementedError()

  @Category("Vfs")
  @ArgsType(api_vfs.ApiGetVfsFileContentUpdateStateArgs)
  @ResultType(api_vfs.ApiGetVfsFileContentUpdateStateResult)
  @Http("GET", "/api/clients/<client_id>/vfs-update/<path:operation_id>")
  def GetVfsFileContentUpdateState(self, args, token=None):
    """Get state of a previously started content update operation."""

    raise NotImplementedError()

  @Category("Vfs")
  @ArgsType(api_vfs.ApiGetFileDecodersArgs)
  @ResultType(api_vfs.ApiGetFileDecodersResult)
  @Http("GET", "/api/clients/<client_id>/vfs-decoders/<path:file_path>")
  def GetFileDecoders(self, args, token=None):
    """Get the decoder names that are applicable to the specified file."""
    raise NotImplementedError()

  @Category("Vfs")
  @ArgsType(api_vfs.ApiGetDecodedFileArgs)
  @ResultBinaryStream()
  @Http("GET", "/api/clients/<client_id>/vfs-decoded-blob/"
        "<decoder_name>/<path:file_path>")
  def GetDecodedFileBlob(self, args, token=None):
    """Get a decoded view of the specified file."""
    raise NotImplementedError()

  # Clients labels methods.
  # ======================
  #
  @Category("Clients")
  @ResultType(api_client.ApiListClientsLabelsResult)
  @Http("GET", "/api/clients/labels")
  @NoAuditLogRequired()
  def ListClientsLabels(self, args, token=None):
    """List all available clients labels."""

    raise NotImplementedError()

  @Category("Clients")
  @ArgsType(api_client.ApiAddClientsLabelsArgs)
  @Http("POST", "/api/clients/labels/add")
  @NoAuditLogRequired()
  def AddClientsLabels(self, args, token=None):
    """Labels given clients with given labels."""

    raise NotImplementedError()

  @Category("Clients")
  @ArgsType(api_client.ApiRemoveClientsLabelsArgs)
  @Http("POST", "/api/clients/labels/remove")
  @NoAuditLogRequired()
  def RemoveClientsLabels(self, args, token=None):
    """Remove given labels from given clients."""

    raise NotImplementedError()

  # Clients flows methods.
  # =====================
  #
  @Category("Flows")
  @ArgsType(api_flow.ApiListFlowsArgs)
  @ResultType(api_flow.ApiListFlowsResult)
  @Http("GET", "/api/clients/<client_id>/flows")
  def ListFlows(self, args, token=None):
    """List flows on a given client."""

    raise NotImplementedError()

  @Category("Flows")
  @ArgsType(api_flow.ApiGetFlowArgs)
  @ResultType(api_flow.ApiFlow)
  @Http(
      "GET",
      "/api/clients/<client_id>/flows/<path:flow_id>",
      strip_root_types=False)
  def GetFlow(self, args, token=None):
    """Get flow details."""

    raise NotImplementedError()

  @Category("Flows")
  @ArgsType(api_flow.ApiCreateFlowArgs)
  @ResultType(api_flow.ApiFlow)
  @Http("POST", "/api/clients/<client_id>/flows", strip_root_types=False)
  def CreateFlow(self, args, token=None):
    """Start a new flow on a given client."""

    raise NotImplementedError()

  @Category("Flows")
  @ArgsType(api_flow.ApiCancelFlowArgs)
  @Http("POST", "/api/clients/<client_id>/flows/<path:flow_id>/actions/cancel")
  def CancelFlow(self, args, token=None):
    """Stop given flow on a given client."""

    raise NotImplementedError()

  @Category("Flows")
  @ArgsType(api_flow.ApiListFlowRequestsArgs)
  @ResultType(api_flow.ApiListFlowRequestsResult)
  @Http("GET", "/api/clients/<client_id>/flows/<path:flow_id>/requests")
  def ListFlowRequests(self, args, token=None):
    """List pending action requests of a given flow on a given client."""

    raise NotImplementedError()

  @Category("Flows")
  @ArgsType(api_flow.ApiListFlowResultsArgs)
  @ResultType(api_flow.ApiListFlowResultsResult)
  @Http("GET", "/api/clients/<client_id>/flows/<path:flow_id>/results")
  def ListFlowResults(self, args, token=None):
    """List results of a given flow on a given client."""

    raise NotImplementedError()

  @Category("Flows")
  @ArgsType(api_flow.ApiGetExportedFlowResultsArgs)
  @ResultBinaryStream()
  @Http("GET", "/api/clients/<client_id>/flows/<path:flow_id>/"
        "exported-results/<plugin_name>")
  def GetExportedFlowResults(self, args, token=None):
    """Stream flow results using one of the instant output plugins."""

    raise NotImplementedError()

  @Category("Flows")
  @ArgsType(api_flow.ApiGetFlowResultsExportCommandArgs)
  @ResultType(api_flow.ApiGetFlowResultsExportCommandResult)
  @Http("GET", "/api/clients/<client_id>/flows/<path:flow_id>/results/"
        "export-command")
  def GetFlowResultsExportCommand(self, args, token=None):
    """Get export tool command to export flow results."""

    raise NotImplementedError()

  @Category("Flows")
  @ArgsType(api_flow.ApiGetFlowFilesArchiveArgs)
  @ResultBinaryStream()
  @Http("GET", "/api/clients/<client_id>/flows/<path:flow_id>/results/"
        "files-archive")
  def GetFlowFilesArchive(self, args, token=None):
    """Get ZIP or TAR.GZ archive with files downloaded by the flow."""

    raise NotImplementedError()

  @Category("Flows")
  @ArgsType(api_flow.ApiListFlowOutputPluginsArgs)
  @ResultType(api_flow.ApiListFlowOutputPluginsResult)
  @Http("GET", "/api/clients/<client_id>/flows/<path:flow_id>/output-plugins")
  def ListFlowOutputPlugins(self, args, token=None):
    """List output plugins used by the flow."""

    raise NotImplementedError()

  @Category("Flows")
  @ArgsType(api_flow.ApiListFlowOutputPluginLogsArgs)
  @ResultType(api_flow.ApiListFlowOutputPluginLogsResult)
  @Http("GET", "/api/clients/<client_id>/flows/<path:flow_id>/"
        "output-plugins/<plugin_id>/logs")
  def ListFlowOutputPluginLogs(self, args, token=None):
    """List output plugin logs of the flow."""

    raise NotImplementedError()

  @Category("Flows")
  @ArgsType(api_flow.ApiListFlowOutputPluginErrorsArgs)
  @ResultType(api_flow.ApiListFlowOutputPluginErrorsResult)
  @Http("GET", "/api/clients/<client_id>/flows/<path:flow_id>/"
        "output-plugins/<plugin_id>/errors")
  def ListFlowOutputPluginErrors(self, args, token=None):
    """List output plugin errors of the flow."""

    raise NotImplementedError()

  @Category("Flows")
  @ArgsType(api_flow.ApiListFlowLogsArgs)
  @ResultType(api_flow.ApiListFlowLogsResult)
  @Http("GET", "/api/clients/<client_id>/flows/<path:flow_id>/log")
  def ListFlowLogs(self, args, token=None):
    """List logs of the flow."""

    raise NotImplementedError()

  # Cron jobs methods.
  # =================
  #
  @Category("Cron")
  @ArgsType(api_cron.ApiListCronJobsArgs)
  @ResultType(api_cron.ApiListCronJobsResult)
  @NoAuditLogRequired()
  @Http("GET", "/api/cron-jobs")
  def ListCronJobs(self, args, token=None):
    """List available cron jobs."""

    raise NotImplementedError()

  @Category("Cron")
  @ArgsType(api_cron.ApiCreateCronJobArgs)
  @ResultType(api_cron.ApiCronJob)
  @Http("POST", "/api/cron-jobs", strip_root_types=False)
  def CreateCronJob(self, args, token=None):
    """Create new cron job."""

    raise NotImplementedError()

  @Category("Cron")
  @ArgsType(api_cron.ApiGetCronJobArgs)
  @ResultType(api_cron.ApiCronJob)
  @Http("GET", "/api/cron-jobs/<cron_job_id>", strip_root_types=False)
  def GetCronJob(self, args, token=None):
    """Get details of a given cron job."""

    raise NotImplementedError()

  @Category("Cron")
  @ArgsType(api_cron.ApiForceRunCronJobArgs)
  @Http("POST", "/api/cron-jobs/<cron_job_id>/actions/force-run")
  def ForceRunCronJob(self, args, token=None):
    """Force an out-of-schedule run of a given cron job."""

    raise NotImplementedError()

  @Category("Hunts")
  @ArgsType(api_cron.ApiModifyCronJobArgs)
  @ResultType(api_cron.ApiCronJob)
  @Http("PATCH", "/api/cron-jobs/<cron_job_id>", strip_root_types=False)
  def ModifyCronJob(self, args, token=None):
    """Modify cron job (includes enabling/disabling)."""

    raise NotImplementedError()

  @Category("Cron")
  @ArgsType(api_cron.ApiListCronJobRunsArgs)
  @ResultType(api_cron.ApiListCronJobRunsResult)
  @Http("GET", "/api/cron-jobs/<cron_job_id>/runs")
  def ListCronJobRuns(self, args, token=None):
    """List runs initiated by the given cron job."""

    raise NotImplementedError()

  @Category("Cron")
  @ArgsType(api_cron.ApiGetCronJobRunArgs)
  @ResultType(api_cron.ApiCronJobRun)
  @Http(
      "GET",
      "/api/cron-jobs/<cron_job_id>/runs/<run_id>",
      strip_root_types=False)
  def GetCronJobRun(self, args, token=None):
    """Get details of a run started by a cron job."""

    raise NotImplementedError()

  @Category("Cron")
  @ArgsType(api_cron.ApiDeleteCronJobArgs)
  @Http("DELETE", "/api/cron-jobs/<cron_job_id>")
  def DeleteCronJob(self, args, token=None):
    """Delete given cron job and all its flows."""

    raise NotImplementedError()

  # Hunts methods.
  # =============
  #
  @Category("Hunts")
  @ArgsType(api_hunt.ApiListHuntsArgs)
  @ResultType(api_hunt.ApiListHuntsResult)
  @Http("GET", "/api/hunts")
  @NoAuditLogRequired()
  def ListHunts(self, args, token=None):
    """List hunts."""

    raise NotImplementedError()

  @Category("Hunts")
  @ArgsType(api_hunt.ApiGetHuntArgs)
  @ResultType(api_hunt.ApiHunt)
  @Http("GET", "/api/hunts/<hunt_id>", strip_root_types=False)
  def GetHunt(self, args, token=None):
    """Get details of a hunt with a given id."""

    raise NotImplementedError()

  @Category("Hunts")
  @ArgsType(api_hunt.ApiListHuntErrorsArgs)
  @ResultType(api_hunt.ApiListHuntErrorsResult)
  @Http("GET", "/api/hunts/<hunt_id>/errors")
  def ListHuntErrors(self, args, token=None):
    """List hunt errors."""

    raise NotImplementedError()

  @Category("Hunts")
  @ArgsType(api_hunt.ApiListHuntLogsArgs)
  @ResultType(api_hunt.ApiListHuntLogsResult)
  # TODO(user): change "log" to "logs"
  @Http("GET", "/api/hunts/<hunt_id>/log")
  def ListHuntLogs(self, args, token=None):
    """List hunt logs."""

    raise NotImplementedError()

  @Category("Hunts")
  @ArgsType(api_hunt.ApiListHuntResultsArgs)
  @ResultType(api_hunt.ApiListHuntResultsResult)
  @Http("GET", "/api/hunts/<hunt_id>/results")
  def ListHuntResults(self, args, token=None):
    """List hunt results."""

    raise NotImplementedError()

  @Category("Hunts")
  @ArgsType(api_hunt.ApiGetExportedHuntResultsArgs)
  @ResultBinaryStream()
  @Http("GET", "/api/hunts/<hunt_id>/exported-results/<plugin_name>")
  def GetExportedHuntResults(self, args, token=None):
    """Stream hunt results using one of the instant output plugins."""

    raise NotImplementedError()

  @Category("Hunts")
  @ArgsType(api_hunt.ApiGetHuntResultsExportCommandArgs)
  @ResultType(api_hunt.ApiGetHuntResultsExportCommandResult)
  @Http("GET", "/api/hunts/<hunt_id>/results/export-command")
  def GetHuntResultsExportCommand(self, args, token=None):
    """Get export command that exports hunt results."""

    raise NotImplementedError()

  @Category("Hunts")
  @ArgsType(api_hunt.ApiListHuntOutputPluginsArgs)
  @ResultType(api_hunt.ApiListHuntOutputPluginsResult)
  @Http("GET", "/api/hunts/<hunt_id>/output-plugins")
  def ListHuntOutputPlugins(self, args, token=None):
    """List output plugins used by the hunt."""

    raise NotImplementedError()

  @Category("Hunts")
  @ArgsType(api_hunt.ApiListHuntOutputPluginLogsArgs)
  @ResultType(api_hunt.ApiListHuntOutputPluginLogsResult)
  @Http("GET", "/api/hunts/<hunt_id>/output-plugins/<plugin_id>/logs")
  def ListHuntOutputPluginLogs(self, args, token=None):
    """List hunt output plugins logs."""

    raise NotImplementedError()

  @Category("Hunts")
  @ArgsType(api_hunt.ApiListHuntOutputPluginErrorsArgs)
  @ResultType(api_hunt.ApiListHuntOutputPluginErrorsResult)
  @Http("GET", "/api/hunts/<hunt_id>/output-plugins/<plugin_id>/errors")
  def ListHuntOutputPluginErrors(self, args, token=None):
    """List hunt output plugins errors."""

    raise NotImplementedError()

  @Category("Hunts")
  @ArgsType(api_hunt.ApiListHuntCrashesArgs)
  @ResultType(api_hunt.ApiListHuntCrashesResult)
  @Http("GET", "/api/hunts/<hunt_id>/crashes")
  def ListHuntCrashes(self, args, token=None):
    """List all crashes caused by the hunt."""

    raise NotImplementedError()

  @Category("Hunts")
  @ArgsType(api_hunt.ApiGetHuntClientCompletionStatsArgs)
  @ResultType(api_hunt.ApiGetHuntClientCompletionStatsResult)
  @Http("GET", "/api/hunts/<hunt_id>/client-completion-stats")
  def GetHuntClientCompletionStats(self, args, token=None):
    """Get hunt completion stats."""

    raise NotImplementedError()

  @Category("Hunts")
  @ArgsType(api_hunt.ApiGetHuntStatsArgs)
  @ResultType(api_hunt.ApiGetHuntStatsResult)
  @Http("GET", "/api/hunts/<hunt_id>/stats")
  def GetHuntStats(self, args, token=None):
    """Get general hunt stats."""

    raise NotImplementedError()

  @Category("Hunts")
  @ArgsType(api_hunt.ApiListHuntClientsArgs)
  @ResultType(api_hunt.ApiListHuntClientsResult)
  @Http("GET", "/api/hunts/<hunt_id>/clients/<client_status>")
  def ListHuntClients(self, args, token=None):
    """List clients involved into the hunt."""

    raise NotImplementedError()

  @Category("Hunts")
  @ArgsType(api_hunt.ApiGetHuntContextArgs)
  @ResultType(api_hunt.ApiGetHuntContextResult)
  @Http("GET", "/api/hunts/<hunt_id>/context")
  def GetHuntContext(self, args, token=None):
    """Get a low-level hunt context (useful for debugging)."""

    raise NotImplementedError()

  @Category("Hunts")
  @ArgsType(api_hunt.ApiCreateHuntArgs)
  @ResultType(api_hunt.ApiHunt)
  @Http("POST", "/api/hunts", strip_root_types=False)
  def CreateHunt(self, args, token=None):
    """Create a new hunt."""

    raise NotImplementedError()

  @Category("Hunts")
  @ArgsType(api_hunt.ApiModifyHuntArgs)
  @ResultType(api_hunt.ApiHunt)
  @Http("PATCH", "/api/hunts/<hunt_id>", strip_root_types=False)
  def ModifyHunt(self, args, token=None):
    """Modify hunt (includes stopping/starting)."""

    raise NotImplementedError()

  @Category("Hunts")
  @ArgsType(api_hunt.ApiDeleteHuntArgs)
  @Http("DELETE", "/api/hunts/<hunt_id>", strip_root_types=False)
  def DeleteHunt(self, args, token=None):
    """Delete a hunt with all its data."""

    raise NotImplementedError()

  @Category("Hunts")
  @ArgsType(api_hunt.ApiGetHuntFilesArchiveArgs)
  @ResultBinaryStream()
  @Http("GET", "/api/hunts/<hunt_id>/results/files-archive")
  def GetHuntFilesArchive(self, args, token=None):
    """Get ZIP or TAR.GZ archive with all the files downloaded by the hunt."""

    raise NotImplementedError()

  @Category("Hunts")
  @ArgsType(api_hunt.ApiGetHuntFileArgs)
  @ResultBinaryStream()
  @Http("GET", "/api/hunts/<hunt_id>/results/clients/<client_id>/vfs-blob"
        "/<path:vfs_path>")
  def GetHuntFile(self, args, token=None):
    """Get a file referenced by one of the hunt results."""

    raise NotImplementedError()

  # Stats metrics methods.
  # =====================
  #
  @Category("Other")
  @ArgsType(api_stats.ApiListStatsStoreMetricsMetadataArgs)
  @ResultType(api_stats.ApiListStatsStoreMetricsMetadataResult)
  @Http("GET", "/api/stats/store/<component>/metadata")
  @NoAuditLogRequired()
  def ListStatsStoreMetricsMetadata(self, args, token=None):
    """List metadata of available stats metrics."""

    raise NotImplementedError()

  @Category("Other")
  @Http("GET", "/api/stats/store/<component>/metrics/<metric_name>")
  @ArgsType(api_stats.ApiGetStatsStoreMetricArgs)
  @ResultType(api_stats.ApiStatsStoreMetric)
  @NoAuditLogRequired()
  def GetStatsStoreMetric(self, args, token=None):
    """Get data corresponding to a given stats metric."""

    raise NotImplementedError()

  # TODO(user,user): Change the naming convention from stats to reports
  # throughout the codebase.
  @Category("Other")
  @Http("GET", "/api/stats/reports")
  @ResultType(api_stats.ApiListReportsResult)
  def ListReports(self, args, token=None):
    """List available stats reports."""

    raise NotImplementedError()

  @Category("Other")
  @Http("GET", "/api/stats/reports/<name>")
  @ArgsType(api_stats.ApiGetReportArgs)
  @ResultType(api_stats.rdf_report_plugins.ApiReport)
  def GetReport(self, args, token=None):
    """Get data of a given report."""

    raise NotImplementedError()

  # Approvals methods.
  # =================
  #
  @Category("User")
  @ArgsType(api_user.ApiCreateClientApprovalArgs)
  @ResultType(api_user.ApiClientApproval)
  @Http(
      "POST",
      "/api/users/me/approvals/client/<client_id>",
      strip_root_types=False)
  def CreateClientApproval(self, args, token=None):
    """Create new client approval."""

    raise NotImplementedError()

  @Category("User")
  @ArgsType(api_user.ApiGetClientApprovalArgs)
  @ResultType(api_user.ApiClientApproval)
  @NoAuditLogRequired()
  @Http(
      "GET",
      "/api/users/<username>/approvals/client/<client_id>/<approval_id>",
      strip_root_types=False)
  def GetClientApproval(self, args, token=None):
    """Get client approval identified by approval id, client id and username."""
    raise NotImplementedError()

  @Category("User")
  @ArgsType(api_user.ApiGrantClientApprovalArgs)
  @ResultType(api_user.ApiClientApproval)
  @Http(
      "POST",
      "/api/users/<username>/approvals/client/<client_id>/<approval_id>/"
      "actions/grant",
      strip_root_types=False)
  def GrantClientApproval(self, args, token=None):
    """Grant client approval."""

    raise NotImplementedError()

  @Category("User")
  @ArgsType(api_user.ApiListClientApprovalsArgs)
  @ResultType(api_user.ApiListClientApprovalsResult)
  @NoAuditLogRequired()
  @Http("GET", "/api/users/me/approvals/client")
  @Http("GET", "/api/users/me/approvals/client/<client_id>")
  def ListClientApprovals(self, args, token=None):
    """List client approvals of a current user."""

    raise NotImplementedError()

  @Category("User")
  @ArgsType(api_user.ApiCreateHuntApprovalArgs)
  @ResultType(api_user.ApiHuntApproval)
  @NoAuditLogRequired()
  @Http(
      "POST", "/api/users/me/approvals/hunt/<hunt_id>", strip_root_types=False)
  def CreateHuntApproval(self, args, token=None):
    """Create new hunt approval."""

    raise NotImplementedError()

  @Category("User")
  @ArgsType(api_user.ApiGetHuntApprovalArgs)
  @ResultType(api_user.ApiHuntApproval)
  @NoAuditLogRequired()
  @Http(
      "GET",
      "/api/users/<username>/approvals/hunt/<hunt_id>/<approval_id>",
      strip_root_types=False)
  def GetHuntApproval(self, args, token=None):
    """Get hunt approval identified by approval id, hunt id and username."""
    raise NotImplementedError()

  @Category("User")
  @ArgsType(api_user.ApiGrantHuntApprovalArgs)
  @ResultType(api_user.ApiHuntApproval)
  @Http(
      "POST",
      "/api/users/<username>/approvals/hunt/<hunt_id>/<approval_id>/"
      "actions/grant",
      strip_root_types=False)
  def GrantHuntApproval(self, args, token=None):
    """Grant hunt approval."""

    raise NotImplementedError()

  @Category("User")
  @ArgsType(api_user.ApiListHuntApprovalsArgs)
  @ResultType(api_user.ApiListHuntApprovalsResult)
  @NoAuditLogRequired()
  @Http("GET", "/api/users/me/approvals/hunt")
  def ListHuntApprovals(self, args, token=None):
    """List hunt approvals of a current user."""

    raise NotImplementedError()

  @Category("User")
  @ArgsType(api_user.ApiCreateCronJobApprovalArgs)
  @ResultType(api_user.ApiCronJobApproval)
  @Http(
      "POST",
      "/api/users/me/approvals/cron-job/<cron_job_id>",
      strip_root_types=False)
  def CreateCronJobApproval(self, args, token=None):
    """Create new cron job approval."""

    raise NotImplementedError()

  @Category("User")
  @ArgsType(api_user.ApiGetCronJobApprovalArgs)
  @ResultType(api_user.ApiCronJobApproval)
  @NoAuditLogRequired()
  @Http(
      "GET",
      "/api/users/<username>/approvals/cron-job/<cron_job_id>/<approval_id>",
      strip_root_types=False)
  def GetCronJobApproval(self, args, token=None):
    """Get cron job approval identified by approval id, cron id and username."""

    raise NotImplementedError()

  @Category("User")
  @ArgsType(api_user.ApiGrantCronJobApprovalArgs)
  @ResultType(api_user.ApiCronJobApproval)
  @Http(
      "POST",
      "/api/users/<username>/approvals/cron-job/<cron_job_id>/<approval_id>/"
      "actions/grant",
      strip_root_types=False)
  def GrantCronJobApproval(self, args, token=None):
    """Grant cron job approval."""

    raise NotImplementedError()

  @Category("User")
  @ArgsType(api_user.ApiListCronJobApprovalsArgs)
  @ResultType(api_user.ApiListCronJobApprovalsResult)
  @NoAuditLogRequired()
  @Http("GET", "/api/users/me/approvals/cron-job")
  def ListCronJobApprovals(self, args, token=None):
    """List cron job approvals of a current user."""

    raise NotImplementedError()

  @Category("User")
  @ArgsType(api_user.ApiListApproverSuggestionsArgs)
  @ResultType(api_user.ApiListApproverSuggestionsResult)
  @Http("GET", "/api/users/approver-suggestions")
  def ListApproverSuggestions(self, args, token=None):
    """List suggestions for approver usernames."""

    raise NotImplementedError()

  # User settings methods.
  # =====================
  #
  @Category("User")
  @ResultType(api_user.ApiGetPendingUserNotificationsCountResult)
  @Http("GET", "/api/users/me/notifications/pending/count")
  @NoAuditLogRequired()
  def GetPendingUserNotificationsCount(self, args, token=None):
    """Get number of pending user notifications."""

    raise NotImplementedError()

  @Category("User")
  @ArgsType(api_user.ApiListPendingUserNotificationsArgs)
  @ResultType(api_user.ApiListPendingUserNotificationsResult)
  @Http("GET", "/api/users/me/notifications/pending")
  @NoAuditLogRequired()
  def ListPendingUserNotifications(self, args, token=None):
    """List pending user notifications."""

    raise NotImplementedError()

  @Category("User")
  @ArgsType(api_user.ApiDeletePendingUserNotificationArgs)
  @Http("DELETE", "/api/users/me/notifications/pending/<timestamp>")
  @NoAuditLogRequired()
  def DeletePendingUserNotification(self, args, token=None):
    """Delete pending user notifications."""

    raise NotImplementedError()

  @Category("User")
  @ArgsType(api_user.ApiListAndResetUserNotificationsArgs)
  @ResultType(api_user.ApiListAndResetUserNotificationsResult)
  @Http("POST", "/api/users/me/notifications")
  @NoAuditLogRequired()
  def ListAndResetUserNotifications(self, args, token=None):
    """List user notifications and mark them all as 'seen'."""

    raise NotImplementedError()

  @Category("User")
  @ResultType(api_user.ApiGrrUser)
  @Http("GET", "/api/users/me", strip_root_types=False)
  @NoAuditLogRequired()
  def GetGrrUser(self, args, token=None):
    """Get current user settings."""

    raise NotImplementedError()

  @Category("User")
  @ArgsType(api_user.ApiGrrUser)
  @Http("POST", "/api/users/me")
  @NoAuditLogRequired()
  def UpdateGrrUser(self, args, token=None):
    """Update current user settings."""

    raise NotImplementedError()

  # Config methods.
  # ==============
  #
  @Category("Settings")
  @ResultType(api_config.ApiGetConfigResult)
  @Http("GET", "/api/config")
  @NoAuditLogRequired()
  def GetConfig(self, args, token=None):
    """Get current AdminUI configuration."""

    raise NotImplementedError()

  @Category("Settings")
  @ArgsType(api_config.ApiGetConfigOptionArgs)
  @ResultType(api_config.ApiConfigOption)
  @Http("GET", "/api/config/<name>")
  @NoAuditLogRequired()
  def GetConfigOption(self, args, token=None):
    """Get a single AdminUI configuration option."""

    raise NotImplementedError()

  @Category("Settings")
  @ResultType(api_config.ApiListGrrBinariesResult)
  @Http("GET", "/api/config/binaries")
  @NoAuditLogRequired()
  def ListGrrBinaries(self, args, token=None):
    """List available GRR binaries (uploaded with grr_config_updater)."""

    raise NotImplementedError()

  @Category("Settings")
  @ArgsType(api_config.ApiGetGrrBinaryArgs)
  @ResultType(api_config.ApiGrrBinary)
  @Http("GET", "/api/config/binaries/<type>/<path:path>")
  @NoAuditLogRequired()
  def GetGrrBinary(self, args, token=None):
    """Get information about GRR binary with the following type and path."""

    raise NotImplementedError()

  @Category("Settings")
  @ArgsType(api_config.ApiGetGrrBinaryBlobArgs)
  @ResultBinaryStream()
  @Http("GET", "/api/config/binaries-blobs/<type>/<path:path>")
  @NoAuditLogRequired()
  def GetGrrBinaryBlob(self, args, token=None):
    """Get contents of a GRR binary (uploaded with grr_config_updater)."""

    raise NotImplementedError()

  # Reflection methods.
  # ==================
  #
  @Category("Reflection")
  @ResultType(api_client.ApiListKbFieldsResult)
  @Http("GET", "/api/clients/kb-fields")
  @NoAuditLogRequired()
  def ListKbFields(self, args, token=None):
    """List all available KnowledgeBase fields."""

    raise NotImplementedError()

  @Category("Reflection")
  @ResultType(api_flow.ApiListFlowDescriptorsResult)
  @Http("GET", "/api/flows/descriptors")
  @NoAuditLogRequired()
  def ListFlowDescriptors(self, args, token=None):
    """List descriptors of all the flows."""

    raise NotImplementedError()

  @Category("Reflection")
  @ResultType(api_reflection.ApiListAff4AttributeDescriptorsResult)
  @Http("GET", "/api/reflection/aff4/attributes", strip_root_types=True)
  @NoAuditLogRequired()
  def ListAff4AttributeDescriptors(self, args, token=None):
    """List descriptors of all AFF4 attributes."""

    raise NotImplementedError()

  @Category("Reflection")
  @ArgsType(api_reflection.ApiGetRDFValueDescriptorArgs)
  @ResultType(api_value_renderers.ApiRDFValueDescriptor)
  @Http("GET", "/api/reflection/rdfvalue/<type>", strip_root_types=False)
  @NoAuditLogRequired()
  def GetRDFValueDescriptor(self, args, token=None):
    """Get RDFValue descriptor for a given RDF type."""

    raise NotImplementedError()

  @Category("Reflection")
  @ResultType(api_reflection.ApiListRDFValueDescriptorsResult)
  @Http("GET", "/api/reflection/rdfvalue/all")
  @NoAuditLogRequired()
  def ListRDFValuesDescriptors(self, args, token=None):
    """List all known RDF types descriptors."""

    raise NotImplementedError()

  # Note: fix the name in ApiOutputPluginsListHandler
  @Category("Reflection")
  @ResultType(api_output_plugin.ApiListOutputPluginDescriptorsResult)
  @Http("GET", "/api/output-plugins/all")
  @NoAuditLogRequired()
  def ListOutputPluginDescriptors(self, args, token=None):
    """List all known output plugins descriptors."""

    raise NotImplementedError()

  @Category("Reflection")
  @ResultType(api_vfs.ApiListKnownEncodingsResult)
  @Http("GET", "/api/reflection/file-encodings")
  @NoAuditLogRequired()
  def ListKnownEncodings(self, args, token=None):
    """List all known encodings names."""

    raise NotImplementedError()

  @Category("Reflection")
  @ResultType(api_reflection.ApiListApiMethodsResult)
  @Http("GET", "/api/reflection/api-methods")
  @NoAuditLogRequired()
  def ListApiMethods(self, args, token=None):
    """List all available API methods."""

    raise NotImplementedError()


class DisabledApiCallRouter(ApiCallRouterStub):
  pass
