#!/usr/bin/env python
# Copyright 2011 Google Inc. All Rights Reserved.

"""These flows are designed for high performance transfers."""


import hashlib
import stat
import time
import zlib

import logging
from grr.lib import aff4
from grr.lib import flow
from grr.lib import rdfvalue
from grr.proto import flows_pb2


class GetFileArgs(rdfvalue.RDFProtoStruct):
  protobuf = flows_pb2.GetFileArgs


class GetFile(flow.GRRFlow):
  """An efficient file transfer mechanism.

  Returns to parent flow:
    An PathSpec.
  """

  category = "/Filesystem/"

  args_type = GetFileArgs

  class SchemaCls(flow.GRRFlow.SchemaCls):
    PROGRESS_GRAPH = aff4.Attribute(
        "aff4:progress", rdfvalue.ProgressGraph,
        "Show a button to generate a progress graph for this flow.",
        default="")

  # We have a maximum of this many chunk reads outstanding (about 10mb)
  WINDOW_SIZE = 200
  CHUNK_SIZE = 512 * 1024

  @flow.StateHandler(next_state=["Stat"])
  def Start(self):
    """Get information about the file from the client."""
    self.state.Register("max_chunk_number",
                        max(2, self.state.args.read_length/self.CHUNK_SIZE))

    self.state.Register("current_chunk_number", 0)
    self.state.Register("file_size", 0)
    self.state.Register("fd", None)
    self.state.Register("stat", None)

    self.CallClient("StatFile", rdfvalue.ListDirRequest(
        pathspec=self.state.args.pathspec),
                    next_state="Stat")

  @flow.StateHandler(next_state=["ReadBuffer", "CheckHashes"])
  def Stat(self, responses):
    """Fix up the pathspec of the file."""
    response = responses.First()
    if responses.success and response:
      self.state.stat = response
      self.state.args.pathspec = self.state.stat.pathspec
    else:
      raise IOError("Error: %s" % responses.status)

    # Adjust the size from st_size if read length is not specified.
    if self.state.args.read_length == 0:
      self.state.file_size = self.state.stat.st_size
    else:
      self.state.file_size = self.state.args.read_length

    self.state.max_chunk_number = (self.state.file_size /
                                   self.CHUNK_SIZE) + 1

    self.CreateBlobImage()
    self.FetchWindow(min(
        self.WINDOW_SIZE,
        self.state.max_chunk_number - self.state.current_chunk_number))

  def FetchWindow(self, number_of_chunks_to_readahead):
    """Read ahead a number of buffers to fill the window."""
    for _ in range(number_of_chunks_to_readahead):

      # Do not read past the end of file
      if self.state.current_chunk_number > self.state.max_chunk_number:
        return

      request = rdfvalue.BufferReference(
          pathspec=self.state.args.pathspec,
          offset=self.state.current_chunk_number * self.CHUNK_SIZE,
          length=self.CHUNK_SIZE)
      self.CallClient("TransferBuffer", request, next_state="ReadBuffer")
      self.state.current_chunk_number += 1

  def CreateBlobImage(self):
    """Force creation of the new AFF4 object.

    Note that this is pinned on the client id - i.e. the client can not change
    aff4 objects outside its tree.
    """
    urn = aff4.AFF4Object.VFSGRRClient.PathspecToURN(
        self.state.args.pathspec, self.client_id)

    self.state.stat.aff4path = urn

    # Create a new Hash image for the data. Note that this object is pickled
    # with this flow between states.
    self.state.fd = aff4.FACTORY.Create(urn, "BlobImage", token=self.token)

    # The chunksize must be set to be the same as the transfer chunk size.
    self.state.fd.SetChunksize(self.CHUNK_SIZE)
    self.state.fd.Set(self.state.fd.Schema.STAT(self.state.stat))

  @flow.StateHandler(next_state=["ReadBuffer", "CheckHashes"])
  def ReadBuffer(self, responses):
    """Read the buffer and write to the file."""
    # Did it work?
    if responses.success:
      response = responses.First()
      if not response:
        raise IOError("Missing hash for offset %s missing" % response.offset)

      if response.offset <= self.state.max_chunk_number * self.CHUNK_SIZE:
        # Write the hash to the index. Note that response.data is the hash of
        # the block (32 bytes) and response.length is the length of the block.
        self.state.fd.AddBlob(response.data, response.length)
        self.Log("Received blob hash %s", response.data.encode("hex"))
        self.Status("Received %s bytes", self.state.fd.size)

        # Add one more chunk to the window.
        self.FetchWindow(1)
    elif (responses.status.status ==
          responses.status.ReturnedStatus.NETWORK_LIMIT_EXCEEDED):
      raise flow.FlowError(responses.status)

  @flow.StateHandler()
  def End(self):
    """Finalize reading the file."""
    fd = self.state.fd
    if fd is None:
      self.Notify("ViewObject", self.client_id, "File failed to be transferred")
    else:
      self.Notify("ViewObject", fd.urn, "File transferred successfully")

      self.Log("Finished reading %s", fd.urn)
      self.Log("Flow Completed in %s seconds",
               time.time() - self.state.context.create_time/1e6)

      stat_response = self.state.fd.Get(self.state.fd.Schema.STAT)

      fd.size = min(fd.size, self.state.file_size)
      fd.Close(sync=True)

      # Notify any parent flows the file is ready to be used now.
      self.SendReply(stat_response)


