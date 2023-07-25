#!/usr/bin/env python
import traceback
from typing import Iterable

from absl import app

from grr_response_core.lib.rdfvalues import file_finder as rdf_file_finder
from grr_response_core.lib.rdfvalues import paths as rdf_paths
from grr_response_server import hunt
from grr_response_server.flows.general import transfer
from grr_response_server.gui import api_call_context
from grr_response_server.gui import gui_test_lib
from grr_response_server.gui.api_plugins import hunt as api_hunt
from grr_response_server.rdfvalues import flow_runner as rdf_flow_runner
from grr_response_server.rdfvalues import output_plugin as rdf_output_plugin
from grr.test_lib import hunt_test_lib
from grr.test_lib import test_lib


def _ListHunts(creator: str) -> Iterable[api_hunt.ApiHunt]:
  handler = api_hunt.ApiListHuntsHandler()
  result = handler.Handle(
      api_hunt.ApiListHuntsArgs(created_by=creator, with_full_summary=True),
      context=api_call_context.ApiCallContext(username=creator),
  )
  return result.items


class HuntPageTest(
    hunt_test_lib.StandardHuntTestMixin, gui_test_lib.GRRSeleniumTest
):
  """Tests the hunt page."""

  def testDisplaysHuntInformation(self):
    hunt_description = "Dummy hunt"
    hunt_flow_args = transfer.GetFileArgs(
        pathspec=rdf_paths.PathSpec(
            path="/tmp/evil.txt",
            pathtype=rdf_paths.PathSpec.PathType.NTFS,
        )
    )
    hunt_id = self.CreateHunt(
        description=hunt_description,
        flow_runner_args=rdf_flow_runner.FlowRunnerArgs(
            flow_name=transfer.GetFile.__name__
        ),
        flow_args=hunt_flow_args,
        client_rule_set=self._CreateForemanClientRuleSet(),
        output_plugins=[
            rdf_output_plugin.OutputPluginDescriptor(
                plugin_name="DummyOutputPlugin",
                args=gui_test_lib.DummyOutputPlugin.args_type(
                    filename_regex="blah!", fetch_binaries=True
                ),
            )
        ],
        client_rate=60,
        creator=self.test_username,
    )

    self.Open(f"/v2/hunts/{hunt_id}")
    self.WaitUntilEqual(f"/v2/hunts/{hunt_id}", self.GetCurrentUrlPath)

    self.WaitUntil(
        self.IsElementPresent, f"css=.hunt-overview:contains('{hunt_id}')"
    )
    self.WaitUntil(
        self.IsElementPresent,
        f"css=.hunt-overview:contains('{self.test_username}')",
    )
    self.WaitUntil(
        self.IsElementPresent, "css=.hunt-overview:contains('GetFile')"
    )
    self.WaitUntil(
        self.IsElementPresent, "css=.hunt-overview:contains('not started')"
    )
    self.WaitUntil(
        self.IsElementPresent,
        "css=.hunt-overview button:contains('View flow arguments')",
    )
    self.Click("css=button:contains('View flow arguments')")
    self.WaitUntil(
        self.IsElementPresent, "css=hunt-flow-arguments:contains('GetFile')"
    )

    self.WaitUntil(
        self.IsElementPresent, "css=approval-card:contains('Access approval')"
    )

    # The hunt has not started yet. No progress or results are shown.
    self.WaitUntilNot(self.IsElementPresent, "css=app-hunt-progress")
    self.WaitUntilNot(self.IsElementPresent, "css=app-hunt-results")

    # The hunt has not started yet. Arguments are visible.
    self.WaitUntil(
        self.IsElementPresent,
        "css=hunt-flow-arguments:contains('GetFile')",
    )
    self.WaitUntil(
        self.IsElementPresent,
        "css=hunt-arguments:contains('60 clients/min')",
    )

    # Start hunt and add results and errors.
    client_ids = self.SetupClients(2)
    hunt.StartHunt(hunt_id)
    self.RunHuntWithClientCrashes([client_ids[0]])
    error_msg = "Client Error"
    self.AddErrorToHunt(
        hunt_id, client_ids[0], error_msg, traceback.format_exc()
    )
    self.RunHunt([client_ids[1]])
    self.AddResultsToHunt(
        hunt_id, client_ids[1], [rdf_file_finder.FileFinderResult()]
    )

    # Make sure new results are reflected on the progress and results.
    self.WaitUntil(
        self.IsElementPresent,
        (
            "css=app-hunt-progress .summary:nth-child(1):contains('Complete50"
            " %1 clients')"
        ),
    )
    self.WaitUntil(
        self.IsElementPresent,
        (
            "css=app-hunt-progress .summary:nth-child(2):contains('In"
            " progress50 %1 clients')"
        ),
    )
    self.WaitUntil(
        self.IsElementPresent,
        (
            "css=app-hunt-progress .summary:nth-child(3):contains('Without"
            " results0 %0 clients')"
        ),
    )
    self.WaitUntil(
        self.IsElementPresent,
        (
            "css=app-hunt-progress .summary:nth-child(4):contains('With"
            " results50 %1 clients')"
        ),
    )
    self.WaitUntil(
        self.IsElementPresent,
        (
            "css=app-hunt-progress .summary:nth-child(5):contains('Errors and"
            " Crashes50 %1 clients')"
        ),
    )

    self.WaitUntil(
        self.IsElementPresent,
        "css=app-hunt-results"
        " [role=tab][aria-selected=true]:contains('Errors')",
    )
    self.WaitUntil(
        self.IsElementPresent,
        f"css=app-hunt-results mat-row:contains('{client_ids[0]}')",
    )
    self.Click("css=app-hunt-results mat-row button:contains('View details')")
    self.WaitUntil(
        self.IsElementPresent,
        f"css=hunt-result-details h3:contains('Client: {client_ids[0]}')",
    )
    self.WaitUntil(
        self.IsElementPresent,
        "css=hunt-result-details flow-details:contains('GetFile')",
    )
    self.WaitUntil(
        self.IsElementPresent,
        f"css=hunt-result-details pre:contains('{error_msg}')",
    )

    # Go back
    self.Open(f"/v2/hunts/{hunt_id}")
    self.WaitUntilEqual(f"/v2/hunts/{hunt_id}", self.GetCurrentUrlPath)

    self.WaitUntil(
        self.IsElementPresent,
        "css=app-hunt-results [role=tab]:contains('File Finder')",
    )
    self.Click("css=app-hunt-results [role=tab]:contains('File Finder')")

    self.WaitUntil(
        self.IsElementPresent,
        f"css=app-hunt-results mat-row:contains('{client_ids[1]}')",
    )
    self.Click("css=app-hunt-results mat-row button:contains('View details')")

    self.WaitUntil(
        self.IsElementPresent,
        f"css=hunt-result-details h3:contains('Client: {client_ids[1]}')",
    )
    self.WaitUntil(
        self.IsElementPresent,
        "css=hunt-result-details flow-details:contains('GetFile')",
    )
    self.WaitUntil(
        self.IsElementPresent,
        "css=hunt-result-details pre:contains('FileFinderResult')",
    )

  def testStoptHunt(self):
    hunt_description = "Dummy hunt"
    hunt_flow_args = transfer.GetFileArgs(
        pathspec=rdf_paths.PathSpec(
            path="/tmp/evil.txt",
            pathtype=rdf_paths.PathSpec.PathType.NTFS,
        )
    )
    hunt_id = self.CreateHunt(
        description=hunt_description,
        flow_runner_args=rdf_flow_runner.FlowRunnerArgs(
            flow_name=transfer.GetFile.__name__
        ),
        flow_args=hunt_flow_args,
        client_rule_set=self._CreateForemanClientRuleSet(),
        output_plugins=[
            rdf_output_plugin.OutputPluginDescriptor(
                plugin_name="DummyOutputPlugin",
                args=gui_test_lib.DummyOutputPlugin.args_type(
                    filename_regex="blah!", fetch_binaries=True
                ),
            )
        ],
        client_rate=60,
        creator=self.test_username,
    )

    self.Open(f"/v2/hunts/{hunt_id}")
    self.WaitUntilEqual(f"/v2/hunts/{hunt_id}", self.GetCurrentUrlPath)

    self.WaitUntil(
        self.IsElementPresent, "css=.hunt-overview:contains('not started')"
    )

    hunts = _ListHunts(self.test_username)
    self.assertLen(hunts, 1)
    self.assertEqual(hunts[0].state, api_hunt.ApiHunt.State.PAUSED)

    self.RequestAndGrantHuntApproval(hunt_id, requestor=self.test_username)
    self.WaitUntil(
        self.IsElementPresent, "css=approval-card:contains('Access granted')"
    )

    self.WaitUntil(self.IsElementPresent, "css=button[name=cancel-button]")
    self.Click("css=button[name=cancel-button]")

    self.WaitUntil(
        self.IsElementPresent, "css=.hunt-overview:contains('Cancelled')"
    )

    hunts = _ListHunts(self.test_username)
    self.assertLen(hunts, 1)
    self.assertEqual(hunts[0].state, api_hunt.ApiHunt.State.STOPPED)

  def testStartHunt(self):
    hunt_description = "Dummy hunt"
    hunt_flow_args = transfer.GetFileArgs(
        pathspec=rdf_paths.PathSpec(
            path="/tmp/evil.txt",
            pathtype=rdf_paths.PathSpec.PathType.NTFS,
        )
    )
    hunt_id = self.CreateHunt(
        description=hunt_description,
        flow_runner_args=rdf_flow_runner.FlowRunnerArgs(
            flow_name=transfer.GetFile.__name__
        ),
        flow_args=hunt_flow_args,
        client_rule_set=self._CreateForemanClientRuleSet(),
        output_plugins=[
            rdf_output_plugin.OutputPluginDescriptor(
                plugin_name="DummyOutputPlugin",
                args=gui_test_lib.DummyOutputPlugin.args_type(
                    filename_regex="blah!", fetch_binaries=True
                ),
            )
        ],
        client_rate=60,
        creator=self.test_username,
    )

    self.Open(f"/v2/hunts/{hunt_id}")
    self.WaitUntilEqual(f"/v2/hunts/{hunt_id}", self.GetCurrentUrlPath)

    self.WaitUntil(
        self.IsElementPresent, "css=.hunt-overview:contains('not started')"
    )

    hunts = _ListHunts(self.test_username)
    self.assertLen(hunts, 1)
    self.assertEqual(hunts[0].state, api_hunt.ApiHunt.State.PAUSED)

    self.RequestAndGrantHuntApproval(hunt_id, requestor=self.test_username)
    self.WaitUntil(
        self.IsElementPresent, "css=approval-card:contains('Access granted')"
    )

    self.WaitUntil(self.IsElementPresent, "css=button[name=start-button]")
    self.Click("css=button[name=start-button]")

    self.WaitUntil(
        self.IsElementPresent, "css=.hunt-overview:contains('running')"
    )

    hunts = _ListHunts(self.test_username)
    self.assertLen(hunts, 1)
    self.assertEqual(hunts[0].state, api_hunt.ApiHunt.State.STARTED)

  def testModifytHunt(self):
    hunt_description = "Dummy hunt"
    hunt_flow_args = transfer.GetFileArgs(
        pathspec=rdf_paths.PathSpec(
            path="/tmp/evil.txt",
            pathtype=rdf_paths.PathSpec.PathType.NTFS,
        )
    )
    hunt_id = self.CreateHunt(
        description=hunt_description,
        flow_runner_args=rdf_flow_runner.FlowRunnerArgs(
            flow_name=transfer.GetFile.__name__
        ),
        flow_args=hunt_flow_args,
        client_rule_set=self._CreateForemanClientRuleSet(),
        output_plugins=[
            rdf_output_plugin.OutputPluginDescriptor(
                plugin_name="DummyOutputPlugin",
                args=gui_test_lib.DummyOutputPlugin.args_type(
                    filename_regex="blah!", fetch_binaries=True
                ),
            )
        ],
        client_rate=60,
        client_limit=0,
        creator=self.test_username,
    )

    self.Open(f"/v2/hunts/{hunt_id}")
    self.WaitUntilEqual(f"/v2/hunts/{hunt_id}", self.GetCurrentUrlPath)

    self.WaitUntil(
        self.IsElementPresent, "css=.hunt-overview:contains('not started')"
    )

    hunts = _ListHunts(self.test_username)
    self.assertLen(hunts, 1)
    self.assertEqual(hunts[0].state, api_hunt.ApiHunt.State.PAUSED)
    self.assertEqual(hunts[0].hunt_runner_args.client_rate, 60)
    self.assertEqual(hunts[0].hunt_runner_args.client_limit, 0)

    self.RequestAndGrantHuntApproval(hunt_id, requestor=self.test_username)
    self.WaitUntil(
        self.IsElementPresent, "css=approval-card:contains('Access granted')"
    )

    self.WaitUntil(self.IsElementPresent, "css=[name=modify-button]")
    self.Click("css=[name=modify-button]")

    self.WaitUntil(
        self.IsElementPresent,
        "css=.run-on-option.mat-button-toggle-checked:contains('All')",
    )
    self.Click("css=.run-on-option button:contains('sample')")
    self.WaitUntil(
        self.IsElementPresent,
        "css=.rollout-speed-option.mat-button-toggle-checked:contains('Custom')",
    )
    self.Click("css=.rollout-speed-option button:contains('Unlimited')")

    self.Click("css=button[id=modifyAndContinue]")
    self.WaitUntilEqual(f"/v2/hunts/{hunt_id}", self.GetCurrentUrlPath)

    hunts = _ListHunts(self.test_username)
    self.assertLen(hunts, 1)
    self.assertEqual(hunts[0].state, api_hunt.ApiHunt.State.STARTED)
    self.assertEqual(hunts[0].hunt_runner_args.client_rate, 0)
    self.assertEqual(hunts[0].hunt_runner_args.client_limit, 100)

  def testBackButtonNavigatesToOldUi(self):
    hunt_description = "Dummy hunt"
    hunt_flow_args = transfer.GetFileArgs(
        pathspec=rdf_paths.PathSpec(
            path="/tmp/evil.txt",
            pathtype=rdf_paths.PathSpec.PathType.NTFS,
        )
    )
    hunt_id = self.CreateHunt(
        description=hunt_description,
        flow_runner_args=rdf_flow_runner.FlowRunnerArgs(
            flow_name=transfer.GetFile.__name__
        ),
        flow_args=hunt_flow_args,
        client_rule_set=self._CreateForemanClientRuleSet(),
        output_plugins=[
            rdf_output_plugin.OutputPluginDescriptor(
                plugin_name="DummyOutputPlugin",
                args=gui_test_lib.DummyOutputPlugin.args_type(
                    filename_regex="blah!", fetch_binaries=True
                ),
            )
        ],
        client_rate=60,
        client_limit=0,
        creator=self.test_username,
    )

    self.Open(f"/v2/hunts/{hunt_id}")
    self.WaitUntilEqual(f"/v2/hunts/{hunt_id}", self.GetCurrentUrlPath)

    self.WaitUntil(self.IsElementPresent, "css=a#fallback-link")
    self.Click("css=a#fallback-link")

    self.WaitUntilEqual(f"/legacy#/hunts/{hunt_id}", self.GetCurrentUrlPath)


class HuntOverviewPageTest(
    hunt_test_lib.StandardHuntTestMixin, gui_test_lib.GRRSeleniumTest
):
  """Tests the hunt overview page."""

  def testBackButtonNavigatesToOldUi(self):
    self.Open("/v2/hunts")
    self.WaitUntilEqual("/v2/hunts", self.GetCurrentUrlPath)

    self.WaitUntil(self.IsElementPresent, "css=a#fallback-link")
    self.Click("css=a#fallback-link")

    self.WaitUntilEqual("/legacy#/hunts", self.GetCurrentUrlPath)


if __name__ == "__main__":
  app.run(test_lib.main)
