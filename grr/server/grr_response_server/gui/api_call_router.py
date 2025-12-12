#!/usr/bin/env python
"""Router classes route API requests to particular handlers."""

import inspect
import re
from typing import Optional

from grr_response_core.lib.util import precondition
from grr_response_proto.api import artifact_pb2 as api_artifact_pb2
from grr_response_proto.api import client_pb2 as api_client_pb2
from grr_response_proto.api import config_pb2 as api_config_pb2
from grr_response_proto.api import cron_pb2 as api_cron_pb2
from grr_response_proto.api import flow_pb2 as api_flow_pb2
from grr_response_proto.api import hunt_pb2 as api_hunt_pb2
from grr_response_proto.api import metadata_pb2 as api_metadata_pb2
from grr_response_proto.api import osquery_pb2 as api_osquery_pb2
from grr_response_proto.api import reflection_pb2 as api_reflection_pb2
from grr_response_proto.api import signed_commands_pb2 as api_signed_commands_pb2
from grr_response_proto.api import timeline_pb2 as api_timeline_pb2
from grr_response_proto.api import user_pb2 as api_user_pb2
from grr_response_proto.api import vfs_pb2 as api_vfs_pb2
from grr_response_proto.api import yara_pb2 as api_yara_pb2
from grr_response_server import access_control
from grr_response_server.gui import api_call_context
from grr_response_server.gui.api_plugins import client as api_client
from grr_response_server.gui.api_plugins import flow as api_flow
from grr_response_server.gui.api_plugins import metadata as api_metadata
from grr_response_server.gui.api_plugins import signed_commands as api_signed_commands
from grr_response_server.gui.api_plugins import timeline as api_timeline
from grr_response_server.gui.api_plugins import vfs as api_vfs


_TYPE_URL_PREFIX: str = "type.googleapis.com/"


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

    http_methods.append((self.method, self.path))

    return func


class ProtoArgsType:
  """Decorator that specifies the proto args type of an API method."""

  def __init__(self, proto_args_type):
    self.proto_args_type = proto_args_type

  def __call__(self, func):
    func.__proto_args_type__ = self.proto_args_type
    return func


class ProtoResultType:
  """Decorator that specifies the proto result type of an API method."""

  def __init__(self, proto_result_type):
    self.proto_result_type = proto_result_type

  def __call__(self, func):
    func.__proto_result_type__ = self.proto_result_type
    return func


class ResultBinaryStream(object):
  """Decorator indicating this API methods will produce a binary stream."""

  def __call__(self, func):
    func.__is_streaming__ = True
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

  def __init__(
      self,
      name,
      doc=None,
      proto_args_type=None,
      args_type_url=None,
      proto_result_type=None,
      result_type_url=None,
      is_streaming=False,
      category=None,
      http_methods=None,
      no_audit_log_required=False,
  ):
    precondition.AssertType(name, str)

    self.name = name
    self.doc = doc
    self.proto_args_type = proto_args_type
    self.args_type_url = args_type_url
    self.proto_result_type = proto_result_type
    self.result_type_url = result_type_url
    self.is_streaming = is_streaming
    self.category = category
    self.http_methods = http_methods or set()
    self.no_audit_log_required = no_audit_log_required

  _RULE_REGEX = re.compile("<([a-zA-Z0-9:_]+)")

  def GetQueryParamsNames(self):
    """Extracts all mandatory and optional parameters from URLs for logging.

    This extracts names of all mandatory parameters that are sent inside the
    URL path for a given route. For example, the path
    /api/clients/<client_id>/last-ip would return ["client_id"].

    For GET requests the returned list will also include optional
    query paramerters. For example, /api/clients?query=... will
    return ["query"]. For non-GET HTTP methods no optional parameters will
    be included into the result.

    Some URL paths contain annotated parameters - for example paths as
    in /api/clients/<client_id>/vfs-index/<path:file_path>. Those
    annotations will be stripped off by this function and just the
    plain parameter name will be returned.

    Returns:
      A list of extracted parameters.
    """
    result = []
    found = set()
    for method, path in self.http_methods or []:
      for arg in re.findall(self._RULE_REGEX, path):
        if ":" in arg:
          arg = arg[arg.find(":") + 1 :]
        result.append(arg)
        found.add(arg)

      if method == "GET" and self.proto_args_type is not None:
        args_proto = self.proto_args_type()
        for field_name in args_proto.DESCRIPTOR.fields_by_name:
          if field_name not in found:
            result.append(field_name)
            found.add(field_name)

    return result


class ApiCallRouter:
  """Routers do ACL checks and route API requests to handlers."""

  __abstract = True  # pylint: disable=g-bad-name

  # If router is configurable, the proto class of its configuration
  # structure should be specified here. Params of this type will
  # be initialized from the routers' configuration file (defined
  # by API.RouterACLConfigFile) and passed into the constructor
  # using the "params" keyword argument.
  proto_params_type = None

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
      for name in dir(i_cls):
        cls_method = getattr(i_cls, name)

        if not callable(cls_method):
          continue

        if not hasattr(cls_method, "__http_methods__"):
          continue

        if hasattr(cls_method, "__proto_args_type__"):
          args_type_url = (
              _TYPE_URL_PREFIX
              + cls_method.__proto_args_type__.DESCRIPTOR.full_name
          )
        else:
          args_type_url = None

        if hasattr(cls_method, "__proto_result_type__"):
          result_type_url = (
              _TYPE_URL_PREFIX
              + cls_method.__proto_result_type__.DESCRIPTOR.full_name
          )
        else:
          result_type_url = None

        result[name] = RouterMethodMetadata(
            name=name,
            doc=cls_method.__doc__,
            proto_args_type=getattr(cls_method, "__proto_args_type__", None),
            args_type_url=args_type_url,
            proto_result_type=getattr(
                cls_method, "__proto_result_type__", None
            ),
            result_type_url=result_type_url,
            is_streaming=getattr(cls_method, "__is_streaming__", False),
            category=getattr(cls_method, "__category__", None),
            http_methods=getattr(cls_method, "__http_methods__", set()),
            no_audit_log_required=getattr(
                cls_method, "__no_audit_log_required__", False
            ),
        )

    return result


