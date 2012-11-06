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

"""Standard actions that happen on the client."""


import ctypes
import hashlib
import os
import socket
import stat
import sys
import tempfile
import time
import zlib


from M2Crypto import EVP
import psutil

from grr.client import conf as flags
import logging
from grr.client import actions
from grr.client import client_config
from grr.client import client_utils_common
from grr.client import vfs

from grr.lib import utils
from grr.proto import jobs_pb2
from grr.proto import sysinfo_pb2

# We do not send larger buffers than this:
MAX_BUFFER_SIZE = 640*1024

FLAGS = flags.FLAGS


class ReadBuffer(actions.ActionPlugin):
  """Reads a buffer from a file and returns it to a server callback."""
  in_protobuf = jobs_pb2.BufferReadMessage
  out_protobuf = jobs_pb2.BufferReadMessage

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
      self.SetStatus(jobs_pb2.GrrStatus.IOERROR, e)
      return

    # Now return the data to the server
    self.SendReply(offset=offset, data=data,
                   length=len(data), pathspec=fd.pathspec.ToProto())


HASH_CACHE = utils.FastStore(100)


class TransferBuffer(actions.ActionPlugin):
  """Reads a buffer from a file and returns it to the server efficiently."""
  in_protobuf = jobs_pb2.BufferReadMessage
  out_protobuf = jobs_pb2.BufferReadMessage

  def Run(self, args):
    """Reads a buffer on the client and sends it to the server."""
    # Make sure we limit the size of our output
    if args.length > MAX_BUFFER_SIZE:
      raise RuntimeError("Can not read buffers this large.")

    # Grab the buffer
    fd = vfs.VFSOpen(args.pathspec)
    fd.Seek(args.offset)
    data = fd.Read(args.length)
    result = jobs_pb2.DataBlob()

    digest = hashlib.sha256(data).digest()

    # Ok we need to send it. First compress the data.
    result.data = zlib.compress(data)
    result.compression = result.ZCOMPRESSION

    # Now return the data to the server into the special TransferStore well
    # known flow.
    self.grr_worker.SendReply(result, session_id="W:TransferStore")

    # Now report the hash of this blob to our flow as well as the offset and
    # length.
    self.SendReply(offset=args.offset, length=len(data),
                   data=digest)


class HashBuffer(actions.ActionPlugin):
  """Hash a buffer from a file and returns it to the server efficiently."""
  in_protobuf = jobs_pb2.BufferReadMessage
  out_protobuf = jobs_pb2.BufferReadMessage

  def Run(self, args):
    """Reads a buffer on the client and sends it to the server."""
    # Make sure we limit the size of our output
    if args.length > MAX_BUFFER_SIZE:
      raise RuntimeError("Can not read buffers this large.")

    # Grab the buffer
    fd = vfs.VFSOpen(args.pathspec)
    fd.Seek(args.offset)
    data = fd.Read(args.length)

    digest = hashlib.sha256(data).digest()

    # Now report the hash of this blob to our flow as well as the offset and
    # length.
    self.SendReply(offset=args.offset, length=len(data),
                   data=digest)


class ListDirectory(ReadBuffer):
  """Lists all the files in a directory."""
  in_protobuf = jobs_pb2.ListDirRequest
  out_protobuf = jobs_pb2.StatResponse

  def Run(self, args):
    """Lists a directory."""
    try:
      directory = vfs.VFSOpen(args.pathspec)
    except (IOError, OSError), e:
      self.SetStatus(jobs_pb2.GrrStatus.IOERROR, e)
      return

    files = list(directory.ListFiles())
    files.sort(key=lambda x: x.pathspec.path)

    for response in files:
      self.SendReply(response)


