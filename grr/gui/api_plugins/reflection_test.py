#!/usr/bin/env python
"""This module contains tests for reflection API handlers."""



from grr.gui import api_call_router
from grr.gui import api_test_lib
from grr.gui.api_plugins import reflection as reflection_plugin

from grr.lib import flags
from grr.lib import test_lib

from grr.lib.rdfvalues import structs as rdf_structs

from grr.proto import tests_pb2


class ApiGetRDFValueDescriptorHandlerRegressionTest(
    api_test_lib.ApiCallHandlerRegressionTest):
  """Regression test for ApiGetRDFValueDescriptorHandler."""

  api_method = "GetRDFValueDescriptor"
  handler = reflection_plugin.ApiGetRDFValueDescriptorHandler

  def Run(self):
    self.Check("GET", "/api/reflection/rdfvalue/Duration")
    self.Check("GET", "/api/reflection/rdfvalue/ApiFlow")


class ApiGetRDFValueDescriptorHandlerTest(test_lib.GRRBaseTest):
  """Test for ApiGetRDFValueDescriptorHandler."""

  def testSuccessfullyRendersReflectionDataForAllTypes(self):
    result = reflection_plugin.ApiListRDFValuesDescriptorsHandler().Handle(
        None, token=self.token)
    # TODO(user): enhance this test.
    self.assertTrue(result)


class SampleGetHandlerArgs(rdf_structs.RDFProtoStruct):
  protobuf = tests_pb2.SampleGetHandlerArgs


class DummyApiCallRouter(api_call_router.ApiCallRouter):
  """Dummy ApiCallRouter implementation overrideing just 1 method."""

  @api_call_router.Http("GET", "/api/method1")
  @api_call_router.ArgsType(SampleGetHandlerArgs)
  def SomeRandomMethodWithArgsType(self, args, token=None):
    """Doc 1."""

  @api_call_router.Http("GET", "/api/method2")
  @api_call_router.ResultType(SampleGetHandlerArgs)
  def SomeRandomMethodWithResultType(self, args, token=None):
    """Doc 2."""

  @api_call_router.Http("GET", "/api/method3")
  @api_call_router.ArgsType(SampleGetHandlerArgs)
  @api_call_router.ResultType(SampleGetHandlerArgs)
  def SomeRandomMethodWithArgsTypeAndResultType(self, args, token=None):
    """Doc 3."""


class ApiListApiMethodsHandlerTest(test_lib.GRRBaseTest):
  """Test for ApiListApiMethodsHandler."""

  def setUp(self):
    super(ApiListApiMethodsHandlerTest, self).setUp()
    self.router = DummyApiCallRouter()
    self.handler = reflection_plugin.ApiListApiMethodsHandler(self.router)

  def testRendersMethodWithArgsCorrectly(self):
    result = self.handler.Handle(None, token=self.token)

    method = [item for item in result.items
              if item.name == "SomeRandomMethodWithArgsType"][0]
    self.assertEqual(method.doc, "Doc 1.")

    self.assertEqual(method.args_type_descriptor.name, "SampleGetHandlerArgs")
    self.assertEqual(
        method.args_type_descriptor.AsPrimitiveProto().default.type_url,
        "type.googleapis.com/SampleGetHandlerArgs")

    self.assertEqual(method.result_kind, "NONE")
    self.assertFalse(method.HasField("result_type"))

  def testRendersMethodWithResultTypeCorrectly(self):
    result = self.handler.Handle(None, token=self.token)

    method = [item for item in result.items
              if item.name == "SomeRandomMethodWithResultType"][0]
    self.assertEqual(method.doc, "Doc 2.")

    self.assertFalse(method.HasField("args_type"))

    self.assertEqual(method.result_kind, "VALUE")
    self.assertEqual(method.result_type_descriptor.name, "SampleGetHandlerArgs")
    self.assertEqual(
        method.result_type_descriptor.AsPrimitiveProto().default.type_url,
        "type.googleapis.com/SampleGetHandlerArgs")

  def testRendersMethodWithArgsTypeAndResultTypeCorrectly(self):
    result = self.handler.Handle(None, token=self.token)

    method = [item for item in result.items
              if item.name == "SomeRandomMethodWithArgsTypeAndResultType"][0]
    self.assertEqual(method.doc, "Doc 3.")

    self.assertEqual(method.args_type_descriptor.name, "SampleGetHandlerArgs")
    self.assertEqual(
        method.args_type_descriptor.AsPrimitiveProto().default.type_url,
        "type.googleapis.com/SampleGetHandlerArgs")

    self.assertEqual(method.result_kind, "VALUE")
    self.assertEqual(method.result_type_descriptor.name, "SampleGetHandlerArgs")
    self.assertEqual(
        method.result_type_descriptor.AsPrimitiveProto().default.type_url,
        "type.googleapis.com/SampleGetHandlerArgs")


def main(argv):
  test_lib.main(argv)


if __name__ == "__main__":
  flags.StartMain(main)
