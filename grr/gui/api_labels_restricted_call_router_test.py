#!/usr/bin/env python
"""Tests for an ApiLabelsRestrictedCallRouter."""




from grr.gui import api_labels_restricted_call_router as api_router

from grr.gui.api_plugins import client as api_client
from grr.gui.api_plugins import flow as api_flow

from grr.lib import access_control
from grr.lib import aff4
from grr.lib import flags
from grr.lib import test_lib

from grr.lib.flows.general import processes


class ApiLabelsRestrictedCallRouterTest(test_lib.GRRBaseTest):
  """Tests for an ApiLabelsRestrictedCallRouter."""

  NON_ACLED_METHODS = [
      # User settings methods.
      "GetPendingUserNotificationsCount",
      "ListPendingUserNotifications",
      "DeletePendingUserNotification",
      "ListAndResetUserNotifications",
      "GetGrrUser",
      "UpdateGrrUser",
      "ListPendingGlobalNotifications",
      "DeletePendingGlobalNotification",

      # Config methods.
      "GetConfig",
      "GetConfigOption",

      # Reflection methods.
      "ListKbFields",
      "ListFlowDescriptors",
      "ListAff4AttributeDescriptors",
      "GetRDFValueDescriptor",
      "ListRDFValuesDescriptors",
      "ListOutputPluginDescriptors",
      "ListKnownEncodings",

      # Documentation methods.
      "GetDocs"
  ]

  def CheckMethod(self, method, **kwargs):
    if not method:
      raise ValueError("Method can't ne None.")

    annotations = api_router.ApiLabelsRestrictedCallRouter.GetAnnotatedMethods()
    args_type = annotations[method.__name__].args_type

    if args_type:
      args = args_type(**kwargs)
      self.checks[method.__name__] = args
    elif kwargs:
      raise ValueError("Method %s doesn't accept arguments." % method.__name__)
    else:
      self.checks[method.__name__] = None

  def RunChecks(self, router):
    result = {}

    for method_name, args in self.checks.items():
      try:
        handler = getattr(router, method_name)(args, token=self.token)
        result[method_name] = (True, handler)
      except (access_control.UnauthorizedAccess, NotImplementedError) as e:
        result[method_name] = (False, e)

    return result

  def setUp(self):
    super(ApiLabelsRestrictedCallRouterTest, self).setUp()

    client_urns = self.SetupClients(1)
    self.client_urn = client_urns[0]
    with aff4.FACTORY.Open(self.client_urn, mode="rw", token=self.token) as fd:
      fd.AddLabels("foo", owner="GRR")
    self.client_id = self.client_urn.Basename()

    self.hunt_id = "H:123456"

    c = api_router.ApiLabelsRestrictedCallRouter

    self.checks = {}

    # Artifacts methods.
    self.CheckMethod(c.ListArtifacts)
    self.CheckMethod(c.UploadArtifact)
    self.CheckMethod(c.DeleteArtifacts)

    # Clients methods
    self.CheckMethod(c.SearchClients)
    self.CheckMethod(c.GetClient, client_id=self.client_id)
    self.CheckMethod(c.GetClientVersionTimes, client_id=self.client_id)
    self.CheckMethod(c.InterrogateClient, client_id=self.client_id)
    self.CheckMethod(c.GetInterrogateOperationState)
    self.CheckMethod(c.GetLastClientIPAddress, client_id=self.client_id)

    # Virtual file system methods.
    self.CheckMethod(c.ListFiles, client_id=self.client_id)
    self.CheckMethod(c.GetFileDetails, client_id=self.client_id)
    self.CheckMethod(c.GetFileText, client_id=self.client_id)
    self.CheckMethod(c.GetFileBlob, client_id=self.client_id)
    self.CheckMethod(c.GetFileVersionTimes, client_id=self.client_id)
    self.CheckMethod(c.GetFileDownloadCommand, client_id=self.client_id)
    self.CheckMethod(c.CreateVfsRefreshOperation, client_id=self.client_id)
    self.CheckMethod(c.GetVfsRefreshOperationState)
    self.CheckMethod(c.GetVfsTimeline, client_id=self.client_id)
    self.CheckMethod(c.GetVfsTimelineAsCsv, client_id=self.client_id)

    # Clients labels methods.
    self.CheckMethod(c.ListClientsLabels)
    self.CheckMethod(c.AddClientsLabels, client_ids=[self.client_id])
    self.CheckMethod(c.RemoveClientsLabels, client_ids=[self.client_id])

    # Clients flows methods.
    self.CheckMethod(c.ListFlows, client_id=self.client_id)
    self.CheckMethod(c.GetFlow, client_id=self.client_id)
    self.CheckMethod(c.CreateFlow,
                     client_id=self.client_id,
                     flow=api_flow.ApiFlow(
                         name=processes.ListProcesses.__name__))
    self.CheckMethod(c.CancelFlow, client_id=self.client_id)
    self.CheckMethod(c.ListFlowResults, client_id=self.client_id)
    self.CheckMethod(c.GetFlowResultsExportCommand, client_id=self.client_id)
    self.CheckMethod(c.GetFlowFilesArchive, client_id=self.client_id)
    self.CheckMethod(c.ListFlowOutputPlugins, client_id=self.client_id)
    self.CheckMethod(c.ListFlowOutputPluginLogs, client_id=self.client_id)
    self.CheckMethod(c.ListFlowOutputPluginErrors, client_id=self.client_id)
    self.CheckMethod(c.ListFlowLogs, client_id=self.client_id)

    # Global flows methods.
    self.CheckMethod(c.CreateGlobalFlow)

    # Cron jobs methods.
    self.CheckMethod(c.ListCronJobs)
    self.CheckMethod(c.CreateCronJob)
    self.CheckMethod(c.DeleteCronJob)

    # Hunts methods.
    self.CheckMethod(c.ListHunts)
    self.CheckMethod(c.GetHunt, hunt_id=self.hunt_id)
    self.CheckMethod(c.ListHuntErrors, hunt_id=self.hunt_id)
    self.CheckMethod(c.ListHuntLogs, hunt_id=self.hunt_id)
    self.CheckMethod(c.ListHuntResults, hunt_id=self.hunt_id)
    self.CheckMethod(c.GetHuntResultsExportCommand, hunt_id=self.hunt_id)
    self.CheckMethod(c.ListHuntOutputPlugins, hunt_id=self.hunt_id)
    self.CheckMethod(c.ListHuntOutputPluginLogs, hunt_id=self.hunt_id)
    self.CheckMethod(c.ListHuntOutputPluginErrors, hunt_id=self.hunt_id)
    self.CheckMethod(c.ListHuntCrashes, hunt_id=self.hunt_id)
    self.CheckMethod(c.GetHuntClientCompletionStats, hunt_id=self.hunt_id)
    self.CheckMethod(c.GetHuntStats, hunt_id=self.hunt_id)
    self.CheckMethod(c.ListHuntClients, hunt_id=self.hunt_id)
    self.CheckMethod(c.GetHuntContext, hunt_id=self.hunt_id)
    self.CheckMethod(c.CreateHunt)
    self.CheckMethod(c.GetHuntFilesArchive, hunt_id=self.hunt_id)
    self.CheckMethod(c.GetHuntFile, hunt_id=self.hunt_id)

    # Stats metrics methods.
    self.CheckMethod(c.ListStatsStoreMetricsMetadata)
    self.CheckMethod(c.GetStatsStoreMetric)

    # Approvals methods.
    self.CheckMethod(c.CreateUserClientApproval, client_id=self.client_id)
    self.CheckMethod(c.GetUserClientApproval, client_id=self.client_id)
    self.CheckMethod(c.ListUserClientApprovals, client_id=self.client_id)
    self.CheckMethod(c.ListUserHuntApprovals)
    self.CheckMethod(c.ListUserCronApprovals)

    # User settings methods.
    self.CheckMethod(c.GetPendingUserNotificationsCount)
    self.CheckMethod(c.ListPendingUserNotifications)
    self.CheckMethod(c.DeletePendingUserNotification)
    self.CheckMethod(c.ListAndResetUserNotifications)
    self.CheckMethod(c.GetGrrUser)
    self.CheckMethod(c.UpdateGrrUser)
    self.CheckMethod(c.ListPendingGlobalNotifications)
    self.CheckMethod(c.DeletePendingGlobalNotification)

    # Config methods.
    self.CheckMethod(c.GetConfig)
    self.CheckMethod(c.GetConfigOption)

    # Reflection methods.
    self.CheckMethod(c.ListKbFields)
    self.CheckMethod(c.ListFlowDescriptors)
    self.CheckMethod(c.ListAff4AttributeDescriptors)
    self.CheckMethod(c.GetRDFValueDescriptor)
    self.CheckMethod(c.ListRDFValuesDescriptors)
    self.CheckMethod(c.ListOutputPluginDescriptors)
    self.CheckMethod(c.ListKnownEncodings)

    # Documentation methods.
    self.CheckMethod(c.GetDocs)

    # Robot methods.
    self.CheckMethod(c.StartRobotGetFilesOperation)
    self.CheckMethod(c.GetRobotGetFilesOperationState)

    non_checked_methods = (
        set(self.checks.keys()) - set(c.GetAnnotatedMethods().keys()))
    if non_checked_methods:
      raise RuntimeError("Not all methods are covered with CheckMethod() "
                         "checks: " + ", ".join(non_checked_methods))

  def CheckOnlyFollowingMethodsArePermitted(self, router, method_names):
    result = self.RunChecks(router)
    for method_name, (status, _) in result.items():
      if method_name in method_names:
        self.assertTrue(status, "%s is permitted" % method_name)
      else:
        self.assertFalse(status, "%s is not permitted" % method_name)

  def testReturnsCustomHandlerForSearchClients(self):
    router = api_router.ApiLabelsRestrictedCallRouter()
    handler = router.SearchClients(None, token=self.token)
    self.assertTrue(isinstance(
        handler, api_client.ApiLabelsRestrictedSearchClientsHandler))

  # Check router with vfs/flows access turned off.
  def testWithoutFlowsWithoutVfsAndUnapprovedClientWithoutLabels(self):
    router = api_router.ApiLabelsRestrictedCallRouter()

    self.CheckOnlyFollowingMethodsArePermitted(router, [
        "SearchClients",
        "ListUserClientApprovals"
    ] + self.NON_ACLED_METHODS)  # pyformat: disable

  def testWithoutFlowsWithoutVfsAndUnapprovedClientWithWrongLabelName(self):
    router = api_router.ApiLabelsRestrictedCallRouter(labels_whitelist=["bar"])

    self.CheckOnlyFollowingMethodsArePermitted(router, [
        "SearchClients",
        "ListUserClientApprovals"
    ] + self.NON_ACLED_METHODS)  # pyformat: disable

  def testWithoutFlowsWithoutVfsAndUnapprovedClientWithWrongLabelOwner(self):
    router = api_router.ApiLabelsRestrictedCallRouter(
        labels_whitelist=["foo"],
        labels_owners_whitelist=["somebody"])

    self.CheckOnlyFollowingMethodsArePermitted(router, [
        "SearchClients",
        "ListUserClientApprovals"
    ] + self.NON_ACLED_METHODS)  # pyformat: disable

  def testWithoutFlowsWithoutVfsAndSingleProperlyLabeledUnapprovedClient(self):
    router = api_router.ApiLabelsRestrictedCallRouter(labels_whitelist=["foo"])
    self.CheckOnlyFollowingMethodsArePermitted(router, [
        "SearchClients",
        "ListUserClientApprovals",
        "GetClient",
        "CreateUserClientApproval",
        "GetUserClientApproval"
    ] + self.NON_ACLED_METHODS)  # pyformat: disable

  def testWithoutFlowsWithoutVfsAndSingleProperlyLabeledApprovedClient(self):
    self.RequestAndGrantClientApproval(self.client_urn, token=self.token)

    router = api_router.ApiLabelsRestrictedCallRouter(labels_whitelist=["foo"])
    self.CheckOnlyFollowingMethodsArePermitted(router, [
        "SearchClients",
        "ListUserClientApprovals",
        "GetClient",
        "CreateUserClientApproval",
        "GetUserClientApproval"
    ] + self.NON_ACLED_METHODS)  # pyformat: disable

  # Check router with vfs access turned on.
  def testWithoutFlowsWithVfsAndSingleMislabeledUnapprovedClient(self):
    router = api_router.ApiLabelsRestrictedCallRouter(allow_vfs_access=True)

    self.CheckOnlyFollowingMethodsArePermitted(router, [
        "SearchClients",
        "ListUserClientApprovals",

        # This operation is always allowed as it doesn't depend on a client
        # id.
        "GetVfsRefreshOperationState"
    ] + self.NON_ACLED_METHODS)  # pyformat: disable

  def testWithoutFlowsWithVfsAndSingleProperlyLabeledUnapprovedClient(self):
    router = api_router.ApiLabelsRestrictedCallRouter(labels_whitelist=["foo"],
                                                      allow_vfs_access=True)

    self.CheckOnlyFollowingMethodsArePermitted(router, [
        "SearchClients",
        "ListUserClientApprovals",
        "GetClient",
        "CreateUserClientApproval",
        "GetUserClientApproval",

        # This operation is always allowed as it doesn't depend on a client
        # id.
        "GetVfsRefreshOperationState"
    ] + self.NON_ACLED_METHODS)  # pyformat: disable

  def testWithoutFlowsWithVfsAndSingleProperlyLabeledAndApprovedClient(self):
    self.RequestAndGrantClientApproval(self.client_urn, token=self.token)

    router = api_router.ApiLabelsRestrictedCallRouter(labels_whitelist=["foo"],
                                                      allow_vfs_access=True)

    self.CheckOnlyFollowingMethodsArePermitted(router, [
        # Client methods.
        "SearchClients",
        "ListUserClientApprovals",
        "GetClient",
        "CreateUserClientApproval",
        "GetUserClientApproval",

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
    router = api_router.ApiLabelsRestrictedCallRouter(allow_flows=True)

    self.CheckOnlyFollowingMethodsArePermitted(router, [
        "SearchClients",
        "ListUserClientApprovals",
    ] + self.NON_ACLED_METHODS)  # pyformat: disable

  def testWithFlowsWithoutVfsAndSingleProperlyLabeledUnapprovedClient(self):
    router = api_router.ApiLabelsRestrictedCallRouter(labels_whitelist=["foo"],
                                                      allow_flows=True)

    self.CheckOnlyFollowingMethodsArePermitted(router, [
        "SearchClients",
        "ListUserClientApprovals",
        "GetClient",
        "CreateUserClientApproval",
        "GetUserClientApproval",
    ] + self.NON_ACLED_METHODS)  # pyformat: disable

  def testWithFlowsWithoutVfsAndSingleProperlyLabeledAndApprovedClient(self):
    self.RequestAndGrantClientApproval(self.client_urn, token=self.token)

    router = api_router.ApiLabelsRestrictedCallRouter(labels_whitelist=["foo"],
                                                      allow_flows=True)

    self.CheckOnlyFollowingMethodsArePermitted(router, [
        # Clients methods.
        "SearchClients",
        "ListUserClientApprovals",
        "GetClient",
        "CreateUserClientApproval",
        "GetUserClientApproval",

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
  flags.StartMain(main)
