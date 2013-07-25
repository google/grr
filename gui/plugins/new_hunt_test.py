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
                   "css=.Wizard .HuntFormBody input[name=pathspec_path]")

    # Change "path", "pathtype", "depth" and "ignore_errors" values
    self.Type("css=.Wizard .HuntFormBody input[name=pathspec_path]", "/tmp")
    self.Select("css=.Wizard .HuntFormBody select[name=pathspec_pathtype]",
                "TSK")
    self.Type("css=.Wizard .HuntFormBody input[name=depth]", "42")
    self.Click("css=.Wizard .HuntFormBody input[name=ignore_errors]")

    # Click on "Next" button
    self.Click("css=.Wizard input.Next")
    self.WaitUntil(self.IsTextPresent, "Output Processing")

    # Click on "Back" button and check that all the values in the form
    # remain intact.
    self.Click("css=.Wizard input.Back")
    self.WaitUntil(self.IsElementPresent,
                   "css=.Wizard .HuntFormBody input[name=pathspec_path]")
    self.assertEqual(
        "/tmp", self.GetValue(
            "css=.Wizard .HuntFormBody input[name=pathspec_path]"))
    self.assertEqual(
        "TSK",
        self.GetSelectedLabel(
            "css=.Wizard .HuntFormBody select[name=pathspec_pathtype]"))
    self.assertEqual(
        "42",
        self.GetValue("css=.Wizard .HuntFormBody input[name=depth]"))
    self.assertTrue(
        self.IsChecked("css=.Wizard .HuntFormBody input[name=ignore_errors]"))

    # Click on "Next" button
    self.Click("css=.Wizard input.Next")
    self.WaitUntil(self.IsTextPresent, "Output Processing")

    # Configure the hunt to use a collection and also send an email on results.
    self.Select("css=.Wizard .Rule:nth-of-type(1) select[name=output_type]",
                "Send an email")
    self.Type("css=.Wizard .Rule:nth-of-type(1) input[name=email]",
              "test@grrserver.com")
    self.Click("css=.Wizard input[value='Add another output plugin']")
    self.Select("css=.Wizard .Rule:nth-of-type(2) select[name=output_type]",
                "Store results in a collection")

    # Click on "Next" button again
    self.Click("css=.Wizard input.Next")
    self.WaitUntil(self.IsTextPresent, "Where to run?")

    # Create 3 foreman rules
    self.WaitUntil(
        self.IsElementPresent,
        "css=.Wizard .Rule:nth-of-type(1) select[name=rule_type]")
    self.Select("css=.Wizard .Rule:nth-of-type(1) select[name=rule_type]",
                "Regular expression match")
    self.Type("css=.Wizard .Rule:nth-of-type(1) input[name=attribute_name]",
              "System")
    self.Type("css=.Wizard .Rule:nth-of-type(1) input[name=attribute_regex]",
              "Linux")

    self.Click("css=.Wizard input[value='Add Rule']")
    self.Select("css=.Wizard .Rule:nth-of-type(2) select[name=rule_type]",
                "Integer comparison")
    self.Type("css=.Wizard .Rule:nth-of-type(2) input[name=attribute_name]",
              "Clock")
    self.Select("css=.Wizard .Rule:nth-of-type(2) select[name=operator]",
                "GREATER_THAN")
    self.Type("css=.Wizard .Rule:nth-of-type(2) input[name=value]",
              "1336650631137737")

    self.Click("css=.Wizard input[value='Add Rule']")
    self.Select("css=.Wizard .Rule:nth-of-type(3) select[name=rule_type]",
                "Mac OS X systems")

    # Click on "Back" button
    self.Click("css=.Wizard input.Back")
    self.WaitUntil(self.IsTextPresent, "Output Processing")

    # Click on "Next" button again and check that all the values that we've just
    # entered remain intact.
    self.Click("css=.Wizard input.Next")
    self.WaitUntil(self.IsTextPresent, "Where to run?")
    self.WaitUntil(
        self.IsElementPresent,
        "css=.Wizard .Rule:nth-of-type(1) input[name=attribute_name]")

    self.assertEqual(
        self.GetSelectedLabel(
            "css=.Wizard .Rule:nth-of-type(1) select[name=rule_type]"),
        "Regular expression match")
    self.assertEqual(
        self.GetValue(
            "css=.Wizard .Rule:nth-of-type(1) input[name=attribute_name]"),
        "System")
    self.assertEqual(
        self.GetValue(
            "css=.Wizard .Rule:nth-of-type(1) input[name=attribute_regex]"),
        "Linux")

    self.assertEqual(
        self.GetSelectedLabel(
            "css=.Wizard .Rule:nth-of-type(2) select[name=rule_type]"),
        "Integer comparison")
    self.assertEqual(
        self.GetValue(
            "css=.Wizard .Rule:nth-of-type(2) input[name=attribute_name]"),
        "Clock")
    self.assertEqual(
        self.GetSelectedLabel(
            "css=.Wizard .Rule:nth-of-type(2) select[name=operator]"),
        "GREATER_THAN")
    self.assertEqual(
        self.GetValue("css=.Wizard .Rule:nth-of-type(2) input[name=value]"),
        "1336650631137737")

    self.assertEqual(
        self.GetSelectedLabel(
            "css=.Wizard .Rule:nth-of-type(3) select[name=rule_type]"),
        "Mac OS X systems")

    # Click on "Next" button
    self.Click("css=.Wizard input.Next")
    self.WaitUntil(self.IsTextPresent, "Review")

    # Check that the arguments summary is present.
    self.assertTrue(self.IsTextPresent("Settings"))
    self.assertTrue(self.IsTextPresent("pathspec"))
    self.assertTrue(self.IsTextPresent("/tmp"))
    self.assertTrue(self.IsTextPresent("depth"))
    self.assertTrue(self.IsTextPresent("42"))

    # Check that output plugins are shown.
    self.assertTrue(self.IsTextPresent("Send an email"))
    self.assertTrue(self.IsTextPresent("test@grrserver.com"))
    self.assertTrue(self.IsTextPresent("Store results in a collection."))

    # Check that rules summary is present.
    self.assertTrue(self.IsTextPresent("Rules"))
    self.assertTrue(self.IsTextPresent("regex_rules"))
    self.assertTrue(self.IsTextPresent("actions"))

    # TODO(user): uncomment if we do accurate check for matching client.
    # self.WaitUntil(self.IsTextPresent,
    #                "Out of 2 checked clients, 1 matched")
    # self.WaitUntil(self.IsTextPresent, "aff4:/C.1%015d" % 1)

    # Click on "Run" button
    self.Click("css=.Wizard input.Next")

    # This should be rejected now and a form request is made.
    self.WaitUntil(self.IsTextPresent,
                   "Create a new approval request")

    # This asks the user "test" (which is us) to approve the request.
    self.Type("css=input[id=acl_approver]", "test")
    self.Type("css=input[id=acl_reason]", "test reason")
    self.Click("acl_dialog_submit")

    # Both the "Request Approval" dialog and the wizard should go away
    # after the submit button is pressed.
    self.WaitUntilNot(self.IsTextPresent, "Create a new approval request")
    self.WaitUntilNot(self.IsTextPresent, "Ok!")

    # Check that the hunt object was actually created
    hunts_root = aff4.FACTORY.Open("aff4:/hunts", token=self.token)
    hunts_list = list(hunts_root.OpenChildren())
    self.assertEqual(len(hunts_list), 1)

    # Check that the hunt was created with a correct flow
    hunt = hunts_list[0]
    self.assertEqual(hunt.state.flow_name, "DownloadDirectory")
    self.assertEqual(hunt.state.args["pathspec"].path, "/tmp")
    self.assertEqual(hunt.state.args["pathspec"].pathtype,
                     rdfvalue.PathSpec.PathType.TSK)
    self.assertEqual(hunt.state.args["depth"], 42)
    self.assertEqual(hunt.state.args["ignore_errors"], True)
    self.assertTrue(("CollectionPlugin", {}) in hunt.state.output_plugins)
    self.assertTrue(("EmailPlugin", {"email": "test@grrserver.com"})
                    in hunt.state.output_plugins)

    # Check that hunt was not started
    self.assertEqual(hunt.state.context.hunt_state, hunt.STATE_STOPPED)

    # Check that the hunt object was actually created
    hunts_root = aff4.FACTORY.Open("aff4:/hunts", token=self.token)
    hunts_list = list(hunts_root.OpenChildren())
    self.assertEqual(len(hunts_list), 1)

    # Check that the hunt was created with a correct flow
    hunt = hunts_list[0]
    self.assertEqual(hunt.state.flow_name, "DownloadDirectory")
    self.assertEqual(hunt.state.args["pathspec"].path, "/tmp")
    self.assertEqual(hunt.state.args["pathspec"].pathtype,
                     rdfvalue.PathSpec.PathType.TSK)
    self.assertEqual(hunt.state.args["depth"], 42)
    self.assertEqual(hunt.state.args["ignore_errors"], True)

    # TODO(user): is readonly access to foreman restricted?
    with self.ACLChecksDisabled():
      hunt_rules = self.FindForemanRules(hunt, token=self.token)
    self.assertEquals(len(hunt_rules), 0)

    # Run the hunt.
    with self.ACLChecksDisabled():
      hunt = aff4.FACTORY.Open(hunt.urn, mode="rw", token=self.token)
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
