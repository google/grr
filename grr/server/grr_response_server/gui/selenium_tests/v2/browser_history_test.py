#!/usr/bin/env python
from absl import app

from grr_response_core.lib import rdfvalue
from grr_response_core.lib.rdfvalues import client_fs as rdf_client_fs
from grr_response_core.lib.rdfvalues import paths as rdf_paths
from grr_response_server.flows.general import webhistory
from grr_response_server.gui import api_call_context
from grr_response_server.gui import gui_test_lib
from grr_response_server.gui.api_plugins import flow as api_flow
from grr_response_server.rdfvalues import flow_objects as rdf_flow_objects
from grr.test_lib import flow_test_lib
from grr.test_lib import test_lib


def _GenResults(browser, i):
  return webhistory.CollectBrowserHistoryResult(
      browser=browser,
      stat_entry=rdf_client_fs.StatEntry(
          pathspec=rdf_paths.PathSpec.OS(
              path=f"/home/foo/{browser.name.lower()}-{i}"),
          st_mode=0o644,
          st_dev=16777220 + i,
          st_nlink=1 + i,
          st_uid=237586 + i,
          st_gid=89939 + i,
          st_size=42 + i,
          st_atime=rdfvalue.RDFDatetime.FromSecondsSinceEpoch(400000 + i),
          st_mtime=rdfvalue.RDFDatetime.FromSecondsSinceEpoch(40000 + i),
          st_ctime=rdfvalue.RDFDatetime.FromSecondsSinceEpoch(4000 + i),
      ))