class HashTracker(object):
  """A class to track a blob hash."""

  def __init__(self, hash_response):
    self.hash_response = hash_response
    self.blob_urn = rdfvalue.RDFURN("aff4:/blobs").Add(
        hash_response.data.encode("hex"))


class FastGetFile(GetFile):
  """An experimental GetFile which uses deduplication to save bandwidth."""

  # We can be much more aggressive here.
  WINDOW_SIZE = 400

  @flow.StateHandler()
  def Start(self, responses):
    super(FastGetFile, self).Start(responses)
    self.state.Register("queue", [])

  def FetchWindow(self, number_of_chunks_to_readahead):
    """Read ahead a number of buffers to fill the window."""
    number_of_chunks_to_readahead = min(
        number_of_chunks_to_readahead,
        self.state.max_chunk_number - self.state.current_chunk_number)

    for _ in range(number_of_chunks_to_readahead):
      offset = self.state.current_chunk_number * self.CHUNK_SIZE
      request = rdfvalue.BufferReference(pathspec=self.state.args.pathspec,
                                         offset=offset,
                                         length=self.CHUNK_SIZE)
      self.CallClient("HashBuffer", request, next_state="CheckHashes")

      self.state.current_chunk_number += 1

  @flow.StateHandler(next_state=["CheckHashes", "WriteHash"])
  def CheckHashes(self, responses):
    """Check if the hashes are already in the data store.

    In order to minimize the round trips we only actually check the hashes
    periodically.

    Args:
      responses: client responses.
    """
    if (responses.status.status ==
        responses.status.ReturnedStatus.NETWORK_LIMIT_EXCEEDED):
      raise flow.FlowError(responses.status)

    for response in responses:
      self.state.queue.append(HashTracker(response))

    if len(self.state.queue) > self.WINDOW_SIZE:
      check_hashes = self.state.queue[:self.WINDOW_SIZE]
      self.state.queue = self.state.queue[self.WINDOW_SIZE:]
      self.CheckQueuedHashes(check_hashes)

  def CheckQueuedHashes(self, hash_list):
    """Check which of the hashes in the queue we already have."""
    urns = [x.blob_urn for x in hash_list]
    fds = aff4.FACTORY.Stat(urns, token=self.token)

    # These blob urns we have already.
    matched_urns = set([x["urn"] for x in fds])

    # Fetch all the blob urns we do not have and that are not currently already
    # in flight.
    for hash_tracker in hash_list:
      request = hash_tracker.hash_response
      request.pathspec = self.state.args.pathspec

      if hash_tracker.blob_urn in matched_urns:
        self.CallState([request], next_state="WriteHash")
      else:
        self.CallClient("TransferBuffer", request, next_state="WriteHash")

    self.FetchWindow(self.WINDOW_SIZE)

  @flow.StateHandler()
  def WriteHash(self, responses):
    if not responses.success:
      # Silently ignore failures in block-fetches
      # Might want to clean up the 'broken' fingerprint file here.
      return

    response = responses.First()

    self.state.fd.AddBlob(response.data, response.length)
    self.Status("Received %s bytes", self.state.fd.size)

  @flow.StateHandler(next_state=["CheckHashes", "WriteHash"])
  def End(self, _):
    """Flush outstanding hash blobs and retrieve more if needed."""
    if self.state.queue:
      self.CheckQueuedHashes(self.state.queue)
      self.state.queue = []

    else:
      stat_response = self.state.fd.Get(self.state.fd.Schema.STAT)
      self.state.fd.Close(sync=True)

      # Notify any parent flows the file is ready to be used now.
      self.SendReply(stat_response)


