#!/usr/bin/env python
"""Provides conversion functions to be used during RDFProtoStruct migration."""

from grr_response_proto import api_call_router_pb2
from grr_response_server.gui import api_call_router_with_approval_checks


def ToProtoApiCallRouterWithApprovalCheckParams(
    rdf: api_call_router_with_approval_checks.ApiCallRouterWithApprovalCheckParams,
) -> api_call_router_pb2.ApiCallRouterWithApprovalCheckParams:
  return rdf.AsPrimitiveProto()


def ToRDFApiCallRouterWithApprovalCheckParams(
    proto: api_call_router_pb2.ApiCallRouterWithApprovalCheckParams,
) -> api_call_router_with_approval_checks.ApiCallRouterWithApprovalCheckParams:
  return api_call_router_with_approval_checks.ApiCallRouterWithApprovalCheckParams.FromSerializedBytes(
      proto.SerializeToString()
  )
