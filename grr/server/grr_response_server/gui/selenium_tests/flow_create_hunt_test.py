#!/usr/bin/env python
"""Test hunt creation by flow."""
from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals


from grr_response_core.lib import flags

from grr_response_server.flows.general import processes as flows_processes
from grr_response_server.gui import gui_test_lib
from grr_response_server.output_plugins import email_plugin
from grr_response_server.rdfvalues import output_plugin as rdf_output_plugin
from grr.test_lib import action_mocks
from grr.test_lib import db_test_lib
from grr.test_lib import flow_test_lib
from grr.test_lib import hunt_test_lib
from grr.test_lib import test_lib


@db_test_lib.DualDBTest
class TestFlowCreateHunt(gui_test_lib.GRRSeleniumTest,
                         hunt_test_lib.StandardHuntTestMixin):

  def setUp(self):
    super(TestFlowCreateHunt, self).setUp()
    self.client_id = self.SetupClient(0).Basename()
    self.RequestAndGrantClientApproval(self.client_id)
    self.action_mock = action_mocks.FileFinderClientMock()

  def testCreateHuntFromFlow(self):
    email_descriptor = rdf_output_plugin.OutputPluginDescriptor(
        plugin_name=email_plugin.EmailOutputPlugin.__name__,
        plugin_args=email_plugin.EmailOutputPluginArgs(
            email_address="test@localhost", emails_limit=42))

    args = flows_processes.ListProcessesArgs(
        filename_regex="test[a-z]*", fetch_binaries=True)

    flow_test_lib.StartFlow(
        flows_processes.ListProcesses,
        flow_args=args,
        client_id=self.client_id,
        output_plugins=[email_descriptor])

    # Navigate to client and select newly created flow.
    self.Open("/#/clients/%s" % self.client_id)
    self.Click("css=a[grrtarget='client.flows']")
    self.Click("css=td:contains('ListProcesses')")

    # Open wizard and check if flow arguments are copied.
    self.Click("css=button[name=create_hunt]")

    self.WaitUntilEqual("test[a-z]*", self.GetValue,
                        "css=label:contains('Filename Regex') ~ * input")

    self.WaitUntil(
        self.IsChecked, "css=label:contains('Fetch Binaries') "
        "~ * input[type=checkbox]")

    # Go to output plugins page and check that we did not copy the output
    # plugins.
    self.Click("css=button:contains('Next')")
    self.WaitUntil(self.IsElementPresent,
                   "css=grr-wizard-form:contains('Hunt parameters')")
    self.Click("css=grr-new-hunt-wizard-form button.Next")
    self.WaitUntil(self.IsElementPresent,
                   "css=grr-wizard-form:contains('How to process results')")

    self.WaitUntilNot(self.IsElementPresent,
                      "css=grr-output-plugin-descriptor-form")

    # Nothing else to check, so finish the hunt.
    # Click on "Next" button
    self.Click("css=grr-new-hunt-wizard-form button.Next")
    self.WaitUntil(self.IsElementPresent,
                   "css=grr-wizard-form:contains('Where to run?')")
    self.Click("css=button:contains('Next')")
    self.WaitUntil(self.IsElementPresent,
                   "css=grr-wizard-form:contains('Review')")
    self.Click("css=button:contains('Create Hunt')")
    self.Click("css=button:contains('Done')")

    # Check that we get redirected to ManageHunts.
    self.WaitUntilEqual(1, self.GetCssCount,
                        "css=grr-hunts-list table tbody tr")
    self.WaitUntilEqual(1, self.GetCssCount,
                        "css=grr-hunts-list table tbody tr.row-selected")
    self.WaitUntil(self.IsTextPresent, "GenericHunt")
    self.WaitUntil(self.IsTextPresent, flows_processes.ListProcesses.__name__)

  def testCheckCreateHuntButtonIsOnlyEnabledWithFlowSelection(self):
    flow_test_lib.StartFlow(
        gui_test_lib.RecursiveTestFlow, client_id=self.client_id)

    # Open client and find the flow.
    self.Open("/#/clients/%s" % self.client_id)
    self.Click("css=a[grrtarget='client.flows']")

    # No flow selected, so the button should be disabled.
    self.WaitUntil(self.IsElementPresent,
                   "css=button[name=create_hunt][disabled]")

    # And enabled after selecting the test flow.
    self.Click("css=td:contains('RecursiveTestFlow')")
    self.WaitUntil(self.IsElementPresent,
                   "css=button[name=create_hunt]:not([disabled])")


if __name__ == "__main__":
  flags.StartMain(test_lib.main)
