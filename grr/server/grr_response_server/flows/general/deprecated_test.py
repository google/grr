#!/usr/bin/env python
"""Tests for deprecated flows."""

from absl import app

from grr_response_core.lib import registry
from grr_response_server import flow_base
from grr_response_server.flows.general import deprecated
from grr.test_lib import flow_test_lib
from grr.test_lib import test_lib


class DeprecatedFlowsTest(flow_test_lib.FlowTestsBaseclass):

  class DeprecatedFlow(deprecated.AbstractDeprecatedFlow):
    pass

  class ValidFlow(flow_base.FlowBase):
    pass

  def testRegistryGetDeprecatedFlow(self):
    fetched_deprecated_flow = registry.FlowRegistry.FlowClassByName(
        self.DeprecatedFlow.__name__
    )
    self.assertEqual(fetched_deprecated_flow, self.DeprecatedFlow)
    self.assertIn(
        deprecated.AbstractDeprecatedFlow, fetched_deprecated_flow.__bases__
    )

  def testGetNotDeprecatedFlow(self):
    fetched_valid_flow = registry.FlowRegistry.FlowClassByName(
        self.ValidFlow.__name__
    )
    self.assertEqual(fetched_valid_flow, self.ValidFlow)
    self.assertNotIn(
        deprecated.AbstractDeprecatedFlow, fetched_valid_flow.__bases__
    )

  def testRegistryStoresFlowsInAccordingToTheirDeprecationStatus(self):
    self.assertNotIn(
        self.DeprecatedFlow.__name__,
        registry.FlowRegistry.FLOW_REGISTRY,
    )
    self.assertIn(
        self.DeprecatedFlow.__name__,
        registry.FlowRegistry.DEPRECATED_FLOWS,
    )
    self.assertIn(
        self.ValidFlow.__name__,
        registry.FlowRegistry.FLOW_REGISTRY,
    )
    self.assertNotIn(
        self.ValidFlow.__name__,
        registry.FlowRegistry.DEPRECATED_FLOWS,
    )


def main(argv):
  # Run the full test suite
  test_lib.main(argv)


if __name__ == "__main__":
  app.run(main)
