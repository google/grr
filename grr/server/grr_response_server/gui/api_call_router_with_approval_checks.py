#!/usr/bin/env python
"""Implementation of a router class that has approvals-based ACL checks."""

from typing import Optional

from grr_response_core.lib.rdfvalues import structs as rdf_structs
from grr_response_proto import api_call_router_pb2
from grr_response_proto import objects_pb2
from grr_response_proto.api import user_pb2 as api_user_pb2
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
from grr_response_server.gui.api_plugins import osquery as api_osquery
from grr_response_server.gui.api_plugins import signed_commands as api_signed_commands
from grr_response_server.gui.api_plugins import stats as api_stats
from grr_response_server.gui.api_plugins import timeline as api_timeline
from grr_response_server.gui.api_plugins import user as api_user
from grr_response_server.gui.api_plugins import vfs as api_vfs
from grr_response_server.gui.api_plugins import yara as api_yara
from grr_response_server.rdfvalues import hunt_objects as rdf_hunt_objects
from grr_response_server.rdfvalues import mig_hunt_objects


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


class ApiCallRouterWithApprovalCheckParams(rdf_structs.RDFProtoStruct):
  protobuf = api_call_router_pb2.ApiCallRouterWithApprovalCheckParams


class ApiCallRouterWithApprovalChecks(api_call_router.ApiCallRouterStub):
  """Router that uses approvals-based ACL checks."""

  params_type = ApiCallRouterWithApprovalCheckParams

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

  def _CheckFlowOrClientAccess(self, args, context=None):
    try:
      flow = data_store.REL_DB.ReadFlowObject(
          str(args.client_id), str(args.flow_id)
      )
    except db.UnknownFlowError as e:
      raise api_call_handler_base.ResourceNotFoundError(
          "Flow with client id %s and flow id %s could not be found"
          % (args.client_id, args.flow_id)
      ) from e

    # Check for client access if this flow was not scheduled as part of a hunt.
    # Only top-level hunt flows are allowed, which is what any user can see
    # as "hunt results" (child flows results are not available for anyone).
    if flow.parent_hunt_id != flow.flow_id:
      self.approval_checker.CheckClientAccess(context, str(args.client_id))

  def __init__(
      self,
      params: Optional[ApiCallRouterWithApprovalCheckParams] = None,
      approval_checker: Optional[access_controller.ApprovalChecker] = None,
      admin_access_checker: Optional[
          ApprovalCheckParamsAdminAccessChecker
      ] = None,
      delegate: Optional[api_call_router.ApiCallRouter] = None,
  ):
    super().__init__(params=params)

    params = ToProtoApiCallRouterWithApprovalCheckParams(params)

    if not admin_access_checker:
      admin_access_checker = ApprovalCheckParamsAdminAccessChecker(params)
    self.admin_access_checker = admin_access_checker

    if not approval_checker:
      approval_checker = self._GetApprovalChecker(self.admin_access_checker)
    self.approval_checker = approval_checker

    if not delegate:
      delegate = api_call_router_without_checks.ApiCallRouterWithoutChecks()
    self.delegate = delegate

  # Artifacts methods.
  # =================
  #
  # pytype: disable=attribute-error
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
    self.approval_checker.CheckClientAccess(context, str(args.client_id))

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
    self.approval_checker.CheckClientAccess(context, str(args.client_id))

    return self.delegate.InterrogateClient(args, context=context)

  def GetInterrogateOperationState(self, args, context=None):
    # No ACL checks are required here, since the user can only check
    # operations started by themselves.

    return self.delegate.GetInterrogateOperationState(args, context=context)

  def GetLastClientIPAddress(self, args, context=None):
    # Everybody is allowed to get the last ip address of a particular client.

    return self.delegate.GetLastClientIPAddress(args, context=context)

  def ListClientCrashes(self, args, context=None):
    self.approval_checker.CheckClientAccess(context, str(args.client_id))

    return self.delegate.ListClientCrashes(args, context=context)

  def KillFleetspeak(
      self,
      args: api_client.ApiKillFleetspeakArgs,
      context: Optional[api_call_context.ApiCallContext] = None,
  ) -> api_client.ApiKillFleetspeakHandler:
    self.approval_checker.CheckClientAccess(context, str(args.client_id))
    return self.delegate.KillFleetspeak(args, context=context)

  def RestartFleetspeakGrrService(
      self,
      args: api_client.ApiRestartFleetspeakGrrServiceArgs,
      context: Optional[api_call_context.ApiCallContext] = None,
  ) -> api_client.ApiRestartFleetspeakGrrServiceHandler:
    self.approval_checker.CheckClientAccess(context, str(args.client_id))
    return self.delegate.RestartFleetspeakGrrService(args, context=context)

  def DeleteFleetspeakPendingMessages(
      self,
      args: api_client.ApiDeleteFleetspeakPendingMessagesArgs,
      context: Optional[api_call_context.ApiCallContext] = None,
  ) -> api_client.ApiDeleteFleetspeakPendingMessagesHandler:
    self.approval_checker.CheckClientAccess(context, str(args.client_id))
    return self.delegate.DeleteFleetspeakPendingMessages(args, context=context)

  def GetFleetspeakPendingMessages(
      self,
      args: api_client.ApiGetFleetspeakPendingMessagesArgs,
      context: Optional[api_call_context.ApiCallContext] = None,
  ) -> api_client.ApiGetFleetspeakPendingMessagesHandler:
    self.approval_checker.CheckClientAccess(context, str(args.client_id))
    return self.delegate.GetFleetspeakPendingMessages(args, context=context)

  def GetFleetspeakPendingMessageCount(
      self,
      args: api_client.ApiGetFleetspeakPendingMessageCountArgs,
      context: Optional[api_call_context.ApiCallContext] = None,
  ) -> api_client.ApiGetFleetspeakPendingMessageCountHandler:
    self.approval_checker.CheckClientAccess(context, str(args.client_id))
    return self.delegate.GetFleetspeakPendingMessageCount(args, context=context)

  # Virtual file system methods.
  # ============================
  #
  def ListFiles(self, args, context=None):
    self.approval_checker.CheckClientAccess(context, str(args.client_id))

    return self.delegate.ListFiles(args, context=context)

  def BrowseFilesystem(
      self,
      args: api_vfs.ApiBrowseFilesystemArgs,
      context: Optional[api_call_context.ApiCallContext] = None,
  ) -> api_vfs.ApiBrowseFilesystemHandler:
    self.approval_checker.CheckClientAccess(context, str(args.client_id))

    return self.delegate.BrowseFilesystem(args, context=context)

  def GetVfsFilesArchive(self, args, context=None):
    self.approval_checker.CheckClientAccess(context, str(args.client_id))

    return self.delegate.GetVfsFilesArchive(args, context=context)

  def GetFileDetails(self, args, context=None):
    self.approval_checker.CheckClientAccess(context, str(args.client_id))

    return self.delegate.GetFileDetails(args, context=context)

  def GetFileText(self, args, context=None):
    self.approval_checker.CheckClientAccess(context, str(args.client_id))

    return self.delegate.GetFileText(args, context=context)

  def GetFileBlob(self, args, context=None):
    self.approval_checker.CheckClientAccess(context, str(args.client_id))

    return self.delegate.GetFileBlob(args, context=context)

  def GetFileVersionTimes(self, args, context=None):
    self.approval_checker.CheckClientAccess(context, str(args.client_id))

    return self.delegate.GetFileVersionTimes(args, context=context)

  def GetFileDownloadCommand(self, args, context=None):
    self.approval_checker.CheckClientAccess(context, str(args.client_id))

    return self.delegate.GetFileDownloadCommand(args, context=context)

  def CreateVfsRefreshOperation(self, args, context=None):
    self.approval_checker.CheckClientAccess(context, str(args.client_id))

    return self.delegate.CreateVfsRefreshOperation(args, context=context)

  def GetVfsRefreshOperationState(self, args, context=None):
    # No ACL checks are required here, since the user can only check
    # operations started by themselves.

    return self.delegate.GetVfsRefreshOperationState(args, context=context)

  def GetVfsTimeline(self, args, context=None):
    self.approval_checker.CheckClientAccess(context, str(args.client_id))

    return self.delegate.GetVfsTimeline(args, context=context)

  def GetVfsTimelineAsCsv(self, args, context=None):
    self.approval_checker.CheckClientAccess(context, str(args.client_id))

    return self.delegate.GetVfsTimelineAsCsv(args, context=context)

  def UpdateVfsFileContent(self, args, context=None):
    self.approval_checker.CheckClientAccess(context, str(args.client_id))

    return self.delegate.UpdateVfsFileContent(args, context=context)

  def GetVfsFileContentUpdateState(self, args, context=None):
    # No ACL checks are required here, since the user can only check
    # operations started by themselves.

    return self.delegate.GetVfsFileContentUpdateState(args, context=context)

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
    self.approval_checker.CheckClientAccess(context, str(args.client_id))

    return self.delegate.ListFlows(args, context=context)

  def GetFlow(self, args, context=None):
    self._CheckFlowOrClientAccess(args, context)

    return self.delegate.GetFlow(args, context=context)

  def CreateFlow(self, args, context=None):
    self.approval_checker.CheckClientAccess(context, str(args.client_id))
    self.admin_access_checker.CheckIfCanStartFlow(
        context.username, args.flow.name or args.flow.runner_args.flow_name
    )

    return self.delegate.CreateFlow(args, context=context)

  def CancelFlow(self, args, context=None):
    self.approval_checker.CheckClientAccess(context, str(args.client_id))

    return self.delegate.CancelFlow(args, context=context)

  def ListFlowRequests(self, args, context=None):
    self.approval_checker.CheckClientAccess(context, str(args.client_id))

    return self.delegate.ListFlowRequests(args, context=context)

  def ListFlowResults(self, args, context=None):
    self._CheckFlowOrClientAccess(args, context)

    return self.delegate.ListFlowResults(args, context=context)

  def GetExportedFlowResults(self, args, context=None):
    self._CheckFlowOrClientAccess(args, context)

    return self.delegate.GetExportedFlowResults(args, context=context)

  def GetFlowResultsExportCommand(self, args, context=None):
    self._CheckFlowOrClientAccess(args, context)

    return self.delegate.GetFlowResultsExportCommand(args, context=context)

  def GetFlowFilesArchive(self, args, context=None):
    self._CheckFlowOrClientAccess(args, context)

    return self.delegate.GetFlowFilesArchive(args, context=context)

  def ListFlowOutputPlugins(self, args, context=None):
    self.approval_checker.CheckClientAccess(context, str(args.client_id))

    return self.delegate.ListFlowOutputPlugins(args, context=context)

  def ListFlowOutputPluginLogs(self, args, context=None):
    self.approval_checker.CheckClientAccess(context, str(args.client_id))

    return self.delegate.ListFlowOutputPluginLogs(args, context=context)

  def ListFlowOutputPluginErrors(self, args, context=None):
    self.approval_checker.CheckClientAccess(context, str(args.client_id))

    return self.delegate.ListFlowOutputPluginErrors(args, context=context)

  def ListFlowLogs(self, args, context=None):
    self.approval_checker.CheckClientAccess(context, str(args.client_id))

    return self.delegate.ListFlowLogs(args, context=context)

  def GetCollectedTimeline(self, args, context=None):
    try:
      flow = data_store.REL_DB.ReadFlowObject(
          str(args.client_id), str(args.flow_id)
      )
    except db.UnknownFlowError:
      raise api_call_handler_base.ResourceNotFoundError(
          "Flow with client id %s and flow id %s could not be found"
          % (args.client_id, args.flow_id)
      )

    if flow.flow_class_name != timeline.TimelineFlow.__name__:
      raise ValueError("Flow '{}' is not a timeline flow".format(flow.flow_id))

    # Check for client access if this flow was not scheduled as part of a hunt.
    if flow.parent_hunt_id != flow.flow_id:
      self.approval_checker.CheckClientAccess(context, str(args.client_id))

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

  def GetOsqueryResults(
      self,
      args: api_osquery.ApiGetOsqueryResultsArgs,
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
    self.approval_checker.CheckCronJobAccess(context, str(args.cron_job_id))

    return self.delegate.ForceRunCronJob(args, context=context)

  def ModifyCronJob(self, args, context=None):
    self.approval_checker.CheckCronJobAccess(context, str(args.cron_job_id))

    return self.delegate.ModifyCronJob(args, context=context)

  def ListCronJobRuns(self, args, context=None):
    # Everybody can list cron jobs' runs.

    return self.delegate.ListCronJobRuns(args, context=context)

  def GetCronJobRun(self, args, context=None):
    # Everybody can get cron runs.

    return self.delegate.GetCronJobRun(args, context=context)

  def DeleteCronJob(self, args, context=None):
    self.approval_checker.CheckCronJobAccess(context, str(args.cron_job_id))

    return self.delegate.DeleteCronJob(args, context=context)

  # Hunts methods.
  # =============
  #
  def ListHunts(self, args, context=None):
    # Everybody can list hunts.

    return self.delegate.ListHunts(args, context=context)

  def VerifyHuntAccess(self, args, context=None):
    self.approval_checker.CheckHuntAccess(context, str(args.hunt_id))

    return self.delegate.VerifyHuntAccess(args, context=context)

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

  def CountHuntResultsByType(self, args, context=None):
    # Everybody can look into hunt's results.

    return self.delegate.CountHuntResultsByType(args, context=context)

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

    return self.delegate.CreateHunt(args, context=context)

  def ModifyHunt(self, args, context=None):
    # Starting/stopping hunt or modifying its attributes requires an approval.
    self.approval_checker.CheckHuntAccess(context, str(args.hunt_id))

    return self.delegate.ModifyHunt(args, context=context)

  def _GetHuntObj(self, hunt_id, context=None) -> rdf_hunt_objects.Hunt:
    try:
      hunt_obj = data_store.REL_DB.ReadHuntObject(str(hunt_id))
      hunt_obj = mig_hunt_objects.ToRDFHunt(hunt_obj)
      return hunt_obj
    except db.UnknownHuntError:
      raise api_call_handler_base.ResourceNotFoundError(
          "Hunt with id %s could not be found" % hunt_id
      )

  def DeleteHunt(self, args, context=None):
    hunt_obj = self._GetHuntObj(args.hunt_id, context=context)

    # Hunt's creator is allowed to delete the hunt.
    if context.username != hunt_obj.creator:
      self.approval_checker.CheckHuntAccess(context, str(args.hunt_id))

    return self.delegate.DeleteHunt(args, context=context)

  def GetHuntFilesArchive(self, args, context=None):
    self.approval_checker.CheckHuntAccess(context, str(args.hunt_id))

    return self.delegate.GetHuntFilesArchive(args, context=context)

  def GetHuntFile(self, args, context=None):
    self.approval_checker.CheckHuntAccess(context, str(args.hunt_id))

    return self.delegate.GetHuntFile(args, context=context)

  def GetCollectedHuntTimelines(
      self,
      args: api_timeline.ApiGetCollectedHuntTimelinesArgs,
      context: Optional[api_call_context.ApiCallContext] = None,
  ) -> api_timeline.ApiGetCollectedHuntTimelinesHandler:
    # Everybody can export collected hunt timelines.
    return self.delegate.GetCollectedHuntTimelines(args, context=context)

  # Stats metrics methods.
  # =====================
  #
  def ListReports(self, args, context=None):
    # Everybody can list the reports.

    return self.delegate.ListReports(args, context=context)

  def GetReport(self, args, context=None):
    # Everybody can get report data.

    return self.delegate.GetReport(args, context=context)

  def IncrementCounterMetric(
      self,
      args: api_stats.ApiIncrementCounterMetricArgs,
      context: Optional[api_call_context.ApiCallContext] = None,
  ) -> api_stats.ApiIncrementCounterMetricHandler:
    # Everybody can increase metrics.

    return self.delegate.IncrementCounterMetric(args, context=context)

  # Approvals methods.
  # =================
  #
  def CreateClientApproval(self, args, context=None):
    # Everybody can create a user client approval.
    return api_user.ApiCreateClientApprovalHandler(self.approval_checker)

  def GetClientApproval(self, args, context=None):
    # Everybody can have access to everybody's client approvals, provided
    # they know: a client id, a username of the requester and an approval id.

    return api_user.ApiGetClientApprovalHandler(self.approval_checker)

  def GrantClientApproval(self, args, context=None):
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

  def ListClientApprovals(self, args, context=None):
    # Everybody can list their own user client approvals.

    return api_user.ApiListClientApprovalsHandler(self.approval_checker)

  def CreateHuntApproval(self, args, context=None):
    # Everybody can request a hunt approval.

    return api_user.ApiCreateHuntApprovalHandler(self.approval_checker)

  def GetHuntApproval(self, args, context=None):
    # Everybody can have access to everybody's hunts approvals, provided
    # they know: a hunt id, a username of the requester and an approval id.

    return api_user.ApiGetHuntApprovalHandler(self.approval_checker)

  def GrantHuntApproval(self, args, context=None):
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

  def ListHuntApprovals(self, args, context=None):
    # Everybody can list their own user hunt approvals.

    return api_user.ApiListHuntApprovalsHandler(self.approval_checker)

  def CreateCronJobApproval(self, args, context=None):
    # Everybody can request a cron job approval.

    return api_user.ApiCreateCronJobApprovalHandler(self.approval_checker)

  def GetCronJobApproval(self, args, context=None):
    # Everybody can have access to everybody's crons approvals, provided
    # they know: a cron job id, a username of the requester and an approval id.

    return api_user.ApiGetCronJobApprovalHandler(self.approval_checker)

  def GrantCronJobApproval(self, args, context=None):
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

  def ListCronJobApprovals(self, args, context=None):
    # Everybody can list their own user cron approvals.

    return api_user.ApiListCronJobApprovalsHandler(self.approval_checker)

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

    interface_traits = api_user_pb2.ApiGrrUserInterfaceTraits(
        cron_jobs_nav_item_enabled=True,
        create_cron_job_action_enabled=True,
        hunt_manager_nav_item_enabled=True,
        create_hunt_action_enabled=True,
        show_statistics_nav_item_enabled=True,
        server_load_nav_item_enabled=True,
        manage_binaries_nav_item_enabled=True,
        upload_binary_action_enabled=True,
        settings_nav_item_enabled=True,
        artifact_manager_nav_item_enabled=True,
        upload_artifact_action_enabled=True,
        search_clients_action_enabled=True,
        browse_virtual_file_system_nav_item_enabled=True,
        start_client_flow_nav_item_enabled=True,
        manage_client_flows_nav_item_enabled=True,
        modify_client_labels_action_enabled=True,
        hunt_approval_required=True,
    )
    try:
      # Without access to restricted flows, one can not launch Python hacks and
      # binaries. Hence, we don't display the "Manage binaries" page.
      self.admin_access_checker.CheckIfHasAdminAccess(context.username)
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
    self.admin_access_checker.CheckIfHasAdminAccess(context.username)

    return self.delegate.ListGrrBinaries(args, context=context)

  def GetGrrBinary(self, args, context=None):
    self.admin_access_checker.CheckIfHasAdminAccess(context.username)

    return self.delegate.GetGrrBinary(args, context=context)

  def GetGrrBinaryBlob(self, args, context=None):
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

  # pytype: enable=attribute-error


# TODO: Copy of migration function to avoid circular dependency.
def ToProtoApiCallRouterWithApprovalCheckParams(
    rdf: ApiCallRouterWithApprovalCheckParams,
) -> api_call_router_pb2.ApiCallRouterWithApprovalCheckParams:
  return rdf.AsPrimitiveProto()
