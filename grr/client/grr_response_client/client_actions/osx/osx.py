#!/usr/bin/env python
"""OSX specific actions.

Most of these actions share an interface (in/out rdfvalues) with linux actions
of the same name. OSX-only actions are registered with the server via
libs/server_stubs.py
"""
from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

import ctypes
import logging
import os
import re
import shutil
import socket
import struct
import sys


from future.builtins import bytes
from future.utils import iteritems
from future.utils import itervalues
import pytsk3

from grr_response_client import actions
from grr_response_client import client_utils_common
from grr_response_client import client_utils_osx
from grr_response_client.client_actions import standard
from grr_response_client.osx.objc import ServiceManagement

from grr_response_core import config
from grr_response_core.lib import rdfvalue
from grr_response_core.lib.parsers import osx_launchd
from grr_response_core.lib.rdfvalues import client as rdf_client
from grr_response_core.lib.rdfvalues import client_action as rdf_client_action
from grr_response_core.lib.rdfvalues import client_fs as rdf_client_fs
from grr_response_core.lib.rdfvalues import client_network as rdf_client_network
from grr_response_core.lib.rdfvalues import protodict as rdf_protodict
from grr_response_core.lib.util import precondition


class Error(Exception):
  """Base error class."""


class UnsupportedOSVersionError(Error):
  """This action not supported on this os version."""


# https://github.com/apple/darwin-xnu/blob/master/bsd/sys/_types/_sa_family_t.h
#
# typedef __uint8_t sa_family_t;

sa_family_t = ctypes.c_uint8  # pylint: disable=invalid-name

# https://developer.apple.com/documentation/kernel/in_port_t?language=objc
#
# typedef __uint16_t in_port_t;

in_port_t = ctypes.c_uint16  # pylint: disable=invalid-name

# https://developer.apple.com/documentation/kernel/in_addr_t?language=objc
#
# typedef __uint32_t in_addr_t;

in_addr_t = ctypes.c_uint32  # pylint: disable=invalid-name

# https://github.com/apple/darwin-xnu/blob/master/bsd/netinet6/in6.h
#
# struct in6_addr {
#     union {
#         __uint8_t   __u6_addr8[16];
#         __uint16_t  __u6_addr16[8];
#         __uint32_t  __u6_addr32[4];
#     } __u6_addr; /* 128-bit IP6 address */
# };

in6_addr_t = ctypes.c_uint8 * 16  # pylint: disable=invalid-name

# https://github.com/apple/darwin-xnu/blob/master/bsd/sys/socket.h
#
# struct sockaddr {
#     __uint8_t   sa_len;       /* total length */
#     sa_family_t sa_family;    /* [XSI] address family */
#     char        sa_data[14];  /* [XSI] addr value (actually larger) */
# };


class Sockaddr(ctypes.Structure):
  """The sockaddr structure."""

  _fields_ = [
      ("sa_len", ctypes.c_uint8),
      ("sa_family", sa_family_t),
      ("sa_data", ctypes.c_ubyte * 14),
  ]


# https://github.com/apple/darwin-xnu/blob/master/bsd/net/if_dl.h
#
# struct sockaddr_dl {
#       u_char  sdl_len;        /* Total length of sockaddr */
#       u_char  sdl_family;     /* AF_LINK */
#       u_short sdl_index;      /* if != 0, system given index for interface */
#       u_char  sdl_type;       /* interface type */
#       u_char  sdl_nlen;       /* interface name length, no trailing 0 reqd. */
#       u_char  sdl_alen;       /* link level address length */
#       u_char  sdl_slen;       /* link layer selector length */
#       char    sdl_data[12];   /* minimum work area, can be larger;
#                                  contains both if name and ll address */
# };

# Interfaces can have names up to 15 chars long and sdl_data contains name + mac
# but no separators - we need to make sdl_data at least 15+6 bytes.


