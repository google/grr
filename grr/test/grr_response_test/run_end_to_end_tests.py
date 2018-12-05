#!/usr/bin/env python
"""Helper script for running end-to-end tests."""
from __future__ import absolute_import
from __future__ import division

import getpass
import logging
import sys

# We need to import the server_plugins module before other server init modules.
# pylint: disable=unused-import,g-bad-import-order
from grr_response_server import server_plugins
# pylint: disable=unused-import,g-bad-import-order

from grr_response_core import config
from grr_response_core.config import contexts
from grr_response_core.lib import flags
from grr_response_server import access_control
from grr_response_server import data_store
from grr_response_server import server_startup
from grr_response_test.end_to_end_tests import runner

flags.DEFINE_string("api_endpoint", "http://localhost:8000",
                    "GRR API endpoint.")

flags.DEFINE_string("api_user", "admin", "Username for GRR API.")

flags.DEFINE_string("api_password", "", "Password for GRR API.")

flags.DEFINE_string("client_id", "", "Id for client to run tests against.")

flags.DEFINE_list(
    "whitelisted_tests", [],
    "(Optional) comma-separated list of tests to run (skipping all others).")

flags.DEFINE_list(
    "blacklisted_tests", [],
    "(Optional) comma-separated list of tests to skip. Trumps "
    "--whitelisted_tests if there are any conflicts.")

# We use a logging Filter to exclude noisy unwanted log output.
flags.DEFINE_list("filenames_excluded_from_log", ["connectionpool.py"],
                  "Files whose log messages won't get printed.")

flags.DEFINE_bool("upload_test_binaries", True,
                  "Whether to upload executables needed by some e2e tests.")

flags.DEFINE_list(
    "ignore_test_context", False,
    "When set, run_end_to_end_tests doesn't load the config with a "
    "default 'Test Context' added.")


class E2ELogFilter(logging.Filter):
  """Logging filter that excludes log messages for particular files."""

  def filter(self, record):
    return record.filename not in flags.FLAGS.filenames_excluded_from_log


def main(argv):
  del argv  # Unused.

  if not flags.FLAGS.ignore_test_context:
    config.CONFIG.AddContext(contexts.TEST_CONTEXT,
                             "Context for running tests.")

  server_startup.Init()
  for handler in logging.getLogger().handlers:
    handler.addFilter(E2ELogFilter())
  data_store.default_token = access_control.ACLToken(
      username=getpass.getuser(), reason="End-to-end tests")
  test_runner = runner.E2ETestRunner(
      api_endpoint=flags.FLAGS.api_endpoint,
      api_user=flags.FLAGS.api_user,
      api_password=flags.FLAGS.api_password,
      whitelisted_tests=flags.FLAGS.whitelisted_tests,
      blacklisted_tests=flags.FLAGS.blacklisted_tests,
      upload_test_binaries=flags.FLAGS.upload_test_binaries)
  test_runner.Initialize()

  results, _ = test_runner.RunTestsAgainstClient(flags.FLAGS.client_id)
  # Exit with a non-0 error code if one of the tests failed.
  for r in results.values():
    if r.errors or r.failures:
      sys.exit(1)


if __name__ == "__main__":
  flags.StartMain(main)
