#!/usr/bin/env python
"""Tests for host table in search view."""

import unittest
from grr.gui import gui_test_lib

from grr.lib import flags
from grr.server import aff4


class TestHostTable(gui_test_lib.SearchClientTestBase):
  """Tests the main content view."""

  def testUserLabelIsShownAsBootstrapSuccessLabel(self):
    with aff4.FACTORY.Open(
        "C.0000000000000001", mode="rw", token=self.token) as client:
      client.AddLabel("foo", owner=self.token.username)

    self.Open("/#/search?q=.")

    self.WaitUntil(self.IsVisible, "css=tr:contains('C.0000000000000001') "
                   "span.label-success:contains('foo')")

  def testSystemLabelIsShownAsRegularBootstrapLabel(self):
    with aff4.FACTORY.Open(
        "C.0000000000000001", mode="rw", token=self.token) as client:
      client.AddLabel("bar", owner="GRR")

    self.Open("/#/search?q=.")
    self.WaitUntil(self.IsVisible, "css=tr:contains('C.0000000000000001') "
                   "span.label:not(.label-success):contains('bar')")

  def testLabelButtonIsDisabledByDefault(self):
    self.Open("/#/search?q=.")
    self.WaitUntil(self.IsVisible, "css=button[name=AddLabels][disabled]")

  def testLabelButtonIsEnabledWhenClientIsSelected(self):
    self.Open("/#/search?q=.")

    self.WaitUntil(self.IsVisible, "css=button[name=AddLabels][disabled]")
    self.Click("css=input.client-checkbox[client_id='C.0000000000000001']")
    self.WaitUntilNot(self.IsVisible, "css=button[name=AddLabels][disabled]")

  def testAddClientsLabelsDialogShowsListOfSelectedClients(self):
    self.Open("/#/search?q=.")

    # Select 3 clients and click 'Add Label' button.
    self.Click("css=input.client-checkbox[client_id='C.0000000000000001']")
    self.Click("css=input.client-checkbox[client_id='C.0000000000000003']")
    self.Click("css=input.client-checkbox[client_id='C.0000000000000007']")
    self.Click("css=button[name=AddLabels]:not([disabled])")

    # Check that all 3 client ids are shown in the dialog.
    self.WaitUntil(self.IsVisible, "css=*[name=AddClientsLabelsDialog]:"
                   "contains('C.0000000000000001')")
    self.WaitUntil(self.IsVisible, "css=*[name=AddClientsLabelsDialog]:"
                   "contains('C.0000000000000003')")
    self.WaitUntil(self.IsVisible, "css=*[name=AddClientsLabelsDialog]:"
                   "contains('C.0000000000000007')")

  def testAddClientsLabelsDialogShowsErrorWhenAddingLabelWithComma(self):
    self.Open("/#/search?q=.")

    # Select 1 client and click 'Add Label' button.
    self.Click("css=input.client-checkbox[client_id='C.0000000000000001']")
    self.Click("css=button[name=AddLabels]:not([disabled])")

    # Type label name
    self.Type("css=*[name=AddClientsLabelsDialog] input[name=labelBox]", "a,b")

    # Click proceed and check that error message is displayed and that
    # dialog is not going away.
    self.Click("css=*[name=AddClientsLabelsDialog] button[name=Proceed]")
    self.WaitUntil(self.IsTextPresent, "Label name can only contain")
    self.WaitUntil(self.IsVisible, "css=*[name=AddClientsLabelsDialog]")

  def testLabelIsAppliedCorrectlyViaAddClientsLabelsDialog(self):
    self.Open("/#/search?q=.")

    # Select 1 client and click 'Add Label' button.
    self.Click("css=input.client-checkbox[client_id='C.0000000000000001']")
    self.Click("css=button[name=AddLabels]:not([disabled])")

    # Type label name.
    self.Type("css=*[name=AddClientsLabelsDialog] input[name=labelBox]",
              "issue 42")

    # Click proceed and check that success message is displayed and that
    # proceed button is replaced with close button.
    self.Click("css=*[name=AddClientsLabelsDialog] button[name=Proceed]")
    self.WaitUntil(self.IsTextPresent, "Label was successfully added")
    self.WaitUntilNot(self.IsVisible, "css=*[name=AddClientsLabelsDialog] "
                      "button[name=Proceed]")

    # Click on "Close" button and check that dialog has disappeared.
    self.Click("css=*[name=AddClientsLabelsDialog] button[name=Close]")
    self.WaitUntilNot(self.IsVisible, "css=*[name=AddClientsLabelsDialog]")

    # Check that label has appeared in the clients list.
    self.WaitUntil(self.IsVisible, "css=tr:contains('C.0000000000000001') "
                   "span.label-success:contains('issue 42')")

  def testAppliedLabelBecomesSearchableImmediately(self):
    self.Open("/#/search?q=.")

    # Select 2 clients and click 'Add Label' button.
    self.Click("css=input.client-checkbox[client_id='C.0000000000000001']")
    self.Click("css=input.client-checkbox[client_id='C.0000000000000002']")
    self.Click("css=button[name=AddLabels]:not([disabled])")

    # Type label name.
    self.Type("css=*[name=AddClientsLabelsDialog] input[name=labelBox]",
              "issue 42")

    # Click proceed and check that success message is displayed and that
    # proceed button is replaced with close button.
    self.Click("css=*[name=AddClientsLabelsDialog] button[name=Proceed]")
    self.WaitUntil(self.IsTextPresent, "Label was successfully added")
    self.WaitUntilNot(self.IsVisible, "css=*[name=AddClientsLabelsDialog] "
                      "button[name=Proceed]")

    # Click on "Close" button and check that dialog has disappeared.
    self.Click("css=*[name=AddClientsLabelsDialog] button[name=Close]")
    self.WaitUntilNot(self.IsVisible, "css=*[name=AddClientsLabelsDialog]")

    # Search using the new label and check that the labeled clients are shown.
    self.Open("/#main=HostTable&q=label:\"issue 42\"")
    self.WaitUntil(self.IsTextPresent, "C.0000000000000001")
    self.WaitUntil(self.IsTextPresent, "C.0000000000000002")

    # Now we test if we can remove the label and if the search index is updated.

    # Select 1 client and click 'Remove Label' button.
    self.Click("css=input.client-checkbox[client_id='C.0000000000000001']")
    self.Click("css=button[name=RemoveLabels]:not([disabled])")
    # The label should already be prefilled in the dropdown.
    self.WaitUntil(self.IsTextPresent, "issue 42")

    self.Click("css=*[name=RemoveClientsLabelsDialog] button[name=Proceed]")

    # Open client search with label and check that labeled client is not shown
    # anymore.
    self.Open("/#main=HostTable&q=label:\"issue 42\"")

    self.WaitUntil(self.IsTextPresent, "C.0000000000000002")
    # This client must not be in the results anymore.
    self.assertFalse(self.IsTextPresent("C.0000000000000001"))

  def testSelectionIsPreservedWhenAddClientsLabelsDialogIsCancelled(self):
    self.Open("/#/search?q=.")

    # Select 1 client and click 'Add Label' button.
    self.Click("css=input.client-checkbox[client_id='C.0000000000000001']")
    self.Click("css=button[name=AddLabels]:not([disabled])")

    # Click on "Cancel" button and check that dialog has disappeared.
    self.Click("css=*[name=AddClientsLabelsDialog] button[name=Cancel]")
    self.WaitUntilNot(self.IsVisible, "css=*[name=AddClientsLabelsDialog]")

    # Ensure that checkbox is still checked
    self.WaitUntil(self.IsVisible, "css=input.client-checkbox["
                   "client_id='C.0000000000000001']:checked")

  def testSelectionIsResetWhenLabelIsAppliedViaAddClientsLabelsDialog(self):
    self.Open("/#/search?q=.")

    # Select 1 client and click 'Add Label' button.
    self.Click("css=input.client-checkbox[client_id='C.0000000000000001']")
    self.Click("css=button[name=AddLabels]:not([disabled])")

    # Type label name, click on "Proceed" and "Close" buttons.
    self.Type("css=*[name=AddClientsLabelsDialog] input[name=labelBox]",
              "issue 42")
    self.Click("css=*[name=AddClientsLabelsDialog] button[name=Proceed]")
    self.Click("css=*[name=AddClientsLabelsDialog] button[name=Close]")

    # Ensure that checkbox is not checked anymore.
    self.WaitUntil(self.IsVisible, "css=input.client-checkbox["
                   "client_id='C.0000000000000001']:not(:checked)")

  def testCheckAllCheckboxSelectsAllClients(self):
    self.Open("/#/search?q=.")

    self.WaitUntil(self.IsTextPresent, "C.0000000000000001")

    # Check that checkboxes for certain clients are unchecked.
    self.WaitUntil(self.IsVisible, "css=input.client-checkbox["
                   "client_id='C.0000000000000001']:not(:checked)")
    self.WaitUntil(self.IsVisible, "css=input.client-checkbox["
                   "client_id='C.0000000000000004']:not(:checked)")
    self.WaitUntil(self.IsVisible, "css=input.client-checkbox["
                   "client_id='C.0000000000000007']:not(:checked)")

    # Click on 'check all checkbox'
    self.Click("css=input.client-checkbox.select-all")

    # Check that checkboxes for certain clients are now checked.
    self.WaitUntil(self.IsVisible, "css=input.client-checkbox["
                   "client_id='C.0000000000000001']:checked")
    self.WaitUntil(self.IsVisible, "css=input.client-checkbox["
                   "client_id='C.0000000000000004']:checked")
    self.WaitUntil(self.IsVisible, "css=input.client-checkbox["
                   "client_id='C.0000000000000007']:checked")

    # Click once more on 'check all checkbox'.
    self.Click("css=input.client-checkbox.select-all")

    # Check that checkboxes for certain clients are now again unchecked.
    self.WaitUntil(self.IsVisible, "css=input.client-checkbox["
                   "client_id='C.0000000000000001']:not(:checked)")
    self.WaitUntil(self.IsVisible, "css=input.client-checkbox["
                   "client_id='C.0000000000000004']:not(:checked)")
    self.WaitUntil(self.IsVisible, "css=input.client-checkbox["
                   "client_id='C.0000000000000007']:not(:checked)")

  def testClientsSelectedWithSelectAllAreShownInAddClientsLabelsDialog(self):
    self.Open("/#/search?q=.")

    self.WaitUntil(self.IsTextPresent, "C.0000000000000001")

    # Click on 'check all checkbox'.
    self.Click("css=input.client-checkbox.select-all")

    # Click on 'Apply Label' button.
    self.Click("css=button[name=AddLabels]:not([disabled])")

    # Check that client ids are shown in the dialog.
    self.WaitUntil(self.IsVisible, "css=*[name=AddClientsLabelsDialog]:"
                   "contains('C.0000000000000001')")
    self.WaitUntil(self.IsVisible, "css=*[name=AddClientsLabelsDialog]:"
                   "contains('C.0000000000000004')")
    self.WaitUntil(self.IsVisible, "css=*[name=AddClientsLabelsDialog]:"
                   "contains('C.0000000000000007')")


def main(argv):
  del argv  # Unused.
  # Run the full test suite
  unittest.main()


if __name__ == "__main__":
  flags.StartMain(main)
