#!/usr/bin/env python
"""Standard actions that happen on the client."""
from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

import ctypes
import gzip
import hashlib
import io
import logging
import os
import platform
import socket
import sys
import time
import zlib


import psutil

from grr_response_client import actions
from grr_response_client import client_utils_common
from grr_response_client import vfs
from grr_response_client.client_actions import tempfiles
from grr_response_core import config
from grr_response_core.lib import constants
from grr_response_core.lib import flags
from grr_response_core.lib import rdfvalue
from grr_response_core.lib import utils
from grr_response_core.lib.rdfvalues import client as rdf_client
from grr_response_core.lib.rdfvalues import client_action as rdf_client_action
from grr_response_core.lib.rdfvalues import client_fs as rdf_client_fs
from grr_response_core.lib.rdfvalues import client_network as rdf_client_network
from grr_response_core.lib.rdfvalues import crypto as rdf_crypto
from grr_response_core.lib.rdfvalues import flows as rdf_flows
from grr_response_core.lib.rdfvalues import paths as rdf_paths
from grr_response_core.lib.rdfvalues import protodict as rdf_protodict
from grr_response_core.lib.util import precondition


class ReadBuffer(actions.ActionPlugin):
  """Reads a buffer from a file and returns it to a server callback."""
  in_rdfvalue = rdf_client.BufferReference
  out_rdfvalues = [rdf_client.BufferReference]

  def Run(self, args):
    """Reads a buffer on the client and sends it to the server."""
    # Make sure we limit the size of our output
    if args.length > constants.CLIENT_MAX_BUFFER_SIZE:
      raise RuntimeError("Can not read buffers this large.")

    try:
      fd = vfs.VFSOpen(args.pathspec, progress_callback=self.Progress)

      fd.Seek(args.offset)
      offset = fd.Tell()

      data = fd.Read(args.length)

    except (IOError, OSError) as e:
      self.SetStatus(rdf_flows.GrrStatus.ReturnedStatus.IOERROR, e)
      return

    # Now return the data to the server
    self.SendReply(
        rdf_client.BufferReference(
            offset=offset, data=data, length=len(data), pathspec=fd.pathspec))


class TransferBuffer(actions.ActionPlugin):
  """Reads a buffer from a file and returns it to the server efficiently."""
  in_rdfvalue = rdf_client.BufferReference
  out_rdfvalues = [rdf_client.BufferReference]

  def Run(self, args):
    """Reads a buffer on the client and sends it to the server."""
    # Make sure we limit the size of our output
    if args.length > constants.CLIENT_MAX_BUFFER_SIZE:
      raise RuntimeError("Can not read buffers this large.")

    data = vfs.ReadVFS(
        args.pathspec,
        args.offset,
        args.length,
        progress_callback=self.Progress)
    result = rdf_protodict.DataBlob(
        data=zlib.compress(data),
        compression=rdf_protodict.DataBlob.CompressionType.ZCOMPRESSION)

    digest = hashlib.sha256(data).digest()

    # Ensure that the buffer is counted against this response. Check network
    # send limit.
    self.ChargeBytesToSession(len(data))

    # Now return the data to the server into the special TransferStore well
    # known flow.
    self.grr_worker.SendReply(
        result, session_id=rdfvalue.SessionID(flow_name="TransferStore"))

    # Now report the hash of this blob to our flow as well as the offset and
    # length.
    self.SendReply(
        rdf_client.BufferReference(
            offset=args.offset, length=len(data), data=digest))


class HashBuffer(actions.ActionPlugin):
  """Hash a buffer from a file and returns it to the server efficiently."""
  in_rdfvalue = rdf_client.BufferReference
  out_rdfvalues = [rdf_client.BufferReference]

  def Run(self, args):
    """Reads a buffer on the client and sends it to the server."""
    # Make sure we limit the size of our output
    if args.length > constants.CLIENT_MAX_BUFFER_SIZE:
      raise RuntimeError("Can not read buffers this large.")

    data = vfs.ReadVFS(args.pathspec, args.offset, args.length)

    digest = hashlib.sha256(data).digest()

    # Now report the hash of this blob to our flow as well as the offset and
    # length.
    self.SendReply(
        rdf_client.BufferReference(
            offset=args.offset, length=len(data), data=digest))


class HashFile(actions.ActionPlugin):
  """Hash an entire file using multiple algorithms."""
  in_rdfvalue = rdf_client_action.FingerprintRequest
  out_rdfvalues = [rdf_client_action.FingerprintResponse]

  _hash_types = {
      "md5": hashlib.md5,
      "sha1": hashlib.sha1,
      "sha256": hashlib.sha256,
  }

  def Run(self, args):
    hash_types = set()
    for t in args.tuples:
      for hash_name in t.hashers:
        hash_types.add(str(hash_name).lower())

    hasher = client_utils_common.MultiHasher(hash_types, progress=self.Progress)
    with vfs.VFSOpen(args.pathspec, progress_callback=self.Progress) as fd:
      hasher.HashFile(fd, args.max_filesize)

    hash_object = hasher.GetHashObject()
    response = rdf_client_action.FingerprintResponse(
        pathspec=fd.pathspec,
        bytes_read=hash_object.num_bytes,
        hash=hash_object)
    self.SendReply(response)