class CollectBrowserHistoryTest(gui_test_lib.GRRSeleniumTest):
  """Tests the search UI."""

  def setUp(self):
    super().setUp()
    self.client_id = self.SetupClient(0)
    self.RequestAndGrantClientApproval(self.client_id)

  def testCorrectlyDisplaysInProgressStateForMultipleBrowsers(self):
    # Start the flow with 2 browsers scheduled for collection.
    flow_args = webhistory.CollectBrowserHistoryArgs(browsers=[
        webhistory.CollectBrowserHistoryArgs.Browser.CHROME,
        webhistory.CollectBrowserHistoryArgs.Browser.OPERA,
    ])
    flow_test_lib.StartFlow(
        webhistory.CollectBrowserHistory,
        creator=self.test_username,
        client_id=self.client_id,
        flow_args=flow_args)

    with flow_test_lib.FlowProgressOverride(
        webhistory.CollectBrowserHistory,
        webhistory.CollectBrowserHistoryProgress(browsers=[
            webhistory.BrowserProgress(
                browser=webhistory.Browser.CHROME,
                status=webhistory.BrowserProgress.Status.IN_PROGRESS,
                num_collected_files=0,
            ),
            webhistory.BrowserProgress(
                browser=webhistory.Browser.OPERA,
                status=webhistory.BrowserProgress.Status.IN_PROGRESS,
                num_collected_files=0,
            ),
        ])):
      self.Open(f"/v2/clients/{self.client_id}")
      # Expand the flow.
      self.Click("css=.flow-title:contains('Browser History')")
      self.WaitUntil(self.IsElementPresent,
                     "css=.row:contains('Chrome') .in-progress")
      self.WaitUntil(self.IsElementPresent,
                     "css=.row:contains('Opera') .in-progress")
      # Check that other browsers are not shown.
      self.WaitUntilNot(self.IsElementPresent, "css=.row:contains('Safari')")
      self.WaitUntilNot(self.IsElementPresent,
                        "css=.row:contains('Internet Explorer')")
      self.WaitUntilNot(self.IsElementPresent, "css=.row:contains('Firefox')")

  def testCorrectlyDisplaysSuccessStateForSingleBrowser(self):
    flow_args = webhistory.CollectBrowserHistoryArgs(
        browsers=[webhistory.CollectBrowserHistoryArgs.Browser.CHROME])
    flow_test_lib.StartFlow(
        webhistory.CollectBrowserHistory,
        creator=self.test_username,
        client_id=self.client_id,
        flow_args=flow_args)

    with flow_test_lib.FlowProgressOverride(
        webhistory.CollectBrowserHistory,
        webhistory.CollectBrowserHistoryProgress(browsers=[
            webhistory.BrowserProgress(
                browser=webhistory.Browser.CHROME,
                status=webhistory.BrowserProgress.Status.SUCCESS,
                num_collected_files=1,
            ),
        ])):
      self.Open(f"/v2/clients/{self.client_id}")
      # Expand the flow.
      self.Click("css=.flow-title:contains('Browser History')")
      self.WaitUntil(self.IsElementPresent,
                     "css=.row:contains('Chrome') .success:contains('1 file')")
      # Check that other browsers are not shown.
      self.WaitUntilNot(self.IsElementPresent, "css=.row:contains('Opera')")
      self.WaitUntilNot(self.IsElementPresent, "css=.row:contains('Safari')")
      self.WaitUntilNot(self.IsElementPresent,
                        "css=.row:contains('Internet Explorer')")
      self.WaitUntilNot(self.IsElementPresent, "css=.row:contains('Firefox')")

  def testCorrectlyDisplaysWarningStateForSingleBrowser(self):
    flow_args = webhistory.CollectBrowserHistoryArgs(
        browsers=[webhistory.CollectBrowserHistoryArgs.Browser.CHROME])
    flow_test_lib.StartFlow(
        webhistory.CollectBrowserHistory,
        creator=self.test_username,
        client_id=self.client_id,
        flow_args=flow_args)

    with flow_test_lib.FlowProgressOverride(
        webhistory.CollectBrowserHistory,
        webhistory.CollectBrowserHistoryProgress(browsers=[
            webhistory.BrowserProgress(
                browser=webhistory.Browser.CHROME,
                status=webhistory.BrowserProgress.Status.SUCCESS,
                num_collected_files=0,
            ),
        ])):
      self.Open(f"/v2/clients/{self.client_id}")
      # Expand the flow.
      self.Click("css=.flow-title:contains('Browser History')")
      self.WaitUntil(
          self.IsElementPresent,
          "css=.row:contains('Chrome') .warning:contains('No files collected')")
      # Check that other browsers are not shown.
      self.WaitUntilNot(self.IsElementPresent, "css=.row:contains('Opera')")
      self.WaitUntilNot(self.IsElementPresent, "css=.row:contains('Safari')")
      self.WaitUntilNot(self.IsElementPresent,
                        "css=.row:contains('Internet Explorer')")
      self.WaitUntilNot(self.IsElementPresent, "css=.row:contains('Firefox')")

  def testCorrectlyDisplaysErrorForSingleBrowser(self):
    flow_args = webhistory.CollectBrowserHistoryArgs(
        browsers=[webhistory.CollectBrowserHistoryArgs.Browser.CHROME])
    flow_test_lib.StartFlow(
        webhistory.CollectBrowserHistory,
        creator=self.test_username,
        client_id=self.client_id,
        flow_args=flow_args)

    with flow_test_lib.FlowProgressOverride(
        webhistory.CollectBrowserHistory,
        webhistory.CollectBrowserHistoryProgress(browsers=[
            webhistory.BrowserProgress(
                browser=webhistory.Browser.CHROME,
                status=webhistory.BrowserProgress.Status.ERROR,
                description="Something went wrong",
                num_collected_files=0,
            ),
        ])):
      self.Open(f"/v2/clients/{self.client_id}")
      # Expand the flow.
      self.Click("css=.flow-title:contains('Browser History')")
      self.WaitUntil(
          self.IsElementPresent,
          "css=.row:contains('Chrome') .error:contains('Something went wrong')")
      # Check that other browsers are not shown.
      self.WaitUntilNot(self.IsElementPresent, "css=.row:contains('Opera')")
      self.WaitUntilNot(self.IsElementPresent, "css=.row:contains('Safari')")
      self.WaitUntilNot(self.IsElementPresent,
                        "css=.row:contains('Internet Explorer')")
      self.WaitUntilNot(self.IsElementPresent, "css=.row:contains('Firefox')")

  def testShowsDownloadButtonOnFlowCompletion(self):
    flow_args = webhistory.CollectBrowserHistoryArgs(
        browsers=[webhistory.CollectBrowserHistoryArgs.Browser.CHROME])
    flow_id = flow_test_lib.StartFlow(
        webhistory.CollectBrowserHistory,
        creator=self.test_username,
        client_id=self.client_id,
        flow_args=flow_args)

    with flow_test_lib.FlowProgressOverride(
        webhistory.CollectBrowserHistory,
        webhistory.CollectBrowserHistoryProgress(browsers=[
            webhistory.BrowserProgress(
                browser=webhistory.Browser.CHROME,
                status=webhistory.BrowserProgress.Status.IN_PROGRESS,
                num_collected_files=0,
            ),
        ])):
      self.Open(f"/v2/clients/{self.client_id}")
      # Make sure that the flow panel is already displayed...
      self.WaitUntil(self.IsElementPresent,
                     "css=.flow-title:contains('Browser History')")
      # ...and then check for the presence of the 'Download all' button.
      self.WaitUntilNot(self.IsElementPresent,
                        "css=a[mat-stroked-button]:contains('Download all')")

    flow_test_lib.MarkFlowAsFinished(self.client_id, flow_id)

    with flow_test_lib.FlowProgressOverride(
        webhistory.CollectBrowserHistory,
        webhistory.CollectBrowserHistoryProgress(browsers=[
            webhistory.BrowserProgress(
                browser=webhistory.Browser.CHROME,
                status=webhistory.BrowserProgress.Status.IN_PROGRESS,
                num_collected_files=1,
            ),
        ])):
      with flow_test_lib.FlowResultMetadataOverride(
          webhistory.CollectBrowserHistory,
          rdf_flow_objects.FlowResultMetadata(
              is_metadata_set=True,
              num_results_per_type_tag=[
                  rdf_flow_objects.FlowResultCount(
                      type=webhistory.CollectBrowserHistoryResult.__name__,
                      count=1)
              ])):
        # The flow details view should get updated automatically.
        self.WaitUntil(self.IsElementPresent,
                       "css=a[mat-stroked-button]:contains('Download')")

  def testDisplaysMultipleResultsForSingleBrowser(self):
    flow_args = webhistory.CollectBrowserHistoryArgs(
        browsers=[webhistory.CollectBrowserHistoryArgs.Browser.CHROME])
    flow_id = flow_test_lib.StartFlow(
        webhistory.CollectBrowserHistory,
        creator=self.test_username,
        client_id=self.client_id,
        flow_args=flow_args)

    flow_test_lib.AddResultsToFlow(
        self.client_id,
        flow_id,
        [_GenResults(webhistory.Browser.CHROME, i) for i in range(200)],
        tag="CHROME")

    with flow_test_lib.FlowProgressOverride(
        webhistory.CollectBrowserHistory,
        webhistory.CollectBrowserHistoryProgress(browsers=[
            webhistory.BrowserProgress(
                browser=webhistory.Browser.CHROME,
                status=webhistory.BrowserProgress.Status.SUCCESS,
                num_collected_files=200,
            ),
        ])):
      self.Open(f"/v2/clients/{self.client_id}")
      # Expand the flow.
      self.Click("css=.flow-title:contains('Browser History')")
      # Expand the browser.
      self.Click("css=div.title:contains('Chrome')")
      # Update pagination to display all the results.
      self.MatSelect("css=.top-paginator mat-select", "100")
      # Check that only first 100 results are visible. First row is the table
      # header, so we start with 1.
      self.WaitUntil(self.IsElementPresent, "css=.results tr:nth(1)")
      self.WaitUntilNot(
          self.IsElementPresent,
          "css=.results tr:nth(101):contains('/home/foo/chrome-99')")

      # Check that clicking Load More loads the rest. The button can be hidden
      # under the approval bottom sheet, so for now we workaround by clicking it
      # programmatically and not with a mouse event.
      self.WaitUntil(self.IsElementPresent, "css=button:contains('Load More')")
      self.driver.execute_script(
          """$("button:contains('Load More')").click();""")
      # Update pagination to display all the results.
      self.MatSelect("css=.top-paginator mat-select", "500")

      self.WaitUntil(
          self.IsElementPresent,
          "css=.results tr:nth(200):contains('/home/foo/chrome-199')")
      self.WaitUntilNot(self.IsElementPresent, "css=.results tr:nth(201)")

      # Check that the "load more" button disappears when everything is loaded.
      self.WaitUntilNot(self.IsElementPresent,
                        "css=button:contains('Load More')")

  def testAllowsCopyingResultPathToClipboard(self):
    # TODO: remove the skip instruction as soon as latest Chrome
    # and WebDriver versions are used in the CI infrastructure.
    self.skipTest("Temporarily disabling: running this test requires "
                  "having latest Chrome/WebDriver versions in the CI "
                  "setup.")

    flow_args = webhistory.CollectBrowserHistoryArgs(
        browsers=[webhistory.CollectBrowserHistoryArgs.Browser.CHROME])
    flow_id = flow_test_lib.StartFlow(
        webhistory.CollectBrowserHistory,
        creator=self.test_username,
        client_id=self.client_id,
        flow_args=flow_args)

    flow_test_lib.AddResultsToFlow(
        self.client_id,
        flow_id, [_GenResults(webhistory.Browser.CHROME, 0)],
        tag="CHROME")

    with flow_test_lib.FlowProgressOverride(
        webhistory.CollectBrowserHistory,
        webhistory.CollectBrowserHistoryProgress(browsers=[
            webhistory.BrowserProgress(
                browser=webhistory.Browser.CHROME,
                status=webhistory.BrowserProgress.Status.SUCCESS,
                num_collected_files=1,
            ),
        ])):
      self.Open(f"/v2/clients/{self.client_id}")
      # Expand the flow.
      self.Click("css=.flow-title:contains('Browser History')")
      # Expand the browser.
      self.Click("css=div.title:contains('Chrome')")
      # Hover and click on the copy button.
      self.MoveMouseTo(
          "css=.results tr:nth(1):contains('/home/foo/chrome-0') td.path")
      # Click on the now visible button.
      self.Click(
          "css=.results tr:nth(1):contains('/home/foo/chrome-0') td.path "
          "button.copy-button")

      clip_value = self.GetClipboard()
      self.assertEqual(clip_value, "/home/foo/chrome-0")

  def testDisplaysAndHidesResultsForSingleBrowser(self):
    flow_args = webhistory.CollectBrowserHistoryArgs(browsers=[
        webhistory.CollectBrowserHistoryArgs.Browser.CHROME,
        webhistory.CollectBrowserHistoryArgs.Browser.OPERA,
    ])
    flow_id = flow_test_lib.StartFlow(
        webhistory.CollectBrowserHistory,
        creator=self.test_username,
        client_id=self.client_id,
        flow_args=flow_args)

    flow_test_lib.AddResultsToFlow(
        self.client_id,
        flow_id, [_GenResults(webhistory.Browser.CHROME, 0)],
        tag="CHROME")
    flow_test_lib.AddResultsToFlow(
        self.client_id,
        flow_id, [_GenResults(webhistory.Browser.OPERA, 0)],
        tag="OPERA")
    with flow_test_lib.FlowProgressOverride(
        webhistory.CollectBrowserHistory,
        webhistory.CollectBrowserHistoryProgress(browsers=[
            webhistory.BrowserProgress(
                browser=webhistory.Browser.CHROME,
                status=webhistory.BrowserProgress.Status.SUCCESS,
                num_collected_files=1,
            ),
            webhistory.BrowserProgress(
                browser=webhistory.Browser.OPERA,
                status=webhistory.BrowserProgress.Status.SUCCESS,
                num_collected_files=1,
            )
        ])):
      self.Open(f"/v2/clients/{self.client_id}")
      self.Click("css=.flow-title:contains('Browser History')")

      self.ScrollIntoView("css=div.title:contains('Chrome')")
      self.Click("css=div.title:contains('Chrome')")
      self.WaitUntil(self.IsElementPresent,
                     "css=.results tr:contains('/home/foo/chrome-0')")
      # Only Chrome's results should be shown.
      self.WaitUntilNot(self.IsElementPresent,
                        "css=.results tr:contains('/home/foo/opera-0')")
      # Second click should toggle the browser results view.
      self.Click("css=div.title:contains('Chrome')")
      self.WaitUntilNot(self.IsElementPresent,
                        "css=.results tr:contains('/home/foo/chrome-0')")

      self.Click("css=div.title:contains('Opera')")
      self.WaitUntil(self.IsElementPresent,
                     "css=.results tr:contains('/home/foo/opera-0')")
      # Only Opera's results should be shown.
      self.WaitUntilNot(self.IsElementPresent,
                        "css=.results tr:contains('/home/foo/chrome-0')")
      # Second click should toggle the browser results view.
      self.Click("css=div.title:contains('Opera')")
      self.WaitUntilNot(self.IsElementPresent,
                        "css=.results tr:contains('/home/foo/opera-9')")

  def testUpdatesResultsOfRunningFlowDynamically(self):
    flow_args = webhistory.CollectBrowserHistoryArgs(
        browsers=[webhistory.CollectBrowserHistoryArgs.Browser.CHROME])
    flow_id = flow_test_lib.StartFlow(
        webhistory.CollectBrowserHistory,
        creator=self.test_username,
        client_id=self.client_id,
        flow_args=flow_args)

    self.Open(f"/v2/clients/{self.client_id}")
    self.WaitUntil(self.IsElementPresent,
                   "css=.flow-title:contains('Browser History')")

    progress_0_results = webhistory.CollectBrowserHistoryProgress(browsers=[
        webhistory.BrowserProgress(
            browser=webhistory.Browser.CHROME,
            status=webhistory.BrowserProgress.Status.IN_PROGRESS,
            num_collected_files=0,
        )
    ])
    with flow_test_lib.FlowProgressOverride(webhistory.CollectBrowserHistory,
                                            progress_0_results):
      self.WaitUntil(self.IsElementPresent, "css=div.title:contains('Chrome')")
      self.WaitUntilNot(
          self.IsElementPresent,
          ("css=collect-browser-history-details result-accordion " +
           ".header:contains('keyboard_arrow_down')"))

    flow_test_lib.AddResultsToFlow(
        self.client_id,
        flow_id, [_GenResults(webhistory.Browser.CHROME, i) for i in range(9)],
        tag="CHROME")
    progress_10_results = webhistory.CollectBrowserHistoryProgress(browsers=[
        webhistory.BrowserProgress(
            browser=webhistory.Browser.CHROME,
            status=webhistory.BrowserProgress.Status.IN_PROGRESS,
            num_collected_files=9,
        )
    ])
    with flow_test_lib.FlowProgressOverride(webhistory.CollectBrowserHistory,
                                            progress_10_results):
      self.WaitUntil(self.IsElementPresent,
                     ("css=collect-browser-history-details result-accordion " +
                      ".header:contains('keyboard_arrow_down')"))
      self.Click("css=div.title:contains('Chrome')")
      self.WaitUntilEqual(9, self.GetCssCount, "css=tr:contains('/home/foo')")

    flow_test_lib.AddResultsToFlow(
        self.client_id,
        flow_id, [_GenResults(webhistory.Browser.CHROME, 10)],
        tag="CHROME")
    progress_10_results = webhistory.CollectBrowserHistoryProgress(browsers=[
        webhistory.BrowserProgress(
            browser=webhistory.Browser.CHROME,
            status=webhistory.BrowserProgress.Status.IN_PROGRESS,
            num_collected_files=10,
        )
    ])
    with flow_test_lib.FlowProgressOverride(webhistory.CollectBrowserHistory,
                                            progress_10_results):
      self.WaitUntilEqual(10, self.GetCssCount, "css=tr:contains('/home/foo')")

  def testBrowserHistoryFlowForm(self):
    self.Open(f"/v2/clients/{self.client_id}")

    self.Click('css=flow-form button:contains("Collect browser history")')

    # Uncheck Firefox, all other browser remain checked per default.
    self.Click("css=flow-form mat-checkbox[name=collectFirefox] label")

    self.Click('css=flow-form button:contains("Start")')

    def FlowHasBeenStarted():
      handler = api_flow.ApiListFlowsHandler()
      flows = handler.Handle(
          api_flow.ApiListFlowsArgs(
              client_id=self.client_id, top_flows_only=True),
          context=api_call_context.ApiCallContext(
              username=self.test_username)).items
      self.assertLessEqual(len(flows), 1)
      return flows[0] if len(flows) == 1 else None

    flow = self.WaitUntil(FlowHasBeenStarted)

    self.assertEqual(flow.name, webhistory.CollectBrowserHistory.__name__)
    self.assertCountEqual(
        flow.args.browsers,
        [
            webhistory.CollectBrowserHistoryArgs.Browser.CHROME,
            # Only Firefox has been unchecked, so it should not appear.
            webhistory.CollectBrowserHistoryArgs.Browser.INTERNET_EXPLORER,
            webhistory.CollectBrowserHistoryArgs.Browser.SAFARI,
            webhistory.CollectBrowserHistoryArgs.Browser.OPERA,
        ])


if __name__ == "__main__":
  app.run(test_lib.main)
