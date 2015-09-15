#!/usr/bin/env python

"""Test of "New Hunt" wizard."""


from grr.gui import runtests_test

from grr.lib import access_control
from grr.lib import aff4
from grr.lib import data_store
from grr.lib import flags
from grr.lib import output_plugin
from grr.lib import test_lib
from grr.lib.flows.general import processes
from grr.lib.rdfvalues import client as rdf_client
from grr.lib.rdfvalues import foreman as rdf_foreman
from grr.lib.rdfvalues import paths as rdf_paths


class DummyOutputPlugin(output_plugin.OutputPlugin):
  """An output plugin that sends an email for each response received."""

  name = "dummy"
  description = "Dummy do do."
  args_type = processes.ListProcessesArgs

  def ProcessResponses(self, responses):
    pass


class TestNewHuntWizard(test_lib.GRRSeleniumTest):
  """Test the Cron view GUI."""

  @staticmethod
  def FindForemanRules(hunt, token):
    fman = aff4.FACTORY.Open("aff4:/foreman", mode="r", aff4_type="GRRForeman",
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
      if aff4.VFSGRRClient.CLIENT_ID_RE.match(client_urn.Basename()):
        data_store.DB.DeleteSubject(client_urn, token=token)

    # Add 2 distinct clients
    client_id = "C.1%015d" % 0
    fd = aff4.FACTORY.Create(rdf_client.ClientURN(client_id), "VFSGRRClient",
                             token=token)
    fd.Set(fd.Schema.SYSTEM("Windows"))
    fd.Set(fd.Schema.CLOCK(2336650631137737))
    fd.Close()

    client_id = "C.1%015d" % 1
    fd = aff4.FACTORY.Create(rdf_client.ClientURN(client_id), "VFSGRRClient",
                             token=token)
    fd.Set(fd.Schema.SYSTEM("Linux"))
    fd.Set(fd.Schema.CLOCK(2336650631137737))
    fd.Close()

  def setUp(self):
    super(TestNewHuntWizard, self).setUp()

    with self.ACLChecksDisabled():
      # Create a Foreman with an empty rule set.
      with aff4.FACTORY.Create("aff4:/foreman", "GRRForeman", mode="rw",
                               token=self.token) as self.foreman:
        self.foreman.Set(self.foreman.Schema.RULES())
        self.foreman.Close()

  def testNewHuntWizard(self):
    with self.ACLChecksDisabled():
      self.CreateHuntFixtureWithTwoClients()

    # Open up and click on View Hunts.
    self.Open("/")
    self.WaitUntil(self.IsElementPresent, "client_query")
    self.WaitUntil(self.IsElementPresent, "css=a[grrtarget=ManageHunts]")
    self.Click("css=a[grrtarget=ManageHunts]")
    self.WaitUntil(self.IsElementPresent, "css=button[name=NewHunt]")

    # Open up "New Hunt" wizard
    self.Click("css=button[name=NewHunt]")
    self.WaitUntil(self.IsTextPresent, "What to run?")

    # Click on Filesystem item in flows list
    self.WaitUntil(self.IsElementPresent, "css=#_Filesystem > ins.jstree-icon")
    self.Click("css=#_Filesystem > ins.jstree-icon")

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

    self.Click("css=grr-new-hunt-wizard-form button[name=Add]")
    # Configure the hunt to send an email on results.
    self.Select("css=grr-new-hunt-wizard-form select",
                "DummyOutputPlugin")
    self.Type(
        "css=grr-new-hunt-wizard-form "
        "grr-form-proto-single-field:has(label:contains('Filename Regex')) "
        "input", "some regex")

    # Click on "Next" button
    self.Click("css=grr-new-hunt-wizard-form button.Next")
    self.WaitUntil(self.IsTextPresent, "Where to run?")

    # Create 3 foreman rules. Note that "Add" button adds rules to the beginning
    # of a list. So we always use :nth(0) selector.
    self.Select("css=grr-new-hunt-wizard-form div.Rule:nth(0) select",
                "Regular Expression")
    self.Select(
        "css=grr-new-hunt-wizard-form div.Rule:nth(0) "
        "grr-form-proto-single-field:has(label:contains('Attribute name')) "
        "select", "System")
    self.Type(
        "css=grr-new-hunt-wizard-form div.Rule:nth(0) "
        "grr-form-proto-single-field:has(label:contains('Attribute regex')) "
        "input", "Linux")

    self.Click("css=grr-new-hunt-wizard-form button[name=Add]")
    self.Select("css=grr-new-hunt-wizard-form div.Rule:nth(0) select",
                "Integer Rule")
    self.Select(
        "css=grr-new-hunt-wizard-form div.Rule:nth(0) "
        "grr-form-proto-single-field:has(label:contains('Attribute name')) "
        "select", "Clock")
    self.Select(
        "css=grr-new-hunt-wizard-form div.Rule:nth(0) "
        "grr-form-proto-single-field:has(label:contains('Operator')) select",
        "GREATER_THAN")
    self.Type(
        "css=grr-new-hunt-wizard-form div.Rule:nth(0) "
        "grr-form-proto-single-field:has(label:contains('Value')) input",
        "1336650631137737")

    self.Click("css=grr-new-hunt-wizard-form button[name=Add]")
    self.Select("css=grr-new-hunt-wizard-form div.Rule:nth(0) select",
                "OS X")

    # Click on "Back" button
    self.Click("css=grr-new-hunt-wizard-form button.Back")
    self.WaitUntil(self.IsTextPresent, "Output Processing")

    # Click on "Next" button again and check that all the values that we've just
    # entered remain intact.
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

    # Check that rules summary is present.
    self.assertTrue(self.IsTextPresent("Regex rules"))

    # Click on "Run" button
    self.Click("css=grr-new-hunt-wizard-form button.Next")

    self.WaitUntil(self.IsTextPresent, "Created Hunt")

    # Close the window and check that the hunt was created.
    self.Click("css=button.Next")

    # Select newly created cron job.
    self.Click("css=grr-hunts-list td:contains('GenericHunt')")

    # Check that correct details are displayed in cron job details tab.
    self.WaitUntil(self.IsTextPresent, "GenericHunt")
    self.WaitUntil(self.IsTextPresent, "Flow args")

    self.assertTrue(self.IsTextPresent("Paths"))
    self.assertTrue(self.IsTextPresent("/tmp"))

    self.assertTrue(self.IsTextPresent("DummyOutputPlugin"))
    self.assertTrue(self.IsTextPresent("some regex"))

    # Check that the hunt object was actually created
    hunts_root = aff4.FACTORY.Open("aff4:/hunts", token=self.token)
    hunts_list = list(hunts_root.OpenChildren())
    self.assertEqual(len(hunts_list), 1)

    # Check that the hunt was created with a correct flow
    hunt = hunts_list[0]
    self.assertEqual(hunt.state.args.flow_runner_args.flow_name,
                     "FileFinder")
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
    self.assertTrue(
        abs(int(hunt_rules[0].expires - hunt_rules[0].created) -
            31 * 24 * 60 * 60) <= 1)

    self.assertEqual(len(hunt_rules[0].regex_rules), 2)
    self.assertEqual(hunt_rules[0].regex_rules[0].path, "/")
    self.assertEqual(hunt_rules[0].regex_rules[0].attribute_name, "System")
    self.assertEqual(hunt_rules[0].regex_rules[0].attribute_regex, "Darwin")

    self.assertEqual(hunt_rules[0].regex_rules[1].path, "/")
    self.assertEqual(hunt_rules[0].regex_rules[1].attribute_name, "System")
    self.assertEqual(hunt_rules[0].regex_rules[1].attribute_regex, "Linux")

    self.assertEqual(len(hunt_rules[0].integer_rules), 1)
    self.assertEqual(hunt_rules[0].integer_rules[0].path, "/")
    self.assertEqual(hunt_rules[0].integer_rules[0].attribute_name, "Clock")
    self.assertEqual(hunt_rules[0].integer_rules[0].operator,
                     rdf_foreman.ForemanAttributeInteger.Operator.GREATER_THAN)
    self.assertEqual(hunt_rules[0].integer_rules[0].value, 1336650631137737)

  def testOutputPluginsListEmptyWhenNoDefaultOutputPluginSet(self):
    self.Open("/#main=ManageHunts")
    self.Click("css=button[name=NewHunt]")

    # Select "List Processes" flow.
    self.Click("css=#_Processes > ins.jstree-icon")
    self.Click("link=ListProcesses")

    # There should be no dummy output plugin visible.
    self.Click("css=grr-new-hunt-wizard-form button.Next")
    self.WaitUntil(self.IsTextPresent, "Output Processing")
    self.WaitUntilNot(self.IsTextPresent, "Dummy do do")

  def testDefaultOutputPluginIsCorrectlyAddedToThePluginsList(self):
    with test_lib.ConfigOverrider({
        "AdminUI.new_hunt_wizard.default_output_plugin":
        "DummyOutputPlugin"}):
      self.Open("/#main=ManageHunts")
      self.Click("css=button[name=NewHunt]")

      # Select "List Processes" flow.
      self.Click("css=#_Processes > ins.jstree-icon")
      self.Click("link=ListProcesses")

      # Dummy output plugin should be added by default.
      self.Click("css=grr-new-hunt-wizard-form button.Next")
      self.WaitUntil(self.IsTextPresent, "Output Processing")
      self.WaitUntil(self.IsTextPresent, "DummyOutputPlugin")

  def testLabelsHuntRuleDisplaysAvailableLabels(self):
    with self.ACLChecksDisabled():
      with aff4.FACTORY.Open("C.0000000000000001", aff4_type="VFSGRRClient",
                             mode="rw", token=self.token) as client:
        client.AddLabels("foo", owner="owner1")
        client.AddLabels("bar", owner="owner2")

    self.Open("/#main=ManageHunts")
    self.Click("css=button[name=NewHunt]")

    # Select "List Processes" flow.
    self.Click("css=#_Processes > ins.jstree-icon")
    self.Click("link=ListProcesses")

    # Click 'Next' to go to output plugins page.
    self.Click("css=grr-new-hunt-wizard-form button.Next")

    # Click 'Next' to go to hunt rules page.
    self.Click("css=grr-new-hunt-wizard-form button.Next")

    # Select 'Clients With Label' rule.
    self.Select("css=grr-new-hunt-wizard-form div.Rule select",
                "Clients With Label")

    # Check that there's an option present for labels 'bar' (this option should
    # be selected) and for label 'foo'.
    self.WaitUntil(self.IsElementPresent,
                   "css=grr-new-hunt-wizard-form div.Rule "
                   ".form-group:has(label:contains('Label')) "
                   "select option:selected[label=bar]")
    self.WaitUntil(self.IsElementPresent,
                   "css=grr-new-hunt-wizard-form div.Rule "
                   ".form-group:has(label:contains('Label')) "
                   "select option:not(:selected)[label=foo]")

  def testLabelsHuntRuleCreatesForemanRegexRuleInResultingHunt(self):
    with self.ACLChecksDisabled():
      with aff4.FACTORY.Open("C.0000000000000001", mode="rw",
                             token=self.token) as client:
        client.AddLabels("foo", owner="test")

    self.Open("/#main=ManageHunts")
    self.Click("css=button[name=NewHunt]")

    # Select "List Processes" flow.
    self.Click("css=#_Processes > ins.jstree-icon")
    self.Click("link=ListProcesses")

    # Click 'Next' to go to the output plugins page.
    self.Click("css=grr-new-hunt-wizard-form button.Next")

    # Click 'Next' to go to the hunt rules page.
    self.Click("css=grr-new-hunt-wizard-form button.Next")

    # Select 'Clients With Label' rule.
    self.Select("css=grr-new-hunt-wizard-form div.Rule select",
                "Clients With Label")
    self.Select("css=grr-new-hunt-wizard-form div.Rule "
                ".form-group:has(label:contains('Label')) select", "foo")

    # Click 'Next' to go to the hunt overview page. Check that generated regexp
    # is displayed there.
    self.Click("css=grr-new-hunt-wizard-form button.Next")
    self.WaitUntil(self.IsTextPresent, "(.+,|\\A)foo(,.+|\\Z)")

    # Click 'Next' to go to submit the hunt and wait until it's created.
    self.Click("css=grr-new-hunt-wizard-form button.Next")
    self.WaitUntil(self.IsTextPresent, "Created Hunt")

    # Get hunt's rules.
    with self.ACLChecksDisabled():
      hunts_root = aff4.FACTORY.Open("aff4:/hunts", token=self.token)
      hunts_list = list(hunts_root.OpenChildren(mode="rw"))
      hunt = hunts_list[0]

      hunt.Run()  # Run the hunt so that rules are added to the foreman.
      hunt_rules = self.FindForemanRules(hunt, token=self.token)

    self.assertEqual(len(hunt_rules), 1)
    self.assertEqual(len(hunt_rules[0].regex_rules), 1)
    self.assertEqual(hunt_rules[0].regex_rules[0].path, "/")
    self.assertEqual(hunt_rules[0].regex_rules[0].attribute_name, "Labels")
    self.assertEqual(hunt_rules[0].regex_rules[0].attribute_regex,
                     "(.+,|\\A)foo(,.+|\\Z)")

  def testLabelsHuntRuleMatchesCorrectClients(self):
    with self.ACLChecksDisabled():
      client_ids = self.SetupClients(10)

    with self.ACLChecksDisabled():
      with aff4.FACTORY.Open("C.0000000000000001", mode="rw",
                             token=self.token) as client:
        client.AddLabels("foo", owner="owner1")
        client.AddLabels("bar", owner="owner2")

      with aff4.FACTORY.Open("C.0000000000000007", mode="rw",
                             token=self.token) as client:
        client.AddLabels("bar", owner="GRR")

    self.Open("/#main=ManageHunts")
    self.Click("css=button[name=NewHunt]")

    # Select "List Processes" flow.
    self.Click("css=#_Processes > ins.jstree-icon")
    self.Click("link=ListProcesses")

    # Click 'Next' to go to the output plugins page and then to hunt rules page.
    self.Click("css=grr-new-hunt-wizard-form button.Next")
    self.Click("css=grr-new-hunt-wizard-form button.Next")

    # Select 'Clients With Label' rule.
    self.Select("css=grr-new-hunt-wizard-form div.Rule select",
                "Clients With Label")
    self.Select("css=grr-new-hunt-wizard-form div.Rule "
                ".form-group:has(label:contains('Label')) select", "foo")

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
        foreman.AssignTasksToClient(client_id)

      # Check that hunt flow was started only on labeled clients.
      for client_id in client_ids:
        flows_count = len(list(aff4.FACTORY.Open(
            client_id.Add("flows"), token=self.token).ListChildren()))

        if (client_id == rdf_client.ClientURN("C.0000000000000001") or
            client_id == rdf_client.ClientURN("C.0000000000000007")):
          self.assertEqual(flows_count, 1)
        else:
          self.assertEqual(flows_count, 0)


def main(argv):
  # Run the full test suite
  runtests_test.SeleniumTestProgram(argv=argv)

if __name__ == "__main__":
  flags.StartMain(main)
