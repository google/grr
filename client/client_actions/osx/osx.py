#!/usr/bin/env python
# Copyright 2011 Google Inc. All Rights Reserved.

"""OSX specific actions."""



import ctypes
import logging
import os
import re
import shutil
import StringIO
import sys
import tarfile


import pytsk3

from grr.client import actions
from grr.client import client_utils_common
from grr.client import client_utils_osx
from grr.client.client_actions import standard
from grr.client.osx.objc import ServiceManagement
from grr.client.vfs_handlers import memory

from grr.lib import config_lib
from grr.lib import rdfvalue
from grr.lib import utils
from grr.parsers import osx_launchd


class Error(Exception):
  """Base error class."""


class UnsupportedOSVersionError(Error):
  """This action not supported on this os version."""


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
      ("sin_family", ctypes.c_ubyte),
      ("sin_port", ctypes.c_ushort),
      ("sin_addr", ctypes.c_ubyte * 4),
      ("sin_zero", ctypes.c_char * 8)
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

setattr(Ifaddrs, "_fields_", [
    ("ifa_next", ctypes.POINTER(Ifaddrs)),
    ("ifa_name", ctypes.POINTER(ctypes.c_char)),
    ("ifa_flags", ctypes.c_uint),
    ("ifa_addr", ctypes.POINTER(ctypes.c_char)),
    ("ifa_netmask", ctypes.POINTER(ctypes.c_char)),
    ("ifa_broadaddr", ctypes.POINTER(ctypes.c_char)),
    ("ifa_destaddr", ctypes.POINTER(ctypes.c_char)),
    ("ifa_data", ctypes.POINTER(ctypes.c_char))
    ])


class EnumerateInterfaces(actions.ActionPlugin):
  """Enumerate all MAC addresses of all NICs."""
  out_rdfvalue = rdfvalue.Interface

  def Run(self, unused_args):
    """Enumerate all MAC addresses."""
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
        iffamily = ord(m.contents.ifa_addr[1])
        if iffamily == 0x2:     # AF_INET
          data = ctypes.cast(m.contents.ifa_addr, ctypes.POINTER(Sockaddrin))
          ip4 = "".join(map(chr, data.contents.sin_addr))
          address_type = rdfvalue.NetworkAddress.Family.INET
          address = rdfvalue.NetworkAddress(address_type=address_type,
                                            packed_bytes=ip4)
          addresses.setdefault(ifname, []).append(address)

        if iffamily == 0x12:    # AF_LINK
          data = ctypes.cast(m.contents.ifa_addr, ctypes.POINTER(Sockaddrdl))
          iflen = data.contents.sdl_nlen
          addlen = data.contents.sdl_alen
          macs[ifname] = "".join(
              map(chr, data.contents.sdl_data[iflen:iflen+addlen]))

        if iffamily == 0x1E:     # AF_INET6
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
      if address_list:
        args["addresses"] = address_list
      self.SendReply(**args)


class GetInstallDate(actions.ActionPlugin):
  """Estimate the install date of this system."""
  out_rdfvalue = rdfvalue.DataBlob

  def Run(self, unused_args):
    for f in ["/var/log/CDIS.custom", "/var", "/private"]:
      try:
        stat = os.stat(f)
        self.SendReply(integer=int(stat.st_ctime))
        return
      except OSError:
        pass
    self.SendReply(integer=0)


