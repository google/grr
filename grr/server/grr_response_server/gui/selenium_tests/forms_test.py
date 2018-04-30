#!/usr/bin/env python
# -*- mode: python; encoding: utf-8 -*-
"""Tests for the UI forms."""

import unittest
from grr.lib import flags
from grr.lib.rdfvalues import structs as rdf_structs
from grr_response_proto import tests_pb2
from grr.server.grr_response_server import flow
from grr.server.grr_response_server.flows.general import file_finder as flows_file_finder
from grr.server.grr_response_server.gui import gui_test_lib
from grr.test_lib import db_test_lib


class DefaultArgsTestFlowArgs(rdf_structs.RDFProtoStruct):
  protobuf = tests_pb2.DefaultArgsTestFlowArgs


class DefaultArgsTestFlow(flow.GRRFlow):
  args_type = DefaultArgsTestFlowArgs
  category = "/Tests/"
  behaviours = flow.GRRFlow.behaviours + "BASIC"


@db_test_lib.DualDBTest
class TestForms(gui_test_lib.GRRSeleniumTest):
  """Tests basic forms rendering."""

  def testControlsWithoutDefaultValuesAreCorrectlyDisplayed(self):
    # Open the "new hunt" form and select the DefaultArgsTestFlow.
    self.Open("/#main=ManageHunts")
    self.Click("css=button[name=NewHunt]")

    self.Click("css=#_Tests > i.jstree-icon")
    self.Click("link=DefaultArgsTestFlow")

    self.WaitUntil(self.IsTextPresent, "String value")

    # Check that shown default values of the controls are just default
    # values of the corresponding types.
    self.WaitUntilEqual(
        "", self.GetValue, "css=grr-new-hunt-wizard-form "
        ".form-group:has(label:contains('String value')) input")
    self.WaitUntilEqual(
        "0", self.GetValue, "css=grr-new-hunt-wizard-form "
        ".form-group:has(label:contains('Int value')) input")
    self.WaitUntil(
        self.IsElementPresent, "css=grr-new-hunt-wizard-form "
        ".form-group:has(label:contains('Bool value')) input:not(:checked)")
    self.WaitUntil(
        self.IsElementPresent, "css=grr-new-hunt-wizard-form "
        ".form-group:has(label:contains('Enum value')) select "
        "option:selected(label='OPTION_1 (default)')")

  def testControlsWithDefaultValuesAreCorrectlyDisplayed(self):
    # Open the "new hunt" form and select the DefaultArgsTestFlow.
    self.Open("/#main=ManageHunts")
    self.Click("css=button[name=NewHunt]")

    self.Click("css=#_Tests > i.jstree-icon")
    self.Click("link=DefaultArgsTestFlow")

    self.WaitUntil(self.IsTextPresent, "String value")

    # Check that shown default values of the controls are the default values
    # that we specified in the RDFValue definition.
    self.WaitUntilEqual(
        "default string", self.GetValue, "css=grr-new-hunt-wizard-form "
        ".form-group:has(label:contains('String value with default')) input")
    self.WaitUntilEqual(
        "42", self.GetValue, "css=grr-new-hunt-wizard-form "
        ".form-group:has(label:contains('Int value with default')) input")
    self.WaitUntil(
        self.IsElementPresent, "css=grr-new-hunt-wizard-form "
        ".form-group:has(label:contains('Bool value with default')) "
        "input:checked")
    self.WaitUntil(
        self.IsElementPresent, "css=grr-new-hunt-wizard-form "
        ".form-group:has(label:contains('Enum value with default')) select "
        "option:selected(label='OPTION_2 (default)')")

  def testFileFinderArgsPathsDocHintIsDisplayed(self):
    self.Open("/#/hunts")

    self.Click("css=button[name=NewHunt]")

    self.Click("css=#_Filesystem > i.jstree-icon")
    self.Click("link=" + flows_file_finder.FileFinder.friendly_name)

    self.WaitUntil(
        self.IsElementPresent, "css=label:contains(Paths) "
        "a[href*='help/investigating-with-grr/flows/"
        "specifying-file-paths.html']")

  def testFileFinderArgsHasOnePathAddedByDefault(self):
    self.Open("/#/hunts")

    self.Click("css=button[name=NewHunt]")

    self.Click("css=#_Filesystem > i.jstree-icon")
    self.Click("link=" + flows_file_finder.FileFinder.friendly_name)

    self.WaitUntil(self.IsElementPresent,
                   "css=input[placeholder*='Type %% for autocompletion']")


