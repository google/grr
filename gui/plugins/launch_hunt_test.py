#!/usr/bin/env python
"""Test of "Launch Hunt" wizard."""


from grr.lib import access_control
from grr.lib import aff4
from grr.lib import data_store
from grr.lib import rdfvalue
from grr.lib import test_lib


class TestLaunchHuntWizard(test_lib.GRRSeleniumTest):
  """Test the Cron view GUI."""

  @staticmethod
  def FindForemanRules(hunt, token):
    fman = aff4.FACTORY.Open("aff4:/foreman", mode="r", token=token)
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
    super(TestLaunchHuntWizard, self).setUp()
    self.CreateHuntFixture()

  def testLaunchHuntWizardWithoutACLChecks(self):
    """Test that we can launch a hunt through the wizard."""
    # Create a Foreman with an empty rule set
    self.foreman = aff4.FACTORY.Create("aff4:/foreman", "GRRForeman",
                                       mode="rw", token=self.token)
    self.foreman.Set(self.foreman.Schema.RULES())
    self.foreman.Close()

    # Open up and click on View Hunts.
    sel = self.selenium
    sel.open("/")
    self.WaitUntil(sel.is_element_present, "client_query")
    self.WaitUntil(sel.is_element_present, "css=a[grrtarget=ManageHunts]")
    sel.click("css=a[grrtarget=ManageHunts]")
    self.WaitUntil(sel.is_element_present, "css=button[name=LaunchHunt]")

    # Open up "Launch Hunt" wizard
    sel.click("css=button[name=LaunchHunt]")
    self.WaitUntil(sel.is_text_present, "Step 1. Select And Configure The Flow")

    # Click on Filesystem item in flows list
    self.WaitUntil(sel.is_element_present, "css=#_Filesystem > ins.jstree-icon")
    sel.click("css=#_Filesystem > ins.jstree-icon")

    # Click on DownloadDirectory item in Filesystem flows list
    self.WaitUntil(sel.is_element_present,
                   "link=DownloadDirectory")
    sel.click("link=DownloadDirectory")

    # Wait for flow configuration form to be rendered (just wait for first
    # input field).
    self.WaitUntil(sel.is_element_present,
                   "css=.Wizard .HuntFormBody input[name=pathspec_path]")

    # Change "path", "pathtype", "depth" and "ignore_errors" values
    sel.type("css=.Wizard .HuntFormBody input[name=pathspec_path]", "/tmp")
    sel.select("css=.Wizard .HuntFormBody select[name=pathspec_pathtype]",
               "label=TSK")
    sel.type("css=.Wizard .HuntFormBody input[name=depth]", "42")
    sel.click("css=.Wizard .HuntFormBody input[name=ignore_errors]")

    # Click on "Next" button
    sel.click("css=.Wizard input.Next")
    self.WaitUntil(sel.is_text_present, "Step 2. Configure Hunt Rules")

    # Click on "Back" button and check that all the values in the form
    # remain intact.
    sel.click("css=.Wizard input.Back")
    self.WaitUntil(sel.is_element_present,
                   "css=.Wizard .HuntFormBody input[name=pathspec_path]")
    self.assertEqual(
        "/tmp", sel.get_value(
            "css=.Wizard .HuntFormBody input[name=pathspec_path]"))
    self.assertEqual(
        "TSK",
        sel.get_selected_label(
            "css=.Wizard .HuntFormBody select[name=pathspec_pathtype]"))
    self.assertEqual(
        "42",
        sel.get_value("css=.Wizard .HuntFormBody input[name=depth]"))
    self.assertTrue(
        sel.is_checked("css=.Wizard .HuntFormBody input[name=ignore_errors]"))

    # Click on "Next" button again
    sel.click("css=.Wizard input.Next")
    self.WaitUntil(sel.is_text_present, "Step 2. Configure Hunt Rules")

    # Create 3 foreman rules
    self.WaitUntil(
        sel.is_element_present,
        "css=.Wizard .Rule:nth-of-type(1) input[name=attribute_name]")
    sel.type("css=.Wizard .Rule:nth-of-type(1) input[name=attribute_name]",
             "System")
    sel.type("css=.Wizard .Rule:nth-of-type(1) input[name=attribute_regex]",
             "Linux")

    sel.click("css=.Wizard input[value='Add Rule']")
    sel.select("css=.Wizard .Rule:nth-of-type(2) select[name=rule_type]",
               "label=ForemanAttributeInteger")

    sel.type("css=.Wizard .Rule:nth-of-type(2) input[name=attribute_name]",
             "Clock")
    sel.select("css=.Wizard .Rule:nth-of-type(2) select[name=operator]",
               "label=GREATER_THAN")
    sel.type("css=.Wizard .Rule:nth-of-type(2) input[name=value]",
             "1336650631137737")

    sel.click("css=.Wizard input[value='Add Rule']")
    sel.select("css=.Wizard .Rule:nth-of-type(3) select[name=rule_type]",
               "label=MatchDarwin")

    # Click on "Back" button
    sel.click("css=.Wizard input.Back")
    self.WaitUntil(sel.is_text_present, "Step 1. Select And Configure The Flow")

    # Click on "Next" button again and check that all the values that we've just
    # entered remain intact.
    sel.click("css=.Wizard input.Next")
    self.WaitUntil(sel.is_text_present, "Step 2. Configure Hunt Rules")
    self.WaitUntil(
        sel.is_element_present,
        "css=.Wizard .Rule:nth-of-type(1) input[name=attribute_name]")

    self.assertEqual(
        sel.get_selected_label(
            "css=.Wizard .Rule:nth-of-type(1) select[name=rule_type]"),
        "ForemanAttributeRegex")
    self.assertEqual(
        sel.get_value(
            "css=.Wizard .Rule:nth-of-type(1) input[name=attribute_name]"),
        "System")
    self.assertEqual(
        sel.get_value(
            "css=.Wizard .Rule:nth-of-type(1) input[name=attribute_regex]"),
        "Linux")

    self.assertEqual(
        sel.get_selected_label(
            "css=.Wizard .Rule:nth-of-type(2) select[name=rule_type]"),
        "ForemanAttributeInteger")
    self.assertEqual(
        sel.get_value(
            "css=.Wizard .Rule:nth-of-type(2) input[name=attribute_name]"),
        "Clock")
    self.assertEqual(
        sel.get_selected_label(
            "css=.Wizard .Rule:nth-of-type(2) select[name=operator]"),
        "GREATER_THAN")
    self.assertEqual(
        sel.get_value("css=.Wizard .Rule:nth-of-type(2) input[name=value]"),
        "1336650631137737")

    self.assertEqual(
        sel.get_selected_label(
            "css=.Wizard .Rule:nth-of-type(3) select[name=rule_type]"),
        "MatchDarwin")

    # Click on "Next" button
    sel.click("css=.Wizard input.Next")
    self.WaitUntil(sel.is_text_present,
                   "Step 3. Review The Hunt")

    # TODO(user): uncomment if we do accurate check for matching client.
    # self.WaitUntil(sel.is_text_present,
    #                "Out of 2 checked clients, 1 matched")
    # self.WaitUntil(sel.is_text_present, "aff4:/C.1%015d" % 1)

    # Click on "Run" button
    sel.click("css=.Wizard input.Next")
    self.WaitUntil(sel.is_text_present, "Hunt was scheduled!")

    # Click on "Done" button, ensure that wizard is closed after that
    sel.click("css=.Wizard input.Next")
    self.WaitUntil(sel.is_text_present, "Hunt was scheduled")
    self.assertFalse(sel.is_text_present("Launch New Hunt"))

    # Check that the hunt object was actually created
    hunts_root = aff4.FACTORY.Open("aff4:/hunts", token=self.token)
    hunts_list = list(hunts_root.OpenChildren())
    self.assertEqual(len(hunts_list), 1)

    # Check that the hunt was created with a correct flow
    hunt = hunts_list[0]
    flow = hunt.GetFlowObj()
    self.assertEqual(flow.flow_name, "DownloadDirectory")
    self.assertEqual(flow.args["pathspec"].path, "/tmp")
    self.assertEqual(flow.args["pathspec"].pathtype,
                     rdfvalue.RDFPathSpec.Enum("TSK"))
    self.assertEqual(flow.args["depth"], 42)
    self.assertEqual(flow.args["ignore_errors"], True)

    # Check that the hunt was created with correct rules
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
                      rdfvalue.ForemanAttributeInteger.Enum("GREATER_THAN"))
    self.assertEquals(hunt_rules[0].integer_rules[0].value, 1336650631137737)

  def testLaunchHuntWizardWithACLChecks(self):
    # Create a Foreman with an empty rule set
    self.foreman = aff4.FACTORY.Create("aff4:/foreman", "GRRForeman",
                                       mode="rw", token=self.token)
    self.foreman.Set(self.foreman.Schema.RULES())
    self.foreman.Close()

    self.InstallACLChecks()

    # Open up and click on View Hunts.
    sel = self.selenium
    sel.open("/")
    self.WaitUntil(sel.is_element_present, "client_query")
    self.WaitUntil(sel.is_element_present, "css=a[grrtarget=ManageHunts]")
    sel.click("css=a[grrtarget=ManageHunts]")
    self.WaitUntil(sel.is_element_present, "css=button[name=LaunchHunt]")

    # Open up "Launch Hunt" wizard
    sel.click("css=button[name=LaunchHunt]")
    self.WaitUntil(sel.is_text_present, "Step 1. Select And Configure The Flow")

    # Click on Filesystem item in flows list
    self.WaitUntil(sel.is_element_present, "css=#_Filesystem > ins.jstree-icon")
    sel.click("css=#_Filesystem > ins.jstree-icon")

    # Click on DownloadDirectory item in Filesystem flows list
    self.WaitUntil(sel.is_element_present,
                   "link=DownloadDirectory")
    sel.click("link=DownloadDirectory")

    # Wait for flow configuration form to be rendered (just wait for first
    # input field).
    self.WaitUntil(sel.is_element_present,
                   "css=.Wizard .HuntFormBody input[name=pathspec_path]")

    # Change "path", "pathtype", "depth" and "ignore_errors" values
    sel.type("css=.Wizard .HuntFormBody input[name=pathspec_path]", "/tmp")
    sel.select("css=.Wizard .HuntFormBody select[name=pathspec_pathtype]",
               "label=TSK")
    sel.type("css=.Wizard .HuntFormBody input[name=depth]", "42")
    sel.click("css=.Wizard .HuntFormBody input[name=ignore_errors]")

    # Click on "Next" button
    sel.click("css=.Wizard input.Next")
    self.WaitUntil(sel.is_text_present, "Step 2. Configure Hunt Rules")

    # Create 2 foreman rules
    self.WaitUntil(
        sel.is_element_present,
        "css=.Wizard .Rule:nth-of-type(1) input[name=attribute_name]")
    sel.type("css=.Wizard .Rule:nth-of-type(1) input[name=attribute_name]",
             "System")
    sel.type("css=.Wizard .Rule:nth-of-type(1) input[name=attribute_regex]",
             "Linux")

    sel.click("css=.Wizard input[value='Add Rule']")
    sel.select("css=.Wizard .Rule:nth-of-type(2) select[name=rule_type]",
               "label=ForemanAttributeInteger")

    sel.type("css=.Wizard .Rule:nth-of-type(2) input[name=attribute_name]",
             "Clock")
    sel.select("css=.Wizard .Rule:nth-of-type(2) select[name=operator]",
               "label=GREATER_THAN")
    sel.type("css=.Wizard .Rule:nth-of-type(2) input[name=value]",
             "1336650631137737")

    # Click on "Next" button
    sel.click("css=.Wizard input.Next")
    self.WaitUntil(sel.is_text_present,
                   "Step 3. Review The Hunt")

    # TODO(user): uncomment if we do accurate check for matching client.
    # self.WaitUntil(sel.is_text_present,
    #                "Out of 2 checked clients, 1 matched")
    # self.WaitUntil(sel.is_text_present, "aff4:/C.1%015d" % 1)

    # Click on "Run" button
    sel.click("css=.Wizard input.Next")

    # This should be rejected now and a form request is made.
    self.WaitUntil(sel.is_element_present,
                   "css=h3:contains('Create a new approval')")

    # This asks the user "test" (which is us) to approve the request.
    sel.type("css=input[id=acl_approver]", "test")
    sel.type("css=input[id=acl_reason]", "test reason")
    sel.click("acl_dialog_submit")

    # Both the "Request Approval" dialog and the wizard should go away
    # after the submit button is pressed.
    self.WaitUntil(lambda x: not sel.is_element_present(x),
                   "css=h3:contains('Create a new approval')")
    self.WaitUntil(lambda x: not sel.is_text_present(x),
                   "Done")

    # Check that the hunt object was actually created
    hunts_root = aff4.FACTORY.Open("aff4:/hunts", token=self.token)
    hunts_list = list(hunts_root.OpenChildren())
    self.assertEqual(len(hunts_list), 1)

    # Check that the hunt was created with a correct flow
    hunt = hunts_list[0]
    flow = hunt.GetFlowObj()
    self.assertEqual(flow.flow_name, "DownloadDirectory")
    self.assertEqual(flow.args["pathspec"].path, "/tmp")
    self.assertEqual(flow.args["pathspec"].pathtype,
                     rdfvalue.RDFPathSpec.Enum("TSK"))
    self.assertEqual(flow.args["depth"], 42)
    self.assertEqual(flow.args["ignore_errors"], True)

    # Check that hunt was not started
    self.assertEqual(hunt.Get(hunt.Schema.STATE), hunt.STATE_STOPPED)

    # Check that there are no foreman rules installed for this hunt
    self.UninstallACLChecks()

    hunt_rules = self.FindForemanRules(hunt, token=self.token)
    self.assertEquals(len(hunt_rules), 0)
