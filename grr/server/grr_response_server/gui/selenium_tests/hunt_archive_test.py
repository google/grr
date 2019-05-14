#!/usr/bin/env python
# -*- encoding: utf-8 -*-
"""Test the hunt_view interface."""
from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

from absl import app
import mock

from grr_response_core.lib import utils
from grr_response_core.lib.rdfvalues import client as rdf_client
from grr_response_core.lib.rdfvalues import client_fs as rdf_client_fs
from grr_response_core.lib.rdfvalues import file_finder as rdf_file_finder
from grr_response_core.lib.rdfvalues import paths as rdf_paths
from grr_response_server import aff4
from grr_response_server import data_store
from grr_response_server import file_store
from grr_response_server.flows.general import collectors
from grr_response_server.flows.general import export as flow_export
from grr_response_server.gui import archive_generator
from grr_response_server.gui import gui_test_lib
from grr.test_lib import db_test_lib
from grr.test_lib import test_lib


@db_test_lib.DualDBTest
class TestHuntArchiving(gui_test_lib.GRRSeleniumHuntTest):
  """Test the hunt archive download functionality."""

  def testDoesNotShowGenerateArchiveButtonForNonExportableRDFValues(self):
    values = [rdf_client.Process(pid=1), rdf_client.Process(pid=42423)]

    hunt_urn, _ = self.CreateGenericHuntWithCollection(values=values)
    hunt_id = hunt_urn.Basename()

    self.Open("/")
    self.Click("css=a[grrtarget=hunts]")
    self.Click("css=td:contains('%s')" % hunt_id)
    self.Click("css=li[heading=Results]")

    self.WaitUntil(self.IsTextPresent, "42423")
    self.WaitUntilNot(self.IsTextPresent,
                      "Files referenced in this collection can be downloaded")

  def testDoesNotShowGenerateArchiveButtonWhenResultCollectionIsEmpty(self):
    hunt_urn, _ = self.CreateGenericHuntWithCollection([])
    hunt_id = hunt_urn.Basename()

    self.Open("/")
    self.Click("css=a[grrtarget=hunts]")
    self.Click("css=td:contains('%s')" % hunt_id)
    self.Click("css=li[heading=Results]")

    self.WaitUntil(self.IsTextPresent, "Value")
    self.WaitUntilNot(self.IsTextPresent,
                      "Files referenced in this collection can be downloaded")

  def testShowsGenerateArchiveButtonForFileFinderHunt(self):
    stat_entry = rdf_client_fs.StatEntry(
        pathspec=rdf_paths.PathSpec(
            path="/foo/bar", pathtype=rdf_paths.PathSpec.PathType.OS))
    values = [rdf_file_finder.FileFinderResult(stat_entry=stat_entry)]

    hunt_urn, _ = self.CreateGenericHuntWithCollection(values=values)
    hunt_id = hunt_urn.Basename()

    self.Open("/")
    self.Click("css=a[grrtarget=hunts]")
    self.Click("css=td:contains('%s')" % hunt_id)
    self.Click("css=li[heading=Results]")

    self.WaitUntil(self.IsTextPresent,
                   "Files referenced in this collection can be downloaded")

  def testShowsGenerateArchiveButtonForArtifactDownloaderHunt(self):
    stat_entry = rdf_client_fs.StatEntry(
        pathspec=rdf_paths.PathSpec(
            path="/foo/bar", pathtype=rdf_paths.PathSpec.PathType.OS))
    values = [
        collectors.ArtifactFilesDownloaderResult(downloaded_file=stat_entry)
    ]

    hunt_urn, _ = self.CreateGenericHuntWithCollection(values=values)
    hunt_id = hunt_urn.Basename()

    self.Open("/")
    self.Click("css=a[grrtarget=hunts]")
    self.Click("css=td:contains('%s')" % hunt_id)
    self.Click("css=li[heading=Results]")

    self.WaitUntil(self.IsTextPresent,
                   "Files referenced in this collection can be downloaded")

  def testExportCommandIsShownForStatEntryResults(self):
    stat_entry = rdf_client_fs.StatEntry(
        pathspec=rdf_paths.PathSpec(
            path="/foo/bar", pathtype=rdf_paths.PathSpec.PathType.OS))
    values = [rdf_file_finder.FileFinderResult(stat_entry=stat_entry)]

    hunt_urn, _ = self.CreateGenericHuntWithCollection(values=values)
    hunt_id = hunt_urn.Basename()

    self.Open("/#/hunts/%s/results" % hunt_id)
    self.Click("link=Show export command")

    self.WaitUntil(
        self.IsTextPresent, "/usr/bin/grr_api_shell 'http://localhost:8000/' "
        "--exec_code 'grrapi.Hunt(\"%s\").GetFilesArchive()."
        "WriteToFile(\"./hunt_results_%s.zip\")'" %
        (hunt_urn.Basename(), hunt_urn.Basename().replace(":", "_")))

  def testExportCommandIsNotShownWhenNoResults(self):
    hunt_urn, _ = self.CreateGenericHuntWithCollection([])
    hunt_id = hunt_urn.Basename()

    self.Open("/#/hunts/%s/results" % hunt_id)
    self.WaitUntil(self.IsElementPresent,
                   "css=grr-hunt-results:contains('Value')")
    self.WaitUntilNot(self.IsTextPresent, "Show export command")

  def testExportCommandIsNotShownForNonFileResults(self):
    values = [rdf_client.Process(pid=1), rdf_client.Process(pid=42423)]

    hunt_urn, _ = self.CreateGenericHuntWithCollection(values=values)
    hunt_id = hunt_urn.Basename()

    self.Open("/#/hunts/%s/results" % hunt_id)
    self.WaitUntil(self.IsElementPresent,
                   "css=grr-hunt-results:contains('Value')")
    self.WaitUntilNot(self.IsTextPresent, "Show export command")

  def testHuntAuthorizationIsRequiredToGenerateResultsArchive(self):
    stat_entry = rdf_client_fs.StatEntry(
        pathspec=rdf_paths.PathSpec(
            path="/foo/bar", pathtype=rdf_paths.PathSpec.PathType.OS))
    values = [rdf_file_finder.FileFinderResult(stat_entry=stat_entry)]

    hunt_urn, _ = self.CreateGenericHuntWithCollection(values=values)
    hunt_id = hunt_urn.Basename()

    self.Open("/")
    self.Click("css=a[grrtarget=hunts]")
    self.Click("css=td:contains('%s')" % hunt_id)
    self.Click("css=li[heading=Results]")
    self.Click("css=button.DownloadButton")

    self.WaitUntil(self.IsTextPresent, "Create a new approval request")

  def testGenerateZipButtonGetsDisabledAfterClick(self):
    hunt_urn = self._CreateHuntWithDownloadedFile()
    hunt_id = hunt_urn.Basename()
    self.RequestAndGrantHuntApproval(hunt_id)

    self.Open("/")
    self.Click("css=a[grrtarget=hunts]")
    self.Click("css=td:contains('%s')" % hunt_id)
    self.Click("css=li[heading=Results]")
    self.Click("css=button.DownloadButton")

    self.WaitUntil(self.IsElementPresent, "css=button.DownloadButton[disabled]")
    self.WaitUntil(self.IsTextPresent, "Generation has started")

  def testShowsNotificationWhenArchiveGenerationIsDone(self):
    hunt_urn = self._CreateHuntWithDownloadedFile()
    hunt_id = hunt_urn.Basename()
    self.RequestAndGrantHuntApproval(hunt_id)

    self.Open("/")
    self.Click("css=a[grrtarget=hunts]")
    self.Click("css=td:contains('%s')" % hunt_id)
    self.Click("css=li[heading=Results]")
    self.Click("css=button.DownloadButton")
    self.WaitUntil(self.IsTextPresent, "Generation has started")

    self.WaitUntil(self.IsUserNotificationPresent,
                   "Downloaded archive of hunt %s" % hunt_id)
    # Check that the archive generating flow does not end with an error.
    self.WaitUntilNot(self.IsUserNotificationPresent, "terminated due to error")

  def testShowsErrorMessageIfArchiveStreamingFailsBeforeFirstChunkIsSent(self):
    hunt_urn = self._CreateHuntWithDownloadedFile()
    hunt_id = hunt_urn.Basename()
    self.RequestAndGrantHuntApproval(hunt_id)

    def RaisingStub(*unused_args, **unused_kwargs):
      raise RuntimeError("something went wrong")

    with utils.Stubber(archive_generator.GetCompatClass(), "Generate",
                       RaisingStub):
      self.Open("/")
      self.Click("css=a[grrtarget=hunts]")
      self.Click("css=td:contains('%s')" % hunt_id)
      self.Click("css=li[heading=Results]")
      self.Click("css=button.DownloadButton")
      self.WaitUntil(self.IsTextPresent,
                     "Can't generate archive: Unknown error")
      self.WaitUntil(self.IsUserNotificationPresent,
                     "Archive generation failed for hunt")

  def testShowsNotificationIfArchiveStreamingFailsInProgress(self):
    hunt_urn = self._CreateHuntWithDownloadedFile()
    hunt_id = hunt_urn.Basename()
    self.RequestAndGrantHuntApproval(hunt_id)

    def RaisingStub(*unused_args, **unused_kwargs):
      yield b"foo"
      yield b"bar"
      raise RuntimeError("something went wrong")

    with utils.Stubber(archive_generator.GetCompatClass(), "Generate",
                       RaisingStub):
      self.Open("/")
      self.Click("css=a[grrtarget=hunts]")
      self.Click("css=td:contains('%s')" % hunt_id)
      self.Click("css=li[heading=Results]")
      self.Click("css=button.DownloadButton")
      self.WaitUntil(self.IsUserNotificationPresent,
                     "Archive generation failed for hunt")
      # There will be no failure message, as we can't get a status from an
      # iframe that triggers the download.
      self.WaitUntilNot(self.IsTextPresent,
                        "Can't generate archive: Unknown error")

  def testDoesNotShowPerFileDownloadButtonForNonExportableRDFValues(self):
    values = [rdf_client.Process(pid=1), rdf_client.Process(pid=42423)]

    hunt_urn, _ = self.CreateGenericHuntWithCollection(values=values)
    hunt_id = hunt_urn.Basename()

    self.Open("/")
    self.Click("css=a[grrtarget=hunts]")
    self.Click("css=td:contains('%s')" % hunt_id)
    self.Click("css=li[heading=Results]")

    self.WaitUntil(self.IsTextPresent, "42423")
    self.WaitUntilNot(
        self.IsElementPresent,
        "css=grr-results-collection button:has(span.glyphicon-download)")

  def testShowsPerFileDownloadButtonForFileFinderHunt(self):
    stat_entry = rdf_client_fs.StatEntry(
        pathspec=rdf_paths.PathSpec(
            path="/foo/bar", pathtype=rdf_paths.PathSpec.PathType.OS))
    values = [rdf_file_finder.FileFinderResult(stat_entry=stat_entry)]

    hunt_urn, _ = self.CreateGenericHuntWithCollection(values=values)
    hunt_id = hunt_urn.Basename()

    self.Open("/")
    self.Click("css=a[grrtarget=hunts]")
    self.Click("css=td:contains('%s')" % hunt_id)
    self.Click("css=li[heading=Results]")

    self.WaitUntil(
        self.IsElementPresent,
        "css=grr-results-collection button:has(span.glyphicon-download)")

  def testShowsPerFileDownloadButtonForArtifactDownloaderHunt(self):
    stat_entry = rdf_client_fs.StatEntry(
        pathspec=rdf_paths.PathSpec(
            path="/foo/bar", pathtype=rdf_paths.PathSpec.PathType.OS))
    values = [
        collectors.ArtifactFilesDownloaderResult(downloaded_file=stat_entry)
    ]

    hunt_urn, _ = self.CreateGenericHuntWithCollection(values=values)
    hunt_id = hunt_urn.Basename()

    self.Open("/")
    self.Click("css=a[grrtarget=hunts]")
    self.Click("css=td:contains('%s')" % hunt_id)
    self.Click("css=li[heading=Results]")

    self.WaitUntil(
        self.IsElementPresent,
        "css=grr-results-collection button:has(span.glyphicon-download)")

  def testHuntAuthorizationIsRequiredToDownloadSingleHuntFile(self):
    hunt_urn = self._CreateHuntWithDownloadedFile()
    hunt_id = hunt_urn.Basename()

    self.Open("/")
    self.Click("css=a[grrtarget=hunts]")
    self.Click("css=td:contains('%s')" % hunt_id)
    self.Click("css=li[heading=Results]")
    self.Click("css=grr-results-collection button:has(span.glyphicon-download)")

    self.WaitUntil(self.IsTextPresent, "Create a new approval request")

  def testDownloadsSingleHuntFileIfAuthorizationIsPresent(self):
    hunt_urn = self._CreateHuntWithDownloadedFile()
    hunt_id = hunt_urn.Basename()
    results = self.GetHuntResults(hunt_urn)

    self.RequestAndGrantHuntApproval(hunt_id)

    self.Open("/")
    self.Click("css=a[grrtarget=hunts]")
    self.Click("css=td:contains('%s')" % hunt_id)
    self.Click("css=li[heading=Results]")

    if data_store.RelationalDBEnabled():
      fd = file_store.OpenFile(
          flow_export.CollectionItemToClientPath(results[0]))
    else:
      fd = aff4.FACTORY.Open(
          flow_export.CollectionItemToAff4Path(results[0]), token=self.token)

    with mock.patch.object(fd.__class__, "Read") as mock_obj:
      self.Click(
          "css=grr-results-collection button:has(span.glyphicon-download)")
      self.WaitUntil(lambda: mock_obj.called)

  def testDisplaysErrorMessageIfSingleHuntFileCanNotBeRead(self):
    hunt_urn = self._CreateHuntWithDownloadedFile()
    hunt_id = hunt_urn.Basename()
    results = self.GetHuntResults(hunt_urn)
    original_result = results[0]

    payload = original_result.payload.Copy()
    payload.pathspec.path += "blah"

    client_id = self.SetupClients(1)[0]
    self.AddResultsToHunt(hunt_urn, client_id, [payload])

    self.RequestAndGrantHuntApproval(hunt_id)

    self.Open("/")
    self.Click("css=a[grrtarget=hunts]")
    self.Click("css=td:contains('%s')" % hunt_id)
    self.Click("css=li[heading=Results]")
    self.Click(
        "css=grr-results-collection button:has(span.glyphicon-download):last")
    self.WaitUntil(self.IsTextPresent, "Couldn't download the file.")


if __name__ == "__main__":
  app.run(test_lib.main)
