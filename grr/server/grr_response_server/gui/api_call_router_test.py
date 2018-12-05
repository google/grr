#!/usr/bin/env python
"""Tests for API call routers."""
from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals


from grr_response_core.lib import flags

from grr_response_server.gui import api_call_router
from grr.test_lib import test_lib


class SingleMethodDummyApiCallRouter(api_call_router.ApiCallRouter):
  """Dummy ApiCallRouter implementation overriding just a single method."""

  @api_call_router.Http("GET", "/api/foo/bar")
  def SomeRandomMethod(self, args, token=None):
    pass

  def CreateFlow(self, args, token=None):
    pass


class SingleMethodDummyApiCallRouterChild(SingleMethodDummyApiCallRouter):
  pass


class ApiCallRouterTest(test_lib.GRRBaseTest):
  """Tests for ApiCallRouter."""

  def testAllAnnotatedMethodsAreNotImplemented(self):
    # We can't initialize ApiCallRouter directly because it's abstract.
    router = api_call_router.DisabledApiCallRouter()

    for name in api_call_router.ApiCallRouter.GetAnnotatedMethods():
      with self.assertRaises(NotImplementedError):
        getattr(router, name)(None, token=None)

  def testGetAnnotatedMethodsReturnsNonEmptyDict(self):
    methods = api_call_router.ApiCallRouterStub.GetAnnotatedMethods()
    self.assertTrue(methods)

  def testGetAnnotatedMethodsReturnsMethodsFromAllClassesInMroChain(self):
    self.assertIn("SomeRandomMethod",
                  SingleMethodDummyApiCallRouter.GetAnnotatedMethods())
    self.assertIn("SomeRandomMethod",
                  SingleMethodDummyApiCallRouterChild.GetAnnotatedMethods())


class RouterMethodMetadataTest(test_lib.GRRBaseTest):
  """Tests for RouterMethodMetadata."""

  def testGetQueryParamsNamesReturnsEmptyListOnEmptyMetadata(self):
    m = api_call_router.RouterMethodMetadata("SomeMethod")
    self.assertEqual(m.GetQueryParamsNames(), [])

  def testGetQueryParamsNamesWorksCorrectly(self):
    m = api_call_router.RouterMethodMetadata(
        "SomeMethod", http_methods=[("GET", "/a/<foo>/<bar:zoo>", {})])
    self.assertEqual(m.GetQueryParamsNames(), ["foo", "zoo"])


def main(argv):
  test_lib.main(argv)


if __name__ == "__main__":
  flags.StartMain(main)
