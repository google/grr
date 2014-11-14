#!/usr/bin/env python
"""Tests for the UI forms."""


from grr.gui import runtests_test

# We have to import test_lib first to properly initialize aff4 and rdfvalues.
# pylint: disable=g-bad-import-order
from grr.lib import test_lib
# pylint: enable=g-bad-import-order

from grr.lib import flags
from grr.lib import flow
from grr.lib import rdfvalue
from grr.proto import tests_pb2


class DefaultArgsTestFlowArgs(rdfvalue.RDFProtoStruct):
  protobuf = tests_pb2.DefaultArgsTestFlowArgs


class DefaultArgsTestFlow(flow.GRRFlow):
  args_type = DefaultArgsTestFlowArgs
  category = "/Tests/"
  behaviours = flow.GRRFlow.behaviours + "BASIC"


class TestForms(test_lib.GRRSeleniumTest):
  """Tests for NavigatorView (left side bar)."""

  def testControlsWithoutDefaultValuesAreCorrectlyDisplayed(self):
    # Open the "new hunt" form and select the DefaultArgsTestFlow.
    self.Open("/#main=ManageHunts")
    self.Click("css=button[name=NewHunt]")
    self.Click("css=li[path='/Tests'] > a")
    self.Click("css=li[path='/Tests/DefaultArgsTestFlow'] > a")
    self.WaitUntil(self.IsTextPresent, "String value")

    # Check that shown default values of the controls are just default
    # values of the corresponding types.
    self.WaitUntilEqual(
        "", self.GetValue, "css=#args-string_value.unset")
    self.WaitUntilEqual(
        "0", self.GetValue, "css=#args-int_value.unset")
    self.WaitUntil(self.IsElementPresent,
                   "css=#args-bool_value.unset:not(:checked)")
    self.WaitUntilEqual(
        "OPTION_1", self.GetValue, "css=#args-enum_value.unset")

  def testControlsWithDefaultValuesAreCorrectlyDisplayed(self):
    # Open the "new hunt" form and select the DefaultArgsTestFlow.
    self.Open("/#main=ManageHunts")
    self.Click("css=button[name=NewHunt]")
    self.Click("css=li[path='/Tests'] > a")
    self.Click("css=li[path='/Tests/DefaultArgsTestFlow'] > a")
    self.WaitUntil(self.IsTextPresent, "String value")

    # Check that shown default values of the controls are the default values
    # that we specified in the RDFValue definition.
    self.WaitUntilEqual(
        "default string",
        self.GetValue, "css=#args-string_value_with_default.unset")
    self.WaitUntilEqual(
        "42",
        self.GetValue, "css=#args-int_value_with_default.unset")
    self.WaitUntil(
        self.IsElementPresent,
        "css=#args-bool_value_with_default.unset:checked")
    self.WaitUntilEqual(
        "OPTION_2",
        self.GetValue, "css=#args-enum_value_with_default.unset")


def main(argv):
  # Run the full test suite
  runtests_test.SeleniumTestProgram(argv=argv)

if __name__ == "__main__":
  flags.StartMain(main)
