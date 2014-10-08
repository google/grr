#!/usr/bin/env python
"""Standard actions that happen on the client."""


import cStringIO as StringIO
import ctypes
import gzip
import hashlib
import os
import platform
import socket
import sys
import time
import zlib


import psutil

import logging

from grr.client import actions
from grr.client import client_utils_common
from grr.client import vfs
from grr.client.client_actions import tempfiles
from grr.lib import config_lib
from grr.lib import flags
from grr.lib import rdfvalue
from grr.lib import utils
from grr.lib.rdfvalues import crypto


# We do not send larger buffers than this:
MAX_BUFFER_SIZE = 640*1024


class ReadBuffer(actions.ActionPlugin):
  """Reads a buffer from a file and returns it to a server callback."""
  in_rdfvalue = rdfvalue.BufferReference
  out_rdfvalue = rdfvalue.BufferReference

  def Run(self, args):
    """Reads a buffer on the client and sends it to the server."""
    # Make sure we limit the size of our output
    if args.length > MAX_BUFFER_SIZE:
      raise RuntimeError("Can not read buffers this large.")

    try:
      fd = vfs.VFSOpen(args.pathspec, progress_callback=self.Progress)

      fd.Seek(args.offset)
      offset = fd.Tell()

      data = fd.Read(args.length)

    except (IOError, OSError), e:
      self.SetStatus(rdfvalue.GrrStatus.ReturnedStatus.IOERROR, e)
      return

    # Now return the data to the server
    self.SendReply(offset=offset, data=data,
                   length=len(data), pathspec=fd.pathspec)


HASH_CACHE = utils.FastStore(100)


class TransferBuffer(actions.ActionPlugin):
  """Reads a buffer from a file and returns it to the server efficiently."""
  in_rdfvalue = rdfvalue.BufferReference
  out_rdfvalue = rdfvalue.BufferReference

  def Run(self, args):
    """Reads a buffer on the client and sends it to the server."""
    # Make sure we limit the size of our output
    if args.length > MAX_BUFFER_SIZE:
      raise RuntimeError("Can not read buffers this large.")

    data = vfs.ReadVFS(args.pathspec, args.offset, args.length,
                       progress_callback=self.Progress)
    result = rdfvalue.DataBlob(
        data=zlib.compress(data),
        compression=rdfvalue.DataBlob.CompressionType.ZCOMPRESSION)

    digest = hashlib.sha256(data).digest()

    # Ensure that the buffer is counted against this response. Check network
    # send limit.
    self.ChargeBytesToSession(len(data))

    # Now return the data to the server into the special TransferStore well
    # known flow.
    self.grr_worker.SendReply(
        result, session_id=rdfvalue.SessionID("aff4:/flows/W:TransferStore"))

    # Now report the hash of this blob to our flow as well as the offset and
    # length.
    self.SendReply(offset=args.offset, length=len(data),
                   data=digest)


class HashBuffer(actions.ActionPlugin):
  """Hash a buffer from a file and returns it to the server efficiently."""
  in_rdfvalue = rdfvalue.BufferReference
  out_rdfvalue = rdfvalue.BufferReference

  def Run(self, args):
    """Reads a buffer on the client and sends it to the server."""
    # Make sure we limit the size of our output
    if args.length > MAX_BUFFER_SIZE:
      raise RuntimeError("Can not read buffers this large.")

    data = vfs.ReadVFS(args.pathspec, args.offset, args.length)

    digest = hashlib.sha256(data).digest()

    # Now report the hash of this blob to our flow as well as the offset and
    # length.
    self.SendReply(offset=args.offset, length=len(data),
                   data=digest)


class CopyPathToFile(actions.ActionPlugin):
  """Copy contents of a pathspec to a file on disk."""
  in_rdfvalue = rdfvalue.CopyPathToFileRequest
  out_rdfvalue = rdfvalue.CopyPathToFileRequest

  BLOCK_SIZE = 10 * 1024 * 1024

  def _Copy(self, dest_fd):
    """Copy from VFS to file until no more data or self.length is reached.

    Args:
      dest_fd: file object to write to
    Returns:
      self.written: bytes written
    """
    while self.written < self.length:
      to_read = min(self.length - self.written, self.BLOCK_SIZE)
      data = self.src_fd.read(to_read)
      if not data:
        break

      dest_fd.write(data)
      self.written += len(data)

      # Send heartbeats for long files.
      self.Progress()
    return self.written

  def Run(self, args):
    """Read from a VFS file and write to a GRRTempFile on disk.

    If file writing doesn't complete files won't be cleaned up.

    Args:
      args: see CopyPathToFile in jobs.proto
    """
    self.src_fd = vfs.VFSOpen(args.src_path, progress_callback=self.Progress)
    self.src_fd.Seek(args.offset)
    offset = self.src_fd.Tell()

    self.length = args.length or (1024 ** 4)  # 1 TB

    self.written = 0
    suffix = ".gz" if args.gzip_output else ""

    self.dest_fd = tempfiles.CreateGRRTempFile(directory=args.dest_dir,
                                               lifetime=args.lifetime,
                                               suffix=suffix)
    self.dest_file = self.dest_fd.name
    with self.dest_fd:

      if args.gzip_output:
        gzip_fd = gzip.GzipFile(self.dest_file, "wb", 9, self.dest_fd)

        # Gzip filehandle needs its own close method called
        with gzip_fd:
          self._Copy(gzip_fd)
      else:
        self._Copy(self.dest_fd)

    pathspec_out = rdfvalue.PathSpec(
        path=self.dest_file, pathtype=rdfvalue.PathSpec.PathType.OS)
    self.SendReply(offset=offset, length=self.written, src_path=args.src_path,
                   dest_dir=args.dest_dir, dest_path=pathspec_out,
                   gzip_output=args.gzip_output)


