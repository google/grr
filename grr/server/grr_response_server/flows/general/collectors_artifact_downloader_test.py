#!/usr/bin/env python
"""Tests for grr_response_server.flows.general.collectors.

These test cover the artifact downloader functionality which downloads files
referenced by artifacts.
"""
from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

from grr_response_core.lib import flags
from grr_response_core.lib import utils
from grr_response_core.lib.rdfvalues import client_fs as rdf_client_fs
from grr_response_core.lib.rdfvalues import paths as rdf_paths
from grr_response_core.lib.rdfvalues import protodict as rdf_protodict
from grr_response_server.flows.general import collectors
from grr_response_server.flows.general import transfer
from grr.test_lib import db_test_lib
from grr.test_lib import flow_test_lib
from grr.test_lib import test_lib


@db_test_lib.DualDBTest
class ArtifactFilesDownloaderFlowTest(flow_test_lib.FlowTestsBaseclass):

  def setUp(self):
    super(ArtifactFilesDownloaderFlowTest, self).setUp()

    self.stubbers = []

    self.collector_replies = []

    def ArtifactCollectorStub(this):
      for r in self.collector_replies:
        this.SendReply(r)

    stubber = utils.Stubber(collectors.ArtifactCollectorFlowMixin, "Start",
                            ArtifactCollectorStub)
    stubber.Start()
    self.stubbers.append(stubber)

    self.start_file_fetch_args = []
    self.received_files = []
    self.failed_files = []

    def StartFileFetch(this, pathspec, request_data=None):
      self.start_file_fetch_args.append(pathspec)

      for r in self.received_files:
        this.ReceiveFetchedFile(r, None, request_data=request_data)

      for r in self.failed_files:
        this.FileFetchFailed(pathspec, "StatFile", request_data=request_data)

    stubber = utils.Stubber(transfer.MultiGetFileLogic, "StartFileFetch",
                            StartFileFetch)
    stubber.Start()
    self.stubbers.append(stubber)

  def tearDown(self):
    super(ArtifactFilesDownloaderFlowTest, self).tearDown()

    for stubber in self.stubbers:
      stubber.Stop()

  def RunFlow(self, client_id, artifact_list=None, use_tsk=False):
    if artifact_list is None:
      artifact_list = ["WindowsRunKeys"]

    session_id = flow_test_lib.TestFlowHelper(
        collectors.ArtifactFilesDownloaderFlow.__name__,
        client_id=client_id,
        artifact_list=artifact_list,
        use_tsk=use_tsk,
        token=self.token)

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
  flags.StartMain(main)
