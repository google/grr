# Lint as: python3
"""This module contains tests for metadata API handlers."""
from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

import json
import pkg_resources

from absl import app

from grr_response_core.lib.rdfvalues import structs as rdf_structs

from grr_response_server.gui import api_call_router
from grr_response_server.gui import api_test_lib

from grr_response_server.gui.api_plugins import metadata as metadata_plugin

from grr.test_lib import skip
from grr.test_lib import test_lib

from grr_response_proto import tests_pb2


class MetadataSimpleMessage(rdf_structs.RDFProtoStruct):
  protobuf = tests_pb2.MetadataSimpleMessage


class MetadataPrimitiveTypesMessage(rdf_structs.RDFProtoStruct):
  protobuf = tests_pb2.MetadataPrimitiveTypesMessage


class MetadataRepeatedFieldMessage(rdf_structs.RDFProtoStruct):
  protobuf = tests_pb2.MetadataRepeatedFieldMessage


class MetadataEnumFieldMessage(rdf_structs.RDFProtoStruct):
  protobuf = tests_pb2.MetadataEnumFieldMessage


class MetadataTypesHierarchyRoot(rdf_structs.RDFProtoStruct):
  protobuf = tests_pb2.MetadataTypesHierarchyRoot
  rdf_deps = [
    "MetadataTypesHierarchyCyclic",
    "MetadataTypesHierarchyLeaf",
  ]


class MetadataTypesHierarchyCyclic(rdf_structs.RDFProtoStruct):
  protobuf = tests_pb2.MetadataTypesHierarchyCyclic
  rdf_deps = [
    MetadataTypesHierarchyRoot,
    "MetadataTypesHierarchyLeaf",
  ]


class MetadataTypesHierarchyLeaf(rdf_structs.RDFProtoStruct):
  protobuf = tests_pb2.MetadataTypesHierarchyLeaf


class MetadataOneofMessage(rdf_structs.RDFProtoStruct):
  protobuf = tests_pb2.MetadataOneofMessage
  rdf_deps = [
    MetadataSimpleMessage,
  ]


class MetadataDummyApiCallRouter(api_call_router.ApiCallRouter):
  """Dummy `ApiCallRouter` implementation used for Metadata testing."""

  @api_call_router.ArgsType(MetadataSimpleMessage)
  @api_call_router.Http("GET", "/metadata_test/method1/<metadata_id>")
  @api_call_router.Http("HEAD", "/metadata_test/method1/<metadata_id>")
  @api_call_router.Http("POST", "/metadata_test/method1/<metadata_id>")
  def Method1WithArgsType(self, args, token=None):
    """Method 1 description."""

  @api_call_router.ResultType(MetadataSimpleMessage)
  @api_call_router.Http("GET", "/metadata_test/method2")
  @api_call_router.Http("HEAD", "/metadata_test/method2")
  @api_call_router.Http("POST", "/metadata_test/method2")
  def Method2WithResultType(self, args, token=None):
    """Method 2 description."""

  @api_call_router.ArgsType(MetadataPrimitiveTypesMessage)
  @api_call_router.ResultBinaryStream()
  @api_call_router.Http("GET", "/metadata_test/method3")
  def Method3PrimitiveTypes(self, args, token=None):
    """Method 3 description."""

  @api_call_router.ArgsType(MetadataRepeatedFieldMessage)
  @api_call_router.Http("GET", "/metadata_test/method4")
  @api_call_router.Http("POST", "/metadata_test/method4")
  def Method4RepeatedField(self, args, token=None):
    """Method 4 description."""

  @api_call_router.ArgsType(MetadataEnumFieldMessage)
  @api_call_router.Http("GET", "/metadata_test/method5")
  @api_call_router.Http("POST", "/metadata_test/method5")
  def Method5EnumField(self, args, token=None):
    """Method 5 description."""

  @api_call_router.ArgsType(MetadataTypesHierarchyRoot)
  @api_call_router.ResultType(MetadataTypesHierarchyLeaf)
  @api_call_router.Http("GET", "/metadata_test/method6")
  def Method6TypeReferences(self, args, token=None):
    """Method 6 description."""

  @api_call_router.ArgsType(MetadataOneofMessage)
  @api_call_router.ResultType(MetadataOneofMessage)
  @api_call_router.Http("GET", "/metadata_test/method7")
  def Method7ProtobufOneof(self, args, token=None):
    """Method 7 description."""