class Sockaddrdl(ctypes.Structure):
  """The sockaddr_dl struct."""
  _fields_ = [
      ("sdl_len", ctypes.c_ubyte),
      ("sdl_family", ctypes.c_ubyte),
      ("sdl_index", ctypes.c_ushort),
      ("sdl_type", ctypes.c_ubyte),
      ("sdl_nlen", ctypes.c_ubyte),
      ("sdl_alen", ctypes.c_ubyte),
      ("sdl_slen", ctypes.c_ubyte),
      ("sdl_data", ctypes.c_ubyte * 24),
  ]


# struct sockaddr_in {
#         __uint8_t       sin_len;
#         sa_family_t     sin_family;
#         in_port_t       sin_port;
#         struct  in_addr sin_addr;
#         char            sin_zero[8];
# };


class Sockaddrin(ctypes.Structure):
  """The sockaddr_in struct."""
  _fields_ = [
      ("sin_len", ctypes.c_ubyte),
      ("sin_family", sa_family_t),
      ("sin_port", in_port_t),
      ("sin_addr", in_addr_t),
      ("sin_zero", ctypes.c_ubyte * 8),
  ]


# struct sockaddr_in6 {
#         __uint8_t       sin6_len;       /* length of this struct */
#         sa_family_t     sin6_family;    /* AF_INET6 (sa_family_t) */
#         in_port_t       sin6_port;      /* Transport layer port */
#         __uint32_t      sin6_flowinfo;  /* IP6 flow information */
#         struct in6_addr sin6_addr;      /* IP6 address */
#         __uint32_t      sin6_scope_id;  /* scope zone index */
# };


class Sockaddrin6(ctypes.Structure):
  """The sockaddr_in6 struct."""
  _fields_ = [
      ("sin6_len", ctypes.c_ubyte),
      ("sin6_family", sa_family_t),
      ("sin6_port", ctypes.c_ushort),
      ("sin6_flowinfo", ctypes.c_uint32),
      ("sin6_addr", in6_addr_t),
      ("sin6_scope_id", ctypes.c_uint32),
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
    ("ifa_addr", ctypes.POINTER(Sockaddr)),
    ("ifa_netmask", ctypes.POINTER(Sockaddr)),
    ("ifa_broadaddr", ctypes.POINTER(Sockaddr)),
    ("ifa_destaddr", ctypes.POINTER(Sockaddr)),
    ("ifa_data", ctypes.c_void_p),
]

AF_INET = socket.AF_INET
AF_INET6 = socket.AF_INET6
AF_LINK = 0x12


def IterIfaddrs(ifaddrs):
  """Iterates over contents of the intrusive linked list of `ifaddrs`.

  Args:
    ifaddrs: A pointer to the first node of `ifaddrs` linked list. Can be NULL.

  Yields:
    Instances of `Ifaddr`.
  """
  precondition.AssertOptionalType(ifaddrs, ctypes.POINTER(Ifaddrs))

  while ifaddrs:
    yield ifaddrs.contents
    ifaddrs = ifaddrs.contents.ifa_next


def ParseIfaddrs(ifaddrs):
  """Parses contents of the intrusive linked list of `ifaddrs`.

  Args:
    ifaddrs: A pointer to the first node of `ifaddrs` linked list. Can be NULL.

  Returns:
    An iterator over instances of `rdf_client_network.Interface`.
  """
  precondition.AssertOptionalType(ifaddrs, ctypes.POINTER(Ifaddrs))

  ifaces = {}

  for ifaddr in IterIfaddrs(ifaddrs):
    ifname = ctypes.string_at(ifaddr.ifa_name).decode("utf-8")
    iface = ifaces.setdefault(ifname, rdf_client_network.Interface())
    iface.ifname = ifname

    if not ifaddr.ifa_addr:
      continue

    sockaddr = ctypes.cast(ifaddr.ifa_addr, ctypes.POINTER(Sockaddr))
    iffamily = sockaddr.contents.sa_family
    if iffamily == AF_INET:
      sockaddrin = ctypes.cast(ifaddr.ifa_addr, ctypes.POINTER(Sockaddrin))

      address = rdf_client_network.NetworkAddress()
      address.address_type = rdf_client_network.NetworkAddress.Family.INET
      address.packed_bytes = struct.pack("=L", sockaddrin.contents.sin_addr)
      iface.addresses.append(address)
    elif iffamily == AF_INET6:
      sockaddrin = ctypes.cast(ifaddr.ifa_addr, ctypes.POINTER(Sockaddrin6))

      address = rdf_client_network.NetworkAddress()
      address.address_type = rdf_client_network.NetworkAddress.Family.INET6
      address.packed_bytes = bytes(list(sockaddrin.contents.sin6_addr))
      iface.addresses.append(address)
    elif iffamily == AF_LINK:
      sockaddrdl = ctypes.cast(ifaddr.ifa_addr, ctypes.POINTER(Sockaddrdl))

      nlen = sockaddrdl.contents.sdl_nlen
      alen = sockaddrdl.contents.sdl_alen
      iface.mac_address = bytes(sockaddrdl.contents.sdl_data[nlen:nlen + alen])
    else:
      raise ValueError("Unexpected socket address family: %s" % iffamily)

  return itervalues(ifaces)


