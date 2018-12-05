#!/usr/bin/env python
"""Linux specific actions."""
from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

import ctypes
import ctypes.util
import glob
import io
import os
import pwd
import time


from builtins import bytes  # pylint: disable=redefined-builtin
from builtins import range  # pylint: disable=redefined-builtin
from future.utils import iteritems

from grr_response_client import actions
from grr_response_client import client_utils_common
from grr_response_client.client_actions import standard
from grr_response_core.lib import rdfvalue
from grr_response_core.lib import utils
from grr_response_core.lib.rdfvalues import client as rdf_client
from grr_response_core.lib.rdfvalues import client_fs as rdf_client_fs
from grr_response_core.lib.rdfvalues import client_network as rdf_client_network
from grr_response_core.lib.rdfvalues import protodict as rdf_protodict

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
  ]  # pyformat: disable

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
  ]  # pyformat: disable

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
]  # pyformat: disable


def EnumerateInterfacesFromClient(args):
  """Enumerate all interfaces and collect their MAC addresses."""
  del args  # Unused

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
      # TODO(hanuszczak): There are some Python 3-incompatible `chr` usages
      # here, they should be fixed.
      if iffamily == 0x2:  # AF_INET
        data = ctypes.cast(m.contents.ifa_addr, ctypes.POINTER(Sockaddrin))
        ip4 = bytes(list(data.contents.sin_addr))
        address_type = rdf_client_network.NetworkAddress.Family.INET
        address = rdf_client_network.NetworkAddress(
            address_type=address_type, packed_bytes=ip4)
        addresses.setdefault(ifname, []).append(address)

      if iffamily == 0x11:  # AF_PACKET
        data = ctypes.cast(m.contents.ifa_addr, ctypes.POINTER(Sockaddrll))
        addlen = data.contents.sll_halen
        macs[ifname] = bytes(list(data.contents.sll_addr[:addlen]))

      if iffamily == 0xA:  # AF_INET6
        data = ctypes.cast(m.contents.ifa_addr, ctypes.POINTER(Sockaddrin6))
        ip6 = bytes(list(data.contents.sin6_addr))
        address_type = rdf_client_network.NetworkAddress.Family.INET6
        address = rdf_client_network.NetworkAddress(
            address_type=address_type, packed_bytes=ip6)
        addresses.setdefault(ifname, []).append(address)
    except ValueError:
      # Some interfaces don't have a iffamily and will raise a null pointer
      # exception. We still want to send back the name.
      pass

    m = m.contents.ifa_next

  libc.freeifaddrs(p_ifa)

  for interface in ifs:
    mac = macs.setdefault(interface, b"")
    address_list = addresses.setdefault(interface, b"")
    args = {"ifname": interface}
    if mac:
      args["mac_address"] = mac
    if addresses:
      args["addresses"] = address_list
    yield rdf_client_network.Interface(**args)


class EnumerateInterfaces(actions.ActionPlugin):
  """Enumerates all MAC addresses on this system."""
  out_rdfvalues = [rdf_client_network.Interface]

  def Run(self, args):
    """Enumerate all interfaces and collect their MAC addresses."""
    for res in EnumerateInterfacesFromClient(args):
      self.SendReply(res)


class GetInstallDate(actions.ActionPlugin):
  """Estimate the install date of this system."""
  out_rdfvalues = [rdf_protodict.DataBlob, rdfvalue.RDFDatetime]

  def Run(self, unused_args):
    ctime = os.stat("/lost+found").st_ctime
    self.SendReply(rdfvalue.RDFDatetime.FromSecondsSinceEpoch(ctime))


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


def EnumerateUsersFromClient(args):
  """Enumerates all the users on this system."""

  del args  # Unused

  users = _ParseWtmp()
  for user, last_login in iteritems(users):

    # Lose the null termination
    username = user.split("\x00", 1)[0]

    if username:
      # Somehow the last login time can be < 0. There is no documentation
      # what this means so we just set it to 0 (the rdfvalue field is
      # unsigned so we can't send negative values).
      if last_login < 0:
        last_login = 0

      result = rdf_client.User(
          username=utils.SmartUnicode(username),
          last_logon=last_login * 1000000)

      try:
        pwdict = pwd.getpwnam(username)
        result.homedir = utils.SmartUnicode(pwdict.pw_dir)
        result.full_name = utils.SmartUnicode(pwdict.pw_gecos)
        result.uid = pwdict.pw_uid
        result.gid = pwdict.pw_gid
        result.shell = utils.SmartUnicode(pwdict.pw_shell)
      except KeyError:
        pass

      yield result


