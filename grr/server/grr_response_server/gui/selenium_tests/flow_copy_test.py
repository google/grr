#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Test flow copy UI."""
from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals


import mock

from grr_response_core.lib import flags
from grr_response_core.lib.rdfvalues import client as rdf_client
from grr_response_core.lib.rdfvalues import file_finder as rdf_file_finder
from grr_response_server import access_control
from grr_response_server import aff4
from grr_response_server import data_store
from grr_response_server.flows.general import file_finder as flows_file_finder
from grr_response_server.flows.general import processes as flows_processes
from grr_response_server.gui import api_call_router_with_approval_checks
from grr_response_server.gui import gui_test_lib
from grr_response_server.output_plugins import email_plugin
from grr_response_server.rdfvalues import output_plugin as rdf_output_plugin
from grr.test_lib import db_test_lib
from grr.test_lib import fixture_test_lib
from grr.test_lib import flow_test_lib
from grr.test_lib import hunt_test_lib
from grr.test_lib import test_lib


@db_test_lib.DualDBTest
class TestFlowCopy(gui_test_lib.GRRSeleniumTest,
                   hunt_test_lib.StandardHuntTestMixin):

  def setUp(self):
    super(TestFlowCopy, self).setUp()

    # Prepare our fixture.
    self.client_id = rdf_client.ClientURN("C.0000000000000001")
    # This attribute is used by StandardHuntTestMixin.
    self.client_ids = [self.client_id]
    fixture_test_lib.ClientFixture(self.client_id, self.token)
    self.RequestAndGrantClientApproval("C.0000000000000001")

    self.email_descriptor = rdf_output_plugin.OutputPluginDescriptor(
        plugin_name=email_plugin.EmailOutputPlugin.__name__,
        plugin_args=email_plugin.EmailOutputPluginArgs(
            email_address="test@localhost", emails_limit=42))

  def testOriginalFlowArgsAreShownInCopyForm(self):
    args = flows_processes.ListProcessesArgs(
        filename_regex="test[a-z]*", fetch_binaries=True)
    flow_test_lib.StartFlow(
        flows_processes.ListProcesses,
        flow_args=args,
        client_id=self.client_id,
        output_plugins=[self.email_descriptor])

    # Navigate to client and select newly created flow.
    self.Open("/#/clients/C.0000000000000001/flows")
    self.Click("css=td:contains('ListProcesses')")

    # Open wizard and check if flow arguments are copied.
    self.Click("css=button[name=copy_flow]")

    self.WaitUntil(self.IsTextPresent, "Copy ListProcesses flow")

    self.WaitUntilEqual("test[a-z]*", self.GetValue,
                        "css=label:contains('Filename Regex') ~ * input")

    self.WaitUntil(
        self.IsChecked, "css=label:contains('Fetch Binaries') "
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
    flow_test_lib.StartFlow(
        flows_processes.ListProcesses, flow_args=args, client_id=self.client_id)

    # Navigate to client and select newly created flow.
    self.Open("/#/clients/C.0000000000000001/flows")
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
    self.WaitUntil(
        self.IsElementPresent, "css=grr-client-flows-list "
        "tr:contains('ListProcesses'):nth(0).row-selected")

  def testAddingOutputPluginToCopiedFlowWorks(self):
    args = flows_processes.ListProcessesArgs(
        filename_regex="test[a-z]*", fetch_binaries=True)
    flow_test_lib.StartFlow(
        flows_processes.ListProcesses, flow_args=args, client_id=self.client_id)

    # Navigate to client and select newly created flow.
    self.Open("/#/clients/C.0000000000000001/flows")
    self.Click("css=td:contains('ListProcesses')")

    # Open wizard and check if flow arguments are copied.
    self.Click("css=button[name=copy_flow]")

    self.Click("css=label:contains('Output Plugins') ~ * button")
    self.WaitUntil(self.IsElementPresent,
                   "css=label:contains('Plugin') ~ * select")

  def testUserChangesToCopiedFlowAreRespected(self):
    args = flows_processes.ListProcessesArgs(
        filename_regex="test[a-z]*", fetch_binaries=True)
    flow_test_lib.StartFlow(
        flows_processes.ListProcesses,
        flow_args=args,
        client_id=self.client_id,
        output_plugins=[self.email_descriptor])

    # Navigate to client and select newly created flow.
    self.Open("/#/clients/C.0000000000000001/flows")
    self.Click("css=td:contains('ListProcesses')")

    # Open wizard and change the arguments.
    self.Click("css=button[name=copy_flow]")

    self.Type("css=label:contains('Filename Regex') ~ * input",
              "somethingElse*")

    self.Click("css=label:contains('Fetch Binaries') ~ * input[type=checkbox]")

    # Change output plugin and add another one.
    self.Click("css=label:contains('Output Plugins') ~ * button")
    self.Select(
        "css=grr-output-plugin-descriptor-form "
        "label:contains('Plugin') ~ * select:eq(0)", "DummyOutputPlugin")
    self.Type(
        "css=grr-output-plugin-descriptor-form "
        "label:contains('Filename Regex'):eq(0) ~ * input:text", "foobar!")

    self.Click("css=button:contains('Launch')")

    # Check that flows list got updated and that the new flow is selected.
    self.WaitUntil(
        self.IsElementPresent,
        "css=grr-client-flows-list tr:contains('ListProcesses'):nth(1)")
    self.WaitUntil(
        self.IsElementPresent, "css=grr-client-flows-list "
        "tr:contains('ListProcesses'):nth(0).row-selected")

    # Now open the last flow and check that it has the changes we made.
    if data_store.RelationalDBFlowsEnabled():
      flows = data_store.REL_DB.ReadAllFlowObjects(self.client_id.Basename())
      flows.sort(key=lambda f: f.create_time)
      fobj = flows[-1]

      self.assertListEqual(
          list(fobj.output_plugins), [
              rdf_output_plugin.OutputPluginDescriptor(
                  plugin_name=gui_test_lib.DummyOutputPlugin.__name__,
                  plugin_args=flows_processes.ListProcessesArgs(
                      filename_regex="foobar!")), self.email_descriptor
          ])
    else:
      fd = aff4.FACTORY.Open(self.client_id.Add("flows"), token=self.token)
      flows = sorted(fd.ListChildren(), key=lambda x: x.age)
      fobj = aff4.FACTORY.Open(flows[-1], token=self.token)
      self.assertListEqual(
          list(fobj.runner_args.output_plugins), [
              rdf_output_plugin.OutputPluginDescriptor(
                  plugin_name=gui_test_lib.DummyOutputPlugin.__name__,
                  plugin_args=flows_processes.ListProcessesArgs(
                      filename_regex="foobar!")), self.email_descriptor
          ])

    self.assertEqual(
        fobj.args,
        flows_processes.ListProcessesArgs(filename_regex="somethingElse*",))

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
    self.WaitUntil(
        self.IsElementPresent, "css=grr-client-flows-list "
        "tr:contains('GetFile'):nth(0).row-selected")

  def testCopyingFlowWithRawBytesWithNonAsciiCharsInArgumentsWorks(self):
    # Literal is defined simply as "bytes" in its proto definition. We make sure
    # to assign ascii-incompatible value to it here.
    condition = rdf_file_finder.FileFinderCondition.ContentsLiteralMatch(
        literal="zażółć gęślą jaźń".encode("utf-8"))
    action = rdf_file_finder.FileFinderAction.Download()
    args = rdf_file_finder.FileFinderArgs(
        action=action, conditions=[condition], paths=["a/b/*"])

    flow_test_lib.StartFlow(
        flows_file_finder.FileFinder, flow_args=args, client_id=self.client_id)

    # Navigate to client and select newly created flow.
    self.Open("/#/clients/C.0000000000000001/flows")
    self.Click("css=td:contains('FileFinder')")

    # Open wizard and launch the copy flow.
    self.Click("css=button[name=copy_flow]")
    self.Click("css=button:contains('Launch')")

    # Check that flows list got updated and that the new flow is selected.
    self.WaitUntil(
        self.IsElementPresent,
        "css=grr-client-flows-list tr:contains('FileFinder'):nth(1)")
    self.WaitUntil(
        self.IsElementPresent, "css=grr-client-flows-list "
        "tr:contains('FileFinder'):nth(0).row-selected")

  def testCopyACLErrorIsCorrectlyDisplayed(self):
    args = rdf_file_finder.FileFinderArgs(paths=["a/b/*"])
    flow_test_lib.StartFlow(
        flows_file_finder.FileFinder, flow_args=args, client_id=self.client_id)

    # Navigate to client and select newly created flow.
    self.Open("/#/clients/C.0000000000000001/flows")
    self.Click("css=td:contains('FileFinder')")

    # Stub out the API handler to guarantee failure.
    with mock.patch.object(
        api_call_router_with_approval_checks.ApiCallRouterWithApprovalChecks,
        "CreateFlow") as create_flow_mock:
      # The error has to be an ACL error, since ACL errors are not handled
      # by the global errors handler and are not automatically displayed.
      create_flow_mock.side_effect = [
          access_control.UnauthorizedAccess("oh no!")
      ]

      # Open wizard and launch the copy flow.
      self.Click("css=button[name=copy_flow]")
      self.Click("css=button:contains('Launch')")

    self.WaitUntil(self.IsElementPresent,
                   "css=.modal-dialog .text-danger:contains('oh no!')")

    # Check that closing the dialog doesn't change flow selection.
    self.Click("css=button[name=Close]")
    self.WaitUntil(self.IsElementPresent,
                   "css=grr-client-flows-view tr.row-selected")


if __name__ == "__main__":
  flags.StartMain(test_lib.main)
