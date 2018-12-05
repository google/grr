#!/usr/bin/env python
"""Tests for ApiCallRobotRouter."""
from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals


from future.utils import iterkeys

from grr_response_core.lib import flags

from grr_response_core.lib.rdfvalues import artifacts as rdf_artifacts
from grr_response_core.lib.rdfvalues import file_finder as rdf_file_finder
from grr_response_server import access_control
from grr_response_server import flow
from grr_response_server.flows.general import collectors
from grr_response_server.flows.general import file_finder
from grr_response_server.gui import api_call_robot_router as rr
from grr_response_server.gui.api_plugins import flow as api_flow

from grr.test_lib import flow_test_lib
from grr.test_lib import test_lib


class AnotherFileFinder(flow.GRRFlow):
  args_type = rdf_file_finder.FileFinderArgs


class AnotherArtifactCollector(flow.GRRFlow):
  args_type = rdf_artifacts.ArtifactCollectorFlowArgs


class ApiRobotCreateFlowHandlerTest(test_lib.GRRBaseTest):
  """Tests for ApiRobotCreateFlowHandler."""

  def setUp(self):
    super(ApiRobotCreateFlowHandlerTest, self).setUp()
    self.client_id = self.SetupClient(0)

  def testPassesFlowArgsThroughIfNoOverridesSpecified(self):
    h = rr.ApiRobotCreateFlowHandler(robot_id="foo")

    args = api_flow.ApiCreateFlowArgs(client_id=self.client_id.Basename())
    args.flow.name = file_finder.FileFinder.__name__
    args.flow.args = rdf_file_finder.FileFinderArgs(paths=["foo"])

    f = h.Handle(args=args, token=self.token)
    self.assertEqual(f.args.paths, ["foo"])

  def testOverridesFlowArgsThroughIfOverridesSpecified(self):
    override_flow_args = rdf_file_finder.FileFinderArgs(paths=["bar"])
    h = rr.ApiRobotCreateFlowHandler(
        robot_id="foo", override_flow_args=override_flow_args)

    args = api_flow.ApiCreateFlowArgs(client_id=self.client_id.Basename())
    args.flow.name = file_finder.FileFinder.__name__
    args.flow.args = rdf_file_finder.FileFinderArgs(paths=["foo"])

    f = h.Handle(args=args, token=self.token)
    self.assertEqual(f.args.paths, ["bar"])


