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


import ctypes
import ctypes.util
import logging
import os
import pwd
import stat
import tempfile

from grr.client import actions
from grr.client import client_utils_common
from grr.client import client_utils_linux
from grr.client.client_actions import standard
from grr.client.client_actions.linux import ko_patcher
from grr.lib import utils
from grr.proto import jobs_pb2
from grr.proto import sysinfo_pb2


# struct sockaddr_ll
#   {
#     unsigned short int sll_family;
#     unsigned short int sll_protocol;
#     int sll_ifindex;
#     unsigned short int sll_hatype;
#     unsigned char sll_pkttype;
#     unsigned char sll_halen;
#     unsigned char sll_addr[8];
#   };


class Sockaddrll(ctypes.Structure):
  """The sockaddr_ll struct."""
  _fields_ = [
      ("sll_family", ctypes.c_ushort),
      ("sll_protocol", ctypes.c_ushort),
      ("sll_ifindex", ctypes.c_byte * 4),
      ("sll_hatype", ctypes.c_ushort),
      ("sll_pkttype", ctypes.c_ubyte),
      ("sll_halen", ctypes.c_ubyte),
      ("sll_addr", ctypes.c_char * 8),
      ]

# struct sockaddr_in {
#   sa_family_t           sin_family;     /* Address family               */
#   __be16                sin_port;       /* Port number                  */
#   struct in_addr        sin_addr;       /* Internet address             */
#   /* Pad to size of `struct sockaddr'. */
#   unsigned char         __pad[__SOCK_SIZE__ - sizeof(short int) -
#                         sizeof(unsigned short int) - sizeof(struct in_addr)];
# };


class Sockaddrin(ctypes.Structure):
  """The sockaddr_in struct."""
  _fields_ = [
      ("sin_family", ctypes.c_ubyte),
      ("sin_port", ctypes.c_ushort),
      ("sin_addr", ctypes.c_ubyte * 4),
      ("sin_zero", ctypes.c_char * 8)
      ]

# struct sockaddr_in6 {
#         unsigned short int      sin6_family;    /* AF_INET6 */
#         __be16                  sin6_port;      /* Transport layer port # */
#         __be32                  sin6_flowinfo;  /* IPv6 flow information */
#         struct in6_addr         sin6_addr;      /* IPv6 address */
#         __u32                   sin6_scope_id;  /* scope id */
# };


class Sockaddrin6(ctypes.Structure):
  """The sockaddr_in6 struct."""
  _fields_ = [
      ("sin6_family", ctypes.c_ubyte),
      ("sin6_port", ctypes.c_ushort),
      ("sin6_flowinfo", ctypes.c_ubyte * 4),
      ("sin6_addr", ctypes.c_ubyte * 16),
      ("sin6_scope_id", ctypes.c_ubyte * 4)
      ]


# struct ifaddrs   *ifa_next;         /* Pointer to next struct */
#          char             *ifa_name;         /* Interface name */
#          u_int             ifa_flags;        /* Interface flags */
#          struct sockaddr  *ifa_addr;         /* Interface address */
#          struct sockaddr  *ifa_netmask;      /* Interface netmask */
#          struct sockaddr  *ifa_broadaddr;    /* Interface broadcast address */
#          struct sockaddr  *ifa_dstaddr;      /* P2P interface destination */
#          void             *ifa_data;         /* Address specific data */


class Ifaddrs(ctypes.Structure):
  pass

Ifaddrs._fields_ = [
    ("ifa_next", ctypes.POINTER(Ifaddrs)),
    ("ifa_name", ctypes.POINTER(ctypes.c_char)),
    ("ifa_flags", ctypes.c_uint),
    ("ifa_addr", ctypes.POINTER(ctypes.c_char)),
    ("ifa_netmask", ctypes.POINTER(ctypes.c_char)),
    ("ifa_broadaddr", ctypes.POINTER(ctypes.c_char)),
    ("ifa_destaddr", ctypes.POINTER(ctypes.c_char)),
    ("ifa_data", ctypes.POINTER(ctypes.c_char))
    ]


class EnumerateInterfaces(actions.ActionPlugin):
  """Enumerates all MAC addresses on this system."""
  out_protobuf = jobs_pb2.Interface

  def Run(self, unused_args):
    """Enumerate all interfaces and collect their MAC addresses."""
    libc = ctypes.cdll.LoadLibrary(ctypes.util.find_library("c"))
    ifa = Ifaddrs()
    p_ifa = ctypes.pointer(ifa)
    libc.getifaddrs(ctypes.pointer(p_ifa))

    addresses = {}
    macs = {}
    ifs = set()

    m = p_ifa
    while m:
      ifname = ctypes.string_at(m.contents.ifa_name)
      ifs.add(ifname)
      try:
        iffamily = ord(m.contents.ifa_addr[0])
        if iffamily == 0x2:     # AF_INET
          data = ctypes.cast(m.contents.ifa_addr, ctypes.POINTER(Sockaddrin))
          ip4 = "".join(map(chr, data.contents.sin_addr))
          address_type = jobs_pb2.NetworkAddress.INET
          address = jobs_pb2.NetworkAddress(address_type=address_type,
                                            packed_bytes=ip4)
          addresses.setdefault(ifname, []).append(address)

        if iffamily == 0x11:    # AF_PACKET
          data = ctypes.cast(m.contents.ifa_addr, ctypes.POINTER(Sockaddrll))
          addlen = data.contents.sll_halen
          macs[ifname] = data.contents.sll_addr[:addlen]

        if iffamily == 0xA:     # AF_INET6
          data = ctypes.cast(m.contents.ifa_addr, ctypes.POINTER(Sockaddrin6))
          ip6 = "".join(map(chr, data.contents.sin6_addr))
          address_type = jobs_pb2.NetworkAddress.INET6
          address = jobs_pb2.NetworkAddress(address_type=address_type,
                                            packed_bytes=ip6)
          addresses.setdefault(ifname, []).append(address)
      except ValueError:
        # Some interfaces don't have a iffamily and will raise a null pointer
        # exception. We still want to send back the name.
        pass

      m = m.contents.ifa_next

    libc.freeifaddrs(p_ifa)

    for interface in ifs:
      mac = macs.setdefault(interface, "")
      address_list = addresses.setdefault(interface, "")
      args = {"ifname": interface}
      if mac:
        args["mac_address"] = mac
      if addresses:
        args["addresses"] = address_list
      self.SendReply(**args)


