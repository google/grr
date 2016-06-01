#!/usr/bin/env python
"""These flows are designed for high performance transfers."""


import hashlib
import time
import zlib

import logging
from grr.lib import aff4
from grr.lib import config_lib
from grr.lib import data_store
from grr.lib import flow
from grr.lib import rdfvalue
from grr.lib import utils
from grr.lib.aff4_objects import aff4_grr
from grr.lib.aff4_objects import collects
from grr.lib.aff4_objects import filestore
from grr.lib.rdfvalues import client as rdf_client
from grr.lib.rdfvalues import crypto as rdf_crypto
from grr.lib.rdfvalues import flows as rdf_flows
from grr.lib.rdfvalues import paths as rdf_paths
from grr.lib.rdfvalues import protodict as rdf_protodict
from grr.lib.rdfvalues import structs as rdf_structs
from grr.proto import flows_pb2


class GetFileArgs(rdf_structs.RDFProtoStruct):
  protobuf = flows_pb2.GetFileArgs


class GetFile(flow.GRRFlow):
  """An efficient file transfer mechanism (deprecated, use MultiGetFile).

  This flow is deprecated in favor of MultiGetFile, but kept for now for use by
  MemoryCollector since the buffer hashing performed by MultiGetFile is
  pointless for memory acquisition.

  GetFile can also retrieve content from device files that report a size of 0 in
  stat when read_length is specified.

  Returns to parent flow:
    An PathSpec.
  """

  category = "/Filesystem/"

  args_type = GetFileArgs

  # We have a maximum of this many chunk reads outstanding (about 10mb)
  WINDOW_SIZE = 200
  CHUNK_SIZE = 512 * 1024

  @classmethod
  def GetDefaultArgs(cls, token=None):
    _ = token
    result = cls.args_type()
    result.pathspec.pathtype = "OS"

    return result

  @flow.StateHandler(next_state=["Stat"])
  def Start(self):
    """Get information about the file from the client."""
    self.state.Register("max_chunk_number",
                        max(2, self.args.read_length / self.CHUNK_SIZE))

    self.state.Register("current_chunk_number", 0)
    self.state.Register("file_size", 0)
    self.state.Register("fd", None)
    self.state.Register("stat", None)

    self.CallClient("StatFile",
                    rdf_client.ListDirRequest(pathspec=self.args.pathspec),
                    next_state="Stat")

  @flow.StateHandler(next_state=["ReadBuffer", "CheckHashes"])
  def Stat(self, responses):
    """Fix up the pathspec of the file."""
    response = responses.First()
    if responses.success and response:
      self.state.stat = response
      # TODO(user): This is a workaround for broken clients sending back
      # empty pathspecs for pathtype MEMORY. Not needed for clients > 3.0.0.5.
      if self.state.stat.pathspec.path:
        self.args.pathspec = self.state.stat.pathspec
    else:
      if not self.args.ignore_stat_failure:
        raise IOError("Error: %s" % responses.status)

      # Just fill up a bogus stat entry.
      self.state.stat = rdf_client.StatEntry(pathspec=self.args.pathspec)

    # Adjust the size from st_size if read length is not specified.
    if self.args.read_length == 0:
      self.state.file_size = self.state.stat.st_size
    else:
      self.state.file_size = self.args.read_length

    self.state.max_chunk_number = (self.state.file_size / self.CHUNK_SIZE) + 1

    self.CreateBlobImage()
    self.FetchWindow(min(self.WINDOW_SIZE, self.state.max_chunk_number -
                         self.state.current_chunk_number))

  def FetchWindow(self, number_of_chunks_to_readahead):
    """Read ahead a number of buffers to fill the window."""
    for _ in range(number_of_chunks_to_readahead):

      # Do not read past the end of file
      if self.state.current_chunk_number > self.state.max_chunk_number:
        return

      request = rdf_client.BufferReference(
          pathspec=self.args.pathspec,
          offset=self.state.current_chunk_number * self.CHUNK_SIZE,
          length=self.CHUNK_SIZE)
      self.CallClient("TransferBuffer", request, next_state="ReadBuffer")
      self.state.current_chunk_number += 1

  def CreateBlobImage(self):
    """Force creation of the new AFF4 object.

    Note that this is pinned on the client id - i.e. the client can not change
    aff4 objects outside its tree.
    """
    urn = aff4.AFF4Object.VFSGRRClient.PathspecToURN(self.args.pathspec,
                                                     self.client_id)

    self.state.stat.aff4path = urn

    # Create a new BlobImage for the data. Note that this object is pickled
    # with this flow between states.
    self.state.fd = aff4.FACTORY.Create(urn,
                                        aff4_grr.VFSBlobImage,
                                        token=self.token)

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
               time.time() - self.state.context.create_time / 1e6)

      stat_response = self.state.fd.Get(self.state.fd.Schema.STAT)

      fd.size = min(fd.size, self.state.file_size)
      fd.Set(fd.Schema.CONTENT_LAST, rdfvalue.RDFDatetime().Now())
      fd.Close(sync=True)

      # Notify any parent flows the file is ready to be used now.
      self.SendReply(stat_response)

    super(GetFile, self).End()


