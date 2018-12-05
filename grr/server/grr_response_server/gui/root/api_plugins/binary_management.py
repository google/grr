#!/usr/bin/env python
"""Root-access-level API handlers for binary management."""
from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

from grr_response_core.lib.rdfvalues import crypto as rdf_crypto
from grr_response_core.lib.rdfvalues import structs as rdf_structs
from grr_response_proto.api.root import binary_management_pb2
from grr_response_server import signed_binary_utils
from grr_response_server.gui import api_call_handler_base
from grr_response_server.gui.api_plugins import config as api_config


class GrrBinaryNotFoundError(api_call_handler_base.ResourceNotFoundError):
  """Raised when a flow is not found."""


class ApiUploadGrrBinaryArgs(rdf_structs.RDFProtoStruct):
  protobuf = binary_management_pb2.ApiUploadGrrBinaryArgs
  rdf_deps = [
      rdf_crypto.SignedBlob,
  ]


class ApiDeleteGrrBinaryArgs(rdf_structs.RDFProtoStruct):
  protobuf = binary_management_pb2.ApiDeleteGrrBinaryArgs
  rdf_deps = []


def _GetBinaryRootUrn(binary_type):
  if binary_type == api_config.ApiGrrBinary.Type.PYTHON_HACK:
    return signed_binary_utils.GetAFF4PythonHackRoot()
  elif binary_type == api_config.ApiGrrBinary.Type.EXECUTABLE:
    return signed_binary_utils.GetAFF4ExecutablesRoot()
  else:
    raise ValueError("Invalid binary type: %s" % binary_type)


class ApiUploadGrrBinaryHandler(api_call_handler_base.ApiCallHandler):
  """Uploads GRR binary to a given path."""

  args_type = ApiUploadGrrBinaryArgs

  def Handle(self, args, token=None):
    if not args.path:
      raise ValueError("Invalid binary path: %s" % args.path)

    root_urn = _GetBinaryRootUrn(args.type)
    signed_binary_utils.WriteSignedBinaryBlobs(
        root_urn.Add(args.path), list(args.blobs), token=token)


class ApiDeleteGrrBinaryHandler(api_call_handler_base.ApiCallHandler):
  """Deletes GRR binary with a given type and path."""

  args_type = ApiDeleteGrrBinaryArgs

  def Handle(self, args, token=None):
    if not args.path:
      raise ValueError("Invalid binary path: %s" % args.path)

    root_urn = _GetBinaryRootUrn(args.type)
    try:
      signed_binary_utils.DeleteSignedBinary(
          root_urn.Add(args.path), token=token)
    except signed_binary_utils.SignedBinaryNotFoundError:
      raise GrrBinaryNotFoundError(
          "No binary with type=%s and path=%s was found." % (args.type,
                                                             args.path))
