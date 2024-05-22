#!/usr/bin/env python
"""Provides conversion functions to be used during RDFProtoStruct migration."""

from grr_response_proto.api import yara_pb2
from grr_response_server.gui.api_plugins import yara


def ToProtoApiUploadYaraSignatureArgs(
    rdf: yara.ApiUploadYaraSignatureArgs,
) -> yara_pb2.ApiUploadYaraSignatureArgs:
  return rdf.AsPrimitiveProto()


def ToRDFApiUploadYaraSignatureArgs(
    proto: yara_pb2.ApiUploadYaraSignatureArgs,
) -> yara.ApiUploadYaraSignatureArgs:
  return yara.ApiUploadYaraSignatureArgs.FromSerializedBytes(
      proto.SerializeToString()
  )


def ToProtoApiUploadYaraSignatureResult(
    rdf: yara.ApiUploadYaraSignatureResult,
) -> yara_pb2.ApiUploadYaraSignatureResult:
  return rdf.AsPrimitiveProto()


def ToRDFApiUploadYaraSignatureResult(
    proto: yara_pb2.ApiUploadYaraSignatureResult,
) -> yara.ApiUploadYaraSignatureResult:
  return yara.ApiUploadYaraSignatureResult.FromSerializedBytes(
      proto.SerializeToString()
  )
