#!/usr/bin/env python
"""End-to-end tests for container-related flows."""

from grr_response_test.end_to_end_tests import test_base


class TestListContainers(test_base.EndToEndTest):
  """Tests for the ListContainers flow."""

  platforms = [
      test_base.EndToEndTest.Platform.LINUX,
  ]

  def runTest(self):
    f = self.RunFlowAndWait("ListContainers")

    results = list(f.ListResults())
    self.assertTrue(results)
