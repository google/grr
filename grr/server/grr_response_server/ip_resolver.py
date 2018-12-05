#!/usr/bin/env python
"""A resolver for ip addresses to hostnames."""
from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

import logging
import socket


from future.utils import with_metaclass
import ipaddr

from grr_response_core import config
from grr_response_core.lib import registry
from grr_response_core.lib import utils


class IPInfo(object):
  UNKNOWN = 0
  INTERNAL = 1
  EXTERNAL = 2
  VPN = 3


class IPResolverBase(with_metaclass(registry.MetaclassRegistry, object)):

  def RetrieveIPInfo(self, ip):
    raise NotImplementedError()


class IPResolver(IPResolverBase):
  """Resolves IP addresses to hostnames."""

  def __init__(self):
    super(IPResolver, self).__init__()
    self.cache = utils.FastStore(max_size=100)

  def RetrieveIPInfo(self, ip):
    if not ip:
      return (IPInfo.UNKNOWN, "No ip information.")
    if not isinstance(ip, (ipaddr.IPv4Address, ipaddr.IPv6Address)):
      raise ValueError("Excepted ipaddr.IPAddress object, got %s" % type(ip))

    ip_str = utils.SmartStr(ip)
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


class IPResolverInit(registry.InitHook):

  def RunOnce(self):
    global IP_RESOLVER
    ip_resolver_cls_name = config.CONFIG["Server.ip_resolver_class"]
    logging.debug("Using ip resolver: %s", ip_resolver_cls_name)
    cls = IPResolverBase.GetPlugin(ip_resolver_cls_name)

    IP_RESOLVER = cls()
