#!/usr/bin/env python
"""Tests for logging classes."""

import logging
import time
from unittest import mock

from absl import app

from grr_response_core.stats import default_stats_collector
from grr_response_core.stats import metrics
from grr_response_proto import jobs_pb2
from grr_response_server import server_logging
from grr_response_server.gui import api_call_context
from grr_response_server.gui import http_request
from grr_response_server.gui import http_response
from grr.test_lib import acl_test_lib
from grr.test_lib import stats_test_lib
from grr.test_lib import test_lib


class ApplicationLoggerTests(test_lib.GRRBaseTest):
  """Store tests."""

  def Log(self, msg, *args):
    if args:
      self.log += msg % (args)
    else:
      self.log += msg

  def setUp(self):
    super().setUp()

    self.l = server_logging.GrrApplicationLogger()

    self.log = ""
    log_stubber = mock.patch.object(logging, "info", self.Log)
    log_stubber.start()
    self.addCleanup(log_stubber.stop)

  def testGetEventId(self):
    self.assertGreater(
        len(self.l.GetNewEventId()), 20, "Invalid event ID generated"
    )
    self.assertGreater(
        len(self.l.GetNewEventId(int(time.time() * 1e6))),
        20,
        "Invalid event ID generated",
    )

  def testLogHttpAdminUIAccess(self):
    request = http_request.HttpRequest({
        "wsgi.url_scheme": "http",
        "SERVER_NAME": "foo.bar",
        "SERVER_PORT": "1234",
    })
    request.user = "testuser"

    response = http_response.HttpResponse(
        status=202,
        headers={"X-API-Method": "TestMethod"},
        context=api_call_context.ApiCallContext(
            username=request.user,
            approval=acl_test_lib.BuildClientApprovalRequest(
                reason="foo/test1234", requestor_username=request.user
            ),
        ),
    )

    self.l.LogHttpAdminUIAccess(request, response)
    self.assertIn("foo/test1234", self.log)

  def testLogHttpFrontendAccess(self):
    request = self._GenHttpRequestProto()

    self.l.LogHttpFrontendAccess(request)
    self.assertIn("/test?omg=11%45x%20%20", self.log)

  def _GenHttpRequestProto(self):
    """Create a valid request object."""
    request = jobs_pb2.HttpRequest()
    request.source_ip = "127.0.0.1"
    request.user_agent = "Firefox or something"
    request.url = "http://test.com/test?omg=11%45x%20%20"
    request.user = "anonymous"
    request.timestamp = int(time.time() * 1e6)
    request.size = 1000
    return request


class ErrorLogHandlerTests(stats_test_lib.StatsCollectorTestMixin):
  """Store tests."""

  def _SetupTestLogger(self, unique_name: str) -> logging.Logger:
    test_logger = logging.getLogger(unique_name)
    error_log_handler = server_logging.ErrorLogsHandler()

    test_logger.addHandler(error_log_handler)
    self.addCleanup(lambda: test_logger.removeHandler(error_log_handler))

    return test_logger

  def testErrorLogHandlerWorks(self):
    # Get logger unique to this test
    test_logger = self._SetupTestLogger(self.testErrorLogHandlerWorks.__name__)

    with self.SetUpStatsCollector(
        default_stats_collector.DefaultStatsCollector()
    ):
      fake_counter = metrics.Counter(
          "fake",
          fields=[
              ("level", str),
          ],
      )

    with mock.patch.object(server_logging, "LOG_CALLS_COUNTER", fake_counter):
      # Make sure counter is set to zero
      self.assertEqual(0, fake_counter.GetValue(fields=["ERROR"]))
      self.assertEqual(0, fake_counter.GetValue(fields=["CRITICAL"]))

      # Log an error
      test_logger.error("oh no!")
      self.assertEqual(1, fake_counter.GetValue(fields=["ERROR"]))
      self.assertEqual(0, fake_counter.GetValue(fields=["CRITICAL"]))

      # Log an exception
      test_logger.exception("not again!")
      self.assertEqual(2, fake_counter.GetValue(fields=["ERROR"]))
      self.assertEqual(0, fake_counter.GetValue(fields=["CRITICAL"]))

      # Log critical error
      test_logger.critical("I give up!")
      self.assertEqual(2, fake_counter.GetValue(fields=["ERROR"]))
      self.assertEqual(1, fake_counter.GetValue(fields=["CRITICAL"]))


def main(argv):
  del argv  # Unused.
  test_lib.main()


if __name__ == "__main__":
  app.run(main)
