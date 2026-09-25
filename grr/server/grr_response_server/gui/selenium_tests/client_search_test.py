#!/usr/bin/env python
from absl import app

from grr_response_server.gui import gui_test_lib
from grr.test_lib import test_lib


class ClientSearchTest(gui_test_lib.GRRSeleniumTest):
  """Tests the search UI."""

  def testSearchingForDotShowsAllClients(self):
    cids = self.SetupClients(5)

    self.Open("/")
    self.Type("css=input[name=clientSearchBox]", ".", end_with_enter=True)

    for cid in cids:
      self.WaitUntil(self.IsElementPresent, f"xpath=//tr[contains(., '{cid}')]")

  def testSearchingForNonExistentClientShowsEmpty(self):
    self.SetupClients(5)

    self.Open("/")
    self.Type(
        "css=input[name=clientSearchBox]",
        "non-existent-client",
        end_with_enter=True,
    )

    self.WaitUntil(
        self.IsElementPresent,
        "xpath=//tr[contains(., 'No search results found.')]",
    )

  def testSearchingForClientLabelShowsClientsWithLabel(self):
    cids = [
        self.SetupClient(idx, labels=[f"test-label-{idx}"]) for idx in range(3)
    ]

    self.Open("/")
    self.Type(
        "css=input[name=clientSearchBox]",
        "label:test-label-0",
        end_with_enter=True,
    )

    self.WaitUntil(
        self.IsElementPresent, f"xpath=//tr[contains(., '{cids[0]}')]"
    )
    self.WaitUntilNot(
        self.IsElementPresent, f"xpath=//tr[contains(., '{cids[1]}')]"
    )
    self.WaitUntilNot(
        self.IsElementPresent, f"xpath=//tr[contains(., '{cids[2]}')]"
    )


if __name__ == "__main__":
  app.run(test_lib.main)
