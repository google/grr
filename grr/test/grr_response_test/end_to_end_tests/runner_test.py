#!/usr/bin/env python
import os
import sys
import unittest

import mock
import requests

from grr_api_client import api
from grr_api_client import client
from grr_api_client import config as api_config
from grr_api_client import context
from grr_api_client import types
from grr_api_client import utils as api_utils
from grr.lib import flags
from grr.server.grr_response_server.gui.api_plugins import client as plugin_client
from grr_response_test.end_to_end_tests import fake_tests
from grr_response_test.end_to_end_tests import runner
from grr_response_test.end_to_end_tests import test_base
from grr.test_lib import test_lib


class FakeApi(object):
  """Stand-in for the real GRR API."""

  def __init__(self, client_data=None, raise_conn_error=False):
    self._raise_conn_error = raise_conn_error
    self.client = mock.Mock(autospec=client.Client)
    if client_data:
      self.client.data = client_data
      self.client.client_id = client_data.client_id
    self.request_count = 0
    self.types = types.Types(mock.Mock(spec=context.GrrApiContext))

  def ListGrrBinaries(self):
    self.request_count += 1
    if self._raise_conn_error and self.request_count == 1:
      raise requests.ConnectionError("Fake Connection Error.")
    linux_binary = mock.Mock(spec=api_config.GrrBinary)
    linux_binary.path = runner.E2ETestRunner.LINUX_TEST_BINARY_PATH
    windows_binary = mock.Mock(spec=api_config.GrrBinary)
    windows_binary.path = runner.E2ETestRunner.WINDOWS_TEST_BINARY_PATH
    return api_utils.ItemsIterator(items=[linux_binary, windows_binary])

  def Client(self, client_id):
    self.request_count += 1
    if client_id != self.client.client_id:
      raise ValueError("Client id (%s) does not match registered client (%s)." %
                       (client_id, self.client.client_id))
    client_ref = mock.Mock(autospec=client.ClientRef)
    client_ref.Get.return_value = self.client
    return client_ref


FAKE_E2E_TESTS = [
    fake_tests.FakeE2ETestAll, fake_tests.FakeE2ETestDarwinLinux,
    fake_tests.FakeE2ETestLinux, fake_tests.FakeE2ETestDarwin
]


