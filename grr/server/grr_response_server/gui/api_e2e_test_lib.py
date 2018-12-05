#!/usr/bin/env python
"""End-to-end tests for the API.

API plugins are tested with their own dedicated unit-tests that are
protocol- and server-independent. End-to-end tests are meant to use
the full GRR server stack (web server + API client library).
"""
from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

import logging
import threading


import portpicker

from grr_api_client import api as grr_api
from grr_api_client import utils as grr_api_utils
from grr_response_core.lib import utils
from grr_response_server.gui import api_auth_manager
from grr_response_server.gui import api_call_router_without_checks
from grr_response_server.gui import webauth
from grr_response_server.gui import wsgiapp_testlib
from grr_response_server.gui.root import api_root_router
from grr.test_lib import acl_test_lib
from grr.test_lib import test_lib


class ApiE2ETest(test_lib.GRRBaseTest, acl_test_lib.AclTestMixin):
  """Base class for all API E2E tests."""

  def setUp(self):
    super(ApiE2ETest, self).setUp()

    api_auth_manager.APIACLInit.InitApiAuthManager()
    self.token.username = "api_test_robot_user"
    webauth.WEBAUTH_MANAGER.SetUserName(self.token.username)

    self.port = ApiE2ETest.server_port
    self.endpoint = "http://localhost:%s" % self.port
    self.api = grr_api.InitHttp(api_endpoint=self.endpoint)

    self.poll_stubber = utils.MultiStubber(
        (grr_api_utils, "DEFAULT_POLL_INTERVAL", 0.1),
        (grr_api_utils, "DEFAULT_POLL_TIMEOUT", 10))
    self.poll_stubber.Start()

  def tearDown(self):
    super(ApiE2ETest, self).tearDown()
    self.poll_stubber.Stop()

  _api_set_up_lock = threading.RLock()
  _api_set_up_done = False

  @classmethod
  def setUpClass(cls):
    super(ApiE2ETest, cls).setUpClass()
    with ApiE2ETest._api_set_up_lock:
      if not ApiE2ETest._api_set_up_done:

        # Set up HTTP server
        port = portpicker.pick_unused_port()
        ApiE2ETest.server_port = port
        logging.info("Picked free AdminUI port for HTTP %d.", port)

        ApiE2ETest.trd = wsgiapp_testlib.ServerThread(
            port, name="api_e2e_server")
        ApiE2ETest.trd.StartAndWaitUntilServing()

        ApiE2ETest._api_set_up_done = True

  @classmethod
  def tearDownClass(cls):
    super(ApiE2ETest, cls).tearDownClass()
    ApiE2ETest.trd.Stop()


class RootApiBinaryManagementTestRouter(
    api_root_router.ApiRootRouter,
    api_call_router_without_checks.ApiCallRouterWithoutChecks):
  """Root router combined with an unrestricted router for easier testing."""


class RootApiE2ETest(ApiE2ETest):
  """Base class for tests dealing with root API calls."""

  def setUp(self):
    super(RootApiE2ETest, self).setUp()

    self.root_api_config_overrider = test_lib.ConfigOverrider({
        "API.DefaultRouter": RootApiBinaryManagementTestRouter.__name__
    })
    self.root_api_config_overrider.Start()

    # Force creation of new APIAuthorizationManager, so that configuration
    # changes are picked up.
    api_auth_manager.APIACLInit.InitApiAuthManager()

  def tearDown(self):
    super(RootApiE2ETest, self).tearDown()
    self.root_api_config_overrider.Stop()
