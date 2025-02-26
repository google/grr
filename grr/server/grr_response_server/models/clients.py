#!/usr/bin/env python
"""Module with data models and helpers related to clients."""

from collections.abc import Mapping
import ipaddress
from typing import Optional, Union

from google.protobuf import message as pb_message
from grr_response_core.lib import rdfvalue
from grr_response_proto import jobs_pb2
from grr_response_proto import objects_pb2
from grr_response_proto.api import client_pb2
from grr_response_server import fleetspeak_utils
from grr_response_server.models import protobuf_utils as models_utils
from fleetspeak.src.common.proto.fleetspeak import common_pb2
from fleetspeak.src.server.proto.fleetspeak_server import admin_pb2


def FleetspeakValidationInfoFromDict(
    tags: Mapping[str, str],
) -> jobs_pb2.FleetspeakValidationInfo:
  """Creates Fleetspeak validation information from the given tags.

  Args:
    tags: A mapping from tag keys to tag values.

  Returns:
    A Fleetspeak validation information for the given tags.
  """
  info = jobs_pb2.FleetspeakValidationInfo()

  for key, value in tags.items():
    info.tags.add(key=key, value=value)

  return info


def FleetspeakValidationInfoToDict(
    info: jobs_pb2.FleetspeakValidationInfo,
) -> Mapping[str, str]:
  """Creates a tag mapping from the given Fleetspeak validation information.

  Args:
    info: A Fleetspeak validation information.

  Returns:
    A mapping from tag keys to tag values.
  """
  result = {}

  for tag in info.tags:
    if not tag.key:
      raise ValueError("Empty tag key")
    if tag.key in result:
      raise ValueError(f"Duplicate tag key {tag.key!r}")
    if not tag.value:
      raise ValueError(f"Empty tag value for key {tag.key!r}")

    result[tag.key] = tag.value

  return result


def ApiFleetspeakAddressFromFleetspeakProto(
    fs_address: common_pb2.Address,
) -> client_pb2.ApiFleetspeakAddress:
  res = client_pb2.ApiFleetspeakAddress(
      service_name=fs_address.service_name,
  )
  if fs_address.client_id:
    res.client_id = fleetspeak_utils.FleetspeakIDToGRRID(fs_address.client_id)
  return res


def ApiFleetspeakAnnotationsFromFleetspeakProto(
    fs_annotations: common_pb2.Annotations,
) -> client_pb2.ApiFleetspeakAnnotations:
  result = client_pb2.ApiFleetspeakAnnotations()
  for entry in fs_annotations.entries:
    result.entries.append(
        client_pb2.ApiFleetspeakAnnotations.Entry(
            key=entry.key, value=entry.value
        )
    )
  return result


def ApiFleetspeakValidationInfoFromFleetspeakProto(
    fs_val_info: common_pb2.ValidationInfo,
) -> client_pb2.ApiFleetspeakValidationInfo:
  result = client_pb2.ApiFleetspeakValidationInfo()
  for key, value in fs_val_info.tags.items():
    result.tags.append(
        client_pb2.ApiFleetspeakValidationInfo.Tag(key=key, value=value)
    )
  return result


def ApiFleetspeakMessageResultFromFleetspeakProto(
    fs_msg_res: common_pb2.MessageResult,
) -> client_pb2.ApiFleetspeakMessageResult:
  result = client_pb2.ApiFleetspeakMessageResult(
      failed=fs_msg_res.failed,
      failed_reason=fs_msg_res.failed_reason,
  )
  if fs_msg_res.HasField("processed_time"):
    result.processed_time = rdfvalue.RDFDatetime.FromDatetime(
        fs_msg_res.processed_time.ToDatetime()
    ).AsMicrosecondsSinceEpoch()
  return result


def _PriorityFromFleetspeakProto(
    priority: common_pb2.Message.Priority,
) -> Optional["client_pb2.ApiFleetspeakMessage.Priority"]:
  if priority == common_pb2.Message.Priority.LOW:
    return client_pb2.ApiFleetspeakMessage.Priority.LOW
  elif priority == common_pb2.Message.Priority.MEDIUM:
    return client_pb2.ApiFleetspeakMessage.Priority.MEDIUM
  elif priority == common_pb2.Message.Priority.HIGH:
    return client_pb2.ApiFleetspeakMessage.Priority.HIGH
  else:
    return None