class HashTracker(object):

  def __init__(self, hash_response, is_known=False):
    self.hash_response = hash_response
    self.is_known = is_known
    self.digest = hash_response.data.encode("hex")


class FileTracker(object):
  """A Class to track a single file download."""

  def __init__(self, stat_entry, client_id, request_data, index=None):
    self.fd = None
    self.stat_entry = stat_entry
    self.hash_obj = None
    self.hash_list = []
    self.pathspec = stat_entry.pathspec
    self.urn = aff4.AFF4Object.VFSGRRClient.PathspecToURN(self.pathspec,
                                                          client_id)
    self.stat_entry.aff4path = self.urn
    self.request_data = request_data
    self.index = index

    # The total number of bytes available in this file. This may be different
    # from the size as reported by stat() for special files (e.g. proc files).
    self.bytes_read = 0

    # The number of bytes we are expected to fetch. This value depends on
    # - the bytes available (stat_entry.st_size or bytes_read if available).
    # - a limit to the file size in the flow (self.args.file_size).
    self.size_to_download = 0

  def __str__(self):
    sha256 = self.hash_obj and self.hash_obj.sha256
    if sha256:
      return "<Tracker: %s (sha256: %s)>" % (self.urn, sha256)
    else:
      return "<Tracker: %s >" % self.urn

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
    self.fd = aff4.FACTORY.Create(self.urn, filetype, mode="w", token=token)
    self.fd.SetChunksize(chunksize)
    self.fd.Set(self.fd.Schema.STAT(self.stat_entry))
    self.fd.Set(self.fd.Schema.PATHSPEC(self.pathspec))
    self.fd.Set(self.fd.Schema.CONTENT_LAST(rdfvalue.RDFDatetime().Now()))
    return self.fd


