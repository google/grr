#!/usr/bin/env python
from absl import app

from grr_response_core.lib.rdfvalues import paths as rdf_paths
from grr_response_server.flows.general import large_file
from grr_response_server.gui import gui_test_lib
from grr.test_lib import flow_test_lib
from grr.test_lib import test_lib


class LargeFileTest(gui_test_lib.GRRSeleniumTest):
  """Tests the LargeFile Flow."""

  def setUp(self):
    super().setUp()
    self.client_id = self.SetupClient(0)
    self.RequestAndGrantClientApproval(self.client_id)

  def testDisplaysSessionUrlWhenCollectionInProgress(self):
    flow_args = large_file.CollectLargeFileFlowArgs(
        path_spec=rdf_paths.PathSpec(
            pathtype=rdf_paths.PathSpec.PathType.OS,
            path="/file",
        ),
        signed_url="http://signed_url",
    )

    flow_test_lib.StartFlow(
        large_file.CollectLargeFileFlow,
        creator=self.test_username,
        client_id=self.client_id,
        flow_args=flow_args,
    )

    with flow_test_lib.FlowProgressOverride(
        large_file.CollectLargeFileFlow,
        large_file.CollectLargeFileFlowProgress(
            session_uri="http://session_uri"
        ),
    ):
      self.Open(f"/v2/clients/{self.client_id}")
      self.WaitUntil(
          self.IsElementPresent,
          "css=.flow-title:contains('Collect large file')",
      )
      self.Click("css=result-accordion .title:contains('/file')")
      self.WaitUntil(
          self.IsElementPresent,
          "css=collect-large-file-flow-details"
          " result-accordion:contains('http://session_uri')",
      )

  def testDisplaysCollectedResult(self):
    flow_args = large_file.CollectLargeFileFlowArgs(
        path_spec=rdf_paths.PathSpec(
            pathtype=rdf_paths.PathSpec.PathType.OS,
            path="/file",
        ),
        signed_url="http://signed_url",
    )
    flow_id = flow_test_lib.StartFlow(
        large_file.CollectLargeFileFlow,
        creator=self.test_username,
        client_id=self.client_id,
        flow_args=flow_args,
    )

    flow_test_lib.AddResultsToFlow(
        self.client_id,
        flow_id,
        [
            large_file.CollectLargeFileFlowResult(
                session_uri="http://session_uri",
                total_bytes_sent=123,
            )
        ],
    )
    with flow_test_lib.FlowProgressOverride(
        large_file.CollectLargeFileFlow,
        large_file.CollectLargeFileFlowProgress(
            session_uri="http://session_uri_from_progress"
        ),
    ):
      self.Open(f"/v2/clients/{self.client_id}")

      self.WaitUntil(
          self.IsElementPresent,
          "css=.flow-title:contains('Collect large file')",
      )
      self.Click("css=result-accordion .title:contains('/file')")
      self.WaitUntil(
          self.IsElementPresent,
          "css=collect-large-file-flow-details"
          " result-accordion:contains('http://session_uri')",
      )
      self.WaitUntil(
          self.IsElementPresent,
          "css=collect-large-file-flow-details"
          " result-accordion:contains('123 B')",
      )


if __name__ == "__main__":
  app.run(test_lib.main)
