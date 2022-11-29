#!/usr/bin/env python
from absl import app

from grr_response_core.lib.rdfvalues import file_finder as rdf_file_finder
from grr_response_server import flow
from grr_response_server.flows import file
from grr_response_server.gui import gui_test_lib
from grr_response_server.rdfvalues import flow_runner as rdf_flow_runner
from grr.test_lib import test_lib


class ApprovalTest(gui_test_lib.GRRSeleniumTest):

  def testApprovalPageShowsAllRelevantInformation(self):
    client_id = self.SetupClient(0, fqdn="foo.bar.bazzle")
    self.CreateUser("requestrick")
    self.CreateUser("approveannie")
    approval_id = self.RequestClientApproval(
        client_id,
        reason="t/1234",
        requestor="requestrick",
        approver="approveannie")

    self.Open(
        f"/v2/clients/{client_id}/users/requestrick/approvals/{approval_id}")

    self.WaitUntil(self.IsTextPresent, client_id)
    self.WaitUntil(self.IsTextPresent, "foo.bar.bazzle")
    self.WaitUntil(self.IsTextPresent, "requestrick")
    self.WaitUntil(self.IsTextPresent, "approveannie")
    self.WaitUntil(self.IsTextPresent, "t/1234")

  def testGrantButtonGrantsApproval(self):
    client_id = self.SetupClient(0)
    self.CreateUser("requestrick")
    approval_id = self.RequestClientApproval(
        client_id, reason="t/1234", requestor="requestrick")
    self.Open(
        f"/v2/clients/{client_id}/users/requestrick/approvals/{approval_id}")

    self.WaitUntil(self.IsElementPresent, "css=button:contains('Grant')")

    approvals = self.ListClientApprovals(requestor="requestrick")
    self.assertLen(approvals, 1)
    self.assertFalse(approvals[0].is_valid)

    self.Click("css=button:contains('Grant')")

    def ApprovalHasBeenGranted():
      approvals = self.ListClientApprovals(requestor="requestrick")
      self.assertLen(approvals, 1)
      return approvals[0].is_valid

    self.WaitUntil(ApprovalHasBeenGranted)

  def testScheduledFlowsAreShown(self):
    client_id = self.SetupClient(0)
    self.CreateUser("requestrick")
    self.CreateUser("approveannie")

    flow.ScheduleFlow(
        client_id=client_id,
        creator="requestrick",
        flow_name=file.CollectSingleFile.__name__,
        flow_args=rdf_file_finder.CollectSingleFileArgs(path="/foo"),
        runner_args=rdf_flow_runner.FlowRunnerArgs())

    approval_id = self.RequestClientApproval(
        client_id,
        reason="t/1234",
        requestor="requestrick",
        approver="approveannie")

    self.Open(
        f"/v2/clients/{client_id}/users/requestrick/approvals/{approval_id}")

    # Change to pretty display name as soon as ScheduledFlowList uses these.
    self.WaitUntil(self.IsTextPresent, "CollectSingleFile")

  def testBackButtonNavigatesToOldUi(self):
    client_id = self.SetupClient(0)
    self.CreateUser("requestrick")
    approval_id = self.RequestClientApproval(
        client_id, reason="t/1234", requestor="requestrick")

    self.Open(
        f"/v2/clients/{client_id}/users/requestrick/approvals/{approval_id}")
    self.WaitUntil(self.IsElementPresent, "css=a#fallback-link")
    self.Click("css=a#fallback-link")

    self.WaitUntilEqual(
        f"/#/users/requestrick/approvals/client/{client_id}/{approval_id}",
        self.GetCurrentUrlPath)


if __name__ == "__main__":
  app.run(test_lib.main)