class GetMBRArgs(rdfvalue.RDFProtoStruct):
  protobuf = flows_pb2.GetMBRArgs


class GetMBR(flow.GRRFlow):
  """A flow to retrieve the MBR.

  Returns to parent flow:
    The retrieved MBR.
  """

  category = "/Filesystem/"
  args_type = GetMBRArgs

  @flow.StateHandler(next_state=["StoreMBR"])
  def Start(self):
    """Schedules the ReadBuffer client action."""
    pathspec = rdfvalue.PathSpec(
        path="\\\\.\\PhysicalDrive0\\",
        pathtype=rdfvalue.PathSpec.PathType.OS,
        path_options=rdfvalue.PathSpec.Options.CASE_LITERAL)

    request = rdfvalue.BufferReference(pathspec=pathspec, offset=0,
                                       length=self.state.args.length)
    self.CallClient("ReadBuffer", request, next_state="StoreMBR")

  @flow.StateHandler()
  def StoreMBR(self, responses):
    """This method stores the MBR."""

    if not responses.success:
      msg = "Could not retrieve MBR: %s" % responses.status
      self.Log(msg)
      raise flow.FlowError(msg)

    response = responses.First()

    mbr = aff4.FACTORY.Create(self.client_id.Add("mbr"), "VFSMemoryFile",
                              mode="rw", token=self.token)
    mbr.write(response.data)
    mbr.Close()
    self.Log("Successfully stored the MBR (%d bytes)." % len(response.data))
    self.SendReply(rdfvalue.RDFBytes(response.data))


class TransferStore(flow.WellKnownFlow):
  """Store a buffer into a determined location."""
  well_known_session_id = rdfvalue.SessionID("aff4:/flows/W:TransferStore")

  def ProcessMessage(self, message):
    """Write the blob into the AFF4 blob storage area."""
    # Check that the message is authenticated
    if (message.auth_state !=
        rdfvalue.GrrMessage.AuthorizationState.AUTHENTICATED):
      logging.error("TransferStore request from %s is not authenticated.",
                    message.source)
      return

    read_buffer = rdfvalue.DataBlob(message.args)

    # Only store non empty buffers
    if read_buffer.data:
      data = read_buffer.data

      if (read_buffer.compression ==
          rdfvalue.DataBlob.CompressionType.ZCOMPRESSION):
        cdata = data
        data = zlib.decompress(cdata)
      elif (read_buffer.compression ==
            rdfvalue.DataBlob.CompressionType.UNCOMPRESSED):
        cdata = zlib.compress(data)
      else:
        raise RuntimeError("Unsupported compression")

      # The hash is done on the uncompressed data
      digest = hashlib.sha256(data).digest()
      urn = rdfvalue.RDFURN("aff4:/blobs").Add(digest.encode("hex"))

      # Write the blob to the data store. We cheat here and just store the
      # compressed data to avoid recompressing it.
      fd = aff4.FACTORY.Create(urn, "AFF4MemoryStream", mode="w",
                               token=self.token)
      fd.Set(fd.Schema.CONTENT(cdata))
      fd.Set(fd.Schema.SIZE(len(data)))
      super(aff4.AFF4MemoryStream, fd).Close(sync=True)

      logging.info("Got blob %s (length %s)", digest.encode("hex"),
                   len(cdata))


class FileDownloaderArgs(rdfvalue.RDFProtoStruct):
  protobuf = flows_pb2.FileDownloaderArgs