def ApiFleetspeakMessageFromFleetspeakProto(
    fs_msg: common_pb2.Message,
) -> client_pb2.ApiFleetspeakMessage:
  """Creates an ApiFleetspeakMessage from the given Fleetspeak Message proto."""

  result = client_pb2.ApiFleetspeakMessage()
  if fs_msg.message_id:
    result.message_id = fs_msg.message_id
  if fs_msg.source_message_id:
    result.source_message_id = fs_msg.source_message_id
  if fs_msg.message_type:
    result.message_type = fs_msg.message_type
  if fs_msg.background:
    result.background = fs_msg.background
  if fs_msg.priority:
    result.priority = _PriorityFromFleetspeakProto(fs_msg.priority)
  if fs_msg.HasField("source"):
    result.source.CopyFrom(
        ApiFleetspeakAddressFromFleetspeakProto(fs_msg.source)
    )
  if fs_msg.HasField("destination"):
    result.destination.CopyFrom(
        ApiFleetspeakAddressFromFleetspeakProto(fs_msg.destination)
    )
  if fs_msg.HasField("creation_time"):
    result.creation_time = rdfvalue.RDFDatetime.FromDatetime(
        fs_msg.creation_time.ToDatetime()
    ).AsMicrosecondsSinceEpoch()
  if fs_msg.HasField("data"):
    result.data.CopyFrom(fs_msg.data)
  if fs_msg.HasField("validation_info"):
    result.validation_info.CopyFrom(
        ApiFleetspeakValidationInfoFromFleetspeakProto(fs_msg.validation_info)
    )
  if fs_msg.HasField("result"):
    result.result.CopyFrom(
        ApiFleetspeakMessageResultFromFleetspeakProto(fs_msg.result)
    )
  if fs_msg.HasField("annotations"):
    result.annotations.CopyFrom(
        ApiFleetspeakAnnotationsFromFleetspeakProto(fs_msg.annotations)
    )
  return result


def ApiGetFleetspeakPendingMessagesResultFromFleetspeakProto(
    fs_res: admin_pb2.GetPendingMessagesResponse,
) -> client_pb2.ApiGetFleetspeakPendingMessagesResult:
  result = client_pb2.ApiGetFleetspeakPendingMessagesResult()
  for message in fs_res.messages:
    result.messages.append(ApiFleetspeakMessageFromFleetspeakProto(message))
  return result


def NetworkAddressFromPackedBytes(
    packed_bytes: bytes,
) -> jobs_pb2.NetworkAddress:
  """Creates a network address message from its packed bytes representation.

  Args:
    packed_bytes: Bytes of the IP address.

  Returns:
    A network address message corresponding to the given IP address.

  Raises:
    ValueError: If the given IP address has invalid length.
  """
  address = jobs_pb2.NetworkAddress()
  address.packed_bytes = packed_bytes

  if len(packed_bytes) * 8 == 32:
    address.address_type = jobs_pb2.NetworkAddress.INET
  elif len(packed_bytes) * 8 == 128:
    address.address_type = jobs_pb2.NetworkAddress.INET6
  else:
    raise ValueError(f"Unexpected IP address bytes length: {len(packed_bytes)}")

  return address


def NetworkAddressFromIPAddress(
    ip_address: Union[ipaddress.IPv4Address, ipaddress.IPv6Address],
) -> jobs_pb2.NetworkAddress:
  """Creates a network address message from a standard IP address object.

  Args:
    ip_address: IP address to convert.

  Returns:
    A network address message corresponding to the given IP address.
  """
  return NetworkAddressFromPackedBytes(ip_address.packed)


