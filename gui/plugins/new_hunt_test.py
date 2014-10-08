#!/usr/bin/env python

"""Test of "New Hunt" wizard."""


from grr.gui import runtests_test

from grr.lib import access_control
from grr.lib import aff4
from grr.lib import config_lib
from grr.lib import data_store
from grr.lib import flags
from grr.lib import rdfvalue
from grr.lib import test_lib
from grr.lib.hunts import output_plugins


class DummyOutputPlugin(output_plugins.HuntOutputPlugin):
  """An output plugin that sends an email for each response received."""

  name = "dummy"
  description = "Dummy do do."
  args_type = rdfvalue.ListProcessesArgs


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
    fd = aff4.FACTORY.Create(rdfvalue.ClientURN(client_id), "VFSGRRClient",
                             token=token)
    fd.Set(fd.Schema.SYSTEM("Windows"))
    fd.Set(fd.Schema.CLOCK(2336650631137737))
    fd.Close()

    client_id = "C.1%015d" % 1
    fd = aff4.FACTORY.Create(rdfvalue.ClientURN(client_id), "VFSGRRClient",
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
                   "css=.Wizard input[id=args-paths-0]")

    # Change "path" and "pathtype" values
    self.Type("css=.Wizard input[id=args-paths-0]", "/tmp")
    self.Select("css=.Wizard select[id=args-pathtype]", "TSK")

    # Click on "Next" button
    self.Click("css=.Wizard button.Next")
    self.WaitUntil(self.IsTextPresent, "Output Processing")

    # Click on "Back" button and check that all the values in the form
    # remain intact.
    self.Click("css=.Wizard button.Back")
    self.WaitUntil(self.IsElementPresent,
                   "css=.Wizard input#args-paths-0")

    self.assertEqual("/tmp", self.GetValue(
        "css=.Wizard input#args-paths-0"))

    self.assertEqual(
        "TSK", self.GetSelectedLabel("css=.Wizard select#args-pathtype"))

    # Click on "Next" button
    self.Click("css=.Wizard button.Next")
    self.WaitUntil(self.IsTextPresent, "Output Processing")

    self.Click("css=.Wizard button:contains('Add Output Plugin')")
    # Configure the hunt to send an email on results.
    self.Select("css=.Wizard select[id=output_1-option]",
                "Send an email for each result.")
    self.Type("css=.Wizard input[id=output_1-email]",
              "test@%s" % config_lib.CONFIG["Logging.domain"])

    # Click on "Next" button
    self.Click("css=.Wizard button.Next")
    self.WaitUntil(self.IsTextPresent, "Where to run?")

    # Create 3 foreman rules
    self.WaitUntil(
        self.IsElementPresent,
        "css=.Wizard select[id=rule_1-option]")
    self.Select("css=.Wizard select[id=rule_1-option]",
                "Regular Expressions")
    self.Select("css=.Wizard select[id=rule_1-attribute_name]",
                "System")
    self.Type("css=.Wizard input[id=rule_1-attribute_regex]",
              "Linux")

    # Make the button visible by scrolling to the bottom.
    self.driver.execute_script("""
$("button:contains('Add Rule')").parent().scrollTop(10000)
""")

    self.Click("css=.Wizard button:contains('Add Rule')")
    self.Select("css=.Wizard select[id=rule_2-option]",
                "Integer Rule")
    self.Select("css=.Wizard select[id=rule_2-attribute_name]",
                "Clock")
    self.Select("css=.Wizard select[id=rule_2-operator]",
                "GREATER_THAN")
    self.Type("css=.Wizard input[id=rule_2-value]",
              "1336650631137737")

    # Make the button visible by scrolling to the bottom.
    self.driver.execute_script("""
$("button:contains('Add Rule')").parent().scrollTop(10000)
""")

    self.Click("css=.Wizard button:contains('Add Rule')")
    self.Select("css=.Wizard select[id=rule_3-option]",
                "OSX")

    # Make the button visible by scrolling to the bottom.
    self.driver.execute_script("""
$("button:contains('Add Rule')").parent().scrollTop(10000)
""")

    # Click on "Back" button
    self.Click("css=.Wizard button.Back")
    self.WaitUntil(self.IsTextPresent, "Output Processing")

    # Click on "Next" button again and check that all the values that we've just
    # entered remain intact.
    self.Click("css=.Wizard button.Next")
    self.WaitUntil(self.IsTextPresent, "Where to run?")

    # Click on "Next" button
    self.Click("css=.Wizard button.Next")
    self.WaitUntil(self.IsTextPresent, "Review")

    # Check that the arguments summary is present.
    self.WaitUntil(self.IsTextPresent, "Paths")
    self.WaitUntil(self.IsTextPresent, "/tmp")

    # Check that output plugins are shown.
    self.assertTrue(self.IsTextPresent("EmailPlugin"))
    self.assertTrue(self.IsTextPresent("test@%s" %
                                       config_lib.CONFIG["Logging.domain"]))

    # Check that rules summary is present.
    self.assertTrue(self.IsTextPresent("Regex rules"))

    # Click on "Run" button
    self.Click("css=.Wizard button.Next")

    self.WaitUntil(self.IsTextPresent,
                   "Hunt was created!")

    # Close the window and check that cron job object was created.
    self.Click("css=button.Finish")

    # Select newly created cron job.
    self.Click("css=td:contains('GenericHunt')")

    # Check that correct details are displayed in cron job details tab.
    self.WaitUntil(self.IsTextPresent, "GenericHunt")
    self.WaitUntil(self.IsTextPresent, "Flow args")

    self.assertTrue(self.IsTextPresent("Paths"))
    self.assertTrue(self.IsTextPresent("/tmp"))

    self.assertTrue(self.IsTextPresent("EmailPlugin"))
    self.assertTrue(self.IsTextPresent("test@%s" %
                                       config_lib.CONFIG["Logging.domain"]))

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
                     rdfvalue.PathSpec.PathType.TSK)
    # self.assertEqual(hunt.state.args.flow_args.ignore_errors, True)
    self.assertTrue(hunt.state.args.output_plugins[0].plugin_name,
                    "EmailPlugin")

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
    self.assertEqual(hunt_rules[0].regex_rules[0].attribute_regex, "Linux")

    self.assertEqual(hunt_rules[0].regex_rules[1].path, "/")
    self.assertEqual(hunt_rules[0].regex_rules[1].attribute_name, "System")
    self.assertEqual(hunt_rules[0].regex_rules[1].attribute_regex, "Darwin")

    self.assertEqual(len(hunt_rules[0].integer_rules), 1)
    self.assertEqual(hunt_rules[0].integer_rules[0].path, "/")
    self.assertEqual(hunt_rules[0].integer_rules[0].attribute_name, "Clock")
    self.assertEqual(hunt_rules[0].integer_rules[0].operator,
                     rdfvalue.ForemanAttributeInteger.Operator.GREATER_THAN)
    self.assertEqual(hunt_rules[0].integer_rules[0].value, 1336650631137737)

  def testOutputPluginsListEmptyWhenNoDefaultOutputPluginSet(self):
    self.Open("/#main=ManageHunts")
    self.Click("css=button[name=NewHunt]")

    # Select "List Processes" flow.
    self.Click("css=#_Processes > ins.jstree-icon")
    self.Click("link=ListProcesses")

    # There should be no dummy output plugin visible.
    self.Click("css=.Wizard button.Next")
    self.WaitUntil(self.IsTextPresent, "Output Processing")
    self.WaitUntilNot(self.IsTextPresent, "Dummy do do")

  def testDefaultOutputPluginIsCorrectlyAddedToThePluginsList(self):
    config_lib.CONFIG.Set("AdminUI.new_hunt_wizard.default_output_plugin",
                          "DummyOutputPlugin")

    self.Open("/#main=ManageHunts")
    self.Click("css=button[name=NewHunt]")

    # Select "List Processes" flow.
    self.Click("css=#_Processes > ins.jstree-icon")
    self.Click("link=ListProcesses")

    # Dummy output plugin should be added by default.
    self.Click("css=.Wizard button.Next")
    self.WaitUntil(self.IsTextPresent, "Output Processing")
    self.WaitUntil(self.IsTextPresent, "Dummy do do")

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
    self.Click("css=.Wizard button.Next")

    # Click 'Next' to go to hunt rules page.
    self.Click("css=.Wizard button.Next")

    # Select 'Clients With Label' rule.
    self.Select("css=.Wizard select[id=rule_1-option]", "Clients With Label")

    # Check that there's an option present for labels 'bar' (this option should
    # be selected) and for label 'foo'.
    self.WaitUntil(self.IsElementPresent,
                   "css=.Wizard select[id=rule_1] option:selected[value=bar]")
    self.WaitUntil(self.IsElementPresent,
                   "css=.Wizard select[id=rule_1] option[value=bar]")

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
    self.Click("css=.Wizard button.Next")

    # Click 'Next' to go to the hunt rules page.
    self.Click("css=.Wizard button.Next")

    # Select 'Clients With Label' rule.
    self.Select("css=.Wizard select[id=rule_1-option]", "Clients With Label")
    self.Select("css=.Wizard select[id=rule_1]", "foo")

    # Click 'Next' to go to the hunt overview page. Check that generated regexp
    # is displayed there.
    self.Click("css=.Wizard button.Next")
    self.WaitUntil(self.IsTextPresent, "(.+,|\\A)foo(,.+|\\Z)")

    # Click 'Next' to go to submit the hunt and wait until it's created.
    self.Click("css=.Wizard button.Next")
    self.WaitUntil(self.IsTextPresent, "Hunt was created!")

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
    self.Click("css=.Wizard button.Next")
    self.Click("css=.Wizard button.Next")

    # Select 'Clients With Label' rule.
    self.Select("css=.Wizard select[id=rule_1-option]", "Clients With Label")
    self.Select("css=.Wizard select[id=rule_1]", "foo")

    # Click 'Next' to go to hunt overview page.  Then click 'Next' to go to
    # submit the hunt and wait until it's created.
    self.Click("css=.Wizard button.Next")
    self.Click("css=.Wizard button.Next")
    self.WaitUntil(self.IsTextPresent, "Hunt was created!")

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

        if (client_id == rdfvalue.ClientURN("C.0000000000000001") or
            client_id == rdfvalue.ClientURN("C.0000000000000007")):
          self.assertEqual(flows_count, 1)
        else:
          self.assertEqual(flows_count, 0)


def main(argv):
  # Run the full test suite
  runtests_test.SeleniumTestProgram(argv=argv)

if __name__ == "__main__":
  flags.StartMain(main)
