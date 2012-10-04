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

"""These are filesystem related flows."""


import stat

from grr.lib import aff4
from grr.lib import flow
from grr.lib import type_info
from grr.lib import utils
from grr.proto import jobs_pb2


class ListDirectory(flow.GRRFlow):
  """List files in a directory."""

  category = "/Filesystem/"
  urn = None
  flow_typeinfo = {"pathtype": type_info.ProtoEnum(jobs_pb2.Path, "PathType"),
                   "pathspec": type_info.ProtoOrNone(jobs_pb2.Path)}

  def __init__(self, path="/",
               pathtype=jobs_pb2.Path.OS,
               pathspec=None, **kwargs):
    """Constructor.

    Args:
      path: The directory path to list.
      pathtype: Identifies requested path type (Enum from Path protobuf).
      pathspec: This flow also accepts all the information in one pathspec.
    """
    if pathspec:
      self._pathpb = pathspec
      self.path = pathspec.path
    else:
      self.path = utils.NormalizePath(path)
      self._pathpb = jobs_pb2.Path(path=self.path, pathtype=int(pathtype))

    flow.GRRFlow.__init__(self, **kwargs)

  @flow.StateHandler(next_state=["List", "Stat"])
  def Start(self, unused_response):
    """Issue a request to list the directory."""
    self.CallClient("StatFile", pathspec=self._pathpb, next_state="Stat")

    # We use data to pass the path to the callback:
    self.CallClient("ListDirectory", pathspec=self._pathpb, next_state="List")

  @flow.StateHandler(jobs_pb2.StatResponse)
  def Stat(self, responses):
    """Save stat information on the directory."""
    # Did it work?
    if not responses.success:
      self.Error("Could not stat directory: %s" % responses.status)

    else:
      # Keep the stat response for later.
      self.stat = responses.First()
      self.directory_pathspec = utils.Pathspec(self.stat.pathspec)

      # The full path of the object is the combination of the client_id and the
      # path.
      self.urn = aff4.AFF4Object.VFSGRRClient.PathspecToURN(
          self.directory_pathspec, self.client_id)

  @flow.StateHandler(jobs_pb2.StatResponse)
  def List(self, responses):
    """Collect the directory listing and store in the datastore."""
    if not responses.success:
      raise flow.FlowError(str(responses.status))

    self.Status("Listed %s", self.urn)

    # The AFF4 object is opened for writing with an asyncronous close for speed.
    fd = aff4.FACTORY.Create(self.urn, "VFSDirectory", mode="w",
                             token=self.token)

    fd.Set(fd.Schema.PATHSPEC(self.directory_pathspec))
    fd.Set(fd.Schema.STAT(self.stat))

    fd.Close(sync=False)

    for st in responses:
      self.CreateAFF4Object(st, self.client_id, self.token, False)
      self.SendReply(st)  # Send Stats to parent flows.

    aff4.FACTORY.Flush()

  def End(self):
    if self.urn:
      self.Notify("ViewObject", self.urn, u"Listed {0}".format(self.path))

  def CreateAFF4Object(self, stat_response, client_id, token, sync=False):
    """This creates a File or a Directory from a stat response."""

    urn = aff4.AFF4Object.VFSGRRClient.PathspecToURN(stat_response.pathspec,
                                                     client_id)
    if stat.S_ISDIR(stat_response.st_mode):
      fd = aff4.FACTORY.Create(urn, "VFSDirectory", mode="w", token=token)
    else:
      fd = aff4.FACTORY.Create(urn, "VFSFile", mode="w", token=token)
    fd.Set(fd.Schema.STAT(stat_response))
    fd.Set(fd.Schema.PATHSPEC(stat_response.pathspec))
    fd.Close(sync=sync)


class IteratedListDirectory(ListDirectory):
  """A Flow to retrieve a directory listing using an iterator.

  This flow is an example for how to use the iterated client actions. Normally
  you do not need to call this flow - a ListDirectory flow is enough.
  """

  category = None

  @flow.StateHandler(next_state="List")
  def Start(self, unused_response):
    """Issue a request to list the directory."""
    # We use data to pass the path to the callback:
    self.request = jobs_pb2.ListDirRequest(pathspec=self._pathpb)

    # For this example we will use a really small number to force many round
    # trips with the client. This is a performance killer.
    self.request.iterator.number = 50
    self.responses = []
    self.urn = None

    self.CallClient("IteratedListDirectory", self.request,
                    next_state="List", request_data=dict(path=self.path))

  @flow.StateHandler(jobs_pb2.StatResponse, next_state="List")
  def List(self, responses):
    """Collect the directory listing and store in the data store."""
    if not responses.success:
      raise flow.FlowError(str(responses.status))

    if responses:
      for response in responses:
        self.responses.append(response)

      self.request.iterator.CopyFrom(responses.iterator)
      self.CallClient("IteratedListDirectory", self.request, next_state="List")
    else:
      self.StoreDirectory()

  def StoreDirectory(self):
    """Store the content of the directory listing in the AFF4 object."""
    # The full path of the object is the combination of the client_id and the
    # path.
    if not self.responses: return

    directory_pathspec = utils.Pathspec(self.responses[0].pathspec).Dirname()

    urn = aff4.AFF4Object.VFSGRRClient.PathspecToURN(
        directory_pathspec, self.client_id)

    if not self.urn: self.urn = urn    # First dir we get back is the main urn.

    fd = aff4.FACTORY.Create(urn, "VFSDirectory", token=self.token)
    fd.Close(sync=False)

    for st in self.responses:
      self.CreateAFF4Object(st, self.client_id, self.token)
      self.SendReply(st)  # Send Stats to parent flows.

  def End(self):
    self.Notify("ViewObject", self.urn, "List of {0} completed.".format(
        self.path))


