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
from grr.lib.aff4_objects import filestore
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

    # Create a new BlobImage for the data. Note that this object is pickled
    # with this flow between states.
    self.state.fd = aff4.FACTORY.Create(urn, "VFSBlobImage", token=self.token)

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


class HashTracker(object):
  def __init__(self, hash_response, is_known=False):
    self.hash_response = hash_response
    self.is_known = is_known
    self.blob_urn = rdfvalue.RDFURN("aff4:/blobs").Add(
        hash_response.data.encode("hex"))


class FileTracker(object):
  """A Class to track a single file download."""

  def __init__(self, vfs_urn, stat_entry, digest):
    self.fd = None
    self.urn = vfs_urn
    self.stat_entry = stat_entry
    self.digest = digest
    self.file_size = stat_entry.st_size
    self.pathspec = stat_entry.pathspec
    self.hash_list = []

  def __str__(self):
    return "<Tracker: %s (%s hashes)>" % (self.urn, len(self.hash_list))

  def CreateVFSFile(self, filetype, token=None, chunksize=None):
    """Create a VFSFile with stat_entry metadata.

    We don't do this in __init__ since we need to first need to determine the
    appropriate filetype.

    Args:
      filetype: string filetype
      token: ACL token
      chunksize: BlobImage chunksize
    Side-Effect:
      sets self.fd
    Returns:
      filehandle open for write
    """
    # We create the file in the client namespace and populate with metadata.
    self.fd = aff4.FACTORY.Create(self.urn, filetype, mode="w",
                                  token=token)
    self.fd.SetChunksize(chunksize)
    self.fd.Set(self.fd.Schema.STAT(self.stat_entry))
    self.fd.Set(self.fd.Schema.SIZE(self.file_size))
    self.fd.Set(self.fd.Schema.PATHSPEC(self.pathspec))
    return self.fd


class MultiGetFileArgs(rdfvalue.RDFProtoStruct):
  protobuf = flows_pb2.MultiGetFileArgs


