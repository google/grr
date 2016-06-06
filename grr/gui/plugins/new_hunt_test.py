#!/usr/bin/env python
"""Test of "New Hunt" wizard."""


from grr.gui import runtests_test

from grr.lib import access_control
from grr.lib import aff4
from grr.lib import data_store
from grr.lib import flags
from grr.lib import flow_runner
from grr.lib import hunts
from grr.lib import output_plugin
from grr.lib import test_lib
from grr.lib.aff4_objects import aff4_grr
from grr.lib.flows.general import file_finder
from grr.lib.flows.general import processes
from grr.lib.flows.general import transfer
from grr.lib.rdfvalues import client as rdf_client
from grr.lib.rdfvalues import paths as rdf_paths
from grr.server import foreman as rdf_foreman


class DummyOutputPlugin(output_plugin.OutputPlugin):
  """An output plugin that sends an email for each response received."""

  name = "dummy"
  description = "Dummy do do."
  args_type = processes.ListProcessesArgs

  def ProcessResponses(self, responses):
    pass


class TestNewHuntWizard(test_lib.GRRSeleniumTest):
  """Test the "new hunt wizard" GUI."""

  @staticmethod
  def FindForemanRules(hunt, token):
    fman = aff4.FACTORY.Open("aff4:/foreman",
                             mode="r",
                             aff4_type=aff4_grr.GRRForeman,
                             token=token)
    hunt_rules = []
    rules = fman.Get(fman.Schema.RULES, [])
    for rule in rules:
      for action in rule.actions:
        if action.hunt_id == hunt.urn:
          hunt_rules.append(rule)
    return hunt_rules

  @staticmethod
  def CreateHuntFixtureWithTwoClients():
    token = access_control.ACLToken(username="test", reason="test")

    # Ensure that clients list is empty
    root = aff4.FACTORY.Open(aff4.ROOT_URN, token=token)
    for client_urn in root.ListChildren():
      if aff4_grr.VFSGRRClient.CLIENT_ID_RE.match(client_urn.Basename()):
        data_store.DB.DeleteSubject(client_urn, token=token)

    # Add 2 distinct clients
    client_id = "C.1%015d" % 0
    fd = aff4.FACTORY.Create(
        rdf_client.ClientURN(client_id),
        aff4_grr.VFSGRRClient,
        token=token)
    fd.Set(fd.Schema.SYSTEM("Windows"))
    fd.Set(fd.Schema.CLOCK(2336650631137737))
    fd.Close()

    client_id = "C.1%015d" % 1
    fd = aff4.FACTORY.Create(
        rdf_client.ClientURN(client_id),
        aff4_grr.VFSGRRClient,
        token=token)
    fd.Set(fd.Schema.SYSTEM("Linux"))
    fd.Set(fd.Schema.CLOCK(2336650631137737))
    fd.Close()

  def setUp(self):
    super(TestNewHuntWizard, self).setUp()

    with self.ACLChecksDisabled():
      # Create a Foreman with an empty rule set.
      with aff4.FACTORY.Create("aff4:/foreman",
                               aff4_grr.GRRForeman,
                               mode="rw",
                               token=self.token) as self.foreman:
        self.foreman.Set(self.foreman.Schema.RULES())
        self.foreman.Close()

  def testNewHuntWizard(self):
    with self.ACLChecksDisabled():
      self.CreateHuntFixtureWithTwoClients()

    # Open up and click on View Hunts.
    self.Open("/")
    self.WaitUntil(self.IsElementPresent, "client_query")
    self.WaitUntil(self.IsElementPresent, "css=a[grrtarget=hunts]")
    self.Click("css=a[grrtarget=hunts]")
    self.WaitUntil(self.IsElementPresent, "css=button[name=NewHunt]")

    # Open up "New Hunt" wizard
    self.Click("css=button[name=NewHunt]")
    self.WaitUntil(self.IsTextPresent, "What to run?")

    # Click on Filesystem item in flows list
    self.WaitUntil(self.IsElementPresent, "css=#_Filesystem > i.jstree-icon")
    self.Click("css=#_Filesystem > i.jstree-icon")

    # Click on the FileFinder item in Filesystem flows list
    self.Click("link=File Finder")

    # Wait for flow configuration form to be rendered (just wait for first
    # input field).
    self.WaitUntil(self.IsElementPresent,
                   "css=grr-new-hunt-wizard-form label:contains('Paths')")

    # Change "path" and "pathtype" values
    self.Type("css=grr-new-hunt-wizard-form "
              "grr-form-proto-repeated-field:has(label:contains('Paths')) "
              "input", "/tmp")
    self.Select("css=grr-new-hunt-wizard-form "
                "grr-form-proto-single-field:has(label:contains('Pathtype')) "
                "select", "TSK")

    # Click on "Next" button
    self.Click("css=grr-new-hunt-wizard-form button.Next")
    self.WaitUntil(self.IsTextPresent, "Output Processing")

    # Click on "Back" button and check that all the values in the form
    # remain intact.
    self.Click("css=grr-new-hunt-wizard-form button.Back")
    self.WaitUntil(self.IsElementPresent,
                   "css=grr-new-hunt-wizard-form label:contains('Paths')")

    self.assertEqual("/tmp", self.GetValue(
        "css=grr-new-hunt-wizard-form "
        "grr-form-proto-repeated-field:has(label:contains('Paths')) input"))

    self.assertEqual("TSK", self.GetSelectedLabel(
        "css=grr-new-hunt-wizard-form "
        "grr-form-proto-single-field:has(label:contains('Pathtype')) select"))

    # Click on "Next" button
    self.Click("css=grr-new-hunt-wizard-form button.Next")
    self.WaitUntil(self.IsTextPresent, "Output Processing")

    # Configure the hunt to use dummy output plugin.
    self.Click("css=grr-new-hunt-wizard-form button[name=Add]")
    self.Select("css=grr-new-hunt-wizard-form select", "DummyOutputPlugin")
    self.Type(
        "css=grr-new-hunt-wizard-form "
        "grr-form-proto-single-field:has(label:contains('Filename Regex')) "
        "input", "some regex")

    # Click on "Next" button
    self.Click("css=grr-new-hunt-wizard-form button.Next")
    self.WaitUntil(self.IsTextPresent, "Where to run?")

    # Empty set of rules should be valid.
    self.WaitUntil(self.IsElementPresent, "css=button.Next:not([disabled])")

    # A note informs what an empty set of rules means.
    self.WaitUntil(self.IsTextPresent, "No rules specified! "
                   "The hunt will run on all clients.")

    # Alternative match mode that matches a client if
    # any of the rules evaluates to true can be selected.
    self.Select("css=grr-configure-rules-page "
                "label:contains('Match mode') ~ * select", "Match any")

    # The note depends on the match mode.
    self.WaitUntil(self.IsTextPresent, "No rules specified! "
                   "The hunt won't run on any client.")

    # Create 3 foreman rules. Note that "Add" button adds rules
    # to the beginning of a list. So we always use :nth(0) selector.
    self.Click("css=grr-configure-rules-page button[name=Add]")

    self.Select("css=grr-configure-rules-page div.well:nth(0) select", "Regex")
    self.Select("css=grr-configure-rules-page div.well:nth(0) "
                "label:contains('Attribute name') ~ * select", "System")
    self.Type("css=grr-configure-rules-page div.well:nth(0) "
              "label:contains('Attribute regex') ~ * input", "Linux")

    self.Click("css=grr-configure-rules-page button[name=Add]")
    self.Select("css=grr-configure-rules-page div.well:nth(0) select",
                "Integer")
    self.Select("css=grr-configure-rules-page div.well:nth(0) "
                "label:contains('Attribute name') ~ * select", "Clock")
    self.Select("css=grr-configure-rules-page div.well:nth(0) "
                "label:contains('Operator') ~ * select", "GREATER_THAN")
    self.Type("css=grr-configure-rules-page div.well:nth(0) "
              "label:contains('Value') ~ * input", "1336650631137737")

    self.Click("css=grr-configure-rules-page button[name=Add]")
    self.Click("css=grr-configure-rules-page div.well:nth(0) "
               "label:contains('Os darwin') ~ * input[type=checkbox]")

    # Click on "Back" button
    self.Click("css=grr-new-hunt-wizard-form button.Back")
    self.WaitUntil(self.IsTextPresent, "Output Processing")

    # Click on "Next" button again and check that all the values that
    # we've just entered remain intact.
    self.Click("css=grr-new-hunt-wizard-form button.Next")
    self.WaitUntil(self.IsTextPresent, "Where to run?")

    # Click on "Next" button
    self.Click("css=grr-new-hunt-wizard-form button.Next")
    self.WaitUntil(self.IsTextPresent, "Review")

    # Check that the arguments summary is present.
    self.WaitUntil(self.IsTextPresent, "Paths")
    self.WaitUntil(self.IsTextPresent, "/tmp")

    # Check that output plugins are shown.
    self.assertTrue(self.IsTextPresent("DummyOutputPlugin"))
    self.assertTrue(self.IsTextPresent("some regex"))

    # Check that there's no deprecated rules summary.
    self.assertFalse(self.IsTextPresent("Regex rules"))
    self.assertFalse(self.IsTextPresent("Integer rules"))

    # Check that rules summary is present.
    self.assertTrue(self.IsTextPresent("Client rule set"))

    # Click on "Run" button
    self.Click("css=grr-new-hunt-wizard-form button.Next")

    self.WaitUntil(self.IsTextPresent, "Created Hunt")

    # Close the window and check that the hunt was created.
    self.Click("css=button.Next")

    # Select newly created hunt.
    self.Click("css=grr-hunts-list td:contains('GenericHunt')")

    # Check that correct details are displayed in hunt details tab.
    self.WaitUntil(self.IsTextPresent, "GenericHunt")
    self.WaitUntil(self.IsTextPresent, "Flow args")

    self.assertTrue(self.IsTextPresent("Paths"))
    self.assertTrue(self.IsTextPresent("/tmp"))

    self.assertTrue(self.IsTextPresent("DummyOutputPlugin"))
    self.assertTrue(self.IsTextPresent("some regex"))

    # Check that there's no deprecated rules summary.
    self.assertFalse(self.IsTextPresent("Regex rules"))
    self.assertFalse(self.IsTextPresent("Integer rules"))

    # Check that rules summary is present.
    self.assertTrue(self.IsTextPresent("Client rule set"))

    # Check that the hunt object was actually created
    hunts_root = aff4.FACTORY.Open("aff4:/hunts", token=self.token)
    hunts_list = list(hunts_root.OpenChildren())
    self.assertEqual(len(hunts_list), 1)

    # Check that the hunt was created with a correct flow
    hunt = hunts_list[0]
    self.assertEqual(hunt.state.args.flow_runner_args.flow_name,
                     file_finder.FileFinder.__name__)
    self.assertEqual(hunt.state.args.flow_args.paths[0], "/tmp")
    self.assertEqual(hunt.state.args.flow_args.pathtype,
                     rdf_paths.PathSpec.PathType.TSK)
    # self.assertEqual(hunt.state.args.flow_args.ignore_errors, True)
    self.assertTrue(hunt.state.args.output_plugins[0].plugin_name,
                    "DummyOutputPlugin")

    # Check that hunt was not started
    self.assertEqual(hunt.Get(hunt.Schema.STATE), "PAUSED")

    # Now try to start the hunt.
    self.Click("css=button[name=RunHunt]")

    # Note that hunt ACL controls are already tested in acl_manager_test.py.

    # Run the hunt.
    with self.ACLChecksDisabled():
      with aff4.FACTORY.Open(hunt.urn, mode="rw", token=self.token) as hunt:
        hunt.Run()

    # Check that the hunt was created with correct rules
    with self.ACLChecksDisabled():
      hunt_rules = self.FindForemanRules(hunt, token=self.token)

    self.assertEqual(len(hunt_rules), 1)
    f = 14 * 24 * 60 * 60
    self.assertLessEqual(
        abs(int(hunt_rules[0].expires - hunt_rules[0].created) - f), 1)

    r = hunt_rules[0].client_rule_set

    self.assertEqual(r.match_mode,
                     rdf_foreman.ForemanClientRuleSet.MatchMode.MATCH_ANY)
    self.assertEqual(len(r.rules), 3)

    self.assertEqual(r.rules[0].rule_type,
                     rdf_foreman.ForemanClientRule.Type.OS)
    self.assertEqual(r.rules[0].os.os_windows, False)
    self.assertEqual(r.rules[0].os.os_linux, False)
    self.assertEqual(r.rules[0].os.os_darwin, True)

    self.assertEqual(r.rules[1].rule_type,
                     rdf_foreman.ForemanClientRule.Type.INTEGER)
    self.assertEqual(r.rules[1].integer.path, "/")
    self.assertEqual(r.rules[1].integer.attribute_name, "Clock")
    self.assertEqual(r.rules[1].integer.operator,
                     rdf_foreman.ForemanIntegerClientRule.Operator.GREATER_THAN)
    self.assertEqual(r.rules[1].integer.value, 1336650631137737)

    self.assertEqual(r.rules[2].rule_type,
                     rdf_foreman.ForemanClientRule.Type.REGEX)
    self.assertEqual(r.rules[2].regex.path, "/")
    self.assertEqual(r.rules[2].regex.attribute_name, "System")
    self.assertEqual(r.rules[2].regex.attribute_regex, "Linux")

  def testLiteralExpressionIsProcessedCorrectly(self):
    """Literals are raw bytes. Testing that raw bytes are processed right."""

    # Open up and click on View Hunts.
    self.Open("/")
    self.Click("css=a[grrtarget=hunts]")

    # Open up "New Hunt" wizard
    self.Click("css=button[name=NewHunt]")
    self.WaitUntil(self.IsTextPresent, "What to run?")

    # Click on Filesystem item in flows list
    self.WaitUntil(self.IsElementPresent, "css=#_Filesystem > i.jstree-icon")
    self.Click("css=#_Filesystem > i.jstree-icon")

    # Click on the FileFinder item in Filesystem flows list
    self.Click("link=File Finder")

    self.Click("css=label:contains('Conditions') ~ * button")
    self.Select("css=label:contains('Condition type') ~ * select",
                "Contents literal match")
    self.Type("css=label:contains('Literal') ~ * input", "foo\\x0d\\xc8bar")

    # Click on "Next" button
    self.Click("css=grr-new-hunt-wizard-form button.Next")
    self.WaitUntil(self.IsTextPresent, "Output Processing")
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

    # Check that the hunt object was actually created
    hunts_root = aff4.FACTORY.Open("aff4:/hunts", token=self.token)
    hunts_list = list(hunts_root.OpenChildren())
    self.assertEqual(len(hunts_list), 1)

    # Check that the hunt was created with a correct literal value.
    hunt = hunts_list[0]
    self.assertEqual(hunt.state.args.flow_runner_args.flow_name,
                     file_finder.FileFinder.__name__)
    self.assertEqual(
        hunt.state.args.flow_args.conditions[0].contents_literal_match.literal,
        "foo\x0d\xc8bar")

  def testOutputPluginsListEmptyWhenNoDefaultOutputPluginSet(self):
    self.Open("/#main=ManageHunts")
    self.Click("css=button[name=NewHunt]")

    # Select "List Processes" flow.
    self.Click("css=#_Processes > i.jstree-icon")
    self.Click("link=ListProcesses")

    # There should be no dummy output plugin visible.
    self.Click("css=grr-new-hunt-wizard-form button.Next")
    self.WaitUntil(self.IsTextPresent, "Output Processing")
    self.WaitUntilNot(self.IsTextPresent, "Dummy do do")

  def testDefaultOutputPluginIsCorrectlyAddedToThePluginsList(self):
    with test_lib.ConfigOverrider({
        "AdminUI.new_hunt_wizard.default_output_plugin": "DummyOutputPlugin"
    }):
      self.Open("/#main=ManageHunts")
      self.Click("css=button[name=NewHunt]")

      # Select "List Processes" flow.
      self.Click("css=#_Processes > i.jstree-icon")
      self.Click("link=ListProcesses")

      # Dummy output plugin should be added by default.
      self.Click("css=grr-new-hunt-wizard-form button.Next")
      self.WaitUntil(self.IsTextPresent, "Output Processing")
      self.WaitUntil(self.IsTextPresent, "DummyOutputPlugin")

  def testLabelsHuntRuleDisplaysAvailableLabels(self):
    with self.ACLChecksDisabled():
      with aff4.FACTORY.Open("C.0000000000000001",
                             aff4_type=aff4_grr.VFSGRRClient,
                             mode="rw",
                             token=self.token) as client:
        client.AddLabels("foo", owner="owner1")
        client.AddLabels("bar", owner="owner2")

    self.Open("/#main=ManageHunts")
    self.Click("css=button[name=NewHunt]")

    # Select "List Processes" flow.
    self.Click("css=#_Processes > i.jstree-icon")
    self.Click("link=ListProcesses")

    # Click 'Next' to go to output plugins page.
    self.Click("css=grr-new-hunt-wizard-form button.Next")

    # Click 'Next' to go to hunt rules page.
    self.Click("css=grr-new-hunt-wizard-form button.Next")

    self.Click("css=grr-new-hunt-wizard-form button[name=Add]")

    # Select 'Clients With Label' rule.
    self.Select("css=grr-new-hunt-wizard-form div.well select", "Label")
    # Check that there's an option present for labels 'bar' (this option
    # should be selected) and for label 'foo'.
    self.WaitUntil(self.IsElementPresent,
                   "css=grr-new-hunt-wizard-form div.well "
                   ".form-group:has(label:contains('Label')) "
                   "select option:selected[label=bar]")
    self.WaitUntil(self.IsElementPresent,
                   "css=grr-new-hunt-wizard-form div.well "
                   ".form-group:has(label:contains('Label')) "
                   "select option:not(:selected)[label=foo]")

  def testLabelsHuntRuleMatchesCorrectClients(self):
    with self.ACLChecksDisabled():
      client_ids = self.SetupClients(10)

    with self.ACLChecksDisabled():
      with aff4.FACTORY.Open(client_ids[1],
                             mode="rw",
                             token=self.token) as client:
        client.AddLabels("foo", owner="owner1")
        client.AddLabels("bar", owner="owner2")

      with aff4.FACTORY.Open(client_ids[7],
                             mode="rw",
                             token=self.token) as client:
        client.AddLabels("bar", owner="GRR")

    self.Open("/#main=ManageHunts")
    self.Click("css=button[name=NewHunt]")

    # Select "List Processes" flow.
    self.Click("css=#_Processes > i.jstree-icon")
    self.Click("link=ListProcesses")

    # Click 'Next' to go to the output plugins page and then to hunt rules
    # page.
    self.Click("css=grr-new-hunt-wizard-form button.Next")
    self.Click("css=grr-new-hunt-wizard-form button.Next")

    # Select 'Clients With Label' rule.
    self.Click("css=grr-configure-rules-page button[name=Add]")
    self.Select("css=grr-new-hunt-wizard-form div.well select", "Label")
    self.Select("css=grr-new-hunt-wizard-form div.well .form-group "
                ".form-group:has(label:contains('Label')):nth-last-of-type(1) "
                "select", "foo")
    self.Click("css=grr-new-hunt-wizard-form div.well .form-group "
               ".form-group:has(label:contains('Add label')) button")
    self.Select("css=grr-new-hunt-wizard-form div.well .form-group "
                ".form-group:has(label:contains('Label')):nth-last-of-type(1) "
                "select", "bar")
    self.Select("css=grr-new-hunt-wizard-form div.well .form-group "
                ".form-group:has(label:contains('Match mode')) select",
                "Match any")

    # Click 'Next' to go to hunt overview page.  Then click 'Next' to go to
    # submit the hunt and wait until it's created.
    self.Click("css=grr-new-hunt-wizard-form button.Next")
    self.Click("css=grr-new-hunt-wizard-form button.Next")
    self.WaitUntil(self.IsTextPresent, "Created Hunt")

    with self.ACLChecksDisabled():
      hunts_root = aff4.FACTORY.Open("aff4:/hunts", token=self.token)
      hunts_list = list(hunts_root.OpenChildren(mode="rw"))
      hunt = hunts_list[0]

      hunt.Run()  # Run the hunt so that rules are added to the foreman.

      foreman = aff4.FACTORY.Open("aff4:/foreman", mode="rw", token=self.token)
      for client_id in client_ids:
        tasks_assigned = foreman.AssignTasksToClient(client_id)
        if client_id in [client_ids[1], client_ids[7]]:
          self.assertTrue(tasks_assigned)
        else:
          self.assertFalse(tasks_assigned)

  @staticmethod
  def CreateSampleHunt(description, token=None):
    hunts.GRRHunt.StartHunt(
        hunt_name="GenericHunt",
        description=description,
        flow_runner_args=flow_runner.FlowRunnerArgs(flow_name="GetFile"),
        flow_args=transfer.GetFileArgs(pathspec=rdf_paths.PathSpec(
            path="/tmp/evil.txt",
            pathtype=rdf_paths.PathSpec.PathType.TSK,)),
        client_rule_set=rdf_foreman.ForemanClientRuleSet(rules=[
            rdf_foreman.ForemanClientRule(
                rule_type=rdf_foreman.ForemanClientRule.Type.REGEX,
                regex=rdf_foreman.ForemanRegexClientRule(
                    attribute_name="GRR client",
                    attribute_regex="GRR"))
        ]),
        output_plugins=[
            output_plugin.OutputPluginDescriptor(
                plugin_name="DummyOutputPlugin",
                plugin_args=DummyOutputPlugin.args_type(filename_regex="blah!",
                                                        fetch_binaries=True))
        ],
        client_rate=60,
        token=token)

  def testCopyHuntPrefillsNewHuntWizard(self):
    with self.ACLChecksDisabled():
      self.CreateSampleHunt("model hunt", token=self.token)

    self.Open("/#main=ManageHunts")
    self.Click("css=tr:contains('model hunt')")
    self.Click("css=button[name=CopyHunt]:not([disabled])")

    # Wait until dialog appears.
    self.WaitUntil(self.IsTextPresent, "What to run?")

    # Check that non-default values of sample hunt are prefilled.
    self.WaitUntilEqual("/tmp/evil.txt", self.GetValue,
                        "css=grr-new-hunt-wizard-form "
                        "label:contains('Path') ~ * input:text")

    self.WaitUntilEqual("TSK", self.GetText, "css=grr-new-hunt-wizard-form "
                        "label:contains('Pathtype') ~ * select option:selected")

    self.WaitUntilEqual("model hunt (copy)", self.GetValue,
                        "css=grr-new-hunt-wizard-form "
                        "label:contains('Description') ~ * input:text")

    self.WaitUntilEqual("60", self.GetValue, "css=grr-new-hunt-wizard-form "
                        "label:contains('Client rate') ~ * input")

    # Click on "Next" button.
    self.Click("css=grr-new-hunt-wizard-form button.Next")
    self.WaitUntil(self.IsTextPresent, "Output Processing")

    # Check that output plugins list is prefilled.
    self.WaitUntilEqual("DummyOutputPlugin", self.GetText,
                        "css=grr-new-hunt-wizard-form "
                        "label:contains('Plugin') ~ * select option:selected")

    self.WaitUntilEqual("blah!", self.GetValue, "css=grr-new-hunt-wizard-form "
                        "label:contains('Filename Regex') ~ * input:text")

    self.WaitUntil(self.IsElementPresent, "css=grr-new-hunt-wizard-form "
                   "label:contains('Fetch Binaries') ~ * input:checked")

    # Click on "Next" button.
    self.Click("css=grr-new-hunt-wizard-form button.Next")
    self.WaitUntil(self.IsTextPresent, "Where to run?")

    # Check that rules list is prefilled.
    self.WaitUntilEqual("Regex", self.GetText, "css=grr-new-hunt-wizard-form "
                        "label:contains('Rule type') "
                        "~ * select option:selected")

    self.WaitUntilEqual("GRR client", self.GetText,
                        "css=grr-new-hunt-wizard-form "
                        "label:contains('Attribute name') "
                        "~ * select option:selected")

    self.WaitUntilEqual("GRR", self.GetValue, "css=grr-new-hunt-wizard-form "
                        "label:contains('Attribute regex') ~ * input:text")

    # Click on "Next" button.
    self.Click("css=grr-new-hunt-wizard-form button.Next")
    self.WaitUntil(self.IsTextPresent, "Review")

    # Check that review page contains expected values.
    self.WaitUntil(self.IsTextPresent, "TSK")
    self.WaitUntil(self.IsTextPresent, "/tmp/evil.txt")
    self.WaitUntil(self.IsTextPresent, "GetFile")
    self.WaitUntil(self.IsTextPresent, "DummyOutputPlugin")
    self.WaitUntil(self.IsTextPresent, "blah!")
    self.WaitUntil(self.IsTextPresent, "model hunt (copy)")
    self.WaitUntil(self.IsTextPresent, "GRR client")
    self.WaitUntil(self.IsTextPresent, "60")

  def testCopyHuntCreatesExactCopyWithChangedDescription(self):
    with self.ACLChecksDisabled():
      self.CreateSampleHunt("model hunt", token=self.token)

    self.Open("/#main=ManageHunts")
    self.Click("css=tr:contains('model hunt')")
    self.Click("css=button[name=CopyHunt]:not([disabled])")

    # Wait until dialog appears and then click through.
    self.WaitUntil(self.IsTextPresent, "What to run?")

    # Click on "Next" button.
    self.Click("css=grr-new-hunt-wizard-form button.Next")
    self.WaitUntil(self.IsTextPresent, "Output Processing")

    # Click on "Next" button.
    self.Click("css=grr-new-hunt-wizard-form button.Next")
    self.WaitUntil(self.IsTextPresent, "Where to run?")

    # Click on "Next" button.
    self.Click("css=grr-new-hunt-wizard-form button.Next")
    self.WaitUntil(self.IsTextPresent, "Review")

    # Click on "Run" button.
    self.Click("css=grr-new-hunt-wizard-form button.Next")
    self.WaitUntil(self.IsTextPresent, "Created Hunt")

    with self.ACLChecksDisabled():
      hunts_root = aff4.FACTORY.Open("aff4:/hunts", token=self.token)
      hunts_list = sorted(list(hunts_root.ListChildren()), key=lambda x: x.age)

      self.assertEqual(len(hunts_list), 2)

      first_hunt = aff4.FACTORY.Open(hunts_list[0], token=self.token)
      last_hunt = aff4.FACTORY.Open(hunts_list[1], token=self.token)

      # Check that generic hunt arguments are equal.
      self.assertEqual(first_hunt.args, last_hunt.args)

      # Check that hunts runner arguments are equal except for the description.
      # Hunt copy has ' (copy)' added to the description.
      first_runner_args = first_hunt.state.context.args
      last_runner_args = last_hunt.state.context.args

      self.assertEqual(first_runner_args.description + " (copy)",
                       last_runner_args.description)
      self.assertEqual(first_runner_args.client_rate,
                       last_runner_args.client_rate)
      self.assertEqual(first_runner_args.hunt_name, last_runner_args.hunt_name)
      self.assertEqual(first_runner_args.client_rule_set,
                       last_runner_args.client_rule_set)

  def testCopyHuntRespectsUserChanges(self):
    with self.ACLChecksDisabled():
      self.CreateSampleHunt("model hunt", token=self.token)

    self.Open("/#main=ManageHunts")
    self.Click("css=tr:contains('model hunt')")
    self.Click("css=button[name=CopyHunt]:not([disabled])")

    # Wait until dialog appears and then click through.
    self.WaitUntil(self.IsTextPresent, "What to run?")

    # Change values in the flow configuration.
    self.Type("css=grr-new-hunt-wizard-form label:contains('Path') "
              "~ * input:text", "/tmp/very-evil.txt")

    self.Select("css=grr-new-hunt-wizard-form label:contains('Pathtype') "
                "~ * select", "OS")

    self.Type("css=grr-new-hunt-wizard-form label:contains('Description') "
              "~ * input:text", "my personal copy")

    self.Type("css=grr-new-hunt-wizard-form label:contains('Client rate') "
              "~ * input", "42")

    # Click on "Next" button.
    self.Click("css=grr-new-hunt-wizard-form button.Next")
    self.WaitUntil(self.IsTextPresent, "Output Processing")

    # Change output plugin and add another one.
    self.Click("css=grr-new-hunt-wizard-form button[name=Add]")
    self.Select("css=grr-configure-output-plugins-page select:eq(0)",
                "DummyOutputPlugin")
    self.Type("css=grr-configure-output-plugins-page "
              "label:contains('Filename Regex'):eq(0) ~ * input:text",
              "foobar!")

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
    self.WaitUntil(self.IsTextPresent, "GetFile")
    self.WaitUntil(self.IsTextPresent, "DummyOutputPlugin")
    self.WaitUntil(self.IsTextPresent, "foobar!")
    self.WaitUntil(self.IsTextPresent, "blah!")
    self.WaitUntil(self.IsTextPresent, "my personal copy")
    self.WaitUntil(self.IsTextPresent, "Os darwin")
    self.WaitUntil(self.IsTextPresent, "42")

    # Click on "Run" button.
    self.Click("css=grr-new-hunt-wizard-form button.Next")
    self.WaitUntil(self.IsTextPresent, "Created Hunt")

    with self.ACLChecksDisabled():
      hunts_root = aff4.FACTORY.Open("aff4:/hunts", token=self.token)
      hunts_list = sorted(list(hunts_root.ListChildren()), key=lambda x: x.age)

      self.assertEqual(len(hunts_list), 2)
      last_hunt = aff4.FACTORY.Open(hunts_list[-1], token=self.token)

      self.assertEqual(last_hunt.args.flow_args.pathspec.path,
                       "/tmp/very-evil.txt")
      self.assertEqual(last_hunt.args.flow_args.pathspec.pathtype, "OS")
      self.assertEqual(last_hunt.args.flow_runner_args.flow_name, "GetFile")

      self.assertEqual(len(last_hunt.args.output_plugins), 2)
      self.assertEqual(last_hunt.args.output_plugins[0].plugin_name,
                       "DummyOutputPlugin")
      self.assertEqual(
          last_hunt.args.output_plugins[0].plugin_args.filename_regex,
          "foobar!")
      self.assertEqual(
          last_hunt.args.output_plugins[0].plugin_args.fetch_binaries, False)
      self.assertEqual(last_hunt.args.output_plugins[1].plugin_name,
                       "DummyOutputPlugin")
      self.assertEqual(
          last_hunt.args.output_plugins[1].plugin_args.filename_regex, "blah!")
      self.assertEqual(
          last_hunt.args.output_plugins[1].plugin_args.fetch_binaries, True)

      runner_args = last_hunt.state.context.args
      self.assertAlmostEqual(runner_args.client_rate, 42)
      self.assertEqual(runner_args.description, "my personal copy")
      self.assertEqual(runner_args.client_rule_set,
                       rdf_foreman.ForemanClientRuleSet(rules=[
                           rdf_foreman.ForemanClientRule(
                               os=rdf_foreman.ForemanOsClientRule(
                                   os_darwin=True))
                       ]))

  def testCopyHuntHandlesLiteralExpressionCorrectly(self):
    """Literals are raw bytes. Testing that raw bytes are processed right."""
    literal_match = file_finder.FileFinderContentsLiteralMatchCondition(
        literal="foo\x0d\xc8bar")

    with self.ACLChecksDisabled():
      hunts.GRRHunt.StartHunt(
          hunt_name="GenericHunt",
          description="model hunt",
          flow_runner_args=flow_runner.FlowRunnerArgs(
              flow_name=file_finder.FileFinder.__name__),
          flow_args=file_finder.FileFinderArgs(conditions=[
              file_finder.FileFinderCondition(
                  condition_type="CONTENTS_LITERAL_MATCH",
                  contents_literal_match=literal_match)
          ],
                                               paths=["/tmp/evil.txt"]),
          token=self.token)

    self.Open("/#main=ManageHunts")
    self.Click("css=tr:contains('model hunt')")
    self.Click("css=button[name=CopyHunt]:not([disabled])")

    # Wait until dialog appears.
    self.WaitUntil(self.IsTextPresent, "What to run?")

    # Check that non-default values of sample hunt are prefilled.
    self.WaitUntilEqual("foo\\x0d\\xc8bar", self.GetValue,
                        "css=grr-new-hunt-wizard-form "
                        "label:contains('Literal') ~ * input:text")

    # Click on "Next" button.
    self.Click("css=grr-new-hunt-wizard-form button.Next")
    self.WaitUntil(self.IsTextPresent, "Output Processing")
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

    hunts_root = aff4.FACTORY.Open("aff4:/hunts", token=self.token)
    hunts_list = sorted(list(hunts_root.ListChildren()), key=lambda x: x.age)

    self.assertEqual(len(hunts_list), 2)
    last_hunt = aff4.FACTORY.Open(hunts_list[-1], token=self.token)

    # Check that the hunt was created with a correct literal value.
    self.assertEqual(last_hunt.state.args.flow_runner_args.flow_name,
                     file_finder.FileFinder.__name__)
    self.assertEqual(last_hunt.state.args.flow_args.conditions[0]
                     .contents_literal_match.literal, "foo\x0d\xc8bar")

  def testCopyHuntPreservesRuleType(self):
    with self.ACLChecksDisabled():
      hunts.GRRHunt.StartHunt(
          hunt_name="GenericHunt",
          description="model hunt",
          flow_runner_args=flow_runner.FlowRunnerArgs(flow_name="GetFile"),
          flow_args=transfer.GetFileArgs(pathspec=rdf_paths.PathSpec(
              path="/tmp/evil.txt",
              pathtype=rdf_paths.PathSpec.PathType.TSK,)),
          client_rule_set=rdf_foreman.ForemanClientRuleSet(rules=[
              rdf_foreman.ForemanClientRule(
                  rule_type=rdf_foreman.ForemanClientRule.Type.OS,
                  os=rdf_foreman.ForemanOsClientRule(os_darwin=True))
          ]),
          token=self.token)

    self.Open("/#main=ManageHunts")
    self.Click("css=tr:contains('model hunt')")
    self.Click("css=button[name=CopyHunt]:not([disabled])")

    # Wait until dialog appears.
    self.WaitUntil(self.IsTextPresent, "What to run?")
    # Click on "Next" button.
    self.Click("css=grr-new-hunt-wizard-form button.Next")
    self.WaitUntil(self.IsTextPresent, "Output Processing")
    # Click on "Next" button
    self.Click("css=grr-new-hunt-wizard-form button.Next")
    self.WaitUntil(self.IsTextPresent, "Where to run?")
    self.WaitUntil(self.IsElementPresent, "css=grr-new-hunt-wizard-form "
                   "label:contains('Os darwin') ~ * input:checked")


def main(argv):
  # Run the full test suite
  runtests_test.SeleniumTestProgram(argv=argv)


if __name__ == "__main__":
  flags.StartMain(main)
