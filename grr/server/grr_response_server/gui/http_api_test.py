#!/usr/bin/env python
# -*- encoding: utf-8 -*-
"""Tests for HTTP API."""

from unittest import mock

from absl import app
from absl.testing import absltest

from grr_response_core.lib.rdfvalues import client as rdf_client
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
from grr_response_server.gui import api_call_router_registry
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
    super().setUp()
    config_overrider = test_lib.ConfigOverrider({
        "API.DefaultRouter": compatibility.GetName(TestHttpApiRouter),
    })
    config_overrider.Start()
    self.addCleanup(config_overrider.Stop)

    patcher = mock.patch.object(api_call_router_registry,
                                "_API_CALL_ROUTER_REGISTRY", {})
    patcher.start()
    self.addCleanup(patcher.stop)
    api_call_router_registry.RegisterApiCallRouter("TestHttpApiRouter",
                                                   TestHttpApiRouter)
    # pylint: disable=g-long-lambda
    self.addCleanup(lambda: api_call_router_registry.UnregisterApiCallRouter(
        "TestHttpApiRouter"))
    api_call_router_registry.RegisterApiCallRouter("TestHttpApiRouter",
                                                   TestHttpApiRouter)

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
                     query_parameters=None,
                     headers=None):
    request = mock.MagicMock()
    request.method = method
    request.path = path
    request.scheme = "http"
    request.environ = {"SERVER_NAME": "foo.bar", "SERVER_PORT": 1234}
    request.user = username
    request.email = None
    request.args = query_parameters or {}
    request.content_type = "application/json; charset=utf-8"
    request.headers = headers or {}
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
    super().setUp()

    config_overrider = test_lib.ConfigOverrider({
        "API.DefaultRouter": compatibility.GetName(TestHttpApiRouter),
    })
    config_overrider.Start()
    self.addCleanup(config_overrider.Stop)

    patcher = mock.patch.object(api_call_router_registry,
                                "_API_CALL_ROUTER_REGISTRY", {})
    patcher.start()
    self.addCleanup(patcher.stop)
    api_call_router_registry.RegisterApiCallRouter("TestHttpApiRouter",
                                                   TestHttpApiRouter)
    # pylint: disable=g-long-lambda
    self.addCleanup(lambda: api_call_router_registry.UnregisterApiCallRouter(
        "TestHttpApiRouter"))
    api_call_router_registry.RegisterApiCallRouter("TestHttpApiRouter",
                                                   TestHttpApiRouter)

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
        fields=["SampleGet", "http", "SUCCESS", "unknown"]), \
    self.assertStatsCounterDelta(
        0, http_api.API_ACCESS_PROBE_LATENCY,
        fields=["SampleGet", "http", "RESOURCE_EXHAUSTED", "unknown"]), \
    self.assertStatsCounterDelta(
        0, http_api.API_ACCESS_PROBE_LATENCY,
        fields=["SampleGet", "http", "FORBIDDEN", "unknown"]), \
    self.assertStatsCounterDelta(
        0, http_api.API_ACCESS_PROBE_LATENCY,
        fields=["SampleGet", "http", "NOT_FOUND", "unknown"]), \
    self.assertStatsCounterDelta(
        0, http_api.API_ACCESS_PROBE_LATENCY,
        fields=["SampleGet", "http", "NOT_IMPLEMENTED", "unknown"]), \
    self.assertStatsCounterDelta(
        0, http_api.API_METHOD_LATENCY,
        fields=["SampleGet", "http", "INVALID_ARGUMENT", "unknown"]), \
    self.assertStatsCounterDelta(
        0, http_api.API_ACCESS_PROBE_LATENCY,
        fields=["SampleGet", "http", "SERVER_ERROR", "unknown"]):
      # pylint: enable=g-backslash-continuation

      self._RenderResponse(
          self._CreateRequest("HEAD", "/test_sample/some/path"))

  def testStatsAreCorrectlyUpdatedOnGetRequests(self):
    # pylint: disable=g-backslash-continuation
    with self.assertStatsCounterDelta(
        1, http_api.API_METHOD_LATENCY,
        fields=["SampleGet", "http", "SUCCESS", "unknown"]), \
    self.assertStatsCounterDelta(
        0, http_api.API_METHOD_LATENCY,
        fields=["SampleGet", "http", "FORBIDDEN", "unknown"]), \
    self.assertStatsCounterDelta(
        0, http_api.API_METHOD_LATENCY,
        fields=["SampleGet", "http", "RESOURCE_EXHAUSTED", "unknown"]), \
    self.assertStatsCounterDelta(
        0, http_api.API_METHOD_LATENCY,
        fields=["SampleGet", "http", "NOT_FOUND", "unknown"]), \
    self.assertStatsCounterDelta(
        0, http_api.API_METHOD_LATENCY,
        fields=["SampleGet", "http", "NOT_IMPLEMENTED", "unknown"]), \
    self.assertStatsCounterDelta(
        0, http_api.API_METHOD_LATENCY,
        fields=["SampleGet", "http", "INVALID_ARGUMENT", "unknown"]), \
    self.assertStatsCounterDelta(
        0, http_api.API_METHOD_LATENCY,
        fields=["SampleGet", "http", "SERVER_ERROR", "unknown"]):
      # pylint: enable=g-backslash-continuation

      self._RenderResponse(self._CreateRequest("GET", "/test_sample/some/path"))

  def testOriginIsExtractedFromRequest(self):
    with self.assertStatsCounterDelta(
        1,
        http_api.API_METHOD_LATENCY,
        fields=["SampleGet", "http", "SUCCESS", "GRR-UI/1.0"]):
      self._RenderResponse(
          self._CreateRequest(
              "GET",
              "/test_sample/some/path",
              headers={"X-User-Agent": "GRR-UI/1.0"}))

    with self.assertStatsCounterDelta(
        1,
        http_api.API_METHOD_LATENCY,
        fields=["SampleGet", "http", "SUCCESS", "GRR-UI/2.0"]):
      self._RenderResponse(
          self._CreateRequest(
              "GET",
              "/test_sample/some/path",
              headers={"X-User-Agent": "GRR-UI/2.0"}))

  def testUnknownOriginsAreLabelledUnknown(self):
    with self.assertStatsCounterDelta(
        1,
        http_api.API_METHOD_LATENCY,
        fields=["SampleGet", "http", "SUCCESS", "unknown"]):
      self._RenderResponse(
          self._CreateRequest(
              "GET",
              "/test_sample/some/path",
              headers={"X-User-Agent": "GRR-UI/invalid"}))

    with self.assertStatsCounterDelta(
        1,
        http_api.API_METHOD_LATENCY,
        fields=["SampleGet", "http", "SUCCESS", "unknown"]):
      self._RenderResponse(
          self._CreateRequest(
              "GET", "/test_sample/some/path", headers={"X-User-Agent": ""}))

    with self.assertStatsCounterDelta(
        1,
        http_api.API_METHOD_LATENCY,
        fields=["SampleGet", "http", "SUCCESS", "unknown"]):
      self._RenderResponse(
          self._CreateRequest("GET", "/test_sample/some/path", headers={}))

  def testStatsAreCorrectlyUpdatedOnVariousStatusCodes(self):

    def CheckMethod(url, method_name, status):
      # pylint: disable=g-backslash-continuation
      with self.assertStatsCounterDelta(
          1 if status == "SUCCESS" else 0,
          http_api.API_METHOD_LATENCY,
          fields=[method_name, "http", "SUCCESS", "unknown"]), \
      self.assertStatsCounterDelta(
          1 if status == "FORBIDDEN" else 0,
          http_api.API_METHOD_LATENCY,
          fields=[method_name, "http", "FORBIDDEN", "unknown"]), \
      self.assertStatsCounterDelta(
          1 if status == "RESOURCE_EXHAUSTED" else 0,
          http_api.API_METHOD_LATENCY,
          fields=[method_name, "http", "RESOURCE_EXHAUSTED", "unknown"]), \
      self.assertStatsCounterDelta(
          1 if status == "NOT_FOUND" else 0,
          http_api.API_METHOD_LATENCY,
          fields=[method_name, "http", "NOT_FOUND", "unknown"]), \
      self.assertStatsCounterDelta(
          1 if status == "NOT_IMPLEMENTED" else 0,
          http_api.API_METHOD_LATENCY,
          fields=[method_name, "http", "NOT_IMPLEMENTED", "unknown"]), \
      self.assertStatsCounterDelta(
          1 if status == "INVALID_ARGUMENT" else 0,
          http_api.API_METHOD_LATENCY,
          fields=[method_name, "http", "INVALID_ARGUMENT", "unknown"]), \
      self.assertStatsCounterDelta(
          1 if status == "SERVER_ERROR" else 0,
          http_api.API_METHOD_LATENCY,
          fields=[method_name, "http", "SERVER_ERROR", "unknown"]):
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


