#!/usr/bin/env python
"""Implementation of a router class that has approvals-based ACL checks."""



from grr.gui import api_call_router
from grr.gui import api_call_router_without_checks

from grr.lib import access_control
from grr.lib import rdfvalue

from grr.lib.aff4_objects import cronjobs
from grr.lib.aff4_objects import user_managers


class ApiCallRouterWithApprovalChecksWithoutRobotAccess(
    api_call_router.ApiCallRouter):
  """Router that uses approvals-based ACL checks."""

  full_access_control_manager = None

  @staticmethod
  def ClearCache():
    cls = ApiCallRouterWithApprovalChecksWithoutRobotAccess
    cls.full_access_control_manager = None

  def _GetFullAccessControlManager(self):
    cls = ApiCallRouterWithApprovalChecksWithoutRobotAccess
    if cls.full_access_control_manager is None:
      cls.full_access_control_manager = user_managers.FullAccessControlManager()
    return cls.full_access_control_manager

  def CheckClientAccess(self, client_id, token=None):
    self.legacy_manager.CheckClientAccess(token.RealUID(), client_id)

  def CheckHuntAccess(self, hunt_id, token=None):
    hunt_urn = rdfvalue.RDFURN("aff4:/hunts").Add(hunt_id)
    self.legacy_manager.CheckHuntAccess(token.RealUID(), hunt_urn)

  def CheckCronJobAccess(self, cron_job_id, token=None):
    cron_job_urn = cronjobs.CRON_MANAGER.CRON_JOBS_PATH.Add(cron_job_id)
    self.legacy_manager.CheckCronJobAccess(token.RealUID(), cron_job_urn)

  def CheckIfCanStartClientFlow(self, flow_name, token=None):
    self.legacy_manager.CheckIfCanStartFlow(token.RealUID(),
                                            flow_name,
                                            with_client_id=True)

  def CheckIfCanStartGlobalFlow(self, flow_name, token=None):
    self.legacy_manager.CheckIfCanStartFlow(token.RealUID(),
                                            flow_name,
                                            with_client_id=False)

  def __init__(self, legacy_manager=None, delegate=None):
    super(ApiCallRouterWithApprovalChecksWithoutRobotAccess, self).__init__()

    if not legacy_manager:
      legacy_manager = self._GetFullAccessControlManager()
    self.legacy_manager = legacy_manager

    if not delegate:
      delegate = api_call_router_without_checks.ApiCallRouterWithoutChecks()
    self.delegate = delegate

  # Artifacts methods.
  # =================
  #
  def ListArtifacts(self, args, token=None):
    # Everybody is allowed to list artifacts.

    return self.delegate.ListArtifacts(args, token=token)

  def UploadArtifact(self, args, token=None):
    # Everybody is allowed to upload artifacts.

    return self.delegate.UploadArtifact(args, token=token)

  def DeleteArtifacts(self, args, token=None):
    # Everybody is allowed to delete artifacts.

    return self.delegate.DeleteArtifacts(args, token=token)

  # Clients methods.
  # ===============
  #
  def SearchClients(self, args, token=None):
    # Everybody is allowed to search clients.

    return self.delegate.SearchClients(args, token=token)

  def GetClient(self, args, token=None):
    # Everybody is allowed to get information about a particular client.

    return self.delegate.GetClient(args, token=token)

  def GetClientVersionTimes(self, args, token=None):
    # Everybody is allowed to get the versions of a particular client.

    return self.delegate.GetClientVersionTimes(args, token=token)

  def InterrogateClient(self, args, token=None):
    self.CheckClientAccess(args.client_id, token=token)

    return self.delegate.InterrogateClient(args, token=token)

  def GetInterrogateOperationState(self, args, token=None):
    # No ACL checks are required here, since the user can only check
    # operations started by him- or herself.

    return self.delegate.GetInterrogateOperationState(args, token=token)

  def GetLastClientIPAddress(self, args, token=None):
    # Everybody is allowed to get the last ip address of a particular client.

    return self.delegate.GetLastClientIPAddress(args, token=token)

  # Virtual file system methods.
  # ============================
  #
  def ListFiles(self, args, token=None):
    self.CheckClientAccess(args.client_id, token=token)

    return self.delegate.ListFiles(args, token=token)

  def GetFileDetails(self, args, token=None):
    self.CheckClientAccess(args.client_id, token=token)

    return self.delegate.GetFileDetails(args, token=token)

  def GetFileText(self, args, token=None):
    self.CheckClientAccess(args.client_id, token=token)

    return self.delegate.GetFileText(args, token=token)

  def GetFileBlob(self, args, token=None):
    self.CheckClientAccess(args.client_id, token=token)

    return self.delegate.GetFileBlob(args, token=token)

  def GetFileVersionTimes(self, args, token=None):
    self.CheckClientAccess(args.client_id, token=token)

    return self.delegate.GetFileVersionTimes(args, token=token)

  def GetFileDownloadCommand(self, args, token=None):
    self.CheckClientAccess(args.client_id, token=token)

    return self.delegate.GetFileDownloadCommand(args, token=token)

  def CreateVfsRefreshOperation(self, args, token=None):
    self.CheckClientAccess(args.client_id, token=token)

    return self.delegate.CreateVfsRefreshOperation(args, token=token)

  def GetVfsRefreshOperationState(self, args, token=None):
    # No ACL checks are required here, since the user can only check
    # operations started by him- or herself.

    return self.delegate.GetVfsRefreshOperationState(args, token=token)

  def GetVfsTimeline(self, args, token=None):
    self.CheckClientAccess(args.client_id, token=token)

    return self.delegate.GetVfsTimeline(args, token=token)

  def GetVfsTimelineAsCsv(self, args, token=None):
    self.CheckClientAccess(args.client_id, token=token)

    return self.delegate.GetVfsTimelineAsCsv(args, token=token)

  def UpdateVfsFileContent(self, args, token=None):
    self.CheckClientAccess(args.client_id, token=token)

    return self.delegate.UpdateVfsFileContent(args, token=token)

  def GetVfsFileContentUpdateState(self, args, token=None):
    # No ACL checks are required here, since the user can only check
    # operations started by him- or herself.

    return self.delegate.GetVfsFileContentUpdateState(args, token=token)

  # Clients labels methods.
  # ======================
  #
  def ListClientsLabels(self, args, token=None):
    # Everybody is allowed to get a list of all labels used on the system.

    return self.delegate.ListClientsLabels(args, token=token)

  def AddClientsLabels(self, args, token=None):
    # Everybody is allowed to add labels. Labels owner will be attributed to
    # the current user.

    return self.delegate.AddClientsLabels(args, token=token)

  def RemoveClientsLabels(self, args, token=None):
    # Everybody is allowed to remove labels. ApiRemoveClientsLabelsHandler is
    # written in such a way, so that it will only delete user's own labels.

    return self.delegate.RemoveClientsLabels(args, token=token)

  # Clients flows methods.
  # =====================
  #
  def ListFlows(self, args, token=None):
    self.CheckClientAccess(args.client_id, token=token)

    return self.delegate.ListFlows(args, token=token)

  def GetFlow(self, args, token=None):
    self.CheckClientAccess(args.client_id, token=token)

    return self.delegate.GetFlow(args, token=token)

  def CreateFlow(self, args, token=None):
    self.CheckClientAccess(args.client_id, token=token)
    self.CheckIfCanStartClientFlow(args.flow.name or
                                   args.flow.runner_args.flow_name,
                                   token=token)

    return self.delegate.CreateFlow(args, token=token)

  def CancelFlow(self, args, token=None):
    self.CheckClientAccess(args.client_id, token=token)

    return self.delegate.CancelFlow(args, token=token)

  def ListFlowResults(self, args, token=None):
    self.CheckClientAccess(args.client_id, token=token)

    return self.delegate.ListFlowResults(args, token=token)

  def GetFlowResultsExportCommand(self, args, token=None):
    self.CheckClientAccess(args.client_id, token=token)

    return self.delegate.GetFlowResultsExportCommand(args, token=token)

  def GetFlowFilesArchive(self, args, token=None):
    self.CheckClientAccess(args.client_id, token=token)

    return self.delegate.GetFlowFilesArchive(args, token=token)

  def ListFlowOutputPlugins(self, args, token=None):
    self.CheckClientAccess(args.client_id, token=token)

    return self.delegate.ListFlowOutputPlugins(args, token=token)

  def ListFlowOutputPluginLogs(self, args, token=None):
    self.CheckClientAccess(args.client_id, token=token)

    return self.delegate.ListFlowOutputPluginLogs(args, token=token)

  def ListFlowOutputPluginErrors(self, args, token=None):
    self.CheckClientAccess(args.client_id, token=token)

    return self.delegate.ListFlowOutputPluginErrors(args, token=token)

  def ListFlowLogs(self, args, token=None):
    self.CheckClientAccess(args.client_id, token=token)

    return self.delegate.ListFlowLogs(args, token=token)

  # Global flows methods.
  # ====================
  #
  def CreateGlobalFlow(self, args, token=None):
    self.CheckIfCanStartGlobalFlow(args.flow.name or
                                   args.flow.runner_args.flow_name,
                                   token=token)

    return self.delegate.CreateGlobalFlow(args, token=token)

  # Cron jobs methods.
  # =================
  #
  def ListCronJobs(self, args, token=None):
    # Everybody can list cron jobs.

    return self.delegate.ListCronJobs(args, token=token)

  def CreateCronJob(self, args, token=None):
    # Everybody can create a cron job.

    return self.delegate.CreateCronJob(args, token=token)

  def DeleteCronJob(self, args, token=None):
    self.CheckCronJobAccess(args.cron_job_id, token=token)

    return self.delegate.DeleteCronJob(args, token=token)

  # Hunts methods.
  # =============
  #
  def ListHunts(self, args, token=None):
    # Everybody can list hunts.

    return self.delegate.ListHunts(args, token=token)

  def GetHunt(self, args, token=None):
    # Everybody can get hunt's information.

    return self.delegate.GetHunt(args, token=token)

  def ListHuntErrors(self, args, token=None):
    # Everybody can get hunt errors list.

    return self.delegate.ListHuntErrors(args, token=token)

  def ListHuntLogs(self, args, token=None):
    # Everybody can look into hunt's logs.

    return self.delegate.ListHuntLogs(args, token=token)

  def ListHuntResults(self, args, token=None):
    # Everybody can look into hunt's results.

    return self.delegate.ListHuntResults(args, token=token)

  def GetHuntResultsExportCommand(self, args, token=None):
    # Everybody can get hunt's export command.

    return self.delegate.GetHuntResultsExportCommand(args, token=token)

  def ListHuntOutputPlugins(self, args, token=None):
    # Everybody can list hunt output plugins.

    return self.delegate.ListHuntOutputPlugins(args, token=token)

  def ListHuntOutputPluginLogs(self, args, token=None):
    # Everybody can list hunt output plugins logs.

    return self.delegate.ListHuntOutputPluginLogs(args, token=token)

  def ListHuntOutputPluginErrors(self, args, token=None):
    # Everybody can list hunt output plugin errors.

    return self.delegate.ListHuntOutputPluginErrors(args, token=token)

  def ListHuntCrashes(self, args, token=None):
    # Everybody can list hunt's crashes.

    return self.delegate.ListHuntCrashes(args, token=token)

  def GetHuntClientCompletionStats(self, args, token=None):
    # Everybody can get hunt's client completion stats.

    return self.delegate.GetHuntClientCompletionStats(args, token=token)

  def GetHuntStats(self, args, token=None):
    # Everybody can get hunt's stats.

    return self.delegate.GetHuntStats(args, token=token)

  def ListHuntClients(self, args, token=None):
    # Everybody can get hunt's clients.

    return self.delegate.ListHuntClients(args, token=token)

  def GetHuntContext(self, args, token=None):
    # Everybody can get hunt's context.

    return self.delegate.GetHuntContext(args, token=token)

  def CreateHunt(self, args, token=None):
    # Everybody can create a hunt.

    return self.delegate.CreateHunt(args, token=token)

  def GetHuntFilesArchive(self, args, token=None):
    # TODO(user): introduce a special type for hunt ids and use
    # to check the correctness of args.hunt_id. Currently args.hunt_id accepts
    # any URN, whereas we want it to accept only hunt ids, i.e. H:123456.
    self.CheckHuntAccess(rdfvalue.RDFURN(args.hunt_id).Basename(), token=token)

    return self.delegate.GetHuntFilesArchive(args, token=token)

  def GetHuntFile(self, args, token=None):
    # TODO(user): introduce a special type for hunt ids and use
    # to check the correctness of args.hunt_id. Currently args.hunt_id accepts
    # any URN, whereas we want it to accept only hunt ids, i.e. H:123456.
    self.CheckHuntAccess(rdfvalue.RDFURN(args.hunt_id).Basename(), token=token)

    return self.delegate.GetHuntFile(args, token=token)

  # Stats metrics methods.
  # =====================
  #
  def ListStatsStoreMetricsMetadata(self, args, token=None):
    # Everybody can list stats store metrics metadata.

    return self.delegate.ListStatsStoreMetricsMetadata(args, token=token)

  def GetStatsStoreMetric(self, args, token=None):
    # Everybody can get a metric.

    return self.delegate.GetStatsStoreMetric(args, token=token)

  # Approvals methods.
  # =================
  #
  def CreateUserClientApproval(self, args, token=None):
    # Everybody can create a user client approval.

    return self.delegate.CreateUserClientApproval(args, token=token)

  def GetUserClientApproval(self, args, token=None):
    # Everybody can get their own user client approvals.

    return self.delegate.GetUserClientApproval(args, token=token)

  def ListUserClientApprovals(self, args, token=None):
    # Everybody can list their own user client approvals.

    return self.delegate.ListUserClientApprovals(args, token=token)

  def ListUserHuntApprovals(self, args, token=None):
    # Everybody can list their own user hunt approvals.

    return self.delegate.ListUserHuntApprovals(args, token=token)

  def ListUserCronApprovals(self, args, token=None):
    # Everybody can list their own user cron approvals.

    return self.delegate.ListUserCronApprovals(args, token=token)

  # User settings methods.
  # =====================
  #
  def GetPendingUserNotificationsCount(self, args, token=None):
    # Everybody can get their own pending notifications count.

    return self.delegate.GetPendingUserNotificationsCount(args, token=token)

  def ListPendingUserNotifications(self, args, token=None):
    # Everybody can get their own pending notifications count.

    return self.delegate.ListPendingUserNotifications(args, token=token)

  def DeletePendingUserNotification(self, args, token=None):
    # Everybody can get their own pending notifications count.

    return self.delegate.DeletePendingUserNotification(args, token=token)

  def ListAndResetUserNotifications(self, args, token=None):
    # Everybody can get their own user notifications.

    return self.delegate.ListAndResetUserNotifications(args, token=token)

  def GetGrrUser(self, args, token=None):
    # Everybody can get their own user settings.

    return self.delegate.GetGrrUser(args, token=token)

  def UpdateGrrUser(self, args, token=None):
    # Everybody can update their own user settings.

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

  # Robot methods (methods that provide limited access to the system and
  # are supposed to be triggered by the scripts).
  # ====================================================================
  #
  def StartRobotGetFilesOperation(self, args, token=None):
    # Robot methods are not accessible for normal users.

    raise access_control.UnauthorizedAccess("Robot methods can't be used "
                                            "by normal users.")

  def GetRobotGetFilesOperationState(self, args, token=None):
    # Robot methods are not accessible for normal users.

    raise access_control.UnauthorizedAccess("Robot methods can't be used "
                                            "by normal users.")


class ApiCallRouterWithApprovalChecksWithRobotAccess(
    ApiCallRouterWithApprovalChecksWithoutRobotAccess):

  # Robot methods (methods that provide limited access to the system and
  # are supposed to be triggered by the scripts).
  # ====================================================================
  #
  def StartRobotGetFilesOperation(self, args, token=None):
    return self.delegate.StartRobotGetFilesOperation(args, token=token)

  def GetRobotGetFilesOperationState(self, args, token=None):
    return self.delegate.GetRobotGetFilesOperationState(args, token=token)
