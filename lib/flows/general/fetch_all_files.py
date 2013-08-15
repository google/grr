#!/usr/bin/env python
"""Find certain types of files, compute hashes, and fetch unknown ones."""



import stat

from grr.parsers import fingerprint
from grr.lib import aff4
from grr.lib import data_store
from grr.lib import flow
from grr.lib import rdfvalue
from grr.lib import type_info
from grr.proto import jobs_pb2


class AuthenticodeSignedData(rdfvalue.RDFProtoStruct):
  protobuf = jobs_pb2.AuthenticodeSignedData


class VFSBlobImage(aff4.BlobImage, aff4.VFSFile):
  class SchemaCls(aff4.BlobImage.SchemaCls, aff4.VFSFile.SchemaCls):
    SIGNED_DATA = aff4.Attribute(
        "aff4:signed_data", AuthenticodeSignedData,
        "Signed data which may be present in PE files.")


class FileStoreImage(aff4.BlobImage):
  """The AFF4 files that are stored in the file store area.

  Files in the file store are essentially blob images, containing indexes to the
  client files which matches their hash.

  It is possible to query for all clients which match a specific hash or a
  regular expression of the aff4 path to the files on these clients.
  """

  class SchemaCls(aff4.BlobImage.SchemaCls):
    # The file store does not need to version file content.
    HASHES = aff4.Attribute("aff4:hashes", rdfvalue.HashList,
                            "List of hashes of each chunk in this file.",
                            versioned=False)

  def AddIndex(self, target):
    """Adds an indexed reference to the target URN."""
    predicate = ("index:target:%s" % target).lower()
    data_store.DB.MultiSet(self.urn, {predicate: target}, token=self.token,
                           replace=True, sync=False)

  def Query(self, target_regex, limit=100):
    """Search the index for matches to the file specified by the regex.

    Args:
       target_regex: The regular expression to match against the index.

       limit: Either a tuple of (start, limit) or a maximum number of results to
         return.

    Yields:
      URNs of files which have the same data as this file - as read from the
      index.
    """
    # Make the regular expression.
    regex = ["index:target:.*%s.*" % target_regex.lower()]
    start = 0
    try:
      start, length = limit
    except TypeError:
      length = limit

    # Get all the unique hits
    for i, (_, hit, _) in enumerate(data_store.DB.ResolveRegex(
        self.urn, regex, token=self.token, limit=limit)):

      if i < start: continue

      if i >= start + length:
        break

      yield rdfvalue.RDFURN(hit)


class HashTracker(object):
  def __init__(self, hash_response, is_known=False):
    self.hash_response = hash_response
    self.is_known = is_known
    self.blob_urn = rdfvalue.RDFURN("aff4:/blobs").Add(
        hash_response.data.encode("hex"))


