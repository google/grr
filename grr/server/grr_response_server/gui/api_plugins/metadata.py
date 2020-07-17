#!/usr/bin/env python
# Lint as: python3
"""A module with API methods related to the GRR metadata."""
import json

from typing import Optional

from grr_response_core import version
from grr_response_core.lib.rdfvalues import structs as rdf_structs
from grr_response_proto.api import metadata_pb2
from grr_response_server import access_control
from grr_response_server.gui import api_call_handler_base


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

  def __init__(self, router):
    self.router = router

  def _GetPathArgsFromPath(self, path: str) -> [str]:
    """Extract path parameters from a Werkzeug Rule URL."""
    path_args = []

    nodes = path.split("/")
    for node in nodes:
      if len(node) > 0 and node[0] == '<' and node[-1] == '>':
        node = node[1:-1]
        arg = node.split(":")[-1] # Werkzeug type converter might be specified.
        path_args.append(arg)

    return path_args

  def Handle(
      self,
      args: None,
      token: Optional[access_control.ACLToken] = None,
  ) -> ApiGetOpenApiDescriptionResult:
    """Handles requests for getting the OpenAPI description of the GRR API."""

    result = ApiGetOpenApiDescriptionResult()

    oas_version = "3.0.3" #TODO: Don't hard code it.

    # The main OpenAPI description object.
    root_obj = dict()
    root_obj["openapi"] = oas_version

    # The Info Object "info" field.
    info_obj = dict()
    info_obj["title"] = "GRR Rapid Response API"
    info_obj["description"] = "GRR Rapid Response is an incident response " \
                              "framework focused on remote live forensics."

    contact_obj = dict()
    contact_obj["name"] = "GRR GitHub Repository"
    contact_obj["url"] = "https://github.com/google/grr"
    info_obj["contact"] = contact_obj

    license_obj = dict()
    license_obj["name"] = "Apache 2.0"
    license_obj["url"] = "http://www.apache.org/licenses/LICENSE-2.0"
    info_obj["license"] = license_obj

    version_dict = version.Version()
    info_obj["version"] = f"{version_dict['major']}.{version_dict['minor']}." \
                          f"{version_dict['revision']}." \
                          f"{version_dict['release']}"
    root_obj["info"] = info_obj

    # The Paths Object "paths" field.
    paths_obj = dict()

    router_methods = self.router.__class__.GetAnnotatedMethods()
    for router_method in router_methods.values():
      for http_method, path, strip_root_types in router_method.http_methods:
        if path not in paths_obj:
          paths_obj[path] = dict()

        # The Path Object associated with the current path.
        path_obj = paths_obj[path]

        # The Operation Object associated with the current http method.
        operation_obj = dict()
        operation_obj["tags"] = [router_method.category]
        operation_obj["description"] = router_method.doc
        operation_obj["operationId"] = f"{http_method}_{path}_" \
                                       f"{router_method.name}"
        operation_obj["parameters"] = []
        if router_method.args_type:
          type_infos = router_method.args_type().type_infos
        else:
          type_infos = []
        path_args = self._GetPathArgsFromPath(path)
        path_args = set(path_args)

        # TODO: Instead of defining parameter schemas here (and potentially
        # duplicating definitions, do it in two passes of the method arguments:
        # first define all the schemas in the "components" field of the OpenAPI
        # object (root) and then, in the second pass, just reference the
        # required types.
        body_parameters = []
        for type_info in type_infos:
          # The Parameter Object used to describe the parameter.
          parameter_obj = dict()
          parameter_obj["name"] = type_info.name
          if type_info.name in path_args:
            parameter_obj["in"] = "path"
            # TODO: Check how Python's True gets serialized to JSON.
            parameter_obj["required"] = True
          elif http_method.upper() in ["GET", "HEAD"]:
            parameter_obj["in"] = "query"
          else:
            body_parameters.append(type_info)
            continue

          # The Schema Object used to describe the type of the parameter.
          schema_obj = dict()
          schema_obj["type"] = "string"
          parameter_obj["schema"] = schema_obj
          # TODO: Investigate more about style.
          parameter_obj["style"] = "simple"

          operation_obj["parameters"].append(parameter_obj)

        if body_parameters:
          # The Request Body Object which describes data sent in the message
          # body.
          request_body_obj = dict()
          request_body_obj["content"] = dict()
          # TODO: Not all requests sending a message body will use JSON.
          # They might use multipart/form-data and send a file?
          media_obj = dict()
          schema_obj = dict()
          schema_obj["type"] = "object"
          schema_obj["properties"] = dict()
          for type_info in body_parameters:
            schema_obj["properties"][type_info.name] = {"type": "string"}

          media_obj["schema"] = schema_obj
          request_body_obj["content"]["application/json"] = media_obj
          request_body_obj["content"]["multipart/form-data"] = media_obj

          operation_obj["requestBody"] = request_body_obj


        path_obj[http_method.lower()] = operation_obj

    root_obj["paths"] = paths_obj

    result.openapi_description = json.dumps(root_obj)

    return result
