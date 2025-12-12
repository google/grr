#!/usr/bin/env python
"""Tests for HTTP API."""

import json
from unittest import mock

from absl import app
from absl.testing import absltest

from grr_response_proto import knowledge_base_pb2
from grr_response_proto import tests_pb2
from grr_response_server import access_control
from grr_response_server import data_store
from grr_response_server.databases import db
from grr_response_server.gui import api_auth_manager
from grr_response_server.gui import api_call_handler_base
from grr_response_server.gui import api_call_router
from grr_response_server.gui import api_call_router_registry
from grr_response_server.gui import http_api
from grr_response_server.rdfvalues import mig_objects
from grr.test_lib import stats_test_lib
from grr.test_lib import test_lib


class SampleGetHandler(api_call_handler_base.ApiCallHandler):

  proto_args_type = tests_pb2.SampleGetHandlerArgs
  proto_result_type = tests_pb2.SampleGetHandlerResult

  def Handle(self, args, context=None):
    return tests_pb2.SampleGetHandlerResult(
        method="GET", path=args.path, foo=args.foo
    )


class SampleStreamingHandler(api_call_handler_base.ApiCallHandler):

  def _Generate(self):
    content_chunks = ["foo", "bar", "blah"]
    for chunk in content_chunks:
      yield chunk

  def Handle(self, unused_args, context=None):
    return api_call_handler_base.ApiBinaryStream(
        "test.ext", content_generator=self._Generate(), content_length=1337
    )


class SampleDeleteHandler(api_call_handler_base.ApiCallHandler):

  proto_args_type = tests_pb2.SampleDeleteHandlerArgs
  proto_result_type = tests_pb2.SampleDeleteHandlerResult

  def Handle(self, args, context=None):
    return tests_pb2.SampleDeleteHandlerResult(
        method="DELETE", resource=args.resource_id
    )


class SamplePatchHandler(api_call_handler_base.ApiCallHandler):

  proto_args_type = tests_pb2.SamplePatchHandlerArgs
  proto_result_type = tests_pb2.SamplePatchHandlerResult

  def Handle(self, args, context=None):
    return tests_pb2.SamplePatchHandlerResult(
        method="PATCH", resource=args.resource_id
    )


