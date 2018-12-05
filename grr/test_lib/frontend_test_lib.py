#!/usr/bin/env python
"""Utility classes for front-end testing."""
from __future__ import absolute_import
from __future__ import division

from grr_response_core.lib import utils
from grr.test_lib import flow_test_lib
from grr.test_lib import test_lib


class FrontEndServerTest(flow_test_lib.FlowTestsBaseclass):
  """Base for GRRFEServer tests."""

  _CONFIG_OVERRIDER = test_lib.ConfigOverrider({
      # Whitelist test flow.
      "Frontend.well_known_flows": [
          utils.SmartStr(flow_test_lib.WellKnownSessionTest
                         .well_known_session_id.FlowName())
      ],
      # For tests, small pools are ok.
      "Threadpool.size":
          10,
  })

  def setUp(self):
    super(FrontEndServerTest, self).setUp()
    self._CONFIG_OVERRIDER.Start()

  def tearDown(self):
    super(FrontEndServerTest, self).tearDown()
    self._CONFIG_OVERRIDER.Stop()
