#!/usr/bin/env python
# -*- mode: python; encoding: utf-8 -*-

"""Tests for HTTP API."""



import json
import urllib2

from grr.gui import api_aff4_object_renderers
from grr.gui import api_call_renderer_base
from grr.gui import api_call_renderers
from grr.gui import http_api

from grr.lib import flags
from grr.lib import registry
from grr.lib import test_lib
from grr.lib import utils
from grr.lib.rdfvalues import structs as rdf_structs
from grr.proto import tests_pb2


class SampleGetRendererArgs(rdf_structs.RDFProtoStruct):
  protobuf = tests_pb2.SampleGetRendererArgs


class SampleGetRenderer(api_call_renderer_base.ApiCallRenderer):

  args_type = SampleGetRendererArgs

  def Render(self, args, token=None):
    return {
        "method": "GET",
        "path": args.path,
        "foo": args.foo
    }


class SampleGetRendererWithAdditionalArgsArgs(rdf_structs.RDFProtoStruct):
  protobuf = tests_pb2.SampleGetRendererWithAdditionalArgsArgs


class SampleGetRendererWithAdditionalArgs(
    api_call_renderer_base.ApiCallRenderer):

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
    http_api.RegisterHttpRouteHandler(
        "GET", "/test_sample/<path:path>", SampleGetRenderer)
    http_api.RegisterHttpRouteHandler(
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
    response = http_api.RenderHttpResponse(request)

    if response.content.startswith(")]}'\n"):
      response.content = response.content[5:]

    return response

  def testBuildToken(self):
    request = self._CreateRequest("POST", "/test_sample/some/path")
    request.META["HTTP_X_GRR_REASON"] = urllib2.quote("区最 trailing space ")
    token = http_api.BuildToken(request, 20)
    self.assertEqual(token.reason, utils.SmartUnicode("区最 trailing space "))

  def testReturnsRendererMatchingUrlAndMethod(self):
    renderer, _ = http_api.GetRendererForHttpRequest(
        self._CreateRequest("GET", "/test_sample/some/path"))
    self.assertTrue(isinstance(renderer, SampleGetRenderer))

  def testPathParamsAreReturnedWithMatchingRenderer(self):
    _, path_params = http_api.GetRendererForHttpRequest(
        self._CreateRequest("GET", "/test_sample/some/path"))
    self.assertEqual(path_params, {"path": "some/path"})

  def testRaisesIfNoRendererMatchesUrl(self):
    self.assertRaises(api_call_renderers.ApiCallRendererNotFoundError,
                      http_api.GetRendererForHttpRequest,
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
    additional_args = http_api.FillAdditionalArgsFromRequest(
        {
            "AFF4Object.limit_lists": "10",
            "RDFValueCollection.with_total_count": "1"
        }, {
            "AFF4Object": api_aff4_object_renderers.ApiAFF4ObjectRendererArgs,
            "RDFValueCollection":
            api_aff4_object_renderers.ApiRDFValueCollectionRendererArgs
        })
    additional_args = sorted(additional_args, key=lambda x: x.name)

    self.assertListEqual(
        [x.name for x in additional_args],
        ["AFF4Object", "RDFValueCollection"])
    self.assertListEqual(
        [x.type for x in additional_args],
        ["ApiAFF4ObjectRendererArgs", "ApiRDFValueCollectionRendererArgs"])
    self.assertListEqual(
        [x.args for x in additional_args],
        [api_aff4_object_renderers.ApiAFF4ObjectRendererArgs(limit_lists=10),
         api_aff4_object_renderers.ApiRDFValueCollectionRendererArgs(
             with_total_count=True)])

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
