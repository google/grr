#!/usr/bin/env python
# Lint as: python3
"""End-to-end tests for the API.

API plugins are tested with their own dedicated unit-tests that are
protocol- and server-independent. End-to-end tests are meant to use
the full GRR server stack (web server + API client library).
"""
from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

import logging

import portpicker

from grr_api_client import api as grr_api
from grr_api_client import utils as grr_api_utils
from grr_response_core.lib import utils
from grr_response_core.lib.util import compatibility
from grr_response_server.flows.general import registry_init  # pylint: disable=unused-import
from grr_response_server.gui import api_auth_manager
from grr_response_server.gui import api_call_context
from grr_response_server.gui import api_call_router_without_checks
from grr_response_server.gui import webauth
from grr_response_server.gui import wsgiapp_testlib
from grr_response_server.gui.root import api_root_router
from grr.test_lib import acl_test_lib
from grr.test_lib import test_lib


class ApiIntegrationTest(test_lib.GRRBaseTest, acl_test_lib.AclTestMixin):
  """Base class for all API E2E tests."""

  def setUp(self):
    super(ApiIntegrationTest, self).setUp()

    api_auth_manager.InitializeApiAuthManager()
    self.context = api_call_context.ApiCallContext("api_test_robot_user")
    self.token.username = self.context.username
    try:
      webauth.WEBAUTH_MANAGER.SetUserName(self.context.username)
    except AttributeError:
      # Only the NullWebAuthManager supports SetUserName
      pass

    self.CreateUser(self.context.username)

    self.port = ApiIntegrationTest.server_port
    self.endpoint = "http://localhost:%s" % self.port
    self.api = grr_api.InitHttp(api_endpoint=self.endpoint)

    poll_stubber = utils.MultiStubber(
        (grr_api_utils, "DEFAULT_POLL_INTERVAL", 0.1),
        (grr_api_utils, "DEFAULT_POLL_TIMEOUT", 10))
    poll_stubber.Start()
    self.addCleanup(poll_stubber.Stop)

  _api_set_up_done = False
  _server_trd = None
  server_port = None

  # NOTE: there's no corresponding tearDownClass method for the logic
  # below, since we want to have one SSL server thread not per test
  # suite, but per process. It effectively has to survive set up/tear down
  # of all the test suites inheriting from ApiIntegrationTest.
  @classmethod
  def setUpClass(cls):
    super(ApiIntegrationTest, cls).setUpClass()
    if ApiIntegrationTest._api_set_up_done:
      return

    # Set up HTTP server
    port = portpicker.pick_unused_port()
    ApiIntegrationTest.server_port = port
    logging.info("Picked free AdminUI port for HTTP %d.", port)

    ApiIntegrationTest._server_trd = wsgiapp_testlib.ServerThread(
        port, name="api_integration_server")
    ApiIntegrationTest._server_trd.StartAndWaitUntilServing()

    ApiIntegrationTest._api_set_up_done = True


class RootApiBinaryManagementTestRouter(
    api_root_router.ApiRootRouter,
    api_call_router_without_checks.ApiCallRouterWithoutChecks):
  """Root router combined with an unrestricted router for easier testing."""


class RootApiIntegrationTest(ApiIntegrationTest):
  """Base class for tests dealing with root API calls."""

  def setUp(self):
    super(RootApiIntegrationTest, self).setUp()

    default_router = RootApiBinaryManagementTestRouter
    root_api_config_overrider = test_lib.ConfigOverrider(
        {"API.DefaultRouter": compatibility.GetName(default_router)})
    root_api_config_overrider.Start()
    self.addCleanup(root_api_config_overrider.Stop)

    # Force creation of new APIAuthorizationManager, so that configuration
    # changes are picked up.
    api_auth_manager.InitializeApiAuthManager()