def EnumerateInterfacesFromClient(args):
  """Enumerate all MAC addresses."""
  del args  # Unused

  libc = ctypes.cdll.LoadLibrary(ctypes.util.find_library("c"))
  ifa = Ifaddrs()
  p_ifa = ctypes.pointer(ifa)
  libc.getifaddrs(ctypes.pointer(p_ifa))

  for iface in ParseIfaddrs(p_ifa):
    yield iface

  libc.freeifaddrs(p_ifa)


class EnumerateInterfaces(actions.ActionPlugin):
  """Enumerate all MAC addresses of all NICs."""
  out_rdfvalues = [rdf_client_network.Interface]

  def Run(self, args):
    for res in EnumerateInterfacesFromClient(args):
      self.SendReply(res)


class GetInstallDate(actions.ActionPlugin):
  """Estimate the install date of this system."""
  out_rdfvalues = [rdf_protodict.DataBlob]

  def Run(self, unused_args):
    for f in ["/var/log/CDIS.custom", "/var", "/private"]:
      try:
        ctime = os.stat(f).st_ctime
        self.SendReply(rdfvalue.RDFDatetime.FromSecondsSinceEpoch(ctime))
        return
      except OSError:
        pass
    self.SendReply(rdfvalue.RDFDatetime.FromSecondsSinceEpoch(0))


def EnumerateFilesystemsFromClient(args):
  """List all local filesystems mounted on this system."""
  del args  # Unused.
  for fs_struct in client_utils_osx.GetFileSystems():
    yield rdf_client_fs.Filesystem(
        device=fs_struct.f_mntfromname,
        mount_point=fs_struct.f_mntonname,
        type=fs_struct.f_fstypename)

  drive_re = re.compile("r?disk[0-9].*")
  for drive in os.listdir("/dev"):
    if not drive_re.match(drive):
      continue

    path = os.path.join("/dev", drive)
    try:
      img_inf = pytsk3.Img_Info(path)
      # This is a volume or a partition - we send back a TSK device.
      yield rdf_client_fs.Filesystem(device=path)

      vol_inf = pytsk3.Volume_Info(img_inf)

      for volume in vol_inf:
        if volume.flags == pytsk3.TSK_VS_PART_FLAG_ALLOC:
          offset = volume.start * vol_inf.info.block_size
          yield rdf_client_fs.Filesystem(
              device=path + ":" + str(offset), type="partition")

    except (IOError, RuntimeError):
      continue


class EnumerateFilesystems(actions.ActionPlugin):
  """Enumerate all unique filesystems local to the system."""
  out_rdfvalues = [rdf_client_fs.Filesystem]

  def Run(self, args):
    for res in EnumerateFilesystemsFromClient(args):
      self.SendReply(res)


