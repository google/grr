#!/usr/bin/env python
"""Provides conversion functions to be used during RDFProtoStruct migration."""

from grr_response_core.lib.rdfvalues import client_action as rdf_client_action
from grr_response_proto import flows_pb2
from grr_response_proto import jobs_pb2


def ToProtoEchoRequest(
    rdf: rdf_client_action.EchoRequest,
) -> jobs_pb2.EchoRequest:
  return rdf.AsPrimitiveProto()


def ToRDFEchoRequest(
    proto: jobs_pb2.EchoRequest,
) -> rdf_client_action.EchoRequest:
  return rdf_client_action.EchoRequest.FromSerializedBytes(
      proto.SerializeToString()
  )


def ToProtoExecuteBinaryRequest(
    rdf: rdf_client_action.ExecuteBinaryRequest,
) -> jobs_pb2.ExecuteBinaryRequest:
  return rdf.AsPrimitiveProto()


def ToRDFExecuteBinaryRequest(
    proto: jobs_pb2.ExecuteBinaryRequest,
) -> rdf_client_action.ExecuteBinaryRequest:
  return rdf_client_action.ExecuteBinaryRequest.FromSerializedBytes(
      proto.SerializeToString()
  )


def ToProtoExecuteBinaryResponse(
    rdf: rdf_client_action.ExecuteBinaryResponse,
) -> jobs_pb2.ExecuteBinaryResponse:
  return rdf.AsPrimitiveProto()


def ToRDFExecuteBinaryResponse(
    proto: jobs_pb2.ExecuteBinaryResponse,
) -> rdf_client_action.ExecuteBinaryResponse:
  return rdf_client_action.ExecuteBinaryResponse.FromSerializedBytes(
      proto.SerializeToString()
  )


def ToProtoExecutePythonRequest(
    rdf: rdf_client_action.ExecutePythonRequest,
) -> jobs_pb2.ExecutePythonRequest:
  return rdf.AsPrimitiveProto()


def ToRDFExecutePythonRequest(
    proto: jobs_pb2.ExecutePythonRequest,
) -> rdf_client_action.ExecutePythonRequest:
  return rdf_client_action.ExecutePythonRequest.FromSerializedBytes(
      proto.SerializeToString()
  )


def ToProtoExecutePythonResponse(
    rdf: rdf_client_action.ExecutePythonResponse,
) -> jobs_pb2.ExecutePythonResponse:
  return rdf.AsPrimitiveProto()


def ToRDFExecutePythonResponse(
    proto: jobs_pb2.ExecutePythonResponse,
) -> rdf_client_action.ExecutePythonResponse:
  return rdf_client_action.ExecutePythonResponse.FromSerializedBytes(
      proto.SerializeToString()
  )


def ToProtoExecuteRequest(
    rdf: rdf_client_action.ExecuteRequest,
) -> jobs_pb2.ExecuteRequest:
  return rdf.AsPrimitiveProto()


def ToRDFExecuteRequest(
    proto: jobs_pb2.ExecuteRequest,
) -> rdf_client_action.ExecuteRequest:
  return rdf_client_action.ExecuteRequest.FromSerializedBytes(
      proto.SerializeToString()
  )


def ToProtoExecuteResponse(
    rdf: rdf_client_action.ExecuteResponse,
) -> jobs_pb2.ExecuteResponse:
  return rdf.AsPrimitiveProto()


def ToRDFExecuteResponse(
    proto: jobs_pb2.ExecuteResponse,
) -> rdf_client_action.ExecuteResponse:
  return rdf_client_action.ExecuteResponse.FromSerializedBytes(
      proto.SerializeToString()
  )


def ToProtoIterator(rdf: rdf_client_action.Iterator) -> jobs_pb2.Iterator:
  return rdf.AsPrimitiveProto()


def ToRDFIterator(proto: jobs_pb2.Iterator) -> rdf_client_action.Iterator:
  return rdf_client_action.Iterator.FromSerializedBytes(
      proto.SerializeToString()
  )


def ToProtoListDirRequest(
    rdf: rdf_client_action.ListDirRequest,
) -> jobs_pb2.ListDirRequest:
  return rdf.AsPrimitiveProto()


def ToRDFListDirRequest(
    proto: jobs_pb2.ListDirRequest,
) -> rdf_client_action.ListDirRequest:
  return rdf_client_action.ListDirRequest.FromSerializedBytes(
      proto.SerializeToString()
  )


def ToProtoGetFileStatRequest(
    rdf: rdf_client_action.GetFileStatRequest,
) -> jobs_pb2.GetFileStatRequest:
  return rdf.AsPrimitiveProto()


def ToRDFGetFileStatRequest(
    proto: jobs_pb2.GetFileStatRequest,
) -> rdf_client_action.GetFileStatRequest:
  return rdf_client_action.GetFileStatRequest.FromSerializedBytes(
      proto.SerializeToString()
  )


def ToProtoFingerprintTuple(
    rdf: rdf_client_action.FingerprintTuple,
) -> jobs_pb2.FingerprintTuple:
  return rdf.AsPrimitiveProto()


def ToRDFFingerprintTuple(
    proto: jobs_pb2.FingerprintTuple,
) -> rdf_client_action.FingerprintTuple:
  return rdf_client_action.FingerprintTuple.FromSerializedBytes(
      proto.SerializeToString()
  )


def ToProtoFingerprintRequest(
    rdf: rdf_client_action.FingerprintRequest,
) -> jobs_pb2.FingerprintRequest:
  return rdf.AsPrimitiveProto()


def ToRDFFingerprintRequest(
    proto: jobs_pb2.FingerprintRequest,
) -> rdf_client_action.FingerprintRequest:
  return rdf_client_action.FingerprintRequest.FromSerializedBytes(
      proto.SerializeToString()
  )


def ToProtoFingerprintResponse(
    rdf: rdf_client_action.FingerprintResponse,
) -> jobs_pb2.FingerprintResponse:
  return rdf.AsPrimitiveProto()


def ToRDFFingerprintResponse(
    proto: jobs_pb2.FingerprintResponse,
) -> rdf_client_action.FingerprintResponse:
  return rdf_client_action.FingerprintResponse.FromSerializedBytes(
      proto.SerializeToString()
  )


def ToProtoWMIRequest(rdf: rdf_client_action.WMIRequest) -> jobs_pb2.WMIRequest:
  return rdf.AsPrimitiveProto()


def ToRDFWMIRequest(proto: jobs_pb2.WMIRequest) -> rdf_client_action.WMIRequest:
  return rdf_client_action.WMIRequest.FromSerializedBytes(
      proto.SerializeToString()
  )


def ToProtoStatFSRequest(
    rdf: rdf_client_action.StatFSRequest,
) -> jobs_pb2.StatFSRequest:
  return rdf.AsPrimitiveProto()


def ToRDFStatFSRequest(
    proto: jobs_pb2.StatFSRequest,
) -> rdf_client_action.StatFSRequest:
  return rdf_client_action.StatFSRequest.FromSerializedBytes(
      proto.SerializeToString()
  )


def ToProtoListNetworkConnectionsArgs(
    rdf: rdf_client_action.ListNetworkConnectionsArgs,
) -> flows_pb2.ListNetworkConnectionsArgs:
  return rdf.AsPrimitiveProto()


def ToRDFListNetworkConnectionsArgs(
    proto: flows_pb2.ListNetworkConnectionsArgs,
) -> rdf_client_action.ListNetworkConnectionsArgs:
  return rdf_client_action.ListNetworkConnectionsArgs.FromSerializedBytes(
      proto.SerializeToString()
  )
