#!/usr/bin/env python
# Lint as: python3
"""A module with API methods related to the GRR metadata."""
import json
import inspect
import collections

from urllib import parse as urlparse
from typing import Optional, cast
from typing import Type, Any, Union, Tuple, List, Set, Dict, DefaultDict

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
ArraySchema = Dict[str, Union[str, SchemaReference]]
EnumSchema = Dict[str, Union[str, Tuple[str, ...]]]
MessageSchema = Dict[
  str, Union[str,
             Dict[str, Union[SchemaReference, ArraySchema]]]
]
Schema = Union[PrimitiveSchema, EnumSchema, MessageSchema, ArraySchema]
PrimitiveDescription = Dict[str, Union[str, PrimitiveSchema]]

# Follows the proto3 JSON encoding [1] as a base, but whenever
# the OpenAPI Specification [2] provides a more specific description of the
# same type, its version is used (noted by "OAS (type, format)" comments), with
# the exception of `int64` which uses `string` as a type.
#
# [1]: https://developers.google.com/protocol-buffers/docs/proto3#json
# [2]: https://swagger.io/specification/#data-types
primitive_types: Dict[Union[int, str], PrimitiveDescription] = {
  protobuf2.TYPE_DOUBLE: {
    "name": "protobuf2.TYPE_DOUBLE",
    "schema": {"type": "number", "format": "double"},  # OAS (type, format)
  },
  protobuf2.TYPE_FLOAT: {
    "name": "protobuf2.TYPE_FLOAT",
    "schema": {"type": "number", "format": "float"},  # OAS (type, format)
  },
  protobuf2.TYPE_INT64: {
    "name": "protobuf2.TYPE_INT64",
    "schema": {"type": "string", "format": "int64"},
  },
  protobuf2.TYPE_UINT64: {
    "name": "protobuf2.TYPE_UINT64",
    "schema": {"type": "string", "format": "uint64"},
  },
  protobuf2.TYPE_INT32: {
    "name": "protobuf2.TYPE_INT32",
    "schema": {"type": "integer", "format": "int32"},  # OAS (type, format)
  },
  protobuf2.TYPE_FIXED64: {
    "name": "protobuf2.TYPE_FIXED64",
    "schema": {"type": "string", "format": "fixed64"}
  },
  protobuf2.TYPE_FIXED32: {
    "name": "protobuf2.TYPE_FIXED32",
    "schema": {"type": "number", "format": "fixed32"},
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
    "schema": {"type": "string", "format": "byte"},  # OAS (type, format)
  },
  protobuf2.TYPE_UINT32: {
    "name": "protobuf2.TYPE_UINT32",
    "schema": {"type": "number", "format": "uint32"},
  },
  protobuf2.TYPE_SFIXED32: {
    "name": "protobuf2.TYPE_SFIXED32",
    "schema": {"type": "number", "format": "sfixed32"},
  },
  protobuf2.TYPE_SFIXED64: {
    "name": "protobuf2.TYPE_SFIXED64",
    "schema": {"type": "string", "format": "sfixed64"},
  },
  protobuf2.TYPE_SINT32: {
    "name": "protobuf2.TYPE_SINT32",
    "schema": {"type": "integer", "format": "int32"},  # OAS (type, format)
  },
  protobuf2.TYPE_SINT64: {
    "name": "protobuf2.TYPE_SINT64",
    "schema": {"type": "string", "format": "sint64"},
  },
  "BinaryStream": {
    "name": "BinaryStream",
    "schema": {"type": "string", "format": "binary"},
  }
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
  """Renders a description of the API using the OpenAPI Specification."""

  args_type = None
  result_type = ApiGetOpenApiDescriptionResult

  def __init__(self, router: Any) -> None:
    # TODO(hanuszczak): Break dependency cycle between this module and
    # `api_call_router.py` and then use `ApiCallRouter` as `self.router`'s and
    # the argument's type.
    self.router: Any = router
    # The JSON-serialized root `OpenAPI Object`.
    self.openapi_obj_json: Optional[str] = None
    self.schema_objs: Optional[Dict[str, Schema]] = None

  def _AddPrimitiveTypesSchemas(self) -> None:
    """Adds the OpenAPI schemas for protobuf primitives and `BinaryStream`."""
    if self.schema_objs is None:  # Check required by mypy.
      raise AssertionError(
        "The container of OpenAPI type schemas is not initialized."
      )

    primitive_types_schemas = {
      primitive_type["name"]: primitive_type["schema"]
      for primitive_type in primitive_types.values()
    }

    self.schema_objs.update(
      cast(Dict[str, Dict[str, str]], primitive_types_schemas)
    )

  def _CreateEnumSchema(
      self,
      descriptor: EnumDescriptor,
  ) -> None:
    """Creates the OpenAPI schema of a protobuf enum.

    This method should generally not be called directly, but rather through
    `_CreateSchema` which takes care of error-verifications and caching.
    This enum type is guaranteed to be a leaf in a type traversal, so there is
    no need for the `visiting` set that `_CreateMessageSchema` uses to detect
    cycles.

    Args:
      descriptor: The protobuf `EnumDescriptor` of the enum type whose schema is
        extracted.

    Returns:
      Nothing, the schema is stored in `self.schema_objs`.
    """
    if self.schema_objs is None:  # Check required by mypy.
      raise AssertionError(
        "The container of OpenAPI type schemas is not initialized."
      )

    enum_schema_obj: EnumSchema = {
      "type": "string",
    }

    if len(descriptor.values) > 0:
      enum_schema_obj["enum"] = (
        tuple([enum_value.name for enum_value in descriptor.values])
      )
      enum_schema_obj["description"] = (
        "\n".join([f"{enum_value.name} == {enum_value.number}"
                   for enum_value in descriptor.values])
      )
    else:
      enum_schema_obj["enum"] = ()

    self.schema_objs[_GetTypeName(descriptor)] = enum_schema_obj

  def _CreateMessageSchema(
      self,
      descriptor: Descriptor,
      visiting: Set[str]
  ) -> None:
    """Creates the OpenAPI schema of a protobuf message.

    This method should generally not be called directly, but rather through
    `_CreateSchema` which takes care of error-verifications and caching.

    Args:
      descriptor: The protobuf `Descriptor` associated with a protobuf message.
      visiting: A set of type names that are in the process of having their
        OpenAPI schemas constructed and have their associated `_Create*Schema`
        call in the current call stack.

    Returns:
      Nothing, the schema is stored in `self.schema_objs`.
    """
    if self.schema_objs is None:  # Check required by mypy.
      raise AssertionError(
        "The container of OpenAPI type schemas is not initialized."
      )

    type_name = _GetTypeName(descriptor)

    properties = dict()
    visiting.add(type_name)

    # Create schemas for the fields' types.
    for field_descriptor in descriptor.fields:
      field_name = field_descriptor.name
      message_descriptor = field_descriptor.message_type # None if not Message.
      enum_descriptor = field_descriptor.enum_type # None if not Enum.
      descriptor = message_descriptor or enum_descriptor

      if descriptor:
        self._CreateSchema(descriptor, visiting)

      properties[field_name] = (
        self._GetReferenceObject(
          _GetTypeName(field_descriptor),
          field_descriptor.label == protobuf2.LABEL_REPEATED)
      )

    visiting.remove(type_name)

    self.schema_objs[type_name] = cast(
      MessageSchema,
      {
        "type": "object",
        "properties": properties,
      }
    )

  def _CreateSchema(
      self,
      cls: Union[Descriptor, FieldDescriptor, EnumDescriptor, Type, int, str],
      visiting: Set[str]
  ) -> None:
    """Create OpenAPI schema from any valid type descriptor or identifier."""
    if self.schema_objs is None:  # Check required by mypy.
      raise AssertionError(
        "The container of OpenAPI type schemas is not initialized."
      )

    if cls is None:
      raise ValueError(f"Trying to extract schema of None.")

    type_name = _GetTypeName(cls)
    # "Primitive" types should be already present in `self.schema_objs`.
    if type_name in self.schema_objs:
      return

    if type_name in visiting:
      # Dependency cycle.
      return

    if isinstance(cls, Descriptor):
      self._CreateMessageSchema(cls, visiting)
      return

    if isinstance(cls, EnumDescriptor):
      self._CreateEnumSchema(cls)
      return

    raise TypeError(f"Don't know how to handle type \"{type_name}\" "
                    f"which is not a protobuf message Descriptor, "
                    f"nor an EnumDescriptor, nor a primitive type.")

  def _CreateSchemas(self) -> None:
    """Create OpenAPI schemas for all the used protobuf types."""

    self.schema_objs = dict()  # Holds OpenAPI representations of types.
    self._AddPrimitiveTypesSchemas()

    # Holds state of types extraction (white/gray nodes).
    visiting: Set[str] = set()
    router_methods = self.router.__class__.GetAnnotatedMethods()
    for method_metadata in router_methods.values():
      args_type = method_metadata.args_type
      if args_type:
        if (
            inspect.isclass(args_type) and
            issubclass(args_type, rdf_structs.RDFProtoStruct)
        ):
          self._CreateSchema(args_type.protobuf.DESCRIPTOR, visiting)
        else:
          self._CreateSchema(args_type, visiting)

      result_type = method_metadata.result_type
      if result_type:
        if (
            inspect.isclass(result_type) and
            issubclass(result_type, rdf_structs.RDFProtoStruct)
        ):
          self._CreateSchema(result_type.protobuf.DESCRIPTOR, visiting)
        else:
          self._CreateSchema(result_type, visiting)

  def _GetReferenceObject(
      self,
      type_name: str,
      is_array: bool = False
  ) -> Union[SchemaReference, ArraySchema]:
    """Get a `Reference Object` that points to a schema definition.

    All types (including protobuf primitives) are expected to have been
    previously defined in the `components` field of the root `OpenAPI Object`
    and are used via OpenAPI references.

    Args:
      type_name: The name of the type for which an OpenAPI `Reference Object`
        will be created and returned.
      is_array: A boolean flag indicating whether the selected type's reference
        object should be wrapped in an OpenAPI array as the items type.

    Returns:
      If the `is_array` argument is set to `False`, then an OpenAPI `Reference
      Object` representing the path to the actual OpenAPI schema definition of
      the selected type.
      If the `is_array` argument is set to `True`, then an OpenAPI array schema
      is constructed that uses for the `items` field an OpenAPI `Reference
      Object` associated with the type's schema.
    """
    if self.schema_objs is None:
      raise AssertionError(
        "The container of OpenAPI type schemas is not initialized."
      )

    reference_obj = {"$ref": f"#/components/schemas/{type_name}"}

    if is_array:
      array_schema: ArraySchema = {
        "type": "array",
        "items": reference_obj
      }
      return array_schema

    return reference_obj

  def _GetParameters(
      self,
      path_params: List[FieldDescriptor],
      query_params: List[FieldDescriptor]
  ) -> List[
    Dict[str, Union[str, bool, SchemaReference, ArraySchema]]
  ]:
    """Create the OpenAPI description of the parameters of a route."""
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

      parameter_obj["schema"] = (
        self._GetReferenceObject(
          _GetTypeName(field_d),
          field_d.label == protobuf2.LABEL_REPEATED
        )
      )

      parameters.append(parameter_obj)

    return parameters

  def _GetRequestBody(
      self,
      body_params: List[FieldDescriptor]
  ) -> Dict[str, Dict]:
    """Create the OpenAPI description of the request body of a route."""
    if not body_params:
      return {}

    properties = dict()
    for field_d in body_params:
      field_name = field_d.name
      properties[field_name] = (
        self._GetReferenceObject(
          _GetTypeName(field_d),
          field_d.label == protobuf2.LABEL_REPEATED
        )
      )

    return {
      "content": {
        "application/json": {
          "schema": {
            "type": "object",
            "properties": properties,
          },
        },
      },
    }

  def _GetResponseObject200(
      self,
      result_type: Union[rdf_structs.RDFProtoStruct, str],
      router_method_name: str
  ) -> Dict[str, Union[str, Dict]]:
    """Create the OpenAPI description of a successful, 200 HTTP response."""
    resp_success_obj: Dict[str, Union[str, Dict]] = dict()

    if result_type:
      if (
          isinstance(result_type, type) and
          issubclass(result_type, rdf_structs.RDFProtoStruct)
      ):
        result_type_name = _GetTypeName(
          cast(rdf_structs.RDFProtoStruct, result_type).protobuf.DESCRIPTOR
        )
      else:
        result_type_name = _GetTypeName(result_type)

      resp_success_obj["description"] = (
        f"The call to the {router_method_name} API method succeeded and it "
        f"returned an instance of {result_type_name}."
      )

      media_obj = {"schema": self._GetReferenceObject(result_type_name)}

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
    """Create the OpenAPI description used by all undescribed HTTP responses."""
    resp_default_obj= {
      "description": f"The call to the {router_method_name} API method did not "
                     f"succeed."
    }

    return resp_default_obj

  def _GetOpenApiVersion(self) -> str:
    """Return the OpenAPI Specification version of the generated description."""
    # TODO: Maybe get the OpenAPI specification version from a config file.
    oas_version = "3.0.3"

    return oas_version

  def _GetInfo(self) -> Dict[str, Union[str, Dict]]:
    """Create the Info Object used by the `info` field."""
    version_dict = version.Version()

    return {
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
    }

  def _GetServers(self) -> List[Dict[str, str]]:
    """Create a list of `Server Object`s used by the `servers` field."""
    return [
      {
        "url": "/",
        "description": "Root path of the GRR API",
      },
    ]

  def _GetComponents(
      self
  ) -> Dict[str, Dict[str, Union[PrimitiveSchema, EnumSchema, MessageSchema]]]:
    """Create the `Components Object` that holds all schema definitions."""
    self._CreateSchemas()
    if self.schema_objs is None:  # Check required by mypy.
      raise AssertionError(
        "The container of OpenAPI type schemas is not initialized."
      )

    # The `Components Object` `components` field of the root `OpenAPI Object`.
    return {
      "schemas": cast(
        Dict[str, Union[PrimitiveSchema, EnumSchema, MessageSchema]],
        self.schema_objs
      )
    }

  def _SeparateFieldsIntoParams(
      self,
      http_method: str,
      path: str,
      args_type: Type[rdf_structs.RDFProtoStruct]
  ) -> Tuple[
    List[FieldDescriptor], List[FieldDescriptor], List[FieldDescriptor]
  ]:
    """Group `FieldDescriptors` of a protobuf message by http params types."""
    field_descriptors = []
    if args_type:
      if not (
          inspect.isclass(args_type) and
          issubclass(args_type, rdf_structs.RDFProtoStruct)
      ):
        raise TypeError("Router method args type is not a RDFProtoStruct "
                        "subclass.")
      field_descriptors = args_type.protobuf.DESCRIPTOR.fields

    # Separate fields into params: path, query and part of the request body.
    path_params_names = set(_GetPathArgsFromPath(path))
    path_params = []
    query_params = []
    body_params = []
    for field_d in field_descriptors:
      if field_d.name in path_params_names:
        path_params.append(field_d)
      elif http_method.upper() in ("GET", "HEAD"):
        query_params.append(field_d)
      else:
        body_params.append(field_d)

    return path_params, query_params, body_params

  def _GetOperationDescription(
      self,
      http_method: str,
      path: str,
      router_method: Any,
  ) -> Dict[str, Any]:
    """Create the OpenAPI `Operation Object` associated with the given args."""

    url_path = (  # Rewrite the path in a URL-friendly format.
      path
        .replace("/", "-")
        .replace("<", "_")
        .replace(">", "_")
        .replace(":", "-")
    )
    path_params, query_params, body_params = (
      self._SeparateFieldsIntoParams(http_method, path, router_method.args_type)
    )

    # The `Operation Object` associated with the current http method.
    operation_obj = {
      "tags": [router_method.category or "NoCategory", ],
      "description": router_method.doc or "No description.",
      "operationId": urlparse.quote(f"{http_method}-{url_path}-"
                                    f"{router_method.name}"),
      "parameters": self._GetParameters(path_params, query_params),
      "responses": {
        "200": (
          self._GetResponseObject200(router_method.result_type,
                                     router_method.name)
        ),
        "default": self._GetResponseObjectDefault(router_method.name),
      },
    }
    if body_params: # Only POST methods should have an associated `requestBody`.
      operation_obj["requestBody"] = self._GetRequestBody(body_params)

    return operation_obj

  def _GetPaths(self) -> Dict[str, Dict]:
    """Create the OpenAPI description of all the routes exposed by the API."""

    # The `Paths Object` `paths` field of the root `OpenAPI Object`.
    paths_obj: DefaultDict[str, Dict] = collections.defaultdict(dict)

    router_methods = self.router.__class__.GetAnnotatedMethods()
    for router_method_name in router_methods:
      router_method = router_methods[router_method_name]
      for http_method, path, strip_root_types in router_method.http_methods:
        normalized_path = _NormalizePath(path)

        # The `Path Object` associated with the current path.
        path_obj = paths_obj[normalized_path]
        path_obj[http_method.lower()] = (
          self._GetOperationDescription(http_method, path, router_method)
        )

    return paths_obj

  def Handle(
      self,
      args: None,
      token: Optional[access_control.ACLToken] = None,
  ) -> ApiGetOpenApiDescriptionResult:
    """Handle requests for the OpenAPI description of the GRR API."""
    result = ApiGetOpenApiDescriptionResult()

    if self.openapi_obj_json is not None:
      result.openapi_description = self.openapi_obj_json
      return result

    openapi_obj = {
      "openapi": self._GetOpenApiVersion(),
      "info": self._GetInfo(),
      "servers": self._GetServers(),
      "components": self._GetComponents(),
      "paths": self._GetPaths(),
    }

    self.openapi_obj_json = json.dumps(openapi_obj)

    result.openapi_description = self.openapi_obj_json
    return result


def _NormalizePathComponent(component: str) -> str:
  """Normalize the given path component to be used in a valid OpenAPI path."""
  if component.startswith("<") and component.endswith(">"):
    component = component[1:-1]
    component = component.split(":")[-1]
    component = f"{{{component}}}"

  return component


def _NormalizePath(path: str) -> str:
  """Keep only fixed parts and parameter names from Werkzeug URL patterns.

  The OpenAPI Specification requires that parameters are surrounded by { } which
  are added in `_NormalizePathComponent`.

  Args:
    path: The path whose representation will be normalized.

  Returns:
    The normalized version of the path argument, which is a valid OpenAPI path,
    with curly brackets around path arguments.
  """
  components = path.split("/")
  normalized_components = [
    _NormalizePathComponent(component) for component in components
  ]

  normalized_path = "/".join(normalized_components)

  return normalized_path


def _GetPathArgsFromPath(path: str) -> List[str]:
  """Extract path parameters from a Werkzeug Rule URL."""
  path_args = []

  components = path.split("/")
  for component in components:
    if component.startswith("<") and component.endswith(">"):
      normalized_component = _NormalizePathComponent(component)
      normalized_component = normalized_component[1:-1]
      path_args.append(normalized_component)

  return path_args


def _GetTypeName(
    cls: Union[Descriptor, FieldDescriptor, EnumDescriptor, Type, int, str],
) -> str:
  """Extract type name from protobuf `Descriptor`/`type`/`int`/`str`."""
  if isinstance(cls, FieldDescriptor):
    if cls.message_type:
      return _GetTypeName(cls.message_type)
    if cls.enum_type:
      return _GetTypeName(cls.enum_type)

    return _GetTypeName(cls.type)

  if isinstance(cls, Descriptor):
    return cls.full_name

  if isinstance(cls, EnumDescriptor):
    return cls.full_name

  if isinstance(cls, type):
    return cls.__name__

  if isinstance(cls, int):  # It's a `protobuf.Descriptor.type` value.
    return cast(str, primitive_types[cls]["name"])

  return str(cls)  # Cover `BinaryStream` and `None`.
