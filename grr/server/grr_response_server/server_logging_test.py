#!/usr/bin/env python
"""Tests for logging classes."""
from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

import logging

import time

from werkzeug import wrappers as werkzeug_wrappers

from grr_response_core.lib import flags
from grr_response_core.lib import utils
from grr_response_proto import jobs_pb2
from grr_response_server import server_logging
from grr_response_server.gui import wsgiapp
from grr.test_lib import test_lib


class ApplicationLoggerTests(test_lib.GRRBaseTest):
  """Store tests."""

  def Log(self, msg, *args):
    if args:
      self.log += msg % (args)
    else:
      self.log += msg

  def setUp(self):
    super(ApplicationLoggerTests, self).setUp()

    self.l = server_logging.GrrApplicationLogger()

    self.log = ""
    self.log_stubber = utils.Stubber(logging, "info", self.Log)
    self.log_stubber.Start()

  def tearDown(self):
    super(ApplicationLoggerTests, self).tearDown()

    self.log_stubber.Stop()

  def testGetEventId(self):
    self.assertGreater(
        len(self.l.GetNewEventId()), 20, "Invalid event ID generated")
    self.assertGreater(
        len(self.l.GetNewEventId(int(time.time() * 1e6))), 20,
        "Invalid event ID generated")

  def testLogHttpAdminUIAccess(self):
    request = wsgiapp.HttpRequest({
        "wsgi.url_scheme": "http",
        "SERVER_NAME": "foo.bar",
        "SERVER_PORT": "1234"
    })
    request.user = "testuser"

    response = werkzeug_wrappers.Response(
        status=202,
        headers={
            "X-GRR-Reason": "foo/test1234",
            "X-API-Method": "TestMethod"
        })

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


def main(argv):
  del argv  # Unused.
  test_lib.main()


if __name__ == "__main__":
  flags.StartMain(main)
