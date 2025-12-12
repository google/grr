#!/usr/bin/env python
"""Implementation of a router class that has approvals-based ACL checks."""

from typing import Optional

from grr_response_proto import api_call_router_pb2
from grr_response_proto import hunts_pb2
from grr_response_proto import objects_pb2
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
from grr_response_server import access_control
from grr_response_server import data_store
from grr_response_server.authorization import groups
from grr_response_server.databases import db
from grr_response_server.flows.general import osquery
from grr_response_server.flows.general import timeline
from grr_response_server.gui import access_controller
from grr_response_server.gui import api_call_context
from grr_response_server.gui import api_call_handler_base
from grr_response_server.gui import api_call_router
from grr_response_server.gui import api_call_router_without_checks
from grr_response_server.gui.api_plugins import client as api_client
from grr_response_server.gui.api_plugins import flow as api_flow
from grr_response_server.gui.api_plugins import metadata as api_metadata
from grr_response_server.gui.api_plugins import signed_commands as api_signed_commands
from grr_response_server.gui.api_plugins import timeline as api_timeline
from grr_response_server.gui.api_plugins import user as api_user
from grr_response_server.gui.api_plugins import yara as api_yara


class ApprovalCheckParamsAdminAccessChecker(
    access_controller.AdminAccessChecker
):
  """Checks if a user has admin access based on the router params."""

  _AUTH_SUBJECT = "admin-access"

  def __init__(
      self,
      params: api_call_router_pb2.ApiCallRouterWithApprovalCheckParams,
  ) -> None:
    self._params = params

    self._admin_groups_manager = groups.CreateGroupAccessManager()
    for g in params.admin_groups:
      self._admin_groups_manager.AuthorizeGroup(g, self._AUTH_SUBJECT)

  # TODO: Add the `@override` annotation [1] once we can use
  # Python 3.12 features.
  #
  # [1]: https://peps.python.org/pep-0698/
  def CheckIfHasAdminAccess(self, username: str) -> None:
    """Checks whether a given user has admin access."""

    use_db_admin_attribute = not bool(self._params.ignore_admin_user_attribute)
    if use_db_admin_attribute:
      user = data_store.REL_DB.ReadGRRUser(username)
      if user.user_type == objects_pb2.GRRUser.UserType.USER_TYPE_ADMIN:
        return

    if username in self._params.admin_users:
      return

    if self._admin_groups_manager.MemberOfAuthorizedGroup(
        username, self._AUTH_SUBJECT
    ):
      return

    raise access_control.UnauthorizedAccess(
        "No Admin user access for %s." % username
    )


class ApprovalCheckParamsMitigationFlowsAccessChecker(
    access_controller.MitigationFlowsAccessChecker
):
  """Checks if a user has permission to run mitigation flows based on the router params."""

  _AUTH_SUBJECT = "mitigation-flows-access"

  def __init__(
      self,
      params: api_call_router_pb2.ApiCallRouterWithApprovalCheckParams,
  ) -> None:
    self._params = params

    self._admin_groups_manager = groups.CreateGroupAccessManager()
    for g in params.mitigation_flows_groups:
      self._admin_groups_manager.AuthorizeGroup(g, self._AUTH_SUBJECT)

  # TODO: Add the `@override` annotation [1] once we can use
  # Python 3.12 features.
  #
  # [1]: https://peps.python.org/pep-0698/
  def CheckIfHasAccessToMitigationFlows(self, username: str) -> None:
    """Checks whether a given user has access to mitigation flows."""

    if username in self._params.mitigation_flows_users:
      return

    if self._admin_groups_manager.MemberOfAuthorizedGroup(
        username, self._AUTH_SUBJECT
    ):
      return

    raise access_control.UnauthorizedAccess(
        f"No access to mitigation flows for {username}."
    )


