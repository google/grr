#!/usr/bin/env python
"""A module with utilities for testing GRR's Colab library."""
import functools
from unittest import mock

import portpicker

from grr_api_client import api
from grr_api_client import flow as api_flow
from grr_api_client import vfs as api_vfs
from grr_response_client import client_actions
from grr_colab import _api
from grr_response_core.lib.util import compatibility
from grr_response_server.gui import api_auth_manager
from grr_response_server.gui import api_call_router_with_approval_checks
from grr_response_server.gui import api_integration_test_lib
from grr_response_server.gui import wsgiapp_testlib
from grr.test_lib import action_mocks
from grr.test_lib import client_action_test_lib
from grr.test_lib import flow_test_lib
from grr.test_lib import test_lib
from grr.test_lib import testing_startup


class ColabTestMixin(object):
  """A mixin intended for tests that need to leverage GRR's Colab library."""

  @classmethod
  def setUpClass(cls) -> None:
    """Performs all initialization needed to interface with GRR's API."""
    # This is a mixin class intended to be used with `absltest.TestCase`.
    super(ColabTestMixin, cls).setUpClass()  # pytype: disable=attribute-error

    # TODO(hanuszczak): `TestInit` is awful, does a lot of unnecessary stuff and
    # should be avoided. However, because of all the global state that GRR has
    # currently, it is extremely hard figure out which parts need initialization
    # and which do not. Once AFF4 is gone, hopefully this should become much
    # simpler and `TestInit` will no longer be necessary.
    testing_startup.TestInit()

    port = portpicker.pick_unused_port()

    cls._server_thread = wsgiapp_testlib.ServerThread(port, name="ServerThread")
    cls._server_thread.StartAndWaitUntilServing()

    _api._API = api.InitHttp(api_endpoint="http://localhost:{}".format(port))  # pylint: disable=protected-access

  @classmethod
  def tearDownClass(cls) -> None:
    """Cleanups all the resources allocated during class initialization."""
    # This is a mixin class intended to be used with `absltest.TestCase`.
    super(ColabTestMixin, cls).tearDownClass()  # pytype: disable=attribute-error

    cls._server_thread.Stop()

    _api._API = None  # pylint: disable=protected-access


class ColabE2ETest(client_action_test_lib.WithAllClientActionsMixin,
                   api_integration_test_lib.ApiIntegrationTest):
  """A base test class for Colab tests that need to run flows.

  This test class is rather heavy (as it inherits from `GRRBaseTest` among other
  things). If possible, `ColabTestMixin` should be used instead (e.g. for tests
  that just need to read data from the database).
  """

  @classmethod
  def setUpClass(cls) -> None:
    # TODO(hanuszczak): See comment about `TestInit` in `ColabTestMixin`.
    # Testing startup has to be called before `setUpClass` of the superclass,
    # because it requires things like the configuration system to be already
    # initialized.
    testing_startup.TestInit()
    super(ColabE2ETest, cls).setUpClass()

  def setUp(self) -> None:
    super().setUp()

    # We override original `WaitUntilDone` with a one that executes all flows
    # on all clients. An alternative approach would be to use a background task,
    # but that does come with a significant amount of unnecessary overhead.
    #
    # This is needed, because running flows is asynchronous whereas Colab tries
    # to offer a synchronous, blocking API.
    def wait_until_done_wrapper(func):

      def wait_until_done(*args, **kwargs):
        actions = list(client_actions.REGISTRY.values())
        client_mock = action_mocks.ActionMock(*actions)

        flow_test_lib.FinishAllFlows(client_mock=client_mock)
        func(*args, **kwargs)

      return wait_until_done

    flow_wait_until_done_patcher = mock.patch.object(
        api_flow.FlowBase, "WaitUntilDone",
        wait_until_done_wrapper(api_flow.FlowBase.WaitUntilDone))

    file_wait_until_done_patcher = mock.patch.object(
        api_vfs.FileOperation, "WaitUntilDone",
        wait_until_done_wrapper(api_vfs.FileOperation.WaitUntilDone))

    flow_wait_until_done_patcher.start()
    self.addCleanup(flow_wait_until_done_patcher.stop)

    file_wait_until_done_patcher.start()
    self.addCleanup(file_wait_until_done_patcher.stop)

    api_patcher = mock.patch.object(_api, "_API", self.api)

    api_patcher.start()
    self.addCleanup(api_patcher.stop)


def with_approval_checks(func):
  """Makes give function to execute with required approvals granted."""

  @functools.wraps(func)
  def wrapper(*args, **kwargs):  # pylint: disable=missing-docstring
    cls = api_call_router_with_approval_checks.ApiCallRouterWithApprovalChecks
    cls.ClearCache()

    config_overrider = test_lib.ConfigOverrider(
        {"API.DefaultRouter": compatibility.GetName(cls)})
    with config_overrider:
      api_auth_manager.InitializeApiAuthManager()
      func(*args, **kwargs)

  return wrapper
