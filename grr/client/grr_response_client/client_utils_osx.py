#!/usr/bin/env python
"""OSX specific utils."""
from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

import ctypes
import ctypes.util
import logging
import os
import platform


from builtins import range  # pylint: disable=redefined-builtin

from grr_response_client import client_utils_osx_linux
from grr_response_client.osx import objc
from grr_response_client.osx import process
from grr_response_core.lib import utils
from grr_response_core.lib.rdfvalues import paths as rdf_paths

# Shared functions between macOS and Linux.
# pylint: disable=invalid-name
GetExtAttrs = client_utils_osx_linux.GetExtAttrs
CanonicalPathToLocalPath = client_utils_osx_linux.CanonicalPathToLocalPath
LocalPathToCanonicalPath = client_utils_osx_linux.LocalPathToCanonicalPath
NannyController = client_utils_osx_linux.NannyController
VerifyFileOwner = client_utils_osx_linux.VerifyFileOwner
TransactionLog = client_utils_osx_linux.TransactionLog

# pylint: enable=invalid-name


def FindProxies():
  """This reads the OSX system configuration and gets the proxies."""

  sc = objc.SystemConfiguration()

  # Get the dictionary of network proxy settings
  settings = sc.dll.SCDynamicStoreCopyProxies(None)
  if not settings:
    return []

  try:
    cf_http_enabled = sc.CFDictRetrieve(settings, "kSCPropNetProxiesHTTPEnable")
    if cf_http_enabled and bool(sc.CFNumToInt32(cf_http_enabled)):
      # Proxy settings for HTTP are enabled
      cfproxy = sc.CFDictRetrieve(settings, "kSCPropNetProxiesHTTPProxy")
      cfport = sc.CFDictRetrieve(settings, "kSCPropNetProxiesHTTPPort")
      if cfproxy and cfport:
        proxy = sc.CFStringToPystring(cfproxy)
        port = sc.CFNumToInt32(cfport)
        return ["http://%s:%d/" % (proxy, port)]

    cf_auto_enabled = sc.CFDictRetrieve(
        settings, "kSCPropNetProxiesProxyAutoConfigEnable")

    if cf_auto_enabled and bool(sc.CFNumToInt32(cf_auto_enabled)):
      cfurl = sc.CFDictRetrieve(settings,
                                "kSCPropNetProxiesProxyAutoConfigURLString")
      if cfurl:
        unused_url = sc.CFStringToPystring(cfurl)
        # TODO(amoser): Auto config is enabled, what is the plan here?
        # Basically, all we get is the URL of a javascript file. To get the
        # correct proxy for a given URL, browsers call a Javascript function
        # that returns the correct proxy URL. The question is now, do we really
        # want to start running downloaded js on the client?
        return []

  finally:
    sc.dll.CFRelease(settings)
  return []


def GetMountpoints():
  """List all the filesystems mounted on the system."""
  devices = {}

  for filesys in GetFileSystems():
    devices[filesys.f_mntonname] = (filesys.f_mntfromname, filesys.f_fstypename)

  return devices


class StatFSStruct(utils.Struct):
  """Parse filesystems getfsstat."""
  _fields = [
      ("h", "f_otype;"),
      ("h", "f_oflags;"),
      ("l", "f_bsize;"),
      ("l", "f_iosize;"),
      ("l", "f_blocks;"),
      ("l", "f_bfree;"),
      ("l", "f_bavail;"),
      ("l", "f_files;"),
      ("l", "f_ffree;"),
      ("Q", "f_fsid;"),
      ("l", "f_owner;"),
      ("h", "f_reserved1;"),
      ("h", "f_type;"),
      ("l", "f_flags;"),
      ("2l", "f_reserved2"),
      ("15s", "f_fstypename"),
      ("90s", "f_mntonname"),
      ("90s", "f_mntfromname"),
      ("x", "f_reserved3"),
      ("16x", "f_reserved4")
  ]  # pyformat:disable


class StatFS64Struct(utils.Struct):
  """Parse filesystems getfsstat for 64 bit."""
  _fields = [
      ("<L", "f_bsize"),
      ("l", "f_iosize"),
      ("Q", "f_blocks"),
      ("Q", "f_bfree"),
      ("Q", "f_bavail"),
      ("Q", "f_files"),
      ("Q", "f_ffree"),
      ("l", "f_fsid1"),
      ("l", "f_fsid2"),
      ("l", "f_owner"),
      ("L", "f_type"),
      ("L", "f_flags"),
      ("L", "f_fssubtype"),
      ("16s", "f_fstypename"),
      ("1024s", "f_mntonname"),
      ("1024s", "f_mntfromname"),
      ("32s", "f_reserved")
  ]  # pyformat:disable


