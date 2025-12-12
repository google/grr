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

  @api_call_router.Http("GET", "/api/v2/foo/bar")
  def SomeRandomMethod(self, args, context=None):
    pass

  def CreateFlow(self, args, context=None):
    pass


class DummyRouterWithTypedMethods(api_call_router.ApiCallRouter):
  """Dummy ApiCallRouter implementation overriding just a single method."""

  @api_call_router.ProtoArgsType(tests_pb2.SampleGetHandlerArgs)
  @api_call_router.ProtoResultType(tests_pb2.SampleGetHandlerResult)
  @api_call_router.Http("GET", "/api/path/<path:path>")
  def GetWithProtoTypes(self, args, context=None):
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
    self.assertIn(
        "SomeRandomMethod", SingleMethodDummyApiCallRouter.GetAnnotatedMethods()
    )
    self.assertIn(
        "SomeRandomMethod",
        SingleMethodDummyApiCallRouterChild.GetAnnotatedMethods(),
    )

  def testGetAnnotatedMethodsReturnsProtoTypeInformation(self):
    methods = DummyRouterWithTypedMethods.GetAnnotatedMethods()
    self.assertIn("GetWithProtoTypes", methods)
    metadata = methods["GetWithProtoTypes"]

    self.assertEqual(
        metadata.proto_args_type,
        tests_pb2.SampleGetHandlerArgs,
    )
    self.assertEqual(
        metadata.args_type_url,
        "type.googleapis.com/grr.SampleGetHandlerArgs",
    )
    self.assertEqual(
        metadata.proto_result_type,
        tests_pb2.SampleGetHandlerResult,
    )
    self.assertEqual(
        metadata.result_type_url,
        "type.googleapis.com/grr.SampleGetHandlerResult",
    )

  def testHttpUrlParametersMatchArgs(self):
    """Tests that URL params are actual fields of ProtoArgsType in HTTP routes."""

    # Example:
    # @ProtoArgsType(api_client_pb2.ApiGetClientArgs)
    # @Http("GET", "/api/v2/clients/<client_id>")

    methods = api_call_router.ApiCallRouterStub.GetAnnotatedMethods()
    for method in methods.values():
      if method.proto_args_type is None:
        continue  # Skip methods like ListOutputPluginDescriptors.

      valid_parameters = method.proto_args_type.DESCRIPTOR.fields_by_name.keys()
      for name in method.GetQueryParamsNames():
        self.assertIn(
            name,
            valid_parameters,
            "Parameter {} in route {} is not found in {}. "
            "Valid parameters are {}.".format(
                name,
                method.name,
                method.proto_args_type.__name__,
                valid_parameters,
            ),
        )

  def testRouterMethodNamesAreInLengthLimit(self):
    for name in api_call_router.ApiCallRouterStub.GetAnnotatedMethods():
      self.assertLessEqual(
          len(name),
          128,
          "Router method name {} exceeds MySQL length limit of 128.".format(
              name
          ),
      )


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
        "SomeMethod", http_methods=[("GET", "/a/<arg>/<bar:zoo>")]
    )
    self.assertEqual(m.GetQueryParamsNames(), ["arg", "zoo"])

  def testGetQueryParamsNamesReturnsOptionalParamsForGET(self):
    m = api_call_router.RouterMethodMetadata(
        "SomeMethod",
        proto_args_type=tests_pb2.ApiSingleStringArgument,
        http_methods=[("GET", "/a/<foo>/<bar:zoo>")],
    )
    self.assertEqual(m.GetQueryParamsNames(), ["foo", "zoo", "arg"])

  def testGetQueryParamsNamesReturnsNoOptionalParamsForPOST(self):
    m = api_call_router.RouterMethodMetadata(
        "SomeMethod",
        proto_args_type=tests_pb2.ApiSingleStringArgument,
        http_methods=[("POST", "/a/<foo>/<bar:zoo>")],
    )
    self.assertEqual(m.GetQueryParamsNames(), ["foo", "zoo"])


def main(argv):
  test_lib.main(argv)


if __name__ == "__main__":
  app.run(main)
