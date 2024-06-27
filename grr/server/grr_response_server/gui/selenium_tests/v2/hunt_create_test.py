#!/usr/bin/env python
import datetime
from typing import Iterable

from absl import app

from grr_response_core.lib.rdfvalues import config as rdf_config
from grr_response_core.lib.rdfvalues import paths as rdf_paths
from grr_response_core.lib.util import retry
from grr_response_proto import flows_pb2
from grr_response_server.flows.general import mig_network
from grr_response_server.flows.general import mig_transfer
from grr_response_server.flows.general import network
from grr_response_server.flows.general import transfer
from grr_response_server.gui import api_call_context
from grr_response_server.gui import gui_test_lib
from grr_response_server.gui.api_plugins import hunt as api_hunt
from grr_response_server.rdfvalues import flow_runner as rdf_flow_runner
from grr_response_server.rdfvalues import output_plugin as rdf_output_plugin
from grr.test_lib import flow_test_lib
from grr.test_lib import hunt_test_lib
from grr.test_lib import test_lib


class HuntCreationTest(
    hunt_test_lib.StandardHuntTestMixin, gui_test_lib.GRRSeleniumTest
):
  """Tests the hunt creation."""

  @retry.On(
      AssertionError,
      opts=retry.Opts(
          attempts=3,
          init_delay=datetime.timedelta(seconds=1),
      ),
  )
  def _ListHuntsAndAssertCount(
      self, creator: str, expected_count: int
  ) -> Iterable[api_hunt.ApiHunt]:
    handler = api_hunt.ApiListHuntsHandler()
    result = handler.Handle(
        api_hunt.ApiListHuntsArgs(created_by=creator, with_full_summary=True),
        context=api_call_context.ApiCallContext(username=creator),
    )
    self.assertLen(result.items, expected_count)
    return result.items

  def testCreateHuntFromFlow(self):
    client_id = self.SetupClient(0)
    self.RequestAndGrantClientApproval(client_id)
    flow_args = network.NetstatArgs(listening_only=True)
    flow_id = flow_test_lib.StartFlow(
        network.Netstat,
        creator=self.test_username,
        client_id=client_id,
        flow_args=flow_args,
    )

    self.Open(f"/v2/clients/{client_id}")
    self.WaitUntil(
        self.IsElementPresent, "css=flow-details:contains('Netstat')"
    )

    self.Click("css=flow-details button[name=flowContextMenu]")
    self.WaitUntil(self.IsElementPresent, "css=button[name=createHunt]")
    self.Click("css=button[name=createHunt]")

    # Redirects the user to new hunt page with original flow information.
    self.WaitUntilEqual("/v2/new-hunt", self.GetCurrentUrlPath)
    self.WaitUntilEqual(
        f"clientId={client_id}&flowId={flow_id}", self.GetCurrentUrlQuery
    )

    # Make sure original flow information is displayed.
    self.WaitUntil(self.IsElementPresent, "css=[name=titleInput]")
    self.WaitUntil(self.IsElementPresent, "css=td:contains('Original flow')")
    self.WaitUntil(
        self.IsElementPresent, "css=flow-details:contains('Netstat')"
    )

    # Configure extra hunt-stuff.
    self.Click("css=mat-checkbox:contains('Linux')")
    self.Click("css=.rollout-speed-option button:contains('Unlimited')")

    # Fill out necessary approval information and create hunt.
    self.Type("css=approval-card input[name=reason]", "because")
    self.Click("css=button[id=runHunt]")

    hunts = self._ListHuntsAndAssertCount(self.test_username, 1)
    self.assertEqual(hunts[0].creator, self.test_username)
    unpacked_flow_args = flows_pb2.NetstatArgs()
    hunts[0].flow_args.Unpack(unpacked_flow_args)
    unpacked_flow_args_rdf = mig_network.ToRDFNetstatArgs(unpacked_flow_args)
    self.assertEqual(unpacked_flow_args_rdf, flow_args)  # Ensure proper copy.

    # Redirects to the new hunt page, check basic parts of the page are shown.
    self.WaitUntilEqual(f"/v2/hunts/{hunts[0].hunt_id}", self.GetCurrentUrlPath)

    self.WaitUntil(
        self.IsElementPresent, "css=button:contains('View flow arguments')"
    )
    self.Click("css=button:contains('View flow arguments')")
    self.WaitUntil(
        self.IsElementPresent, "css=hunt-flow-arguments:contains('Netstat')"
    )
    self.WaitUntil(
        self.IsElementPresent, f"css=hunt-flow-arguments:contains('{flow_id}')"
    )
    self.WaitUntil(
        self.IsElementPresent, "css=approval-card:contains('Request sent')"
    )

  def testCreateHuntFromHunt(self):
    original_hunt_description = "Dummy hunt"
    original_hunt_flow_args = transfer.GetFileArgs(
        pathspec=rdf_paths.PathSpec(
            path="/tmp/evil.txt",
            pathtype=rdf_paths.PathSpec.PathType.NTFS,
        )
    )
    original_hunt_id = self.CreateHunt(
        description=original_hunt_description,
        flow_runner_args=rdf_flow_runner.FlowRunnerArgs(
            flow_name=transfer.GetFile.__name__
        ),
        flow_args=original_hunt_flow_args,
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

    self.Open(f"/v2/hunts/{original_hunt_id}")
    self.WaitUntilEqual(f"/v2/hunts/{original_hunt_id}", self.GetCurrentUrlPath)

    self.WaitUntil(self.IsElementPresent, "css=button[name=copy-button]")
    self.Click("css=button[name=copy-button]")

    # Redirects the user to new hunt page with original hunt information.
    self.WaitUntilEqual("/v2/new-hunt", self.GetCurrentUrlPath)
    self.WaitUntilEqual(f"huntId={original_hunt_id}", self.GetCurrentUrlQuery)

    # Make sure original hunt information is displayed.
    self.WaitUntilEqual(
        f"{original_hunt_description} (copy)",
        self.GetValue,
        "css=[name=titleInput]",
    )
    self.WaitUntil(
        self.IsElementPresent, "css=td:contains('Original fleet collection')"
    )
    self.WaitUntil(
        self.IsElementPresent, "css=hunt-flow-arguments:contains('GetFile')"
    )

    # Make sure client params were copied, add another one.
    self.WaitUntil(
        self.IsElementPresent, "css=app-clients-form:contains('Client Name')"
    )
    self.WaitUntil(self.IsElementPresent, "css=[name=condition_0]")
    self.WaitUntil(self.IsElementPresent, "css=button[name=addCondition]")
    self.Click("css=button[name=addCondition]")
    self.WaitUntil(self.IsElementPresent, "css=button:contains('Label')")
    self.Click("css=button:contains('Label')")
    self.WaitUntil(
        self.IsElementPresent, "css=input[id=condition_1_label_name_0]"
    )
    self.Type("css=input[id=condition_1_label_name_0]", "special-label")

    # Check values were copied, and change them.
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

    # Fill out necessary approval information and create hunt.
    self.Type("css=approval-card input[name=reason]", "because")
    self.Click("css=button[id=runHunt]")

    # Give some time for the hunt creation and redirect to happen.
    self.WaitUntil(
        self.IsElementPresent, "css=button:contains('View flow arguments')"
    )

    hunts = self._ListHuntsAndAssertCount(self.test_username, 2)

    if original_hunt_id == hunts[0].hunt_id:
      original_hunt = hunts[0]
      copied_hunt = hunts[1]
    else:
      original_hunt = hunts[1]
      copied_hunt = hunts[0]

    self.assertEqual(original_hunt.creator, self.test_username)
    unpacked_flow_args = flows_pb2.GetFileArgs()
    original_hunt.flow_args.Unpack(unpacked_flow_args)
    unpacked_flow_args_rdf = mig_transfer.ToRDFGetFileArgs(unpacked_flow_args)
    self.assertEqual(unpacked_flow_args_rdf, original_hunt_flow_args)
    self.assertEqual(original_hunt.hunt_runner_args.client_rate, 60)
    self.assertEqual(original_hunt.hunt_runner_args.client_limit, 0)
    self.assertLen(original_hunt.hunt_runner_args.client_rule_set.rules, 1)

    self.assertEqual(copied_hunt.creator, self.test_username)
    unpacked_flow_args = flows_pb2.GetFileArgs()
    copied_hunt.flow_args.Unpack(unpacked_flow_args)
    unpacked_flow_args_rdf = mig_transfer.ToRDFGetFileArgs(unpacked_flow_args)
    self.assertEqual(unpacked_flow_args_rdf, original_hunt_flow_args)
    self.assertEqual(
        copied_hunt.original_object.hunt_reference.hunt_id, original_hunt_id
    )
    self.assertEqual(copied_hunt.hunt_runner_args.client_rate, 0)
    self.assertEqual(copied_hunt.hunt_runner_args.client_limit, 100)
    self.assertLen(copied_hunt.hunt_runner_args.client_rule_set.rules, 2)

    # Confirm redirection data.
    self.WaitUntilEqual(
        f"/v2/hunts/{copied_hunt.hunt_id}", self.GetCurrentUrlPath
    )
    self.Click("css=button:contains('View flow arguments')")
    self.WaitUntil(
        self.IsElementPresent, "css=hunt-flow-arguments:contains('GetFile')"
    )
    self.WaitUntil(
        self.IsElementPresent, "css=approval-card:contains('Request sent')"
    )

  def testNoHuntIsCreatedWhenInputInvalid(self):
    client_id = self.SetupClient(0)
    self.RequestAndGrantClientApproval(client_id)
    flow_id = flow_test_lib.StartFlow(
        network.Netstat,
        creator=self.test_username,
        client_id=client_id,
        flow_args=network.NetstatArgs(),
    )

    self.Open(f"/v2/clients/{client_id}")
    self.WaitUntil(
        self.IsElementPresent, "css=flow-details:contains('Netstat')"
    )

    self.Click("css=flow-details button[name=flowContextMenu]")
    self.WaitUntil(self.IsElementPresent, "css=button[name=createHunt]")
    self.Click("css=button[name=createHunt]")

    # Redirects the user to new hunt page with original flow information.
    self.WaitUntilEqual("/v2/new-hunt", self.GetCurrentUrlPath)
    self.WaitUntilEqual(
        f"clientId={client_id}&flowId={flow_id}", self.GetCurrentUrlQuery
    )
    # Make sure original flow information is displayed.
    self.WaitUntil(self.IsElementPresent, "css=[name=titleInput]")
    self.WaitUntil(self.IsElementPresent, "css=td:contains('Original flow')")
    self.WaitUntil(
        self.IsElementPresent, "css=flow-details:contains('Netstat')"
    )
    self.Click("css=button[name=toggle-advance-params-top]")

    self.Type("css=input[name=activeFor]", "fooo")
    self.Type("css=input[name=aveCPU]", "")
    self.Click("css=.client-cpu-limit-option button:contains('Custom')")
    self.Type("css=input[name=perClientCpuLimit]", "fooo")

    # Fill out necessary approval information and create hunt.
    self.Type("css=approval-card input[name=reason]", "because")
    self.Click("css=button[id=runHunt]")

    self._ListHuntsAndAssertCount(self.test_username, 0)
    self.WaitUntil(self.IsElementPresent, "css=.mdc-snackbar")

  def testHuntPresubmit(self):
    client_id = self.SetupClient(0)
    self.RequestAndGrantClientApproval(client_id)
    flow_id = flow_test_lib.StartFlow(
        network.Netstat,
        creator=self.test_username,
        client_id=client_id,
        flow_args=network.NetstatArgs(),
    )

    hunt_cfg = rdf_config.AdminUIHuntConfig(
        default_exclude_labels=["no-no"],
        make_default_exclude_labels_a_presubmit_check=True,
        presubmit_warning_message="not cool",
    )
    with test_lib.ConfigOverrider({"AdminUI.hunt_config": hunt_cfg}):
      self.Open(f"/v2/new-hunt?clientId={client_id}&flowId={flow_id}")

      # Make sure default exclude labels are displayed.
      self.WaitUntil(
          self.IsElementPresent, "css=input[id=condition_1_label_name_0]"
      )
      self.Type("css=input[id=condition_1_label_name_0]", "no-no")

      self.WaitUntilNot(
          self.IsElementPresent, "css=mat-card.warning:contains('not cool')"
      )

      # Removing the label should trigger the warning.
      self.Click("css=[name=condition_1] button#close")

      # Make sure the warning is now displayed.
      self.WaitUntil(
          self.IsElementPresent, "css=mat-card.warning:contains('not cool')"
      )

      # Fill out necessary approval information and create hunt.
      self.Type("css=approval-card input[name=reason]", "because")
      self.Click("css=button[id=runHunt]")

      self._ListHuntsAndAssertCount(self.test_username, 0)
      # Also fails in the API level,
      self.WaitUntil(self.IsElementPresent, "css=.mdc-snackbar")


if __name__ == "__main__":
  app.run(test_lib.main)
