#!/usr/bin/env python
"""Get Information about network states."""

import logging

import psutil

from grr_response_client import actions
from grr.lib.rdfvalues import client as rdf_client


class ListNetworkConnections(actions.ActionPlugin):
  """Gather open network connection stats."""
  in_rdfvalue = rdf_client.ListNetworkConnectionsArgs
  out_rdfvalues = [rdf_client.NetworkConnection]

  def Run(self, args):
    for proc in psutil.process_iter():
      try:
        connections = proc.connections()
      except (psutil.NoSuchProcess, psutil.AccessDenied):
        continue

      for conn in connections:
        if args.listening_only and conn.status != "LISTEN":
          continue

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