class IteratedListDirectory(actions.IteratedAction):
  """Lists a directory as an iterator."""
  in_protobuf = jobs_pb2.ListDirRequest
  out_protobuf = jobs_pb2.StatResponse

  def Iterate(self, request, client_state):
    """Restores its way through the directory using an Iterator."""
    try:
      fd = vfs.VFSOpen(request.pathspec)
    except (IOError, OSError), e:
      self.SetStatus(jobs_pb2.GrrStatus.IOERROR, e)
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
  in_protobuf = jobs_pb2.ListDirRequest
  out_protobuf = jobs_pb2.StatResponse

  def Run(self, args):
    """Sends a StatResponse for a single file."""
    try:
      fd = vfs.VFSOpen(args.pathspec)
      res = fd.Stat()
      self.SendReply(res)
    except (IOError, OSError), e:
      self.SetStatus(jobs_pb2.GrrStatus.IOERROR, e)
      return


class HashFile(ListDirectory):
  """Hashes the file and transmits it to the server."""
  in_protobuf = jobs_pb2.ListDirRequest
  out_protobuf = jobs_pb2.DataBlob

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
      self.SetStatus(jobs_pb2.GrrStatus.IOERROR, e)
      return

    self.SendReply(data=hasher.digest())


class ExecuteCommand(actions.ActionPlugin):
  """Executes one of the predefined commands."""
  in_protobuf = jobs_pb2.ExecuteRequest
  out_protobuf = jobs_pb2.ExecuteResponse

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

    result = jobs_pb2.ExecuteResponse()
    result.request.CopyFrom(command)
    result.stdout = stdout
    result.stderr = stderr
    result.exit_status = status
    # We have to return microseconds.
    result.time_used = (int) (1e6 * time_used)
    self.SendReply(result)


class ExecuteBinaryCommand(actions.ActionPlugin):
  """Executes a command from a passed in binary.

  Obviously this is a dangerous function, it provides for arbitrary code exec by
  the server running as root/SYSTEM.
  This is protected by the client_config.EXEC_SIGNING_KEY, which should be
  stored offline and well protected.

  This method can be utilized as part of an autoupdate mechanism if necessary.
  """
  in_protobuf = jobs_pb2.ExecuteBinaryRequest
  out_protobuf = jobs_pb2.ExecuteBinaryResponse

  def WriteBlobToFile(self, signed_pb, write_path, suffix=""):
    """Writes the blob to a file and returns its path."""

    if write_path:
      # Caller passed in the path to write our file to.
      with open(write_path, "wb") as fd:
        fd.write(signed_pb.data)
      path = write_path
    else:
      # Need to make a path to use. Want to put it somewhere we know we get
      # good perms.
      if sys.platform == "win32":
        # Wherever we are being run from will have good perms.
        write_dir = os.path.dirname(sys.executable)
      else:
        # We trust mkstemp on other platforms.
        write_dir = None
      handle, path = tempfile.mkstemp(suffix=suffix, prefix="tmp",
                                      dir=write_dir)
      fd = os.fdopen(handle, "wb")
      try:
        fd.write(signed_pb.data)
      finally:
        fd.close()

    return path

  def CleanUp(self, path):
    """Removes the temp file."""
    try:
      os.remove(path)
    except (OSError, IOError), e:
      logging.info("Failed to remove temporary file %s. Err: %s", path, e)

  def VerifyBlob(self, signed_pb):
    pub_key = client_config.EXEC_SIGNING_KEY.get(FLAGS.camode.upper())
    if not client_utils_common.VerifySignedBlob(signed_pb,
                                                pub_key=pub_key):
      raise OSError("Code signature signing failure.")

  def Run(self, args):
    """Run."""
    self.VerifyBlob(args.executable)

    if sys.platform == "win32":
      # We need .exe here.
      suffix = ".exe"
    else:
      suffix = ""
    path = self.WriteBlobToFile(args.executable, args.write_path, suffix)
    os.chmod(path, stat.S_IXUSR | stat.S_IRUSR | stat.S_IWUSR)

    cmd = path
    cmd_args = args.args
    time_limit = args.time_limit

    res = client_utils_common.Execute(cmd, cmd_args, time_limit,
                                      bypass_whitelist=True)
    (stdout, stderr, status, time_used) = res

    self.CleanUp(cmd)

    # Limit output to 10MB so our response doesn't get too big.
    stdout = stdout[:10 * 1024 * 1024]
    stderr = stderr[:10 * 1024 * 1024]

    result = jobs_pb2.ExecuteBinaryResponse()
    result.stdout = stdout
    result.stderr = stderr
    result.exit_status = status
    # We have to return microseconds.
    result.time_used = (int) (1e6 * time_used)
    self.SendReply(result)


