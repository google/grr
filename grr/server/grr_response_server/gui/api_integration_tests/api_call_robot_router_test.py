#!/usr/bin/env python
"""API E2E tests for ApiCallRobotRouter."""

import io
import os
import zipfile

from absl import app

from grr_api_client import errors
from grr_response_core.lib.rdfvalues import file_finder as rdf_file_finder
from grr_response_server.flows.general import file_finder
from grr_response_server.flows.general import processes
from grr_response_server.gui import api_auth_manager
from grr_response_server.gui import api_call_robot_router
from grr_response_server.gui import api_integration_test_lib
from grr.test_lib import action_mocks
from grr.test_lib import flow_test_lib
from grr.test_lib import test_lib


ROBOT_ROUTER_NAME = api_call_robot_router.ApiCallRobotRouter.__name__


class ApiCallRobotRouterE2ETest(api_integration_test_lib.ApiIntegrationTest):

  FILE_FINDER_ROUTER_CONFIG = """
router: "{0}"
router_params:
  file_finder_flow:
    enabled: True
  get_flow:
    enabled: True
  list_flow_results:
    enabled: True
  get_flow_files_archive:
    enabled: True
    include_only_path_globs:
      - "/**/*.plist"
users:
  - "%s"
""".format(ROBOT_ROUTER_NAME)

  def InitRouterConfig(self, router_config):
    router_config_file = os.path.join(self.temp_dir, "api_acls.yaml")
    with io.open(router_config_file, mode="w", encoding="utf-8") as fd:
      fd.write(router_config)

    config_overrider = test_lib.ConfigOverrider(
        {"API.RouterACLConfigFile": router_config_file}
    )
    config_overrider.Start()
    self.addCleanup(config_overrider.Stop)

    # Force creation of new APIAuthorizationManager, so that configuration
    # changes are picked up.
    api_auth_manager.InitializeApiAuthManager()

  def setUp(self):
    super().setUp()
    self.client_id = self.SetupClient(0)

  def testCreatingArbitraryFlowDoesNotWork(self):
    self.InitRouterConfig(
        self.__class__.FILE_FINDER_ROUTER_CONFIG % self.test_username
    )

    client_ref = self.api.Client(client_id=self.client_id)
    with self.assertRaises(errors.AccessForbiddenError):
      client_ref.CreateFlow(name=processes.ListProcesses.__name__)

  def testFileFinderWorkflowWorks(self):
    self.InitRouterConfig(
        self.__class__.FILE_FINDER_ROUTER_CONFIG % self.test_username
    )

    client_ref = self.api.Client(client_id=self.client_id)

    args = rdf_file_finder.FileFinderArgs(
        paths=[
            os.path.join(self.base_path, "test.plist"),
            os.path.join(self.base_path, "numbers.txt"),
            os.path.join(self.base_path, "numbers.txt.ver2"),
        ],
        action=rdf_file_finder.FileFinderAction.Download(),
    ).AsPrimitiveProto()
    flow_obj = client_ref.CreateFlow(
        name=file_finder.FileFinder.__name__, args=args
    )
    self.assertEqual(flow_obj.data.state, flow_obj.data.RUNNING)

    # Now run the flow we just started.
    flow_test_lib.RunFlow(
        flow_obj.client_id,
        flow_obj.flow_id,
        client_mock=action_mocks.FileFinderClientMock(),
    )

    # Refresh flow.
    flow_obj = client_ref.Flow(flow_obj.flow_id).Get()
    self.assertEqual(flow_obj.data.state, flow_obj.data.TERMINATED)

    # Check that we got 3 results (we downloaded 3 files).
    results = list(flow_obj.ListResults())
    self.assertLen(results, 3)
    # We expect results to be FileFinderResult.
    self.assertCountEqual(
        [os.path.basename(r.payload.stat_entry.pathspec.path) for r in results],
        ["test.plist", "numbers.txt", "numbers.txt.ver2"],
    )

    # Now downloads the files archive.
    zip_stream = io.BytesIO()
    flow_obj.GetFilesArchive().WriteToStream(zip_stream)
    zip_fd = zipfile.ZipFile(zip_stream)

    # Now check that the archive has only "test.plist" file, as it's the
    # only file that matches the includelist (see FILE_FINDER_ROUTER_CONFIG).
    # There should be 3 items in the archive: the hash of the "test.plist"
    # file, the symlink to this hash and the MANIFEST file.
    namelist = zip_fd.namelist()
    self.assertLen(namelist, 3)

    # First component of every path in the archive is the containing folder,
    # we should strip it.
    namelist = [os.path.join(*n.split(os.sep)[1:]) for n in namelist]
    self.assertCountEqual(
        [
            # pyformat: disable
            os.path.join(self.client_id, "fs", "os", self.base_path.strip("/"),
                         "test.plist"),
            os.path.join(self.client_id, "client_info.yaml"),
            "MANIFEST"
            # pyformat: enable
        ],
        namelist,
    )

  def testCheckingArbitraryFlowStateDoesNotWork(self):
    self.InitRouterConfig(
        self.__class__.FILE_FINDER_ROUTER_CONFIG % self.test_username
    )
    flow_id = flow_test_lib.StartFlow(
        flow_cls=file_finder.FileFinder, client_id=self.client_id
    )

    flow_ref = self.api.Client(client_id=self.client_id).Flow(flow_id)
    with self.assertRaises(errors.AccessForbiddenError):
      flow_ref.Get()

  def testNoThrottlingDoneByDefault(self):
    self.InitRouterConfig(
        self.__class__.FILE_FINDER_ROUTER_CONFIG % self.test_username
    )

    args = rdf_file_finder.FileFinderArgs(
        action=rdf_file_finder.FileFinderAction(action_type="STAT"),
        paths=["tests.plist"],
    ).AsPrimitiveProto()

    client_ref = self.api.Client(client_id=self.client_id)

    # Create 60 flows in a row to check that no throttling is applied.
    for _ in range(20):
      flow_obj = client_ref.CreateFlow(
          name=file_finder.FileFinder.__name__, args=args
      )
      self.assertEqual(flow_obj.data.state, flow_obj.data.RUNNING)

  FILE_FINDER_THROTTLED_ROUTER_CONFIG = """
router: "{0}"
router_params:
  file_finder_flow:
    enabled: True
    max_flows_per_client_daily: 2
    min_interval_between_duplicate_flows: !duration_seconds "1h"
users:
  - "%s"
""".format(ROBOT_ROUTER_NAME)

  def testFileFinderThrottlingByFlowCountWorks(self):
    self.InitRouterConfig(
        self.__class__.FILE_FINDER_THROTTLED_ROUTER_CONFIG % self.test_username
    )

    args = []
    for p in ["tests.plist", "numbers.txt", "numbers.txt.ver2"]:
      args.append(
          rdf_file_finder.FileFinderArgs(
              action=rdf_file_finder.FileFinderAction(action_type="STAT"),
              paths=[p],
          ).AsPrimitiveProto()
      )

    client_ref = self.api.Client(client_id=self.client_id)

    flow_obj = client_ref.CreateFlow(
        name=file_finder.FileFinder.__name__, args=args[0]
    )
    self.assertEqual(flow_obj.data.state, flow_obj.data.RUNNING)

    flow_obj = client_ref.CreateFlow(
        name=file_finder.FileFinder.__name__, args=args[1]
    )
    self.assertEqual(flow_obj.data.state, flow_obj.data.RUNNING)

    with self.assertRaisesRegex(
        errors.ResourceExhaustedError, "2 flows run since"
    ):
      client_ref.CreateFlow(name=file_finder.FileFinder.__name__, args=args[2])

  def testFileFinderThrottlingByDuplicateIntervalWorks(self):
    self.InitRouterConfig(
        self.__class__.FILE_FINDER_THROTTLED_ROUTER_CONFIG % self.test_username
    )

    args = rdf_file_finder.FileFinderArgs(
        action=rdf_file_finder.FileFinderAction(action_type="STAT"),
        paths=["tests.plist"],
    ).AsPrimitiveProto()

    client_ref = self.api.Client(client_id=self.client_id)

    flow_obj = client_ref.CreateFlow(
        name=file_finder.FileFinder.__name__, args=args
    )
    self.assertEqual(flow_obj.data.state, flow_obj.data.RUNNING)

    flow_obj_2 = client_ref.CreateFlow(
        name=file_finder.FileFinder.__name__, args=args
    )
    self.assertEqual(flow_obj.flow_id, flow_obj_2.flow_id)

  FILE_FINDER_MAX_SIZE_OVERRIDE_CONFIG = """
router: "{0}"
router_params:
  file_finder_flow:
    enabled: True
    max_file_size: 5000000
users:
  - "%s"
""".format(ROBOT_ROUTER_NAME)

  def testFileFinderMaxFileSizeOverrideWorks(self):
    self.InitRouterConfig(
        self.__class__.FILE_FINDER_MAX_SIZE_OVERRIDE_CONFIG % self.test_username
    )

    args = rdf_file_finder.FileFinderArgs(
        action=rdf_file_finder.FileFinderAction(action_type="DOWNLOAD"),
        paths=["tests.plist"],
    ).AsPrimitiveProto()

    client_ref = self.api.Client(client_id=self.client_id)

    flow_obj = client_ref.CreateFlow(
        name=file_finder.FileFinder.__name__, args=args
    )
    flow_args = self.api.types.UnpackAny(flow_obj.data.args)
    self.assertEqual(flow_args.action.download.max_size, 5000000)
    self.assertEqual(
        flow_args.action.download.oversized_file_policy,
        flow_args.action.download.SKIP,
    )


def main(argv):
  test_lib.main(argv)


if __name__ == "__main__":
  app.run(main)
