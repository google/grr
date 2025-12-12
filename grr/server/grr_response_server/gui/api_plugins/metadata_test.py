#!/usr/bin/env python
"""This module contains tests for metadata API handlers."""

import json
from unittest import mock

from absl import app
from absl.testing import absltest

from grr_response_core.lib import registry
from grr_response_proto import jobs_pb2
from grr_response_proto import tests_pb2
from grr_response_server import flow_base
from grr_response_server import output_plugin
from grr_response_server.gui import api_call_context
from grr_response_server.gui import api_call_router
from grr_response_server.gui import api_test_lib
from grr_response_server.gui.api_plugins import metadata as metadata_plugin
from grr_response_server.output_plugins import test_plugins
from grr.test_lib import test_lib


class TestMetadataFlow(flow_base.FlowBase):
  """A test flow for API metadata tests."""

  proto_args_type = tests_pb2.BadArgsFlow1Args
  proto_result_types = (tests_pb2.SendingFlowArgs,)
  proto_store_type = tests_pb2.DummyFlowStore
  proto_progress_type = tests_pb2.DummyFlowProgress

  def Start(self):
    self.Log("Starting test flow.")


class MetadataDummyApiCallRouter(api_call_router.ApiCallRouter):
  """Dummy `ApiCallRouter` implementation used for Metadata testing."""

  @api_call_router.ProtoArgsType(tests_pb2.MetadataSimpleMessage)
  @api_call_router.Http("GET", "/metadata_test/method1/<metadata_id>")
  @api_call_router.Http("HEAD", "/metadata_test/method1/<metadata_id>")
  @api_call_router.Http("POST", "/metadata_test/method1/<metadata_id>")
  def Method1WithArgsType(self, args, context=None):
    """Method 1 description."""

  @api_call_router.ProtoResultType(tests_pb2.MetadataSimpleMessage)
  @api_call_router.Http("GET", "/metadata_test/method2")
  @api_call_router.Http("HEAD", "/metadata_test/method2")
  @api_call_router.Http("POST", "/metadata_test/method2")
  def Method2WithResultType(self, args, context=None):
    """Method 2 description."""

  @api_call_router.ProtoArgsType(tests_pb2.MetadataPrimitiveTypesMessage)
  @api_call_router.ResultBinaryStream()
  @api_call_router.Http("GET", "/metadata_test/method3")
  def Method3PrimitiveTypes(self, args, context=None):
    """Method 3 description."""

  @api_call_router.ProtoArgsType(tests_pb2.MetadataRepeatedFieldMessage)
  @api_call_router.Http("GET", "/metadata_test/method4")
  @api_call_router.Http("POST", "/metadata_test/method4")
  def Method4RepeatedField(self, args, context=None):
    """Method 4 description."""

  @api_call_router.ProtoArgsType(tests_pb2.MetadataEnumFieldMessage)
  @api_call_router.Http("GET", "/metadata_test/method5")
  @api_call_router.Http("POST", "/metadata_test/method5")
  def Method5EnumField(self, args, context=None):
    """Method 5 description."""

  @api_call_router.ProtoArgsType(tests_pb2.MetadataTypesHierarchyRoot)
  @api_call_router.ProtoResultType(tests_pb2.MetadataTypesHierarchyLeaf)
  @api_call_router.Http("GET", "/metadata_test/method6")
  def Method6TypeReferences(self, args, context=None):
    """Method 6 description."""

  @api_call_router.ProtoArgsType(tests_pb2.MetadataOneofMessage)
  @api_call_router.ProtoResultType(tests_pb2.MetadataOneofMessage)
  @api_call_router.Http("GET", "/metadata_test/method7")
  @api_call_router.Http("POST", "/metadata_test/method7")
  def Method7ProtobufOneof(self, args, context=None):
    """Method 7 description."""

  @api_call_router.ProtoArgsType(tests_pb2.MetadataMapMessage)
  @api_call_router.ProtoResultType(tests_pb2.MetadataMapMessage)
  @api_call_router.Http("GET", "/metadata_test/method8")
  @api_call_router.Http("POST", "/metadata_test/method8")
  def Method8ProtobufMap(self, args, context=None):
    """Method 8 description."""

  @api_call_router.ProtoArgsType(tests_pb2.MetadataSimpleMessage)
  @api_call_router.ProtoResultType(tests_pb2.MetadataSimpleMessage)
  @api_call_router.Http("GET", "/metadata_test/method9")
  @api_call_router.Http("GET", "/metadata_test/method9/<metadata_id>")
  @api_call_router.Http(
      "POST", "/metadata_test/method9/<metadata_id>/<metadata_arg1>"
  )
  @api_call_router.Http(
      "GET",
      "/metadata_test/method9/<metadata_id>/<metadata_arg1>/<metadata_arg2>",
  )
  @api_call_router.Http("GET", "/metadata_test/method9/<metadata_id>/fixed1")
  @api_call_router.Http(
      "GET", "/metadata_test/method9/<metadata_id>/fixed1/<metadata_arg1>"
  )
  @api_call_router.Http("GET", "/metadata_test/method9/fixed2/")  # Trailing /.
  @api_call_router.Http("GET", "/metadata_test/method9/fixed2/<metadata_arg1>/")
  @api_call_router.Http(
      "GET", "/metadata_test/method9/fixed2/<metadata_arg1>/<metadata_arg2>/"
  )
  def Method9OptionalPathArgs(self, args, context=None):
    """Method 9 description."""

  @api_call_router.ProtoArgsType(tests_pb2.MetadataSemTypeMessage)
  @api_call_router.ProtoResultType(tests_pb2.MetadataSemTypeMessage)
  @api_call_router.Http("GET", "/metadata_test/method10")
  @api_call_router.Http("POST", "/metadata_test/method10")
  def Method10SemTypeProtobufOption(self, args, context=None):
    """Method 10 description."""


class TestRouterHasNoMethods(api_call_router.ApiCallRouter):
  pass


class TestOutputPlugin(
    output_plugin.OutputPluginProto[tests_pb2.MetadataSimpleMessage]
):
  """A test output plugin for API metadata tests."""

  args_type = tests_pb2.MetadataSimpleMessage


class CreateOutputPluginSchemasTest(absltest.TestCase):
  """Test for `_CreateOutputPluginSchemas`."""

  @test_plugins.WithOutputPluginProto(TestOutputPlugin)
  def testOutputPluginProtosAreCorrectlyDescribed(self):
    self.handler = metadata_plugin.ApiGetOpenApiDescriptionHandler(
        TestRouterHasNoMethods()
    )
    with mock.patch.object(
        registry.FlowRegistry,
        "FLOW_REGISTRY",
        {},
    ):
      result = self.handler.Handle(
          None, context=api_call_context.ApiCallContext("api_test_user")
      )

    openapi_desc_dict = json.loads(result.openapi_description)
    schemas = openapi_desc_dict["components"]["schemas"]

    self.assertIn(tests_pb2.MetadataSimpleMessage.DESCRIPTOR.full_name, schemas)
    self.assertEqual(
        {
            "type": "object",
            "properties": {
                "metadataId": {
                    "$ref": "#/components/schemas/protobuf2.TYPE_STRING",
                },
                "metadataArg1": {
                    "$ref": "#/components/schemas/protobuf2.TYPE_INT64",
                },
                "metadataArg2": {
                    "$ref": "#/components/schemas/protobuf2.TYPE_BOOL",
                },
            },
        },
        schemas[tests_pb2.MetadataSimpleMessage.DESCRIPTOR.full_name],
    )


