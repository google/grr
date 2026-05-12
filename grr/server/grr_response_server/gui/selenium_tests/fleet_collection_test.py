#!/usr/bin/env python
from absl import app

from grr_response_proto import flows_pb2
from grr_response_proto import objects_pb2
from grr_response_server.flows.general import discovery
from grr_response_server.gui import gui_test_lib
from grr.test_lib import test_lib


class FleetCollectionTest(gui_test_lib.GRRSeleniumHuntTest):
  """Tests the fleet collection UI."""

  def testStartFleetCollectionAndLoadResults(self):
    self.client_ids = self.SetupClients(2)
    fleet_collection_id = self.CreateHunt(
        flow_runner_args=flows_pb2.FlowRunnerArgs(
            flow_name=discovery.Interrogate.__name__
        ),
        flow_args=flows_pb2.InterrogateArgs(),
        client_limit=2,
        client_rate=2,
    )
    self.RequestAndGrantHuntApproval(
        fleet_collection_id, requestor=self.test_username
    )

    self.Open(f"/fleet-collections/{fleet_collection_id}/configuration")
    self.WaitUntilEqual(
        f"/fleet-collections/{fleet_collection_id}/configuration",
        self.GetCurrentUrlPath,
    )

    self.WaitUntil(self.IsTextPresent, "Not started")
    self.Click("xpath=//button[contains(., 'Start Fleet Collection')]")
    self.WaitUntil(self.IsTextPresent, "Running")

    self.AddResultsToHunt(
        fleet_collection_id,
        self.client_ids[0],
        [objects_pb2.ClientSnapshot(client_id=self.client_ids[0])],
    )
    self.AddResultsToHunt(
        fleet_collection_id,
        self.client_ids[1],
        [objects_pb2.ClientSnapshot(client_id=self.client_ids[1])],
    )
    self.Open(f"/fleet-collections/{fleet_collection_id}/results")
    self.WaitUntilEqual(
        f"/fleet-collections/{fleet_collection_id}/results",
        self.GetCurrentUrlPath,
    )
    self.WaitUntil(self.IsTextPresent, "2 of 2 results loaded")

  def testModifyFleetCollection(self):
    fleet_collection_id = self.CreateHunt(
        flow_runner_args=flows_pb2.FlowRunnerArgs(
            flow_name=discovery.Interrogate.__name__
        ),
        flow_args=flows_pb2.InterrogateArgs(),
    )
    self.RequestAndGrantHuntApproval(
        fleet_collection_id, requestor=self.test_username
    )

    self.Open(f"/fleet-collections/{fleet_collection_id}/configuration")
    self.WaitUntilEqual(
        f"/fleet-collections/{fleet_collection_id}/configuration",
        self.GetCurrentUrlPath,
    )
    self.WaitUntil(
        self.IsElementPresent,
        "xpath=//button[contains(., 'Modify Rollout Parameters')]",
    )
    self.Click("xpath=//button[contains(., 'Modify Rollout Parameters')]")
    self.WaitUntil(self.IsElementPresent, "css=rollout-form")
    self.Click("css=button[aria-label='Custom client sample']")
    self.WaitUntil(self.IsElementPresent, "css=input[name=customClientLimit]")
    self.Type("css=input[name=customClientLimit]", "123")
    self.Click("xpath=//button[contains(., 'Submit')]")

    self.WaitUntil(self.IsTextPresent, "123 clients (custom)")


if __name__ == "__main__":
  app.run(test_lib.main)
