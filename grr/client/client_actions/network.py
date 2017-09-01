#!/usr/bin/env python
"""Get Information about network states."""

import logging

import psutil

from grr.client import actions
from grr.lib.rdfvalues import client as rdf_client


class Netstat(actions.ActionPlugin):
  """Gather open network connection stats."""
  in_rdfvalue = None
  out_rdfvalues = [rdf_client.NetworkConnection]

  def Run(self, unused_args):
    for proc in psutil.process_iter():
      try:
        connections = proc.connections()
      except (psutil.NoSuchProcess, psutil.AccessDenied):
        continue

      for conn in connections:
        res = rdf_client.NetworkConnection()
        res.pid = proc.pid
        res.process_name = proc.name()
        res.family = conn.family
        res.type = conn.type

        try:
          if conn.status:
            res.state = conn.status
        except ValueError:
          logging.warn("Encountered unknown connection status (%s).",
                       conn.status)

        res.local_address.ip, res.local_address.port = conn.laddr
        if conn.raddr:
          res.remote_address.ip, res.remote_address.port = conn.raddr

        self.SendReply(res)
