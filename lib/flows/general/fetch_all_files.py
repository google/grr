#!/usr/bin/env python
"""Find certain types of files, compute hashes, and fetch unknown ones."""



import stat

from grr.lib import aff4
from grr.lib import config_lib
from grr.lib import flow
from grr.lib import rdfvalue
from grr.lib.aff4_objects import filestore
from grr.proto import flows_pb2


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


class FetchAllFilesArgs(rdfvalue.RDFProtoStruct):
  protobuf = flows_pb2.FetchAllFilesArgs


class FetchAllFiles(flow.GRRFlow):
  """This flow finds files, computes their hashes, and fetches 'new' files.

  The result from this flow is a population of aff4 objects under
  aff4:/filestore/hash/(generic|pecoff)/<hashname>/<hashvalue>.
  There may also be a symlink from the original file to the retrieved
  content.
  """

  category = "/Filesystem/"
  CHUNK_SIZE = 512 * 1024
  _MAX_FETCHABLE_SIZE = 100 * 1024 * 1024

  # Maximum number of files we have in flight before we reiterate the find. Note
  # that if a find iteration returns many files, we may be processing more than
  # this number, but this is a good approximation.
  MAX_FILES_IN_FLIGHT = 2

  # Batch calls to the filestore to this maximum number. This allows us to
  # amortize file store round trips and increases throughput.
  MAX_CALL_TO_FILE_STORE = 100

  args_type = FetchAllFilesArgs

  @flow.StateHandler(next_state="IterateFind")
  def Start(self):
    """Issue the find request."""
    self.state.Register("files_found", 0)
    self.state.Register("files_hashed", 0)
    self.state.Register("files_to_fetch", 0)
    self.state.Register("files_fetched", 0)
    self.state.Register("files_skipped", 0)

    # A dict of urn->hash which are waiting to be checked by the file store.
    self.state.Register("pending_urns", [])

    # A local store for temporary data. Keys are aff4 URNs, values are tuples of
    # (fd, file_size, pathspec, list of hashes).
    self.state.Register("store", {})

    fd = aff4.FACTORY.Open(filestore.FileStore.PATH, "FileStore", mode="r",
                           token=self.token)
    self.state.Register("filestore", fd)

    self.args.findspec.iterator.number = self.args.iteration_count
    self.CallClient("Find", self.args.findspec, next_state="IterateFind")

  @flow.StateHandler(next_state=["IterateFind", "ReceiveFileHash"])
  def IterateFind(self, responses):
    """Iterate through find responses, and spawn fingerprint requests."""
    if not responses.success:
      # We just stop the find iteration, the flow goes on.
      self.Log("Failed Find: %s", responses.status)
      return

    for response in responses:
      # Only process regular files.
      if stat.S_ISREG(response.hit.st_mode):
        self.state.files_found += 1

        # If the binary is too large we just ignore it.
        file_size = response.hit.st_size
        if file_size > self._MAX_FETCHABLE_SIZE:
          self.Log("%s too large to fetch. Size=%d",
                   response.pathspec.CollapsePath(), file_size)

        response.hit.aff4path = aff4.AFF4Object.VFSGRRClient.PathspecToURN(
            response.hit.pathspec, self.client_id)

        self.SendReply(response.hit)
        self.CallClient("HashFile", pathspec=response.hit.pathspec,
                        next_state="ReceiveFileHash",
                        request_data=dict(hit=response.hit))

    # Hold onto the iterator in the state - we might need to re-iterate this
    # later.
    self.args.findspec.iterator = responses.iterator

    # Only find more files if we have no files in flight.
    if responses.iterator.state != rdfvalue.Iterator.State.FINISHED:
      # Only find more files if we have no files in flight.
      if len(self.state.store) < self.MAX_FILES_IN_FLIGHT:
        self.CallClient("Find", self.args.findspec, next_state="IterateFind")

    else:
      # Done!
      self.Log("Found %d files.", self.state.files_found)

  @flow.StateHandler(next_state="CheckHash")
  def ReceiveFileHash(self, responses):
    """Check if we already have this file hash."""
    if not responses.success:
      self.Log("Failed to hash file: %s", responses.status)
      return

    self.state.files_hashed += 1

    response = responses.First()
    hit = responses.request_data["hit"]

    # Store the VFS client namespace URN.
    vfs_urn = aff4.AFF4Object.VFSGRRClient.PathspecToURN(
        hit.pathspec, self.client_id)

    # Keep the file handle around so it is available in following states.
    self.state.store[vfs_urn] = FileTracker(
        vfs_urn, hit, rdfvalue.HashDigest(response.data))

    # Add the file urn to the list of pending urns.
    self.state.pending_urns.append(vfs_urn)

    if len(self.state.pending_urns) >= self.MAX_CALL_TO_FILE_STORE:
      self.CheckHashesWithFileStore()

  def CheckHashesWithFileStore(self):
    """Check all queued up hashes for existence in file store.

    Hashes which do not exist in the file store will be downloaded. This
    function runs on the entire queue in order to minimize the round trips to
    the file store.
    """
    # This checks the file store if we have this file already.
    file_hashes = {}

    for vfs_urn in self.state.pending_urns:
      digest = self.state.store[vfs_urn].digest
      digest.vfs_urn = vfs_urn
      file_hashes[vfs_urn] = digest

    # Clear the pending urns.
    self.state.pending_urns = []

    for file_store_urn, digest in self.state.filestore.CheckHashes(
        file_hashes.values(), external=self.args.use_external_stores):

      self.state.files_skipped += 1

      # In this loop we have only the hashes in the store.
      vfs_urn = digest.vfs_urn
      file_hashes.pop(vfs_urn, None)

      file_tracker = self.state.store.pop(vfs_urn)

      # Just copy the file data from the file store.
      existing_blob = aff4.FACTORY.Open(file_store_urn, token=self.token)

      # Some existing_blob files can be created with 0 size, make sure our size
      # matches the STAT.
      existing_blob.size = file_tracker.file_size

      # Create a file in the client name space with the same classtype and
      # populate its attributes.
      file_tracker.CreateVFSFile(existing_blob.__class__.__name__,
                                 token=self.token,
                                 chunksize=self.CHUNK_SIZE)

      file_tracker.fd.FromBlobImage(existing_blob)
      file_tracker.fd.Set(existing_blob.Get(existing_blob.Schema.HASH))
      file_tracker.fd.Close()

    # Now we iterate over all the files which are not in the store.
    for vfs_urn in file_hashes:
      file_tracker = self.state.store[vfs_urn]
      file_tracker.CreateVFSFile("VFSBlobImage", token=self.token,
                                 chunksize=self.CHUNK_SIZE)

      # We do not have the file here yet - we need to retrieve it.
      expected_number_of_hashes = file_tracker.file_size / self.CHUNK_SIZE + 1

      # We just hash ALL the chunks now.
      self.state.files_to_fetch += 1
      for i in range(expected_number_of_hashes):
        self.CallClient("HashBuffer", pathspec=file_tracker.pathspec,
                        offset=i * self.CHUNK_SIZE,
                        length=self.CHUNK_SIZE, next_state="CheckHash",
                        request_data=dict(urn=vfs_urn))

    lease_time = config_lib.CONFIG["Worker.flow_lease_time"]
    if self.CheckLease() < lease_time/3:
      self.UpdateLease(lease_time)

    if not int(self.state.files_hashed % 100):
      self.Log("Hashed %d files, skipped %s already stored.",
               self.state.files_hashed,
               self.state.files_skipped)

  @flow.StateHandler(next_state="WriteBuffer")
  def CheckHash(self, responses):
    """Check if we have the hashes in the blob area, fetch data from clients."""
    vfs_urn = responses.request_data["urn"]
    file_tracker = self.state.store[vfs_urn]

    hash_response = responses.First()
    if not responses.success or not hash_response:
      self.Log("Failed to read %s: %s" % (file_tracker.urn, responses.status))
      del self.state.store[vfs_urn]
      return

    file_tracker.hash_list.append(HashTracker(hash_response))

    # We wait for all the hashes to be queued in the state, and now we check
    # them all at once to minimize data store round trips.
    max_hashes_required = min(self.MAX_CALL_TO_FILE_STORE,
                              file_tracker.file_size / self.CHUNK_SIZE + 1)

    if len(file_tracker.hash_list) >= max_hashes_required:
      self.FetchFileContent(file_tracker)

  def FetchFileContent(self, file_tracker):
    """Fetch as much as the file's content as possible."""
    # Check if we have all the blobs in the blob AFF4 namespace..
    blobs_we_need = [x.blob_urn for x in file_tracker.hash_list]
    stats = aff4.FACTORY.Stat(blobs_we_need, token=self.token)
    blobs_we_have = set([x["urn"] for x in stats])

    # Now iterate over all the blobs and add them directly to the blob image.
    for hash_tracker in file_tracker.hash_list:
      # Make sure we read the correct pathspec on the client.
      hash_tracker.hash_response.pathspec = file_tracker.pathspec

      if hash_tracker.blob_urn in blobs_we_have:
        # If we have the data we may call our state directly.
        self.CallState([hash_tracker.hash_response],
                       next_state="WriteBuffer", request_data=dict(
                           urn=file_tracker.urn))

      else:
        # We dont have this blob - ask the client to transmit it.
        self.CallClient("TransferBuffer", hash_tracker.hash_response,
                        next_state="WriteBuffer", request_data=dict(
                            urn=file_tracker.urn))

    # Clear the hash list.
    file_tracker.hash_list = []

  @flow.StateHandler(next_state="IterateFind")
  def WriteBuffer(self, responses):
    """Write the hash received to the blob image."""
    # Note that hashes must arrive at this state in the correct order since they
    # are sent in the correct order (either via CallState or CallClient).
    vfs_urn = responses.request_data["urn"]
    if vfs_urn not in self.state.store:
      return

    # Failed to read the file - ignore it.
    if not responses.success:
      return self.RemoveInFlightFile(vfs_urn)

    response = responses.First()
    file_tracker = self.state.store[vfs_urn]
    file_tracker.fd.AddBlob(response.data, response.length)

    if response.offset + response.length >= file_tracker.file_size:
      # File done, remove from the store and close it.
      self.RemoveInFlightFile(vfs_urn)

      # Close and write the file to the data store.
      file_tracker.fd.Close(sync=False)

      # Publish the new file event to cause the file to be added to the
      # filestore.
      self.Publish("FileStore.AddFileToStore", vfs_urn)

      self.state.files_fetched += 1

      if not self.state.files_fetched % 100:
        self.Log("Fetched %d of %d files.", self.state.files_fetched,
                 self.state.files_to_fetch)

  def RemoveInFlightFile(self, vfs_urn):
    del self.state.store[vfs_urn]

    # Only find more files if we have few files in flight.
    if (self.args.findspec.iterator.state != rdfvalue.Iterator.State.FINISHED
        and len(self.state.store) < self.MAX_FILES_IN_FLIGHT):
      self.CallClient("Find", self.args.findspec, next_state="IterateFind")

  @flow.StateHandler(next_state=["CheckHash", "WriteBuffer"])
  def End(self):
    # There are some files still in flight.
    if self.state.store or self.state.pending_urns:
      self.CheckHashesWithFileStore()

      for file_tracker in self.state.store.values():
        self.FetchFileContent(file_tracker)

    else:
      return super(FetchAllFiles, self).End()


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
