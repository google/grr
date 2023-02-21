#!/usr/bin/env python
"""These flows are designed for high performance transfers."""
import logging
import stat
from typing import Any
from typing import Mapping
from typing import Optional
from typing import Sequence
import zlib

from grr_response_core.lib import constants
from grr_response_core.lib import rdfvalue
from grr_response_core.lib.rdfvalues import client as rdf_client
from grr_response_core.lib.rdfvalues import client_action as rdf_client_action
from grr_response_core.lib.rdfvalues import client_fs as rdf_client_fs
from grr_response_core.lib.rdfvalues import crypto as rdf_crypto
from grr_response_core.lib.rdfvalues import paths as rdf_paths
from grr_response_core.lib.rdfvalues import protodict as rdf_protodict
from grr_response_core.lib.rdfvalues import structs as rdf_structs
from grr_response_core.lib.util import text
from grr_response_proto import flows_pb2
from grr_response_server import data_store
from grr_response_server import file_store
from grr_response_server import flow_base
from grr_response_server import message_handlers
from grr_response_server import notification
from grr_response_server import server_stubs
from grr_response_server.databases import db
from grr_response_server.rdfvalues import flow_objects as rdf_flow_objects
from grr_response_server.rdfvalues import objects as rdf_objects


class GetFileArgs(rdf_structs.RDFProtoStruct):
  protobuf = flows_pb2.GetFileArgs
  rdf_deps = [
      rdf_paths.PathSpec,
  ]


