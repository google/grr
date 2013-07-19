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
from grr.lib import type_info
from grr.lib import utils


class GetFile(flow.GRRFlow):
  """An efficient file transfer mechanism.

  Returns to parent flow:
    An PathSpec.
  """

  category = "/Filesystem/"

  flow_typeinfo = type_info.TypeDescriptorSet(
      type_info.PathspecType(
          description="The pathspec for the file to retrieve."),

      type_info.Integer(
          name="read_length",
          default=0,
          help=("The amount of data to read from the file. If 0 we use "
                "the value from a stat call.")
          )
      )

  # We have a maximum of this many chunk reads outstanding (about 10mb)
  WINDOW_SIZE = 200
  CHUNK_SIZE = 512 * 1024

  def Init(self):
    self.state.Register("max_chunk_number",
                        max(2, self.state.read_length/self.CHUNK_SIZE))

    # Read in 512kb chunks
    self.state.Register("chunk_size", self.CHUNK_SIZE)
    self.state.Register("current_chunk_number", 0)
    self.state.Register("file_size", 0)

  @flow.StateHandler(next_state=["Stat"])
  def Start(self):
    """Get information about the file from the client."""
    self.Init()
    self.CallClient("StatFile", rdfvalue.ListDirRequest(
        pathspec=self.state.pathspec),
                    next_state="Stat")

  @flow.StateHandler(next_state=["ReadBuffer", "CheckHashes"])
  def Stat(self, responses):
    """Fix up the pathspec of the file."""
    response = responses.First()
    if responses.success and response:
      self.state.Register("stat", response)
      self.state.pathspec = self.state.stat.pathspec
    else:
      raise IOError("Error: %s" % responses.status)

    # Adjust the size from st_size if read length is not specified.
    if self.state.read_length == 0:
      self.state.file_size = self.state.stat.st_size
    else:
      self.state.file_size = self.state.read_length

    self.state.max_chunk_number = (self.state.file_size /
                                   self.state.chunk_size) + 1

    self.CreateHashImage()
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
          pathspec=self.state.pathspec,
          offset=self.state.current_chunk_number * self.state.chunk_size,
          length=self.state.chunk_size)
      self.CallClient("TransferBuffer", request, next_state="ReadBuffer")
      self.state.current_chunk_number += 1

  def CreateHashImage(self):
    """Force creation of the new AFF4 object.

    Note that this is pinned on the client id - i.e. the client can not change
    aff4 objects outside its tree.
    """
    self.state.Register("urn", aff4.AFF4Object.VFSGRRClient.PathspecToURN(
        self.state.pathspec, self.client_id))

    self.state.stat.aff4path = utils.SmartUnicode(self.state.urn)

    # Create a new Hash image for the data. Note that this object is pickled
    # with this flow between states.
    fd = aff4.FACTORY.Create(self.state.urn, "HashImage",
                             token=self.token)
    # The chunksize must be set to be the same as the transfer chunk size.
    fd.SetChunksize(self.state.chunk_size)
    fd.Set(fd.Schema.STAT(self.state.stat))

    self.state.Register("fd", fd)

  @flow.StateHandler(next_state=["ReadBuffer", "CheckHashes"])
  def ReadBuffer(self, responses):
    """Read the buffer and write to the file."""
    # Did it work?
    if responses.success:
      response = responses.First()
      if not response:
        raise IOError("Missing hash for offset %s missing" % response.offset)

      if response.offset <= self.state.max_chunk_number * self.state.chunk_size:
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
    urn = self.state.get("urn")
    if urn is None:
      self.Notify("ViewObject", self.client_id, "File failed to be transferred")
    else:
      self.Notify("ViewObject", urn, "File transferred successfully")

      self.Log("Finished reading %s", urn)
      self.Log("Flow Completed in %s seconds",
               time.time() - self.state.context.create_time/1e6)

      stat_response = self.state.fd.Get(self.state.fd.Schema.STAT)

      fd = self.state.fd
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

  def Init(self):
    self.state.Register("hash_queue", [])
    self.state.Register("hash_map", {})
    self.state.Register("in_flight", set())
    super(FastGetFile, self).Init()

  def FetchWindow(self, number_of_chunks_to_readahead):
    """Read ahead a number of buffers to fill the window."""
    for _ in range(number_of_chunks_to_readahead):
      # Do not read past the end of file
      if self.state.current_chunk_number > self.state.max_chunk_number:
        return

      offset = self.state.current_chunk_number * self.state.chunk_size
      request = rdfvalue.BufferReference(pathspec=self.state.pathspec,
                                         offset=offset,
                                         length=self.state.chunk_size)
      self.CallClient("HashBuffer", request, next_state="CheckHashes")

      self.state.current_chunk_number += 1

  @flow.StateHandler(next_state=["CheckHashes"])
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
      if response.offset not in self.state.hash_map:
        tracker = HashTracker(response)
        self.state.hash_queue.append(tracker)
        self.state.hash_map[response.offset] = tracker

    self.CheckQueuedHashes()

  def CheckQueuedHashes(self):
    """Check which of the hashes in the queue we already have."""
    urns = [x.blob_urn for x in self.state.hash_queue]
    fds = aff4.FACTORY.Stat(urns, token=self.token)

    # These blob urns we have already.
    matched_urns = set([x["urn"] for x in fds])

    # Fetch all the blob urns we do not have and that are not currently already
    # in flight.
    for hash_blob in self.state.hash_queue:
      offset = hash_blob.hash_response.offset
      if (hash_blob.blob_urn not in matched_urns and
          offset not in self.state.in_flight):
        request = rdfvalue.BufferReference(pathspec=self.state.pathspec,
                                           offset=offset,
                                           length=self.state.chunk_size)
        self.CallClient("TransferBuffer", request, next_state="CheckHashes")
        self.state.in_flight.add(offset)

    # Now read the hashes in order and append as many as possible to the image.
    i = 0
    for i in range(len(self.state.hash_queue)):
      hash_blob = self.state.hash_queue[i]

      if hash_blob.blob_urn not in matched_urns:
        # We can not keep writing until this buffer comes back from the client
        # since hash blobs must be written in order.
        break

      # We must write the hashes in order to the output.
      if hash_blob.hash_response.offset < self.state.fd.size:
        continue

      elif hash_blob.hash_response.offset > self.state.fd.size:
        break

      self.state.fd.AddBlob(hash_blob.hash_response.data,
                            hash_blob.hash_response.length)

      self.Log("Received blob hash %s", hash_blob.blob_urn)
      self.Status("Received %s bytes", self.state.fd.size)

    if i:
      self.state.hash_queue = self.state.hash_queue[i:]
      self.state.hash_map = dict(
          [(x.hash_response.offset, x) for x in self.state.hash_queue])

  @flow.StateHandler(next_state=["CheckHashes"])
  def End(self, responses):
    if self.state.hash_queue:
      self.CheckQueuedHashes()

    # Are we really finished?
    if not self.OutstandingRequests():
      super(FastGetFile, self).End(self.runner, responses)


