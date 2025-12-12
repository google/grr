#!/usr/bin/env python
"""Test the webhistory flows."""

from unittest import mock

from absl import app

from grr_response_core.lib.rdfvalues import client as rdf_client
from grr_response_proto import flows_pb2
from grr_response_proto import jobs_pb2
from grr_response_server import flow_base
from grr_response_server.databases import db
from grr_response_server.flows.general import collectors
from grr_response_server.flows.general import webhistory
from grr.test_lib import action_mocks
from grr.test_lib import flow_test_lib
from grr.test_lib import test_lib


class TestWebHistoryWithArtifacts(flow_test_lib.FlowTestsBaseclass):

  def setUp(self):
    super().setUp()
    users = [
        rdf_client.User(
            username="test",
            full_name="test user",
            homedir="/home/test",
            last_logon=250,
        )
    ]
    self.client_id = self.SetupClient(
        0, system="Linux", os_version="12.04", users=users
    )
    self.client_mock = action_mocks.FileFinderClientMock()


class MockArtifactCollectorFlow(collectors.ArtifactCollectorFlow):

  def Start(self):
    for artifact_name in self.args.artifact_list:
      self.SendReplyProto(
          jobs_pb2.StatEntry(
              pathspec=jobs_pb2.PathSpec(
                  pathtype=jobs_pb2.PathSpec.PathType.OS,
                  path=f"/home/foo/{artifact_name}",
              )
          )
      )


class MockArtifactCollectorFlowWithDuplicatesAndExtensions(
    collectors.ArtifactCollectorFlow
):
  """Mock artifact collector flow for archive mapping tests."""

  def Start(self):
    for artifact_name in self.args.artifact_list:
      self.SendReplyProto(
          jobs_pb2.StatEntry(
              pathspec=jobs_pb2.PathSpec(
                  pathtype=jobs_pb2.PathSpec.PathType.OS,
                  path=f"/home/foo/{artifact_name}.tmp",
              )
          )
      )
      self.SendReplyProto(
          jobs_pb2.StatEntry(
              pathspec=jobs_pb2.PathSpec(
                  pathtype=jobs_pb2.PathSpec.PathType.OS,
                  path=f"/home/foo/{artifact_name}.tmp",
              )
          )
      )