class ApiGetOpenApiDescriptionHandlerTest(api_test_lib.ApiCallHandlerTest):
  """Test for `ApiGetOpenApiDescriptionHandler`."""

  def setUp(self):
    super().setUp()
    self.router = MetadataDummyApiCallRouter()
    self.router_methods = self.router.__class__.GetAnnotatedMethods()

    self.handler = metadata_plugin.ApiGetOpenApiDescriptionHandler(self.router)

    with mock.patch.object(
        registry.FlowRegistry,
        "FLOW_REGISTRY",
        {TestMetadataFlow.__name__: TestMetadataFlow},
    ):
      result = self.handler.Handle(None, context=self.context)

    self.openapi_desc = result.openapi_description
    self.openapi_desc_dict = json.loads(self.openapi_desc)

  def testRouterAnnotatedMethodsAreAllExtracted(self):
    expected_methods = {
        "Method1WithArgsType",
        "Method2WithResultType",
        "Method3PrimitiveTypes",
        "Method4RepeatedField",
        "Method5EnumField",
        "Method6TypeReferences",
        "Method7ProtobufOneof",
        "Method8ProtobufMap",
        "Method9OptionalPathArgs",
        "Method10SemTypeProtobufOption",
    }
    extracted_methods = {method.name for method in self.router_methods.values()}

    self.assertEqual(expected_methods, extracted_methods)

  def testGeneratedOpenApiDescriptionIsValid(self):
    # TODO(user): Move this import to the top when the GitHub
    # issue #813 (https://github.com/google/grr/issues/813) is resolved.
    try:
      # pytype: disable=import-error
      # pylint: disable=g-import-not-at-top
      import openapi_spec_validator
      # pytype: enable=import-error
      # pylint: enable=g-import-not-at-top
    except ImportError:
      raise absltest.SkipTest("`openapi-spec-validator` not installed")

    # Will raise exceptions when the OpenAPI specification is invalid.
    openapi_spec_validator.validate_spec(self.openapi_desc_dict)

  def testAllRoutesAreInOpenApiDescription(self):
    openapi_paths_dict = self.openapi_desc_dict["paths"]

    # Check that there are no extra/missing paths.
    self.assertCountEqual(
        {
            "/metadata_test/method1/{metadataId}",
            "/metadata_test/method2",
            "/metadata_test/method3",
            "/metadata_test/method4",
            "/metadata_test/method5",
            "/metadata_test/method6",
            "/metadata_test/method7",
            "/metadata_test/method8",
            "/metadata_test/method9/{metadataId}",
            "/metadata_test/method9/{metadataId}/{metadataArg1}",
            "/metadata_test/method9/{metadataId}/{metadataArg1}/{metadataArg2}",
            "/metadata_test/method9/{metadataId}/fixed1/{metadataArg1}",
            "/metadata_test/method9/fixed2/{metadataArg1}/{metadataArg2}",
            "/metadata_test/method10",
        },
        openapi_paths_dict.keys(),
    )

    # Check that there are no extra/missing HTTP methods for each path (routes).
    self.assertCountEqual(
        {"get", "head", "post"},
        openapi_paths_dict["/metadata_test/method1/{metadataId}"].keys(),
    )
    self.assertCountEqual(
        {"get", "head", "post"},
        openapi_paths_dict["/metadata_test/method2"].keys(),
    )
    self.assertCountEqual(
        {"get"}, openapi_paths_dict["/metadata_test/method3"].keys()
    )
    self.assertCountEqual(
        {"get", "post"}, openapi_paths_dict["/metadata_test/method4"].keys()
    )
    self.assertCountEqual(
        {"get", "post"}, openapi_paths_dict["/metadata_test/method5"].keys()
    )
    self.assertCountEqual(
        {"get"}, openapi_paths_dict["/metadata_test/method6"].keys()
    )
    self.assertCountEqual(
        {"get", "post"}, openapi_paths_dict["/metadata_test/method7"].keys()
    )
    self.assertCountEqual(
        {"get", "post"}, openapi_paths_dict["/metadata_test/method8"].keys()
    )
    self.assertCountEqual(
        {"get"},
        openapi_paths_dict["/metadata_test/method9/{metadataId}"].keys(),
    )
    self.assertCountEqual(
        {"post"},
        openapi_paths_dict.get(
            "/metadata_test/method9/{metadataId}/{metadataArg1}"
        ).keys(),
    )
    self.assertCountEqual(
        {"get"},
        openapi_paths_dict.get(
            "/metadata_test/method9/{metadataId}/{metadataArg1}/{metadataArg2}"
        ).keys(),
    )
    self.assertCountEqual(
        {"get"},
        openapi_paths_dict.get(
            "/metadata_test/method9/{metadataId}/fixed1/{metadataArg1}"
        ).keys(),
    )

  def testRouteArgsAreCorrectlySeparated(self):
    # Check that the parameters are separated correctly in path, query and
    # request body parameters.

    openapi_paths_dict = self.openapi_desc_dict["paths"]

    # Check the OpenAPI parameters of `Method1WithArgsType` routes.
    method1_path_dict = openapi_paths_dict[
        "/metadata_test/method1/{metadataId}"
    ]

    # Parameters of `GET /metadata_test/method1/{metadata_id}`.
    get_method1_dict = method1_path_dict["get"]

    get_method1_params_path = [
        param["name"]
        for param in get_method1_dict["parameters"]
        if param["in"] == "path"
    ]
    self.assertCountEqual(["metadataId"], get_method1_params_path)

    get_method1_params_query = [
        param["name"]
        for param in get_method1_dict["parameters"]
        if param["in"] == "query"
    ]
    self.assertCountEqual(
        ["metadataArg1", "metadataArg2"], get_method1_params_query
    )

    # `parameters` field is always present, even if it is an empty array,
    # `requestBody` should not be, unless there are arguments in the body.
    self.assertIsNone(get_method1_dict.get("requestBody"))

    # Parameters of `HEAD /metadata_test/method1/{metadata_id}`.
    head_method1_dict = method1_path_dict["head"]

    head_method1_params_path = [
        param["name"]
        for param in head_method1_dict["parameters"]
        if param["in"] == "path"
    ]
    self.assertCountEqual(["metadataId"], head_method1_params_path)

    head_method1_params_query = [
        param["name"]
        for param in get_method1_dict["parameters"]
        if param["in"] == "query"
    ]
    self.assertCountEqual(
        ["metadataArg1", "metadataArg2"], head_method1_params_query
    )

    self.assertIsNone(head_method1_dict.get("requestBody"))

    # Parameters of `POST /metadata_test/method1/{metadata_id}`.
    post_method1_dict = method1_path_dict["post"]

    post_method1_params_path = [
        param["name"]
        for param in post_method1_dict["parameters"]
        if param["in"] == "path"
    ]
    self.assertCountEqual(["metadataId"], post_method1_params_path)

    post_method1_params_query = [
        param["name"]
        for param in post_method1_dict["parameters"]
        if param["in"] == "query"
    ]
    self.assertEmpty(post_method1_params_query)

    # requestBody parameters use their names as keys.
    post_method1_params_body = list(
        post_method1_dict.get("requestBody")
        .get("content")
        .get("application/json")
        .get("schema")
        .get("properties")
    )
    self.assertCountEqual(
        ["metadataArg1", "metadataArg2"], post_method1_params_body
    )

    # Check the OpenAPI parameters of `Method4RepeatedField` routes.
    method4_path_dict = openapi_paths_dict["/metadata_test/method4"]

    # Parameters of `GET /metadata_test/method4`.
    get_method4_dict = method4_path_dict["get"]

    get_method4_params_path = [
        param["name"]
        for param in get_method4_dict["parameters"]
        if param["in"] == "path"
    ]
    self.assertEmpty(get_method4_params_path)

    get_method4_params_query = [
        param["name"]
        for param in get_method4_dict["parameters"]
        if param["in"] == "query"
    ]
    self.assertCountEqual(["fieldRepeated"], get_method4_params_query)

    self.assertIsNone(get_method4_dict.get("requestBody"))

    # Parameters of POST /metadata_test/method4.
    post_method4_dict = method4_path_dict["post"]

    post_method4_params_path = [
        param["name"]
        for param in post_method4_dict["parameters"]
        if param["in"] == "path"
    ]
    self.assertEmpty(post_method4_params_path)

    post_method4_params_query = [
        param["name"]
        for param in post_method4_dict["parameters"]
        if param["in"] == "query"
    ]
    self.assertEmpty(post_method4_params_query)

    post_method4_params_body = list(
        post_method4_dict.get("requestBody")
        .get("content")
        .get("application/json")
        .get("schema")
        .get("properties")
    )
    self.assertCountEqual(["fieldRepeated"], post_method4_params_body)

    # Check the OpenAPI parameters of `Method5EnumField` routes.
    method5_path_dict = openapi_paths_dict["/metadata_test/method5"]

    # Parameters of `GET /metadata_test/method5`.
    get_method5_dict = method5_path_dict["get"]

    get_method5_params_path = [
        param["name"]
        for param in get_method5_dict["parameters"]
        if param["in"] == "path"
    ]
    self.assertEmpty(get_method5_params_path)

    get_method5_params_query = [
        param["name"]
        for param in get_method5_dict["parameters"]
        if param["in"] == "query"
    ]
    self.assertCountEqual(["fieldEnum"], get_method5_params_query)

    self.assertIsNone(get_method5_dict.get("requestBody"))

    # Parameters of `POST /metadata_test/method5`.
    post_method5_dict = method5_path_dict["post"]

    post_method5_params_path = [
        param["name"]
        for param in post_method5_dict["parameters"]
        if param["in"] == "path"
    ]
    self.assertEmpty(post_method5_params_path)

    post_method5_params_query = [
        param["name"]
        for param in post_method5_dict["parameters"]
        if param["in"] == "query"
    ]
    self.assertEmpty(post_method5_params_query)

    post_method5_params_body = list(
        post_method5_dict.get("requestBody")
        .get("content")
        .get("application/json")
        .get("schema")
        .get("properties")
    )
    self.assertCountEqual(["fieldEnum"], post_method5_params_body)

    # Check the OpenAPI parameters of `Method6TypeReferences` routes.
    method6_path_dict = openapi_paths_dict["/metadata_test/method6"]

    # Parameters of `GET /metadata_test/method6`.
    get_method6_dict = method6_path_dict["get"]

    get_method6_params_path = [
        param["name"]
        for param in get_method6_dict["parameters"]
        if param["in"] == "path"
    ]
    self.assertEmpty(get_method6_params_path)

    get_method6_params_query = [
        param["name"]
        for param in get_method6_dict["parameters"]
        if param["in"] == "query"
    ]
    self.assertCountEqual(
        ["fieldInt64", "child1", "child2"], get_method6_params_query
    )

    self.assertIsNone(get_method6_dict.get("requestBody"))

    # Check the OpenAPI parameters of `Method7ProtobufOneof` routes.
    method7_path_dict = openapi_paths_dict["/metadata_test/method7"]

    # Parameters of `GET /metadata_test/method7`.
    get_method7_dict = method7_path_dict["get"]

    get_method7_params_path = [
        param["name"]
        for param in get_method7_dict["parameters"]
        if param["in"] == "path"
    ]
    self.assertEmpty(get_method7_params_path)

    get_method7_params_query = [
        param["name"]
        for param in get_method7_dict["parameters"]
        if param["in"] == "query"
    ]
    self.assertCountEqual(
        ["oneofInt64", "oneofSimplemsg", "fieldInt64"], get_method7_params_query
    )

    self.assertIsNone(get_method7_dict.get("requestBody"))

  def testRoutesResultsAreCorrectlyDescribedInOpenApiDescription(self):
    # Verify the OpenAPI schemas of the response objects.
    # Response types are usually protobuf messages. The expectation in these
    # cases is that the route descriptions include a reference to the type
    # schemas in the `components` field of the root `OpenAPI Object`.
    openapi_paths_dict = self.openapi_desc_dict["paths"]

    # `Method2WithResultType (GET, HEAD, POST)` => `MetadataSimpleMessage`
    method2_path_dict = openapi_paths_dict["/metadata_test/method2"]
    # Check responses for `GET /metadata_test/method2`.
    self.assertEqual(
        {
            "200": {
                "description": (
                    "The call to the Method2WithResultType API method "
                    "succeeded and it returned an instance of "
                    f"{tests_pb2.MetadataSimpleMessage.DESCRIPTOR.full_name}."
                ),
                "content": {
                    "application/json": {
                        "schema": {
                            "$ref": f"#/components/schemas/{tests_pb2.MetadataSimpleMessage.DESCRIPTOR.full_name}",
                        },
                    },
                },
            },
            "default": {
                "description": (
                    "The call to the Method2WithResultType API method did "
                    "not succeed."
                ),
            },
        },
        method2_path_dict["get"]["responses"],
    )
    # Check responses for HEAD /metadata_test/method2.
    self.assertEqual(
        {
            "200": {
                "description": (
                    "The call to the Method2WithResultType API method "
                    "succeeded and it returned an instance of "
                    f"{tests_pb2.MetadataSimpleMessage.DESCRIPTOR.full_name}."
                ),
                "content": {
                    "application/json": {
                        "schema": {
                            "$ref": f"#/components/schemas/{tests_pb2.MetadataSimpleMessage.DESCRIPTOR.full_name}",
                        },
                    },
                },
            },
            "default": {
                "description": (
                    "The call to the Method2WithResultType API method did "
                    "not succeed."
                ),
            },
        },
        method2_path_dict["head"]["responses"],
    )
    # Check responses for `POST /metadata_test/method2`.
    self.assertEqual(
        {
            "200": {
                "description": (
                    "The call to the Method2WithResultType API method "
                    "succeeded and it returned an instance of "
                    f"{tests_pb2.MetadataSimpleMessage.DESCRIPTOR.full_name}."
                ),
                "content": {
                    "application/json": {
                        "schema": {
                            "$ref": f"#/components/schemas/{tests_pb2.MetadataSimpleMessage.DESCRIPTOR.full_name}",
                        },
                    },
                },
            },
            "default": {
                "description": (
                    "The call to the Method2WithResultType API method did "
                    "not succeed."
                ),
            },
        },
        method2_path_dict["post"]["responses"],
    )

    # Method3PrimitiveTypes (GET) => BinaryStream result type.
    method3_path_dict = openapi_paths_dict["/metadata_test/method3"]
    # Check responses for GET /metadata_test/method3.
    self.assertEqual(
        {
            "200": {
                "description": (
                    "The call to the Method3PrimitiveTypes API method "
                    "succeeded and it returned an instance of "
                    "BinaryStream."
                ),
                "content": {
                    "application/octet-stream": {
                        "schema": {
                            "$ref": "#/components/schemas/BinaryStream",
                        },
                    },
                },
            },
            "default": {
                "description": (
                    "The call to the Method3PrimitiveTypes API method did "
                    "not succeed."
                ),
            },
        },
        method3_path_dict["get"]["responses"],
    )

    # `Method4RepeatedField (GET, POST)` => No result type.
    method4_path_dict = openapi_paths_dict["/metadata_test/method4"]
    # Check responses for `GET /metadata_test/method4`.
    self.assertEqual(
        {
            "200": {
                "description": (
                    "The call to the Method4RepeatedField API method succeeded."
                ),
            },
            "default": {
                "description": (
                    "The call to the Method4RepeatedField API method did "
                    "not succeed."
                ),
            },
        },
        method4_path_dict["get"]["responses"],
    )
    # Check responses for `POST /metadata_test/method4`.
    self.assertEqual(
        {
            "200": {
                "description": (
                    "The call to the Method4RepeatedField API method succeeded."
                ),
            },
            "default": {
                "description": (
                    "The call to the Method4RepeatedField API method did "
                    "not succeed."
                ),
            },
        },
        method4_path_dict["post"]["responses"],
    )

  def testPrimitiveTypesAreCorrectlyDescribedAndUsedInOpenApiDescription(self):
    # Primitive type schemas are described in the `components` field of the
    # root `OpenAPI Object`.

    # Firstly, verify that the descriptions of the fields of the
    # `MetadataPrimitiveTypesMessage` (which is the `ArgsType` of
    # `Method3PrimitiveTypes`) include references to the primitive type
    # descriptions.
    self.assertEqual(
        {"$ref": "#/components/schemas/protobuf2.TYPE_DOUBLE"},
        self._GetParamSchema("/metadata_test/method3", "get", "fieldDouble"),
    )
    self.assertEqual(
        {"$ref": "#/components/schemas/protobuf2.TYPE_FLOAT"},
        self._GetParamSchema("/metadata_test/method3", "get", "fieldFloat"),
    )
    self.assertEqual(
        {"$ref": "#/components/schemas/protobuf2.TYPE_INT64"},
        self._GetParamSchema("/metadata_test/method3", "get", "fieldInt64"),
    )
    self.assertEqual(
        {"$ref": "#/components/schemas/protobuf2.TYPE_UINT64"},
        self._GetParamSchema("/metadata_test/method3", "get", "fieldUint64"),
    )
    self.assertEqual(
        {"$ref": "#/components/schemas/protobuf2.TYPE_INT32"},
        self._GetParamSchema("/metadata_test/method3", "get", "fieldInt32"),
    )
    self.assertEqual(
        {"$ref": "#/components/schemas/protobuf2.TYPE_FIXED64"},
        self._GetParamSchema("/metadata_test/method3", "get", "fieldFixed64"),
    )
    self.assertEqual(
        {"$ref": "#/components/schemas/protobuf2.TYPE_FIXED32"},
        self._GetParamSchema("/metadata_test/method3", "get", "fieldFixed32"),
    )
    self.assertEqual(
        {"$ref": "#/components/schemas/protobuf2.TYPE_BOOL"},
        self._GetParamSchema("/metadata_test/method3", "get", "fieldBool"),
    )
    self.assertEqual(
        {"$ref": "#/components/schemas/protobuf2.TYPE_STRING"},
        self._GetParamSchema("/metadata_test/method3", "get", "fieldString"),
    )
    self.assertEqual(
        {"$ref": "#/components/schemas/protobuf2.TYPE_BYTES"},
        self._GetParamSchema("/metadata_test/method3", "get", "fieldBytes"),
    )
    self.assertEqual(
        {"$ref": "#/components/schemas/protobuf2.TYPE_UINT32"},
        self._GetParamSchema("/metadata_test/method3", "get", "fieldUint32"),
    )
    self.assertEqual(
        {"$ref": "#/components/schemas/protobuf2.TYPE_SFIXED32"},
        self._GetParamSchema("/metadata_test/method3", "get", "fieldSfixed32"),
    )
    self.assertEqual(
        {"$ref": "#/components/schemas/protobuf2.TYPE_SFIXED64"},
        self._GetParamSchema("/metadata_test/method3", "get", "fieldSfixed64"),
    )
    self.assertEqual(
        {"$ref": "#/components/schemas/protobuf2.TYPE_SINT32"},
        self._GetParamSchema("/metadata_test/method3", "get", "fieldSint32"),
    )
    self.assertEqual(
        {"$ref": "#/components/schemas/protobuf2.TYPE_SINT64"},
        self._GetParamSchema("/metadata_test/method3", "get", "fieldSint64"),
    )

    # Extract `BinaryStream` type reference from the response schema.
    self.assertEqual(
        {"$ref": "#/components/schemas/BinaryStream"},
        self.openapi_desc_dict.get("paths")
        .get("/metadata_test/method3")
        .get("get")
        .get("responses")
        .get("200")
        .get("content")
        .get("application/octet-stream")
        .get("schema"),
    )

    # Secondly, verify the descriptions of primitive types from the `components`
    # field of the root `OpenAPI Object`.
    component_schemas = self.openapi_desc_dict["components"]["schemas"]

    self.assertEqual(
        {"type": "number", "format": "double"},
        component_schemas["protobuf2.TYPE_DOUBLE"],
    )
    self.assertEqual(
        {"type": "number", "format": "float"},
        component_schemas["protobuf2.TYPE_FLOAT"],
    )
    self.assertEqual(
        {"type": "string", "format": "int64"},
        component_schemas["protobuf2.TYPE_INT64"],
    )
    self.assertEqual(
        {"type": "string", "format": "uint64"},
        component_schemas["protobuf2.TYPE_UINT64"],
    )
    self.assertEqual(
        {"type": "integer", "format": "int32"},
        component_schemas["protobuf2.TYPE_INT32"],
    )
    self.assertEqual(
        {"type": "string", "format": "fixed64"},
        component_schemas["protobuf2.TYPE_FIXED64"],
    )
    self.assertEqual(
        {"type": "number", "format": "fixed32"},
        component_schemas["protobuf2.TYPE_FIXED32"],
    )
    self.assertEqual(
        {"type": "boolean"}, component_schemas["protobuf2.TYPE_BOOL"]
    )
    self.assertEqual(
        {"type": "string"}, component_schemas["protobuf2.TYPE_STRING"]
    )
    self.assertEqual(
        {"type": "string", "format": "byte"},
        component_schemas["protobuf2.TYPE_BYTES"],
    )
    self.assertEqual(
        {"type": "number", "format": "uint32"},
        component_schemas["protobuf2.TYPE_UINT32"],
    )
    self.assertEqual(
        {"type": "number", "format": "sfixed32"},
        component_schemas["protobuf2.TYPE_SFIXED32"],
    )
    self.assertEqual(
        {"type": "string", "format": "sfixed64"},
        component_schemas["protobuf2.TYPE_SFIXED64"],
    )
    self.assertEqual(
        {"type": "integer", "format": "int32"},
        component_schemas["protobuf2.TYPE_INT32"],
    )
    self.assertEqual(
        {"type": "string", "format": "sint64"},
        component_schemas["protobuf2.TYPE_SINT64"],
    )
    self.assertEqual(
        {"type": "string", "format": "binary"},
        component_schemas["BinaryStream"],
    )

  def testRepeatedFieldIsDescribedCorrectlyInOpenApiDescription(self):
    # Extract the `repeated` field from the description of the `GET` route
    # associated with `Method4RepeatedField`.
    # The `repeated` field should be the only parameter and be a query
    # parameter. This aspect is tested by `testRouteArgsAreCorrectlySeparated`.
    get_method4_repeated_field_schema = (
        self.openapi_desc_dict.get("paths")
        .get("/metadata_test/method4")
        .get("get")
        .get("parameters")[0]
        .get("schema")
    )
    self.assertEqual(
        {
            "type": "array",
            "items": {
                "$ref": "#/components/schemas/protobuf2.TYPE_INT64",
            },
        },
        get_method4_repeated_field_schema,
    )

    # Extract the `repeated` field from the description of the `POST` route
    # associated with `Method4RepeatedField`.
    # The repeated field should be the only parameter and be a request body
    # parameter. This aspect is tested by `testRouteArgsAreCorrectlySeparated`.
    post_method4_repeated_field_schema = (
        self.openapi_desc_dict.get("paths")
        .get("/metadata_test/method4")
        .get("post")
        .get("requestBody")
        .get("content")
        .get("application/json")
        .get("schema")
        .get("properties")
        .get("fieldRepeated")
    )
    self.assertEqual(
        {
            "type": "array",
            "items": {
                "$ref": "#/components/schemas/protobuf2.TYPE_INT64",
            },
        },
        post_method4_repeated_field_schema,
    )

  def testEnumFieldIsDescribedCorrectlyInOpenApiDescription(self):
    # The enum type is user defined, so it is reusable and described separately
    # from the field itself, in the `component` field of the root `OpenAPI
    # Object`. Therefore, the expectation is that this field has a reference to
    # the enum type description.
    # We test both the references and the type definition.

    # Test the OpenAPI schema description of the *enum field*.

    # Extract the enum field schema from the description of the `GET` route
    # associated with `Method5EnumField`.
    get_method5_enum_field_schema = (
        self.openapi_desc_dict.get("paths")
        .get("/metadata_test/method5")
        .get("get")
        .get("parameters")[0]
        .get("schema")
    )
    self.assertEqual(
        {
            "description": "UNKNOWN == 0\nFOO == 1\nBAR == 2",
            "allOf": [
                {
                    "$ref": f"#/components/schemas/{tests_pb2.MetadataEnumFieldMessage.MetadataEnum.DESCRIPTOR.full_name}",
                },
            ],
        },
        get_method5_enum_field_schema,
    )

    # Extract the enum field schema from the description of the POST route
    # associated with `Method5EnumField`.
    post_method5_enum_field_schema = (
        self.openapi_desc_dict.get("paths")
        .get("/metadata_test/method5")
        .get("post")
        .get("requestBody")
        .get("content")
        .get("application/json")
        .get("schema")
        .get("properties")
        .get("fieldEnum")
    )
    self.assertEqual(
        {
            "description": "UNKNOWN == 0\nFOO == 1\nBAR == 2",
            "allOf": [
                {
                    "$ref": f"#/components/schemas/{tests_pb2.MetadataEnumFieldMessage.MetadataEnum.DESCRIPTOR.full_name}",
                },
            ],
        },
        post_method5_enum_field_schema,
    )

    # Test the OpenAPI schema description of the *enum field's type*.
    openapi_enum_type_schema = (
        self.openapi_desc_dict.get("components")
        .get("schemas")
        .get(
            f"{tests_pb2.MetadataEnumFieldMessage.MetadataEnum.DESCRIPTOR.full_name}"
        )
    )

    self.assertEqual(
        {
            "type": "string",
            "enum": ["UNKNOWN", "FOO", "BAR"],
            "description": "UNKNOWN == 0\nFOO == 1\nBAR == 2",
        },
        openapi_enum_type_schema,
    )

  def testTypeReferencesAreUsedInOpenApiDescriptionsOfCompositeTypes(self):
    # Tests that references are used for composite types and that the referenced
    # types are declared, including the case of cyclic dependencies.

    # Test that composite types are defined.
    openapi_component_schemas = self.openapi_desc_dict.get("components").get(
        "schemas"
    )
    root = openapi_component_schemas[
        tests_pb2.MetadataTypesHierarchyRoot.DESCRIPTOR.full_name
    ]
    cyclic = openapi_component_schemas[
        tests_pb2.MetadataTypesHierarchyCyclic.DESCRIPTOR.full_name
    ]

    # Test the references between message types.
    root_ref = f"#/components/schemas/{tests_pb2.MetadataTypesHierarchyRoot.DESCRIPTOR.full_name}"
    cyclic_ref = f"#/components/schemas/{tests_pb2.MetadataTypesHierarchyCyclic.DESCRIPTOR.full_name}"
    leaf_ref = f"#/components/schemas/{tests_pb2.MetadataTypesHierarchyLeaf.DESCRIPTOR.full_name}"

    self.assertEqual(root["properties"]["child1"]["$ref"], cyclic_ref)
    self.assertEqual(root["properties"]["child2"]["$ref"], leaf_ref)

    self.assertEqual(cyclic["properties"]["root"]["$ref"], root_ref)  # Cycle.
    self.assertEqual(cyclic["properties"]["child1"]["$ref"], leaf_ref)

  def testProtobufOneofIsDescribedCorrectlyInOpenApiDescription(self):
    # The semantic of `protobuf.oneof` is not currently supported by the
    # OpenAPI Specification (see this GitHub issue [1] for more details) and
    # for the moment we just add the `oneof`'s fields as regular `Parameter
    # Object`s or as schema properties with a `description` field stating that
    # only one of the `protobuf.oneof`'s fields should be present at a time.
    #
    # [1]: github.com/google/grr/issues/822

    # Check the description of the `protobuf.oneof` from the `parameters` field
    # of the `Operation Object` associated with `GET /metadata-test/method7`.
    # Check the `oneof_int64` inner field of the `metadata_oneof`.
    self.assertEqual(
        {
            "description": (
                'This field is part of the "metadata_oneof" oneof. '
                "Only one field per oneof should be present."
            ),
            "allOf": [
                {
                    "$ref": "#/components/schemas/protobuf2.TYPE_INT64",
                },
            ],
        },
        self._GetParamSchema("/metadata_test/method7", "get", "oneofInt64"),
    )
    # Check the `oneof_simplemsg` inner field of the `metadata_oneof`.
    self.assertEqual(
        {
            "description": (
                'This field is part of the "metadata_oneof" oneof. '
                "Only one field per oneof should be present."
            ),
            "allOf": [
                {
                    "$ref": f"#/components/schemas/{tests_pb2.MetadataSimpleMessage.DESCRIPTOR.full_name}",
                },
            ],
        },
        self._GetParamSchema("/metadata_test/method7", "get", "oneofSimplemsg"),
    )

    # Check the description of the `protobuf.oneof` from the `requestBody` field
    # of the `Operation Object` associated with `POST /metadata-test/method7`.
    # Check the `oneof_int64` inner field of the `metadata_oneof`.
    self.assertEqual(
        {
            "description": (
                'This field is part of the "metadata_oneof" oneof. '
                "Only one field per oneof should be present."
            ),
            "allOf": [
                {
                    "$ref": "#/components/schemas/protobuf2.TYPE_INT64",
                },
            ],
        },
        self._GetParamSchema("/metadata_test/method7", "post", "oneofInt64"),
    )
    # Check the `oneof_simplemsg` inner field of the `metadata_oneof`.
    self.assertEqual(
        {
            "description": (
                'This field is part of the "metadata_oneof" oneof. '
                "Only one field per oneof should be present."
            ),
            "allOf": [
                {
                    "$ref": f"#/components/schemas/{tests_pb2.MetadataSimpleMessage.DESCRIPTOR.full_name}",
                },
            ],
        },
        self._GetParamSchema(
            "/metadata_test/method7", "post", "oneofSimplemsg"
        ),
    )

  def testProtobufMapIsDescribedCorrectlyInOpenApiDescription(self):
    # The semantic of `protobuf.map` is partially supported by the OpenAPI
    # Specification, as OAS supports only `string` for the keys' type, while
    # `protobuf.map`s key types can be any of a set of primitive types [1].
    #
    # [1]: https://developers.google.com/protocol-buffers/docs/proto#maps

    # Firstly, check the map schema definition from the `Components Object`.
    openapi_map_type_schema = (
        self.openapi_desc_dict.get("components")
        .get("schemas")
        .get(
            f"{tests_pb2.MetadataMapMessage.DESCRIPTOR.full_name}.FieldMapMap_"
            f"protobuf2.TYPE_SFIXED64:{tests_pb2.MetadataSimpleMessage.DESCRIPTOR.full_name}"
        )
    )
    self.assertEqual(
        {
            "description": (
                "This is a map with real key "
                'type="protobuf2.TYPE_SFIXED64" and value '
                f'type="{tests_pb2.MetadataSimpleMessage.DESCRIPTOR.full_name}"'
            ),
            "type": "object",
            "additionalProperties": {
                "$ref": f"#/components/schemas/{tests_pb2.MetadataSimpleMessage.DESCRIPTOR.full_name}",
            },
        },
        openapi_map_type_schema,
    )

    # Secondly, check the description of the `field_map` route parameter.
    # Check the description of `field_map` from the `parameters` field of the
    # `Operation Object` associated with `GET /metadata-test/method8`.
    self.assertEqual(
        {
            "description": (
                "This is a map with real key "
                'type="protobuf2.TYPE_SFIXED64" and value '
                f'type="{tests_pb2.MetadataSimpleMessage.DESCRIPTOR.full_name}"'
            ),
            "allOf": [
                {
                    "$ref": (
                        f"#/components/schemas/{tests_pb2.MetadataMapMessage.DESCRIPTOR.full_name}.FieldMapMap_"
                        f"protobuf2.TYPE_SFIXED64:{tests_pb2.MetadataSimpleMessage.DESCRIPTOR.full_name}"
                    ),
                },
            ],
        },
        self._GetParamSchema("/metadata_test/method8", "get", "fieldMap"),
    )

    # Check the description of `field_map` from the `requestBody` field of the
    # `Operation Object` associated with `POST /metadata-test/method8`.
    self.assertEqual(
        {
            "description": (
                "This is a map with real key "
                'type="protobuf2.TYPE_SFIXED64" and value '
                f'type="{tests_pb2.MetadataSimpleMessage.DESCRIPTOR.full_name}"'
            ),
            "allOf": [
                {
                    "$ref": (
                        f"#/components/schemas/{tests_pb2.MetadataMapMessage.DESCRIPTOR.full_name}.FieldMapMap_"
                        f"protobuf2.TYPE_SFIXED64:{tests_pb2.MetadataSimpleMessage.DESCRIPTOR.full_name}"
                    ),
                },
            ],
        },
        self._GetParamSchema("/metadata_test/method8", "post", "fieldMap"),
    )

  def testOptionalPathParamsAreCorrectlyDescribedInOpenApiDescription(self):
    # This test verifies that path arguments are marked correctly as optional or
    # required.
    # The fact that the API routes that point out optional path arguments are
    # grouped under the same route described in the OpenAPI description is
    # tested by `testAllRoutesAreInOpenApiDescription`.

    # Test `GET /metadata_test/method9/{metadataId}` parameters.
    self.assertCountEqual(
        [
            {
                "name": "metadataId",
                "in": "path",
                "schema": {
                    "$ref": "#/components/schemas/protobuf2.TYPE_STRING",
                },
            },
            {
                "name": "metadataArg1",
                "in": "query",
                "schema": {
                    "$ref": "#/components/schemas/protobuf2.TYPE_INT64",
                },
            },
            {
                "name": "metadataArg2",
                "in": "query",
                "schema": {
                    "$ref": "#/components/schemas/protobuf2.TYPE_BOOL",
                },
            },
        ],
        [
            self._GetParamDescription(
                "/metadata_test/method9/{metadataId}", "get", "metadataId"
            ),
            self._GetParamDescription(
                "/metadata_test/method9/{metadataId}", "get", "metadataArg1"
            ),
            self._GetParamDescription(
                "/metadata_test/method9/{metadataId}", "get", "metadataArg2"
            ),
        ],
    )

    # Test `GET /metadata_test/method9/{metadataId}/fixed1/{metadataArg1}`
    # parameters.
    self.assertCountEqual(
        [
            {
                "name": "metadataId",
                "in": "path",
                "required": True,
                "schema": {
                    "$ref": "#/components/schemas/protobuf2.TYPE_STRING",
                },
            },
            {
                "name": "metadataArg1",
                "in": "path",
                "schema": {
                    "$ref": "#/components/schemas/protobuf2.TYPE_INT64",
                },
            },
            {
                "name": "metadataArg2",
                "in": "query",
                "schema": {
                    "$ref": "#/components/schemas/protobuf2.TYPE_BOOL",
                },
            },
        ],
        [
            self._GetParamDescription(
                "/metadata_test/method9/{metadataId}/fixed1/{metadataArg1}",
                "get",
                "metadataId",
            ),
            self._GetParamDescription(
                "/metadata_test/method9/{metadataId}/fixed1/{metadataArg1}",
                "get",
                "metadataArg1",
            ),
            self._GetParamDescription(
                "/metadata_test/method9/{metadataId}/fixed1/{metadataArg1}",
                "get",
                "metadataArg2",
            ),
        ],
    )

    # Test
    # `GET /metadata_test/method9/{metadataId}/{metadataArg1}/{metadataArg2}`
    # parameters.
    self.assertCountEqual(
        [
            {
                "name": "metadataId",
                "in": "path",
                "required": True,
                "schema": {
                    "$ref": "#/components/schemas/protobuf2.TYPE_STRING",
                },
            },
            {
                "name": "metadataArg1",
                "in": "path",
                "required": True,
                "schema": {
                    "$ref": "#/components/schemas/protobuf2.TYPE_INT64",
                },
            },
            {
                "name": "metadataArg2",
                "in": "path",
                "required": True,
                "schema": {
                    "$ref": "#/components/schemas/protobuf2.TYPE_BOOL",
                },
            },
        ],
        [
            self._GetParamDescription(
                "/metadata_test"
                "/method9/{metadataId}/{metadataArg1}/{metadataArg2}",
                "get",
                "metadataId",
            ),
            self._GetParamDescription(
                "/metadata_test"
                "/method9/{metadataId}/{metadataArg1}/{metadataArg2}",
                "get",
                "metadataArg1",
            ),
            self._GetParamDescription(
                "/metadata_test"
                "/method9/{metadataId}/{metadataArg1}/{metadataArg2}",
                "get",
                "metadataArg2",
            ),
        ],
    )

    # Test `POST /metadata_test/method9/{metadataId}/{metadataArg1}`
    # parameters.
    self.assertCountEqual(
        [
            {
                "name": "metadataId",
                "in": "path",
                "required": True,
                "schema": {
                    "$ref": "#/components/schemas/protobuf2.TYPE_STRING",
                },
            },
            {
                "name": "metadataArg1",
                "in": "path",
                "required": True,
                "schema": {
                    "$ref": "#/components/schemas/protobuf2.TYPE_INT64",
                },
            },
        ],
        [
            self._GetParamDescription(
                "/metadata_test/method9/{metadataId}/{metadataArg1}",
                "post",
                "metadataId",
            ),
            self._GetParamDescription(
                "/metadata_test/method9/{metadataId}/{metadataArg1}",
                "post",
                "metadataArg1",
            ),
        ],
    )

    # Test `GET /metadata_test/method9/fixed2/{metadataArg1}/{metadataArg2}`
    # parameters.
    self.assertCountEqual(
        [
            {
                "name": "metadataId",
                "in": "query",
                "schema": {
                    "$ref": "#/components/schemas/protobuf2.TYPE_STRING",
                },
            },
            {
                "name": "metadataArg1",
                "in": "path",
                "schema": {
                    "$ref": "#/components/schemas/protobuf2.TYPE_INT64",
                },
            },
            {
                "name": "metadataArg2",
                "in": "path",
                "schema": {
                    "$ref": "#/components/schemas/protobuf2.TYPE_BOOL",
                },
            },
        ],
        [
            self._GetParamDescription(
                "/metadata_test/method9/fixed2/{metadataArg1}/{metadataArg2}",
                "get",
                "metadataId",
            ),
            self._GetParamDescription(
                "/metadata_test/method9/fixed2/{metadataArg1}/{metadataArg2}",
                "get",
                "metadataArg1",
            ),
            self._GetParamDescription(
                "/metadata_test/method9/fixed2/{metadataArg1}/{metadataArg2}",
                "get",
                "metadataArg2",
            ),
        ],
    )

  def _GetParamDescription(self, method_path, http_method, param_name):
    params = (
        self.openapi_desc_dict.get("paths")
        .get(method_path)
        .get(http_method)
        .get("parameters")
    )

    for param in params:
      if param["name"] == param_name:
        return param

    return None

  def _GetParamSchema(self, method_path, http_method, param_name):
    param_description = self._GetParamDescription(
        method_path, http_method, param_name
    )

    if param_description is not None:
      return param_description["schema"]

    if http_method == "post":
      # Try finding the param in the `requestBody`.
      return (
          self.openapi_desc_dict.get("paths")
          .get(method_path)
          .get(http_method)
          .get("requestBody")
          .get("content")
          .get("application/json")
          .get("schema")
          .get("properties")
          .get(param_name)
      )

    return None

  def testRDFTypesAreCorrectlyDescribedAndUsedInOpenApiDescription(self):
    # First, check that fields which have a `sem_type` protobuf field option are
    # described using the `sem_type.type`'s schema.
    expected_field_datetime = {
        "description": (
            "RDF type is `RDFDatetime` and it represents the number "
            "of microseconds since epoch to a timestamp."
        ),
        "allOf": [
            {
                "$ref": "#/components/schemas/RDFDatetime",
            },
        ],
    }
    self.assertEqual(
        expected_field_datetime,
        self._GetParamSchema("/metadata_test/method10", "get", "fieldDatetime"),
    )
    self.assertEqual(
        expected_field_datetime,
        self._GetParamSchema(
            "/metadata_test/method10", "post", "fieldDatetime"
        ),
    )

    expected_field_datetimeseconds = {
        "description": (
            "RDF type is `RDFDatetimeSeconds` and it represents the "
            "number of seconds since epoch to a timestamp."
        ),
        "allOf": [
            {
                "$ref": "#/components/schemas/RDFDatetimeSeconds",
            },
        ],
    }
    self.assertEqual(
        expected_field_datetimeseconds,
        self._GetParamSchema(
            "/metadata_test/method10", "get", "fieldDatetimeseconds"
        ),
    )
    self.assertEqual(
        expected_field_datetimeseconds,
        self._GetParamSchema(
            "/metadata_test/method10", "post", "fieldDatetimeseconds"
        ),
    )

    expected_field_duration = {
        "description": (
            "RDF type is `Duration` and it represents the number of "
            "microseconds between two timestamps."
        ),
        "allOf": [
            {
                "$ref": "#/components/schemas/Duration",
            },
        ],
    }
    self.assertEqual(
        expected_field_duration,
        self._GetParamSchema(
            "/metadata_test/method10", "get", "fieldDurationmicros"
        ),
    )
    self.assertEqual(
        expected_field_duration,
        self._GetParamSchema(
            "/metadata_test/method10", "post", "fieldDurationmicros"
        ),
    )

    expected_field_durationseconds = {
        "description": (
            "RDF type is `DurationSeconds` and it represents the "
            "number of seconds between two timestamps."
        ),
        "allOf": [
            {
                "$ref": "#/components/schemas/DurationSeconds",
            },
        ],
    }
    self.assertEqual(
        expected_field_durationseconds,
        self._GetParamSchema(
            "/metadata_test/method10", "get", "fieldDurationseconds"
        ),
    )
    self.assertEqual(
        expected_field_durationseconds,
        self._GetParamSchema(
            "/metadata_test/method10", "post", "fieldDurationseconds"
        ),
    )

    expected_field_rdfbytes = {
        "description": (
            "RDF type is `RDFBytes` and it represents a buffer of bytes."
        ),
        "allOf": [
            {
                "$ref": "#/components/schemas/RDFBytes",
            },
        ],
    }
    self.assertEqual(
        expected_field_rdfbytes,
        self._GetParamSchema("/metadata_test/method10", "get", "fieldRdfbytes"),
    )
    self.assertEqual(
        expected_field_rdfbytes,
        self._GetParamSchema(
            "/metadata_test/method10", "post", "fieldRdfbytes"
        ),
    )

    expected_field_hashdigest = {
        "description": (
            "RDF type is `HashDigest` and it represents a binary hash "
            "digest with hex string representation."
        ),
        "allOf": [
            {
                "$ref": "#/components/schemas/HashDigest",
            },
        ],
    }
    self.assertEqual(
        expected_field_hashdigest,
        self._GetParamSchema(
            "/metadata_test/method10", "get", "fieldHashdigest"
        ),
    )
    self.assertEqual(
        expected_field_hashdigest,
        self._GetParamSchema(
            "/metadata_test/method10", "post", "fieldHashdigest"
        ),
    )

    expected_field_globexpression = {
        "description": (
            "RDF type is `GlobExpression` and it represents a glob "
            "expression for a client path."
        ),
        "allOf": [
            {
                "$ref": "#/components/schemas/GlobExpression",
            },
        ],
    }
    self.assertEqual(
        expected_field_globexpression,
        self._GetParamSchema(
            "/metadata_test/method10", "get", "fieldGlobexpression"
        ),
    )
    self.assertEqual(
        expected_field_globexpression,
        self._GetParamSchema(
            "/metadata_test/method10", "post", "fieldGlobexpression"
        ),
    )

    expected_field_bytesize = {
        "description": (
            "RDF type is `ByteSize` and it represents a size for "
            "bytes allowing standard unit prefixes."
        ),
        "allOf": [
            {
                "$ref": "#/components/schemas/ByteSize",
            },
        ],
    }
    self.assertEqual(
        expected_field_bytesize,
        self._GetParamSchema("/metadata_test/method10", "get", "fieldBytesize"),
    )
    self.assertEqual(
        expected_field_bytesize,
        self._GetParamSchema(
            "/metadata_test/method10", "post", "fieldBytesize"
        ),
    )

    expected_field_rdfurn = {
        "description": (
            "RDF type is `RDFURN` and it represents an object to "
            "abstract URL manipulation."
        ),
        "allOf": [
            {
                "$ref": "#/components/schemas/RDFURN",
            },
        ],
    }
    self.assertEqual(
        expected_field_rdfurn,
        self._GetParamSchema("/metadata_test/method10", "get", "fieldRdfurn"),
    )
    self.assertEqual(
        expected_field_rdfurn,
        self._GetParamSchema("/metadata_test/method10", "post", "fieldRdfurn"),
    )

    expected_field_sessionid = {
        "description": (
            "RDF type is `SessionID` and it represents an rdfvalue "
            "object that represents a session_id."
        ),
        "allOf": [
            {
                "$ref": "#/components/schemas/SessionID",
            },
        ],
    }
    self.assertEqual(
        expected_field_sessionid,
        self._GetParamSchema(
            "/metadata_test/method10", "get", "fieldSessionid"
        ),
    )
    self.assertEqual(
        expected_field_sessionid,
        self._GetParamSchema(
            "/metadata_test/method10", "post", "fieldSessionid"
        ),
    )

    # Check that descriptions get concatenated in the case we have a
    # `protobuf.oneof` field that has an RDF type `sem_type.type`.
    expected_oneof_datetime = {
        "description": (
            'This field is part of the "semtype_oneof" oneof. Only '
            "one field per oneof should be present. RDF type is "
            "`RDFDatetime` and it represents the number of "
            "microseconds since epoch to a timestamp."
        ),
        "allOf": [
            {
                "$ref": "#/components/schemas/RDFDatetime",
            },
        ],
    }
    self.assertEqual(
        expected_oneof_datetime,
        self._GetParamSchema("/metadata_test/method10", "get", "oneofDatetime"),
    )
    self.assertEqual(
        expected_oneof_datetime,
        self._GetParamSchema(
            "/metadata_test/method10", "post", "oneofDatetime"
        ),
    )

    # Now check that the RDF types have their schemas correctly described.
    component_schemas = self.openapi_desc_dict["components"]["schemas"]

    self.assertEqual(
        {
            "type": "string",
            "format": "uint64",
            "description": (
                "the number of microseconds since epoch to a timestamp"
            ),
        },
        component_schemas["RDFDatetime"],
    )
    self.assertEqual(
        {
            "type": "string",
            "format": "uint64",
            "description": "the number of seconds since epoch to a timestamp",
        },
        component_schemas["RDFDatetimeSeconds"],
    )
    self.assertEqual(
        {
            "type": "string",
            "format": "uint64",
            "description": "the number of microseconds between two timestamps",
        },
        component_schemas["Duration"],
    )
    self.assertEqual(
        {
            "type": "string",
            "format": "uint64",
            "description": "the number of seconds between two timestamps",
        },
        component_schemas["DurationSeconds"],
    )
    self.assertEqual(
        {
            "type": "string",
            "format": "byte",
            "description": "a buffer of bytes",
        },
        component_schemas["RDFBytes"],
    )
    self.assertEqual(
        {
            "type": "string",
            "format": "byte",
            "description": (
                "a binary hash digest with hex string representation"
            ),
        },
        component_schemas["HashDigest"],
    )
    self.assertEqual(
        {
            "type": "string",
            "description": "a glob expression for a client path",
        },
        component_schemas["GlobExpression"],
    )
    self.assertEqual(
        {
            "type": "string",
            "format": "uint64",
            "description": "a size for bytes allowing standard unit prefixes",
        },
        component_schemas["ByteSize"],
    )
    self.assertEqual(
        {
            "type": "string",
            "description": "an object to abstract URL manipulation",
        },
        component_schemas["RDFURN"],
    )
    self.assertEqual(
        {
            "type": "string",
            "description": "an rdfvalue object that represents a session_id",
        },
        component_schemas["SessionID"],
    )

  def testFlowsAreCorrectlyDescribedInOpenApiDescription(self):
    # Flow args, result, store and progress should be described.
    component_schemas = self.openapi_desc_dict["components"]["schemas"]

    self.assertIn(
        tests_pb2.BadArgsFlow1Args.DESCRIPTOR.full_name, component_schemas
    )
    self.assertEqual(
        {
            "type": "object",
            "properties": {
                "arg1": {
                    "$ref": (
                        f"#/components/schemas/{jobs_pb2.PathSpec.DESCRIPTOR.full_name}"
                    ),
                },
            },
        },
        component_schemas[tests_pb2.BadArgsFlow1Args.DESCRIPTOR.full_name],
    )

    self.assertIn(
        tests_pb2.SendingFlowArgs.DESCRIPTOR.full_name, component_schemas
    )
    self.assertEqual(
        {
            "type": "object",
            "properties": {
                "messageCount": {
                    "$ref": "#/components/schemas/protobuf2.TYPE_UINT64",
                },
            },
        },
        component_schemas[tests_pb2.SendingFlowArgs.DESCRIPTOR.full_name],
    )

    self.assertIn(
        tests_pb2.DummyFlowStore.DESCRIPTOR.full_name, component_schemas
    )
    self.assertEqual(
        {
            "type": "object",
            "properties": {
                "msg": {
                    "$ref": "#/components/schemas/protobuf2.TYPE_STRING",
                },
            },
        },
        component_schemas[tests_pb2.DummyFlowStore.DESCRIPTOR.full_name],
    )

    self.assertIn(
        tests_pb2.DummyFlowProgress.DESCRIPTOR.full_name, component_schemas
    )
    self.assertEqual(
        {
            "type": "object",
            "properties": {
                "status": {
                    "$ref": "#/components/schemas/protobuf2.TYPE_STRING",
                },
            },
        },
        component_schemas[tests_pb2.DummyFlowProgress.DESCRIPTOR.full_name],
    )


def main(argv):
  test_lib.main(argv)


if __name__ == "__main__":
  app.run(main)
