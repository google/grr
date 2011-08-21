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

import os

from grr.lib import aff4
from grr.lib import flow
from grr.lib import utils
from grr.proto import jobs_pb2


class ListDirectory(flow.GRRFlow):
  """List files in a directory."""

  category = "/Filesystem/"

  def __init__(self, path="/", pathtype=0, device=None, **kwargs):
    """Constructor.

    Args:
      path: The directory path to list.
      pathtype: Identifies requested path type (Enum from Path protobuf).
      device: Optional raw device that should be accessed.

    """
    self.path = utils.NormalizePath(path)
    self._pathpb = jobs_pb2.Path(path=path, pathtype=pathtype)
    if device:
      self._pathpb.device = device
    flow.GRRFlow.__init__(self, **kwargs)

  @flow.StateHandler(next_state="List")
  def Start(self, unused_response):
    """Issue a request to list the directory."""
    # We use data to pass the path to the callback:
    self.CallClient("ListDirectory", pathspec=self._pathpb, next_state="List")

  @flow.StateHandler(jobs_pb2.StatResponse)
  def List(self, responses):
    """Collect the directory listing and store in the datastore."""
    if not responses.success:
      raise flow.FlowError(str(responses.status))

    r = responses.First()
    path = utils.PathspecToAff4(r.pathspec)
    # We need to guess the correct casing. Newer clients return the full path.
    if "/" in path:
      path = os.path.dirname(path)
    else:
      path = self.path

    # The full path of the object is the combination of the client_id and the
    # path.
    fd = aff4.FACTORY.Create(utils.JoinPath(self.client_id, path),
                             "VFSDirectory")

    self.Log("Listed %s", path)
    fd.DeleteAttribute(fd.Schema.DIRECTORY)

    # New directory Inode
    directory_inode = fd.Schema.DIRECTORY()

    for stat in responses:
      actpath = utils.PathspecToAff4(stat.pathspec)
      if "/" not in stat.pathspec.path or actpath.startswith(path):
        # Only store the basename for efficiency.
        stat.path = os.path.basename(actpath)
        directory_inode.AddDirectoryEntry(stat)
        self.SendReply(stat)  # Send Stats to parent flows.

    # Store it now
    fd.AddAttribute(fd.Schema.DIRECTORY, directory_inode)

    # Remove the flow lock on the directory
    fd.DeleteAttribute(fd.Schema.FLOW)
    fd.Close()


class IteratedListDirectory(ListDirectory):
  """A Flow to retrieve a directory listing using an iterator.

  This flow is an example for how to use the iterated client actions. Normally
  you do not need to call this flow - a ListDirectory flow is enough.
  """

  @flow.StateHandler(next_state="List")
  def Start(self, unused_response):
    """Issue a request to list the directory."""
    # We use data to pass the path to the callback:
    self.request = jobs_pb2.ListDirRequest(pathspec=self._pathpb)

    # For this example we will use a really small number to force many round
    # trips with the client. This is a performance killer.
    self.request.iterator.number = 2
    self.responses = []

    self.CallClient("IteratedListDirectory", self.request,
                    next_state="List", request_data=dict(path=self.path))

  @flow.StateHandler(jobs_pb2.StatResponse, next_state="List")
  def List(self, responses):
    """Collect the directory listing and store in the data store."""
    if len(responses) > 0:
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
    fd = aff4.FACTORY.Create(utils.JoinPath(self.client_id, self.path),
                             "VFSDirectory")
    fd.DeleteAttribute(fd.Schema.DIRECTORY)

    # New directory Inode
    directory_inode = fd.Schema.DIRECTORY()

    for stat in self.responses:
      directory_inode.AddDirectoryEntry(stat)
      self.SendReply(stat)  # Send Stats to parent flows.

    # Store it now
    fd.AddAttribute(fd.Schema.DIRECTORY, directory_inode)
    fd.Close()