class GetMBR(flow.GRRFlow):
  """A flow to retrieve the MBR.

  Returns to parent flow:
    The retrieved MBR.
  """

  category = "/Filesystem/"

  flow_typeinfo = type_info.TypeDescriptorSet(
      type_info.Integer(
          description="The length of the MBR buffer to read.",
          name="length",
          default=4096,
          )
      )

  @flow.StateHandler(next_state=["StoreMBR"])
  def Start(self):
    """Schedules the ReadBuffer client action."""
    pathspec = rdfvalue.PathSpec(
        path="\\\\.\\PhysicalDrive0\\",
        pathtype=rdfvalue.PathSpec.PathType.OS,
        path_options=rdfvalue.PathSpec.Options.CASE_LITERAL)

    request = rdfvalue.BufferReference(pathspec=pathspec, offset=0,
                                       length=self.state.length)
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
      fd.Close(sync=True)

      logging.info("Got blob %s (length %s)", digest.encode("hex"),
                   len(cdata))


class FileDownloader(flow.GRRFlow):
  """Handle the automated collection of multiple files.

  This class contains the logic to automatically collect and store a set
  of files and directories.

  Returns to parent flow:
    A StatResponse protobuf for each downloaded file.
  """

  flow_typeinfo = type_info.TypeDescriptorSet(
      type_info.List(
          description="A list of Find Specifications.",
          name="findspecs",
          validator=type_info.FindSpecType(),
          default=[]),
      type_info.List(
          description="A list of Path specifications to find.",
          name="pathspecs",
          validator=type_info.PathspecType(),
          default=[])
      )

  @flow.StateHandler(next_state=["DownloadFiles", "HandleDownloadedFiles"])
  def Start(self):
    """Queue flows for all valid find specs."""
    if self.state.findspecs is None:
      # Call GetFindSpecs, should be overridden by inheriting classes.
      self.state.findspecs = self.GetFindSpecs()

    if not self.state.findspecs and not self.state.pathspecs:
      self.Error("No usable specs found.")

    for findspec in self.state.findspecs:
      self.CallFlow("FindFiles", next_state="DownloadFiles",
                    findspec=findspec, output=None)

    for pathspec in self.state.pathspecs:
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


