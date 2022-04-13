#!/usr/bin/env python
from absl import app

from grr_response_core.lib.rdfvalues import client_fs as rdf_client_fs
from grr_response_core.lib.rdfvalues import paths as rdf_paths
from grr_response_server.flows.general import filesystem
from grr_response_server.gui import gui_test_lib
from grr_response_server.rdfvalues import flow_objects as rdf_flow_objects
from grr.test_lib import flow_test_lib
from grr.test_lib import test_lib


class ListDirectoryTest(gui_test_lib.GRRSeleniumTest):
  """Tests the ListDirectory Flow."""

  def setUp(self):
    super().setUp()
    self.client_id = self.SetupClient(0)
    self.RequestAndGrantClientApproval(self.client_id)

  def testSubmitForm(self):
    self.Open(f"/v2/clients/{self.client_id}")

    self.WaitUntil(self.IsElementPresent, "css=input[name=flowSearchBox]")

    self.Type(
        "css=input[name=flowSearchBox]", "List directory", end_with_enter=True)

    self.WaitUntil(self.IsElementPresent,
                   "css=mat-radio-group.collection-method-input")
    self.WaitUntil(self.IsElementPresent, "css=input.path-input")

    self.Type("css=input.path-input", "/dir")

    self.Click("css=button[type=submit]")

    self.WaitUntil(self.IsElementPresent,
                   "css=result-accordion .title:contains('/dir')")
    self.assertLen(flow_test_lib.ListAllFlows(client_id=self.client_id), 1)

  def testDisplaysResults(self):
    flow_id = flow_test_lib.StartFlow(
        filesystem.ListDirectory,
        creator=self.test_username,
        client_id=self.client_id,
        pathspec=rdf_paths.PathSpec.OS(path="/path"))

    with flow_test_lib.FlowResultMetadataOverride(
        filesystem.ListDirectory,
        rdf_flow_objects.FlowResultMetadata(
            is_metadata_set=True,
            num_results_per_type_tag=[
                rdf_flow_objects.FlowResultCount(
                    type=rdf_client_fs.StatEntry.__name__, count=1)
            ])):
      self.Open(f"/v2/clients/{self.client_id}")
      self.WaitUntil(self.IsElementPresent,
                     "css=.flow-title:contains('ListDirectory')")

      flow_test_lib.AddResultsToFlow(self.client_id, flow_id, [
          rdf_client_fs.StatEntry(
              pathspec=rdf_paths.PathSpec.OS(path=f"file{i}"))
          for i in range(10)
      ])

      self.Click("css=result-accordion .title:contains('/path')")
      for i in range(10):
        self.WaitUntil(self.IsElementPresent, f"css=td:contains('file{i}')")

  def testFiltersResults(self):
    flow_id = flow_test_lib.StartFlow(
        filesystem.ListDirectory,
        creator=self.test_username,
        client_id=self.client_id,
        pathspec=rdf_paths.PathSpec.OS(path="/path"))

    with flow_test_lib.FlowResultMetadataOverride(
        filesystem.ListDirectory,
        rdf_flow_objects.FlowResultMetadata(
            is_metadata_set=True,
            num_results_per_type_tag=[
                rdf_flow_objects.FlowResultCount(
                    type=rdf_client_fs.StatEntry.__name__, count=1)
            ])):
      self.Open(f"/v2/clients/{self.client_id}")
      self.WaitUntil(self.IsElementPresent,
                     "css=.flow-title:contains('ListDirectory')")

      flow_test_lib.AddResultsToFlow(self.client_id, flow_id, [
          rdf_client_fs.StatEntry(
              pathspec=rdf_paths.PathSpec.OS(path=f"file{i}"))
          for i in range(10)
      ])

      self.Click("css=result-accordion .title:contains('/path')")
      for i in range(10):
        self.WaitUntil(self.IsElementPresent, f"css=td:contains('file{i}')")

      self.Type("css=.filter-input input", "file0")
      self.WaitUntil(self.IsElementPresent, "css=td:contains('file0')")
      # Selecting .path class here to avoid obtaining the file icon column.
      self.assertEqual(self.GetCssCount("css=td.path:contains('file')"), 1)

  def testSorting(self):
    flow_id = flow_test_lib.StartFlow(
        filesystem.ListDirectory,
        creator=self.test_username,
        client_id=self.client_id,
        pathspec=rdf_paths.PathSpec.OS(path="/path"))

    with flow_test_lib.FlowResultMetadataOverride(
        filesystem.ListDirectory,
        rdf_flow_objects.FlowResultMetadata(
            is_metadata_set=True,
            num_results_per_type_tag=[
                rdf_flow_objects.FlowResultCount(
                    type=rdf_client_fs.StatEntry.__name__, count=1)
            ])):
      self.Open(f"/v2/clients/{self.client_id}")
      self.WaitUntil(self.IsElementPresent,
                     "css=.flow-title:contains('ListDirectory')")

      flow_test_lib.AddResultsToFlow(self.client_id, flow_id, [
          rdf_client_fs.StatEntry(
              pathspec=rdf_paths.PathSpec.OS(path=f"file{i}")) for i in range(3)
      ])

      self.Click("css=result-accordion .title:contains('/path')")
      for i in range(3):
        self.WaitUntil(self.IsElementPresent, f"css=td:contains('file{i}')")

      self.Click("css=.mat-sort-header:contains('Path')")
      for i in [0, 1, 2]:  # reordered results asc
        self.WaitUntil(self.IsElementPresent, f"css=td:contains('file{i}')")

      self.Click("css=.mat-sort-header:contains('Path')")
      for i in [2, 1, 0]:  # reordered results desc
        self.WaitUntil(self.IsElementPresent, f"css=td:contains('file{i}')")

  def testPaginationNavigation(self):
    flow_id = flow_test_lib.StartFlow(
        filesystem.ListDirectory,
        creator=self.test_username,
        client_id=self.client_id,
        pathspec=rdf_paths.PathSpec.OS(path="/path"))

    with flow_test_lib.FlowResultMetadataOverride(
        filesystem.ListDirectory,
        rdf_flow_objects.FlowResultMetadata(
            is_metadata_set=True,
            num_results_per_type_tag=[
                rdf_flow_objects.FlowResultCount(
                    type=rdf_client_fs.StatEntry.__name__, count=1)
            ])):
      self.Open(f"/v2/clients/{self.client_id}")
      self.WaitUntil(self.IsElementPresent,
                     "css=.flow-title:contains('ListDirectory')")

      flow_test_lib.AddResultsToFlow(self.client_id, flow_id, [
          rdf_client_fs.StatEntry(
              pathspec=rdf_paths.PathSpec.OS(path=f"file{i}"))
          for i in range(15)
      ])

      self.Click("css=result-accordion .title:contains('/path')")
      for i in range(10):
        self.WaitUntil(self.IsElementPresent, f"css=td:contains('file{i}')")
      self.assertEqual(self.GetCssCount("css=td.path:contains('file')"), 10)

      # Navigation works in both top and bottom paginators.
      self.Click("css=.top-paginator .mat-paginator-navigation-last")
      for i in range(10, 15):
        self.WaitUntil(self.IsElementPresent, f"css=td:contains('file{i}')")
      self.assertEqual(self.GetCssCount("css=td.path:contains('file')"), 5)

      self.ScrollToBottom()
      self.Click("css=.bottom-paginator .mat-paginator-navigation-previous")
      for i in range(10):
        self.WaitUntil(self.IsElementPresent, f"css=td:contains('file{i}')")
      self.assertEqual(self.GetCssCount("css=td.path:contains('file')"), 10)

  def testPaginationSize(self):
    flow_id = flow_test_lib.StartFlow(
        filesystem.ListDirectory,
        creator=self.test_username,
        client_id=self.client_id,
        pathspec=rdf_paths.PathSpec.OS(path="/path"))

    with flow_test_lib.FlowResultMetadataOverride(
        filesystem.ListDirectory,
        rdf_flow_objects.FlowResultMetadata(
            is_metadata_set=True,
            num_results_per_type_tag=[
                rdf_flow_objects.FlowResultCount(
                    type=rdf_client_fs.StatEntry.__name__, count=1)
            ])):
      self.Open(f"/v2/clients/{self.client_id}")
      self.WaitUntil(self.IsElementPresent,
                     "css=.flow-title:contains('ListDirectory')")

      flow_test_lib.AddResultsToFlow(self.client_id, flow_id, [
          rdf_client_fs.StatEntry(
              pathspec=rdf_paths.PathSpec.OS(path=f"file{i}"))
          for i in range(15)
      ])

      self.Click("css=result-accordion .title:contains('/path')")
      for i in range(10):
        self.WaitUntil(self.IsElementPresent, f"css=td:contains('file{i}')")
      self.assertEqual(self.GetCssCount("css=td.path:contains('file')"), 10)

      # Select one paginator updates the other paginator as well as the
      # displayed rows.
      self.MatSelect("css=.bottom-paginator mat-select", "50")
      self.WaitUntilContains("50", self.GetText,
                             "css=.top-paginator mat-select")
      self.WaitUntilContains("50", self.GetText,
                             "css=.bottom-paginator mat-select")
      for i in range(15):
        self.WaitUntil(self.IsElementPresent, f"css=td:contains('file{i}')")
      self.assertEqual(self.GetCssCount("css=td.path:contains('file')"), 15)

      self.MatSelect("css=.top-paginator mat-select", "10")
      self.WaitUntilContains("10", self.GetText,
                             "css=.top-paginator mat-select")
      self.WaitUntilContains("10", self.GetText,
                             "css=.bottom-paginator mat-select")
      for i in range(10):
        self.WaitUntil(self.IsElementPresent, f"css=td:contains('file{i}')")
      self.assertEqual(self.GetCssCount("css=td.path:contains('file')"), 10)

  def testDisplaysArgumentsPopup(self):
    flow_test_lib.StartFlow(
        filesystem.ListDirectory,
        creator=self.test_username,
        client_id=self.client_id,
        pathspec=rdf_paths.PathSpec.OS(path="/path"))

    self.Open(f"/v2/clients/{self.client_id}")
    self.WaitUntil(self.IsElementPresent,
                   "css=.flow-title:contains('ListDirectory')")

    self.Click("css=result-accordion .title:contains('Flow arguments')")

    self.WaitUntil(self.IsElementPresent, "css=input.path-input")
    path_input = self.GetElement("css=input.path-input")
    self.assertEqual("/path", path_input.get_attribute("value"))


if __name__ == "__main__":
  app.run(test_lib.main)
