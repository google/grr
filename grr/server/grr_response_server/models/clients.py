#!/usr/bin/env python
"""Module with data models and helpers related to clients."""

import ipaddress
from typing import Mapping
from typing import Union

from grr_response_proto import jobs_pb2


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
