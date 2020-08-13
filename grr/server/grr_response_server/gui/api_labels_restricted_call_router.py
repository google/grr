#!/usr/bin/env python
# Lint as: python3
"""Router giving access only to clients with certain labels."""
from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals


from grr_response_core.lib.rdfvalues import structs as rdf_structs

from grr_response_proto import api_call_router_pb2
from grr_response_server import access_control

from grr_response_server import data_store

from grr_response_server.gui import api_call_router
from grr_response_server.gui import api_call_router_with_approval_checks
from grr_response_server.gui import api_call_router_without_checks

from grr_response_server.gui.api_plugins import client as api_client

from grr_response_server.gui.api_plugins import user as api_user


def CheckClientLabels(client_id,
                      allow_labels=None,
                      allow_labels_owners=None,
                      token=None):
  """Checks a given client against labels/owners allowlists."""
  del token  # Unused.

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

  def CheckClientLabels(self, client_id, token=None):
    CheckClientLabels(
        client_id,
        allow_labels=self.allow_labels,
        allow_labels_owners=self.allow_labels_owners,
        token=token)

  def CheckVfsAccessAllowed(self):
    if not self.params.allow_vfs_access:
      raise access_control.UnauthorizedAccess(
          "User is not allowed to access virtual file system.")

  def CheckFlowsAllowed(self):
    if not self.params.allow_flows_access:
      raise access_control.UnauthorizedAccess(
          "User is not allowed to work with flows.")

  def CheckIfCanStartClientFlow(self, flow_name, token=None):
    self.access_checker.CheckIfCanStartClientFlow(token.username, flow_name)

  def CheckClientApproval(self, client_id, token=None):
    self.CheckClientLabels(client_id, token=token)
    self.access_checker.CheckClientAccess(token.username, client_id)

  # Clients methods.
  # ===============
  #
  def SearchClients(self, args, token=None):
    return api_client.ApiLabelsRestrictedSearchClientsHandler(
        allow_labels=self.allow_labels,
        allow_labels_owners=self.allow_labels_owners)

  def GetClient(self, args, token=None):
    self.CheckClientLabels(args.client_id, token=token)

    return self.delegate.GetClient(args, token=token)

  def GetClientVersions(self, args, token=None):
    self.CheckClientLabels(args.client_id, token=token)

    return self.delegate.GetClientVersions(args, token=token)

  def GetClientVersionTimes(self, args, token=None):
    self.CheckClientLabels(args.client_id, token=token)

    return self.delegate.GetClientVersionTimes(args, token=token)

  # Virtual file system methods.
  # ============================
  #
  def ListFiles(self, args, token=None):
    self.CheckVfsAccessAllowed()
    self.CheckClientApproval(args.client_id, token=token)

    return self.delegate.ListFiles(args, token=token)

  def GetFileDetails(self, args, token=None):
    self.CheckVfsAccessAllowed()
    self.CheckClientApproval(args.client_id, token=token)

    return self.delegate.GetFileDetails(args, token=token)

  def GetFileText(self, args, token=None):
    self.CheckVfsAccessAllowed()
    self.CheckClientApproval(args.client_id, token=token)

    return self.delegate.GetFileText(args, token=token)

  def GetFileBlob(self, args, token=None):
    self.CheckVfsAccessAllowed()
    self.CheckClientApproval(args.client_id, token=token)

    return self.delegate.GetFileBlob(args, token=token)

  def GetFileVersionTimes(self, args, token=None):
    self.CheckVfsAccessAllowed()
    self.CheckClientApproval(args.client_id, token=token)

    return self.delegate.GetFileVersionTimes(args, token=token)

  def GetFileDownloadCommand(self, args, token=None):
    self.CheckVfsAccessAllowed()
    self.CheckClientApproval(args.client_id, token=token)

    return self.delegate.GetFileDownloadCommand(args, token=token)

  def CreateVfsRefreshOperation(self, args, token=None):
    self.CheckVfsAccessAllowed()
    self.CheckClientApproval(args.client_id, token=token)

    return self.delegate.CreateVfsRefreshOperation(args, token=token)

  def GetVfsRefreshOperationState(self, args, token=None):
    self.CheckVfsAccessAllowed()

    # No ACL checks are required at this stage, since the user can only check
    # operations started by him- or herself.
    return self.delegate.GetVfsRefreshOperationState(args, token=token)

  def GetVfsTimeline(self, args, token=None):
    self.CheckVfsAccessAllowed()
    self.CheckClientApproval(args.client_id, token=token)

    return self.delegate.GetVfsTimeline(args, token=token)

  def GetVfsTimelineAsCsv(self, args, token=None):
    self.CheckVfsAccessAllowed()
    self.CheckClientApproval(args.client_id, token=token)

    return self.delegate.GetVfsTimelineAsCsv(args, token=token)

  # Clients flows methods.
  # =====================
  #
  def ListFlows(self, args, token=None):
    self.CheckFlowsAllowed()
    self.CheckClientApproval(args.client_id, token=token)

    return self.delegate.ListFlows(args, token=token)

  def GetFlow(self, args, token=None):
    self.CheckFlowsAllowed()
    self.CheckClientApproval(args.client_id, token=token)

    return self.delegate.GetFlow(args, token=token)

  def CreateFlow(self, args, token=None):
    self.CheckFlowsAllowed()
    self.CheckClientApproval(args.client_id, token=token)
    self.CheckIfCanStartClientFlow(
        args.flow.name or args.flow.runner_args.flow_name, token=token)

    return self.delegate.CreateFlow(args, token=token)

  def CancelFlow(self, args, token=None):
    self.CheckFlowsAllowed()
    self.CheckClientApproval(args.client_id, token=token)

    return self.delegate.CancelFlow(args, token=token)

  def ListFlowRequests(self, args, token=None):
    self.CheckFlowsAllowed()
    self.CheckClientApproval(args.client_id, token=token)

    return self.delegate.ListFlowRequests(args, token=token)

  def ListFlowResults(self, args, token=None):
    self.CheckFlowsAllowed()
    self.CheckClientApproval(args.client_id, token=token)

    return self.delegate.ListFlowResults(args, token=token)

  def GetFlowResultsExportCommand(self, args, token=None):
    self.CheckFlowsAllowed()
    self.CheckClientApproval(args.client_id, token=token)

    return self.delegate.GetFlowResultsExportCommand(args, token=token)

  def GetFlowFilesArchive(self, args, token=None):
    self.CheckFlowsAllowed()
    self.CheckClientApproval(args.client_id, token=token)

    return self.delegate.GetFlowFilesArchive(args, token=token)

  def ListFlowOutputPlugins(self, args, token=None):
    self.CheckFlowsAllowed()
    self.CheckClientApproval(args.client_id, token=token)

    return self.delegate.ListFlowOutputPlugins(args, token=token)

  def ListFlowOutputPluginLogs(self, args, token=None):
    self.CheckFlowsAllowed()
    self.CheckClientApproval(args.client_id, token=token)

    return self.delegate.ListFlowOutputPluginLogs(args, token=token)

  def ListFlowOutputPluginErrors(self, args, token=None):
    self.CheckFlowsAllowed()
    self.CheckClientApproval(args.client_id, token=token)

    return self.delegate.ListFlowOutputPluginErrors(args, token=token)

  def ListFlowLogs(self, args, token=None):
    self.CheckFlowsAllowed()
    self.CheckClientApproval(args.client_id, token=token)

    return self.delegate.ListFlowLogs(args, token=token)

  # Approvals methods.
  # =================
  #
  def CreateClientApproval(self, args, token=None):
    self.CheckClientLabels(args.client_id, token=token)

    return self.delegate.CreateClientApproval(args, token=token)

  def GetClientApproval(self, args, token=None):
    self.CheckClientLabels(args.client_id, token=token)

    return self.delegate.GetClientApproval(args, token=token)

  def ListClientApprovals(self, args, token=None):
    # Everybody can list their own user client approvals.

    return self.delegate.ListClientApprovals(args, token=token)

  # User settings methods.
  # =====================
  #
  def GetPendingUserNotificationsCount(self, args, token=None):
    # Everybody can get their own pending notifications count.

    return self.delegate.GetPendingUserNotificationsCount(args, token=token)

  def ListPendingUserNotifications(self, args, token=None):
    # Everybody can get their own pending notifications.

    return self.delegate.ListPendingUserNotifications(args, token=token)

  def DeletePendingUserNotification(self, args, token=None):
    # Everybody can delete their own pending notifications.

    return self.delegate.DeletePendingUserNotification(args, token=token)

  def ListAndResetUserNotifications(self, args, token=None):
    # Everybody can get and reset their own user notifications.

    return self.delegate.ListAndResetUserNotifications(args, token=token)

  def GetGrrUser(self, args, token=None):
    # Everybody can get their own user object.

    interface_traits = api_user.ApiGrrUserInterfaceTraits(
        search_clients_action_enabled=True)
    return api_user.ApiGetOwnGrrUserHandler(interface_traits=interface_traits)

  def UpdateGrrUser(self, args, token=None):
    # Everybody can update their own user object.

    return self.delegate.UpdateGrrUser(args, token=token)

  # Config methods.
  # ==============
  #
  def GetConfig(self, args, token=None):
    # Everybody can read the whole config.

    return self.delegate.GetConfig(args, token=token)

  def GetConfigOption(self, args, token=None):
    # Everybody can read selected config options.

    return self.delegate.GetConfigOption(args, token=token)

  def GetUiConfig(self, args, token=None):
    # Everybody can read the ui config.
    return self.delegate.GetUiConfig(args, token=token)

  # Reflection methods.
  # ==================
  #
  def ListKbFields(self, args, token=None):
    # Everybody can list knowledge base fields.

    return self.delegate.ListKbFields(args, token=token)

  def ListFlowDescriptors(self, args, token=None):
    # Everybody can list flow descritors.

    return self.delegate.ListFlowDescriptors(args, token=token)

  def GetRDFValueDescriptor(self, args, token=None):
    # Everybody can get rdfvalue descriptors.

    return self.delegate.GetRDFValueDescriptor(args, token=token)

  def ListRDFValuesDescriptors(self, args, token=None):
    # Everybody can list rdfvalue descriptors.

    return self.delegate.ListRDFValuesDescriptors(args, token=token)

  def ListOutputPluginDescriptors(self, args, token=None):
    # Everybody can list output plugin descriptors.

    return self.delegate.ListOutputPluginDescriptors(args, token=token)

  def ListKnownEncodings(self, args, token=None):
    # Everybody can list file encodings.

    return self.delegate.ListKnownEncodings(args, token=token)

  def ListApiMethods(self, args, token=None):
    # Everybody can list available API methods.

    return self.delegate.ListApiMethods(args, token=token)
