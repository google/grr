#!/usr/bin/env python
"""Provides conversion functions to be used during RDFProtoStruct migration."""
from grr_response_proto import crowdstrike_pb2
from grr_response_server.flows.general import crowdstrike


def ToProtoGetCrowdstrikeAgentIdResult(
    rdf: crowdstrike.GetCrowdstrikeAgentIdResult,
) -> crowdstrike_pb2.GetCrowdstrikeAgentIdResult:
  return rdf.AsPrimitiveProto()


def ToRDFGetCrowdstrikeAgentIdResult(
    proto: crowdstrike_pb2.GetCrowdstrikeAgentIdResult,
) -> crowdstrike.GetCrowdstrikeAgentIdResult:
  return crowdstrike.GetCrowdstrikeAgentIdResult.FromSerializedBytes(
      proto.SerializeToString()
  )