class CopyPathToFile(actions.ActionPlugin):
  """Copy contents of a pathspec to a file on disk."""
  in_rdfvalue = rdf_client_action.CopyPathToFileRequest
  out_rdfvalues = [rdf_client_action.CopyPathToFileRequest]

  BLOCK_SIZE = 10 * 1024 * 1024

  def _Copy(self, src_fd, dest_fd, length):
    """Copy from VFS to file until no more data or length is reached.

    Args:
      src_fd: File object to read from.
      dest_fd: File object to write to.
      length: Number of bytes to write.

    Returns:
      Bytes written.
    """
    written = 0
    while written < length:
      to_read = min(length - written, self.BLOCK_SIZE)
      data = src_fd.read(to_read)
      if not data:
        break

      dest_fd.write(data)
      written += len(data)

      # Send heartbeats for long files.
      self.Progress()
    return written

  def Run(self, args):
    """Read from a VFS file and write to a GRRTempFile on disk.

    If file writing doesn't complete files won't be cleaned up.

    Args:
      args: see CopyPathToFile in jobs.proto
    """
    src_fd = vfs.VFSOpen(args.src_path, progress_callback=self.Progress)
    src_fd.Seek(args.offset)
    offset = src_fd.Tell()

    length = args.length or (1024**4)  # 1 TB

    suffix = ".gz" if args.gzip_output else ""

    dest_fd, dest_pathspec = tempfiles.CreateGRRTempFileVFS(
        lifetime=args.lifetime, suffix=suffix)

    dest_file = dest_fd.name
    with dest_fd:

      if args.gzip_output:
        gzip_fd = gzip.GzipFile(dest_file, "wb", 9, dest_fd)

        # Gzip filehandle needs its own close method called
        with gzip_fd:
          written = self._Copy(src_fd, gzip_fd, length)
      else:
        written = self._Copy(src_fd, dest_fd, length)

    self.SendReply(
        rdf_client_action.CopyPathToFileRequest(
            offset=offset,
            length=written,
            src_path=args.src_path,
            dest_path=dest_pathspec,
            gzip_output=args.gzip_output))


class ListDirectory(ReadBuffer):
  """Lists all the files in a directory."""
  in_rdfvalue = rdf_client_action.ListDirRequest
  out_rdfvalues = [rdf_client_fs.StatEntry]

  def Run(self, args):
    """Lists a directory."""
    try:
      directory = vfs.VFSOpen(args.pathspec, progress_callback=self.Progress)
    except (IOError, OSError) as e:
      self.SetStatus(rdf_flows.GrrStatus.ReturnedStatus.IOERROR, e)
      return

    files = list(directory.ListFiles())
    files.sort(key=lambda x: x.pathspec.path)

    for response in files:
      self.SendReply(response)


def GetFileStatFromClient(args):
  fd = vfs.VFSOpen(args.pathspec)
  stat_entry = fd.Stat(ext_attrs=args.collect_ext_attrs)
  yield stat_entry


class GetFileStat(actions.ActionPlugin):
  """A client action that yields stat of a given file."""

  in_rdfvalue = rdf_client_action.GetFileStatRequest
  out_rdfvalues = [rdf_client_fs.StatEntry]

  def Run(self, args):
    try:
      fd = vfs.VFSOpen(args.pathspec, progress_callback=self.Progress)
      stat_entry = fd.Stat(ext_attrs=args.collect_ext_attrs)
      self.SendReply(stat_entry)
    except (IOError, OSError) as error:
      self.SetStatus(rdf_flows.GrrStatus.ReturnedStatus.IOERROR, error)


def ExecuteCommandFromClient(command):
  """Executes one of the predefined commands.

  Args:
    command: An `ExecuteRequest` object.

  Yields:
    `rdf_client_action.ExecuteResponse` objects.
  """
  cmd = command.cmd
  args = command.args
  time_limit = command.time_limit

  res = client_utils_common.Execute(cmd, args, time_limit)
  (stdout, stderr, status, time_used) = res

  # Limit output to 10MB so our response doesn't get too big.
  stdout = stdout[:10 * 1024 * 1024]
  stderr = stderr[:10 * 1024 * 1024]

  yield rdf_client_action.ExecuteResponse(
      request=command,
      stdout=stdout,
      stderr=stderr,
      exit_status=status,
      # We have to return microseconds.
      time_used=int(1e6 * time_used))


