#!/usr/bin/env python
"""Router giving access only to clients with certain labels."""

from typing import Optional

from grr_response_proto import api_call_router_pb2
from grr_response_proto.api import client_pb2 as api_client_pb2
from grr_response_proto.api import config_pb2 as api_config_pb2
from grr_response_proto.api import flow_pb2 as api_flow_pb2
from grr_response_proto.api import user_pb2 as api_user_pb2
from grr_response_proto.api import vfs_pb2 as api_vfs_pb2
from grr_response_server import access_control
from grr_response_server import data_store
from grr_response_server.gui import access_controller
from grr_response_server.gui import api_call_context
from grr_response_server.gui import api_call_router
from grr_response_server.gui import api_call_router_without_checks
from grr_response_server.gui.api_plugins import client as api_client
from grr_response_server.gui.api_plugins import metadata as api_metadata
from grr_response_server.gui.api_plugins import user as api_user


def CheckClientLabels(client_id, allow_labels=None, allow_labels_owners=None):
  """Checks a given client against labels/owners allowlists."""
  allow_labels = allow_labels or []
  allow_labels_owners = allow_labels_owners or []

  labels = data_store.REL_DB.ReadClientLabels(str(client_id))

  for label in labels:
    if label.name in allow_labels and label.owner in allow_labels_owners:
      return

  raise access_control.UnauthorizedAccess(
      "Client %s doesn't have necessary labels." % client_id
  )


