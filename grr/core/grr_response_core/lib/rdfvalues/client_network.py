#!/usr/bin/env python
"""Network-related client rdfvalues."""
from __future__ import absolute_import
from __future__ import division

from __future__ import unicode_literals

import binascii
import logging

from future.builtins import str

import ipaddress

from typing import Optional
from typing import Text
from typing import Union

from grr_response_core.lib import rdfvalue
from grr_response_core.lib.rdfvalues import protodict as rdf_protodict
from grr_response_core.lib.rdfvalues import structs as rdf_structs
from grr_response_core.lib.util import precondition

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


class Connections(rdf_protodict.RDFValueArray):
  """A list of connections on the host."""
  rdf_type = NetworkConnection


IPAddress = Union[ipaddress.IPv4Address, ipaddress.IPv6Address]


class NetworkAddress(rdf_structs.RDFProtoStruct):
  """A network address.

  We'd prefer to use socket.inet_pton and  inet_ntop here, but they aren't
  available on windows before python 3.4. So we use the older IPv4 functions for
  v4 addresses and our own pure python implementations for IPv6.
  """
  protobuf = jobs_pb2.NetworkAddress
  rdf_deps = [
      rdfvalue.RDFBytes,
  ]

  @property
  def human_readable_address(self):
    addr = self.AsIPAddr()
    if addr is not None:
      return str(addr)
    else:
      return ""

  @human_readable_address.setter
  def human_readable_address(self, value):
    precondition.AssertType(value, Text)
    addr = ipaddress.ip_address(value)

    if isinstance(addr, ipaddress.IPv6Address):
      self.address_type = NetworkAddress.Family.INET6
    elif isinstance(addr, ipaddress.IPv4Address):
      self.address_type = NetworkAddress.Family.INET
    else:
      message = "IP address parsed to an unexpected value: {}".format(addr)
      raise AssertionError(message)

    self.packed_bytes = addr.packed

  def AsIPAddr(self):
    """Returns the IP as an `IPAddress` object (if packed bytes are defined)."""
    if self.packed_bytes is None:
      return None

    packed_bytes = self.packed_bytes.AsBytes()

    try:
      if self.address_type == NetworkAddress.Family.INET:
        return ipaddress.IPv4Address(packed_bytes)
      if self.address_type == NetworkAddress.Family.INET6:
        return ipaddress.IPv6Address(packed_bytes)
    except ipaddress.AddressValueError:
      logging.error("AddressValueError for %s (%s)", packed_bytes.encode("hex"),
                    self.address_type)
      raise

    message = "IP address has invalid type: {}".format(self.address_type)
    raise ValueError(message)


class DNSClientConfiguration(rdf_structs.RDFProtoStruct):
  """DNS client config."""
  protobuf = sysinfo_pb2.DNSClientConfiguration


class MacAddress(rdfvalue.RDFBytes):
  """A MAC address."""

  @property
  def human_readable_address(self):
    return binascii.hexlify(self._value).decode("ascii")

  @human_readable_address.setter
  def human_readable_address(self, value):
    precondition.AssertType(value, Text)
    self._value = binascii.unhexlify(value.encode("ascii"))


class Interface(rdf_structs.RDFProtoStruct):
  """A network interface on the client system."""
  protobuf = jobs_pb2.Interface
  rdf_deps = [
      MacAddress,
      NetworkAddress,
      rdfvalue.RDFDatetime,
  ]

  def GetIPAddresses(self):
    """Return a list of IP addresses."""
    results = []
    for address in self.addresses:
      human_readable_address = address.human_readable_address
      if human_readable_address is not None:
        results.append(human_readable_address)

    return results


class Interfaces(rdf_protodict.RDFValueArray):
  """The list of interfaces on a host."""
  rdf_type = Interface

  def GetIPAddresses(self):
    """Return the list of IP addresses."""
    results = []
    for interface in self:
      results += interface.GetIPAddresses()
    return results