class TestHttpApiRouter(api_call_router.ApiCallRouter):
  """Test router with custom methods."""

  @api_call_router.Http("GET", "/api/v2/test_sample/<path:path>")
  @api_call_router.ProtoArgsType(tests_pb2.SampleGetHandlerArgs)
  @api_call_router.ProtoResultType(tests_pb2.SampleGetHandlerResult)
  def SampleGet(self, args, context=None):
    return SampleGetHandler()

  @api_call_router.Http("GET", "/api/v2/test_sample/raising/<path:path>")
  @api_call_router.ProtoArgsType(tests_pb2.SampleGetHandlerArgs)
  @api_call_router.ProtoResultType(tests_pb2.SampleGetHandlerResult)
  def SampleRaisingGet(self, args, context=None):
    raise access_control.UnauthorizedAccess("oh no", subject="aff4:/foo/bar")

  @api_call_router.Http("GET", "/api/v2/test_sample/streaming")
  @api_call_router.ResultBinaryStream()
  def SampleStreamingGet(self, args, context=None):
    return SampleStreamingHandler()

  @api_call_router.Http("DELETE", "/api/v2/test_resource/<resource_id>")
  @api_call_router.ProtoArgsType(tests_pb2.SampleDeleteHandlerArgs)
  @api_call_router.ProtoResultType(tests_pb2.SampleDeleteHandlerResult)
  def SampleDelete(self, args, context=None):
    return SampleDeleteHandler()

  @api_call_router.Http("PATCH", "/api/v2/test_resource/<resource_id>")
  @api_call_router.ProtoArgsType(tests_pb2.SamplePatchHandlerArgs)
  @api_call_router.ProtoResultType(tests_pb2.SamplePatchHandlerResult)
  def SamplePatch(self, args, context=None):
    return SamplePatchHandler()

  @api_call_router.Http("GET", "/api/v2/failure/not-found")
  def FailureNotFound(self, args, context=None):
    raise api_call_handler_base.ResourceNotFoundError()

  @api_call_router.Http("GET", "/api/v2/failure/server-error")
  def FailureServerError(self, args, context=None):
    raise RuntimeError("Some error")

  @api_call_router.Http("GET", "/api/v2/failure/not-implemented")
  def FailureNotImplemented(self, args, context=None):
    raise NotImplementedError()

  @api_call_router.Http("GET", "/api/v2/failure/unauthorized")
  def FailureUnauthorized(self, args, context=None):
    raise access_control.UnauthorizedAccess("oh no")

  @api_call_router.Http("GET", "/api/v2/failure/resource-exhausted")
  def FailureResourceExhausted(self, args, context=None):
    raise api_call_handler_base.ResourceExhaustedError("exhausted")

  @api_call_router.Http("GET", "/api/v2/failure/invalid-argument")
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
    request.user = "test"
    request.email = None
    request.args = query_parameters or {}
    request.headers = {}
    request.get_data = lambda as_text=False: ""

    return request

  def setUp(self):
    super().setUp()
    config_overrider = test_lib.ConfigOverrider({
        "API.DefaultRouter": TestHttpApiRouter.__name__,
    })
    config_overrider.Start()
    self.addCleanup(config_overrider.Stop)

    patcher = mock.patch.object(
        api_call_router_registry, "_API_CALL_ROUTER_REGISTRY", {}
    )
    patcher.start()
    self.addCleanup(patcher.stop)
    api_call_router_registry.RegisterApiCallRouter(
        "TestHttpApiRouter", TestHttpApiRouter
    )
    # pylint: disable=g-long-lambda
    self.addCleanup(
        lambda: api_call_router_registry.UnregisterApiCallRouter(
            "TestHttpApiRouter"
        )
    )
    api_call_router_registry.RegisterApiCallRouter(
        "TestHttpApiRouter", TestHttpApiRouter
    )

    # Make sure ApiAuthManager is initialized with this configuration setting.
    api_auth_manager.InitializeApiAuthManager()

    self.router_matcher = http_api.RouterMatcher()

  def testReturnsMethodMetadataMatchingUrlAndMethod(self):
    _, method_metadata, _ = self.router_matcher.MatchRouter(
        self._CreateRequest("GET", "/api/v2/test_sample/some/path")
    )

    self.assertEqual(method_metadata.name, "SampleGet")

  def testPathParamsAreReturnedWithMatchingHandler(self):
    _, _, proto_args = self.router_matcher.MatchRouter(
        self._CreateRequest("GET", "/api/v2/test_sample/some/path")
    )
    self.assertEqual(
        proto_args, tests_pb2.SampleGetHandlerArgs(path="some/path")
    )

  def testGetRequestHandlesFlattenedInnerParams(self):
    _, _, proto_args = self.router_matcher.MatchRouter(
        self._CreateRequest(
            "GET",
            "/api/v2/test_sample/some/path",
            query_parameters={
                "foo": "banana",
                "inner.foo": "batata",
                "inner.bar": "1234",
                # TODO: Stop handling booleans as stringified
                # numbers.
                "inner.baz": "1",  # Booleans are sent as stringified number
                "inner.fruits": [
                    "0",  # Acerola
                    "JABUTICABA",
                ],
            },
        )
    )
    self.assertEqual(
        proto_args,
        tests_pb2.SampleGetHandlerArgs(
            path="some/path",
            foo="banana",
            inner=tests_pb2.SampleInnerMessage(
                foo="batata",
                bar=1234,
                baz=True,
                fruits=[
                    tests_pb2.SampleInnerMessage.ACEROLA,
                    tests_pb2.SampleInnerMessage.JABUTICABA,
                ],
            ),
        ),
    )

  def testRaisesIfNoHandlerMatchesUrl(self):
    self.assertRaises(
        http_api.ApiCallRouterNotFoundError,
        self.router_matcher.MatchRouter,
        self._CreateRequest("GET", "/api/v2/some/missing/path"),
    )

  # TODO: Stop messing with the routes and delete this test.
  def testRaisesApiVersionHandling(self):
    # `SampleGet` is annotated for `/api/test_sample/<path:path>`
    # However, we have logic that overrides this route for routes starting
    # with `/api/`, so that we only add and handle `/api/v2/`.
    # Therefore, where `/api/v2/test_sample/some/path` should work,
    # the plain `/api/test_sample/some/path` should not.
    self.assertRaises(
        http_api.ApiCallRouterNotFoundError,
        self.router_matcher.MatchRouter,
        self._CreateRequest("GET", "/api/test_sample/some/path"),
    )
    self.router_matcher.MatchRouter(
        self._CreateRequest("GET", "/api/v2/test_sample/some/path")
    )


