#!/usr/bin/env python
"""Provides conversion functions to be used during RDFProtoStruct migration."""

from grr_response_proto.api import client_pb2
from grr_response_server.gui.api_plugins import client


def ToRDFApiClient(proto: client_pb2.ApiClient) -> client.ApiClient:
  return client.ApiClient.FromSerializedBytes(proto.SerializeToString())