class MultiGetFileMixin(object):
  """A flow mixin to efficiently retrieve a number of files.

  The class extending this can provide a self.state with the following
  attributes:
  - file_size: int. Maximum number of bytes to download.
  - use_external_stores: boolean. If true, look in any defined external file
    stores for files before downloading them, and offer any new files to
    external stores. This should be true unless the external checks are
    misbehaving.
  """

  CHUNK_SIZE = 512 * 1024

  # Batch calls to the filestore to at least to group this many items. This
  # allows us to amortize file store round trips and increases throughput.
  MIN_CALL_TO_FILE_STORE = 200

  def Start(self):
    """Initialize our state."""
    super(MultiGetFileMixin, self).Start()

    self.state.Register("files_hashed", 0)
    self.state.Register("use_external_stores", False)
    self.state.Register("file_size", 0)
    self.state.Register("files_to_fetch", 0)
    self.state.Register("files_fetched", 0)
    self.state.Register("files_skipped", 0)

    # Counter to batch up hash checking in the filestore
    self.state.Register("files_hashed_since_check", 0)

    # A dict of file trackers which are waiting to be checked by the file
    # store.  Keys are vfs urns and values are FileTrack instances.  Values are
    # copied to pending_files for download if not present in FileStore.
    self.state.Register("pending_hashes", {})

    # A dict of file trackers currently being fetched. Keys are vfs urns and
    # values are FileTracker instances.
    self.state.Register("pending_files", {})

    # A mapping of index values to the original pathspecs.
    self.state.Register("indexed_pathspecs", {})

    # Set of blobs we still need to fetch.
    self.state.Register("blobs_we_need", set())

    fd = aff4.FACTORY.Open(filestore.FileStore.PATH,
                           filestore.FileStore,
                           mode="r",
                           token=self.token)
    self.state.Register("filestore", fd)

  def GenerateIndex(self, pathspec):
    h = hashlib.sha256()
    h.update(pathspec.SerializeToString())
    return h.hexdigest()

  def StartFileFetch(self, pathspec, request_data=None):
    """The entry point for this flow mixin - Schedules new file transfer."""
    # Create an index so we can find this pathspec later.
    index = self.GenerateIndex(pathspec)
    self.state.indexed_pathspecs[index] = pathspec

    request_data = request_data or {}
    request_data["index"] = index
    self.CallClient("StatFile",
                    pathspec=pathspec,
                    next_state="StoreStat",
                    request_data=request_data)

    request = rdf_client.FingerprintRequest(pathspec=pathspec,
                                            max_filesize=self.state.file_size)
    request.AddRequest(fp_type=rdf_client.FingerprintTuple.Type.FPT_GENERIC,
                       hashers=[rdf_client.FingerprintTuple.HashType.MD5,
                                rdf_client.FingerprintTuple.HashType.SHA1,
                                rdf_client.FingerprintTuple.HashType.SHA256])

    self.CallClient("HashFile",
                    request,
                    next_state="ReceiveFileHash",
                    request_data=request_data)

  def ReceiveFetchedFile(self, stat_entry, file_hash, request_data=None):
    """This method will be called for each new file successfully fetched.

    Args:
      stat_entry: rdf_client.StatEntry object describing the file.
      file_hash: rdf_crypto.Hash object with file hashes.
      request_data: Arbitrary dictionary that was passed to the corresponding
                    StartFileFetch call.
    """

  def FileFetchFailed(self, pathspec, request_name, request_data=None):
    """This method will be called when stat or hash requests fail.

    Args:
      pathspec: Pathspec of a file that failed to be fetched.
      request_name: Name of a failed client action.
      request_data: Arbitrary dictionary that was passed to the corresponding
                    StartFileFetch call.
    """

  @flow.StateHandler()
  def StoreStat(self, responses):
    """Stores stat entry in the flow's state."""

    if not responses.success:
      self.Log("Failed to stat file: %s", responses.status)
      self.FileFetchFailed(responses.request.request.payload.pathspec,
                           responses.request.request.name,
                           request_data=responses.request_data)
      return

    stat_entry = responses.First()
    index = responses.request_data["index"]
    self.state.pending_hashes[index] = FileTracker(stat_entry, self.client_id,
                                                   responses.request_data,
                                                   index)

  @flow.StateHandler(next_state="CheckHash")
  def ReceiveFileHash(self, responses):
    """Add hash digest to tracker and check with filestore."""
    # Support old clients which may not have the new client action in place yet.
    # TODO(user): Deprecate once all clients have the HashFile action.

    if not responses.success and responses.request.request.name == "HashFile":
      logging.debug(
          "HashFile action not available, falling back to FingerprintFile.")
      self.CallClient("FingerprintFile",
                      responses.request.request.payload,
                      next_state="ReceiveFileHash",
                      request_data=responses.request_data)
      return

    index = responses.request_data["index"]
    if not responses.success:
      self.Log("Failed to hash file: %s", responses.status)
      self.state.pending_hashes.pop(index, None)
      self.FileFetchFailed(responses.request.request.payload.pathspec,
                           responses.request.request.name,
                           request_data=responses.request_data)
      return

    self.state.files_hashed += 1
    response = responses.First()
    if response.HasField("hash"):
      hash_obj = response.hash
    else:
      # Deprecate this method of returning hashes.
      hash_obj = rdf_crypto.Hash()

      if len(response.results) < 1 or response.results[0]["name"] != "generic":
        self.Log("Failed to hash file: %s", self.state.indexed_pathspecs[index])
        self.state.pending_hashes.pop(index, None)
        return

      result = response.results[0]

      try:
        for hash_type in ["md5", "sha1", "sha256"]:
          value = result.GetItem(hash_type)
          setattr(hash_obj, hash_type, value)
      except AttributeError:
        self.Log("Failed to hash file: %s", self.state.indexed_pathspecs[index])
        self.state.pending_hashes.pop(index, None)
        return

    try:
      tracker = self.state.pending_hashes[index]
    except KeyError:
      # TODO(user): implement a test for this and handle the failure
      # gracefully: i.e. maybe we can continue with an empty StatEntry.
      self.Error("Couldn't stat the file, but got the hash (%s): %s" %
                 (utils.SmartStr(index), utils.SmartStr(response.pathspec)))
      return

    tracker.hash_obj = hash_obj
    tracker.bytes_read = response.bytes_read

    self.state.files_hashed_since_check += 1
    if self.state.files_hashed_since_check >= self.MIN_CALL_TO_FILE_STORE:
      self._CheckHashesWithFileStore()

  def _CheckHashesWithFileStore(self):
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
    for index, tracker in self.state.pending_hashes.iteritems():

      # We might not have gotten this hash yet
      if tracker.hash_obj is None:
        continue

      digest = tracker.hash_obj.sha256
      file_hashes[index] = tracker.hash_obj
      hash_to_urn.setdefault(digest, []).append(tracker)

    # First we get all the files which are present in the file store.
    files_in_filestore = set()
    for file_store_urn, hash_obj in self.state.filestore.CheckHashes(
        file_hashes.values(),
        external=self.state.use_external_stores):

      self.HeartBeat()

      # Since checkhashes only returns one digest per unique hash we need to
      # find any other files pending download with the same hash.
      for tracker in hash_to_urn[hash_obj.sha256]:
        self.state.files_skipped += 1
        file_hashes.pop(tracker.index)
        files_in_filestore.add(file_store_urn)
        # Remove this tracker from the pending_hashes store since we no longer
        # need to process it.
        self.state.pending_hashes.pop(tracker.index)

    # Now that the check is done, reset our counter
    self.state.files_hashed_since_check = 0

    # Now copy all existing files to the client aff4 space.
    for existing_blob in aff4.FACTORY.MultiOpen(files_in_filestore,
                                                mode="rw",
                                                token=self.token):

      hashset = existing_blob.Get(existing_blob.Schema.HASH)
      if hashset is None:
        self.Log("Filestore File %s has no hash.", existing_blob.urn)
        continue

      for file_tracker in hash_to_urn.get(hashset.sha256, []):
        # Due to potential filestore corruption, the existing_blob files can
        # have 0 size, make sure our size matches the actual size in that case.
        if existing_blob.size == 0:
          existing_blob.size = (file_tracker.bytes_read or
                                file_tracker.stat_entry.st_size)

        # Create a file in the client name space with the same classtype and
        # populate its attributes.
        file_tracker.CreateVFSFile(existing_blob.__class__,
                                   token=self.token,
                                   chunksize=self.CHUNK_SIZE)

        file_tracker.fd.FromBlobImage(existing_blob)
        file_tracker.fd.Set(hashset)

        # Add this file to the index at the canonical location
        existing_blob.AddIndex(file_tracker.urn)

        # It is not critical that this file be written immediately.
        file_tracker.fd.Close(sync=False)

        # Let the caller know we have this file already.
        self.ReceiveFetchedFile(file_tracker.stat_entry,
                                file_tracker.hash_obj,
                                request_data=file_tracker.request_data)

    # Now we iterate over all the files which are not in the store and arrange
    # for them to be copied.
    for index in file_hashes:

      # Move the tracker from the pending hashes store to the pending files
      # store - it will now be downloaded.
      file_tracker = self.state.pending_hashes.pop(index)
      self.state.pending_files[index] = file_tracker

      # Create the VFS file for this file tracker.
      file_tracker.CreateVFSFile(aff4_grr.VFSBlobImage,
                                 token=self.token,
                                 chunksize=self.CHUNK_SIZE)

      # If we already know how big the file is we use that, otherwise fall back
      # to the size reported by stat.
      if file_tracker.bytes_read > 0:
        file_tracker.size_to_download = file_tracker.bytes_read
      else:
        file_tracker.size_to_download = file_tracker.stat_entry.st_size

      # We do not have the file here yet - we need to retrieve it.
      expected_number_of_hashes = (
          file_tracker.size_to_download / self.CHUNK_SIZE + 1)

      # We just hash ALL the chunks in the file now. NOTE: This maximizes client
      # VFS cache hit rate and is far more efficient than launching multiple
      # GetFile flows.
      self.state.files_to_fetch += 1

      for i in range(expected_number_of_hashes):
        if i == expected_number_of_hashes - 1:
          # The last chunk is short.
          length = file_tracker.size_to_download % self.CHUNK_SIZE
        else:
          length = self.CHUNK_SIZE
        self.CallClient("HashBuffer",
                        pathspec=file_tracker.pathspec,
                        offset=i * self.CHUNK_SIZE,
                        length=length,
                        next_state="CheckHash",
                        request_data=dict(index=index))

    if self.state.files_hashed % 100 == 0:
      self.Log("Hashed %d files, skipped %s already stored.",
               self.state.files_hashed, self.state.files_skipped)

  @flow.StateHandler(next_state="WriteBuffer")
  def CheckHash(self, responses):
    """Adds the block hash to the file tracker responsible for this vfs URN."""
    index = responses.request_data["index"]

    if index not in self.state.pending_files:
      # This is a blobhash for a file we already failed to read and logged as
      # below, check here to avoid logging dups.
      return

    file_tracker = self.state.pending_files[index]

    hash_response = responses.First()
    if not responses.success or not hash_response:
      self.Log("Failed to read %s: %s" % (file_tracker.urn, responses.status))
      del self.state.pending_files[index]
      return

    hash_tracker = HashTracker(hash_response)
    file_tracker.hash_list.append(hash_tracker)

    self.state.blobs_we_need.add(hash_tracker.digest)

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
    for index, file_tracker in self.state.pending_files.iteritems():
      for hash_tracker in file_tracker.hash_list:
        # Make sure we read the correct pathspec on the client.
        hash_tracker.hash_response.pathspec = file_tracker.pathspec

        if hash_tracker.digest in blobs_we_have:
          # If we have the data we may call our state directly.
          self.CallState([hash_tracker.hash_response],
                         next_state="WriteBuffer",
                         request_data=dict(index=index))

        else:
          # We dont have this blob - ask the client to transmit it.
          self.CallClient("TransferBuffer",
                          hash_tracker.hash_response,
                          next_state="WriteBuffer",
                          request_data=dict(index=index))

      # Clear the file tracker's hash list.
      file_tracker.hash_list = []

  @flow.StateHandler(next_state="IterateFind")
  def WriteBuffer(self, responses):
    """Write the hash received to the blob image."""

    # Note that hashes must arrive at this state in the correct order since they
    # are sent in the correct order (either via CallState or CallClient).
    index = responses.request_data["index"]
    if index not in self.state.pending_files:
      return

    # Failed to read the file - ignore it.
    if not responses.success:
      return self.RemoveInFlightFile(index)

    response = responses.First()
    file_tracker = self.state.pending_files.get(index)
    if file_tracker:
      file_tracker.fd.AddBlob(response.data, response.length)

      if (response.length < file_tracker.fd.chunksize or
          response.offset + response.length >= file_tracker.size_to_download):
        # File done, remove from the store and close it.
        self.RemoveInFlightFile(index)

        # Close and write the file to the data store.
        file_tracker.fd.Close(sync=True)

        # Publish the new file event to cause the file to be added to the
        # filestore. This is not time critical so do it when we have spare
        # capacity.
        self.Publish("FileStore.AddFileToStore",
                     file_tracker.fd.urn,
                     priority=rdf_flows.GrrMessage.Priority.LOW_PRIORITY)

        self.state.files_fetched += 1

        if not self.state.files_fetched % 100:
          self.Log("Fetched %d of %d files.", self.state.files_fetched,
                   self.state.files_to_fetch)

  def RemoveInFlightFile(self, index):
    """Removes a file from the pending files list."""

    file_tracker = self.state.pending_files.pop(index)
    if file_tracker:
      self.ReceiveFetchedFile(file_tracker.stat_entry,
                              file_tracker.hash_obj,
                              request_data=file_tracker.request_data)

  @flow.StateHandler(next_state=["CheckHash", "WriteBuffer"])
  def End(self):
    # There are some files still in flight.
    if self.state.pending_hashes or self.state.pending_files:
      self._CheckHashesWithFileStore()
      self.FetchFileContent()

    if not self.runner.OutstandingRequests():
      super(MultiGetFileMixin, self).End()