class HttpRequestHandlerTest(
    test_lib.GRRBaseTest, stats_test_lib.StatsTestMixin
):
  """Test for HttpRequestHandler."""

  def _CreateRequest(
      self, method, path, username="test", query_parameters=None, headers=None
  ):
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

    return json.loads(content)

  def setUp(self):
    super().setUp()

    config_overrider = test_lib.ConfigOverrider({
        "API.DefaultRouter": TestHttpApiRouter.__name__,
    })
    config_overrider.Start()
    self.addCleanup(config_overrider.Stop)

    patcher = mock.patch.object(
        api_call_router_registry, "_API_CALL_ROUTER_REGISTRY", {}
    )
    patcher.start()
    self.addCleanup(patcher.stop)
    api_call_router_registry.RegisterApiCallRouter(
        "TestHttpApiRouter", TestHttpApiRouter
    )
    # pylint: disable=g-long-lambda
    self.addCleanup(
        lambda: api_call_router_registry.UnregisterApiCallRouter(
            "TestHttpApiRouter"
        )
    )
    api_call_router_registry.RegisterApiCallRouter(
        "TestHttpApiRouter", TestHttpApiRouter
    )

    # Make sure ApiAuthManager is initialized with this configuration setting.
    api_auth_manager.InitializeApiAuthManager()

    self.request_handler = http_api.HttpRequestHandler()

  def testSystemUsernameIsNotAllowed(self):
    response = self._RenderResponse(
        self._CreateRequest(
            "GET", "/api/v2/test_sample/some/path", username="GRR"
        )
    )
    self.assertEqual(response.status_code, 403)

  def testRendersGetHandlerCorrectly(self):
    response = self._RenderResponse(
        self._CreateRequest("GET", "/api/v2/test_sample/some/path")
    )

    self.assertEqual(
        self._GetResponseContent(response),
        {"method": "GET", "path": "some/path", "foo": ""},
    )
    self.assertEqual(response.status_code, 200)

  def testRendersGetHandlerProtoOnlyCorrectly(self):
    response = self._RenderResponse(
        self._CreateRequest("GET", "/api/v2/test_sample/some/path")
    )

    self.assertEqual(
        self._GetResponseContent(response),
        {"method": "GET", "path": "some/path", "foo": ""},
    )
    self.assertEqual(response.status_code, 200)

  def testHeadRequestHasStubAsABodyOnSuccess(self):
    response = self._RenderResponse(
        self._CreateRequest("HEAD", "/api/v2/test_sample/some/path")
    )

    self.assertEqual(self._GetResponseContent(response), {"status": "OK"})
    self.assertEqual(response.status_code, 200)

  def testHeadResponseHasSubjectAndReasonOnUnauthorizedAccess(self):
    response = self._RenderResponse(
        self._CreateRequest("HEAD", "/api/v2/test_sample/raising/some/path")
    )

    self.assertEqual(
        self._GetResponseContent(response),
        {"message": "Access denied by ACL: oh no", "subject": "aff4:/foo/bar"},
    )
    self.assertEqual(response.status_code, 403)

  def testHeadResponsePutsDataIntoHeadersOnUnauthorizedAccess(self):
    response = self._RenderResponse(
        self._CreateRequest("HEAD", "/api/v2/test_sample/raising/some/path")
    )

    self.assertEqual(
        response.headers["X-GRR-Unauthorized-Access-Subject"], "aff4:/foo/bar"
    )
    self.assertEqual(
        response.headers["X-GRR-Unauthorized-Access-Reason"], "oh no"
    )

  def testBinaryStreamIsCorrectlyStreamedViaGetMethod(self):
    response = self._RenderResponse(
        self._CreateRequest("GET", "/api/v2/test_sample/streaming")
    )

    self.assertEqual(list(response.iter_encoded()), [b"foo", b"bar", b"blah"])
    self.assertEqual(response.headers["Content-Length"], "1337")

  def testBinaryStreamReturnsContentLengthViaHeadMethod(self):
    response = self._RenderResponse(
        self._CreateRequest("HEAD", "/api/v2/test_sample/streaming")
    )

    self.assertEqual(response.headers["Content-Length"], "1337")

  def testQueryParamsArePassedIntoHandlerArgs(self):
    response = self._RenderResponse(
        self._CreateRequest(
            "GET",
            "/api/v2/test_sample/some/path",
            query_parameters={"foo": "bar"},
        )
    )
    self.assertEqual(
        self._GetResponseContent(response),
        {"method": "GET", "path": "some/path", "foo": "bar"},
    )

  def testRouteArgumentTakesPrecedenceOverQueryParams(self):
    response = self._RenderResponse(
        self._CreateRequest(
            "GET",
            "/api/v2/test_sample/some/path",
            query_parameters={"path": "foobar"},
        )
    )
    self.assertEqual(
        self._GetResponseContent(response),
        {"method": "GET", "path": "some/path", "foo": ""},
    )

  def testRendersDeleteHandlerCorrectly(self):
    response = self._RenderResponse(
        self._CreateRequest("DELETE", "/api/v2/test_resource/R:123456")
    )

    self.assertEqual(
        self._GetResponseContent(response),
        {"method": "DELETE", "resource": "R:123456"},
    )
    self.assertEqual(response.status_code, 200)

  def testRendersPatchHandlerCorrectly(self):
    response = self._RenderResponse(
        self._CreateRequest("PATCH", "/api/v2/test_resource/R:123456")
    )

    self.assertEqual(
        self._GetResponseContent(response),
        {"method": "PATCH", "resource": "R:123456"},
    )
    self.assertEqual(response.status_code, 200)

  def testStatsAreCorrectlyUpdatedOnHeadRequests(self):
    # pylint: disable=g-backslash-continuation
    with (
        self.assertStatsCounterDelta(
            1,
            http_api.API_ACCESS_PROBE_LATENCY,
            fields=["SampleGet", "http", "SUCCESS", "unknown"],
        ),
        self.assertStatsCounterDelta(
            0,
            http_api.API_ACCESS_PROBE_LATENCY,
            fields=["SampleGet", "http", "RESOURCE_EXHAUSTED", "unknown"],
        ),
        self.assertStatsCounterDelta(
            0,
            http_api.API_ACCESS_PROBE_LATENCY,
            fields=["SampleGet", "http", "FORBIDDEN", "unknown"],
        ),
        self.assertStatsCounterDelta(
            0,
            http_api.API_ACCESS_PROBE_LATENCY,
            fields=["SampleGet", "http", "NOT_FOUND", "unknown"],
        ),
        self.assertStatsCounterDelta(
            0,
            http_api.API_ACCESS_PROBE_LATENCY,
            fields=["SampleGet", "http", "NOT_IMPLEMENTED", "unknown"],
        ),
        self.assertStatsCounterDelta(
            0,
            http_api.API_METHOD_LATENCY,
            fields=["SampleGet", "http", "INVALID_ARGUMENT", "unknown"],
        ),
        self.assertStatsCounterDelta(
            0,
            http_api.API_ACCESS_PROBE_LATENCY,
            fields=["SampleGet", "http", "SERVER_ERROR", "unknown"],
        ),
    ):
      # pylint: enable=g-backslash-continuation

      self._RenderResponse(
          self._CreateRequest("HEAD", "/api/v2/test_sample/some/path")
      )

  def testStatsAreCorrectlyUpdatedOnGetRequests(self):
    # pylint: disable=g-backslash-continuation
    with (
        self.assertStatsCounterDelta(
            1,
            http_api.API_METHOD_LATENCY,
            fields=["SampleGet", "http", "SUCCESS", "unknown"],
        ),
        self.assertStatsCounterDelta(
            0,
            http_api.API_METHOD_LATENCY,
            fields=["SampleGet", "http", "FORBIDDEN", "unknown"],
        ),
        self.assertStatsCounterDelta(
            0,
            http_api.API_METHOD_LATENCY,
            fields=["SampleGet", "http", "RESOURCE_EXHAUSTED", "unknown"],
        ),
        self.assertStatsCounterDelta(
            0,
            http_api.API_METHOD_LATENCY,
            fields=["SampleGet", "http", "NOT_FOUND", "unknown"],
        ),
        self.assertStatsCounterDelta(
            0,
            http_api.API_METHOD_LATENCY,
            fields=["SampleGet", "http", "NOT_IMPLEMENTED", "unknown"],
        ),
        self.assertStatsCounterDelta(
            0,
            http_api.API_METHOD_LATENCY,
            fields=["SampleGet", "http", "INVALID_ARGUMENT", "unknown"],
        ),
        self.assertStatsCounterDelta(
            0,
            http_api.API_METHOD_LATENCY,
            fields=["SampleGet", "http", "SERVER_ERROR", "unknown"],
        ),
    ):
      # pylint: enable=g-backslash-continuation

      self._RenderResponse(
          self._CreateRequest("GET", "/api/v2/test_sample/some/path")
      )

  def testOriginIsExtractedFromRequest(self):
    with self.assertStatsCounterDelta(
        1,
        http_api.API_METHOD_LATENCY,
        fields=["SampleGet", "http", "SUCCESS", "GRR-UI/1.0"],
    ):
      self._RenderResponse(
          self._CreateRequest(
              "GET",
              "/api/v2/test_sample/some/path",
              headers={"X-User-Agent": "GRR-UI/1.0"},
          )
      )

    with self.assertStatsCounterDelta(
        1,
        http_api.API_METHOD_LATENCY,
        fields=["SampleGet", "http", "SUCCESS", "GRR-UI/2.0"],
    ):
      self._RenderResponse(
          self._CreateRequest(
              "GET",
              "/api/v2/test_sample/some/path",
              headers={"X-User-Agent": "GRR-UI/2.0"},
          )
      )

  def testUnknownOriginsAreLabelledUnknown(self):
    with self.assertStatsCounterDelta(
        1,
        http_api.API_METHOD_LATENCY,
        fields=["SampleGet", "http", "SUCCESS", "unknown"],
    ):
      self._RenderResponse(
          self._CreateRequest(
              "GET",
              "/api/v2/test_sample/some/path",
              headers={"X-User-Agent": "GRR-UI/invalid"},
          )
      )

    with self.assertStatsCounterDelta(
        1,
        http_api.API_METHOD_LATENCY,
        fields=["SampleGet", "http", "SUCCESS", "unknown"],
    ):
      self._RenderResponse(
          self._CreateRequest(
              "GET",
              "/api/v2/test_sample/some/path",
              headers={"X-User-Agent": ""},
          )
      )

    with self.assertStatsCounterDelta(
        1,
        http_api.API_METHOD_LATENCY,
        fields=["SampleGet", "http", "SUCCESS", "unknown"],
    ):
      self._RenderResponse(
          self._CreateRequest(
              "GET", "/api/v2/test_sample/some/path", headers={}
          )
      )

  def testStatsAreCorrectlyUpdatedOnVariousStatusCodes(self):

    def CheckMethod(url, method_name, status):
      # pylint: disable=g-backslash-continuation
      with (
          self.assertStatsCounterDelta(
              1 if status == "SUCCESS" else 0,
              http_api.API_METHOD_LATENCY,
              fields=[method_name, "http", "SUCCESS", "unknown"],
          ),
          self.assertStatsCounterDelta(
              1 if status == "FORBIDDEN" else 0,
              http_api.API_METHOD_LATENCY,
              fields=[method_name, "http", "FORBIDDEN", "unknown"],
          ),
          self.assertStatsCounterDelta(
              1 if status == "RESOURCE_EXHAUSTED" else 0,
              http_api.API_METHOD_LATENCY,
              fields=[method_name, "http", "RESOURCE_EXHAUSTED", "unknown"],
          ),
          self.assertStatsCounterDelta(
              1 if status == "NOT_FOUND" else 0,
              http_api.API_METHOD_LATENCY,
              fields=[method_name, "http", "NOT_FOUND", "unknown"],
          ),
          self.assertStatsCounterDelta(
              1 if status == "NOT_IMPLEMENTED" else 0,
              http_api.API_METHOD_LATENCY,
              fields=[method_name, "http", "NOT_IMPLEMENTED", "unknown"],
          ),
          self.assertStatsCounterDelta(
              1 if status == "INVALID_ARGUMENT" else 0,
              http_api.API_METHOD_LATENCY,
              fields=[method_name, "http", "INVALID_ARGUMENT", "unknown"],
          ),
          self.assertStatsCounterDelta(
              1 if status == "SERVER_ERROR" else 0,
              http_api.API_METHOD_LATENCY,
              fields=[method_name, "http", "SERVER_ERROR", "unknown"],
          ),
      ):
        # pylint: enable=g-backslash-continuation

        self._RenderResponse(self._CreateRequest("GET", url))

    CheckMethod("/api/v2/failure/not-found", "FailureNotFound", "NOT_FOUND")
    CheckMethod(
        "/api/v2/failure/server-error", "FailureServerError", "SERVER_ERROR"
    )
    CheckMethod(
        "/api/v2/failure/not-implemented",
        "FailureNotImplemented",
        "NOT_IMPLEMENTED",
    )
    CheckMethod(
        "/api/v2/failure/resource-exhausted",
        "FailureResourceExhausted",
        "RESOURCE_EXHAUSTED",
    )
    CheckMethod(
        "/api/v2/failure/unauthorized", "FailureUnauthorized", "FORBIDDEN"
    )
    CheckMethod(
        "/api/v2/failure/invalid-argument",
        "FailureInvalidArgument",
        "INVALID_ARGUMENT",
    )

  def testGrrUserIsCreatedOnMethodCall(self):
    request = self._CreateRequest("HEAD", "/api/v2/test_sample/some/path")

    with self.assertRaises(db.UnknownGRRUserError):
      data_store.REL_DB.ReadGRRUser(request.user)

    self._RenderResponse(
        self._CreateRequest("GET", "/api/v2/test_sample/some/path")
    )

    data_store.REL_DB.ReadGRRUser(request.user)

  def testGrrUserEmailIsSetOnMethodCall(self):
    request = self._CreateRequest("HEAD", "/api/v2/test_sample/some/path")
    request.email = "foo@bar.org"

    with self.assertRaises(db.UnknownGRRUserError):
      data_store.REL_DB.ReadGRRUser(request.user)

    self._RenderResponse(request)

    proto_u = data_store.REL_DB.ReadGRRUser(request.user)
    rdf_u = mig_objects.ToRDFGRRUser(proto_u)
    self.assertEqual(rdf_u.email, "foo@bar.org")


