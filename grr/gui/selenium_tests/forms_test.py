#!/usr/bin/env python
"""Tests for the UI forms."""


import unittest
from grr.gui import gui_test_lib
from grr.lib import flags
from grr.lib.rdfvalues import structs as rdf_structs
from grr.proto import tests_pb2
from grr.server import flow


class DefaultArgsTestFlowArgs(rdf_structs.RDFProtoStruct):
  protobuf = tests_pb2.DefaultArgsTestFlowArgs


class DefaultArgsTestFlow(flow.GRRFlow):
  args_type = DefaultArgsTestFlowArgs
  category = "/Tests/"
  behaviours = flow.GRRFlow.behaviours + "BASIC"


class TestForms(gui_test_lib.GRRSeleniumTest):
  """Tests for NavigatorView (left side bar)."""

  def testControlsWithoutDefaultValuesAreCorrectlyDisplayed(self):
    # Open the "new hunt" form and select the DefaultArgsTestFlow.
    self.Open("/#main=ManageHunts")
    self.Click("css=button[name=NewHunt]")

    self.Click("css=#_Tests > i.jstree-icon")
    self.Click("link=DefaultArgsTestFlow")

    self.WaitUntil(self.IsTextPresent, "String value")

    # Check that shown default values of the controls are just default
    # values of the corresponding types.
    self.WaitUntilEqual("", self.GetValue, "css=grr-new-hunt-wizard-form "
                        ".form-group:has(label:contains('String value')) input")
    self.WaitUntilEqual("0", self.GetValue, "css=grr-new-hunt-wizard-form "
                        ".form-group:has(label:contains('Int value')) input")
    self.WaitUntil(
        self.IsElementPresent, "css=grr-new-hunt-wizard-form "
        ".form-group:has(label:contains('Bool value')) input:not(:checked)")
    self.WaitUntil(self.IsElementPresent, "css=grr-new-hunt-wizard-form "
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
    self.WaitUntil(self.IsElementPresent, "css=grr-new-hunt-wizard-form "
                   ".form-group:has(label:contains('Bool value with default')) "
                   "input:checked")
    self.WaitUntil(
        self.IsElementPresent, "css=grr-new-hunt-wizard-form "
        ".form-group:has(label:contains('Enum value with default')) select "
        "option:selected(label='OPTION_2 (default)')")


def main(argv):
  del argv  # Unused.
  # Run the full test suite
  unittest.main()


if __name__ == "__main__":
  flags.StartMain(main)