class ListDirectory(ReadBuffer):
  """Lists all the files in a directory."""
  in_rdfvalue = rdfvalue.ListDirRequest
  out_rdfvalue = rdfvalue.StatEntry

  def Run(self, args):
    """Lists a directory."""
    try:
      directory = vfs.VFSOpen(args.pathspec, progress_callback=self.Progress)
    except (IOError, OSError), e:
      self.SetStatus(rdfvalue.GrrStatus.ReturnedStatus.IOERROR, e)
      return

    files = list(directory.ListFiles())
    files.sort(key=lambda x: x.pathspec.path)

    for response in files:
      self.SendReply(response)


class IteratedListDirectory(actions.IteratedAction):
  """Lists a directory as an iterator."""
  in_rdfvalue = rdfvalue.ListDirRequest
  out_rdfvalue = rdfvalue.StatEntry

  def Iterate(self, request, client_state):
    """Restores its way through the directory using an Iterator."""
    try:
      fd = vfs.VFSOpen(request.pathspec, progress_callback=self.Progress)
    except (IOError, OSError), e:
      self.SetStatus(rdfvalue.GrrStatus.ReturnedStatus.IOERROR, e)
      return
    files = list(fd.ListFiles())
    files.sort(key=lambda x: x.pathspec.path)

    index = client_state.get("index", 0)
    length = request.iterator.number
    for response in files[index:index+length]:
      self.SendReply(response)

    # Update the state
    client_state["index"] = index + length


class SuspendableListDirectory(actions.SuspendableAction):
  """Lists a directory as a suspendable client action."""
  in_rdfvalue = rdfvalue.ListDirRequest
  out_rdfvalue = rdfvalue.StatEntry

  def Iterate(self):
    try:
      fd = vfs.VFSOpen(self.request.pathspec, progress_callback=self.Progress)
    except (IOError, OSError), e:
      self.SetStatus(rdfvalue.GrrStatus.ReturnedStatus.IOERROR, e)
      return

    length = self.request.iterator.number
    for group in utils.Grouper(fd.ListFiles(), length):
      for response in group:
        self.SendReply(response)

      self.Suspend()


class StatFile(ListDirectory):
  """Sends a StatResponse for a single file."""
  in_rdfvalue = rdfvalue.ListDirRequest
  out_rdfvalue = rdfvalue.StatEntry

  def Run(self, args):
    """Sends a StatResponse for a single file."""
    try:
      fd = vfs.VFSOpen(args.pathspec, progress_callback=self.Progress)
      res = fd.Stat()

      self.SendReply(res)
    except (IOError, OSError), e:
      self.SetStatus(rdfvalue.GrrStatus.ReturnedStatus.IOERROR, e)
      return


