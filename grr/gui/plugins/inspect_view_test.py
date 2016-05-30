#!/usr/bin/env python
# -*- mode: python; encoding: utf-8 -*-
"""Test the inspect interface."""



from grr.gui import runtests_test

from grr.lib import flags
from grr.lib import flow
from grr.lib import queue_manager
from grr.lib import test_lib
from grr.lib.rdfvalues import client as rdf_client
from grr.lib.rdfvalues import flows as rdf_flows


class TestInspectViewBase(test_lib.GRRSeleniumTest):
  pass


class TestClientLoadView(TestInspectViewBase):
  """Tests for ClientLoadView."""

  @staticmethod
  def CreateLeasedClientRequest(
      client_id=rdf_client.ClientURN("C.0000000000000001"),
      token=None):

    flow.GRRFlow.StartFlow(client_id=client_id,
                           flow_name="ListProcesses",
                           token=token)
    with queue_manager.QueueManager(token=token) as manager:
      manager.QueryAndOwn(client_id.Queue(), limit=1, lease_seconds=10000)

  @staticmethod
  def FillClientStats(client_id=rdf_client.ClientURN("C.0000000000000001"),
                      token=None):
    for minute in range(6):
      stats = rdf_client.ClientStats()
      for i in range(minute * 60, (minute + 1) * 60):
        sample = rdf_client.CpuSample(timestamp=int(i * 10 * 1e6),
                                      user_cpu_time=10 + i,
                                      system_cpu_time=20 + i,
                                      cpu_percent=10 + i)
        stats.cpu_samples.Append(sample)

        sample = rdf_client.IOSample(timestamp=int(i * 10 * 1e6),
                                     read_bytes=10 + i,
                                     write_bytes=10 + i * 2)
        stats.io_samples.Append(sample)

      message = rdf_flows.GrrMessage(source=client_id,
                                     args=stats.SerializeToString())
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

    flow.GRRFlow.StartFlow(client_id=rdf_client.ClientURN("C.0000000000000001"),
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
      self.RequestAndGrantClientApproval("C.0000000000000001")

    self.Open("/")

    self.Type("client_query", "C.0000000000000001")
    self.Click("client_query_submit")

    self.WaitUntilEqual(u"C.0000000000000001", self.GetText,
                        "css=span[type=subject]")

    # Choose client 1
    self.Click("css=td:contains('0001')")

    self.Click("css=a[grrtarget='client.launchFlows']")
    self.Click("css=#_Administrative i")

    self.Click("css=a:contains(Interrogate)")

    self.Click("css=button.Launch")

    # Open the "Advanced" dropdown.
    self.Click("css=li#HostAdvanced > a")
    # Click on the "Debug client requests".
    self.Click("css=a[grrtarget='client.debugRequests']")

    self.WaitUntil(self.IsElementPresent, "css=td:contains(GetPlatformInfo)")

    # Check that the we can see the requests in the table.
    for request in "GetPlatformInfo GetConfig EnumerateInterfaces".split():
      self.assertTrue(self.IsElementPresent("css=td:contains(%s)" % request))

    self.Click("css=td:contains(GetPlatformInfo)")

    # Check that the proto is rendered inside the tab.
    self.WaitUntil(self.IsElementPresent,
                   "css=.tab-content td.proto_value:contains(GetPlatformInfo)")

    # Check that the request tab is currently selected.
    self.assertTrue(self.IsElementPresent("css=li.active:contains(Request)"))

    # Here we emulate a mock client with no actions (None) this should produce
    # an error.
    with self.ACLChecksDisabled():
      mock = test_lib.MockClient(
          rdf_client.ClientURN("C.0000000000000001"),
          None,
          token=self.token)
      while mock.Next():
        pass

    # Now select the Responses tab:
    self.Click("css=li a:contains(Responses)")
    self.WaitUntil(self.IsElementPresent, "css=td:contains('flow:response:')")

    self.assertTrue(self.IsElementPresent(
        "css=.tab-content td.proto_value:contains(GENERIC_ERROR)"))

    self.assertTrue(self.IsElementPresent(
        "css=.tab-content td.proto_value:contains(STATUS)"))


def main(argv):
  # Run the full test suite
  runtests_test.SeleniumTestProgram(argv=argv)


if __name__ == "__main__":
  flags.StartMain(main)
