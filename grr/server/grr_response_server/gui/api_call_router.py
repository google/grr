#!/usr/bin/env python
# Lint as: python3
"""Router classes route API requests to particular handlers."""
from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

import inspect
import re
from typing import Optional
from typing import Text

from grr_response_core.lib.registry import MetaclassRegistry
from grr_response_core.lib.util import compatibility
from grr_response_core.lib.util import precondition
from grr_response_server.gui import api_call_context
from grr_response_server.gui import api_call_handler_base
from grr_response_server.gui import api_value_renderers
from grr_response_server.gui.api_plugins import artifact as api_artifact
from grr_response_server.gui.api_plugins import client as api_client
from grr_response_server.gui.api_plugins import config as api_config
from grr_response_server.gui.api_plugins import cron as api_cron
from grr_response_server.gui.api_plugins import flow as api_flow
from grr_response_server.gui.api_plugins import hunt as api_hunt
from grr_response_server.gui.api_plugins import metadata as api_metadata
from grr_response_server.gui.api_plugins import output_plugin as api_output_plugin
from grr_response_server.gui.api_plugins import reflection as api_reflection
from grr_response_server.gui.api_plugins import stats as api_stats
from grr_response_server.gui.api_plugins import timeline as api_timeline
from grr_response_server.gui.api_plugins import user as api_user
from grr_response_server.gui.api_plugins import vfs as api_vfs
from grr_response_server.gui.api_plugins import yara as api_yara


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

    http_methods.append(
        (self.method, self.path, dict(strip_root_types=self.strip_root_types)))

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
    precondition.AssertType(name, Text)

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


