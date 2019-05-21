#!/usr/bin/env python
"""Test of "New Hunt" wizard."""
from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals


from absl import app
from selenium.webdriver.common import keys

from grr_response_core.lib import rdfvalue
from grr_response_core.lib.rdfvalues import paths as rdf_paths
from grr_response_server import aff4
from grr_response_server import data_store
from grr_response_server import foreman
from grr_response_server import foreman_rules
from grr_response_server import hunt as lib_hunt
from grr_response_server.aff4_objects import aff4_grr
from grr_response_server.flows.general import file_finder
from grr_response_server.flows.general import transfer
from grr_response_server.gui import gui_test_lib
from grr_response_server.rdfvalues import flow_runner as rdf_flow_runner
from grr_response_server.rdfvalues import output_plugin as rdf_output_plugin
from grr.test_lib import db_test_lib
from grr.test_lib import test_lib


@db_test_lib.DualDBTest
class TestNewHuntWizard(gui_test_lib.GRRSeleniumHuntTest):
  """Test the "new hunt wizard" GUI."""

  @staticmethod
  def FindForemanRules(hunt_urn, token):
    if data_store.RelationalDBEnabled():
      rules = data_store.REL_DB.ReadAllForemanRules()
      return [rule for rule in rules if rule.hunt_id == hunt_urn.Basename()]
    else:
      fman = aff4.FACTORY.Open(
          "aff4:/foreman", mode="r", aff4_type=aff4_grr.GRRForeman, token=token)
      rules = fman.Get(fman.Schema.RULES, [])
      return [rule for rule in rules if rule.hunt_id == hunt_urn]

  def setUp(self):
    super(TestNewHuntWizard, self).setUp()

    if not data_store.RelationalDBEnabled():
      # Create a Foreman with an empty rule set.
      with aff4.FACTORY.Create(
          "aff4:/foreman", aff4_grr.GRRForeman, mode="rw",
          token=self.token) as self.foreman:
        self.foreman.Set(self.foreman.Schema.RULES())
        self.foreman.Close()

  def testNewHuntWizard(self):
    # Open up and click on View Hunts.
    self.Open("/")
    self.WaitUntil(self.IsElementPresent, "client_query")
    self.WaitUntil(self.IsElementPresent, "css=a[grrtarget=hunts]")
    self.Click("css=a[grrtarget=hunts]")
    self.WaitUntil(self.IsElementPresent, "css=button[name=NewHunt]")

    # Open up "New Hunt" wizard
    self.Click("css=button[name=NewHunt]")
    self.WaitUntil(self.IsElementPresent,
                   "css=grr-wizard-form:contains('What to run?')")

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
    self.Type(
        "css=grr-new-hunt-wizard-form "
        "grr-form-proto-repeated-field:has(label:contains('Paths')) "
        "input", "/tmp")
    self.Select(
        "css=grr-new-hunt-wizard-form "
        "grr-form-proto-single-field:has(label:contains('Pathtype')) "
        "select", "TSK")

    # Click on "Next" button
    self.Click("css=grr-new-hunt-wizard-form button.Next")
    self.WaitUntil(self.IsElementPresent,
                   "css=grr-wizard-form:contains('Hunt parameters')")

    # Click on "Next" button
    self.Click("css=grr-new-hunt-wizard-form button.Next")
    self.WaitUntil(self.IsElementPresent,
                   "css=grr-wizard-form:contains('How to process results')")

    # Click on "Back" button and check that all the values in the form
    # remain intact.
    self.Click("css=grr-new-hunt-wizard-form button.Back")
    self.WaitUntil(self.IsElementPresent,
                   "css=grr-wizard-form:contains('Hunt parameters')")

    self.Click("css=grr-new-hunt-wizard-form button.Back")
    self.WaitUntil(self.IsElementPresent,
                   "css=grr-new-hunt-wizard-form label:contains('Paths')")

    self.assertEqual(
        "/tmp",
        self.GetValue(
            "css=grr-new-hunt-wizard-form "
            "grr-form-proto-repeated-field:has(label:contains('Paths')) input"))

    self.assertEqual(
        "TSK",
        self.GetSelectedLabel(
            "css=grr-new-hunt-wizard-form "
            "grr-form-proto-single-field:has(label:contains('Pathtype')) select"
        ))

    # Click on "Next" button
    self.Click("css=grr-new-hunt-wizard-form button.Next")
    self.WaitUntil(self.IsElementPresent,
                   "css=grr-wizard-form:contains('Hunt parameters')")

    # Click on "Next" button
    self.Click("css=grr-new-hunt-wizard-form button.Next")
    self.WaitUntil(self.IsElementPresent,
                   "css=grr-wizard-form:contains('How to process results')")

    # Configure the hunt to use dummy output plugin.
    self.Click("css=grr-new-hunt-wizard-form button[name=Add]")
    self.Select("css=grr-new-hunt-wizard-form select", "DummyOutputPlugin")
    self.Type(
        "css=grr-new-hunt-wizard-form "
        "grr-form-proto-single-field:has(label:contains('Filepath Regex')) "
        "input", "some regex")

    # Click on "Next" button
    self.Click("css=grr-new-hunt-wizard-form button.Next")
    self.WaitUntil(self.IsElementPresent,
                   "css=grr-wizard-form:contains('Where to run?')")

    # Empty set of rules should be valid.
    self.WaitUntil(self.IsElementPresent, "css=button.Next:not([disabled])")

    # A note informs what an empty set of rules means.
    self.WaitUntil(self.IsElementPresent,
                   "css=grr-wizard-form:contains('No rules specified!')")

    # Alternative match mode that matches a client if
    # any of the rules evaluates to true can be selected.
    self.Select(
        "css=grr-configure-rules-page "
        "label:contains('Match mode') ~ * select", "Match any")

    # The note depends on the match mode.
    self.WaitUntil(self.IsElementPresent,
                   "css=grr-wizard-form:contains('No rules specified!')")

    # Create 3 foreman rules. Note that "Add" button adds rules
    # to the beginning of a list. So we always use :nth(0) selector.
    self.Click("css=grr-configure-rules-page button[name=Add]")
    self.Select("css=grr-configure-rules-page div.well:nth(0) select", "Regex")
    rule = foreman_rules.ForemanRegexClientRule
    label = rule.ForemanStringField.SYSTEM.description
    self.Select(
        "css=grr-configure-rules-page div.well:nth(0) "
        "label:contains('Field') ~ * select", label)
    self.Type(
        "css=grr-configure-rules-page div.well:nth(0) "
        "label:contains('Attribute regex') ~ * input", "Linux")

    self.Click("css=grr-configure-rules-page button[name=Add]")
    self.Select("css=grr-configure-rules-page div.well:nth(0) select",
                "Integer")

    rule = foreman_rules.ForemanIntegerClientRule
    label = rule.ForemanIntegerField.CLIENT_CLOCK.description
    self.Select(
        "css=grr-configure-rules-page div.well:nth(0) "
        "label:contains('Field') ~ * select", label)
    self.Select(
        "css=grr-configure-rules-page div.well:nth(0) "
        "label:contains('Operator') ~ * select", "GREATER_THAN")
    self.Type(
        "css=grr-configure-rules-page div.well:nth(0) "
        "label:contains('Value') ~ * input", "1336650631137737")

    self.Click("css=grr-configure-rules-page button[name=Add]")
    self.Click("css=grr-configure-rules-page div.well:nth(0) "
               "label:contains('Os darwin') ~ * input[type=checkbox]")

    # Click on "Back" button
    self.Click("css=grr-new-hunt-wizard-form button.Back")
    self.WaitUntil(self.IsElementPresent,
                   "css=grr-wizard-form:contains('How to process results')")

    # Click on "Next" button again and check that all the values that
    # we've just entered remain intact.
    self.Click("css=grr-new-hunt-wizard-form button.Next")
    self.WaitUntil(self.IsElementPresent,
                   "css=grr-wizard-form:contains('Where to run?')")

    # Click on "Next" button
    self.Click("css=grr-new-hunt-wizard-form button.Next")
    self.WaitUntil(self.IsElementPresent,
                   "css=grr-wizard-form:contains('Review')")

    # Check that the arguments summary is present.
    self.WaitUntil(self.IsElementPresent,
                   "css=grr-wizard-form:contains('Paths')")
    self.WaitUntil(self.IsElementPresent,
                   "css=grr-wizard-form:contains('/tmp')")

    # Check that output plugins are shown.
    self.assertTrue(
        self.IsElementPresent(
            "css=grr-wizard-form:contains('DummyOutputPlugin')"))
    self.assertTrue(
        self.IsElementPresent("css=grr-wizard-form:contains('some regex')"))

    # Check that there's no deprecated rules summary.
    self.assertFalse(
        self.IsElementPresent("css=grr-wizard-form:contains('Regex rules')"))
    self.assertFalse(
        self.IsElementPresent("css=grr-wizard-form:contains('Integer rules')"))

    # Check that rules summary is present.
    self.assertTrue(
        self.IsElementPresent(
            "css=grr-wizard-form:contains('Client rule set')"))

    # Click on "Run" button
    self.Click("css=grr-new-hunt-wizard-form button.Next")

    self.WaitUntil(self.IsElementPresent,
                   "css=grr-wizard-form:contains('Created Hunt')")

    # Close the window and check that the hunt was created.
    self.Click("css=button.Next")

    # Select newly created hunt.
    self.Click("css=grr-hunts-list td:contains('gui_user')")

    # Check that correct details are displayed in hunt details tab.
    self.WaitUntil(self.IsElementPresent,
                   "css=grr-hunt-inspector:contains('GenericHunt')")
    self.WaitUntil(self.IsElementPresent,
                   "css=grr-hunt-inspector:contains('Flow Arguments')")

    self.assertTrue(
        self.IsElementPresent("css=grr-hunt-inspector:contains('Paths')"))
    self.assertTrue(
        self.IsElementPresent("css=grr-hunt-inspector:contains('/tmp')"))

    self.assertTrue(
        self.IsElementPresent(
            "css=grr-hunt-inspector:contains('DummyOutputPlugin')"))
    self.assertTrue(
        self.IsElementPresent("css=grr-hunt-inspector:contains('some regex')"))

    # Check that there's no deprecated rules summary.
    self.assertFalse(
        self.IsElementPresent("css=grr-hunt-inspector:contains('Regex rules')"))
    self.assertFalse(
        self.IsElementPresent(
            "css=grr-hunt-inspector:contains('Integer rules')"))

    # Check that rules summary is present.
    self.assertTrue(
        self.IsElementPresent(
            "css=grr-hunt-inspector:contains('Client Rule Set')"))

    # Check that the hunt object was actually created
    if data_store.RelationalDBEnabled():
      hunts_list = sorted(
          data_store.REL_DB.ReadHuntObjects(offset=0, count=10),
          key=lambda x: x.create_time)
      self.assertLen(hunts_list, 1)

      # Check that the hunt was created with a correct flow
      hunt = hunts_list[0]

      self.assertEqual(hunt.args.standard.flow_name,
                       file_finder.FileFinder.__name__)
      self.assertEqual(hunt.args.standard.flow_args.paths[0], "/tmp")
      self.assertEqual(hunt.args.standard.flow_args.pathtype,
                       rdf_paths.PathSpec.PathType.TSK)
      # self.assertEqual(hunt.args.flow_args.ignore_errors, True)
      self.assertTrue(hunt.output_plugins[0].plugin_name, "DummyOutputPlugin")

      # Check that hunt was not started
      self.assertEqual(hunt.hunt_state, hunt.HuntState.PAUSED)

      lib_hunt.StartHunt(hunt.hunt_id)

      hunt_rules = self.FindForemanRules(
          rdfvalue.RDFURN("hunts").Add(hunt.hunt_id), token=self.token)
    else:
      hunts_root = aff4.FACTORY.Open("aff4:/hunts", token=self.token)
      hunts_list = list(hunts_root.OpenChildren())
      self.assertLen(hunts_list, 1)

      # Check that the hunt was created with a correct flow
      hunt = hunts_list[0]
      self.assertEqual(hunt.args.flow_runner_args.flow_name,
                       file_finder.FileFinder.__name__)
      self.assertEqual(hunt.args.flow_args.paths[0], "/tmp")
      self.assertEqual(hunt.args.flow_args.pathtype,
                       rdf_paths.PathSpec.PathType.TSK)
      # self.assertEqual(hunt.args.flow_args.ignore_errors, True)
      self.assertTrue(hunt.runner_args.output_plugins[0].plugin_name,
                      "DummyOutputPlugin")

      # Check that hunt was not started
      self.assertEqual(hunt.Get(hunt.Schema.STATE), "PAUSED")

      with aff4.FACTORY.Open(hunt.urn, mode="rw", token=self.token) as hunt:
        hunt.Run()

      hunt_rules = self.FindForemanRules(hunt.urn, token=self.token)

    # Check that the hunt was created with correct rules
    self.assertLen(hunt_rules, 1)
    lifetime = hunt_rules[0].GetLifetime()
    lifetime -= rdfvalue.Duration("2w")
    self.assertLessEqual(lifetime, rdfvalue.Duration("1s"))

    r = hunt_rules[0].client_rule_set

    self.assertEqual(r.match_mode,
                     foreman_rules.ForemanClientRuleSet.MatchMode.MATCH_ANY)
    self.assertLen(r.rules, 3)

    self.assertEqual(r.rules[0].rule_type,
                     foreman_rules.ForemanClientRule.Type.OS)
    self.assertEqual(r.rules[0].os.os_windows, False)
    self.assertEqual(r.rules[0].os.os_linux, False)
    self.assertEqual(r.rules[0].os.os_darwin, True)

    self.assertEqual(r.rules[1].rule_type,
                     foreman_rules.ForemanClientRule.Type.INTEGER)
    self.assertEqual(r.rules[1].integer.field, "CLIENT_CLOCK")
    self.assertEqual(
        r.rules[1].integer.operator,
        foreman_rules.ForemanIntegerClientRule.Operator.GREATER_THAN)
    self.assertEqual(r.rules[1].integer.value, 1336650631137737)

    self.assertEqual(r.rules[2].rule_type,
                     foreman_rules.ForemanClientRule.Type.REGEX)
    self.assertEqual(r.rules[2].regex.field, "SYSTEM")
    self.assertEqual(r.rules[2].regex.attribute_regex, "Linux")

  def testWizardStepCounterIsShownCorrectly(self):
    # Open up and click on View Hunts.
    self.Open("/#/hunts")

    # Open up "New Hunt" wizard
    self.Click("css=button[name=NewHunt]")
    self.WaitUntil(self.IsElementPresent,
                   "css=grr-wizard-form:contains('What to run?')")

    # Click on the FileFinder item in Filesystem flows list
    self.WaitUntil(self.IsElementPresent, "css=#_Filesystem > i.jstree-icon")
    self.Click("css=#_Filesystem > i.jstree-icon")
    self.Click("link=File Finder")

    self.WaitUntil(self.IsElementPresent,
                   "css=grr-wizard-form:contains('Step 1 out of 6')")

    # Click on "Next" button
    self.Click("css=grr-new-hunt-wizard-form button.Next")

    self.WaitUntil(self.IsElementPresent,
                   "css=grr-wizard-form:contains('Step 2 out of 6')")

  def testLiteralExpressionIsProcessedCorrectly(self):
    """Literals are raw bytes. Testing that raw bytes are processed right."""

    # Open up and click on View Hunts.
    self.Open("/")
    self.Click("css=a[grrtarget=hunts]")

    # Open up "New Hunt" wizard
    self.Click("css=button[name=NewHunt]")
    self.WaitUntil(self.IsElementPresent,
                   "css=grr-wizard-form:contains('What to run?')")

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
    self.WaitUntil(self.IsElementPresent,
                   "css=grr-wizard-form:contains('Hunt parameters')")
    # Click on "Next" button
    self.Click("css=grr-new-hunt-wizard-form button.Next")
    self.WaitUntil(self.IsElementPresent,
                   "css=grr-wizard-form:contains('How to process results')")
    # Click on "Next" button
    self.Click("css=grr-new-hunt-wizard-form button.Next")
    self.WaitUntil(self.IsElementPresent,
                   "css=grr-wizard-form:contains('Where to run?')")
    # Click on "Next" button
    self.Click("css=grr-new-hunt-wizard-form button.Next")
    self.WaitUntil(self.IsElementPresent,
                   "css=grr-wizard-form:contains('Review')")

    # Check that the arguments summary is present.
    self.WaitUntil(
        self.IsElementPresent,
        "css=grr-wizard-form:contains('%s')" % file_finder.FileFinder.__name__)
    self.WaitUntil(self.IsTextPresent, b"foo\\x0d\\xc8bar")

    # Click on "Run" button
    self.Click("css=grr-new-hunt-wizard-form button.Next")
    self.WaitUntil(self.IsElementPresent,
                   "css=grr-wizard-form:contains('Created Hunt')")
    # Close the window and check that the hunt was created.
    self.Click("css=button.Next")

    # Check that the hunt object was actually created
    if data_store.RelationalDBEnabled():
      hunts_list = sorted(
          data_store.REL_DB.ReadHuntObjects(offset=0, count=10),
          key=lambda x: x.create_time)
      self.assertLen(hunts_list, 1)

      # Check that the hunt was created with a correct literal value.
      hunt = hunts_list[0]
      self.assertEqual(hunt.args.standard.flow_name,
                       file_finder.FileFinder.__name__)
      self.assertEqual(
          hunt.args.standard.flow_args.conditions[0].contents_literal_match
          .literal, b"foo\x0d\xc8bar")
    else:
      hunts_root = aff4.FACTORY.Open("aff4:/hunts", token=self.token)
      hunts_list = list(hunts_root.OpenChildren())
      self.assertLen(hunts_list, 1)

      # Check that the hunt was created with a correct literal value.
      hunt = hunts_list[0]
      self.assertEqual(hunt.args.flow_runner_args.flow_name,
                       file_finder.FileFinder.__name__)
      self.assertEqual(
          hunt.args.flow_args.conditions[0].contents_literal_match.literal,
          b"foo\x0d\xc8bar")

  def testOutputPluginsListEmptyWhenNoDefaultOutputPluginSet(self):
    self.Open("/#main=ManageHunts")
    self.Click("css=button[name=NewHunt]")

    # Select "List Processes" flow.
    self.Click("css=#_Processes > i.jstree-icon")
    self.Click("link=ListProcesses")

    # Click on "Next" button
    self.Click("css=grr-new-hunt-wizard-form button.Next")
    self.WaitUntil(self.IsElementPresent,
                   "css=grr-wizard-form:contains('Hunt parameters')")

    # There should be no dummy output plugin visible.
    self.Click("css=grr-new-hunt-wizard-form button.Next")
    self.WaitUntil(self.IsElementPresent,
                   "css=grr-wizard-form:contains('How to process results')")
    self.WaitUntilNot(self.IsElementPresent,
                      "css=grr-wizard-form:contains('Dummy do do')")

  def testDefaultOutputPluginIsCorrectlyAddedToThePluginsList(self):
    with test_lib.ConfigOverrider(
        {"AdminUI.new_hunt_wizard.default_output_plugin": "DummyOutputPlugin"}):
      self.Open("/#main=ManageHunts")
      self.Click("css=button[name=NewHunt]")

      # Select "List Processes" flow.
      self.Click("css=#_Processes > i.jstree-icon")
      self.Click("link=ListProcesses")

      # Click on "Next" button
      self.Click("css=grr-new-hunt-wizard-form button.Next")
      self.WaitUntil(self.IsElementPresent,
                     "css=grr-wizard-form:contains('Hunt parameters')")

      # Dummy output plugin should be added by default.
      self.Click("css=grr-new-hunt-wizard-form button.Next")
      self.WaitUntil(self.IsElementPresent,
                     "css=grr-wizard-form:contains('How to process results')")
      self.WaitUntil(self.IsElementPresent,
                     "css=grr-wizard-form:contains('DummyOutputPlugin')")

  def testLabelsHuntRuleDisplaysAvailableLabels(self):
    client_id = self.SetupClient(0).Basename()

    self.AddClientLabel(client_id, u"owner1", u"foo")
    self.AddClientLabel(client_id, u"owner2", u"bar")

    self.Open("/#main=ManageHunts")
    self.Click("css=button[name=NewHunt]")

    # Select "List Processes" flow.
    self.Click("css=#_Processes > i.jstree-icon")
    self.Click("link=ListProcesses")

    # Click 'Next' to go to hunt parameters page.
    self.Click("css=grr-new-hunt-wizard-form button.Next")

    # Click 'Next' to go to output plugins page.
    self.Click("css=grr-new-hunt-wizard-form button.Next")

    # Click 'Next' to go to hunt rules page.
    self.Click("css=grr-new-hunt-wizard-form button.Next")

    self.Click("css=grr-new-hunt-wizard-form button[name=Add]")

    # Select 'Clients With Label' rule.
    self.Select("css=grr-new-hunt-wizard-form div.well select", "Label")
    # Check that there's an option present for labels 'bar' (this option
    # should be selected) and for label 'foo'.
    self.WaitUntil(
        self.IsElementPresent, "css=grr-new-hunt-wizard-form div.well "
        ".form-group:has(label:contains('Label')) "
        "select option:selected[label=bar]")
    self.WaitUntil(
        self.IsElementPresent, "css=grr-new-hunt-wizard-form div.well "
        ".form-group:has(label:contains('Label')) "
        "select option:not(:selected)[label=foo]")

  def testLabelsHuntRuleMatchesCorrectClients(self):
    client_ids = self.SetupClients(10)

    self.AddClientLabel(client_ids[1], u"owner1", u"foo")
    self.AddClientLabel(client_ids[1], u"owner2", u"bar")
    self.AddClientLabel(client_ids[7], u"GRR", u"bar")

    self.Open("/#main=ManageHunts")
    self.Click("css=button[name=NewHunt]")

    # Select "List Processes" flow.
    self.Click("css=#_Processes > i.jstree-icon")
    self.Click("link=ListProcesses")

    # Click 'Next' to go to the output plugins page, hunt parameters page
    # and then to hunt rules page.
    self.Click("css=grr-new-hunt-wizard-form button.Next")
    self.WaitUntil(self.IsElementPresent,
                   "css=grr-wizard-form:contains('Hunt parameters')")
    self.Click("css=grr-new-hunt-wizard-form button.Next")
    self.WaitUntil(self.IsElementPresent,
                   "css=grr-wizard-form:contains('How to process results')")
    self.Click("css=grr-new-hunt-wizard-form button.Next")
    self.WaitUntil(self.IsElementPresent,
                   "css=grr-wizard-form:contains('Where to run?')")

    # Select 'Clients With Label' rule.
    self.Click("css=grr-configure-rules-page button[name=Add]")
    self.Select("css=grr-new-hunt-wizard-form div.well select", "Label")
    self.Select(
        "css=grr-new-hunt-wizard-form div.well .form-group "
        ".form-group:has(label:contains('Label')):nth-last-of-type(1) "
        "select", "foo")
    self.Click("css=grr-new-hunt-wizard-form div.well .form-group "
               ".form-group:has(label:contains('Add label')) button")
    self.Select(
        "css=grr-new-hunt-wizard-form div.well .form-group "
        ".form-group:has(label:contains('Label')):nth-last-of-type(1) "
        "select", "bar")
    self.Select(
        "css=grr-new-hunt-wizard-form div.well .form-group "
        ".form-group:has(label:contains('Match mode')) select", "Match any")

    # Click 'Next' to go to hunt overview page.  Then click 'Next' to go to
    # submit the hunt and wait until it's created.
    self.Click("css=grr-new-hunt-wizard-form button.Next")
    self.Click("css=grr-new-hunt-wizard-form button.Next")
    self.WaitUntil(self.IsElementPresent,
                   "css=grr-wizard-form:contains('Created Hunt')")

    if data_store.RelationalDBEnabled():
      hunts_list = sorted(
          data_store.REL_DB.ReadHuntObjects(offset=0, count=10),
          key=lambda x: x.create_time)
      hunt = hunts_list[0]
      lib_hunt.StartHunt(hunt.hunt_id)
    else:
      hunts_root = aff4.FACTORY.Open("aff4:/hunts", token=self.token)
      hunts_list = list(hunts_root.OpenChildren())
      hunt = hunts_list[0]

      with aff4.FACTORY.Open(hunt.urn, mode="rw", token=self.token) as hunt:
        hunt.Run()

    foreman_obj = foreman.GetForeman(token=self.token)
    for client_id in client_ids:
      tasks_assigned = foreman_obj.AssignTasksToClient(client_id.Basename())
      if client_id in [client_ids[1], client_ids[7]]:
        self.assertTrue(tasks_assigned)
      else:
        self.assertFalse(tasks_assigned)

  def CreateSampleHunt(self, description, token=None):
    self.StartHunt(
        description=description,
        flow_runner_args=rdf_flow_runner.FlowRunnerArgs(
            flow_name=transfer.GetFile.__name__),
        flow_args=transfer.GetFileArgs(
            pathspec=rdf_paths.PathSpec(
                path="/tmp/evil.txt",
                pathtype=rdf_paths.PathSpec.PathType.TSK,
            )),
        client_rule_set=self._CreateForemanClientRuleSet(),
        output_plugins=[
            rdf_output_plugin.OutputPluginDescriptor(
                plugin_name="DummyOutputPlugin",
                plugin_args=gui_test_lib.DummyOutputPlugin.args_type(
                    filename_regex="blah!", fetch_binaries=True))
        ],
        client_rate=60,
        paused=True,
        token=token)

  def testPathAutocomplete(self):
    # Open Hunts
    self.Open("/#/hunts")

    # Open "New Hunt" wizard
    self.Click("css=button[name=NewHunt]")
    self.WaitUntil(self.IsElementPresent,
                   "css=grr-wizard-form:contains('What to run?')")

    # Click on Filesystem item in flows list
    self.Click("css=#_Filesystem > i.jstree-icon")

    # Click on the FileFinder item in Filesystem flows list
    self.Click("link=File Finder")

    input_selector = "css=grr-form-glob-expression input[uib-typeahead]"

    # Change "path"
    self.Type(input_selector, "/foo/%%path")

    self.WaitUntil(self.IsElementPresent,
                   "css=[uib-typeahead-popup]:contains('%%environ_path%%')")

    self.GetElement(input_selector).send_keys(keys.Keys.ENTER)

    self.WaitUntilEqual("/foo/%%environ_path%%", self.GetValue,
                        input_selector + ":text")


if __name__ == "__main__":
  app.run(test_lib.main)
