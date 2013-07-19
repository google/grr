#!/usr/bin/env python
"""Standard actions that happen on the client."""


import ctypes
import gzip
import hashlib
import os
import platform
import socket
import sys
import time
import zlib


from M2Crypto import EVP
import psutil

import logging

from grr.client import actions
from grr.client import client_utils_common
from grr.client import vfs
from grr.client.client_actions import tempfiles
from grr.lib import config_lib
from grr.lib import flags
from grr.lib import rdfvalue
from grr.lib import type_info
from grr.lib import utils


# We do not send larger buffers than this:
MAX_BUFFER_SIZE = 640*1024


config_lib.CONFIG.AddOption(type_info.PEMPublicKey(
    name="Client.executable_signing_public_key",
    description="public key for verifying executable signing."))

config_lib.CONFIG.AddOption(type_info.PEMPrivateKey(
    name="PrivateKeys.executable_signing_private_key",
    description="Private keys for signing executables. NOTE: This "
    "key is usually kept offline and is thus not present in the "
    "configuration file."))

config_lib.CONFIG.AddOption(type_info.PEMPublicKey(
    name="Client.driver_signing_public_key",
    description="public key for verifying driver signing."))

config_lib.CONFIG.AddOption(type_info.PEMPrivateKey(
    name="PrivateKeys.driver_signing_private_key",
    description="Private keys for signing drivers. NOTE: This "
    "key is usually kept offline and is thus not present in the "
    "configuration file."))


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
      fd = vfs.VFSOpen(args.pathspec)

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

    data = vfs.ReadVFS(args.pathspec, args.offset, args.length)
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
    self.src_fd = vfs.VFSOpen(args.src_path)
    self.src_fd.Seek(args.offset)
    offset = self.src_fd.Tell()

    self.length = args.length or sys.maxint

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
      directory = vfs.VFSOpen(args.pathspec)
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
      fd = vfs.VFSOpen(request.pathspec)
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


class StatFile(ListDirectory):
  """Sends a StatResponse for a single file."""
  in_rdfvalue = rdfvalue.ListDirRequest
  out_rdfvalue = rdfvalue.StatEntry

  def Run(self, args):
    """Sends a StatResponse for a single file."""
    try:
      fd = vfs.VFSOpen(args.pathspec)
      res = fd.Stat()

      self.SendReply(res)
    except (IOError, OSError), e:
      self.SetStatus(rdfvalue.GrrStatus.ReturnedStatus.IOERROR, e)
      return