class MultiGetFileArgs(rdf_structs.RDFProtoStruct):
  protobuf = flows_pb2.MultiGetFileArgs


class MultiGetFile(MultiGetFileMixin, flow.GRRFlow):
  """A flow to effectively retrieve a number of files."""

  args_type = MultiGetFileArgs

  @flow.StateHandler(next_state=["ReceiveFileHash", "StoreStat"])
  def Start(self):
    """Start state of the flow."""
    super(MultiGetFile, self).Start()

    self.state.use_external_stores = self.args.use_external_stores

    self.state.file_size = self.args.file_size

    unique_paths = set()

    for pathspec in self.args.pathspecs:

      vfs_urn = aff4.AFF4Object.VFSGRRClient.PathspecToURN(pathspec,
                                                           self.client_id)

      if vfs_urn not in unique_paths:
        # Only Stat/Hash each path once, input pathspecs can have dups.
        unique_paths.add(vfs_urn)

        self.StartFileFetch(pathspec)

  def ReceiveFetchedFile(self, stat_entry, unused_hash_obj, request_data=None):
    """This method will be called for each new file successfully fetched."""
    _ = request_data
    self.SendReply(stat_entry)


class FileStoreCreateFile(flow.EventListener):
  """Receive an event about a new file and add it to the file store.

  The file store is a central place where files are managed in the data
  store. Files are deduplicated and stored centrally.

  This event listener will be fired when a new file is downloaded through
  e.g. the GetFile flow. We then recalculate the file's hashes and store it in
  the data store under a canonical URN.
  """

  EVENTS = ["FileStore.AddFileToStore"]

  well_known_session_id = rdfvalue.SessionID(flow_name="FileStoreCreateFile")

  CHUNK_SIZE = 512 * 1024

  @flow.EventHandler()
  def ProcessMessage(self, message=None, event=None):
    """Process the new file and add to the file store."""
    _ = event
    vfs_urn = message.payload

    vfs_fd = aff4.FACTORY.Open(vfs_urn, mode="rw", token=self.token)
    filestore_fd = aff4.FACTORY.Create(filestore.FileStore.PATH,
                                       filestore.FileStore,
                                       mode="w",
                                       token=self.token)
    filestore_fd.AddFile(vfs_fd)
    vfs_fd.Flush(sync=False)


