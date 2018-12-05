#!/usr/bin/env python
"""Implementation of a router class that has approvals-based ACL checks."""
from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

from grr_response_core.lib import utils
from grr_response_core.lib.util import precondition
from grr_response_core.stats import stats_collector_instance
from grr_response_server import access_control
from grr_response_server import aff4
from grr_response_server import data_store
from grr_response_server import flow
from grr_response_server.aff4_objects import user_managers
from grr_response_server.gui import api_call_handler_base
from grr_response_server.gui import api_call_router
from grr_response_server.gui import api_call_router_without_checks
from grr_response_server.gui import approval_checks
from grr_response_server.gui.api_plugins import flow as api_flow
from grr_response_server.gui.api_plugins import user as api_user
from grr_response_server.hunts import implementation
from grr_response_server.rdfvalues import objects as rdf_objects


class LegacyChecker(object):
  """Legacy access checker implementation."""

  def __init__(self):
    super(LegacyChecker, self).__init__()
    self.legacy_manager = user_managers.FullAccessControlManager()

  def CheckClientAccess(self, username, client_id):
    token = access_control.ACLToken(username=username)
    self.legacy_manager.CheckClientAccess(token, client_id.ToClientURN())

  def CheckHuntAccess(self, username, hunt_id):
    token = access_control.ACLToken(username=username)
    self.legacy_manager.CheckHuntAccess(token, hunt_id.ToURN())

  def CheckCronJobAccess(self, username, cron_job_id):
    token = access_control.ACLToken(username=username)
    self.legacy_manager.CheckCronJobAccess(token, cron_job_id.ToURN())

  def CheckIfCanStartClientFlow(self, username, flow_name):
    token = access_control.ACLToken(username=username)
    self.legacy_manager.CheckIfCanStartFlow(token, flow_name)

  def CheckIfUserIsAdmin(self, username):
    user_managers.CheckUserForLabels(username, ["admin"])


class RelDBChecker(object):
  """Relational DB-based access checker implementation."""

  def __init__(self):
    self.approval_cache_time = 60
    self.acl_cache = utils.AgeBasedCache(
        max_size=10000, max_age=self.approval_cache_time)

  def _CheckAccess(self, username, subject_id, approval_type):
    """Checks access to a given subject by a given user."""
    precondition.AssertType(subject_id, unicode)

    cache_key = (username, subject_id, approval_type)
    try:
      self.acl_cache.Get(cache_key)
      stats_collector_instance.Get().IncrementCounter(
          "approval_searches", fields=["-", "cache"])
      return True
    except KeyError:
      stats_collector_instance.Get().IncrementCounter(
          "approval_searches", fields=["-", "reldb"])

    approvals = data_store.REL_DB.ReadApprovalRequests(
        username, approval_type, subject_id=subject_id, include_expired=False)

    errors = []
    for approval in approvals:
      try:
        approval_checks.CheckApprovalRequest(approval)
        self.acl_cache.Put(cache_key, True)
        return
      except access_control.UnauthorizedAccess as e:
        errors.append(e)

    subject = approval_checks.BuildLegacySubject(subject_id, approval_type)
    if not errors:
      raise access_control.UnauthorizedAccess(
          "No approval found.", subject=subject)
    else:
      raise access_control.UnauthorizedAccess(
          " ".join(utils.SmartStr(e) for e in errors), subject=subject)

  def CheckClientAccess(self, username, client_id):
    """Checks whether a given user can access given client."""
    self._CheckAccess(
        username, unicode(client_id),
        rdf_objects.ApprovalRequest.ApprovalType.APPROVAL_TYPE_CLIENT)

  def CheckHuntAccess(self, username, hunt_id):
    """Checks whether a given user can access given hunt."""

    self._CheckAccess(
        username, unicode(hunt_id),
        rdf_objects.ApprovalRequest.ApprovalType.APPROVAL_TYPE_HUNT)

  def CheckCronJobAccess(self, username, cron_job_id):
    """Checks whether a given user can access given cron job."""

    self._CheckAccess(
        username, unicode(cron_job_id),
        rdf_objects.ApprovalRequest.ApprovalType.APPROVAL_TYPE_CRON_JOB)

  def CheckIfCanStartClientFlow(self, username, flow_name):
    """Checks whether a given user can start a given flow."""
    del username  # Unused.

    flow_cls = flow.GRRFlow.GetPlugin(flow_name)

    if not flow_cls.category:
      raise access_control.UnauthorizedAccess(
          "Flow %s can't be started via the API." % flow_name)

  def CheckIfUserIsAdmin(self, username):
    """Checks whether the user is an admin."""

    user_obj = data_store.REL_DB.ReadGRRUser(username)
    if user_obj.user_type != user_obj.UserType.USER_TYPE_ADMIN:
      raise access_control.UnauthorizedAccess(
          "User %s is not an admin." % username)