class CollectBrowserHistoryTest(flow_test_lib.FlowTestsBaseclass):

  def setUp(self):
    super().setUp()
    self.client_id = self.SetupClient(0)

  def _RunCollectBrowserHistory(self, **kwargs):
    flow_args = webhistory.CollectBrowserHistoryArgs(**kwargs)
    flow_id = flow_test_lib.StartAndRunFlow(
        webhistory.CollectBrowserHistory,
        creator=self.test_username,
        client_mock=action_mocks.ActionMock(),
        client_id=self.client_id,
        flow_args=flow_args,
    )

    results = flow_test_lib.GetFlowResults(self.client_id, flow_id)
    progress = flow_test_lib.GetFlowProgress(self.client_id, flow_id)

    return flow_id, results, progress

  def _CheckProgressNotSetExceptForOne(self, progress, browser):
    self.assertLen(progress.browsers, 1)
    self.assertEqual(progress.browsers[0].browser, browser)
    self.assertEqual(
        progress.browsers[0].status, flows_pb2.BrowserProgress.Status.SUCCESS
    )

  def testCollectsChromeArtifacts(self):
    with mock.patch.object(
        collectors, "ArtifactCollectorFlow", MockArtifactCollectorFlow
    ):
      flow_id, results, progress = self._RunCollectBrowserHistory(
          browsers=[flows_pb2.Browser.CHROMIUM_BASED_BROWSERS]
      )

    self.assertLen(results, 1)
    self.assertEqual(
        results[0].browser, flows_pb2.Browser.CHROMIUM_BASED_BROWSERS
    )
    self.assertEqual(
        ["/home/foo/ChromiumBasedBrowsersHistoryDatabaseFile"],
        [r.stat_entry.pathspec.path for r in results],
    )
    self.assertEqual(
        list(flow_test_lib.GetFlowResultsByTag(self.client_id, flow_id).keys()),
        ["CHROMIUM_BASED_BROWSERS"],
    )

    self.assertLen(progress.browsers, 1)
    self.assertEqual(
        progress.browsers[0].browser, flows_pb2.Browser.CHROMIUM_BASED_BROWSERS
    )
    self.assertEqual(
        progress.browsers[0].status, flows_pb2.BrowserProgress.Status.SUCCESS
    )
    self.assertEqual(progress.browsers[0].num_collected_files, 1)

  def testCollectsChromeInternetExplorerAndSafariArtifacts(self):
    with mock.patch.object(
        collectors, "ArtifactCollectorFlow", MockArtifactCollectorFlow
    ):
      flow_id, results, progress = self._RunCollectBrowserHistory(
          browsers=[
              flows_pb2.Browser.CHROMIUM_BASED_BROWSERS,
              flows_pb2.Browser.INTERNET_EXPLORER,
              flows_pb2.Browser.SAFARI,
          ]
      )

    # MockArtifactCollectorFlow will produce a single stat entry with a
    # pathspec /home/foo/<artifact name> for each artifact scheduled for
    # collection. Hence, by looking at results we can make sure that
    # all artifacts were scheduled for collection.
    pathspecs = [r.stat_entry.pathspec for r in results]
    self.assertCountEqual(
        [
            "ChromiumBasedBrowsersHistoryDatabaseFile",
            "InternetExplorerHistory",
            "SafariHistory",
        ],
        [p.Basename() for p in pathspecs],
    )
    # Check that tags for all browsers are present in the results set.
    self.assertCountEqual(
        flow_test_lib.GetFlowResultsByTag(self.client_id, flow_id).keys(),
        ["CHROMIUM_BASED_BROWSERS", "INTERNET_EXPLORER", "SAFARI"],
    )

    self.assertLen(progress.browsers, 3)
    self.assertCountEqual(
        [
            flows_pb2.Browser.CHROMIUM_BASED_BROWSERS,
            flows_pb2.Browser.INTERNET_EXPLORER,
            flows_pb2.Browser.SAFARI,
        ],
        [bp.browser for bp in progress.browsers],
    )
    for bp in progress.browsers:
      self.assertEqual(bp.status, flows_pb2.BrowserProgress.Status.SUCCESS)
      self.assertEqual(bp.num_collected_files, 1)

  def testCorrectlyGeneratesArchiveMappings(self):
    with mock.patch.object(
        collectors, "ArtifactCollectorFlow", MockArtifactCollectorFlow
    ):
      flow_id, _, _ = self._RunCollectBrowserHistory(
          browsers=[
              flows_pb2.Browser.CHROMIUM_BASED_BROWSERS,
              flows_pb2.Browser.SAFARI,
          ]
      )
      flow = flow_base.FlowBase.CreateFlowInstance(
          flow_test_lib.GetFlowObj(self.client_id, flow_id)
      )
      results = flow_test_lib.GetRawFlowResults(self.client_id, flow_id)

      mappings = flow.GetFilesArchiveMappings(results)

    self.assertCountEqual(
        mappings,
        [
            flow_base.ClientPathArchiveMapping(
                db.ClientPath.OS(
                    self.client_id,
                    ("home", "foo", "ChromiumBasedBrowsersHistoryDatabaseFile"),
                ),
                "chromium_based_browsers/home_foo_ChromiumBasedBrowsersHistoryDatabaseFile",
            ),
            flow_base.ClientPathArchiveMapping(
                db.ClientPath.OS(
                    self.client_id, ("home", "foo", "SafariHistory")
                ),
                "safari/home_foo_SafariHistory",
            ),
        ],
    )

  def testCorrectlyGeneratesArchiveMappingsForDuplicateFiles(self):
    with mock.patch.object(
        collectors,
        "ArtifactCollectorFlow",
        MockArtifactCollectorFlowWithDuplicatesAndExtensions,
    ):
      flow_id, _, _ = self._RunCollectBrowserHistory(
          browsers=[
              flows_pb2.Browser.CHROMIUM_BASED_BROWSERS,
          ]
      )
      flow = flow_base.FlowBase.CreateFlowInstance(
          flow_test_lib.GetFlowObj(self.client_id, flow_id)
      )
      results = flow_test_lib.GetRawFlowResults(self.client_id, flow_id)

      mappings = flow.GetFilesArchiveMappings(results)

    self.assertCountEqual(
        mappings,
        [
            flow_base.ClientPathArchiveMapping(
                db.ClientPath.OS(
                    self.client_id,
                    (
                        "home",
                        "foo",
                        "ChromiumBasedBrowsersHistoryDatabaseFile.tmp",
                    ),
                ),
                "chromium_based_browsers/home_foo_ChromiumBasedBrowsersHistoryDatabaseFile.tmp",
            ),
            flow_base.ClientPathArchiveMapping(
                db.ClientPath.OS(
                    self.client_id,
                    (
                        "home",
                        "foo",
                        "ChromiumBasedBrowsersHistoryDatabaseFile.tmp",
                    ),
                ),
                "chromium_based_browsers/home_foo_ChromiumBasedBrowsersHistoryDatabaseFile_1.tmp",
            ),
        ],
    )

  def testFailsForEmptyBrowsersList(self):
    with self.assertRaisesRegex(
        RuntimeError, "Need to collect at least one type of history."
    ):
      self._RunCollectBrowserHistory()


def main(argv):
  # Run the full test suite
  test_lib.main(argv)


if __name__ == "__main__":
  app.run(main)
