#!/usr/bin/env python
"""Tests for grr.lib.flows.general.filetypes."""


import os

from grr.lib import action_mocks
from grr.lib import aff4
from grr.lib import flags
from grr.lib import test_lib
from grr.lib.aff4_objects import filetypes as aff4_filetypes
from grr.lib.flows.general import filetypes
from grr.lib.rdfvalues import paths as rdf_paths
from grr.lib.rdfvalues import plist as rdf_plist


class TestPlistFlows(test_lib.FlowTestsBaseclass):
  """Tests the PlistValueFilter flow."""

  def _RunFlow(self, flow, context=None, query=None, output=None):
    client_mock = action_mocks.ActionMock("PlistQuery")
    request = rdf_plist.PlistRequest(context=context, query=query)
    request.pathspec.path = os.path.join(self.base_path, "test.plist")
    request.pathspec.pathtype = rdf_paths.PathSpec.PathType.OS

    for _ in test_lib.TestFlowHelper(flow,
                                     client_mock,
                                     client_id=self.client_id,
                                     token=self.token,
                                     request=request,
                                     output=output):
      pass

  def _CheckOutputAFF4Type(self, output):
    # Check the output file is created
    output_path = self.client_id.Add(output)
    aff4.FACTORY.Open(output_path,
                      aff4_type=aff4_filetypes.AFF4PlistQuery,
                      token=self.token)

  def testPlistValueFilter(self):
    output = "analysis/plistvaluefilter_test"
    self._RunFlow(filetypes.PlistValueFilter.__name__,
                  context="",
                  query="",
                  output=output)
    self._CheckOutputAFF4Type(output)


def main(argv):
  # Run the full test suite
  test_lib.GrrTestProgram(argv=argv)


if __name__ == "__main__":
  flags.StartMain(main)
