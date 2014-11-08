#!/usr/bin/env python
"""The auditing system."""


import os

from grr.lib import action_mocks
from grr.lib import aff4
from grr.lib import flags
from grr.lib import rdfvalue
from grr.lib import test_lib


class TestAuditSystem(test_lib.FlowTestsBaseclass):

  def testFlowExecution(self):
    client_mock = action_mocks.ActionMock("ListDirectory", "StatFile")

    for _ in test_lib.TestFlowHelper(
        "ListDirectory", client_mock, client_id=self.client_id,
        pathspec=rdfvalue.PathSpec(
            path=os.path.join(self.base_path, "test_img.dd/test directory"),
            pathtype=rdfvalue.PathSpec.PathType.OS),
        token=self.token):
      pass

    fd = aff4.FACTORY.Open("aff4:/audit/log", token=self.token)

    event = fd[0]

    self.assertEqual(event.action, rdfvalue.AuditEvent.Action.RUN_FLOW)
    self.assertEqual(event.flow_name, "ListDirectory")
    self.assertEqual(event.user, self.token.username)


class FlowTestLoader(test_lib.GRRTestLoader):
  base_class = TestAuditSystem


def main(argv):
  # Run the full test suite
  test_lib.GrrTestProgram(argv=argv, testLoader=FlowTestLoader())

if __name__ == "__main__":
  flags.StartMain(main)