class ApiCallRouterStub(ApiCallRouter):
  """Default router stub with methods definitions only."""

  # Artifacts methods.
  # =================
  #
  @Category("Artifacts")
  @ProtoArgsType(api_artifact_pb2.ApiListArtifactsArgs)
  @ProtoResultType(api_artifact_pb2.ApiListArtifactsResult)
  @Http("GET", "/api/v2/artifacts")
  @NoAuditLogRequired()
  def ListArtifacts(
      self,
      args: api_artifact_pb2.ApiListArtifactsArgs,
      context: Optional[api_call_context.ApiCallContext] = None,
  ):
    """List available artifacts definitions."""

    raise NotImplementedError()

  @Category("Artifacts")
  @ProtoArgsType(api_artifact_pb2.ApiUploadArtifactArgs)
  @Http("POST", "/api/v2/artifacts")
  @NoAuditLogRequired()
  def UploadArtifact(
      self,
      args: api_artifact_pb2.ApiUploadArtifactArgs,
      context: Optional[api_call_context.ApiCallContext] = None,
  ):
    """Upload new artifact definition."""

    raise NotImplementedError()

  @Category("Artifacts")
  @ProtoArgsType(api_artifact_pb2.ApiDeleteArtifactsArgs)
  @Http("DELETE", "/api/v2/artifacts")
  @NoAuditLogRequired()
  def DeleteArtifacts(
      self,
      args: api_artifact_pb2.ApiDeleteArtifactsArgs,
      context: Optional[api_call_context.ApiCallContext] = None,
  ):
    """Delete one of previously uploaded artifacts."""

    raise NotImplementedError()

  # Clients methods.
  # ===============
  #
  @Category("Clients")
  @ProtoArgsType(api_client_pb2.ApiSearchClientsArgs)
  @ProtoResultType(api_client_pb2.ApiSearchClientsResult)
  @Http("GET", "/api/v2/clients")
  def SearchClients(
      self,
      args: api_client_pb2.ApiSearchClientsArgs,
      context: Optional[api_call_context.ApiCallContext] = None,
  ):
    """Search for clients using a search query."""

    raise NotImplementedError()

  @Category("Clients")
  @ProtoArgsType(api_client_pb2.ApiVerifyAccessArgs)
  @ProtoResultType(api_client_pb2.ApiVerifyAccessResult)
  @Http("GET", "/api/v2/clients/<client_id>/access")
  def VerifyAccess(
      self,
      args: api_client_pb2.ApiVerifyAccessArgs,
      context: Optional[api_call_context.ApiCallContext] = None,
  ):
    """Verifies if user has access to a client."""

    raise NotImplementedError()

  @Category("Clients")
  @ProtoArgsType(api_client_pb2.ApiGetClientArgs)
  @ProtoResultType(api_client_pb2.ApiClient)
  @Http("GET", "/api/v2/clients/<client_id>")
  def GetClient(
      self,
      args: api_client_pb2.ApiGetClientArgs,
      context: Optional[api_call_context.ApiCallContext] = None,
  ):
    """Get client with a given client id."""

    raise NotImplementedError()

  @Category("Clients")
  @ProtoArgsType(api_client_pb2.ApiGetClientSnapshotsArgs)
  @ProtoResultType(api_client_pb2.ApiGetClientSnapshotsResult)
  @Http("GET", "/api/v2/clients/<client_id>/snapshots")
  def GetClientSnapshots(
      self,
      args: api_client_pb2.ApiGetClientSnapshotsArgs,
      context: Optional[api_call_context.ApiCallContext] = None,
  ):
    """Get different client snapshots in a given time range.

    Args:
      args: The request arguments.
      context: The API call context.
    """

    raise NotImplementedError()

  @Category("Clients")
  @ProtoArgsType(api_client_pb2.ApiGetClientStartupInfosArgs)
  @ProtoResultType(api_client_pb2.ApiGetClientStartupInfosResult)
  @Http("GET", "/api/v2/clients/<client_id>/startup-infos")
  def GetClientStartupInfos(
      self,
      args: api_client_pb2.ApiGetClientStartupInfosArgs,
      context: Optional[api_call_context.ApiCallContext] = None,
  ):
    """Get different client startup infos in a given time range.

    Args:
      args: The request arguments.
      context: The API call context.
    """

    raise NotImplementedError()

  @Category("Clients")
  @ProtoArgsType(api_client_pb2.ApiGetClientVersionsArgs)
  @ProtoResultType(api_client_pb2.ApiGetClientVersionsResult)
  @Http("GET", "/api/v2/clients/<client_id>/versions")
  def GetClientVersions(
      self,
      args: api_client_pb2.ApiGetClientVersionsArgs,
      context: Optional[api_call_context.ApiCallContext] = None,
  ):
    """Get different client versions in a given time range."""

    raise NotImplementedError()

  @Category("Clients")
  @ProtoArgsType(api_client_pb2.ApiGetClientVersionTimesArgs)
  @ProtoResultType(api_client_pb2.ApiGetClientVersionTimesResult)
  @Http("GET", "/api/v2/clients/<client_id>/version-times")
  def GetClientVersionTimes(
      self,
      args: api_client_pb2.ApiGetClientVersionTimesArgs,
      context: Optional[api_call_context.ApiCallContext] = None,
  ):
    """List available version-times of a client object with a given id."""

    raise NotImplementedError()

  @Category("Clients")
  @ProtoArgsType(api_client_pb2.ApiInterrogateClientArgs)
  @ProtoResultType(api_client_pb2.ApiInterrogateClientResult)
  @Http("POST", "/api/v2/clients/<client_id>/actions/interrogate")
  def InterrogateClient(
      self,
      args: api_client_pb2.ApiInterrogateClientArgs,
      context: Optional[api_call_context.ApiCallContext] = None,
  ):
    """Initiate client interrogation."""

    raise NotImplementedError()

  @Category("Clients")
  @ProtoArgsType(api_client_pb2.ApiGetLastClientIPAddressArgs)
  @ProtoResultType(api_client_pb2.ApiGetLastClientIPAddressResult)
  @Http("GET", "/api/v2/clients/<client_id>/last-ip")
  @NoAuditLogRequired()
  def GetLastClientIPAddress(
      self,
      args: api_client_pb2.ApiGetLastClientIPAddressArgs,
      context: Optional[api_call_context.ApiCallContext] = None,
  ):
    """Get last known client IP address."""

    raise NotImplementedError()

  @Category("Clients")
  @ProtoArgsType(api_client_pb2.ApiListClientCrashesArgs)
  @ProtoResultType(api_client_pb2.ApiListClientCrashesResult)
  @Http("GET", "/api/v2/clients/<client_id>/crashes")
  def ListClientCrashes(
      self,
      args: api_client_pb2.ApiListClientCrashesArgs,
      context: Optional[api_call_context.ApiCallContext] = None,
  ):
    """List crashes of a given client."""

    raise NotImplementedError()

  @Category("Clients")
  @ProtoArgsType(api_client_pb2.ApiKillFleetspeakArgs)
  @Http("PATCH", "/api/v2/clients/<client_id>/fleetspeak/kill")
  def KillFleetspeak(
      self,
      args: api_client_pb2.ApiKillFleetspeakArgs,
      context: Optional[api_call_context.ApiCallContext] = None,
  ) -> api_client.ApiKillFleetspeakHandler:
    raise NotImplementedError()

  @Category("Clients")
  @ProtoArgsType(api_client_pb2.ApiRestartFleetspeakGrrServiceArgs)
  @Http("PATCH", "/api/v2/clients/<client_id>/fleetspeak/grr/restart")
  def RestartFleetspeakGrrService(
      self,
      args: api_client_pb2.ApiRestartFleetspeakGrrServiceArgs,
      context: Optional[api_call_context.ApiCallContext] = None,
  ) -> api_client.ApiRestartFleetspeakGrrServiceHandler:
    raise NotImplementedError()

  @Category("Clients")
  @ProtoArgsType(api_client_pb2.ApiDeleteFleetspeakPendingMessagesArgs)
  @Http("DELETE", "/api/v2/clients/<client_id>/fleetspeak/messages/pending")
  def DeleteFleetspeakPendingMessages(
      self,
      args: api_client_pb2.ApiDeleteFleetspeakPendingMessagesArgs,
      context: Optional[api_call_context.ApiCallContext] = None,
  ) -> api_client.ApiDeleteFleetspeakPendingMessagesHandler:
    raise NotImplementedError()

  @Category("Clients")
  @ProtoArgsType(api_client_pb2.ApiGetFleetspeakPendingMessagesArgs)
  @ProtoResultType(api_client_pb2.ApiGetFleetspeakPendingMessagesResult)
  @Http("GET", "/api/v2/clients/<client_id>/fleetspeak/messages/pending")
  def GetFleetspeakPendingMessages(
      self,
      args: api_client_pb2.ApiGetFleetspeakPendingMessagesArgs,
      context: Optional[api_call_context.ApiCallContext] = None,
  ) -> api_client.ApiGetFleetspeakPendingMessagesHandler:
    raise NotImplementedError()

  @Category("Clients")
  @ProtoArgsType(api_client_pb2.ApiGetFleetspeakPendingMessageCountArgs)
  @ProtoResultType(api_client_pb2.ApiGetFleetspeakPendingMessageCountResult)
  @Http("GET", "/api/v2/clients/<client_id>/fleetspeak/messages/pending/count")
  def GetFleetspeakPendingMessageCount(
      self,
      args: api_client_pb2.ApiGetFleetspeakPendingMessageCountArgs,
      context: Optional[api_call_context.ApiCallContext] = None,
  ) -> api_client.ApiGetFleetspeakPendingMessageCountHandler:
    raise NotImplementedError()

  # Virtual file system methods.
  # ===========================
  #
  @Category("Vfs")
  @ProtoArgsType(api_vfs_pb2.ApiListFilesArgs)
  @ProtoResultType(api_vfs_pb2.ApiListFilesResult)
  @Http("GET", "/api/v2/clients/<client_id>/vfs-index/")
  @Http("GET", "/api/v2/clients/<client_id>/vfs-index/<path:file_path>")
  def ListFiles(
      self,
      args: api_vfs_pb2.ApiListFilesArgs,
      context: Optional[api_call_context.ApiCallContext] = None,
  ):
    """List files in a given VFS directory of a given client."""

    # This method can be called with or without file_path argument and returns
    # the root files for the given client in the latter case.
    # To allow optional url arguments, two url patterns need to be specified.
    raise NotImplementedError()

  @Category("Vfs")
  @ProtoArgsType(api_vfs_pb2.ApiBrowseFilesystemArgs)
  @ProtoResultType(api_vfs_pb2.ApiBrowseFilesystemResult)
  @Http("GET", "/api/v2/clients/<client_id>/filesystem/")
  @Http("GET", "/api/v2/clients/<client_id>/filesystem/<path:path>")
  def BrowseFilesystem(
      self,
      args: api_vfs_pb2.ApiBrowseFilesystemArgs,
      context: Optional[api_call_context.ApiCallContext] = None,
  ) -> api_vfs.ApiBrowseFilesystemHandler:
    """List OS, TSK, NTFS files & directories in a given VFS directory.

    In difference to ListFiles, this method lists all filesystem PathTypes
    (OS, TSK, NTFS) at the same time. VFS specific prefixes like /fs/os can not
    be specified - only actual paths like /etc/.

    This method also allows querying the whole directory tree at once. This
    allows quick loading of useful VFS data when deep-linking to a folder.

    This method does not raise if a path is not found or points to a file
    instead of a directory. Instead, no results are returned for this path. This
    prevents alerts from firing when clients frequently access non-existent
    paths.

    Args:
      args: The request arguments.
      context: The API call context.
    """

    # This method can be called with or without file_path argument and returns
    # the root files for the given client in the latter case.
    # To allow optional url arguments, two url patterns need to be specified.
    raise NotImplementedError()

  @Category("Vfs")
  @ProtoArgsType(api_vfs_pb2.ApiGetVfsFilesArchiveArgs)
  @ResultBinaryStream()
  @Http("GET", "/api/v2/clients/<client_id>/vfs-files-archive/")
  @Http("GET", "/api/v2/clients/<client_id>/vfs-files-archive/<path:file_path>")
  def GetVfsFilesArchive(
      self,
      args: api_vfs_pb2.ApiGetVfsFilesArchiveArgs,
      context: Optional[api_call_context.ApiCallContext] = None,
  ):
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
  @ProtoArgsType(api_vfs_pb2.ApiGetFileDetailsArgs)
  @ProtoResultType(api_vfs_pb2.ApiGetFileDetailsResult)
  @Http("GET", "/api/v2/clients/<client_id>/vfs-details/<path:file_path>")
  def GetFileDetails(
      self,
      args: api_vfs_pb2.ApiGetFileDetailsArgs,
      context: Optional[api_call_context.ApiCallContext] = None,
  ):
    """Get details of a VFS file on a given client."""

    raise NotImplementedError()

  @Category("Vfs")
  @ProtoArgsType(api_vfs_pb2.ApiGetFileTextArgs)
  @ProtoResultType(api_vfs_pb2.ApiGetFileTextResult)
  @Http("GET", "/api/v2/clients/<client_id>/vfs-text/<path:file_path>")
  def GetFileText(
      self,
      args: api_vfs_pb2.ApiGetFileTextArgs,
      context: Optional[api_call_context.ApiCallContext] = None,
  ):
    """Get text file contents of a VFS file on a given client."""

    raise NotImplementedError()

  @Category("Vfs")
  @ProtoArgsType(api_vfs_pb2.ApiGetFileBlobArgs)
  @ResultBinaryStream()
  @Http("GET", "/api/v2/clients/<client_id>/vfs-blob/<path:file_path>")
  def GetFileBlob(
      self,
      args: api_vfs_pb2.ApiGetFileBlobArgs,
      context: Optional[api_call_context.ApiCallContext] = None,
  ):
    """Get byte contents of a VFS file on a given client."""

    raise NotImplementedError()

  @Category("Vfs")
  @ProtoArgsType(api_vfs_pb2.ApiGetFileVersionTimesArgs)
  @ProtoResultType(api_vfs_pb2.ApiGetFileVersionTimesResult)
  @Http("GET", "/api/v2/clients/<client_id>/vfs-version-times/<path:file_path>")
  def GetFileVersionTimes(
      self,
      args: api_vfs_pb2.ApiGetFileVersionTimesArgs,
      context: Optional[api_call_context.ApiCallContext] = None,
  ):
    """Get available version times of a VFS file on a given client."""

    raise NotImplementedError()

  @Category("Vfs")
  @ProtoArgsType(api_vfs_pb2.ApiGetFileDownloadCommandArgs)
  @ProtoResultType(api_vfs_pb2.ApiGetFileDownloadCommandResult)
  @Http(
      "GET", "/api/v2/clients/<client_id>/vfs-download-command/<path:file_path>"
  )
  def GetFileDownloadCommand(
      self,
      args: api_vfs_pb2.ApiGetFileDownloadCommandArgs,
      context: Optional[api_call_context.ApiCallContext] = None,
  ):
    """Get a command line that downloads given VFS file."""

    raise NotImplementedError()

  @Category("Vfs")
  @ProtoArgsType(api_vfs_pb2.ApiCreateVfsRefreshOperationArgs)
  @ProtoResultType(api_vfs_pb2.ApiCreateVfsRefreshOperationResult)
  @Http("POST", "/api/v2/clients/<client_id>/vfs-refresh-operations")
  def CreateVfsRefreshOperation(
      self,
      args: api_vfs_pb2.ApiCreateVfsRefreshOperationArgs,
      context: Optional[api_call_context.ApiCallContext] = None,
  ):
    """Start VFS refresh operation (refreshes a given VFS folder)."""

    raise NotImplementedError()

  @Category("Vfs")
  @ProtoArgsType(api_vfs_pb2.ApiGetVfsRefreshOperationStateArgs)
  @ProtoResultType(api_vfs_pb2.ApiGetVfsRefreshOperationStateResult)
  @Http(
      "GET",
      "/api/v2/clients/<client_id>/vfs-refresh-operations/<path:operation_id>",
  )
  def GetVfsRefreshOperationState(
      self,
      args: api_vfs_pb2.ApiGetVfsRefreshOperationStateArgs,
      context: Optional[api_call_context.ApiCallContext] = None,
  ):
    """Get state of a previously started VFS refresh operation."""

    raise NotImplementedError()

  @Category("Vfs")
  @ProtoArgsType(api_vfs_pb2.ApiGetVfsTimelineArgs)
  @ProtoResultType(api_vfs_pb2.ApiGetVfsTimelineResult)
  @Http("GET", "/api/v2/clients/<client_id>/vfs-timeline/<path:file_path>")
  def GetVfsTimeline(
      self,
      args: api_vfs_pb2.ApiGetVfsTimelineArgs,
      context: Optional[api_call_context.ApiCallContext] = None,
  ):
    """Get event timeline of VFS events for a given VFS path."""

    raise NotImplementedError()

  @Category("Vfs")
  @ProtoArgsType(api_vfs_pb2.ApiGetVfsTimelineAsCsvArgs)
  @ResultBinaryStream()
  @Http("GET", "/api/v2/clients/<client_id>/vfs-timeline-csv/<path:file_path>")
  def GetVfsTimelineAsCsv(
      self,
      args: api_vfs_pb2.ApiGetVfsTimelineAsCsvArgs,
      context: Optional[api_call_context.ApiCallContext] = None,
  ):
    """Get event timeline of VFS evetns for a given VFS path in CSV format."""

    raise NotImplementedError()

  @Category("Vfs")
  @ProtoArgsType(api_vfs_pb2.ApiUpdateVfsFileContentArgs)
  @ProtoResultType(api_vfs_pb2.ApiUpdateVfsFileContentResult)
  @Http("POST", "/api/v2/clients/<client_id>/vfs-update")
  def UpdateVfsFileContent(
      self,
      args: api_vfs_pb2.ApiUpdateVfsFileContentArgs,
      context: Optional[api_call_context.ApiCallContext] = None,
  ):
    """Create request for a new snapshot of the file."""

    raise NotImplementedError()

  @Category("Vfs")
  @ProtoArgsType(api_vfs_pb2.ApiGetVfsFileContentUpdateStateArgs)
  @ProtoResultType(api_vfs_pb2.ApiGetVfsFileContentUpdateStateResult)
  @Http("GET", "/api/v2/clients/<client_id>/vfs-update/<path:operation_id>")
  def GetVfsFileContentUpdateState(
      self,
      args: api_vfs_pb2.ApiGetVfsFileContentUpdateStateArgs,
      context: Optional[api_call_context.ApiCallContext] = None,
  ):
    """Get state of a previously started content update operation."""

    raise NotImplementedError()

  # Clients labels methods.
  # ======================
  #
  @Category("Clients")
  @ProtoResultType(api_client_pb2.ApiListClientsLabelsResult)
  @Http("GET", "/api/v2/clients/labels")
  @NoAuditLogRequired()
  def ListClientsLabels(
      self,
      args: None,
      context: Optional[api_call_context.ApiCallContext] = None,
  ):
    """List all available clients labels."""

    raise NotImplementedError()

  @Category("Clients")
  @ProtoArgsType(api_client_pb2.ApiAddClientsLabelsArgs)
  @Http("POST", "/api/v2/clients/labels/add")
  @NoAuditLogRequired()
  def AddClientsLabels(
      self,
      args: api_client_pb2.ApiAddClientsLabelsArgs,
      context: Optional[api_call_context.ApiCallContext] = None,
  ):
    """Labels given clients with given labels."""

    raise NotImplementedError()

  @Category("Clients")
  @ProtoArgsType(api_client_pb2.ApiRemoveClientsLabelsArgs)
  @Http("POST", "/api/v2/clients/labels/remove")
  @NoAuditLogRequired()
  def RemoveClientsLabels(
      self,
      args: api_client_pb2.ApiRemoveClientsLabelsArgs,
      context: Optional[api_call_context.ApiCallContext] = None,
  ):
    """Remove given labels from given clients."""

    raise NotImplementedError()

  # Clients flows methods.
  # =====================
  #
  @Category("Flows")
  @ProtoArgsType(api_flow_pb2.ApiListFlowsArgs)
  @ProtoResultType(api_flow_pb2.ApiListFlowsResult)
  @Http("GET", "/api/v2/clients/<client_id>/flows")
  def ListFlows(
      self,
      args: api_flow_pb2.ApiListFlowsArgs,
      context: Optional[api_call_context.ApiCallContext] = None,
  ):
    """List flows on a given client."""

    raise NotImplementedError()

  @Category("Flows")
  @ProtoArgsType(api_flow_pb2.ApiGetFlowArgs)
  @ProtoResultType(api_flow_pb2.ApiFlow)
  @Http("GET", "/api/v2/clients/<client_id>/flows/<path:flow_id>")
  def GetFlow(
      self,
      args: api_flow_pb2.ApiGetFlowArgs,
      context: Optional[api_call_context.ApiCallContext] = None,
  ):
    """Get flow details."""

    raise NotImplementedError()

  @Category("Flows")
  @ProtoArgsType(api_flow_pb2.ApiCreateFlowArgs)
  @ProtoResultType(api_flow_pb2.ApiFlow)
  @Http("POST", "/api/v2/clients/<client_id>/flows")
  def CreateFlow(
      self,
      args: api_flow_pb2.ApiCreateFlowArgs,
      context: Optional[api_call_context.ApiCallContext] = None,
  ):
    """Start a new flow on a given client."""

    raise NotImplementedError()

  @Category("Flows")
  @ProtoArgsType(api_flow_pb2.ApiCancelFlowArgs)
  @ProtoResultType(api_flow_pb2.ApiFlow)
  @Http(
      "POST", "/api/v2/clients/<client_id>/flows/<path:flow_id>/actions/cancel"
  )
  def CancelFlow(
      self,
      args: api_flow_pb2.ApiCancelFlowArgs,
      context: Optional[api_call_context.ApiCallContext] = None,
  ):
    """Stop given flow on a given client."""

    raise NotImplementedError()

  @Category("Flows")
  @ProtoArgsType(api_flow_pb2.ApiListFlowRequestsArgs)
  @ProtoResultType(api_flow_pb2.ApiListFlowRequestsResult)
  @Http("GET", "/api/v2/clients/<client_id>/flows/<path:flow_id>/requests")
  def ListFlowRequests(
      self,
      args: api_flow_pb2.ApiListFlowRequestsArgs,
      context: Optional[api_call_context.ApiCallContext] = None,
  ):
    """List pending action requests of a given flow on a given client."""

    raise NotImplementedError()

  @Category("Flows")
  @ProtoArgsType(api_flow_pb2.ApiListFlowResultsArgs)
  @ProtoResultType(api_flow_pb2.ApiListFlowResultsResult)
  @Http("GET", "/api/v2/clients/<client_id>/flows/<path:flow_id>/results")
  def ListFlowResults(
      self,
      args: api_flow_pb2.ApiListFlowResultsArgs,
      context: Optional[api_call_context.ApiCallContext] = None,
  ):
    """List results of a given flow on a given client."""

    raise NotImplementedError()

  @Category("Flows")
  @ProtoArgsType(api_flow_pb2.ApiGetExportedFlowResultsArgs)
  @ResultBinaryStream()
  @Http(
      "GET",
      "/api/v2/clients/<client_id>/flows/<path:flow_id>/"
      "exported-results/<plugin_name>",
  )
  def GetExportedFlowResults(
      self,
      args: api_flow_pb2.ApiGetExportedFlowResultsArgs,
      context: Optional[api_call_context.ApiCallContext] = None,
  ):
    """Stream flow results using one of the instant output plugins."""

    raise NotImplementedError()

  @Category("Flows")
  @ProtoArgsType(api_flow_pb2.ApiGetFlowResultsExportCommandArgs)
  @ProtoResultType(api_flow_pb2.ApiGetFlowResultsExportCommandResult)
  @Http(
      "GET",
      "/api/v2/clients/<client_id>/flows/<path:flow_id>/results/export-command",
  )
  def GetFlowResultsExportCommand(
      self,
      args: api_flow_pb2.ApiGetFlowResultsExportCommandArgs,
      context: Optional[api_call_context.ApiCallContext] = None,
  ):
    """Get export tool command to export flow results."""

    raise NotImplementedError()

  @Category("Flows")
  @ProtoArgsType(api_flow_pb2.ApiGetFlowFilesArchiveArgs)
  @ResultBinaryStream()
  @Http(
      "GET",
      "/api/v2/clients/<client_id>/flows/<path:flow_id>/results/files-archive",
  )
  def GetFlowFilesArchive(
      self,
      args: api_flow_pb2.ApiGetFlowFilesArchiveArgs,
      context: Optional[api_call_context.ApiCallContext] = None,
  ):
    """Get ZIP or TAR.GZ archive with files downloaded by the flow."""

    raise NotImplementedError()

  @Category("Flows")
  @ProtoArgsType(api_flow_pb2.ApiListFlowOutputPluginsArgs)
  @ProtoResultType(api_flow_pb2.ApiListFlowOutputPluginsResult)
  @Http(
      "GET", "/api/v2/clients/<client_id>/flows/<path:flow_id>/output-plugins"
  )
  def ListFlowOutputPlugins(
      self,
      args: api_flow_pb2.ApiListFlowOutputPluginsArgs,
      context: Optional[api_call_context.ApiCallContext] = None,
  ):
    """List output plugins used by the flow."""

    raise NotImplementedError()

  @Category("Flows")
  @ProtoArgsType(api_flow_pb2.ApiListFlowOutputPluginLogsArgs)
  @ProtoResultType(api_flow_pb2.ApiListFlowOutputPluginLogsResult)
  @Http(
      "GET",
      "/api/v2/clients/<client_id>/flows/<path:flow_id>/"
      "output-plugins/<plugin_id>/logs",
  )
  def ListFlowOutputPluginLogs(
      self,
      args: api_flow_pb2.ApiListFlowOutputPluginLogsArgs,
      context: Optional[api_call_context.ApiCallContext] = None,
  ):
    """List output plugin logs of the flow."""

    raise NotImplementedError()

  @Category("Flows")
  @ProtoArgsType(api_flow_pb2.ApiListFlowOutputPluginErrorsArgs)
  @ProtoResultType(api_flow_pb2.ApiListFlowOutputPluginErrorsResult)
  @Http(
      "GET",
      "/api/v2/clients/<client_id>/flows/<path:flow_id>/"
      "output-plugins/<plugin_id>/errors",
  )
  def ListFlowOutputPluginErrors(
      self,
      args: api_flow_pb2.ApiListFlowOutputPluginErrorsArgs,
      context: Optional[api_call_context.ApiCallContext] = None,
  ):
    """List output plugin errors of the flow."""

    raise NotImplementedError()

  @Category("Flows")
  @ProtoArgsType(api_flow_pb2.ApiListAllFlowOutputPluginLogsArgs)
  @ProtoResultType(api_flow_pb2.ApiListAllFlowOutputPluginLogsResult)
  @Http(
      "GET",
      "/api/v2/clients/<client_id>/flows/<path:flow_id>/output-plugins/logs",
  )
  def ListAllFlowOutputPluginLogs(
      self,
      args: api_flow_pb2.ApiListAllFlowOutputPluginLogsArgs,
      context: Optional[api_call_context.ApiCallContext] = None,
  ):
    """List all output plugin logs of the flow."""

    raise NotImplementedError()

  @Category("Flows")
  @ProtoArgsType(api_flow_pb2.ApiListFlowLogsArgs)
  @ProtoResultType(api_flow_pb2.ApiListFlowLogsResult)
  @Http("GET", "/api/v2/clients/<client_id>/flows/<path:flow_id>/log")
  def ListFlowLogs(
      self,
      args: api_flow_pb2.ApiListFlowLogsArgs,
      context: Optional[api_call_context.ApiCallContext] = None,
  ) -> api_flow.ApiListFlowLogsHandler:
    """List logs of the flow."""

    raise NotImplementedError()

  @Category("Flows")
  @ProtoArgsType(api_timeline_pb2.ApiGetCollectedTimelineArgs)
  @ResultBinaryStream()
  @Http("GET", "/api/v2/clients/<client_id>/flows/<flow_id>/timeline/<format>")
  def GetCollectedTimeline(
      self,
      args: api_timeline_pb2.ApiGetCollectedTimelineArgs,
      context: Optional[api_call_context.ApiCallContext] = None,
  ):
    """Exports results of a timeline flow to the specific format."""
    raise NotImplementedError()

  @Category("Flows")
  @ProtoArgsType(api_yara_pb2.ApiUploadYaraSignatureArgs)
  @ProtoResultType(api_yara_pb2.ApiUploadYaraSignatureResult)
  @Http("POST", "/api/v2/yara-signatures")
  def UploadYaraSignature(
      self,
      args: api_yara_pb2.ApiUploadYaraSignatureArgs,
      context: Optional[api_call_context.ApiCallContext] = None,
  ):
    raise NotImplementedError()

  @Category("Flows")
  @ProtoArgsType(api_flow_pb2.ApiExplainGlobExpressionArgs)
  @ProtoResultType(api_flow_pb2.ApiExplainGlobExpressionResult)
  @Http("POST", "/api/v2/clients/<client_id>/glob-expressions:explain")
  def ExplainGlobExpression(
      self,
      args: api_flow_pb2.ApiExplainGlobExpressionArgs,
      context: Optional[api_call_context.ApiCallContext] = None,
  ) -> api_flow.ApiExplainGlobExpressionHandler:
    raise NotImplementedError()

  @Category("Flows")
  @ProtoArgsType(api_flow_pb2.ApiCreateFlowArgs)
  @ProtoResultType(api_flow_pb2.ApiScheduledFlow)
  @Http("POST", "/api/v2/clients/<client_id>/scheduled-flows")
  def ScheduleFlow(
      self,
      args: api_flow_pb2.ApiCreateFlowArgs,
      context: Optional[api_call_context.ApiCallContext] = None,
  ) -> api_flow.ApiScheduleFlowHandler:
    """Schedules a flow on a client, to be started upon approval grant."""
    raise NotImplementedError()

  @Category("Flows")
  @ProtoArgsType(api_flow_pb2.ApiListScheduledFlowsArgs)
  @ProtoResultType(api_flow_pb2.ApiListScheduledFlowsResult)
  @Http("GET", "/api/v2/clients/<client_id>/scheduled-flows/<creator>")
  def ListScheduledFlows(
      self,
      args: api_flow_pb2.ApiListScheduledFlowsArgs,
      context: Optional[api_call_context.ApiCallContext] = None,
  ) -> api_flow.ApiListScheduledFlowsHandler:
    """Lists all scheduled flows from a user on a client."""
    raise NotImplementedError()

  @Category("Flows")
  @ProtoArgsType(api_flow_pb2.ApiUnscheduleFlowArgs)
  @ProtoResultType(api_flow_pb2.ApiUnscheduleFlowResult)
  @Http(
      "DELETE",
      "/api/v2/clients/<client_id>/scheduled-flows/<scheduled_flow_id>",
  )
  def UnscheduleFlow(
      self,
      args: api_flow_pb2.ApiUnscheduleFlowArgs,
      context: Optional[api_call_context.ApiCallContext] = None,
  ) -> api_flow.ApiUnscheduleFlowHandler:
    """Unschedules and deletes a previously scheduled flow."""
    raise NotImplementedError()

  @Category("Flows")
  @ProtoArgsType(api_osquery_pb2.ApiGetOsqueryResultsArgs)
  @ResultBinaryStream()
  @Http(
      "GET",
      "/api/v2/clients/<client_id>/flows/<flow_id>/osquery-results/<format>",
  )
  def GetOsqueryResults(
      self,
      args: api_osquery_pb2.ApiGetOsqueryResultsArgs,
      context: Optional[api_call_context.ApiCallContext] = None,
  ):
    """Export Osquery results for a client and a flow in the specified format."""
    raise NotImplementedError()

  # Signed commands methods.
  # ========================
  #
  @Category("SignedCommands")
  @ProtoResultType(api_signed_commands_pb2.ApiListSignedCommandsResult)
  @Http("GET", "/api/v2/signed-commands")
  def ListSignedCommands(
      self,
      args: Optional[None] = None,
      context: Optional[api_call_context.ApiCallContext] = None,
  ) -> api_signed_commands.ApiListSignedCommandsHandler:
    """Get all signed commands."""
    raise NotImplementedError()

  # Cron jobs methods.
  # =================
  #
  @Category("Cron")
  @ProtoArgsType(api_cron_pb2.ApiListCronJobsArgs)
  @ProtoResultType(api_cron_pb2.ApiListCronJobsResult)
  @NoAuditLogRequired()
  @Http("GET", "/api/v2/cron-jobs")
  def ListCronJobs(
      self,
      args: api_cron_pb2.ApiListCronJobsArgs,
      context: Optional[api_call_context.ApiCallContext] = None,
  ):
    """List available cron jobs."""

    raise NotImplementedError()

  @Category("Cron")
  @ProtoArgsType(api_cron_pb2.ApiCreateCronJobArgs)
  @ProtoResultType(api_cron_pb2.ApiCronJob)
  @Http("POST", "/api/v2/cron-jobs")
  def CreateCronJob(
      self,
      args: api_cron_pb2.ApiCreateCronJobArgs,
      context: Optional[api_call_context.ApiCallContext] = None,
  ):
    """Create new cron job."""

    raise NotImplementedError()

  @Category("Cron")
  @ProtoArgsType(api_cron_pb2.ApiGetCronJobArgs)
  @ProtoResultType(api_cron_pb2.ApiCronJob)
  @Http("GET", "/api/v2/cron-jobs/<cron_job_id>")
  def GetCronJob(
      self,
      args: api_cron_pb2.ApiGetCronJobArgs,
      context: Optional[api_call_context.ApiCallContext] = None,
  ):
    """Get details of a given cron job."""

    raise NotImplementedError()

  @Category("Cron")
  @ProtoArgsType(api_cron_pb2.ApiForceRunCronJobArgs)
  @Http("POST", "/api/v2/cron-jobs/<cron_job_id>/actions/force-run")
  def ForceRunCronJob(
      self,
      args: api_cron_pb2.ApiForceRunCronJobArgs,
      context: Optional[api_call_context.ApiCallContext] = None,
  ):
    """Force an out-of-schedule run of a given cron job."""

    raise NotImplementedError()

  @Category("Hunts")
  @ProtoArgsType(api_cron_pb2.ApiModifyCronJobArgs)
  @ProtoResultType(api_cron_pb2.ApiCronJob)
  @Http("PATCH", "/api/v2/cron-jobs/<cron_job_id>")
  def ModifyCronJob(
      self,
      args: api_cron_pb2.ApiModifyCronJobArgs,
      context: Optional[api_call_context.ApiCallContext] = None,
  ):
    """Modify cron job (includes enabling/disabling)."""

    raise NotImplementedError()

  @Category("Cron")
  @ProtoArgsType(api_cron_pb2.ApiListCronJobRunsArgs)
  @ProtoResultType(api_cron_pb2.ApiListCronJobRunsResult)
  @Http("GET", "/api/v2/cron-jobs/<cron_job_id>/runs")
  def ListCronJobRuns(
      self,
      args: api_cron_pb2.ApiListCronJobRunsArgs,
      context: Optional[api_call_context.ApiCallContext] = None,
  ):
    """List runs initiated by the given cron job."""

    raise NotImplementedError()

  @Category("Cron")
  @ProtoArgsType(api_cron_pb2.ApiGetCronJobRunArgs)
  @ProtoResultType(api_cron_pb2.ApiCronJobRun)
  @Http("GET", "/api/v2/cron-jobs/<cron_job_id>/runs/<run_id>")
  def GetCronJobRun(
      self,
      args: api_cron_pb2.ApiGetCronJobRunArgs,
      context: Optional[api_call_context.ApiCallContext] = None,
  ):
    """Get details of a run started by a cron job."""

    raise NotImplementedError()

  @Category("Cron")
  @ProtoArgsType(api_cron_pb2.ApiDeleteCronJobArgs)
  @Http("DELETE", "/api/v2/cron-jobs/<cron_job_id>")
  def DeleteCronJob(
      self,
      args: api_cron_pb2.ApiDeleteCronJobArgs,
      context: Optional[api_call_context.ApiCallContext] = None,
  ):
    """Delete given cron job and all its flows."""

    raise NotImplementedError()

  # Hunts methods.
  # =============
  #
  @Category("Hunts")
  @ProtoArgsType(api_hunt_pb2.ApiListHuntsArgs)
  @ProtoResultType(api_hunt_pb2.ApiListHuntsResult)
  @Http("GET", "/api/v2/hunts")
  @NoAuditLogRequired()
  def ListHunts(
      self,
      args: api_hunt_pb2.ApiListHuntsArgs,
      context: Optional[api_call_context.ApiCallContext] = None,
  ):
    """List hunts."""

    raise NotImplementedError()

  @Category("Hunts")
  @ProtoArgsType(api_hunt_pb2.ApiVerifyHuntAccessArgs)
  @ProtoResultType(api_hunt_pb2.ApiVerifyHuntAccessResult)
  @Http("GET", "/api/v2/hunts/<hunt_id>/access")
  def VerifyHuntAccess(
      self,
      args: api_hunt_pb2.ApiVerifyHuntAccessArgs,
      context: Optional[api_call_context.ApiCallContext] = None,
  ):
    """Verifies if user has access to a hunt."""

    raise NotImplementedError()

  @Category("Hunts")
  @ProtoArgsType(api_hunt_pb2.ApiGetHuntArgs)
  @ProtoResultType(api_hunt_pb2.ApiHunt)
  @Http("GET", "/api/v2/hunts/<hunt_id>")
  def GetHunt(
      self,
      args: api_hunt_pb2.ApiGetHuntArgs,
      context: Optional[api_call_context.ApiCallContext] = None,
  ):
    """Get details of a hunt with a given id."""

    raise NotImplementedError()

  @Category("Hunts")
  @ProtoArgsType(api_hunt_pb2.ApiListHuntErrorsArgs)
  @ProtoResultType(api_hunt_pb2.ApiListHuntErrorsResult)
  @Http("GET", "/api/v2/hunts/<hunt_id>/errors")
  def ListHuntErrors(
      self,
      args: api_hunt_pb2.ApiListHuntErrorsArgs,
      context: Optional[api_call_context.ApiCallContext] = None,
  ):
    """List hunt errors."""

    raise NotImplementedError()

  @Category("Hunts")
  @ProtoArgsType(api_hunt_pb2.ApiListHuntLogsArgs)
  @ProtoResultType(api_hunt_pb2.ApiListHuntLogsResult)
  @Http("GET", "/api/v2/hunts/<hunt_id>/log")
  def ListHuntLogs(
      self,
      args: api_hunt_pb2.ApiListHuntLogsArgs,
      context: Optional[api_call_context.ApiCallContext] = None,
  ):
    """List hunt logs."""

    raise NotImplementedError()

  @Category("Hunts")
  @ProtoArgsType(api_hunt_pb2.ApiListHuntResultsArgs)
  @ProtoResultType(api_hunt_pb2.ApiListHuntResultsResult)
  @Http("GET", "/api/v2/hunts/<hunt_id>/results")
  def ListHuntResults(
      self,
      args: api_hunt_pb2.ApiListHuntResultsArgs,
      context: Optional[api_call_context.ApiCallContext] = None,
  ):
    """List hunt results."""

    raise NotImplementedError()

  @Category("Hunts")
  @ProtoArgsType(api_hunt_pb2.ApiCountHuntResultsByTypeArgs)
  @ProtoResultType(api_hunt_pb2.ApiCountHuntResultsByTypeResult)
  @Http("GET", "/api/v2/hunts/<hunt_id>/result-counts")
  def CountHuntResultsByType(
      self,
      args: api_hunt_pb2.ApiCountHuntResultsByTypeArgs,
      context: Optional[api_call_context.ApiCallContext] = None,
  ):
    """Count all hunt results by type."""

    raise NotImplementedError()

  @Category("Hunts")
  @ProtoArgsType(api_hunt_pb2.ApiGetExportedHuntResultsArgs)
  @ResultBinaryStream()
  @Http("GET", "/api/v2/hunts/<hunt_id>/exported-results/<plugin_name>")
  def GetExportedHuntResults(
      self,
      args: api_hunt_pb2.ApiGetExportedHuntResultsArgs,
      context: Optional[api_call_context.ApiCallContext] = None,
  ):
    """Stream hunt results using one of the instant output plugins."""

    raise NotImplementedError()

  @Category("Hunts")
  @ProtoArgsType(api_hunt_pb2.ApiGetHuntResultsExportCommandArgs)
  @ProtoResultType(api_hunt_pb2.ApiGetHuntResultsExportCommandResult)
  @Http("GET", "/api/v2/hunts/<hunt_id>/results/export-command")
  def GetHuntResultsExportCommand(
      self,
      args: api_hunt_pb2.ApiGetHuntResultsExportCommandArgs,
      context: Optional[api_call_context.ApiCallContext] = None,
  ):
    """Get export command that exports hunt results."""

    raise NotImplementedError()

  @Category("Hunts")
  @ProtoArgsType(api_hunt_pb2.ApiListHuntOutputPluginsArgs)
  @ProtoResultType(api_hunt_pb2.ApiListHuntOutputPluginsResult)
  @Http("GET", "/api/v2/hunts/<hunt_id>/output-plugins")
  def ListHuntOutputPlugins(
      self,
      args: api_hunt_pb2.ApiListHuntOutputPluginsArgs,
      context: Optional[api_call_context.ApiCallContext] = None,
  ):
    """List output plugins used by the hunt."""

    raise NotImplementedError()

  @Category("Hunts")
  @ProtoArgsType(api_hunt_pb2.ApiListHuntOutputPluginLogsArgs)
  @ProtoResultType(api_hunt_pb2.ApiListHuntOutputPluginLogsResult)
  @Http("GET", "/api/v2/hunts/<hunt_id>/output-plugins/<plugin_id>/logs")
  def ListHuntOutputPluginLogs(
      self,
      args: api_hunt_pb2.ApiListHuntOutputPluginLogsArgs,
      context: Optional[api_call_context.ApiCallContext] = None,
  ):
    """List hunt output plugins logs."""

    raise NotImplementedError()

  @Category("Hunts")
  @ProtoArgsType(api_hunt_pb2.ApiListHuntOutputPluginErrorsArgs)
  @ProtoResultType(api_hunt_pb2.ApiListHuntOutputPluginErrorsResult)
  @Http("GET", "/api/v2/hunts/<hunt_id>/output-plugins/<plugin_id>/errors")
  def ListHuntOutputPluginErrors(
      self,
      args: api_hunt_pb2.ApiListHuntOutputPluginErrorsArgs,
      context: Optional[api_call_context.ApiCallContext] = None,
  ):
    """List hunt output plugins errors."""

    raise NotImplementedError()

  @Category("Hunts")
  @ProtoArgsType(api_hunt_pb2.ApiListHuntCrashesArgs)
  @ProtoResultType(api_hunt_pb2.ApiListHuntCrashesResult)
  @Http("GET", "/api/v2/hunts/<hunt_id>/crashes")
  def ListHuntCrashes(
      self,
      args: api_hunt_pb2.ApiListHuntCrashesArgs,
      context: Optional[api_call_context.ApiCallContext] = None,
  ):
    """List all crashes caused by the hunt."""

    raise NotImplementedError()

  @Category("Hunts")
  @ProtoArgsType(api_hunt_pb2.ApiGetHuntClientCompletionStatsArgs)
  @ProtoResultType(api_hunt_pb2.ApiGetHuntClientCompletionStatsResult)
  @Http("GET", "/api/v2/hunts/<hunt_id>/client-completion-stats")
  def GetHuntClientCompletionStats(
      self,
      args: api_hunt_pb2.ApiGetHuntClientCompletionStatsArgs,
      context: Optional[api_call_context.ApiCallContext] = None,
  ):
    """Get hunt completion stats."""

    raise NotImplementedError()

  @Category("Hunts")
  @ProtoArgsType(api_hunt_pb2.ApiGetHuntStatsArgs)
  @ProtoResultType(api_hunt_pb2.ApiGetHuntStatsResult)
  @Http("GET", "/api/v2/hunts/<hunt_id>/stats")
  def GetHuntStats(
      self,
      args: api_hunt_pb2.ApiGetHuntStatsArgs,
      context: Optional[api_call_context.ApiCallContext] = None,
  ):
    """Get general hunt stats."""

    raise NotImplementedError()

  @Category("Hunts")
  @ProtoArgsType(api_hunt_pb2.ApiListHuntClientsArgs)
  @ProtoResultType(api_hunt_pb2.ApiListHuntClientsResult)
  @Http("GET", "/api/v2/hunts/<hunt_id>/clients/<client_status>")
  def ListHuntClients(
      self,
      args: api_hunt_pb2.ApiListHuntClientsArgs,
      context: Optional[api_call_context.ApiCallContext] = None,
  ):
    """List clients involved into the hunt."""

    raise NotImplementedError()

  @Category("Hunts")
  @ProtoArgsType(api_hunt_pb2.ApiGetHuntContextArgs)
  @ProtoResultType(api_hunt_pb2.ApiGetHuntContextResult)
  @Http("GET", "/api/v2/hunts/<hunt_id>/context")
  def GetHuntContext(
      self,
      args: api_hunt_pb2.ApiGetHuntContextArgs,
      context: Optional[api_call_context.ApiCallContext] = None,
  ):
    """Get a low-level hunt context (useful for debugging)."""

    raise NotImplementedError()

  @Category("Hunts")
  @ProtoArgsType(api_hunt_pb2.ApiCreateHuntArgs)
  @ProtoResultType(api_hunt_pb2.ApiHunt)
  @Http("POST", "/api/v2/hunts")
  def CreateHunt(
      self,
      args: api_hunt_pb2.ApiCreateHuntArgs,
      context: Optional[api_call_context.ApiCallContext] = None,
  ):
    """Create a new hunt."""

    raise NotImplementedError()

  @Category("Hunts")
  @ProtoArgsType(api_hunt_pb2.ApiModifyHuntArgs)
  @ProtoResultType(api_hunt_pb2.ApiHunt)
  @Http("PATCH", "/api/v2/hunts/<hunt_id>")
  def ModifyHunt(
      self,
      args: api_hunt_pb2.ApiModifyHuntArgs,
      context: Optional[api_call_context.ApiCallContext] = None,
  ):
    """Modify hunt (includes stopping/starting)."""

    raise NotImplementedError()

  @Category("Hunts")
  @ProtoArgsType(api_hunt_pb2.ApiDeleteHuntArgs)
  @Http("DELETE", "/api/v2/hunts/<hunt_id>")
  def DeleteHunt(
      self,
      args: api_hunt_pb2.ApiDeleteHuntArgs,
      context: Optional[api_call_context.ApiCallContext] = None,
  ):
    """Delete a hunt with all its data."""

    raise NotImplementedError()

  @Category("Hunts")
  @ProtoArgsType(api_hunt_pb2.ApiGetHuntFilesArchiveArgs)
  @ResultBinaryStream()
  @Http("GET", "/api/v2/hunts/<hunt_id>/results/files-archive")
  def GetHuntFilesArchive(
      self,
      args: api_hunt_pb2.ApiGetHuntFilesArchiveArgs,
      context: Optional[api_call_context.ApiCallContext] = None,
  ):
    """Get ZIP or TAR.GZ archive with all the files downloaded by the hunt."""

    raise NotImplementedError()

  @Category("Hunts")
  @ProtoArgsType(api_hunt_pb2.ApiGetHuntFileArgs)
  @ResultBinaryStream()
  @Http(
      "GET",
      "/api/v2/hunts/<hunt_id>/results/clients/<client_id>/vfs-blob"
      "/<path:vfs_path>",
  )
  def GetHuntFile(
      self,
      args: api_hunt_pb2.ApiGetHuntFileArgs,
      context: Optional[api_call_context.ApiCallContext] = None,
  ):
    """Get a file referenced by one of the hunt results."""

    raise NotImplementedError()

  @Category("Hunts")
  @ProtoArgsType(api_timeline_pb2.ApiGetCollectedHuntTimelinesArgs)
  @ResultBinaryStream()
  @Http("GET", "/api/v2/hunts/<hunt_id>/timelines/<format>")
  def GetCollectedHuntTimelines(
      self,
      args: api_timeline_pb2.ApiGetCollectedHuntTimelinesArgs,
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

  # Approvals methods.
  # =================
  #
  @Category("User")
  @ProtoArgsType(api_user_pb2.ApiCreateClientApprovalArgs)
  @ProtoResultType(api_user_pb2.ApiClientApproval)
  @Http("POST", "/api/v2/users/me/approvals/client/<client_id>")
  def CreateClientApproval(
      self,
      args: api_user_pb2.ApiCreateClientApprovalArgs,
      context: Optional[api_call_context.ApiCallContext] = None,
  ):
    """Create new client approval."""

    raise NotImplementedError()

  @Category("User")
  @ProtoArgsType(api_user_pb2.ApiGetClientApprovalArgs)
  @ProtoResultType(api_user_pb2.ApiClientApproval)
  @NoAuditLogRequired()
  @Http(
      "GET",
      "/api/v2/users/<username>/approvals/client/<client_id>/<approval_id>",
  )
  def GetClientApproval(
      self,
      args: api_user_pb2.ApiGetClientApprovalArgs,
      context: Optional[api_call_context.ApiCallContext] = None,
  ):
    """Get client approval identified by approval id, client id and username."""
    raise NotImplementedError()

  @Category("User")
  @ProtoArgsType(api_user_pb2.ApiGrantClientApprovalArgs)
  @ProtoResultType(api_user_pb2.ApiClientApproval)
  @Http(
      "POST",
      "/api/v2/users/<username>/approvals/client/<client_id>/<approval_id>/"
      "actions/grant",
  )
  def GrantClientApproval(
      self,
      args: api_user_pb2.ApiGrantClientApprovalArgs,
      context: Optional[api_call_context.ApiCallContext] = None,
  ):
    """Grant client approval."""

    raise NotImplementedError()

  @Category("User")
  @ProtoArgsType(api_user_pb2.ApiListClientApprovalsArgs)
  @ProtoResultType(api_user_pb2.ApiListClientApprovalsResult)
  @NoAuditLogRequired()
  @Http("GET", "/api/v2/users/me/approvals/client")
  @Http("GET", "/api/v2/users/me/approvals/client/<client_id>")
  def ListClientApprovals(
      self,
      args: api_user_pb2.ApiListClientApprovalsArgs,
      context: Optional[api_call_context.ApiCallContext] = None,
  ):
    """List client approvals of a current user in reversed timestamp order."""

    raise NotImplementedError()

  @Category("User")
  @ProtoArgsType(api_user_pb2.ApiCreateHuntApprovalArgs)
  @ProtoResultType(api_user_pb2.ApiHuntApproval)
  @NoAuditLogRequired()
  @Http("POST", "/api/v2/users/me/approvals/hunt/<hunt_id>")
  def CreateHuntApproval(
      self,
      args: api_user_pb2.ApiCreateHuntApprovalArgs,
      context: Optional[api_call_context.ApiCallContext] = None,
  ):
    """Create new hunt approval."""

    raise NotImplementedError()

  @Category("User")
  @ProtoArgsType(api_user_pb2.ApiGetHuntApprovalArgs)
  @ProtoResultType(api_user_pb2.ApiHuntApproval)
  @NoAuditLogRequired()
  @Http(
      "GET", "/api/v2/users/<username>/approvals/hunt/<hunt_id>/<approval_id>"
  )
  def GetHuntApproval(
      self,
      args: api_user_pb2.ApiGetHuntApprovalArgs,
      context: Optional[api_call_context.ApiCallContext] = None,
  ):
    """Get hunt approval identified by approval id, hunt id and username."""
    raise NotImplementedError()

  @Category("User")
  @ProtoArgsType(api_user_pb2.ApiGrantHuntApprovalArgs)
  @ProtoResultType(api_user_pb2.ApiHuntApproval)
  @Http(
      "POST",
      "/api/v2/users/<username>/approvals/hunt/<hunt_id>/<approval_id>/"
      "actions/grant",
  )
  def GrantHuntApproval(
      self,
      args: api_user_pb2.ApiGrantHuntApprovalArgs,
      context: Optional[api_call_context.ApiCallContext] = None,
  ):
    """Grant hunt approval."""

    raise NotImplementedError()

  @Category("User")
  @ProtoArgsType(api_user_pb2.ApiListHuntApprovalsArgs)
  @ProtoResultType(api_user_pb2.ApiListHuntApprovalsResult)
  @NoAuditLogRequired()
  @Http("GET", "/api/v2/users/me/approvals/hunt")
  @Http("GET", "/api/v2/users/me/approvals/hunt/<hunt_id>")
  def ListHuntApprovals(
      self,
      args: api_user_pb2.ApiListHuntApprovalsArgs,
      context: Optional[api_call_context.ApiCallContext] = None,
  ):
    """List hunt approvals of a current user."""

    raise NotImplementedError()

  @Category("User")
  @ProtoArgsType(api_user_pb2.ApiCreateCronJobApprovalArgs)
  @ProtoResultType(api_user_pb2.ApiCronJobApproval)
  @Http("POST", "/api/v2/users/me/approvals/cron-job/<cron_job_id>")
  def CreateCronJobApproval(
      self,
      args: api_user_pb2.ApiCreateCronJobApprovalArgs,
      context: Optional[api_call_context.ApiCallContext] = None,
  ):
    """Create new cron job approval."""

    raise NotImplementedError()

  @Category("User")
  @ProtoArgsType(api_user_pb2.ApiGetCronJobApprovalArgs)
  @ProtoResultType(api_user_pb2.ApiCronJobApproval)
  @NoAuditLogRequired()
  @Http(
      "GET",
      "/api/v2/users/<username>/approvals/cron-job/<cron_job_id>/<approval_id>",
  )
  def GetCronJobApproval(
      self,
      args: api_user_pb2.ApiGetCronJobApprovalArgs,
      context: Optional[api_call_context.ApiCallContext] = None,
  ):
    """Get cron job approval identified by approval id, cron id and username."""

    raise NotImplementedError()

  @Category("User")
  @ProtoArgsType(api_user_pb2.ApiGrantCronJobApprovalArgs)
  @ProtoResultType(api_user_pb2.ApiCronJobApproval)
  @Http(
      "POST",
      "/api/v2/users/<username>/approvals/cron-job/<cron_job_id>/<approval_id>/"
      "actions/grant",
  )
  def GrantCronJobApproval(
      self,
      args: api_user_pb2.ApiGrantCronJobApprovalArgs,
      context: Optional[api_call_context.ApiCallContext] = None,
  ):
    """Grant cron job approval."""

    raise NotImplementedError()

  @Category("User")
  @ProtoArgsType(api_user_pb2.ApiListCronJobApprovalsArgs)
  @ProtoResultType(api_user_pb2.ApiListCronJobApprovalsResult)
  @NoAuditLogRequired()
  @Http("GET", "/api/v2/users/me/approvals/cron-job")
  def ListCronJobApprovals(
      self,
      args: api_user_pb2.ApiListCronJobApprovalsArgs,
      context: Optional[api_call_context.ApiCallContext] = None,
  ):
    """List cron job approvals of a current user."""

    raise NotImplementedError()

  @Category("User")
  @ProtoArgsType(api_user_pb2.ApiListApproverSuggestionsArgs)
  @ProtoResultType(api_user_pb2.ApiListApproverSuggestionsResult)
  @Http("GET", "/api/v2/users/approver-suggestions")
  def ListApproverSuggestions(
      self,
      args: api_user_pb2.ApiListApproverSuggestionsArgs,
      context: Optional[api_call_context.ApiCallContext] = None,
  ):
    """List suggestions for approver usernames."""

    raise NotImplementedError()

  # User settings methods.
  # =====================
  #
  @Category("User")
  @ProtoResultType(api_user_pb2.ApiGetPendingUserNotificationsCountResult)
  @Http("GET", "/api/v2/users/me/notifications/pending/count")
  @NoAuditLogRequired()
  def GetPendingUserNotificationsCount(
      self,
      args: None,
      context: Optional[api_call_context.ApiCallContext] = None,
  ):
    """Get number of pending user notifications."""

    raise NotImplementedError()

  @Category("User")
  @ProtoArgsType(api_user_pb2.ApiListPendingUserNotificationsArgs)
  @ProtoResultType(api_user_pb2.ApiListPendingUserNotificationsResult)
  @Http("GET", "/api/v2/users/me/notifications/pending")
  @NoAuditLogRequired()
  def ListPendingUserNotifications(
      self,
      args: api_user_pb2.ApiListPendingUserNotificationsArgs,
      context: Optional[api_call_context.ApiCallContext] = None,
  ):
    """List pending user notifications."""

    raise NotImplementedError()

  @Category("User")
  @ProtoArgsType(api_user_pb2.ApiDeletePendingUserNotificationArgs)
  @Http("DELETE", "/api/v2/users/me/notifications/pending/<timestamp>")
  @NoAuditLogRequired()
  def DeletePendingUserNotification(
      self,
      args: api_user_pb2.ApiDeletePendingUserNotificationArgs,
      context: Optional[api_call_context.ApiCallContext] = None,
  ):
    """Delete pending user notifications."""

    raise NotImplementedError()

  @Category("User")
  @ProtoArgsType(api_user_pb2.ApiListAndResetUserNotificationsArgs)
  @ProtoResultType(api_user_pb2.ApiListAndResetUserNotificationsResult)
  @Http("POST", "/api/v2/users/me/notifications")
  @NoAuditLogRequired()
  def ListAndResetUserNotifications(
      self,
      args: api_user_pb2.ApiListAndResetUserNotificationsArgs,
      context: Optional[api_call_context.ApiCallContext] = None,
  ):
    """List user notifications and mark them all as 'seen'."""

    raise NotImplementedError()

  @Category("User")
  @ProtoResultType(api_user_pb2.ApiGrrUser)
  @Http("GET", "/api/v2/users/me")
  @NoAuditLogRequired()
  def GetGrrUser(
      self,
      args: None,
      context: Optional[api_call_context.ApiCallContext] = None,
  ):
    """Get current user settings."""

    raise NotImplementedError()

  @Category("User")
  @ProtoArgsType(api_user_pb2.ApiGrrUser)
  @ProtoResultType(api_user_pb2.ApiGrrUser)
  @Http("POST", "/api/v2/users/me")
  @NoAuditLogRequired()
  def UpdateGrrUser(
      self,
      args: api_user_pb2.ApiGrrUser,
      context: Optional[api_call_context.ApiCallContext] = None,
  ):
    """Update current user settings."""

    raise NotImplementedError()

  # Config methods.
  # ==============
  #
  @Category("Settings")
  @ProtoResultType(api_config_pb2.ApiGetConfigResult)
  @Http("GET", "/api/v2/config")
  @NoAuditLogRequired()
  def GetConfig(
      self,
      args: None,
      context: Optional[api_call_context.ApiCallContext] = None,
  ):
    """Get current AdminUI configuration."""

    raise NotImplementedError()

  @Category("Settings")
  @ProtoArgsType(api_config_pb2.ApiGetConfigOptionArgs)
  @ProtoResultType(api_config_pb2.ApiConfigOption)
  @Http("GET", "/api/v2/config/<name>")
  @NoAuditLogRequired()
  def GetConfigOption(
      self,
      args: api_config_pb2.ApiGetConfigOptionArgs,
      context: Optional[api_call_context.ApiCallContext] = None,
  ):
    """Get a single AdminUI configuration option."""

    raise NotImplementedError()

  @Category("Settings")
  @ProtoArgsType(api_config_pb2.ApiListGrrBinariesArgs)
  @ProtoResultType(api_config_pb2.ApiListGrrBinariesResult)
  @Http("GET", "/api/v2/config/binaries")
  @NoAuditLogRequired()
  def ListGrrBinaries(
      self,
      args: api_config_pb2.ApiListGrrBinariesArgs,
      context: Optional[api_call_context.ApiCallContext] = None,
  ):
    """List available GRR binaries (uploaded with grr_config_updater)."""

    raise NotImplementedError()

  @Category("Settings")
  @ProtoArgsType(api_config_pb2.ApiGetGrrBinaryArgs)
  @ProtoResultType(api_config_pb2.ApiGrrBinary)
  @Http("GET", "/api/v2/config/binaries/<type>/<path:path>")
  @NoAuditLogRequired()
  def GetGrrBinary(
      self,
      args: api_config_pb2.ApiGetGrrBinaryArgs,
      context: Optional[api_call_context.ApiCallContext] = None,
  ):
    """Get information about GRR binary with the following type and path."""

    raise NotImplementedError()

  @Category("Settings")
  @ProtoArgsType(api_config_pb2.ApiGetGrrBinaryBlobArgs)
  @ResultBinaryStream()
  @Http("GET", "/api/v2/config/binaries-blobs/<type>/<path:path>")
  @NoAuditLogRequired()
  def GetGrrBinaryBlob(
      self,
      args: api_config_pb2.ApiGetGrrBinaryBlobArgs,
      context: Optional[api_call_context.ApiCallContext] = None,
  ):
    """Get contents of a GRR binary (uploaded with grr_config_updater)."""

    raise NotImplementedError()

  @Category("Settings")
  @ProtoResultType(api_config_pb2.ApiUiConfig)
  @Http("GET", "/api/v2/config/ui")
  @NoAuditLogRequired()
  def GetUiConfig(
      self,
      args: None,
      context: Optional[api_call_context.ApiCallContext] = None,
  ):
    """Get configuration values for AdminUI (e.g. heading name, help url)."""

    raise NotImplementedError()

  # Reflection methods.
  # ==================
  #
  @Category("Reflection")
  @ProtoResultType(api_client_pb2.ApiListKbFieldsResult)
  @Http("GET", "/api/v2/clients/kb-fields")
  @NoAuditLogRequired()
  def ListKbFields(
      self,
      args: None,
      context: Optional[api_call_context.ApiCallContext] = None,
  ):
    """List all available KnowledgeBase fields."""

    raise NotImplementedError()

  @Category("Reflection")
  @ProtoResultType(api_flow_pb2.ApiListFlowDescriptorsResult)
  @Http("GET", "/api/v2/flows/descriptors")
  @NoAuditLogRequired()
  def ListFlowDescriptors(
      self,
      args: None,
      context: Optional[api_call_context.ApiCallContext] = None,
  ):
    """List descriptors of all the flows."""

    raise NotImplementedError()

  # Note: fix the name in ApiOutputPluginsListHandler
  @Category("Reflection")
  @ProtoResultType(api_reflection_pb2.ApiListOutputPluginDescriptorsResult)
  @Http("GET", "/api/v2/output-plugins/all")
  @NoAuditLogRequired()
  def ListOutputPluginDescriptors(
      self,
      args: None,
      context: Optional[api_call_context.ApiCallContext] = None,
  ):
    """List all known output plugins descriptors."""

    raise NotImplementedError()

  @Category("Reflection")
  @ProtoResultType(api_reflection_pb2.ApiListApiMethodsResult)
  @Http("GET", "/api/v2/reflection/api-methods")
  @NoAuditLogRequired()
  def ListApiMethods(
      self,
      args: None,
      context: Optional[api_call_context.ApiCallContext] = None,
  ):
    """List all available API methods."""

    raise NotImplementedError()

  @Category("Metadata")
  @ProtoResultType(api_metadata_pb2.ApiGetGrrVersionResult)
  @Http("GET", "/api/v2/metadata/version")
  @NoAuditLogRequired()
  def GetGrrVersion(
      self,
      args: None,
      context: Optional[api_call_context.ApiCallContext] = None,
  ) -> api_metadata.ApiGetGrrVersionHandler:
    """Returns version of the GRR server."""
    raise NotImplementedError()

  @Category("Metadata")
  @ProtoResultType(api_metadata_pb2.ApiGetOpenApiDescriptionResult)
  @Http("GET", "/api/v2/metadata/openapi")
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
  """Fallback Router if no other Router is matching the user's request."""

  def __init__(self, params=None):
    super().__init__(params)

    # Construct handlers explicitly to avoid cell-var-from-loop issue.
    def _MakeAccessForbiddenHandler(method_name):

      def _AccessForbidden(*args, **kwargs):
        raise access_control.UnauthorizedAccess(
            f"No authorized route for {method_name}. "
            "Requestor has no access to GRR or the given API endpoint."
        )

      return _AccessForbidden

    # Instead of overriding all HTTP hander method manually, list all methods
    # and override them at construction time.
    for method_name in self.GetAnnotatedMethods():
      setattr(self, method_name, _MakeAccessForbiddenHandler(method_name))
