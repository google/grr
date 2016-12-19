#!/usr/bin/env python
"""Cloud-related rdfvalues."""

from grr.lib.rdfvalues import structs as rdf_structs
from grr.proto import flows_pb2


class CloudMetadataRequests(rdf_structs.RDFProtoStruct):
  protobuf = flows_pb2.CloudMetadataRequests


class CloudMetadataResponses(rdf_structs.RDFProtoStruct):
  protobuf = flows_pb2.CloudMetadataResponses


class CloudMetadataResponse(rdf_structs.RDFProtoStruct):
  protobuf = flows_pb2.CloudMetadataResponse


class CloudMetadataRequest(rdf_structs.RDFProtoStruct):
  protobuf = flows_pb2.CloudMetadataRequest
