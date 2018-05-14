#!/usr/bin/env python
"""API E2E tests for ApiCallRobotRouter."""

import os
import StringIO
import zipfile


from grr.lib import flags
from grr.lib.rdfvalues import client as rdf_client

from grr.lib.rdfvalues import file_finder as rdf_file_finder
from grr.server.grr_response_server import flow
from grr.server.grr_response_server.flows.general import file_finder
from grr.server.grr_response_server.flows.general import processes
from grr.server.grr_response_server.gui import api_auth_manager
from grr.server.grr_response_server.gui import api_e2e_test_lib

from grr.test_lib import action_mocks
from grr.test_lib import flow_test_lib
from grr.test_lib import test_lib


class ApiCallRobotRouterE2ETest(api_e2e_test_lib.ApiE2ETest):

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
    flow_test_lib.TestFlowHelper(
        flow_urn,
        client_id=client_id,
        client_mock=action_mocks.FileFinderClientMock(),
        token=self.token)

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
