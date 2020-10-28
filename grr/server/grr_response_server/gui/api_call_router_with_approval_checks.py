#!/usr/bin/env python
# Lint as: python3
"""Implementation of a router class that has approvals-based ACL checks."""
from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

from typing import Optional
from typing import Text

from grr_response_core.lib import registry
from grr_response_core.lib import utils
from grr_response_core.lib.util import precondition
from grr_response_core.stats import metrics
from grr_response_server import access_control
from grr_response_server import data_store
from grr_response_server.databases import db
from grr_response_server.flows.general import timeline
from grr_response_server.gui import api_call_context
from grr_response_server.gui import api_call_handler_base
from grr_response_server.gui import api_call_router
from grr_response_server.gui import api_call_router_without_checks
from grr_response_server.gui import approval_checks
from grr_response_server.gui.api_plugins import flow as api_flow
from grr_response_server.gui.api_plugins import hunt as api_hunt
from grr_response_server.gui.api_plugins import metadata as api_metadata
from grr_response_server.gui.api_plugins import timeline as api_timeline
from grr_response_server.gui.api_plugins import user as api_user
from grr_response_server.gui.api_plugins import yara as api_yara
from grr_response_server.rdfvalues import objects as rdf_objects


APPROVAL_SEARCHES = metrics.Counter(
    "approval_searches", fields=[("reason_presence", str), ("source", str)])


