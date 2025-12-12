#!/usr/bin/env python
"""Provides conversion functions to be used during RDFProtoStruct migration."""

from grr_response_proto import flows_pb2
from grr_response_server.flows.general import transfer


def ToProtoMultiGetFileArgs(
    rdf: transfer.MultiGetFileArgs,
) -> flows_pb2.MultiGetFileArgs:
  return rdf.AsPrimitiveProto()


def ToRDFMultiGetFileArgs(
    proto: flows_pb2.MultiGetFileArgs,
) -> transfer.MultiGetFileArgs:
  return transfer.MultiGetFileArgs.FromSerializedBytes(
      proto.SerializeToString()
  )


def ToProtoPathSpecProgress(
    rdf: transfer.PathSpecProgress,
) -> flows_pb2.PathSpecProgress:
  return rdf.AsPrimitiveProto()


def ToRDFPathSpecProgress(
    proto: flows_pb2.PathSpecProgress,
) -> transfer.PathSpecProgress:
  return transfer.PathSpecProgress.FromSerializedBytes(
      proto.SerializeToString()
  )


def ToProtoMultiGetFileProgress(
    rdf: transfer.MultiGetFileProgress,
) -> flows_pb2.MultiGetFileProgress:
  return rdf.AsPrimitiveProto()


def ToRDFMultiGetFileProgress(
    proto: flows_pb2.MultiGetFileProgress,
) -> transfer.MultiGetFileProgress:
  return transfer.MultiGetFileProgress.FromSerializedBytes(
      proto.SerializeToString()
  )


def ToProtoGetMBRArgs(rdf: transfer.GetMBRArgs) -> flows_pb2.GetMBRArgs:
  return rdf.AsPrimitiveProto()


def ToRDFGetMBRArgs(proto: flows_pb2.GetMBRArgs) -> transfer.GetMBRArgs:
  return transfer.GetMBRArgs.FromSerializedBytes(proto.SerializeToString())
