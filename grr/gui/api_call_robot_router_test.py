#!/usr/bin/env python
"""Tests for ApiCallRobotRouter."""

import os
import StringIO
import zipfile


from grr.gui import api_auth_manager
from grr.gui import api_call_robot_router as rr
from grr.gui import http_api_e2e_test

from grr.gui.api_plugins import flow as api_flow

from grr.lib import flags
from grr.lib.rdfvalues import client as rdf_client
from grr.lib.rdfvalues import file_finder as rdf_file_finder
from grr.server import access_control
from grr.server import artifact_utils
from grr.server import flow
from grr.server.flows.general import collectors
from grr.server.flows.general import file_finder
from grr.server.flows.general import processes

from grr.test_lib import action_mocks
from grr.test_lib import flow_test_lib
from grr.test_lib import test_lib


class AnotherFileFinder(flow.GRRFlow):
  args_type = rdf_file_finder.FileFinderArgs


class AnotherArtifactCollector(flow.GRRFlow):
  args_type = artifact_utils.ArtifactCollectorFlowArgs


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
                  args=artifact_utils.ArtifactCollectorFlowArgs(
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
                    args=artifact_utils.ArtifactCollectorFlowArgs(
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
    flow_urn = flow.GRRFlow.StartFlow(
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
    flow_urn = flow.GRRFlow.StartFlow(
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

  def testGetFlowFilesArchiveIsDisabledByDefault(self):
    router = self._CreateRouter()
    with self.assertRaises(access_control.UnauthorizedAccess):
      router.GetFlowFilesArchive(None, token=self.token)

  def testFlowFilesArchiveRaisesIfFlowWasNotCreatedBySameRouter(self):
    flow_urn = flow.GRRFlow.StartFlow(
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
        flow_args=artifact_utils.ArtifactCollectorFlowArgs(
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
        set(router.__class__.GetAnnotatedMethods().keys()) -
        set(self.IMPLEMENTED_METHODS))
    self.assertTrue(unchecked_methods)

    for method_name in unchecked_methods:
      with self.assertRaises(NotImplementedError):
        getattr(router, method_name)(None, token=self.token)


class ApiCallRobotRouterE2ETest(http_api_e2e_test.ApiE2ETest):

  FILE_FINDER_ROUTER_CONFIG = """
router: "ApiCallRobotRouter"
router_params:
  file_finder_flow:
    enabled: True
  get_flow:
    enabled: True
  list_flow_results:
    enabled: True
  get_flow_files_archive:
    enabled: True
    path_globs_whitelist:
      - "/**/*.plist"
  robot_id: "TheRobot"
users:
  - "%s"
"""

  def InitRouterConfig(self, router_config):
    router_config_file = os.path.join(self.temp_dir, "api_acls.yaml")
    with open(router_config_file, "wb") as fd:
      fd.write(router_config)

    self.config_overrider = test_lib.ConfigOverrider({
        "API.RouterACLConfigFile": router_config_file
    })
    self.config_overrider.Start()

    # Force creation of new APIAuthorizationManager, so that configuration
    # changes are picked up.
    api_auth_manager.APIACLInit.InitApiAuthManager()

  def setUp(self):
    super(ApiCallRobotRouterE2ETest, self).setUp()
    self.client_id = self.SetupClient(0)

  def tearDown(self):
    super(ApiCallRobotRouterE2ETest, self).tearDown()
    self.config_overrider.Stop()

  def testCreatingArbitraryFlowDoesNotWork(self):
    self.InitRouterConfig(
        self.__class__.FILE_FINDER_ROUTER_CONFIG % self.token.username)

    client_ref = self.api.Client(client_id=self.client_id.Basename())
    with self.assertRaises(RuntimeError):
      client_ref.CreateFlow(name=processes.ListProcesses.__name__)

  def testFileFinderWorkflowWorks(self):
    self.InitRouterConfig(
        self.__class__.FILE_FINDER_ROUTER_CONFIG % self.token.username)

    client_ref = self.api.Client(client_id=self.client_id.Basename())

    args = rdf_file_finder.FileFinderArgs(
        paths=[
            os.path.join(self.base_path, "test.plist"),
            os.path.join(self.base_path, "numbers.txt"),
            os.path.join(self.base_path, "numbers.txt.ver2")
        ],
        action=rdf_file_finder.FileFinderAction.Download()).AsPrimitiveProto()
    flow_obj = client_ref.CreateFlow(
        name=file_finder.FileFinder.__name__, args=args)
    self.assertEqual(flow_obj.data.state, flow_obj.data.RUNNING)

    # Now run the flow we just started.
    client_id = rdf_client.ClientURN(flow_obj.client_id)
    flow_urn = client_id.Add("flows").Add(flow_obj.flow_id)
    for _ in flow_test_lib.TestFlowHelper(
        flow_urn,
        client_id=client_id,
        client_mock=action_mocks.FileFinderClientMock(),
        token=self.token):
      pass

    # Refresh flow.
    flow_obj = client_ref.Flow(flow_obj.flow_id).Get()
    self.assertEqual(flow_obj.data.state, flow_obj.data.TERMINATED)

    # Check that we got 3 results (we downloaded 3 files).
    results = list(flow_obj.ListResults())
    self.assertEqual(len(results), 3)
    # We expect results to be FileFinderResult.
    self.assertItemsEqual(
        [os.path.basename(r.payload.stat_entry.pathspec.path) for r in results],
        ["test.plist", "numbers.txt", "numbers.txt.ver2"])

    # Now downloads the files archive.
    zip_stream = StringIO.StringIO()
    flow_obj.GetFilesArchive().WriteToStream(zip_stream)
    zip_fd = zipfile.ZipFile(zip_stream)

    # Now check that the archive has only "test.plist" file, as it's the
    # only file that matches the whitelist (see FILE_FINDER_ROUTER_CONFIG).
    # There should be 3 items in the archive: the hash of the "test.plist"
    # file, the symlink to this hash and the MANIFEST file.
    namelist = zip_fd.namelist()
    self.assertEqual(len(namelist), 3)

    # First component of every path in the archive is the containing folder,
    # we should strip it.
    namelist = [os.path.join(*n.split(os.sep)[1:]) for n in namelist]
    self.assertEqual(
        sorted([
            # pyformat: disable
            os.path.join(self.client_id.Basename(), "fs", "os",
                         self.base_path.strip("/"), "test.plist"),
            os.path.join(self.client_id.Basename(), "client_info.yaml"),
            "MANIFEST"
            # pyformat: enable
        ]),
        sorted(namelist))

  def testCheckingArbitraryFlowStateDoesNotWork(self):
    self.InitRouterConfig(
        self.__class__.FILE_FINDER_ROUTER_CONFIG % self.token.username)
    flow_urn = flow.GRRFlow.StartFlow(
        client_id=self.client_id,
        flow_name=file_finder.FileFinder.__name__,
        token=self.token)

    flow_ref = self.api.Client(client_id=self.client_id.Basename()).Flow(
        flow_urn.Basename())
    with self.assertRaises(RuntimeError):
      flow_ref.Get()

  def testNoThrottlingDoneByDefault(self):
    self.InitRouterConfig(
        self.__class__.FILE_FINDER_ROUTER_CONFIG % self.token.username)

    args = rdf_file_finder.FileFinderArgs(
        action=rdf_file_finder.FileFinderAction(action_type="STAT"),
        paths=["tests.plist"]).AsPrimitiveProto()

    client_ref = self.api.Client(client_id=self.client_id.Basename())

    # Create 60 flows in a row to check that no throttling is applied.
    for _ in range(20):
      flow_obj = client_ref.CreateFlow(
          name=file_finder.FileFinder.__name__, args=args)
      self.assertEqual(flow_obj.data.state, flow_obj.data.RUNNING)

  FILE_FINDER_THROTTLED_ROUTER_CONFIG = """
router: "ApiCallRobotRouter"
router_params:
  file_finder_flow:
    enabled: True
    max_flows_per_client_daily: 2
    min_interval_between_duplicate_flows: 1h
  robot_id: "TheRobot"
users:
  - "%s"
"""

  def testFileFinderThrottlingByFlowCountWorks(self):
    self.InitRouterConfig(self.__class__.FILE_FINDER_THROTTLED_ROUTER_CONFIG %
                          self.token.username)

    args = []
    for p in ["tests.plist", "numbers.txt", "numbers.txt.ver2"]:
      args.append(
          rdf_file_finder.FileFinderArgs(
              action=rdf_file_finder.FileFinderAction(action_type="STAT"),
              paths=[p]).AsPrimitiveProto())

    client_ref = self.api.Client(client_id=self.client_id.Basename())

    flow_obj = client_ref.CreateFlow(
        name=file_finder.FileFinder.__name__, args=args[0])
    self.assertEqual(flow_obj.data.state, flow_obj.data.RUNNING)

    flow_obj = client_ref.CreateFlow(
        name=file_finder.FileFinder.__name__, args=args[1])
    self.assertEqual(flow_obj.data.state, flow_obj.data.RUNNING)

    with self.assertRaisesRegexp(RuntimeError, "2 flows run since"):
      client_ref.CreateFlow(name=file_finder.FileFinder.__name__, args=args[2])

  def testFileFinderThrottlingByDuplicateIntervalWorks(self):
    self.InitRouterConfig(self.__class__.FILE_FINDER_THROTTLED_ROUTER_CONFIG %
                          self.token.username)

    args = rdf_file_finder.FileFinderArgs(
        action=rdf_file_finder.FileFinderAction(action_type="STAT"),
        paths=["tests.plist"]).AsPrimitiveProto()

    client_ref = self.api.Client(client_id=self.client_id.Basename())

    flow_obj = client_ref.CreateFlow(
        name=file_finder.FileFinder.__name__, args=args)
    self.assertEqual(flow_obj.data.state, flow_obj.data.RUNNING)

    flow_obj_2 = client_ref.CreateFlow(
        name=file_finder.FileFinder.__name__, args=args)
    self.assertEqual(flow_obj.flow_id, flow_obj_2.flow_id)

  FILE_FINDER_MAX_SIZE_OVERRIDE_CONFIG = """
router: "ApiCallRobotRouter"
router_params:
  file_finder_flow:
    enabled: True
    max_file_size: 5000000
  robot_id: "TheRobot"
users:
  - "%s"
"""

  def testFileFinderMaxFileSizeOverrideWorks(self):
    self.InitRouterConfig(self.__class__.FILE_FINDER_MAX_SIZE_OVERRIDE_CONFIG %
                          self.token.username)

    args = rdf_file_finder.FileFinderArgs(
        action=rdf_file_finder.FileFinderAction(action_type="DOWNLOAD"),
        paths=["tests.plist"]).AsPrimitiveProto()

    client_ref = self.api.Client(client_id=self.client_id.Basename())

    flow_obj = client_ref.CreateFlow(
        name=file_finder.FileFinder.__name__, args=args)
    flow_args = self.api.types.UnpackAny(flow_obj.data.args)
    self.assertEqual(flow_args.action.download.max_size, 5000000)
    self.assertEqual(flow_args.action.download.oversized_file_policy,
                     flow_args.action.download.SKIP)


def main(argv):
  test_lib.main(argv)


if __name__ == "__main__":
  flags.StartMain(main)
