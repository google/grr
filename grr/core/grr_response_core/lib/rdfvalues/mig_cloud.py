#!/usr/bin/env python
"""Provides conversion functions to be used during RDFProtoStruct migration."""

from grr_response_core.lib.rdfvalues import cloud as rdf_cloud
from grr_response_proto import flows_pb2
from grr_response_proto import jobs_pb2


def ToProtoCloudMetadataRequest(
    rdf: rdf_cloud.CloudMetadataRequest,
) -> flows_pb2.CloudMetadataRequest:
  return rdf.AsPrimitiveProto()


def ToRDFCloudMetadataRequest(
    proto: flows_pb2.CloudMetadataRequest,
) -> rdf_cloud.CloudMetadataRequest:
  return rdf_cloud.CloudMetadataRequest.FromSerializedBytes(
      proto.SerializeToString()
  )


def ToProtoCloudMetadataRequests(
    rdf: rdf_cloud.CloudMetadataRequests,
) -> flows_pb2.CloudMetadataRequests:
  return rdf.AsPrimitiveProto()


def ToRDFCloudMetadataRequests(
    proto: flows_pb2.CloudMetadataRequests,
) -> rdf_cloud.CloudMetadataRequests:
  return rdf_cloud.CloudMetadataRequests.FromSerializedBytes(
      proto.SerializeToString()
  )


def ToProtoCloudMetadataResponse(
    rdf: rdf_cloud.CloudMetadataResponse,
) -> flows_pb2.CloudMetadataResponse:
  return rdf.AsPrimitiveProto()


def ToRDFCloudMetadataResponse(
    proto: flows_pb2.CloudMetadataResponse,
) -> rdf_cloud.CloudMetadataResponse:
  return rdf_cloud.CloudMetadataResponse.FromSerializedBytes(
      proto.SerializeToString()
  )


def ToProtoCloudMetadataResponses(
    rdf: rdf_cloud.CloudMetadataResponses,
) -> flows_pb2.CloudMetadataResponses:
  return rdf.AsPrimitiveProto()


def ToRDFCloudMetadataResponses(
    proto: flows_pb2.CloudMetadataResponses,
) -> rdf_cloud.CloudMetadataResponses:
  return rdf_cloud.CloudMetadataResponses.FromSerializedBytes(
      proto.SerializeToString()
  )


def ToProtoGoogleCloudInstance(
    rdf: rdf_cloud.GoogleCloudInstance,
) -> jobs_pb2.GoogleCloudInstance:
  return rdf.AsPrimitiveProto()


def ToRDFGoogleCloudInstance(
    proto: jobs_pb2.GoogleCloudInstance,
) -> rdf_cloud.GoogleCloudInstance:
  return rdf_cloud.GoogleCloudInstance.FromSerializedBytes(
      proto.SerializeToString()
  )


def ToProtoAmazonCloudInstance(
    rdf: rdf_cloud.AmazonCloudInstance,
) -> jobs_pb2.AmazonCloudInstance:
  return rdf.AsPrimitiveProto()


def ToRDFAmazonCloudInstance(
    proto: jobs_pb2.AmazonCloudInstance,
) -> rdf_cloud.AmazonCloudInstance:
  return rdf_cloud.AmazonCloudInstance.FromSerializedBytes(
      proto.SerializeToString()
  )


def ToProtoCloudInstance(
    rdf: rdf_cloud.CloudInstance,
) -> jobs_pb2.CloudInstance:
  return rdf.AsPrimitiveProto()


def ToRDFCloudInstance(
    proto: jobs_pb2.CloudInstance,
) -> rdf_cloud.CloudInstance:
  return rdf_cloud.CloudInstance.FromSerializedBytes(proto.SerializeToString())