class EnumerateFilesystems(actions.ActionPlugin):
  """Enumerate all unique filesystems local to the system."""
  out_rdfvalue = rdfvalue.Filesystem

  def Run(self, unused_args):
    """List all local filesystems mounted on this system."""
    for fs_struct in client_utils_osx.GetFileSystems():
      self.SendReply(device=fs_struct.f_mntfromname,
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
        self.SendReply(device=path)

        vol_inf = pytsk3.Volume_Info(img_inf)

        for volume in vol_inf:
          if volume.flags == pytsk3.TSK_VS_PART_FLAG_ALLOC:
            offset = volume.start * vol_inf.info.block_size
            self.SendReply(device=path + ":" + str(offset),
                           type="partition")

      except (IOError, RuntimeError):
        continue


class OSXEnumerateRunningServices(actions.ActionPlugin):
  """Enumerate all running launchd jobs."""
  in_rdfvalue = None
  out_rdfvalue = rdfvalue.OSXServiceInformation

  def GetRunningLaunchDaemons(self):
    """Get running launchd jobs from objc ServiceManagement framework."""

    sm = ServiceManagement()
    return sm.SMGetJobDictionaries("kSMDomainSystemLaunchd")

  def Run(self, unused_arg):
    """Get running launchd jobs.

    Raises:
      UnsupportedOSVersionError: for OS X earlier than 10.6
    """

    self.osversion = client_utils_osx.OSXVersion().VersionAsFloat()

    if self.osversion < 10.6:
      raise UnsupportedOSVersionError(
          "ServiceManagment API unsupported on < 10.6. This"
          " client is %s" % self.osversion)

    launchd_list = self.GetRunningLaunchDaemons()

    self.parser = osx_launchd.OSXLaunchdJobDict(launchd_list)
    for job in self.parser.Parse():
      response = self.CreateServiceProto(job)
      self.SendReply(response)

  def CreateServiceProto(self, job):
    """Create the Service protobuf.

    Args:
      job: Launchdjobdict from servicemanagement framework.
    Returns:
      sysinfo_pb2.OSXServiceInformation proto
    """
    service = rdfvalue.OSXServiceInformation(
        label=job.get("Label"), program=job.get("Program"),
        sessiontype=job.get("LimitLoadToSessionType"),
        lastexitstatus=int(job["LastExitStatus"]),
        timeout=int(job["TimeOut"]), ondemand=bool(job["OnDemand"]))

    for arg in job.get("ProgramArguments", "", stringify=False):
      # Returns CFArray of CFStrings
      service.args.Append(unicode(arg))

    mach_dict = job.get("MachServices", {}, stringify=False)
    for key, value in mach_dict.iteritems():
      service.machservice.Append("%s:%s" % (key, value))

    job_mach_dict = job.get("PerJobMachServices", {}, stringify=False)
    for key, value in job_mach_dict.iteritems():
      service.perjobmachservice.Append("%s:%s" % (key, value))

    if "PID" in job:
      service.pid = job["PID"].value

    return service


class Uninstall(actions.ActionPlugin):
  """Remove the service that starts us at startup."""
  out_rdfvalue = rdfvalue.DataBlob

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
      os.remove(config_lib.CONFIG["Client.plist_path"])
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

    self.SendReply(string=msg)


class InstallDriver(actions.ActionPlugin):
  """Installs a driver.

  Note that only drivers with a signature that validates with
  client_config.DRIVER_SIGNING_CERT can be loaded.
  """
  in_rdfvalue = rdfvalue.DriverInstallTemplate

  def _FindKext(self, path):
    """Find the .kext directory under path.

    Args:
      path: path string to search
    Returns:
      kext directory path string or raises if not found.
    Raises:
      RuntimeError: if there is no kext under the path.
    """
    for directory, _, _ in os.walk(path):
      if directory.endswith(".kext"):
        return directory
    raise RuntimeError("No .kext directory under %s" % path)

  def Run(self, args):
    """Initializes the driver."""
    # This action might crash the box so we need to flush the transaction log.
    self.SyncTransactionLog()

    if not args.driver:
      raise IOError("No driver supplied.")

    pub_key = config_lib.CONFIG.Get("Client.driver_signing_public_key")

    if not args.driver.Verify(pub_key):
      raise OSError("Driver signature signing failure.")

    if args.force_reload:
      client_utils_osx.UninstallDriver(args.driver_name)
    # Wrap the tarball in a file like object for tarfile to handle it.
    driver_buf = StringIO.StringIO(args.driver.data)
    # Unpack it to a temporary directory.
    with utils.TempDirectory() as kext_tmp_dir:
      driver_archive = tarfile.open(fileobj=driver_buf, mode="r:gz")
      driver_archive.extractall(kext_tmp_dir)
      # Now load it.
      kext_path = self._FindKext(kext_tmp_dir)
      logging.debug("Loading kext {0}".format(kext_path))
      client_utils_osx.InstallDriver(kext_path)


class GetMemoryInformation(actions.ActionPlugin):
  """Loads the driver for memory access and returns a Stat for the device."""

  in_rdfvalue = rdfvalue.PathSpec
  out_rdfvalue = rdfvalue.MemoryInformation

  def Run(self, args):
    """Run."""
    # This action might crash the box so we need to flush the transaction log.
    self.SyncTransactionLog()

    # Do any initialization we need to do.
    logging.debug("Querying device %s", args.path)
    mem_dev = open(args.path, "rb")

    result = rdfvalue.MemoryInformation(
        cr3=memory.OSXMemory.GetCR3(mem_dev),
        device=rdfvalue.PathSpec(
            path=args.path,
            pathtype=rdfvalue.PathSpec.PathType.MEMORY))
    for start, length in memory.OSXMemory.GetMemoryMap(mem_dev):
      result.runs.Append(offset=start, length=length)
    self.SendReply(result)


class UninstallDriver(actions.ActionPlugin):
  """Unloads a memory driver.

  Only if the request contains a valid signature the driver will be uninstalled.
  """

  in_rdfvalue = rdfvalue.DriverInstallTemplate

  def Run(self, args):
    """Unloads a driver."""
    pub_key = config_lib.CONFIG["Client.driver_signing_public_key"]
    if not args.driver.Verify(pub_key):
      raise OSError("Driver signature signing failure.")
    # Unload the driver and pass exceptions through
    client_utils_osx.UninstallDriver(args.driver_name)


class UpdateAgent(standard.ExecuteBinaryCommand):
  """Updates the GRR agent to a new version."""

  suffix = "pkg"

  def ProcessFile(self, path, args):

    cmd = "/usr/sbin/installer"
    cmd_args = ["-pkg", path, "-target", "/"]
    time_limit = args.time_limit

    res = client_utils_common.Execute(cmd, cmd_args, time_limit=time_limit,
                                      bypass_whitelist=True)
    (stdout, stderr, status, time_used) = res

    # Limit output to 10MB so our response doesn't get too big.
    stdout = stdout[:10 * 1024 * 1024]
    stderr = stderr[:10 * 1024 * 1024]

    result = rdfvalue.ExecuteBinaryResponse(stdout=stdout,
                                            stderr=stderr,
                                            exit_status=status,
                                            # We have to return microseconds.
                                            time_used=int(1e6 * time_used))
    self.SendReply(result)