class TestFormsValidation(gui_test_lib.GRRSeleniumTest):
  """Tests forms validation in different workflows ."""

  def setUp(self):
    super(TestFormsValidation, self).setUp()
    self.client_urn = self.SetupClient(0)
    self.RequestAndGrantClientApproval(self.client_urn)

  def testLaunchFlowButtonIsDisabledIfFlowArgumentsInvalid(self):
    self.Open("/#/clients/%s/launch-flow" % self.client_urn.Basename())

    self.Click("css=#_Filesystem")
    self.Click("link=" + flows_file_finder.FileFinder.friendly_name)

    # FileFinder's literal match condition has bytes field that should
    # be validated: it shouldn't contain Unicode characters.
    self.Click("css=label:contains('Conditions') ~ * button")
    self.Select("css=label:contains('Condition type') ~ * select",
                "Contents literal match")
    self.Type("css=label:contains('Literal') ~ * input", u"昨夜")

    self.WaitUntil(
        self.IsElementPresent,
        "css=.text-danger:contains('Unicode characters are not "
        "allowed in a byte string')")
    self.WaitUntil(self.IsElementPresent,
                   "css=button:contains('Launch'):disabled")

    self.Type("css=label:contains('Literal') ~ * input", "something safe")

    self.WaitUntilNot(
        self.IsElementPresent,
        "css=.text-danger:contains('Unicode characters are not "
        "allowed in a byte string')")
    self.WaitUntil(self.IsElementPresent,
                   "css=button:contains('Launch'):not(:disabled)")

  def testLaunchButtonInCopyFlowIsDisabledIfArgumentsInvalid(self):
    self.Open("/#/clients/%s/launch-flow" % self.client_urn.Basename())

    # Launch the flow.
    self.Click("css=#_Filesystem")
    self.Click("link=" + flows_file_finder.FileFinder.friendly_name)
    self.Type("css=grr-form-proto-repeated-field:contains('Paths') input",
              "foo/bar")
    self.Click("css=button:contains('Launch')")

    # Open the copy dialog.
    self.Open("/#/clients/%s/flows" % self.client_urn.Basename())
    self.Click("css=tr:contains('%s')" % flows_file_finder.FileFinder.__name__)
    self.Click("css=button[name=copy_flow]")

    # FileFinder's literal match condition has bytes field that should
    # be validated: it shouldn't contain Unicode characters.
    self.Click("css=label:contains('Conditions') ~ * button")
    self.Select("css=label:contains('Condition type') ~ * select",
                "Contents literal match")
    self.Type("css=label:contains('Literal') ~ * input", u"昨夜")

    self.WaitUntil(
        self.IsElementPresent,
        "css=.text-danger:contains('Unicode characters are not "
        "allowed in a byte string')")
    self.WaitUntil(self.IsElementPresent,
                   "css=button:contains('Launch'):disabled")

    self.Type("css=label:contains('Literal') ~ * input", "something safe")

    self.WaitUntilNot(
        self.IsElementPresent,
        "css=.text-danger:contains('Unicode characters are not "
        "allowed in a byte string')")
    self.WaitUntil(self.IsElementPresent,
                   "css=button:contains('Launch'):not(:disabled)")

  def testNextButtonInHuntWizardIsDisabledIfArgumentsInalid(self):
    self.Open("/#/hunts")
    self.Click("css=button[name=NewHunt]")

    self.Click("css=#_Filesystem")
    self.Click("link=" + flows_file_finder.FileFinder.friendly_name)

    # FileFinder's literal match condition has bytes field that should
    # be validated: it shouldn't contain Unicode characters.
    self.Click("css=label:contains('Conditions') ~ * button")
    self.Select("css=label:contains('Condition type') ~ * select",
                "Contents literal match")
    self.Type("css=label:contains('Literal') ~ * input", u"昨夜")

    self.WaitUntil(
        self.IsElementPresent,
        "css=.text-danger:contains('Unicode characters are not "
        "allowed in a byte string')")
    self.WaitUntil(self.IsElementPresent,
                   "css=button:contains('Next'):disabled")

    self.Type("css=label:contains('Literal') ~ * input", "something safe")

    self.WaitUntilNot(
        self.IsElementPresent,
        "css=.text-danger:contains('Unicode characters are not "
        "allowed in a byte string')")
    self.WaitUntil(self.IsElementPresent,
                   "css=button:contains('Next'):not(:disabled)")


def main(argv):
  del argv  # Unused.
  # Run the full test suite
  unittest.main()


if __name__ == "__main__":
  flags.StartMain(main)
