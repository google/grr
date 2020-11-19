#!/usr/bin/env python
# Lint as: python3
# -*- encoding: utf-8 -*-
"""Tests for HTTP API."""
from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

from absl import app
import mock

from grr_response_core.lib.rdfvalues import structs as rdf_structs
from grr_response_core.lib.util import compatibility
from grr_response_core.lib.util.compat import json
from grr_response_proto import tests_pb2
from grr_response_server import access_control

from grr_response_server import data_store
from grr_response_server.databases import db
from grr_response_server.gui import api_auth_manager
from grr_response_server.gui import api_call_handler_base
from grr_response_server.gui import api_call_router
from grr_response_server.gui import api_test_lib
from grr_response_server.gui import http_api
from grr.test_lib import stats_test_lib
from grr.test_lib import test_lib


class SampleGetHandlerResult(rdf_structs.RDFProtoStruct):
  protobuf = tests_pb2.SampleGetHandlerResult


class SampleGetHandler(api_call_handler_base.ApiCallHandler):

  args_type = api_test_lib.SampleGetHandlerArgs
  result_type = SampleGetHandlerResult

  def Handle(self, args, context=None):
    return SampleGetHandlerResult(method="GET", path=args.path, foo=args.foo)


class SampleStreamingHandler(api_call_handler_base.ApiCallHandler):

  def _Generate(self):
    content_chunks = ["foo", "bar", "blah"]
    for chunk in content_chunks:
      yield chunk

  def Handle(self, unused_args, context=None):
    return api_call_handler_base.ApiBinaryStream(
        "test.ext", content_generator=self._Generate(), content_length=1337)


class SampleDeleteHandlerArgs(rdf_structs.RDFProtoStruct):
  protobuf = tests_pb2.SampleDeleteHandlerArgs


class SampleDeleteHandlerResult(rdf_structs.RDFProtoStruct):
  protobuf = tests_pb2.SampleDeleteHandlerResult


class SampleDeleteHandler(api_call_handler_base.ApiCallHandler):

  args_type = SampleDeleteHandlerArgs
  result_type = SampleDeleteHandlerResult

  def Handle(self, args, context=None):
    return SampleDeleteHandlerResult(method="DELETE", resource=args.resource_id)


class SamplePatchHandlerArgs(rdf_structs.RDFProtoStruct):
  protobuf = tests_pb2.SamplePatchHandlerArgs


class SamplePatchHandlerResult(rdf_structs.RDFProtoStruct):
  protobuf = tests_pb2.SamplePatchHandlerResult


class SamplePatchHandler(api_call_handler_base.ApiCallHandler):

  args_type = SamplePatchHandlerArgs
  result_type = SamplePatchHandlerResult

  def Handle(self, args, context=None):
    return SamplePatchHandlerResult(method="PATCH", resource=args.resource_id)


class TestHttpApiRouter(api_call_router.ApiCallRouter):
  """Test router with custom methods."""

  @api_call_router.Http("GET", "/test_sample/<path:path>")
  @api_call_router.ArgsType(api_test_lib.SampleGetHandlerArgs)
  @api_call_router.ResultType(SampleGetHandlerResult)
  def SampleGet(self, args, context=None):
    return SampleGetHandler()

  @api_call_router.Http("GET", "/test_sample/raising/<path:path>")
  @api_call_router.ArgsType(api_test_lib.SampleGetHandlerArgs)
  @api_call_router.ResultType(SampleGetHandlerResult)
  def SampleRaisingGet(self, args, context=None):
    raise access_control.UnauthorizedAccess("oh no", subject="aff4:/foo/bar")

  @api_call_router.Http("GET", "/test_sample/streaming")
  @api_call_router.ResultBinaryStream()
  def SampleStreamingGet(self, args, context=None):
    return SampleStreamingHandler()

  @api_call_router.Http("DELETE", "/test_resource/<resource_id>")
  @api_call_router.ArgsType(SampleDeleteHandlerArgs)
  @api_call_router.ResultType(SampleDeleteHandlerResult)
  def SampleDelete(self, args, context=None):
    return SampleDeleteHandler()

  @api_call_router.Http("PATCH", "/test_resource/<resource_id>")
  @api_call_router.ArgsType(SamplePatchHandlerArgs)
  @api_call_router.ResultType(SamplePatchHandlerResult)
  def SamplePatch(self, args, context=None):
    return SamplePatchHandler()

  @api_call_router.Http("GET", "/failure/not-found")
  def FailureNotFound(self, args, context=None):
    raise api_call_handler_base.ResourceNotFoundError()

  @api_call_router.Http("GET", "/failure/server-error")
  def FailureServerError(self, args, context=None):
    raise RuntimeError("Some error")

  @api_call_router.Http("GET", "/failure/not-implemented")
  def FailureNotImplemented(self, args, context=None):
    raise NotImplementedError()

  @api_call_router.Http("GET", "/failure/unauthorized")
  def FailureUnauthorized(self, args, context=None):
    raise access_control.UnauthorizedAccess("oh no")

  @api_call_router.Http("GET", "/failure/resource-exhausted")
  def FailureResourceExhausted(self, args, context=None):
    raise api_call_handler_base.ResourceExhaustedError("exhausted")

  @api_call_router.Http("GET", "/failure/invalid-argument")
  def FailureInvalidArgument(self, args, context=None):
    raise ValueError("oh no")


