#!/usr/bin/env python
"""Get Information about network states."""

import logging
import socket

import psutil

from grr_response_client import actions
from grr_response_core.lib.rdfvalues import client_action as rdf_client_action
from grr_response_core.lib.rdfvalues import client_network as rdf_client_network


def ListNetworkConnectionsFromClient(args):
  """Gather open network connection stats.

  Args:
    args: An `rdf_client_action.ListNetworkConnectionArgs` instance.

  Yields:
    `rdf_client_network.NetworkConnection` instances.
  """
  for proc in psutil.process_iter():
    try:
      connections = proc.connections()
    except (psutil.NoSuchProcess, psutil.AccessDenied):
      continue

    for conn in connections:
      if args.listening_only and conn.status != "LISTEN":
        continue

      res = rdf_client_network.NetworkConnection()
      res.pid = proc.pid
      res.process_name = proc.name()
      if conn.family == socket.AF_INET:
        res.family = rdf_client_network.NetworkConnection.Family.INET
      elif conn.family == socket.AF_INET6:
        res.family = rdf_client_network.NetworkConnection.Family.INET6
      else:
        logging.warning(
            "Encountered unknown connection family (%s).", conn.family
        )

      if conn.type == socket.SOCK_STREAM:
        res.type = rdf_client_network.NetworkConnection.Type.SOCK_STREAM
      elif conn.type == socket.SOCK_DGRAM:
        res.type = rdf_client_network.NetworkConnection.Type.SOCK_DGRAM
      else:
        res.type = rdf_client_network.NetworkConnection.Type.UNKNOWN_SOCKET
      try:
        if conn.status:
          res.state = conn.status
      except ValueError:
        logging.warning(
            "Encountered unknown connection status (%s).", conn.status
        )

      res.local_address.ip, res.local_address.port = conn.laddr
      if conn.raddr:
        res.remote_address.ip, res.remote_address.port = conn.raddr

      yield res


class ListNetworkConnections(actions.ActionPlugin):
  """Gather open network connection stats."""

  in_rdfvalue = rdf_client_action.ListNetworkConnectionsArgs
  out_rdfvalues = [rdf_client_network.NetworkConnection]

  def Run(self, args):
    for res in ListNetworkConnectionsFromClient(args):
      self.SendReply(res)
