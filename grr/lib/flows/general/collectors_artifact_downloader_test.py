#!/usr/bin/env python
"""Tests for grr.lib.flows.general.collectors.

These test cover the artifact downloader functionality which downloads files
referenced by artifacts.
"""

from grr.lib import aff4
from grr.lib import artifact
from grr.lib import flags
from grr.lib import flow
from grr.lib import test_lib
from grr.lib import utils
from grr.lib.aff4_objects import collects
# pylint: disable=unused-import
from grr.lib.flows.general import artifact_fallbacks
from grr.lib.flows.general import collectors
# pylint: enable=unused-import
from grr.lib.flows.general import transfer
from grr.lib.rdfvalues import client as rdf_client
from grr.lib.rdfvalues import paths as rdf_paths
from grr.lib.rdfvalues import protodict as rdf_protodict


class ArtifactFilesDownloaderFlowTest(test_lib.FlowTestsBaseclass):

  def setUp(self):
    super(ArtifactFilesDownloaderFlowTest, self).setUp()

    with aff4.FACTORY.Open(self.client_id, token=self.token, mode="rw") as fd:
      fd.Set(fd.Schema.SYSTEM("Windows"))
      kb = fd.Schema.KNOWLEDGE_BASE()
      artifact.SetCoreGRRKnowledgeBaseValues(kb, fd)
      fd.Set(kb)

    self.output_path = "analysis/artifact_files_downloader"
    self.stubbers = []

    self.collector_replies = []

    def ArtifactCollectorStub(this):
      for r in self.collector_replies:
        this.SendReply(r)

    stubber = utils.Stubber(collectors.ArtifactCollectorFlow, "Start",
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

    stubber = utils.Stubber(transfer.MultiGetFileMixin, "StartFileFetch",
                            StartFileFetch)
    stubber.Start()
    self.stubbers.append(stubber)

  def tearDown(self):
    super(ArtifactFilesDownloaderFlowTest, self).tearDown()

    for stubber in self.stubbers:
      stubber.Stop()

  def RunFlow(self, artifact_list=None, use_tsk=False):
    if artifact_list is None:
      artifact_list = ["WindowsRunKeys"]

    urn = flow.GRRFlow.StartFlow(
        flow_name="ArtifactFilesDownloaderFlow",
        client_id=self.client_id,
        artifact_list=artifact_list,
        use_tsk=use_tsk,
        output=self.output_path,
        token=self.token)
    for _ in test_lib.TestFlowHelper(urn, token=self.token):
      pass

    try:
      results_fd = aff4.FACTORY.Open(
          self.client_id.Add(self.output_path),
          aff4_type=collects.RDFValueCollection,
          token=self.token)
      return list(results_fd)
    except aff4.InstantiationError:
      return []

  def MakeRegistryStatEntry(self, path, value):
    options = rdf_paths.PathSpec.Options.CASE_LITERAL
    pathspec = rdf_paths.PathSpec(
        path=path,
        path_options=options,
        pathtype=rdf_paths.PathSpec.PathType.REGISTRY)

    return rdf_client.StatEntry(
        aff4path=self.client_id.Add("registry").Add(path),
        pathspec=pathspec,
        registry_data=rdf_protodict.DataBlob().SetValue(value),
        registry_type=rdf_client.StatEntry.RegistryType.REG_SZ)

  def MakeFileStatEntry(self, path):
    pathspec = rdf_paths.PathSpec(path=path, pathtype="OS")
    return rdf_client.StatEntry(pathspec=pathspec)

  def testDoesNothingIfArtifactCollectorReturnsNothing(self):
    self.RunFlow()
    self.assertFalse(self.start_file_fetch_args)

  def testDoesNotIssueDownloadRequestsIfNoPathIsGuessed(self):
    self.collector_replies = [self.MakeRegistryStatEntry(
        u"HKEY_LOCAL_MACHINE\\SOFTWARE\\foo", u"blah-blah")]
    self.RunFlow()
    self.assertFalse(self.start_file_fetch_args)

  def testJustUsesPathSpecForFileStatEntry(self):
    self.collector_replies = [self.MakeFileStatEntry("C:\\Windows\\bar.exe")]
    self.failed_files = [self.collector_replies[0].pathspec]

    results = self.RunFlow()

    self.assertEquals(len(results), 1)
    self.assertEquals(results[0].found_pathspec,
                      self.collector_replies[0].pathspec)

  def testSendsReplyEvenIfNoPathsAreGuessed(self):
    self.collector_replies = [self.MakeRegistryStatEntry(
        u"HKEY_LOCAL_MACHINE\\SOFTWARE\\foo", u"blah-blah")]

    results = self.RunFlow()

    self.assertEquals(len(results), 1)
    self.assertEquals(results[0].original_result, self.collector_replies[0])
    self.assertFalse(results[0].HasField("found_pathspec"))
    self.assertFalse(results[0].HasField("downloaded_file"))

  def testIncludesGuessedPathspecIfFileFetchFailsIntoReply(self):
    self.collector_replies = [self.MakeRegistryStatEntry(
        u"HKEY_LOCAL_MACHINE\\SOFTWARE\\foo", u"C:\\Windows\\bar.exe")]
    self.failed_files = [rdf_paths.PathSpec(
        path="C:\\Windows\\bar.exe", pathtype="OS")]

    results = self.RunFlow()

    self.assertEquals(len(results), 1)
    self.assertEquals(
        results[0].found_pathspec,
        rdf_paths.PathSpec(
            path="C:\\Windows\\bar.exe", pathtype="OS"))
    self.assertFalse(results[0].HasField("downloaded_file"))

  def testIncludesDownloadedFilesIntoReplyIfFetchSucceeds(self):
    self.collector_replies = [self.MakeRegistryStatEntry(
        u"HKEY_LOCAL_MACHINE\\SOFTWARE\\foo", u"C:\\Windows\\bar.exe")]
    self.received_files = [self.MakeFileStatEntry("C:\\Windows\\bar.exe")]

    results = self.RunFlow()

    self.assertEquals(len(results), 1)
    self.assertEquals(results[0].downloaded_file, self.received_files[0])


def main(argv):
  # Run the full test suite
  test_lib.GrrTestProgram(argv=argv)


if __name__ == "__main__":
  flags.StartMain(main)