class FileCollector(flow.GRRFlow):
  """Flow to create a collection from downloaded files.

  This flow calls the FileDownloader and creates a collection for the results.
  Returns to the parent flow:
    A StatResponse protobuf describing the output collection.
  """

  flow_typeinfo = type_info.TypeDescriptorSet(
      type_info.List(
          name="findspecs",
          description="A list of find specifications.",
          validator=type_info.FindSpecType()),
      type_info.String(
          name="output",
          description="A URN to an AFF4Collection to add each result to.",
          default="analysis/collect/{u}-{t}")
      )

  @flow.StateHandler(next_state="WriteCollection")
  def Start(self):
    """Start FileCollector flow."""
    output = self.state.output.format(t=time.time(), u=self.state.context.user)
    self.state.output = self.client_id.Add(output)
    self.state.Register("fd", aff4.FACTORY.Create(self.state.output,
                                                  "AFF4Collection",
                                                  mode="rw", token=self.token))

    self.Log("Created output collection %s", self.state.output)

    self.state.fd.Set(self.state.fd.Schema.DESCRIPTION(
        "CollectFiles {0}".format(
            self.__class__.__name__)))

    # Just call the FileDownloader with these findspecs
    self.CallFlow("FileDownloader", findspecs=self.state.findspecs,
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

  flow_typeinfo = type_info.TypeDescriptorSet(
      type_info.PathspecType(
          description="The pathspec for the file to retrieve.",
          default=None),
      type_info.String(
          name="host",
          description="Hostname or IP to send the file to.",
          default=None),
      type_info.Integer(
          name="port",
          description="Port number on the listening server.",
          default=12345),
      type_info.SemanticEnum(
          enum_container=rdfvalue.NetworkAddress.Family,
          name="address_family",
          default=rdfvalue.NetworkAddress.Family.INET,
          description="AF_INET or AF_INET6."),
      type_info.EncryptionKey(
          name="key",
          description="An encryption key given in hex representation.",
          length=16),
      type_info.EncryptionKey(
          name="iv",
          description="The iv for AES, also given in hex representation.",
          length=16)
      )

  @flow.StateHandler(next_state="Done")
  def Start(self):
    """This issues the sendfile request."""

    self.state.key = self.state.key.decode("hex")
    self.state.iv = self.state.iv.decode("hex")

    request = rdfvalue.SendFileRequest(key=utils.SmartStr(self.state.key),
                                       iv=utils.SmartStr(self.state.iv),
                                       pathspec=self.state.pathspec,
                                       address_family=self.state.address_family,
                                       host=self.state.host,
                                       port=self.state.port)
    self.CallClient("SendFile", request, next_state="Done")

  @flow.StateHandler()
  def Done(self, responses):
    if not responses.success:
      self.Log(responses.status.error_message)
      raise flow.FlowError(responses.status.error_message)
