#!/usr/bin/env python
"""Tests for grr.lib.flows.general.filetypes."""


import os

from grr.client.client_actions import plist
from grr.lib import action_mocks
from grr.lib import aff4
from grr.lib import flags
from grr.lib import flow_runner
from grr.lib import test_lib
from grr.lib.aff4_objects import sequential_collection
from grr.lib.flows.general import filetypes
from grr.lib.rdfvalues import paths as rdf_paths
from grr.lib.rdfvalues import plist as rdf_plist


class TestPlistFlows(test_lib.FlowTestsBaseclass):
  """Tests the PlistValueFilter flow."""

  def _RunFlow(self, flow, context=None, query=None):
    client_mock = action_mocks.ActionMock(plist.PlistQuery)
    request = rdf_plist.PlistRequest(context=context, query=query)
    request.pathspec.path = os.path.join(self.base_path, "test.plist")
    request.pathspec.pathtype = rdf_paths.PathSpec.PathType.OS

    for s in test_lib.TestFlowHelper(
        flow,
        client_mock,
        client_id=self.client_id,
        token=self.token,
        request=request):
      session_id = s

    return session_id

  def _CheckOutput(self, session_id):
    # Check the output file is created
    output_path = session_id.Add(flow_runner.RESULTS_SUFFIX)
    results = aff4.FACTORY.Open(
        output_path,
        aff4_type=sequential_collection.GeneralIndexedCollection,
        token=self.token)
    self.assertEqual(len(results), 1)
    self.assertEqual(results[0]["nested1"]["nested11"]["key112"], "value112")

  def testPlistValueFilter(self):

    session_id = self._RunFlow(
        filetypes.PlistValueFilter.__name__, context="", query="")
    self._CheckOutput(session_id)


def main(argv):
  # Run the full test suite
  test_lib.GrrTestProgram(argv=argv)


if __name__ == "__main__":
  flags.StartMain(main)