class ExecuteCommand(actions.ActionPlugin):
  """Executes one of the predefined commands."""

  in_rdfvalue = rdf_client_action.ExecuteRequest
  out_rdfvalues = [rdf_client_action.ExecuteResponse]

  def Run(self, args):
    for res in ExecuteCommandFromClient(args):
      self.SendReply(res)


class ExecuteBinaryCommand(actions.ActionPlugin):
  """Executes a command from a passed in binary.

  Obviously this is a dangerous function, it provides for arbitrary code exec by
  the server running as root/SYSTEM.

  This is protected by the CONFIG[PrivateKeys.executable_signing_private_key],
  which should be stored offline and well protected.

  This method can be utilized as part of an autoupdate mechanism if necessary.

  NOTE: If the binary is too large to fit inside a single request, the request
  will have the more_data flag enabled, indicating more data is coming.
  """
  in_rdfvalue = rdf_client_action.ExecuteBinaryRequest
  out_rdfvalues = [rdf_client_action.ExecuteBinaryResponse]

  def WriteBlobToFile(self, request):
    """Writes the blob to a file and returns its path."""
    lifetime = 0
    # Only set the lifetime thread on the last chunk written.
    if not request.more_data:
      lifetime = request.time_limit

      # Keep the file for at least 5 seconds after execution.
      if lifetime > 0:
        lifetime += 5

    # First chunk truncates the file, later chunks append.
    if request.offset == 0:
      mode = "w+b"
    else:
      mode = "r+b"

    temp_file = tempfiles.CreateGRRTempFile(
        filename=request.write_path, mode=mode)
    with temp_file:
      path = temp_file.name
      temp_file.seek(0, 2)
      if temp_file.tell() != request.offset:
        raise IOError("Chunks out of order Error.")

      # Write the new chunk.
      temp_file.write(request.executable.data)

    return path

  def CleanUp(self, path):
    """Removes the temp file."""
    try:
      if os.path.exists(path):
        os.remove(path)
    except (OSError, IOError) as e:
      logging.info("Failed to remove temporary file %s. Err: %s", path, e)

  def Run(self, args):
    """Run."""
    # Verify the executable blob.
    args.executable.Verify(
        config.CONFIG["Client.executable_signing_public_key"])

    path = self.WriteBlobToFile(args)

    # Only actually run the file on the last chunk.
    if not args.more_data:
      self.ProcessFile(path, args)
      self.CleanUp(path)

  def ProcessFile(self, path, args):
    res = client_utils_common.Execute(
        path, args.args, args.time_limit, bypass_whitelist=True)
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


class ExecutePython(actions.ActionPlugin):
  """Executes python code with exec.

  Obviously this is a dangerous function, it provides for arbitrary code exec by
  the server running as root/SYSTEM.

  This is protected by CONFIG[PrivateKeys.executable_signing_private_key], which
  should be stored offline and well protected.
  """
  in_rdfvalue = rdf_client_action.ExecutePythonRequest
  out_rdfvalues = [rdf_client_action.ExecutePythonResponse]

  def Run(self, args):
    """Run."""
    time_start = time.time()

    args.python_code.Verify(
        config.CONFIG["Client.executable_signing_public_key"])

    # The execed code can assign to this variable if it wants to return data.
    logging.debug("exec for python code %s", args.python_code.data[0:100])

    context = globals().copy()
    context["py_args"] = args.py_args.ToDict()
    context["magic_return_str"] = ""
    # Export the Progress function to allow python hacks to call it.
    context["Progress"] = self.Progress

    stdout = io.StringIO()
    with utils.Stubber(sys, "stdout", StdOutHook(stdout)):
      exec(args.python_code.data, context)  # pylint: disable=exec-used

    stdout_output = stdout.getvalue()
    magic_str_output = context.get("magic_return_str")

    if stdout_output and magic_str_output:
      output = "Stdout: %s\nMagic Str:%s\n" % (stdout_output, magic_str_output)
    else:
      output = stdout_output or magic_str_output

    time_used = time.time() - time_start
    # We have to return microseconds.
    self.SendReply(
        rdf_client_action.ExecutePythonResponse(
            time_used=int(1e6 * time_used), return_val=utils.SmartStr(output)))


# TODO(hanuszczak): This class has been moved out of `ExecutePython::Run`. The
# reason is that on Python versions older than 2.7.9 there is a bug [1] with
# `exec` used as a function (which we do in order to maintain compatibility with
# Python 3) that triggers a syntax error if used in a method with other nested
# functions. Once support for older Python version is dropped, this can be moved
# back.
#
# [1]: https://bugs.python.org/issue21591
class StdOutHook(object):

  def __init__(self, buf):
    self.buf = buf

  def write(self, text):  # pylint: disable=invalid-name
    precondition.AssertType(text, unicode)
    self.buf.write(text)