class FetchAllFiles(flow.GRRFlow):
  """This flow finds files, computes their hashes, and fetches 'new' files.

  The result from this flow is a population of aff4 objects under
  aff4:/fp/(generic|pecoff)/<hashname>/<hashvalue>.
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

  flow_typeinfo = type_info.TypeDescriptorSet(
      type_info.Bool(
          description=("This causes the computation of Authenticode "
                       "hashes, and their use for deduplicating file fetches."),
          name="pecoff",
          default=True),

      type_info.FindSpecType(
          description=("Which files to search for. The default is to search "
                       "the entire system for files with an executable "
                       "extension."),
          name="findspec",
          default=rdfvalue.RDFFindSpec(
              pathspec=rdfvalue.PathSpec(
                  path="/",
                  pathtype=rdfvalue.PathSpec.PathType.OS),
              path_regex=r"\.(exe|com|bat|dll|msi|sys|scr|pif)$")
          ),

      type_info.Integer(
          description=("Files examined per iteration before reporting back to"
                       " the server. Should be large enough to make the"
                       " roundtrip to the server worthwhile."),
          name="iteration_count",
          default=20000),

      )

  @flow.StateHandler(next_state="IterateFind")
  def Start(self):
    """Issue the find request."""
    self.state.Register("files_found", 0)
    self.state.Register("files_hashed", 0)
    self.state.Register("files_to_fetch", 0)
    self.state.Register("files_fetched", 0)

    # A local store for temporary data. Keys are aff4 URNs, values are tuples of
    # (fd, file_size, pathspec, list of hashes).
    self.state.Register("store", {})

    self.state.findspec.iterator.number = self.state.iteration_count
    self.CallClient("Find", self.state.findspec, next_state="IterateFind")

  @flow.StateHandler(next_state=["IterateFind", "CheckFileHash"])
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
                        next_state="CheckFileHash",
                        request_data=dict(hit=response.hit))

    # Hold onto the iterator in the state - we might need to re-iterate this
    # later.
    self.state.findspec.iterator = responses.iterator

    # Only find more files if we have no files in flight.
    if responses.iterator.state != rdfvalue.Iterator.State.FINISHED:
      # Only find more files if we have no files in flight.
      if len(self.state.store) < self.MAX_FILES_IN_FLIGHT:
        self.CallClient("Find", self.state.findspec, next_state="IterateFind")

    else:
      # Done!
      self.Log("Found %d files.", self.state.files_found)

  @flow.StateHandler(next_state="CheckHash")
  def CheckFileHash(self, responses):
    """Check if we already have this file hash."""
    if not responses.success:
      self.Log("Failed to hash file: %s", responses.status)
      return

    self.state.files_hashed += 1

    response = responses.First()
    hit = responses.request_data["hit"]
    file_size = hit.st_size

    # Create the file in the VFS under the client's namespace.
    vfs_urn = aff4.AFF4Object.VFSGRRClient.PathspecToURN(
        hit.pathspec, self.client_id)

    # We create the file in the client namespace and populate with metadata.
    fd = aff4.FACTORY.Create(vfs_urn, "VFSBlobImage", mode="w",
                             token=self.token)
    fd.SetChunksize(self.CHUNK_SIZE)
    fd.Set(fd.Schema.HASH(response.data))
    fd.Set(fd.Schema.STAT(hit))
    fd.Set(fd.Schema.PATHSPEC(hit.pathspec))

    try:
      # The canonical name of the file is where we store the file hash.
      canonical_urn = aff4.ROOT_URN.Add("FP/generic/sha256").Add(
          response.data.encode("hex"))

      # If this works, we already have the file in the file store, so just copy
      # the data contents from it to the client space and move on.
      canonical_fd = aff4.FACTORY.Open(canonical_urn, aff4_type="BlobImage",
                                       mode="r", token=self.token)

      fd.FromBlobImage(canonical_fd)
      fd.Close()

    except IOError:
      # We do not have the file here yet - we need to retrieve it.
      expected_number_of_hashes = file_size / self.CHUNK_SIZE + 1

      # Keep the file handle around and write to it in following states.
      self.state.store[vfs_urn] = [fd, file_size, hit.pathspec, []]

      # We just hash ALL the chunks now.
      self.state.files_to_fetch += 1
      for i in range(expected_number_of_hashes):
        self.CallClient("HashBuffer", pathspec=hit.pathspec,
                        offset=i * self.CHUNK_SIZE,
                        length=self.CHUNK_SIZE, next_state="CheckHash",
                        request_data=dict(urn=vfs_urn))

    if not int(self.state.files_hashed % 100):
      self.Log("Hashed %d files.", self.state.files_hashed)

  @flow.StateHandler(next_state="WriteBuffer")
  def CheckHash(self, responses):
    """Check if we have the hashes in the blob area, fetch data from clients."""
    vfs_urn = responses.request_data["urn"]
    fd, file_size, pathspec, hash_list = self.state.store[vfs_urn]

    hash_response = responses.First()
    if not responses.success or not hash_response:
      self.Log("Failed to read %s: %s" % (fd.urn, responses.status))
      del self.state.store[vfs_urn]
      return

    hash_list.append(HashTracker(hash_response))

    # We wait for all the hashes to be queued in the state, and now we check
    # them all at once to minimize data store round trips.
    if len(hash_list) * self.CHUNK_SIZE >= file_size:
      stats = aff4.FACTORY.Stat(hash_list, token=self.token)
      blobs_we_have = set([x["urn"] for x in stats])
      for hash_tracker in hash_list:
        # Make sure we read the correct pathspec on the client.
        hash_tracker.hash_response.pathspec = pathspec
        if hash_tracker.blob_urn in blobs_we_have:
          # If we have the data we may call our state directly.
          self.CallState(hash_tracker.hash_response,
                         next_state="WriteBuffer", request_data=dict(
                             urn=vfs_urn))
        else:
          self.CallClient("TransferBuffer", hash_tracker.hash_response,
                          next_state="WriteBuffer", request_data=dict(
                              urn=vfs_urn))

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
    fd, file_size, _, _ = self.state.store[vfs_urn]

    fd.AddBlob(response.data, response.length)
    if response.offset + response.length >= file_size:
      # File done, remove from the store and close it.
      self.RemoveInFlightFile(vfs_urn)

      # Close and write the file to the data store.
      fd.Close(sync=False)

      self.Publish("FileStore.AddFileToStore", vfs_urn)

      self.state.files_fetched += 1
      if not self.state.files_fetched % 100:
        self.Log("Fetched %d of %d files.", self.state.files_fetched,
                 self.state.files_to_fetch)

  def RemoveInFlightFile(self, canonical_urn):
    del self.state.store[canonical_urn]

    # Only find more files if we have few files in flight.
    if (self.state.findspec.iterator.state != rdfvalue.Iterator.State.FINISHED
        and len(self.state.store) < self.MAX_FILES_IN_FLIGHT):
      self.CallClient("Find", self.state.findspec, next_state="IterateFind")


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
    vfs_fd = aff4.FACTORY.Open(vfs_urn, mode="rw", token=self.token)

    try:
      # Currently we only handle blob images.
      fingerprinter = fingerprint.Fingerprinter(vfs_fd)
      fingerprinter.EvalGeneric()
      fingerprinter.EvalPecoff()

      for result in fingerprinter.HashIt():
        fingerprint_type = result["name"]
        for hash_type in ["md5", "sha1", "sha256", "SignedData"]:
          if hash_type not in result:
            continue

          if hash_type == "SignedData":
            signed_data = result[hash_type][0]
            vfs_fd.Set(vfs_fd.Schema.SIGNED_DATA(revision=signed_data[0],
                                                 cert_type=signed_data[1],
                                                 certificate=signed_data[2]))
            continue

          if hash_type == "sha256":
            client_side_hash = vfs_fd.Get(vfs_fd.Schema.HASH)
            if client_side_hash != result[hash_type]:
              self.Log("Client side hash for %s does not match server "
                       "side hash" % vfs_urn)

              # Update the hash.
              vfs_fd.Set(vfs_fd.Schema.HASH(result[hash_type]))

          # These files are all created through async write so they should be
          # fast.
          file_store_urn = aff4.ROOT_URN.Add("FP").Add(fingerprint_type).Add(
              hash_type).Add(result[hash_type].encode("hex"))

          file_store_fd = aff4.FACTORY.Create(file_store_urn, "FileStoreImage",
                                              mode="w", token=self.token)
          file_store_fd.FromBlobImage(vfs_fd)
          file_store_fd.AddIndex(vfs_urn)
          file_store_fd.Close(sync=False)
    finally:
      vfs_fd.Close()
