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
from grr.lib import utils
from grr.proto import jobs_pb2


class GetFile(flow.GRRFlow):
  """An efficient file transfer mechanism.

  Returns to parent flow:
    A jobs_pb2.Path.
  """

  category = "/Filesystem/"
  out_protobuf = jobs_pb2.StatResponse

  # Read in 512kb chunks
  _CHUNK_SIZE = 512 * 1024

  # We have a maximum of this many chunk reads outstanding (about 10mb)
  _WINDOW_SIZE = 200
  current_chunk_number = 0
  max_chunk_number = 2

  def __init__(self, path="/",
               pathtype=utils.ProtoEnum(jobs_pb2.Path, "PathType", "OS"),
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
    flow.GRRFlow.__init__(self, **kwargs)

  @flow.StateHandler(next_state=["Stat", "ReadBuffer"])
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

  @flow.StateHandler(next_state="ReadBuffer")
  def ReadBuffer(self, responses):
    """Read the buffer and write to the file."""
    # Did it work?
    if responses.success:
      response = responses.First()
      if not response:
        raise IOError("Missing hash for offset %s missing" % response.offset)

      if response.offset == 0:
        # Force creation of the new AFF4 object (Note that this is pinned on the
        # client id - i.e. the client can not change aff4 objects outside its
        # tree).
        self.urn = aff4.AFF4Object.VFSGRRClient.PathspecToURN(
            self.pathspec, self.client_id)
        self.stat.aff4path = utils.SmartUnicode(self.urn)

        # Create a new Hash image for the data. Note that this object is pickled
        # with this flow between states.
        self.fd = aff4.FACTORY.Create(self.urn, "HashImage", token=self.token)

        # The chunksize must be set to be the same as the transfer chunk size.
        self.fd.Set(self.fd.Schema.CHUNKSIZE(self._CHUNK_SIZE))
        self.fd.Set(self.fd.Schema.STAT(self.stat))

        self.max_chunk_number = self.stat.st_size / self._CHUNK_SIZE

        # Fill up the window with requests
        self.FetchWindow(self._WINDOW_SIZE)

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

      # Notify any parent flows the file is ready to be used now.
      self.SendReply(self.fd.Get(self.fd.Schema.STAT))
      self.fd.Close(sync=True)


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
      fd.Close(sync=False)

      logging.info("Got blob %s (length %s)", digest.encode("hex"),
                   len(cdata))


class FileDownloader(flow.GRRFlow):
  """Handle the automated collection of multiple files.

  This class contains the logic to automatically collect and store a set
  of files and directories.

  Classes that want to implement this functionality for a specific
  set of files should inherit from it and override __init__ and set
  self.findspecs to something appropriate.

  Alternatively they can override GetFindSpecs for simple cases.

  Returns to parent flow:
    A StatResponse protobuf for each downloaded file.
  """

  out_protobuf = jobs_pb2.StatResponse

  def __init__(self, findspecs=None, **kwargs):
    """Determine the usable findspecs.

    Args:
      findspecs: A list of jobs_pb2.Find protos. If None, self.GetFindSpecs
          will be called to get the specs.
    """
    flow.GRRFlow.__init__(self, **kwargs)

    self.findspecs = findspecs

  @flow.StateHandler(next_state=["DownloadFiles"])
  def Start(self):
    """Queue flows for all valid find specs."""
    if self.findspecs is None:
      # Call GetFindSpecs, should be overridden by inheriting classes.
      self.findspecs = list(self.GetFindSpecs())

    if not self.findspecs:
      self.Log("No usable specs found.")
      self.Terminate()

    for findspec in self.findspecs:
      self.CallFlow("FindFiles", next_state="DownloadFiles",
                    findspec=findspec, output=None)

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


class FileCollector(flow.GRRFlow):
  """Flow to create a collection from downloaded files.

  This flow calls the FileDownloader and creates a collection for the results.
  Returns to the parent flow:
    A StatResponse protobuf describing the output collection.
  """

  out_protobuf = jobs_pb2.StatResponse

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