class MultiGetFile(flow.GRRFlow):
  """A flow to effectively retrieve a number of files."""

  args_type = MultiGetFileArgs

  CHUNK_SIZE = 512 * 1024

  # Batch calls to the filestore to at least to group this many items. This
  # allows us to amortize file store round trips and increases throughput.
  MIN_CALL_TO_FILE_STORE = 200

  @flow.StateHandler(next_state="ReceiveFileHash")
  def Start(self):
    """Start state of the flow."""
    self.state.Register("files_hashed", 0)
    self.state.Register("files_to_fetch", 0)
    self.state.Register("files_fetched", 0)
    self.state.Register("files_skipped", 0)

    # A dict of urn->file hash which are waiting to be checked by the file
    # store.
    self.state.Register("pending_hashes", {})

    # A dict of file trackers currently being fetched. Keys are vfs urns and
    # values are FileTracker instances.
    self.state.Register("pending_files", {})

    # Set of blobs we still need to fetch.
    self.state.Register("blobs_we_need", set())

    fd = aff4.FACTORY.Open(filestore.FileStore.PATH, "FileStore", mode="r",
                           token=self.token)
    self.state.Register("filestore", fd)

    for stat_entry in self.args.files_stat_entries:
      self.CallClient("HashFile", pathspec=stat_entry.pathspec,
                      next_state="ReceiveFileHash",
                      request_data=dict(stat_entry=stat_entry))

  @flow.StateHandler(next_state="CheckHash")
  def ReceiveFileHash(self, responses):
    """Receive hashes and add to pending hashes."""
    if not responses.success:
      self.Log("Failed to hash file: %s", responses.status)
      return

    self.state.files_hashed += 1

    response = responses.First()
    stat_entry = responses.request_data["stat_entry"]

    # Store the VFS client namespace URN.
    vfs_urn = aff4.AFF4Object.VFSGRRClient.PathspecToURN(
        stat_entry.pathspec, self.client_id)

    # Create a file tracker for this file and add to the pending hashes store.
    self.state.pending_hashes[vfs_urn] = FileTracker(
        vfs_urn, stat_entry, rdfvalue.HashDigest(response.data))

    if len(self.state.pending_hashes) >= self.MIN_CALL_TO_FILE_STORE:
      self.CheckHashesWithFileStore()

  def CheckHashesWithFileStore(self):
    """Check all queued up hashes for existence in file store.

    Hashes which do not exist in the file store will be downloaded. This
    function flushes the entire queue (self.state.pending_hashes) in order to
    minimize the round trips to the file store.

    If a file was found in the file store it is copied from there into the
    client's VFS namespace. Otherwise, we request the client to hash every block
    in the file, and add it to the file tracking queue
    (self.state.pending_files).
    """
    if not self.state.pending_hashes:
      return

    # This map represents all the hashes in the pending urns.
    file_hashes = {}

    # Store urns by hash to allow us to remove duplicates.
    # keys are hashdigest objects, values are arrays of tracker objects.
    hash_to_urn = {}
    for vfs_urn, tracker in self.state.pending_hashes.iteritems():
      digest = tracker.digest
      digest.vfs_urn = vfs_urn
      file_hashes[vfs_urn] = digest
      hash_to_urn.setdefault(digest, []).append(tracker)

    # First we get all the files which are present in the file store.
    files_in_filestore = {}
    for file_store_urn, digest in self.state.filestore.CheckHashes(
        file_hashes.values(), external=self.args.use_external_stores):

      self.HeartBeat()

      # Since checkhashes only returns one digest per unique hash we need to
      # find any other files pending download with the same hash.
      for tracker in hash_to_urn[digest]:
        vfs_urn = tracker.digest.vfs_urn
        self.state.files_skipped += 1
        file_hashes.pop(vfs_urn, None)
        # Remove this tracker from the pending_hashes store since we no longer
        # need to process it.  Store it to copy into the client VFS space
        files_in_filestore[file_store_urn] = self.state.pending_hashes.pop(
            vfs_urn, None)

    # Now copy all existing files to the client aff4 space.
    for existing_blob in aff4.FACTORY.MultiOpen(files_in_filestore,
                                                mode="r", token=self.token):

      hashset = existing_blob.Get(existing_blob.Schema.HASH)
      for file_tracker in hash_to_urn.get(hashset.sha256, []):

        # Some existing_blob files can be created with 0 size, make sure our
        # size matches the STAT.
        existing_blob.size = file_tracker.file_size

        # Create a file in the client name space with the same classtype and
        # populate its attributes.
        file_tracker.CreateVFSFile(existing_blob.__class__.__name__,
                                   token=self.token,
                                   chunksize=self.CHUNK_SIZE)

        file_tracker.fd.FromBlobImage(existing_blob)
        file_tracker.fd.Set(hashset)

        # Add this file to the index at the canonical location
        existing_blob.AddIndex(file_tracker.urn)

        # It is not critical that this file be written immediately.
        file_tracker.fd.Close(sync=False)

    # Now we iterate over all the files which are not in the store and arrange
    # for them to be copied.
    for vfs_urn in file_hashes:

      # Move the tracker from the pending hashes store to the pending files
      # store - it will now be downloaded.
      file_tracker = self.state.pending_hashes.pop(vfs_urn, None)
      self.state.pending_files[vfs_urn] = file_tracker

      # Create the VFS file for this file tracker.
      file_tracker.CreateVFSFile("VFSBlobImage", token=self.token,
                                 chunksize=self.CHUNK_SIZE)

      # We do not have the file here yet - we need to retrieve it.
      expected_number_of_hashes = file_tracker.file_size / self.CHUNK_SIZE + 1

      # We just hash ALL the chunks in the file now. NOTE: This maximizes client
      # VFS cache hit rate and is far more efficient than launching multiple
      # GetFile flows.
      self.state.files_to_fetch += 1
      for i in range(expected_number_of_hashes):
        self.CallClient("HashBuffer", pathspec=file_tracker.pathspec,
                        offset=i * self.CHUNK_SIZE,
                        length=self.CHUNK_SIZE, next_state="CheckHash",
                        request_data=dict(urn=vfs_urn))

    if self.state.files_hashed % 100 == 0:
      self.Log("Hashed %d files, skipped %s already stored.",
               self.state.files_hashed, self.state.files_skipped)

    # Clear the pending urns. This should already be empty now but just in case
    # we clear it.
    self.state.pending_hashes = {}

  @flow.StateHandler(next_state="WriteBuffer")
  def CheckHash(self, responses):
    """Adds the block hash to the file tracker responsible for this vfs URN."""
    vfs_urn = responses.request_data["urn"]
    file_tracker = self.state.pending_files[vfs_urn]

    hash_response = responses.First()
    if not responses.success or not hash_response:
      self.Log("Failed to read %s: %s" % (file_tracker.urn, responses.status))
      del self.state.pending_files[vfs_urn]
      return

    hash_tracker = HashTracker(hash_response)
    file_tracker.hash_list.append(hash_tracker)

    self.state.blobs_we_need.add(hash_tracker.blob_urn)

    if len(self.state.blobs_we_need) > self.MIN_CALL_TO_FILE_STORE:
      self.FetchFileContent()

  def FetchFileContent(self):
    """Fetch as much as the file's content as possible.

    This drains the pending_files store by checking which blobs we already have
    in the store and issuing calls to the client to receive outstanding blobs.
    """
    if not self.state.pending_files:
      return

    # Check if we have all the blobs in the blob AFF4 namespace..
    stats = aff4.FACTORY.Stat(self.state.blobs_we_need, token=self.token)
    blobs_we_have = set([x["urn"] for x in stats])
    self.state.blobs_we_need = set()

    # Now iterate over all the blobs and add them directly to the blob image.
    for vfs_urn, file_tracker in self.state.pending_files.iteritems():
      for hash_tracker in file_tracker.hash_list:
        # Make sure we read the correct pathspec on the client.
        hash_tracker.hash_response.pathspec = file_tracker.pathspec

        if hash_tracker.blob_urn in blobs_we_have:
          # If we have the data we may call our state directly.
          self.CallState([hash_tracker.hash_response],
                         next_state="WriteBuffer",
                         request_data=dict(urn=vfs_urn))

        else:
          # We dont have this blob - ask the client to transmit it.
          self.CallClient("TransferBuffer", hash_tracker.hash_response,
                          next_state="WriteBuffer",
                          request_data=dict(urn=vfs_urn))

      # Clear the file tracker's hash list.
      file_tracker.hash_list = []

  @flow.StateHandler(next_state="IterateFind")
  def WriteBuffer(self, responses):
    """Write the hash received to the blob image."""
    # Note that hashes must arrive at this state in the correct order since they
    # are sent in the correct order (either via CallState or CallClient).
    vfs_urn = responses.request_data["urn"]
    if vfs_urn not in self.state.pending_files:
      return

    # Failed to read the file - ignore it.
    if not responses.success:
      return self.RemoveInFlightFile(vfs_urn)

    response = responses.First()
    file_tracker = self.state.pending_files[vfs_urn]
    file_tracker.fd.AddBlob(response.data, response.length)

    if response.offset + response.length >= file_tracker.file_size:
      # File done, remove from the store and close it.
      self.RemoveInFlightFile(vfs_urn)

      # Close and write the file to the data store.
      file_tracker.fd.Close(sync=False)

      # Publish the new file event to cause the file to be added to the
      # filestore. This is not time critical so do it when we have spare
      # capacity.
      self.Publish("FileStore.AddFileToStore", vfs_urn,
                   priority=rdfvalue.GrrMessage.Priority.LOW_PRIORITY)

      self.state.files_fetched += 1

      if not self.state.files_fetched % 100:
        self.Log("Fetched %d of %d files.", self.state.files_fetched,
                 self.state.files_to_fetch)

  def RemoveInFlightFile(self, vfs_urn):
    self.SendReply(self.state.pending_files[vfs_urn].stat_entry)
    del self.state.pending_files[vfs_urn]

  @flow.StateHandler(next_state=["CheckHash", "WriteBuffer"])
  def End(self):
    # There are some files still in flight.
    if self.state.pending_hashes or self.state.pending_files:
      self.CheckHashesWithFileStore()
      self.FetchFileContent()

    else:
      return super(MultiGetFile, self).End()


