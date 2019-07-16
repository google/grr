#!/usr/bin/env python
# -*- encoding: utf-8 -*-
"""Test flows results UI."""
from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

from absl import app

from grr_response_core.lib.rdfvalues import client_action as rdf_client_action
from grr_response_server import data_store
from grr_response_server.gui import gui_test_lib
from grr_response_server.rdfvalues import flow_objects as rdf_flow_objects
from grr.test_lib import flow_test_lib
from grr.test_lib import test_lib


class TestFlowResults(gui_test_lib.GRRSeleniumTest):
  """Test the flow results UI."""

  def setUp(self):
    super(TestFlowResults, self).setUp()

    self.client_id = self.SetupClient(0)
    self.RequestAndGrantClientApproval(self.client_id)

  def testLaunchBinaryFlowResultsHaveReadableStdOutAndStdErr(self):
    flow_id = flow_test_lib.StartFlow(
        gui_test_lib.RecursiveTestFlow, client_id=self.client_id)

    stderr = "Oh, ok, this is just a string 昨"
    stdout = "\00\00\00\00"
    response = rdf_client_action.ExecuteResponse(
        stderr=stderr.encode("utf-8"), stdout=stdout.encode("utf-8"))

    data_store.REL_DB.WriteFlowResults([
        rdf_flow_objects.FlowResult(
            client_id=self.client_id, flow_id=flow_id, payload=response)
    ])

    self.Open("/#/clients/%s/flows/%s/results" % (self.client_id, flow_id))
    # jQuery treats the backslash ('\') character as a special one, hence we
    # have to escape it twice: once for Javascript itself and second time
    # for jQuery.
    self.WaitUntil(
        self.IsElementPresent, r"css=grr-flow-inspector:contains('Oh, ok, "
        r"this is just a string \\\\xe6\\\\x98\\\\xa8')")
    self.WaitUntil(
        self.IsElementPresent,
        r"css=grr-flow-inspector:contains('\\\\x00\\\\x00\\\\x00\\\\x00')")


if __name__ == "__main__":
  app.run(test_lib.main)
