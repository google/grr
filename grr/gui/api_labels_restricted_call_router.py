#!/usr/bin/env python
"""Router giving access only to clients with certain labels."""



from grr.gui import api_call_router
from grr.gui import api_call_router_without_checks

from grr.gui.api_plugins import client as api_client
from grr.gui.api_plugins import user as api_user

from grr.lib import access_control

from grr.lib import aff4
from grr.lib import utils

from grr.lib.aff4_objects import aff4_grr
from grr.lib.aff4_objects import user_managers


class ApiLabelsRestrictedCallRouter(api_call_router.ApiCallRouter):
  """Router that restricts access only to clients with certain labels."""

  def __init__(self,
               labels_whitelist=None,
               labels_owners_whitelist=None,
               allow_flows=False,
               allow_vfs_access=False,
               legacy_manager=None,
               delegate=None):
    super(ApiLabelsRestrictedCallRouter, self).__init__()

    self.labels_whitelist = set(labels_whitelist or [])
    # "GRR" is a system label. Labels returned by the client during the
    # interrogate have owner="GRR".
    self.labels_owners_whitelist = set(labels_owners_whitelist or ["GRR"])

    self.allow_flows = allow_flows
    self.allow_vfs_access = allow_vfs_access

    if not legacy_manager:
      legacy_manager = user_managers.FullAccessControlManager()
    self.legacy_manager = legacy_manager

    if not delegate:
      delegate = api_call_router_without_checks.ApiCallRouterWithoutChecks()
    self.delegate = delegate

  def CheckClientLabels(self, client_id, token=None):
    has_label = False
    with aff4.FACTORY.Open(client_id,
                           aff4_type=aff4_grr.VFSGRRClient,
                           token=token) as fd:
      for label in fd.GetLabels():
        if (label.name in self.labels_whitelist and
            label.owner in self.labels_owners_whitelist):
          has_label = True
          break

    if not has_label:
      raise access_control.UnauthorizedAccess(
          "Client %s doesn't have necessary labels." %
          utils.SmartStr(client_id))

  def CheckVfsAccessAllowed(self):
    if not self.allow_vfs_access:
      raise access_control.UnauthorizedAccess(
          "User is not allowed to access virtual file system.")

  def CheckFlowsAllowed(self):
    if not self.allow_flows:
      raise access_control.UnauthorizedAccess(
          "User is not allowed to work with flows.")

  def CheckIfCanStartClientFlow(self, flow_name, token=None):
    self.legacy_manager.CheckIfCanStartFlow(token.RealUID(),
                                            flow_name,
                                            with_client_id=True)

  def CheckClientApproval(self, client_id, token=None):
    self.CheckClientLabels(client_id, token=token)
    self.legacy_manager.CheckClientAccess(token.RealUID(), client_id)

  # Clients methods.
  # ===============
  #
  def SearchClients(self, args, token=None):
    return api_client.ApiLabelsRestrictedSearchClientsHandler(
        labels_whitelist=self.labels_whitelist,
        labels_owners_whitelist=self.labels_owners_whitelist)

  def GetClient(self, args, token=None):
    self.CheckClientLabels(args.client_id, token=token)

    return self.delegate.GetClient(args, token=token)

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
    self.CheckIfCanStartClientFlow(args.flow.name or
                                   args.flow.runner_args.flow_name,
                                   token=token)

    return self.delegate.CreateFlow(args, token=token)

  def CancelFlow(self, args, token=None):
    self.CheckFlowsAllowed()
    self.CheckClientApproval(args.client_id, token=token)

    return self.delegate.CancelFlow(args, token=token)

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
  def CreateUserClientApproval(self, args, token=None):
    self.CheckClientLabels(args.client_id, token=token)

    return self.delegate.CreateUserClientApproval(args, token=token)

  def GetUserClientApproval(self, args, token=None):
    self.CheckClientLabels(args.client_id, token=token)

    return self.delegate.GetUserClientApproval(args, token=token)

  def ListUserClientApprovals(self, args, token=None):
    # Everybody can list their own user client approvals.

    return self.delegate.ListUserClientApprovals(args, token=token)

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
    return api_user.ApiGetGrrUserHandler(interface_traits=interface_traits)

  def UpdateGrrUser(self, args, token=None):
    # Everybody can update their own user object.

    return self.delegate.UpdateGrrUser(args, token=token)

  def ListPendingGlobalNotifications(self, args, token=None):
    # Everybody can get their global pending notifications.

    return self.delegate.ListPendingGlobalNotifications(args, token=token)

  def DeletePendingGlobalNotification(self, args, token=None):
    # Everybody can delete their global pending notifications.

    return self.delegate.DeletePendingGlobalNotification(args, token=token)

  # Config methods.
  # ==============
  #
  def GetConfig(self, args, token=None):
    # Everybody can read the whole config.

    return self.delegate.GetConfig(args, token=token)

  def GetConfigOption(self, args, token=None):
    # Everybody can read selected config options.

    return self.delegate.GetConfigOption(args, token=token)

  # Reflection methods.
  # ==================
  #
  def ListKbFields(self, args, token=None):
    # Everybody can list knowledge base fields.

    return self.delegate.ListKbFields(args, token=token)

  def ListFlowDescriptors(self, args, token=None):
    # Everybody can list flow descritors.

    return self.delegate.ListFlowDescriptors(args, token=token)

  def ListAff4AttributeDescriptors(self, args, token=None):
    # Everybody can list aff4 attribute descriptors.

    return self.delegate.ListAff4AttributeDescriptors(args, token=token)

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

  # Documentation methods.
  # =====================
  #
  def GetDocs(self, args, token=None):
    # Everybody can get the docs.

    return self.delegate.GetDocs(args, token=token)