class AccessChecker(object):
  """Relational DB-based access checker implementation."""

  APPROVAL_CACHE_TIME = 60

  def __init__(self):
    self.acl_cache = utils.AgeBasedCache(
        max_size=10000, max_age=self.APPROVAL_CACHE_TIME)

  def _CheckAccess(self, username, subject_id, approval_type):
    """Checks access to a given subject by a given user."""
    precondition.AssertType(subject_id, Text)

    cache_key = (username, subject_id, approval_type)
    try:
      approval = self.acl_cache.Get(cache_key)
      APPROVAL_SEARCHES.Increment(fields=["-", "cache"])
      return approval
    except KeyError:
      APPROVAL_SEARCHES.Increment(fields=["-", "reldb"])

    approvals = data_store.REL_DB.ReadApprovalRequests(
        username, approval_type, subject_id=subject_id, include_expired=False)

    errors = []
    for approval in approvals:
      try:
        approval_checks.CheckApprovalRequest(approval)
        self.acl_cache.Put(cache_key, approval)
        return approval
      except access_control.UnauthorizedAccess as e:
        errors.append(e)

    subject = approval_checks.BuildLegacySubject(subject_id, approval_type)
    if not errors:
      raise access_control.UnauthorizedAccess(
          "No approval found.", subject=subject)
    else:
      raise access_control.UnauthorizedAccess(
          " ".join(str(e) for e in errors), subject=subject)

  def CheckClientAccess(self, context, client_id):
    """Checks whether a given user can access given client."""
    context.approval = self._CheckAccess(
        context.username, str(client_id),
        rdf_objects.ApprovalRequest.ApprovalType.APPROVAL_TYPE_CLIENT)

  def CheckHuntAccess(self, context, hunt_id):
    """Checks whether a given user can access given hunt."""
    context.approval = self._CheckAccess(
        context.username, str(hunt_id),
        rdf_objects.ApprovalRequest.ApprovalType.APPROVAL_TYPE_HUNT)

  def CheckCronJobAccess(self, context, cron_job_id):
    """Checks whether a given user can access given cron job."""
    context.approval = self._CheckAccess(
        context.username, str(cron_job_id),
        rdf_objects.ApprovalRequest.ApprovalType.APPROVAL_TYPE_CRON_JOB)

  def CheckIfCanStartClientFlow(self, username, flow_name):
    """Checks whether a given user can start a given flow."""
    del username  # Unused.

    flow_cls = registry.FlowRegistry.FLOW_REGISTRY.get(flow_name)

    if not flow_cls.category:
      raise access_control.UnauthorizedAccess(
          "Flow %s can't be started via the API." % flow_name)

  def CheckIfUserIsAdmin(self, username):
    """Checks whether the user is an admin."""

    user_obj = data_store.REL_DB.ReadGRRUser(username)
    if user_obj.user_type != user_obj.UserType.USER_TYPE_ADMIN:
      raise access_control.UnauthorizedAccess("User %s is not an admin." %
                                              username)


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
      cls.access_checker = AccessChecker()

    return cls.access_checker

  def __init__(self, params=None, access_checker=None, delegate=None):
    super().__init__(params=params)

    if not access_checker:
      access_checker = self._GetAccessChecker()
    self.access_checker = access_checker

    if not delegate:
      delegate = api_call_router_without_checks.ApiCallRouterWithoutChecks()
    self.delegate = delegate

  # Artifacts methods.
  # =================
  #
  def ListArtifacts(self, args, context=None):
    # Everybody is allowed to list artifacts.

    return self.delegate.ListArtifacts(args, context=context)

  def UploadArtifact(self, args, context=None):
    # Everybody is allowed to upload artifacts.

    return self.delegate.UploadArtifact(args, context=context)

  def DeleteArtifacts(self, args, context=None):
    # Everybody is allowed to delete artifacts.

    return self.delegate.DeleteArtifacts(args, context=context)

  # Clients methods.
  # ===============
  #
  def SearchClients(self, args, context=None):
    # Everybody is allowed to search clients.

    return self.delegate.SearchClients(args, context=context)

  def VerifyAccess(self, args, context=None):
    self.access_checker.CheckClientAccess(context, args.client_id)

    return self.delegate.VerifyAccess(args, context=context)

  def GetClient(self, args, context=None):
    # Everybody is allowed to get information about a particular client.

    return self.delegate.GetClient(args, context=context)

  def GetClientVersions(self, args, context=None):
    # Everybody is allowed to get historical information about a client.

    return self.delegate.GetClientVersions(args, context=context)

  def GetClientVersionTimes(self, args, context=None):
    # Everybody is allowed to get the versions of a particular client.

    return self.delegate.GetClientVersionTimes(args, context=context)

  def InterrogateClient(self, args, context=None):
    self.access_checker.CheckClientAccess(context, args.client_id)

    return self.delegate.InterrogateClient(args, context=context)

  def GetInterrogateOperationState(self, args, context=None):
    # No ACL checks are required here, since the user can only check
    # operations started by him- or herself.

    return self.delegate.GetInterrogateOperationState(args, context=context)

  def GetLastClientIPAddress(self, args, context=None):
    # Everybody is allowed to get the last ip address of a particular client.

    return self.delegate.GetLastClientIPAddress(args, context=context)

  def ListClientCrashes(self, args, context=None):
    self.access_checker.CheckClientAccess(context, args.client_id)

    return self.delegate.ListClientCrashes(args, context=context)

  def ListClientActionRequests(self, args, context=None):
    self.access_checker.CheckClientAccess(context, args.client_id)

    return self.delegate.ListClientActionRequests(args, context=context)

  def GetClientLoadStats(self, args, context=None):
    self.access_checker.CheckClientAccess(context, args.client_id)

    return self.delegate.GetClientLoadStats(args, context=context)

  # Virtual file system methods.
  # ============================
  #
  def ListFiles(self, args, context=None):
    self.access_checker.CheckClientAccess(context, args.client_id)

    return self.delegate.ListFiles(args, context=context)

  def GetVfsFilesArchive(self, args, context=None):
    self.access_checker.CheckClientAccess(context, args.client_id)

    return self.delegate.GetVfsFilesArchive(args, context=context)

  def GetFileDetails(self, args, context=None):
    self.access_checker.CheckClientAccess(context, args.client_id)

    return self.delegate.GetFileDetails(args, context=context)

  def GetFileText(self, args, context=None):
    self.access_checker.CheckClientAccess(context, args.client_id)

    return self.delegate.GetFileText(args, context=context)

  def GetFileBlob(self, args, context=None):
    self.access_checker.CheckClientAccess(context, args.client_id)

    return self.delegate.GetFileBlob(args, context=context)

  def GetFileVersionTimes(self, args, context=None):
    self.access_checker.CheckClientAccess(context, args.client_id)

    return self.delegate.GetFileVersionTimes(args, context=context)

  def GetFileDownloadCommand(self, args, context=None):
    self.access_checker.CheckClientAccess(context, args.client_id)

    return self.delegate.GetFileDownloadCommand(args, context=context)

  def CreateVfsRefreshOperation(self, args, context=None):
    self.access_checker.CheckClientAccess(context, args.client_id)

    return self.delegate.CreateVfsRefreshOperation(args, context=context)

  def GetVfsRefreshOperationState(self, args, context=None):
    # No ACL checks are required here, since the user can only check
    # operations started by him- or herself.

    return self.delegate.GetVfsRefreshOperationState(args, context=context)

  def GetVfsTimeline(self, args, context=None):
    self.access_checker.CheckClientAccess(context, args.client_id)

    return self.delegate.GetVfsTimeline(args, context=context)

  def GetVfsTimelineAsCsv(self, args, context=None):
    self.access_checker.CheckClientAccess(context, args.client_id)

    return self.delegate.GetVfsTimelineAsCsv(args, context=context)

  def UpdateVfsFileContent(self, args, context=None):
    self.access_checker.CheckClientAccess(context, args.client_id)

    return self.delegate.UpdateVfsFileContent(args, context=context)

  def GetVfsFileContentUpdateState(self, args, context=None):
    # No ACL checks are required here, since the user can only check
    # operations started by him- or herself.

    return self.delegate.GetVfsFileContentUpdateState(args, context=context)

  def GetFileDecoders(self, args, context=None):
    self.access_checker.CheckClientAccess(context, args.client_id)
    return self.delegate.GetFileDecoders(args, context=context)

  def GetDecodedFileBlob(self, args, context=None):
    self.access_checker.CheckClientAccess(context, args.client_id)
    return self.delegate.GetDecodedFileBlob(args, context=context)

  # Clients labels methods.
  # ======================
  #
  def ListClientsLabels(self, args, context=None):
    # Everybody is allowed to get a list of all labels used on the system.

    return self.delegate.ListClientsLabels(args, context=context)

  def AddClientsLabels(self, args, context=None):
    # Everybody is allowed to add labels. Labels owner will be attributed to
    # the current user.

    return self.delegate.AddClientsLabels(args, context=context)

  def RemoveClientsLabels(self, args, context=None):
    # Everybody is allowed to remove labels. ApiRemoveClientsLabelsHandler is
    # written in such a way, so that it will only delete user's own labels.

    return self.delegate.RemoveClientsLabels(args, context=context)

  # Clients flows methods.
  # =====================
  #
  def ListFlows(self, args, context=None):
    self.access_checker.CheckClientAccess(context, args.client_id)

    return self.delegate.ListFlows(args, context=context)

  def GetFlow(self, args, context=None):
    self.access_checker.CheckClientAccess(context, args.client_id)

    return self.delegate.GetFlow(args, context=context)

  def CreateFlow(self, args, context=None):
    self.access_checker.CheckClientAccess(context, args.client_id)
    self.access_checker.CheckIfCanStartClientFlow(
        context.username, args.flow.name or args.flow.runner_args.flow_name)

    return self.delegate.CreateFlow(args, context=context)

  def CancelFlow(self, args, context=None):
    self.access_checker.CheckClientAccess(context, args.client_id)

    return self.delegate.CancelFlow(args, context=context)

  def ListFlowRequests(self, args, context=None):
    self.access_checker.CheckClientAccess(context, args.client_id)

    return self.delegate.ListFlowRequests(args, context=context)

  def ListFlowResults(self, args, context=None):
    self.access_checker.CheckClientAccess(context, args.client_id)

    return self.delegate.ListFlowResults(args, context=context)

  def GetExportedFlowResults(self, args, context=None):
    self.access_checker.CheckClientAccess(context, args.client_id)

    return self.delegate.GetExportedFlowResults(args, context=context)

  def GetFlowResultsExportCommand(self, args, context=None):
    self.access_checker.CheckClientAccess(context, args.client_id)

    return self.delegate.GetFlowResultsExportCommand(args, context=context)

  def GetFlowFilesArchive(self, args, context=None):
    self.access_checker.CheckClientAccess(context, args.client_id)

    return self.delegate.GetFlowFilesArchive(args, context=context)

  def ListFlowOutputPlugins(self, args, context=None):
    self.access_checker.CheckClientAccess(context, args.client_id)

    return self.delegate.ListFlowOutputPlugins(args, context=context)

  def ListFlowOutputPluginLogs(self, args, context=None):
    self.access_checker.CheckClientAccess(context, args.client_id)

    return self.delegate.ListFlowOutputPluginLogs(args, context=context)

  def ListFlowOutputPluginErrors(self, args, context=None):
    self.access_checker.CheckClientAccess(context, args.client_id)

    return self.delegate.ListFlowOutputPluginErrors(args, context=context)

  def ListFlowLogs(self, args, context=None):
    self.access_checker.CheckClientAccess(context, args.client_id)

    return self.delegate.ListFlowLogs(args, context=context)

  def GetCollectedTimeline(self, args, context=None):
    try:
      flow = data_store.REL_DB.ReadFlowObject(
          str(args.client_id), str(args.flow_id))
    except db.UnknownFlowError:
      raise api_call_handler_base.ResourceNotFoundError(
          "Flow with client id %s and flow id %s could not be found" %
          (args.client_id, args.flow_id))

    if flow.flow_class_name != timeline.TimelineFlow.__name__:
      raise ValueError("Flow '{}' is not a timeline flow".format(flow.flow_id))

    # Check for client access if this flow was not scheduled as part of a hunt.
    if flow.parent_hunt_id != flow.flow_id:
      self.access_checker.CheckClientAccess(context, args.client_id)

    return self.delegate.GetCollectedTimeline(args, context=context)

  def UploadYaraSignature(
      self,
      args: api_yara.ApiUploadYaraSignatureArgs,
      context: Optional[api_call_context.ApiCallContext] = None,
  ) -> api_yara.ApiUploadYaraSignatureHandler:
    return self.delegate.UploadYaraSignature(args, context=context)

  def ExplainGlobExpression(
      self,
      args: api_flow.ApiExplainGlobExpressionArgs,
      context: Optional[api_call_context.ApiCallContext] = None,
  ) -> api_flow.ApiExplainGlobExpressionHandler:
    # ExplainGlobExpression only exposes the KnowledgeBase, which does not need
    # approval.
    return self.delegate.ExplainGlobExpression(args, context=context)

  def ScheduleFlow(
      self,
      args: api_flow.ApiCreateFlowArgs,
      context: Optional[api_call_context.ApiCallContext] = None,
  ) -> api_flow.ApiScheduleFlowHandler:
    return self.delegate.ScheduleFlow(args, context=context)

  def ListScheduledFlows(
      self,
      args: api_flow.ApiListScheduledFlowsArgs,
      context: Optional[api_call_context.ApiCallContext] = None,
  ) -> api_flow.ApiListScheduledFlowsHandler:
    return self.delegate.ListScheduledFlows(args, context=context)

  def UnscheduleFlow(
      self,
      args: api_flow.ApiUnscheduleFlowArgs,
      context: Optional[api_call_context.ApiCallContext] = None,
  ) -> api_flow.ApiUnscheduleFlowHandler:
    return self.delegate.UnscheduleFlow(args, context=context)

  # Cron jobs methods.
  # =================
  #
  def ListCronJobs(self, args, context=None):
    # Everybody can list cron jobs.

    return self.delegate.ListCronJobs(args, context=context)

  def CreateCronJob(self, args, context=None):
    # Everybody can create a cron job.

    return self.delegate.CreateCronJob(args, context=context)

  def GetCronJob(self, args, context=None):
    # Everybody can retrieve a cron job.

    return self.delegate.GetCronJob(args, context=context)

  def ForceRunCronJob(self, args, context=None):
    self.access_checker.CheckCronJobAccess(context, args.cron_job_id)

    return self.delegate.ForceRunCronJob(args, context=context)

  def ModifyCronJob(self, args, context=None):
    self.access_checker.CheckCronJobAccess(context, args.cron_job_id)

    return self.delegate.ModifyCronJob(args, context=context)

  def ListCronJobRuns(self, args, context=None):
    # Everybody can list cron jobs' runs.

    return self.delegate.ListCronJobRuns(args, context=context)

  def GetCronJobRun(self, args, context=None):
    # Everybody can get cron runs.

    return self.delegate.GetCronJobRun(args, context=context)

  def DeleteCronJob(self, args, context=None):
    self.access_checker.CheckCronJobAccess(context, args.cron_job_id)

    return self.delegate.DeleteCronJob(args, context=context)

  # Hunts methods.
  # =============
  #
  def ListHunts(self, args, context=None):
    # Everybody can list hunts.

    return self.delegate.ListHunts(args, context=context)

  def GetHunt(self, args, context=None):
    # Everybody can get hunt's information.

    return self.delegate.GetHunt(args, context=context)

  def ListHuntErrors(self, args, context=None):
    # Everybody can get hunt errors list.

    return self.delegate.ListHuntErrors(args, context=context)

  def ListHuntLogs(self, args, context=None):
    # Everybody can look into hunt's logs.

    return self.delegate.ListHuntLogs(args, context=context)

  def ListHuntResults(self, args, context=None):
    # Everybody can look into hunt's results.

    return self.delegate.ListHuntResults(args, context=context)

  def GetExportedHuntResults(self, args, context=None):
    # Everybody can export hunt's results.

    return self.delegate.GetExportedHuntResults(args, context=context)

  def GetHuntResultsExportCommand(self, args, context=None):
    # Everybody can get hunt's export command.

    return self.delegate.GetHuntResultsExportCommand(args, context=context)

  def ListHuntOutputPlugins(self, args, context=None):
    # Everybody can list hunt output plugins.

    return self.delegate.ListHuntOutputPlugins(args, context=context)

  def ListHuntOutputPluginLogs(self, args, context=None):
    # Everybody can list hunt output plugins logs.

    return self.delegate.ListHuntOutputPluginLogs(args, context=context)

  def ListHuntOutputPluginErrors(self, args, context=None):
    # Everybody can list hunt output plugin errors.

    return self.delegate.ListHuntOutputPluginErrors(args, context=context)

  def ListHuntCrashes(self, args, context=None):
    # Everybody can list hunt's crashes.

    return self.delegate.ListHuntCrashes(args, context=context)

  def GetHuntClientCompletionStats(self, args, context=None):
    # Everybody can get hunt's client completion stats.

    return self.delegate.GetHuntClientCompletionStats(args, context=context)

  def GetHuntStats(self, args, context=None):
    # Everybody can get hunt's stats.

    return self.delegate.GetHuntStats(args, context=context)

  def ListHuntClients(self, args, context=None):
    # Everybody can get hunt's clients.

    return self.delegate.ListHuntClients(args, context=context)

  def GetHuntContext(self, args, context=None):
    # Everybody can get hunt's context.

    return self.delegate.GetHuntContext(args, context=context)

  def CreateHunt(self, args, context=None):
    # Everybody can create a hunt.

    return self.delegate.CreateHunt(args, context=context)

  def ModifyHunt(self, args, context=None):
    # Starting/stopping hunt or modifying its attributes requires an approval.
    self.access_checker.CheckHuntAccess(context, args.hunt_id)

    return self.delegate.ModifyHunt(args, context=context)

  def _GetHuntObj(self, hunt_id, context=None):
    try:
      return data_store.REL_DB.ReadHuntObject(str(hunt_id))
    except db.UnknownHuntError:
      raise api_call_handler_base.ResourceNotFoundError(
          "Hunt with id %s could not be found" % hunt_id)

  def DeleteHunt(self, args, context=None):
    hunt_obj = self._GetHuntObj(args.hunt_id, context=context)

    # Hunt's creator is allowed to delete the hunt.
    if context.username != hunt_obj.creator:
      self.access_checker.CheckHuntAccess(context, args.hunt_id)

    return self.delegate.DeleteHunt(args, context=context)

  def GetHuntFilesArchive(self, args, context=None):
    self.access_checker.CheckHuntAccess(context, args.hunt_id)

    return self.delegate.GetHuntFilesArchive(args, context=context)

  def GetHuntFile(self, args, context=None):
    self.access_checker.CheckHuntAccess(context, args.hunt_id)

    return self.delegate.GetHuntFile(args, context=context)

  def GetCollectedHuntTimelines(
      self,
      args: api_timeline.ApiGetCollectedHuntTimelinesArgs,
      context: Optional[api_call_context.ApiCallContext] = None,
  ) -> api_timeline.ApiGetCollectedHuntTimelinesHandler:
    # Everybody can export collected hunt timelines.
    return self.delegate.GetCollectedHuntTimelines(args, context=context)

  def CreatePerClientFileCollectionHunt(
      self, args: api_hunt.ApiCreatePerClientFileCollectionHuntArgs,
      context: api_call_context.ApiCallContext
  ) -> api_call_handler_base.ApiCallHandler:
    """Create a new per-client file collection hunt."""
    # Everybody can create a per-client file collection hunt.
    return self.delegate.CreatePerClientFileCollectionHunt(
        args, context=context)

  # Stats metrics methods.
  # =====================
  #
  def ListReports(self, args, context=None):
    # Everybody can list the reports.

    return self.delegate.ListReports(args, context=context)

  def GetReport(self, args, context=None):
    # Everybody can get report data.

    return self.delegate.GetReport(args, context=context)

  # Approvals methods.
  # =================
  #
  def CreateClientApproval(self, args, context=None):
    # Everybody can create a user client approval.

    return self.delegate.CreateClientApproval(args, context=context)

  def GetClientApproval(self, args, context=None):
    # Everybody can have access to everybody's client approvals, provided
    # they know: a client id, a username of the requester and an approval id.

    return self.delegate.GetClientApproval(args, context=context)

  def GrantClientApproval(self, args, context=None):
    # Everybody can grant everybody's client approvals, provided
    # they know: a client id, a username of the requester and an approval id.
    #
    # NOTE: Granting an approval doesn't necessarily mean that corresponding
    # approval request becomes fulfilled right away. Calling this method
    # adds the caller to the approval's approvers list. Then it depends
    # on a particular approval if this list is sufficient or not.
    # Typical case: user can grant his own approval, but this won't make
    # the approval valid.

    return self.delegate.GrantClientApproval(args, context=context)

  def ListClientApprovals(self, args, context=None):
    # Everybody can list their own user client approvals.

    return self.delegate.ListClientApprovals(args, context=context)

  def CreateHuntApproval(self, args, context=None):
    # Everybody can request a hunt approval.

    return self.delegate.CreateHuntApproval(args, context=context)

  def GetHuntApproval(self, args, context=None):
    # Everybody can have access to everybody's hunts approvals, provided
    # they know: a hunt id, a username of the requester and an approval id.

    return self.delegate.GetHuntApproval(args, context=context)

  def GrantHuntApproval(self, args, context=None):
    # Everybody can grant everybody's hunts approvals, provided
    # they know: a hunt id, a username of the requester and an approval id.
    #
    # NOTE: Granting an approval doesn't necessarily mean that corresponding
    # approval request becomes fulfilled right away. Calling this method
    # adds the caller to the approval's approvers list. Then it depends
    # on a particular approval if this list is sufficient or not.
    # Typical case: user can grant his own approval, but this won't make
    # the approval valid.

    return self.delegate.GrantHuntApproval(args, context=context)

  def ListHuntApprovals(self, args, context=None):
    # Everybody can list their own user hunt approvals.

    return self.delegate.ListHuntApprovals(args, context=context)

  def CreateCronJobApproval(self, args, context=None):
    # Everybody can request a cron job approval.

    return self.delegate.CreateCronJobApproval(args, context=context)

  def GetCronJobApproval(self, args, context=None):
    # Everybody can have access to everybody's crons approvals, provided
    # they know: a cron job id, a username of the requester and an approval id.

    return self.delegate.GetCronJobApproval(args, context=context)

  def GrantCronJobApproval(self, args, context=None):
    # Everybody can have access to everybody's crons approvals, provided
    # they know: a cron job id, a username of the requester and an approval id.
    #
    # NOTE: Granting an approval doesn't necessarily mean that corresponding
    # approval request becomes fulfilled right away. Calling this method
    # adds the caller to the approval's approvers list. Then it depends
    # on a particular approval if this list is sufficient or not.
    # Typical case: user can grant his own approval, but this won't make
    # the approval valid.

    return self.delegate.GrantCronJobApproval(args, context=context)

  def ListCronJobApprovals(self, args, context=None):
    # Everybody can list their own user cron approvals.

    return self.delegate.ListCronJobApprovals(args, context=context)

  def ListApproverSuggestions(self, args, context=None):
    # Everybody can list suggestions for approver usernames.

    return self.delegate.ListApproverSuggestions(args, context=context)

  # User settings methods.
  # =====================
  #
  def GetPendingUserNotificationsCount(self, args, context=None):
    # Everybody can get their own pending notifications count.

    return self.delegate.GetPendingUserNotificationsCount(args, context=context)

  def ListPendingUserNotifications(self, args, context=None):
    # Everybody can get their own pending notifications count.

    return self.delegate.ListPendingUserNotifications(args, context=context)

  def DeletePendingUserNotification(self, args, context=None):
    # Everybody can get their own pending notifications count.

    return self.delegate.DeletePendingUserNotification(args, context=context)

  def ListAndResetUserNotifications(self, args, context=None):
    # Everybody can get their own user notifications.

    return self.delegate.ListAndResetUserNotifications(args, context=context)

  def GetGrrUser(self, args, context=None):
    # Everybody can get their own user settings.

    interface_traits = api_user.ApiGrrUserInterfaceTraits().EnableAll()
    try:
      self.access_checker.CheckIfUserIsAdmin(context.username)
    except access_control.UnauthorizedAccess:
      interface_traits.manage_binaries_nav_item_enabled = False

    return api_user.ApiGetOwnGrrUserHandler(interface_traits=interface_traits)

  def UpdateGrrUser(self, args, context=None):
    # Everybody can update their own user settings.

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

  def ListGrrBinaries(self, args, context=None):
    self.access_checker.CheckIfUserIsAdmin(context.username)

    return self.delegate.ListGrrBinaries(args, context=context)

  def GetGrrBinary(self, args, context=None):
    self.access_checker.CheckIfUserIsAdmin(context.username)

    return self.delegate.GetGrrBinary(args, context=context)

  def GetGrrBinaryBlob(self, args, context=None):
    self.access_checker.CheckIfUserIsAdmin(context.username)

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
        self.access_checker.CheckIfCanStartClientFlow)

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
