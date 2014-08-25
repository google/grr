#!/usr/bin/env python
"""Tests for debugging flows."""


import os

from grr.lib import action_mocks
from grr.lib import rdfvalue
from grr.lib import test_lib

from grr.lib.flows import console  # pylint: disable=unused-import


class TestDebugFlows(test_lib.FlowTestsBaseclass):

  def testClientAction(self):
    client_mock = action_mocks.ActionMock("ListDirectory")
    pathspec = rdfvalue.PathSpec(
        path=os.path.join(self.base_path, "test_img.dd"),
        pathtype=rdfvalue.PathSpec.PathType.OS)

    request = rdfvalue.ListDirRequest(pathspec=pathspec)

    for _ in test_lib.TestFlowHelper(
        "ClientAction", client_mock, client_id=self.client_id,
        action="ListDirectory", break_pdb=False,
        action_args=request, token=self.token):
      pass
