#!/usr/bin/env python
"""Tests for API call renderers."""



# pylint: disable=unused-import,g-bad-import-order
from grr.lib import server_plugins
# pylint: enable=unused-import,g-bad-import-order

import json

from grr.gui import api_aff4_object_renderers
from grr.gui import api_call_renderers

from grr.lib import flags
from grr.lib import rdfvalue
from grr.lib import registry
from grr.lib import test_lib
from grr.lib import utils
from grr.proto import tests_pb2


class SampleGetRendererArgs(rdfvalue.RDFProtoStruct):
  protobuf = tests_pb2.SampleGetRendererArgs


class SampleGetRenderer(api_call_renderers.ApiCallRenderer):

  args_type = SampleGetRendererArgs

  def Render(self, args, token=None):
    return {
        "method": "GET",
        "path": args.path,
        "foo": args.foo
    }


class SampleGetRendererWithAdditionalArgsArgs(rdfvalue.RDFProtoStruct):
  protobuf = tests_pb2.SampleGetRendererWithAdditionalArgsArgs


class SampleGetRendererWithAdditionalArgs(api_call_renderers.ApiCallRenderer):

  args_type = SampleGetRendererWithAdditionalArgsArgs
  additional_args_types = {
      "AFF4Object": api_aff4_object_renderers.ApiAFF4ObjectRendererArgs,
      "RDFValueCollection": (api_aff4_object_renderers.
                             ApiRDFValueCollectionRendererArgs)
      }

  def Render(self, args, token=None):
    result = {
        "method": "GET",
        "path": args.path,
        "foo": args.foo
    }

    if args.additional_args:
      rendered_additional_args = []
      for arg in args.additional_args:
        rendered_additional_args.append(str(arg))
      result["additional_args"] = rendered_additional_args

    return result


class TestHttpRoutingInit(registry.InitHook):

  def RunOnce(self):
    api_call_renderers.RegisterHttpRouteHandler(
        "GET", "/test_sample/<path:path>", SampleGetRenderer)
    api_call_renderers.RegisterHttpRouteHandler(
        "GET", "/test_sample_with_additional_args/<path:path>",
        SampleGetRendererWithAdditionalArgs)


class RenderHttpResponseTest(test_lib.GRRBaseTest):
  """Test for api_call_renderers.RenderHttpResponse logic."""

  def _CreateRequest(self, method, path, query_parameters=None):
    if not query_parameters:
      query_parameters = {}

    request = utils.DataObject()
    request.method = method
    request.path = path
    request.scheme = "http"
    request.environ = {
        "SERVER_NAME": "foo.bar",
        "SERVER_PORT": 1234
    }
    request.user = "test"
    if method == "GET":
      request.GET = query_parameters
    request.META = {}

    return request

  def _RenderResponse(self, request):
    response = api_call_renderers.RenderHttpResponse(request)

    if response.content.startswith(")]}'\n"):
      response.content = response.content[5:]

    return response

  def testReturnsRendererMatchingUrlAndMethod(self):
    renderer, _ = api_call_renderers.GetRendererForHttpRequest(
        self._CreateRequest("GET", "/test_sample/some/path"))
    self.assertTrue(isinstance(renderer, SampleGetRenderer))

  def testPathParamsAreReturnedWithMatchingRenderer(self):
    _, path_params = api_call_renderers.GetRendererForHttpRequest(
        self._CreateRequest("GET", "/test_sample/some/path"))
    self.assertEqual(path_params, {"path": "some/path"})

  def testRaisesIfNoRendererMatchesUrl(self):
    self.assertRaises(api_call_renderers.ApiCallRendererNotFoundError,
                      api_call_renderers.GetRendererForHttpRequest,
                      self._CreateRequest("GET",
                                          "/some/missing/path"))

  def testRendersGetRendererCorrectly(self):
    response = self._RenderResponse(
        self._CreateRequest("GET", "/test_sample/some/path"))

    self.assertEqual(
        json.loads(response.content),
        {"method": "GET",
         "path": "some/path",
         "foo": ""})
    self.assertEqual(response.status_code, 200)

  def testQueryParamsArePassedIntoRendererArgs(self):
    response = self._RenderResponse(
        self._CreateRequest("GET", "/test_sample/some/path",
                            query_parameters={"foo": "bar"}))
    self.assertEqual(
        json.loads(response.content),
        {"method": "GET",
         "path": "some/path",
         "foo": "bar"})

  def testRouteArgumentTakesPrecedenceOverQueryParams(self):
    response = self._RenderResponse(
        self._CreateRequest("GET", "/test_sample/some/path",
                            query_parameters={"path": "foobar"}))
    self.assertEqual(
        json.loads(response.content),
        {"method": "GET",
         "path": "some/path",
         "foo": ""})

  def testAdditionalArgumentsAreParsedCorrectly(self):
    additional_args = api_call_renderers.FillAdditionalArgsFromRequest(
        {"AFF4Object.limit_lists": "10",
         "RDFValueCollection.with_total_count": "1"},
        {"AFF4Object": rdfvalue.ApiAFF4ObjectRendererArgs,
         "RDFValueCollection": rdfvalue.ApiRDFValueCollectionRendererArgs})
    additional_args = sorted(additional_args, key=lambda x: x.name)

    self.assertListEqual(
        [x.name for x in additional_args],
        ["AFF4Object", "RDFValueCollection"])
    self.assertListEqual(
        [x.type for x in additional_args],
        ["ApiAFF4ObjectRendererArgs", "ApiRDFValueCollectionRendererArgs"])
    self.assertListEqual(
        [x.args for x in additional_args],
        [rdfvalue.ApiAFF4ObjectRendererArgs(limit_lists=10),
         rdfvalue.ApiRDFValueCollectionRendererArgs(with_total_count=True)])

  def testAdditionalArgumentsAreFoundAndPassedToTheRenderer(self):
    response = self._RenderResponse(
        self._CreateRequest("GET",
                            "/test_sample_with_additional_args/some/path",
                            query_parameters={"foo": "42"}))
    self.assertEqual(
        json.loads(response.content),
        {"method": "GET",
         "path": "some/path",
         "foo": "42"})


def main(argv):
  test_lib.main(argv)


if __name__ == "__main__":
  flags.StartMain(main)
