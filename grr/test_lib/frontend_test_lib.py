#!/usr/bin/env python
"""Utility classes for front-end testing."""
from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

from grr_response_core.lib import utils
from grr.test_lib import flow_test_lib
from grr.test_lib import test_lib


class FrontEndServerTest(flow_test_lib.FlowTestsBaseclass):
  """Base for GRRFEServer tests."""

  def setUp(self):
    super(FrontEndServerTest, self).setUp()
    config_overrider = test_lib.ConfigOverrider({
        # Whitelist test flow.
        "Frontend.well_known_flows": [
            utils.SmartStr(flow_test_lib.WellKnownSessionTest
                           .well_known_session_id.FlowName())
        ],
        # For tests, small pools are ok.
        "Threadpool.size": 10,
    })
    config_overrider.Start()
    self.addCleanup(config_overrider.Stop)
