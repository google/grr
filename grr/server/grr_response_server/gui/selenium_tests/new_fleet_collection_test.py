#!/usr/bin/env python
from absl import app

from grr_response_proto import flows_pb2
from grr_response_server.flows.general import discovery
from grr_response_server.gui import gui_test_lib
from grr.test_lib import flow_test_lib
from grr.test_lib import test_lib


class NewFleetCollectionTest(gui_test_lib.GRRSeleniumTest):
  """Tests the new fleet collection UI."""

  def testCreateFleetCollectionFromFlow(self):
    client_id = self.SetupClient(0)
    self.RequestAndGrantClientApproval(client_id)

    flow_id = flow_test_lib.StartFlow(
        flow_cls=discovery.Interrogate,
        creator=self.test_username,
        client_id=client_id,
        flow_args=flows_pb2.InterrogateArgs(),
    )

    self.Open(f"/clients/{client_id}/flows")
    self.WaitUntil(
        self.IsElementPresent,
        "xpath=//a[@mat-list-item][contains(., 'Interrogate')]",
    )
    self.Click(f"css=button[aria-label='Flow menu for {flow_id}']")
    self.WaitUntil(
        self.IsElementPresent,
        "xpath=//button[contains(., 'Create a fleet collection')]",
    )
    self.Click("xpath=//button[contains(., 'Create a fleet collection')]")

    # Redirects the user to new fleet collection page with original flow
    # information.
    self.WaitUntilEqual("/new-fleet-collection", self.GetCurrentUrlPath)
    self.WaitUntilEqual(
        f"clientId={client_id}&flowId={flow_id}", self.GetCurrentUrlQuery
    )

    # Fill in the fleet collection name as the field is required.
    self.WaitUntil(self.IsElementPresent, "css=[name=fleetCollectionName]")
    self.Type(
        "css=input[name=fleetCollectionName]",
        "TEST_FLEET_COLLECTION",
    )

    self.Click("xpath=//button[contains(., 'Create Fleet Collection')]")

    # Redirects the user to the access request page.
    self.WaitUntil(self.IsTextPresent, "New access request")

    # Verify that the fleet collection is created and is in the list.
    self.Open("/fleet-collections")
    self.WaitUntil(
        self.IsElementPresent,
        "xpath=//a[@mat-list-item][contains(., 'TEST_FLEET_COLLECTION')]",
    )


if __name__ == "__main__":
  app.run(test_lib.main)