class RecursiveListDirectory(ListDirectory):
  """Recursively list directory on the client."""

  category = "/Filesystem/"
  flow_typeinfo = {"pathtype": type_info.ProtoEnum(jobs_pb2.Path, "PathType"),
                   "pathspec": type_info.ProtoOrNone(jobs_pb2.Path)}

  def __init__(self, path="/",
               pathtype=jobs_pb2.Path.OS,
               pathspec=None, max_depth=5, **kwargs):
    """This flow builds a timeline for the filesystem on the client.

    Args:
      path: Search recursively from this place.
      pathtype: Identifies requested path type. Enum from Path protobuf.
      pathspec: This flow also accepts all the information in one pathspec.
      max_depth: Maximum depth to recurse
    """
    flow.GRRFlow.__init__(self, **kwargs)
    self.max_depth = max_depth
    if pathspec:
      self.pathspec = pathspec
    else:
      self.pathspec = jobs_pb2.Path(path=utils.NormalizePath(path),
                                    pathtype=int(pathtype))

    # The first directory we listed.
    self.first_directory = None

    self._dir_count = 0
    self._file_count = 0

  @flow.StateHandler(next_state="ProcessDirectory")
  def Start(self):
    """List the initial directory."""
    self.CallClient("ListDirectory", pathspec=self.pathspec,
                    next_state="ProcessDirectory")

  @flow.StateHandler(next_state="ProcessDirectory")
  def ProcessDirectory(self, responses):
    """Recursively list the directory, and add to the timeline."""
    if responses.success:
      r = responses.First()

      if r is None: return
      directory_pathspec = utils.Pathspec(r.pathspec).Dirname()

      urn = aff4.AFF4Object.VFSGRRClient.PathspecToURN(
          directory_pathspec, self.client_id)

      self.StoreDirectory(responses)

      # If the urn is too deep we quit to prevent recursion errors.
      if self.first_directory is None:
        self.first_directory = urn
      elif (len(urn.RelativeName(self.first_directory).split("/")) >=
            self.max_depth):
        self.Log("Exceeded maximum path depth at %s.",
                 urn.RelativeName(self.first_directory))
        return

      for stat_response in responses:
        # Queue a list directory for each directory here, but do not follow
        # symlinks.
        if (not stat_response.HasField("symlink") and
            stat.S_ISDIR(stat_response.st_mode)):
          self.CallClient("ListDirectory", pathspec=stat_response.pathspec,
                          next_state="ProcessDirectory")
          self._dir_count += 1
          if self._dir_count % 100 == 0:   # Log every 100 directories
            self.Status("Reading %s. (%d nodes, %d directories done)",
                        urn.RelativeName(self.first_directory),
                        self._file_count, self._dir_count)
      self._file_count += len(responses)

  def StoreDirectory(self, responses):
    """Stores all stat responses."""
    for st in responses:
      self.CreateAFF4Object(st, self.client_id, self.token)
      self.SendReply(st)  # Send Stats to parent flows.

  def End(self):
    status_text = "Recursive Directory Listing complete %d nodes, %d dirs"
    self.Notify("ViewObject", self.first_directory, status_text % (
        self._file_count, self._dir_count))
    self.Status(status_text, self._file_count, self._dir_count)