class ApiCallRobotRouterTest(test_lib.GRRBaseTest):
  """Tests for ApiCallRobotRouter."""

  def _CreateRouter(self, delegate=None, **kwargs):
    params = rr.ApiCallRobotRouterParams(robot_id=self.robot_id, **kwargs)
    return rr.ApiCallRobotRouter(params=params, delegate=delegate)

  def setUp(self):
    super(ApiCallRobotRouterTest, self).setUp()
    self.client_id = self.SetupClient(0)
    self.robot_id = "TestRobot"

  def testSearchClientsIsDisabledByDefault(self):
    router = self._CreateRouter()
    with self.assertRaises(access_control.UnauthorizedAccess):
      router.SearchClients(None, token=self.token)

  def testSearchClientsWorksWhenExplicitlyEnabled(self):
    router = self._CreateRouter(
        search_clients=rr.RobotRouterSearchClientsParams(enabled=True))
    router.SearchClients(None, token=self.token)

  def testCreateFlowRaisesIfClientIdNotSpecified(self):
    router = self._CreateRouter()
    with self.assertRaises(ValueError):
      router.CreateFlow(api_flow.ApiCreateFlowArgs(), token=self.token)

  def testCreateFlowIsDisabledByDefault(self):
    router = self._CreateRouter()
    with self.assertRaises(access_control.UnauthorizedAccess):
      router.CreateFlow(
          api_flow.ApiCreateFlowArgs(client_id=self.client_id),
          token=self.token)

  def testFileFinderWorksWhenEnabledAndArgumentsAreCorrect(self):
    router = None

    def Check(path):
      router.CreateFlow(
          api_flow.ApiCreateFlowArgs(
              flow=api_flow.ApiFlow(
                  name=file_finder.FileFinder.__name__,
                  args=rdf_file_finder.FileFinderArgs(paths=[path])),
              client_id=self.client_id),
          token=self.token)

    router = self._CreateRouter(
        file_finder_flow=rr.RobotRouterFileFinderFlowParams(enabled=True))
    Check("/foo/bar")

    router = self._CreateRouter(
        file_finder_flow=rr.RobotRouterFileFinderFlowParams(
            enabled=True, globs_allowed=True))
    Check("/foo/bar/**/*")

    router = self._CreateRouter(
        file_finder_flow=rr.RobotRouterFileFinderFlowParams(
            enabled=True, interpolations_allowed=True))
    Check("%%users.homedir%%/foo")

    router = self._CreateRouter(
        file_finder_flow=rr.RobotRouterFileFinderFlowParams(
            enabled=True, globs_allowed=True, interpolations_allowed=True))
    Check("%%users.homedir%%/foo/**/*")

  def testFileFinderRaisesWhenEnabledButArgumentsNotCorrect(self):
    router = None

    def Check(path):
      with self.assertRaises(access_control.UnauthorizedAccess):
        router.CreateFlow(
            api_flow.ApiCreateFlowArgs(
                flow=api_flow.ApiFlow(
                    name=file_finder.FileFinder.__name__,
                    args=rdf_file_finder.FileFinderArgs(paths=[path])),
                client_id=self.client_id),
            token=self.token)

    router = self._CreateRouter(
        file_finder_flow=rr.RobotRouterFileFinderFlowParams(enabled=True))
    Check("/foo/bar/**/*")

    router = self._CreateRouter(
        file_finder_flow=rr.RobotRouterFileFinderFlowParams(enabled=True))
    Check("%%users.homedir%%/foo")

  def testFileFinderFlowNameCanBeOverriden(self):
    router = self._CreateRouter(
        file_finder_flow=rr.RobotRouterFileFinderFlowParams(
            enabled=True, file_finder_flow_name=AnotherFileFinder.__name__))

    with self.assertRaises(access_control.UnauthorizedAccess):
      router.CreateFlow(
          api_flow.ApiCreateFlowArgs(
              flow=api_flow.ApiFlow(name=file_finder.FileFinder.__name__),
              client_id=self.client_id),
          token=self.token)

    router.CreateFlow(
        api_flow.ApiCreateFlowArgs(
            flow=api_flow.ApiFlow(name=AnotherFileFinder.__name__),
            client_id=self.client_id),
        token=self.token)

  def testFileFinderHashMaxFileSizeCanBeOverriden(self):
    router = self._CreateRouter(
        file_finder_flow=rr.RobotRouterFileFinderFlowParams(
            enabled=True, max_file_size=42))

    ha = rdf_file_finder.FileFinderHashActionOptions()
    ha.max_size = 80
    ha.oversized_file_policy = ha.OversizedFilePolicy.HASH_TRUNCATED

    path = "/foo/bar"
    handler = router.CreateFlow(
        api_flow.ApiCreateFlowArgs(
            flow=api_flow.ApiFlow(
                name=file_finder.FileFinder.__name__,
                args=rdf_file_finder.FileFinderArgs(
                    paths=[path],
                    action=rdf_file_finder.FileFinderAction(
                        action_type="HASH", hash=ha))),
            client_id=self.client_id),
        token=self.token)

    ha = handler.override_flow_args.action.hash
    self.assertEqual(ha.oversized_file_policy, ha.OversizedFilePolicy.SKIP)
    self.assertEqual(ha.max_size, 42)

  def testFileFinderDownloadMaxFileSizeCanBeOverriden(self):
    router = self._CreateRouter(
        file_finder_flow=rr.RobotRouterFileFinderFlowParams(
            enabled=True, max_file_size=42))

    da = rdf_file_finder.FileFinderDownloadActionOptions()
    da.max_size = 80
    da.oversized_file_policy = da.OversizedFilePolicy.DOWNLOAD_TRUNCATED

    path = "/foo/bar"
    handler = router.CreateFlow(
        api_flow.ApiCreateFlowArgs(
            flow=api_flow.ApiFlow(
                name=file_finder.FileFinder.__name__,
                args=rdf_file_finder.FileFinderArgs(
                    paths=[path],
                    action=rdf_file_finder.FileFinderAction(
                        action_type="DOWNLOAD", download=da))),
            client_id=self.client_id),
        token=self.token)

    da = handler.override_flow_args.action.download
    self.assertEqual(da.oversized_file_policy, da.OversizedFilePolicy.SKIP)
    self.assertEqual(da.max_size, 42)

  def testArtifactCollectorWorksWhenEnabledAndArgumentsAreCorrect(self):
    router = None

    def Check(artifacts):
      router.CreateFlow(
          api_flow.ApiCreateFlowArgs(
              flow=api_flow.ApiFlow(
                  name=collectors.ArtifactCollectorFlow.__name__,
                  args=rdf_artifacts.ArtifactCollectorFlowArgs(
                      artifact_list=artifacts)),
              client_id=self.client_id),
          token=self.token)

    router = self._CreateRouter(
        artifact_collector_flow=rr.RobotRouterArtifactCollectorFlowParams(
            enabled=True))
    Check([])

    router = self._CreateRouter(
        artifact_collector_flow=rr.RobotRouterArtifactCollectorFlowParams(
            enabled=True, artifacts_whitelist=["foo"]))
    Check(["foo"])

    router = self._CreateRouter(
        artifact_collector_flow=rr.RobotRouterArtifactCollectorFlowParams(
            enabled=True, artifacts_whitelist=["foo", "bar", "blah"]))
    Check(["foo", "blah"])

  def testArtifactCollectorRaisesWhenEnabledButArgumentsNotCorrect(self):
    router = None

    def Check(artifacts):
      with self.assertRaises(access_control.UnauthorizedAccess):
        router.CreateFlow(
            api_flow.ApiCreateFlowArgs(
                flow=api_flow.ApiFlow(
                    name=collectors.ArtifactCollectorFlow.__name__,
                    args=rdf_artifacts.ArtifactCollectorFlowArgs(
                        artifact_list=artifacts)),
                client_id=self.client_id),
            token=self.token)

    router = self._CreateRouter(
        artifact_collector_flow=rr.RobotRouterArtifactCollectorFlowParams(
            enabled=True))
    Check(["foo"])

    router = self._CreateRouter(
        artifact_collector_flow=rr.RobotRouterArtifactCollectorFlowParams(
            enabled=True, artifacts_whitelist=["bar", "blah"]))
    Check(["foo", "bar"])

  def testArtifactCollectorFlowNameCanBeOverriden(self):
    router = self._CreateRouter(
        artifact_collector_flow=rr.RobotRouterArtifactCollectorFlowParams(
            enabled=True,
            artifact_collector_flow_name=AnotherArtifactCollector.__name__))

    with self.assertRaises(access_control.UnauthorizedAccess):
      router.CreateFlow(
          api_flow.ApiCreateFlowArgs(
              flow=api_flow.ApiFlow(
                  name=collectors.ArtifactCollectorFlow.__name__),
              client_id=self.client_id),
          token=self.token)

    router.CreateFlow(
        api_flow.ApiCreateFlowArgs(
            flow=api_flow.ApiFlow(name=AnotherArtifactCollector.__name__),
            client_id=self.client_id),
        token=self.token)

  def testOnlyFileFinderAndArtifactCollectorFlowsAreAllowed(self):
    router = self._CreateRouter(
        file_finder_flow=rr.RobotRouterFileFinderFlowParams(enabled=True),
        artifact_collector_flow=rr.RobotRouterArtifactCollectorFlowParams(
            enabled=True))

    with self.assertRaises(access_control.UnauthorizedAccess):
      router.CreateFlow(
          api_flow.ApiCreateFlowArgs(
              flow=api_flow.ApiFlow(name=flow_test_lib.BrokenFlow.__name__),
              client_id=self.client_id),
          token=self.token)

  def _CreateFlowWithRobotId(self, flow_name=None, flow_args=None):
    flow_name = flow_name or file_finder.FileFinder.__name__

    handler = rr.ApiRobotCreateFlowHandler(robot_id=self.robot_id)
    flow_result = handler.Handle(
        api_flow.ApiCreateFlowArgs(
            client_id=self.client_id,
            flow=api_flow.ApiFlow(name=flow_name, args=flow_args)),
        token=self.token)
    return flow_result.flow_id

  def testGetFlowIsDisabledByDefault(self):
    router = self._CreateRouter()
    with self.assertRaises(access_control.UnauthorizedAccess):
      router.GetFlow(None, token=self.token)

  def testGetFlowRaisesIfFlowWasNotCreatedBySameRouter(self):
    flow_urn = flow.StartAFF4Flow(
        client_id=self.client_id,
        flow_name=file_finder.FileFinder.__name__,
        token=self.token)

    router = self._CreateRouter(
        get_flow=rr.RobotRouterGetFlowParams(enabled=True))
    with self.assertRaises(access_control.UnauthorizedAccess):
      router.GetFlow(
          api_flow.ApiGetFlowArgs(
              client_id=self.client_id, flow_id=flow_urn.Basename()),
          token=self.token)

  def testGetFlowWorksIfFlowWasCreatedBySameRouter(self):
    flow_id = self._CreateFlowWithRobotId()
    router = self._CreateRouter(
        get_flow=rr.RobotRouterGetFlowParams(enabled=True))
    router.GetFlow(
        api_flow.ApiGetFlowArgs(client_id=self.client_id, flow_id=flow_id),
        token=self.token)

  def testListFlowResultsIsDisabledByDefault(self):
    router = self._CreateRouter()
    with self.assertRaises(access_control.UnauthorizedAccess):
      router.ListFlowResults(None, token=self.token)

  def testListFlowResultsRaisesIfFlowWasNotCreatedBySameRouter(self):
    flow_urn = flow.StartAFF4Flow(
        client_id=self.client_id,
        flow_name=file_finder.FileFinder.__name__,
        token=self.token)

    router = self._CreateRouter(
        list_flow_results=rr.RobotRouterListFlowResultsParams(enabled=True))
    with self.assertRaises(access_control.UnauthorizedAccess):
      router.ListFlowResults(
          api_flow.ApiListFlowResultsArgs(
              client_id=self.client_id, flow_id=flow_urn.Basename()),
          token=self.token)

  def testListFlowResultsWorksIfFlowWasCreatedBySameRouter(self):
    flow_id = self._CreateFlowWithRobotId()
    router = self._CreateRouter(
        list_flow_results=rr.RobotRouterListFlowResultsParams(enabled=True))
    router.ListFlowResults(
        api_flow.ApiListFlowResultsArgs(
            client_id=self.client_id, flow_id=flow_id),
        token=self.token)

  def testListFlowLogsIsDisabledByDefault(self):
    router = self._CreateRouter()
    with self.assertRaises(access_control.UnauthorizedAccess):
      router.ListFlowLogs(None, token=self.token)

  def testListFlowLogsRaisesIfFlowWasNotCreatedBySameRouter(self):
    flow_urn = flow.StartAFF4Flow(
        client_id=self.client_id,
        flow_name=file_finder.FileFinder.__name__,
        token=self.token)

    router = self._CreateRouter(
        list_flow_logs=rr.RobotRouterListFlowLogsParams(enabled=True))
    with self.assertRaises(access_control.UnauthorizedAccess):
      router.ListFlowLogs(
          api_flow.ApiListFlowLogsArgs(
              client_id=self.client_id, flow_id=flow_urn.Basename()),
          token=self.token)

  def testListFlowLogsWorksIfFlowWasCreatedBySameRouter(self):
    flow_id = self._CreateFlowWithRobotId()
    router = self._CreateRouter(
        list_flow_logs=rr.RobotRouterListFlowLogsParams(enabled=True))
    router.ListFlowLogs(
        api_flow.ApiListFlowLogsArgs(client_id=self.client_id, flow_id=flow_id),
        token=self.token)

  def testGetFlowFilesArchiveIsDisabledByDefault(self):
    router = self._CreateRouter()
    with self.assertRaises(access_control.UnauthorizedAccess):
      router.GetFlowFilesArchive(None, token=self.token)

  def testFlowFilesArchiveRaisesIfFlowWasNotCreatedBySameRouter(self):
    flow_urn = flow.StartAFF4Flow(
        client_id=self.client_id,
        flow_name=file_finder.FileFinder.__name__,
        token=self.token)

    router = self._CreateRouter()
    with self.assertRaises(access_control.UnauthorizedAccess):
      router.GetFlowFilesArchive(
          api_flow.ApiGetFlowFilesArchiveArgs(
              client_id=self.client_id, flow_id=flow_urn.Basename()),
          token=self.token)

  def testGetFlowFilesArchiveWorksIfFlowWasCreatedBySameRouter(self):
    flow_id = self._CreateFlowWithRobotId()
    router = self._CreateRouter(
        get_flow_files_archive=rr.RobotRouterGetFlowFilesArchiveParams(
            enabled=True))
    router.GetFlowFilesArchive(
        api_flow.ApiGetFlowFilesArchiveArgs(
            client_id=self.client_id, flow_id=flow_id),
        token=self.token)

  def testGetFlowFilesArchiveReturnsLimitedHandler(self):
    flow_id = self._CreateFlowWithRobotId()
    router = self._CreateRouter(
        get_flow_files_archive=rr.RobotRouterGetFlowFilesArchiveParams(
            enabled=True,
            path_globs_blacklist=["**/*.txt"],
            path_globs_whitelist=["foo/*", "bar/*"]))
    handler = router.GetFlowFilesArchive(
        api_flow.ApiGetFlowFilesArchiveArgs(
            client_id=self.client_id, flow_id=flow_id),
        token=self.token)
    self.assertEqual(handler.path_globs_blacklist, ["**/*.txt"])
    self.assertEqual(handler.path_globs_whitelist, ["foo/*", "bar/*"])

  def testGetFlowFilesArchiveReturnsNonLimitedHandlerForArtifactsWhenNeeded(
      self):
    router = self._CreateRouter(
        artifact_collector_flow=rr.RobotRouterArtifactCollectorFlowParams(
            artifact_collector_flow_name=AnotherArtifactCollector.__name__),
        get_flow_files_archive=rr.RobotRouterGetFlowFilesArchiveParams(
            enabled=True,
            skip_glob_checks_for_artifact_collector=True,
            path_globs_blacklist=["**/*.txt"],
            path_globs_whitelist=["foo/*", "bar/*"]))

    flow_id = self._CreateFlowWithRobotId()
    handler = router.GetFlowFilesArchive(
        api_flow.ApiGetFlowFilesArchiveArgs(
            client_id=self.client_id, flow_id=flow_id),
        token=self.token)
    self.assertEqual(handler.path_globs_blacklist, ["**/*.txt"])
    self.assertEqual(handler.path_globs_whitelist, ["foo/*", "bar/*"])

    flow_id = self._CreateFlowWithRobotId(
        flow_name=AnotherArtifactCollector.__name__,
        flow_args=rdf_artifacts.ArtifactCollectorFlowArgs(
            artifact_list=["Foo"]))
    handler = router.GetFlowFilesArchive(
        api_flow.ApiGetFlowFilesArchiveArgs(
            client_id=self.client_id, flow_id=flow_id),
        token=self.token)
    self.assertTrue(handler.path_globs_blacklist is None)
    self.assertTrue(handler.path_globs_whitelist is None)

  IMPLEMENTED_METHODS = [
      "SearchClients",
      "CreateFlow",
      "GetFlow",
      "ListFlowResults",
      "ListFlowLogs",
      "GetFlowFilesArchive",
      # This single reflection method is needed for API libraries to work
      # correctly.
      "ListApiMethods",
      # TODO(user): Remove methods below as soon as they are deprecated
      # in favor of the methods above.
      "StartRobotGetFilesOperation",
      "GetRobotGetFilesOperationState"
  ]

  def testAllOtherMethodsAreNotImplemented(self):
    router = self._CreateRouter()

    unchecked_methods = (
        set(iterkeys(router.__class__.GetAnnotatedMethods())) - set(
            self.IMPLEMENTED_METHODS))
    self.assertTrue(unchecked_methods)

    for method_name in unchecked_methods:
      with self.assertRaises(NotImplementedError):
        getattr(router, method_name)(None, token=self.token)


def main(argv):
  test_lib.main(argv)


if __name__ == "__main__":
  flags.StartMain(main)
