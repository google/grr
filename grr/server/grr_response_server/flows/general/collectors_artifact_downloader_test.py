#!/usr/bin/env python
"""Tests for grr_response_server.flows.general.collectors.

These test cover the artifact downloader functionality which downloads files
referenced by artifacts.
"""
from unittest import mock

from absl import app

from grr_response_core.lib.rdfvalues import client_fs as rdf_client_fs
from grr_response_core.lib.rdfvalues import paths as rdf_paths
from grr_response_core.lib.rdfvalues import protodict as rdf_protodict
from grr_response_server.flows.general import collectors
from grr_response_server.flows.general import transfer
from grr.test_lib import flow_test_lib
from grr.test_lib import test_lib


class ArtifactFilesDownloaderFlowTest(flow_test_lib.FlowTestsBaseclass):

  def setUp(self):
    super().setUp()

    self.collector_replies = []

    def ArtifactCollectorStub(this):
      for r in self.collector_replies:
        this.SendReply(r)

    start_stubber = mock.patch.object(collectors.ArtifactCollectorFlow, "Start",
                                      ArtifactCollectorStub)
    start_stubber.start()
    self.addCleanup(start_stubber.stop)

    self.start_file_fetch_args = []
    self.received_files = []
    self.failed_files = []

    def StartFileFetch(this, pathspec, request_data=None):
      self.start_file_fetch_args.append(pathspec)

      # We had a bug where the Start method of the MultiGetFileLogic wasn't
      # called correctly so we now check that the state is set up properly.
      self.assertIn("indexed_pathspecs", this.state)

      for r in self.received_files:
        this.ReceiveFetchedFile(
            r, None, request_data=request_data, is_duplicate=False)

      for r in self.failed_files:
        this.FileFetchFailed(r, request_data=request_data)

    sff_stubber = mock.patch.object(transfer.MultiGetFileLogic,
                                    "StartFileFetch", StartFileFetch)
    sff_stubber.start()
    self.addCleanup(sff_stubber.stop)

  def RunFlow(self,
              client_id,
              artifact_list=None,
              use_raw_filesystem_access=False):
    if artifact_list is None:
      artifact_list = ["WindowsRunKeys"]

    session_id = flow_test_lib.TestFlowHelper(
        collectors.ArtifactFilesDownloaderFlow.__name__,
        client_id=client_id,
        artifact_list=artifact_list,
        use_raw_filesystem_access=use_raw_filesystem_access,
        creator=self.test_username)

    return flow_test_lib.GetFlowResults(client_id, session_id)

  def MakeRegistryStatEntry(self, path, value):
    options = rdf_paths.PathSpec.Options.CASE_LITERAL
    pathspec = rdf_paths.PathSpec(
        path=path,
        path_options=options,
        pathtype=rdf_paths.PathSpec.PathType.REGISTRY)

    return rdf_client_fs.StatEntry(
        pathspec=pathspec,
        registry_data=rdf_protodict.DataBlob().SetValue(value),
        registry_type=rdf_client_fs.StatEntry.RegistryType.REG_SZ)

  def MakeFileStatEntry(self, path):
    pathspec = rdf_paths.PathSpec(path=path, pathtype="OS")
    return rdf_client_fs.StatEntry(pathspec=pathspec)

  def testDoesNothingIfArtifactCollectorReturnsNothing(self):
    client_id = self.SetupClient(0)
    self.RunFlow(client_id)
    self.assertFalse(self.start_file_fetch_args)

  def testDoesNotIssueDownloadRequestsIfNoPathIsGuessed(self):
    client_id = self.SetupClient(0)
    self.collector_replies = [
        self.MakeRegistryStatEntry(u"HKEY_LOCAL_MACHINE\\SOFTWARE\\foo",
                                   u"blah-blah")
    ]
    self.RunFlow(client_id)
    self.assertFalse(self.start_file_fetch_args)

  def testJustUsesPathSpecForFileStatEntry(self):
    client_id = self.SetupClient(0)
    self.collector_replies = [self.MakeFileStatEntry("C:\\Windows\\bar.exe")]
    self.failed_files = [self.collector_replies[0].pathspec]

    results = self.RunFlow(client_id)

    self.assertLen(results, 1)
    self.assertEqual(results[0].found_pathspec,
                     self.collector_replies[0].pathspec)

  def testSendsReplyEvenIfNoPathsAreGuessed(self):
    client_id = self.SetupClient(0)
    self.collector_replies = [
        self.MakeRegistryStatEntry(u"HKEY_LOCAL_MACHINE\\SOFTWARE\\foo",
                                   u"blah-blah")
    ]

    results = self.RunFlow(client_id)

    self.assertLen(results, 1)
    self.assertEqual(results[0].original_result, self.collector_replies[0])
    self.assertFalse(results[0].HasField("found_pathspec"))
    self.assertFalse(results[0].HasField("downloaded_file"))

  def testIncludesGuessedPathspecIfFileFetchFailsIntoReply(self):
    client_id = self.SetupClient(0)
    self.collector_replies = [
        self.MakeRegistryStatEntry(u"HKEY_LOCAL_MACHINE\\SOFTWARE\\foo",
                                   u"C:\\Windows\\bar.exe")
    ]
    self.failed_files = [
        rdf_paths.PathSpec(path="C:\\Windows\\bar.exe", pathtype="OS")
    ]

    results = self.RunFlow(client_id)

    self.assertLen(results, 1)
    self.assertEqual(
        results[0].found_pathspec,
        rdf_paths.PathSpec(path="C:\\Windows\\bar.exe", pathtype="OS"))
    self.assertFalse(results[0].HasField("downloaded_file"))

  def testIncludesDownloadedFilesIntoReplyIfFetchSucceeds(self):
    client_id = self.SetupClient(0)
    self.collector_replies = [
        self.MakeRegistryStatEntry(u"HKEY_LOCAL_MACHINE\\SOFTWARE\\foo",
                                   u"C:\\Windows\\bar.exe")
    ]
    self.received_files = [self.MakeFileStatEntry("C:\\Windows\\bar.exe")]

    results = self.RunFlow(client_id)

    self.assertLen(results, 1)
    self.assertEqual(results[0].downloaded_file, self.received_files[0])


def main(argv):
  # Run the full test suite
  test_lib.main(argv)


if __name__ == "__main__":
  app.run(main)
