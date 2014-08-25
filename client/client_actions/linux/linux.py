#!/usr/bin/env python
"""Linux specific actions."""


import ctypes
import ctypes.util
import logging
import os
import pwd
import stat
import subprocess
import tempfile
import time

from grr.client import actions
from grr.client import client_utils_common
from grr.client.client_actions import standard
from grr.client.client_actions.linux import ko_patcher
from grr.lib import config_lib
from grr.lib import rdfvalue
from grr.lib import utils

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
      ("sll_addr", ctypes.c_ubyte * 8),
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

Ifaddrs._fields_ = [  # pylint: disable=protected-access
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
  out_rdfvalue = rdfvalue.Interface

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
          address_type = rdfvalue.NetworkAddress.Family.INET
          address = rdfvalue.NetworkAddress(address_type=address_type,
                                            packed_bytes=ip4)
          addresses.setdefault(ifname, []).append(address)

        if iffamily == 0x11:    # AF_PACKET
          data = ctypes.cast(m.contents.ifa_addr, ctypes.POINTER(Sockaddrll))
          addlen = data.contents.sll_halen
          macs[ifname] = "".join(map(chr, data.contents.sll_addr[:addlen]))

        if iffamily == 0xA:     # AF_INET6
          data = ctypes.cast(m.contents.ifa_addr, ctypes.POINTER(Sockaddrin6))
          ip6 = "".join(map(chr, data.contents.sin6_addr))
          address_type = rdfvalue.NetworkAddress.Family.INET6
          address = rdfvalue.NetworkAddress(address_type=address_type,
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
      self.SendReply(rdfvalue.Interface(**args))


class GetInstallDate(actions.ActionPlugin):
  """Estimate the install date of this system."""
  out_rdfvalue = rdfvalue.DataBlob

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
  """Enumerates all the users on this system.

  While wtmp can be collected and parsed server-side using artifacts, we keep
  this client action to avoid collecting every wtmp on every interrogate, and to
  allow for the metadata (homedir) expansion to occur on the client, where we
  have access to LDAP.

  This client action used to return rdfvalue.User.  To allow for backwards
  compatibility we expect it to be called via the LinuxUserProfiles artifact and
  we convert User to KnowledgeBaseUser in the artifact parser on the server.
  """
  out_rdfvalue = rdfvalue.KnowledgeBaseUser

  def ParseWtmp(self):
    """Parse wtmp and extract the last logon time."""
    users = {}

    wtmp_struct_size = UtmpStruct.GetSize()
    for filename in sorted(os.listdir("/var/log")):
      if filename.startswith("wtmp"):
        try:
          wtmp = open(os.path.join("/var/log", filename)).read()
        except IOError:
          continue

        for offset in xrange(0, len(wtmp), wtmp_struct_size):
          try:
            record = UtmpStruct(wtmp[offset:offset+wtmp_struct_size])
          except RuntimeError:
            break

          # Users only appear for USER_PROCESS events, others are system.
          if record.ut_type != 7:
            continue

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

        # Somehow the last login time can be < 0. There is no documentation
        # what this means so we just set it to 0 (the rdfvalue field is
        # unsigned so we can't send negative values).
        if last_login < 0:
          last_login = 0

        self.SendReply(username=utils.SmartUnicode(username),
                       homedir=utils.SmartUnicode(homedir),
                       full_name=utils.SmartUnicode(full_name),
                       last_logon=last_login*1000000)


class EnumerateFilesystems(actions.ActionPlugin):
  """Enumerate all unique filesystems local to the system."""
  acceptable_filesystems = set(["ext2", "ext3", "ext4", "vfat", "ntfs"])
  out_rdfvalue = rdfvalue.Filesystem

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
  in_rdfvalue = None
  out_rdfvalue = None

  def Run(self, unused_arg):
    raise RuntimeError("Not implemented")


class Uninstall(actions.ActionPlugin):
  """Uninstall GRR. Place holder, does nothing.

  Note this needs to handle the different distributions separately, e.g. Redhat
  vs Debian.
  """
  out_rdfvalue = rdfvalue.DataBlob

  def Run(self, unused_arg):
    raise RuntimeError("Not implemented")


class UninstallDriver(actions.ActionPlugin):
  """Unloads a memory driver.

  Note that only drivers with a signature that validates with
  client_config.DRIVER_SIGNING_CERT can be uninstalled.
  """

  in_rdfvalue = rdfvalue.DriverInstallTemplate

  @staticmethod
  def UninstallDriver(driver_name):
    """Unloads the driver.

    Args:
      driver_name: Name of the driver.

    Raises:
      OSError: On failure to uninstall.
    """
    cmd = ["/sbin/rmmod", driver_name]

    p = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    p.communicate()
    exit_status = p.returncode
    logging.info("Unloading driver finished, status: %d.", exit_status)
    if exit_status != 0:
      raise OSError("Failed to unload driver.")

  def Run(self, args):
    """Unloads a driver."""
    self.SyncTransactionLog()

    # This will raise if the signature is bad.
    args.driver.Verify(config_lib.CONFIG["Client.driver_signing_public_key"])

    # Do the unload and let exceptions pass through.
    self.UninstallDriver(args.driver_name)


class InstallDriver(UninstallDriver):
  """Installs a driver.

  Note that only drivers with a signature that validates with
  client_config.DRIVER_SIGNING_CERT can be loaded.
  """

  @staticmethod
  def InstallDriver(driver_path):
    """Loads a driver and starts it."""

    cmd = ["/sbin/insmod", driver_path]

    p = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    p.communicate()
    exit_status = p.returncode
    logging.info("Loading driver finished, status: %d.", exit_status)
    if exit_status != 0:
      raise OSError("Failed to load driver, may already be installed.")

  def Run(self, args):
    """Initializes the driver."""
    # This action might crash the box so we need to flush the
    # transaction log.
    self.SyncTransactionLog()

    # This will raise if the signature is bad.
    args.driver.Verify(config_lib.CONFIG["Client.driver_signing_public_key"])

    if args.force_reload:
      try:
        self.UninstallDriver(args.driver_name)
      except OSError:
        logging.warning("Failed to unload driver.")

    try:
      fd = tempfile.NamedTemporaryFile()
      data = args.driver.data
      if args.mode >= rdfvalue.DriverInstallTemplate.RewriteMode.ENABLE:
        force = args.mode == rdfvalue.DriverInstallTemplate.RewriteMode.FORCE
        data = ko_patcher.KernelObjectPatcher().Patch(data, force_patch=force)
      fd.write(data)
      fd.flush()
    except IOError, e:
      raise IOError("Failed to write driver file %s" % e)

    try:
      # Let exceptions pass through.
      self.InstallDriver(fd.name)

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

  in_rdfvalue = rdfvalue.PathSpec
  out_rdfvalue = rdfvalue.MemoryInformation

  def Run(self, args):
    """Run."""
    result = rdfvalue.MemoryInformation()

    # Try if we can actually open the device.
    with open(args.path, "rb") as fd:
      fd.read(5)

    result.device = rdfvalue.PathSpec(
        path=args.path,
        pathtype=rdfvalue.PathSpec.PathType.MEMORY)

    self.SendReply(result)


class UpdateAgent(standard.ExecuteBinaryCommand):
  """Updates the GRR agent to a new version."""

  suffix = "deb"

  def ProcessFile(self, path, args):

    cmd = "/usr/bin/dpkg"
    cmd_args = ["-i", path]
    time_limit = args.time_limit

    client_utils_common.Execute(cmd, cmd_args, time_limit=time_limit,
                                bypass_whitelist=True, daemon=True)

    # The installer will run in the background and kill the main process
    # so we just wait. If something goes wrong, the nanny will restart the
    # service after a short while and the client will come back to life.
    time.sleep(1000)
