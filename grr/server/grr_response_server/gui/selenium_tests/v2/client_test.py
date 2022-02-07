#!/usr/bin/env python
from absl import app

from grr_response_server import data_store
from grr_response_server.gui import gui_test_lib
from grr.test_lib import test_lib


class ClientTest(gui_test_lib.GRRSeleniumTest):

  def testLabelsAreShownAndCanBeRemoved(self):
    client_id = self.SetupClient(0)
    data_store.REL_DB.AddClientLabels(client_id, self.test_username,
                                      ["mylabel", "foobar"])

    self.Open(f"/v2/clients/{client_id}")
    self.WaitUntil(self.IsTextPresent, client_id)
    self.WaitUntil(self.IsTextPresent, "mylabel")
    self.WaitUntil(self.IsTextPresent, "foobar")

    self.Click("css=:contains('mylabel') > [aria-label='Remove label']")
    self.WaitUntilNot(self.IsTextPresent, "mylabel")

    self.assertEqual(
        ["foobar"],
        [l.name for l in data_store.REL_DB.ReadClientLabels(client_id)])

  def testClientTimelineOpensInDrawer(self):
    version = "foobazzle3000"
    client_id = self.SetupClient(0, os_version=version, fqdn="foo.bar")

    self.Open(f"/v2/clients/{client_id}")
    self.WaitUntil(self.IsTextPresent, "foo.bar")
    # Test that version only shows up after opening the details drawer. If
    # the version is every moved to the client summary shown on the client page,
    # use a different field for testing.
    self.WaitUntilNot(self.IsTextPresent, version)

    element = self.WaitUntil(self.GetVisibleElement,
                             "css=a:contains('Client details')")
    self.assertEndsWith(
        element.get_attribute("href"),
        "/v2/clients/C.1000000000000000/flows/(drawer:details)")
    element.click()

    self.WaitUntilContains("drawer", self.GetCurrentUrlPath)
    self.WaitUntil(self.IsTextPresent, version)


if __name__ == "__main__":
  app.run(test_lib.main)
