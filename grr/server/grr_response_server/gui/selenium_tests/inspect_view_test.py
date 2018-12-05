#!/usr/bin/env python
# -*- mode: python; encoding: utf-8 -*-
"""Test the inspect interface."""
from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals


from grr_response_core.lib import flags
from grr_response_core.lib.rdfvalues import client as rdf_client
from grr_response_server import data_store
from grr_response_server import flow
from grr_response_server import queue_manager
from grr_response_server.flows.general import discovery as flow_discovery
from grr_response_server.flows.general import processes
from grr_response_server.gui import gui_test_lib
from grr.test_lib import db_test_lib
from grr.test_lib import flow_test_lib
from grr.test_lib import test_lib


class TestInspectViewBase(gui_test_lib.GRRSeleniumTest):
  pass


@db_test_lib.DualDBTest
class TestClientLoadView(TestInspectViewBase):
  """Tests for ClientLoadView."""

  def setUp(self):
    super(TestClientLoadView, self).setUp()
    self.client_id = self.SetupClient(0).Basename()

  @staticmethod
  def CreateLeasedClientRequest(client_id=None, token=None):

    if not client_id:
      client_id = rdf_client.ClientURN("C.0000000000000001")
    else:
      client_id = rdf_client.ClientURN(client_id)

    flow.StartAFF4Flow(
        client_id=client_id,
        flow_name=processes.ListProcesses.__name__,
        token=token)
    with queue_manager.QueueManager(token=token) as manager:
      manager.QueryAndOwn(client_id.Queue(), limit=1, lease_seconds=10000)

  def testNoClientActionIsDisplayed(self):
    self.RequestAndGrantClientApproval(self.client_id)

    self.Open("/#/clients/%s/load-stats" % self.client_id)
    self.WaitUntil(self.IsTextPresent, "No actions currently in progress.")

  def testNoClientActionIsDisplayedWhenFlowIsStarted(self):
    self.RequestAndGrantClientApproval(self.client_id)

    self.Open("/#/clients/%s/load-stats" % self.client_id)
    self.WaitUntil(self.IsTextPresent, "No actions currently in progress.")

    flow.StartAFF4Flow(
        client_id=rdf_client.ClientURN(self.client_id),
        flow_name=processes.ListProcesses.__name__,
        token=self.token)

  def testClientActionIsDisplayedWhenItReceiveByTheClient(self):
    self.RequestAndGrantClientApproval(self.client_id)
    self.CreateLeasedClientRequest(client_id=self.client_id, token=self.token)

    self.Open("/#/clients/%s/load-stats" % self.client_id)
    self.WaitUntil(self.IsTextPresent, processes.ListProcesses.__name__)
    self.WaitUntil(self.IsTextPresent, "Leased until")


@db_test_lib.DualDBTest
class TestDebugClientRequestsView(TestInspectViewBase):
  """Test the inspect interface."""

  def testInspect(self):
    """Test the inspect UI."""
    client_id = self.SetupClient(0)

    self.RequestAndGrantClientApproval(client_id)

    flow.StartAFF4Flow(
        client_id=rdf_client.ClientURN(client_id),
        flow_name=flow_discovery.Interrogate.__name__,
        token=self.token)
    mock = flow_test_lib.MockClient(client_id, None, token=self.token)
    while mock.Next():
      pass

    self.Open("/#/clients/%s/debug-requests" % client_id.Basename())

    # Check that the we can see both requests and responses.
    self.WaitUntil(self.IsTextPresent, "GetPlatformInfo")
    self.WaitUntil(self.IsTextPresent, "GetConfig")
    self.WaitUntil(self.IsTextPresent, "EnumerateInterfaces")
    if not data_store.RelationalDBFlowsEnabled():
      self.WaitUntil(self.IsTextPresent, "GENERIC_ERROR")
      self.WaitUntil(self.IsTextPresent, "STATUS")


if __name__ == "__main__":
  flags.StartMain(test_lib.main)
