#!/usr/bin/env python
"""Test flow copy UI."""


import unittest
from grr.gui import gui_test_lib

from grr.lib import flags
from grr.lib.rdfvalues import client as rdf_client
from grr.server import aff4
from grr.server import flow
from grr.server import output_plugin
from grr.server.flows.general import processes as flows_processes
from grr.server.hunts import standard_test
from grr.server.output_plugins import email_plugin
from grr.test_lib import fixture_test_lib


class TestFlowCopy(gui_test_lib.GRRSeleniumTest,
                   standard_test.StandardHuntTestMixin):

  def setUp(self):
    super(TestFlowCopy, self).setUp()

    # Prepare our fixture.
    self.client_id = rdf_client.ClientURN("C.0000000000000001")
    # This attribute is used by StandardHuntTestMixin.
    self.client_ids = [self.client_id]
    fixture_test_lib.ClientFixture(self.client_id, self.token)
    self.RequestAndGrantClientApproval("C.0000000000000001")

    self.email_descriptor = output_plugin.OutputPluginDescriptor(
        plugin_name=email_plugin.EmailOutputPlugin.__name__,
        plugin_args=email_plugin.EmailOutputPluginArgs(
            email_address="test@localhost", emails_limit=42))

  def testOriginalFlowArgsAreShownInCopyForm(self):
    args = flows_processes.ListProcessesArgs(
        filename_regex="test[a-z]*", fetch_binaries=True)
    flow.GRRFlow.StartFlow(
        flow_name=flows_processes.ListProcesses.__name__,
        args=args,
        client_id=self.client_id,
        output_plugins=[self.email_descriptor],
        token=self.token)

    # Navigate to client and select newly created flow.
    self.Open("/#c=C.0000000000000001")
    self.Click("css=a[grrtarget='client.flows']")
    self.Click("css=td:contains('ListProcesses')")

    # Open wizard and check if flow arguments are copied.
    self.Click("css=button[name=copy_flow]")

    self.WaitUntil(self.IsTextPresent, "Copy ListProcesses flow")

    self.WaitUntilEqual("test[a-z]*", self.GetValue,
                        "css=label:contains('Filename Regex') ~ * input")

    self.WaitUntil(self.IsChecked, "css=label:contains('Fetch Binaries') "
                   "~ * input[type=checkbox]")

    # Check that output plugin info is also copied.
    self.WaitUntilEqual("string:EmailOutputPlugin", self.GetValue,
                        "css=label:contains('Plugin') ~ * select")
    self.WaitUntilEqual("test@localhost", self.GetValue,
                        "css=label:contains('Email address') ~ * input")
    self.WaitUntilEqual("42", self.GetValue,
                        "css=label:contains('Emails limit') ~ * input")

  def testCopyingFlowUpdatesFlowListAndSelectsNewFlow(self):
    args = flows_processes.ListProcessesArgs(
        filename_regex="test[a-z]*", fetch_binaries=True)
    flow.GRRFlow.StartFlow(
        flow_name=flows_processes.ListProcesses.__name__,
        args=args,
        client_id=self.client_id,
        token=self.token)

    # Navigate to client and select newly created flow.
    self.Open("/#c=C.0000000000000001")
    self.Click("css=a[grrtarget='client.flows']")
    self.Click("css=td:contains('ListProcesses')")

    # Check that there's only one ListProcesses flow.
    self.WaitUntilNot(
        self.IsElementPresent,
        "css=grr-client-flows-list tr:contains('ListProcesses'):nth(1)")

    # Open wizard and check if flow arguments are copied.
    self.Click("css=button[name=copy_flow]")
    self.Click("css=button:contains('Launch'):not([disabled])")

    # Check that flows list got updated and that the new flow is selected.
    self.WaitUntil(
        self.IsElementPresent,
        "css=grr-client-flows-list tr:contains('ListProcesses'):nth(1)")
    self.WaitUntil(self.IsElementPresent, "css=grr-client-flows-list "
                   "tr:contains('ListProcesses'):nth(0).row-selected")

  def testAddingOutputPluginToCopiedFlowWorks(self):
    args = flows_processes.ListProcessesArgs(
        filename_regex="test[a-z]*", fetch_binaries=True)
    flow.GRRFlow.StartFlow(
        flow_name=flows_processes.ListProcesses.__name__,
        args=args,
        client_id=self.client_id,
        token=self.token)

    # Navigate to client and select newly created flow.
    self.Open("/#c=C.0000000000000001")
    self.Click("css=a[grrtarget='client.flows']")
    self.Click("css=td:contains('ListProcesses')")

    # Open wizard and check if flow arguments are copied.
    self.Click("css=button[name=copy_flow]")

    self.Click("css=label:contains('Output Plugins') ~ * button")
    self.WaitUntil(self.IsElementPresent,
                   "css=label:contains('Plugin') ~ * select")

  def testUserChangesToCopiedFlowAreRespected(self):
    args = flows_processes.ListProcessesArgs(
        filename_regex="test[a-z]*", fetch_binaries=True)
    flow.GRRFlow.StartFlow(
        flow_name=flows_processes.ListProcesses.__name__,
        args=args,
        client_id=self.client_id,
        output_plugins=[self.email_descriptor],
        token=self.token)

    # Navigate to client and select newly created flow.
    self.Open("/#c=C.0000000000000001")
    self.Click("css=a[grrtarget='client.flows']")
    self.Click("css=td:contains('ListProcesses')")

    # Open wizard and change the arguments.
    self.Click("css=button[name=copy_flow]")

    self.Type("css=label:contains('Filename Regex') ~ * input",
              "somethingElse*")

    self.Click("css=label:contains('Fetch Binaries') ~ * input[type=checkbox]")

    # Change output plugin and add another one.
    self.Click("css=label:contains('Output Plugins') ~ * button")
    self.Select("css=grr-output-plugin-descriptor-form "
                "label:contains('Plugin') ~ * select:eq(0)",
                "DummyOutputPlugin")
    self.Type("css=grr-output-plugin-descriptor-form "
              "label:contains('Filename Regex'):eq(0) ~ * input:text",
              "foobar!")

    self.Click("css=button:contains('Launch')")

    # Check that flows list got updated and that the new flow is selected.
    self.WaitUntil(
        self.IsElementPresent,
        "css=grr-client-flows-list tr:contains('ListProcesses'):nth(1)")
    self.WaitUntil(self.IsElementPresent, "css=grr-client-flows-list "
                   "tr:contains('ListProcesses'):nth(0).row-selected")

    # Now open the last flow and check that it has the changes we made.
    fd = aff4.FACTORY.Open(self.client_id.Add("flows"), token=self.token)
    flows = sorted(fd.ListChildren(), key=lambda x: x.age)
    fobj = aff4.FACTORY.Open(flows[-1], token=self.token)

    self.assertEqual(fobj.args,
                     flows_processes.ListProcessesArgs(
                         filename_regex="somethingElse*",))
    self.assertListEqual(
        list(fobj.runner_args.output_plugins), [
            output_plugin.OutputPluginDescriptor(
                plugin_name=gui_test_lib.DummyOutputPlugin.__name__,
                plugin_args=flows_processes.ListProcessesArgs(
                    filename_regex="foobar!")), self.email_descriptor
        ])

  def testCopyingHuntFlowWorks(self):
    self.StartHunt(description="demo hunt")
    self.AssignTasksToClients(client_ids=[self.client_id])
    self.RunHunt(failrate=-1)

    # Navigate to client and select newly created hunt flow.
    self.Open("/#/clients/%s" % self.client_id.Basename())
    self.Click("css=a[grrtarget='client.flows']")

    # StartHunt creates a hunt with a GetFile flow, so selecting a GetFile row.
    self.Click("css=td:contains('GetFile')")
    self.Click("css=button[name=copy_flow]")
    self.Click("css=button:contains('Launch')")

    # Check that flows list got updated and that the new flow is selected.
    self.WaitUntil(self.IsElementPresent,
                   "css=grr-client-flows-list tr:contains('GetFile'):nth(1)")
    self.WaitUntil(self.IsElementPresent, "css=grr-client-flows-list "
                   "tr:contains('GetFile'):nth(0).row-selected")


def main(argv):
  del argv  # Unused.
  # Run the full test suite
  unittest.main()


if __name__ == "__main__":
  flags.StartMain(main)
