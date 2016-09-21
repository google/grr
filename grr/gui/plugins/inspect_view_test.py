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
from grr.lib.rdfvalues import flows as rdf_flows


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

  @staticmethod
  def FillClientStats(client_id=rdf_client.ClientURN("C.0000000000000001"),
                      token=None):
    for minute in range(6):
      stats = rdf_client.ClientStats()
      for i in range(minute * 60, (minute + 1) * 60):
        sample = rdf_client.CpuSample(
            timestamp=int(i * 10 * 1e6),
            user_cpu_time=10 + i,
            system_cpu_time=20 + i,
            cpu_percent=10 + i)
        stats.cpu_samples.Append(sample)

        sample = rdf_client.IOSample(
            timestamp=int(i * 10 * 1e6),
            read_bytes=10 + i,
            write_bytes=10 + i * 2)
        stats.io_samples.Append(sample)

      message = rdf_flows.GrrMessage(
          source=client_id, args=stats.SerializeToString())
      flow.WellKnownFlow.GetAllWellKnownFlows(
          token=token)["Stats"].ProcessMessage(message)

  def testNoClientActionIsDisplayed(self):
    with self.ACLChecksDisabled():
      self.RequestAndGrantClientApproval("C.0000000000000001")

    self.Open("/#c=C.0000000000000001&main=ClientLoadView")
    self.WaitUntil(self.IsTextPresent, "No actions currently in progress.")

  def testNoClientActionIsDisplayedWhenFlowIsStarted(self):
    with self.ACLChecksDisabled():
      self.RequestAndGrantClientApproval("C.0000000000000001")

    self.Open("/#c=C.0000000000000001&main=ClientLoadView")
    self.WaitUntil(self.IsTextPresent, "No actions currently in progress.")

    flow.GRRFlow.StartFlow(
        client_id=rdf_client.ClientURN("C.0000000000000001"),
        flow_name="ListProcesses",
        token=self.token)

  def testClientActionIsDisplayedWhenItReceiveByTheClient(self):
    with self.ACLChecksDisabled():
      self.RequestAndGrantClientApproval("C.0000000000000001")
      self.CreateLeasedClientRequest(token=self.token)

    self.Open("/#c=C.0000000000000001&main=ClientLoadView")
    self.WaitUntil(self.IsTextPresent, "ListProcesses")
    self.WaitUntil(self.IsTextPresent, "MEDIUM_PRIORITY")


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
