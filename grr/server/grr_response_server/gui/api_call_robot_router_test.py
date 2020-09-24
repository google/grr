#!/usr/bin/env python
# Lint as: python3
"""Tests for ApiCallRobotRouter."""
from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

from absl import app

from grr_response_core.lib.rdfvalues import artifacts as rdf_artifacts
from grr_response_core.lib.rdfvalues import file_finder as rdf_file_finder
from grr_response_server import access_control
from grr_response_server import flow_base
from grr_response_server.flows.general import collectors
from grr_response_server.flows.general import file_finder
from grr_response_server.gui import api_call_context
from grr_response_server.gui import api_call_robot_router as rr
from grr_response_server.gui.api_plugins import flow as api_flow

from grr.test_lib import acl_test_lib
from grr.test_lib import flow_test_lib
from grr.test_lib import test_lib


class AnotherFileFinder(flow_base.FlowBase):
  args_type = rdf_file_finder.FileFinderArgs


class AnotherArtifactCollector(flow_base.FlowBase):
  args_type = rdf_artifacts.ArtifactCollectorFlowArgs


class ApiRobotCreateFlowHandlerTest(test_lib.GRRBaseTest):
  """Tests for ApiRobotCreateFlowHandler."""

  def setUp(self):
    super(ApiRobotCreateFlowHandlerTest, self).setUp()
    self.client_id = self.SetupClient(0)
    self.context = api_call_context.ApiCallContext("test")

  def testPassesFlowArgsThroughIfNoOverridesSpecified(self):
    h = rr.ApiRobotCreateFlowHandler()

    args = api_flow.ApiCreateFlowArgs(client_id=self.client_id)
    args.flow.name = file_finder.FileFinder.__name__
    args.flow.args = rdf_file_finder.FileFinderArgs(paths=["foo"])

    f = h.Handle(args=args, context=self.context)
    self.assertEqual(f.args.paths, ["foo"])

  def testOverridesFlowNameIfOverrideArgIsSpecified(self):
    h = rr.ApiRobotCreateFlowHandler(
        override_flow_name=AnotherFileFinder.__name__)  # pylint: disable=undefined-variable

    args = api_flow.ApiCreateFlowArgs(client_id=self.client_id)
    args.flow.name = file_finder.FileFinder.__name__
    args.flow.args = rdf_file_finder.FileFinderArgs(paths=["foo"])

    f = h.Handle(args=args, context=self.context)
    self.assertEqual(f.name, AnotherFileFinder.__name__)  # pylint: disable=undefined-variable

  def testOverridesFlowArgsThroughIfOverridesSpecified(self):
    override_flow_args = rdf_file_finder.FileFinderArgs(paths=["bar"])
    h = rr.ApiRobotCreateFlowHandler(override_flow_args=override_flow_args)

    args = api_flow.ApiCreateFlowArgs(client_id=self.client_id)
    args.flow.name = file_finder.FileFinder.__name__
    args.flow.args = rdf_file_finder.FileFinderArgs(paths=["foo"])

    f = h.Handle(args=args, context=self.context)
    self.assertEqual(f.args.paths, ["bar"])


