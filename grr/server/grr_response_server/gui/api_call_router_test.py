#!/usr/bin/env python
"""Tests for API call routers."""

from absl import app

from grr_response_core.lib.rdfvalues import structs as rdf_structs
from grr_response_proto import tests_pb2
from grr_response_server import access_control
from grr_response_server.gui import api_call_router
from grr.test_lib import test_lib


class SingleMethodDummyApiCallRouter(api_call_router.ApiCallRouter):
  """Dummy ApiCallRouter implementation overriding just a single method."""

  @api_call_router.Http("GET", "/api/foo/bar")
  def SomeRandomMethod(self, args, context=None):
    pass

  def CreateFlow(self, args, context=None):
    pass


class SingleMethodDummyApiCallRouterChild(SingleMethodDummyApiCallRouter):
  pass


class EmptyRouter(api_call_router.ApiCallRouterStub):
  pass


class ApiCallRouterTest(test_lib.GRRBaseTest):
  """Tests for ApiCallRouter."""

  def testAllAnnotatedMethodsAreNotImplemented(self):
    # We can't initialize ApiCallRouter directly because it's abstract.
    router = EmptyRouter()

    for name in api_call_router.ApiCallRouter.GetAnnotatedMethods():
      with self.assertRaises(NotImplementedError):
        getattr(router, name)(None, context=None)

  def testGetAnnotatedMethodsReturnsNonEmptyDict(self):
    methods = api_call_router.ApiCallRouterStub.GetAnnotatedMethods()
    self.assertTrue(methods)

  def testGetAnnotatedMethodsReturnsMethodsFromAllClassesInMroChain(self):
    self.assertIn("SomeRandomMethod",
                  SingleMethodDummyApiCallRouter.GetAnnotatedMethods())
    self.assertIn("SomeRandomMethod",
                  SingleMethodDummyApiCallRouterChild.GetAnnotatedMethods())

  def testHttpUrlParametersMatchArgs(self):
    """Tests that URL params are actual fields of ArgsType in HTTP routes."""

    # Example:
    # @ArgsType(api_client.ApiGetClientArgs)
    # @Http("GET", "/api/clients/<client_id>")

    methods = api_call_router.ApiCallRouterStub.GetAnnotatedMethods()
    for method in methods.values():
      if method.args_type is None:
        continue  # Skip methods like ListOutputPluginDescriptors.

      valid_parameters = method.args_type.type_infos.descriptor_names
      for name in method.GetQueryParamsNames():
        self.assertIn(
            name, valid_parameters,
            "Parameter {} in route {} is not found in {}. "
            "Valid parameters are {}.".format(name, method.name,
                                              method.args_type.__name__,
                                              valid_parameters))

  def testRouterMethodNamesAreInLengthLimit(self):
    for name in api_call_router.ApiCallRouterStub.GetAnnotatedMethods():
      self.assertLessEqual(
          len(name), 128,
          "Router method name {} exceeds MySQL length limit of 128.".format(
              name))


class DisabledApiCallRouterTest(test_lib.GRRBaseTest):
  """Tests for ApiCallRouter."""

  def testRaisesUnauthorizedAccess(self):
    router = api_call_router.DisabledApiCallRouter()

    with self.assertRaises(access_control.UnauthorizedAccess):
      router.SearchClients(None)


class ApiSingleStringArgument(rdf_structs.RDFProtoStruct):
  protobuf = tests_pb2.ApiSingleStringArgument


class RouterMethodMetadataTest(test_lib.GRRBaseTest):
  """Tests for RouterMethodMetadata."""

  def testGetQueryParamsNamesReturnsEmptyListsOnEmptyMetadata(self):
    m = api_call_router.RouterMethodMetadata("SomeMethod")
    self.assertEqual(m.GetQueryParamsNames(), [])

  def testGetQueryParamsNamesReturnsMandaotryParamsCorrectly(self):
    m = api_call_router.RouterMethodMetadata(
        "SomeMethod", http_methods=[("GET", "/a/<arg>/<bar:zoo>", {})])
    self.assertEqual(m.GetQueryParamsNames(), ["arg", "zoo"])

  def testGetQueryParamsNamesReturnsOptionalParamsForGET(self):
    m = api_call_router.RouterMethodMetadata(
        "SomeMethod",
        args_type=ApiSingleStringArgument,
        http_methods=[("GET", "/a/<foo>/<bar:zoo>", {})])
    self.assertEqual(m.GetQueryParamsNames(), ["foo", "zoo", "arg"])

  def testGetQueryParamsNamesReturnsNoOptionalParamsForPOST(self):
    m = api_call_router.RouterMethodMetadata(
        "SomeMethod",
        args_type=ApiSingleStringArgument,
        http_methods=[("POST", "/a/<foo>/<bar:zoo>", {})])
    self.assertEqual(m.GetQueryParamsNames(), ["foo", "zoo"])


def main(argv):
  test_lib.main(argv)


if __name__ == "__main__":
  app.run(main)