class GetInstallDate(actions.ActionPlugin):
  """Estimate the install date of this system."""
  out_protobuf = jobs_pb2.DataBlob

  def Run(self, unused_args):
    self.SendReply(integer=int(os.stat("/lost+found").st_ctime))


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
      except RuntimeError:
        break

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
            except OSError:
              pass

        except ValueError:
          pass

  def Run(self, unused_args):
    """List all the filesystems mounted on the system."""
    self.devices = {}
    # For now we check all the mounted filesystems.
    self.CheckMounts("/proc/mounts")
    self.CheckMounts("/etc/mtab")

    for device, (fs_type, mnt_point) in self.devices.items():
      self.SendReply(mount_point=mnt_point, type=fs_type, device=device)


class EnumerateRunningServices(actions.ActionPlugin):
  """List running daemons.

  TODO(user): This is a placeholder and needs to be implemented.
  """
  in_protobuf = None
  out_protobuf = sysinfo_pb2.Service

  def Run(self, unused_arg):
    raise RuntimeError("Not implemented")


class InstallDriver(actions.ActionPlugin):
  """Installs a driver.

  Note that only drivers with a signature that validates with
  client_config.DRIVER_SIGNING_CERT can be loaded.
  """
  in_protobuf = jobs_pb2.InstallDriverRequest

  def Run(self, args):
    """Initializes the driver."""
    # This action might crash the box so we need to flush the transaction log.
    self.SyncTransactionLog()

    if not args.driver:
      raise IOError("No driver supplied.")

    if not client_utils_common.VerifySignedBlob(args.driver):
      raise OSError("Driver signature signing failure.")

    if args.force_reload:
      try:
        client_utils_linux.UninstallDriver(args.driver_name)
      except OSError:
        logging.warning("Failed to unload driver.")

    try:
      fd = tempfile.NamedTemporaryFile()
      data = args.driver.data
      if args.mode >= jobs_pb2.InstallDriverRequest.ENABLE:
        force = args.mode == jobs_pb2.InstallDriverRequest.FORCE
        data = ko_patcher.KernelObjectPatcher().Patch(data, force_patch=force)
      fd.write(data)
      fd.flush()
    except IOError, e:
      raise IOError("Failed to write driver file %s" % e)

    try:
      # Let exceptions pass through.
      client_utils_linux.InstallDriver(fd.name)

      try:
        line = open("/sys/class/misc/%s/dev" % args.driver_name, "r").read(
            ).rstrip()
        major, minor = line.split(":")
        os.mknod(args.path, stat.S_IFCHR | 0600,
                 os.makedev(int(major), int(minor)))
      except (IOError, OSError):
        pass

    finally:
      fd.close()


class GetMemoryInformation(actions.ActionPlugin):
  """Loads the driver for memory access and returns a Stat for the device."""

  in_protobuf = jobs_pb2.Path
  out_protobuf = jobs_pb2.MemoryInformation

  def Run(self, args):
    """Run."""
    result = self.out_protobuf()

    # Try if we can actually open the device.
    with open(args.path, "rb") as fd:
      fd.read(5)

    result.device.path = args.path
    result.device.pathtype = jobs_pb2.Path.MEMORY

    self.SendReply(result)


class UninstallDriver(actions.ActionPlugin):
  """Unloads a memory driver.

  Note that only drivers with a signature that validates with
  client_config.DRIVER_SIGNING_CERT can be uninstalled.
  """

  in_protobuf = jobs_pb2.InstallDriverRequest

  def Run(self, args):
    """Unloads a driver."""

    # First check the drver they sent us validates.
    client_utils_common.VerifySignedBlob(args.driver, verify_data=False)

    # Do the unload and let exceptions pass through.
    client_utils_linux.UninstallDriver(args.driver_name)


class UpdateAgent(standard.ExecuteBinaryCommand):
  """Updates the GRR agent to a new version."""

  in_protobuf = jobs_pb2.ExecuteBinaryRequest
  out_protobuf = jobs_pb2.ExecuteBinaryResponse

  # This is not yet supported but we need this stub here so the worker can
  # determine the correct protobufs.
