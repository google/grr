#!/usr/bin/env python
# Lint as: python3
"""A module with API methods related to the GRR metadata."""
import json
import inspect

from urllib import parse as urlparse
from typing import Optional, Type, Any, Union, Tuple, List, Set, Dict, cast

from google.protobuf.descriptor import Descriptor
from google.protobuf.descriptor import EnumDescriptor
from google.protobuf.descriptor import FieldDescriptor

from grr_response_core import version
from grr_response_core.lib.rdfvalues import structs as rdf_structs
from grr_response_core.lib.rdfvalues import proto2 as protobuf2
from grr_response_proto.api import metadata_pb2
from grr_response_server import access_control
from grr_response_server.gui import api_call_handler_base

# Type aliases used throughout the metadata module.
SchemaReference = Dict[str, str]
PrimitiveSchema = Dict[str, str]
ArraySchema = Dict[str, Union[str, PrimitiveSchema, SchemaReference]]
EnumSchema = Dict[str, Union[str, Tuple[int, ...]]]
MessageSchema = Dict[
  str, Union[str,
             Dict[str, Union[SchemaReference, PrimitiveSchema, ArraySchema]]]
]
Schema = Union[PrimitiveSchema, EnumSchema, MessageSchema, ArraySchema]
PrimitiveDescription = Dict[str, Union[str, PrimitiveSchema]]

primitive_types: Dict[Union[int, str], PrimitiveDescription] = {
  protobuf2.TYPE_DOUBLE: {
    "name": "protobuf2.TYPE_DOUBLE",
    "schema": {"type": "number", "format": "double"},
  },
  protobuf2.TYPE_FLOAT: {
    "name": "protobuf2.TYPE_FLOAT",
    "schema": {"type": "number", "format": "float"},
  },
  protobuf2.TYPE_INT64: {
    "name": "protobuf2.TYPE_INT64",
    "schema": {"type": "integer", "format":"int64"},
  },
  protobuf2.TYPE_UINT64: {
    "name": "protobuf2.TYPE_UINT64",
    "schema": {"type": "integer", "format":"uint64"},
  },
  protobuf2.TYPE_INT32: {
    "name": "protobuf2.TYPE_INT32",
    "schema": {"type": "integer", "format": "int32"},
  },
  protobuf2.TYPE_FIXED64: {
    "name": "protobuf2.TYPE_FIXED64",
    "schema": {"type": "integer", "format": "uint64"}
  },
  protobuf2.TYPE_FIXED32: {
    "name": "protobuf2.TYPE_FIXED32",
    "schema": {"type": "integer", "format": "uint32"},
  },
  protobuf2.TYPE_BOOL: {
    "name": "protobuf2.TYPE_BOOL",
    "schema": {"type": "boolean"},
  },
  protobuf2.TYPE_STRING: {
    "name": "protobuf2.TYPE_STRING",
    "schema": {"type": "string"},
  },
  protobuf2.TYPE_BYTES: {
    "name": "protobuf2.TYPE_BYTES",
    # TODO: Here, "byte" (base64) might be used ?
    "schema": {"type": "string", "format": "binary"},
  },
  protobuf2.TYPE_UINT32: {
    "name": "protobuf2.TYPE_UINT32",
    "schema": {"type": "integer", "format": "uint32"},
  },
  protobuf2.TYPE_SFIXED32: {
    "name": "protobuf2.TYPE_SFIXED32",
    "schema": {"type": "integer", "format": "int32"},
  },
  protobuf2.TYPE_SFIXED64: {
    "name": "protobuf2.TYPE_SFIXED64",
    "schema": {"type": "integer","format": "int64"},
  },
  protobuf2.TYPE_SINT32: {
    "name": "protobuf2.TYPE_SINT32",
    "schema": {"type": "integer", "format": "int32"},
  },
  protobuf2.TYPE_SINT64: {
    "name": "protobuf2.TYPE_SINT64",
    "schema": {"type": "integer","format": "int64"},
  },
  "BinaryStream": {
    "name": "BinaryStream",
    "schema": {"type": "string", "format": "binary"},
  }
}

primitive_types_names: Set[str] = {
  primitive_type["name"] for primitive_type in primitive_types.values()
}