class GetMBRArgs(rdf_structs.RDFProtoStruct):
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
    pathspec = rdf_paths.PathSpec(
        path="\\\\.\\PhysicalDrive0\\",
        pathtype=rdf_paths.PathSpec.PathType.OS,
        path_options=rdf_paths.PathSpec.Options.CASE_LITERAL)

    request = rdf_client.BufferReference(pathspec=pathspec,
                                         offset=0,
                                         length=self.args.length)
    self.CallClient("ReadBuffer", request, next_state="StoreMBR")

  @flow.StateHandler()
  def StoreMBR(self, responses):
    """This method stores the MBR."""

    if not responses.success:
      msg = "Could not retrieve MBR: %s" % responses.status
      self.Log(msg)
      raise flow.FlowError(msg)

    response = responses.First()

    mbr = aff4.FACTORY.Create(
        self.client_id.Add("mbr"),
        aff4_grr.VFSFile,
        mode="w",
        token=self.token)
    mbr.write(response.data)
    mbr.Close()
    self.Log("Successfully stored the MBR (%d bytes)." % len(response.data))
    self.SendReply(rdfvalue.RDFBytes(response.data))


class TransferStore(flow.WellKnownFlow):
  """Store a buffer into a determined location."""
  well_known_session_id = rdfvalue.SessionID(flow_name="TransferStore")

  def ProcessMessages(self, msg_list):
    blobs = []
    for message in msg_list:
      if (message.auth_state !=
          rdf_flows.GrrMessage.AuthorizationState.AUTHENTICATED):
        logging.error("TransferStore request from %s is not authenticated.",
                      message.source)
        continue

      read_buffer = message.payload
      data = read_buffer.data
      if not data:
        continue

      if (read_buffer.compression ==
          rdf_protodict.DataBlob.CompressionType.ZCOMPRESSION):
        data = zlib.decompress(data)
      elif (read_buffer.compression ==
            rdf_protodict.DataBlob.CompressionType.UNCOMPRESSED):
        pass
      else:
        raise RuntimeError("Unsupported compression")

      blobs.append(data)

    data_store.DB.StoreBlobs(blobs, token=self.token)

  def ProcessMessage(self, message):
    """Write the blob into the AFF4 blob storage area."""
    return self.ProcessMessages([message])


