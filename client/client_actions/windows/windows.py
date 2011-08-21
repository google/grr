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

"""Windows specific actions."""



import exceptions
import logging
import socket
import sys
import _winreg

import netbios
import win32api
import win32net
import win32service
import win32serviceutil

from grr.client import actions
from grr.client import client_config
from grr.client import comms
from grr.client import conf
from grr.client.client_actions import wmi
from grr.proto import jobs_pb2
from grr.proto import sysinfo_pb2


class GetInstallDate(actions.ActionPlugin):
  """Estimate the install date of this system."""
  out_protobuf = jobs_pb2.DataBlob

  def Run(self, unused_args):
    # We need to turn on 64 bit access as per
    # http://msdn.microsoft.com/en-us/library/aa384129(v=VS.85).aspx
    subkey = _winreg.OpenKey(
        _winreg.HKEY_LOCAL_MACHINE,
        "Software\\Microsoft\\Windows NT\\CurrentVersion",
        0,
        0x100 | _winreg.KEY_READ)
    install_date = _winreg.QueryValueEx(subkey, "InstallDate")
    self.SendReply(integer=install_date[0])


class EnumerateUsers(actions.ActionPlugin):
  """Enumerates all the users on this system."""
  out_protobuf = jobs_pb2.UserAccount

  def GetHomeDir(self, sid):
    """Get the home directory from the registry for a given SID."""

    profiles_key = r"SOFTWARE\Microsoft\Windows NT\CurrentVersion\ProfileList"
    homedir = ""

    try:
      key = _winreg.OpenKey(_winreg.HKEY_LOCAL_MACHINE,
                            profiles_key + "\\" + sid,
                            0, _winreg.KEY_WOW64_64KEY)

      (homedir, _) = _winreg.QueryValueEx(key, "ProfileImagePath")
      _winreg.CloseKey(key)

    except exceptions.WindowsError:
      pass

    return homedir

  def Run(self, unused_args):
    """Enumerate all users on this machine."""

    for acc in wmi.RunWMIQuery("SELECT * FROM Win32_UserAccount"):
      info = win32net.NetUserGetInfo(acc["Domain"], acc["Name"], 3)

      homedir = self.GetHomeDir(acc["SID"])

      self.SendReply(username=acc["Name"],
                     domain=acc["Domain"],
                     full_name=info["full_name"],
                     comment=info["comment"],
                     last_logon=info["last_logon"],
                     homedir=homedir)


class EnumerateInterfaces(actions.ActionPlugin):
  """Enumerate all MAC addresses of all NICs."""
  out_protobuf = jobs_pb2.Interface

  def Run(self, unused_args):
    """Enumerate all MAC addresses."""
    # Code sample from comp.lang.python:
    # http://groups.google.com/group/comp.lang.python/msg/fd2e7437d72c1c21
    # code ported from "HOWTO: Get the MAC Address for an Ethernet
    # Adapter" MS KB ID: Q118623
    # Get all IP addresses on the system
    _, _, ipaddress_list = socket.gethostbyname_ex(socket.gethostname())

    ncb = netbios.NCB()
    ncb.Command = netbios.NCBENUM
    la_enum = netbios.LANA_ENUM()
    ncb.Buffer = la_enum
    rc = netbios.Netbios(ncb)
    if rc != 0:
      raise RuntimeError("Unable to enumerate interfaces (%d)" % (rc,))

    # We basically try to enumerate the mac for all ip addresses using all their
    # interfaces.
    for i in range(la_enum.length):
      for ipaddress in ipaddress_list:
        ncb.Reset()
        ncb.Command = netbios.NCBRESET
        ncb.Lana_num = ord(la_enum.lana[i])
        ncb.Callname = ipaddress
        rc = netbios.Netbios(ncb)
        if rc != 0: continue

        ncb.Reset()
        ncb.Command = netbios.NCBASTAT
        ncb.Callname = ipaddress
        ncb.Lana_num = ord(la_enum.lana[i])
        adapter = netbios.ADAPTER_STATUS()
        ncb.Buffer = adapter
        rc = netbios.Netbios(ncb)
        if rc != 0: continue

        # Tell the server about it
        self.SendReply(ip_address=socket.inet_aton(ipaddress),
                       mac_address=adapter.adapter_address)


class EnumerateFilesystems(actions.ActionPlugin):
  """Enumerate all unique filesystems local to the system."""
  out_protobuf = sysinfo_pb2.Filesystem

  def Run(self, unused_args):
    """List all local filesystems mounted on this system."""
    for drive in win32api.GetLogicalDriveStrings().split("\x00"):
      if drive:
        drive = drive.lower()
        try:
          label, _, _, _, fs_type = win32api.GetVolumeInformation(drive)
          self.SendReply(device="/dev/%s" % drive[0],
                         mount_point="/%s/" % drive[0],
                         type=fs_type, label=label)
        except win32api.error: pass


class Uninstall(actions.ActionPlugin):
  """Remove the service that starts us at startup."""
  out_protobuf = jobs_pb2.DataBlob

  def Run(self, unused_arg):
    """This kills us with no cleanups."""
    logging.debug("Disabling service")
    if conf.RUNNING_AS_SERVICE:
      # Import here as we only want it if we're running as a service.
      from grr.client import win32grr

      win32serviceutil.ChangeServiceConfig(
          "win32grr.GRRMonitor", client_config.SERVICE_NAME,
          startType=win32service.SERVICE_DISABLED)
      svc_config = QueryService(client_config.SERVICE_NAME)
      if svc_config[1] == win32service.SERVICE_DISABLED:
        logging.info("Disabled service successfully")
        self.SendReply(string="Service disabled.")
      else:
        self.SendReply(string="Service failed to disable.")
    else:
      self.SendReply(string="Not running as service.")


class Kill(actions.ActionPlugin):
  """This ourselves with no cleanups."""
  out_protobuf = jobs_pb2.GrrMessage

  def Run(self, unused_arg):
    """Run the kill."""
    if isinstance(self.grr_context, comms.SlaveContext):
      sys.exit(0)
    else:
      # Kill off children if we are running separated.
      if isinstance(self.grr_context, comms.ProcessSeparatedContext):
        logging.info("Requesting termination of slaves.")
        self.grr_context.Terminate()

      # Send a message back to the service to say that we are about to shutdown.
      reply = jobs_pb2.GrrStatus()
      reply.status = jobs_pb2.GrrStatus.OK
      # Queue up the response message.
      self.SendReply(reply, message_type=jobs_pb2.GrrMessage.STATUS,
                     jump_queue=True)
      # Force a comms run.
      status = self.grr_context.RunOnce()
      if status.code != 200:
        logging.error("Could not communicate our own death, re-death predicted")

      if conf.RUNNING_AS_SERVICE:
        # Terminate service
        win32serviceutil.StopService(client_config.SERVICE_NAME)
      else:
        # Die ourselves.
        logging.info("Dying on request.")
        sys.exit(0)


def QueryService(svc_name):
  """Query service and get its config."""
  hscm = win32service.OpenSCManager(None, None,
                                    win32service.SC_MANAGER_ALL_ACCESS)
  result = None
  try:
    hs = win32serviceutil.SmartOpenService(hscm, svc_name,
                                           win32service.SERVICE_ALL_ACCESS)
    result = win32service.QueryServiceConfig(hs)
    win32service.CloseServiceHandle(hs)
  finally:
    win32service.CloseServiceHandle(hscm)

  return result