class HashFile(ListDirectory):
  """Hashes the file and transmits it to the server."""
  in_rdfvalue = rdfvalue.ListDirRequest
  out_rdfvalue = rdfvalue.DataBlob

  def Run(self, args):
    """Hash a file."""
    try:
      fd = vfs.VFSOpen(args.pathspec)
      hasher = hashlib.sha256()
      while True:
        data = fd.Read(1024*1024)
        if not data: break

        hasher.update(data)

    except (IOError, OSError), e:
      self.SetStatus(rdfvalue.GrrStatus.ReturnedStatus.IOERROR, e)
      return

    self.SendReply(data=hasher.digest())


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
  """
  in_rdfvalue = rdfvalue.ExecuteBinaryRequest
  out_rdfvalue = rdfvalue.ExecuteBinaryResponse

  def WriteBlobToFile(self, signed_pb, lifetime, suffix=""):
    """Writes the blob to a file and returns its path."""

    temp_file = tempfiles.CreateGRRTempFile(suffix=suffix, lifetime=lifetime)
    with temp_file:
      path = temp_file.name
      temp_file.write(signed_pb.data)

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

    if sys.platform == "win32":
      # We need .exe here.
      suffix = ".exe"
    else:
      suffix = ""

    lifetime = args.time_limit
    # Keep the file for at least 5 seconds after execution.
    if lifetime > 0:
      lifetime += 5

    path = self.WriteBlobToFile(args.executable, lifetime, suffix)

    res = client_utils_common.Execute(path, args.args, args.time_limit,
                                      bypass_whitelist=True)
    (stdout, stderr, status, time_used) = res

    self.CleanUp(path)

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

    args.python_code.Verify(config_lib.CONFIG[
        "Client.executable_signing_public_key"])

    # The execed code can assign to this variable if it wants to return data.
    magic_return_str = ""
    logging.debug("exec for python code %s", args.python_code.data[0:100])
    # pylint: disable=exec-statement,unused-variable
    py_args = args.py_args.ToDict()
    exec(args.python_code.data)
    # pylint: enable=exec-statement,unused-variable
    time_used = time.time() - time_start
    # We have to return microseconds.
    result = rdfvalue.ExecutePythonResponse(
        time_used=int(1e6 * time_used),
        return_val=utils.SmartStr(magic_return_str))
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

  states = {
      "UNKNOWN": rdfvalue.NetworkConnection.State.UNKNOWN,
      "LISTEN": rdfvalue.NetworkConnection.State.LISTEN,
      "ESTABLISHED": rdfvalue.NetworkConnection.State.ESTAB,
      "TIME_WAIT": rdfvalue.NetworkConnection.State.TIME_WAIT,
      "CLOSE_WAIT": rdfvalue.NetworkConnection.State.CLOSE_WAIT,
      }

  def Run(self, unused_arg):
    # psutil will cause an active loop on Windows 2000
    if platform.system() == "Windows" and platform.version().startswith("5.0"):
      raise RuntimeError("ListProcesses not supported on Windows 2000")

    for proc in psutil.process_iter():
      response = rdfvalue.Process()
      for field in ["pid", "ppid", "name", "exe", "username", "terminal"]:
        try:
          if not hasattr(proc, field) or not getattr(proc, field):
            continue
          value = getattr(proc, field)
          if isinstance(value, (int, long)):
            setattr(response, field, value)
          else:
            setattr(response, field, utils.SmartUnicode(value))

        except (psutil.NoSuchProcess, psutil.AccessDenied):
          pass

      try:
        for arg in proc.cmdline:
          response.cmdline.append(utils.SmartUnicode(arg))
      except (psutil.NoSuchProcess, psutil.AccessDenied):
        pass

      try:
        response.nice = proc.get_nice()
      except (psutil.NoSuchProcess, psutil.AccessDenied):
        pass

      try:
        # Not available on Windows.
        if hasattr(proc, "uids"):
          (response.real_uid, response.effective_uid,
           response.saved_uid) = proc.uids
          (response.real_gid, response.effective_gid,
           response.saved_gid) = proc.gids
      except (psutil.NoSuchProcess, psutil.AccessDenied):
        pass

      try:
        response.ctime = long(proc.create_time * 1e6)
        response.status = str(proc.status)
      except (psutil.NoSuchProcess, psutil.AccessDenied):
        pass

      try:
        # Not available on OSX.
        if hasattr(proc, "getcwd"):
          response.cwd = utils.SmartUnicode(proc.getcwd())
      except (psutil.NoSuchProcess, psutil.AccessDenied):
        pass

      try:
        response.num_threads = proc.get_num_threads()
      except (psutil.NoSuchProcess, psutil.AccessDenied, RuntimeError):
        pass

      try:
        (response.user_cpu_time,
         response.system_cpu_time) = proc.get_cpu_times()
        # This is very time consuming so we do not collect cpu_percent here.
        # response.cpu_percent = proc.get_cpu_percent()
      except (psutil.NoSuchProcess, psutil.AccessDenied):
        pass

      try:
        response.RSS_size, response.VMS_size = proc.get_memory_info()
        response.memory_percent = proc.get_memory_percent()
      except (psutil.NoSuchProcess, psutil.AccessDenied):
        pass

      # Due to a bug in psutil, this function is disabled for now.
      # try:
      #   for f in proc.get_open_files():
      #     response.open_files.append(utils.SmartUnicode(f.path))
      # except (psutil.NoSuchProcess, psutil.AccessDenied):
      #   pass

      try:
        for c in proc.get_connections():
          conn = response.connections.Append(family=c.family,
                                             type=c.type)

          if c.status in self.states:
            conn.state = self.states[c.status]
          elif c.status:
            logging.info("Encountered unknown connection status (%s).",
                         c.status)

          conn.local_address.ip, conn.local_address.port = c.local_address

          # Could be in state LISTEN.
          if c.remote_address:
            conn.remote_address.ip, conn.remote_address.port = c.remote_address

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
  OP_ENCRYPT = 1

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
    fd = vfs.VFSOpen(args.pathspec)

    key = args.key
    if len(key) != 16:
      raise RuntimeError("Invalid key length (%d)." % len(key))

    iv = args.iv
    if len(iv) != 16:
      raise RuntimeError("Invalid iv length (%d)." % len(iv))

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

    cipher = EVP.Cipher(alg="aes_128_cbc", key=key, iv=iv, op=self.OP_ENCRYPT)

    while True:
      data = fd.read(self.BLOCK_SIZE)
      if not data:
        break
      self.Send(s, cipher.update(data))
      # Send heartbeats for long files.
      self.Progress()
    self.Send(s, cipher.final())
    s.close()

    self.SendReply(fd.Stat())