class ApiLabelsRestrictedCallRouter(api_call_router.ApiCallRouterStub):
  """Router that restricts access only to clients with certain labels."""

  proto_params_type = api_call_router_pb2.ApiLabelsRestrictedCallRouterParams

  def __init__(
      self,
      params: Optional[
          api_call_router_pb2.ApiLabelsRestrictedCallRouterParams
      ] = None,
      approval_checker: Optional[access_controller.ApprovalChecker] = None,
      delegate: Optional[api_call_router.ApiCallRouter] = None,
  ):
    super().__init__(params=params)

    if not params:
      params = api_call_router_pb2.ApiLabelsRestrictedCallRouterParams()
    self.params = params

    self.allow_labels = set(params.allow_labels)
    # "GRR" is a system label. Labels returned by the client during the
    # interrogate have owner="GRR".
    self.allow_labels_owners = set(params.allow_labels_owners or ["GRR"])

    self.admin_access_checker = access_controller.AdminAccessChecker()
    self.mitigation_flows_access_checker = (
        access_controller.MitigationFlowsAccessChecker()
    )

    if not approval_checker:
      approval_checker = access_controller.ApprovalChecker(
          self.admin_access_checker
      )
    self.approval_checker = approval_checker

    if not delegate:
      delegate = api_call_router_without_checks.ApiCallRouterWithoutChecks()
    self.delegate = delegate

  def CheckClientLabels(self, client_id):
    CheckClientLabels(
        client_id,
        allow_labels=self.allow_labels,
        allow_labels_owners=self.allow_labels_owners,
    )

  def CheckVfsAccessAllowed(self):
    if not self.params.allow_vfs_access:
      raise access_control.UnauthorizedAccess(
          "User is not allowed to access virtual file system."
      )

  def CheckFlowsAllowed(self):
    if not self.params.allow_flows_access:
      raise access_control.UnauthorizedAccess(
          "User is not allowed to work with flows."
      )

  def CheckIfCanStartFlow(self, flow_name, context=None):
    self.admin_access_checker.CheckIfCanStartFlow(context.username, flow_name)

  def CheckClientApproval(self, client_id, context=None):
    self.CheckClientLabels(client_id)
    self.approval_checker.CheckClientAccess(context, str(client_id))

  # Clients methods.
  # ===============
  #
  def SearchClients(
      self,
      args: api_client_pb2.ApiSearchClientsArgs,
      context: Optional[api_call_context.ApiCallContext] = None,
  ) -> api_client.ApiLabelsRestrictedSearchClientsHandler:
    return api_client.ApiLabelsRestrictedSearchClientsHandler(
        allow_labels=self.allow_labels,
        allow_labels_owners=self.allow_labels_owners,
    )

  def GetClient(
      self,
      args: api_client_pb2.ApiGetClientArgs,
      context: Optional[api_call_context.ApiCallContext] = None,
  ):
    self.CheckClientLabels(args.client_id)

    return self.delegate.GetClient(args, context=context)

  def GetClientVersions(
      self,
      args: api_client_pb2.ApiGetClientVersionsArgs,
      context: Optional[api_call_context.ApiCallContext] = None,
  ):
    self.CheckClientLabels(args.client_id)

    return self.delegate.GetClientVersions(args, context=context)

  def GetClientVersionTimes(
      self,
      args: api_client_pb2.ApiGetClientVersionTimesArgs,
      context: Optional[api_call_context.ApiCallContext] = None,
  ):
    self.CheckClientLabels(args.client_id)

    return self.delegate.GetClientVersionTimes(args, context=context)

  def GetClientSnapshots(
      self,
      args: api_client_pb2.ApiGetClientSnapshotsArgs,
      context: Optional[api_call_context.ApiCallContext] = None,
  ):
    self.CheckClientLabels(args.client_id)

    return self.delegate.GetClientSnapshots(args, context=context)

  def GetClientStartupInfos(
      self,
      args: api_client_pb2.ApiGetClientStartupInfosArgs,
      context: Optional[api_call_context.ApiCallContext] = None,
  ):
    self.CheckClientLabels(args.client_id)

    return self.delegate.GetClientStartupInfos(args, context=context)

  # Virtual file system methods.
  # ============================
  #
  def ListFiles(
      self,
      args: api_vfs_pb2.ApiListFilesArgs,
      context: Optional[api_call_context.ApiCallContext] = None,
  ):
    self.CheckVfsAccessAllowed()
    self.CheckClientApproval(args.client_id, context=context)

    return self.delegate.ListFiles(args, context=context)

  def BrowseFilesystem(
      self,
      args: api_vfs_pb2.ApiBrowseFilesystemArgs,
      context: Optional[api_call_context.ApiCallContext] = None,
  ):
    self.CheckVfsAccessAllowed()
    self.CheckClientApproval(args.client_id, context=context)

    return self.delegate.BrowseFilesystem(args, context=context)

  def GetFileDetails(
      self,
      args: api_vfs_pb2.ApiGetFileDetailsArgs,
      context: Optional[api_call_context.ApiCallContext] = None,
  ):
    self.CheckVfsAccessAllowed()
    self.CheckClientApproval(args.client_id, context=context)

    return self.delegate.GetFileDetails(args, context=context)

  def GetFileText(
      self,
      args: api_vfs_pb2.ApiGetFileTextArgs,
      context: Optional[api_call_context.ApiCallContext] = None,
  ):
    self.CheckVfsAccessAllowed()
    self.CheckClientApproval(args.client_id, context=context)

    return self.delegate.GetFileText(args, context=context)

  def GetFileBlob(
      self,
      args: api_vfs_pb2.ApiGetFileBlobArgs,
      context: Optional[api_call_context.ApiCallContext] = None,
  ):
    self.CheckVfsAccessAllowed()
    self.CheckClientApproval(args.client_id, context=context)

    return self.delegate.GetFileBlob(args, context=context)

  def GetFileVersionTimes(
      self,
      args: api_vfs_pb2.ApiGetFileVersionTimesArgs,
      context: Optional[api_call_context.ApiCallContext] = None,
  ):
    self.CheckVfsAccessAllowed()
    self.CheckClientApproval(args.client_id, context=context)

    return self.delegate.GetFileVersionTimes(args, context=context)

  def GetFileDownloadCommand(
      self,
      args: api_vfs_pb2.ApiGetFileDownloadCommandArgs,
      context: Optional[api_call_context.ApiCallContext] = None,
  ):
    self.CheckVfsAccessAllowed()
    self.CheckClientApproval(args.client_id, context=context)

    return self.delegate.GetFileDownloadCommand(args, context=context)

  def CreateVfsRefreshOperation(
      self,
      args: api_vfs_pb2.ApiCreateVfsRefreshOperationArgs,
      context: Optional[api_call_context.ApiCallContext] = None,
  ):
    self.CheckVfsAccessAllowed()
    self.CheckClientApproval(args.client_id, context=context)

    return self.delegate.CreateVfsRefreshOperation(args, context=context)

  def GetVfsRefreshOperationState(
      self,
      args: api_vfs_pb2.ApiGetVfsRefreshOperationStateArgs,
      context: Optional[api_call_context.ApiCallContext] = None,
  ):
    self.CheckVfsAccessAllowed()

    # No ACL checks are required at this stage, since the user can only check
    # operations started by themselves.
    return self.delegate.GetVfsRefreshOperationState(args, context=context)

  def GetVfsTimeline(
      self,
      args: api_vfs_pb2.ApiGetVfsTimelineArgs,
      context: Optional[api_call_context.ApiCallContext] = None,
  ):
    self.CheckVfsAccessAllowed()
    self.CheckClientApproval(args.client_id, context=context)

    return self.delegate.GetVfsTimeline(args, context=context)

  def GetVfsTimelineAsCsv(
      self,
      args: api_vfs_pb2.ApiGetVfsTimelineAsCsvArgs,
      context: Optional[api_call_context.ApiCallContext] = None,
  ):
    self.CheckVfsAccessAllowed()
    self.CheckClientApproval(args.client_id, context=context)

    return self.delegate.GetVfsTimelineAsCsv(args, context=context)

  # Clients flows methods.
  # =====================
  #
  def ListFlows(
      self,
      args: api_flow_pb2.ApiListFlowsArgs,
      context: Optional[api_call_context.ApiCallContext] = None,
  ):
    self.CheckFlowsAllowed()
    self.CheckClientApproval(args.client_id, context=context)

    return self.delegate.ListFlows(args, context=context)

  def GetFlow(
      self,
      args: api_flow_pb2.ApiGetFlowArgs,
      context: Optional[api_call_context.ApiCallContext] = None,
  ):
    self.CheckFlowsAllowed()
    self.CheckClientApproval(args.client_id, context=context)

    return self.delegate.GetFlow(args, context=context)

  def CreateFlow(
      self,
      args: api_flow_pb2.ApiCreateFlowArgs,
      context: Optional[api_call_context.ApiCallContext] = None,
  ):
    self.CheckFlowsAllowed()
    self.CheckClientApproval(args.client_id, context=context)
    self.CheckIfCanStartFlow(
        args.flow.name or args.flow.runner_args.flow_name, context=context
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
    self.CheckFlowsAllowed()
    self.CheckClientApproval(args.client_id, context=context)

    return self.delegate.CancelFlow(args, context=context)

  def ListFlowRequests(
      self,
      args: api_flow_pb2.ApiListFlowRequestsArgs,
      context: Optional[api_call_context.ApiCallContext] = None,
  ):
    self.CheckFlowsAllowed()
    self.CheckClientApproval(args.client_id, context=context)

    return self.delegate.ListFlowRequests(args, context=context)

  def ListFlowResults(
      self,
      args: api_flow_pb2.ApiListFlowResultsArgs,
      context: Optional[api_call_context.ApiCallContext] = None,
  ):
    self.CheckFlowsAllowed()
    self.CheckClientApproval(args.client_id, context=context)

    return self.delegate.ListFlowResults(args, context=context)

  def GetFlowResultsExportCommand(
      self,
      args: api_flow_pb2.ApiGetFlowResultsExportCommandArgs,
      context: Optional[api_call_context.ApiCallContext] = None,
  ):
    self.CheckFlowsAllowed()
    self.CheckClientApproval(args.client_id, context=context)

    return self.delegate.GetFlowResultsExportCommand(args, context=context)

  def GetFlowFilesArchive(
      self,
      args: api_flow_pb2.ApiGetFlowFilesArchiveArgs,
      context: Optional[api_call_context.ApiCallContext] = None,
  ):
    self.CheckFlowsAllowed()
    self.CheckClientApproval(args.client_id, context=context)

    return self.delegate.GetFlowFilesArchive(args, context=context)

  def ListFlowOutputPlugins(
      self,
      args: api_flow_pb2.ApiListFlowOutputPluginsArgs,
      context: Optional[api_call_context.ApiCallContext] = None,
  ):
    self.CheckFlowsAllowed()
    self.CheckClientApproval(args.client_id, context=context)

    return self.delegate.ListFlowOutputPlugins(args, context=context)

  def ListFlowOutputPluginLogs(
      self,
      args: api_flow_pb2.ApiListFlowOutputPluginLogsArgs,
      context: Optional[api_call_context.ApiCallContext] = None,
  ):
    self.CheckFlowsAllowed()
    self.CheckClientApproval(args.client_id, context=context)

    return self.delegate.ListFlowOutputPluginLogs(args, context=context)

  def ListFlowOutputPluginErrors(
      self,
      args: api_flow_pb2.ApiListFlowOutputPluginErrorsArgs,
      context: Optional[api_call_context.ApiCallContext] = None,
  ):
    self.CheckFlowsAllowed()
    self.CheckClientApproval(args.client_id, context=context)

    return self.delegate.ListFlowOutputPluginErrors(args, context=context)

  def ListAllFlowOutputPluginLogs(
      self,
      args: api_flow_pb2.ApiListAllFlowOutputPluginLogsArgs,
      context: Optional[api_call_context.ApiCallContext] = None,
  ):
    self.CheckFlowsAllowed()
    self.CheckClientApproval(args.client_id, context=context)

    return self.delegate.ListAllFlowOutputPluginLogs(args, context=context)

  def ListFlowLogs(
      self,
      args: api_flow_pb2.ApiListFlowLogsArgs,
      context: Optional[api_call_context.ApiCallContext] = None,
  ):
    self.CheckFlowsAllowed()
    self.CheckClientApproval(args.client_id, context=context)

    return self.delegate.ListFlowLogs(args, context=context)

  # Approvals methods.
  # =================
  #
  def CreateClientApproval(
      self,
      args: api_user_pb2.ApiCreateClientApprovalArgs,
      context: Optional[api_call_context.ApiCallContext] = None,
  ):
    self.CheckClientLabels(args.client_id)

    return self.delegate.CreateClientApproval(args, context=context)

  def GetClientApproval(
      self,
      args: api_user_pb2.ApiGetClientApprovalArgs,
      context: Optional[api_call_context.ApiCallContext] = None,
  ):
    self.CheckClientLabels(args.client_id)

    return self.delegate.GetClientApproval(args, context=context)

  def ListClientApprovals(
      self,
      args: api_user_pb2.ApiListClientApprovalsArgs,
      context: Optional[api_call_context.ApiCallContext] = None,
  ):
    # Everybody can list their own user client approvals.

    return self.delegate.ListClientApprovals(args, context=context)

  # User settings methods.
  # =====================
  #
  def GetPendingUserNotificationsCount(
      self,
      args: None,
      context: Optional[api_call_context.ApiCallContext] = None,
  ) -> api_user.ApiGetPendingUserNotificationsCountHandler:
    # Everybody can get their own pending notifications count.

    return self.delegate.GetPendingUserNotificationsCount(args, context=context)

  def ListPendingUserNotifications(
      self,
      args: api_user_pb2.ApiListPendingUserNotificationsArgs,
      context: Optional[api_call_context.ApiCallContext] = None,
  ):
    # Everybody can get their own pending notifications.

    return self.delegate.ListPendingUserNotifications(args, context=context)

  def DeletePendingUserNotification(
      self,
      args: api_user_pb2.ApiDeletePendingUserNotificationArgs,
      context: Optional[api_call_context.ApiCallContext] = None,
  ):
    # Everybody can delete their own pending notifications.

    return self.delegate.DeletePendingUserNotification(args, context=context)

  def ListAndResetUserNotifications(
      self,
      args: api_user_pb2.ApiListAndResetUserNotificationsArgs,
      context: Optional[api_call_context.ApiCallContext] = None,
  ):
    # Everybody can get and reset their own user notifications.

    return self.delegate.ListAndResetUserNotifications(args, context=context)

  def GetGrrUser(
      self,
      args: None,
      context: Optional[api_call_context.ApiCallContext] = None,
  ) -> api_user.ApiGetOwnGrrUserHandler:
    # Everybody can get their own user object.

    return api_user.ApiGetOwnGrrUserHandler(is_admin=False)

  def UpdateGrrUser(
      self,
      args: api_user_pb2.ApiGrrUser,
      context: Optional[api_call_context.ApiCallContext] = None,
  ):
    # Everybody can update their own user object.

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

    return self.delegate.ListFlowDescriptors(args, context=context)

  def ListOutputPluginDescriptors(self, args, context=None):
    # Everybody can list output plugin descriptors.

    return self.delegate.ListOutputPluginDescriptors(args, context=context)

  def ListApiMethods(self, args, context=None):
    # Everybody can list available API methods.

    return self.delegate.ListApiMethods(args, context=context)

  def GetOpenApiDescription(
      self,
      args: None,
      context: Optional[api_call_context.ApiCallContext] = None,
  ) -> api_metadata.ApiGetOpenApiDescriptionHandler:
    """Returns a description of the API following the OpenAPI specification."""
    # Everybody can get the OpenAPI description.
    return self.delegate.GetOpenApiDescription(args, context=context)
