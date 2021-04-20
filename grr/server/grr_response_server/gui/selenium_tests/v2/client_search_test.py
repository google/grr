#!/usr/bin/env python
from absl import app

from grr_response_server.gui import gui_test_lib
from grr.test_lib import test_lib


class ClientSearchTest(gui_test_lib.GRRSeleniumTest):
  """Tests the search UI."""

  def testSearchingForDotShowsAllClients(self):
    client_ids = self.SetupClients(5)

    self.Open("/v2")
    self.Type("css=input[name=clientSearchBox]", ".", end_with_enter=True)

    for cid in client_ids:
      self.WaitUntil(self.IsElementPresent, f"css=tr:contains('{cid}')")


if __name__ == "__main__":
  app.run(test_lib.main)
