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


"""These flows are designed for high performance transfers."""


import hashlib
import stat
import time
import zlib

import logging
from grr.lib import aff4
from grr.lib import flow
from grr.lib import type_info
from grr.lib import utils
from grr.proto import jobs_pb2


class GetFile(flow.GRRFlow):
  """An efficient file transfer mechanism.

  Returns to parent flow:
    A jobs_pb2.Path.
  """

  category = "/Filesystem/"
  out_protobuf = jobs_pb2.StatResponse
  flow_typeinfo = {"pathtype": type_info.ProtoEnum(jobs_pb2.Path, "PathType"),
                   "pathspec": type_info.Proto(jobs_pb2.Path)}

  # Read in 512kb chunks
  _CHUNK_SIZE = 512 * 1024

  # We have a maximum of this many chunk reads outstanding (about 10mb)
  _WINDOW_SIZE = 200
  current_chunk_number = 0
  max_chunk_number = 2

  def __init__(self, path="/",
               pathtype=jobs_pb2.Path.OS,
               pathspec=None, **kwargs):
    """Constructor.

    This flow uses chunking and hashes to de-duplicate data and send it
    efficiently.

    Args:
      path: The directory path to list.
      pathtype: Identifies requested path type. Enum from Path protobuf.
      pathspec: This flow also accepts all the information in one pathspec.
        which is preferred over the path and pathtype definition
    """
    self.urn = None
    if pathspec:
      self.pathspec = utils.Pathspec(pathspec)
    else:
      self.pathspec = utils.Pathspec(path=path, pathtype=int(pathtype))

    self.fd = None
    flow.GRRFlow.__init__(self, **kwargs)

  @flow.StateHandler(next_state=["Stat", "ReadBuffer", "CheckHashes"])
  def Start(self):
    """Get information about the file from the client."""
    self.CallClient("StatFile", pathspec=self.pathspec.ToProto(),
                    next_state="Stat")

    # Read the first buffer
    self.FetchWindow(self.max_chunk_number)

  @flow.StateHandler()
  def Stat(self, responses):
    """Fix up the pathspec of the file."""
    if responses.success:
      self.stat = responses.First()
      self.pathspec = utils.Pathspec(self.stat.pathspec)
    else:
      raise IOError("Error: %s" % responses.status)

  def FetchWindow(self, number_of_chunks_to_readahead):
    """Read ahead a number of buffers to fill the window."""
    for _ in range(number_of_chunks_to_readahead):

      # Do not read past the end of file
      if self.current_chunk_number > self.max_chunk_number:
        return

      self.CallClient("TransferBuffer", pathspec=self.pathspec.ToProto(),
                      offset=self.current_chunk_number * self._CHUNK_SIZE,
                      length=self._CHUNK_SIZE, next_state="ReadBuffer")
      self.current_chunk_number += 1

  def CreateHashImage(self):
    """Force creation of the new AFF4 object.

    Note that this is pinned on the client id - i.e. the client can not change
    aff4 objects outside its tree.
    """
    self.urn = aff4.AFF4Object.VFSGRRClient.PathspecToURN(
        self.pathspec, self.client_id)
    self.stat.aff4path = utils.SmartUnicode(self.urn)

    # Create a new Hash image for the data. Note that this object is pickled
    # with this flow between states.
    self.fd = aff4.FACTORY.Create(self.urn, "HashImage", token=self.token)

    # The chunksize must be set to be the same as the transfer chunk size.
    self.fd.Set(self.fd.Schema.CHUNKSIZE(self._CHUNK_SIZE))
    self.fd.Set(self.fd.Schema.STAT(self.stat))
    self.fd.Set(self.fd.Schema.CONTENT_LOCK(self.session_id))

    self.max_chunk_number = self.stat.st_size / self._CHUNK_SIZE

    # Fill up the window with requests
    self.FetchWindow(self._WINDOW_SIZE)

  @flow.StateHandler(next_state=["ReadBuffer", "CheckHashes"])
  def ReadBuffer(self, responses):
    """Read the buffer and write to the file."""
    # Did it work?
    if responses.success:
      response = responses.First()
      if not response:
        raise IOError("Missing hash for offset %s missing" % response.offset)

      if self.fd is None:
        self.CreateHashImage()

      # Write the hash to the index. Note that response.data is the hash of the
      # block (32 bytes) and response.length is the length of the block.
      self.fd.AddBlob(response.data, response.length)
      self.Log("Received blob hash %s", response.data.encode("hex"))
      self.Status("Received %s bytes", self.fd.size)

      # Add one more chunk to the window.
      self.FetchWindow(1)

  def End(self):
    """Finalize reading the file."""
    if self.urn is None:
      self.Notify("ViewObject", self.client_id, "File failed to be transferred")
    else:
      self.Notify("ViewObject", self.urn, "File transferred successfully")

      self.Log("Finished reading %s", self.urn)
      self.Log("Flow Completed in %s seconds",
               time.time() - self.flow_pb.create_time/1e6)

      response = self.fd.Get(self.fd.Schema.STAT)
      self.fd.Close(sync=True)
      # Notify any parent flows the file is ready to be used now.
      self.SendReply(response)


