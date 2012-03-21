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
import logging
import platform
import re
import socket
import stat
import sys
import time
import zlib


from grr.client import conf as flags
from grr.client import actions
from grr.client import client_config
from grr.client import client_utils_common
from grr.client import comms
from grr.client import conf
from grr.client import vfs
from grr.lib import utils
from grr.proto import jobs_pb2

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

    # Check if the hash is in cache
    try:
      HASH_CACHE.Get(digest)
    except KeyError:
      # Ok we need to send it. First compress the data.
      result.data = zlib.compress(data)
      result.compression = result.ZCOMPRESSION

      # Now return the data to the server into the special TransferStore well
      # known flow.
      self.grr_context.SendReply(result, session_id="W:TransferStore")
      HASH_CACHE.Put(digest, 1)

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


class Echo(actions.ActionPlugin):
  """Returns a message to the server."""
  in_protobuf = jobs_pb2.PrintStr
  out_protobuf = jobs_pb2.PrintStr

  def Run(self, args):
    self.SendReply(args)


class GetHostname(actions.ActionPlugin):
  """Retrieves the host name of the client."""
  out_protobuf = jobs_pb2.DataBlob

  def Run(self, unused_args):
    self.SendReply(string=socket.gethostname())


class GetPlatformInfo(actions.ActionPlugin):
  """Retrieves platform information."""
  out_protobuf = jobs_pb2.Uname

  def Run(self, unused_args):
    uname = platform.uname()
    self.SendReply(system=uname[0],
                   node=uname[1],
                   release=uname[2],
                   version=uname[3],
                   machine=uname[4])


class KillSlave(actions.ActionPlugin):
  """Kills any slaves, no cleanups."""

  def Run(self, unused_arg):
    if isinstance(self.grr_context, comms.SlaveContext):
      logging.info("Dying on request.")
      sys.exit(0)


class Find(actions.IteratedAction):
  """Recurses through a directory returning files which match conditions."""
  in_protobuf = jobs_pb2.Find
  out_protobuf = jobs_pb2.Find

  filesystem_id = 0

  # If this is true we do not cross filesystem boundary
  xdev = False

  def ListDirectory(self, pathspec, state, depth=0):
    """A Recursive generator of files."""
    pathspec = utils.Pathspec(pathspec)

    # Limit recursion depth
    if depth >= self.max_depth: return

    try:
      fd = vfs.VFSOpen(pathspec)
      files = list(fd.ListFiles())
    except (IOError, OSError), e:
      if depth == 0:
        # We failed to open the directory the server asked for because dir
        # doesn't exist or some other reason. So we set status and return
        # back to the caller ending the Iterator.
        self.SetStatus(jobs_pb2.GrrStatus.IOERROR, e)
      else:
        # Can't open the directory we're searching, ignore the directory.
        logging.info("Find failed to ListDirectory for %s. Err: %s", pathspec, e)
      return

    files.sort(key=lambda x: x.pathspec.SerializeToString())

    # Recover the start point for this directory from the state dict so we can
    # resume.
    start = state.get(pathspec.CollapsePath(), 0)

    for i, file_stat in enumerate(files):
      # Skip the files we already did before
      if i < start: continue

      if stat.S_ISDIR(file_stat.st_mode):
        # Do not traverse directories in a different filesystem.
        if self.filesystem_id == 0 or self.filesystem_id == file_stat.st_dev:
          for child_stat in self.ListDirectory(file_stat.pathspec,
                                               state, depth + 1):
            yield child_stat

      if self.xdev:
        self.filesystem_id = file_stat.st_dev

      state[pathspec.CollapsePath()] = i + 1
      yield file_stat

    # Now remove this from the state dict to prevent it from getting too large
    try:
      del state[pathspec.CollapsePath()]
    except KeyError:
      pass

  def FilterFile(self, file_stat):
    """Tests a file for filters.

    Args:
      file_stat: A StatResponse of specified file.

    Returns:
      True of the file matches all conditions, false otherwise.
    """
    # Check timestamp if needed
    try:
      if (file_stat.st_mtime > self.filter_expression["start_time"] and
          file_stat.st_mtime < self.filter_expression["end_time"]):
        return True
    except KeyError:
      pass

    # Filename regex test
    if not self.filter_expression["filename_regex"].search(
        utils.Pathspec(file_stat.pathspec).Basename()):
      return False

    # Should we test for content? (Key Error skips this check)
    if ("data_regex" in self.filter_expression and
        not self.TestFileContent(file_stat)):
      return False
    return True

  def TestFileContent(self, file_stat):
    """Checks the file for the presence of the regular expression."""
    # Content regex check
    try:
      data_regex = self.filter_expression["data_regex"]

      # Can only search regular files
      if not stat.S_ISREG(file_stat.st_mode): return False

      # Search the file
      found = False
      data = ""

      with vfs.VFSOpen(file_stat.pathspec) as fd:
        while True:
          data_read = fd.read(1000000)
          if not data_read: break
          data += data_read

          if data_regex.search(data):
            found = True
            break

          # Keep a bit of context from the last buffer to ensure we dont miss a
          # match broken by buffer. We do not expect regex's to match something
          # larger than about 100 chars.
          data = data[-100:]

      if not found: return False
    except (IOError, KeyError):
      pass

    return True

  def Iterate(self, request, client_state):
    """Restores its way through the directory using an Iterator."""
    self.filter_expression = dict(filename_regex=re.compile(request.path_regex))

    if request.HasField("data_regex"):
      self.filter_expression["data_regex"] = re.compile(request.data_regex)

    if request.HasField("end_time") or request.HasField("start_time"):
      self.filter_expression["end_time"] = request.end_time or time.time() * 1e6
      self.filter_expression["start_time"] = request.start_time

    limit = request.iterator.number
    self.xdev = request.xdev
    self.max_depth = request.max_depth

    # TODO(user): What is a reasonable measure of work here?
    for count, f in enumerate(
        self.ListDirectory(request.pathspec, client_state)):
      # Only send the reply if the file matches all criteria
      if self.FilterFile(f):
        result = jobs_pb2.Find()
        result.hit.CopyFrom(f)
        self.SendReply(result)

      # We only check a limited number of files in each iteration. This might
      # result in returning an empty response - but the iterator is not yet
      # complete. Flows must check the state of the iterator explicitly.
      if count >= limit - 1:
        logging.debug("Processed %s entries, quitting", count)
        return

    # End this iterator
    request.iterator.state = jobs_pb2.Iterator.FINISHED


