#!/usr/bin/env python
"""Tests for ApiCallRouterWithoutChecks."""




from grr.gui import api_call_handler_base
from grr.gui import api_call_router
from grr.gui import api_call_router_without_checks

from grr.lib import flags
from grr.lib import test_lib


class ApiCallRouterWithoutChecksTest(test_lib.GRRBaseTest):
  """Tests for ApiCallRouterWithoutChecks."""

  def setUp(self):
    super(ApiCallRouterWithoutChecksTest, self).setUp()
    self.router = api_call_router_without_checks.ApiCallRouterWithoutChecks()

  def testAllAnnotatedMethodsReturnHandler(self):
    for name in api_call_router.ApiCallRouter.GetAnnotatedMethods():
      handler = getattr(self.router, name)(None, token=None)
      self.assertTrue(isinstance(handler, api_call_handler_base.ApiCallHandler))


def main(argv):
  test_lib.main(argv)


if __name__ == "__main__":
  flags.StartMain(main)
