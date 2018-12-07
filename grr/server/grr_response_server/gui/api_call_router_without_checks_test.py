#!/usr/bin/env python
"""Tests for ApiCallRouterWithoutChecks."""
from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals


from grr_response_core.lib import flags
from grr_response_server.gui import api_call_handler_base
from grr_response_server.gui import api_call_router

from grr_response_server.gui import api_call_router_without_checks
from grr.test_lib import test_lib


class ApiCallRouterWithoutChecksTest(test_lib.GRRBaseTest):
  """Tests for ApiCallRouterWithoutChecks."""

  def setUp(self):
    super(ApiCallRouterWithoutChecksTest, self).setUp()
    self.router = api_call_router_without_checks.ApiCallRouterWithoutChecks()

  def testAllAnnotatedMethodsReturnHandler(self):
    for name in api_call_router.ApiCallRouter.GetAnnotatedMethods():
      handler = getattr(self.router, name)(None, token=None)
      self.assertIsInstance(handler, api_call_handler_base.ApiCallHandler)


def main(argv):
  test_lib.main(argv)


if __name__ == "__main__":
  flags.StartMain(main)
