#!/usr/bin/env python
"""Helper script for running end-to-end tests."""

import getpass
import logging
import os
import unittest

# We need to import the server_plugins module before other server init modules.
# pylint: disable=unused-import,g-bad-import-order
from grr.lib import server_plugins
# pylint: disable=unused-import,g-bad-import-order

from grr import config
from grr_api_client import api
from grr.config import contexts
from grr.lib import config_lib
from grr.lib import flags
from grr.server import access_control
from grr.server import data_store
from grr.server import maintenance_utils
from grr.server import server_startup
from grr_response_test.end_to_end_tests import test_base
# pylint: disable=unused-import
from grr_response_test.end_to_end_tests import tests
# pylint: enable=unused-import


flags.DEFINE_string("api_endpoint", "http://localhost:8000",
                    "GRR API endpoint.")

flags.DEFINE_string("api_user", "admin", "Username for GRR API.")

flags.DEFINE_string("api_password", "", "Password for GRR API.")

flags.DEFINE_list("client_ids", [],
                  "List of client ids to test. If unset we use "
                  "Test.end_to_end_client_ids from the config.")

flags.DEFINE_list("hostnames", [],
                  "List of client hostnames to test. If unset we use "
                  "Test.end_to_end_client_hostnames from the config.")

flags.DEFINE_list("testnames", [],
                  "List of test cases to run. If unset we run all "
                  "tests for a client's platform.")

# We use a logging Filter to exclude noisy unwanted log output.
flags.DEFINE_list("filenames_excluded_from_log", ["connectionpool.py"],
                  "Files whose log messages won't get printed.")

flags.DEFINE_bool("upload_test_binaries", True,
                  "Whether to upload executables needed by some e2e tests.")


def RunEndToEndTests():
  """Runs end-to-end tests against clients using the GRR API."""

  ValidateAllTests()

  logging.info("Connecting to API at %s", flags.FLAGS.api_endpoint)
  password = flags.FLAGS.api_password
  if not password:
    password = getpass.getpass(prompt="Please enter the API password for "
                               "user '%s': " % flags.FLAGS.api_user)
  grr_api = api.InitHttp(
      api_endpoint=flags.FLAGS.api_endpoint,
      auth=(flags.FLAGS.api_user, password))

  logging.info("Fetching client data from the API.")
  target_clients = test_base.GetClientTestTargets(
      grr_api=grr_api,
      client_ids=flags.FLAGS.client_ids,
      hostnames=flags.FLAGS.hostnames)
  if not target_clients:
    raise RuntimeError(
        "No clients to test on. Either pass --client_ids or --hostnames "
        "or check that corresponding clients checked in recently.")

  # Make sure binaries required by tests are uploaded to the datastore.
  if flags.FLAGS.upload_test_binaries:
    api_response = grr_api._context.SendRequest("ListGrrBinaries", None)
    server_paths = {item.path for item in api_response.items}
    UploadBinaryIfAbsent(server_paths, "hello", "linux/test/hello")
    UploadBinaryIfAbsent(server_paths, "hello.exe", "windows/test/hello.exe")

  results_by_client = {}
  max_test_name_len = 0

  logging.info("Running tests against %d clients...", len(target_clients))
  for client in target_clients:
    results_by_client[client.client_id] = RunTestsAgainstClient(grr_api, client)
    for test_name in results_by_client[client.client_id]:
      max_test_name_len = max(max_test_name_len, len(test_name))

  for client_urn, results in results_by_client.iteritems():
    logging.info("Results for %s:", client_urn)
    for test_name, result in sorted(results.items()):
      res = "[  OK  ]"
      if result.errors or result.failures:
        res = "[ FAIL ]"
      # Print a summary line for the test, using left-alignment for the test
      # name and right alignment for the result.
      logging.info("\t%s %s", (test_name + ":").ljust(max_test_name_len + 1),
                   res.rjust(10))


def ValidateAllTests():
  logging.info("Validating %d tests...", len(test_base.REGISTRY))
  for cls in test_base.REGISTRY.values():
    if not cls.platforms:
      raise ValueError(
          "%s: 'platforms' attribute can't be empty" % cls.__name__)

    for p in cls.platforms:
      if p not in test_base.EndToEndTest.Platform.ALL:
        raise ValueError("Unsupported platform: %s in class %s" %
                         (p, cls.__name__))


def UploadBinaryIfAbsent(server_paths, bin_name, server_path):
  if server_path in server_paths:
    return
  logging.info("Binary %s not uploaded yet. Will upload.", server_path)
  package_dir = config_lib.Resource().Filter(
      "grr_response_test@grr-response-test")
  with open(os.path.join(package_dir, "test_data", bin_name), "rb") as f:
    maintenance_utils.UploadSignedConfigBlob(
        f.read(), "aff4:/config/executables/%s" % server_path)


def RunTestsAgainstClient(grr_api, client):
  """Runs all applicable end-to-end tests against a given client.

  Args:
      grr_api: GRR API connection.
      client: grr_api_client.Client

  Returns:
      A dict mapping test-methods to their results.

  Raises:
      RuntimeError: The client's platform isn't known to the GRR server.
  """
  if not client.data.os_info.system:
    raise RuntimeError("Unknown system type for client %s. Likely waiting "
                       "on interrogate to complete." % client.client_id)

  results = {}
  test_base.init_fn = lambda: (grr_api, client)
  test_runner = unittest.TextTestRunner()
  for test_case in test_base.REGISTRY.values():
    if client.data.os_info.system not in test_case.platforms:
      continue

    test_suite = unittest.TestLoader().loadTestsFromTestCase(test_case)
    for test in test_suite:
      test_name = "%s.%s" % (test.__class__.__name__, test._testMethodName)
      if (flags.FLAGS.testnames and
          test_case.__name__ not in flags.FLAGS.testnames and
          test_name not in flags.FLAGS.testnames):
        logging.debug("Skipping test: %s", test_name)
        continue
      logging.info("Running %s on %s (%s: %s, %s, %s)", test_name,
                   client.client_id, client.data.os_info.fqdn,
                   client.data.os_info.system, client.data.os_info.version,
                   client.data.os_info.machine)
      results[test_name] = test_runner.run(test)
  return results


class E2ELogFilter(logging.Filter):
  """Logging filter that excludes log messages for particular files."""

  def filter(self, record):
    return record.filename not in flags.FLAGS.filenames_excluded_from_log


def main(argv):
  del argv  # Unused.
  config.CONFIG.AddContext(contexts.TEST_CONTEXT, "Context for running tests.")
  server_startup.Init()
  for handler in logging.getLogger().handlers:
    handler.addFilter(E2ELogFilter())
  data_store.default_token = access_control.ACLToken(
      username=getpass.getuser(), reason="End-to-end tests")
  return RunEndToEndTests()


if __name__ == "__main__":
  flags.StartMain(main)