class GetConfig(actions.ActionPlugin):
  """Retrieves the running configuration parameters."""
  in_protobuf = None
  out_protobuf = jobs_pb2.GRRConfig

  def Run(self, unused_arg):
    out = jobs_pb2.GRRConfig()
    for field in out.DESCRIPTOR.fields_by_name:
      if hasattr(conf.FLAGS, field):
        setattr(out, field, getattr(conf.FLAGS, field))
    self.SendReply(out)


class UpdateConfig(actions.ActionPlugin):
  """Updates configuration parameters on the client."""
  in_protobuf = jobs_pb2.GRRConfig

  UPDATEABLE_FIELDS = ["foreman_check_frequency",
                       "location",
                       "max_post_size",
                       "max_out_queue",
                       "poll_min",
                       "poll_max",
                       "poll_slew",
                       "compression",
                       "verbose"]

  def Run(self, arg):
    """Does the actual work."""
    updated_keys = []
    disallowed_fields = []
    for field, value in arg.ListFields():
      if field.name in self.UPDATEABLE_FIELDS:
        setattr(conf.FLAGS, field.name, value)
        updated_keys.append(field.name)
      else:
        disallowed_fields.append(field.name)

    if disallowed_fields:
      logging.warning("Received an update request for restricted field(s) %s.",
                      ",".join(disallowed_fields))
    try:
      conf.PARSER.UpdateConfig(updated_keys)
    except (IOError, OSError):
      pass


class GetClientInfo(actions.ActionPlugin):
  """Obtains information about the GRR client installed."""
  out_protobuf = jobs_pb2.ClientInformation

  def Run(self, unused_args):

    self.SendReply(
        client_name=client_config.GRR_CLIENT_NAME,
        client_version=client_config.GRR_CLIENT_VERSION,
        revision=client_config.GRR_CLIENT_REVISION,
        build_time=client_config.GRR_CLIENT_BUILDTIME,
        )


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

    # Limit output to 200k so our response doesn't get too big.
    stdout = stdout[:200 * 1024]
    stderr = stderr[:200 * 1024]

    result = jobs_pb2.ExecuteResponse()
    result.request.CopyFrom(command)
    result.stdout = stdout
    result.stderr = stderr
    result.exit_status = status
    # We have to return microseconds.
    result.time_used = (int) (1e6 * time_used)
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
