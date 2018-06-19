#!/usr/bin/env python
"""Utility classes for front-end testing."""

from grr import config
from grr.lib import utils
from grr.server.grr_response_server import frontend_lib
from grr.test_lib import flow_test_lib
from grr.test_lib import test_lib


class FrontEndServerTest(flow_test_lib.FlowTestsBaseclass):
  """Base for GRRFEServer tests."""

  MESSAGE_EXPIRY_TIME = 100

  _CONFIG_OVERRIDER = test_lib.ConfigOverrider({
      # Whitelist test flow.
      "Frontend.well_known_flows": [
          utils.SmartStr(
              flow_test_lib.WellKnownSessionTest.well_known_session_id.FlowName(
              ))
      ],
      # For tests, small pools are ok.
      "Threadpool.size":
          10,
  })

  def setUp(self):
    super(FrontEndServerTest, self).setUp()
    self._CONFIG_OVERRIDER.Start()

    self.InitTestServer()

  def tearDown(self):
    super(FrontEndServerTest, self).tearDown()
    self._CONFIG_OVERRIDER.Stop()

  def InitTestServer(self):
    self.server = frontend_lib.FrontEndServer(
        certificate=config.CONFIG["Frontend.certificate"],
        private_key=config.CONFIG["PrivateKeys.server_key"],
        message_expiry_time=self.MESSAGE_EXPIRY_TIME,
        threadpool_prefix="pool-%s" % self._testMethodName)