class FileStoreCreateFile(flow.EventListener):
  """Receive an event about a new file and add it to the file store.

  The file store is a central place where files are managed in the data
  store. Files are deduplicated and stored centrally.

  This event listener will be fired when a new file is downloaded through
  e.g. the GetFile flow. We then recalculate the file's hashes and store it in
  the data store under a canonical URN.
  """

  EVENTS = ["FileStore.AddFileToStore"]

  well_known_session_id = rdfvalue.SessionID(
      "aff4:/flows/W:FileStoreCreateFile")

  CHUNK_SIZE = 512 * 1024

  def UpdateIndex(self, target_urn, src_urn):
    """Update the index from the source to the target."""
    idx = aff4.FACTORY.Create(src_urn, "AFF4Index", mode="w", token=self.token)
    idx.Add(target_urn, "", target_urn)

  @flow.EventHandler()
  def ProcessMessage(self, message=None, event=None):
    """Process the new file and add to the file store."""
    _ = event
    vfs_urn = message.payload
    with aff4.FACTORY.Open(vfs_urn, mode="rw", token=self.token) as vfs_fd:
      filestore_fd = aff4.FACTORY.Create(filestore.FileStore.PATH, "FileStore",
                                         mode="w", token=self.token)
      filestore_fd.AddFile(vfs_fd)
      vfs_fd.Flush(sync=False)


class GetMBRArgs(rdfvalue.RDFProtoStruct):
  protobuf = flows_pb2.GetMBRArgs


class GetMBR(flow.GRRFlow):
  """A flow to retrieve the MBR.

  Returns to parent flow:
    The retrieved MBR.
  """

  category = "/Filesystem/"
  args_type = GetMBRArgs
  behaviours = flow.GRRFlow.behaviours + "BASIC"

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
  args_type = rdfvalue.SendFileRequest

  @flow.StateHandler(next_state="Done")
  def Start(self):
    """This issues the sendfile request."""
    self.CallClient("SendFile", self.args, next_state="Done")

  @flow.StateHandler()
  def Done(self, responses):
    if not responses.success:
      self.Log(responses.status.error_message)
      raise flow.FlowError(responses.status.error_message)