class ApiCallRouterWithApprovalChecks(api_call_router.ApiCallRouterStub):
  """Router that uses approvals-based ACL checks."""

  access_checker = None

  @staticmethod
  def ClearCache():
    cls = ApiCallRouterWithApprovalChecks
    cls.access_checker = None

  def _GetAccessChecker(self):
    cls = ApiCallRouterWithApprovalChecks

    if cls.access_checker is None:
      if data_store.RelationalDBReadEnabled():
        cls.access_checker = RelDBChecker()
      else:
        cls.access_checker = LegacyChecker()

    return cls.access_checker

  def __init__(self, params=None, access_checker=None, delegate=None):
    super(ApiCallRouterWithApprovalChecks, self).__init__(params=params)

    if not access_checker:
      access_checker = self._GetAccessChecker()
    self.access_checker = access_checker

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

  def GetClientVersions(self, args, token=None):
    # Everybody is allowed to get historical information about a client.

    return self.delegate.GetClientVersions(args, token=token)

  def GetClientVersionTimes(self, args, token=None):
    # Everybody is allowed to get the versions of a particular client.

    return self.delegate.GetClientVersionTimes(args, token=token)

  def InterrogateClient(self, args, token=None):
    self.access_checker.CheckClientAccess(token.username, args.client_id)

    return self.delegate.InterrogateClient(args, token=token)

  def GetInterrogateOperationState(self, args, token=None):
    # No ACL checks are required here, since the user can only check
    # operations started by him- or herself.

    return self.delegate.GetInterrogateOperationState(args, token=token)

  def GetLastClientIPAddress(self, args, token=None):
    # Everybody is allowed to get the last ip address of a particular client.

    return self.delegate.GetLastClientIPAddress(args, token=token)

  def ListClientCrashes(self, args, token=None):
    self.access_checker.CheckClientAccess(token.username, args.client_id)

    return self.delegate.ListClientCrashes(args, token=token)

  def ListClientActionRequests(self, args, token=None):
    self.access_checker.CheckClientAccess(token.username, args.client_id)

    return self.delegate.ListClientActionRequests(args, token=token)

  def GetClientLoadStats(self, args, token=None):
    self.access_checker.CheckClientAccess(token.username, args.client_id)

    return self.delegate.GetClientLoadStats(args, token=token)

  # Virtual file system methods.
  # ============================
  #
  def ListFiles(self, args, token=None):
    self.access_checker.CheckClientAccess(token.username, args.client_id)

    return self.delegate.ListFiles(args, token=token)

  def GetVfsFilesArchive(self, args, token=None):
    self.access_checker.CheckClientAccess(token.username, args.client_id)

    return self.delegate.GetVfsFilesArchive(args, token=token)

  def GetFileDetails(self, args, token=None):
    self.access_checker.CheckClientAccess(token.username, args.client_id)

    return self.delegate.GetFileDetails(args, token=token)

  def GetFileText(self, args, token=None):
    self.access_checker.CheckClientAccess(token.username, args.client_id)

    return self.delegate.GetFileText(args, token=token)

  def GetFileBlob(self, args, token=None):
    self.access_checker.CheckClientAccess(token.username, args.client_id)

    return self.delegate.GetFileBlob(args, token=token)

  def GetFileVersionTimes(self, args, token=None):
    self.access_checker.CheckClientAccess(token.username, args.client_id)

    return self.delegate.GetFileVersionTimes(args, token=token)

  def GetFileDownloadCommand(self, args, token=None):
    self.access_checker.CheckClientAccess(token.username, args.client_id)

    return self.delegate.GetFileDownloadCommand(args, token=token)

  def CreateVfsRefreshOperation(self, args, token=None):
    self.access_checker.CheckClientAccess(token.username, args.client_id)

    return self.delegate.CreateVfsRefreshOperation(args, token=token)

  def GetVfsRefreshOperationState(self, args, token=None):
    # No ACL checks are required here, since the user can only check
    # operations started by him- or herself.

    return self.delegate.GetVfsRefreshOperationState(args, token=token)

  def GetVfsTimeline(self, args, token=None):
    self.access_checker.CheckClientAccess(token.username, args.client_id)

    return self.delegate.GetVfsTimeline(args, token=token)

  def GetVfsTimelineAsCsv(self, args, token=None):
    self.access_checker.CheckClientAccess(token.username, args.client_id)

    return self.delegate.GetVfsTimelineAsCsv(args, token=token)

  def UpdateVfsFileContent(self, args, token=None):
    self.access_checker.CheckClientAccess(token.username, args.client_id)

    return self.delegate.UpdateVfsFileContent(args, token=token)

  def GetVfsFileContentUpdateState(self, args, token=None):
    # No ACL checks are required here, since the user can only check
    # operations started by him- or herself.

    return self.delegate.GetVfsFileContentUpdateState(args, token=token)

  def GetFileDecoders(self, args, token=None):
    self.access_checker.CheckClientAccess(token.username, args.client_id)
    return self.delegate.GetFileDecoders(args, token=token)

  def GetDecodedFileBlob(self, args, token=None):
    self.access_checker.CheckClientAccess(token.username, args.client_id)
    return self.delegate.GetDecodedFileBlob(args, token=token)

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
    self.access_checker.CheckClientAccess(token.username, args.client_id)

    return self.delegate.ListFlows(args, token=token)

  def GetFlow(self, args, token=None):
    self.access_checker.CheckClientAccess(token.username, args.client_id)

    return self.delegate.GetFlow(args, token=token)

  def CreateFlow(self, args, token=None):
    self.access_checker.CheckClientAccess(token.username, args.client_id)
    self.access_checker.CheckIfCanStartClientFlow(
        token.username, args.flow.name or args.flow.runner_args.flow_name)

    return self.delegate.CreateFlow(args, token=token)

  def CancelFlow(self, args, token=None):
    self.access_checker.CheckClientAccess(token.username, args.client_id)

    return self.delegate.CancelFlow(args, token=token)

  def ListFlowRequests(self, args, token=None):
    self.access_checker.CheckClientAccess(token.username, args.client_id)

    return self.delegate.ListFlowRequests(args, token=token)

  def ListFlowResults(self, args, token=None):
    self.access_checker.CheckClientAccess(token.username, args.client_id)

    return self.delegate.ListFlowResults(args, token=token)

  def GetExportedFlowResults(self, args, token=None):
    self.access_checker.CheckClientAccess(token.username, args.client_id)

    return self.delegate.GetExportedFlowResults(args, token=token)

  def GetFlowResultsExportCommand(self, args, token=None):
    self.access_checker.CheckClientAccess(token.username, args.client_id)

    return self.delegate.GetFlowResultsExportCommand(args, token=token)

  def GetFlowFilesArchive(self, args, token=None):
    self.access_checker.CheckClientAccess(token.username, args.client_id)

    return self.delegate.GetFlowFilesArchive(args, token=token)

  def ListFlowOutputPlugins(self, args, token=None):
    self.access_checker.CheckClientAccess(token.username, args.client_id)

    return self.delegate.ListFlowOutputPlugins(args, token=token)

  def ListFlowOutputPluginLogs(self, args, token=None):
    self.access_checker.CheckClientAccess(token.username, args.client_id)

    return self.delegate.ListFlowOutputPluginLogs(args, token=token)

  def ListFlowOutputPluginErrors(self, args, token=None):
    self.access_checker.CheckClientAccess(token.username, args.client_id)

    return self.delegate.ListFlowOutputPluginErrors(args, token=token)

  def ListFlowLogs(self, args, token=None):
    self.access_checker.CheckClientAccess(token.username, args.client_id)

    return self.delegate.ListFlowLogs(args, token=token)

  # Cron jobs methods.
  # =================
  #
  def ListCronJobs(self, args, token=None):
    # Everybody can list cron jobs.

    return self.delegate.ListCronJobs(args, token=token)

  def CreateCronJob(self, args, token=None):
    # Everybody can create a cron job.

    return self.delegate.CreateCronJob(args, token=token)

  def GetCronJob(self, args, token=None):
    # Everybody can retrieve a cron job.

    return self.delegate.GetCronJob(args, token=token)

  def ForceRunCronJob(self, args, token=None):
    self.access_checker.CheckCronJobAccess(token.username, args.cron_job_id)

    return self.delegate.ForceRunCronJob(args, token=token)

  def ModifyCronJob(self, args, token=None):
    self.access_checker.CheckCronJobAccess(token.username, args.cron_job_id)

    return self.delegate.ModifyCronJob(args, token=token)

  def ListCronJobRuns(self, args, token=None):
    # Everybody can list cron jobs' runs.

    return self.delegate.ListCronJobRuns(args, token=token)

  def GetCronJobRun(self, args, token=None):
    # Everybody can get cron runs.

    return self.delegate.GetCronJobRun(args, token=token)

  def DeleteCronJob(self, args, token=None):
    self.access_checker.CheckCronJobAccess(token.username, args.cron_job_id)

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

  def GetExportedHuntResults(self, args, token=None):
    # Everybody can export hunt's results.

    return self.delegate.GetExportedHuntResults(args, token=token)

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

  def ModifyHunt(self, args, token=None):
    # Starting/stopping hunt or modifying its attributes requires an approval.
    self.access_checker.CheckHuntAccess(token.username, args.hunt_id)

    return self.delegate.ModifyHunt(args, token=token)

  def _GetHuntObj(self, hunt_id, token=None):
    hunt_urn = hunt_id.ToURN()
    try:
      return aff4.FACTORY.Open(
          hunt_urn, aff4_type=implementation.GRRHunt, token=token)
    except aff4.InstantiationError:
      raise api_call_handler_base.ResourceNotFoundError(
          "Hunt with id %s could not be found" % hunt_id)

  def DeleteHunt(self, args, token=None):
    hunt_obj = self._GetHuntObj(args.hunt_id, token=token)

    # Hunt's creator is allowed to delete the hunt.
    if token.username != hunt_obj.creator:
      self.access_checker.CheckHuntAccess(token.username, args.hunt_id)

    return self.delegate.DeleteHunt(args, token=token)

  def GetHuntFilesArchive(self, args, token=None):
    self.access_checker.CheckHuntAccess(token.username, args.hunt_id)

    return self.delegate.GetHuntFilesArchive(args, token=token)

  def GetHuntFile(self, args, token=None):
    self.access_checker.CheckHuntAccess(token.username, args.hunt_id)

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

  def ListReports(self, args, token=None):
    # Everybody can list the reports.

    return self.delegate.ListReports(args, token=token)

  def GetReport(self, args, token=None):
    # Everybody can get report data.

    return self.delegate.GetReport(args, token=token)

  # Approvals methods.
  # =================
  #
  def CreateClientApproval(self, args, token=None):
    # Everybody can create a user client approval.

    return self.delegate.CreateClientApproval(args, token=token)

  def GetClientApproval(self, args, token=None):
    # Everybody can have access to everybody's client approvals, provided
    # they know: a client id, a username of the requester and an approval id.

    return self.delegate.GetClientApproval(args, token=token)

  def GrantClientApproval(self, args, token=None):
    # Everybody can grant everybody's client approvals, provided
    # they know: a client id, a username of the requester and an approval id.
    #
    # NOTE: Granting an approval doesn't necessarily mean that corresponding
    # approval request becomes fulfilled right away. Calling this method
    # adds the caller to the approval's approvers list. Then it depends
    # on a particular approval if this list is sufficient or not.
    # Typical case: user can grant his own approval, but this won't make
    # the approval valid.

    return self.delegate.GrantClientApproval(args, token=token)

  def ListClientApprovals(self, args, token=None):
    # Everybody can list their own user client approvals.

    return self.delegate.ListClientApprovals(args, token=token)

  def CreateHuntApproval(self, args, token=None):
    # Everybody can request a hunt approval.

    return self.delegate.CreateHuntApproval(args, token=token)

  def GetHuntApproval(self, args, token=None):
    # Everybody can have access to everybody's hunts approvals, provided
    # they know: a hunt id, a username of the requester and an approval id.

    return self.delegate.GetHuntApproval(args, token=token)

  def GrantHuntApproval(self, args, token=None):
    # Everybody can grant everybody's hunts approvals, provided
    # they know: a hunt id, a username of the requester and an approval id.
    #
    # NOTE: Granting an approval doesn't necessarily mean that corresponding
    # approval request becomes fulfilled right away. Calling this method
    # adds the caller to the approval's approvers list. Then it depends
    # on a particular approval if this list is sufficient or not.
    # Typical case: user can grant his own approval, but this won't make
    # the approval valid.

    return self.delegate.GrantHuntApproval(args, token=token)

  def ListHuntApprovals(self, args, token=None):
    # Everybody can list their own user hunt approvals.

    return self.delegate.ListHuntApprovals(args, token=token)

  def CreateCronJobApproval(self, args, token=None):
    # Everybody can request a cron job approval.

    return self.delegate.CreateCronJobApproval(args, token=token)

  def GetCronJobApproval(self, args, token=None):
    # Everybody can have access to everybody's crons approvals, provided
    # they know: a cron job id, a username of the requester and an approval id.

    return self.delegate.GetCronJobApproval(args, token=token)

  def GrantCronJobApproval(self, args, token=None):
    # Everybody can have access to everybody's crons approvals, provided
    # they know: a cron job id, a username of the requester and an approval id.
    #
    # NOTE: Granting an approval doesn't necessarily mean that corresponding
    # approval request becomes fulfilled right away. Calling this method
    # adds the caller to the approval's approvers list. Then it depends
    # on a particular approval if this list is sufficient or not.
    # Typical case: user can grant his own approval, but this won't make
    # the approval valid.

    return self.delegate.GrantCronJobApproval(args, token=token)

  def ListCronJobApprovals(self, args, token=None):
    # Everybody can list their own user cron approvals.

    return self.delegate.ListCronJobApprovals(args, token=token)

  def ListApproverSuggestions(self, args, token=None):
    # Everybody can list suggestions for approver usernames.

    return self.delegate.ListApproverSuggestions(args, token=token)

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

    interface_traits = api_user.ApiGrrUserInterfaceTraits().EnableAll()
    try:
      self.access_checker.CheckIfUserIsAdmin(token.username)
    except access_control.UnauthorizedAccess:
      interface_traits.manage_binaries_nav_item_enabled = False

    return api_user.ApiGetOwnGrrUserHandler(interface_traits=interface_traits)

  def UpdateGrrUser(self, args, token=None):
    # Everybody can update their own user settings.

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

  def ListGrrBinaries(self, args, token=None):
    self.access_checker.CheckIfUserIsAdmin(token.username)

    return self.delegate.ListGrrBinaries(args, token=token)

  def GetGrrBinary(self, args, token=None):
    self.access_checker.CheckIfUserIsAdmin(token.username)

    return self.delegate.GetGrrBinary(args, token=token)

  def GetGrrBinaryBlob(self, args, token=None):
    self.access_checker.CheckIfUserIsAdmin(token.username)

    return self.delegate.GetGrrBinaryBlob(args, token=token)

  # Reflection methods.
  # ==================
  #
  def ListKbFields(self, args, token=None):
    # Everybody can list knowledge base fields.

    return self.delegate.ListKbFields(args, token=token)

  def ListFlowDescriptors(self, args, token=None):
    # Everybody can list flow descritors.

    return api_flow.ApiListFlowDescriptorsHandler(
        self.access_checker.CheckIfCanStartClientFlow)

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

  def ListApiMethods(self, args, token=None):
    # Everybody can get the docs.

    return self.delegate.ListApiMethods(args, token=token)


# This class is kept here for backwards compatibility only.
# TODO(user): Remove EOQ42017
class ApiCallRouterWithApprovalChecksWithoutRobotAccess(
    ApiCallRouterWithApprovalChecks):
  pass


# This class is kept here for backwards compatibility only.
# TODO(user): Remove EOQ42017
class ApiCallRouterWithApprovalChecksWithRobotAccess(
    ApiCallRouterWithApprovalChecks):
  pass