class ApiCallRouterWithApprovalChecks(api_call_router.ApiCallRouterStub):
  """Router that uses approvals-based ACL checks."""

  proto_params_type = api_call_router_pb2.ApiCallRouterWithApprovalCheckParams

  cached_admin_access_checker = None
  cached_approval_checker = None

  @staticmethod
  def ClearCache():
    cls = ApiCallRouterWithApprovalChecks
    cls.cached_approval_checker = None
    cls.cached_admin_access_checker = None

  def _GetApprovalChecker(
      self,
      admin_access_checker: ApprovalCheckParamsAdminAccessChecker,
  ):
    cls = ApiCallRouterWithApprovalChecks

    if cls.cached_approval_checker is None:
      cls.cached_approval_checker = access_controller.ApprovalChecker(
          admin_access_checker
      )

    return cls.cached_approval_checker

  def _CheckFlowOrClientAccess(
      self, client_id: str, flow_id: str, context=None
  ):
    try:
      flow = data_store.REL_DB.ReadFlowObject(client_id, flow_id)
    except db.UnknownFlowError as e:
      raise api_call_handler_base.ResourceNotFoundError(
          "Flow with client id %s and flow id %s could not be found"
          % (client_id, flow_id)
      ) from e

    # Check for client access if this flow was not scheduled as part of a hunt.
    # Only top-level hunt flows are allowed, which is what any user can see
    # as "hunt results" (child flows results are not available for anyone).
    if flow.parent_hunt_id != flow.flow_id:
      self.approval_checker.CheckClientAccess(context, client_id)

  def __init__(
      self,
      params: Optional[
          api_call_router_pb2.ApiCallRouterWithApprovalCheckParams
      ] = None,
      approval_checker: Optional[access_controller.ApprovalChecker] = None,
      admin_access_checker: Optional[
          ApprovalCheckParamsAdminAccessChecker
      ] = None,
      mitigation_flows_access_checker: Optional[
          ApprovalCheckParamsMitigationFlowsAccessChecker
      ] = None,
      delegate: Optional[api_call_router.ApiCallRouter] = None,
  ):
    super().__init__(params=params)

    if not admin_access_checker:
      admin_access_checker = ApprovalCheckParamsAdminAccessChecker(params)
    self.admin_access_checker = admin_access_checker

    if not approval_checker:
      approval_checker = self._GetApprovalChecker(self.admin_access_checker)
    self.approval_checker = approval_checker

    if not mitigation_flows_access_checker:
      mitigation_flows_access_checker = (
          ApprovalCheckParamsMitigationFlowsAccessChecker(params)
      )
    self.mitigation_flows_access_checker = mitigation_flows_access_checker

    if not delegate:
      delegate = api_call_router_without_checks.ApiCallRouterWithoutChecks()
    self.delegate = delegate

  # Artifacts methods.
  # =================
  #
  # pytype: disable=attribute-error
  def ListArtifacts(
      self,
      args: api_artifact_pb2.ApiListArtifactsArgs,
      context: Optional[api_call_context.ApiCallContext] = None,
  ):
    # Everybody is allowed to list artifacts.

    return self.delegate.ListArtifacts(args, context=context)

  def UploadArtifact(
      self,
      args: api_artifact_pb2.ApiUploadArtifactArgs,
      context: Optional[api_call_context.ApiCallContext] = None,
  ):
    # Everybody is allowed to upload artifacts.

    return self.delegate.UploadArtifact(args, context=context)

  def DeleteArtifacts(
      self,
      args: api_artifact_pb2.ApiDeleteArtifactsArgs,
      context: Optional[api_call_context.ApiCallContext] = None,
  ):
    # Everybody is allowed to delete artifacts.

    return self.delegate.DeleteArtifacts(args, context=context)

  # Clients methods.
  # ===============
  #
  def SearchClients(
      self,
      args: api_client_pb2.ApiSearchClientsArgs,
      context: Optional[api_call_context.ApiCallContext] = None,
  ):
    # Everybody is allowed to search clients.

    return self.delegate.SearchClients(args, context=context)

  def VerifyAccess(
      self,
      args: api_client_pb2.ApiVerifyAccessArgs,
      context: Optional[api_call_context.ApiCallContext] = None,
  ):
    self.approval_checker.CheckClientAccess(context, args.client_id)

    return self.delegate.VerifyAccess(args, context=context)

  def GetClient(
      self,
      args: api_client_pb2.ApiGetClientArgs,
      context: Optional[api_call_context.ApiCallContext] = None,
  ):
    # Everybody is allowed to get information about a particular client.

    return self.delegate.GetClient(args, context=context)

  def GetClientVersions(
      self,
      args: api_client_pb2.ApiGetClientVersionsArgs,
      context: Optional[api_call_context.ApiCallContext] = None,
  ):
    # Everybody is allowed to get historical information about a client.

    return self.delegate.GetClientVersions(args, context=context)

  def GetClientVersionTimes(
      self,
      args: api_client_pb2.ApiGetClientVersionTimesArgs,
      context: Optional[api_call_context.ApiCallContext] = None,
  ):
    # Everybody is allowed to get the versions of a particular client.

    return self.delegate.GetClientVersionTimes(args, context=context)

  def GetClientSnapshots(
      self,
      args: api_client_pb2.ApiGetClientSnapshotsArgs,
      context: Optional[api_call_context.ApiCallContext] = None,
  ):
    # Everybody is allowed to get historical information about a client.

    return self.delegate.GetClientSnapshots(args, context=context)

  def GetClientStartupInfos(
      self,
      args: api_client_pb2.ApiGetClientStartupInfosArgs,
      context: Optional[api_call_context.ApiCallContext] = None,
  ) -> api_client.ApiGetClientStartupInfosHandler:
    # Everybody is allowed to get historical information about a client.

    return self.delegate.GetClientStartupInfos(args, context=context)

  def InterrogateClient(
      self,
      args: api_client_pb2.ApiInterrogateClientArgs,
      context: Optional[api_call_context.ApiCallContext] = None,
  ):
    self.approval_checker.CheckClientAccess(context, args.client_id)

    return self.delegate.InterrogateClient(args, context=context)

  def GetLastClientIPAddress(
      self,
      args: api_client_pb2.ApiGetLastClientIPAddressArgs,
      context: Optional[api_call_context.ApiCallContext] = None,
  ):
    # Everybody is allowed to get the last ip address of a particular client.

    return self.delegate.GetLastClientIPAddress(args, context=context)

  def ListClientCrashes(
      self,
      args: api_client_pb2.ApiListClientCrashesArgs,
      context: Optional[api_call_context.ApiCallContext] = None,
  ):
    self.approval_checker.CheckClientAccess(context, args.client_id)

    return self.delegate.ListClientCrashes(args, context=context)

  def KillFleetspeak(
      self,
      args: api_client_pb2.ApiKillFleetspeakArgs,
      context: Optional[api_call_context.ApiCallContext] = None,
  ) -> api_client.ApiKillFleetspeakHandler:
    self.approval_checker.CheckClientAccess(context, args.client_id)
    return self.delegate.KillFleetspeak(args, context=context)

  def RestartFleetspeakGrrService(
      self,
      args: api_client_pb2.ApiRestartFleetspeakGrrServiceArgs,
      context: Optional[api_call_context.ApiCallContext] = None,
  ) -> api_client.ApiRestartFleetspeakGrrServiceHandler:
    self.approval_checker.CheckClientAccess(context, args.client_id)
    return self.delegate.RestartFleetspeakGrrService(args, context=context)

  def DeleteFleetspeakPendingMessages(
      self,
      args: api_client_pb2.ApiDeleteFleetspeakPendingMessagesArgs,
      context: Optional[api_call_context.ApiCallContext] = None,
  ) -> api_client.ApiDeleteFleetspeakPendingMessagesHandler:
    self.approval_checker.CheckClientAccess(context, args.client_id)
    return self.delegate.DeleteFleetspeakPendingMessages(args, context=context)

  def GetFleetspeakPendingMessages(
      self,
      args: api_client_pb2.ApiGetFleetspeakPendingMessagesArgs,
      context: Optional[api_call_context.ApiCallContext] = None,
  ) -> api_client.ApiGetFleetspeakPendingMessagesHandler:
    self.approval_checker.CheckClientAccess(context, args.client_id)
    return self.delegate.GetFleetspeakPendingMessages(args, context=context)

  def GetFleetspeakPendingMessageCount(
      self,
      args: api_client_pb2.ApiGetFleetspeakPendingMessageCountArgs,
      context: Optional[api_call_context.ApiCallContext] = None,
  ) -> api_client.ApiGetFleetspeakPendingMessageCountHandler:
    self.approval_checker.CheckClientAccess(context, args.client_id)
    return self.delegate.GetFleetspeakPendingMessageCount(args, context=context)

  # Virtual file system methods.
  # ============================
  #
  def ListFiles(
      self,
      args: api_vfs_pb2.ApiListFilesArgs,
      context: Optional[api_call_context.ApiCallContext] = None,
  ):
    self.approval_checker.CheckClientAccess(context, args.client_id)

    return self.delegate.ListFiles(args, context=context)

  def BrowseFilesystem(
      self,
      args: api_vfs_pb2.ApiBrowseFilesystemArgs,
      context: Optional[api_call_context.ApiCallContext] = None,
  ):
    self.approval_checker.CheckClientAccess(context, args.client_id)

    return self.delegate.BrowseFilesystem(args, context=context)

  def GetVfsFilesArchive(
      self,
      args: api_vfs_pb2.ApiGetVfsFilesArchiveArgs,
      context: Optional[api_call_context.ApiCallContext] = None,
  ):
    self.approval_checker.CheckClientAccess(context, args.client_id)

    return self.delegate.GetVfsFilesArchive(args, context=context)

  def GetFileDetails(
      self,
      args: api_vfs_pb2.ApiGetFileDetailsArgs,
      context: Optional[api_call_context.ApiCallContext] = None,
  ):
    self.approval_checker.CheckClientAccess(context, args.client_id)

    return self.delegate.GetFileDetails(args, context=context)

  def GetFileText(
      self,
      args: api_vfs_pb2.ApiGetFileTextArgs,
      context: Optional[api_call_context.ApiCallContext] = None,
  ):
    self.approval_checker.CheckClientAccess(context, args.client_id)

    return self.delegate.GetFileText(args, context=context)

  def GetFileBlob(
      self,
      args: api_vfs_pb2.ApiGetFileBlobArgs,
      context: Optional[api_call_context.ApiCallContext] = None,
  ):
    self.approval_checker.CheckClientAccess(context, args.client_id)

    return self.delegate.GetFileBlob(args, context=context)

  def GetFileVersionTimes(
      self,
      args: api_vfs_pb2.ApiGetFileVersionTimesArgs,
      context: Optional[api_call_context.ApiCallContext] = None,
  ):
    self.approval_checker.CheckClientAccess(context, args.client_id)

    return self.delegate.GetFileVersionTimes(args, context=context)

  def GetFileDownloadCommand(
      self,
      args: api_vfs_pb2.ApiGetFileDownloadCommandArgs,
      context: Optional[api_call_context.ApiCallContext] = None,
  ):
    self.approval_checker.CheckClientAccess(context, args.client_id)

    return self.delegate.GetFileDownloadCommand(args, context=context)

  def CreateVfsRefreshOperation(
      self,
      args: api_vfs_pb2.ApiCreateVfsRefreshOperationArgs,
      context: Optional[api_call_context.ApiCallContext] = None,
  ):
    self.approval_checker.CheckClientAccess(context, args.client_id)

    return self.delegate.CreateVfsRefreshOperation(args, context=context)

  def GetVfsRefreshOperationState(
      self,
      args: api_vfs_pb2.ApiGetVfsRefreshOperationStateArgs,
      context: Optional[api_call_context.ApiCallContext] = None,
  ):
    # No ACL checks are required here, since the user can only check
    # operations started by themselves.

    return self.delegate.GetVfsRefreshOperationState(args, context=context)

  def GetVfsTimeline(
      self,
      args: api_vfs_pb2.ApiGetVfsTimelineArgs,
      context: Optional[api_call_context.ApiCallContext] = None,
  ):
    self.approval_checker.CheckClientAccess(context, args.client_id)

    return self.delegate.GetVfsTimeline(args, context=context)

  def GetVfsTimelineAsCsv(
      self,
      args: api_vfs_pb2.ApiGetVfsTimelineAsCsvArgs,
      context: Optional[api_call_context.ApiCallContext] = None,
  ):
    self.approval_checker.CheckClientAccess(context, args.client_id)

    return self.delegate.GetVfsTimelineAsCsv(args, context=context)

  def UpdateVfsFileContent(
      self,
      args: api_vfs_pb2.ApiUpdateVfsFileContentArgs,
      context: Optional[api_call_context.ApiCallContext] = None,
  ):
    self.approval_checker.CheckClientAccess(context, args.client_id)

    return self.delegate.UpdateVfsFileContent(args, context=context)

  def GetVfsFileContentUpdateState(
      self,
      args: api_vfs_pb2.ApiGetVfsFileContentUpdateStateArgs,
      context: Optional[api_call_context.ApiCallContext] = None,
  ):
    # No ACL checks are required here, since the user can only check
    # operations started by themselves.

    return self.delegate.GetVfsFileContentUpdateState(args, context=context)

  # Clients labels methods.
  # ======================
  #
  def ListClientsLabels(self, args, context=None):
    # Everybody is allowed to get a list of all labels used on the system.

    return self.delegate.ListClientsLabels(args, context=context)

  def AddClientsLabels(
      self,
      args: api_client_pb2.ApiAddClientsLabelsArgs,
      context: Optional[api_call_context.ApiCallContext] = None,
  ):
    # Everybody is allowed to add labels. Labels owner will be attributed to
    # the current user.

    return self.delegate.AddClientsLabels(args, context=context)

  def RemoveClientsLabels(
      self,
      args: api_client_pb2.ApiRemoveClientsLabelsArgs,
      context: Optional[api_call_context.ApiCallContext] = None,
  ):
    # Everybody is allowed to remove labels. ApiRemoveClientsLabelsHandler is
    # written in such a way, so that it will only delete user's own labels.

    return self.delegate.RemoveClientsLabels(args, context=context)

  # Clients flows methods.
  # =====================
  #
  def ListFlows(
      self,
      args: api_flow_pb2.ApiListFlowsArgs,
      context: Optional[api_call_context.ApiCallContext] = None,
  ):
    self.approval_checker.CheckClientAccess(context, args.client_id)

    return self.delegate.ListFlows(args, context=context)

  def GetFlow(
      self,
      args: api_flow_pb2.ApiGetFlowArgs,
      context: Optional[api_call_context.ApiCallContext] = None,
  ):
    self._CheckFlowOrClientAccess(args.client_id, args.flow_id, context)

    return self.delegate.GetFlow(args, context=context)

  def CreateFlow(
      self,
      args: api_flow_pb2.ApiCreateFlowArgs,
      context: Optional[api_call_context.ApiCallContext] = None,
  ):
    self.approval_checker.CheckClientAccess(context, args.client_id)
    self.admin_access_checker.CheckIfCanStartFlow(
        context.username, args.flow.name or args.flow.runner_args.flow_name
    )
    self.mitigation_flows_access_checker.CheckIfHasAccessToFlow(
        context.username, args.flow.name or args.flow.runner_args.flow_name
    )

    return self.delegate.CreateFlow(args, context=context)

  def CancelFlow(
      self,
      args: api_flow_pb2.ApiCancelFlowArgs,
      context: Optional[api_call_context.ApiCallContext] = None,
  ):
    self.approval_checker.CheckClientAccess(context, args.client_id)

    return self.delegate.CancelFlow(args, context=context)

  def ListFlowRequests(
      self,
      args: api_flow_pb2.ApiListFlowRequestsArgs,
      context: Optional[api_call_context.ApiCallContext] = None,
  ):
    self.approval_checker.CheckClientAccess(context, args.client_id)

    return self.delegate.ListFlowRequests(args, context=context)

  def ListFlowResults(
      self,
      args: api_flow_pb2.ApiListFlowResultsArgs,
      context: Optional[api_call_context.ApiCallContext] = None,
  ) -> api_flow.ApiListFlowResultsHandler:
    self._CheckFlowOrClientAccess(args.client_id, args.flow_id, context)

    return self.delegate.ListFlowResults(args, context=context)

  def GetExportedFlowResults(
      self,
      args: api_flow_pb2.ApiGetExportedFlowResultsArgs,
      context: Optional[api_call_context.ApiCallContext] = None,
  ):
    self._CheckFlowOrClientAccess(args.client_id, args.flow_id, context)

    return self.delegate.GetExportedFlowResults(args, context=context)

  def GetFlowResultsExportCommand(
      self,
      args: api_flow_pb2.ApiGetFlowResultsExportCommandArgs,
      context: Optional[api_call_context.ApiCallContext] = None,
  ):
    self._CheckFlowOrClientAccess(args.client_id, args.flow_id, context)

    return self.delegate.GetFlowResultsExportCommand(args, context=context)

  def GetFlowFilesArchive(
      self,
      args: api_flow_pb2.ApiGetFlowFilesArchiveArgs,
      context: Optional[api_call_context.ApiCallContext] = None,
  ) -> api_flow.ApiGetFlowFilesArchiveHandler:
    self._CheckFlowOrClientAccess(
        str(args.client_id), str(args.flow_id), context
    )

    return self.delegate.GetFlowFilesArchive(args, context=context)

  def ListFlowOutputPlugins(
      self,
      args: api_flow_pb2.ApiListFlowOutputPluginsArgs,
      context: Optional[api_call_context.ApiCallContext] = None,
  ):
    self.approval_checker.CheckClientAccess(context, args.client_id)

    return self.delegate.ListFlowOutputPlugins(args, context=context)

  def ListFlowOutputPluginLogs(
      self,
      args: api_flow_pb2.ApiListFlowOutputPluginLogsArgs,
      context: Optional[api_call_context.ApiCallContext] = None,
  ):
    self.approval_checker.CheckClientAccess(context, args.client_id)

    return self.delegate.ListFlowOutputPluginLogs(args, context=context)

  def ListFlowOutputPluginErrors(
      self,
      args: api_flow_pb2.ApiListFlowOutputPluginErrorsArgs,
      context: Optional[api_call_context.ApiCallContext] = None,
  ):
    self.approval_checker.CheckClientAccess(context, args.client_id)

    return self.delegate.ListFlowOutputPluginErrors(args, context=context)

  def ListAllFlowOutputPluginLogs(
      self,
      args: api_flow_pb2.ApiListAllFlowOutputPluginLogsArgs,
      context: Optional[api_call_context.ApiCallContext] = None,
  ):
    self.approval_checker.CheckClientAccess(context, args.client_id)

    return self.delegate.ListAllFlowOutputPluginLogs(args, context=context)

  def ListFlowLogs(
      self,
      args: api_flow_pb2.ApiListFlowLogsArgs,
      context: Optional[api_call_context.ApiCallContext] = None,
  ):
    self.approval_checker.CheckClientAccess(context, args.client_id)

    return self.delegate.ListFlowLogs(args, context=context)

  def GetCollectedTimeline(
      self,
      args: api_timeline_pb2.ApiGetCollectedTimelineArgs,
      context: Optional[api_call_context.ApiCallContext] = None,
  ):
    try:
      flow = data_store.REL_DB.ReadFlowObject(args.client_id, args.flow_id)
    except db.UnknownFlowError:
      raise api_call_handler_base.ResourceNotFoundError(
          "Flow with client id %s and flow id %s could not be found"
          % (args.client_id, args.flow_id)
      )

    if flow.flow_class_name != timeline.TimelineFlow.__name__:
      raise ValueError("Flow '{}' is not a timeline flow".format(flow.flow_id))

    # Check for client access if this flow was not scheduled as part of a hunt.
    if flow.parent_hunt_id != flow.flow_id:
      self.approval_checker.CheckClientAccess(context, args.client_id)

    return self.delegate.GetCollectedTimeline(args, context=context)

  def UploadYaraSignature(
      self,
      args: api_yara_pb2.ApiUploadYaraSignatureArgs,
      context: Optional[api_call_context.ApiCallContext] = None,
  ) -> api_yara.ApiUploadYaraSignatureHandler:
    return self.delegate.UploadYaraSignature(args, context=context)

  def ExplainGlobExpression(
      self,
      args: api_flow_pb2.ApiExplainGlobExpressionArgs,
      context: Optional[api_call_context.ApiCallContext] = None,
  ) -> api_flow.ApiExplainGlobExpressionHandler:
    # ExplainGlobExpression only exposes the KnowledgeBase, which does not need
    # approval.
    return self.delegate.ExplainGlobExpression(args, context=context)

  def ScheduleFlow(
      self,
      args: api_flow_pb2.ApiCreateFlowArgs,
      context: Optional[api_call_context.ApiCallContext] = None,
  ) -> api_flow.ApiScheduleFlowHandler:
    self.mitigation_flows_access_checker.CheckIfHasAccessToFlow(
        context.username, args.flow.name or args.flow.runner_args.flow_name
    )

    return self.delegate.ScheduleFlow(args, context=context)

  def ListScheduledFlows(
      self,
      args: api_flow_pb2.ApiListScheduledFlowsArgs,
      context: Optional[api_call_context.ApiCallContext] = None,
  ) -> api_flow.ApiListScheduledFlowsHandler:
    return self.delegate.ListScheduledFlows(args, context=context)

  def UnscheduleFlow(
      self,
      args: api_flow_pb2.ApiUnscheduleFlowArgs,
      context: Optional[api_call_context.ApiCallContext] = None,
  ) -> api_flow.ApiUnscheduleFlowHandler:
    return self.delegate.UnscheduleFlow(args, context=context)

  def GetOsqueryResults(
      self,
      args: api_osquery_pb2.ApiGetOsqueryResultsArgs,
      context: Optional[api_call_context.ApiCallContext] = None,
  ):
    try:
      flow = data_store.REL_DB.ReadFlowObject(
          str(args.client_id), str(args.flow_id)
      )
    except db.UnknownFlowError:
      raise api_call_handler_base.ResourceNotFoundError(
          "Flow with client id %s and flow id %s could not be found"
          % (args.client_id, args.flow_id)
      )

    if flow.flow_class_name != osquery.OsqueryFlow.__name__:
      raise ValueError("Flow '{}' is not an osquery flow".format(flow.flow_id))

    # Check for client access if this flow was not scheduled as part of a hunt.
    if flow.parent_hunt_id != flow.flow_id:
      self.approval_checker.CheckClientAccess(context, str(args.client_id))

    return self.delegate.GetOsqueryResults(args, context=context)

  # Signed commands methods.
  # ========================
  #
  def ListSignedCommands(
      self,
      args: Optional[None] = None,
      context: Optional[api_call_context.ApiCallContext] = None,
  ) -> api_signed_commands.ApiListSignedCommandsHandler:
    # Everybody can retrieve signed commands.

    return self.delegate.ListSignedCommands(args, context=context)

  # Cron jobs methods.
  # =================
  #
  def ListCronJobs(
      self,
      args: api_cron_pb2.ApiListCronJobsArgs,
      context: Optional[api_call_context.ApiCallContext] = None,
  ):
    # Everybody can list cron jobs.

    return self.delegate.ListCronJobs(args, context=context)

  def CreateCronJob(
      self,
      args: api_cron_pb2.ApiCreateCronJobArgs,
      context: Optional[api_call_context.ApiCallContext] = None,
  ):
    # Everybody can create a cron job.

    return self.delegate.CreateCronJob(args, context=context)

  def GetCronJob(
      self,
      args: api_cron_pb2.ApiGetCronJobArgs,
      context: Optional[api_call_context.ApiCallContext] = None,
  ):
    # Everybody can retrieve a cron job.

    return self.delegate.GetCronJob(args, context=context)

  def ForceRunCronJob(
      self,
      args: api_cron_pb2.ApiForceRunCronJobArgs,
      context: Optional[api_call_context.ApiCallContext] = None,
  ):
    self.approval_checker.CheckCronJobAccess(context, str(args.cron_job_id))

    return self.delegate.ForceRunCronJob(args, context=context)

  def ModifyCronJob(
      self,
      args: api_cron_pb2.ApiModifyCronJobArgs,
      context: Optional[api_call_context.ApiCallContext] = None,
  ):
    self.approval_checker.CheckCronJobAccess(context, str(args.cron_job_id))

    return self.delegate.ModifyCronJob(args, context=context)

  def ListCronJobRuns(
      self,
      args: api_cron_pb2.ApiListCronJobRunsArgs,
      context: Optional[api_call_context.ApiCallContext] = None,
  ):
    # Everybody can list cron jobs' runs.

    return self.delegate.ListCronJobRuns(args, context=context)

  def GetCronJobRun(
      self,
      args: api_cron_pb2.ApiGetCronJobRunArgs,
      context: Optional[api_call_context.ApiCallContext] = None,
  ):
    # Everybody can get cron runs.

    return self.delegate.GetCronJobRun(args, context=context)

  def DeleteCronJob(
      self,
      args: api_cron_pb2.ApiDeleteCronJobArgs,
      context: Optional[api_call_context.ApiCallContext] = None,
  ):
    self.approval_checker.CheckCronJobAccess(context, str(args.cron_job_id))

    return self.delegate.DeleteCronJob(args, context=context)

  # Hunts methods.
  # =============
  #
  def ListHunts(
      self,
      args: api_hunt_pb2.ApiListHuntsArgs,
      context: Optional[api_call_context.ApiCallContext] = None,
  ):
    # Everybody can list hunts.

    return self.delegate.ListHunts(args, context=context)

  def VerifyHuntAccess(
      self,
      args: api_hunt_pb2.ApiVerifyHuntAccessArgs,
      context: Optional[api_call_context.ApiCallContext] = None,
  ):
    self.approval_checker.CheckHuntAccess(context, str(args.hunt_id))

    return self.delegate.VerifyHuntAccess(args, context=context)

  def GetHunt(
      self,
      args: api_hunt_pb2.ApiGetHuntArgs,
      context: Optional[api_call_context.ApiCallContext] = None,
  ):
    # Everybody can get hunt's information.

    return self.delegate.GetHunt(args, context=context)

  def ListHuntErrors(
      self,
      args: api_hunt_pb2.ApiListHuntErrorsArgs,
      context: Optional[api_call_context.ApiCallContext] = None,
  ):
    # Everybody can get hunt errors list.

    return self.delegate.ListHuntErrors(args, context=context)

  def ListHuntLogs(
      self,
      args: api_hunt_pb2.ApiListHuntLogsArgs,
      context: Optional[api_call_context.ApiCallContext] = None,
  ):
    # Everybody can look into hunt's logs.

    return self.delegate.ListHuntLogs(args, context=context)

  def ListHuntResults(
      self,
      args: api_hunt_pb2.ApiListHuntResultsArgs,
      context: Optional[api_call_context.ApiCallContext] = None,
  ):
    # Everybody can look into hunt's results.

    return self.delegate.ListHuntResults(args, context=context)

  def CountHuntResultsByType(
      self,
      args: api_hunt_pb2.ApiCountHuntResultsByTypeArgs,
      context: Optional[api_call_context.ApiCallContext] = None,
  ):
    # Everybody can look into hunt's results.

    return self.delegate.CountHuntResultsByType(args, context=context)

  def GetExportedHuntResults(
      self,
      args: api_hunt_pb2.ApiGetExportedHuntResultsArgs,
      context: Optional[api_call_context.ApiCallContext] = None,
  ):
    # Everybody can export hunt's results.

    return self.delegate.GetExportedHuntResults(args, context=context)

  def GetHuntResultsExportCommand(
      self,
      args: api_hunt_pb2.ApiGetHuntResultsExportCommandArgs,
      context: Optional[api_call_context.ApiCallContext] = None,
  ):
    # Everybody can get hunt's export command.

    return self.delegate.GetHuntResultsExportCommand(args, context=context)

  def ListHuntOutputPlugins(
      self,
      args: api_hunt_pb2.ApiListHuntOutputPluginsArgs,
      context: Optional[api_call_context.ApiCallContext] = None,
  ):
    # Everybody can list hunt output plugins.

    return self.delegate.ListHuntOutputPlugins(args, context=context)

  def ListHuntOutputPluginLogs(
      self,
      args: api_hunt_pb2.ApiListHuntOutputPluginLogsArgs,
      context: Optional[api_call_context.ApiCallContext] = None,
  ):
    # Everybody can list hunt output plugins logs.

    return self.delegate.ListHuntOutputPluginLogs(args, context=context)

  def ListHuntOutputPluginErrors(
      self,
      args: api_hunt_pb2.ApiListHuntOutputPluginErrorsArgs,
      context: Optional[api_call_context.ApiCallContext] = None,
  ):
    # Everybody can list hunt output plugin errors.

    return self.delegate.ListHuntOutputPluginErrors(args, context=context)

  def ListHuntCrashes(
      self,
      args: api_hunt_pb2.ApiListHuntCrashesArgs,
      context: Optional[api_call_context.ApiCallContext] = None,
  ):
    # Everybody can list hunt's crashes.

    return self.delegate.ListHuntCrashes(args, context=context)

  def GetHuntClientCompletionStats(
      self,
      args: api_hunt_pb2.ApiGetHuntClientCompletionStatsArgs,
      context: Optional[api_call_context.ApiCallContext] = None,
  ):
    # Everybody can get hunt's client completion stats.

    return self.delegate.GetHuntClientCompletionStats(args, context=context)

  def GetHuntStats(
      self,
      args: api_hunt_pb2.ApiGetHuntStatsArgs,
      context: Optional[api_call_context.ApiCallContext] = None,
  ):
    # Everybody can get hunt's stats.

    return self.delegate.GetHuntStats(args, context=context)

  def ListHuntClients(
      self,
      args: api_hunt_pb2.ApiListHuntClientsArgs,
      context: Optional[api_call_context.ApiCallContext] = None,
  ):
    # Everybody can get hunt's clients.

    return self.delegate.ListHuntClients(args, context=context)

  def GetHuntContext(
      self,
      args: api_hunt_pb2.ApiGetHuntContextArgs,
      context: Optional[api_call_context.ApiCallContext] = None,
  ):
    # Everybody can get hunt's context.

    return self.delegate.GetHuntContext(args, context=context)

  def CreateHunt(
      self,
      args: api_hunt_pb2.ApiCreateHuntArgs,
      context: Optional[api_call_context.ApiCallContext] = None,
  ):
    # One can create a hunt if one can create a flow of the same type.
    #
    # If the user doesn't have access to restricted flows, the user
    # shouldn't be able to create hunts involving such flows.
    #
    # Note: after the hunt is created, even if it involved restricted flows,
    # normal approval ACL checks apply. Namely: another user can start
    # such a hunt, if such user gets a valid hunt approval.
    self.admin_access_checker.CheckIfCanStartFlow(
        context.username, args.flow_name
    )
    self.mitigation_flows_access_checker.CheckIfHasAccessToFlow(
        context.username, args.flow_name
    )

    return self.delegate.CreateHunt(args, context=context)

  def ModifyHunt(
      self,
      args: api_hunt_pb2.ApiModifyHuntArgs,
      context: Optional[api_call_context.ApiCallContext] = None,
  ):
    # Starting/stopping hunt or modifying its attributes requires an approval.
    self.approval_checker.CheckHuntAccess(context, str(args.hunt_id))

    return self.delegate.ModifyHunt(args, context=context)

  def _GetHuntObj(self, hunt_id: str) -> hunts_pb2.Hunt:
    try:
      return data_store.REL_DB.ReadHuntObject(hunt_id)
    except db.UnknownHuntError:
      raise api_call_handler_base.ResourceNotFoundError(
          "Hunt with id %s could not be found" % hunt_id
      )

  def DeleteHunt(
      self,
      args: api_hunt_pb2.ApiDeleteHuntArgs,
      context: Optional[api_call_context.ApiCallContext] = None,
  ):
    hunt_obj = self._GetHuntObj(args.hunt_id)

    # Hunt's creator is allowed to delete the hunt.
    if context.username != hunt_obj.creator:
      self.approval_checker.CheckHuntAccess(context, str(args.hunt_id))

    return self.delegate.DeleteHunt(args, context=context)

  def GetHuntFilesArchive(
      self,
      args: api_hunt_pb2.ApiGetHuntFilesArchiveArgs,
      context: Optional[api_call_context.ApiCallContext] = None,
  ):
    self.approval_checker.CheckHuntAccess(context, str(args.hunt_id))

    return self.delegate.GetHuntFilesArchive(args, context=context)

  def GetHuntFile(
      self,
      args: api_hunt_pb2.ApiGetHuntFileArgs,
      context: Optional[api_call_context.ApiCallContext] = None,
  ):
    self.approval_checker.CheckHuntAccess(context, str(args.hunt_id))

    return self.delegate.GetHuntFile(args, context=context)

  def GetCollectedHuntTimelines(
      self,
      args: api_timeline_pb2.ApiGetCollectedHuntTimelinesArgs,
      context: Optional[api_call_context.ApiCallContext] = None,
  ) -> api_timeline.ApiGetCollectedHuntTimelinesHandler:
    # Everybody can export collected hunt timelines.
    return self.delegate.GetCollectedHuntTimelines(args, context=context)

  # Approvals methods.
  # =================
  #
  def CreateClientApproval(
      self,
      args: api_user_pb2.ApiCreateClientApprovalArgs,
      context: Optional[api_call_context.ApiCallContext] = None,
  ):
    # Everybody can create a user client approval.
    return api_user.ApiCreateClientApprovalHandler(self.approval_checker)

  def GetClientApproval(
      self,
      args: api_user_pb2.ApiGetClientApprovalArgs,
      context: Optional[api_call_context.ApiCallContext] = None,
  ):
    # Everybody can have access to everybody's client approvals, provided
    # they know: a client id, a username of the requester and an approval id.

    return api_user.ApiGetClientApprovalHandler(self.approval_checker)

  def GrantClientApproval(
      self,
      args: api_user_pb2.ApiGrantClientApprovalArgs,
      context: Optional[api_call_context.ApiCallContext] = None,
  ):
    # Everybody can grant everybody's client approvals, provided
    # they know: a client id, a username of the requester and an approval id.
    #
    # NOTE: Granting an approval doesn't necessarily mean that corresponding
    # approval request becomes fulfilled right away. Calling this method
    # adds the caller to the approval's approvers list. Then it depends
    # on a particular approval if this list is sufficient or not.
    # Typical case: user can grant their own approval, but this won't make
    # the approval valid.

    return api_user.ApiGrantClientApprovalHandler(self.approval_checker)

  def ListClientApprovals(
      self,
      args: api_user_pb2.ApiListClientApprovalsArgs,
      context: Optional[api_call_context.ApiCallContext] = None,
  ):
    # Everybody can list their own user client approvals.

    return api_user.ApiListClientApprovalsHandler(self.approval_checker)

  def CreateHuntApproval(
      self,
      args: api_user_pb2.ApiCreateHuntApprovalArgs,
      context: Optional[api_call_context.ApiCallContext] = None,
  ):
    # Everybody can request a hunt approval.

    return api_user.ApiCreateHuntApprovalHandler(self.approval_checker)

  def GetHuntApproval(
      self,
      args: api_user_pb2.ApiGetHuntApprovalArgs,
      context: Optional[api_call_context.ApiCallContext] = None,
  ):
    # Everybody can have access to everybody's hunts approvals, provided
    # they know: a hunt id, a username of the requester and an approval id.

    return api_user.ApiGetHuntApprovalHandler(self.approval_checker)

  def GrantHuntApproval(
      self,
      args: api_user_pb2.ApiGrantHuntApprovalArgs,
      context: Optional[api_call_context.ApiCallContext] = None,
  ):
    # Everybody can grant everybody's hunts approvals, provided
    # they know: a hunt id, a username of the requester and an approval id.
    #
    # NOTE: Granting an approval doesn't necessarily mean that corresponding
    # approval request becomes fulfilled right away. Calling this method
    # adds the caller to the approval's approvers list. Then it depends
    # on a particular approval if this list is sufficient or not.
    # Typical case: user can grant their own approval, but this won't make
    # the approval valid.

    return api_user.ApiGrantHuntApprovalHandler(self.approval_checker)

  def ListHuntApprovals(
      self,
      args: api_user_pb2.ApiListHuntApprovalsArgs,
      context: Optional[api_call_context.ApiCallContext] = None,
  ):
    # Everybody can list their own user hunt approvals.

    return api_user.ApiListHuntApprovalsHandler(self.approval_checker)

  def CreateCronJobApproval(
      self,
      args: api_user_pb2.ApiCreateCronJobApprovalArgs,
      context: Optional[api_call_context.ApiCallContext] = None,
  ):
    # Everybody can request a cron job approval.

    return api_user.ApiCreateCronJobApprovalHandler(self.approval_checker)

  def GetCronJobApproval(
      self,
      args: api_user_pb2.ApiGetCronJobApprovalArgs,
      context: Optional[api_call_context.ApiCallContext] = None,
  ):
    # Everybody can have access to everybody's crons approvals, provided
    # they know: a cron job id, a username of the requester and an approval id.

    return api_user.ApiGetCronJobApprovalHandler(self.approval_checker)

  def GrantCronJobApproval(
      self,
      args: api_user_pb2.ApiGrantCronJobApprovalArgs,
      context: Optional[api_call_context.ApiCallContext] = None,
  ):
    # Everybody can have access to everybody's crons approvals, provided
    # they know: a cron job id, a username of the requester and an approval id.
    #
    # NOTE: Granting an approval doesn't necessarily mean that corresponding
    # approval request becomes fulfilled right away. Calling this method
    # adds the caller to the approval's approvers list. Then it depends
    # on a particular approval if this list is sufficient or not.
    # Typical case: user can grant their own approval, but this won't make
    # the approval valid.

    return api_user.ApiGrantCronJobApprovalHandler(self.approval_checker)

  def ListCronJobApprovals(
      self,
      args: api_user_pb2.ApiListCronJobApprovalsArgs,
      context: Optional[api_call_context.ApiCallContext] = None,
  ):
    # Everybody can list their own user cron approvals.

    return api_user.ApiListCronJobApprovalsHandler(self.approval_checker)

  def ListApproverSuggestions(
      self,
      args: api_user_pb2.ApiListApproverSuggestionsArgs,
      context: Optional[api_call_context.ApiCallContext] = None,
  ):
    # Everybody can list suggestions for approver usernames.

    return self.delegate.ListApproverSuggestions(args, context=context)

  # User settings methods.
  # =====================
  #
  def GetPendingUserNotificationsCount(
      self,
      args: None,
      context: Optional[api_call_context.ApiCallContext] = None,
  ):
    # Everybody can get their own pending notifications count.

    return self.delegate.GetPendingUserNotificationsCount(args, context=context)

  def ListPendingUserNotifications(
      self,
      args: api_user_pb2.ApiListPendingUserNotificationsArgs,
      context: Optional[api_call_context.ApiCallContext] = None,
  ):
    # Everybody can get their own pending notifications count.

    return self.delegate.ListPendingUserNotifications(args, context=context)

  def DeletePendingUserNotification(
      self,
      args: api_user_pb2.ApiDeletePendingUserNotificationArgs,
      context: Optional[api_call_context.ApiCallContext] = None,
  ):
    # Everybody can get their own pending notifications count.

    return self.delegate.DeletePendingUserNotification(args, context=context)

  def ListAndResetUserNotifications(
      self,
      args: api_user_pb2.ApiListAndResetUserNotificationsArgs,
      context: Optional[api_call_context.ApiCallContext] = None,
  ):
    # Everybody can get their own user notifications.

    return self.delegate.ListAndResetUserNotifications(args, context=context)

  def GetGrrUser(
      self,
      args: None,
      context: Optional[api_call_context.ApiCallContext] = None,
  ):
    # Everybody can get their own user settings.

    is_admin = False
    try:
      # Without access to restricted flows, one can not launch Python hacks and
      # binaries. Hence, we don't display the "Manage binaries" page.
      self.admin_access_checker.CheckIfHasAdminAccess(context.username)
      is_admin = True
    except access_control.UnauthorizedAccess:
      pass

    return api_user.ApiGetOwnGrrUserHandler(is_admin=is_admin)

  def UpdateGrrUser(
      self,
      args: api_user_pb2.ApiGrrUser,
      context: Optional[api_call_context.ApiCallContext] = None,
  ):
    # Everybody can update their own user settings.

    return self.delegate.UpdateGrrUser(args, context=context)

  # Config methods.
  # ==============
  #
  def GetConfig(self, args, context=None):
    # Everybody can read the whole config.

    return self.delegate.GetConfig(args, context=context)

  def GetConfigOption(
      self,
      args: api_config_pb2.ApiGetConfigOptionArgs,
      context: Optional[api_call_context.ApiCallContext] = None,
  ):
    # Everybody can read selected config options.

    return self.delegate.GetConfigOption(args, context=context)

  def ListGrrBinaries(
      self,
      args: api_config_pb2.ApiListGrrBinariesArgs,
      context: Optional[api_call_context.ApiCallContext] = None,
  ):
    self.admin_access_checker.CheckIfHasAdminAccess(context.username)

    return self.delegate.ListGrrBinaries(args, context=context)

  def GetGrrBinary(
      self,
      args: api_config_pb2.ApiGetGrrBinaryArgs,
      context: Optional[api_call_context.ApiCallContext] = None,
  ):
    self.admin_access_checker.CheckIfHasAdminAccess(context.username)

    return self.delegate.GetGrrBinary(args, context=context)

  def GetGrrBinaryBlob(
      self,
      args: api_config_pb2.ApiGetGrrBinaryBlobArgs,
      context: Optional[api_call_context.ApiCallContext] = None,
  ):
    self.admin_access_checker.CheckIfHasAdminAccess(context.username)

    return self.delegate.GetGrrBinaryBlob(args, context=context)

  def GetUiConfig(self, args, context=None):
    # Everybody can read the ui config.
    return self.delegate.GetUiConfig(args, context=context)

  # Reflection methods.
  # ==================
  #
  def ListKbFields(self, args, context=None):
    # Everybody can list knowledge base fields.

    return self.delegate.ListKbFields(args, context=context)

  def ListFlowDescriptors(self, args, context=None):
    # Everybody can list flow descritors.

    return api_flow.ApiListFlowDescriptorsHandler(
        self.admin_access_checker.CheckIfCanStartFlow
    )

  def ListOutputPluginDescriptors(self, args, context=None):
    # Everybody can list output plugin descriptors.

    return self.delegate.ListOutputPluginDescriptors(args, context=context)

  def ListApiMethods(self, args, context=None):
    # Everybody can get the docs.

    return self.delegate.ListApiMethods(args, context=context)

  def GetGrrVersion(
      self,
      args: None,
      context: Optional[api_call_context.ApiCallContext] = None,
  ) -> api_metadata.ApiGetGrrVersionHandler:
    # Everybody can get version of the GRR server.
    return self.delegate.GetGrrVersion(args, context=context)

  def GetOpenApiDescription(
      self,
      args: None,
      context: Optional[api_call_context.ApiCallContext] = None,
  ) -> api_metadata.ApiGetOpenApiDescriptionHandler:
    """Returns a description of the API following the OpenAPI specification."""
    # Everybody can get the OpenAPI description.
    return self.delegate.GetOpenApiDescription(args, context=context)

  # pytype: enable=attribute-error
