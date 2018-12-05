#!/usr/bin/env python
"""Network-related client rdfvalues."""

from __future__ import absolute_import
from __future__ import division

import socket

import ipaddr

from grr_response_core.lib import ipv6_utils
from grr_response_core.lib import rdfvalue

from grr_response_core.lib.rdfvalues import protodict as rdf_protodict
from grr_response_core.lib.rdfvalues import structs as rdf_structs

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
    if self.human_readable:
      return self.human_readable
    else:
      try:
        if self.address_type == NetworkAddress.Family.INET:
          return ipv6_utils.InetNtoP(socket.AF_INET, str(self.packed_bytes))
        else:
          return ipv6_utils.InetNtoP(socket.AF_INET6, str(self.packed_bytes))
      except ValueError as e:
        return str(e)

  @human_readable_address.setter
  def human_readable_address(self, value):
    if ":" in value:
      # IPv6
      self.address_type = NetworkAddress.Family.INET6
      self.packed_bytes = ipv6_utils.InetPtoN(socket.AF_INET6, value)
    else:
      # IPv4
      self.address_type = NetworkAddress.Family.INET
      self.packed_bytes = ipv6_utils.InetPtoN(socket.AF_INET, value)

  def AsIPAddr(self):
    """Returns the ip as an ipaddr.IPADdress object.

    Raises a ValueError if the stored data does not represent a valid ip.
    """
    try:
      if self.address_type == NetworkAddress.Family.INET:
        return ipaddr.IPv4Address(self.human_readable_address)
      elif self.address_type == NetworkAddress.Family.INET6:
        return ipaddr.IPv6Address(self.human_readable_address)
      else:
        raise ValueError("Unknown address type: %d" % self.address_type)
    except ipaddr.AddressValueError:
      raise ValueError("Invalid IP address: %s" % self.human_readable_address)


class DNSClientConfiguration(rdf_structs.RDFProtoStruct):
  """DNS client config."""
  protobuf = sysinfo_pb2.DNSClientConfiguration


class MacAddress(rdfvalue.RDFBytes):
  """A MAC address."""

  @property
  def human_readable_address(self):
    return self._value.encode("hex")

  @human_readable_address.setter
  def human_readable_address(self, value):
    self._value = value.decode("hex")


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
      if address.human_readable:
        results.append(address.human_readable)
      else:
        if address.address_type == NetworkAddress.Family.INET:
          results.append(
              ipv6_utils.InetNtoP(socket.AF_INET, str(address.packed_bytes)))
        else:
          results.append(
              ipv6_utils.InetNtoP(socket.AF_INET6, str(address.packed_bytes)))
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
