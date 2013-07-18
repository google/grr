#!/usr/bin/env python
# Copyright 2012 Google Inc. All Rights Reserved.

"""Get Information about network states."""




import psutil

import logging

from grr.client import actions
from grr.lib import rdfvalue


class Netstat(actions.ActionPlugin):
  """Gather open network connection stats."""
  in_rdfvalue = None
  out_rdfvalue = rdfvalue.NetworkConnection

  states = {
      "UNKNOWN": rdfvalue.NetworkConnection.State.UNKNOWN,
      "LISTEN": rdfvalue.NetworkConnection.State.LISTEN,
      "ESTABLISHED": rdfvalue.NetworkConnection.State.ESTAB,
      "TIME_WAIT": rdfvalue.NetworkConnection.State.TIME_WAIT,
      "CLOSE_WAIT": rdfvalue.NetworkConnection.State.CLOSE_WAIT,
      }

  def Run(self, unused_args):
    netstat = []

    for proc in psutil.process_iter():
      try:
        netstat.append((proc.pid, proc.get_connections()))
      except (psutil.NoSuchProcess, psutil.AccessDenied):
        pass

    for pid, connections in netstat:
      for conn in connections:
        res = rdfvalue.NetworkConnection()
        res.pid = pid
        res.family = conn.family
        res.type = conn.type

        try:
          res.state = self.states[conn.status]
        except KeyError:
          if conn.status:
            logging.warn("Encountered unknown connection status (%s).",
                         conn.status)

        res.local_address.ip, res.local_address.port = conn.local_address
        if conn.remote_address:
          res.remote_address.ip, res.remote_address.port = conn.remote_address

        self.SendReply(res)