class FileDownloader(flow.GRRFlow):
  """Handle the automated collection of multiple files.

  This class contains the logic to automatically collect and store a set
  of files and directories.

  Returns to parent flow:
    A StatResponse protobuf for each downloaded file.
  """
  args_type = FileDownloaderArgs

  @flow.StateHandler(next_state=["DownloadFiles", "HandleDownloadedFiles"])
  def Start(self):
    """Queue flows for all valid find specs."""
    if not self.state.args.HasField("findspecs"):
      # Call GetFindSpecs, should be overridden by inheriting classes.
      self.state.args.findspecs = self.GetFindSpecs()

    if not self.state.args.findspecs and not self.state.pathspecs:
      self.Error("No usable specs found.")

    for findspec in self.state.args.findspecs:
      self.CallFlow("FindFiles", next_state="DownloadFiles",
                    findspec=findspec, output=None)

    for pathspec in self.state.args.pathspecs:
      self.CallFlow("GetFile", next_state="HandleDownloadedFiles",
                    pathspec=pathspec)

  @flow.StateHandler(next_state="HandleDownloadedFiles")
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
                        pathspec=response.pathspec,
                        request_data=dict(pathspec=response.pathspec))

      self.Log("Scheduling download of %d files", count)

    else:
      self.Log("Find failed %s", responses.status)

  @flow.StateHandler()
  def HandleDownloadedFiles(self, responses):
    """Handle the Stats that come back from the GetFile calls."""
    if responses.success:
      # GetFile returns a list of StatEntry.
      for response in responses:
        self.Log("Downloaded %s", response)
        self.SendReply(response)
    else:
      self.Log("Download of file %s failed %s",
               responses.request_data["pathspec"], responses.status)

  def GetFindSpecs(self):
    """Returns iterable of rdfvalue.FindSpec objects. Should be overridden."""
    return []

  def GetPathSpecs(self):
    """Returns iterable of rdfvalue.PathSpec objects. Should be overridden."""
    return []


class FileCollectorArgs(rdfvalue.RDFProtoStruct):
  protobuf = flows_pb2.FileCollectorArgs


class FileCollector(flow.GRRFlow):
  """Flow to create a collection from downloaded files.

  This flow calls the FileDownloader and creates a collection for the results.
  Returns to the parent flow:
    A StatResponse protobuf describing the output collection.
  """
  args_type = FileCollectorArgs

  @flow.StateHandler(next_state="WriteCollection")
  def Start(self):
    """Start FileCollector flow."""
    output = self.args.output.format(t=time.time(), u=self.state.context.user)
    self.state.Register("output", self.client_id.Add(output))
    self.state.Register("fd", aff4.FACTORY.Create(self.state.output,
                                                  "AFF4Collection",
                                                  mode="rw", token=self.token))

    self.Log("Created output collection %s", self.state.output)

    self.state.fd.Set(self.state.fd.Schema.DESCRIPTION(
        "CollectFiles {0}".format(
            self.__class__.__name__)))

    # Just call the FileDownloader with these findspecs
    self.CallFlow("FileDownloader", findspecs=self.args.findspecs,
                  next_state="WriteCollection")

  @flow.StateHandler()
  def WriteCollection(self, responses):
    """Adds the results to the collection."""
    for response_stat in responses:
      self.state.fd.Add(stat=response_stat, urn=response_stat.aff4path)

    self.state.fd.Close(True)

    # Tell our caller about the new collection.
    self.SendReply(self.state.fd.urn)

  @flow.StateHandler()
  def End(self):
    # Notify our creator.
    num_files = len(self.state.fd)

    self.Notify("ViewObject", self.state.output,
                "Completed download of {0:d} files.".format(num_files))


class SendFileArgs(rdfvalue.RDFProtoStruct):
  protobuf = flows_pb2.SendFileArgs


class SendFile(flow.GRRFlow):
  """This flow sends a file to remote listener.

  To use this flow, choose a key and an IV in hex format (if run from the GUI,
  there will be a pregenerated pair key and iv for you to use) and run a
  listener on the server you want to use like this:

  nc -l <port> | openssl aes-128-cbc -d -K <key> -iv <iv> > <filename>

  Returns to parent flow:
    A rdfvalue.StatEntry of the sent file.
  """

  category = "/Filesystem/"
  args_type = SendFileArgs

  @flow.StateHandler(next_state="Done")
  def Start(self):
    """This issues the sendfile request."""

    self.state.Register("key", self.state.args.key.decode("hex"))
    self.state.Register("iv", self.state.args.iv.decode("hex"))

    request = rdfvalue.SendFileRequest(
        key=self.state.key,
        iv=self.state.iv,
        pathspec=self.state.args.pathspec,
        address_family=self.state.args.address_family,
        host=self.state.args.host,
        port=self.state.args.port)
    self.CallClient("SendFile", request, next_state="Done")

  @flow.StateHandler()
  def Done(self, responses):
    if not responses.success:
      self.Log(responses.status.error_message)
      raise flow.FlowError(responses.status.error_message)
