#!/usr/bin/env python
# Lint as: python3
"""A module with API methods related to the GRR metadata."""
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