class GetFile(flow.GRRFlow):
  """Simple file retrival."""

  category = "/Filesystem/"

  # Read in 32kb chunks
  _CHUNK_SIZE = 1024 * 32

  # We have a maximum of this many chunk reads outstanding (about 10mb)
  _WINDOW_SIZE = 330

  def __init__(self, client_id=None, path="/", pathtype=0,
               device=None, aff4_chunk_size=2**20, **kwargs):
    """Constructor.

    Args:
      client_id: The client id.
      path: The directory path to list.
      pathtype: Identifies requested path type. Enum from Path protobuf.
      device: Optional raw device that should be accessed.
      aff4_chunk_size: Specifies how much data is sent back from the
                       client in each chunk.

      kwargs: passthrough.
    """
    self._path = path
    self.urn = None
    self.current_chunk_number = 0
    self.aff4_chunk_size = aff4_chunk_size
    self.fd = None
    self._pathpb = jobs_pb2.Path(path=path, pathtype=pathtype)
    if device:
      self._pathpb = device
    flow.GRRFlow.__init__(self, client_id=client_id, **kwargs)

  @flow.StateHandler(next_state=["Hash", "Stat"])
  def Start(self):
    """Get information about the file from the client."""

    # We first obtain information about how large the file is
    self.CallClient("StatFile", pathspec=self._pathpb, next_state="Stat")

    # This flow relies on the fact that responses are always returned
    # in order:
    self.CallClient("HashFile", pathspec=self._pathpb, next_state="Hash")

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
      self.Log("Error Stat()ing file %s: %s", self._path, responses.status)
      raise IOError("Could not stat %s" % self._path)

    stat = responses.First()

    # Newer clients normalize the path correctly.
    if "/" in stat.pathspec.path:
      self._path = utils.PathspecToAff4(stat.pathspec)
      self._pathpb.CopyFrom(stat.pathspec)

    self.SendReply(self._pathpb)

    # Force creation of the new AFF4 object
    self.urn = aff4.ROOT_URN.Add(self.client_id).Add(self._path)
    self.Load()

    self.file_size = stat.st_size
    self.fd.Set(self.fd.Schema.STAT, aff4.FACTORY.RDFValue("StatEntry")(stat))
    self.fd.Set(self.fd.Schema.SIZE, aff4.RDFInteger(0))

    # Read the first lot of chunks to save on round trips
    number_of_chunks_to_readahead = min(
        self.file_size/self._CHUNK_SIZE + 1, self._WINDOW_SIZE)

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
      file_hash = aff4.RDFSHAValue(responses.First().data)
      self.fd.Set(self.fd.Schema.HASH, file_hash)
      self.Log("File hash is %s", file_hash)

  @flow.StateHandler(jobs_pb2.BufferReadMessage, next_state="ReadBuffer")
  def ReadBuffer(self, responses):
    """Read the buffer and write to the file."""
    # Did it work?
    if not responses.success:
      self.Log("Error running ReadBuffer: %s", responses.status)
      return

    response = responses.First()
    if not response:
      self.Log("Missing response to ReadBuffer: %s", responses.status)
      return

    self.Log("Received %s:%s", response.offset, response.length)

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
    self.Log("Finished reading %s", self._path)
    self.Save()

  def Save(self):
    if self.fd is not None:
      self.fd.Close()
      self.fd = None

  def Load(self):
    """Create the aff4 object."""
    if self.urn is None: return

    try:
      self.fd = aff4.FACTORY.Open(self.urn, "w").Upgrade("VFSFile")
    except IOError:
      self.fd = aff4.FACTORY.Create(self.urn, "VFSDirectory").Upgrade("VFSFile")

    # Set the chunksize if needed
    if self.fd.Get(self.fd.Schema.CHUNKSIZE) != self.aff4_chunk_size:
      self.fd.Set(self.fd.Schema.CHUNKSIZE,
                  aff4.RDFInteger(self.aff4_chunk_size))