class ApiGetGrrVersionResult(rdf_structs.RDFProtoStruct):
  """An RDF wrapper for result of the API method for getting GRR version."""

  protobuf = metadata_pb2.ApiGetGrrVersionResult
  rdf_deps = []


class ApiGetGrrVersionHandler(api_call_handler_base.ApiCallHandler):
  """An API handler for the API method for getting GRR version."""

  result_type = ApiGetGrrVersionResult

  def Handle(
      self,
      args: None,
      token: Optional[access_control.ACLToken] = None,
  ) -> ApiGetGrrVersionResult:
    del args, token  # Unused.

    version_dict = version.Version()

    result = ApiGetGrrVersionResult()
    result.major = version_dict["major"]
    result.minor = version_dict["minor"]
    result.revision = version_dict["revision"]
    result.release = version_dict["release"]
    return result


class ApiGetOpenApiDescriptionResult(rdf_structs.RDFProtoStruct):
  """An RDF wrapper for the OpenAPI description of the GRR API."""

  protobuf = metadata_pb2.ApiGetOpenApiDescriptionResult


class ApiGetOpenApiDescriptionHandler(api_call_handler_base.ApiCallHandler):
  """Renders a description of the API using the OpenAPI specification."""

  args_type = None
  result_type = ApiGetOpenApiDescriptionResult

  def __init__(self, router: Any) -> None:
    # TODO(hanuszczak): Break dependency cycle between this module and
    # `api_call_router.py` and then use ApiCallRouter as self.router's and the
    # argument's type.
    self.router: Any = router
    # The main OpenAPI description object.
    self.open_api_obj: Optional[Dict[str, Union[str, List, Dict]]] = None
    self.schema_objs: Optional[Dict[str, Schema]] = None

  def _NormalizePathComponent(self, component: str) -> str:
    """Normalize the given path component to be used in a valid OpenAPI path."""
    if len(component) > 0 and component[0] == '<' and component[-1] == '>':
      component = component[1:-1]
      component = component.split(":")[-1]
      component = f"{{{component}}}"

    return component

  def _NormalizePath(self, path: str) -> str:
    """Keep only fixed parts and parameter names from Werkzeug URL patterns.

    The OpenAPI specification requires that parameters are surrounded by { }
    which are added in _NormalizePathComponent.

    Args:
      path: The path whose representation will be normalized.

    Returns:
      The normalized version of the path argument, which is a valid OpenAPI
      path, with curly brackets around path arguments.
    """
    components = path.split("/")
    normalized_components = [
      self._NormalizePathComponent(component) for component in components
    ]

    normalized_path = '/'.join(normalized_components)

    return normalized_path

  def _GetPathArgsFromPath(self, path: str) -> List[str]:
    """Extract path parameters from a Werkzeug Rule URL."""
    path_args = []

    components = path.split("/")
    for component in components:
      if len(component) > 0 and component[0] == '<' and component[-1] == '>':
        normalized_component = self._NormalizePathComponent(component)
        normalized_component = normalized_component[1:-1]
        path_args.append(normalized_component)

    return path_args

  def _GetTypeName(
      self,
      cls: Union[Descriptor, FieldDescriptor, EnumDescriptor, Type, int, str]
  ) -> str:
    """Generically extract type name from protobuf Descriptors/Type/int/str."""
    if isinstance(cls, FieldDescriptor):
      if cls.message_type:
        return self._GetTypeName(cls.message_type)
      if cls.enum_type:
        return self._GetTypeName(cls.enum_type)

      return self._GetTypeName(cls.type)

    if isinstance(cls, Descriptor):
      return cls.full_name

    if isinstance(cls, EnumDescriptor):
      return cls.full_name

    if isinstance(cls, type):
      return cls.__name__

    if isinstance(cls, int):  # It's a protobuf.Descriptor.type value.
      return primitive_types[cls]["name"]

    return str(cls)  # Cover "BinaryStream" and None.

  def _SetMetadata(self) -> None:
    """Set `openapi`, `info`, `servers` fields of the root OpenAPI object."""
    if self.open_api_obj is None:  # Check required by mypy.
      raise AssertionError("The root OpenAPI object is uninitialized.")

    oas_version = "3.0.3"
    version_dict = version.Version()

    # This dictionary holds the "metadata" fields of the OpenAPI root object,
    # basically everything but the paths and the components descriptions.
    metadata_dict = {
      "openapi": oas_version,
      "info": {
        "title": "GRR Rapid Response API",
        "description": "GRR Rapid Response is an incident response framework "
                       "focused on remote live forensics.",
        "contact": {
          "name": "GRR GitHub Repository",
          "url": "https://github.com/google/grr"
        },
        "license": {
          "name": "Apache 2.0",
          "url": "http://www.apache.org/licenses/LICENSE-2.0"
        },
        "version": (
          f"{version_dict['major']}."
          f"{version_dict['minor']}."
          f"{version_dict['revision']}."
          f"{version_dict['release']}"
        )
      },
      "servers": [
        {
          "url": "/",
          "description": "Root path of the GRR API",
        },
      ],
    }  # type: Dict[str, Union[str, List, Dict]]

    # Merge this "metadata" dictionary into the main OpenAPI dictionary.
    self.open_api_obj.update(metadata_dict)

  def _AddPrimitiveTypesSchemas(self) -> None:
    """Adds the OpenAPI schemas for Protobuf primitives and BinaryStream."""
    if self.schema_objs is None:  # Check required by mypy.
      raise AssertionError(
        "The container of OpenAPI type schemas is not initialized."
      )

    primitive_types_schemas = {
      primitive_type["name"]: primitive_type["schema"]
      for primitive_type in primitive_types.values()
    }

    self.schema_objs.update(primitive_types_schemas)

  def _ExtractEnumSchema(
      self,
      descriptor: EnumDescriptor,
  ) -> EnumSchema:
    """Extracts OpenAPI schema of a protobuf enum.

    This method should generally not be called directly, but rather through
    _ExtractSchema which takes care of error-verifications and caching.
    This enum type is guaranteed to be a leaf in a type traversal, so there is
    no need for the `visiting` set that _ExtractMessageSchema uses to detect
    cycles.

    Args:
      descriptor: The protobuf EnumDescriptor of the enum type whose schema is
        extracted.

    Returns:
      The constructed OpenAPI schema associated with the given enum type.
    """
    if self.schema_objs is None:  # Check required by mypy.
      raise AssertionError(
        "The container of OpenAPI type schemas is not initialized."
      )

    enum_schema_obj = {
      "type": "integer",
      "format": "int32"
    }  # type: Dict[str, Union[str, Tuple[int, ...]]]

    if len(descriptor.values) > 0:
      enum_schema_obj["enum"] = (
        tuple([enum_value.number for enum_value in descriptor.values])
      )
      enum_schema_obj["description"] = (
        "\n".join([f"{enum_value.number} == {enum_value.name}"
                   for enum_value in descriptor.values])
      )
    else:
      enum_schema_obj["enum"] = ()

    self.schema_objs[self._GetTypeName(descriptor)] = enum_schema_obj

    return enum_schema_obj

  def _ExtractMessageSchema(
      self,
      descriptor: Descriptor,
      visiting: Set[str]
  ) -> MessageSchema:
    """Extracts OpenAPI schema of a protobuf message.

    This method should generally not be called directly, but rather through
    _ExtractSchema which takes care of error-verifications and caching.

    Args:
      descriptor: The protobuf Descriptor associated with a protobuf message.
      visiting: A set of type names that are in the process of having their
        OpenAPI schemas constructed and have their associated _Extract*Schema
        call in the current call stack.

    Returns:
      The constructed OpenAPI schema associated with this message type.
    """
    if self.schema_objs is None:  # Check required by mypy.
      raise AssertionError(
        "The container of OpenAPI type schemas is not initialized."
      )

    type_name = self._GetTypeName(descriptor)

    schema_obj = {"type": "object"}  # type: MessageSchema
    properties = dict()  # Required to please mypy.
    visiting.add(type_name)

    for field_descriptor in descriptor.fields:
      field_name = field_descriptor.name
      message_descriptor = field_descriptor.message_type # None if not Message.
      enum_descriptor = field_descriptor.enum_type # None if not Enum.
      descriptor = message_descriptor or enum_descriptor

      if descriptor:
        self._ExtractSchema(descriptor, visiting)

      schema_or_ref_obj = (
        self._GetSchemaOrReferenceObject(
          self._GetTypeName(field_descriptor),
          field_descriptor.label == protobuf2.LABEL_REPEATED)
      )

      properties[field_name] = schema_or_ref_obj

    visiting.remove(type_name)

    schema_obj["properties"] = properties
    self.schema_objs[type_name] = schema_obj

    return schema_obj

  def _ExtractSchema(
      self,
      cls: Union[Descriptor, FieldDescriptor, EnumDescriptor, Type, int, str],
      visiting: Set[str]
  ) -> Optional[Schema]:
    """Build OpenAPI schema from any valid type descriptor or identifier."""
    if self.schema_objs is None:  # Check required by mypy.
      raise AssertionError(
        "The container of OpenAPI type schemas is not initialized."
      )

    if cls is None:
      raise ValueError(f"Trying to extract schema of None.")

    type_name = self._GetTypeName(cls)
    # "Primitive" types should be already present in self.schema_objs.
    if type_name in self.schema_objs:
      return self.schema_objs[type_name]

    if type_name in visiting:
      # Dependency cycle.
      return None

    if isinstance(cls, Descriptor):
      return self._ExtractMessageSchema(cls, visiting)

    if isinstance(cls, EnumDescriptor):
      return self._ExtractEnumSchema(cls)

    raise TypeError(f"Don't know how to handle type \"{type_name}\" "
                    f"which is not a protobuf message Descriptor, "
                    f"nor an EnumDescriptor, nor a primitive type.")

  def _ExtractSchemas(self) -> None:
    """Extracts OpenAPI schemas for all the used protobuf types."""

    self.schema_objs = dict()  # Holds OpenAPI representations of types.
    self._AddPrimitiveTypesSchemas()

    # Holds state of types extraction (white/gray nodes).
    visiting = set()  # type: Set[str]
    router_methods = self.router.__class__.GetAnnotatedMethods()
    for method_metadata in router_methods.values():
      args_type = method_metadata.args_type
      if args_type:
        if (
            inspect.isclass(args_type) and
            issubclass(args_type, rdf_structs.RDFProtoStruct)
        ):
          self._ExtractSchema(args_type.protobuf.DESCRIPTOR, visiting)
        else:
          self._ExtractSchema(args_type, visiting)

      result_type = method_metadata.result_type
      if result_type:
        if (
            inspect.isclass(result_type) and
            issubclass(result_type, rdf_structs.RDFProtoStruct)
        ):
          self._ExtractSchema(result_type.protobuf.DESCRIPTOR, visiting)
        else:
          self._ExtractSchema(result_type, visiting)

  def _SetComponents(self) -> None:
    """Set the `components` OpenAPI field to the extracted schema objects."""
    if self.open_api_obj is None:  # Check required by mypy.
      raise AssertionError("The root OpenAPI object is uninitialized.")
    if self.schema_objs is None:
      raise AssertionError(
        "The container of OpenAPI type schemas is not initialized."
      )

    schemas_obj = dict()
    type_names = set(self.schema_objs.keys())
    # Create components only for composite types.
    for type_name in type_names - primitive_types_names:
      schemas_obj[type_name] = self.schema_objs[type_name]

    # The Components Object "components" of the root OpenAPI object.
    components_obj = {"schemas": schemas_obj}

    self.open_api_obj["components"] = components_obj

  def _GetSchemaOrReferenceObject(
      self,
      type_name: str,
      is_array: bool = False
  ) -> Union[PrimitiveSchema, SchemaReference, ArraySchema]:
    """Get an existing Schema Object if primitive type, else a Reference Object.

    Primitive, not composite types don't have an actual schema, but rather an
    equivalent OpenAPI representation that gets returned for them.
    More complex types are expected to have been previously defined as OpenAPI
    components and are used through OpenAPI references.

    Args:
      type_name: The name of the type whose OpenAPI (previously constructed)
        schema will be returned or the name of the type for which an OpenAPI
        reference object will be created and returned.
      is_array: A boolean flag indicating whether the selected type's schema or
        reference object should be wrapped in an OpenAPI array as the items
        type.

    Returns:
      If the `is_array` argument is set to False, then:
      - if the type is primitive, returns the associated OpenAPI schema object;
      - else, an OpenAPI reference object representing the path to the actual
        OpenAPI schema definition of the selected type.
      If the `is_array` argument is set to True, then an OpenAPI array schema
      is constructed that uses the for the `items` field:
      - if the type is primitive, the actual OpenAPI schema of the type;
      -else, an OpenAPI reference object associated with the type's schema.
    """
    if self.schema_objs is None:
      raise AssertionError(
        "The container of OpenAPI type schemas is not initialized."
      )

    schema_or_ref_obj = (
      None
    )  # type: Optional[Union[PrimitiveSchema, SchemaReference]]
    if type_name in primitive_types_names:
      schema_obj = self.schema_objs[type_name]
      schema_or_ref_obj = cast(PrimitiveSchema, schema_obj)
    else:
      reference_obj = {"$ref": f"#/components/schemas/{type_name}"}
      schema_or_ref_obj = reference_obj

    if schema_or_ref_obj is None:  # Check required by mypy.
      raise AssertionError("Failed to find schema or create reference.")

    if is_array:
      array_schema = {
        "type": "array",
        "items": schema_or_ref_obj
      }  # type: ArraySchema
      return array_schema

    return schema_or_ref_obj

  def _GetParameters(
      self,
      path_params: List[FieldDescriptor],
      query_params: List[FieldDescriptor]
  ) -> List[
    Dict[str, Union[str, bool, PrimitiveSchema, SchemaReference, ArraySchema]]
  ]:
    """Build the OpenAPI description of the parameters of a route."""
    parameters = []

    path_params_set = set(path_params)
    query_params_set = set(query_params)
    for field_d in path_params_set | query_params_set:
      parameter_obj = {"name": field_d.name}
      if field_d in path_params_set:
        parameter_obj["in"] = "path"
        parameter_obj["required"] = True
      else:
        parameter_obj["in"] = "query"

      schema_or_ref_obj = (
        self._GetSchemaOrReferenceObject(
          self._GetTypeName(field_d),
          field_d.label == protobuf2.LABEL_REPEATED
        )
      )
      parameter_obj["schema"] = schema_or_ref_obj

      parameters.append(parameter_obj)

    return parameters

  def _GetRequestBody(
      self,
      body_params: List[FieldDescriptor]
  ) -> Dict[str, Dict]:
    """Build the OpenAPI description of the request body required by a route."""
    request_body_obj = {"content": dict()}  # type: Dict[str, Dict]

    properties = dict()
    for field_d in body_params:
      field_name = field_d.name
      schema_or_ref_obj = (
        self._GetSchemaOrReferenceObject(
          self._GetTypeName(field_d),
          field_d.label == protobuf2.LABEL_REPEATED
        )
      )
      properties[field_name] = schema_or_ref_obj

    schema_obj = {
      "type": "object",
      "properties": properties
    }  # type: Dict[str, Union[str, Dict]]

    media_obj = {"schema": schema_obj}

    request_body_obj["content"]["application/json"] = media_obj

    return request_body_obj

  def _GetResponseObject200(
      self,
      result_type: Union[rdf_structs.RDFProtoStruct, str],
      router_method_name: str
  ) -> Dict[str, Union[str, Dict]]:
    """Build the OpenAPI description of a successful, 200 HTTP response."""
    resp_success_obj = dict()  # type: Dict[str, Union[str, Dict]]

    if result_type:
      if (
          isinstance(result_type, type) and
          issubclass(result_type, rdf_structs.RDFProtoStruct)
      ):
        result_type_name = self._GetTypeName(
          cast(rdf_structs.RDFProtoStruct, result_type).protobuf.DESCRIPTOR
        )
      else:
        result_type_name = self._GetTypeName(result_type)

      resp_success_obj["description"] = (
        f"The call to the {router_method_name} API method succeeded and it "
        f"returned an instance of {result_type_name}."
      )

      schema_or_ref_obj = self._GetSchemaOrReferenceObject(result_type_name)
      media_obj = {"schema": schema_or_ref_obj}

      content = dict()  # Needed to please mypy.
      if result_type == "BinaryStream":
        content["application/octet-stream"] = media_obj
      else:
        content["application/json"] = media_obj
      resp_success_obj["content"] = content
    else:
      resp_success_obj["description"] = (
        f"The call to the {router_method_name} API method succeeded."
      )

    return resp_success_obj

  def _GetResponseObjectDefault(
      self,
      router_method_name: str
  ) -> Dict[str, str]:
    """Build the OpenAPI description used for all undescribed HTTP responses."""
    resp_default_obj= {
      "description": f"The call to the {router_method_name} API method did not "
                     f"succeed."
    }

    return resp_default_obj

  def _SetEndpoints(self) -> None:
    """Build the OpenAPI description of all the routes exposed by the API."""
    if self.open_api_obj is None:  # Check required by mypy.
      raise AssertionError("The root OpenAPI object is uninitialized.")

    # The Paths Object "paths" field of the root OpenAPI object.
    paths_obj = dict()  # type: Dict[str, Dict]

    router_methods = self.router.__class__.GetAnnotatedMethods()
    for router_method_name in router_methods:
      router_method = router_methods[router_method_name]
      for http_method, path, strip_root_types in router_method.http_methods:
        normalized_path = self._NormalizePath(path)
        path_args = set(self._GetPathArgsFromPath(path))

        if normalized_path not in paths_obj:
          paths_obj[normalized_path] = dict()

        # The Path Object associated with the current path.
        path_obj = paths_obj[normalized_path]

        url_path = (
          path
            .replace('/', '-')
            .replace('<', '_')
            .replace('>', '_')
            .replace(':', '-')
        )
        # The Operation Object associated with the current http method.
        operation_obj = {
          "tags": [router_method.category or "NoCategory",],
          "description": router_method.doc or "No description.",
          "operationId": urlparse.quote(f"{http_method}-{url_path}-"
                                        f"{router_method.name}")
        }  # type: Dict[str, Any]

        # Parameters extraction.
        field_descriptors = []
        if router_method.args_type:
          if not (
              inspect.isclass(router_method.args_type) and
              issubclass(router_method.args_type, rdf_structs.RDFProtoStruct)
          ):
            raise TypeError("Router method args type is not a RDFProtoStruct "
                            "subclass.")
          field_descriptors = router_method.args_type.protobuf.DESCRIPTOR.fields

        # Triage fields into params: path, query and part of the request body.
        path_params = []
        query_params = []
        body_params = []
        for field_d in field_descriptors:
          if field_d.name in path_args:
            path_params.append(field_d)
          elif http_method.upper() in ("GET", "HEAD"):
            query_params.append(field_d)
          else:
            body_params.append(field_d)

        operation_obj["parameters"] = self._GetParameters(path_params,
                                                          query_params)

        if body_params:
          # The Request Body Object for data sent in the HTTP message body.
          operation_obj["requestBody"] = self._GetRequestBody(body_params)

        # The Responses Object which describes the responses associated with
        # HTTP response codes.
        responses_obj = {
          "200": (
            self._GetResponseObject200(router_method.result_type,
                                       router_method_name)
          ),
          "default": self._GetResponseObjectDefault(router_method_name),
        }  # type: Dict[str, Dict]

        operation_obj["responses"] = responses_obj

        path_obj[http_method.lower()] = operation_obj

    self.open_api_obj["paths"] = paths_obj

  def Handle(
      self,
      args: None,
      token: Optional[access_control.ACLToken] = None,
  ) -> ApiGetOpenApiDescriptionResult:
    """Handle requests for the OpenAPI description of the GRR API."""
    result = ApiGetOpenApiDescriptionResult()

    if self.open_api_obj is not None:
      result.open_api_description = json.dumps(self.open_api_obj)
      return result

    self.open_api_obj = dict()
    self._SetMetadata()
    self._ExtractSchemas()
    self._SetComponents()
    self._SetEndpoints()

    result.open_api_description = json.dumps(self.open_api_obj)
    return result