class ExecuteCommand(actions.ActionPlugin):
  """Executes one of the predefined commands."""
  in_rdfvalue = rdfvalue.ExecuteRequest
  out_rdfvalue = rdfvalue.ExecuteResponse

  def Run(self, command):
    """Run."""
    cmd = command.cmd
    args = command.args
    time_limit = command.time_limit

    res = client_utils_common.Execute(cmd, args, time_limit)
    (stdout, stderr, status, time_used) = res

    # Limit output to 10MB so our response doesn't get too big.
    stdout = stdout[:10 * 1024 * 1024]
    stderr = stderr[:10 * 1024 * 1024]

    result = rdfvalue.ExecuteResponse(
        request=command,
        stdout=stdout,
        stderr=stderr,
        exit_status=status,
        # We have to return microseconds.
        time_used=int(1e6 * time_used))
    self.SendReply(result)


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
  in_rdfvalue = rdfvalue.ExecuteBinaryRequest
  out_rdfvalue = rdfvalue.ExecuteBinaryResponse

  suffix = ""

  def WriteBlobToFile(self, request, suffix=""):
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

    temp_file = tempfiles.CreateGRRTempFile(filename=request.write_path,
                                            suffix=suffix, mode=mode)
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
    except (OSError, IOError), e:
      logging.info("Failed to remove temporary file %s. Err: %s", path, e)

  def Run(self, args):
    """Run."""
    # Verify the executable blob.
    args.executable.Verify(config_lib.CONFIG[
        "Client.executable_signing_public_key"])

    path = self.WriteBlobToFile(args, self.suffix)

    # Only actually run the file on the last chunk.
    if not args.more_data:
      self.ProcessFile(path, args)
      self.CleanUp(path)

  def ProcessFile(self, path, args):
    res = client_utils_common.Execute(path, args.args, args.time_limit,
                                      bypass_whitelist=True)
    (stdout, stderr, status, time_used) = res

    # Limit output to 10MB so our response doesn't get too big.
    stdout = stdout[:10 * 1024 * 1024]
    stderr = stderr[:10 * 1024 * 1024]

    result = rdfvalue.ExecuteBinaryResponse(
        stdout=stdout,
        stderr=stderr,
        exit_status=status,
        # We have to return microseconds.
        time_used=int(1e6 * time_used))

    self.SendReply(result)


class ExecutePython(actions.ActionPlugin):
  """Executes python code with exec.

  Obviously this is a dangerous function, it provides for arbitrary code exec by
  the server running as root/SYSTEM.

  This is protected by CONFIG[PrivateKeys.executable_signing_private_key], which
  should be stored offline and well protected.
  """
  in_rdfvalue = rdfvalue.ExecutePythonRequest
  out_rdfvalue = rdfvalue.ExecutePythonResponse

  def Run(self, args):
    """Run."""
    time_start = time.time()

    class StdOutHook(object):

      def __init__(self, buf):
        self.buf = buf

      def write(self, text):
        self.buf.write(text)

    args.python_code.Verify(config_lib.CONFIG[
        "Client.executable_signing_public_key"])

    # The execed code can assign to this variable if it wants to return data.
    logging.debug("exec for python code %s", args.python_code.data[0:100])

    context = globals().copy()
    context["py_args"] = args.py_args.ToDict()
    context["magic_return_str"] = ""
    # Export the Progress function to allow python hacks to call it.
    context["Progress"] = self.Progress

    stdout = StringIO.StringIO()
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
    result = rdfvalue.ExecutePythonResponse(
        time_used=int(1e6 * time_used),
        return_val=utils.SmartStr(output))
    self.SendReply(result)


class Segfault(actions.ActionPlugin):
  """This action is just for debugging. It induces a segfault."""
  in_rdfvalue = None
  out_rdfvalue = None

  def Run(self, unused_args):
    """Does the segfaulting."""
    if flags.FLAGS.debug:
      logging.warning("Segfault action requested :(")
      print ctypes.cast(1, ctypes.POINTER(ctypes.c_void_p)).contents
    else:
      logging.warning("Segfault requested but not running in debug mode.")


