#!/usr/bin/env python
"""Provides conversion functions to be used during RDFProtoStruct migration."""

from grr_response_proto import acls_pb2
from grr_response_server.authorization import client_approval_auth


def ToProtoClientApprovalAuthorization(
    rdf: client_approval_auth.ClientApprovalAuthorization,
) -> acls_pb2.ClientApprovalAuthorization:
  return rdf.AsPrimitiveProto()


def ToRDFClientApprovalAuthorization(
    proto: acls_pb2.ClientApprovalAuthorization,
) -> client_approval_auth.ClientApprovalAuthorization:
  return client_approval_auth.ClientApprovalAuthorization.FromSerializedBytes(
      proto.SerializeToString()
  )
