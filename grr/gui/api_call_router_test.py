#!/usr/bin/env python
"""Tests for API call routers."""




from grr.gui import api_call_router

from grr.lib import flags
from grr.lib import test_lib


class DummyApiCallRouter(api_call_router.ApiCallRouter):
  """Dummy ApiCallRouter implementation overrideing just 1 method."""

  @api_call_router.Http("GET", "/api/foo/bar")
  def SomeRandomMethod(self, args, token=None):
    pass

  def CreateFlow(self, args, token=None):
    pass


class DummyApiCallRouterChild(DummyApiCallRouter):
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
    methods = api_call_router.ApiCallRouter.GetAnnotatedMethods()
    self.assertTrue(methods)

  def testGetAnnotatedMethodsReturnsMethodsFromAllClassesInMroChain(self):
    self.assertTrue("SomeRandomMethod" in
                    DummyApiCallRouter.GetAnnotatedMethods())
    self.assertTrue("SomeRandomMethod" in
                    DummyApiCallRouterChild.GetAnnotatedMethods())


def main(argv):
  test_lib.main(argv)


if __name__ == "__main__":
  flags.StartMain(main)
