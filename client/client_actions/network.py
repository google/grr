#!/usr/bin/env python
"""Get Information about network states."""




import psutil

import logging

from grr.client import actions
from grr.lib import rdfvalue


class Netstat(actions.ActionPlugin):
  """Gather open network connection stats."""
  in_rdfvalue = None
  out_rdfvalue = rdfvalue.NetworkConnection

  def Run(self, unused_args):
    netstat = []

    for proc in psutil.process_iter():
      try:
        netstat.append((proc.pid, proc.connections()))
      except (psutil.NoSuchProcess, psutil.AccessDenied):
        pass

    for pid, connections in netstat:
      for conn in connections:
        res = rdfvalue.NetworkConnection()
        res.pid = pid
        res.family = conn.family
        res.type = conn.type

        try:
          if conn.status:
            res.state = conn.status
        except ValueError:
          logging.warn("Encountered unknown connection status (%s).",
                       conn.status)

        res.local_address.ip, res.local_address.port = conn.local_address
        if conn.remote_address:
          res.remote_address.ip, res.remote_address.port = conn.remote_address

        self.SendReply(res)
