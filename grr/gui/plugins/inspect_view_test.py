#!/usr/bin/env python
# -*- mode: python; encoding: utf-8 -*-
"""Test the inspect interface."""



from grr.gui import runtests_test

from grr.lib import flags
from grr.lib import flow
from grr.lib import queue_manager
from grr.lib import test_lib
from grr.lib.flows.general import discovery as flow_discovery
from grr.lib.rdfvalues import client as rdf_client


class TestInspectViewBase(test_lib.GRRSeleniumTest):
  pass


class TestClientLoadView(TestInspectViewBase):
  """Tests for ClientLoadView."""

  @staticmethod
  def CreateLeasedClientRequest(
      client_id=rdf_client.ClientURN("C.0000000000000001"), token=None):

    flow.GRRFlow.StartFlow(
        client_id=client_id, flow_name="ListProcesses", token=token)
    with queue_manager.QueueManager(token=token) as manager:
      manager.QueryAndOwn(client_id.Queue(), limit=1, lease_seconds=10000)

  def testNoClientActionIsDisplayed(self):
    with self.ACLChecksDisabled():
      self.RequestAndGrantClientApproval("C.0000000000000001")

    self.Open("/#/clients/C.0000000000000001/load-stats")
    self.WaitUntil(self.IsTextPresent, "No actions currently in progress.")

  def testNoClientActionIsDisplayedWhenFlowIsStarted(self):
    with self.ACLChecksDisabled():
      self.RequestAndGrantClientApproval("C.0000000000000001")

    self.Open("/#/clients/C.0000000000000001/load-stats")
    self.WaitUntil(self.IsTextPresent, "No actions currently in progress.")

    flow.GRRFlow.StartFlow(
        client_id=rdf_client.ClientURN("C.0000000000000001"),
        flow_name="ListProcesses",
        token=self.token)

  def testClientActionIsDisplayedWhenItReceiveByTheClient(self):
    with self.ACLChecksDisabled():
      self.RequestAndGrantClientApproval("C.0000000000000001")
      self.CreateLeasedClientRequest(token=self.token)

    self.Open("/#/clients/C.0000000000000001/load-stats")
    self.WaitUntil(self.IsTextPresent, "ListProcesses")
    self.WaitUntil(self.IsTextPresent, "Task id")
    self.WaitUntil(self.IsTextPresent, "Task eta")


class TestDebugClientRequestsView(TestInspectViewBase):
  """Test the inspect interface."""

  def testInspect(self):
    """Test the inspect UI."""
    with self.ACLChecksDisabled():
      client_id = self.SetupClients(1)[0]

      self.RequestAndGrantClientApproval(client_id)

      flow.GRRFlow.StartFlow(
          client_id=client_id,
          flow_name=flow_discovery.Interrogate.__name__,
          token=self.token)
      mock = test_lib.MockClient(client_id, None, token=self.token)
      while mock.Next():
        pass

    self.Open("/#/clients/%s/debug-requests" % client_id.Basename())

    # Check that the we can see both requests and responses.
    self.WaitUntil(self.IsTextPresent, "GetPlatformInfo")
    self.WaitUntil(self.IsTextPresent, "GetConfig")
    self.WaitUntil(self.IsTextPresent, "EnumerateInterfaces")
    self.WaitUntil(self.IsTextPresent, "GENERIC_ERROR")
    self.WaitUntil(self.IsTextPresent, "STATUS")
    self.WaitUntil(self.IsTextPresent, "Task id")


def main(argv):
  # Run the full test suite
  runtests_test.SeleniumTestProgram(argv=argv)


if __name__ == "__main__":
  flags.StartMain(main)
