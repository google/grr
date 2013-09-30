#!/usr/bin/env python

"""Test of "New Hunt" wizard."""


from grr.gui import runtests_test

from grr.lib import access_control
from grr.lib import aff4
from grr.lib import data_store
from grr.lib import flags
from grr.lib import rdfvalue
from grr.lib import test_lib


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
  def CreateHuntFixture():
    token = access_control.ACLToken(username="test", reason="test")

    # Ensure that clients list is empty
    root = aff4.FACTORY.Open(aff4.ROOT_URN, token=token)
    for client_urn in root.ListChildren():
      data_store.DB.DeleteSubject(client_urn, token=token)

    # Ensure that hunts list is empty
    hunts_root = aff4.FACTORY.Open("aff4:/hunts", token=token)
    for hunt_urn in hunts_root.ListChildren():
      data_store.DB.DeleteSubject(hunt_urn, token=token)

    # Add 2 distinct clients
    client_id = "C.1%015d" % 0
    fd = aff4.FACTORY.Create(aff4.ROOT_URN.Add(client_id), "VFSGRRClient",
                             token=token)
    fd.Set(fd.Schema.SYSTEM("Windows"))
    fd.Set(fd.Schema.CLOCK(2336650631137737))
    fd.Close()

    client_id = "C.1%015d" % 1
    fd = aff4.FACTORY.Create(aff4.ROOT_URN.Add(client_id), "VFSGRRClient",
                             token=token)
    fd.Set(fd.Schema.SYSTEM("Linux"))
    fd.Set(fd.Schema.CLOCK(2336650631137737))
    fd.Close()

  def setUp(self):
    super(TestNewHuntWizard, self).setUp()
    with self.ACLChecksDisabled():
      self.CreateHuntFixture()

  def testNewHuntWizard(self):
    with self.ACLChecksDisabled():
      # Create a Foreman with an empty rule set
      self.foreman = aff4.FACTORY.Create("aff4:/foreman", "GRRForeman",
                                         token=self.token)
      self.foreman.Set(self.foreman.Schema.RULES())
      self.foreman.Close()

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

    # Click on DownloadDirectory item in Filesystem flows list
    self.WaitUntil(self.IsElementPresent,
                   "link=DownloadDirectory")
    self.Click("link=DownloadDirectory")

    # Wait for flow configuration form to be rendered (just wait for first
    # input field).
    self.WaitUntil(self.IsElementPresent,
                   "css=.Wizard input[id=args-pathspec-path]")

    # Change "path", "pathtype", "depth" and "ignore_errors" values
    self.Type("css=.Wizard input[id=args-pathspec-path]", "/tmp")
    self.Select("css=.Wizard select[id=args-pathspec-pathtype]",
                "TSK")
    self.Type("css=.Wizard input[id=args-depth]", "42")
    self.Click("css=.Wizard input[id=args-ignore_errors]")

    # Click on "Next" button
    self.Click("css=.Wizard button.Next")
    self.WaitUntil(self.IsTextPresent, "Output Processing")

    # Click on "Back" button and check that all the values in the form
    # remain intact.
    self.Click("css=.Wizard button.Back")
    self.WaitUntil(self.IsElementPresent,
                   "css=.Wizard input#args-pathspec-path")
    self.assertEqual(
        "/tmp", self.GetValue(
            "css=.Wizard input#args-pathspec-path"))
    self.assertEqual(
        "TSK",
        self.GetSelectedLabel(
            "css=.Wizard select#args-pathspec-pathtype"))
    self.assertEqual(
        "42",
        self.GetValue("css=.Wizard input#args-depth"))
    self.assertTrue(
        self.IsChecked("css=.Wizard input#args-ignore_errors"))

    # Click on "Next" button
    self.Click("css=.Wizard button.Next")
    self.WaitUntil(self.IsTextPresent, "Output Processing")

    # Configure the hunt to use a collection and also send an email on results.
    self.Select("css=.Wizard select[id=output_1-option]",
                "Send an email for each result.")
    self.Type("css=.Wizard input[id=output_1-email]",
              "test@grrserver.com")

    self.Click("css=.Wizard button:contains('Add Output Plugin')")
    self.Select(
        "css=.Wizard select[id=output_2-option]",
        "         Store results in a collection.\n          (default)\n     ")

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
    self.WaitUntil(self.IsTextPresent, "Pathspec")
    self.WaitUntil(self.IsTextPresent, "/tmp")
    self.WaitUntil(self.IsTextPresent, "Depth")
    self.WaitUntil(self.IsTextPresent, "42")

    # Check that output plugins are shown.
    self.assertTrue(self.IsTextPresent("EmailPlugin"))
    self.assertTrue(self.IsTextPresent("test@grrserver.com"))
    self.assertTrue(self.IsTextPresent("CollectionPlugin"))

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

    self.assertTrue(self.IsTextPresent("Pathspec"))
    self.assertTrue(self.IsTextPresent("/tmp"))
    self.assertTrue(self.IsTextPresent("Depth"))
    self.assertTrue(self.IsTextPresent("42"))

    self.assertTrue(self.IsTextPresent("EmailPlugin"))
    self.assertTrue(self.IsTextPresent("test@grrserver.com"))
    self.assertTrue(self.IsTextPresent("CollectionPlugin"))

    # Check that the hunt object was actually created
    hunts_root = aff4.FACTORY.Open("aff4:/hunts", token=self.token)
    hunts_list = list(hunts_root.OpenChildren())
    self.assertEqual(len(hunts_list), 1)

    # Check that the hunt was created with a correct flow
    hunt = hunts_list[0]
    self.assertEqual(hunt.state.args.flow_runner_args.flow_name,
                     "DownloadDirectory")
    self.assertEqual(hunt.state.args.flow_args.pathspec.path, "/tmp")
    self.assertEqual(hunt.state.args.flow_args.pathspec.pathtype,
                     rdfvalue.PathSpec.PathType.TSK)
    self.assertEqual(hunt.state.args.flow_args.depth, 42)
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

    self.assertEquals(len(hunt_rules), 1)
    self.assertTrue(
        abs(int((hunt_rules[0].expires - hunt_rules[0].created) * 1e-6) -
            31 * 24 * 60 * 60) <= 1)

    self.assertEquals(len(hunt_rules[0].regex_rules), 2)
    self.assertEquals(hunt_rules[0].regex_rules[0].path, "/")
    self.assertEquals(hunt_rules[0].regex_rules[0].attribute_name, "System")
    self.assertEquals(hunt_rules[0].regex_rules[0].attribute_regex, "Linux")

    self.assertEquals(hunt_rules[0].regex_rules[1].path, "/")
    self.assertEquals(hunt_rules[0].regex_rules[1].attribute_name, "System")
    self.assertEquals(hunt_rules[0].regex_rules[1].attribute_regex, "Darwin")

    self.assertEquals(len(hunt_rules[0].integer_rules), 1)
    self.assertEquals(hunt_rules[0].integer_rules[0].path, "/")
    self.assertEquals(hunt_rules[0].integer_rules[0].attribute_name, "Clock")
    self.assertEquals(hunt_rules[0].integer_rules[0].operator,
                      rdfvalue.ForemanAttributeInteger.Operator.GREATER_THAN)
    self.assertEquals(hunt_rules[0].integer_rules[0].value, 1336650631137737)


def main(argv):
  # Run the full test suite
  runtests_test.SeleniumTestProgram(argv=argv)

if __name__ == "__main__":
  flags.StartMain(main)
