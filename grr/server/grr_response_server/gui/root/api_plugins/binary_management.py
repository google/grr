#!/usr/bin/env python
"""Root-access-level API handlers for binary management."""

from grr.lib.rdfvalues import crypto as rdf_crypto
from grr.lib.rdfvalues import structs as rdf_structs
from grr_response_proto.api.root import binary_management_pb2
from grr.server.grr_response_server import aff4
from grr.server.grr_response_server import data_store
from grr.server.grr_response_server.aff4_objects import collects
from grr.server.grr_response_server.gui import api_call_handler_base
from grr.server.grr_response_server.gui.api_plugins import config as api_config


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
    return aff4.FACTORY.GetPythonHackRoot()
  elif binary_type == api_config.ApiGrrBinary.Type.EXECUTABLE:
    return aff4.FACTORY.GetExecutablesRoot()
  else:
    raise ValueError("Invalid binary type: %s" % binary_type)


class ApiUploadGrrBinaryHandler(api_call_handler_base.ApiCallHandler):
  """Uploads GRR binary to a given path."""

  args_type = ApiUploadGrrBinaryArgs

  def Handle(self, args, token=None):
    if not args.path:
      raise ValueError("Invalid binary path: %s" % args.path)

    root_urn = _GetBinaryRootUrn(args.type)
    urn = root_urn.Add(args.path)

    aff4.FACTORY.Delete(urn, token=token)
    with data_store.DB.GetMutationPool() as pool:
      with aff4.FACTORY.Create(
          urn,
          collects.GRRSignedBlob,
          mode="w",
          mutation_pool=pool,
          token=token) as fd:
        for blob in args.blobs:
          fd.Add(blob, mutation_pool=pool)


class ApiDeleteGrrBinaryHandler(api_call_handler_base.ApiCallHandler):
  """Deletes GRR binary with a given type and path."""

  args_type = ApiDeleteGrrBinaryArgs

  def Handle(self, args, token=None):
    if not args.path:
      raise ValueError("Invalid binary path: %s" % args.path)

    root_urn = _GetBinaryRootUrn(args.type)
    urn = root_urn.Add(args.path)

    # Check that the binary exists.
    try:
      aff4.FACTORY.Open(urn, aff4_type=aff4.AFF4Stream, token=token)
    except IOError:
      raise GrrBinaryNotFoundError(
          "No binary with type=%s and path=%s was found." % (args.type,
                                                             args.path))

    aff4.FACTORY.Delete(urn, token=token)
