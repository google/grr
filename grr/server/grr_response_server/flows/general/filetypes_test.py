#!/usr/bin/env python
"""Tests for grr_response_server.flows.general.filetypes."""
from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

import os

from absl import app

from grr_response_client.client_actions import plist
from grr_response_core.lib.rdfvalues import paths as rdf_paths
from grr_response_core.lib.rdfvalues import plist as rdf_plist
from grr_response_server.flows.general import filetypes
from grr.test_lib import action_mocks
from grr.test_lib import flow_test_lib
from grr.test_lib import test_lib


class TestPlistFlows(flow_test_lib.FlowTestsBaseclass):
  """Tests the PlistValueFilter flow."""

  def _RunFlow(self, client_id, flow_name, context=None, query=None):
    client_mock = action_mocks.ActionMock(plist.PlistQuery)
    request = rdf_plist.PlistRequest(context=context, query=query)
    request.pathspec.path = os.path.join(self.base_path, "test.plist")
    request.pathspec.pathtype = rdf_paths.PathSpec.PathType.OS

    session_id = flow_test_lib.TestFlowHelper(
        flow_name,
        client_mock,
        client_id=client_id,
        token=self.token,
        request=request)

    return session_id

  def testPlistValueFilter(self):
    client_id = self.SetupClient(0)

    session_id = self._RunFlow(
        client_id, filetypes.PlistValueFilter.__name__, context="", query="")

    results = flow_test_lib.GetFlowResults(client_id, session_id)
    self.assertLen(results, 1)
    result_dict = results[0].dict
    self.assertEqual(result_dict["nested1"]["nested11"]["key112"], "value112")


def main(argv):
  # Run the full test suite
  test_lib.main(argv)


if __name__ == "__main__":
  app.run(main)
