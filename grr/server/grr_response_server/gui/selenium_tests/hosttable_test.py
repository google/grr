#!/usr/bin/env python
"""Tests for host table in search view."""
from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals


from grr_response_core.lib import flags

from grr_response_server.gui import gui_test_lib
from grr.test_lib import db_test_lib
from grr.test_lib import test_lib


@db_test_lib.DualDBTest
class TestHostTable(gui_test_lib.SearchClientTestBase):
  """Tests the main content view."""

  def setUp(self):
    super(TestHostTable, self).setUp()
    self.client_ids = [u.Basename() for u in self.SetupClients(10)]

  def testUserLabelIsShownAsBootstrapSuccessLabel(self):
    self.AddClientLabel(self.client_ids[0], self.token.username, u"foo")

    self.Open("/#/search?q=.")

    self.WaitUntil(
        self.IsVisible, "css=tr:contains('%s') "
        "span.label-success:contains('foo')" % self.client_ids[0])

  def testSystemLabelIsShownAsRegularBootstrapLabel(self):
    self.AddClientLabel(self.client_ids[0], u"GRR", u"bar")

    self.Open("/#/search?q=.")
    self.WaitUntil(
        self.IsVisible, "css=tr:contains('%s') "
        "span.label:not(.label-success):contains('bar')" % self.client_ids[0])

  def testLabelButtonIsDisabledByDefault(self):
    self.Open("/#/search?q=.")
    self.WaitUntil(self.IsVisible, "css=button[name=AddLabels][disabled]")

  def testLabelButtonIsEnabledWhenClientIsSelected(self):
    self.Open("/#/search?q=.")

    self.WaitUntil(self.IsVisible, "css=button[name=AddLabels][disabled]")
    self.Click("css=input.client-checkbox[client_id='%s']" % self.client_ids[0])
    self.WaitUntilNot(self.IsVisible, "css=button[name=AddLabels][disabled]")

  def testAddClientsLabelsDialogShowsListOfSelectedClients(self):
    self.Open("/#/search?q=.")

    # Select 3 clients and click 'Add Label' button.
    self.Click("css=input.client-checkbox[client_id='%s']" % self.client_ids[0])
    self.Click("css=input.client-checkbox[client_id='%s']" % self.client_ids[2])
    self.Click("css=input.client-checkbox[client_id='%s']" % self.client_ids[6])
    self.Click("css=button[name=AddLabels]:not([disabled])")

    # Check that all 3 client ids are shown in the dialog.
    self.WaitUntil(
        self.IsVisible, "css=*[name=AddClientsLabelsDialog]:"
        "contains('%s')" % self.client_ids[0])
    self.WaitUntil(
        self.IsVisible, "css=*[name=AddClientsLabelsDialog]:"
        "contains('%s')" % self.client_ids[2])
    self.WaitUntil(
        self.IsVisible, "css=*[name=AddClientsLabelsDialog]:"
        "contains('%s')" % self.client_ids[6])

  def testAddClientsLabelsDialogShowsErrorWhenAddingLabelWithComma(self):
    self.Open("/#/search?q=.")

    # Select 1 client and click 'Add Label' button.
    self.Click("css=input.client-checkbox[client_id='%s']" % self.client_ids[0])
    self.Click("css=button[name=AddLabels]:not([disabled])")

    # Type label name
    self.Type("css=*[name=AddClientsLabelsDialog] input[name=labelBox]", "a,b")

    # Click proceed and check that error message is displayed and that
    # dialog is not going away.
    # TODO(user): convert to Bad Request (400) status code.
    with self.DisableHttpErrorChecks():
      self.Click("css=*[name=AddClientsLabelsDialog] button[name=Proceed]")
      self.WaitUntil(self.IsTextPresent, "Label name can only contain")
      self.WaitUntil(self.IsVisible, "css=*[name=AddClientsLabelsDialog]")

  def testLabelIsAppliedCorrectlyViaAddClientsLabelsDialog(self):
    self.Open("/#/search?q=.")

    # Select 1 client and click 'Add Label' button.
    self.Click("css=input.client-checkbox[client_id='%s']" % self.client_ids[0])
    self.Click("css=button[name=AddLabels]:not([disabled])")

    # Type label name.
    self.Type("css=*[name=AddClientsLabelsDialog] input[name=labelBox]",
              "issue 42")

    # Click proceed and check that success message is displayed and that
    # proceed button is replaced with close button.
    self.Click("css=*[name=AddClientsLabelsDialog] button[name=Proceed]")
    self.WaitUntil(self.IsTextPresent, "Label was successfully added")
    self.WaitUntilNot(
        self.IsVisible, "css=*[name=AddClientsLabelsDialog] "
        "button[name=Proceed]")

    # Click on "Close" button and check that dialog has disappeared.
    self.Click("css=*[name=AddClientsLabelsDialog] button[name=Close]")
    self.WaitUntilNot(self.IsVisible, "css=*[name=AddClientsLabelsDialog]")

    # Check that label has appeared in the clients list.
    self.WaitUntil(
        self.IsVisible, "css=tr:contains('%s') "
        "span.label-success:contains('issue 42')" % self.client_ids[0])

  def testAppliedLabelBecomesSearchableImmediately(self):
    self.Open("/#/search?q=.")

    # Select 2 clients and click 'Add Label' button.
    self.Click("css=input.client-checkbox[client_id='%s']" % self.client_ids[0])
    self.Click("css=input.client-checkbox[client_id='%s']" % self.client_ids[1])
    self.Click("css=button[name=AddLabels]:not([disabled])")

    # Type label name.
    self.Type("css=*[name=AddClientsLabelsDialog] input[name=labelBox]",
              "issue 42")

    # Click proceed and check that success message is displayed and that
    # proceed button is replaced with close button.
    self.Click("css=*[name=AddClientsLabelsDialog] button[name=Proceed]")
    self.WaitUntil(self.IsTextPresent, "Label was successfully added")
    self.WaitUntilNot(
        self.IsVisible, "css=*[name=AddClientsLabelsDialog] "
        "button[name=Proceed]")

    # Click on "Close" button and check that dialog has disappeared.
    self.Click("css=*[name=AddClientsLabelsDialog] button[name=Close]")
    self.WaitUntilNot(self.IsVisible, "css=*[name=AddClientsLabelsDialog]")

    # Search using the new label and check that the labeled clients are shown.
    self.Open("/#main=HostTable&q=label:\"issue 42\"")
    self.WaitUntil(self.IsTextPresent, "%s" % self.client_ids[0])
    self.WaitUntil(self.IsTextPresent, "%s" % self.client_ids[1])

    # Now we test if we can remove the label and if the search index is updated.

    # Select 1 client and click 'Remove Label' button.
    self.Click("css=input.client-checkbox[client_id='%s']" % self.client_ids[0])
    self.Click("css=button[name=RemoveLabels]:not([disabled])")
    # The label should already be prefilled in the dropdown.
    self.WaitUntil(self.IsTextPresent, "issue 42")

    self.Click("css=*[name=RemoveClientsLabelsDialog] button[name=Proceed]")

    # Open client search with label and check that labeled client is not shown
    # anymore.
    self.Open("/#main=HostTable&q=label:\"issue 42\"")

    self.WaitUntil(self.IsTextPresent, self.client_ids[1])
    # This client must not be in the results anymore.
    self.assertFalse(self.IsTextPresent(self.client_ids[0]))

  def testSelectionIsPreservedWhenAddClientsLabelsDialogIsCancelled(self):
    self.Open("/#/search?q=.")

    # Select 1 client and click 'Add Label' button.
    self.Click("css=input.client-checkbox[client_id='%s']" % self.client_ids[0])
    self.Click("css=button[name=AddLabels]:not([disabled])")

    # Click on "Cancel" button and check that dialog has disappeared.
    self.Click("css=*[name=AddClientsLabelsDialog] button[name=Cancel]")
    self.WaitUntilNot(self.IsVisible, "css=*[name=AddClientsLabelsDialog]")

    # Ensure that checkbox is still checked
    self.WaitUntil(
        self.IsVisible, "css=input.client-checkbox["
        "client_id='%s']:checked" % self.client_ids[0])

  def testSelectionIsResetWhenLabelIsAppliedViaAddClientsLabelsDialog(self):
    self.Open("/#/search?q=.")

    # Select 1 client and click 'Add Label' button.
    self.Click("css=input.client-checkbox[client_id='%s']" % self.client_ids[0])
    self.Click("css=button[name=AddLabels]:not([disabled])")

    # Type label name, click on "Proceed" and "Close" buttons.
    self.Type("css=*[name=AddClientsLabelsDialog] input[name=labelBox]",
              "issue 42")
    self.Click("css=*[name=AddClientsLabelsDialog] button[name=Proceed]")
    self.Click("css=*[name=AddClientsLabelsDialog] button[name=Close]")

    # Ensure that checkbox is not checked anymore.
    self.WaitUntil(
        self.IsVisible, "css=input.client-checkbox["
        "client_id='%s']:not(:checked)" % self.client_ids[0])

  def testCheckAllCheckboxSelectsAllClients(self):
    self.Open("/#/search?q=.")

    self.WaitUntil(self.IsTextPresent, self.client_ids[0])

    # Check that checkboxes for certain clients are unchecked.
    self.WaitUntil(
        self.IsVisible, "css=input.client-checkbox["
        "client_id='%s']:not(:checked)" % self.client_ids[0])
    self.WaitUntil(
        self.IsVisible, "css=input.client-checkbox["
        "client_id='%s']:not(:checked)" % self.client_ids[3])
    self.WaitUntil(
        self.IsVisible, "css=input.client-checkbox["
        "client_id='%s']:not(:checked)" % self.client_ids[6])

    # Click on 'check all checkbox'
    self.Click("css=input.client-checkbox.select-all")

    # Check that checkboxes for certain clients are now checked.
    self.WaitUntil(
        self.IsVisible, "css=input.client-checkbox["
        "client_id='%s']:checked" % self.client_ids[0])
    self.WaitUntil(
        self.IsVisible, "css=input.client-checkbox["
        "client_id='%s']:checked" % self.client_ids[3])
    self.WaitUntil(
        self.IsVisible, "css=input.client-checkbox["
        "client_id='%s']:checked" % self.client_ids[6])

    # Click once more on 'check all checkbox'.
    self.Click("css=input.client-checkbox.select-all")

    # Check that checkboxes for certain clients are now again unchecked.
    self.WaitUntil(
        self.IsVisible, "css=input.client-checkbox["
        "client_id='%s']:not(:checked)" % self.client_ids[0])
    self.WaitUntil(
        self.IsVisible, "css=input.client-checkbox["
        "client_id='%s']:not(:checked)" % self.client_ids[3])
    self.WaitUntil(
        self.IsVisible, "css=input.client-checkbox["
        "client_id='%s']:not(:checked)" % self.client_ids[6])

  def testClientsSelectedWithSelectAllAreShownInAddClientsLabelsDialog(self):
    self.Open("/#/search?q=.")

    self.WaitUntil(self.IsTextPresent, self.client_ids[0])

    # Click on 'check all checkbox'.
    self.Click("css=input.client-checkbox.select-all")

    # Click on 'Apply Label' button.
    self.Click("css=button[name=AddLabels]:not([disabled])")

    # Check that client ids are shown in the dialog.
    self.WaitUntil(
        self.IsVisible, "css=*[name=AddClientsLabelsDialog]:"
        "contains('%s')" % self.client_ids[0])
    self.WaitUntil(
        self.IsVisible, "css=*[name=AddClientsLabelsDialog]:"
        "contains('%s')" % self.client_ids[3])
    self.WaitUntil(
        self.IsVisible, "css=*[name=AddClientsLabelsDialog]:"
        "contains('%s')" % self.client_ids[6])


if __name__ == "__main__":
  flags.StartMain(test_lib.main)