class UnflattenDictTest(absltest.TestCase):

  def testNothingNested(self):
    result = http_api.UnflattenDict({
        "a": "b",
        "c": "d",
    })
    self.assertEqual(
        result,
        {
            "a": "b",
            "c": "d",
        },
    )

  def testFlatMerged(self):
    result = http_api.UnflattenDict({
        "foo": "outer_foo",
        "inner.foo": "inner_foo",
        "has.more.levels": "1234",  # More than 2 levels
        "inner.list": [  # Merged with `inner.foo`
            "0",
            "JABUTICABA",
        ],
    })
    self.assertEqual(
        result,
        {
            "foo": "outer_foo",
            "inner": {
                "foo": "inner_foo",
                "list": ["0", "JABUTICABA"],
            },
            "has": {
                "more": {
                    "levels": "1234",
                },
            },
        },
    )


class RecursivelyBuildProtoFromStringDictTest(absltest.TestCase):

  def testSingleBool(self):
    proto = tests_pb2.BoolMessage()

    http_api.RecursivelyBuildProtoFromStringDict({"foo": "1"}, proto)
    self.assertEqual(proto, tests_pb2.BoolMessage(foo=True))

    http_api.RecursivelyBuildProtoFromStringDict({"foo": "true"}, proto)
    self.assertEqual(proto, tests_pb2.BoolMessage(foo=True))

    http_api.RecursivelyBuildProtoFromStringDict({"foo": "0"}, proto)
    self.assertEqual(proto, tests_pb2.BoolMessage(foo=False))

    http_api.RecursivelyBuildProtoFromStringDict({"foo": "false"}, proto)
    self.assertEqual(proto, tests_pb2.BoolMessage(foo=False))

  def testEnum(self):
    proto = tests_pb2.EnumMessage()
    http_api.RecursivelyBuildProtoFromStringDict({"foo": "0"}, proto)
    self.assertEqual(
        proto, tests_pb2.EnumMessage(foo=tests_pb2.EnumMessage.NestedEnum.NULL)
    )

    http_api.RecursivelyBuildProtoFromStringDict({"foo": "NULL"}, proto)
    self.assertEqual(
        proto, tests_pb2.EnumMessage(foo=tests_pb2.EnumMessage.NestedEnum.NULL)
    )

    http_api.RecursivelyBuildProtoFromStringDict({"foo": "1"}, proto)
    self.assertEqual(
        proto, tests_pb2.EnumMessage(foo=tests_pb2.EnumMessage.NestedEnum.ONE)
    )

    with self.assertRaises(ValueError):
      http_api.RecursivelyBuildProtoFromStringDict({"foo": "null"}, proto)

    with self.assertRaises(ValueError):
      http_api.RecursivelyBuildProtoFromStringDict({"foo": "100"}, proto)

  def testSimple(self):
    dct = {
        "username": "foo",
        "uid": "42",
    }
    proto = knowledge_base_pb2.User()
    http_api.RecursivelyBuildProtoFromStringDict(dct, proto)

    self.assertEqual(proto.username, "foo")
    self.assertEqual(proto.uid, 42)

  def testFlatDictIsIgnored(self):
    dct = {
        "pw_entry.age": "1337",
    }
    proto = knowledge_base_pb2.User()
    http_api.RecursivelyBuildProtoFromStringDict(dct, proto)

    self.assertEqual(proto, knowledge_base_pb2.User())

  def testNestedDict(self):
    dct = {
        "pw_entry": {"age": "1337"},
    }
    proto = knowledge_base_pb2.User()
    http_api.RecursivelyBuildProtoFromStringDict(dct, proto)

    self.assertEqual(proto.pw_entry.age, 1337)

  def testNonExistingFieldIsIgnored(self):
    dct = {
        "some_non_existing_field": "should_be_ignored",
    }
    proto = knowledge_base_pb2.User()
    http_api.RecursivelyBuildProtoFromStringDict(dct, proto)
    self.assertEqual(proto, knowledge_base_pb2.User())

  def testWrongType(self):
    dct = {
        "uid": "foobar",
    }
    proto = knowledge_base_pb2.User()

    with self.assertRaisesRegex(ValueError, "foobar"):
      http_api.RecursivelyBuildProtoFromStringDict(dct, proto)


def main(argv):
  test_lib.main(argv)


if __name__ == "__main__":
  app.run(main)
