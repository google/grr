#!/usr/bin/env python
# Lint as: python3
"""Router giving access only to clients with certain labels."""
from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

from typing import Optional

from grr_response_core.lib.rdfvalues import structs as rdf_structs

from grr_response_proto import api_call_router_pb2
from grr_response_server import access_control

from grr_response_server import data_store

from grr_response_server.gui import api_call_context
from grr_response_server.gui import api_call_router
from grr_response_server.gui import api_call_router_with_approval_checks
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
    if (label.name in allow_labels and label.owner in allow_labels_owners):
      return

  raise access_control.UnauthorizedAccess(
      "Client %s doesn't have necessary labels." % client_id)


class ApiLabelsRestrictedCallRouterParams(rdf_structs.RDFProtoStruct):
  protobuf = api_call_router_pb2.ApiLabelsRestrictedCallRouterParams


class ApiLabelsRestrictedCallRouter(api_call_router.ApiCallRouterStub):
  """Router that restricts access only to clients with certain labels."""

  params_type = ApiLabelsRestrictedCallRouterParams

  def __init__(self, params=None, access_checker=None, delegate=None):
    super().__init__(params=params)

    self.params = params = params or self.__class__.params_type()

    self.allow_labels = set(params.allow_labels)
    # "GRR" is a system label. Labels returned by the client during the
    # interrogate have owner="GRR".
    self.allow_labels_owners = set(params.allow_labels_owners or ["GRR"])

    if not access_checker:
      access_checker = api_call_router_with_approval_checks.AccessChecker()
    self.access_checker = access_checker

    if not delegate:
      delegate = api_call_router_without_checks.ApiCallRouterWithoutChecks()
    self.delegate = delegate

  def CheckClientLabels(self, client_id):
    CheckClientLabels(
        client_id,
        allow_labels=self.allow_labels,
        allow_labels_owners=self.allow_labels_owners)

  def CheckVfsAccessAllowed(self):
    if not self.params.allow_vfs_access:
      raise access_control.UnauthorizedAccess(
          "User is not allowed to access virtual file system.")

  def CheckFlowsAllowed(self):
    if not self.params.allow_flows_access:
      raise access_control.UnauthorizedAccess(
          "User is not allowed to work with flows.")

  def CheckIfCanStartClientFlow(self, flow_name, context=None):
    self.access_checker.CheckIfCanStartClientFlow(context.username, flow_name)

  def CheckClientApproval(self, client_id, context=None):
    self.CheckClientLabels(client_id)
    self.access_checker.CheckClientAccess(context, client_id)

  # Clients methods.
  # ===============
  #
  def SearchClients(self, args, context=None):
    return api_client.ApiLabelsRestrictedSearchClientsHandler(
        allow_labels=self.allow_labels,
        allow_labels_owners=self.allow_labels_owners)

  def GetClient(self, args, context=None):
    self.CheckClientLabels(args.client_id)

    return self.delegate.GetClient(args, context=context)

  def GetClientVersions(self, args, context=None):
    self.CheckClientLabels(args.client_id)

    return self.delegate.GetClientVersions(args, context=context)

  def GetClientVersionTimes(self, args, context=None):
    self.CheckClientLabels(args.client_id)

    return self.delegate.GetClientVersionTimes(args, context=context)

  # Virtual file system methods.
  # ============================
  #
  def ListFiles(self, args, context=None):
    self.CheckVfsAccessAllowed()
    self.CheckClientApproval(args.client_id, context=context)

    return self.delegate.ListFiles(args, context=context)

  def GetFileDetails(self, args, context=None):
    self.CheckVfsAccessAllowed()
    self.CheckClientApproval(args.client_id, context=context)

    return self.delegate.GetFileDetails(args, context=context)

  def GetFileText(self, args, context=None):
    self.CheckVfsAccessAllowed()
    self.CheckClientApproval(args.client_id, context=context)

    return self.delegate.GetFileText(args, context=context)

  def GetFileBlob(self, args, context=None):
    self.CheckVfsAccessAllowed()
    self.CheckClientApproval(args.client_id, context=context)

    return self.delegate.GetFileBlob(args, context=context)

  def GetFileVersionTimes(self, args, context=None):
    self.CheckVfsAccessAllowed()
    self.CheckClientApproval(args.client_id, context=context)

    return self.delegate.GetFileVersionTimes(args, context=context)

  def GetFileDownloadCommand(self, args, context=None):
    self.CheckVfsAccessAllowed()
    self.CheckClientApproval(args.client_id, context=context)

    return self.delegate.GetFileDownloadCommand(args, context=context)

  def CreateVfsRefreshOperation(self, args, context=None):
    self.CheckVfsAccessAllowed()
    self.CheckClientApproval(args.client_id, context=context)

    return self.delegate.CreateVfsRefreshOperation(args, context=context)

  def GetVfsRefreshOperationState(self, args, context=None):
    self.CheckVfsAccessAllowed()

    # No ACL checks are required at this stage, since the user can only check
    # operations started by him- or herself.
    return self.delegate.GetVfsRefreshOperationState(args, context=context)

  def GetVfsTimeline(self, args, context=None):
    self.CheckVfsAccessAllowed()
    self.CheckClientApproval(args.client_id, context=context)

    return self.delegate.GetVfsTimeline(args, context=context)

  def GetVfsTimelineAsCsv(self, args, context=None):
    self.CheckVfsAccessAllowed()
    self.CheckClientApproval(args.client_id, context=context)

    return self.delegate.GetVfsTimelineAsCsv(args, context=context)

  # Clients flows methods.
  # =====================
  #
  def ListFlows(self, args, context=None):
    self.CheckFlowsAllowed()
    self.CheckClientApproval(args.client_id, context=context)

    return self.delegate.ListFlows(args, context=context)

  def GetFlow(self, args, context=None):
    self.CheckFlowsAllowed()
    self.CheckClientApproval(args.client_id, context=context)

    return self.delegate.GetFlow(args, context=context)

  def CreateFlow(self, args, context=None):
    self.CheckFlowsAllowed()
    self.CheckClientApproval(args.client_id, context=context)
    self.CheckIfCanStartClientFlow(
        args.flow.name or args.flow.runner_args.flow_name, context=context)

    return self.delegate.CreateFlow(args, context=context)

  def CancelFlow(self, args, context=None):
    self.CheckFlowsAllowed()
    self.CheckClientApproval(args.client_id, context=context)

    return self.delegate.CancelFlow(args, context=context)

  def ListFlowRequests(self, args, context=None):
    self.CheckFlowsAllowed()
    self.CheckClientApproval(args.client_id, context=context)

    return self.delegate.ListFlowRequests(args, context=context)

  def ListFlowResults(self, args, context=None):
    self.CheckFlowsAllowed()
    self.CheckClientApproval(args.client_id, context=context)

    return self.delegate.ListFlowResults(args, context=context)

  def GetFlowResultsExportCommand(self, args, context=None):
    self.CheckFlowsAllowed()
    self.CheckClientApproval(args.client_id, context=context)

    return self.delegate.GetFlowResultsExportCommand(args, context=context)

  def GetFlowFilesArchive(self, args, context=None):
    self.CheckFlowsAllowed()
    self.CheckClientApproval(args.client_id, context=context)

    return self.delegate.GetFlowFilesArchive(args, context=context)

  def ListFlowOutputPlugins(self, args, context=None):
    self.CheckFlowsAllowed()
    self.CheckClientApproval(args.client_id, context=context)

    return self.delegate.ListFlowOutputPlugins(args, context=context)

  def ListFlowOutputPluginLogs(self, args, context=None):
    self.CheckFlowsAllowed()
    self.CheckClientApproval(args.client_id, context=context)

    return self.delegate.ListFlowOutputPluginLogs(args, context=context)

  def ListFlowOutputPluginErrors(self, args, context=None):
    self.CheckFlowsAllowed()
    self.CheckClientApproval(args.client_id, context=context)

    return self.delegate.ListFlowOutputPluginErrors(args, context=context)

  def ListFlowLogs(self, args, context=None):
    self.CheckFlowsAllowed()
    self.CheckClientApproval(args.client_id, context=context)

    return self.delegate.ListFlowLogs(args, context=context)

  # Approvals methods.
  # =================
  #
  def CreateClientApproval(self, args, context=None):
    self.CheckClientLabels(args.client_id)

    return self.delegate.CreateClientApproval(args, context=context)

  def GetClientApproval(self, args, context=None):
    self.CheckClientLabels(args.client_id)

    return self.delegate.GetClientApproval(args, context=context)

  def ListClientApprovals(self, args, context=None):
    # Everybody can list their own user client approvals.

    return self.delegate.ListClientApprovals(args, context=context)

  # User settings methods.
  # =====================
  #
  def GetPendingUserNotificationsCount(self, args, context=None):
    # Everybody can get their own pending notifications count.

    return self.delegate.GetPendingUserNotificationsCount(args, context=context)

  def ListPendingUserNotifications(self, args, context=None):
    # Everybody can get their own pending notifications.

    return self.delegate.ListPendingUserNotifications(args, context=context)

  def DeletePendingUserNotification(self, args, context=None):
    # Everybody can delete their own pending notifications.

    return self.delegate.DeletePendingUserNotification(args, context=context)

  def ListAndResetUserNotifications(self, args, context=None):
    # Everybody can get and reset their own user notifications.

    return self.delegate.ListAndResetUserNotifications(args, context=context)

  def GetGrrUser(self, args, context=None):
    # Everybody can get their own user object.

    interface_traits = api_user.ApiGrrUserInterfaceTraits(
        search_clients_action_enabled=True)
    return api_user.ApiGetOwnGrrUserHandler(interface_traits=interface_traits)

  def UpdateGrrUser(self, args, context=None):
    # Everybody can update their own user object.

    return self.delegate.UpdateGrrUser(args, context=context)

  # Config methods.
  # ==============
  #
  def GetConfig(self, args, context=None):
    # Everybody can read the whole config.

    return self.delegate.GetConfig(args, context=context)

  def GetConfigOption(self, args, context=None):
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

  def GetRDFValueDescriptor(self, args, context=None):
    # Everybody can get rdfvalue descriptors.

    return self.delegate.GetRDFValueDescriptor(args, context=context)

  def ListRDFValuesDescriptors(self, args, context=None):
    # Everybody can list rdfvalue descriptors.

    return self.delegate.ListRDFValuesDescriptors(args, context=context)

  def ListOutputPluginDescriptors(self, args, context=None):
    # Everybody can list output plugin descriptors.

    return self.delegate.ListOutputPluginDescriptors(args, context=context)

  def ListKnownEncodings(self, args, context=None):
    # Everybody can list file encodings.

    return self.delegate.ListKnownEncodings(args, context=context)

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