def GetFileSystems():
  """Make syscalls to get the mounted filesystems.

  Returns:
    A list of Struct objects.

  Based on the information for getfsstat
    http://developer.apple.com/library/mac/#documentation/Darwin/
      Reference/ManPages/man2/getfsstat.2.html
  """
  version = OSXVersion()
  major, minor = version.VersionAsMajorMinor()

  libc = ctypes.cdll.LoadLibrary(ctypes.util.find_library("c"))

  if major <= 10 and minor <= 5:
    use_64 = False
    fs_struct = StatFSStruct
  else:
    use_64 = True
    fs_struct = StatFS64Struct

  # Get max 20 file systems.
  struct_size = fs_struct.GetSize()
  buf_size = struct_size * 20

  cbuf = ctypes.create_string_buffer(buf_size)

  if use_64:
    # MNT_NOWAIT = 2 - don't ask the filesystems, just return cache.
    ret = libc.getfsstat64(ctypes.byref(cbuf), buf_size, 2)
  else:
    ret = libc.getfsstat(ctypes.byref(cbuf), buf_size, 2)

  if ret == 0:
    logging.debug("getfsstat failed err: %s", ret)
    return []
  return ParseFileSystemsStruct(fs_struct, ret, cbuf)


def ParseFileSystemsStruct(struct_class, fs_count, data):
  """Take the struct type and parse it into a list of structs."""
  results = []
  cstr = lambda x: x.split("\x00", 1)[0]
  for count in range(0, fs_count):
    struct_size = struct_class.GetSize()
    s_data = data[count * struct_size:(count + 1) * struct_size]
    s = struct_class(s_data)
    s.f_fstypename = cstr(s.f_fstypename)
    s.f_mntonname = cstr(s.f_mntonname)
    s.f_mntfromname = cstr(s.f_mntfromname)
    results.append(s)
  return results


def GetRawDevice(path):
  """Resolve the raw device that contains the path."""
  device_map = GetMountpoints()

  path = utils.SmartUnicode(path)
  mount_point = path = utils.NormalizePath(path, "/")

  result = rdf_paths.PathSpec(pathtype=rdf_paths.PathSpec.PathType.OS)

  # Assign the most specific mount point to the result
  while mount_point:
    try:
      result.path, fs_type = device_map[mount_point]
      if fs_type in [
          "ext2", "ext3", "ext4", "vfat", "ntfs", "Apple_HFS", "hfs", "msdos"
      ]:
        # These are read filesystems
        result.pathtype = rdf_paths.PathSpec.PathType.OS
      else:
        result.pathtype = rdf_paths.PathSpec.PathType.UNSET

      # Drop the mount point
      path = utils.NormalizePath(path[len(mount_point):])

      return result, path
    except KeyError:
      mount_point = os.path.dirname(mount_point)


def InstallDriver(kext_path):
  """Calls into the IOKit to load a kext by file-system path.

  Apple kext API doco here:
    http://developer.apple.com/library/mac/#documentation/IOKit/Reference/
      KextManager_header_reference/Reference/reference.html

  Args:
    kext_path: Absolute or relative POSIX path to the kext.

  Raises:
    OSError: On failure to load the kext.
  """
  km = objc.KextManager()

  cf_kext_path = km.PyStringToCFString(kext_path)
  kext_url = km.dll.CFURLCreateWithFileSystemPath(
      objc.CF_DEFAULT_ALLOCATOR, cf_kext_path, objc.POSIX_PATH_STYLE, True)
  status = km.iokit.KextManagerLoadKextWithURL(kext_url, None)

  km.dll.CFRelease(kext_url)
  km.dll.CFRelease(cf_kext_path)
  if status is not objc.OS_SUCCESS:
    raise OSError("Failed to load kext at {0}: {1}".format(kext_path, status))


def UninstallDriver(bundle_name):
  """Calls into the IOKit to unload a kext by its name.

  Args:
    bundle_name: The bundle identifier of the kernel extension as defined in
                 Info.plist field CFBundleIdentifier.
  Returns:
    The error code from the library call. objc.OS_SUCCESS if successfull.
  """
  km = objc.KextManager()

  cf_bundle_name = km.PyStringToCFString(bundle_name)
  status = km.iokit.KextManagerUnloadKextWithIdentifier(cf_bundle_name)
  km.dll.CFRelease(cf_bundle_name)
  return status


class OSXVersion(object):
  """Convenience functions for working with OSX versions."""

  def __init__(self):
    self.version = platform.mac_ver()[0]
    self.splitversion = self.version.split(".")
    self.majorminor = self.splitversion[0:2]

  def VersionAsMajorMinor(self):
    """Get version as major minor array.

    Returns:
      [10, 8] for 10.8.1
    """
    return [int(x) for x in self.majorminor]

  def VersionString(self):
    """Get version string.

    Returns:
      "10.8.1" for 10.8.1
    """
    return self.version


def KeepAlive():
  # Not yet supported for OSX.
  pass


def OpenProcessForMemoryAccess(pid=None):
  return process.Process(pid=pid)


def MemoryRegions(proc, options):
  for start, length in proc.Regions(
      skip_executable_regions=options.skip_executable_regions,
      skip_readonly_regions=options.skip_readonly_regions,
      skip_shared_regions=options.skip_shared_regions):
    yield start, length