class SendFile(flow.GRRFlow):
  """This flow sends a file to remote listener.

  To use this flow, choose a key and an IV in hex format (if run from the GUI,
  there will be a pregenerated pair key and iv for you to use) and run a
  listener on the server you want to use like this:

  nc -l <port> | openssl aes-128-cbc -d -K <key> -iv <iv> > <filename>

  Returns to parent flow:
    A rdf_client.StatEntry of the sent file.
  """

  category = "/Filesystem/"
  args_type = rdf_client.SendFileRequest

  @flow.StateHandler(next_state="Done")
  def Start(self):
    """This issues the sendfile request."""
    self.CallClient("SendFile", self.args, next_state="Done")

  @flow.StateHandler()
  def Done(self, responses):
    if not responses.success:
      self.Log(responses.status.error_message)
      raise flow.FlowError(responses.status.error_message)


class LoadComponentMixin(object):
  """A mixin which loads components on the client.

  Use this mixin to force the client to load the required components prior to
  launching client actions implemented by those components.
  """

  # We handle client exits by ourselves.
  handles_crashes = True

  def LoadComponentOnClient(self, name=None, version=None, next_state=None):
    """Load the component with the specified name and version."""
    if next_state is None:
      raise TypeError("next_state not specified.")

    client = aff4.FACTORY.Open(self.client_id, token=self.token)
    system = unicode(client.Get(client.Schema.SYSTEM) or "").lower()

    # TODO(user): Remove python hack when client 3.1 is pushed.
    request_data = dict(name=name, version=version, next_state=next_state)
    python_hack_root_urn = config_lib.CONFIG.Get("Config.python_hack_root")
    python_hack_path = python_hack_root_urn.Add(system).Add(
        "restart_if_component_loaded.py")

    fd = aff4.FACTORY.Open(python_hack_path, token=self.token)
    if not isinstance(fd, collects.GRRSignedBlob):
      logging.info("Python hack %s not available.", python_hack_path)

      self.CallStateInline(next_state="LoadComponentAfterFlushOldComponent",
                           request_data=request_data)
    else:
      logging.info("Sending python hack %s", python_hack_path)

      for python_blob in fd:
        self.CallClient("ExecutePython",
                        python_code=python_blob,
                        py_args=dict(name=name, version=version),
                        next_state="LoadComponentAfterFlushOldComponent",
                        request_data=request_data)

  @flow.StateHandler()
  def LoadComponentAfterFlushOldComponent(self, responses):
    """Load the component."""
    request_data = responses.request_data
    name = request_data["name"]
    version = request_data["version"]
    next_state = request_data["next_state"]

    # Get the component summary.
    component_urn = config_lib.CONFIG.Get("Config.aff4_root").Add(
        "components").Add("%s_%s" % (name, version))

    try:
      fd = aff4.FACTORY.Open(component_urn,
                             aff4_type=collects.ComponentObject,
                             mode="r",
                             token=self.token)
    except IOError as e:
      raise IOError("Required component not found: %s" % e)

    component_summary = fd.Get(fd.Schema.COMPONENT)
    if component_summary is None:
      raise RuntimeError("Component %s (%s) does not exist in data store." %
                         (name, version))

    self.CallClient("LoadComponent",
                    summary=component_summary,
                    next_state="ComponentLoaded",
                    request_data=dict(next_state=next_state))

  @flow.StateHandler()
  def ComponentLoaded(self, responses):
    if not responses.success:
      self.Log(responses.status.error_message)
      raise flow.FlowError(responses.status.error_message)

    self.Log("Loaded component %s", responses.First().summary.name)
    self.CallStateInline(next_state=responses.request_data["next_state"])
