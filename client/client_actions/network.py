#!/usr/bin/env python
# Copyright 2012 Google Inc.
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.


"""Get Information about network states."""




import psutil

import logging

from grr.client import actions
from grr.lib import rdfvalue
from grr.proto import sysinfo_pb2


class Netstat(actions.ActionPlugin):
  """Gather open network connection stats."""
  in_rdfvalue = None
  out_rdfvalue = rdfvalue.NetworkConnection

  states = {
      "UNKNOWN": sysinfo_pb2.NetworkConnection.UNKNOWN,
      "LISTEN": sysinfo_pb2.NetworkConnection.LISTEN,
      "ESTABLISHED": sysinfo_pb2.NetworkConnection.ESTAB,
      "TIME_WAIT": sysinfo_pb2.NetworkConnection.TIME_WAIT,
      "CLOSE_WAIT": sysinfo_pb2.NetworkConnection.CLOSE_WAIT,
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
        res = sysinfo_pb2.NetworkConnection()
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
