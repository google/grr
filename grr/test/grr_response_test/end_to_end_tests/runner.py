#!/usr/bin/env python
"""Helper for running end-to-end tests."""
from __future__ import absolute_import
from __future__ import division

import collections
import getpass
import inspect
import logging
import os
import time
import unittest


from future.moves.urllib import parse as urlparse
from future.utils import iteritems
from future.utils import itervalues
from future.utils import string_types
import requests

from grr_api_client import api
from grr_response_core.lib import package
from grr_response_server import maintenance_utils
from grr_response_test.end_to_end_tests import test_base

# We need to import all test classes so they can be added in test_base.REGISTRY
# by their metaclass.
#
# pylint: disable=unused-import
from grr_response_test.end_to_end_tests import tests

# pylint: enable=unused-import


class E2ETestError(Exception):
  pass


class E2ETestRunner(object):
  """Runs end-to-end tests against clients using the GRR API.

  If running in an Appveyor VM, test results (along with error messages) will
  be streamed to Appveyor, and will be visible in the Appveyor dashboard.
  """

  APPVEYOR_API_VARNAME = "APPVEYOR_API_URL"
  LOGFILE_SUCCESS_RESULT = "[ PASS ]"
  LOGFILE_FAILURE_RESULT = "[ FAIL ]"
  APPVEYOR_SUCCESS_RESULT = "Passed"
  APPVEYOR_FAILURE_RESULT = "Failed"
  LINUX_TEST_BINARY_NAME = "hello"
  LINUX_TEST_BINARY_PATH = "linux/test/hello"
  WINDOWS_TEST_BINARY_NAME = "hello.exe"
  WINDOWS_TEST_BINARY_PATH = "windows/test/hello.exe"

  def __init__(self,
               api_endpoint="",
               api_user="",
               api_password="",
               whitelisted_tests=None,
               blacklisted_tests=None,
               upload_test_binaries=True,
               api_retry_period_secs=30.0,
               api_retry_deadline_secs=500.0,
               max_test_attempts=3):
    if not api_endpoint:
      raise ValueError("GRR api_endpoint is required.")
    if isinstance(whitelisted_tests, string_types):
      raise ValueError("whitelisted_tests should be a list.")
    if isinstance(blacklisted_tests, string_types):
      raise ValueError("blacklisted_tests should be a list.")
    if max_test_attempts < 1:
      raise ValueError(
          "max_test_attempts (%d) must be at least 1." % max_test_attempts)
    self._api_endpoint = api_endpoint
    self._api_user = api_user
    self._api_password = api_password
    self._whitelisted_tests = set(whitelisted_tests or set())
    self._blacklisted_tests = set(blacklisted_tests or set())
    self._upload_test_binaries = upload_test_binaries
    self._api_retry_period_secs = api_retry_period_secs
    self._api_retry_deadline_secs = api_retry_deadline_secs
    self._max_test_attempts = max_test_attempts
    self._grr_api = None
    self._appveyor_tests_endpoint = ""
    self._appveyor_messages_endpoint = ""

  def Initialize(self):
    """Initializes state in preparation for running end-to-end tests.

    Only needs to be called once.
    """
    appveyor_root_url = os.environ.get(self.APPVEYOR_API_VARNAME, None)
    if appveyor_root_url:
      logging.info("Using Appveyor API at %s", appveyor_root_url)
      # See https://www.appveyor.com/docs/build-worker-api/
      self._appveyor_tests_endpoint = urlparse.urljoin(appveyor_root_url,
                                                       "api/tests")
      self._appveyor_messages_endpoint = urlparse.urljoin(
          appveyor_root_url, "api/build/messages")

    logging.info("Connecting to GRR API at %s", self._api_endpoint)
    password = self._api_password
    if not password:
      password = getpass.getpass(prompt="Please enter the API password for "
                                 "user '%s': " % self._api_user)
    self._grr_api = api.InitHttp(
        api_endpoint=self._api_endpoint, auth=(self._api_user, password))

    # Make sure binaries required by tests are uploaded to the datastore.
    if self._upload_test_binaries:
      binary_paths = self._GetUploadedBinaries()
      if self.LINUX_TEST_BINARY_PATH not in binary_paths:
        self._UploadBinary(self.LINUX_TEST_BINARY_NAME,
                           self.LINUX_TEST_BINARY_PATH)
      if self.WINDOWS_TEST_BINARY_PATH not in binary_paths:
        self._UploadBinary(self.WINDOWS_TEST_BINARY_NAME,
                           self.WINDOWS_TEST_BINARY_PATH)

  def _GetUploadedBinaries(self):
    """Fetches all binaries that have been uploaded to GRR."""
    start_time = time.time()
    while True:
      try:
        return {item.path for item in self._grr_api.ListGrrBinaries()}
      except requests.ConnectionError as e:
        if time.time() - start_time > self._api_retry_deadline_secs:
          logging.error("Timeout of %d seconds exceeded.",
                        self._api_retry_deadline_secs)
          raise
        logging.error("Encountered error trying to connect to GRR API: %s",
                      e.args)
      logging.info("Retrying in %d seconds...", self._api_retry_period_secs)
      time.sleep(self._api_retry_period_secs)

  def _UploadBinary(self, bin_name, server_path):
    """Uploads a binary from the GRR installation dir to the datastore."""
    # TODO(user): Upload binaries via the GRR API.
    logging.info("Uploading %s binary to server.", server_path)
    package_dir = package.ResourcePath("grr-response-test", "grr_response_test")
    with open(os.path.join(package_dir, "test_data", bin_name), "rb") as f:
      maintenance_utils.UploadSignedConfigBlob(
          f.read(), "aff4:/config/executables/%s" % server_path)

  def RunTestsAgainstClient(self, client_id):
    """Runs all applicable end-to-end tests against the given client."""
    if self._grr_api is None:
      raise E2ETestError("API connection has not been initialized.")
    client = self._GetClient(client_id)
    test_base.init_fn = lambda: (self._grr_api, client)
    unittest_runner = unittest.TextTestRunner()

    results = collections.OrderedDict()
    for test_name, test in iteritems(self._GetApplicableTests(client)):
      result, millis_elapsed = self._RetryTest(test_name, test, unittest_runner)
      results[test_name] = result
      if not self._appveyor_tests_endpoint:
        continue

      assert_failures = ""
      unexpected_errors = ""
      appveyor_result_string = self.APPVEYOR_SUCCESS_RESULT
      if result.failures:
        appveyor_result_string = self.APPVEYOR_FAILURE_RESULT
        assert_failures = "\n".join([msg for _, msg in result.failures])
      if result.errors:
        appveyor_result_string = self.APPVEYOR_FAILURE_RESULT
        unexpected_errors = "\n".join([msg for _, msg in result.errors])
      resp = requests.post(
          self._appveyor_tests_endpoint,
          json={
              "testName":
                  test_name,
              "testFramework":
                  "JUnit",
              "outcome":
                  appveyor_result_string,
              "durationMilliseconds":
                  str(millis_elapsed),
              "fileName":
                  os.path.basename(inspect.getsourcefile(test.__class__)),
              "ErrorMessage":
                  assert_failures,
              "ErrorStackTrace":
                  unexpected_errors,
          })
      logging.debug("Uploaded results of %s to Appveyor. Response: %s",
                    test_name, resp)

    if not results:
      logging.warning("Failed to find any matching tests for %s.",
                      client.client_id)
      return {}, []

    # Log test results.
    report_lines = self._GenerateReportLines(client_id, results)
    for line in report_lines:
      logging.info(line)
    return results, report_lines

  def _GetClient(self, client_id):
    """Fetches the given client from the GRR API.

    If the client's platform is unknown, an Interrogate flow will be launched,
    and we will keep retrying until the platform is available. Having the
    platform available in the datastore is pre-requisite to many end-to-end
    tests.

    Args:
      client_id: Client's URN.

    Returns:
      An ApiClient object containing data about the client.
    """
    start_time = time.time()

    def DeadlineExceeded():
      return time.time() - start_time > self._api_retry_deadline_secs

    interrogate_launched = False
    while True:
      try:
        client = self._grr_api.Client(client_id).Get()
        if client.data.os_info.system and client.data.knowledge_base.os:
          return client
        if DeadlineExceeded():
          raise E2ETestError("Timeout of %d seconds exceeded for %s." %
                             (self._api_retry_deadline_secs, client.client_id))
        logging.warning("Platform for %s is not yet known to GRR.",
                        client.client_id)
        if not interrogate_launched:
          interrogate_flow = client.CreateFlow(
              name="Interrogate",
              runner_args=self._grr_api.types.CreateFlowRunnerArgs())
          interrogate_launched = True
          logging.info(
              "Launched Interrogate flow (%s) to retrieve system info "
              "from %s.", interrogate_flow.flow_id, client.client_id)
      except requests.ConnectionError as e:
        if DeadlineExceeded():
          raise
        logging.error("Encountered error trying to connect to GRR API: %s",
                      e.args)
      logging.info("Retrying in %d seconds...", self._api_retry_period_secs)
      time.sleep(self._api_retry_period_secs)

  def _GetApplicableTests(self, client):
    """Returns all e2e test methods that should be run against the client."""
    applicable_tests = {}
    for test_class in itervalues(test_base.REGISTRY):
      if client.data.os_info.system not in test_class.platforms:
        continue
      test_suite = unittest.TestLoader().loadTestsFromTestCase(test_class)
      for test in test_suite:
        test_name = "%s.%s" % (test_class.__name__, test._testMethodName)
        if (self._whitelisted_tests and
            test_class.__name__ not in self._whitelisted_tests and
            test_name not in self._whitelisted_tests):
          logging.debug("%s not in whitelist. Skipping for %s.", test_name,
                        client.client_id)
          continue
        elif (test_class.__name__ in self._blacklisted_tests or
              test_name in self._blacklisted_tests):
          logging.debug("%s is explicitly blacklisted. Skipping for %s.",
                        test_name, client.client_id)
          continue
        else:
          applicable_tests[test_name] = test
    return collections.OrderedDict(sorted(iteritems(applicable_tests)))

  def _RetryTest(self, test_name, test, unittest_runner):
    """Runs the given test with the given test runner, retrying on failure."""
    num_attempts = 0
    result = None
    millis_elapsed = None
    while num_attempts < self._max_test_attempts:
      start_time = time.time()
      result = unittest_runner.run(test)
      millis_elapsed = int((time.time() - start_time) * 1000)
      num_attempts += 1
      if result.failures or result.errors:
        attempts_left = self._max_test_attempts - num_attempts
        logging.error("Test %s failed. Attempts left: %d", test_name,
                      attempts_left)
        if attempts_left > 0:
          logging.info("Retrying test after %s seconds.",
                       self._api_retry_period_secs)
          time.sleep(self._api_retry_period_secs)
        continue

      if num_attempts > 1 and self._appveyor_messages_endpoint:
        appveyor_msg = "Flaky test %s passed after %d attempts." % (
            test_name, num_attempts)
        resp = requests.post(
            self._appveyor_messages_endpoint,
            json={
                "message": appveyor_msg,
                "category": "information"
            })
        logging.debug("Uploaded info message for %s to Appveyor. Response: %s",
                      test_name, resp)

      break  # Test passed, no need for retry.

    return result, millis_elapsed

  def _GenerateReportLines(self, client_id, results_dict):
    """Summarizes test results for printing to a terminal/log-file."""
    if not results_dict:
      return []
    report_lines = []
    max_test_name_len = max(len(test_name) for test_name in results_dict)
    report_lines.append("Results for %s:" % client_id)
    for test_name, result in iteritems(results_dict):
      pretty_result = self.LOGFILE_SUCCESS_RESULT
      if result.errors or result.failures:
        pretty_result = self.LOGFILE_FAILURE_RESULT
      # Print a summary line for the test, using left-alignment for the test
      # name and right alignment for the result.
      report_lines.append(
          "\t%s %s" % ((test_name + ":").ljust(max_test_name_len + 1),
                       pretty_result.rjust(10)))
    return report_lines
