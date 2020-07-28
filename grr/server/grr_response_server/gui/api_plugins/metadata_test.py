#!/usr/bin/env python
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


class MetadataDummyApiCallRouter(api_call_router.ApiCallRouter):
  """Dummy ApiCallRouter implementation used for Metadata testing."""

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


class ApiGetOpenApiDescriptionHandlerTest(api_test_lib.ApiCallHandlerTest):
  """Test for ApiGetOpenApiDescriptionHandler."""
  def setUp(self):
    super(ApiGetOpenApiDescriptionHandlerTest, self).setUp()
    self.router = MetadataDummyApiCallRouter()
    self.router_methods = self.router.__class__.GetAnnotatedMethods()

    self.handler = metadata_plugin.ApiGetOpenApiDescriptionHandler(self.router)

    result = self.handler.Handle(None, token=self.token)
    self.open_api_desc = result.open_api_description
    self.open_api_desc_dict = json.loads(self.open_api_desc)

  @skip.If(
    "openapi-spec-validator" not in {p.key for p in pkg_resources.working_set},
    "The openapi-spec-validator module used for validating the OpenAPI "
    "specification is not installed."
  )
  def testRendersValidOpenApiDescription(self):
    import openapi_spec_validator
    try:
      errors = openapi_spec_validator.validate_spec(self.open_api_desc_dict)
    except:
      errors = True

    self.assertIsNone(errors)

  def testAllRoutesInOpenApiDescription(self):
    for router_method in self.router_methods.values():
      for http_method, path, strip_root_types in router_method.http_methods:
        simple_path = self.handler._SimplifyPath(path)
        http_method = http_method.lower()

        operation_obj = \
          self.open_api_desc_dict["paths"][simple_path][http_method]

        self.assertIsNotNone(operation_obj)

  def testRouteArgsSeparationInPathQueryBody(self):
    for router_method in self.router_methods.values():
      for http_method, path, strip_root_types in router_method.http_methods:
        simple_path = self.handler._SimplifyPath(path)
        http_method = http_method.lower()

        field_descriptors = []
        if router_method.args_type:
          field_descriptors = router_method.args_type.protobuf.DESCRIPTOR.fields

        path_args = self.handler._GetPathArgsFromPath(path)
        path_args = set(path_args)

        # Triage parameters from the RDFProtoStruct class.
        path_params = set()
        query_params = set()
        body_params = set()

        for field_d in field_descriptors:
          field_name = field_d.name
          if field_name in path_args:
            path_params.add(field_name)
          elif http_method.upper() in ("GET", "HEAD"):
            query_params.add(field_name)
          else:
            body_params.add(field_name)

        # Triage parameters from the generated OpenAPI description.
        open_api_path_params = set()
        open_api_query_params = set()
        open_api_body_params = set()

        # https://swagger.io/specification/#operation-object
        operation_obj = \
          self.open_api_desc_dict["paths"][simple_path][http_method]

        # parameters = operation_obj.get("parameters")
        # self.assertIsNotNone(parameters)
        parameters = operation_obj["parameters"]
        for parameter in parameters:
          param_name = parameter["name"]
          if parameter["in"] == "path":
            open_api_path_params.add(param_name)
          elif parameter["in"] == "query":
            open_api_query_params.add(param_name)
          else:
            raise TypeError("Wrong OpenAPI parameter location: "
                            "\"{parameter["in"]}\"")

        request_body_obj = operation_obj.get("requestBody")
        if request_body_obj:
          schema_obj = request_body_obj["content"]["application/json"]["schema"]
          for param_name in schema_obj["properties"]:
            open_api_body_params.add(param_name)

        self.assertSetEqual(path_params, open_api_path_params)
        self.assertSetEqual(query_params, open_api_query_params)
        self.assertSetEqual(body_params, open_api_body_params)

  def testRouteResultOpenApiDescription(self):
    for router_method in self.router_methods.values():
      for http_method, path, strip_root_types in router_method.http_methods:
        simple_path = self.handler._SimplifyPath(path)
        http_method = http_method.lower()

        # Check if there is a result type annotated to the method object.
        result_type = router_method.result_type is not None

        # Check if there is a result type schema in the OpenAPI description.
        # https://swagger.io/specification/#operation-object
        operation_obj = \
          self.open_api_desc_dict["paths"][simple_path][http_method]
        responses_obj = operation_obj["responses"]

        self.assertIn("200", responses_obj)
        self.assertIn("default", responses_obj)

        resp_200 = responses_obj["200"]
        result_type_open_api = "content" in resp_200

        self.assertEqual(result_type, result_type_open_api)

  def testOpenApiPrimitiveTypesDescription(self):
    operation_obj = (
      self.open_api_desc_dict
        .get("paths")
        .get("/metadata_test/method3")
        .get("get")
    )
    primitive_parameters = operation_obj["parameters"]

    open_api_primitives = {p["name"]: p["schema"] for p in primitive_parameters}
    open_api_primitives["BinaryStream"] = (
      operation_obj
        .get("responses")
        .get("200")
        .get("content")
        .get("application/octet-stream")
        .get("schema")
    )

    expected = dict()

    expected_double = {"type": "number", "format": "double"}
    expected["field_double"] = expected_double

    expected_float = {"type": "number", "format": "float"}
    expected["field_float"] = expected_float

    expected_int64 = {"type": "integer", "format": "int64"}
    expected["field_int64"] = expected_int64

    expected_uint64 = {"type": "integer", "format": "uint64"}
    expected["field_uint64"] = expected_uint64

    expected_int32 = {"type": "integer", "format": "int32"}
    expected["field_int32"] = expected_int32

    expected_fixed64 = {"type": "integer", "format": "uint64"}
    expected["field_fixed64"] = expected_fixed64

    expected_fixed32 = {"type": "integer", "format": "uint32"}
    expected["field_fixed32"] = expected_fixed32

    expected_bool = {"type": "boolean"}
    expected["field_bool"] = expected_bool

    expected_string = {"type": "string"}
    expected["field_string"] = expected_string

    expected_bytes = {"type": "string", "format": "binary"}
    expected["field_bytes"] = expected_bytes

    expected_uint32 = {"type": "integer", "format": "uint32"}
    expected["field_uint32"] = expected_uint32

    expected_sfixed32 = {"type": "integer", "format": "int32"}
    expected["field_sfixed32"] = expected_sfixed32

    expected_sfixed64 = {"type": "integer", "format": "int64"}
    expected["field_sfixed64"] = expected_sfixed64

    expected_sint32 = {"type": "integer", "format": "int32"}
    expected["field_sint32"] = expected_sint32

    expected_sint64 = {"type": "integer", "format": "int64"}
    expected["field_sint64"] = expected_sint64

    expected_binarystream = {"type": "string", "format": "binary"}
    expected["BinaryStream"] = expected_binarystream

    self.assertDictEqual(expected, open_api_primitives)

  def testRepetitiveField(self):
    # Test the GET route. The repeated field should be a query parameter.
    params = (self.open_api_desc_dict.get("paths").get("/metadata_test/method4")
              .get("get").get("parameters"))
    self.assertEqual(len(params), 1)

    param = params[0]
    self.assertEqual(param["in"], "query")
    schema = param["schema"]
    self.assertEqual(schema["type"], "array")
    self.assertEqual(schema["items"]["type"], "integer")
    self.assertEqual(schema["items"]["format"], "int64")

    # Test the POST route. The repeated field should be in the request body.
    req_body = (self.open_api_desc_dict.get("paths")
                .get("/metadata_test/method4").get("post").get("requestBody"))
    req_schema = req_body["content"]["application/json"]["schema"]
    self.assertEqual(req_schema["type"], "object")
    schema = req_schema["properties"]["field_repeated"]
    self.assertEqual(schema["type"], "array")
    self.assertEqual(schema["items"]["type"], "integer")
    self.assertEqual(schema["items"]["format"], "int64")

  def testEnumField(self):
    # Test the GET route. The enum field should be a query parameter.
    params = (self.open_api_desc_dict.get("paths").get("/metadata_test/method5")
              .get("get").get("parameters"))
    self.assertEqual(len(params), 1)

    param = params[0]
    self.assertEqual(param["in"], "query")
    ref_get = param["schema"]["$ref"]
    ref_nodes = ref_get.split("/")
    ref_nodes = ref_nodes[1:]
    schema = self.open_api_desc_dict
    for node in ref_nodes:
      schema = schema[node]

    # Test the OpenAPI component agains its protobuf counterpart.
    self.assertEqual(schema["type"], "integer")
    self.assertEqual(schema["format"], "int32")
    enum_values_open_api = set(schema["enum"])

    message_d = MetadataEnumFieldMessage.protobuf.DESCRIPTOR
    self.assertEqual(len(message_d.enum_types), 1)
    enum_d = message_d.enum_types[0]
    enum_values_ds = enum_d.values
    enum_values_protobuf = set(
      [enum_value_d.number for enum_value_d in enum_values_ds])
    self.assertSetEqual(enum_values_open_api, enum_values_protobuf)

    # Test the POST route. The enum field should be in the request body.
    # Just check that the structure is correct and that the same component
    # is referenced as above.
    req_body = (self.open_api_desc_dict.get("paths")
                .get("/metadata_test/method5").get("post").get("requestBody"))
    req_schema = req_body["content"]["application/json"]["schema"]
    self.assertEqual(req_schema["type"], "object")
    ref_post = req_schema["properties"]["field_enum"]["$ref"]
    self.assertEqual(ref_post, ref_get)

  def testOpenApiTypeReferences(self):
    # Tests that references are used for composite types and that the referenced
    # types are declared, including the case of cyclic dependencies.

    # Test that composite types are defined.
    components_schemas = self.open_api_desc_dict["components"]["schemas"]
    root = components_schemas["grr.MetadataTypesHierarchyRoot"]
    root_ref = "#/components/schemas/grr.MetadataTypesHierarchyRoot"
    cyclic = components_schemas["grr.MetadataTypesHierarchyCyclic"]
    cyclic_ref = "#/components/schemas/grr.MetadataTypesHierarchyCyclic"
    leaf = components_schemas["grr.MetadataTypesHierarchyLeaf"]
    leaf_ref = "#/components/schemas/grr.MetadataTypesHierarchyLeaf"

    # Test the references between message types.
    self.assertEqual(root["properties"]["child_1"]["$ref"], cyclic_ref)
    self.assertEqual(root["properties"]["child_2"]["$ref"], leaf_ref)

    self.assertEqual(cyclic["properties"]["root"]["$ref"], root_ref) # Cycle.
    self.assertEqual(cyclic["properties"]["child_1"]["$ref"], leaf_ref)


def main(argv):
  test_lib.main(argv)


if __name__ == "__main__":
  app.run(main)
