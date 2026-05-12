#!/usr/bin/env python
from absl import app
from grr_response_server import data_store
from grr_response_server.gui import gui_test_lib
from grr.test_lib import test_lib


class ClientTest(gui_test_lib.GRRSeleniumTest):

  def testLabelsAreShownAndCanBeRemoved(self):
    client_id = self.SetupClient(0)
    self.AddClientLabel(client_id, self.test_username, "foo")
    self.AddClientLabel(client_id, self.test_username, "bar")

    self.Open(f"/clients/{client_id}")
    self.WaitUntil(self.IsTextPresent, client_id)
    self.WaitUntil(self.IsTextPresent, "foo")
    self.WaitUntil(self.IsTextPresent, "bar")

    self.Click("xpath=//mat-chip[contains(., 'foo')]//*[@matchipremove]")
    self.WaitUntil(
        self.IsElementPresent, "xpath=//button[contains(., 'Remove')]"
    )
    self.Click("xpath=//button[contains(., 'Remove')]")

    self.WaitUntilNot(self.IsTextPresent, "foo")
    self.assertEqual(
        ["bar"],
        [l.name for l in data_store.REL_DB.ReadClientLabels(client_id)],
    )

  def testClientLabelCanBeAdded(self):
    client_id = self.SetupClient(0)

    self.Open(f"/clients/{client_id}")
    self.WaitUntil(self.IsTextPresent, client_id)

    self.Click("xpath=//button[contains(., 'Add label')]")
    self.WaitUntil(self.IsElementPresent, "css=input")
    self.Type("css=input", "new-test-label")
    self.WaitUntil(
        self.IsElementPresent,
        "xpath=//mat-option[contains(., 'Add new label')]",
    )
    self.Click("xpath=//mat-option[contains(., 'Add new label')]")
    self.Click("xpath=//mat-dialog-actions//button[contains(., 'Add')]")

    self.WaitUntil(self.IsTextPresent, "new-test-label")
    self.assertEqual(
        ["new-test-label"],
        [l.name for l in data_store.REL_DB.ReadClientLabels(client_id)],
    )

  def testCanStartFlow(self):
    client_id = self.SetupClient(0)
    self.RequestAndGrantClientApproval(client_id)

    self.Open(f"/clients/{client_id}")
    self.WaitUntil(self.IsTextPresent, client_id)

    self.WaitUntil(
        self.IsElementPresent, "xpath=//button[contains(., 'New Flow')]"
    )
    self.Click("xpath=//button[contains(., 'New Flow')]")
    self.WaitUntil(
        self.IsElementPresent, "xpath=//button[contains(., 'Interrogate')]"
    )
    self.Click("xpath=//button[contains(., 'Interrogate')]")
    self.WaitUntil(
        self.IsElementPresent,
        "xpath=//button[contains(., 'Schedule Flow')]",
    )
    self.Click("xpath=//button[contains(., 'Schedule Flow')]")

    self.WaitUntil(
        self.IsElementPresent,
        "xpath=//a[@mat-list-item][contains(., 'Interrogate')]",
    )

  def testCanListDirectoryFromVFS(self):
    client_id = self.SetupClient(0)
    self.RequestAndGrantClientApproval(client_id)

    self.Open(f"/clients/{client_id}/files")

    self.WaitUntil(
        self.IsElementPresent, "xpath=//button[contains(., 'folder')]"
    )
    self.Click("xpath=//button[contains(., 'folder')]")

    self.WaitUntil(
        self.IsElementPresent,
        "xpath=//button[contains(., 'List directory & subdirectories')]",
    )
    self.Click("xpath=//button[contains(., 'List directory & subdirectories')]")

    self.Open(f"/clients/{client_id}/flows")
    self.WaitUntil(
        self.IsElementPresent,
        "xpath=//a[@mat-list-item][contains(., 'Recursive list directory: /')]",
    )


if __name__ == "__main__":
  app.run(test_lib.main)
