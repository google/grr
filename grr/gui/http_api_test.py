#!/usr/bin/env python
# -*- mode: python; encoding: utf-8 -*-
"""Tests for HTTP API."""



import json
import urllib2

from grr.gui import api_auth_manager
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
    return {"method": "GET", "path": args.path, "foo": args.foo}


class SampleStreamingHandler(api_call_handler_base.ApiCallHandler):

  def _Generate(self):
    content_chunks = ["foo", "bar", "blah"]
    for chunk in content_chunks:
      yield chunk

  def Handle(self, unused_args, token=None):
    return api_call_handler_base.ApiBinaryStream(
        "test.ext",
        content_generator=self._Generate(),
        content_length=1337)


class SampleDeleteHandlerArgs(rdf_structs.RDFProtoStruct):
  protobuf = tests_pb2.SampleDeleteHandlerArgs


class SampleDeleteHandler(api_call_handler_base.ApiCallHandler):

  args_type = SampleDeleteHandlerArgs

  def Render(self, args, token=None):
    return {"method": "DELETE", "resource": args.resource_id}


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

  @api_call_router.Http("DELETE", "/test_resource/<resource_id>")
  @api_call_router.ArgsType(SampleDeleteHandlerArgs)
  def SampleDelete(self, args, token=None):
    return SampleDeleteHandler()

  @api_call_router.Http("GET", "/failure/not-found")
  def FailureNotFound(self, args, token=None):
    raise api_call_handler_base.ResourceNotFoundError()

  @api_call_router.Http("GET", "/failure/server-error")
  def FailureServerError(self, args, token=None):
    raise RuntimeError("Some error")

  @api_call_router.Http("GET", "/failure/not-implemented")
  def FailureNotImplemented(self, args, token=None):
    raise NotImplementedError()

  @api_call_router.Http("GET", "/failure/unauthorized")
  def FailureUnauthorized(self, args, token=None):
    raise access_control.UnauthorizedAccess("oh no")


class RouterMatcherTest(test_lib.GRRBaseTest):
  """Test for RouterMatcher."""

  def _CreateRequest(self, method, path, query_parameters=None):
    if not query_parameters:
      query_parameters = {}

    request = utils.DataObject()
    request.method = method
    request.path = path
    request.scheme = "http"
    request.environ = {"SERVER_NAME": "foo.bar", "SERVER_PORT": 1234}
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
    # Make sure ApiAuthManager is initialized with this configuration setting.
    api_auth_manager.APIACLInit.InitApiAuthManager()

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
                      self._CreateRequest("GET", "/some/missing/path"))


