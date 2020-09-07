#!/usr/bin/env python
# Lint as: python3
"""A module with API methods related to the GRR metadata."""
import json
import inspect
import collections

from urllib import parse as urlparse
from typing import Optional, cast
from typing import Type, TypeVar, Any, Union
from typing import Iterable, Collection
from typing import Tuple, List, Set
from typing import Dict, DefaultDict
from typing import NamedTuple

from functools import cmp_to_key

from google.protobuf.descriptor import Descriptor
from google.protobuf.descriptor import EnumDescriptor
from google.protobuf.descriptor import FieldDescriptor
from google.protobuf.descriptor import OneofDescriptor

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
DescribedSchema = Dict[str,
                       Union[str, List[SchemaReference], List[ArraySchema]]]
Schema = Union[PrimitiveSchema, EnumSchema, MessageSchema, ArraySchema]
PrimitiveDescription = Dict[str, Union[str, PrimitiveSchema]]
TypeHinter = Union[Descriptor, FieldDescriptor, EnumDescriptor, Type, int, str]


class KeyValueDescriptor(NamedTuple):
  """A named tuple for `protobuf.map`'s `key` and `value` `FieldDescriptor`s."""
  key: FieldDescriptor
  value: FieldDescriptor


class RouteInfo(NamedTuple):
  """A named tuple for the lists of route components and path arguments."""
  # A list of the HTTP method and the components of a URL path.
  route_comps: List[str]
  # A list of path components that represent required path parameters.
  req_path_params_comps: List[str]
  # A list of path components that represent optional path parameters.
  opt_path_params_comps: List[str]


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
  },
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
      raise AssertionError("OpenAPI type schemas not initialized.")

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
      raise AssertionError("OpenAPI type schemas not initialized.")

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
      visiting: Set[str],
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
      raise AssertionError("OpenAPI type schemas not initialized.")

    type_name = _GetTypeName(descriptor)

    properties = dict()
    visiting.add(type_name)

    # Create schemas for the fields' types.
    for field_descriptor in descriptor.fields:
      field_name = field_descriptor.name
      self._CreateSchema(field_descriptor, visiting)

      properties[field_name] = self._GetDescribedSchema(field_descriptor)

    visiting.remove(type_name)

    self.schema_objs[type_name] = cast(
      MessageSchema,
      {
        "type": "object",
        "properties": properties,
      }
    )

  def _CreateMapFieldSchema(
      self,
      field_descriptor: FieldDescriptor,
      visiting: Set[str],
  ) -> None:
    """Creates the OpenAPI schema of a `protobuf.map` field type.

    This method should generally not be called directly, but rather through
    `_CreateSchema` which takes care of error-verifications and caching. The
    OpenAPI Specification allows only maps with strings as keys, so, as a
    workaround, we state the actual key type in the `description` fields of the
    **schemas of the properties/parameters** that use this type (in order to be
    displayed by documentation generation tools, see `_GetDescribedSchema`).
    A `description` field is also added by this method in the schema definition
    which will be added to the `Components Object` of the root `OpenAPI Object`
    for more clarity when reading the generated description of the components.

    Args:
      field_descriptor: The protobuf `FieldDescriptor` associated with a
        protobuf field.
      visiting: A set of type names that are in the process of having their
        OpenAPI schemas constructed and have their associated `_Create*Schema`
        call in the current call stack.

    Returns:
      Nothing, the schema is stored in `self.schema_objs`.
    """
    if self.schema_objs is None:  # Check required by mypy.
      raise AssertionError("OpenAPI type schemas not initialized.")

    if field_descriptor is None:  # Check required by mypy.
      raise AssertionError(f"`field_descriptor` is None.")

    type_name: str = _GetTypeName(field_descriptor)
    visiting.add(type_name)

    key_value_d = _GetMapFieldKeyValueTypes(field_descriptor)
    if key_value_d is None:
      raise AssertionError(f"`field_descriptor` doesn't have a map type.")

    key_type_name = _GetTypeName(key_value_d.key)
    value_type_name = _GetTypeName(key_value_d.value)

    # pylint: disable=line-too-long
    # `protobuf.map` key types can be only a subset of the primitive types [1],
    # so there is definitely no composite key type to further visit, but the
    # value type "can be any type except another map" [1] or an array [2].
    #
    # [1]: https://developers.google.com/protocol-buffers/docs/proto#maps
    # [2]: https://developers.google.com/protocol-buffers/docs/reference/proto2-spec#map_field
    # pylint: enable=line-too-long
    self._CreateSchema(key_value_d.value, visiting)

    visiting.remove(type_name)

    self.schema_objs[type_name] = cast(
      Dict[str, Union[str, SchemaReference]],
      {
        "description": f"This is a map with real key type=\"{key_type_name}\" "
                       f"and value type=\"{value_type_name}\"",
        "type": "object",
        "additionalProperties": _GetReferenceObject(value_type_name),
      }
    )

  def _CreateSchema(
      self,
      cls: Optional[TypeHinter],
      visiting: Set[str],
  ) -> None:
    """Create OpenAPI schema from any valid type descriptor or identifier."""
    if self.schema_objs is None:  # Check required by mypy.
      raise AssertionError("OpenAPI type schemas not initialized.")

    if cls is None:
      raise ValueError(f"Trying to extract schema of None.")

    type_name = _GetTypeName(cls)
    # "Primitive" types should be already present in `self.schema_objs`.
    if type_name in self.schema_objs:
      return

    if type_name in visiting:
      # Dependency cycle.
      return

    if isinstance(cls, FieldDescriptor):
      if _IsMapField(cls):
        self._CreateMapFieldSchema(cls, visiting)
        return

      descriptor = cls.message_type or cls.enum_type
      if descriptor:
        self._CreateSchema(descriptor, visiting)
      # else, this field is of a primitive type whose schema is already created.

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

  def _GetDescribedSchema(
      self,
      field_descriptor: FieldDescriptor,
  ) -> Union[SchemaReference, ArraySchema, DescribedSchema]:
    """Wrap a type schema in a dictionary with a `description` field, if needed.

    This function takes into consideration the fact that the a message field
    might have a protobuf type that is not completely supported by the OpenAPI
    Specification (such as `protobuf.oneof` or `protobuf.map`) and wraps the
    `Reference Object` or the OpenAPI array accordingly in order to include a
    description of the complete semantics of the type.

    Args:
      field_descriptor: The protobuf `FieldDescriptor` associated with the
        target field.

    Returns:
      If the schema of the field does not require any description to explain the
      semantics, then a normal schema or reference, else, a dictionary that
      includes a `description` entry along the `Reference Object` or schema.
    """
    if self.schema_objs is None:  # Check required by mypy.
      raise AssertionError("OpenAPI type schemas not initialized.")

    type_name = _GetTypeName(field_descriptor)
    containing_oneof: OneofDescriptor = field_descriptor.containing_oneof
    description = ""
    array_schema = None
    reference_obj = None

    # Get the array schema or the `Reference Object`.
    if (
        field_descriptor.label == protobuf2.LABEL_REPEATED and
        not _IsMapField(field_descriptor)
    ):
      array_schema = _GetArraySchema(type_name)
    else:
      reference_obj = _GetReferenceObject(type_name)

    # Build the description.
    # `protobuf.oneof` related description.
    # The semantic of `protobuf.oneof` is not currently supported by the
    # OpenAPI Specification. See this GitHub issue [1] for more details.
    #
    # [1]: github.com/google/grr/issues/822
    if containing_oneof is not None:
      if description:
        description += " "

      description += (
        f"This field is part of the \"{containing_oneof.name}\" oneof. "
        f"Only one field per oneof should be present."
      )

    # `protobuf.map` related description.
    if _IsMapField(field_descriptor):
      if description:
        description += " "

      map_type_schema = self.schema_objs[type_name]
      description += cast(
        str, map_type_schema.get("description", "")
      )

    # The following `allOf` is required to display the description by
    # documentation generation tools because the OAS specifies that there
    # should not be any sibling properties to a `$ref`. This is the
    # workaround proposed by the ReDoc community [1].
    #
    # [1]: github.com/Redocly/redoc/issues/453#issuecomment-420898421
    if description:
      return cast(
        DescribedSchema,
        {
          "description": description,
          "allOf": [reference_obj or array_schema],
        }
      )

    if reference_obj is not None:
      return reference_obj
    elif array_schema is not None:  # Check required by mypy.
      return array_schema

    raise AssertionError(  # Required by mypy.
      "No array schema nor `Reference Object` were created."
    )

  def _GetParameters(
      self,
      required_path_params: Iterable[FieldDescriptor],
      optional_path_params: Iterable[FieldDescriptor],
      query_params: Iterable[FieldDescriptor],
  ) -> List[
    Dict[str, Union[str, bool, SchemaReference, ArraySchema]]
  ]:
    """Create the OpenAPI description of the parameters of a route."""
    parameters = []

    req_path_params_set = set(required_path_params)
    opt_path_params_set = set(optional_path_params)
    query_params_set = set(query_params)
    for field_d in req_path_params_set | opt_path_params_set | query_params_set:
      parameter_obj = {"name": field_d.name}
      if field_d in req_path_params_set:
        parameter_obj["in"] = "path"
        parameter_obj["required"] = True
      elif field_d in opt_path_params_set:
        parameter_obj["in"] = "path"
      else:
        parameter_obj["in"] = "query"

      parameter_obj["schema"] = self._GetDescribedSchema(field_d)

      parameters.append(parameter_obj)

    return parameters

  def _GetRequestBody(
      self,
      body_params: Iterable[FieldDescriptor],
  ) -> Dict[str, Dict]:
    """Create the OpenAPI description of the request body of a route."""
    if not body_params:
      return {}

    properties: (
      Dict[str, Union[SchemaReference, ArraySchema, DescribedSchema]]
    ) = dict()
    for field_d in body_params:
      field_name = field_d.name
      properties[field_name] = self._GetDescribedSchema(field_d)

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
      router_method_name: str,
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

      media_obj = {"schema": _GetReferenceObject(result_type_name)}

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
      router_method_name: str,
  ) -> Dict[str, str]:
    """Create the OpenAPI description used by all undescribed HTTP responses."""
    resp_default_obj= {
      "description": f"The call to the {router_method_name} API method did not "
                     f"succeed.",
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
      ),
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
      self,
  ) -> Dict[str, Dict[str, Union[PrimitiveSchema, EnumSchema, MessageSchema]]]:
    """Create the `Components Object` that holds all schema definitions."""
    self._CreateSchemas()
    if self.schema_objs is None:  # Check required by mypy.
      raise AssertionError("OpenAPI type schemas not initialized.")

    # The `Components Object` `components` field of the root `OpenAPI Object`.
    return {
      "schemas": cast(
        Dict[str, Union[PrimitiveSchema, EnumSchema, MessageSchema]],
        self.schema_objs
      ),
    }

  def _SeparateFieldsIntoParams(
      self,
      http_method: str,
      path: str,
      args_type: Type[rdf_structs.RDFProtoStruct],
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
    path_params_names = set(_GetPathParamsFromPath(path))
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
      required_path_params: Iterable[FieldDescriptor],
      optional_path_params: Iterable[FieldDescriptor],
      query_params: Iterable[FieldDescriptor],
      body_params: Iterable[FieldDescriptor],
  ) -> Dict[str, Any]:
    """Create the OpenAPI `Operation Object` associated with the given args."""

    url_path = (  # Rewrite the path in a URL-friendly format.
      path
        .replace("/", "-")
        .replace("<", "_")
        .replace(">", "_")
        .replace(":", "-")
    )

    # The `Operation Object` associated with the current http method.
    operation_obj = {
      "tags": [router_method.category or "NoCategory"],
      "description": router_method.doc or "No description.",
      "operationId": urlparse.quote(f"{http_method}-{url_path}-"
                                    f"{router_method.name}"),
      "parameters": self._GetParameters(
        required_path_params, optional_path_params, query_params
      ),
      "responses": {
        "200": (
          self._GetResponseObject200(router_method.result_type,
                                     router_method.name)
        ),
        "default": self._GetResponseObjectDefault(router_method.name),
      },
    }
    # Only POST methods should have an associated `requestBody`.
    if body_params:
      operation_obj["requestBody"] = self._GetRequestBody(body_params)

    return operation_obj

  def _GetPaths(self) -> Dict[str, Dict]:
    """Create the OpenAPI description of all the routes exposed by the API."""

    # The `Paths Object` `paths` field of the root `OpenAPI Object`.
    paths_obj: DefaultDict[str, Dict] = collections.defaultdict(dict)

    router_methods = self.router.__class__.GetAnnotatedMethods()
    for router_method in router_methods.values():
      # To extract optional path parameters, all the routes associated with this
      # router method must be analysed and grouped.
      ungrouped_routes = []
      for http_method, path, strip_root_types in router_method.http_methods:
        path_components = path.split("/")
        ungrouped_routes.append([http_method] + path_components)

      grouped_routes = _GetGroupedRoutes(ungrouped_routes)
      for route_info in grouped_routes:
        # Components (comps) are URL components, including Werkzeug path
        # arguments such as `<client_id>` or `<path:file_path>`.
        route_comps, req_path_params_comps, opt_path_params_comps = route_info
        http_method = route_comps[0]
        path = "/".join(route_comps[1:])

        # Separate the route parameters into path params, query params and
        # request body params.
        path_params, query_params, body_params = self._SeparateFieldsIntoParams(
          http_method, path, router_method.args_type
        )

        # Separate the path params into required and optional path params.
        # First, extract path params names by normalizing the Werkzeug path args
        # components to OpenAPI path args and remove the surrounding brackets.
        req_path_params_names = [
          _NormalizePathComponent(comp)[1:-1] for comp in req_path_params_comps
        ]
        opt_path_params_names = [
          _NormalizePathComponent(comp)[1:-1] for comp in opt_path_params_comps
        ]
        req_path_params = []
        opt_path_params = []
        for path_param in path_params:
          if path_param.name in req_path_params_names:
            req_path_params.append(path_param)
          elif path_param.name in opt_path_params_names:
            opt_path_params.append(path_param)
          else:
            raise AssertionError(
              f"Path parameter {path_param.name} was not classified as "
              f"required/optional."
            )

        normalized_path = _NormalizePath(path)
        path_obj = paths_obj[normalized_path]
        path_obj[http_method.lower()] = (
          self._GetOperationDescription(
            http_method, normalized_path, router_method,
            req_path_params, opt_path_params, query_params, body_params
          )
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


def _GetPathParamsFromPath(path: str) -> List[str]:
  """Extract path parameters from a Werkzeug Rule URL."""
  path_params = []

  components = path.split("/")
  for component in components:
    if component.startswith("<") and component.endswith(">"):
      normalized_component = _NormalizePathComponent(component)
      normalized_component = normalized_component[1:-1]
      path_params.append(normalized_component)

  return path_params


def _GetTypeName(cls: Optional[TypeHinter]) -> str:
  """Extract type name from protobuf `Descriptor`/`type`/`int`/`str`."""
  if isinstance(cls, FieldDescriptor):
    if _IsMapField(cls):
      map_type_name = _GetTypeName(cls.message_type)
      if map_type_name.endswith("Entry"):
        map_type_name = map_type_name[:-5]

      key_value_d = _GetMapFieldKeyValueTypes(cls)
      if key_value_d is None:
        raise AssertionError(f"cls is not a map FieldDescriptor")

      key_type_name = _GetTypeName(key_value_d.key)
      value_type_name = _GetTypeName(key_value_d.value)

      return f"{map_type_name}Map_{key_type_name}:{value_type_name}"

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


def _GetReferenceObject(type_name: str) -> SchemaReference:
  """Get a `Reference Object` that points to a schema definition.

  All types (including protobuf primitives) are expected to have been
  previously defined in the `components` field of the root `OpenAPI Object`
  and are used via OpenAPI references.

  Args:
    type_name: The name of the type for which an OpenAPI `Reference Object`
      will be created and returned.

  Returns:
    An OpenAPI `Reference Object` representing the path to the actual OpenAPI
    schema definition of the selected type.
  """
  return {
    "$ref": f"#/components/schemas/{type_name}",
  }


def _GetArraySchema(items_type_name: str) -> ArraySchema:
  """Get the schema of an array with items of the given type."""
  return {
    "type": "array",
    "items": _GetReferenceObject(items_type_name),
  }


def _GetMapEntryTypeName(field_name: str) -> str:
  """Extract the name of the associated map type from a field's name."""
  capitalized_name_components = map(str.capitalize, field_name.split("_"))

  return f"{''.join(capitalized_name_components)}Entry"


def _GetMapFieldKeyValueTypes(
    field_descriptor: FieldDescriptor,
) -> Optional[KeyValueDescriptor]:
  """Get `FieldDescriptor`s for the types of a map field, if the field is a map.

  `protobuf.map` fields are compiled as repeated fields of newly created types
  that represent a map entry (i.e. auxiliary protobuf messages with a `key` and
  `value` field). This function verifies that all the signs of a compiled
  `protobuf.map` field are present for the current `FieldDescriptor` and, if
  this field is actually a `protobuf.map`, it returns the `key` and `value`
  `FieldDescriptor`s.

  Args:
    field_descriptor: The protobuf `FieldDescriptor` whose type is checked if it
      is a map and whose type's associated `key` and `value` `FieldDescriptor`s
      are returned.

  Returns:
    A `KeyValueDescriptor` named tuple consisting of the `key` and `value`
    `FieldDescriptor`s (in this order) extracted from the given
    `FieldDescriptor`'s map entry message type, or `None` if the given
    `FieldDescriptor` does not describe a map field.
  """
  if field_descriptor.label != protobuf2.LABEL_REPEATED:
    return None

  entry_descriptor: Optional[Descriptor] = field_descriptor.message_type
  if entry_descriptor is None:
    return None

  if _GetMapEntryTypeName(field_descriptor.name) != entry_descriptor.name:
    return None

  if len(entry_descriptor.fields) != 2:
    return None

  if (
      entry_descriptor.fields[0].name == "key" and
      entry_descriptor.fields[1].name == "value"
  ):
    return KeyValueDescriptor(
      key=entry_descriptor.fields[0], value=entry_descriptor.fields[1]
    )

  if (
      entry_descriptor.fields[0].name == "value" and
      entry_descriptor.fields[1].name == "key"
  ):
    return KeyValueDescriptor(
      key=entry_descriptor.fields[1], value=entry_descriptor.fields[0]
    )

  return None


def _IsMapField(field_descriptor: FieldDescriptor) -> bool:
  """Checks that a `FieldDescriptor` is of a map type."""
  return _GetMapFieldKeyValueTypes(field_descriptor) is not None


ComponentTrieNodeSubclass = TypeVar(
  "ComponentTrieNodeSubclass", bound="ComponentTrieNode"
)

# TODO: Remove Trie class and Trie implementation-based functions / methods.
class ComponentTrieNode:
  def __init__(
      self,
      component: str,
      parent_path: str,
  ) -> None:
    self.component = component
    if parent_path:
      self.path = f"{parent_path}/{component}"
    else:
      self.path = component
    self.is_path_arg = component.startswith("<") and component.endswith(">")
    self.is_route_end = False
    self.children: Dict[str, ComponentTrieNode] = dict()

  @classmethod
  def FromRoutes(
      cls: Type[ComponentTrieNodeSubclass],
      routes: Iterable[Iterable[str]]
  ) -> ComponentTrieNodeSubclass:
    """Creates a trie of routes components and returns the root of the trie."""
    root = cls("", "")

    for route in routes:
      curr_node: ComponentTrieNode = root

      for component in route:
        if component not in curr_node.children:
          curr_node.children[component] = (
            cls(component, curr_node.path)
          )
        curr_node = curr_node.children[component]

      curr_node.is_route_end = True

    return root


def _GroupRoutesByStem(
    curr_node: ComponentTrieNode,
    path_params: List[ComponentTrieNode],
    stem_node: Optional[ComponentTrieNode],
    grouped_routes_stems: Dict[str, Dict],
) -> None:
  """Group routes with the same stem and extract required/optional path args."""
  new_stem_node = stem_node

  if curr_node.is_path_arg:
    path_params.append(curr_node)

  if curr_node.is_route_end:
    if stem_node is None:
      new_stem_node = curr_node
    elif curr_node.is_path_arg:
      grouped_routes_stems[stem_node.path]["optional"].append(curr_node)
    else:
      # It's a terminal fixed URL component => new route which might have some
      # optional path parameters.
      new_stem_node = curr_node
  else:
    # Non-terminal components that are waiting for components farther to the
    # right to end the URL they are part of. The path parameters in this
    # situation will be marked as required.
    new_stem_node = None

  if new_stem_node is not None and new_stem_node != stem_node:
    # We've detected a new route end with its associated fixed stem.
    grouped_routes_stems[new_stem_node.path] = {
      "required": path_params.copy(),
      "optional": [],
    }

  for child in curr_node.children.values():
    _GroupRoutesByStem(child, path_params, new_stem_node, grouped_routes_stems)

  # We'll go back to the parent of this node, so we remove the current path arg
  # from the list of path args, as we will next go on a diferent branch/path in
  # the trie.
  if curr_node.is_path_arg:
    path_params.pop()


def _CompareComponentsCollections(
    comps_1: Collection[str],
    comps_2: Collection[str],
) -> int:
  """Function to order two collections of route components lexicographically."""
  for comp_1, comp_2 in zip(comps_1, comps_2):
    if comp_1 < comp_2:
      return -1
    if comp_1 > comp_2:
      return 1

  if len(comps_1) < len(comps_2):
    return -1
  if len(comps_1) > len(comps_2):
    return 1

  return 0


class UngroupedRoute(NamedTuple):
  """A named tuple for storing routes and their state during route grouping."""
  route: Collection[str]
  processed: bool


def _IsExtension(
    longer_route: List[str],
    smaller_route: List[str],
) -> bool:
  len_longer = len(longer_route)
  len_smaller = len(smaller_route)
  # The longer child route is expected to have exactly one more path component.
  if len_longer - len_smaller != 1:
    return False
  # And that single extra path component must be a path parameter.
  if not(longer_route[-1].startswith("<") and longer_route[-1].endswith(">")):
    return False

  # Verify that the rest of the components are the same.
  for comp_longer, comp_smaller in zip(longer_route, smaller_route):
    if comp_longer != comp_smaller:
      return False

  return True


def _ExtractPathParamsFromRouteList(route_comps: Collection[str]) -> Set[str]:
  path_params = set()
  for comp in route_comps:
    if comp.startswith("<") and comp.endswith(">"):
      path_params.add(comp)

  return path_params


def _GetGroupedRoutes(routes: List[Collection[str]]) -> List[RouteInfo]:
  """Get a list of routes and their required and optional path parameters."""
  routes.sort(key=cmp_to_key(_CompareComponentsCollections))
  ungrouped_routes = [
    UngroupedRoute(route=route, processed=False) for route in routes
  ]
  num_routes = len(ungrouped_routes)

  grouped_routes = []
  for i_stem_route in range(num_routes):
    stem_route, stem_route_processed = ungrouped_routes[i_stem_route]
    if stem_route_processed:
      continue

    parent_route = stem_route
    for i_child_route in range(i_stem_route + 1, num_routes):
      child_route, child_route_processed = ungrouped_routes[i_child_route]

      if child_route_processed:
        continue
      ungrouped_routes[i_child_route].processed = True

      if _IsExtension(child_route, parent_route):
        parent_route = child_route

    required_path_params = _ExtractPathParamsFromRouteList(stem_route)
    optional_path_params = (
        _ExtractPathParamsFromRouteList(parent_route) - required_path_params
    )

    grouped_routes.append(
      RouteInfo(
        route_comps=parent_route,
        req_path_params_comps=list(required_path_params),
        opt_path_params_comps=list(optional_path_params),
      )
    )

  return grouped_routes