class FastGetFile(GetFile):
  """An experimental GetFile which uses deduplication to save bandwidth."""

  # We can be much more aggressive here.
  _WINDOW_SIZE = 400

  flow_typeinfo = {"pathtype": type_info.ProtoEnum(jobs_pb2.Path, "PathType"),
                   "pathspec": type_info.Proto(jobs_pb2.Path)}

  def __init__(self, path="/", pathtype=jobs_pb2.Path.OS,
               pathspec=None, **kwargs):
    self.hash_queue = []
    super(FastGetFile, self).__init__(path=path, pathtype=pathtype,
                                      pathspec=pathspec, **kwargs)

  def FetchWindow(self, number_of_chunks_to_readahead):
    """Read ahead a number of buffers to fill the window."""
    for _ in range(number_of_chunks_to_readahead):

      # Do not read past the end of file
      if self.current_chunk_number > self.max_chunk_number:
        return

      self.CallClient("HashBuffer", pathspec=self.pathspec.ToProto(),
                      offset=self.current_chunk_number * self._CHUNK_SIZE,
                      length=self._CHUNK_SIZE, next_state="CheckHashes")
      self.current_chunk_number += 1

  def CreateHashImage(self):
    super(FastGetFile, self).CreateHashImage()
    self.hash_queue = []

  @flow.StateHandler(next_state=["ReadBuffer", "CheckHashes"])
  def CheckHashes(self, responses):
    """Check if the hashes are already in the data store."""
    for response in responses:
      blob_urn = aff4.ROOT_URN.Add("blobs").Add(response.data.encode("hex"))
      self.hash_queue.append((blob_urn, response))

    if len(self.hash_queue) > self._WINDOW_SIZE / 2:
      self.CheckQueuedHashes()

  def CheckQueuedHashes(self):
    """Check which of the hashes in the queue we already have."""
    urns = [blob_urn for blob_urn, _ in self.hash_queue]
    fds = aff4.FACTORY.Stat(urns, token=self.token)

    # These blob urns we have already.
    matched_urns = set([x["urn"] for x in fds])

    for blob_urn, response in self.hash_queue:
      if blob_urn in matched_urns:
        if self.fd is None:
          self.CreateHashImage()

        self.fd.AddBlob(response.data, response.length)
        self.Log("Received blob hash %s", response.data.encode("hex"))
        self.Status("Received %s bytes", self.fd.size)
      else:
        self.CallClient("TransferBuffer", pathspec=self.pathspec.ToProto(),
                        offset=response.offset, length=self._CHUNK_SIZE,
                        next_state="ReadBuffer")

      # Keep the window open in any case by hashing the next buffer.  Do not
      # read past the end of file though.
      if self.current_chunk_number < self.max_chunk_number:
        self.CallClient("HashBuffer", pathspec=self.pathspec.ToProto(),
                        offset=self.current_chunk_number * self._CHUNK_SIZE,
                        length=self._CHUNK_SIZE, next_state="CheckHashes")

        self.current_chunk_number += 1

    # Clear the queue.
    self.hash_queue = []

  @flow.StateHandler(next_state=["CheckHashes", "ReadBuffer"])
  def End(self):
    if self.hash_queue:
      self.CheckQueuedHashes()
    else:
      super(FastGetFile, self).End()


