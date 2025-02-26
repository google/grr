#!/usr/bin/env python
"""Provides conversion functions to be used during RDFProtoStruct migration."""

from grr_response_proto import flows_pb2
from grr_response_server.flows.general import processes


def ToProtoListProcessesArgs(
    rdf: processes.ListProcessesArgs,
) -> flows_pb2.ListProcessesArgs:
  return rdf.AsPrimitiveProto()


def ToRDFListProcessesArgs(
    proto: flows_pb2.ListProcessesArgs,
) -> processes.ListProcessesArgs:
  return processes.ListProcessesArgs.FromSerializedBytes(
      proto.SerializeToString()
  )
