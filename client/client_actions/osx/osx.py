#!/usr/bin/env python
# Copyright 2011 Google Inc.
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


"""OSX specific actions."""



import ctypes
import logging
import os
import platform
import sys

from grr.client import actions
from grr.client import comms
from grr.lib import utils
from grr.proto import jobs_pb2
from grr.proto import sysinfo_pb2


class GetInstallDate(actions.ActionPlugin):
  """Estimate the install date of this system."""
  out_protobuf = jobs_pb2.DataBlob

  def Run(self, unused_args):
    # TODO(user): Find a sensible way to implement this.
    self.SendReply(integer=0)


class EnumerateUsers(actions.ActionPlugin):
  """Enumerates all the users on this system."""
  out_protobuf = jobs_pb2.UserAccount

  def Run(self, unused_args):
    """Enumerate all users on this machine."""
    # TODO(user): Add /var/run/utmpx parsing as per linux
    blacklist = ["Shared"]
    for user in os.listdir("/Users"):
      userdir = "/Users/{0}".format(user)
      if user not in blacklist and os.path.isdir(userdir):
        self.SendReply(username=user, homedir=userdir)


class EnumerateInterfaces(actions.ActionPlugin):
  """Enumerate all MAC addresses of all NICs.

  See: http://developer.apple.com/library/mac/#documentation/Darwin/Reference/ManPages/man4/netintro.4.html
  """
  out_protobuf = jobs_pb2.Interface

  def Run(self, unused_args):
    """Enumerate all MAC addresses."""
    # TODO(user): Implement this.
    pass


class EnumerateFilesystems(actions.ActionPlugin):
  """Enumerate all unique filesystems local to the system."""
  out_protobuf = sysinfo_pb2.Filesystem

  def Run(self, unused_args):
    """List all local filesystems mounted on this system."""
    for fs_struct in GetFileSystems():
      self.SendReply(device=fs_struct.f_mntfromname,
                     mount_point=fs_struct.f_mntonname,
                     type=fs_struct.f_fstypename)


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
  ]


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
  ]


def GetFileSystems():
  """Make syscalls to get the mounted filesystems.

  Returns:
    A list of Struct objects.

  Based on the information for getfsstat
  http://developer.apple.com/library/mac/#documentation/Darwin/Reference/ManPages/man2/getfsstat.2.html
  """
  major, minor = platform.mac_ver()[0].split(".")[0:2]
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
  cstr = lambda x: x.split("\0", 1)[0]
  for count in range(0, fs_count):
    struct_size = struct_class.GetSize()
    s_data = data[count * struct_size:(count + 1) * struct_size]
    s = struct_class(s_data)
    s.f_fstypename = cstr(s.f_fstypename)
    s.f_mntonname = cstr(s.f_mntonname)
    s.f_mntfromname = cstr(s.f_mntfromname)
    results.append(s)
  return results


class Kill(actions.ActionPlugin):
  """Kill our process with no cleanups."""
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

      # Die ourselves.
      logging.info("Dying on request.")
      sys.exit(0)