class GetFile(flow_base.FlowBase):
  """An efficient file transfer mechanism (deprecated, use MultiGetFile).

  This flow is deprecated in favor of MultiGetFile, but kept for now for use by
  MemoryCollector since the buffer hashing performed by MultiGetFile is
  pointless for memory acquisition.

  GetFile can also retrieve content from device files that report a size of 0 in
  stat when read_length is specified.

  Returns to parent flow:
    A PathSpec.
  """

  category = "/Filesystem/"

  args_type = GetFileArgs

  # We have a maximum of this many chunk reads outstanding (about 10mb)
  WINDOW_SIZE = 200
  CHUNK_SIZE = 512 * 1024

  @classmethod
  def GetDefaultArgs(cls, username=None):
    del username
    result = cls.args_type()
    result.pathspec.pathtype = "OS"

    return result

  def Start(self):
    """Get information about the file from the client."""
    self.state.max_chunk_number = max(2,
                                      self.args.read_length // self.CHUNK_SIZE)

    self.state.current_chunk_number = 0
    self.state.file_size = 0
    self.state.blobs = []
    self.state.stat_entry = None
    self.state.num_bytes_collected = 0
    self.state.target_pathspec = self.args.pathspec.Copy()

    # TODO(hanuszczak): Support for old clients ends on 2021-01-01.
    # This conditional should be removed after that date.
    if not self.client_version or self.client_version >= 3221:
      stub = server_stubs.GetFileStat
      request = rdf_client_action.GetFileStatRequest(
          pathspec=self.state.target_pathspec, follow_symlink=True)
    else:
      stub = server_stubs.StatFile
      request = rdf_client_action.ListDirRequest(
          pathspec=self.state.target_pathspec)

    self.CallClient(stub, request, next_state=self.Stat.__name__)

  def Stat(self, responses):
    """Fix up the pathspec of the file."""
    response = responses.First()

    file_size_known = True
    if responses.success and response:
      if stat.S_ISDIR(int(response.st_mode)):
        raise ValueError("`GetFile` called on a directory")

      if not stat.S_ISREG(int(response.st_mode)) and response.st_size == 0:
        file_size_known = False

      self.state.stat_entry = response
    else:
      if not self.args.ignore_stat_failure:
        raise IOError("Error: %s" % responses.status)

      # Just fill up a bogus stat entry.
      self.state.stat_entry = rdf_client_fs.StatEntry(
          pathspec=self.state.target_pathspec)
      file_size_known = False

    # File size is not known, so we have to use user-provided read_length
    # or pathspec.file_size_override to limit the amount of bytes we're
    # going to try to read.
    if not file_size_known:
      if not self.state.target_pathspec.HasField(
          "file_size_override") and not self.args.read_length:
        raise ValueError("The file couldn't be stat-ed. Its size is not known."
                         " Either read_length or pathspec.file_size_override"
                         " has to be provided.")

      # This is not a regular file and the size is 0. Let's use read_length or
      # file_size_override as a best guess for the file size.
      if self.args.read_length == 0:
        self.state.stat_entry.st_size = self.state.target_pathspec.file_size_override
      else:
        self.state.stat_entry.st_size = (
            self.state.target_pathspec.offset + self.args.read_length)

    # Adjust the size from st_size if read length is not specified.
    if self.args.read_length == 0:
      self.state.file_size = max(
          0,
          self.state.stat_entry.st_size - self.state.stat_entry.pathspec.offset)
    else:
      self.state.file_size = self.args.read_length
      if not self.state.target_pathspec.HasField("file_size_override"):
        self.state.target_pathspec.file_size_override = (
            self.state.target_pathspec.offset + self.args.read_length)

    self.state.max_chunk_number = (self.state.file_size // self.CHUNK_SIZE) + 1

    self.FetchWindow(
        min(self.WINDOW_SIZE,
            self.state.max_chunk_number - self.state["current_chunk_number"]))

  def FetchWindow(self, number_of_chunks_to_readahead):
    """Read ahead a number of buffers to fill the window."""
    for _ in range(number_of_chunks_to_readahead):

      # Do not read past the end of file
      next_offset = self.state.current_chunk_number * self.CHUNK_SIZE
      if next_offset >= self.state.file_size:
        return

      request = rdf_client.BufferReference(
          pathspec=self.state.target_pathspec,
          offset=next_offset,
          length=min(self.state.file_size - next_offset, self.CHUNK_SIZE))
      self.CallClient(
          server_stubs.TransferBuffer,
          request,
          next_state=self.ReadBuffer.__name__)
      self.state.current_chunk_number += 1

  def _AddFileToFileStore(self):
    stat_entry = self.state.stat_entry
    path_info = rdf_objects.PathInfo.FromStatEntry(stat_entry)

    blob_refs = []
    offset = 0
    for data, size in self.state.blobs:
      blob_refs.append(
          rdf_objects.BlobReference(
              offset=offset,
              size=size,
              blob_id=rdf_objects.BlobID.FromSerializedBytes(data)))
      offset += size

    client_path = db.ClientPath.FromPathInfo(self.client_id, path_info)
    hash_id = file_store.AddFileWithUnknownHash(client_path, blob_refs)

    path_info.hash_entry.sha256 = hash_id.AsBytes()
    path_info.hash_entry.num_bytes = offset

    data_store.REL_DB.WritePathInfos(self.client_id, [path_info])

    # Save some space.
    del self.state["blobs"]

  def ReadBuffer(self, responses):
    """Read the buffer and write to the file."""
    # Did it work?
    if not responses.success:
      return

    response = responses.First()
    if not response:
      raise IOError("Missing hash for offset %s missing" % response.offset)

    self.state.num_bytes_collected += response.length

    if response.offset <= self.state.max_chunk_number * self.CHUNK_SIZE:
      # Response.data is the hash of the block (32 bytes) and
      # response.length is the length of the block.
      self.state.blobs.append((response.data, response.length))

      self.Log("Received blob hash %s", text.Hexify(response.data))

      # Add one more chunk to the window.
      self.FetchWindow(1)

  def NotifyAboutEnd(self):
    super().NotifyAboutEnd()

    stat_entry = self.state.stat_entry
    if not stat_entry:
      stat_entry = rdf_client_fs.StatEntry(pathspec=self.state.target_pathspec)

    urn = stat_entry.AFF4Path(self.client_urn)
    components = urn.Split()
    file_ref = None
    if len(components) > 3:
      file_ref = rdf_objects.VfsFileReference(
          client_id=components[0],
          path_type=components[2].upper(),
          path_components=components[3:])

    if self.state.num_bytes_collected >= self.state.file_size:
      notification.Notify(
          self.creator,
          rdf_objects.UserNotification.Type.TYPE_VFS_FILE_COLLECTED,
          "File transferred successfully.",
          rdf_objects.ObjectReference(
              reference_type=rdf_objects.ObjectReference.Type.VFS_FILE,
              vfs_file=file_ref))
    elif self.state.num_bytes_collected > 0:
      notification.Notify(
          self.creator,
          rdf_objects.UserNotification.Type.TYPE_VFS_FILE_COLLECTED,
          "File transferred partially (%d bytes out of %d)." %
          (self.state.num_bytes_collected, self.state.file_size),
          rdf_objects.ObjectReference(
              reference_type=rdf_objects.ObjectReference.Type.VFS_FILE,
              vfs_file=file_ref))
    else:
      notification.Notify(
          self.creator,
          rdf_objects.UserNotification.Type.TYPE_VFS_FILE_COLLECTION_FAILED,
          "File transfer failed.",
          rdf_objects.ObjectReference(
              reference_type=rdf_objects.ObjectReference.Type.VFS_FILE,
              vfs_file=file_ref))

  def End(self, responses):
    """Finalize reading the file."""
    if self.state.num_bytes_collected >= 0:
      self._AddFileToFileStore()

      stat_entry = self.state.stat_entry
      if self.state.num_bytes_collected >= self.state.file_size:
        self.Log("File %s transferred successfully.",
                 stat_entry.AFF4Path(self.client_urn))
      else:
        self.Log("File %s transferred partially (%d bytes out of %d).",
                 stat_entry.AFF4Path(self.client_urn),
                 self.state.num_bytes_collected, self.state.file_size)

      # Notify any parent flows the file is ready to be used now.
      self.SendReply(stat_entry)
    else:
      self.Log("File transfer failed.")

    super().End(responses)


# TODO: Improve typing and testing situation.
class MultiGetFileLogic(object):
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

  def Start(self,
            file_size=0,
            maximum_pending_files=1000,
            use_external_stores=False):
    """Initialize our state."""
    super().Start()

    self.state.files_hashed = 0
    self.state.use_external_stores = use_external_stores
    self.state.file_size = file_size
    self.state.files_to_fetch = 0
    self.state.files_fetched = 0
    self.state.files_skipped = 0
    self.state.files_failed = 0

    # Controls how far to go on the collection: stat, hash and collect contents.
    # By default we go through the whole process (collecting file contents), but
    # we can stop when we finish getting the stat or hash.
    self.state.stop_at_stat = False
    self.state.stop_at_hash = False

    # Counter to batch up hash checking in the filestore
    self.state.files_hashed_since_check = 0

    # A dict of file trackers which are waiting to be stat'd.
    # Keys are vfs urns and values are FileTrack instances.  Values are
    # copied to pending_hashes for download if not present in FileStore.
    self.state.pending_stats: Mapping[int, Mapping[str, Any]] = {}

    # A dict of file trackers which are waiting to be checked by the file
    # store.  Keys are vfs urns and values are FileTrack instances.  Values are
    # copied to pending_files for download if not present in FileStore.
    self.state.pending_hashes = {}

    # A dict of file trackers currently being fetched. Keys are vfs urns and
    # values are FileTracker instances.
    self.state.pending_files = {}

    # The maximum number of files we are allowed to download concurrently.
    self.state.maximum_pending_files = maximum_pending_files

    # As pathspecs are added to the flow they are appended to this array. We
    # then simply pass their index in this array as a surrogate for the full
    # pathspec. This allows us to use integers to track pathspecs in dicts etc.
    self.state.indexed_pathspecs = []
    self.state.request_data_list = []

    # The index of the next pathspec to start. Pathspecs are added to
    # indexed_pathspecs and wait there until there are free trackers for
    # them. When the number of pending_files falls below the
    # "maximum_pending_files" count] = we increment this index and start of
    # downloading another pathspec.
    self.state.next_pathspec_to_start = 0

    # Number of blob hashes we have received but not yet scheduled for download.
    self.state.blob_hashes_pending = 0

  def StartFileFetch(self, pathspec, request_data=None):
    """The entry point for this flow mixin - Schedules new file transfer."""
    # Create an index so we can find this pathspec later.
    self.state.indexed_pathspecs.append(pathspec)
    self.state.request_data_list.append(request_data)
    self._TryToStartNextPathspec()

  def _TryToStartNextPathspec(self):
    """Try to schedule the next pathspec if there is enough capacity."""

    # If there's no capacity, there's nothing to do here.
    if not self._HasEnoughCapacity():
      return

    try:
      index = self.state.next_pathspec_to_start
      pathspec = self.state.indexed_pathspecs[index]
      self.state.next_pathspec_to_start = index + 1
    except IndexError:
      # We did all the pathspecs, nothing left to do here.
      return

    # First stat the file, then hash the file if needed.
    self._ScheduleStatFile(index, pathspec)
    if getattr(self.state, "stop_at_stat", False):
      return

    self._ScheduleHashFile(index, pathspec)

  def _HasEnoughCapacity(self) -> bool:
    """Checks whether there is enough capacity to schedule next pathspec."""

    if self.state.maximum_pending_files <= len(self.state.pending_files):
      return False

    if self.state.maximum_pending_files <= len(self.state.pending_hashes):
      return False

    if self.state.maximum_pending_files <= len(self.state.pending_stats):
      return False

    return True

  def _ScheduleStatFile(self, index: int, pathspec: rdf_paths.PathSpec) -> None:
    """Schedules the appropriate Stat File Client Action.

    Args:
      index: Index of the current file to get Stat for.
      pathspec: Pathspec of the current file to get Stat for.
    """

    # Add the file tracker to the pending stats list where it waits until the
    # stat comes back.
    self.state.pending_stats[index] = {"index": index}

    # TODO(hanuszczak): Support for old clients ends on 2021-01-01.
    # This conditional should be removed after that date.
    if not self.client_version or self.client_version >= 3221:
      stub = server_stubs.GetFileStat
      request = rdf_client_action.GetFileStatRequest(pathspec=pathspec)
      request.follow_symlink = True
      request_name = "GetFileStat"
    else:
      stub = server_stubs.StatFile
      request = rdf_client_action.ListDirRequest(pathspec=pathspec)
      request_name = "StatFile"

    self.CallClient(
        stub,
        request,
        next_state=self._ReceiveFileStat.__name__,
        request_data=dict(index=index, request_name=request_name))

  def _ScheduleHashFile(self, index: int, pathspec: rdf_paths.PathSpec) -> None:
    """Schedules the HashFile Client Action.

    Args:
      index: Index of the current file to be hashed.
      pathspec: Pathspec of the current file to be hashed.
    """

    # Add the file tracker to the pending hashes list where it waits until the
    # hash comes back.
    self.state.pending_hashes[index] = {"index": index}

    request = rdf_client_action.FingerprintRequest(
        pathspec=pathspec, max_filesize=self.state.file_size)
    request.AddRequest(
        fp_type=rdf_client_action.FingerprintTuple.Type.FPT_GENERIC,
        hashers=[
            rdf_client_action.FingerprintTuple.HashType.MD5,
            rdf_client_action.FingerprintTuple.HashType.SHA1,
            rdf_client_action.FingerprintTuple.HashType.SHA256
        ])

    self.CallClient(
        server_stubs.HashFile,
        request,
        next_state=self._ReceiveFileHash.__name__,
        request_data=dict(index=index))

  def _RemoveCompletedPathspec(self, index):
    """Removes a pathspec from the list of pathspecs."""
    pathspec = self.state.indexed_pathspecs[index]
    request_data = self.state.request_data_list[index]

    self.state.indexed_pathspecs[index] = None
    self.state.request_data_list[index] = None
    self.state.pending_stats.pop(index, None)
    self.state.pending_hashes.pop(index, None)
    self.state.pending_files.pop(index, None)

    # We have a bit more room in the pending_hashes so we try to schedule
    # another pathspec.
    self._TryToStartNextPathspec()
    return pathspec, request_data

  def _ReceiveFetchedFile(self, tracker, is_duplicate=False):
    """Remove pathspec for this index and call the ReceiveFetchedFile method."""
    index = tracker["index"]

    _, request_data = self._RemoveCompletedPathspec(index)

    # Report the request_data for this flow's caller.
    self.ReceiveFetchedFile(
        tracker["stat_entry"],
        tracker["hash_obj"],
        request_data=request_data,
        is_duplicate=is_duplicate)

  def ReceiveFetchedFile(self,
                         stat_entry,
                         file_hash,
                         request_data=None,
                         is_duplicate=False):
    """This method will be called for each new file successfully fetched.

    Args:
      stat_entry: rdf_client_fs.StatEntry object describing the file.
      file_hash: rdf_crypto.Hash object with file hashes.
      request_data: Arbitrary dictionary that was passed to the corresponding
        StartFileFetch call.
      is_duplicate: If True, the file wasn't actually collected as its hash was
        found in the filestore.
    """

  def _FileFetchFailed(self, index: int,
                       status: Optional[rdf_flow_objects.FlowStatus]):
    """Remove pathspec for this index and call the FileFetchFailed method."""

    pathspec, request_data = self._RemoveCompletedPathspec(index)
    if pathspec is None:
      # This was already reported as failed.
      return

    self.state.files_failed += 1

    # Report the request_data for this flow's caller.
    self.FileFetchFailed(pathspec, request_data=request_data, status=status)

  def FileFetchFailed(self,
                      pathspec: rdf_paths.PathSpec,
                      request_data: Any = None,
                      status: Optional[rdf_flow_objects.FlowStatus] = None):
    """This method will be called when stat or hash requests fail.

    Args:
      pathspec: Pathspec of a file that failed to be fetched.
      request_data: Arbitrary dictionary that was passed to the corresponding
        StartFileFetch call.
      status: FlowStatus that contains more error details.
    """

  def _ReceiveFileStat(self, responses):
    """Stores stat entry in the flow's state."""

    index = responses.request_data["index"]
    if not responses.success:
      self.Log("Failed to stat file: %s", responses.status)
      self.state.pending_stats.pop(index, None)
      # Report failure.
      self._FileFetchFailed(index, status=responses.status)
      return

    stat_entry = responses.First()

    # This stat is no longer pending, so we free the tracker.
    self.state.pending_stats.pop(index, None)

    request_data = self.state.request_data_list[index]
    self.ReceiveFetchedFileStat(stat_entry, request_data)

    if getattr(self.state, "stop_at_stat", False):
      self._RemoveCompletedPathspec(index)
      return

    # Propagate stat information to hash queue (same index is used across).
    hash_tracker = self.state.pending_hashes[index]
    hash_tracker["stat_entry"] = stat_entry

  def ReceiveFetchedFileStat(
      self,
      stat_entry: rdf_client_fs.StatEntry,
      request_data: Optional[Mapping[str, Any]] = None) -> None:
    """This method will be called for each new file stat successfully fetched.

    Args:
      stat_entry: rdf_client_fs.StatEntry object describing the file.
      request_data: Arbitrary dictionary that was passed to the corresponding
        StartFileFetch call.
    """
    pass

  def _ReceiveFileHash(self, responses):
    """Add hash digest to tracker and check with filestore."""

    index = responses.request_data["index"]
    if not responses.success:
      self.Log("Failed to hash file: %s", responses.status)
      self.state.pending_hashes.pop(index, None)
      # Report the error.
      self._FileFetchFailed(index, status=responses.status)
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
      # Hashing the file failed, but we did stat it.
      self._FileFetchFailed(index, status=responses.status)
      return

    tracker["hash_obj"] = hash_obj
    tracker["bytes_read"] = response.bytes_read

    stat_entry = tracker["stat_entry"]
    request_data = self.state.request_data_list[index]
    self.ReceiveFetchedFileHash(stat_entry, hash_obj, request_data)

    if getattr(self.state, "stop_at_hash", False):
      self._RemoveCompletedPathspec(index)
      return

    self.state.files_hashed_since_check += 1
    if self.state.files_hashed_since_check >= self.MIN_CALL_TO_FILE_STORE:
      self._CheckHashesWithFileStore()

  def ReceiveFetchedFileHash(
      self,
      stat_entry: rdf_client_fs.StatEntry,
      file_hash: rdf_crypto.Hash,
      request_data: Optional[Mapping[str, Any]] = None) -> None:
    """This method will be called for each new file hash successfully fetched.

    Args:
      stat_entry: rdf_client_fs.StatEntry object describing the file.
      file_hash: rdf_crypto.Hash object with file hashes.
      request_data: Arbitrary dictionary that was passed to the corresponding
        StartFileFetch call.
    """
    pass

  def _CheckHashesWithFileStore(self):
    """Check all queued up hashes for existence in file store.

    Hashes which do not exist in the file store will be downloaded. This
    function flushes the entire queue (self.state.pending_hashes) in order to
    minimize the round trips to the file store.

    If a file was found in the file store it is not scheduled for collection
    and its PathInfo is written to the datastore pointing to the file store's
    hash. Otherwise, we request the client to hash every block in the file,
    and add it to the file tracking queue (self.state.pending_files).
    """
    if not self.state.pending_hashes:
      return

    # This map represents all the hashes in the pending urns.
    file_hashes = {}

    # Store a mapping of hash to tracker. Keys are hashdigest objects,
    # values are arrays of tracker dicts.
    hash_to_tracker = {}
    for index, tracker in self.state.pending_hashes.items():
      # We might not have gotten this hash yet
      if tracker.get("hash_obj") is None:
        continue

      hash_obj = tracker["hash_obj"]
      digest = hash_obj.sha256
      file_hashes[index] = hash_obj
      hash_to_tracker.setdefault(rdf_objects.SHA256HashID(digest),
                                 []).append(tracker)

    # First we get all the files which are present in the file store.
    files_in_filestore = set()

    statuses = file_store.CheckHashes([
        rdf_objects.SHA256HashID.FromSerializedBytes(ho.sha256.AsBytes())
        for ho in file_hashes.values()
    ])
    for hash_id, status in statuses.items():
      self.HeartBeat()

      if not status:
        continue

      # Since checkhashes only returns one digest per unique hash we need to
      # find any other files pending download with the same hash.
      for tracker in hash_to_tracker[hash_id]:
        self.state.files_skipped += 1
        file_hashes.pop(tracker["index"])
        files_in_filestore.add(hash_id)
        # Remove this tracker from the pending_hashes store since we no longer
        # need to process it.
        self.state.pending_hashes.pop(tracker["index"])

    # Now that the check is done, reset our counter
    self.state.files_hashed_since_check = 0
    # Now copy all existing files to the client aff4 space.
    for hash_id in files_in_filestore:

      for file_tracker in hash_to_tracker.get(hash_id, []):
        stat_entry = file_tracker["stat_entry"]
        path_info = rdf_objects.PathInfo.FromStatEntry(stat_entry)
        path_info.hash_entry = file_tracker["hash_obj"]
        data_store.REL_DB.WritePathInfos(self.client_id, [path_info])

        # Report this hit to the flow's caller.
        self._ReceiveFetchedFile(file_tracker, is_duplicate=True)

    # Now we iterate over all the files which are not in the store and arrange
    # for them to be copied.
    for index in file_hashes:

      # Move the tracker from the pending hashes store to the pending files
      # store - it will now be downloaded.
      file_tracker = self.state.pending_hashes.pop(index)
      self.state.pending_files[index] = file_tracker

      # If we already know how big the file is we use that, otherwise fall back
      # to the size reported by stat.
      if file_tracker["bytes_read"] > 0:
        file_tracker["size_to_download"] = file_tracker["bytes_read"]
      else:
        file_tracker["size_to_download"] = file_tracker["stat_entry"].st_size

      # We do not have the file here yet - we need to retrieve it.
      expected_number_of_hashes = file_tracker["expected_chunks"] = (
          file_tracker["size_to_download"] // self.CHUNK_SIZE + 1)

      # We just hash ALL the chunks in the file now. NOTE: This maximizes client
      # VFS cache hit rate and is far more efficient than launching multiple
      # GetFile flows.
      self.state.files_to_fetch += 1

      for i in range(expected_number_of_hashes):
        if i == expected_number_of_hashes - 1:
          # The last chunk is short.
          length = file_tracker["size_to_download"] % self.CHUNK_SIZE
        else:
          length = self.CHUNK_SIZE

        self.CallClient(
            server_stubs.HashBuffer,
            pathspec=file_tracker["stat_entry"].pathspec,
            offset=i * self.CHUNK_SIZE,
            length=length,
            next_state=self._CheckHash.__name__,
            request_data=dict(index=index))

    if self.state.files_hashed % 100 == 0:
      self.Log("Hashed %d files, skipped %s already stored.",
               self.state.files_hashed, self.state.files_skipped)

  def _CheckHash(self, responses):
    """Adds the block hash to the file tracker responsible for this vfs URN."""
    index = responses.request_data["index"]

    if index not in self.state.pending_files:
      # This is a blobhash for a file we already failed to read and logged as
      # below, check here to avoid logging dups.
      return

    file_tracker = self.state.pending_files[index]

    hash_response = responses.First()
    if not responses.success or not hash_response:
      urn = file_tracker["stat_entry"].pathspec.AFF4Path(self.client_urn)
      self.Log("Failed to read %s: %s", urn, responses.status)
      self._FileFetchFailed(index, status=responses.status)
      return

    file_tracker.setdefault("hash_list", []).append(hash_response)

    self.state.blob_hashes_pending += 1

    if self.state.blob_hashes_pending > self.MIN_CALL_TO_FILE_STORE:
      self._FetchFileContent()

  def _FetchFileContent(self):
    """Fetch as much as the file's content as possible.

    This drains the pending_files store by checking which blobs we already have
    in the store and issuing calls to the client to receive outstanding blobs.
    """
    if not self.state.pending_files:
      return

    # Check what blobs we already have in the blob store.
    blob_hashes = []
    for file_tracker in self.state.pending_files.values():
      for hash_response in file_tracker.get("hash_list", []):
        blob_hashes.append(
            rdf_objects.BlobID.FromSerializedBytes(hash_response.data))

    # This is effectively a BlobStore call.
    existing_blobs = data_store.BLOBS.CheckBlobsExist(blob_hashes)

    self.state.blob_hashes_pending = 0

    # If we encounter hashes that we already have, we will update
    # self.state.pending_files right away.
    for index, file_tracker in list(self.state.pending_files.items()):
      for i, hash_response in enumerate(file_tracker.get("hash_list", [])):
        # Make sure we read the correct pathspec on the client.
        hash_response.pathspec = file_tracker["stat_entry"].pathspec

        if existing_blobs[rdf_objects.BlobID.FromSerializedBytes(
            hash_response.data)]:
          # If we have the data we may call our state directly.
          self.CallStateInline(
              messages=[hash_response],
              next_state=self._WriteBuffer.__name__,
              request_data=dict(index=index, blob_index=i))
        else:
          # We dont have this blob - ask the client to transmit it.
          self.CallClient(
              server_stubs.TransferBuffer,
              hash_response,
              next_state=self._WriteBuffer.__name__,
              request_data=dict(index=index, blob_index=i))

  def _WriteBuffer(self, responses):
    """Write the hash received to the blob image."""

    index = responses.request_data["index"]
    if index not in self.state.pending_files:
      return

    # Failed to read the file - ignore it.
    if not responses.success:
      self._FileFetchFailed(index, status=responses.status)
      return

    response = responses.First()
    file_tracker = self.state.pending_files.get(index)
    if not file_tracker:
      return

    blob_dict = file_tracker.setdefault("blobs", {})
    blob_index = responses.request_data["blob_index"]
    blob_dict[blob_index] = (response.data, response.length)

    if len(blob_dict) != file_tracker["expected_chunks"]:
      # We need more data before we can write the file.
      return

    # Write the file to the data store.
    stat_entry = file_tracker["stat_entry"]

    path_info = rdf_objects.PathInfo.FromStatEntry(stat_entry)

    blob_refs = []
    offset = 0
    for index in sorted(blob_dict):
      digest, size = blob_dict[index]
      blob_refs.append(
          rdf_objects.BlobReference(
              offset=offset,
              size=size,
              blob_id=rdf_objects.BlobID.FromSerializedBytes(digest)))
      offset += size

    hash_obj = file_tracker["hash_obj"]

    client_path = db.ClientPath.FromPathInfo(self.client_id, path_info)
    hash_id = file_store.AddFileWithUnknownHash(
        client_path,
        blob_refs,
        use_external_stores=self.state.use_external_stores)
    # If the hash that we've calculated matches what we got from the
    # client, then simply store the full hash entry.
    # Otherwise store just the hash that we've calculated.
    if hash_id.AsBytes() == hash_obj.sha256:
      path_info.hash_entry = hash_obj
    else:
      path_info.hash_entry.sha256 = hash_id.AsBytes()
      path_info.hash_entry.num_bytes = offset

    data_store.REL_DB.WritePathInfos(self.client_id, [path_info])

    # Save some space.
    del file_tracker["blobs"]
    del file_tracker["hash_list"]

    # File done, remove from the store and close it.
    self._ReceiveFetchedFile(file_tracker)

    self.state.files_fetched += 1

    if not self.state.files_fetched % 100:
      self.Log("Fetched %d of %d files.", self.state.files_fetched,
               self.state.files_to_fetch)

  def End(self, responses):
    # There are some files still in flight.
    if self.state.pending_hashes or self.state.pending_files:
      self._CheckHashesWithFileStore()
      self._FetchFileContent()

    if not self.outstanding_requests:
      super().End(responses)


class MultiGetFileArgs(rdf_structs.RDFProtoStruct):
  protobuf = flows_pb2.MultiGetFileArgs
  rdf_deps = [
      rdfvalue.ByteSize,
      rdf_paths.PathSpec,
  ]


class PathSpecProgress(rdf_structs.RDFProtoStruct):
  protobuf = flows_pb2.PathSpecProgress
  rdf_deps = [
      rdf_paths.PathSpec,
  ]


class MultiGetFileProgress(rdf_structs.RDFProtoStruct):
  protobuf = flows_pb2.MultiGetFileProgress
  rdf_deps = [
      PathSpecProgress,
  ]


class MultiGetFile(MultiGetFileLogic, flow_base.FlowBase):
  """A flow to effectively retrieve a number of files."""

  args_type = MultiGetFileArgs
  progress_type = MultiGetFileProgress
  result_types = (rdf_client_fs.StatEntry,)

  def GetProgress(self) -> MultiGetFileProgress:
    return MultiGetFileProgress(
        num_pending_hashes=len(self.state.pending_hashes),
        num_pending_files=len(self.state.pending_files),
        num_skipped=self.state.files_skipped,
        num_collected=self.state.files_fetched,
        num_failed=self.state.files_failed,
        pathspecs_progress=self.state.pathspecs_progress)

  def Start(self):
    """Start state of the flow."""
    super().Start(
        file_size=self.args.file_size,
        maximum_pending_files=self.args.maximum_pending_files,
        use_external_stores=self.args.use_external_stores)

    unique_paths = set()

    self.state.pathspecs_progress = [
        PathSpecProgress(
            pathspec=p, status=PathSpecProgress.Status.IN_PROGRESS)
        for p in self.args.pathspecs
    ]

    for i, pathspec in enumerate(self.args.pathspecs):
      vfs_urn = pathspec.AFF4Path(self.client_urn)

      if vfs_urn not in unique_paths:
        # Only Stat/Hash each path once, input pathspecs can have dups.
        unique_paths.add(vfs_urn)

        self.StartFileFetch(pathspec, request_data=i)

  def ReceiveFetchedFile(self,
                         stat_entry,
                         unused_hash_obj,
                         request_data=None,
                         is_duplicate=False):
    """This method will be called for each new file successfully fetched."""
    if is_duplicate:
      status = PathSpecProgress.Status.SKIPPED
    else:
      status = PathSpecProgress.Status.COLLECTED
    self.state.pathspecs_progress[request_data].status = status

    self.SendReply(stat_entry)

  def FileFetchFailed(self, pathspec, request_data=None, status=None):
    """This method will be called when stat or hash requests fail."""
    self.state.pathspecs_progress[
        request_data].status = PathSpecProgress.Status.FAILED


class GetMBRArgs(rdf_structs.RDFProtoStruct):
  protobuf = flows_pb2.GetMBRArgs


class GetMBR(flow_base.FlowBase):
  """A flow to retrieve the MBR.

  Returns to parent flow:
    The retrieved MBR.
  """

  category = "/Filesystem/"
  args_type = GetMBRArgs
  behaviours = flow_base.BEHAVIOUR_BASIC

  def Start(self):
    """Schedules the ReadBuffer client action."""
    pathspec = rdf_paths.PathSpec(
        path="\\\\.\\PhysicalDrive0\\",
        pathtype=rdf_paths.PathSpec.PathType.OS,
        path_options=rdf_paths.PathSpec.Options.CASE_LITERAL)

    self.state.bytes_downloaded = 0
    # An array to collect buffers. This is not very efficient, MBR
    # data should be kept short though so this is not a big deal.
    self.state.buffers = []

    buffer_size = constants.CLIENT_MAX_BUFFER_SIZE
    buffers_we_need = self.args.length // buffer_size
    if self.args.length % buffer_size:
      buffers_we_need += 1

    bytes_we_need = self.args.length

    for i in range(buffers_we_need):
      request = rdf_client.BufferReference(
          pathspec=pathspec,
          offset=i * buffer_size,
          length=min(bytes_we_need, buffer_size))
      self.CallClient(
          server_stubs.ReadBuffer, request, next_state=self.StoreMBR.__name__)
      bytes_we_need -= buffer_size

  def StoreMBR(self, responses):
    """This method stores the MBR."""

    if not responses.success:
      msg = "Could not retrieve MBR: %s" % responses.status
      self.Log(msg)
      raise flow_base.FlowError(msg)

    response = responses.First()

    self.state.buffers.append(response.data)
    self.state.bytes_downloaded += len(response.data)

    if self.state.bytes_downloaded >= self.args.length:
      mbr_data = b"".join(self.state.buffers)
      self.state.buffers = None

      self.Log("Successfully collected the MBR (%d bytes)." % len(mbr_data))
      self.SendReply(rdfvalue.RDFBytes(mbr_data))


class BlobHandler(message_handlers.MessageHandler):
  """Message handler to store blobs."""

  handler_name = "BlobHandler"

  def ProcessMessages(
      self,
      msgs: Sequence[rdf_objects.MessageHandlerRequest],
  ) -> None:
    blobs = []
    for msg in msgs:
      blob = msg.request.payload

      data = blob.data
      logging.info("Received of length %s from '%s'", len(data), msg.client_id)

      if not data:
        continue

      ct = rdf_protodict.DataBlob.CompressionType
      if blob.compression == ct.ZCOMPRESSION:
        data = zlib.decompress(data)
      elif blob.compression == ct.UNCOMPRESSED:
        pass
      else:
        raise ValueError("Unsupported compression")

      blobs.append(data)

    data_store.BLOBS.WriteBlobsWithUnknownHashes(blobs)


class SendFile(flow_base.FlowBase):
  """This flow sends a file to remote listener.

  To use this flow, choose a key and an IV in hex format (if run from the GUI,
  there will be a pregenerated pair key and iv for you to use) and run a
  listener on the server you want to use like this:

  nc -l <port> | openssl aes-128-cbc -d -K <key> -iv <iv> > <filename>

  Returns to parent flow:
    A rdf_client_fs.StatEntry of the sent file.
  """

  category = "/Filesystem/"
  args_type = rdf_client_action.SendFileRequest

  def Start(self):
    """This issues the sendfile request."""
    self.CallClient(
        server_stubs.SendFile, self.args, next_state=self.Done.__name__)

  def Done(self, responses):
    if not responses.success:
      self.Log(responses.status.error_message)
      raise flow_base.FlowError(responses.status.error_message)
