#!/usr/bin/env python
"""Tests for an ApiLabelsRestrictedCallRouter."""

from absl import app

from grr_response_proto import api_call_router_pb2
from grr_response_proto.api import client_pb2 as api_client_pb2
from grr_response_proto.api import flow_pb2 as api_flow_pb2
from grr_response_proto.api import hunt_pb2 as api_hunt_pb2
from grr_response_proto.api import user_pb2 as api_user_pb2
from grr_response_proto.api import vfs_pb2 as api_vfs_pb2
from grr_response_server import access_control
from grr_response_server import data_store
from grr_response_server.flows.general import processes
from grr_response_server.gui import api_call_context
from grr_response_server.gui import api_labels_restricted_call_router as api_router
from grr_response_server.gui.api_plugins import client as api_client
from grr.test_lib import acl_test_lib
from grr.test_lib import test_lib


class CheckClientLabelsTest(test_lib.GRRBaseTest):
  """Tests for CheckClientLabels function."""

  def setUp(self):
    super().setUp()
    self.client_id = self.SetupClient(0)

    self.allow_labels = ["foo"]

    data_store.REL_DB.WriteGRRUser("GRR")
    self.allow_labels_owners = ["GRR"]

  def _AddLabel(self, name, owner=None):
    data_store.REL_DB.AddClientLabels(self.client_id, owner, [name])

  def testDoesNotRaiseWhenLabelMatches(self):
    self._AddLabel("foo", owner="GRR")

    api_router.CheckClientLabels(
        self.client_id,
        allow_labels=self.allow_labels,
        allow_labels_owners=self.allow_labels_owners,
    )

  def testDoesNotRaiseWhenLabelMatchesAmongManyLabels(self):
    self._AddLabel("bar", owner="GRR")
    self._AddLabel("foo", owner="GRR")
    self._AddLabel("zig", owner="GRR")
    self._AddLabel("zag", owner="GRR")

    api_router.CheckClientLabels(
        self.client_id,
        allow_labels=self.allow_labels,
        allow_labels_owners=self.allow_labels_owners,
    )

  def testRaisesWhenLabelDoesNotMatch(self):
    self._AddLabel("bar", owner="GRR")

    with self.assertRaises(access_control.UnauthorizedAccess):
      api_router.CheckClientLabels(
          self.client_id,
          allow_labels=self.allow_labels,
          allow_labels_owners=self.allow_labels_owners,
      )

  def testRaisesWhenLabelDoesNotMatchAmongManyLabels(self):
    self._AddLabel("foo1", owner="GRR")
    self._AddLabel("2foo", owner="GRR")
    self._AddLabel("1foo2", owner="GRR")
    self._AddLabel("bar", owner="GRR")

    with self.assertRaises(access_control.UnauthorizedAccess):
      api_router.CheckClientLabels(
          self.client_id,
          allow_labels=self.allow_labels,
          allow_labels_owners=self.allow_labels_owners,
      )

  def testRaisesIfOwnerDoesNotMatch(self):
    data_store.REL_DB.WriteGRRUser("GRRother")
    self._AddLabel("foo", owner="GRRother")

    with self.assertRaises(access_control.UnauthorizedAccess):
      api_router.CheckClientLabels(
          self.client_id,
          allow_labels=self.allow_labels,
          allow_labels_owners=self.allow_labels_owners,
      )


