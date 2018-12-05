#!/usr/bin/env python
"""Client actions requests and responses."""

from __future__ import absolute_import
from __future__ import division

from grr_response_core.lib import rdfvalue

from grr_response_core.lib.rdfvalues import crypto as rdf_crypto
from grr_response_core.lib.rdfvalues import paths as rdf_paths
from grr_response_core.lib.rdfvalues import protodict as rdf_protodict
from grr_response_core.lib.rdfvalues import structs as rdf_structs

from grr_response_proto import flows_pb2
from grr_response_proto import jobs_pb2


class EchoRequest(rdf_structs.RDFProtoStruct):
  protobuf = jobs_pb2.PrintStr


class ExecuteBinaryRequest(rdf_structs.RDFProtoStruct):
  protobuf = jobs_pb2.ExecuteBinaryRequest
  rdf_deps = [
      rdf_crypto.SignedBlob,
  ]


class ExecuteBinaryResponse(rdf_structs.RDFProtoStruct):
  protobuf = jobs_pb2.ExecuteBinaryResponse


class ExecutePythonRequest(rdf_structs.RDFProtoStruct):
  protobuf = jobs_pb2.ExecutePythonRequest
  rdf_deps = [
      rdf_protodict.Dict,
      rdf_crypto.SignedBlob,
  ]


class ExecutePythonResponse(rdf_structs.RDFProtoStruct):
  protobuf = jobs_pb2.ExecutePythonResponse


class ExecuteRequest(rdf_structs.RDFProtoStruct):
  protobuf = jobs_pb2.ExecuteRequest


class CopyPathToFileRequest(rdf_structs.RDFProtoStruct):
  protobuf = jobs_pb2.CopyPathToFile
  rdf_deps = [
      rdf_paths.PathSpec,
  ]


class ExecuteResponse(rdf_structs.RDFProtoStruct):
  protobuf = jobs_pb2.ExecuteResponse
  rdf_deps = [
      ExecuteRequest,
  ]


class SendFileRequest(rdf_structs.RDFProtoStruct):
  """Arguments for the `SendFile` action."""

  protobuf = jobs_pb2.SendFileRequest
  rdf_deps = [
      rdf_crypto.AES128Key,
      rdf_paths.PathSpec,
  ]

  def Validate(self):
    self.pathspec.Validate()

    if not self.host:
      raise ValueError("A host must be specified.")


class Iterator(rdf_structs.RDFProtoStruct):
  """An Iterated client action is one which can be resumed on the client."""
  protobuf = jobs_pb2.Iterator
  rdf_deps = [
      rdf_protodict.Dict,
  ]


class ListDirRequest(rdf_structs.RDFProtoStruct):
  protobuf = jobs_pb2.ListDirRequest
  rdf_deps = [
      Iterator,
      rdf_paths.PathSpec,
  ]


class GetFileStatRequest(rdf_structs.RDFProtoStruct):

  protobuf = jobs_pb2.GetFileStatRequest
  rdf_deps = [
      rdf_paths.PathSpec,
  ]


class FingerprintTuple(rdf_structs.RDFProtoStruct):
  protobuf = jobs_pb2.FingerprintTuple


class FingerprintRequest(rdf_structs.RDFProtoStruct):
  protobuf = jobs_pb2.FingerprintRequest
  rdf_deps = [
      FingerprintTuple,
      rdf_paths.PathSpec,
  ]

  def AddRequest(self, *args, **kw):
    self.tuples.Append(*args, **kw)


class FingerprintResponse(rdf_structs.RDFProtoStruct):
  """Proto containing dicts with hashes."""
  protobuf = jobs_pb2.FingerprintResponse
  rdf_deps = [
      rdf_protodict.Dict,
      rdf_crypto.Hash,
      rdf_paths.PathSpec,
  ]

  def GetFingerprint(self, name):
    """Gets the first fingerprint type from the protobuf."""
    for result in self.results:
      if result.GetItem("name") == name:
        return result


class WMIRequest(rdf_structs.RDFProtoStruct):
  protobuf = jobs_pb2.WmiRequest


class StatFSRequest(rdf_structs.RDFProtoStruct):
  protobuf = jobs_pb2.StatFSRequest


class GetClientStatsRequest(rdf_structs.RDFProtoStruct):
  """Request for GetClientStats action."""
  protobuf = jobs_pb2.GetClientStatsRequest
  rdf_deps = [
      rdfvalue.RDFDatetime,
  ]


class ListNetworkConnectionsArgs(rdf_structs.RDFProtoStruct):
  """Args for the ListNetworkConnections client action."""
  protobuf = flows_pb2.ListNetworkConnectionsArgs
