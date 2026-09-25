#!/usr/bin/env python
"""End to end tests for GRR discovery flows."""

from grr_response_proto import objects_pb2
from grr_response_test.end_to_end_tests import test_base


class TestClientInterrogate(test_base.EndToEndTest):
  """Test for the Interrogate flow on all platforms."""

  platforms = test_base.EndToEndTest.Platform.ALL

  def runTest(self):
    f = self.RunFlowAndWait("Interrogate")

    results = list(f.ListResults())
    self.assertLen(results, 1)

    snapshot: objects_pb2.ClientSnapshot = results[0].payload

    self.assertNotEmpty(snapshot.knowledge_base.users)
    for u in snapshot.knowledge_base.users:
      self.assertNotEmpty(u.username)

      if self.platform == test_base.EndToEndTest.Platform.LINUX:
        self.assertTrue(u.uid)
      elif self.platform == test_base.EndToEndTest.Platform.WINDOWS:
        self.assertNotEmpty(u.sid)
        self.assertNotEmpty(u.userprofile)
      elif self.platform == test_base.EndToEndTest.Platform.DARWIN:
        self.assertNotEmpty(u.username)
      else:
        raise ValueError(f"Unknown client platform: {self.platform}")
