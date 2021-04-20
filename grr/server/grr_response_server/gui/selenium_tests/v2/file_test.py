#!/usr/bin/env python
import binascii

from absl import app

from grr_response_core.lib.rdfvalues import client_fs as rdf_client_fs
from grr_response_core.lib.rdfvalues import crypto as rdf_crypto
from grr_response_core.lib.rdfvalues import file_finder as rdf_file_finder
from grr_response_core.lib.rdfvalues import paths as rdf_paths
from grr_response_server.flows import file
from grr_response_server.gui import gui_test_lib
from grr.test_lib import flow_test_lib
from grr.test_lib import test_lib


class CollectSingleFileTest(gui_test_lib.GRRSeleniumTest):
  """Tests the search UI."""

  def _GenSampleResult(self,
                       use_ntfs: bool = False
                      ) -> rdf_file_finder.CollectSingleFileResult:
    if use_ntfs:
      pathspec = rdf_paths.PathSpec.NTFS(path="/etc/hosts")
    else:
      pathspec = rdf_paths.PathSpec.OS(path="/etc/hosts")

    return rdf_file_finder.CollectSingleFileResult(
        stat=rdf_client_fs.StatEntry(
            pathspec=pathspec,
            st_mode=33184,
            st_size=4242,
            st_atime=1336469177,
            st_mtime=1336129892,
            st_ctime=1336129892,
        ),
        hash=rdf_crypto.Hash(
            sha256=binascii.unhexlify(
                "9e8dc93e150021bb4752029ebbff51394aa36f069cf19901578e4f06017acdb5"
            ),
            sha1=binascii.unhexlify("6dd6bee591dfcb6d75eb705405302c3eab65e21a"),
            md5=binascii.unhexlify("8b0a15eefe63fd41f8dc9dee01c5cf9a")))

  def setUp(self):
    super().setUp()
    self.client_id = self.SetupClient(0)
    self.RequestAndGrantClientApproval(self.client_id)

  def testCorrectlyDisplaysInProgressStatus(self):
    flow_args = rdf_file_finder.CollectSingleFileArgs(path="/etc/hosts")
    flow_test_lib.StartFlow(
        file.CollectSingleFile,
        creator=self.test_username,
        client_id=self.client_id,
        flow_args=flow_args)

    with flow_test_lib.FlowProgressOverride(
        file.CollectSingleFile,
        rdf_file_finder.CollectSingleFileProgress(
            status=rdf_file_finder.CollectSingleFileProgress.Status.IN_PROGRESS)
    ):
      self.Open(f"/v2/clients/{self.client_id}")
      self.WaitUntil(self.IsElementPresent,
                     "css=.flow-title:contains('File content')")
      self.WaitUntil(
          self.IsElementPresent,
          "css=collect-single-file-details .requested-path:contains('/etc/hosts')"
      )
      self.WaitUntilNot(self.IsElementPresent,
                        "css=collect-single-file-details .collected-result")

  def testCorrectlyDisplaysCollectedResult(self):
    flow_args = rdf_file_finder.CollectSingleFileArgs(path="/etc/hosts")
    flow_test_lib.StartFlow(
        file.CollectSingleFile,
        creator=self.test_username,
        client_id=self.client_id,
        flow_args=flow_args)

    with flow_test_lib.FlowProgressOverride(
        file.CollectSingleFile,
        rdf_file_finder.CollectSingleFileProgress(
            status=rdf_file_finder.CollectSingleFileProgress.Status.COLLECTED,
            result=self._GenSampleResult())):

      self.Open(f"/v2/clients/{self.client_id}")
      self.WaitUntil(
          self.IsElementPresent,
          "css=collect-single-file-details .collected-result:contains('/etc/hosts')"
      )
      self.WaitUntil(
          self.IsElementPresent,
          "css=collect-single-file-details .collected-result:contains('4.14 KiB')"
      )
      self.WaitUntilNot(self.IsElementPresent,
                        "css=collect-single-file-details .requested-path")

  def testCorrectlyDisplaysNonStandardPathTypeNote(self):
    flow_args = rdf_file_finder.CollectSingleFileArgs(path="/etc/hosts")
    flow_test_lib.StartFlow(
        file.CollectSingleFile,
        creator=self.test_username,
        client_id=self.client_id,
        flow_args=flow_args)

    with flow_test_lib.FlowProgressOverride(
        file.CollectSingleFile,
        rdf_file_finder.CollectSingleFileProgress(
            status=rdf_file_finder.CollectSingleFileProgress.Status.COLLECTED,
            result=self._GenSampleResult(use_ntfs=True))):

      self.Open(f"/v2/clients/{self.client_id}")
      self.WaitUntil(
          self.IsElementPresent,
          "css=collect-single-file-details .collected-result:contains('/etc/hosts')"
      )
      self.WaitUntil(
          self.IsElementPresent,
          "css=collect-single-file-details .path-type-note:contains("
          "'File was fetched by parsing the raw disk image with libfsntfs')")

  def testCorrectlyDisplaysDownloadButtonOnSuccess(self):
    flow_args = rdf_file_finder.CollectSingleFileArgs(path="/etc/hosts")
    flow_test_lib.StartFlow(
        file.CollectSingleFile,
        creator=self.test_username,
        client_id=self.client_id,
        flow_args=flow_args)

    self.Open(f"/v2/clients/{self.client_id}")
    self.WaitUntil(
        self.IsElementPresent,
        "css=collect-single-file-details .requested-path:contains('/etc/hosts')"
    )
    self.WaitUntilNot(self.IsElementPresent,
                      "css=a[mat-stroked-button]:contains('Download')")

    with flow_test_lib.FlowProgressOverride(
        file.CollectSingleFile,
        rdf_file_finder.CollectSingleFileProgress(
            status=rdf_file_finder.CollectSingleFileProgress.Status.COLLECTED,
            result=self._GenSampleResult())):
      self.WaitUntil(self.IsElementPresent,
                     "css=a[mat-stroked-button]:contains('Download')")

  def testCorrectlyDisplaysNotFoundResult(self):
    flow_args = rdf_file_finder.CollectSingleFileArgs(path="/etc/hosts")
    flow_id = flow_test_lib.StartFlow(
        file.CollectSingleFile,
        creator=self.test_username,
        client_id=self.client_id,
        flow_args=flow_args)
    flow_test_lib.MarkFlowAsFailed(self.client_id, flow_id)

    with flow_test_lib.FlowProgressOverride(
        file.CollectSingleFile,
        rdf_file_finder.CollectSingleFileProgress(
            status=rdf_file_finder.CollectSingleFileProgress.Status.NOT_FOUND)):
      self.Open(f"/v2/clients/{self.client_id}")
      self.WaitUntil(self.IsElementPresent, "css=.flow-status mat-icon.error")
      self.WaitUntil(
          self.IsElementPresent,
          "css=collect-single-file-details .error:contains('File not found')")

  def testCorrectlyDisplaysError(self):
    flow_args = rdf_file_finder.CollectSingleFileArgs(path="/etc/hosts")
    flow_id = flow_test_lib.StartFlow(
        file.CollectSingleFile,
        creator=self.test_username,
        client_id=self.client_id,
        flow_args=flow_args)
    flow_test_lib.MarkFlowAsFailed(self.client_id, flow_id)

    with flow_test_lib.FlowProgressOverride(
        file.CollectSingleFile,
        rdf_file_finder.CollectSingleFileProgress(
            status=rdf_file_finder.CollectSingleFileProgress.Status.FAILED,
            error_description="Something went wrong")):
      self.Open(f"/v2/clients/{self.client_id}")
      self.WaitUntil(
          self.IsElementPresent,
          "css=collect-single-file-details .error:contains('Something went wrong')"
      )


if __name__ == "__main__":
  app.run(test_lib.main)