class SlowGetFile(flow.GRRFlow):
  """Simple file retrival."""

  category = "/Filesystem/"
  flow_typeinfo = {"pathtype": type_info.ProtoEnum(jobs_pb2.Path, "PathType"),
                   "pathspec": type_info.ProtoOrNone(jobs_pb2.Path)}

  # Read in 32kb chunks
  _CHUNK_SIZE = 1024 * 32

  # We have a maximum of this many chunk reads outstanding (about 10mb)
  _WINDOW_SIZE = 330

  def __init__(self, path="/",
               pathtype=jobs_pb2.Path.OS, aff4_chunk_size=2**20,
               pathspec=None, **kwargs):
    """Constructor.

    This flow does not use the efficient hash transfer mechanism used in GetFile
    so its only really suitable for transferring very small files.

    Args:
      path: The directory path to list.
      pathtype: Identifies requested path type. Enum from Path protobuf.
      aff4_chunk_size: Specifies how much data is sent back from the
                       client in each chunk.
      pathspec: Use a pathspec instead of a path.
    """
    self.urn = None
    self.current_chunk_number = 0
    self.aff4_chunk_size = aff4_chunk_size
    self.fd = None
    if pathspec:
      self._pathpb = pathspec
    else:
      self._pathpb = jobs_pb2.Path(path=path, pathtype=int(pathtype))

    flow.GRRFlow.__init__(self, **kwargs)

  @flow.StateHandler(next_state=["Hash", "Stat", "ReadBuffer"])
  def Start(self):
    """Get information about the file from the client."""

    # We first obtain information about how large the file is
    self.CallClient("StatFile", pathspec=self._pathpb, next_state="Stat")

    # This flow relies on the fact that responses are always returned
    # in order:
    self.CallClient("HashFile", pathspec=self._pathpb, next_state="Hash")

    # Read the first buffer
    self.CallClient("ReadBuffer", pathspec=self._pathpb, offset=0,
                    length=self._CHUNK_SIZE, next_state="ReadBuffer")

  @flow.StateHandler(jobs_pb2.StatResponse, next_state="ReadBuffer")
  def Stat(self, responses):
    """Retrieve the file size.

    We determine how to store the file based on its size.

    Args:
     responses: Standard state Responses object.

    Raises:
     IOError: if the stat() fails on the client.
    """
    # Did it work?
    if not responses.success:
      # Its better to raise rather than merely logging since it will make it to
      # the flow's protobuf and users can inspect the reason this flow failed.
      raise IOError("Could not stat file: %s" % responses.status)

    # Keep the stat response for later.
    self.stat = responses.First()

    # Update the pathspec from the client.
    self._pathpb.CopyFrom(self.stat.pathspec)

  def FetchWindow(self):
    """Read ahead a number of buffers to fill the window."""
    # Read the first lot of chunks to save on round trips
    number_of_chunks_to_readahead = min(
        self.file_size/self._CHUNK_SIZE + 1 - self.current_chunk_number,
        self._WINDOW_SIZE)

    for _ in range(number_of_chunks_to_readahead):
      bytes_needed_to_read = (
          self.file_size - self._CHUNK_SIZE * self.current_chunk_number)
      self.CallClient("ReadBuffer", pathspec=self._pathpb,
                      offset=self.current_chunk_number * self._CHUNK_SIZE,
                      length=min(self._CHUNK_SIZE, bytes_needed_to_read),
                      next_state="ReadBuffer")
      self.current_chunk_number += 1

  @flow.StateHandler(jobs_pb2.DataBlob)
  def Hash(self, responses):
    """Store the hash of the file."""
    # Did it work?
    if responses.success:
      self.file_hash = aff4.RDFSHAValue(responses.First().data)
      self.Log("File hash is %s", self.file_hash)

  @flow.StateHandler(jobs_pb2.BufferReadMessage, next_state="ReadBuffer")
  def ReadBuffer(self, responses):
    """Read the buffer and write to the file."""
    # Did it work?
    if not responses.success:
      raise IOError("Error running ReadBuffer: %s" % responses.status)

    # Postpone creating the AFF4 object until we get at least one successful
    # buffer back.
    response = responses.First()

    # Initial packet
    if response.offset == 0:
      # Force creation of the new AFF4 object
      self.urn = aff4.AFF4Object.VFSGRRClient.PathspecToURN(
          self._pathpb, self.client_id)

      self.file_size = self.stat.st_size
      self.Load()

      self.fd.Truncate(0)
      self.fd.Set(self.fd.Schema.HASH, self.file_hash)
      self.fd.Set(self.fd.Schema.STAT(self.stat))

      # Now we know how large the file is we can fill the window
      self.FetchWindow()

    if not response:
      raise IOError("Missing response to ReadBuffer: %s" % responses.status)

    self.fd.Seek(response.offset)
    self.fd.Write(response.data)

    # If the file is done, we dont hang around
    if self.fd.Tell() >= self.file_size:
      self.Terminate()

    offset_to_read = self.current_chunk_number * self._CHUNK_SIZE
    bytes_needed_to_read = (
        self.file_size - self._CHUNK_SIZE * self.current_chunk_number)

    # Dont read past the end of file
    if offset_to_read < self.file_size:
      self.CallClient("ReadBuffer", pathspec=self._pathpb,
                      offset=offset_to_read,
                      length=min(bytes_needed_to_read, self._CHUNK_SIZE),
                      next_state="ReadBuffer")

    self.current_chunk_number += 1

  def End(self):
    """Finalize reading the file."""
    self.Notify("ViewObject", self.urn, "File transferred successfully")

    self.Status("Finished reading %s", self._pathpb.path)
    self.Save()

    # Notify any parent flows.
    self.SendReply(self._pathpb)

  def Save(self):
    if self.fd is not None:
      # Update our status
      self.Status("Received %s/%s bytes.", self.fd.size, self.file_size)
      self.fd.Close()
      self.fd = None

  def Load(self):
    """Create the aff4 object."""
    if self.urn is None: return

    self.fd = aff4.FACTORY.Create(self.urn, "VFSFile", mode="rw",
                                  token=self.token)

    # Set the chunksize if needed
    if self.fd.Get(self.fd.Schema.CHUNKSIZE) != self.aff4_chunk_size:
      self.fd.Set(self.fd.Schema.CHUNKSIZE(self.aff4_chunk_size))
