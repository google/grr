#!/usr/bin/env python
# -*- mode: python; encoding: utf-8 -*-
"""Tests for HTTP API."""
from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

import json


from future.moves.urllib import parse as urlparse
import mock

from grr_response_core.lib import flags
from grr_response_core.lib.rdfvalues import structs as rdf_structs
from grr_response_proto import tests_pb2
from grr_response_server import access_control

from grr_response_server import aff4
from grr_response_server import data_store
from grr_response_server import db
from grr_response_server.aff4_objects import users as aff4_users
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

  def Handle(self, args, token=None):
    return SampleGetHandlerResult(method="GET", path=args.path, foo=args.foo)


class SampleStreamingHandler(api_call_handler_base.ApiCallHandler):

  def _Generate(self):
    content_chunks = ["foo", "bar", "blah"]
    for chunk in content_chunks:
      yield chunk

  def Handle(self, unused_args, token=None):
    return api_call_handler_base.ApiBinaryStream(
        "test.ext", content_generator=self._Generate(), content_length=1337)


class SampleDeleteHandlerArgs(rdf_structs.RDFProtoStruct):
  protobuf = tests_pb2.SampleDeleteHandlerArgs


class SampleDeleteHandlerResult(rdf_structs.RDFProtoStruct):
  protobuf = tests_pb2.SampleDeleteHandlerResult


class SampleDeleteHandler(api_call_handler_base.ApiCallHandler):

  args_type = SampleDeleteHandlerArgs
  result_type = SampleDeleteHandlerResult

  def Handle(self, args, token=None):
    return SampleDeleteHandlerResult(method="DELETE", resource=args.resource_id)


class SamplePatchHandlerArgs(rdf_structs.RDFProtoStruct):
  protobuf = tests_pb2.SamplePatchHandlerArgs


class SamplePatchHandlerResult(rdf_structs.RDFProtoStruct):
  protobuf = tests_pb2.SamplePatchHandlerResult


class SamplePatchHandler(api_call_handler_base.ApiCallHandler):

  args_type = SamplePatchHandlerArgs
  result_type = SamplePatchHandlerResult

  def Handle(self, args, token=None):
    return SamplePatchHandlerResult(method="PATCH", resource=args.resource_id)


class TestHttpApiRouter(api_call_router.ApiCallRouter):
  """Test router with custom methods."""

  @api_call_router.Http("GET", "/test_sample/<path:path>")
  @api_call_router.ArgsType(api_test_lib.SampleGetHandlerArgs)
  @api_call_router.ResultType(SampleGetHandlerResult)
  def SampleGet(self, args, token=None):
    return SampleGetHandler()

  @api_call_router.Http("GET", "/test_sample/raising/<path:path>")
  @api_call_router.ArgsType(api_test_lib.SampleGetHandlerArgs)
  @api_call_router.ResultType(SampleGetHandlerResult)
  def SampleRaisingGet(self, args, token=None):
    raise access_control.UnauthorizedAccess("oh no", subject="aff4:/foo/bar")

  @api_call_router.Http("GET", "/test_sample/streaming")
  @api_call_router.ResultBinaryStream()
  def SampleStreamingGet(self, args, token=None):
    return SampleStreamingHandler()

  @api_call_router.Http("DELETE", "/test_resource/<resource_id>")
  @api_call_router.ArgsType(SampleDeleteHandlerArgs)
  @api_call_router.ResultType(SampleDeleteHandlerResult)
  def SampleDelete(self, args, token=None):
    return SampleDeleteHandler()

  @api_call_router.Http("PATCH", "/test_resource/<resource_id>")
  @api_call_router.ArgsType(SamplePatchHandlerArgs)
  @api_call_router.ResultType(SamplePatchHandlerResult)
  def SamplePatch(self, args, token=None):
    return SamplePatchHandler()

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
    request = mock.MagicMock()
    request.method = method
    request.path = path
    request.scheme = "http"
    request.environ = {"SERVER_NAME": "foo.bar", "SERVER_PORT": 1234}
    request.user = u"test"
    request.args = query_parameters or {}
    request.headers = {}
    request.get_data = lambda as_text=False: ""

    return request

  def setUp(self):
    super(RouterMatcherTest, self).setUp()
    self.config_overrider = test_lib.ConfigOverrider({
        "API.DefaultRouter": TestHttpApiRouter.__name__
    })
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
    self.assertEqual(
        router_args, api_test_lib.SampleGetHandlerArgs(path="some/path"))

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

    return json.loads(content)

  def setUp(self):
    super(HttpRequestHandlerTest, self).setUp()

    self.config_overrider = test_lib.ConfigOverrider({
        "API.DefaultRouter": TestHttpApiRouter.__name__
    })
    self.config_overrider.Start()
    # Make sure ApiAuthManager is initialized with this configuration setting.
    api_auth_manager.APIACLInit.InitApiAuthManager()

    self.request_handler = http_api.HttpRequestHandler()

  def tearDown(self):
    super(HttpRequestHandlerTest, self).tearDown()
    self.config_overrider.Stop()

  def testBuildToken(self):
    request = self._CreateRequest("POST", "/test_sample/some/path")
    request.headers["X-Grr-Reason"] = urlparse.quote(
        "区最 trailing space ".encode("utf-8"))
    token = self.request_handler.BuildToken(request, 20)
    self.assertEqual(token.reason, "区最 trailing space ")

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

    self.assertEqual(list(response.iter_encoded()), ["foo", "bar", "blah"])
    self.assertEqual(response.headers["Content-Length"], "1337")

  def testBinaryStreamReturnsContentLengthViaHeadMethod(self):
    response = self._RenderResponse(
        self._CreateRequest("HEAD", "/test_sample/streaming"))

    self.assertEqual(response.headers["Content-Length"], "1337")

  def testQueryParamsArePassedIntoHandlerArgs(self):
    response = self._RenderResponse(
        self._CreateRequest(
            "GET", "/test_sample/some/path", query_parameters={
                "foo": "bar"
            }))
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
            query_parameters={
                "path": "foobar"
            }))
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

      self._RenderResponse(
          self._CreateRequest("HEAD", "/test_sample/some/path"))

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

  def testGrrUserIsCreatedOnMethodCall(self):
    request = self._CreateRequest("HEAD", "/test_sample/some/path")

    self.assertFalse(
        aff4.FACTORY.ExistsWithType(
            "aff4:/users/%s" % request.user, aff4_type=aff4_users.GRRUser))
    with self.assertRaises(db.UnknownGRRUserError):
      data_store.REL_DB.ReadGRRUser(request.user)

    self._RenderResponse(self._CreateRequest("GET", "/test_sample/some/path"))

    self.assertTrue(
        aff4.FACTORY.ExistsWithType(
            "aff4:/users/%s" % request.user, aff4_type=aff4_users.GRRUser))
    data_store.REL_DB.ReadGRRUser(request.user)


def main(argv):
  test_lib.main(argv)


if __name__ == "__main__":
  flags.StartMain(main)
