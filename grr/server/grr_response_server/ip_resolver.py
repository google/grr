#!/usr/bin/env python
"""A resolver for ip addresses to hostnames."""

import ipaddress
import logging
import socket

from grr_response_core import config
from grr_response_core.lib import utils
from grr_response_core.lib.registry import MetaclassRegistry
from grr_response_core.lib.util import precondition


class IPInfo(object):
  UNKNOWN = 0
  INTERNAL = 1
  EXTERNAL = 2
  VPN = 3


class IPResolverBase(metaclass=MetaclassRegistry):

  def RetrieveIPInfo(self, ip):
    raise NotImplementedError()


class IPResolver(IPResolverBase):
  """Resolves IP addresses to hostnames."""

  def __init__(self):
    super().__init__()
    self.cache = utils.FastStore(max_size=100)

  def RetrieveIPInfo(self, ip):
    precondition.AssertOptionalType(
        ip, (ipaddress.IPv4Address, ipaddress.IPv6Address)
    )

    if ip is None:
      return (IPInfo.UNKNOWN, "No ip information.")

    ip_str = str(ip)
    try:
      return self.cache.Get(ip_str)
    except KeyError:
      pass

    if ip.version == 6:
      res = self.RetrieveIP6Info(ip)
    else:
      res = self.RetrieveIP4Info(ip)

    self.cache.Put(ip_str, res)
    return res

  def RetrieveIP4Info(self, ip):
    """Retrieves information for an IP4 address."""
    if ip.is_private:
      return (IPInfo.INTERNAL, "Internal IP address.")
    try:
      # It's an external IP, let's try to do a reverse lookup.
      res = socket.getnameinfo((str(ip), 0), socket.NI_NAMEREQD)
      return (IPInfo.EXTERNAL, res[0])
    except (socket.error, socket.herror, socket.gaierror):
      return (IPInfo.EXTERNAL, "Unknown IP address.")

  def RetrieveIP6Info(self, ip):
    """Retrieves information for an IP6 address."""
    _ = ip
    return (IPInfo.INTERNAL, "Internal IP6 address.")


IP_RESOLVER = None


@utils.RunOnce
def IPResolverInitOnce():
  """Initializes IP resolver."""
  global IP_RESOLVER
  ip_resolver_cls_name = config.CONFIG["Server.ip_resolver_class"]
  logging.debug("Using ip resolver: %s", ip_resolver_cls_name)
  cls = IPResolverBase.GetPlugin(ip_resolver_cls_name)

  IP_RESOLVER = cls()