class GetMBR(flow.GRRFlow):
  """A flow to retrieve the MBR.

  Returns to parent flow:
    The retrieved MBR.
  """

  category = "/Filesystem/"
  out_protobuf = jobs_pb2.BufferReadMessage

  def __init__(self, length=4096, **kw):
    self.length = length
    super(GetMBR, self).__init__(**kw)

  @flow.StateHandler(next_state=["StoreMBR"])
  def Start(self):
    """Schedules the ReadBuffer client action."""
    pathspec = jobs_pb2.Path(path="\\\\.\\PhysicalDrive0\\",
                             pathtype=jobs_pb2.Path.OS,
                             path_options=jobs_pb2.Path.CASE_LITERAL)

    self.CallClient("ReadBuffer", pathspec=pathspec, offset=0,
                    length=self.length, next_state="StoreMBR")

  @flow.StateHandler()
  def StoreMBR(self, responses):
    """This method stores the MBR."""

    if not responses.success:
      msg = "Could not retrieve MBR: %s" % responses.status
      self.Log(msg)
      raise flow.FlowError(msg)

    response = responses.First()

    mbr = aff4.FACTORY.Create("aff4:/%s/mbr" % self.client_id, "VFSMemoryFile",
                              mode="rw", token=self.token)
    mbr.write(response.data)
    mbr.Close()
    self.Log("Successfully stored the MBR (%d bytes)." % len(response.data))
    self.SendReply(response)


class TransferStore(flow.WellKnownFlow):
  """Store a buffer into a determined location."""
  well_known_session_id = "W:TransferStore"

  def ProcessMessage(self, message):
    """Write the blob into the AFF4 blob storage area."""
    # Check that the message is authenticated
    if message.auth_state != jobs_pb2.GrrMessage.AUTHENTICATED:
      logging.error("TransferStore request from %s is not authenticated.",
                    message.source)
      return

    read_buffer = jobs_pb2.DataBlob()
    read_buffer.ParseFromString(message.args)

    # Only store non empty buffers
    if read_buffer.data:
      data = read_buffer.data

      if read_buffer.compression == jobs_pb2.DataBlob.ZCOMPRESSION:
        cdata = data
        data = zlib.decompress(cdata)
      elif read_buffer.compression == jobs_pb2.DataBlob.UNCOMPRESSED:
        cdata = zlib.compress(data)
      else:
        raise RuntimeError("Unsupported compression")

      # The hash is done on the uncompressed data
      digest = hashlib.sha256(data).digest()
      urn = aff4.ROOT_URN.Add("blobs").Add(digest.encode("hex"))

      # Write the blob to the data store. We cheat here and just store the
      # compressed data to avoid recompressing it.
      fd = aff4.FACTORY.Create(urn, "AFF4MemoryStream", mode="w",
                               token=self.token)
      fd.Set(fd.Schema.CONTENT(cdata))
      fd.Set(fd.Schema.SIZE(len(data)))
      fd.Close(sync=True)

      logging.info("Got blob %s (length %s)", digest.encode("hex"),
                   len(cdata))


