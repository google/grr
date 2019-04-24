#!/usr/bin/env python
# -*- encoding: utf-8 -*-
"""Test the inspect interface."""
from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals


from absl import app

from grr_response_core.lib import rdfvalue
from grr_response_core.lib.rdfvalues import client as rdf_client
from grr_response_core.lib.rdfvalues import flows as rdf_flows
from grr_response_server import data_store
from grr_response_server import flow
from grr_response_server import queue_manager
from grr_response_server.flows.general import discovery as flow_discovery
from grr_response_server.flows.general import processes
from grr_response_server.gui import gui_test_lib
from grr_response_server.rdfvalues import flow_objects as rdf_flow_objects
from grr.test_lib import db_test_lib
from grr.test_lib import test_lib


class TestInspectViewBase(gui_test_lib.GRRSeleniumTest):
  pass


@db_test_lib.DualDBTest
class TestClientLoadView(TestInspectViewBase):
  """Tests for ClientLoadView."""

  def setUp(self):
    super(TestClientLoadView, self).setUp()
    self.client_id = self.SetupClient(0).Basename()

  def CreateLeasedClientRequest(self, client_id=None, token=None):
    if data_store.RelationalDBEnabled():
      flow.StartFlow(
          client_id=client_id.Basename(), flow_cls=processes.ListProcesses)
      client_messages = data_store.REL_DB.LeaseClientActionRequests(
          client_id.Basename(), lease_time=rdfvalue.Duration("10000s"))
      self.assertNotEmpty(client_messages)
    else:
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

  def testClientActionIsDisplayedWhenItReceiveByTheClient(self):
    self.RequestAndGrantClientApproval(self.client_id)
    client_urn = rdf_client.ClientURN(self.client_id)
    self.CreateLeasedClientRequest(client_id=client_urn, token=self.token)

    self.Open("/#/clients/%s/load-stats" % self.client_id)
    self.WaitUntil(self.IsTextPresent, processes.ListProcesses.__name__)
    self.WaitUntil(self.IsTextPresent, "Leased until")


@db_test_lib.DualDBTest
class TestDebugClientRequestsView(TestInspectViewBase):
  """Test the inspect interface."""

  def testInspect(self):
    """Test the inspect UI."""
    client_urn = self.SetupClient(0)
    client_id = client_urn.Basename()

    self.RequestAndGrantClientApproval(client_id)

    if data_store.RelationalDBEnabled():
      flow_id = flow.StartFlow(
          client_id=client_id, flow_cls=flow_discovery.Interrogate)
      status = rdf_flow_objects.FlowStatus(
          client_id=client_id, flow_id=flow_id, request_id=1, response_id=2)
      data_store.REL_DB.WriteFlowResponses([status])
    else:
      session_id = flow.StartAFF4Flow(
          client_id=client_urn,
          flow_name=flow_discovery.Interrogate.__name__,
          token=self.token)
      status = rdf_flows.GrrMessage(
          request_id=1,
          response_id=2,
          session_id=session_id,
          type=rdf_flows.GrrMessage.Type.STATUS,
          auth_state=rdf_flows.GrrMessage.AuthorizationState.AUTHENTICATED)
      with queue_manager.QueueManager(token=self.token) as manager:
        manager.QueueResponse(status)

    self.Open("/#/clients/%s/debug-requests" % client_id)

    # Check that the we can see both requests and responses.
    self.WaitUntil(self.IsTextPresent, "GetPlatformInfo")
    self.WaitUntil(self.IsTextPresent, "GetConfig")
    self.WaitUntil(self.IsTextPresent, "EnumerateInterfaces")

    self.WaitUntil(self.IsTextPresent, "STATUS")


if __name__ == "__main__":
  app.run(test_lib.main)