class RouterMatcherTest(test_lib.GRRBaseTest):
  """Test for RouterMatcher."""

  def _CreateRequest(self, method, path, query_parameters=None):
    request = mock.MagicMock()
    request.method = method
    request.path = path
    request.scheme = "http"
    request.environ = {"SERVER_NAME": "foo.bar", "SERVER_PORT": 1234}
    request.user = u"test"
    request.email = None
    request.args = query_parameters or {}
    request.headers = {}
    request.get_data = lambda as_text=False: ""

    return request

  def setUp(self):
    super(RouterMatcherTest, self).setUp()
    config_overrider = test_lib.ConfigOverrider({
        "API.DefaultRouter": compatibility.GetName(TestHttpApiRouter),
    })
    config_overrider.Start()
    self.addCleanup(config_overrider.Stop)

    # Make sure ApiAuthManager is initialized with this configuration setting.
    api_auth_manager.InitializeApiAuthManager()

    self.router_matcher = http_api.RouterMatcher()

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
    self.assertEqual(router_args,
                     api_test_lib.SampleGetHandlerArgs(path="some/path"))

  def testRaisesIfNoHandlerMatchesUrl(self):
    self.assertRaises(http_api.ApiCallRouterNotFoundError,
                      self.router_matcher.MatchRouter,
                      self._CreateRequest("GET", "/some/missing/path"))


