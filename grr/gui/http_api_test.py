#!/usr/bin/env python
# -*- mode: python; encoding: utf-8 -*-

"""Tests for HTTP API."""



import json
import urllib2

from grr.gui import api_aff4_object_renderers
from grr.gui import api_call_handler_base
from grr.gui import api_call_router
from grr.gui import http_api

from grr.lib import access_control
from grr.lib import flags
from grr.lib import test_lib
from grr.lib import utils
from grr.lib.rdfvalues import structs as rdf_structs
from grr.proto import tests_pb2


class SampleGetHandlerArgs(rdf_structs.RDFProtoStruct):
  protobuf = tests_pb2.SampleGetHandlerArgs


class SampleGetHandler(api_call_handler_base.ApiCallHandler):

  args_type = SampleGetHandlerArgs

  def Render(self, args, token=None):
    return {
        "method": "GET",
        "path": args.path,
        "foo": args.foo
    }


class SampleGetHandlerWithAdditionalArgsArgs(rdf_structs.RDFProtoStruct):
  protobuf = tests_pb2.SampleGetHandlerWithAdditionalArgsArgs


class SampleGetHandlerWithAdditionalArgs(
    api_call_handler_base.ApiCallHandler):

  args_type = SampleGetHandlerWithAdditionalArgsArgs
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


class SampleStreamingHandler(api_call_handler_base.ApiCallHandler):

  def _Generate(self):
    content_chunks = ["foo", "bar", "blah"]
    for chunk in content_chunks:
      yield chunk

  def Handle(self, unused_args, token=None):
    return api_call_handler_base.ApiBinaryStream(
        "test.ext", content_generator=self._Generate())


class TestHttpApiRouter(api_call_router.ApiCallRouter):
  """Test router with custom methods."""

  @api_call_router.Http("GET", "/test_sample/<path:path>")
  @api_call_router.ArgsType(SampleGetHandlerArgs)
  def SampleGet(self, args, token=None):
    return SampleGetHandler()

  @api_call_router.Http("GET", "/test_sample/raising/<path:path>")
  @api_call_router.ArgsType(SampleGetHandlerArgs)
  def SampleRaisingGet(self, args, token=None):
    raise access_control.UnauthorizedAccess("oh no", subject="aff4:/foo/bar")

  @api_call_router.Http("GET", "/test_sample/streaming")
  @api_call_router.ResultBinaryStream()
  def SampleStreamingGet(self, args, token=None):
    return SampleStreamingHandler()

  @api_call_router.Http("GET", "/test_sample_with_additional_args/<path:path>")
  @api_call_router.ArgsType(SampleGetHandlerWithAdditionalArgsArgs)
  @api_call_router.AdditionalArgsTypes({
      "AFF4Object": api_aff4_object_renderers.ApiAFF4ObjectRendererArgs,
      "RDFValueCollection": (api_aff4_object_renderers.
                             ApiRDFValueCollectionRendererArgs)
  })
  def SampleGetWithAdditionalArgs(self, args, token=None):
    return SampleGetHandlerWithAdditionalArgs()


class RouterMatcherTest(test_lib.GRRBaseTest):
  """Test for RouterMatcher."""

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

  def setUp(self):
    super(RouterMatcherTest, self).setUp()
    self.config_overrider = test_lib.ConfigOverrider(
        {"API.DefaultRouter": TestHttpApiRouter.__name__})
    self.config_overrider.Start()

    self.router_matcher = http_api.RouterMatcher()

  def tearDown(self):
    super(RouterMatcherTest, self).tearDown()
    self.config_overrider.Stop()

  def testReturnsMethodMetadataMatchingUrlAndMethod(self):
    router, method_metadata, router_args = self.router_matcher.MatchRouter(
        self._CreateRequest("GET", "/test_sample/some/path"))
    _ = router
    _ = router_args

    self.assertEqual(method_metadata.name, "SampleGet")

  def testPathParamsAreReturnedWithMatchingHandler(self):
    router, method_metadata, router_args = self.router_matcher.MatchRouter(
        self._CreateRequest("GET", "/test_sample/some/path"))
    _ = router
    _ = method_metadata
    self.assertEqual(router_args, {"path": "some/path"})

  def testRaisesIfNoHandlerMatchesUrl(self):
    self.assertRaises(http_api.ApiCallRouterNotFoundError,
                      self.router_matcher.MatchRouter,
                      self._CreateRequest("GET",
                                          "/some/missing/path"))


class HttpRequestHandlerTest(test_lib.GRRBaseTest):
  """Test for HttpRequestHandler."""

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
    if method in ["GET", "HEAD"]:
      request.GET = query_parameters
    request.META = {}

    return request

  def _RenderResponse(self, request):
    response = http_api.RenderHttpResponse(request)

    if hasattr(response, "content"):
      if response.content.startswith(")]}'\n"):
        response.content = response.content[5:]

    return response

  def setUp(self):
    super(HttpRequestHandlerTest, self).setUp()
    self.config_overrider = test_lib.ConfigOverrider(
        {"API.DefaultRouter": TestHttpApiRouter.__name__})
    self.config_overrider.Start()

    self.request_handler = http_api.HttpRequestHandler()

  def tearDown(self):
    super(HttpRequestHandlerTest, self).tearDown()
    self.config_overrider.Stop()

  def testBuildToken(self):
    request = self._CreateRequest("POST", "/test_sample/some/path")
    request.META["HTTP_X_GRR_REASON"] = urllib2.quote("区最 trailing space ")
    token = self.request_handler.BuildToken(request, 20)
    self.assertEqual(token.reason, utils.SmartUnicode("区最 trailing space "))

  def testRendersGetHandlerCorrectly(self):
    response = self._RenderResponse(
        self._CreateRequest("GET", "/test_sample/some/path"))

    self.assertEqual(
        json.loads(response.content),
        {"method": "GET",
         "path": "some/path",
         "foo": ""})
    self.assertEqual(response.status_code, 200)

  def testHeadRequestHasStubAsABodyOnSuccess(self):
    response = self._RenderResponse(
        self._CreateRequest("HEAD", "/test_sample/some/path"))

    self.assertEqual(json.loads(response.content), {"status": "OK"})
    self.assertEqual(response.status_code, 200)

  def testHeadResponseHasSubjectAndReasonOnUnauthorizedAccess(self):
    response = self._RenderResponse(
        self._CreateRequest("HEAD", "/test_sample/raising/some/path"))

    self.assertEqual(json.loads(response.content),
                     {"message": "Access denied by ACL: oh no",
                      "subject": "aff4:/foo/bar"})
    self.assertEqual(response.status_code, 403)

  def testHeadResponsePutsDataIntoHeadersOnUnauthorizedAccess(self):
    response = self._RenderResponse(
        self._CreateRequest("HEAD", "/test_sample/raising/some/path"))

    headers = dict(response.items())
    self.assertEqual(headers["X-GRR-Unauthorized-Access-Subject"],
                     "aff4:/foo/bar")
    self.assertEqual(headers["X-GRR-Unauthorized-Access-Reason"],
                     "oh no")

  def testBinaryStreamIsCorrectlyStreamedViaGetMethod(self):
    response = self._RenderResponse(
        self._CreateRequest("GET", "/test_sample/streaming"))
    self.assertEqual(list(response.streaming_content),
                     ["foo", "bar", "blah"])

  def testQueryParamsArePassedIntoHandlerArgs(self):
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
    additional_args = self.request_handler.FillAdditionalArgsFromRequest(
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

  def testAdditionalArgumentsAreFoundAndPassedToTheHandler(self):
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
