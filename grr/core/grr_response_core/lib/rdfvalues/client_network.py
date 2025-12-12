#!/usr/bin/env python
"""Network-related client rdfvalues."""

import binascii
import ipaddress
import logging
from typing import Optional, Union

from grr_response_core.lib import rdfvalue
from grr_response_core.lib.rdfvalues import structs as rdf_structs
from grr_response_core.lib.util import precondition
from grr_response_core.lib.util import text
from grr_response_proto import jobs_pb2
from grr_response_proto import sysinfo_pb2


class NetworkEndpoint(rdf_structs.RDFProtoStruct):
  protobuf = sysinfo_pb2.NetworkEndpoint


class NetworkConnection(rdf_structs.RDFProtoStruct):
  """Information about a single network connection."""

  protobuf = sysinfo_pb2.NetworkConnection
  rdf_deps = [
      NetworkEndpoint,
  ]


IPAddress = Union[ipaddress.IPv4Address, ipaddress.IPv6Address]


class NetworkAddress(rdf_structs.RDFProtoStruct):
  """A network address.

  We'd prefer to use socket.inet_pton and  inet_ntop here, but they aren't
  available on windows before python 3.4. So we use the older IPv4 functions for
  v4 addresses and our own pure python implementations for IPv6.
  """

  protobuf = jobs_pb2.NetworkAddress

  @classmethod
  def FromPackedBytes(cls, ip: bytes) -> "NetworkAddress":
    result = cls()
    result.packed_bytes = ip

    if len(ip) * 8 == 32:
      result.address_type = jobs_pb2.NetworkAddress.INET
    elif len(ip) * 8 == 128:
      result.address_type = jobs_pb2.NetworkAddress.INET6
    else:
      message = f"Unexpected IP address length: {len(ip)}"
      raise ValueError(message)

    return result

  @property
  def human_readable_address(self) -> str:
    addr = self.AsIPAddr()
    if addr is not None:
      return str(addr)
    else:
      return ""

  @human_readable_address.setter
  def human_readable_address(self, value: str) -> None:
    precondition.AssertType(value, str)
    addr = ipaddress.ip_address(value)

    if isinstance(addr, ipaddress.IPv6Address):
      self.address_type = NetworkAddress.Family.INET6
    elif isinstance(addr, ipaddress.IPv4Address):
      self.address_type = NetworkAddress.Family.INET
    else:
      message = "IP address parsed to an unexpected value: {}".format(addr)
      raise AssertionError(message)

    self.packed_bytes = addr.packed

  def AsIPAddr(self) -> Optional[IPAddress]:
    """Returns the IP as an `IPAddress` object (if packed bytes are defined)."""
    precondition.AssertOptionalType(self.packed_bytes, bytes)

    if self.packed_bytes is None:
      return None

    try:
      if self.address_type == NetworkAddress.Family.INET:
        return ipaddress.IPv4Address(self.packed_bytes)
      if self.address_type == NetworkAddress.Family.INET6:
        return ipaddress.IPv6Address(self.packed_bytes)
    except ipaddress.AddressValueError:
      hex_packed_bytes = text.Hexify(self.packed_bytes)
      logging.error(
          "AddressValueError for %s (%s)", hex_packed_bytes, self.address_type
      )
      raise

    message = "IP address has invalid type: {}".format(self.address_type)
    raise ValueError(message)


class DNSClientConfiguration(rdf_structs.RDFProtoStruct):
  """DNS client config."""

  protobuf = sysinfo_pb2.DNSClientConfiguration


class MacAddress(rdfvalue.RDFBytes):
  """A MAC address."""

  @property
  def human_readable_address(self) -> str:
    return text.Hexify(self._value)

  @classmethod
  def FromHumanReadableAddress(cls, string: str):
    precondition.AssertType(string, str)
    return cls(binascii.unhexlify(string.encode("ascii")))


class Interface(rdf_structs.RDFProtoStruct):
  """A network interface on the client system."""

  protobuf = jobs_pb2.Interface
  rdf_deps = [
      MacAddress,
      NetworkAddress,
  ]

  def GetIPAddresses(self):
    """Return a list of IP addresses."""
    results = []
    for address in self.addresses:
      human_readable_address = address.human_readable_address
      if human_readable_address is not None:
        results.append(human_readable_address)

    return results