class HttpRequestHandlerTest(test_lib.GRRBaseTest,
                             stats_test_lib.StatsTestMixin):
  """Test for HttpRequestHandler."""

  def _CreateRequest(self,
                     method,
                     path,
                     username=u"test",
                     query_parameters=None):
    request = mock.MagicMock()
    request.method = method
    request.path = path
    request.scheme = "http"
    request.environ = {"SERVER_NAME": "foo.bar", "SERVER_PORT": 1234}
    request.user = username
    request.email = None
    request.args = query_parameters or {}
    request.content_type = "application/json; charset=utf-8"
    request.headers = {}
    request.get_data = lambda as_text=False: ""

    return request

  def _RenderResponse(self, request):
    return http_api.RenderHttpResponse(request)

  def _GetResponseContent(self, response):
    content = response.get_data(as_text=True)
    if content.startswith(")]}'\n"):
      content = content[5:]

    return json.Parse(content)

  def setUp(self):
    super(HttpRequestHandlerTest, self).setUp()

    config_overrider = test_lib.ConfigOverrider({
        "API.DefaultRouter": compatibility.GetName(TestHttpApiRouter),
    })
    config_overrider.Start()
    self.addCleanup(config_overrider.Stop)
    # Make sure ApiAuthManager is initialized with this configuration setting.
    api_auth_manager.InitializeApiAuthManager()

    self.request_handler = http_api.HttpRequestHandler()

  def testSystemUsernameIsNotAllowed(self):
    response = self._RenderResponse(
        self._CreateRequest("GET", "/test_sample/some/path", username=u"GRR"))
    self.assertEqual(response.status_code, 403)

  def testRendersGetHandlerCorrectly(self):
    response = self._RenderResponse(
        self._CreateRequest("GET", "/test_sample/some/path"))

    self.assertEqual(
        self._GetResponseContent(response), {
            "method": "GET",
            "path": "some/path",
            "foo": ""
        })
    self.assertEqual(response.status_code, 200)

  def testHeadRequestHasStubAsABodyOnSuccess(self):
    response = self._RenderResponse(
        self._CreateRequest("HEAD", "/test_sample/some/path"))

    self.assertEqual(self._GetResponseContent(response), {"status": "OK"})
    self.assertEqual(response.status_code, 200)

  def testHeadResponseHasSubjectAndReasonOnUnauthorizedAccess(self):
    response = self._RenderResponse(
        self._CreateRequest("HEAD", "/test_sample/raising/some/path"))

    self.assertEqual(
        self._GetResponseContent(response), {
            "message": "Access denied by ACL: oh no",
            "subject": "aff4:/foo/bar"
        })
    self.assertEqual(response.status_code, 403)

  def testHeadResponsePutsDataIntoHeadersOnUnauthorizedAccess(self):
    response = self._RenderResponse(
        self._CreateRequest("HEAD", "/test_sample/raising/some/path"))

    self.assertEqual(response.headers["X-GRR-Unauthorized-Access-Subject"],
                     "aff4:/foo/bar")
    self.assertEqual(response.headers["X-GRR-Unauthorized-Access-Reason"],
                     "oh no")

  def testBinaryStreamIsCorrectlyStreamedViaGetMethod(self):
    response = self._RenderResponse(
        self._CreateRequest("GET", "/test_sample/streaming"))

    self.assertEqual(list(response.iter_encoded()), [b"foo", b"bar", b"blah"])
    self.assertEqual(response.headers["Content-Length"], "1337")

  def testBinaryStreamReturnsContentLengthViaHeadMethod(self):
    response = self._RenderResponse(
        self._CreateRequest("HEAD", "/test_sample/streaming"))

    self.assertEqual(response.headers["Content-Length"], "1337")

  def testQueryParamsArePassedIntoHandlerArgs(self):
    response = self._RenderResponse(
        self._CreateRequest(
            "GET", "/test_sample/some/path", query_parameters={"foo": "bar"}))
    self.assertEqual(
        self._GetResponseContent(response), {
            "method": "GET",
            "path": "some/path",
            "foo": "bar"
        })

  def testRouteArgumentTakesPrecedenceOverQueryParams(self):
    response = self._RenderResponse(
        self._CreateRequest(
            "GET",
            "/test_sample/some/path",
            query_parameters={"path": "foobar"}))
    self.assertEqual(
        self._GetResponseContent(response), {
            "method": "GET",
            "path": "some/path",
            "foo": ""
        })

  def testRendersDeleteHandlerCorrectly(self):
    response = self._RenderResponse(
        self._CreateRequest("DELETE", "/test_resource/R:123456"))

    self.assertEqual(
        self._GetResponseContent(response), {
            "method": "DELETE",
            "resource": "R:123456"
        })
    self.assertEqual(response.status_code, 200)

  def testRendersPatchHandlerCorrectly(self):
    response = self._RenderResponse(
        self._CreateRequest("PATCH", "/test_resource/R:123456"))

    self.assertEqual(
        self._GetResponseContent(response), {
            "method": "PATCH",
            "resource": "R:123456"
        })
    self.assertEqual(response.status_code, 200)

  def testStatsAreCorrectlyUpdatedOnHeadRequests(self):
    # pylint: disable=g-backslash-continuation
    with self.assertStatsCounterDelta(
        1, http_api.API_ACCESS_PROBE_LATENCY,
        fields=["SampleGet", "http", "SUCCESS"]), \
    self.assertStatsCounterDelta(
        0, http_api.API_ACCESS_PROBE_LATENCY,
        fields=["SampleGet", "http", "RESOURCE_EXHAUSTED"]), \
    self.assertStatsCounterDelta(
        0, http_api.API_ACCESS_PROBE_LATENCY,
        fields=["SampleGet", "http", "FORBIDDEN"]), \
    self.assertStatsCounterDelta(
        0, http_api.API_ACCESS_PROBE_LATENCY,
        fields=["SampleGet", "http", "NOT_FOUND"]), \
    self.assertStatsCounterDelta(
        0, http_api.API_ACCESS_PROBE_LATENCY,
        fields=["SampleGet", "http", "NOT_IMPLEMENTED"]), \
    self.assertStatsCounterDelta(
        0, http_api.API_METHOD_LATENCY,
        fields=["SampleGet", "http", "INVALID_ARGUMENT"]), \
    self.assertStatsCounterDelta(
        0, http_api.API_ACCESS_PROBE_LATENCY,
        fields=["SampleGet", "http", "SERVER_ERROR"]):
      # pylint: enable=g-backslash-continuation

      self._RenderResponse(
          self._CreateRequest("HEAD", "/test_sample/some/path"))

  def testStatsAreCorrectlyUpdatedOnGetRequests(self):
    # pylint: disable=g-backslash-continuation
    with self.assertStatsCounterDelta(
        1, http_api.API_METHOD_LATENCY,
        fields=["SampleGet", "http", "SUCCESS"]), \
    self.assertStatsCounterDelta(
        0, http_api.API_METHOD_LATENCY,
        fields=["SampleGet", "http", "FORBIDDEN"]), \
    self.assertStatsCounterDelta(
        0, http_api.API_METHOD_LATENCY,
        fields=["SampleGet", "http", "RESOURCE_EXHAUSTED"]), \
    self.assertStatsCounterDelta(
        0, http_api.API_METHOD_LATENCY,
        fields=["SampleGet", "http", "NOT_FOUND"]), \
    self.assertStatsCounterDelta(
        0, http_api.API_METHOD_LATENCY,
        fields=["SampleGet", "http", "NOT_IMPLEMENTED"]), \
    self.assertStatsCounterDelta(
        0, http_api.API_METHOD_LATENCY,
        fields=["SampleGet", "http", "INVALID_ARGUMENT"]), \
    self.assertStatsCounterDelta(
        0, http_api.API_METHOD_LATENCY,
        fields=["SampleGet", "http", "SERVER_ERROR"]):
      # pylint: enable=g-backslash-continuation

      self._RenderResponse(self._CreateRequest("GET", "/test_sample/some/path"))

  def testStatsAreCorrectlyUpdatedOnVariousStatusCodes(self):

    def CheckMethod(url, method_name, status):
      # pylint: disable=g-backslash-continuation
      with self.assertStatsCounterDelta(
          1 if status == "SUCCESS" else 0,
          http_api.API_METHOD_LATENCY,
          fields=[method_name, "http", "SUCCESS"]), \
      self.assertStatsCounterDelta(
          1 if status == "FORBIDDEN" else 0,
          http_api.API_METHOD_LATENCY,
          fields=[method_name, "http", "FORBIDDEN"]), \
      self.assertStatsCounterDelta(
          1 if status == "RESOURCE_EXHAUSTED" else 0,
          http_api.API_METHOD_LATENCY,
          fields=[method_name, "http", "RESOURCE_EXHAUSTED"]), \
      self.assertStatsCounterDelta(
          1 if status == "NOT_FOUND" else 0,
          http_api.API_METHOD_LATENCY,
          fields=[method_name, "http", "NOT_FOUND"]), \
      self.assertStatsCounterDelta(
          1 if status == "NOT_IMPLEMENTED" else 0,
          http_api.API_METHOD_LATENCY,
          fields=[method_name, "http", "NOT_IMPLEMENTED"]), \
      self.assertStatsCounterDelta(
          1 if status == "INVALID_ARGUMENT" else 0,
          http_api.API_METHOD_LATENCY,
          fields=[method_name, "http", "INVALID_ARGUMENT"]), \
      self.assertStatsCounterDelta(
          1 if status == "SERVER_ERROR" else 0,
          http_api.API_METHOD_LATENCY,
          fields=[method_name, "http", "SERVER_ERROR"]):
        # pylint: enable=g-backslash-continuation

        self._RenderResponse(self._CreateRequest("GET", url))

    CheckMethod("/failure/not-found", "FailureNotFound", "NOT_FOUND")
    CheckMethod("/failure/server-error", "FailureServerError", "SERVER_ERROR")
    CheckMethod("/failure/not-implemented", "FailureNotImplemented",
                "NOT_IMPLEMENTED")
    CheckMethod("/failure/resource-exhausted", "FailureResourceExhausted",
                "RESOURCE_EXHAUSTED")
    CheckMethod("/failure/unauthorized", "FailureUnauthorized", "FORBIDDEN")
    CheckMethod("/failure/invalid-argument", "FailureInvalidArgument",
                "INVALID_ARGUMENT")

  def testGrrUserIsCreatedOnMethodCall(self):
    request = self._CreateRequest("HEAD", "/test_sample/some/path")

    with self.assertRaises(db.UnknownGRRUserError):
      data_store.REL_DB.ReadGRRUser(request.user)

    self._RenderResponse(self._CreateRequest("GET", "/test_sample/some/path"))

    data_store.REL_DB.ReadGRRUser(request.user)

  def testGrrUserEmailIsSetOnMethodCall(self):
    request = self._CreateRequest("HEAD", "/test_sample/some/path")
    request.email = "foo@bar.org"

    with self.assertRaises(db.UnknownGRRUserError):
      data_store.REL_DB.ReadGRRUser(request.user)

    self._RenderResponse(request)

    u = data_store.REL_DB.ReadGRRUser(request.user)
    self.assertEqual(u.email, "foo@bar.org")


def main(argv):
  test_lib.main(argv)


if __name__ == "__main__":
  app.run(main)
