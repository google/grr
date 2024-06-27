#!/usr/bin/env python
"""A module with API handlers related to the YARA memory scanning."""

from typing import Optional

from grr_response_core.lib.rdfvalues import structs as rdf_structs
from grr_response_proto.api import yara_pb2
from grr_response_server import data_store
from grr_response_server.gui import api_call_context
from grr_response_server.gui import api_call_handler_base


class ApiUploadYaraSignatureArgs(rdf_structs.RDFProtoStruct):
  """An RDF wrapper class for arguments of YARA singature uploader."""

  protobuf = yara_pb2.ApiUploadYaraSignatureArgs
  rdf_deps = []


class ApiUploadYaraSignatureResult(rdf_structs.RDFProtoStruct):
  """An RDF wrapper class for results of YARA signature uploader."""

  protobuf = yara_pb2.ApiUploadYaraSignatureResult
  rdf_deps = []


class ApiUploadYaraSignatureHandler(api_call_handler_base.ApiCallHandler):
  """An API handler for uploading YARA signatures."""

  args_type = ApiUploadYaraSignatureArgs
  result_type = ApiUploadYaraSignatureResult
  proto_args_type = yara_pb2.ApiUploadYaraSignatureArgs
  proto_result_type = yara_pb2.ApiUploadYaraSignatureResult

  def Handle(  # pytype: disable=signature-mismatch  # overriding-parameter-count-checks
      self,
      args: yara_pb2.ApiUploadYaraSignatureArgs,
      context: Optional[api_call_context.ApiCallContext],
  ) -> yara_pb2.ApiUploadYaraSignatureResult:
    assert context is not None

    blob = args.signature.encode("utf-8")
    blob_id = data_store.BLOBS.WriteBlobWithUnknownHash(blob)

    data_store.REL_DB.WriteYaraSignatureReference(blob_id, context.username)

    result = yara_pb2.ApiUploadYaraSignatureResult()
    result.blob_id = bytes(blob_id)
    return result