class ApiCallRobotRouterTest(acl_test_lib.AclTestMixin, test_lib.GRRBaseTest):
  """Tests for ApiCallRobotRouter."""

  def _CreateRouter(self, delegate=None, **kwargs):
    params = rr.ApiCallRobotRouterParams(**kwargs)
    return rr.ApiCallRobotRouter(params=params, delegate=delegate)

  def setUp(self):
    super(ApiCallRobotRouterTest, self).setUp()
    self.client_id = self.SetupClient(0)
    self.context = api_call_context.ApiCallContext("test")
    self.another_username = "someotherguy"
    self.CreateUser(self.another_username)

  def testSearchClientsIsDisabledByDefault(self):
    router = self._CreateRouter()
    with self.assertRaises(access_control.UnauthorizedAccess):
      router.SearchClients(None, context=self.context)

  def testSearchClientsWorksWhenExplicitlyEnabled(self):
    router = self._CreateRouter(
        search_clients=rr.RobotRouterSearchClientsParams(enabled=True))
    router.SearchClients(None, context=self.context)

  def testCreateFlowRaisesIfClientIdNotSpecified(self):
    router = self._CreateRouter()
    with self.assertRaises(ValueError):
      router.CreateFlow(api_flow.ApiCreateFlowArgs(), context=self.context)

  def testCreateFlowIsDisabledByDefault(self):
    router = self._CreateRouter()
    with self.assertRaises(access_control.UnauthorizedAccess):
      router.CreateFlow(
          api_flow.ApiCreateFlowArgs(client_id=self.client_id),
          context=self.context)

  def testFileFinderWorksWhenEnabledAndArgumentsAreCorrect(self):
    router = None

    def Check(path):
      router.CreateFlow(
          api_flow.ApiCreateFlowArgs(
              flow=api_flow.ApiFlow(
                  name=file_finder.FileFinder.__name__,
                  args=rdf_file_finder.FileFinderArgs(paths=[path])),
              client_id=self.client_id),
          context=self.context)

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
            context=self.context)

    router = self._CreateRouter(
        file_finder_flow=rr.RobotRouterFileFinderFlowParams(enabled=True))
    Check("/foo/bar/**/*")

    router = self._CreateRouter(
        file_finder_flow=rr.RobotRouterFileFinderFlowParams(enabled=True))
    Check("%%users.homedir%%/foo")

  def testFileFinderFlowNameCanBeOverridden(self):
    router = self._CreateRouter(
        file_finder_flow=rr.RobotRouterFileFinderFlowParams(
            enabled=True, file_finder_flow_name=AnotherFileFinder.__name__))  # pylint: disable=undefined-variable

    handler = router.CreateFlow(
        api_flow.ApiCreateFlowArgs(
            flow=api_flow.ApiFlow(name=AnotherFileFinder.__name__),  # pylint: disable=undefined-variable
            client_id=self.client_id),
        context=self.context)

    self.assertEqual(handler.override_flow_name, AnotherFileFinder.__name__)  # pylint: disable=undefined-variable

  def testOverriddenFileFinderFlowCanBeCreatedUsingOriginalFileFinderName(self):
    router = self._CreateRouter(
        file_finder_flow=rr.RobotRouterFileFinderFlowParams(
            enabled=True, file_finder_flow_name=AnotherFileFinder.__name__))  # pylint: disable=undefined-variable

    handler = router.CreateFlow(
        api_flow.ApiCreateFlowArgs(
            flow=api_flow.ApiFlow(name=file_finder.FileFinder.__name__),
            client_id=self.client_id),
        context=self.context)

    self.assertEqual(handler.override_flow_name, AnotherFileFinder.__name__)  # pylint: disable=undefined-variable

  def testFileFinderHashMaxFileSizeCanBeOverridden(self):
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
        context=self.context)

    ha = handler.override_flow_args.action.hash
    self.assertEqual(ha.oversized_file_policy, ha.OversizedFilePolicy.SKIP)
    self.assertEqual(ha.max_size, 42)

  def testFileFinderDownloadMaxFileSizeCanBeOverridden(self):
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
        context=self.context)

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
          context=self.context)

    router = self._CreateRouter(
        artifact_collector_flow=rr.RobotRouterArtifactCollectorFlowParams(
            enabled=True))
    Check([])

    router = self._CreateRouter(
        artifact_collector_flow=rr.RobotRouterArtifactCollectorFlowParams(
            enabled=True, allow_artifacts=["foo"]))
    Check(["foo"])

    router = self._CreateRouter(
        artifact_collector_flow=rr.RobotRouterArtifactCollectorFlowParams(
            enabled=True, allow_artifacts=["foo", "bar", "blah"]))
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
            context=self.context)

    router = self._CreateRouter(
        artifact_collector_flow=rr.RobotRouterArtifactCollectorFlowParams(
            enabled=True))
    Check(["foo"])

    router = self._CreateRouter(
        artifact_collector_flow=rr.RobotRouterArtifactCollectorFlowParams(
            enabled=True, allow_artifacts=["bar", "blah"]))
    Check(["foo", "bar"])

  def testArtifactCollectorFlowNameCanBeOverridden(self):
    router = self._CreateRouter(
        artifact_collector_flow=rr.RobotRouterArtifactCollectorFlowParams(
            enabled=True,
            artifact_collector_flow_name=AnotherArtifactCollector.__name__))  # pylint: disable=undefined-variable

    handler = router.CreateFlow(
        api_flow.ApiCreateFlowArgs(
            flow=api_flow.ApiFlow(name=AnotherArtifactCollector.__name__),  # pylint: disable=undefined-variable
            client_id=self.client_id),
        context=self.context)

    self.assertEqual(handler.override_flow_name,
                     AnotherArtifactCollector.__name__)  # pylint: disable=undefined-variable

  def testOverriddenArtifactCollectorFlowCanBeCreatedUsingOriginalName(self):
    router = self._CreateRouter(
        artifact_collector_flow=rr.RobotRouterArtifactCollectorFlowParams(
            enabled=True,
            artifact_collector_flow_name=AnotherArtifactCollector.__name__))  # pylint: disable=undefined-variable

    handler = router.CreateFlow(
        api_flow.ApiCreateFlowArgs(
            flow=api_flow.ApiFlow(
                name=collectors.ArtifactCollectorFlow.__name__),
            client_id=self.client_id),
        context=self.context)

    self.assertEqual(handler.override_flow_name,
                     AnotherArtifactCollector.__name__)  # pylint: disable=undefined-variable

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
          context=self.context)

  def _CreateFlowWithRobotId(self, flow_name=None, flow_args=None):
    flow_name = flow_name or file_finder.FileFinder.__name__

    handler = rr.ApiRobotCreateFlowHandler()
    flow_result = handler.Handle(
        api_flow.ApiCreateFlowArgs(
            client_id=self.client_id,
            flow=api_flow.ApiFlow(name=flow_name, args=flow_args)),
        context=self.context)
    return flow_result.flow_id

  def testGetFlowIsDisabledByDefault(self):
    router = self._CreateRouter()
    with self.assertRaises(access_control.UnauthorizedAccess):
      router.GetFlow(None, context=self.context)

  def testGetFlowRaisesIfFlowWasNotCreatedBySameUser(self):
    flow_id = flow_test_lib.StartFlow(
        file_finder.FileFinder, self.client_id, creator=self.another_username)

    router = self._CreateRouter(
        get_flow=rr.RobotRouterGetFlowParams(enabled=True))
    with self.assertRaises(access_control.UnauthorizedAccess):
      router.GetFlow(
          api_flow.ApiGetFlowArgs(client_id=self.client_id, flow_id=flow_id),
          context=self.context)

  def testGetFlowWorksIfFlowWasCreatedBySameUser(self):
    flow_id = self._CreateFlowWithRobotId()
    router = self._CreateRouter(
        get_flow=rr.RobotRouterGetFlowParams(enabled=True))
    router.GetFlow(
        api_flow.ApiGetFlowArgs(client_id=self.client_id, flow_id=flow_id),
        context=self.context)

  def testListFlowResultsIsDisabledByDefault(self):
    router = self._CreateRouter()
    with self.assertRaises(access_control.UnauthorizedAccess):
      router.ListFlowResults(None, context=self.context)

  def testListFlowResultsRaisesIfFlowWasNotCreatedBySameUser(self):
    flow_id = flow_test_lib.StartFlow(
        file_finder.FileFinder, self.client_id, creator=self.another_username)

    router = self._CreateRouter(
        list_flow_results=rr.RobotRouterListFlowResultsParams(enabled=True))
    with self.assertRaises(access_control.UnauthorizedAccess):
      router.ListFlowResults(
          api_flow.ApiListFlowResultsArgs(
              client_id=self.client_id, flow_id=flow_id),
          context=self.context)

  def testListFlowResultsWorksIfFlowWasCreatedBySameUser(self):
    flow_id = self._CreateFlowWithRobotId()
    router = self._CreateRouter(
        list_flow_results=rr.RobotRouterListFlowResultsParams(enabled=True))
    router.ListFlowResults(
        api_flow.ApiListFlowResultsArgs(
            client_id=self.client_id, flow_id=flow_id),
        context=self.context)

  def testListFlowLogsIsDisabledByDefault(self):
    router = self._CreateRouter()
    with self.assertRaises(access_control.UnauthorizedAccess):
      router.ListFlowLogs(None, context=self.context)

  def testListFlowLogsRaisesIfFlowWasNotCreatedBySameUser(self):
    flow_id = flow_test_lib.StartFlow(
        file_finder.FileFinder, self.client_id, creator=self.another_username)

    router = self._CreateRouter(
        list_flow_logs=rr.RobotRouterListFlowLogsParams(enabled=True))
    with self.assertRaises(access_control.UnauthorizedAccess):
      router.ListFlowLogs(
          api_flow.ApiListFlowLogsArgs(
              client_id=self.client_id, flow_id=flow_id),
          context=self.context)

  def testListFlowLogsWorksIfFlowWasCreatedBySameUser(self):
    flow_id = self._CreateFlowWithRobotId()
    router = self._CreateRouter(
        list_flow_logs=rr.RobotRouterListFlowLogsParams(enabled=True))
    router.ListFlowLogs(
        api_flow.ApiListFlowLogsArgs(client_id=self.client_id, flow_id=flow_id),
        context=self.context)

  def testGetFlowFilesArchiveIsDisabledByDefault(self):
    router = self._CreateRouter()
    with self.assertRaises(access_control.UnauthorizedAccess):
      router.GetFlowFilesArchive(None, context=self.context)

  def testFlowFilesArchiveRaisesIfFlowWasNotCreatedBySameUser(self):
    flow_id = flow_test_lib.StartFlow(
        file_finder.FileFinder, self.client_id, creator=self.another_username)

    router = self._CreateRouter()
    with self.assertRaises(access_control.UnauthorizedAccess):
      router.GetFlowFilesArchive(
          api_flow.ApiGetFlowFilesArchiveArgs(
              client_id=self.client_id, flow_id=flow_id),
          context=self.context)

  def testGetFlowFilesArchiveWorksIfFlowWasCreatedBySameUser(self):
    flow_id = self._CreateFlowWithRobotId()
    router = self._CreateRouter(
        get_flow_files_archive=rr.RobotRouterGetFlowFilesArchiveParams(
            enabled=True))
    router.GetFlowFilesArchive(
        api_flow.ApiGetFlowFilesArchiveArgs(
            client_id=self.client_id, flow_id=flow_id),
        context=self.context)

  def testGetFlowFilesArchiveReturnsLimitedHandler(self):
    flow_id = self._CreateFlowWithRobotId()
    router = self._CreateRouter(
        get_flow_files_archive=rr.RobotRouterGetFlowFilesArchiveParams(
            enabled=True,
            exclude_path_globs=["**/*.txt"],
            include_only_path_globs=["foo/*", "bar/*"]))
    handler = router.GetFlowFilesArchive(
        api_flow.ApiGetFlowFilesArchiveArgs(
            client_id=self.client_id, flow_id=flow_id),
        context=self.context)
    self.assertEqual(handler.exclude_path_globs, ["**/*.txt"])
    self.assertEqual(handler.include_only_path_globs, ["foo/*", "bar/*"])

  def testGetFlowFilesArchiveReturnsNonLimitedHandlerForArtifactsWhenNeeded(
      self):
    router = self._CreateRouter(
        artifact_collector_flow=rr.RobotRouterArtifactCollectorFlowParams(
            artifact_collector_flow_name=AnotherArtifactCollector.__name__),  # pylint: disable=undefined-variable
        get_flow_files_archive=rr.RobotRouterGetFlowFilesArchiveParams(
            enabled=True,
            skip_glob_checks_for_artifact_collector=True,
            exclude_path_globs=["**/*.txt"],
            include_only_path_globs=["foo/*", "bar/*"]))

    flow_id = self._CreateFlowWithRobotId()
    handler = router.GetFlowFilesArchive(
        api_flow.ApiGetFlowFilesArchiveArgs(
            client_id=self.client_id, flow_id=flow_id),
        context=self.context)
    self.assertEqual(handler.exclude_path_globs, ["**/*.txt"])
    self.assertEqual(handler.include_only_path_globs, ["foo/*", "bar/*"])

    flow_id = self._CreateFlowWithRobotId(
        flow_name=AnotherArtifactCollector.__name__,  # pylint: disable=undefined-variable
        flow_args=rdf_artifacts.ArtifactCollectorFlowArgs(
            artifact_list=["Foo"]))
    handler = router.GetFlowFilesArchive(
        api_flow.ApiGetFlowFilesArchiveArgs(
            client_id=self.client_id, flow_id=flow_id),
        context=self.context)
    self.assertIsNone(handler.exclude_path_globs)
    self.assertIsNone(handler.include_only_path_globs)

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
      "GetOpenApiDescription",
      # TODO(user): Remove methods below as soon as they are deprecated
      # in favor of the methods above.
      "StartRobotGetFilesOperation",
      "GetRobotGetFilesOperationState"
  ]

  def testAllOtherMethodsAreNotImplemented(self):
    router = self._CreateRouter()

    unchecked_methods = (
        set(router.__class__.GetAnnotatedMethods().keys()) -
        set(self.IMPLEMENTED_METHODS))
    self.assertTrue(unchecked_methods)

    for method_name in unchecked_methods:
      with self.assertRaises(NotImplementedError):
        getattr(router, method_name)(None, context=self.context)


def main(argv):
  test_lib.main(argv)


if __name__ == "__main__":
  app.run(main)
