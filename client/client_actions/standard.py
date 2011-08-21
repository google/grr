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


import hashlib
import logging
import os
import platform
import re
import socket
import stat
import sys
import time
from grr.client import conf as flags
from grr.client import actions
from grr.client import client_utils
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
    """Read a buffer on the client and send to the server."""
    # Make sure we limit the size of our output
    if args.length > MAX_BUFFER_SIZE:
      raise RuntimeError("Can not read buffers this large.")

    fd = vfs.VFSHandlerFactory(args.pathspec)

    fd.Seek(args.offset)
    offset = fd.Tell()

    data = fd.Read(args.length)

    respathspec = client_utils.SplitPathspec(fd.request)

    # Now return the data to the server
    self.SendReply(offset=offset, data=data,
                   length=len(data), pathspec=respathspec)


class ListDirectory(ReadBuffer):
  """Lists all the files in a directory."""
  in_protobuf = jobs_pb2.ListDirRequest
  out_protobuf = jobs_pb2.StatResponse

  def Run(self, args):
    """List a directory."""
    directory = vfs.VFSHandlerFactory(args.pathspec)
    files = list(directory.ListFiles())
    files.sort(key=lambda x: x.path)

    for response in files:
      self.SendReply(response)


class IteratedListDirectory(actions.IteratedAction):
  """Lists a directory as an iterator."""
  in_protobuf = jobs_pb2.ListDirRequest
  out_protobuf = jobs_pb2.StatResponse

  def Iterate(self, request, client_state):
    """Restore our way through the directory using an Iterator."""
    files = list(vfs.VFSHandlerFactory(request.pathspec).ListFiles())
    files.sort(key=lambda x: x.path)

    index = client_state.get("index", 0)
    length = request.iterator.number
    for response in files[index:index+length]:
      self.SendReply(response)

    # Update the state
    client_state["index"] = index + length


class StatFile(ListDirectory):
  """Send a StatResponse for a single file."""
  in_protobuf = jobs_pb2.ListDirRequest
  out_protobuf = jobs_pb2.StatResponse

  def Run(self, args):
    """Send a StatResponse for a single file."""
    fd = vfs.VFSHandlerFactory(args.pathspec)
    res = fd.Stat()
    self.SendReply(res)


class HashFile(ListDirectory):
  """Hash the file and transmit it to the server."""
  in_protobuf = jobs_pb2.ListDirRequest
  out_protobuf = jobs_pb2.DataBlob

  def Run(self, args):
    """Hash a file."""
    fd = vfs.VFSHandlerFactory(args.pathspec)

    hasher = hashlib.sha256()
    while True:
      data = fd.Read(1024*1024)
      if not data: break

      hasher.update(data)

    self.SendReply(data=hasher.digest())


class Echo(actions.ActionPlugin):
  """Return a message to the server."""
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
  """Retrieve platform information."""
  out_protobuf = jobs_pb2.Uname

  def Run(self, unused_args):
    uname = platform.uname()
    self.SendReply(system=uname[0],
                   node=uname[1],
                   release=uname[2],
                   version=uname[3],
                   machine=uname[4])


class KillSlave(actions.ActionPlugin):
  """Kill any slaves, no cleanups."""

  def Run(self, unused_arg):
    if isinstance(self.grr_context, comms.SlaveContext):
      logging.info("Dying on request.")
      sys.exit(0)


class Find(actions.IteratedAction):
  """Recurse through a directory returning files which match conditions."""
  in_protobuf = jobs_pb2.Find
  out_protobuf = jobs_pb2.Find

  filesystem_id = 0

  # If this is true we do not cross filesystem boundary
  xdev = False

  def ListDirectory(self, pathspec, state, depth=0):
    """A Recursive generator of files."""
    # Limit recursion depth
    if depth >= self.max_depth: return

    files = list(vfs.VFSHandlerFactory(pathspec).ListFiles())

    # Recover the start point for this directory from the state dict so we can
    # resume.
    start = state.get(pathspec.path, 0)

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

      state[pathspec.path] = i + 1
      yield file_stat

    # Now remove this from the state dict to prevent it from getting too large
    try:
      del state[pathspec.path]
    except KeyError: pass

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
    except KeyError: pass

    # Filename regex test

    # SplitPath guarantees that mountpoint+path yields a valid os path...
    path = file_stat.pathspec.mountpoint + file_stat.pathspec.path
    if not self.filter_expression["filename_regex"].search(
        os.path.basename(os.path.normpath(utils.SmartStr(path)))):
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

      with vfs.VFSHandlerFactory(file_stat.pathspec) as fd:
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
    except (IOError, KeyError): pass

    return True

  def Iterate(self, request, client_state):
    """Restore our way through the directory using an Iterator."""
    self.filter_expression = dict(filename_regex=re.compile(request.path_regex))

    if request.HasField("data_regex"):
      self.filter_expression["data_regex"] = re.compile(request.data_regex)

    if request.HasField("end_time") or request.HasField("start_time"):
      self.filter_expression["end_time"] = request.end_time or time.time() * 1e6
      self.filter_expression["start_time"] = request.start_time

    limit = request.iterator.number
    self.xdev = request.xdev
    self.max_depth = request.max_depth
    count = 0

    # TODO(user): What is a reasonable measure of work here?
    for f in self.ListDirectory(request.pathspec, client_state):
      # Only send the reply if the file matches all criteria
      if self.FilterFile(f):
        result = jobs_pb2.Find()
        result.hit.CopyFrom(f)
        self.SendReply(result)

      # We only check a limited number of files in each iteration. This might
      # result in returning an empty response - but the iterator is not yet
      # complete. Flows much check the state of the iterator explicitly.
      count += 1
      if count >= limit:
        logging.debug("Processed %s entries, quitting", count)
        return

    # End this iterator
    request.iterator.state = jobs_pb2.Iterator.FINISHED


class UpdateConfig(actions.ActionPlugin):
  """Updates configuration parameters on the client."""
  in_protobuf = jobs_pb2.GRRConfig

  def Run(self, arg):
    updated_keys = []
    for field, value in arg.ListFields():
      setattr(conf.FLAGS, field.name, value)
      updated_keys.append(field.name)

    conf.PARSER.UpdateConfig(updated_keys)
