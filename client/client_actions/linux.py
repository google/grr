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


"""Linux specific actions."""


import fcntl
import logging
import os
import pwd
import re
import socket
import struct

from grr.client import actions
from grr.client import comms
from grr.lib import utils
from grr.proto import jobs_pb2
from grr.proto import sysinfo_pb2


class GetInstallDate(actions.ActionPlugin):
  """Estimate the install date of this system."""
  out_protobuf = jobs_pb2.DataBlob

  def Run(self, unused_args):
    stat = os.stat("/lost+found")
    self.SendReply(integer=int(stat.st_ctime))


class UtmpStruct(utils.Struct):
  """Parse wtmp file from utmp.h."""
  _fields = [
      ("h", "ut_type"),
      ("i", "ut_pid"),
      ("32s", "ut_line"),
      ("4s", "ut_id"),
      ("32s", "ut_user"),
      ("256s", "ut_host"),
      ("i", "ut_exit"),
      ("i", "ut_session"),
      ("i", "tv_sec"),
      ("i", "tv_usec"),
      ("4i", "ut_addr_v6"),
      ("20s", "unused"),
      ]


class EnumerateUsers(actions.ActionPlugin):
  """Enumerates all the users on this system."""
  out_protobuf = jobs_pb2.UserAccount

  def ParseWtmp(self):
    """Parse wtmp and extract the last logon time."""
    users = {}
    wtmp = open("/var/log/wtmp").read()
    while wtmp:
      try:
        record = UtmpStruct(wtmp)
      except RuntimeError: break

      wtmp = wtmp[record.size:]

      try:
        if users[record.ut_user] < record.tv_sec:
          users[record.ut_user] = record.tv_sec
      except KeyError:
        users[record.ut_user] = record.tv_sec

    return users

  def Run(self, unused_args):
    """Enumerates all the users on this system."""
    users = self.ParseWtmp()
    for user, last_login in users.iteritems():
      # Lose the null termination
      username = user.split("\x00", 1)[0]

      if username:
        try:
          pwdict = pwd.getpwnam(username)
          homedir = pwdict[5]    # pw_dir
          full_name = pwdict[4]  # pw_gecos
        except KeyError:
          homedir = ""
          full_name = ""

        self.SendReply(username=username, homedir=homedir,
                       full_name=full_name, last_logon=last_login*1000000)


class EnumerateInterfaces(actions.ActionPlugin):
  """Enumerates all MAC addresses on this system."""
  out_protobuf = jobs_pb2.Interface

  def Run(self, unused_args):
    """Enumerate all interfaces and collect their MAC addresses."""
    # First get a list of all interfaces (Not all of them are
    # necessarily real)
    interfaces = []
    for line in open("/proc/net/dev"):
      m = re.match(r"\s*([^:]+):", line)
      if m:
        interfaces.append(m.group(1))

    # Now for each interface recover MAC address
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, 0)
    for interface in interfaces:
      try:
        # From /usr/include/linux/sockios.h:
        #  define SIOCGIFHWADDR   0x8927          /* Get hardware address*/
        mac = fcntl.ioctl(s.fileno(), 0x8927,
                          struct.pack("256s", interface))[18:18+6]

        # IP addresses assigned to interfaces change all the time but
        # it might be worth recording them here as a time snapshot

        #define SIOCGIFADDR     0x8915          /* get PA address */
        ip_address = fcntl.ioctl(s.fileno(), 0x8915,
                                 struct.pack("256s", interface))[20:24]

        # Send the server info about this interface
        self.SendReply(mac_address=mac, ip_address=ip_address,
                       ifname=interface)

      except IOError:
        pass


class EnumerateFilesystems(actions.ActionPlugin):
  """Enumerate all unique filesystems local to the system."""
  acceptable_filesystems = set(["ext2", "ext3", "ext4", "vfat", "ntfs"])
  out_protobuf = sysinfo_pb2.Filesystem

  def CheckMounts(self, filename):
    """Parses the currently mounted devices."""
    # This handles the case where the same filesystem is mounted on
    # multiple places.
    with open(filename) as fd:
      for line in fd:
        try:
          device, mnt_point, fs_type, _ = line.split(" ", 3)
          if fs_type in self.acceptable_filesystems:
            try:
              os.stat(device)
              self.devices[device] = (fs_type, mnt_point)
            except OSError: pass

        except ValueError: pass

  def Run(self, unused_args):
    """List all the filesystems mounted on the system."""
    self.devices = {}
    # For now we check all the mounted filesystems.
    self.CheckMounts("/proc/mounts")
    self.CheckMounts("/etc/mtab")

    for device, (fs_type, mnt_point) in self.devices.items():
      self.SendReply(mount_point=mnt_point, type=fs_type, device=device)


class Kill(actions.ActionPlugin):
  """This ourselves with no cleanups."""

  def Run(self, unused_arg):
    if isinstance(self.grr_context, comms.ProcessSeparatedContext):
      logging.info("Terminating slaves.")
      self.grr_context.Terminate()

    # Die ourselves.
    logging.info("Dying on request.")
    os._exit(0)