class FlatDictToRDFValue(absltest.TestCase):

  def testSimple(self):
    dct = {
        "username": "foo",
        "uid": "42",
    }

    user = http_api.FlatDictToRDFValue(dct, rdf_client.User)
    self.assertEqual(user.username, "foo")
    self.assertEqual(user.uid, 42)

  def testNested(self):
    dct = {
        "pw_entry.age": "1337",
    }

    user = http_api.FlatDictToRDFValue(dct, rdf_client.User)
    self.assertEqual(user.pw_entry.age, 1337)

  def testEnum(self):
    dct = {
        "hash_type": "MD5",
    }

    pw_entry = http_api.FlatDictToRDFValue(dct, rdf_client.PwEntry)
    self.assertEqual(pw_entry.hash_type, rdf_client.PwEntry.PwHash.MD5)

  def testNonExistingField(self):
    dct = {
        "some_non_existing_field": "foobar",
    }

    pw_entry = http_api.FlatDictToRDFValue(dct, rdf_client.PwEntry)
    self.assertFalse(hasattr(pw_entry, "some_non_existing_field"))

  def testWrongType(self):
    dct = {
        "uid": "foobar",
    }

    with self.assertRaisesRegex(ValueError, "foobar"):
      http_api.FlatDictToRDFValue(dct, rdf_client.User)

  def testPythonSpecific(self):
    dct = {
        "__class__": "foobar",
    }

    pw_entry = http_api.FlatDictToRDFValue(dct, rdf_client.PwEntry)
    self.assertEqual(pw_entry.__class__, rdf_client.PwEntry)


def main(argv):
  test_lib.main(argv)


if __name__ == "__main__":
  app.run(main)