class ApiCallRouter(metaclass=MetaclassRegistry):
  """Routers do ACL checks and route API requests to handlers."""
  __abstract = True  # pylint: disable=g-bad-name

  # If router is configurable, RDFValue class of its configuration
  # structure should be specified here. Params of this type will
  # be initialized from the routers configuration file (defined
  # by API.RouterACLConfigFile) and passed into the constructor
  # using "params" keyword argument.
  params_type = None

  def __init__(self, params=None):
    """Constructor.

    Accepts optional router parameters.

    Args:
      params: None, or an RDFValue instance of params_type.
    """
    super().__init__()
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
  def ListArtifacts(self, args, context=None):
    """List available artifacts definitions."""

    raise NotImplementedError()

  @Category("Artifacts")
  @ArgsType(api_artifact.ApiUploadArtifactArgs)
  @Http("POST", "/api/artifacts")
  @NoAuditLogRequired()
  def UploadArtifact(self, args, context=None):
    """Upload new artifact definition."""

    raise NotImplementedError()

  @Category("Artifacts")
  @ArgsType(api_artifact.ApiDeleteArtifactsArgs)
  @Http("DELETE", "/api/artifacts")
  @NoAuditLogRequired()
  def DeleteArtifacts(self, args, context=None):
    """Delete one of previously uploaded artifacts."""

    raise NotImplementedError()

  # Clients methods.
  # ===============
  #
  @Category("Clients")
  @ArgsType(api_client.ApiSearchClientsArgs)
  @ResultType(api_client.ApiSearchClientsResult)
  @Http("GET", "/api/clients")
  def SearchClients(self, args, context=None):
    """Search for clients using a search query."""

    raise NotImplementedError()

  @Category("Clients")
  @ArgsType(api_client.ApiVerifyAccessArgs)
  @ResultType(api_client.ApiVerifyAccessResult)
  @Http("GET", "/api/clients/<client_id>/access")
  def VerifyAccess(self, args, context=None):
    """Verifies if user has access to a client."""

    raise NotImplementedError()

  @Category("Clients")
  @ArgsType(api_client.ApiGetClientArgs)
  @ResultType(api_client.ApiClient)
  @Http("GET", "/api/clients/<client_id>", strip_root_types=False)
  def GetClient(self, args, context=None):
    """Get client with a given client id."""

    raise NotImplementedError()

  @Category("Clients")
  @ArgsType(api_client.ApiGetClientVersionsArgs)
  @ResultType(api_client.ApiGetClientVersionsResult)
  @Http("GET", "/api/clients/<client_id>/versions")
  def GetClientVersions(self, args, context=None):
    """Get different client versions in a given time range."""

    raise NotImplementedError()

  @Category("Clients")
  @ArgsType(api_client.ApiGetClientVersionTimesArgs)
  @ResultType(api_client.ApiGetClientVersionTimesResult)
  @Http("GET", "/api/clients/<client_id>/version-times")
  def GetClientVersionTimes(self, args, context=None):
    """List available version-times of a client object with a given id."""

    raise NotImplementedError()

  @Category("Clients")
  @ArgsType(api_client.ApiInterrogateClientArgs)
  @ResultType(api_client.ApiInterrogateClientResult)
  @Http("POST", "/api/clients/<client_id>/actions/interrogate")
  def InterrogateClient(self, args, context=None):
    """Inititate client interrogation."""

    raise NotImplementedError()

  @Category("Clients")
  @ArgsType(api_client.ApiGetInterrogateOperationStateArgs)
  @ResultType(api_client.ApiGetInterrogateOperationStateResult)
  @Http("GET",
        "/api/clients/<client_id>/actions/interrogate/<path:operation_id>")
  def GetInterrogateOperationState(self, args, context=None):
    """Get state of a previously started interrogation."""

    raise NotImplementedError()

  @Category("Clients")
  @ArgsType(api_client.ApiGetLastClientIPAddressArgs)
  @ResultType(api_client.ApiGetLastClientIPAddressResult)
  @Http("GET", "/api/clients/<client_id>/last-ip")
  @NoAuditLogRequired()
  def GetLastClientIPAddress(self, args, context=None):
    """Get last known client IP address."""

    raise NotImplementedError()

  @Category("Clients")
  @ArgsType(api_client.ApiListClientCrashesArgs)
  @ResultType(api_client.ApiListClientCrashesResult)
  @Http("GET", "/api/clients/<client_id>/crashes")
  def ListClientCrashes(self, args, context=None):
    """List crashes of a given client."""

    raise NotImplementedError()

  @Category("Clients")
  @ArgsType(api_client.ApiListClientActionRequestsArgs)
  @ResultType(api_client.ApiListClientActionRequestsResult)
  @Http("GET", "/api/clients/<client_id>/action-requests")
  def ListClientActionRequests(self, args, context=None):
    """List pending action requests for a given client."""

    raise NotImplementedError()

  @Category("Clients")
  @ArgsType(api_client.ApiGetClientLoadStatsArgs)
  @ResultType(api_client.ApiGetClientLoadStatsResult)
  @Http("GET", "/api/clients/<client_id>/load-stats/<metric>")
  def GetClientLoadStats(self, args, context=None):
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
  def ListFiles(self, args, context=None):
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
  def GetVfsFilesArchive(self, args, context=None):
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
  def GetFileDetails(self, args, context=None):
    """Get details of a VFS file on a given client."""

    raise NotImplementedError()

  @Category("Vfs")
  @ArgsType(api_vfs.ApiGetFileTextArgs)
  @ResultType(api_vfs.ApiGetFileTextResult)
  @Http("GET", "/api/clients/<client_id>/vfs-text/<path:file_path>")
  def GetFileText(self, args, context=None):
    """Get text file contents of a VFS file on a given client."""

    raise NotImplementedError()

  @Category("Vfs")
  @ArgsType(api_vfs.ApiGetFileBlobArgs)
  @ResultBinaryStream()
  @Http("GET", "/api/clients/<client_id>/vfs-blob/<path:file_path>")
  def GetFileBlob(self, args, context=None):
    """Get byte contents of a VFS file on a given client."""

    raise NotImplementedError()

  @Category("Vfs")
  @ArgsType(api_vfs.ApiGetFileVersionTimesArgs)
  @ResultType(api_vfs.ApiGetFileVersionTimesResult)
  @Http("GET", "/api/clients/<client_id>/vfs-version-times/<path:file_path>")
  def GetFileVersionTimes(self, args, context=None):
    """Get available version times of a VFS file on a given client."""

    raise NotImplementedError()

  @Category("Vfs")
  @ArgsType(api_vfs.ApiGetFileDownloadCommandArgs)
  @ResultType(api_vfs.ApiGetFileDownloadCommandResult)
  @Http("GET", "/api/clients/<client_id>/vfs-download-command/<path:file_path>")
  def GetFileDownloadCommand(self, args, context=None):
    """Get a command line that downloads given VFS file."""

    raise NotImplementedError()

  @Category("Vfs")
  @ArgsType(api_vfs.ApiCreateVfsRefreshOperationArgs)
  @ResultType(api_vfs.ApiCreateVfsRefreshOperationResult)
  @Http("POST", "/api/clients/<client_id>/vfs-refresh-operations")
  def CreateVfsRefreshOperation(self, args, context=None):
    """Start VFS refresh operation (refreshes a given VFS folder)."""

    raise NotImplementedError()

  @Category("Vfs")
  @ArgsType(api_vfs.ApiGetVfsRefreshOperationStateArgs)
  @ResultType(api_vfs.ApiGetVfsRefreshOperationStateResult)
  @Http("GET",
        "/api/clients/<client_id>/vfs-refresh-operations/<path:operation_id>")
  def GetVfsRefreshOperationState(self, args, context=None):
    """Get state of a previously started VFS refresh operation."""

    raise NotImplementedError()

  @Category("Vfs")
  @ArgsType(api_vfs.ApiGetVfsTimelineArgs)
  @ResultType(api_vfs.ApiGetVfsTimelineResult)
  @Http("GET", "/api/clients/<client_id>/vfs-timeline/<path:file_path>")
  def GetVfsTimeline(self, args, context=None):
    """Get event timeline of VFS events for a given VFS path."""

    raise NotImplementedError()

  @Category("Vfs")
  @ArgsType(api_vfs.ApiGetVfsTimelineAsCsvArgs)
  @ResultBinaryStream()
  @Http("GET", "/api/clients/<client_id>/vfs-timeline-csv/<path:file_path>")
  def GetVfsTimelineAsCsv(self, args, context=None):
    """Get event timeline of VFS evetns for a given VFS path in CSV format."""

    raise NotImplementedError()

  @Category("Vfs")
  @ArgsType(api_vfs.ApiUpdateVfsFileContentArgs)
  @ResultType(api_vfs.ApiUpdateVfsFileContentResult)
  @Http("POST", "/api/clients/<client_id>/vfs-update")
  def UpdateVfsFileContent(self, args, context=None):
    """Create request for a new snapshot of the file."""

    raise NotImplementedError()

  @Category("Vfs")
  @ArgsType(api_vfs.ApiGetVfsFileContentUpdateStateArgs)
  @ResultType(api_vfs.ApiGetVfsFileContentUpdateStateResult)
  @Http("GET", "/api/clients/<client_id>/vfs-update/<path:operation_id>")
  def GetVfsFileContentUpdateState(self, args, context=None):
    """Get state of a previously started content update operation."""

    raise NotImplementedError()

  @Category("Vfs")
  @ArgsType(api_vfs.ApiGetFileDecodersArgs)
  @ResultType(api_vfs.ApiGetFileDecodersResult)
  @Http("GET", "/api/clients/<client_id>/vfs-decoders/<path:file_path>")
  def GetFileDecoders(self, args, context=None):
    """Get the decoder names that are applicable to the specified file."""
    raise NotImplementedError()

  @Category("Vfs")
  @ArgsType(api_vfs.ApiGetDecodedFileArgs)
  @ResultBinaryStream()
  @Http("GET", "/api/clients/<client_id>/vfs-decoded-blob/"
        "<decoder_name>/<path:file_path>")
  def GetDecodedFileBlob(self, args, context=None):
    """Get a decoded view of the specified file."""
    raise NotImplementedError()

  # Clients labels methods.
  # ======================
  #
  @Category("Clients")
  @ResultType(api_client.ApiListClientsLabelsResult)
  @Http("GET", "/api/clients/labels")
  @NoAuditLogRequired()
  def ListClientsLabels(self, args, context=None):
    """List all available clients labels."""

    raise NotImplementedError()

  @Category("Clients")
  @ArgsType(api_client.ApiAddClientsLabelsArgs)
  @Http("POST", "/api/clients/labels/add")
  @NoAuditLogRequired()
  def AddClientsLabels(self, args, context=None):
    """Labels given clients with given labels."""

    raise NotImplementedError()

  @Category("Clients")
  @ArgsType(api_client.ApiRemoveClientsLabelsArgs)
  @Http("POST", "/api/clients/labels/remove")
  @NoAuditLogRequired()
  def RemoveClientsLabels(self, args, context=None):
    """Remove given labels from given clients."""

    raise NotImplementedError()

  # Clients flows methods.
  # =====================
  #
  @Category("Flows")
  @ArgsType(api_flow.ApiListFlowsArgs)
  @ResultType(api_flow.ApiListFlowsResult)
  @Http("GET", "/api/clients/<client_id>/flows")
  def ListFlows(self, args, context=None):
    """List flows on a given client."""

    raise NotImplementedError()

  @Category("Flows")
  @ArgsType(api_flow.ApiGetFlowArgs)
  @ResultType(api_flow.ApiFlow)
  @Http(
      "GET",
      "/api/clients/<client_id>/flows/<path:flow_id>",
      strip_root_types=False)
  def GetFlow(self, args, context=None):
    """Get flow details."""

    raise NotImplementedError()

  @Category("Flows")
  @ArgsType(api_flow.ApiCreateFlowArgs)
  @ResultType(api_flow.ApiFlow)
  @Http("POST", "/api/clients/<client_id>/flows", strip_root_types=False)
  def CreateFlow(self, args, context=None):
    """Start a new flow on a given client."""

    raise NotImplementedError()

  @Category("Flows")
  @ArgsType(api_flow.ApiCancelFlowArgs)
  @ResultType(api_flow.ApiFlow)
  @Http("POST", "/api/clients/<client_id>/flows/<path:flow_id>/actions/cancel")
  def CancelFlow(self, args, context=None):
    """Stop given flow on a given client."""

    raise NotImplementedError()

  @Category("Flows")
  @ArgsType(api_flow.ApiListFlowRequestsArgs)
  @ResultType(api_flow.ApiListFlowRequestsResult)
  @Http("GET", "/api/clients/<client_id>/flows/<path:flow_id>/requests")
  def ListFlowRequests(self, args, context=None):
    """List pending action requests of a given flow on a given client."""

    raise NotImplementedError()

  @Category("Flows")
  @ArgsType(api_flow.ApiListFlowResultsArgs)
  @ResultType(api_flow.ApiListFlowResultsResult)
  @Http("GET", "/api/clients/<client_id>/flows/<path:flow_id>/results")
  def ListFlowResults(self, args, context=None):
    """List results of a given flow on a given client."""

    raise NotImplementedError()

  @Category("Flows")
  @ArgsType(api_flow.ApiGetExportedFlowResultsArgs)
  @ResultBinaryStream()
  @Http("GET", "/api/clients/<client_id>/flows/<path:flow_id>/"
        "exported-results/<plugin_name>")
  def GetExportedFlowResults(self, args, context=None):
    """Stream flow results using one of the instant output plugins."""

    raise NotImplementedError()

  @Category("Flows")
  @ArgsType(api_flow.ApiGetFlowResultsExportCommandArgs)
  @ResultType(api_flow.ApiGetFlowResultsExportCommandResult)
  @Http("GET", "/api/clients/<client_id>/flows/<path:flow_id>/results/"
        "export-command")
  def GetFlowResultsExportCommand(self, args, context=None):
    """Get export tool command to export flow results."""

    raise NotImplementedError()

  @Category("Flows")
  @ArgsType(api_flow.ApiGetFlowFilesArchiveArgs)
  @ResultBinaryStream()
  @Http("GET", "/api/clients/<client_id>/flows/<path:flow_id>/results/"
        "files-archive")
  def GetFlowFilesArchive(self, args, context=None):
    """Get ZIP or TAR.GZ archive with files downloaded by the flow."""

    raise NotImplementedError()

  @Category("Flows")
  @ArgsType(api_flow.ApiListFlowOutputPluginsArgs)
  @ResultType(api_flow.ApiListFlowOutputPluginsResult)
  @Http("GET", "/api/clients/<client_id>/flows/<path:flow_id>/output-plugins")
  def ListFlowOutputPlugins(self, args, context=None):
    """List output plugins used by the flow."""

    raise NotImplementedError()

  @Category("Flows")
  @ArgsType(api_flow.ApiListFlowOutputPluginLogsArgs)
  @ResultType(api_flow.ApiListFlowOutputPluginLogsResult)
  @Http("GET", "/api/clients/<client_id>/flows/<path:flow_id>/"
        "output-plugins/<plugin_id>/logs")
  def ListFlowOutputPluginLogs(self, args, context=None):
    """List output plugin logs of the flow."""

    raise NotImplementedError()

  @Category("Flows")
  @ArgsType(api_flow.ApiListFlowOutputPluginErrorsArgs)
  @ResultType(api_flow.ApiListFlowOutputPluginErrorsResult)
  @Http("GET", "/api/clients/<client_id>/flows/<path:flow_id>/"
        "output-plugins/<plugin_id>/errors")
  def ListFlowOutputPluginErrors(self, args, context=None):
    """List output plugin errors of the flow."""

    raise NotImplementedError()

  @Category("Flows")
  @ArgsType(api_flow.ApiListFlowLogsArgs)
  @ResultType(api_flow.ApiListFlowLogsResult)
  @Http("GET", "/api/clients/<client_id>/flows/<path:flow_id>/log")
  def ListFlowLogs(self, args, context=None):
    """List logs of the flow."""

    raise NotImplementedError()

  @Category("Flows")
  @ArgsType(api_timeline.ApiGetCollectedTimelineArgs)
  @ResultBinaryStream()
  @Http("GET", "/api/clients/<client_id>/flows/<flow_id>/timeline/<format>")
  def GetCollectedTimeline(self, args, context=None):
    """Exports results of a timeline flow to the specific format."""
    raise NotImplementedError()

  @Category("Flows")
  @ArgsType(api_yara.ApiUploadYaraSignatureArgs)
  @ResultType(api_yara.ApiUploadYaraSignatureResult)
  @Http("POST", "/api/yara-signatures")
  def UploadYaraSignature(
      self,
      args: api_yara.ApiUploadYaraSignatureArgs,
      context: Optional[api_call_context.ApiCallContext] = None,
  ) -> api_yara.ApiUploadYaraSignatureHandler:
    raise NotImplementedError()

  @Category("Flows")
  @ArgsType(api_flow.ApiExplainGlobExpressionArgs)
  @ResultType(api_flow.ApiExplainGlobExpressionResult)
  @Http("POST", "/api/clients/<client_id>/glob-expressions:explain")
  def ExplainGlobExpression(
      self,
      args: api_flow.ApiExplainGlobExpressionArgs,
      context: Optional[api_call_context.ApiCallContext] = None,
  ) -> api_flow.ApiExplainGlobExpressionHandler:
    raise NotImplementedError()

  @Category("Flows")
  @ArgsType(api_flow.ApiCreateFlowArgs)
  @ResultType(api_flow.ApiScheduledFlow)
  @Http(
      "POST",
      "/api/clients/<client_id>/scheduled-flows",
      strip_root_types=False)
  def ScheduleFlow(
      self,
      args: api_flow.ApiCreateFlowArgs,
      context: Optional[api_call_context.ApiCallContext] = None,
  ) -> api_flow.ApiScheduleFlowHandler:
    """Schedules a flow on a client, to be started upon approval grant."""
    raise NotImplementedError()

  @Category("Flows")
  @ArgsType(api_flow.ApiListScheduledFlowsArgs)
  @ResultType(api_flow.ApiListScheduledFlowsResult)
  @Http("GET", "/api/clients/<client_id>/scheduled-flows/<creator>/")
  def ListScheduledFlows(
      self,
      args: api_flow.ApiListScheduledFlowsArgs,
      context: Optional[api_call_context.ApiCallContext] = None,
  ) -> api_flow.ApiListScheduledFlowsHandler:
    """Lists all scheduled flows from a user on a client."""
    raise NotImplementedError()

  @Category("Flows")
  @ArgsType(api_flow.ApiUnscheduleFlowArgs)
  @ResultType(api_flow.ApiUnscheduleFlowResult)
  @Http("DELETE",
        "/api/clients/<client_id>/scheduled-flows/<scheduled_flow_id>")
  def UnscheduleFlow(
      self,
      args: api_flow.ApiUnscheduleFlowArgs,
      context: Optional[api_call_context.ApiCallContext] = None,
  ) -> api_flow.ApiUnscheduleFlowHandler:
    """Unschedules and deletes a previously scheduled flow."""
    raise NotImplementedError()

  # Cron jobs methods.
  # =================
  #
  @Category("Cron")
  @ArgsType(api_cron.ApiListCronJobsArgs)
  @ResultType(api_cron.ApiListCronJobsResult)
  @NoAuditLogRequired()
  @Http("GET", "/api/cron-jobs")
  def ListCronJobs(self, args, context=None):
    """List available cron jobs."""

    raise NotImplementedError()

  @Category("Cron")
  @ArgsType(api_cron.ApiCreateCronJobArgs)
  @ResultType(api_cron.ApiCronJob)
  @Http("POST", "/api/cron-jobs", strip_root_types=False)
  def CreateCronJob(self, args, context=None):
    """Create new cron job."""

    raise NotImplementedError()

  @Category("Cron")
  @ArgsType(api_cron.ApiGetCronJobArgs)
  @ResultType(api_cron.ApiCronJob)
  @Http("GET", "/api/cron-jobs/<cron_job_id>", strip_root_types=False)
  def GetCronJob(self, args, context=None):
    """Get details of a given cron job."""

    raise NotImplementedError()

  @Category("Cron")
  @ArgsType(api_cron.ApiForceRunCronJobArgs)
  @Http("POST", "/api/cron-jobs/<cron_job_id>/actions/force-run")
  def ForceRunCronJob(self, args, context=None):
    """Force an out-of-schedule run of a given cron job."""

    raise NotImplementedError()

  @Category("Hunts")
  @ArgsType(api_cron.ApiModifyCronJobArgs)
  @ResultType(api_cron.ApiCronJob)
  @Http("PATCH", "/api/cron-jobs/<cron_job_id>", strip_root_types=False)
  def ModifyCronJob(self, args, context=None):
    """Modify cron job (includes enabling/disabling)."""

    raise NotImplementedError()

  @Category("Cron")
  @ArgsType(api_cron.ApiListCronJobRunsArgs)
  @ResultType(api_cron.ApiListCronJobRunsResult)
  @Http("GET", "/api/cron-jobs/<cron_job_id>/runs")
  def ListCronJobRuns(self, args, context=None):
    """List runs initiated by the given cron job."""

    raise NotImplementedError()

  @Category("Cron")
  @ArgsType(api_cron.ApiGetCronJobRunArgs)
  @ResultType(api_cron.ApiCronJobRun)
  @Http(
      "GET",
      "/api/cron-jobs/<cron_job_id>/runs/<run_id>",
      strip_root_types=False)
  def GetCronJobRun(self, args, context=None):
    """Get details of a run started by a cron job."""

    raise NotImplementedError()

  @Category("Cron")
  @ArgsType(api_cron.ApiDeleteCronJobArgs)
  @Http("DELETE", "/api/cron-jobs/<cron_job_id>")
  def DeleteCronJob(self, args, context=None):
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
  def ListHunts(self, args, context=None):
    """List hunts."""

    raise NotImplementedError()

  @Category("Hunts")
  @ArgsType(api_hunt.ApiGetHuntArgs)
  @ResultType(api_hunt.ApiHunt)
  @Http("GET", "/api/hunts/<hunt_id>", strip_root_types=False)
  def GetHunt(self, args, context=None):
    """Get details of a hunt with a given id."""

    raise NotImplementedError()

  @Category("Hunts")
  @ArgsType(api_hunt.ApiListHuntErrorsArgs)
  @ResultType(api_hunt.ApiListHuntErrorsResult)
  @Http("GET", "/api/hunts/<hunt_id>/errors")
  def ListHuntErrors(self, args, context=None):
    """List hunt errors."""

    raise NotImplementedError()

  @Category("Hunts")
  @ArgsType(api_hunt.ApiListHuntLogsArgs)
  @ResultType(api_hunt.ApiListHuntLogsResult)
  # TODO(user): change "log" to "logs"
  @Http("GET", "/api/hunts/<hunt_id>/log")
  def ListHuntLogs(self, args, context=None):
    """List hunt logs."""

    raise NotImplementedError()

  @Category("Hunts")
  @ArgsType(api_hunt.ApiListHuntResultsArgs)
  @ResultType(api_hunt.ApiListHuntResultsResult)
  @Http("GET", "/api/hunts/<hunt_id>/results")
  def ListHuntResults(self, args, context=None):
    """List hunt results."""

    raise NotImplementedError()

  @Category("Hunts")
  @ArgsType(api_hunt.ApiGetExportedHuntResultsArgs)
  @ResultBinaryStream()
  @Http("GET", "/api/hunts/<hunt_id>/exported-results/<plugin_name>")
  def GetExportedHuntResults(self, args, context=None):
    """Stream hunt results using one of the instant output plugins."""

    raise NotImplementedError()

  @Category("Hunts")
  @ArgsType(api_hunt.ApiGetHuntResultsExportCommandArgs)
  @ResultType(api_hunt.ApiGetHuntResultsExportCommandResult)
  @Http("GET", "/api/hunts/<hunt_id>/results/export-command")
  def GetHuntResultsExportCommand(self, args, context=None):
    """Get export command that exports hunt results."""

    raise NotImplementedError()

  @Category("Hunts")
  @ArgsType(api_hunt.ApiListHuntOutputPluginsArgs)
  @ResultType(api_hunt.ApiListHuntOutputPluginsResult)
  @Http("GET", "/api/hunts/<hunt_id>/output-plugins")
  def ListHuntOutputPlugins(self, args, context=None):
    """List output plugins used by the hunt."""

    raise NotImplementedError()

  @Category("Hunts")
  @ArgsType(api_hunt.ApiListHuntOutputPluginLogsArgs)
  @ResultType(api_hunt.ApiListHuntOutputPluginLogsResult)
  @Http("GET", "/api/hunts/<hunt_id>/output-plugins/<plugin_id>/logs")
  def ListHuntOutputPluginLogs(self, args, context=None):
    """List hunt output plugins logs."""

    raise NotImplementedError()

  @Category("Hunts")
  @ArgsType(api_hunt.ApiListHuntOutputPluginErrorsArgs)
  @ResultType(api_hunt.ApiListHuntOutputPluginErrorsResult)
  @Http("GET", "/api/hunts/<hunt_id>/output-plugins/<plugin_id>/errors")
  def ListHuntOutputPluginErrors(self, args, context=None):
    """List hunt output plugins errors."""

    raise NotImplementedError()

  @Category("Hunts")
  @ArgsType(api_hunt.ApiListHuntCrashesArgs)
  @ResultType(api_hunt.ApiListHuntCrashesResult)
  @Http("GET", "/api/hunts/<hunt_id>/crashes")
  def ListHuntCrashes(self, args, context=None):
    """List all crashes caused by the hunt."""

    raise NotImplementedError()

  @Category("Hunts")
  @ArgsType(api_hunt.ApiGetHuntClientCompletionStatsArgs)
  @ResultType(api_hunt.ApiGetHuntClientCompletionStatsResult)
  @Http("GET", "/api/hunts/<hunt_id>/client-completion-stats")
  def GetHuntClientCompletionStats(self, args, context=None):
    """Get hunt completion stats."""

    raise NotImplementedError()

  @Category("Hunts")
  @ArgsType(api_hunt.ApiGetHuntStatsArgs)
  @ResultType(api_hunt.ApiGetHuntStatsResult)
  @Http("GET", "/api/hunts/<hunt_id>/stats")
  def GetHuntStats(self, args, context=None):
    """Get general hunt stats."""

    raise NotImplementedError()

  @Category("Hunts")
  @ArgsType(api_hunt.ApiListHuntClientsArgs)
  @ResultType(api_hunt.ApiListHuntClientsResult)
  @Http("GET", "/api/hunts/<hunt_id>/clients/<client_status>")
  def ListHuntClients(self, args, context=None):
    """List clients involved into the hunt."""

    raise NotImplementedError()

  @Category("Hunts")
  @ArgsType(api_hunt.ApiGetHuntContextArgs)
  @ResultType(api_hunt.ApiGetHuntContextResult)
  @Http("GET", "/api/hunts/<hunt_id>/context")
  def GetHuntContext(self, args, context=None):
    """Get a low-level hunt context (useful for debugging)."""

    raise NotImplementedError()

  @Category("Hunts")
  @ArgsType(api_hunt.ApiCreateHuntArgs)
  @ResultType(api_hunt.ApiHunt)
  @Http("POST", "/api/hunts", strip_root_types=False)
  def CreateHunt(self, args, context=None):
    """Create a new hunt."""

    raise NotImplementedError()

  @Category("Hunts")
  @ArgsType(api_hunt.ApiModifyHuntArgs)
  @ResultType(api_hunt.ApiHunt)
  @Http("PATCH", "/api/hunts/<hunt_id>", strip_root_types=False)
  def ModifyHunt(self, args, context=None):
    """Modify hunt (includes stopping/starting)."""

    raise NotImplementedError()

  @Category("Hunts")
  @ArgsType(api_hunt.ApiDeleteHuntArgs)
  @Http("DELETE", "/api/hunts/<hunt_id>", strip_root_types=False)
  def DeleteHunt(self, args, context=None):
    """Delete a hunt with all its data."""

    raise NotImplementedError()

  @Category("Hunts")
  @ArgsType(api_hunt.ApiGetHuntFilesArchiveArgs)
  @ResultBinaryStream()
  @Http("GET", "/api/hunts/<hunt_id>/results/files-archive")
  def GetHuntFilesArchive(self, args, context=None):
    """Get ZIP or TAR.GZ archive with all the files downloaded by the hunt."""

    raise NotImplementedError()

  @Category("Hunts")
  @ArgsType(api_hunt.ApiGetHuntFileArgs)
  @ResultBinaryStream()
  @Http("GET", "/api/hunts/<hunt_id>/results/clients/<client_id>/vfs-blob"
        "/<path:vfs_path>")
  def GetHuntFile(self, args, context=None):
    """Get a file referenced by one of the hunt results."""

    raise NotImplementedError()

  @Category("Hunts")
  @ArgsType(api_timeline.ApiGetCollectedHuntTimelinesArgs)
  @ResultBinaryStream()
  @Http("GET", "/api/hunts/<hunt_id>/timelines/<format>")
  def GetCollectedHuntTimelines(
      self,
      args: api_timeline.ApiGetCollectedHuntTimelinesArgs,
      context: Optional[api_call_context.ApiCallContext] = None,
  ) -> api_timeline.ApiGetCollectedHuntTimelinesHandler:
    """Exports results of a timeline hunt.

    The results are exported as a ZIP archive whose files follow the specified
    format. Each file in the ZIP archive contains results for a particular
    client.

    Args:
      args: The timeline hunt export request arguments.
      context: The API call context.

    Returns:
      An API handler for the timeline hunt export.
    """
    raise NotImplementedError()

  @Category("Hunts")
  @ArgsType(api_hunt.ApiCreatePerClientFileCollectionHuntArgs)
  @ResultType(api_hunt.ApiHunt)
  @Http("POST", "/api/hunts/per-client-file-collection", strip_root_types=False)
  def CreatePerClientFileCollectionHunt(
      self, args: api_hunt.ApiCreatePerClientFileCollectionHuntArgs,
      context: api_call_context.ApiCallContext
  ) -> api_call_handler_base.ApiCallHandler:
    """Create a new per-client file collection hunt."""
    raise NotImplementedError()

  # Stats metrics methods.
  # =====================
  #
  # TODO(user,user): Change the naming convention from stats to reports
  # throughout the codebase.
  @Category("Other")
  @Http("GET", "/api/stats/reports")
  @ResultType(api_stats.ApiListReportsResult)
  def ListReports(self, args, context=None):
    """List available stats reports."""

    raise NotImplementedError()

  @Category("Other")
  @Http("GET", "/api/stats/reports/<name>")
  @ArgsType(api_stats.ApiGetReportArgs)
  @ResultType(api_stats.rdf_report_plugins.ApiReport)
  def GetReport(self, args, context=None):
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
  def CreateClientApproval(self, args, context=None):
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
  def GetClientApproval(self, args, context=None):
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
  def GrantClientApproval(self, args, context=None):
    """Grant client approval."""

    raise NotImplementedError()

  @Category("User")
  @ArgsType(api_user.ApiListClientApprovalsArgs)
  @ResultType(api_user.ApiListClientApprovalsResult)
  @NoAuditLogRequired()
  @Http("GET", "/api/users/me/approvals/client")
  @Http("GET", "/api/users/me/approvals/client/<client_id>")
  def ListClientApprovals(self, args, context=None):
    """List client approvals of a current user in reversed timestamp order."""

    raise NotImplementedError()

  @Category("User")
  @ArgsType(api_user.ApiCreateHuntApprovalArgs)
  @ResultType(api_user.ApiHuntApproval)
  @NoAuditLogRequired()
  @Http(
      "POST", "/api/users/me/approvals/hunt/<hunt_id>", strip_root_types=False)
  def CreateHuntApproval(self, args, context=None):
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
  def GetHuntApproval(self, args, context=None):
    """Get hunt approval identified by approval id, hunt id and username."""
    raise NotImplementedError()

  @Category("User")
  @ArgsType(api_user.ApiGrantHuntApprovalArgs)
  @ResultType(api_user.ApiHuntApproval)
  @Http(
      "POST", "/api/users/<username>/approvals/hunt/<hunt_id>/<approval_id>/"
      "actions/grant",
      strip_root_types=False)
  def GrantHuntApproval(self, args, context=None):
    """Grant hunt approval."""

    raise NotImplementedError()

  @Category("User")
  @ArgsType(api_user.ApiListHuntApprovalsArgs)
  @ResultType(api_user.ApiListHuntApprovalsResult)
  @NoAuditLogRequired()
  @Http("GET", "/api/users/me/approvals/hunt")
  def ListHuntApprovals(self, args, context=None):
    """List hunt approvals of a current user."""

    raise NotImplementedError()

  @Category("User")
  @ArgsType(api_user.ApiCreateCronJobApprovalArgs)
  @ResultType(api_user.ApiCronJobApproval)
  @Http(
      "POST",
      "/api/users/me/approvals/cron-job/<cron_job_id>",
      strip_root_types=False)
  def CreateCronJobApproval(self, args, context=None):
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
  def GetCronJobApproval(self, args, context=None):
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
  def GrantCronJobApproval(self, args, context=None):
    """Grant cron job approval."""

    raise NotImplementedError()

  @Category("User")
  @ArgsType(api_user.ApiListCronJobApprovalsArgs)
  @ResultType(api_user.ApiListCronJobApprovalsResult)
  @NoAuditLogRequired()
  @Http("GET", "/api/users/me/approvals/cron-job")
  def ListCronJobApprovals(self, args, context=None):
    """List cron job approvals of a current user."""

    raise NotImplementedError()

  @Category("User")
  @ArgsType(api_user.ApiListApproverSuggestionsArgs)
  @ResultType(api_user.ApiListApproverSuggestionsResult)
  @Http("GET", "/api/users/approver-suggestions")
  def ListApproverSuggestions(self, args, context=None):
    """List suggestions for approver usernames."""

    raise NotImplementedError()

  # User settings methods.
  # =====================
  #
  @Category("User")
  @ResultType(api_user.ApiGetPendingUserNotificationsCountResult)
  @Http("GET", "/api/users/me/notifications/pending/count")
  @NoAuditLogRequired()
  def GetPendingUserNotificationsCount(self, args, context=None):
    """Get number of pending user notifications."""

    raise NotImplementedError()

  @Category("User")
  @ArgsType(api_user.ApiListPendingUserNotificationsArgs)
  @ResultType(api_user.ApiListPendingUserNotificationsResult)
  @Http("GET", "/api/users/me/notifications/pending")
  @NoAuditLogRequired()
  def ListPendingUserNotifications(self, args, context=None):
    """List pending user notifications."""

    raise NotImplementedError()

  @Category("User")
  @ArgsType(api_user.ApiDeletePendingUserNotificationArgs)
  @Http("DELETE", "/api/users/me/notifications/pending/<timestamp>")
  @NoAuditLogRequired()
  def DeletePendingUserNotification(self, args, context=None):
    """Delete pending user notifications."""

    raise NotImplementedError()

  @Category("User")
  @ArgsType(api_user.ApiListAndResetUserNotificationsArgs)
  @ResultType(api_user.ApiListAndResetUserNotificationsResult)
  @Http("POST", "/api/users/me/notifications")
  @NoAuditLogRequired()
  def ListAndResetUserNotifications(self, args, context=None):
    """List user notifications and mark them all as 'seen'."""

    raise NotImplementedError()

  @Category("User")
  @ResultType(api_user.ApiGrrUser)
  @Http("GET", "/api/users/me", strip_root_types=False)
  @NoAuditLogRequired()
  def GetGrrUser(self, args, context=None):
    """Get current user settings."""

    raise NotImplementedError()

  @Category("User")
  @ArgsType(api_user.ApiGrrUser)
  @Http("POST", "/api/users/me")
  @NoAuditLogRequired()
  def UpdateGrrUser(self, args, context=None):
    """Update current user settings."""

    raise NotImplementedError()

  # Config methods.
  # ==============
  #
  @Category("Settings")
  @ResultType(api_config.ApiGetConfigResult)
  @Http("GET", "/api/config")
  @NoAuditLogRequired()
  def GetConfig(self, args, context=None):
    """Get current AdminUI configuration."""

    raise NotImplementedError()

  @Category("Settings")
  @ArgsType(api_config.ApiGetConfigOptionArgs)
  @ResultType(api_config.ApiConfigOption)
  @Http("GET", "/api/config/<name>")
  @NoAuditLogRequired()
  def GetConfigOption(self, args, context=None):
    """Get a single AdminUI configuration option."""

    raise NotImplementedError()

  @Category("Settings")
  @ResultType(api_config.ApiListGrrBinariesResult)
  @Http("GET", "/api/config/binaries")
  @NoAuditLogRequired()
  def ListGrrBinaries(self, args, context=None):
    """List available GRR binaries (uploaded with grr_config_updater)."""

    raise NotImplementedError()

  @Category("Settings")
  @ArgsType(api_config.ApiGetGrrBinaryArgs)
  @ResultType(api_config.ApiGrrBinary)
  @Http("GET", "/api/config/binaries/<type>/<path:path>")
  @NoAuditLogRequired()
  def GetGrrBinary(self, args, context=None):
    """Get information about GRR binary with the following type and path."""

    raise NotImplementedError()

  @Category("Settings")
  @ArgsType(api_config.ApiGetGrrBinaryBlobArgs)
  @ResultBinaryStream()
  @Http("GET", "/api/config/binaries-blobs/<type>/<path:path>")
  @NoAuditLogRequired()
  def GetGrrBinaryBlob(self, args, context=None):
    """Get contents of a GRR binary (uploaded with grr_config_updater)."""

    raise NotImplementedError()

  @Category("Settings")
  @ResultType(api_config.ApiUiConfig)
  @Http("GET", "/api/config/ui")
  @NoAuditLogRequired()
  def GetUiConfig(self, args, context=None):
    """Get configuration values for AdminUI (e.g. heading name, help url)."""

    raise NotImplementedError()

  # Reflection methods.
  # ==================
  #
  @Category("Reflection")
  @ResultType(api_client.ApiListKbFieldsResult)
  @Http("GET", "/api/clients/kb-fields")
  @NoAuditLogRequired()
  def ListKbFields(self, args, context=None):
    """List all available KnowledgeBase fields."""

    raise NotImplementedError()

  @Category("Reflection")
  @ResultType(api_flow.ApiListFlowDescriptorsResult)
  @Http("GET", "/api/flows/descriptors")
  @NoAuditLogRequired()
  def ListFlowDescriptors(self, args, context=None):
    """List descriptors of all the flows."""

    raise NotImplementedError()

  @Category("Reflection")
  @ArgsType(api_reflection.ApiGetRDFValueDescriptorArgs)
  @ResultType(api_value_renderers.ApiRDFValueDescriptor)
  @Http("GET", "/api/reflection/rdfvalue/<type>", strip_root_types=False)
  @NoAuditLogRequired()
  def GetRDFValueDescriptor(self, args, context=None):
    """Get RDFValue descriptor for a given RDF type."""

    raise NotImplementedError()

  @Category("Reflection")
  @ResultType(api_reflection.ApiListRDFValueDescriptorsResult)
  @Http("GET", "/api/reflection/rdfvalue/all")
  @NoAuditLogRequired()
  def ListRDFValuesDescriptors(self, args, context=None):
    """List all known RDF types descriptors."""

    raise NotImplementedError()

  # Note: fix the name in ApiOutputPluginsListHandler
  @Category("Reflection")
  @ResultType(api_output_plugin.ApiListOutputPluginDescriptorsResult)
  @Http("GET", "/api/output-plugins/all")
  @NoAuditLogRequired()
  def ListOutputPluginDescriptors(self, args, context=None):
    """List all known output plugins descriptors."""

    raise NotImplementedError()

  @Category("Reflection")
  @ResultType(api_vfs.ApiListKnownEncodingsResult)
  @Http("GET", "/api/reflection/file-encodings")
  @NoAuditLogRequired()
  def ListKnownEncodings(self, args, context=None):
    """List all known encodings names."""

    raise NotImplementedError()

  @Category("Reflection")
  @ResultType(api_reflection.ApiListApiMethodsResult)
  @Http("GET", "/api/reflection/api-methods")
  @NoAuditLogRequired()
  def ListApiMethods(self, args, context=None):
    """List all available API methods."""

    raise NotImplementedError()

  @Category("Metadata")
  @ResultType(api_metadata.ApiGetGrrVersionResult)
  @Http("GET", "/api/metadata/version")
  @NoAuditLogRequired()
  def GetGrrVersion(
      self,
      args: None,
      context: Optional[api_call_context.ApiCallContext] = None,
  ) -> api_metadata.ApiGetGrrVersionHandler:
    """Returns version of the GRR server."""
    raise NotImplementedError()

  @Category("Metadata")
  @ResultType(api_metadata.ApiGetOpenApiDescriptionResult)
  @Http("GET", "/api/metadata/openapi")
  @NoAuditLogRequired()
  def GetOpenApiDescription(
      self,
      args: None,
      context: Optional[api_call_context.ApiCallContext] = None,
  ) -> api_metadata.ApiGetOpenApiDescriptionHandler:
    """Returns a description of the API following the OpenAPI specification.

    Args:
      args: None, this API method does not require any arguments.
      context: the API call context.

    Returns:
      An ApiGetOpenApiDescriptionHandler object whose Handle method is used to
      create and return the OpenAPI description of the GRR API.
    """
    raise NotImplementedError()


class DisabledApiCallRouter(ApiCallRouterStub):
  pass