def ApiClientFromClientSnapshot(
    snapshot: objects_pb2.ClientSnapshot,
) -> client_pb2.ApiClient:
  """Creates an API client proto from a client snapshot proto."""
  api_client = client_pb2.ApiClient(
      client_id=snapshot.client_id,
      # TODO(amoser): Deprecate all urns.
      urn=f"aff4:/{snapshot.client_id}",
  )

  if snapshot.metadata and snapshot.metadata.source_flow_id:
    api_client.source_flow_id = snapshot.metadata.source_flow_id

  api_client.agent_info.CopyFrom(snapshot.startup_info.client_info)
  api_client.hardware_info.CopyFrom(snapshot.hardware_info)

  # src_proto, dest_proto, field_name, dest_field_name
  models_utils.CopyAttr(snapshot, api_client.os_info, "os_version", "version")
  models_utils.CopyAttr(snapshot, api_client.os_info, "os_release", "release")
  models_utils.CopyAttr(snapshot, api_client.os_info, "kernel")
  models_utils.CopyAttr(snapshot, api_client.os_info, "arch", "machine")
  models_utils.CopyAttr(
      snapshot, api_client.os_info, "install_time", "install_date"
  )

  if snapshot.HasField("knowledge_base"):
    api_client.knowledge_base.CopyFrom(snapshot.knowledge_base)
    models_utils.CopyAttr(
        snapshot.knowledge_base, api_client.os_info, "os", "system"
    )
    models_utils.CopyAttr(snapshot.knowledge_base, api_client.os_info, "fqdn")

  if snapshot.interfaces:
    api_client.interfaces.extend(snapshot.interfaces)
  if snapshot.volumes:
    api_client.volumes.extend(snapshot.volumes)
  if snapshot.HasField("cloud_instance"):
    api_client.cloud_instance.CopyFrom(snapshot.cloud_instance)

  api_client.age = snapshot.timestamp

  models_utils.CopyAttr(snapshot, api_client, "memory_size")
  if snapshot.HasField("startup_info"):
    models_utils.CopyAttr(
        snapshot.startup_info, api_client, "boot_time", "last_booted_at"
    )

  return api_client


def ApiClientFromClientFullInfo(
    client_id: str,
    client_info: objects_pb2.ClientFullInfo,
) -> client_pb2.ApiClient:
  """Creates an API client proto from a client full info proto."""
  api_client = client_pb2.ApiClient(client_id=client_id)

  if client_info.HasField("last_snapshot"):
    # Just a basic check to ensure that the object has correct client id.
    if client_info.last_snapshot.client_id != client_id:
      raise ValueError(
          "Invalid last snapshot client id: "
          f"{client_id} expected but "
          f"{client_info.last_snapshot.client_id} found"
      )

    api_client = ApiClientFromClientSnapshot(client_info.last_snapshot)
  else:
    # Every returned object should have `age` specified. If we cannot get this
    # information from the snapshot (because there is none), we just use the
    # time of the first observation of the client.
    if not client_info.last_snapshot.timestamp:
      api_client.age = client_info.metadata.first_seen

  # If we have it, use the boot_time / agent info from the startup
  # info which might be more recent than the interrogation
  # results. At some point we should have a dedicated API for
  # startup information instead of packing it into the API client
  # object.

  if client_info.HasField("last_startup_info"):
    models_utils.CopyAttr(
        client_info.last_startup_info, api_client, "boot_time", "last_booted_at"
    )
    if client_info.last_startup_info.HasField("client_info"):
      api_client.agent_info.CopyFrom(client_info.last_startup_info.client_info)

  if client_info.HasField("last_rrg_startup"):
    version = client_info.last_rrg_startup.metadata.version
    api_client.rrg_version = f"{version.major}.{version.minor}.{version.patch}"
    if version.pre:
      api_client.rrg_version += f"-{version.pre}"
    api_client.rrg_args.extend(client_info.last_rrg_startup.args)

  md = client_info.metadata
  if md:
    models_utils.CopyAttr(md, api_client, "first_seen", "first_seen_at")
    models_utils.CopyAttr(md, api_client, "ping", "last_seen_at")
    models_utils.CopyAttr(
        md, api_client, "last_crash_timestamp", "last_crash_at"
    )

  api_client.labels.extend(client_info.labels)

  return api_client


def SetGrrMessagePayload(
    message: jobs_pb2.GrrMessage,
    rdf_name: str,
    payload: pb_message.Message,
) -> None:
  """Sets the payload of the given GrrMessage like the RDF class would.

  * Uses underlying `args` and `args_rdf_name` fields to set the payload.
  * Properly packs the proto into the into the `payload_any` field.

  Args:
    message: The GrrMessage to set the payload of.
    rdf_name: The name of the equivalent RDFProtoStruct class of the payload.
    payload: The proto payload to set.
  """
  message.args_rdf_name = rdf_name
  message.args = payload.SerializeToString()
  # We also pack the proto into the payload_any field. This is
  # unfourtunately not used by the client, but we prefer relying on it in
  # the server when available, so for consistency we set it here too, even
  # if it's an outbound message.
  message.payload_any.Pack(payload)