class E2ETestRunnerTest(test_lib.GRRBaseTest):

  def setUp(self):
    super(E2ETestRunnerTest, self).setUp()
    api_init_http_patcher = mock.patch.object(api, "InitHttp")
    self.api_init_http = api_init_http_patcher.start()
    self.addCleanup(api_init_http_patcher.stop)

  def testSanityCheckE2ETests(self):
    """Checks that all E2E tests have valid platforms specified."""
    self.assertTrue(test_base.REGISTRY)
    for test_class in test_base.REGISTRY.values():
      self.assertTrue(test_class.platforms,
                      "%s has no platforms specified" % test_class.__name__)
      for platform in test_class.platforms:
        self.assertIn(platform, test_base.EndToEndTest.Platform.ALL,
                      "%s has an invalid platform" % test_class.__name__)

  def testRetryInitialConnectionErrors(self):
    """Tests retrying of requests to the GRR API on connection errors."""
    grr_api = FakeApi(raise_conn_error=True)
    self.api_init_http.return_value = grr_api
    e2e_runner = self._CreateE2ETestRunner(api_retry_deadline_secs=5.0)
    e2e_runner.Initialize()
    # First request should fail with a connection error. Second request should
    # be successful.
    self.assertEqual(grr_api.request_count, 2)

  def testRetryDeadline(self):
    """Tests enforcing of connection-retry deadlines."""
    self.api_init_http.return_value = FakeApi(raise_conn_error=True)
    e2e_runner = self._CreateE2ETestRunner()  # Default deadline of zero secs.
    with self.assertRaises(requests.ConnectionError):
      e2e_runner.Initialize()

  def testClientPlatformUnavailable(self):
    """Tests that an Interrogate flow is launched if the platform is unknown."""
    api_client = self._CreateApiClient("")
    grr_api = FakeApi(client_data=api_client)
    self.api_init_http.return_value = grr_api
    e2e_runner = self._CreateE2ETestRunner(
        api_retry_period_secs=0.1, api_retry_deadline_secs=0.5)
    e2e_runner.Initialize()
    # The retry deadline should expire after a few retries, throwing an
    # exception.
    with self.assertRaises(runner.E2ETestError):
      e2e_runner.RunTestsAgainstClient(api_client.client_id)
    self.assertGreater(grr_api.request_count, 1)
    # Exactly one Interrogate flow should be launched.
    grr_api.client.CreateFlow.assert_called_once_with(
        name="Interrogate", runner_args=mock.ANY)

  @mock.patch.object(requests, "post")
  @mock.patch.object(unittest, "TextTestRunner")
  @mock.patch.dict(
      test_base.REGISTRY, {tc.__name__: tc for tc in FAKE_E2E_TESTS},
      clear=True)
  @mock.patch.dict(os.environ,
                   {runner.E2ETestRunner.APPVEYOR_API_VARNAME: "http://test"})
  def testRunAllLinuxE2ETests(self, unittest_runner, requests_post):
    api_client = self._CreateApiClient("Linux")
    grr_api = FakeApi(client_data=api_client)
    self.api_init_http.return_value = grr_api
    unittest_runner.return_value = mock.Mock(run=self._UnittestRunStub)
    e2e_runner = self._CreateE2ETestRunner(
        blacklisted_tests=["FakeE2ETestLinux"])
    e2e_runner.Initialize()
    actual_results = e2e_runner.RunTestsAgainstClient(api_client.client_id)
    expected_results = [
        "Results for %s:" % api_client.client_id,
        "\tFakeE2ETestAll.testCommon:                [ PASS ]",
        "\tFakeE2ETestDarwinLinux.testCommon:        [ FAIL ]",
        "\tFakeE2ETestDarwinLinux.testDarwinLinux:   [ FAIL ]"
    ]
    self.assertEqual(actual_results, expected_results)

    # Test data sent to the Appveyor API.
    self.assertEqual(len(requests_post.call_args_list), 3)
    test0_args, test0_kwargs = requests_post.call_args_list[0]
    test1_args, test1_kwargs = requests_post.call_args_list[1]
    self.assertEqual(test0_args, ("http://test/api/tests",))
    self.assertEqual(test1_args, ("http://test/api/tests",))
    self.assertIn("json", test0_kwargs)
    self.assertIn("json", test1_kwargs)
    expected_test0_json = {
        "testName": "FakeE2ETestAll.testCommon",
        "testFramework": "JUnit",
        "outcome": "Passed",
        "fileName": "fake_tests.py",
        "ErrorMessage": "",
        "ErrorStackTrace": "",
    }
    expected_test1_json = {
        "testName": "FakeE2ETestDarwinLinux.testCommon",
        "testFramework": "JUnit",
        "outcome": "Failed",
        "fileName": "fake_tests.py",
        "ErrorMessage": "",
    }
    self.assertDictContainsSubset(expected_test0_json, test0_kwargs["json"])
    self.assertDictContainsSubset(expected_test1_json, test1_kwargs["json"])
    # Check that failure messages get reported to Appveyor.
    self.assertIn("This is a fake error.",
                  test1_kwargs["json"]["ErrorStackTrace"])

  @mock.patch.object(requests, "post")
  @mock.patch.object(unittest, "TextTestRunner")
  @mock.patch.dict(
      test_base.REGISTRY, {tc.__name__: tc for tc in FAKE_E2E_TESTS},
      clear=True)
  @mock.patch.dict(os.environ,
                   {runner.E2ETestRunner.APPVEYOR_API_VARNAME: "http://appvyr"})
  def testWhitelisting(self, unittest_runner, requests_post):
    api_client = self._CreateApiClient("Linux")
    grr_api = FakeApi(client_data=api_client)
    self.api_init_http.return_value = grr_api
    unittest_runner.return_value = mock.Mock(run=self._UnittestRunStub)
    e2e_runner = self._CreateE2ETestRunner(whitelisted_tests=[
        "FakeE2ETestLinux.testLinux", "FakeE2ETestDarwinLinux"
    ])
    e2e_runner.Initialize()
    actual_results = e2e_runner.RunTestsAgainstClient(api_client.client_id)
    expected_results = [
        "Results for %s:" % api_client.client_id,
        "\tFakeE2ETestDarwinLinux.testCommon:        [ FAIL ]",
        "\tFakeE2ETestDarwinLinux.testDarwinLinux:   [ FAIL ]",
        "\tFakeE2ETestLinux.testLinux:               [ PASS ]"
    ]
    self.assertEqual(actual_results, expected_results)
    self.assertEqual(len(requests_post.call_args_list), 3)

  def _CreateE2ETestRunner(self,
                           api_retry_period_secs=0.0,
                           api_retry_deadline_secs=0.0,
                           **kwargs):
    """Creates an E2ETestRunner that by default doesn't retry or wait."""
    return runner.E2ETestRunner(
        api_endpoint="http://grr",
        api_password="test",
        api_retry_period_secs=api_retry_period_secs,
        api_retry_deadline_secs=api_retry_deadline_secs,
        **kwargs)

  def _CreateApiClient(self, platform):
    client_snapshot = self.SetupTestClientObject(0, system=platform)
    api_client = plugin_client.ApiClient()
    api_client.InitFromClientObject(client_snapshot)
    return api_client

  def _UnittestRunStub(self, test):
    result = unittest.TestResult()
    # Fail the FakeE2ETestDarwinLinux e2e test, and pass all others.
    if test.__class__ is fake_tests.FakeE2ETestDarwinLinux:
      fake_exc_info = None
      try:
        raise runner.E2ETestError("This is a fake error.")
      except runner.E2ETestError:
        fake_exc_info = sys.exc_info()
      result.addError(test, fake_exc_info)
    else:
      result.addSuccess(test)
    return result


def main(argv):
  test_lib.main(argv)


if __name__ == "__main__":
  flags.StartMain(main)