class FileDownloader(flow.GRRFlow):
  """Handle the automated collection of multiple files.

  This class contains the logic to automatically collect and store a set
  of files and directories.

  Classes that want to implement this functionality for a specific
  set of files should inherit from it and override __init__ and set
  self.findspecs and/or self.pathspecs to something appropriate.

  Alternatively they can override GetFindSpecs for simple cases.

  Returns to parent flow:
    A StatResponse protobuf for each downloaded file.
  """

  out_protobuf = jobs_pb2.StatResponse
  flow_typeinfo = {"findspecs": type_info.ListProto(jobs_pb2.Find),
                   "pathspecs": type_info.Proto(jobs_pb2.Path)}

  def __init__(self, findspecs=None, pathspecs=None, **kwargs):
    """Determine the usable findspecs.

    Args:
      findspecs: A list of jobs_pb2.Find protos. If None, self.GetFindSpecs
          will be called to get the specs.
      pathspecs: A list of jobs_pb2.Path protos. If None, self.GetPathSpecs
          will be called to get the specs.
    """
    flow.GRRFlow.__init__(self, **kwargs)

    self.findspecs = findspecs
    self.pathspecs = pathspecs

  @flow.StateHandler(next_state=["DownloadFiles", "HandleDownloadedFiles"])
  def Start(self):
    """Queue flows for all valid find specs."""
    if self.findspecs is None:
      # Call GetFindSpecs, should be overridden by inheriting classes.
      self.findspecs = self.GetFindSpecs()

    if self.pathspecs is None:
      # Call GetPathSpecs, should be overridden by inheriting classes.
      self.pathspecs = self.GetPathSpecs()

    if not self.findspecs and not self.pathspecs:
      self.Error("No usable specs found.")

    for findspec in self.findspecs:
      self.CallFlow("FindFiles", next_state="DownloadFiles",
                    findspec=findspec, output=None)

    for pathspec in self.pathspecs:
      self.CallFlow("GetFile", next_state="HandleDownloadedFiles",
                    pathspec=pathspec)

  @flow.StateHandler(jobs_pb2.StatResponse, next_state="HandleDownloadedFiles")
  def DownloadFiles(self, responses):
    """For each file found in the resulting collection, download it."""
    if responses.success:
      count = 0
      for response in responses:
        # Only download regular files.
        if stat.S_ISREG(response.st_mode):
          count += 1
          self.CallFlow("GetFile",
                        next_state="HandleDownloadedFiles",
                        pathspec=response.pathspec)

      self.Log("Scheduling download of %d files", count)

    else:
      self.Log("Find failed %s", responses.status)

  @flow.StateHandler(jobs_pb2.StatResponse)
  def HandleDownloadedFiles(self, responses):
    """Handle the Stats that come back from the GetFile calls."""
    if responses.success:
      # GetFile returns a list of StatResponse protos.
      for response_stat in responses:
        self.Log("Downloaded %s", response_stat.pathspec)
        self.SendReply(response_stat)
    else:
      self.Log("Download of file %s failed %s",
               responses.GetRequestArgPb().pathspec, responses.status)

  def GetFindSpecs(self):
    """Returns iterable of jobs_pb2.Find objects. Should be overridden."""
    return []

  def GetPathSpecs(self):
    """Returns iterable of jobs_pb2.Path objects. Should be overridden."""
    return []


class FileCollector(flow.GRRFlow):
  """Flow to create a collection from downloaded files.

  This flow calls the FileDownloader and creates a collection for the results.
  Returns to the parent flow:
    A StatResponse protobuf describing the output collection.
  """

  out_protobuf = jobs_pb2.StatResponse
  flow_typeinfo = {"findspecs": type_info.ListProto(jobs_pb2.Find)}

  def __init__(self, findspecs=None,
               output="analysis/collect/{u}-{t}", **kwargs):
    """Download all files matching the findspecs and generate a collection.

    Args:
      findspecs: A list of jobs_pb2.Find protos. If None, self.GetFindSpecs
          will be called to get the specs.
      output: If set, a URN to an AFF4Collection to add each result to.
          This will create the collection if it does not exist.
    """
    flow.GRRFlow.__init__(self, **kwargs)

    # Expand special escapes.
    output = output.format(t=time.time(), u=self.user)
    self.output = aff4.ROOT_URN.Add(self.client_id).Add(output)
    self.collection_list = None

    self.fd = aff4.FACTORY.Create(self.output, "AFF4Collection", mode="rw",
                                  token=self.token)
    self.Log("Created output collection %s", self.output)

    self.fd.Set(self.fd.Schema.DESCRIPTION("CollectFiles {0}".format(
        self.__class__.__name__)))

    # Append to the collection if needed.
    self.collection_list = self.fd.Get(self.fd.Schema.COLLECTION)
    self.findspecs = findspecs

  @flow.StateHandler(next_state="WriteCollection")
  def Start(self):
    if self.findspecs:
      # Just call the FileDownloader with these findspecs
      self.CallFlow("FileDownloader", findspecs=self.findspecs,
                    next_state="WriteCollection")
    else:
      self.Log("No findspecs to run.")

  @flow.StateHandler()
  def WriteCollection(self, responses):
    """Adds the results to the collection."""
    for response_stat in responses:
      self.collection_list.Append(response_stat)

    self.fd.Set(self.fd.Schema.COLLECTION, self.collection_list)
    self.fd.Close(True)

    # Tell our caller about the new collection.
    self.SendReply(jobs_pb2.StatResponse(
        aff4path=utils.SmartUnicode(self.fd.urn)))

  @flow.StateHandler()
  def End(self):
    # Notify our creator.
    num_files = len(self.collection_list)

    self.Notify("ViewObject", self.output,
                "Completed download of {0:d} files.".format(num_files))