class Segfault(actions.ActionPlugin):
  """This action is just for debugging. It induces a segfault."""
  in_rdfvalue = None
  out_rdfvalues = [None]

  def Run(self, unused_args):
    """Does the segfaulting."""
    if flags.FLAGS.debug:
      logging.warning("Segfault action requested :(")
      print(ctypes.cast(1, ctypes.POINTER(ctypes.c_void_p)).contents)
    else:
      logging.warning("Segfault requested but not running in debug mode.")


def ListProcessesFromClient(args):
  del args  # Unused

  # psutil will cause an active loop on Windows 2000
  if platform.system() == "Windows" and platform.version().startswith("5.0"):
    raise RuntimeError("ListProcesses not supported on Windows 2000")

  for proc in psutil.process_iter():
    yield rdf_client.Process.FromPsutilProcess(proc)


class ListProcesses(actions.ActionPlugin):
  """This action lists all the processes running on a machine."""
  in_rdfvalue = None
  out_rdfvalues = [rdf_client.Process]

  def Run(self, args):
    for res in ListProcessesFromClient(args):
      self.SendReply(res)

      # Reading information here is slow so we heartbeat between processes.
      self.Progress()


class SendFile(actions.ActionPlugin):
  """This action encrypts and sends a file to a remote listener."""
  in_rdfvalue = rdf_client_action.SendFileRequest
  out_rdfvalues = [rdf_client_fs.StatEntry]

  # 10 MB.
  BLOCK_SIZE = 1024 * 1024 * 10

  def Send(self, sock, msg):
    totalsent = 0
    n = len(msg)
    while totalsent < n:
      sent = sock.send(msg[totalsent:])
      if sent == 0:
        raise RuntimeError("socket connection broken")
      totalsent += sent

  def Run(self, args):
    """Run."""

    # Open the file.
    fd = vfs.VFSOpen(args.pathspec, progress_callback=self.Progress)

    if args.address_family == rdf_client_network.NetworkAddress.Family.INET:
      family = socket.AF_INET
    elif args.address_family == rdf_client_network.NetworkAddress.Family.INET6:
      family = socket.AF_INET6
    else:
      raise RuntimeError("Socket address family not supported.")

    s = socket.socket(family, socket.SOCK_STREAM)

    try:
      s.connect((args.host, args.port))
    except socket.error as e:
      raise RuntimeError(str(e))

    cipher = rdf_crypto.AES128CBCCipher(args.key, args.iv)
    streaming_encryptor = rdf_crypto.StreamingCBCEncryptor(cipher)

    while True:
      data = fd.read(self.BLOCK_SIZE)
      if not data:
        break

      self.Send(s, streaming_encryptor.Update(data))
      # Send heartbeats for long files.
      self.Progress()

    self.Send(s, streaming_encryptor.Finalize())
    s.close()

    self.SendReply(fd.Stat())


def StatFSFromClient(args):
  """Call os.statvfs for a given list of paths.

  Args:
    args: An `rdf_client_action.StatFSRequest`.

  Yields:
    `rdf_client_fs.UnixVolume` instances.

  Raises:
    RuntimeError: if called on a Windows system.
  """
  if platform.system() == "Windows":
    raise RuntimeError("os.statvfs not available on Windows")

  for path in args.path_list:

    try:
      fd = vfs.VFSOpen(rdf_paths.PathSpec(path=path, pathtype=args.pathtype))
      st = fd.StatFS()
      mount_point = fd.GetMountPoint()
    except (IOError, OSError):
      continue

    unix = rdf_client_fs.UnixVolume(mount_point=mount_point)

    # On linux pre 2.6 kernels don't have frsize, so we fall back to bsize.
    # The actual_available_allocation_units attribute is set to blocks
    # available to the unprivileged user, root may have some additional
    # reserved space.
    yield rdf_client_fs.Volume(
        bytes_per_sector=(st.f_frsize or st.f_bsize),
        sectors_per_allocation_unit=1,
        total_allocation_units=st.f_blocks,
        actual_available_allocation_units=st.f_bavail,
        unixvolume=unix)


class StatFS(actions.ActionPlugin):
  """Call os.statvfs for a given list of paths.

  OS X and Linux only.

  Note that a statvfs call for a network filesystem (e.g. NFS) that is
  unavailable, e.g. due to no network, will result in the call blocking.
  """
  in_rdfvalue = rdf_client_action.StatFSRequest
  out_rdfvalues = [rdf_client_fs.Volume]

  def Run(self, args):
    for res in StatFSFromClient(args):
      self.SendReply(res)
      self.Progress()


class GetMemorySize(actions.ActionPlugin):
  out_rdfvalues = [rdfvalue.ByteSize]

  def Run(self, args):
    _ = args
    self.SendReply(rdfvalue.ByteSize(psutil.virtual_memory()[0]))