class HttpRequestHandlerTest(test_lib.GRRBaseTest):
  """Test for HttpRequestHandler."""

  def _CreateRequest(self,
                     method,
                     path,
                     username="test",
                     query_parameters=None):
    if not query_parameters:
      query_parameters = {}

    request = utils.DataObject()
    request.method = method
    request.path = path
    request.scheme = "http"
    request.environ = {"SERVER_NAME": "foo.bar", "SERVER_PORT": 1234}
    request.user = username
    if method in ["GET", "HEAD", "DELETE"]:
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
    # Make sure ApiAuthManager is initialized with this configuration setting.
    api_auth_manager.APIACLInit.InitApiAuthManager()

    self.request_handler = http_api.HttpRequestHandler()

  def tearDown(self):
    super(HttpRequestHandlerTest, self).tearDown()
    self.config_overrider.Stop()

  def testBuildToken(self):
    request = self._CreateRequest("POST", "/test_sample/some/path")
    request.META["HTTP_X_GRR_REASON"] = urllib2.quote("区最 trailing space ")
    token = self.request_handler.BuildToken(request, 20)
    self.assertEqual(token.reason, utils.SmartUnicode("区最 trailing space "))

  def testSystemUsernameIsNotAllowed(self):
    response = self._RenderResponse(self._CreateRequest(
        "GET", "/test_sample/some/path",
        username="GRR"))
    self.assertEqual(response.status_code, 403)

  def testRendersGetHandlerCorrectly(self):
    response = self._RenderResponse(self._CreateRequest(
        "GET", "/test_sample/some/path"))

    self.assertEqual(
        json.loads(response.content), {"method": "GET",
                                       "path": "some/path",
                                       "foo": ""})
    self.assertEqual(response.status_code, 200)

  def testHeadRequestHasStubAsABodyOnSuccess(self):
    response = self._RenderResponse(self._CreateRequest(
        "HEAD", "/test_sample/some/path"))

    self.assertEqual(json.loads(response.content), {"status": "OK"})
    self.assertEqual(response.status_code, 200)

  def testHeadResponseHasSubjectAndReasonOnUnauthorizedAccess(self):
    response = self._RenderResponse(self._CreateRequest(
        "HEAD", "/test_sample/raising/some/path"))

    self.assertEqual(
        json.loads(response.content), {"message": "Access denied by ACL: oh no",
                                       "subject": "aff4:/foo/bar"})
    self.assertEqual(response.status_code, 403)

  def testHeadResponsePutsDataIntoHeadersOnUnauthorizedAccess(self):
    response = self._RenderResponse(self._CreateRequest(
        "HEAD", "/test_sample/raising/some/path"))

    headers = dict(response.items())
    self.assertEqual(headers["X-GRR-Unauthorized-Access-Subject"],
                     "aff4:/foo/bar")
    self.assertEqual(headers["X-GRR-Unauthorized-Access-Reason"], "oh no")

  def testBinaryStreamIsCorrectlyStreamedViaGetMethod(self):
    response = self._RenderResponse(self._CreateRequest(
        "GET", "/test_sample/streaming"))

    headers = dict(response.items())
    self.assertEqual(list(response.streaming_content), ["foo", "bar", "blah"])
    self.assertEqual(headers["Content-Length"], "1337")

  def testBinaryStreamReturnsContentLengthViaHeadMethod(self):
    response = self._RenderResponse(self._CreateRequest(
        "HEAD", "/test_sample/streaming"))

    headers = dict(response.items())
    self.assertEqual(headers["Content-Length"], "1337")

  def testQueryParamsArePassedIntoHandlerArgs(self):
    response = self._RenderResponse(self._CreateRequest(
        "GET", "/test_sample/some/path",
        query_parameters={"foo": "bar"}))
    self.assertEqual(
        json.loads(response.content), {"method": "GET",
                                       "path": "some/path",
                                       "foo": "bar"})

  def testRouteArgumentTakesPrecedenceOverQueryParams(self):
    response = self._RenderResponse(self._CreateRequest(
        "GET",
        "/test_sample/some/path",
        query_parameters={"path": "foobar"}))
    self.assertEqual(
        json.loads(response.content), {"method": "GET",
                                       "path": "some/path",
                                       "foo": ""})

  def testRendersDeleteHandlerCorrectly(self):
    response = self._RenderResponse(self._CreateRequest(
        "DELETE", "/test_resource/R:123456"))

    self.assertEqual(
        json.loads(response.content), {"method": "DELETE",
                                       "resource": "R:123456"})
    self.assertEqual(response.status_code, 200)

  def testStatsAreCorrectlyUpdatedOnHeadRequests(self):
    with self.assertStatsCounterDelta(
        1, "api_access_probe_latency",
        fields=["SampleGet", "http", "SUCCESS"]), \
    self.assertStatsCounterDelta(
        0, "api_access_probe_latency",
        fields=["SampleGet", "http", "FORBIDDEN"]), \
    self.assertStatsCounterDelta(
        0, "api_access_probe_latency",
        fields=["SampleGet", "http", "NOT_FOUND"]), \
    self.assertStatsCounterDelta(
        0, "api_access_probe_latency",
        fields=["SampleGet", "http", "NOT_IMPLEMENTED"]), \
    self.assertStatsCounterDelta(
        0, "api_access_probe_latency",
        fields=["SampleGet", "http", "SERVER_ERROR"]):

      self._RenderResponse(self._CreateRequest("HEAD",
                                               "/test_sample/some/path"))

  def testStatsAreCorrectlyUpdatedOnGetRequests(self):
    with self.assertStatsCounterDelta(
        1, "api_method_latency",
        fields=["SampleGet", "http", "SUCCESS"]), \
    self.assertStatsCounterDelta(
        0, "api_method_latency",
        fields=["SampleGet", "http", "FORBIDDEN"]), \
    self.assertStatsCounterDelta(
        0, "api_method_latency",
        fields=["SampleGet", "http", "NOT_FOUND"]), \
    self.assertStatsCounterDelta(
        0, "api_method_latency",
        fields=["SampleGet", "http", "NOT_IMPLEMENTED"]), \
    self.assertStatsCounterDelta(
        0, "api_method_latency",
        fields=["SampleGet", "http", "SERVER_ERROR"]):

      self._RenderResponse(self._CreateRequest("GET", "/test_sample/some/path"))

  def testStatsAreCorrectlyUpdatedOnVariousStatusCodes(self):

    def CheckMethod(url, method_name, status):
      with self.assertStatsCounterDelta(
          status == "SUCCESS" and 1 or 0,
          "api_method_latency",
          fields=[method_name, "http", "SUCCESS"]), \
      self.assertStatsCounterDelta(
          status == "FORBIDDEN" and 1 or 0,
          "api_method_latency",
          fields=[method_name, "http", "FORBIDDEN"]), \
      self.assertStatsCounterDelta(
          status == "NOT_FOUND" and 1 or 0,
          "api_method_latency",
          fields=[method_name, "http", "NOT_FOUND"]), \
      self.assertStatsCounterDelta(
          status == "NOT_IMPLEMENTED" and 1 or 0,
          "api_method_latency",
          fields=[method_name, "http", "NOT_IMPLEMENTED"]), \
      self.assertStatsCounterDelta(
          status == "SERVER_ERROR" and 1 or 0,
          "api_method_latency",
          fields=[method_name, "http", "SERVER_ERROR"]):

        self._RenderResponse(self._CreateRequest("GET", url))

    CheckMethod("/failure/not-found", "FailureNotFound", "NOT_FOUND")
    CheckMethod("/failure/server-error", "FailureServerError", "SERVER_ERROR")
    CheckMethod("/failure/not-implemented", "FailureNotImplemented",
                "NOT_IMPLEMENTED")
    CheckMethod("/failure/unauthorized", "FailureUnauthorized", "FORBIDDEN")


def main(argv):
  test_lib.main(argv)


if __name__ == "__main__":
  flags.StartMain(main)