class ExecutePython(actions.ActionPlugin):
  """Executes python code with exec.

  Obviously this is a dangerous function, it provides for arbitrary code exec by
  the server running as root/SYSTEM.
  This is protected by the client_config.EXEC_SIGNING_KEY, which should be
  stored offline and well protected.
  """
  in_protobuf = jobs_pb2.ExecutePythonRequest
  out_protobuf = jobs_pb2.ExecutePythonResponse

  def Run(self, args):
    """Run."""
    time_start = time.time()

    pub_key = client_config.EXEC_SIGNING_KEY.get(FLAGS.camode.upper())
    if not client_utils_common.VerifySignedBlob(args.python_code,
                                                pub_key=pub_key):
      raise OSError("Code signature signing failure.")

    # The execed code can assign to this variable if it wants to return data.
    magic_return_str = ""
    logging.debug("exec for python code %s", args.python_code.data[0:100])
    # pylint: disable=W0122
    exec(args.python_code.data)
    # pylint: enable=W0122
    time_used = time.time() - time_start
    # We have to return microseconds.
    result = jobs_pb2.ExecutePythonResponse()
    result.time_used = (int) (1e6 * time_used)
    result.return_val = utils.SmartStr(magic_return_str)
    self.SendReply(result)


class Segfault(actions.ActionPlugin):
  """This action is just for debugging. It induces a segfault."""
  in_protobuf = jobs_pb2.EmptyMessage
  out_protobuf = jobs_pb2.EmptyMessage

  def Run(self, unused_args):
    """Does the segfaulting."""
    if FLAGS.debug:
      logging.warning("Segfault action requested :(")
      print ctypes.cast(1, ctypes.POINTER(ctypes.c_void_p)).contents
    else:
      logging.warning("Segfault requested but not running in debug mode.")


class ListProcesses(actions.ActionPlugin):
  """This action lists all the processes running on a machine."""
  in_protobuf = None
  out_protobuf = sysinfo_pb2.Process

  states = {
      "UNKNOWN": sysinfo_pb2.NetworkConnection.UNKNOWN,
      "LISTEN": sysinfo_pb2.NetworkConnection.LISTEN,
      "ESTABLISHED": sysinfo_pb2.NetworkConnection.ESTAB,
      "TIME_WAIT": sysinfo_pb2.NetworkConnection.TIME_WAIT,
      "CLOSE_WAIT": sysinfo_pb2.NetworkConnection.CLOSE_WAIT,
      }

  def Run(self, unused_arg):

    for proc in psutil.process_iter():
      response = sysinfo_pb2.Process()
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
          response.cwd = proc.getcwd()
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

      try:
        for f in proc.get_open_files():
          response.open_files.append(utils.SmartUnicode(f.path))
      except (psutil.NoSuchProcess, psutil.AccessDenied):
        pass

      try:
        for c in proc.get_connections():
          conn = response.connections.add()
          conn.family = c.family
          conn.type = c.type
          if c.status in self.states:
            conn.state = self.states[c.status]
          elif c.status:
            logging.info("Encountered unknown connection status (%s).",
                         c.status)

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
  in_protobuf = jobs_pb2.SendFileRequest
  out_protobuf = jobs_pb2.StatResponse

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

    if args.address_family == jobs_pb2.NetworkAddress.INET:
      family = socket.AF_INET
    elif args.address_family == jobs_pb2.NetworkAddress.INET6:
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