class EnumerateUsers(actions.ActionPlugin):
  """Enumerates all the users on this system.

  While wtmp can be collected and parsed server-side using artifacts, we keep
  this client action to avoid collecting every wtmp on every interrogate, and to
  allow for the metadata (homedir) expansion to occur on the client, where we
  have access to LDAP.
  """
  # Client versions 3.0.7.1 and older used to return KnowledgeBaseUser.
  # KnowledgeBaseUser was renamed to User.
  out_rdfvalues = [rdf_client.User, rdf_client.KnowledgeBaseUser]

  def Run(self, args):
    for res in EnumerateUsersFromClient(args):
      self.SendReply(res)


ACCEPTABLE_FILESYSTEMS = {
    "ext2",
    "ext3",
    "ext4",
    "vfat",
    "ntfs",
    "btrfs",
    "Reiserfs",
    "XFS",
    "JFS",
    "squashfs",
}


def CheckMounts(filename):
  """Parses the currently mounted devices."""
  with io.open(filename, "rb") as fd:
    for line in fd:
      try:
        device, mnt_point, fs_type, _ = line.split(" ", 3)
      except ValueError:
        continue
      if fs_type in ACCEPTABLE_FILESYSTEMS:
        if os.path.exists(device):
          yield device, fs_type, mnt_point


def EnumerateFilesystemsFromClient(args):
  """List all the filesystems mounted on the system."""
  del args  # Unused.

  filenames = ["/proc/mounts", "/etc/mtab"]

  for filename in filenames:
    for device, fs_type, mnt_point in CheckMounts(filename):
      yield rdf_client_fs.Filesystem(
          mount_point=mnt_point, type=fs_type, device=device)


class EnumerateFilesystems(actions.ActionPlugin):
  """Enumerate all unique filesystems local to the system.

  Filesystems picked from:
    https://www.kernel.org/doc/Documentation/filesystems/
  """
  out_rdfvalues = [rdf_client_fs.Filesystem]

  def Run(self, args):
    for res in EnumerateFilesystemsFromClient(args):
      self.SendReply(res)


class EnumerateRunningServices(actions.ActionPlugin):
  """List running daemons.

  TODO(user): This is a placeholder and needs to be implemented.
  """
  in_rdfvalue = None
  out_rdfvalues = [None]

  def Run(self, unused_arg):
    raise NotImplementedError("Not implemented")


class Uninstall(actions.ActionPlugin):
  """Uninstall GRR. Place holder, does nothing.

  Note this needs to handle the different distributions separately, e.g. Redhat
  vs Debian.
  """
  out_rdfvalues = [rdf_protodict.DataBlob]

  def Run(self, unused_arg):
    raise NotImplementedError("Not implemented")


class UpdateAgent(standard.ExecuteBinaryCommand):
  """Updates the GRR agent to a new version."""

  def ProcessFile(self, path, args):
    if path.endswith(".deb"):
      self._InstallDeb(path, args)
    elif path.endswith(".rpm"):
      self._InstallRpm(path)
    else:
      raise ValueError("Unknown suffix for file %s." % path)

  def _InstallDeb(self, path, args):
    cmd = "/usr/bin/dpkg"
    cmd_args = ["-i", path]
    time_limit = args.time_limit

    client_utils_common.Execute(
        cmd,
        cmd_args,
        time_limit=time_limit,
        bypass_whitelist=True,
        daemon=True)

    # The installer will run in the background and kill the main process
    # so we just wait. If something goes wrong, the nanny will restart the
    # service after a short while and the client will come back to life.
    time.sleep(1000)

  def _InstallRpm(self, path):
    """Client update for rpm based distros.

    Upgrading rpms is a bit more tricky than upgrading deb packages since there
    is a preinstall script that kills the running GRR daemon and, thus, also
    the installer process. We need to make sure we detach the child process
    properly and therefore cannot use client_utils_common.Execute().

    Args:
      path: Path to the .rpm.
    """

    pid = os.fork()
    if pid == 0:
      # This is the child that will become the installer process.

      cmd = "/bin/rpm"
      cmd_args = [cmd, "-U", "--replacepkgs", "--replacefiles", path]

      # We need to clean the environment or rpm will fail - similar to the
      # use_client_context=False parameter.
      env = os.environ.copy()
      env.pop("LD_LIBRARY_PATH", None)
      env.pop("PYTHON_PATH", None)

      # This call doesn't return.
      os.execve(cmd, cmd_args, env)

    else:
      # The installer will run in the background and kill the main process
      # so we just wait. If something goes wrong, the nanny will restart the
      # service after a short while and the client will come back to life.
      time.sleep(1000)


def _ParseWtmp():
  """Parse wtmp and utmp and extract the last logon time."""
  users = {}

  wtmp_struct_size = UtmpStruct.GetSize()
  filenames = glob.glob("/var/log/wtmp*") + ["/var/run/utmp"]

  for filename in filenames:
    try:
      wtmp = open(filename, "rb").read()
    except IOError:
      continue

    for offset in range(0, len(wtmp), wtmp_struct_size):
      try:
        record = UtmpStruct(wtmp[offset:offset + wtmp_struct_size])
      except utils.ParsingError:
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
