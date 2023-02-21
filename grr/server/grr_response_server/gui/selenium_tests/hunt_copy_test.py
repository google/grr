#!/usr/bin/env python
"""Test of "Copy Hunt" wizard."""

from absl import app

from grr_response_core.lib.rdfvalues import file_finder as rdf_file_finder
from grr_response_core.lib.rdfvalues import paths as rdf_paths
from grr_response_server import data_store
from grr_response_server import foreman_rules
from grr_response_server.flows.general import file_finder
from grr_response_server.flows.general import transfer
from grr_response_server.gui import gui_test_lib
from grr_response_server.rdfvalues import flow_runner as rdf_flow_runner
from grr_response_server.rdfvalues import output_plugin as rdf_output_plugin
from grr.test_lib import test_lib


class HuntCopyTest(gui_test_lib.GRRSeleniumHuntTest):
  """Test the hunt copying GUI."""

  def CreateSampleHunt(self, description, creator=None):
    self.StartHunt(
        description=description,
        flow_runner_args=rdf_flow_runner.FlowRunnerArgs(
            flow_name=transfer.GetFile.__name__),
        flow_args=transfer.GetFileArgs(
            pathspec=rdf_paths.PathSpec(
                path="/tmp/evil.txt",
                pathtype=rdf_paths.PathSpec.PathType.NTFS,
            )),
        client_rule_set=self._CreateForemanClientRuleSet(),
        output_plugins=[
            rdf_output_plugin.OutputPluginDescriptor(
                plugin_name="DummyOutputPlugin",
                args=gui_test_lib.DummyOutputPlugin.args_type(
                    filename_regex="blah!", fetch_binaries=True))
        ],
        client_rate=60,
        paused=True,
        creator=creator)

  def testCopyHuntPrefillsNewHuntWizard(self):
    self.CreateSampleHunt("model hunt")

    self.Open("/#main=ManageHunts")
    self.Click("css=tr:contains('model hunt')")
    self.Click("css=button[name=CopyHunt]:not([disabled])")

    # Wait until dialog appears.
    self.WaitUntil(self.IsTextPresent, "What to run?")

    # Check that non-default values of sample hunt are prefilled.
    self.WaitUntilEqual(
        "/tmp/evil.txt", self.GetValue, "css=grr-new-hunt-wizard-form "
        "label:contains('Path') ~ * input:text")

    self.WaitUntilEqual(
        "NTFS", self.GetText, "css=grr-new-hunt-wizard-form "
        "label:contains('Pathtype') ~ * select option:selected")

    # Click on "Next" button
    self.Click("css=grr-new-hunt-wizard-form button.Next")
    self.WaitUntil(self.IsElementPresent,
                   "css=grr-wizard-form:contains('Hunt parameters')")

    self.WaitUntilEqual(
        "model hunt (copy)", self.GetValue, "css=grr-new-hunt-wizard-form "
        "label:contains('Description') ~ * input:text")

    self.WaitUntilEqual(
        "60", self.GetValue, "css=grr-new-hunt-wizard-form "
        "label:contains('Client rate') ~ * input")

    # Click on "Next" button.
    self.Click("css=grr-new-hunt-wizard-form button.Next")
    self.WaitUntil(self.IsTextPresent, "How to process results")

    # Check that output plugins list is prefilled.
    self.WaitUntilEqual(
        "DummyOutputPlugin", self.GetText, "css=grr-new-hunt-wizard-form "
        "label:contains('Plugin') ~ * select option:selected")

    self.WaitUntilEqual(
        "blah!", self.GetValue, "css=grr-new-hunt-wizard-form "
        "label:contains('Filepath Regex') ~ * input:text")

    self.WaitUntil(
        self.IsElementPresent, "css=grr-new-hunt-wizard-form "
        "label:contains('Fetch Binaries') ~ * input:checked")

    # Click on "Next" button.
    self.Click("css=grr-new-hunt-wizard-form button.Next")
    self.WaitUntil(self.IsTextPresent, "Where to run?")

    # Check that rules list is prefilled.
    self.WaitUntilEqual(
        "Regex", self.GetText, "css=grr-new-hunt-wizard-form "
        "label:contains('Rule type') "
        "~ * select option:selected")

    rule = foreman_rules.ForemanRegexClientRule
    label = rule.ForemanStringField.CLIENT_NAME.description
    self.WaitUntilEqual(
        label, self.GetText, "css=grr-new-hunt-wizard-form "
        "label:contains('Field') "
        "~ * select option:selected")

    self.WaitUntilEqual(
        "GRR", self.GetValue, "css=grr-new-hunt-wizard-form "
        "label:contains('Attribute regex') ~ * input:text")

    # Click on "Next" button.
    self.Click("css=grr-new-hunt-wizard-form button.Next")
    self.WaitUntil(self.IsTextPresent, "Review")

    # Check that review page contains expected values.
    self.WaitUntil(self.IsTextPresent, "NTFS")
    self.WaitUntil(self.IsTextPresent, "/tmp/evil.txt")
    self.WaitUntil(self.IsTextPresent, transfer.GetFile.__name__)
    self.WaitUntil(self.IsTextPresent, "DummyOutputPlugin")
    self.WaitUntil(self.IsTextPresent, "blah!")
    self.WaitUntil(self.IsTextPresent, "model hunt (copy)")
    self.WaitUntil(self.IsTextPresent, "CLIENT_NAME")
    self.WaitUntil(self.IsTextPresent, "60")

  def testCopyHuntCreatesExactCopyWithChangedDescription(self):
    self.CreateSampleHunt("model hunt")

    self.Open("/#main=ManageHunts")
    self.Click("css=tr:contains('model hunt')")
    self.Click("css=button[name=CopyHunt]:not([disabled])")

    # Wait until dialog appears and then click through.
    self.WaitUntil(self.IsTextPresent, "What to run?")

    # Click on "Next" button
    self.Click("css=grr-new-hunt-wizard-form button.Next")
    self.WaitUntil(self.IsElementPresent,
                   "css=grr-wizard-form:contains('Hunt parameters')")

    # Click on "Next" button.
    self.Click("css=grr-new-hunt-wizard-form button.Next")
    self.WaitUntil(self.IsTextPresent, "How to process results")

    # Click on "Next" button.
    self.Click("css=grr-new-hunt-wizard-form button.Next")
    self.WaitUntil(self.IsTextPresent, "Where to run?")

    # Click on "Next" button.
    self.Click("css=grr-new-hunt-wizard-form button.Next")
    self.WaitUntil(self.IsTextPresent, "Review")

    # Click on "Run" button.
    self.Click("css=grr-new-hunt-wizard-form button.Next")
    self.WaitUntil(self.IsTextPresent, "Created Hunt")

    hunts_list = sorted(
        data_store.REL_DB.ReadHuntObjects(offset=0, count=10),
        key=lambda x: x.create_time)

    self.assertLen(hunts_list, 2)

    first_hunt = hunts_list[0]
    last_hunt = hunts_list[1]

    # Check that generic hunt arguments are equal.
    self.assertEqual(first_hunt.args, last_hunt.args)

    self.assertEqual(first_hunt.description + " (copy)", last_hunt.description)
    self.assertEqual(first_hunt.client_rate, last_hunt.client_rate)
    self.assertEqual(first_hunt.client_rule_set, last_hunt.client_rule_set)

  def testCopyHuntRespectsUserChanges(self):
    self.CreateSampleHunt("model hunt")

    self.Open("/#main=ManageHunts")
    self.Click("css=tr:contains('model hunt')")
    self.Click("css=button[name=CopyHunt]:not([disabled])")

    # Wait until dialog appears and then click through.
    self.WaitUntil(self.IsTextPresent, "What to run?")

    # Change values in the flow configuration.
    self.Type(
        "css=grr-new-hunt-wizard-form label:contains('Path') "
        "~ * input:text", "/tmp/very-evil.txt")

    self.Select(
        "css=grr-new-hunt-wizard-form label:contains('Pathtype') "
        "~ * select", "OS")

    # Click on "Next" button
    self.Click("css=grr-new-hunt-wizard-form button.Next")
    self.WaitUntil(self.IsElementPresent,
                   "css=grr-wizard-form:contains('Hunt parameters')")

    self.Type(
        "css=grr-new-hunt-wizard-form label:contains('Description') "
        "~ * input:text", "my personal copy")

    self.Type(
        "css=grr-new-hunt-wizard-form label:contains('Client rate') "
        "~ * input", "42")

    # Click on "Next" button.
    self.Click("css=grr-new-hunt-wizard-form button.Next")
    self.WaitUntil(self.IsTextPresent, "How to process results")

    # Change output plugin and add another one.
    self.Click("css=grr-new-hunt-wizard-form button[name=Add]")
    self.Select("css=grr-configure-output-plugins-page select:eq(0)",
                "DummyOutputPlugin")
    self.Type(
        "css=grr-configure-output-plugins-page "
        "label:contains('Filepath Regex'):eq(0) ~ * input:text", "foobar!")

    # Click on "Next" button.
    self.Click("css=grr-new-hunt-wizard-form button.Next")
    self.WaitUntil(self.IsTextPresent, "Where to run?")

    # Replace a rule with another one.
    self.Click("css=grr-configure-rules-page button[name=Remove]")
    self.Click("css=grr-configure-rules-page button[name=Add]")
    self.Click("css=grr-configure-rules-page label:contains('Os darwin') ~ * "
               "input[type=checkbox]")

    # Click on "Next" button.
    self.Click("css=grr-new-hunt-wizard-form button.Next")
    self.WaitUntil(self.IsTextPresent, "Review")

    # Check that expected values are shown in the review.
    self.WaitUntil(self.IsTextPresent, "OS")
    self.WaitUntil(self.IsTextPresent, "/tmp/very-evil.txt")
    self.WaitUntil(self.IsTextPresent, transfer.GetFile.__name__)
    self.WaitUntil(self.IsTextPresent, "DummyOutputPlugin")
    self.WaitUntil(self.IsTextPresent, "foobar!")
    self.WaitUntil(self.IsTextPresent, "blah!")
    self.WaitUntil(self.IsTextPresent, "my personal copy")
    self.WaitUntil(self.IsTextPresent, "Os darwin")
    self.WaitUntil(self.IsTextPresent, "42")

    # Click on "Run" button.
    self.Click("css=grr-new-hunt-wizard-form button.Next")
    self.WaitUntil(self.IsTextPresent, "Created Hunt")

    hunts_list = sorted(
        data_store.REL_DB.ReadHuntObjects(offset=0, count=10),
        key=lambda x: x.create_time)

    self.assertLen(hunts_list, 2)

    last_hunt = hunts_list[-1]

    args = last_hunt.args.standard.flow_args.Unpack(transfer.GetFileArgs)
    self.assertEqual(args.pathspec.path, "/tmp/very-evil.txt")
    self.assertEqual(args.pathspec.pathtype, "OS")
    self.assertEqual(last_hunt.args.standard.flow_name,
                     transfer.GetFile.__name__)

    self.assertLen(last_hunt.output_plugins, 2)
    self.assertEqual(
        last_hunt.output_plugins[0],
        rdf_output_plugin.OutputPluginDescriptor(
            plugin_name="DummyOutputPlugin",
            args=gui_test_lib.DummyOutputPlugin.args_type(
                filename_regex="foobar!")))
    self.assertEqual(
        last_hunt.output_plugins[1],
        rdf_output_plugin.OutputPluginDescriptor(
            plugin_name="DummyOutputPlugin",
            args=gui_test_lib.DummyOutputPlugin.args_type(
                filename_regex="blah!", fetch_binaries=True)))

    self.assertAlmostEqual(last_hunt.client_rate, 42)
    self.assertEqual(last_hunt.description, "my personal copy")
    self.assertEqual(
        last_hunt.client_rule_set,
        foreman_rules.ForemanClientRuleSet(rules=[
            foreman_rules.ForemanClientRule(
                os=foreman_rules.ForemanOsClientRule(os_darwin=True))
        ]))

  def testCopyHuntHandlesLiteralExpressionCorrectly(self):
    """Literals are raw bytes. Testing that raw bytes are processed right."""
    literal_match = rdf_file_finder.FileFinderContentsLiteralMatchCondition(
        literal=b"foo\x0d\xc8bar")

    self.StartHunt(
        description="model hunt",
        flow_runner_args=rdf_flow_runner.FlowRunnerArgs(
            flow_name=file_finder.FileFinder.__name__),
        flow_args=rdf_file_finder.FileFinderArgs(
            conditions=[
                rdf_file_finder.FileFinderCondition(
                    condition_type="CONTENTS_LITERAL_MATCH",
                    contents_literal_match=literal_match)
            ],
            paths=["/tmp/evil.txt"]))

    self.Open("/#main=ManageHunts")
    self.Click("css=tr:contains('model hunt')")
    self.Click("css=button[name=CopyHunt]:not([disabled])")

    # Wait until dialog appears.
    self.WaitUntil(self.IsTextPresent, "What to run?")

    # Check that non-default values of sample hunt are prefilled.
    self.WaitUntilEqual(
        "foo\\x0d\\xc8bar", self.GetValue, "css=grr-new-hunt-wizard-form "
        "label:contains('Literal') ~ * input:text")

    # Click on "Next" button
    self.Click("css=grr-new-hunt-wizard-form button.Next")
    self.WaitUntil(self.IsElementPresent,
                   "css=grr-wizard-form:contains('Hunt parameters')")
    # Click on "Next" button.
    self.Click("css=grr-new-hunt-wizard-form button.Next")
    self.WaitUntil(self.IsTextPresent, "How to process results")
    # Click on "Next" button
    self.Click("css=grr-new-hunt-wizard-form button.Next")
    self.WaitUntil(self.IsTextPresent, "Where to run?")
    # Click on "Next" button
    self.Click("css=grr-new-hunt-wizard-form button.Next")
    self.WaitUntil(self.IsTextPresent, "Review")

    # Check that the arguments summary is present.
    self.WaitUntil(self.IsTextPresent, file_finder.FileFinder.__name__)
    self.WaitUntil(self.IsTextPresent, "foo\\x0d\\xc8bar")

    # Click on "Run" button
    self.Click("css=grr-new-hunt-wizard-form button.Next")
    self.WaitUntil(self.IsTextPresent, "Created Hunt")
    # Close the window and check that the hunt was created.
    self.Click("css=button.Next")

    hunts_list = sorted(
        data_store.REL_DB.ReadHuntObjects(offset=0, count=10),
        key=lambda x: x.create_time)

    self.assertLen(hunts_list, 2)

    last_hunt = hunts_list[-1]

    # Check that the hunt was created with a correct literal value.
    self.assertEqual(last_hunt.args.standard.flow_name,
                     file_finder.FileFinder.__name__)

    args = last_hunt.args.standard.flow_args.Unpack(
        rdf_file_finder.FileFinderArgs)
    self.assertEqual(args.conditions[0].contents_literal_match.literal,
                     b"foo\x0d\xc8bar")

  def testCopyHuntPreservesRuleType(self):
    self.StartHunt(
        description="model hunt",
        flow_runner_args=rdf_flow_runner.FlowRunnerArgs(
            flow_name=transfer.GetFile.__name__),
        flow_args=transfer.GetFileArgs(
            pathspec=rdf_paths.PathSpec(
                path="/tmp/evil.txt",
                pathtype=rdf_paths.PathSpec.PathType.NTFS,
            )),
        client_rule_set=foreman_rules.ForemanClientRuleSet(rules=[
            foreman_rules.ForemanClientRule(
                rule_type=foreman_rules.ForemanClientRule.Type.OS,
                os=foreman_rules.ForemanOsClientRule(os_darwin=True))
        ]),
        creator=self.test_username)

    self.Open("/#main=ManageHunts")
    self.Click("css=tr:contains('model hunt')")
    self.Click("css=button[name=CopyHunt]:not([disabled])")

    # Wait until dialog appears.
    self.WaitUntil(self.IsTextPresent, "What to run?")
    # Click on "Next" button
    self.Click("css=grr-new-hunt-wizard-form button.Next")
    self.WaitUntil(self.IsElementPresent,
                   "css=grr-wizard-form:contains('Hunt parameters')")
    # Click on "Next" button.
    self.Click("css=grr-new-hunt-wizard-form button.Next")
    self.WaitUntil(self.IsTextPresent, "How to process results")
    # Click on "Next" button
    self.Click("css=grr-new-hunt-wizard-form button.Next")
    self.WaitUntil(self.IsTextPresent, "Where to run?")
    self.WaitUntil(
        self.IsElementPresent, "css=grr-new-hunt-wizard-form "
        "label:contains('Os darwin') ~ * input:checked")

  def testRuleTypeChangeClearsItsProto(self):
    # Open up and click on View Hunts.
    self.Open("/")
    self.Click("css=a[grrtarget=hunts]")

    # Open up "New Hunt" wizard
    self.Click("css=button[name=NewHunt]")

    # Click on Filesystem item in flows list
    self.Click("css=#_Filesystem > i.jstree-icon")

    # Click on the FileFinder item in Filesystem flows list
    self.Click("link=File Finder")

    # Click on "Next" button
    self.Click("css=grr-new-hunt-wizard-form button.Next")
    self.WaitUntil(self.IsElementPresent,
                   "css=grr-wizard-form:contains('Hunt parameters')")

    # Click on "Next" button
    self.Click("css=grr-new-hunt-wizard-form button.Next")
    self.WaitUntil(self.IsTextPresent, "How to process results")

    # Click on "Next" button
    self.Click("css=grr-new-hunt-wizard-form button.Next")
    self.WaitUntil(self.IsTextPresent, "Where to run?")

    # Changing the rule type clears the entered data under the hood.
    self.Click("css=grr-configure-rules-page button[name=Add]")
    self.Click("css=grr-configure-rules-page div.well:nth(0) "
               "label:contains('Os windows') ~ * input[type=checkbox]")
    self.Select("css=grr-configure-rules-page div.well:nth(0) select",
                "Integer")
    rule = foreman_rules.ForemanIntegerClientRule
    label = rule.ForemanIntegerField.CLIENT_CLOCK.description
    self.Select(
        "css=grr-configure-rules-page div.well:nth(0) "
        "label:contains('Field') ~ * select", label)

    # Click on "Next" button
    self.Click("css=grr-new-hunt-wizard-form button.Next")
    self.WaitUntil(self.IsTextPresent, "Review")

    # Click on "Run" button
    self.Click("css=grr-new-hunt-wizard-form button.Next")

    self.WaitUntil(self.IsTextPresent, "Created Hunt")
    # Close the window
    self.Click("css=button.Next")

    # Check that the hunt object was actually created
    hunts_list = sorted(
        data_store.REL_DB.ReadHuntObjects(offset=0, count=10),
        key=lambda x: x.create_time)

    self.assertLen(hunts_list, 1)

    hunt = hunts_list[0]

    # Check that the hunt was created with correct rules
    rules = hunt.client_rule_set.rules
    self.assertLen(rules, 1)
    rule = rules[0]

    self.assertEqual(rule.rule_type,
                     foreman_rules.ForemanClientRule.Type.INTEGER)
    self.assertEqual(rule.integer.field, "CLIENT_CLOCK")

    # Assert that the deselected union field is cleared
    self.assertFalse(rule.os.os_windows)

  def testApprovalIndicatesThatHuntWasCopiedFromAnotherHunt(self):
    self.CreateSampleHunt("model hunt", creator=self.test_username)

    self.Open("/#main=ManageHunts")
    self.Click("css=tr:contains('model hunt')")

    # Open the wizard.
    self.Click("css=button[name=CopyHunt]:not([disabled])")

    # Go to the hunt parameters page.
    self.Click("css=grr-new-hunt-wizard-form button.Next")
    # Go to the output plugins page.
    self.Click("css=grr-new-hunt-wizard-form button.Next")
    # Go to the rules page.
    self.Click("css=grr-new-hunt-wizard-form button.Next")
    # Go to the review page.
    self.Click("css=grr-new-hunt-wizard-form button.Next")

    # Create the hunt.
    self.Click("css=button:contains('Create Hunt')")
    self.Click("css=button:contains('Done')")

    # Request an approval.
    hunts = data_store.REL_DB.ListHuntObjects(offset=0, count=2)
    # Results should be sorted in the create time desc order, so
    # taking the first one should give us the latest hunt.
    h = hunts[0]
    approval_id = self.RequestHuntApproval(
        h.hunt_id,
        requestor=self.test_username,
        reason="reason",
        approver=self.test_username)

    # Open the approval page.
    self.Open("/#/users/%s/approvals/hunt/%s/%s" %
              (self.test_username, h.hunt_id, approval_id))
    self.WaitUntil(self.IsElementPresent,
                   "css=div.panel-body:contains('This hunt was copied from')")


if __name__ == "__main__":
  app.run(test_lib.main)