class ApiGetOpenApiDescriptionHandlerTest(api_test_lib.ApiCallHandlerTest):
  """Test for `ApiGetOpenApiDescriptionHandler`."""
  def setUp(self):
    super(ApiGetOpenApiDescriptionHandlerTest, self).setUp()
    self.router = MetadataDummyApiCallRouter()
    self.router_methods = self.router.__class__.GetAnnotatedMethods()

    self.handler = metadata_plugin.ApiGetOpenApiDescriptionHandler(self.router)

    result = self.handler.Handle(None, token=self.token)
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
    }
    extracted_methods = {method.name for method in self.router_methods.values()}

    self.assertEqual(expected_methods, extracted_methods)

  @skip.If(
    "openapi-spec-validator" not in {p.key for p in pkg_resources.working_set},
    "The openapi-spec-validator module used for validating the OpenAPI "
    "specification is not installed."
  )
  def testGeneratedOpenApiDescriptionIsValid(self):
    # TODO(alexandrucosminmihai): Move this import to the top when the GitHub
    # issue #813 (https://github.com/google/grr/issues/813) is resolved.
    import openapi_spec_validator
    # Will raise exceptions when the OpenAPI specification is invalid.
    openapi_spec_validator.validate_spec(self.openapi_desc_dict)

  def testAllRoutesAreInOpenApiDescription(self):
    openapi_paths_dict = self.openapi_desc_dict["paths"]

    # Check that there are no extra/missing paths.
    self.assertCountEqual(
      {
        "/metadata_test/method1/{metadata_id}",
        "/metadata_test/method2",
        "/metadata_test/method3",
        "/metadata_test/method4",
        "/metadata_test/method5",
        "/metadata_test/method6",
        "/metadata_test/method7",
      },
      openapi_paths_dict.keys()
    )

    # Check that there are no extra/missing HTTP methods for each path (routes).
    self.assertCountEqual(
      {"get", "head", "post", },
      openapi_paths_dict["/metadata_test/method1/{metadata_id}"].keys()
    )
    self.assertCountEqual(
      {"get", "head", "post", },
      openapi_paths_dict["/metadata_test/method2"].keys()
    )
    self.assertCountEqual(
      {"get", },
      openapi_paths_dict["/metadata_test/method3"].keys()
    )
    self.assertCountEqual(
      {"get", "post", },
      openapi_paths_dict["/metadata_test/method4"].keys()
    )
    self.assertCountEqual(
      {"get", "post", },
      openapi_paths_dict["/metadata_test/method5"].keys()
    )
    self.assertCountEqual(
      {"get", },
      openapi_paths_dict["/metadata_test/method6"].keys()
    )
    self.assertCountEqual(
      {"get", },
      openapi_paths_dict["/metadata_test/method7"].keys()
    )

  def testRouteArgsAreCorrectlySeparated(self):
    # Check that for each route the parameters are separated correctly in path,
    # query and request body parameters.

    openapi_paths_dict = self.openapi_desc_dict["paths"]

    # Check the OpenAPI parameters of `Method1WithArgsType` routes.
    method1_path_dict = (
      openapi_paths_dict["/metadata_test/method1/{metadata_id}"]
    )

    # Parameters of `GET /metadata_test/method1/{metadata_id}`.
    get_method1_dict = method1_path_dict["get"]

    get_method1_params_path = [
      param["name"]
      for param in get_method1_dict["parameters"] if param["in"] == "path"
    ]
    self.assertCountEqual(["metadata_id", ], get_method1_params_path)

    get_method1_params_query = [
      param["name"]
      for param in get_method1_dict["parameters"] if param["in"] == "query"
    ]
    self.assertCountEqual(
      ["metadata_arg1", "metadata_arg2", ],
      get_method1_params_query
    )

    # `parameters` field is always present, even if it is an empty array,
    # `requestBody` should not be, unless there are arguments in the body.
    self.assertIsNone(get_method1_dict.get("requestBody"))

    # Parameters of `HEAD /metadata_test/method1/{metadata_id}`.
    head_method1_dict = method1_path_dict["head"]

    head_method1_params_path = [
      param["name"]
      for param in head_method1_dict["parameters"] if param["in"] == "path"
    ]
    self.assertCountEqual(["metadata_id", ], head_method1_params_path)

    head_method1_params_query = [
      param["name"]
      for param in get_method1_dict["parameters"] if param["in"] == "query"
    ]
    self.assertCountEqual(
    ["metadata_arg1", "metadata_arg2", ],
      head_method1_params_query
    )

    self.assertIsNone(head_method1_dict.get("requestBody"))

    # Parameters of `POST /metadata_test/method1/{metadata_id}`.
    post_method1_dict = method1_path_dict["post"]

    post_method1_params_path = [
      param["name"]
      for param in post_method1_dict["parameters"] if param["in"] == "path"
    ]
    self.assertCountEqual(["metadata_id"], post_method1_params_path)

    post_method1_params_query = [
      param["name"]
      for param in post_method1_dict["parameters"] if param["in"] == "query"
    ]
    self.assertEmpty(post_method1_params_query)

    post_method1_params_body = [
      param # requestBody parameters use their names as keys.
      for param in post_method1_dict.get("requestBody").get("content")
        .get("application/json").get("schema").get("properties")
    ]
    self.assertCountEqual(
      ["metadata_arg1", "metadata_arg2", ],
      post_method1_params_body
    )

    # Check the OpenAPI parameters of `Method4RepeatedField` routes.
    method4_path_dict = openapi_paths_dict["/metadata_test/method4"]

    # Parameters of `GET /metadata_test/method4`.
    get_method4_dict = method4_path_dict["get"]

    get_method4_params_path = [
      param["name"]
      for param in get_method4_dict["parameters"] if param["in"] == "path"
    ]
    self.assertEmpty(get_method4_params_path)

    get_method4_params_query = [
      param["name"]
      for param in get_method4_dict["parameters"] if param["in"] == "query"
    ]
    self.assertCountEqual(["field_repeated", ], get_method4_params_query)

    self.assertIsNone(get_method4_dict.get("requestBody"))

    # Parameters of POST /metadata_test/method4.
    post_method4_dict = method4_path_dict["post"]

    post_method4_params_path = [
      param["name"]
      for param in post_method4_dict["parameters"] if param["in"] == "path"
    ]
    self.assertEmpty(post_method4_params_path)

    post_method4_params_query = [
      param["name"]
      for param in post_method4_dict["parameters"] if param["in"] == "query"
    ]
    self.assertEmpty(post_method4_params_query)

    post_method4_params_body = [
      param
      for param in post_method4_dict.get("requestBody").get("content")
        .get("application/json").get("schema").get("properties")
    ]
    self.assertCountEqual(["field_repeated", ], post_method4_params_body)

    # Check the OpenAPI parameters of `Method5EnumField` routes.
    method5_path_dict = openapi_paths_dict["/metadata_test/method5"]

    # Parameters of `GET /metadata_test/method5`.
    get_method5_dict = method5_path_dict["get"]

    get_method5_params_path = [
      param["name"]
      for param in get_method5_dict["parameters"] if param["in"] == "path"
    ]
    self.assertEmpty(get_method5_params_path)

    get_method5_params_query = [
      param["name"]
      for param in get_method5_dict["parameters"] if param["in"] == "query"
    ]
    self.assertCountEqual(["field_enum"], get_method5_params_query)

    self.assertIsNone(get_method5_dict.get("requestBody"))

    # Parameters of `POST /metadata_test/method5`.
    post_method5_dict = method5_path_dict["post"]

    post_method5_params_path = [
      param["name"]
      for param in post_method5_dict["parameters"] if param["in"] == "path"
    ]
    self.assertEmpty(post_method5_params_path)

    post_method5_params_query = [
      param["name"]
      for param in post_method5_dict["parameters"] if param["in"] == "query"
    ]
    self.assertEmpty(post_method5_params_query)

    post_method5_params_body = [
      param
      for param in post_method5_dict.get("requestBody").get("content")
        .get("application/json").get("schema").get("properties")
    ]
    self.assertCountEqual(["field_enum", ], post_method5_params_body)

    # Check the OpenAPI parameters of `Method6TypeReferences` routes.
    method6_path_dict = openapi_paths_dict["/metadata_test/method6"]

    # Parameters of `GET /metadata_test/method6`.
    get_method6_dict = method6_path_dict["get"]

    get_method6_params_path = [
      param["name"]
      for param in get_method6_dict["parameters"] if param["in"] == "path"
    ]
    self.assertEmpty(get_method6_params_path)

    get_method6_params_query = [
      param["name"]
      for param in get_method6_dict["parameters"] if param["in"] == "query"
    ]
    self.assertCountEqual(
      ["field_int64", "child_1", "child_2", ],
      get_method6_params_query
    )

    self.assertIsNone(get_method6_dict.get("requestBody"))

    # Check the OpenAPI parameters of `Method7ProtobufOneof` routes.
    method7_path_dict = openapi_paths_dict["/metadata_test/method7"]

    # Parameters of `GET /metadata_test/method7`.
    get_method7_dict = method7_path_dict["get"]

    get_method7_params_path = [
      param["name"]
      for param in get_method7_dict["parameters"] if param["in"] == "path"
    ]
    self.assertEmpty(get_method7_params_path)

    get_method7_params_query = [
      param["name"]
      for param in get_method7_dict["parameters"] if param["in"] == "query"
    ]
    self.assertCountEqual(
      ["oneof_int64", "oneof_simplemsg", "field_int64", ],
      get_method7_params_query
    )

    self.assertIsNone(get_method7_dict.get("requestBody"))

  def testRoutesResultsAreCorrectlyDescribedInOpenApiDescription(self):
    # Verify the OpenAPI schemas of the response objects.
    # Response types are usually protobuf messages. The expectation in these
    # cases is that the routes descriptions include a reference to the type
    # schemas in the `components` field of the root `OpenAPI Object`.
    openapi_paths_dict = self.openapi_desc_dict["paths"]

    # `Method2WithResultType (GET, HEAD, POST)` => `MetadataSimpleMessage`
    method2_path_dict = openapi_paths_dict["/metadata_test/method2"]
    # Check responses for `GET /metadata_test/method2`.
    self.assertEqual(
      {
        "200": {
          "description": "The call to the Method2WithResultType API method "
                         "succeeded and it returned an instance of "
                         "grr.MetadataSimpleMessage.",
          "content": {
            "application/json": {
              "schema": {
                "$ref": "#/components/schemas/grr.MetadataSimpleMessage",
              },
            },
          },
        },
        "default": {
          "description": "The call to the Method2WithResultType API method did "
                         "not succeed.",
        },
      },
      method2_path_dict["get"]["responses"]
    )
    # Check responses for HEAD /metadata_test/method2.
    self.assertEqual(
      {
        "200": {
          "description": "The call to the Method2WithResultType API method "
                         "succeeded and it returned an instance of "
                         "grr.MetadataSimpleMessage.",
          "content": {
            "application/json": {
              "schema": {
                "$ref": "#/components/schemas/grr.MetadataSimpleMessage",
              },
            },
          },
        },
        "default": {
          "description": "The call to the Method2WithResultType API method did "
                         "not succeed.",
        },
      },
      method2_path_dict["head"]["responses"]
    )
    # Check responses for `POST /metadata_test/method2`.
    self.assertEqual(
      {
        "200": {
          "description": "The call to the Method2WithResultType API method "
                         "succeeded and it returned an instance of "
                         "grr.MetadataSimpleMessage.",
          "content": {
            "application/json": {
              "schema": {
                "$ref": "#/components/schemas/grr.MetadataSimpleMessage",
              },
            },
          },
        },
        "default": {
          "description": "The call to the Method2WithResultType API method did "
                         "not succeed.",
        },
      },
      method2_path_dict["post"]["responses"]
    )

    # Method3PrimitiveTypes (GET) => BinaryStream result type.
    method3_path_dict = openapi_paths_dict["/metadata_test/method3"]
    # Check responses for GET /metadata_test/method3.
    self.assertEqual(
      {
        "200": {
          "description": "The call to the Method3PrimitiveTypes API method "
                         "succeeded and it returned an instance of "
                         "BinaryStream.",
          "content": {
            "application/octet-stream": {
              "schema": {
                "$ref": "#/components/schemas/BinaryStream",
              },
            },
          },
        },
        "default": {
          "description": "The call to the Method3PrimitiveTypes API method did "
                         "not succeed.",
        },
      },
      method3_path_dict["get"]["responses"]
    )

    # `Method4RepeatedField (GET, POST)` => No result type.
    method4_path_dict = openapi_paths_dict["/metadata_test/method4"]
    # Check responses for `GET /metadata_test/method4`.
    self.assertEqual(
      {
        "200": {
          "description": "The call to the Method4RepeatedField API method "
                         "succeeded.",
        },
        "default": {
          "description": "The call to the Method4RepeatedField API method did "
                         "not succeed.",
        },
      },
      method4_path_dict["get"]["responses"]
    )
    # Check responses for `POST /metadata_test/method4`.
    self.assertEqual(
      {
        "200": {
          "description": "The call to the Method4RepeatedField API method "
                         "succeeded.",
        },
        "default": {
          "description": "The call to the Method4RepeatedField API method did "
                         "not succeed.",
        },
      },
      method4_path_dict["post"]["responses"]
    )

  def testPrimitiveTypesAreCorrectlyDescribedAndUsedInOpenApiDescription(self):
    # Primitive types schemas are described in the `components` field of the
    # root `OpenAPI Object`.

    # Firstly, verify that the descriptions of the fields of the
    # `MetadataPrimitiveTypesMessage` (which is the `ArgsType` of
    # `Method3PrimitiveTypes`) include references to the primitive types
    # descriptions.
    self.assertEqual(
      {"$ref": "#/components/schemas/protobuf2.TYPE_DOUBLE", },
      self._GetParamSchema("/metadata_test/method3", "get", "field_double")
    )
    self.assertEqual(
      {"$ref": "#/components/schemas/protobuf2.TYPE_FLOAT", },
      self._GetParamSchema("/metadata_test/method3", "get", "field_float")
    )
    self.assertEqual(
      {"$ref": "#/components/schemas/protobuf2.TYPE_INT64", },
      self._GetParamSchema("/metadata_test/method3", "get", "field_int64")
    )
    self.assertEqual(
      {"$ref": "#/components/schemas/protobuf2.TYPE_UINT64", },
      self._GetParamSchema("/metadata_test/method3", "get", "field_uint64")
    )
    self.assertEqual(
      {"$ref": "#/components/schemas/protobuf2.TYPE_INT32", },
      self._GetParamSchema("/metadata_test/method3", "get", "field_int32")
    )
    self.assertEqual(
      {"$ref": "#/components/schemas/protobuf2.TYPE_FIXED64", },
      self._GetParamSchema("/metadata_test/method3", "get", "field_fixed64")
    )
    self.assertEqual(
      {"$ref": "#/components/schemas/protobuf2.TYPE_FIXED32", },
      self._GetParamSchema("/metadata_test/method3", "get", "field_fixed32")
    )
    self.assertEqual(
      {"$ref": "#/components/schemas/protobuf2.TYPE_BOOL", },
      self._GetParamSchema("/metadata_test/method3", "get", "field_bool")
    )
    self.assertEqual(
      {"$ref": "#/components/schemas/protobuf2.TYPE_STRING", },
      self._GetParamSchema("/metadata_test/method3", "get", "field_string")
    )
    self.assertEqual(
      {"$ref": "#/components/schemas/protobuf2.TYPE_BYTES", },
      self._GetParamSchema("/metadata_test/method3", "get", "field_bytes")
    )
    self.assertEqual(
      {"$ref": "#/components/schemas/protobuf2.TYPE_UINT32", },
      self._GetParamSchema("/metadata_test/method3", "get", "field_uint32")
    )
    self.assertEqual(
      {"$ref": "#/components/schemas/protobuf2.TYPE_SFIXED32", },
      self._GetParamSchema("/metadata_test/method3", "get", "field_sfixed32")
    )
    self.assertEqual(
      {"$ref": "#/components/schemas/protobuf2.TYPE_SFIXED64", },
      self._GetParamSchema("/metadata_test/method3", "get", "field_sfixed64")
    )
    self.assertEqual(
      {"$ref": "#/components/schemas/protobuf2.TYPE_SINT32", },
      self._GetParamSchema("/metadata_test/method3", "get", "field_sint32")
    )
    self.assertEqual(
      {"$ref": "#/components/schemas/protobuf2.TYPE_SINT64", },
      self._GetParamSchema("/metadata_test/method3", "get", "field_sint64")
    )

    # Extract `BinaryStream` type reference from the response schema.
    self.assertEqual(
      {"$ref": "#/components/schemas/BinaryStream", },
      self.openapi_desc_dict
        .get("paths")
        .get("/metadata_test/method3")
        .get("get")
        .get("responses")
        .get("200")
        .get("content")
        .get("application/octet-stream")
        .get("schema")
    )

    # Secondly, verify the descriptions of primitive types from the `components`
    # field of the root `OpenAPI Object`.
    components_schemas = self.openapi_desc_dict["components"]["schemas"]

    self.assertEqual(
      {"type": "number", "format": "double", },
      components_schemas["protobuf2.TYPE_DOUBLE"]
    )
    self.assertEqual(
      {"type": "number", "format": "float", },
      components_schemas["protobuf2.TYPE_FLOAT"]
    )
    self.assertEqual(
      {"type": "string", "format": "int64", },
      components_schemas["protobuf2.TYPE_INT64"]
    )
    self.assertEqual(
      {"type": "string", "format": "uint64", },
      components_schemas["protobuf2.TYPE_UINT64"]
    )
    self.assertEqual(
      {"type": "integer", "format": "int32", },
      components_schemas["protobuf2.TYPE_INT32"]
    )
    self.assertEqual(
      {"type": "string", "format": "fixed64", },
      components_schemas["protobuf2.TYPE_FIXED64"]
    )
    self.assertEqual(
      {"type": "number", "format": "fixed32", },
      components_schemas["protobuf2.TYPE_FIXED32"]
    )
    self.assertEqual(
      {"type": "boolean", },
      components_schemas["protobuf2.TYPE_BOOL"]
    )
    self.assertEqual(
      {"type": "string", },
      components_schemas["protobuf2.TYPE_STRING"]
    )
    self.assertEqual(
      {"type": "string", "format": "byte", },
      components_schemas["protobuf2.TYPE_BYTES"]
    )
    self.assertEqual(
      {"type": "number", "format": "uint32", },
      components_schemas["protobuf2.TYPE_UINT32"]
    )
    self.assertEqual(
      {"type": "number", "format": "sfixed32", },
      components_schemas["protobuf2.TYPE_SFIXED32"]
    )
    self.assertEqual(
      {"type": "string", "format": "sfixed64", },
      components_schemas["protobuf2.TYPE_SFIXED64"]
    )
    self.assertEqual(
      {"type": "integer", "format": "int32", },
      components_schemas["protobuf2.TYPE_INT32"]
    )
    self.assertEqual(
      {"type": "string", "format": "sint64", },
      components_schemas["protobuf2.TYPE_SINT64"]
    )
    self.assertEqual(
      {"type": "string", "format": "binary", },
      components_schemas["BinaryStream"]
    )

  def testRepeatedFieldIsDescribedCorrectlyInOpenApiDescription(self):
    # Extract the `repeated` field from the description of the `GET` route
    # associated with `Method4RepeatedField`.
    # The `repeated` field should be the only parameter and be a query
    # parameter. This aspect is tested by `testRouteArgsAreCorrectlySeparated`.
    get_method4_repeated_field_schema = (
      self.openapi_desc_dict
        .get("paths")
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
      get_method4_repeated_field_schema
    )

    # Extract the `repeated` field from the description of the `POST` route
    # associated with `Method4RepeatedField`.
    # The repeated field should be the only parameter and be a request body
    # parameter. This aspect is tested by `testRouteArgsAreCorrectlySeparated`.
    post_method4_repeated_field_schema = (
      self.openapi_desc_dict
        .get("paths")
        .get("/metadata_test/method4")
        .get("post")
        .get("requestBody")
        .get("content")
        .get("application/json")
        .get("schema")
        .get("properties")
        .get("field_repeated")
    )
    self.assertEqual(
      {
        "type": "array",
        "items": {
          "$ref": "#/components/schemas/protobuf2.TYPE_INT64",
        },
      },
      post_method4_repeated_field_schema
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
      self.openapi_desc_dict
        .get("paths")
        .get("/metadata_test/method5")
        .get("get")
        .get("parameters")[0]
        .get("schema")
    )
    self.assertEqual(
      {
        "$ref":
          "#/components/schemas/grr.MetadataEnumFieldMessage.metadata_enum",
      },
      get_method5_enum_field_schema
    )

    # Extract the enum field schema from the description of the POST route
    # associated with `Method5EnumField`.
    post_method5_enum_field_schema = (
      self.openapi_desc_dict
        .get("paths")
        .get("/metadata_test/method5")
        .get("post")
        .get("requestBody")
        .get("content")
        .get("application/json")
        .get("schema")
        .get("properties")
        .get("field_enum")
    )
    self.assertEqual(
      {
        "$ref":
          "#/components/schemas/grr.MetadataEnumFieldMessage.metadata_enum",
      },
      post_method5_enum_field_schema
    )

    # Test the OpenAPI schema description of the *enum field's type*.
    openapi_enum_type_schema = (
      self.openapi_desc_dict
        .get("components")
        .get("schemas")
        .get("grr.MetadataEnumFieldMessage.metadata_enum")
    )

    self.assertEqual(
      {
        "type": "string",
        "enum": ["A", "B", "C", ],
        "description": "A == 1\nB == 2\nC == 3",
      },
      openapi_enum_type_schema
    )

  def testTypeReferencesAreUsedInOpenApiDescriptionsOfCompositeTypes(self):
    # Tests that references are used for composite types and that the referenced
    # types are declared, including the case of cyclic dependencies.

    # Test that composite types are defined.
    openapi_components_schemas = (
      self.openapi_desc_dict
        .get("components")
        .get("schemas")
    )
    root = openapi_components_schemas["grr.MetadataTypesHierarchyRoot"]
    cyclic = openapi_components_schemas["grr.MetadataTypesHierarchyCyclic"]
    leaf = openapi_components_schemas["grr.MetadataTypesHierarchyLeaf"]

    # Test the references between message types.
    root_ref = "#/components/schemas/grr.MetadataTypesHierarchyRoot"
    cyclic_ref = "#/components/schemas/grr.MetadataTypesHierarchyCyclic"
    leaf_ref = "#/components/schemas/grr.MetadataTypesHierarchyLeaf"

    self.assertEqual(root["properties"]["child_1"]["$ref"], cyclic_ref)
    self.assertEqual(root["properties"]["child_2"]["$ref"], leaf_ref)

    self.assertEqual(cyclic["properties"]["root"]["$ref"], root_ref)  # Cycle.
    self.assertEqual(cyclic["properties"]["child_1"]["$ref"], leaf_ref)

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
        "description": "This field is part of the \"metadata_oneof\" oneof. "
                       "Only one field per oneof should be present.",
        "allOf": [
          {
            "$ref": "#/components/schemas/protobuf2.TYPE_INT64",
          },
        ],
      },
      self._GetParamSchema("/metadata_test/method7", "get", "oneof_int64")
    )
    # Check the `oneof_simplemsg` inner field of the `metadata_oneof`.
    self.assertEqual(
      {
        "description": "This field is part of the \"metadata_oneof\" oneof. "
                       "Only one field per oneof should be present.",
        "allOf": [
          {
            "$ref": "#/components/schemas/grr.MetadataSimpleMessage",
          },
        ],
      },
      self._GetParamSchema("/metadata_test/method7", "get", "oneof_simplemsg")
    )

  def _GetParamSchema(self, method_path, http_method, param_name):
    params = (
      self.openapi_desc_dict
        .get("paths")
        .get(method_path)
        .get(http_method)
        .get("parameters")
    )

    for param in params:
      if param["name"] == param_name:
        return param["schema"]


def main(argv):
  test_lib.main(argv)


if __name__ == "__main__":
  app.run(main)
