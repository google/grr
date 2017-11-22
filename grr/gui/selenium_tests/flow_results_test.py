#!/usr/bin/env python
# -*- mode: python; encoding: utf-8 -*-
"""Test flows results UI."""


import unittest
from grr.gui import gui_test_lib

from grr.lib import flags
from grr.lib.rdfvalues import client as rdf_client
from grr.server import data_store
from grr.server import flow


class TestFlowResults(gui_test_lib.GRRSeleniumTest):
  """Test the flow results UI."""

  def setUp(self):
    super(TestFlowResults, self).setUp()

    self.client_id = rdf_client.ClientURN("C.0000000000000001")
    self.RequestAndGrantClientApproval(self.client_id)

  def testLaunchBinaryFlowResultsHaveReadableStdOutAndStdErr(self):
    flow_urn = flow.GRRFlow.StartFlow(
        client_id="aff4:/C.0000000000000001",
        flow_name=gui_test_lib.RecursiveTestFlow.__name__,
        token=self.token)

    response = rdf_client.ExecuteResponse(
        stderr="Oh, ok, this is just a string 昨", stdout="\00\00\00\00")

    with data_store.DB.GetMutationPool() as pool:
      flow.GRRFlow.ResultCollectionForFID(flow_urn).Add(
          response, mutation_pool=pool)

    self.Open("/#/clients/%s/flows/%s/results" % (self.client_id.Basename(),
                                                  flow_urn.Basename()))
    # jQuery treats the backslash ('\') character as a special one, hence we
    # have to escape it twice: once for Javascript itself and second time
    # for jQuery.
    self.WaitUntil(self.IsElementPresent,
                   r"css=grr-flow-inspector:contains('Oh, ok, "
                   r"this is just a string \\\\xe6\\\\x98\\\\xa8')")
    self.WaitUntil(
        self.IsElementPresent,
        r"css=grr-flow-inspector:contains('\\\\x00\\\\x00\\\\x00\\\\x00')")


def main(argv):
  del argv  # Unused.
  # Run the full test suite
  unittest.main()


if __name__ == "__main__":
  flags.StartMain(main)
