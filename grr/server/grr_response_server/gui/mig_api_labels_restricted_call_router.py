#!/usr/bin/env python
"""Provides conversion functions to be used during RDFProtoStruct migration."""

from grr_response_proto import api_call_router_pb2
from grr_response_server.gui import api_labels_restricted_call_router


def ToProtoApiLabelsRestrictedCallRouterParams(
    rdf: api_labels_restricted_call_router.ApiLabelsRestrictedCallRouterParams,
) -> api_call_router_pb2.ApiLabelsRestrictedCallRouterParams:
  return rdf.AsPrimitiveProto()


def ToRDFApiLabelsRestrictedCallRouterParams(
    proto: api_call_router_pb2.ApiLabelsRestrictedCallRouterParams,
) -> api_labels_restricted_call_router.ApiLabelsRestrictedCallRouterParams:
  return api_labels_restricted_call_router.ApiLabelsRestrictedCallRouterParams.FromSerializedBytes(
      proto.SerializeToString()
  )
