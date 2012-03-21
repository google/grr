#!/usr/bin/env python

# Copyright 2010 Google Inc.
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


# This file inspired from recipe:
# http://code.activestate.com/recipes/392572-using-the-win32-iphelper-api/

import ctypes
import socket

from grr.client import actions
from grr.proto import sysinfo_pb2

# We want to use the standard microsoft API names for structs

DWORD = ctypes.c_ulong
ULONGLONG = ctypes.c_ulonglong
LARGE_INTEGER = ctypes.c_ulonglong
NO_ERROR = 0
NULL = ""

AF_INET = 2
AF_INET6 = 10

TCP_TABLE_BASIC_LISTENER = 0
TCP_TABLE_BASIC_CONNECTIONS = 1
TCP_TABLE_BASIC_ALL = 2
TCP_TABLE_OWNER_PID_LISTENER = 3
TCP_TABLE_OWNER_PID_CONNECTIONS = 4
TCP_TABLE_OWNER_PID_ALL = 5
TCP_TABLE_OWNER_MODULE_LISTENER = 6
TCP_TABLE_OWNER_MODULE_CONNECTIONS = 7
TCP_TABLE_OWNER_MODULE_ALL = 8

UDP_TABLE_BASIC = 0
UDP_TABLE_OWNER_PID = 1
UDP_TABLE_OWNER_MODULE = 2

TCPIP_OWNING_MODULE_SIZE = 16

ANY_SIZE = 1


# defing our MIB row structures
class MIB_TCPROW_OWNER_MODULE(ctypes.Structure):
  _fields_ = [("dwState", DWORD),
              ("dwLocalAddr", DWORD),
              ("dwLocalPort", DWORD),
              ("dwRemoteAddr", DWORD),
              ("dwRemotePort", DWORD),
              ("dwOwningPid", DWORD),
              ("liCreateTimestamp", LARGE_INTEGER),
              ("OwningModuleInfo", ULONGLONG * TCPIP_OWNING_MODULE_SIZE)
             ]


class MIB_UDPROW_OWNER_MODULE(ctypes.Structure):
  _fields_ = [("dwLocalAddr", DWORD),
              ("dwLocalPort", DWORD),
              ("dwOwningPid", DWORD),
              ("liCreateTimestamp", LARGE_INTEGER),
              ("dwFlags", DWORD),
              ("OwningModuleInfo", ULONGLONG * TCPIP_OWNING_MODULE_SIZE)
             ]


class Netstat(actions.ActionPlugin):
  """Gather open network connection stats."""
  in_protobuf = None
  out_protobuf = sysinfo_pb2.Connection

  def Run(self, unused_args):
    """Use the iphelper API to gather all network stats."""
    for connection in self.SendTcpInfo():
      self.SendReply(connection)

    for connection in self.SendUdpInfo():
      self.SendReply(connection)

  def SendTcpInfo(self):
    """Gather information about TCP sockets."""
    dwSize = DWORD(0)

    # call once to get dwSize
    ctypes.windll.iphlpapi.GetExtendedTcpTable(
        NULL, ctypes.byref(dwSize), 0,
        AF_INET, TCP_TABLE_OWNER_MODULE_ALL, 0)

    class MIB_TCPTABLE_OWNER_MODULE(ctypes.Structure):
      _fields_ = [("dwNumEntries", DWORD),
                  ("table", MIB_TCPROW_OWNER_MODULE * dwSize.value)]

    tcpTable = MIB_TCPTABLE_OWNER_MODULE()
    err = ctypes.windll.iphlpapi.GetExtendedTcpTable(
        ctypes.byref(tcpTable), ctypes.byref(dwSize), 0,
        AF_INET, TCP_TABLE_OWNER_MODULE_ALL, 0)

    # now make the call to GetTcpTable to get the data
    if err != NO_ERROR:
      raise RuntimeError("GetExtendedTcpTable returned %s" % err)

    for i in range(0, tcpTable.dwNumEntries):
      item = tcpTable.table[i]

      yield sysinfo_pb2.Connection(
          type=sysinfo_pb2.Connection.TCP,
          state=item.dwState,
          local_addr=socket.ntohl(item.dwLocalAddr),
          local_port=socket.ntohs(item.dwLocalPort),
          remote_addr=socket.ntohl(item.dwRemoteAddr),
          remote_port=socket.ntohs(item.dwRemotePort),
          pid=item.dwOwningPid,
          ctime=item.liCreateTimestamp)

  def SendUdpInfo(self):
    """Gather information about UDP sockets."""
    dwSize = DWORD(0)

    # call once to get dwSize
    ctypes.windll.iphlpapi.GetExtendedUdpTable(
        NULL, ctypes.byref(dwSize), 0,
        AF_INET, UDP_TABLE_OWNER_MODULE, 0)

    class MIB_UDPTABLE_OWNER_MODULE(ctypes.Structure):
      _fields_ = [("dwNumEntries", DWORD),
                  ("table", MIB_UDPROW_OWNER_MODULE * dwSize.value)]

    udpTable = MIB_UDPTABLE_OWNER_MODULE()
    err = ctypes.windll.iphlpapi.GetExtendedUdpTable(
        ctypes.byref(udpTable), ctypes.byref(dwSize), 0,
        AF_INET, UDP_TABLE_OWNER_MODULE, 0)

    # now make the call to GetTcpTable to get the data
    if err != NO_ERROR:
      raise RuntimeError("GetExtendedUdpTable returned %s" % err)

    for i in range(0, udpTable.dwNumEntries):
      item = udpTable.table[i]

      yield sysinfo_pb2.Connection(
          type=sysinfo_pb2.Connection.UDP,
          local_addr=socket.ntohl(item.dwLocalAddr),
          local_port=socket.ntohs(item.dwLocalPort),
          pid=item.dwOwningPid,
          ctime=item.liCreateTimestamp)
