#!/usr/bin/env python
"""Cloud-related rdfvalues."""

from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals


from future.utils import iteritems

from grr_response_core.lib.rdfvalues import protodict as rdf_protodict
from grr_response_core.lib.rdfvalues import structs as rdf_structs
from grr_response_proto import flows_pb2
from grr_response_proto import jobs_pb2

AMAZON_URL_BASE = "http://169.254.169.254/latest/meta-data/"
AMAZON_BIOS_REGEX = ".*amazon"
AMAZON_SERVICE_REGEX = "SERVICE_NAME: AWSLiteAgent"
GOOGLE_URL_BASE = "http://metadata.google.internal/computeMetadata/v1"
GOOGLE_BIOS_REGEX = "Google"
GOOGLE_SERVICE_REGEX = "SERVICE_NAME: GCEAgent"


class CloudMetadataRequest(rdf_structs.RDFProtoStruct):
  protobuf = flows_pb2.CloudMetadataRequest
  rdf_deps = [
      rdf_protodict.Dict,
  ]


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


def _MakeArgs(amazon_collection_map, google_collection_map):
  """Build metadata requests list from collection maps."""
  request_list = []
  for url, label in iteritems(amazon_collection_map):
    request_list.append(
        CloudMetadataRequest(
            bios_version_regex=AMAZON_BIOS_REGEX,
            service_name_regex=AMAZON_SERVICE_REGEX,
            instance_type="AMAZON",
            timeout=1.0,
            url=url,
            label=label))
  for url, label in iteritems(google_collection_map):
    request_list.append(
        CloudMetadataRequest(
            bios_version_regex=GOOGLE_BIOS_REGEX,
            service_name_regex=GOOGLE_SERVICE_REGEX,
            headers={"Metadata-Flavor": "Google"},
            instance_type="GOOGLE",
            timeout=1.0,
            url=url,
            label=label))
  return request_list


def MakeGoogleUniqueID(cloud_instance):
  """Make the google unique ID of zone/project/id."""
  if not (cloud_instance.zone and cloud_instance.project_id and
          cloud_instance.instance_id):
    raise ValueError("Bad zone/project_id/id: '%s/%s/%s'" %
                     (cloud_instance.zone, cloud_instance.project_id,
                      cloud_instance.instance_id))
  return "/".join([
      cloud_instance.zone.split("/")[-1], cloud_instance.project_id,
      cloud_instance.instance_id
  ])


def BuildCloudMetadataRequests():
  """Build the standard set of cloud metadata to collect during interrogate."""
  amazon_collection_map = {
      "/".join((AMAZON_URL_BASE, "instance-id")): "instance_id",
      "/".join((AMAZON_URL_BASE, "ami-id")): "ami_id",
      "/".join((AMAZON_URL_BASE, "hostname")): "hostname",
      "/".join((AMAZON_URL_BASE, "public-hostname")): "public_hostname",
      "/".join((AMAZON_URL_BASE, "instance-type")): "instance_type",
  }
  google_collection_map = {
      "/".join((GOOGLE_URL_BASE, "instance/id")): "instance_id",
      "/".join((GOOGLE_URL_BASE, "instance/zone")): "zone",
      "/".join((GOOGLE_URL_BASE, "project/project-id")): "project_id",
      "/".join((GOOGLE_URL_BASE, "instance/hostname")): "hostname",
      "/".join((GOOGLE_URL_BASE, "instance/machine-type")): "machine_type",
  }

  return CloudMetadataRequests(requests=_MakeArgs(amazon_collection_map,
                                                  google_collection_map))


def ConvertCloudMetadataResponsesToCloudInstance(metadata_responses):
  """Convert CloudMetadataResponses to CloudInstance proto.

  Ideally we'd just get the client to fill out a CloudInstance proto, but we
  need to keep the flexibility of collecting new metadata and creating new
  fields without a client push. So instead we bring back essentially a dict of
  results and fill the proto on the server side.

  Args:
    metadata_responses: CloudMetadataResponses object from the client.
  Returns:
    CloudInstance object
  Raises:
    ValueError: if client passes bad or unset cloud type.
  """
  if metadata_responses.instance_type == "GOOGLE":
    cloud_instance = GoogleCloudInstance()
    result = CloudInstance(cloud_type="GOOGLE", google=cloud_instance)
  elif metadata_responses.instance_type == "AMAZON":
    cloud_instance = AmazonCloudInstance()
    result = CloudInstance(cloud_type="AMAZON", amazon=cloud_instance)
  else:
    raise ValueError(
        "Unknown cloud instance type: %s" % metadata_responses.instance_type)

  for cloud_metadata in metadata_responses.responses:
    setattr(cloud_instance, cloud_metadata.label, cloud_metadata.text)

  if result.cloud_type == "GOOGLE":
    cloud_instance.unique_id = MakeGoogleUniqueID(cloud_instance)

  return result