class ListProcesses(actions.ActionPlugin):
  """This action lists all the processes running on a machine."""
  in_rdfvalue = None
  out_rdfvalue = rdfvalue.Process

  def Run(self, unused_arg):
    # psutil will cause an active loop on Windows 2000
    if platform.system() == "Windows" and platform.version().startswith("5.0"):
      raise RuntimeError("ListProcesses not supported on Windows 2000")

    for proc in psutil.process_iter():
      response = rdfvalue.Process()
      process_fields = ["pid", "ppid", "name", "exe", "username", "terminal"]

      for field in process_fields:
        try:
          value = getattr(proc, field)
          if value is None:
            continue

          if callable(value):
            value = value()

          if not isinstance(value, (int, long)):
            value = utils.SmartUnicode(value)

          setattr(response, field, value)
        except (psutil.NoSuchProcess, psutil.AccessDenied, AttributeError):
          pass

      try:
        for arg in proc.cmdline():
          response.cmdline.append(utils.SmartUnicode(arg))
      except (psutil.NoSuchProcess, psutil.AccessDenied):
        pass

      try:
        response.nice = proc.nice()
      except (psutil.NoSuchProcess, psutil.AccessDenied):
        pass

      try:
        # Not available on Windows.
        if hasattr(proc, "uids"):
          (response.real_uid, response.effective_uid,
           response.saved_uid) = proc.uids()
          (response.real_gid, response.effective_gid,
           response.saved_gid) = proc.gids()
      except (psutil.NoSuchProcess, psutil.AccessDenied):
        pass

      try:
        response.ctime = long(proc.create_time() * 1e6)
        response.status = str(proc.status())
      except (psutil.NoSuchProcess, psutil.AccessDenied):
        pass

      try:
        # Not available on OSX.
        if hasattr(proc, "cwd"):
          response.cwd = utils.SmartUnicode(proc.cwd())
      except (psutil.NoSuchProcess, psutil.AccessDenied):
        pass

      try:
        response.num_threads = proc.num_threads()
      except (psutil.NoSuchProcess, psutil.AccessDenied, RuntimeError):
        pass

      try:
        (response.user_cpu_time,
         response.system_cpu_time) = proc.cpu_times()
        # This is very time consuming so we do not collect cpu_percent here.
        # response.cpu_percent = proc.get_cpu_percent()
      except (psutil.NoSuchProcess, psutil.AccessDenied):
        pass

      try:
        response.RSS_size, response.VMS_size = proc.memory_info()
        response.memory_percent = proc.memory_percent()
      except (psutil.NoSuchProcess, psutil.AccessDenied):
        pass

      # Due to a bug in psutil, this function is disabled for now
      # (https://github.com/giampaolo/psutil/issues/340)
      # try:
      #  for f in proc.open_files():
      #    response.open_files.append(utils.SmartUnicode(f.path))
      # except (psutil.NoSuchProcess, psutil.AccessDenied):
      #  pass

      try:
        for c in proc.connections():
          conn = response.connections.Append(family=c.family,
                                             type=c.type,
                                             pid=proc.pid)

          try:
            conn.state = c.status
          except ValueError:
            logging.info("Encountered unknown connection status (%s).",
                         c.status)

          try:
            conn.local_address.ip, conn.local_address.port = c.laddr

            # Could be in state LISTEN.
            if c.raddr:
              conn.remote_address.ip, conn.remote_address.port = c.raddr
          except AttributeError:
            conn.local_address.ip, conn.local_address.port = c.local_address

            # Could be in state LISTEN.
            if c.remote_address:
              (conn.remote_address.ip,
               conn.remote_address.port) = c.remote_address

      except (psutil.NoSuchProcess, psutil.AccessDenied):
        pass

      self.SendReply(response)
      # Reading information here is slow so we heartbeat between processes.
      self.Progress()


class SendFile(actions.ActionPlugin):
  """This action encrypts and sends a file to a remote listener."""
  in_rdfvalue = rdfvalue.SendFileRequest
  out_rdfvalue = rdfvalue.StatEntry

  BLOCK_SIZE = 1024 * 1024 * 10  # 10 MB

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

    if args.address_family == rdfvalue.NetworkAddress.Family.INET:
      family = socket.AF_INET
    elif args.address_family == rdfvalue.NetworkAddress.Family.INET6:
      family = socket.AF_INET6
    else:
      raise RuntimeError("Socket address family not supported.")

    s = socket.socket(family, socket.SOCK_STREAM)

    try:
      s.connect((args.host, args.port))
    except socket.error as e:
      raise RuntimeError(str(e))

    cipher = crypto.AES128CBCCipher(args.key, args.iv,
                                    crypto.Cipher.OP_ENCRYPT)

    while True:
      data = fd.read(self.BLOCK_SIZE)
      if not data:
        break
      self.Send(s, cipher.Update(data))
      # Send heartbeats for long files.
      self.Progress()
    self.Send(s, cipher.Final())
    s.close()

    self.SendReply(fd.Stat())


class StatFS(actions.ActionPlugin):
  """Call os.statvfs for a given list of paths. OS X and Linux only.

  Note that a statvfs call for a network filesystem (e.g. NFS) that is
  unavailable, e.g. due to no network, will result in the call blocking.
  """
  in_rdfvalue = rdfvalue.StatFSRequest
  out_rdfvalue = rdfvalue.Volume

  def Run(self, args):
    if platform.system() == "Windows":
      raise RuntimeError("os.statvfs not available on Windows")

    for path in args.path_list:

      try:
        fd = vfs.VFSOpen(rdfvalue.PathSpec(path=path, pathtype=args.pathtype),
                         progress_callback=self.Progress)
        st = fd.StatFS()
        mount_point = fd.GetMountPoint()
      except (IOError, OSError), e:
        self.SetStatus(rdfvalue.GrrStatus.ReturnedStatus.IOERROR, e)
        continue

      unix = rdfvalue.UnixVolume(mount_point=mount_point)

      # On linux pre 2.6 kernels don't have frsize, so we fall back to bsize.
      # The actual_available_allocation_units attribute is set to blocks
      # available to the unprivileged user, root may have some additional
      # reserved space.
      result = rdfvalue.Volume(bytes_per_sector=(st.f_frsize or st.f_bsize),
                               sectors_per_allocation_unit=1,
                               total_allocation_units=st.f_blocks,
                               actual_available_allocation_units=st.f_bavail,
                               unix=unix)
      self.SendReply(result)
