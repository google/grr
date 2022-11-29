#!/usr/bin/env python
"""Helper script for running end-to-end tests."""

import logging
import sys

from absl import app
from absl import flags

# We need to import the server_plugins module before other server init modules.
# pylint: disable=unused-import,g-bad-import-order
from grr_response_server import server_plugins
# pylint: disable=unused-import,g-bad-import-order

from grr_response_core import config
from grr_response_core.config import contexts
from grr_response_server import server_startup
from grr_response_test.end_to_end_tests import runner

_API_ENDPOINT = flags.DEFINE_string("api_endpoint", "http://localhost:8000",
                                    "GRR API endpoint.")

_API_USER = flags.DEFINE_string("api_user", "admin", "Username for GRR API.")

_API_PASSWORD = flags.DEFINE_string("api_password", "", "Password for GRR API.")

_CLIENT_ID = flags.DEFINE_string("client_id", "",
                                 "Id for client to run tests against.")

_RUN_ONLY_TESTS = flags.DEFINE_list(
    "run_only_tests", [],
    "(Optional) comma-separated list of tests to run (skipping all others).")

_SKIP_TESTS = flags.DEFINE_list(
    "skip_tests", [], "(Optional) comma-separated list of tests to skip.")

flags.DEFINE_list(
    name="manual_tests",
    default=[],
    help="(optional) A comma-separated list of manual tests to run.",
)

# We use a logging Filter to exclude noisy unwanted log output.
_FILENAMES_EXCLUDED_FROM_LOG = flags.DEFINE_list(
    "filenames_excluded_from_log", ["connectionpool.py"],
    "Files whose log messages won't get printed.")

_UPLOAD_TEST_BINARIES = flags.DEFINE_bool(
    "upload_test_binaries", True,
    "Whether to upload executables needed by some e2e tests.")

_IGNORE_TEST_CONTEXT = flags.DEFINE_list(
    "ignore_test_context", False,
    "When set, run_end_to_end_tests doesn't load the config with a "
    "default 'Test Context' added.")


class E2ELogFilter(logging.Filter):
  """Logging filter that excludes log messages for particular files."""

  def filter(self, record):
    return record.filename not in _FILENAMES_EXCLUDED_FROM_LOG.value


def main(argv):
  del argv  # Unused.

  if not _IGNORE_TEST_CONTEXT.value:
    config.CONFIG.AddContext(contexts.TEST_CONTEXT,
                             "Context for running tests.")

  server_startup.Init()
  for handler in logging.getLogger().handlers:
    handler.addFilter(E2ELogFilter())
    handler.setLevel(logging.INFO)

  test_runner = runner.E2ETestRunner(
      api_endpoint=_API_ENDPOINT.value,
      api_user=_API_USER.value,
      api_password=_API_PASSWORD.value,
      run_only_tests=_RUN_ONLY_TESTS.value,
      skip_tests=_SKIP_TESTS.value,
      manual_tests=flags.FLAGS.manual_tests,
      upload_test_binaries=_UPLOAD_TEST_BINARIES.value)
  test_runner.Initialize()

  results, _ = test_runner.RunTestsAgainstClient(_CLIENT_ID.value)
  # Exit with a non-0 error code if one of the tests failed.
  for r in results.values():
    if r.errors or r.failures:
      sys.exit(1)


if __name__ == "__main__":
  app.run(main)