def CreateServiceProto(job):
  """Create the Service protobuf.

  Args:
    job: Launchdjobdict from servicemanagement framework.

  Returns:
    sysinfo_pb2.OSXServiceInformation proto
  """
  service = rdf_client.OSXServiceInformation(
      label=job.get("Label"),
      program=job.get("Program"),
      sessiontype=job.get("LimitLoadToSessionType"),
      lastexitstatus=int(job["LastExitStatus"]),
      timeout=int(job["TimeOut"]),
      ondemand=bool(job["OnDemand"]))

  for arg in job.get("ProgramArguments", "", stringify=False):
    # Returns CFArray of CFStrings
    service.args.Append(unicode(arg))

  mach_dict = job.get("MachServices", {}, stringify=False)
  for key, value in iteritems(mach_dict):
    service.machservice.Append("%s:%s" % (key, value))

  job_mach_dict = job.get("PerJobMachServices", {}, stringify=False)
  for key, value in iteritems(job_mach_dict):
    service.perjobmachservice.Append("%s:%s" % (key, value))

  if "PID" in job:
    service.pid = job["PID"].value

  return service


def GetRunningLaunchDaemons():
  """Get running launchd jobs from objc ServiceManagement framework."""

  sm = ServiceManagement()
  return sm.SMGetJobDictionaries("kSMDomainSystemLaunchd")


def OSXEnumerateRunningServicesFromClient(args):
  """Get running launchd jobs.

  Args:
    args: Unused.

  Yields:
    `rdf_client.OSXServiceInformation` instances.

  Raises:
      UnsupportedOSVersionError: for OS X earlier than 10.6.
  """
  del args  # Unused.
  osx_version = client_utils_osx.OSXVersion()
  version_array = osx_version.VersionAsMajorMinor()

  if version_array[:2] < [10, 6]:
    raise UnsupportedOSVersionError(
        "ServiceManagement API unsupported on < 10.6. This client is %s" %
        osx_version.VersionString())

  launchd_list = GetRunningLaunchDaemons()

  parser = osx_launchd.OSXLaunchdJobDict(launchd_list)
  for job in parser.Parse():
    response = CreateServiceProto(job)
    yield response


class OSXEnumerateRunningServices(actions.ActionPlugin):
  """Enumerate all running launchd jobs."""
  in_rdfvalue = None
  out_rdfvalues = [rdf_client.OSXServiceInformation]

  def Run(self, args):
    for res in OSXEnumerateRunningServicesFromClient(args):
      self.SendReply(res)


class Uninstall(actions.ActionPlugin):
  """Remove the service that starts us at startup."""
  out_rdfvalues = [rdf_protodict.DataBlob]

  def Run(self, unused_arg):
    """This kills us with no cleanups."""
    logging.debug("Disabling service")

    msg = "Service disabled."
    if hasattr(sys, "frozen"):
      grr_binary = os.path.abspath(sys.executable)
    elif __file__:
      grr_binary = os.path.abspath(__file__)

    try:
      os.remove(grr_binary)
    except OSError:
      msg = "Could not remove binary."

    try:
      os.remove(config.CONFIG["Client.plist_path"])
    except OSError:
      if "Could not" in msg:
        msg += " Could not remove plist file."
      else:
        msg = "Could not remove plist file."

    # Get the directory we are running in from pyinstaller. This is either the
    # GRR directory which we should delete (onedir mode) or a generated temp
    # directory which we can delete without problems in onefile mode.
    directory = getattr(sys, "_MEIPASS", None)
    if directory:
      shutil.rmtree(directory, ignore_errors=True)

    self.SendReply(rdf_protodict.DataBlob(string=msg))


class UpdateAgent(standard.ExecuteBinaryCommand):
  """Updates the GRR agent to a new version."""

  def ProcessFile(self, path, args):

    cmd = "/usr/sbin/installer"
    cmd_args = ["-pkg", path, "-target", "/"]
    time_limit = args.time_limit

    res = client_utils_common.Execute(
        cmd, cmd_args, time_limit=time_limit, bypass_whitelist=True)
    (stdout, stderr, status, time_used) = res

    # Limit output to 10MB so our response doesn't get too big.
    stdout = stdout[:10 * 1024 * 1024]
    stderr = stderr[:10 * 1024 * 1024]

    self.SendReply(
        rdf_client_action.ExecuteBinaryResponse(
            stdout=stdout,
            stderr=stderr,
            exit_status=status,
            # We have to return microseconds.
            time_used=int(1e6 * time_used)))
