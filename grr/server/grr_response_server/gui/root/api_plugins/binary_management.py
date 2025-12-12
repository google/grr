#!/usr/bin/env python
"""Root-access-level API handlers for binary management."""

from typing import Optional

from grr_response_core import config
from grr_response_core.lib import rdfvalue
from grr_response_core.lib.rdfvalues import crypto as rdf_crypto
from grr_response_core.lib.rdfvalues import structs as rdf_structs
from grr_response_proto.api import config_pb2
from grr_response_proto.api.root import binary_management_pb2
from grr_response_server import access_control
from grr_response_server import signed_binary_utils
from grr_response_server.gui import api_call_context
from grr_response_server.gui import api_call_handler_base


class GrrBinaryNotFoundError(api_call_handler_base.ResourceNotFoundError):
  """Raised when a flow is not found."""


class GrrBinaryIsNotOverwritableError(access_control.UnauthorizedAccess):
  """Raised when one tries to overwrite an existing GRR binary."""


class GrrBinaryIsNotDeletableError(access_control.UnauthorizedAccess):
  """Raised when one tries to delete an existing GRR binary."""


class ApiUploadGrrBinaryArgs(rdf_structs.RDFProtoStruct):
  protobuf = binary_management_pb2.ApiUploadGrrBinaryArgs
  rdf_deps = [
      rdf_crypto.SignedBlob,
  ]


class ApiDeleteGrrBinaryArgs(rdf_structs.RDFProtoStruct):
  protobuf = binary_management_pb2.ApiDeleteGrrBinaryArgs
  rdf_deps = []


def _GetBinaryRootUrn(
    binary_type: config_pb2.ApiGrrBinary.Type,
) -> rdfvalue.RDFURN:
  if binary_type == config_pb2.ApiGrrBinary.Type.PYTHON_HACK:
    return signed_binary_utils.GetAFF4PythonHackRoot()
  elif binary_type == config_pb2.ApiGrrBinary.Type.EXECUTABLE:
    return signed_binary_utils.GetAFF4ExecutablesRoot()
  else:
    raise ValueError("Invalid binary type: %s" % binary_type)


class ApiUploadGrrBinaryHandler(api_call_handler_base.ApiCallHandler):
  """Uploads GRR binary to a given path."""

  proto_args_type = binary_management_pb2.ApiUploadGrrBinaryArgs

  def Handle(
      self,
      args: binary_management_pb2.ApiUploadGrrBinaryArgs,
      context: Optional[api_call_context.ApiCallContext] = None,
  ) -> None:
    if not args.path:
      raise ValueError("Invalid binary path: %s" % args.path)

    root_urn = _GetBinaryRootUrn(args.type)
    urn = root_urn.Add(args.path)

    # If GRR binaries are readonly, check if a binary with the given
    # name and type exists and raise if it does.
    if config.CONFIG["Server.grr_binaries_readonly"]:
      try:
        signed_binary_utils.FetchBlobsForSignedBinaryByURN(urn)
        raise GrrBinaryIsNotOverwritableError(
            f"GRR binary ({args.path}, {args.type}) can't be overwritten: "
            "all binaries are read-only.")
      except signed_binary_utils.SignedBinaryNotFoundError:
        pass

    signed_binary_utils.WriteSignedBinaryBlobs(urn, list(args.blobs))


class ApiDeleteGrrBinaryHandler(api_call_handler_base.ApiCallHandler):
  """Deletes GRR binary with a given type and path."""

  proto_args_type = binary_management_pb2.ApiDeleteGrrBinaryArgs

  def Handle(
      self,
      args: binary_management_pb2.ApiDeleteGrrBinaryArgs,
      context: Optional[api_call_context.ApiCallContext] = None,
  ) -> None:
    if not args.path:
      raise ValueError("Invalid binary path: %s" % args.path)

    # We do not allow deleting GRR binaries if the readonly configuration
    # flag is set.
    if config.CONFIG["Server.grr_binaries_readonly"]:
      raise GrrBinaryIsNotDeletableError(
          f"GRR binary ({args.path}, {args.type}) can't be deleted: "
          "all binaries are read-only.")

    root_urn = _GetBinaryRootUrn(args.type)
    try:
      signed_binary_utils.DeleteSignedBinary(root_urn.Add(args.path))
    except signed_binary_utils.SignedBinaryNotFoundError:
      raise GrrBinaryNotFoundError(
          "No binary with type=%s and path=%s was found." %
          (args.type, args.path))
