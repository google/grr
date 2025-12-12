#!/usr/bin/env python
"""This module contains tests for reflection API handlers."""

from absl import app

from grr_response_proto import tests_pb2
from grr_response_server.gui import api_call_router
from grr_response_server.gui import api_test_lib
from grr_response_server.gui.api_plugins import reflection as reflection_plugin
from grr.test_lib import test_lib


class DummyApiCallRouter(api_call_router.ApiCallRouter):
  """Dummy ApiCallRouter implementation overriding just 1 method."""

  @api_call_router.Http("GET", "/api/v2/method1")
  @api_call_router.ProtoArgsType(tests_pb2.SampleGetHandlerArgs)
  def SomeRandomMethodWithArgsType(self, args, context=None):
    """Doc 1."""

  @api_call_router.Http("GET", "/api/v2/method2")
  @api_call_router.ProtoResultType(tests_pb2.SampleGetHandlerArgs)
  def SomeRandomMethodWithResultType(self, args, context=None):
    """Doc 2."""

  @api_call_router.Http("GET", "/api/v2/method3")
  @api_call_router.ProtoArgsType(tests_pb2.SampleGetHandlerArgs)
  @api_call_router.ProtoResultType(tests_pb2.SampleGetHandlerArgs)
  def SomeRandomMethodWithArgsTypeAndResultType(self, args, context=None):
    """Doc 3."""


class ApiListApiMethodsHandlerTest(api_test_lib.ApiCallHandlerTest):
  """Test for ApiListApiMethodsHandler."""

  def setUp(self):
    super().setUp()
    self.router = DummyApiCallRouter()
    self.handler = reflection_plugin.ApiListApiMethodsHandler(self.router)

  def testRendersMethodWithArgsCorrectly(self):
    result = self.handler.Handle(None, context=self.context)

    method = [
        item
        for item in result.items
        if item.name == "SomeRandomMethodWithArgsType"
    ][0]
    self.assertEqual(method.doc, "Doc 1.")

    self.assertEqual(
        method.args_type_url,
        "type.googleapis.com/grr.SampleGetHandlerArgs",
    )
    self.assertFalse(method.HasField("result_type_url"))

  def testRendersMethodWithResultTypeCorrectly(self):
    result = self.handler.Handle(None, context=self.context)

    method = [
        item
        for item in result.items
        if item.name == "SomeRandomMethodWithResultType"
    ][0]
    self.assertEqual(method.doc, "Doc 2.")

    self.assertFalse(method.HasField("args_type_url"))
    self.assertEqual(
        method.result_type_url,
        "type.googleapis.com/grr.SampleGetHandlerArgs",
    )

  def testRendersMethodWithArgsTypeAndResultTypeCorrectly(self):
    result = self.handler.Handle(None, context=self.context)

    method = [
        item
        for item in result.items
        if item.name == "SomeRandomMethodWithArgsTypeAndResultType"
    ][0]
    self.assertEqual(method.doc, "Doc 3.")

    self.assertEqual(
        method.args_type_url,
        "type.googleapis.com/grr.SampleGetHandlerArgs",
    )
    self.assertEqual(
        method.result_type_url,
        "type.googleapis.com/grr.SampleGetHandlerArgs",
    )


def main(argv):
  test_lib.main(argv)


if __name__ == "__main__":
  app.run(main)
