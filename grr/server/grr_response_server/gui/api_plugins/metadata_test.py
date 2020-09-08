# Lint as: python3
"""This module contains tests for metadata API handlers."""
from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

import json
import pkg_resources

from absl import app

from grr_response_core.lib import rdfvalue
from grr_response_core.lib.rdfvalues import structs as rdf_structs
from grr_response_core.lib.rdfvalues import paths as rdf_paths

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


class MetadataMapMessage(rdf_structs.RDFProtoStruct):
  protobuf = tests_pb2.MetadataMapMessage
  rdf_deps = [
    "FieldMapEntry",
  ]


class MetadataSemTypeMessage(rdf_structs.RDFProtoStruct):
  protobuf = tests_pb2.MetadataSemTypeMessage
  rdf_deps = [
    rdfvalue.RDFDatetime,
    rdfvalue.RDFDatetimeSeconds,
    rdfvalue.Duration,
    rdfvalue.DurationSeconds,
    rdfvalue.RDFBytes,
    rdfvalue.HashDigest,
    rdf_paths.GlobExpression,
    rdfvalue.ByteSize,
    rdfvalue.RDFURN,
    rdfvalue.SessionID,
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
  @api_call_router.Http("POST", "/metadata_test/method7")
  def Method7ProtobufOneof(self, args, token=None):
    """Method 7 description."""

  @api_call_router.ArgsType(MetadataMapMessage)
  @api_call_router.ResultType(MetadataMapMessage)
  @api_call_router.Http("GET", "/metadata_test/method8")
  @api_call_router.Http("POST", "/metadata_test/method8")
  def Method8ProtobufMap(self, args, token=None):
    """Method 8 description."""

  @api_call_router.ArgsType(MetadataSimpleMessage)
  @api_call_router.ResultType(MetadataSimpleMessage)
  @api_call_router.Http("GET", "/metadata_test/method9")
  @api_call_router.Http("GET", "/metadata_test/method9/<metadata_id>")
  @api_call_router.Http(
    "POST", "/metadata_test/method9/<metadata_id>/<metadata_arg1>"
  )
  @api_call_router.Http(
    "GET",
    "/metadata_test/method9/<metadata_id>/<metadata_arg1>/<metadata_arg2>"
  )
  @api_call_router.Http("GET", "/metadata_test/method9/<metadata_id>/fixed1")
  @api_call_router.Http(
    "GET", "/metadata_test/method9/<metadata_id>/fixed1/<metadata_arg1>"
  )
  def Method9OptionalPathArgs(self, args, token=None):
    """Method 9 description"""


  @api_call_router.ArgsType(MetadataSemTypeMessage)
  @api_call_router.ResultType(MetadataSemTypeMessage)
  @api_call_router.Http("GET", "/metadata_test/method10")
  @api_call_router.Http("POST", "/metadata_test/method10")
  def Method10SemTypeProtobufOption(self, args, token=None):
    """Method 10 description"""


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
      "Method8ProtobufMap",
      "Method9OptionalPathArgs",
      "Method10SemTypeProtobufOption",
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
        "/metadata_test/method8",
        "/metadata_test/method9/{metadata_id}",
        "/metadata_test/method9/{metadata_id}/{metadata_arg1}",
        "/metadata_test/method9/{metadata_id}/{metadata_arg1}/{metadata_arg2}",
        "/metadata_test/method9/{metadata_id}/fixed1/{metadata_arg1}",
        "/metadata_test/method10",
      },
      openapi_paths_dict.keys()
    )

    # Check that there are no extra/missing HTTP methods for each path (routes).
    self.assertCountEqual(
      {"get", "head", "post"},
      openapi_paths_dict["/metadata_test/method1/{metadata_id}"].keys()
    )
    self.assertCountEqual(
      {"get", "head", "post"},
      openapi_paths_dict["/metadata_test/method2"].keys()
    )
    self.assertCountEqual(
      {"get"},
      openapi_paths_dict["/metadata_test/method3"].keys()
    )
    self.assertCountEqual(
      {"get", "post"},
      openapi_paths_dict["/metadata_test/method4"].keys()
    )
    self.assertCountEqual(
      {"get", "post"},
      openapi_paths_dict["/metadata_test/method5"].keys()
    )
    self.assertCountEqual(
      {"get"},
      openapi_paths_dict["/metadata_test/method6"].keys()
    )
    self.assertCountEqual(
      {"get", "post"},
      openapi_paths_dict["/metadata_test/method7"].keys()
    )
    self.assertCountEqual(
      {"get", "post"},
      openapi_paths_dict["/metadata_test/method8"].keys()
    )
    self.assertCountEqual(
      {"get"},
      openapi_paths_dict["/metadata_test/method9/{metadata_id}"].keys()
    )
    self.assertCountEqual(
      {"post"},
      openapi_paths_dict
        .get("/metadata_test/method9/{metadata_id}/{metadata_arg1}").keys()
    )
    self.assertCountEqual(
      {"get"},
      openapi_paths_dict.get(
        "/metadata_test/method9/{metadata_id}/{metadata_arg1}/{metadata_arg2}"
      ).keys()
    )
    self.assertCountEqual(
      {"get"},
      openapi_paths_dict.get(
        "/metadata_test/method9/{metadata_id}/fixed1/{metadata_arg1}"
      ).keys()
    )

  def testRouteArgsAreCorrectlySeparated(self):
    # Check that the parameters are separated correctly in path, query and
    # request body parameters.

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
    self.assertCountEqual(["metadata_id"], get_method1_params_path)

    get_method1_params_query = [
      param["name"]
      for param in get_method1_dict["parameters"] if param["in"] == "query"
    ]
    self.assertCountEqual(
      ["metadata_arg1", "metadata_arg2"],
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
    self.assertCountEqual(["metadata_id"], head_method1_params_path)

    head_method1_params_query = [
      param["name"]
      for param in get_method1_dict["parameters"] if param["in"] == "query"
    ]
    self.assertCountEqual(
      ["metadata_arg1", "metadata_arg2"],
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
      ["metadata_arg1", "metadata_arg2"],
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
    self.assertCountEqual(["field_repeated"], get_method4_params_query)

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
    self.assertCountEqual(["field_repeated"], post_method4_params_body)

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
    self.assertCountEqual(["field_enum"], post_method5_params_body)

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
      ["field_int64", "child_1", "child_2"],
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
      ["oneof_int64", "oneof_simplemsg", "field_int64"],
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
      {"$ref": "#/components/schemas/protobuf2.TYPE_DOUBLE"},
      self._GetParamSchema("/metadata_test/method3", "get", "field_double")
    )
    self.assertEqual(
      {"$ref": "#/components/schemas/protobuf2.TYPE_FLOAT"},
      self._GetParamSchema("/metadata_test/method3", "get", "field_float")
    )
    self.assertEqual(
      {"$ref": "#/components/schemas/protobuf2.TYPE_INT64"},
      self._GetParamSchema("/metadata_test/method3", "get", "field_int64")
    )
    self.assertEqual(
      {"$ref": "#/components/schemas/protobuf2.TYPE_UINT64"},
      self._GetParamSchema("/metadata_test/method3", "get", "field_uint64")
    )
    self.assertEqual(
      {"$ref": "#/components/schemas/protobuf2.TYPE_INT32"},
      self._GetParamSchema("/metadata_test/method3", "get", "field_int32")
    )
    self.assertEqual(
      {"$ref": "#/components/schemas/protobuf2.TYPE_FIXED64"},
      self._GetParamSchema("/metadata_test/method3", "get", "field_fixed64")
    )
    self.assertEqual(
      {"$ref": "#/components/schemas/protobuf2.TYPE_FIXED32"},
      self._GetParamSchema("/metadata_test/method3", "get", "field_fixed32")
    )
    self.assertEqual(
      {"$ref": "#/components/schemas/protobuf2.TYPE_BOOL"},
      self._GetParamSchema("/metadata_test/method3", "get", "field_bool")
    )
    self.assertEqual(
      {"$ref": "#/components/schemas/protobuf2.TYPE_STRING"},
      self._GetParamSchema("/metadata_test/method3", "get", "field_string")
    )
    self.assertEqual(
      {"$ref": "#/components/schemas/protobuf2.TYPE_BYTES"},
      self._GetParamSchema("/metadata_test/method3", "get", "field_bytes")
    )
    self.assertEqual(
      {"$ref": "#/components/schemas/protobuf2.TYPE_UINT32"},
      self._GetParamSchema("/metadata_test/method3", "get", "field_uint32")
    )
    self.assertEqual(
      {"$ref": "#/components/schemas/protobuf2.TYPE_SFIXED32"},
      self._GetParamSchema("/metadata_test/method3", "get", "field_sfixed32")
    )
    self.assertEqual(
      {"$ref": "#/components/schemas/protobuf2.TYPE_SFIXED64"},
      self._GetParamSchema("/metadata_test/method3", "get", "field_sfixed64")
    )
    self.assertEqual(
      {"$ref": "#/components/schemas/protobuf2.TYPE_SINT32"},
      self._GetParamSchema("/metadata_test/method3", "get", "field_sint32")
    )
    self.assertEqual(
      {"$ref": "#/components/schemas/protobuf2.TYPE_SINT64"},
      self._GetParamSchema("/metadata_test/method3", "get", "field_sint64")
    )

    # Extract `BinaryStream` type reference from the response schema.
    self.assertEqual(
      {"$ref": "#/components/schemas/BinaryStream"},
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
      {"type": "number", "format": "double"},
      components_schemas["protobuf2.TYPE_DOUBLE"]
    )
    self.assertEqual(
      {"type": "number", "format": "float"},
      components_schemas["protobuf2.TYPE_FLOAT"]
    )
    self.assertEqual(
      {"type": "string", "format": "int64"},
      components_schemas["protobuf2.TYPE_INT64"]
    )
    self.assertEqual(
      {"type": "string", "format": "uint64"},
      components_schemas["protobuf2.TYPE_UINT64"]
    )
    self.assertEqual(
      {"type": "integer", "format": "int32"},
      components_schemas["protobuf2.TYPE_INT32"]
    )
    self.assertEqual(
      {"type": "string", "format": "fixed64"},
      components_schemas["protobuf2.TYPE_FIXED64"]
    )
    self.assertEqual(
      {"type": "number", "format": "fixed32"},
      components_schemas["protobuf2.TYPE_FIXED32"]
    )
    self.assertEqual(
      {"type": "boolean"},
      components_schemas["protobuf2.TYPE_BOOL"]
    )
    self.assertEqual(
      {"type": "string"},
      components_schemas["protobuf2.TYPE_STRING"]
    )
    self.assertEqual(
      {"type": "string", "format": "byte"},
      components_schemas["protobuf2.TYPE_BYTES"]
    )
    self.assertEqual(
      {"type": "number", "format": "uint32"},
      components_schemas["protobuf2.TYPE_UINT32"]
    )
    self.assertEqual(
      {"type": "number", "format": "sfixed32"},
      components_schemas["protobuf2.TYPE_SFIXED32"]
    )
    self.assertEqual(
      {"type": "string", "format": "sfixed64"},
      components_schemas["protobuf2.TYPE_SFIXED64"]
    )
    self.assertEqual(
      {"type": "integer", "format": "int32"},
      components_schemas["protobuf2.TYPE_INT32"]
    )
    self.assertEqual(
      {"type": "string", "format": "sint64"},
      components_schemas["protobuf2.TYPE_SINT64"]
    )
    self.assertEqual(
      {"type": "string", "format": "binary"},
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
        "description": "A == 1\nB == 2\nC == 3",
        "allOf": [
          {
            "$ref":
              "#/components/schemas/grr.MetadataEnumFieldMessage.metadata_enum",
          },
        ],
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
        "description": "A == 1\nB == 2\nC == 3",
        "allOf": [
          {
            "$ref":
              "#/components/schemas/grr.MetadataEnumFieldMessage.metadata_enum",
          },
        ],
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
        "enum": ["A", "B", "C"],
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

    # Check the description of the `protobuf.oneof` from the `requestBody` field
    # of the `Operation Object` associated with `POST /metadata-test/method7`.
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
      self._GetParamSchema("/metadata_test/method7", "post", "oneof_int64")
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
      self._GetParamSchema("/metadata_test/method7", "post", "oneof_simplemsg")
    )

  def testProtobufMapIsDescribedCorrectlyInOpenApiDescription(self):
    # The semantic of `protobuf.map` is partially supported by the OpenAPI
    # Specification, as OAS supports only `string` for the keys' type, while
    # `protobuf.map`s key types can be any of a set of primitive types [1].
    #
    # [1]: https://developers.google.com/protocol-buffers/docs/proto#maps

    # Firstly, check the map schema definition from the `Components Object`.
    openapi_map_type_schema = (
      self.openapi_desc_dict
        .get("components")
        .get("schemas")
        .get("grr.MetadataMapMessage.FieldMapMap_"
             "protobuf2.TYPE_SFIXED64:grr.MetadataSimpleMessage")
    )
    self.assertEqual(
      {
        "description": "This is a map with real key "
                       "type=\"protobuf2.TYPE_SFIXED64\" and value "
                       "type=\"grr.MetadataSimpleMessage\"",
        "type": "object",
        "additionalProperties": {
          "$ref": "#/components/schemas/grr.MetadataSimpleMessage",
        },
      },
      openapi_map_type_schema
    )

    # Secondly, check the description of the `field_map` routes parameter.
    # Check the description of `field_map` from the `parameters` field of the
    # `Operation Object` associated with `GET /metadata-test/method8`.
    self.assertEqual(
      {
        "description": "This is a map with real key "
                       "type=\"protobuf2.TYPE_SFIXED64\" and value "
                       "type=\"grr.MetadataSimpleMessage\"",
        "allOf": [
          {
            "$ref": "#/components/schemas/grr.MetadataMapMessage.FieldMapMap_"
                    "protobuf2.TYPE_SFIXED64:grr.MetadataSimpleMessage",
          },
        ],
      },
      self._GetParamSchema("/metadata_test/method8", "get", "field_map")
    )

    # Check the description of `field_map` from the `requestBody` field of the
    # `Operation Object` associated with `POST /metadata-test/method8`.
    self.assertEqual(
      {
        "description": "This is a map with real key "
                       "type=\"protobuf2.TYPE_SFIXED64\" and value "
                       "type=\"grr.MetadataSimpleMessage\"",
        "allOf": [
          {
            "$ref": "#/components/schemas/grr.MetadataMapMessage.FieldMapMap_"
                    "protobuf2.TYPE_SFIXED64:grr.MetadataSimpleMessage",
          },
        ],
      },
      self._GetParamSchema("/metadata_test/method8", "post", "field_map")
    )

  def testOptionalPathParamsAreCorrectlyDescribedInOpenApiDescription(self):
    # This test verifies that path arguments are marked correctly as optional or
    # required.
    # The fact that the API routes that point out optional path arguments are
    # grouped under the same route described in the OpenAPI description is
    # tested by `testAllRoutesAreInOpenApiDescription`.

    # Test `GET /metadata_test/method9/{metadata_id}` parameters.
    self.assertCountEqual(
      [
        {
          "name": "metadata_id",
          "in": "path",
          "schema": {
            "$ref": "#/components/schemas/protobuf2.TYPE_STRING",
          },
        },
        {
          "name": "metadata_arg1",
          "in": "query",
          "schema": {
            "$ref": "#/components/schemas/protobuf2.TYPE_INT64",
          },
        },
        {
          "name": "metadata_arg2",
          "in": "query",
          "schema": {
            "$ref": "#/components/schemas/protobuf2.TYPE_BOOL",
          },
        },
      ],
      [
        self._GetParamDescription("/metadata_test/method9/{metadata_id}", "get",
                                  "metadata_id"),
        self._GetParamDescription("/metadata_test/method9/{metadata_id}", "get",
                                  "metadata_arg1"),
        self._GetParamDescription("/metadata_test/method9/{metadata_id}", "get",
                                  "metadata_arg2"),
      ]
    )

    # Test `GET /metadata_test/method9/{metadata_id}/fixed1/{metadata_arg1}`
    # parameters.
    self.assertCountEqual(
      [
        {
          "name": "metadata_id",
          "in": "path",
          "required": True,
          "schema": {
            "$ref": "#/components/schemas/protobuf2.TYPE_STRING",
          },
        },
        {
          "name": "metadata_arg1",
          "in": "path",
          "schema": {
            "$ref": "#/components/schemas/protobuf2.TYPE_INT64",
          },
        },
        {
          "name": "metadata_arg2",
          "in": "query",
          "schema": {
            "$ref": "#/components/schemas/protobuf2.TYPE_BOOL",
          },
        },
      ],
      [
        self._GetParamDescription(
          "/metadata_test/method9/{metadata_id}/fixed1/{metadata_arg1}",
          "get",
          "metadata_id"
        ),
        self._GetParamDescription(
          "/metadata_test/method9/{metadata_id}/fixed1/{metadata_arg1}",
          "get",
          "metadata_arg1"
        ),
        self._GetParamDescription(
          "/metadata_test/method9/{metadata_id}/fixed1/{metadata_arg1}",
          "get",
          "metadata_arg2"
        ),
      ]
    )

    # Test
    # `GET /metadata_test/method9/{metadata_id}/{metadata_arg1}/{metadata_arg2}`
    # parameters.
    self.assertCountEqual(
      [
        {
          "name": "metadata_id",
          "in": "path",
          "required": True,
          "schema": {
            "$ref": "#/components/schemas/protobuf2.TYPE_STRING",
          },
        },
        {
          "name": "metadata_arg1",
          "in": "path",
          "required": True,
          "schema": {
            "$ref": "#/components/schemas/protobuf2.TYPE_INT64",
          },
        },
        {
          "name": "metadata_arg2",
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
          "/method9/{metadata_id}/{metadata_arg1}/{metadata_arg2}",
          "get",
          "metadata_id"
        ),
        self._GetParamDescription(
          "/metadata_test"
          "/method9/{metadata_id}/{metadata_arg1}/{metadata_arg2}",
          "get",
          "metadata_arg1"
        ),
        self._GetParamDescription(
          "/metadata_test"
          "/method9/{metadata_id}/{metadata_arg1}/{metadata_arg2}",
          "get",
          "metadata_arg2"
        ),
      ]
    )

    # Test `POST /metadata_test/method9/{metadata_id}/{metadata_arg1}`
    # parameters.
    self.assertCountEqual(
      [
        {
          "name": "metadata_id",
          "in": "path",
          "required": True,
          "schema": {
            "$ref": "#/components/schemas/protobuf2.TYPE_STRING",
          },
        },
        {
          "name": "metadata_arg1",
          "in": "path",
          "required": True,
          "schema": {
            "$ref": "#/components/schemas/protobuf2.TYPE_INT64",
          },
        },
      ],
      [
        self._GetParamDescription(
          "/metadata_test/method9/{metadata_id}/{metadata_arg1}",
          "post",
          "metadata_id"
        ),
        self._GetParamDescription(
          "/metadata_test/method9/{metadata_id}/{metadata_arg1}",
          "post",
          "metadata_arg1"
        ),
      ]
    )

  def _GetParamDescription(self, method_path, http_method, param_name):
    params = (
      self.openapi_desc_dict
        .get("paths")
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
        self.openapi_desc_dict
          .get("paths")
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
      "description": "RDF type is `RDFDatetime` and it represents the number "
                     "of microseconds since epoch to a timestamp.",
      "allOf": [
        {
          "$ref": "#/components/schemas/RDFDatetime",
        },
      ],
    }
    self.assertEqual(
      expected_field_datetime,
      self._GetParamSchema("/metadata_test/method10", "get", "field_datetime")
    )
    self.assertEqual(
      expected_field_datetime,
      self._GetParamSchema("/metadata_test/method10", "post", "field_datetime")
    )

    expected_field_datetimeseconds = {
      "description": "RDF type is `RDFDatetimeSeconds` and it represents the "
                     "number of seconds since epoch to a timestamp.",
      "allOf": [
        {
          "$ref": "#/components/schemas/RDFDatetimeSeconds",
        },
      ],
    }
    self.assertEqual(
      expected_field_datetimeseconds,
      self._GetParamSchema("/metadata_test/method10", "get",
                           "field_datetimeseconds")
    )
    self.assertEqual(
      expected_field_datetimeseconds,
      self._GetParamSchema("/metadata_test/method10", "post",
                           "field_datetimeseconds")
    )

    expected_field_duration = {
      "description": "RDF type is `Duration` and it represents the number of "
                     "microseconds between two timestamps.",
      "allOf": [
        {
          "$ref": "#/components/schemas/Duration",
        },
      ],
    }
    self.assertEqual(
      expected_field_duration,
      self._GetParamSchema("/metadata_test/method10", "get", "field_duration")
    )
    self.assertEqual(
      expected_field_duration,
      self._GetParamSchema("/metadata_test/method10", "post", "field_duration")
    )

    expected_field_durationseconds = {
      "description": "RDF type is `DurationSeconds` and it represents the "
                     "number of seconds between two timestamps.",
      "allOf": [
        {
          "$ref": "#/components/schemas/DurationSeconds",
        },
      ],
    }
    self.assertEqual(
      expected_field_durationseconds,
      self._GetParamSchema("/metadata_test/method10", "get",
                           "field_durationseconds")
    )
    self.assertEqual(
      expected_field_durationseconds,
      self._GetParamSchema("/metadata_test/method10", "post",
                           "field_durationseconds")
    )

    expected_field_rdfbytes = {
      "description": "RDF type is `RDFBytes` and it represents a buffer of "
                     "bytes.",
      "allOf": [
        {
          "$ref": "#/components/schemas/RDFBytes",
        },
      ],
    }
    self.assertEqual(
      expected_field_rdfbytes,
      self._GetParamSchema("/metadata_test/method10", "get", "field_rdfbytes")
    )
    self.assertEqual(
      expected_field_rdfbytes,
      self._GetParamSchema("/metadata_test/method10", "post", "field_rdfbytes")
    )

    expected_field_hashdigest = {
      "description": "RDF type is `HashDigest` and it represents a binary hash "
                     "digest with hex string representation.",
      "allOf": [
        {
          "$ref": "#/components/schemas/HashDigest",
        },
      ],
    }
    self.assertEqual(
      expected_field_hashdigest,
      self._GetParamSchema("/metadata_test/method10", "get", "field_hashdigest")
    )
    self.assertEqual(
      expected_field_hashdigest,
      self._GetParamSchema("/metadata_test/method10", "post",
                           "field_hashdigest")
    )

    expected_field_globexpression = {
      "description": "RDF type is `GlobExpression` and it represents a glob "
                     "expression for a client path.",
      "allOf": [
        {
          "$ref": "#/components/schemas/GlobExpression",
        },
      ],
    }
    self.assertEqual(
      expected_field_globexpression,
      self._GetParamSchema("/metadata_test/method10", "get",
                           "field_globexpression")
    )
    self.assertEqual(
      expected_field_globexpression,
      self._GetParamSchema("/metadata_test/method10", "post",
                           "field_globexpression")
    )

    expected_field_bytesize = {
      "description": "RDF type is `ByteSize` and it represents a size for "
                     "bytes allowing standard unit prefixes.",
      "allOf": [
        {
          "$ref": "#/components/schemas/ByteSize",
        },
      ],
    }
    self.assertEqual(
      expected_field_bytesize,
      self._GetParamSchema("/metadata_test/method10", "get", "field_bytesize")
    )
    self.assertEqual(
      expected_field_bytesize,
      self._GetParamSchema("/metadata_test/method10", "post", "field_bytesize")
    )

    expected_field_rdfurn = {
      "description": "RDF type is `RDFURN` and it represents an object to "
                     "abstract URL manipulation.",
      "allOf": [
        {
          "$ref": "#/components/schemas/RDFURN",
        },
      ],
    }
    self.assertEqual(
      expected_field_rdfurn,
      self._GetParamSchema("/metadata_test/method10", "get", "field_rdfurn")
    )
    self.assertEqual(
      expected_field_rdfurn,
      self._GetParamSchema("/metadata_test/method10", "post", "field_rdfurn")
    )

    expected_field_sessionid = {
      "description": "RDF type is `SessionID` and it represents an rdfvalue "
                     "object that represents a session_id.",
      "allOf": [
        {
          "$ref": "#/components/schemas/SessionID",
        },
      ],
    }
    self.assertEqual(
      expected_field_sessionid,
      self._GetParamSchema("/metadata_test/method10", "get", "field_sessionid")
    )
    self.assertEqual(
      expected_field_sessionid,
      self._GetParamSchema("/metadata_test/method10", "post", "field_sessionid")
    )

    # Check that descriptions get concatenated in the case we have a
    # `protobuf.oneof` field that has an RDF type `sem_type.type`.
    expected_oneof_datetime = {
      "description": "This field is part of the \"semtype_oneof\" oneof. Only "
                     "one field per oneof should be present. RDF type is "
                     "`RDFDatetime` and it represents the number of "
                     "microseconds since epoch to a timestamp.",
      "allOf": [
        {
          "$ref": "#/components/schemas/RDFDatetime",
        },
      ],
    }
    self.assertEqual(
      expected_oneof_datetime,
      self._GetParamSchema("/metadata_test/method10", "get", "oneof_datetime")
    )
    self.assertEqual(
      expected_oneof_datetime,
      self._GetParamSchema("/metadata_test/method10", "post", "oneof_datetime")
    )

    # Now check that the RDF types have their schemas correctly described.
    components_schemas = self.openapi_desc_dict["components"]["schemas"]

    self.assertEqual(
      {
        "type": "string",
        "format": "uint64",
        "description": "RDF type is `RDFDatetime` and it represents "
                       "the number of microseconds since epoch to a timestamp.",
      },
      components_schemas["RDFDatetime"]
    )
    self.assertEqual(
      {
        "type": "string",
        "format": "uint64",
        "description": "RDF type is `RDFDatetimeSeconds` and it represents "
                       "the number of seconds since epoch to a timestamp.",
      },
      components_schemas["RDFDatetimeSeconds"]
    )
    self.assertEqual(
      {
        "type": "string",
        "format": "uint64",
        "description": "RDF type is `Duration` and it represents "
                       "the number of microseconds between two timestamps.",
      },
      components_schemas["Duration"]
    )
    self.assertEqual(
      {
        "type": "string",
        "format": "uint64",
        "description": "RDF type is `DurationSeconds` and it represents "
                       "the number of seconds between two timestamps.",
      },
      components_schemas["DurationSeconds"]
    )
    self.assertEqual(
      {
        "type": "string",
        "format": "byte",
        "description": "RDF type is `RDFBytes` and it represents "
                       "a buffer of bytes.",
      },
      components_schemas["RDFBytes"]
    )
    self.assertEqual(
      {
        "type": "string",
        "format": "byte",
        "description": "RDF type is `HashDigest` and it represents "
                       "a binary hash digest with hex string representation.",
      },
      components_schemas["HashDigest"]
    )
    self.assertEqual(
      {
        "type": "string",
        "description": "RDF type is `GlobExpression` and it represents "
                       "a glob expression for a client path.",
      },
      components_schemas["GlobExpression"]
    )
    self.assertEqual(
      {
        "type": "string",
        "format": "uint64",
        "description": "RDF type is `ByteSize` and it represents "
                       "a size for bytes allowing standard unit prefixes.",
      },
      components_schemas["ByteSize"]
    )
    self.assertEqual(
      {
        "type": "string",
        "description": "RDF type is `RDFURN` and it represents "
                       "an object to abstract URL manipulation.",
      },
      components_schemas["RDFURN"]
    )
    self.assertEqual(
      {
        "type": "string",
        "description": "RDF type is `SessionID` and it represents "
                       "an rdfvalue object that represents a session_id.",
      },
      components_schemas["SessionID"]
    )


def main(argv):
  test_lib.main(argv)


if __name__ == "__main__":
  app.run(main)
