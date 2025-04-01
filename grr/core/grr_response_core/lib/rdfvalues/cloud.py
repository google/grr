#!/usr/bin/env python
"""Cloud-related rdfvalues."""

from grr_response_core.lib.rdfvalues import protodict as rdf_protodict
from grr_response_core.lib.rdfvalues import structs as rdf_structs
from grr_response_proto import flows_pb2
from grr_response_proto import jobs_pb2

AMAZON_URL_BASE = "http://169.254.169.254/latest/meta-data"
AMAZON_BIOS_REGEX = ".*amazon"
AMAZON_SERVICE_REGEX = "SERVICE_NAME: AWSLiteAgent"
# Using the ip and not metadata.google.internal to avoid issues on endpoints
# with misconfigured DNS resolvers.
GOOGLE_URL_BASE = "http://169.254.169.254/computeMetadata/v1"
GOOGLE_BIOS_REGEX = "Google"
GOOGLE_SERVICE_REGEX = "SERVICE_NAME: GCEAgent"


class CloudMetadataRequest(rdf_structs.RDFProtoStruct):
  """RDF wrapper for `CloudMetadataRequest` message."""

  protobuf = flows_pb2.CloudMetadataRequest
  rdf_deps = [
      rdf_protodict.Dict,
  ]

  @classmethod
  def ForAmazon(cls, *args, **kwargs) -> "CloudMetadataRequest":
    return cls(
        *args,
        **kwargs,
        bios_version_regex=AMAZON_BIOS_REGEX,
        service_name_regex=AMAZON_SERVICE_REGEX,
        instance_type=CloudInstance.InstanceType.AMAZON,
        timeout=1.0,
    )

  @classmethod
  def ForGoogle(cls, *args, **kwargs) -> "CloudMetadataRequest":
    return cls(
        *args,
        **kwargs,
        bios_version_regex=GOOGLE_BIOS_REGEX,
        service_name_regex=GOOGLE_SERVICE_REGEX,
        headers={"Metadata-Flavor": "Google"},
        instance_type=CloudInstance.InstanceType.GOOGLE,
        timeout=1.0,
    )


class CloudMetadataRequests(rdf_structs.RDFProtoStruct):
  protobuf = flows_pb2.CloudMetadataRequests
  rdf_deps = [
      CloudMetadataRequest,
  ]


class CloudMetadataResponse(rdf_structs.RDFProtoStruct):
  protobuf = flows_pb2.CloudMetadataResponse


class CloudMetadataResponses(rdf_structs.RDFProtoStruct):
  protobuf = flows_pb2.CloudMetadataResponses
  rdf_deps = [
      CloudMetadataResponse,
  ]


class GoogleCloudInstance(rdf_structs.RDFProtoStruct):
  protobuf = jobs_pb2.GoogleCloudInstance


class AmazonCloudInstance(rdf_structs.RDFProtoStruct):
  protobuf = jobs_pb2.AmazonCloudInstance


class CloudInstance(rdf_structs.RDFProtoStruct):
  protobuf = jobs_pb2.CloudInstance
  rdf_deps = [
      AmazonCloudInstance,
      GoogleCloudInstance,
  ]


# TODO: Return a proto instead of an RDFValue.
def BuildCloudMetadataRequests():
  """Build the standard set of cloud metadata to collect during interrogate.

  The `label` field is used to identify the metadata in the response, and should
  match a valid field of the corresponding <Platform>CloudInstance proto.
  Example: A request for instance_type=CloudInstance.InstanceType.GOOGLE with
          `label="instance_id"` -> `GoogleCloudInstance.instance_id`

  Returns:
    A CloudMetadataRequests proto with the standard set of interrogate requests.
  """
  return CloudMetadataRequests(
      requests=[
          CloudMetadataRequest.ForAmazon(
              url="/".join((AMAZON_URL_BASE, "instance-id")),
              label="instance_id",
          ),
          CloudMetadataRequest.ForAmazon(
              url="/".join((AMAZON_URL_BASE, "ami-id")),
              label="ami_id",
          ),
          CloudMetadataRequest.ForAmazon(
              url="/".join((AMAZON_URL_BASE, "hostname")),
              label="hostname",
          ),
          CloudMetadataRequest.ForAmazon(
              url="/".join((AMAZON_URL_BASE, "public-hostname")),
              label="public_hostname",
              # Per AWS documentation, `public-hostname` is available only on
              # hosts with public IPv4 addresses and `enableDnsHostnames` option
              # set. Otherwise, attempts to query this property will result in
              # 404 HTTP status.
              #
              # https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/instancedata-data-categories.html
              ignore_http_errors=True,
          ),
          CloudMetadataRequest.ForAmazon(
              url="/".join((AMAZON_URL_BASE, "instance-type")),
              label="instance_type",
          ),
          CloudMetadataRequest.ForGoogle(
              url="/".join((GOOGLE_URL_BASE, "instance/id")),
              label="instance_id",
          ),
          CloudMetadataRequest.ForGoogle(
              url="/".join((GOOGLE_URL_BASE, "instance/zone")),
              label="zone",
          ),
          CloudMetadataRequest.ForGoogle(
              url="/".join((GOOGLE_URL_BASE, "project/project-id")),
              label="project_id",
          ),
          CloudMetadataRequest.ForGoogle(
              url="/".join((GOOGLE_URL_BASE, "instance/hostname")),
              label="hostname",
          ),
          CloudMetadataRequest.ForGoogle(
              url="/".join((GOOGLE_URL_BASE, "instance/machine-type")),
              label="machine_type",
          ),
      ],
  )
