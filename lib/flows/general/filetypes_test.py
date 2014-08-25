#!/usr/bin/env python
"""Tests for grr.lib.flows.general.filetypes."""


import os

from grr.lib import action_mocks
from grr.lib import aff4
from grr.lib import rdfvalue
from grr.lib import test_lib


class TestPlistFlows(test_lib.FlowTestsBaseclass):
  """Tests the PlistValueFilter flow."""

  def _RunFlow(self, flow, context=None, query=None, output=None):
    client_mock = action_mocks.ActionMock("PlistQuery")
    request = rdfvalue.PlistRequest(context=context, query=query)
    request.pathspec.path = os.path.join(self.base_path, "test.plist")
    request.pathspec.pathtype = rdfvalue.PathSpec.PathType.OS

    for _ in test_lib.TestFlowHelper(
        flow, client_mock, client_id=self.client_id, token=self.token,
        request=request, output=output):
      pass

  def _CheckOutputAFF4Type(self, output):
    # Check the output file is created
    output_path = self.client_id.Add(output)
    aff4.FACTORY.Open(output_path, aff4_type="AFF4PlistQuery",
                      token=self.token)

  def testPlistValueFilter(self):
    output = "analysis/plistvaluefilter_test"
    self._RunFlow("PlistValueFilter", context="", query="",
                  output=output)
    self._CheckOutputAFF4Type(output)