class ApiLabelsRestrictedCallRouterTest(
    test_lib.GRRBaseTest, acl_test_lib.AclTestMixin
):
  """Tests for an ApiLabelsRestrictedCallRouter."""

  NON_ACLED_METHODS = [
      # User settings methods.
      "GetPendingUserNotificationsCount",
      "ListPendingUserNotifications",
      "DeletePendingUserNotification",
      "ListAndResetUserNotifications",
      "GetGrrUser",
      "UpdateGrrUser",
      # Config methods.
      "GetConfig",
      "GetConfigOption",
      # Reflection methods.
      "ListKbFields",
      "ListFlowDescriptors",
      "ListOutputPluginDescriptors",
      "ListApiMethods",
  ]

  def CheckMethod(self, method, proto_args=None):
    if not method:
      raise ValueError("Method can't ne None.")

    annotations = api_router.ApiLabelsRestrictedCallRouter.GetAnnotatedMethods()
    proto_args_type = annotations[method.__name__].proto_args_type

    if proto_args_type:
      self.checks[method.__name__] = proto_args
    else:
      self.checks[method.__name__] = None

  def RunChecks(self, router):
    result = {}

    for method_name, args in self.checks.items():
      try:
        handler = getattr(router, method_name)(args, context=self.context)
        result[method_name] = (True, handler)
      except (access_control.UnauthorizedAccess, NotImplementedError) as e:
        result[method_name] = (False, e)

    return result

  def setUp(self):
    super().setUp()

    self.client_id = self.SetupClient(0)

    data_store.REL_DB.WriteGRRUser("GRR")
    data_store.REL_DB.AddClientLabels(self.client_id, "GRR", ["foo"])

    self.hunt_id = "H:123456"
    self.context = api_call_context.ApiCallContext("test")

    c = api_router.ApiLabelsRestrictedCallRouter

    self.checks = {}

    # Artifacts methods.
    self.CheckMethod(c.ListArtifacts)
    self.CheckMethod(c.UploadArtifact)
    self.CheckMethod(c.DeleteArtifacts)

    # Clients methods
    self.CheckMethod(c.SearchClients)
    self.CheckMethod(
        c.GetClient, api_client_pb2.ApiGetClientArgs(client_id=self.client_id)
    )
    self.CheckMethod(
        c.GetClientVersions,
        api_client_pb2.ApiGetClientVersionsArgs(client_id=self.client_id),
    )
    self.CheckMethod(
        c.GetClientVersionTimes,
        api_client_pb2.ApiGetClientVersionTimesArgs(client_id=self.client_id),
    )
    self.CheckMethod(
        c.InterrogateClient,
        api_client_pb2.ApiInterrogateClientArgs(client_id=self.client_id),
    )
    self.CheckMethod(
        c.GetLastClientIPAddress,
        api_client_pb2.ApiGetLastClientIPAddressArgs(client_id=self.client_id),
    )

    # Virtual file system methods.
    self.CheckMethod(
        c.ListFiles, api_vfs_pb2.ApiListFilesArgs(client_id=self.client_id)
    )
    self.CheckMethod(
        c.GetFileDetails,
        api_vfs_pb2.ApiGetFileDetailsArgs(client_id=self.client_id),
    )
    self.CheckMethod(
        c.GetFileText, api_vfs_pb2.ApiGetFileTextArgs(client_id=self.client_id)
    )
    self.CheckMethod(
        c.GetFileBlob, api_vfs_pb2.ApiGetFileBlobArgs(client_id=self.client_id)
    )
    self.CheckMethod(
        c.GetFileVersionTimes,
        api_vfs_pb2.ApiGetFileVersionTimesArgs(client_id=self.client_id),
    )
    self.CheckMethod(
        c.GetFileDownloadCommand,
        api_vfs_pb2.ApiGetFileDownloadCommandArgs(client_id=self.client_id),
    )
    self.CheckMethod(
        c.CreateVfsRefreshOperation,
        api_vfs_pb2.ApiCreateVfsRefreshOperationArgs(client_id=self.client_id),
    )
    self.CheckMethod(c.GetVfsRefreshOperationState)
    self.CheckMethod(
        c.GetVfsTimeline,
        api_vfs_pb2.ApiGetVfsTimelineArgs(client_id=self.client_id),
    )
    self.CheckMethod(
        c.GetVfsTimelineAsCsv,
        api_vfs_pb2.ApiGetVfsTimelineAsCsvArgs(client_id=self.client_id),
    )

    # Clients labels methods.
    self.CheckMethod(c.ListClientsLabels)
    self.CheckMethod(
        c.AddClientsLabels,
        api_client_pb2.ApiAddClientsLabelsArgs(client_ids=[self.client_id]),
    )
    self.CheckMethod(
        c.RemoveClientsLabels,
        api_client_pb2.ApiRemoveClientsLabelsArgs(client_ids=[self.client_id]),
    )

    # Clients flows methods.
    self.CheckMethod(
        c.ListFlows, api_flow_pb2.ApiListFlowsArgs(client_id=self.client_id)
    )
    self.CheckMethod(
        c.GetFlow,
        proto_args=api_flow_pb2.ApiGetFlowArgs(client_id=self.client_id),
    )
    self.CheckMethod(
        c.CreateFlow,
        proto_args=api_flow_pb2.ApiCreateFlowArgs(
            client_id=self.client_id,
            flow=api_flow_pb2.ApiFlow(name=processes.ListProcesses.__name__),
        ),
    )
    self.CheckMethod(
        c.CancelFlow, api_flow_pb2.ApiCancelFlowArgs(client_id=self.client_id)
    )
    self.CheckMethod(
        c.ListFlowResults,
        proto_args=api_flow_pb2.ApiListFlowResultsArgs(
            client_id=self.client_id
        ),
    )
    self.CheckMethod(
        c.GetFlowResultsExportCommand,
        api_flow_pb2.ApiGetFlowResultsExportCommandArgs(
            client_id=self.client_id
        ),
    )
    self.CheckMethod(
        c.GetFlowFilesArchive,
        api_flow_pb2.ApiGetFlowFilesArchiveArgs(client_id=self.client_id),
    )
    self.CheckMethod(
        c.ListFlowOutputPlugins,
        api_flow_pb2.ApiListFlowOutputPluginsArgs(client_id=self.client_id),
    )
    self.CheckMethod(
        c.ListFlowOutputPluginLogs,
        api_flow_pb2.ApiListFlowOutputPluginLogsArgs(client_id=self.client_id),
    )
    self.CheckMethod(
        c.ListFlowOutputPluginErrors,
        api_flow_pb2.ApiListFlowOutputPluginErrorsArgs(
            client_id=self.client_id
        ),
    )
    self.CheckMethod(
        c.ListFlowLogs,
        api_flow_pb2.ApiListFlowLogsArgs(client_id=self.client_id),
    )

    # Cron jobs methods.
    self.CheckMethod(c.ListCronJobs)
    self.CheckMethod(c.CreateCronJob)
    self.CheckMethod(c.DeleteCronJob)

    # Hunts methods.
    self.CheckMethod(c.ListHunts)
    self.CheckMethod(
        c.GetHunt, api_hunt_pb2.ApiGetHuntArgs(hunt_id=self.hunt_id)
    )
    self.CheckMethod(
        c.ListHuntErrors,
        api_hunt_pb2.ApiListHuntErrorsArgs(hunt_id=self.hunt_id),
    )
    self.CheckMethod(
        c.ListHuntLogs, api_hunt_pb2.ApiListHuntLogsArgs(hunt_id=self.hunt_id)
    )
    self.CheckMethod(
        c.ListHuntResults,
        api_hunt_pb2.ApiListHuntResultsArgs(hunt_id=self.hunt_id),
    )
    self.CheckMethod(
        c.GetHuntResultsExportCommand,
        api_hunt_pb2.ApiGetHuntResultsExportCommandArgs(hunt_id=self.hunt_id),
    )
    self.CheckMethod(
        c.ListHuntOutputPlugins,
        api_hunt_pb2.ApiListHuntOutputPluginsArgs(hunt_id=self.hunt_id),
    )
    self.CheckMethod(
        c.ListHuntOutputPluginLogs,
        api_hunt_pb2.ApiListHuntOutputPluginLogsArgs(hunt_id=self.hunt_id),
    )
    self.CheckMethod(
        c.ListHuntOutputPluginErrors,
        api_hunt_pb2.ApiListHuntOutputPluginErrorsArgs(hunt_id=self.hunt_id),
    )
    self.CheckMethod(
        c.ListHuntCrashes,
        api_hunt_pb2.ApiListHuntCrashesArgs(hunt_id=self.hunt_id),
    )
    self.CheckMethod(
        c.GetHuntClientCompletionStats,
        api_hunt_pb2.ApiGetHuntClientCompletionStatsArgs(hunt_id=self.hunt_id),
    )
    self.CheckMethod(
        c.GetHuntStats, api_hunt_pb2.ApiGetHuntStatsArgs(hunt_id=self.hunt_id)
    )
    self.CheckMethod(
        c.ListHuntClients,
        api_hunt_pb2.ApiListHuntClientsArgs(hunt_id=self.hunt_id),
    )
    self.CheckMethod(
        c.GetHuntContext,
        api_hunt_pb2.ApiGetHuntContextArgs(hunt_id=self.hunt_id),
    )
    self.CheckMethod(c.CreateHunt)
    self.CheckMethod(
        c.GetHuntFilesArchive,
        api_hunt_pb2.ApiGetHuntFilesArchiveArgs(hunt_id=self.hunt_id),
    )
    self.CheckMethod(
        c.GetHuntFile, api_hunt_pb2.ApiGetHuntFileArgs(hunt_id=self.hunt_id)
    )

    # Approvals methods.
    self.CheckMethod(
        c.CreateClientApproval,
        api_user_pb2.ApiCreateClientApprovalArgs(client_id=self.client_id),
    )
    self.CheckMethod(
        c.GetClientApproval,
        api_user_pb2.ApiGetClientApprovalArgs(client_id=self.client_id),
    )
    self.CheckMethod(
        c.ListClientApprovals,
        api_user_pb2.ApiListClientApprovalsArgs(client_id=self.client_id),
    )
    self.CheckMethod(c.ListHuntApprovals)
    self.CheckMethod(c.ListCronJobApprovals)

    # User settings methods.
    self.CheckMethod(c.GetPendingUserNotificationsCount)
    self.CheckMethod(c.ListPendingUserNotifications)
    self.CheckMethod(c.DeletePendingUserNotification)
    self.CheckMethod(c.ListAndResetUserNotifications)
    self.CheckMethod(c.GetGrrUser)
    self.CheckMethod(c.UpdateGrrUser)

    # Config methods.
    self.CheckMethod(c.GetConfig)
    self.CheckMethod(c.GetConfigOption)

    # Reflection methods.
    self.CheckMethod(c.ListKbFields)
    self.CheckMethod(c.ListFlowDescriptors)
    self.CheckMethod(c.ListOutputPluginDescriptors)
    self.CheckMethod(c.ListApiMethods)

    non_checked_methods = set(self.checks.keys()) - set(
        c.GetAnnotatedMethods().keys()
    )
    if non_checked_methods:
      raise RuntimeError(
          "Not all methods are covered with CheckMethod() checks: "
          + ", ".join(non_checked_methods)
      )

  def CheckOnlyFollowingMethodsArePermitted(self, router, method_names):
    result = self.RunChecks(router)
    for method_name, (status, _) in result.items():
      if method_name in method_names:
        self.assertTrue(
            status, "%s must be permitted, but it's not" % method_name
        )
      else:
        self.assertFalse(
            status, "%s must not be permitted, but it is" % method_name
        )

  def testReturnsCustomHandlerForSearchClients(self):
    router = api_router.ApiLabelsRestrictedCallRouter()
    handler = router.SearchClients(None, context=self.context)
    self.assertIsInstance(
        handler, api_client.ApiLabelsRestrictedSearchClientsHandler
    )

  # Check router with vfs/flows access turned off.
  def testWithoutFlowsWithoutVfsAndUnapprovedClientWithoutLabels(self):
    router = api_router.ApiLabelsRestrictedCallRouter()

    self.CheckOnlyFollowingMethodsArePermitted(router, [
        "SearchClients",
        "ListClientApprovals"
    ] + self.NON_ACLED_METHODS)  # pyformat: disable

  def testWithoutFlowsWithoutVfsAndUnapprovedClientWithWrongLabelName(self):
    params = api_call_router_pb2.ApiLabelsRestrictedCallRouterParams(
        allow_labels=["bar"]
    )
    router = api_router.ApiLabelsRestrictedCallRouter(params=params)

    self.CheckOnlyFollowingMethodsArePermitted(router, [
        "SearchClients",
        "ListClientApprovals"
    ] + self.NON_ACLED_METHODS)  # pyformat: disable

  def testWithoutFlowsWithoutVfsAndUnapprovedClientWithWrongLabelOwner(self):
    params = api_call_router_pb2.ApiLabelsRestrictedCallRouterParams(
        allow_labels=["foo"], allow_labels_owners=["somebody"]
    )
    router = api_router.ApiLabelsRestrictedCallRouter(params=params)

    self.CheckOnlyFollowingMethodsArePermitted(router, [
        "SearchClients",
        "ListClientApprovals"
    ] + self.NON_ACLED_METHODS)  # pyformat: disable

  def testWithoutFlowsWithoutVfsAndSingleProperlyLabeledUnapprovedClient(self):
    params = api_call_router_pb2.ApiLabelsRestrictedCallRouterParams(
        allow_labels=["foo"]
    )
    router = api_router.ApiLabelsRestrictedCallRouter(params=params)

    self.CheckOnlyFollowingMethodsArePermitted(router, [
        "SearchClients",
        "ListClientApprovals",
        "GetClient",
        "GetClientVersions",
        "GetClientVersionTimes",
        "GetClientSnapshots",
        "GetClientStartupInfos",
        "CreateClientApproval",
        "GetClientApproval"
    ] + self.NON_ACLED_METHODS)  # pyformat: disable

  def testWithoutFlowsWithoutVfsAndSingleProperlyLabeledApprovedClient(self):
    self.RequestAndGrantClientApproval(self.client_id)

    params = api_call_router_pb2.ApiLabelsRestrictedCallRouterParams(
        allow_labels=["foo"]
    )
    router = api_router.ApiLabelsRestrictedCallRouter(params=params)
    self.CheckOnlyFollowingMethodsArePermitted(router, [
        "SearchClients",
        "ListClientApprovals",
        "GetClient",
        "GetClientVersions",
        "GetClientVersionTimes",
        "GetClientSnapshots",
        "GetClientStartupInfos",
        "CreateClientApproval",
        "GetClientApproval"
    ] + self.NON_ACLED_METHODS)  # pyformat: disable

  # Check router with vfs access turned on.
  def testWithoutFlowsWithVfsAndSingleMislabeledUnapprovedClient(self):
    params = api_call_router_pb2.ApiLabelsRestrictedCallRouterParams(
        allow_vfs_access=True
    )
    router = api_router.ApiLabelsRestrictedCallRouter(params=params)

    self.CheckOnlyFollowingMethodsArePermitted(router, [
        "SearchClients",
        "ListClientApprovals",

        # This operation is always allowed as it doesn't depend on a client
        # id.
        "GetVfsRefreshOperationState"
    ] + self.NON_ACLED_METHODS)  # pyformat: disable

  def testWithoutFlowsWithVfsAndSingleProperlyLabeledUnapprovedClient(self):
    params = api_call_router_pb2.ApiLabelsRestrictedCallRouterParams(
        allow_labels=["foo"], allow_vfs_access=True
    )
    router = api_router.ApiLabelsRestrictedCallRouter(params=params)

    self.CheckOnlyFollowingMethodsArePermitted(router, [
        "SearchClients",
        "ListClientApprovals",
        "GetClient",
        "GetClientVersions",
        "GetClientVersionTimes",
        "CreateClientApproval",
        "GetClientApproval",

        # This operation is always allowed as it doesn't depend on a client
        # id.
        "GetVfsRefreshOperationState"
    ] + self.NON_ACLED_METHODS)  # pyformat: disable

  def testWithoutFlowsWithVfsAndSingleProperlyLabeledAndApprovedClient(self):
    self.RequestAndGrantClientApproval(self.client_id)

    params = api_call_router_pb2.ApiLabelsRestrictedCallRouterParams(
        allow_labels=["foo"], allow_vfs_access=True
    )
    router = api_router.ApiLabelsRestrictedCallRouter(params=params)

    self.CheckOnlyFollowingMethodsArePermitted(router, [
        # Client methods.
        "SearchClients",
        "ListClientApprovals",
        "GetClient",
        "GetClientVersions",
        "GetClientVersionTimes",
        "CreateClientApproval",
        "GetClientApproval",

        # VFS methods
        "ListFiles",
        "GetFileDetails",
        "GetFileText",
        "GetFileBlob",
        "GetFileVersionTimes",
        "GetFileDownloadCommand",
        "CreateVfsRefreshOperation",
        "GetVfsRefreshOperationState",
        "GetVfsTimeline",
        "GetVfsTimelineAsCsv"
    ] + self.NON_ACLED_METHODS)  # pyformat: disable

  # Check router with flows access turned on.
  def testWithFlowsWithoutVfsAndSingleMislabeledUnapprovedClient(self):
    params = api_call_router_pb2.ApiLabelsRestrictedCallRouterParams(
        allow_flows_access=True
    )
    router = api_router.ApiLabelsRestrictedCallRouter(params=params)

    self.CheckOnlyFollowingMethodsArePermitted(router, [
        "SearchClients",
        "ListClientApprovals",
    ] + self.NON_ACLED_METHODS)  # pyformat: disable

  def testWithFlowsWithoutVfsAndSingleProperlyLabeledUnapprovedClient(self):
    params = api_call_router_pb2.ApiLabelsRestrictedCallRouterParams(
        allow_labels=["foo"], allow_flows_access=True
    )
    router = api_router.ApiLabelsRestrictedCallRouter(params=params)

    self.CheckOnlyFollowingMethodsArePermitted(router, [
        "SearchClients",
        "ListClientApprovals",
        "GetClient",
        "GetClientVersions",
        "GetClientVersionTimes",
        "CreateClientApproval",
        "GetClientApproval",
    ] + self.NON_ACLED_METHODS)  # pyformat: disable

  def testWithFlowsWithoutVfsAndSingleProperlyLabeledAndApprovedClient(self):
    self.RequestAndGrantClientApproval(self.client_id)

    params = api_call_router_pb2.ApiLabelsRestrictedCallRouterParams(
        allow_labels=["foo"], allow_flows_access=True
    )
    router = api_router.ApiLabelsRestrictedCallRouter(params=params)

    self.CheckOnlyFollowingMethodsArePermitted(router, [
        # Clients methods.
        "SearchClients",
        "ListClientApprovals",
        "GetClient",
        "GetClientVersions",
        "GetClientVersionTimes",
        "CreateClientApproval",
        "GetClientApproval",

        # Flows methods.
        "ListFlows",
        "GetFlow",
        "CreateFlow",
        "CancelFlow",
        "ListFlowResults",
        "GetFlowResultsExportCommand",
        "GetFlowFilesArchive",
        "ListFlowOutputPlugins",
        "ListFlowOutputPluginLogs",
        "ListFlowOutputPluginErrors",
        "ListFlowLogs",
    ] + self.NON_ACLED_METHODS)  # pyformat: disable


def main(argv):
  test_lib.main(argv)


if __name__ == "__main__":
  app.run(main)
