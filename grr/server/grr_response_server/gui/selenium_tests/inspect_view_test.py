#!/usr/bin/env python
# -*- encoding: utf-8 -*-
"""Test the inspect interface."""
from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

from absl import app

from grr_response_core.lib import rdfvalue
from grr_response_server import data_store
from grr_response_server import flow
from grr_response_server.flows.general import discovery as flow_discovery
from grr_response_server.flows.general import processes
from grr_response_server.gui import gui_test_lib
from grr_response_server.rdfvalues import flow_objects as rdf_flow_objects
from grr.test_lib import test_lib


class TestInspectViewBase(gui_test_lib.GRRSeleniumTest):
  pass


class TestClientLoadView(TestInspectViewBase):
  """Tests for ClientLoadView."""

  def setUp(self):
    super(TestClientLoadView, self).setUp()
    self.client_id = self.SetupClient(0)

  def CreateLeasedClientRequest(self, client_id=None, token=None):
    flow.StartFlow(client_id=client_id, flow_cls=processes.ListProcesses)
    client_messages = data_store.REL_DB.LeaseClientActionRequests(
        client_id, lease_time=rdfvalue.Duration.From(10000, rdfvalue.SECONDS))
    self.assertNotEmpty(client_messages)

  def testNoClientActionIsDisplayed(self):
    self.RequestAndGrantClientApproval(self.client_id)

    self.Open("/#/clients/%s/load-stats" % self.client_id)
    self.WaitUntil(self.IsTextPresent, "No actions currently in progress.")

  def testClientActionIsDisplayedWhenItReceiveByTheClient(self):
    self.RequestAndGrantClientApproval(self.client_id)
    self.CreateLeasedClientRequest(client_id=self.client_id, token=self.token)

    self.Open("/#/clients/%s/load-stats" % self.client_id)
    self.WaitUntil(self.IsTextPresent, processes.ListProcesses.__name__)
    self.WaitUntil(self.IsTextPresent, "Leased until")


class TestDebugClientRequestsView(TestInspectViewBase):
  """Test the inspect interface."""

  def testInspect(self):
    """Test the inspect UI."""
    client_id = self.SetupClient(0)

    self.RequestAndGrantClientApproval(client_id)

    flow_id = flow.StartFlow(
        client_id=client_id, flow_cls=flow_discovery.Interrogate)
    status = rdf_flow_objects.FlowStatus(
        client_id=client_id, flow_id=flow_id, request_id=1, response_id=2)
    data_store.REL_DB.WriteFlowResponses([status])

    self.Open("/#/clients/%s/debug-requests" % client_id)

    # Check that the we can see both requests and responses.
    self.WaitUntil(self.IsTextPresent, "GetPlatformInfo")
    self.WaitUntil(self.IsTextPresent, "GetConfig")
    self.WaitUntil(self.IsTextPresent, "EnumerateInterfaces")

    self.WaitUntil(self.IsTextPresent, "STATUS")


if __name__ == "__main__":
  app.run(test_lib.main)
