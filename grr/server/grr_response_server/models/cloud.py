#!/usr/bin/env python
"""Cloud-related data and helpers."""

from grr_response_proto import flows_pb2
from grr_response_proto import jobs_pb2


def MakeGoogleUniqueID(cloud_instance: jobs_pb2.GoogleCloudInstance) -> str:
  """Make the google unique ID of zone/project/id."""
  if not (
      cloud_instance.zone
      and cloud_instance.project_id
      and cloud_instance.instance_id
  ):
    raise ValueError(
        "Bad zone/project_id/id: '%s/%s/%s'"
        % (
            cloud_instance.zone,
            cloud_instance.project_id,
            cloud_instance.instance_id,
        )
    )
  return "/".join([
      cloud_instance.zone.split("/")[-1],
      cloud_instance.project_id,
      cloud_instance.instance_id,
  ])


def ConvertCloudMetadataResponsesToCloudInstance(
    metadata_responses: flows_pb2.CloudMetadataResponses,
) -> jobs_pb2.CloudInstance:
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
  if (
      metadata_responses.instance_type
      == jobs_pb2.CloudInstance.InstanceType.GOOGLE
  ):
    cloud_instance = jobs_pb2.GoogleCloudInstance()
    for cloud_metadata in metadata_responses.responses:
      setattr(cloud_instance, cloud_metadata.label, cloud_metadata.text)
    cloud_instance.unique_id = MakeGoogleUniqueID(cloud_instance)
    result = jobs_pb2.CloudInstance(
        cloud_type=jobs_pb2.CloudInstance.InstanceType.GOOGLE,
        google=cloud_instance,
    )

  elif (
      metadata_responses.instance_type
      == jobs_pb2.CloudInstance.InstanceType.AMAZON
  ):
    cloud_instance = jobs_pb2.AmazonCloudInstance()
    for cloud_metadata in metadata_responses.responses:
      setattr(cloud_instance, cloud_metadata.label, cloud_metadata.text)
    result = jobs_pb2.CloudInstance(
        cloud_type=jobs_pb2.CloudInstance.InstanceType.AMAZON,
        amazon=cloud_instance,
    )

  else:
    raise ValueError(
        "Unknown cloud instance type: %s" % metadata_responses.instance_type
    )

  return result
