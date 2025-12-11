#!/usr/bin/env python
"""These flows are designed for high performance transfers."""

from collections.abc import MutableSequence, Sequence
import logging
from typing import Optional
import zlib

from google.protobuf import any_pb2
from grr_response_core.lib import constants
from grr_response_core.lib import rdfvalue
from grr_response_core.lib.rdfvalues import client as rdf_client
from grr_response_core.lib.rdfvalues import client_fs as rdf_client_fs
from grr_response_core.lib.rdfvalues import crypto as rdf_crypto
from grr_response_core.lib.rdfvalues import mig_client_fs
from grr_response_core.lib.rdfvalues import mig_crypto
from grr_response_core.lib.rdfvalues import mig_paths
from grr_response_core.lib.rdfvalues import mig_protodict
from grr_response_core.lib.rdfvalues import paths as rdf_paths
from grr_response_core.lib.rdfvalues import protodict as rdf_protodict
from grr_response_core.lib.rdfvalues import structs as rdf_structs
from grr_response_core.stats import metrics
from grr_response_proto import flows_pb2
from grr_response_proto import jobs_pb2
from grr_response_proto import objects_pb2
from grr_response_proto.api import config_pb2
from grr_response_server import data_store
from grr_response_server import file_store
from grr_response_server import flow_base
from grr_response_server import flow_responses
from grr_response_server import message_handlers
from grr_response_server import rrg_fs
from grr_response_server import rrg_stubs
from grr_response_server import server_stubs
from grr_response_server.databases import db
from grr_response_server.flows.general import filesystem
from grr_response_server.models import blobs as models_blobs
from grr_response_server.rdfvalues import mig_objects
from grr_response_server.rdfvalues import objects as rdf_objects
from grr_response_server.rdfvalues import wrappers as rdf_wrappers
from grr_response_proto.rrg import fs_pb2 as rrg_fs_pb2
from grr_response_proto.rrg import os_pb2 as rrg_os_pb2
from grr_response_proto.rrg.action import get_file_contents_pb2 as rrg_get_file_contents_pb2
from grr_response_proto.rrg.action import get_file_metadata_pb2 as rrg_get_file_metadata_pb2
from grr_response_proto.rrg.action import get_file_sha256_pb2 as rrg_get_file_sha256_pb2


_BLOBSTORE_HIT = metrics.Counter(name="multi_get_file_blobstore_hit")
_BLOBSTORE_MISS = metrics.Counter(name="multi_get_file_blobstore_miss")


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


class IndexToBufferReference(rdf_structs.RDFProtoStruct):
  protobuf = flows_pb2.IndexToBufferReference
  rdf_deps = [
      rdf_client.BufferReference,
  ]


class MultiGetFileTracker(rdf_structs.RDFProtoStruct):
  protobuf = flows_pb2.MultiGetFileTracker
  rdf_deps = [
      rdf_client_fs.StatEntry,
      rdf_crypto.Hash,
      rdf_client.BufferReference,
      IndexToBufferReference,
  ]


def _RemoveIndexToTracker(
    index_to_tracker_list: MutableSequence[flows_pb2.IndexToTracker],
    remove_index: int,
):
  for current_index, tracker in enumerate(index_to_tracker_list):
    if tracker.index == remove_index:
      del index_to_tracker_list[current_index]
      break


def _FindIndexToTracker(
    repeated_field: Sequence[flows_pb2.IndexToTracker], find_index: int
) -> Optional[flows_pb2.IndexToTracker]:
  for index_to_tracker in repeated_field:
    if index_to_tracker.index == find_index:
      return index_to_tracker
  return None


def _FindMultiGetFileTracker(
    repeated_field: Sequence[flows_pb2.IndexToTracker], find_index: int
) -> Optional[flows_pb2.MultiGetFileTracker]:
  for index_to_tracker in repeated_field:
    if index_to_tracker.index == find_index:
      return index_to_tracker.tracker
  return None


# TODO: Remove this function once we have migrated to protos.
# This function is duplicated from `mig_transfer` due to circular dependencies.
def ToRDFPathSpecProgress(
    proto: flows_pb2.PathSpecProgress,
) -> PathSpecProgress:
  return PathSpecProgress.FromSerializedBytes(proto.SerializeToString())


# TODO: Remove this function once we have migrated to protos.
# This function is duplicated from `mig_transfer` due to circular dependencies.
def ToRDFMultiGetFileProgress(
    proto: flows_pb2.MultiGetFileProgress,
) -> MultiGetFileProgress:
  return MultiGetFileProgress.FromSerializedBytes(proto.SerializeToString())


class MultiGetFile(
    flow_base.FlowBase[
        flows_pb2.MultiGetFileArgs,
        flows_pb2.MultiGetFileStore,
        flows_pb2.MultiGetFileProgress,
    ]
):
  """A flow to effectively retrieve a number of files."""

  args_type = MultiGetFileArgs
  progress_type = MultiGetFileProgress
  result_types = (rdf_client_fs.StatEntry,)

  proto_args_type = flows_pb2.MultiGetFileArgs
  proto_result_types = (jobs_pb2.StatEntry,)
  proto_progress_type = flows_pb2.MultiGetFileProgress
  proto_store_type = flows_pb2.MultiGetFileStore

  only_protos_allowed = True

  category = "/Filesystem/"
  behaviours = flow_base.BEHAVIOUR_DEBUG

  CHUNK_SIZE = 512 * 1024

  # Batch calls to the filestore to at least to group this many items. This
  # allows us to amortize file store round trips and increases throughput.
  MIN_CALL_TO_FILE_STORE = 200

  def GetProgress(self) -> MultiGetFileProgress:
    return ToRDFMultiGetFileProgress(self.GetProtoProgress())

  def GetProtoProgress(self) -> flows_pb2.MultiGetFileProgress:
    progress = flows_pb2.MultiGetFileProgress()
    if self.store.pending_hashes:
      progress.num_pending_hashes = len(self.store.pending_hashes)
    if self.store.pending_files:
      progress.num_pending_files = len(self.store.pending_files)
    if self.store.num_files_skipped:
      progress.num_skipped = self.store.num_files_skipped
    if self.store.num_files_fetched:
      progress.num_collected = self.store.num_files_fetched
    if self.store.num_files_failed:
      progress.num_failed = self.store.num_files_failed
    if self.store.pathspecs_progress:
      progress.pathspecs_progress.extend(self.store.pathspecs_progress)
    return progress

  def Start(self):
    """Start state of the flow."""

    self.store.num_files_to_fetch = 0
    self.store.num_files_hashed = 0
    self.store.num_files_fetched = 0
    self.store.num_files_skipped = 0
    self.store.num_files_failed = 0

    # Counter to batch up hash checking in the filestore
    self.store.num_files_hashed_since_check = 0

    # A dict of file trackers which are waiting to be stat'd.
    # Keys are vfs urns and values are FileTrack instances.  Values are
    # copied to pending_hashes for download if not present in FileStore.
    self.store.pending_stats: Sequence[flows_pb2.IndexToTracker]

    # A dict of file trackers which are waiting to be checked by the file
    # store.  Keys are vfs urns and values are FileTrack instances.  Values are
    # copied to pending_files for download if not present in FileStore.
    self.store.pending_hashes: Sequence[flows_pb2.IndexToTracker]

    # A dict of file trackers currently being fetched. Keys are vfs urns and
    # values are FileTracker instances.
    self.store.pending_files: Sequence[flows_pb2.IndexToTracker]

    # As pathspecs are added to the flow they are appended to this array. We
    # then simply pass their index in this array as a surrogate for the full
    # pathspec. This allows us to use integers to track pathspecs in dicts etc.
    self.store.indexed_pathspecs: Sequence[jobs_pb2.PathSpec]

    # The index of the next pathspec to start. Pathspecs are added to
    # indexed_pathspecs and wait there until there are free trackers for
    # them. When the number of pending_files falls below the
    # "maximum_pending_files" count] = we increment this index and start of
    # downloading another pathspec.
    self.store.next_pathspec_to_start = 0

    # Number of blob hashes we have received but not yet scheduled for download.
    self.store.blob_hashes_pending = 0

    unique_paths = set()
    # This should be refactored to store one progress per *unique* pathspec.
    self.store.pathspecs_progress.extend([
        flows_pb2.PathSpecProgress(
            pathspec=p, status=PathSpecProgress.Status.IN_PROGRESS
        )
        for p in self.proto_args.pathspecs
    ])

    for pathspec in self.proto_args.pathspecs:
      vfs_urn = mig_paths.ToRDFPathSpec(pathspec).AFF4Path(self.client_urn)

      if vfs_urn not in unique_paths:
        # Only Stat/Hash each path once, input pathspecs can have dups.
        unique_paths.add(vfs_urn)

        self.StartFileFetch(pathspec)

  def StartFileFetch(self, pathspec: jobs_pb2.PathSpec):
    """Schedules new file transfer."""
    # Create an index so we can find this pathspec later.
    self.store.indexed_pathspecs.append(pathspec)
    self._TryToStartNextPathspec()

  def _TryToStartNextPathspec(self):
    """Try to schedule the next pathspec if there is enough capacity."""

    # If there's no capacity, there's nothing to do here.
    if not self._HasEnoughCapacity():
      return

    try:
      index = self.store.next_pathspec_to_start
      pathspec = self.store.indexed_pathspecs[index]
      self.store.next_pathspec_to_start = index + 1
    except IndexError:
      # We did all the pathspecs, nothing left to do here.
      return

    if self.rrg_support and pathspec.pathtype in [
        jobs_pb2.PathSpec.OS,
        jobs_pb2.PathSpec.TMPFILE,
    ]:
      pending_stat = self.store.pending_stats.add()
      pending_stat.index = index
      pending_stat.tracker.index = index

      get_file_metadata = rrg_stubs.GetFileMetadata()

      path = get_file_metadata.args.paths.add()
      path.raw_bytes = pathspec.path.encode()
      # TODO: Sometimes GRR "fixes" Windows paths and inserts a
      # leading '/' in front (e.g. to have `/C:/Windows`). RRG does not treat it
      # as a valid absolute path and so we need to "unfix" it here.
      #
      # We should fix GRR not to do this path fixing.
      if self.rrg_os_type == rrg_os_pb2.WINDOWS:
        path.raw_bytes = path.raw_bytes.removeprefix(b"/")

      if self.proto_args.stop_at != flows_pb2.MultiGetFileArgs.StopAt.STAT:
        pending_hash = self.store.pending_hashes.add()
        pending_hash.index = index
        pending_hash.tracker.index = index

        get_file_metadata.args.md5 = True
        get_file_metadata.args.sha1 = True
        get_file_metadata.args.sha256 = True

      get_file_metadata.context["index"] = str(index)
      get_file_metadata.Call(self._ProcessGetFileMetadata)
      return

    # First stat the file, then hash the file if needed.
    self._ScheduleStatFile(index, pathspec)
    if self.proto_args.stop_at == MultiGetFileArgs.StopAt.STAT:
      return

    self._ScheduleHashFile(index, pathspec)

  @flow_base.UseProto2AnyResponses
  def _ProcessGetFileMetadata(
      self,
      responses: flow_responses.Responses[any_pb2.Any],
  ) -> None:
    index = int(responses.request_data["index"])

    if not responses.success or not responses:
      self.Log("Failed to collect file metadata: %s", responses.status)
      _RemoveIndexToTracker(self.store.pending_stats, index)
      _RemoveIndexToTracker(self.store.pending_hashes, index)
      self._FileFetchFailed(index)
      return

    if len(responses) != 1:
      raise flow_base.FlowError(
          f"Unexpected number of responses: {len(responses)}",
      )

    response = rrg_get_file_metadata_pb2.Result()
    response.ParseFromString(list(responses)[0].value)

    if response.metadata.type == rrg_fs_pb2.FileMetadata.FILE:
      pass
    elif response.metadata.type == rrg_fs_pb2.FileMetadata.SYMLINK:
      # TODO: Add support for symlinks.
      raise NotImplementedError()
    else:
      self.Log(
          "Unexpected file type for '%s': %s",
          response.path.raw_bytes.decode("utf-8", "backslashreplace"),
          rrg_fs_pb2.FileMetadata.Type.Name(response.metadata.type),
      )
      _RemoveIndexToTracker(self.store.pending_stats, index)
      _RemoveIndexToTracker(self.store.pending_hashes, index)
      self._FileFetchFailed(index)
      return

    stat_entry = rrg_fs.StatEntry(response.metadata)
    stat_entry.pathspec.CopyFrom(self.store.indexed_pathspecs[index])

    _RemoveIndexToTracker(self.store.pending_stats, index)

    if self.proto_args.stop_at == flows_pb2.MultiGetFileArgs.StopAt.STAT:
      progress = self.store.pathspecs_progress[index]
      progress.status = flows_pb2.PathSpecProgress.COLLECTED

      filesystem.WritePartialFileResults(
          self.client_id,
          mig_client_fs.ToRDFStatEntry(stat_entry),
      )
      self.SendReplyProto(stat_entry)
      self._RemoveCompletedPathspec(index)
      return

    if not response.md5:
      raise flow_base.FlowError(f"MD5 missing for {index}")
    if not response.sha1:
      raise flow_base.FlowError(f"SHA-1 missing for {index}")
    if not response.sha256:
      raise flow_base.FlowError(f"SHA-256 missing {index}")

    pending_hash = _FindMultiGetFileTracker(self.store.pending_hashes, index)
    if pending_hash is None:
      raise flow_base.FlowError(f"Missing pending hash tracker for {index}")

    pending_hash.stat_entry.CopyFrom(stat_entry)
    pending_hash.hash_obj.md5 = response.md5
    pending_hash.hash_obj.sha1 = response.sha1
    pending_hash.hash_obj.sha256 = response.sha256

    self.store.num_files_hashed += 1

    if self.proto_args.stop_at == flows_pb2.MultiGetFileArgs.StopAt.HASH:
      progress = self.store.pathspecs_progress[index]
      progress.status = flows_pb2.PathSpecProgress.COLLECTED

      filesystem.WritePartialFileResults(
          self.client_id,
          mig_client_fs.ToRDFStatEntry(stat_entry),
          mig_crypto.ToRDFHash(pending_hash.hash_obj),
      )
      self.SendReplyProto(stat_entry)
      self._RemoveCompletedPathspec(index)
      return

    self.store.num_files_hashed_since_check += 1
    if self.store.num_files_hashed_since_check >= self.MIN_CALL_TO_FILE_STORE:
      self._CheckHashesWithFileStore()

  def _HasEnoughCapacity(self) -> bool:
    """Checks whether there is enough capacity to schedule next pathspec."""
    maximum_pending_files = self.proto_args.maximum_pending_files or 1000

    if maximum_pending_files <= len(self.store.pending_files):
      return False

    if maximum_pending_files <= len(self.store.pending_hashes):
      return False

    if maximum_pending_files <= len(self.store.pending_stats):
      return False

    return True

  def _ScheduleStatFile(self, index: int, pathspec: jobs_pb2.PathSpec) -> None:
    """Schedules the appropriate Stat File Client Action.

    Args:
      index: Index of the current file to get Stat for.
      pathspec: Pathspec of the current file to get Stat for.
    """
    # Add the file tracker to the pending stats list where it waits until the
    # stat comes back.
    self.store.pending_stats.append(
        flows_pb2.IndexToTracker(
            index=index, tracker=flows_pb2.MultiGetFileTracker(index=index)
        )
    )

    request = jobs_pb2.GetFileStatRequest(
        pathspec=pathspec,
        follow_symlink=True,
    )
    self.CallClientProto(
        server_stubs.GetFileStat,
        request,
        next_state=self._ReceiveFileStat.__name__,
        request_data=dict(index=index, request_name="GetFileStat"),
    )

  def _RemoveCompletedPathspec(self, index):
    """Removes a pathspec from the list of pathspecs."""
    # We copy the contents of the pathspec here to return it later.
    # Simply grabbing the reference (self.store.indexed_pathspecs[index]) is
    # not enough, since we override the dict entry below (and the reference here
    # would point to the new entry, not to the original object).
    pathspec = jobs_pb2.PathSpec()
    pathspec.CopyFrom(self.store.indexed_pathspecs[index])

    self.store.indexed_pathspecs[index].CopyFrom(jobs_pb2.PathSpec())
    _RemoveIndexToTracker(self.store.pending_stats, index)
    _RemoveIndexToTracker(self.store.pending_hashes, index)
    _RemoveIndexToTracker(self.store.pending_files, index)

    # We have a bit more room in the pending_hashes so we try to schedule
    # another pathspec.
    self._TryToStartNextPathspec()
    return pathspec

  @flow_base.UseProto2AnyResponses
  def _ReceiveFileStat(self, responses: flow_responses.Responses[any_pb2.Any]):
    """Stores stat entry in the flow's state."""

    index = responses.request_data["index"]
    if not responses.success:
      self.Log("Failed to stat file: %s", responses.status)
      _RemoveIndexToTracker(self.store.pending_stats, index)
      # Report failure.
      self._FileFetchFailed(index)
      return

    any_stat_entry = responses.First()
    assert any_stat_entry is not None
    stat_entry = jobs_pb2.StatEntry()
    stat_entry.ParseFromString(any_stat_entry.value)

    # This stat is no longer pending, so we free the tracker.
    _RemoveIndexToTracker(self.store.pending_stats, index)

    self.ReceiveFetchedFileStat(stat_entry, index)

    if self.proto_args.stop_at == MultiGetFileArgs.StopAt.STAT:
      self._RemoveCompletedPathspec(index)
      return

    # Propagate stat information to hash queue (same index is used across).
    hash_tracker = _FindMultiGetFileTracker(self.store.pending_hashes, index)
    if hash_tracker is None:
      self.Error(
          error_message=(
              "Something went wrong, nothing found in pending_hashes for "
              f" index: {index}"
          )
      )

    hash_tracker.stat_entry.CopyFrom(stat_entry)

  def ReceiveFetchedFileStat(
      self,
      stat_entry: jobs_pb2.StatEntry,
      index: int,
  ) -> None:
    # If we're only meant to get the STAT, report the result.
    if self.proto_args.stop_at == MultiGetFileArgs.StopAt.STAT:
      self.store.pathspecs_progress[index].status = (
          PathSpecProgress.Status.COLLECTED
      )
      filesystem.WritePartialFileResults(
          self.client_id, mig_client_fs.ToRDFStatEntry(stat_entry)
      )
      self.SendReplyProto(stat_entry)

  def _ScheduleHashFile(self, index: int, pathspec: jobs_pb2.PathSpec) -> None:
    """Schedules the HashFile Client Action.

    Args:
      index: Index of the current file to be hashed.
      pathspec: Pathspec of the current file to be hashed.
    """
    # Add the file tracker to the pending hashes list where it waits until the
    # hash comes back.
    self.store.pending_hashes.append(
        flows_pb2.IndexToTracker(
            index=index,
            tracker=flows_pb2.MultiGetFileTracker(index=index),
        )
    )
    default_file_size = 1000000000  # 1Gb
    request = jobs_pb2.FingerprintRequest(
        pathspec=pathspec,
        max_filesize=self.proto_args.file_size or default_file_size,
        tuples=[
            jobs_pb2.FingerprintTuple(
                fp_type=jobs_pb2.FingerprintTuple.Type.FPT_GENERIC,
                hashers=[
                    jobs_pb2.FingerprintTuple.HashType.MD5,
                    jobs_pb2.FingerprintTuple.HashType.SHA1,
                    jobs_pb2.FingerprintTuple.HashType.SHA256,
                ],
            )
        ],
    )

    self.CallClientProto(
        server_stubs.HashFile,
        request,
        next_state=self._ReceiveFileHash.__name__,
        request_data=dict(index=index),
    )

  @flow_base.UseProto2AnyResponses
  def _ReceiveFileHash(self, responses: flow_responses.Responses[any_pb2.Any]):
    """Add hash digest to tracker and check with filestore."""

    index = responses.request_data["index"]
    if not responses.success:
      self.Log("Failed to hash file: %s", responses.status)
      _RemoveIndexToTracker(self.store.pending_hashes, index)
      # Report the error.
      self._FileFetchFailed(index)
      return

    self.store.num_files_hashed += 1
    response_any = responses.First()
    assert response_any is not None
    response = jobs_pb2.FingerprintResponse()
    response.ParseFromString(response_any.value)

    if response.HasField("hash"):
      hash_obj = response.hash
    else:
      # Deprecate this method of returning hashes.
      hash_obj = rdf_crypto.Hash()

      if len(response.results) < 1:
        self.Log("Failed to hash file: %s", self.store.indexed_pathspecs[index])
        _RemoveIndexToTracker(self.store.pending_hashes, index)
        return

      result = response.results[0]
      rdf_result = mig_protodict.ToRDFDict(result)
      if rdf_result["name"] != "generic":
        self.Log("Failed to hash file: %s", self.store.indexed_pathspecs[index])
        _RemoveIndexToTracker(self.store.pending_hashes, index)
        return

      try:
        for hash_type in ["md5", "sha1", "sha256"]:
          value = rdf_result.GetItem(hash_type)
          setattr(hash_obj, hash_type, value)
      except AttributeError:
        self.Log("Failed to hash file: %s", self.store.indexed_pathspecs[index])
        _RemoveIndexToTracker(self.store.pending_hashes, index)
        return
      hash_obj = mig_crypto.ToProtoHash(hash_obj)

    tracker = _FindMultiGetFileTracker(self.store.pending_hashes, index)
    if tracker is None:
      # Hashing the file failed, but we did stat it.
      self._FileFetchFailed(index)
      return

    tracker.hash_obj.CopyFrom(hash_obj)
    tracker.bytes_read = response.bytes_read

    self.ReceiveFetchedFileHash(tracker.stat_entry, hash_obj, index)

    if self.proto_args.stop_at == MultiGetFileArgs.StopAt.HASH:
      self._RemoveCompletedPathspec(index)
      return

    self.store.num_files_hashed_since_check += 1
    if self.store.num_files_hashed_since_check >= self.MIN_CALL_TO_FILE_STORE:
      self._CheckHashesWithFileStore()

  def ReceiveFetchedFileHash(
      self,
      stat_entry: jobs_pb2.StatEntry,
      file_hash: jobs_pb2.Hash,
      index: int,
  ) -> None:
    # If we're only meant to get the HASH, report the result.
    if self.proto_args.stop_at == MultiGetFileArgs.StopAt.HASH:
      self.store.pathspecs_progress[index].status = (
          PathSpecProgress.Status.COLLECTED
      )
      filesystem.WritePartialFileResults(
          self.client_id,
          mig_client_fs.ToRDFStatEntry(stat_entry),
          mig_crypto.ToRDFHash(file_hash),
      )
      self.SendReplyProto(stat_entry)

  def _CheckHashesWithFileStore(self):
    """Check all queued up hashes for existence in file store.

    Hashes which do not exist in the file store will be downloaded. This
    function flushes the entire queue (self.store.pending_hashes) in order to
    minimize the round trips to the file store.

    If a file was found in the file store it is not scheduled for collection
    and its PathInfo is written to the datastore pointing to the file store's
    hash. Otherwise, we request the client to hash every block in the file,
    and add it to the file tracking queue (self.store.pending_files).
    """
    if not self.store.pending_hashes:
      return

    # This map represents all the hashes in the pending urns.
    file_hashes = {}

    # Store a mapping of hash to tracker. Keys are hashdigest objects,
    # values are arrays of tracker dicts.
    hash_to_tracker = {}
    for index_to_tracker in self.store.pending_hashes:
      # We might not have gotten this hash yet
      if not index_to_tracker.tracker.hash_obj.sha256:
        continue

      hash_obj = index_to_tracker.tracker.hash_obj
      digest = hash_obj.sha256
      file_hashes[index_to_tracker.index] = hash_obj
      hash_to_tracker.setdefault(rdf_objects.SHA256HashID(digest), []).append(
          index_to_tracker.tracker
      )

    # First we get all the files which are present in the file store.
    files_in_filestore = set()

    statuses = file_store.CheckHashes([
        rdf_objects.SHA256HashID.FromSerializedBytes(ho.sha256)
        for ho in file_hashes.values()
    ])
    for hash_id, status in statuses.items():
      if not status:
        continue

      # Since checkhashes only returns one digest per unique hash we need to
      # find any other files pending download with the same hash.
      for tracker in hash_to_tracker[hash_id]:
        self.store.num_files_skipped += 1
        file_hashes.pop(tracker.index)
        files_in_filestore.add(hash_id)
        # Remove this tracker from the pending_hashes store since we no longer
        # need to process it.
        _RemoveIndexToTracker(self.store.pending_hashes, tracker.index)

    # Now that the check is done, reset our counter
    self.store.num_files_hashed_since_check = 0
    # Now copy all existing files to the client aff4 space.
    for hash_id in files_in_filestore:

      for file_tracker in hash_to_tracker.get(hash_id, []):
        stat_entry = file_tracker.stat_entry
        path_info = rdf_objects.PathInfo.FromStatEntry(
            mig_client_fs.ToRDFStatEntry(stat_entry)
        )
        proto_path_info = mig_objects.ToProtoPathInfo(path_info)
        proto_path_info.hash_entry.CopyFrom(file_tracker.hash_obj)
        data_store.REL_DB.WritePathInfos(self.client_id, [proto_path_info])

        # Report this hit to the flow's caller.
        self._ReceiveFetchedFile(file_tracker, is_duplicate=True)

    # Now we iterate over all the files which are not in the store and arrange
    # for them to be copied.
    for index in file_hashes:

      # Move the tracker from the pending hashes store to the pending files
      # store - it will now be downloaded.
      index_to_tracker = _FindIndexToTracker(self.store.pending_hashes, index)
      _RemoveIndexToTracker(self.store.pending_hashes, index)

      # Append appends a COPY of the object (`index_to_tracker` is no longer
      # the pointer we want to use to modify the object).
      # So we append and then try to find the right object again.
      # This way, we can modify it below and not worry about adding it later
      # to the right queue.
      self.store.pending_files.append(index_to_tracker)
      index_to_tracker = _FindIndexToTracker(self.store.pending_files, index)
      file_tracker = index_to_tracker.tracker

      # If we already know how big the file is we use that, otherwise fall back
      # to the size reported by stat.
      if file_tracker.bytes_read > 0:
        file_tracker.size_to_download = file_tracker.bytes_read
      else:
        file_tracker.size_to_download = file_tracker.stat_entry.st_size

      # We do not have the file here yet - we need to retrieve it.
      file_tracker.expected_chunks = (
          file_tracker.size_to_download // self.CHUNK_SIZE + 1
      )
      expected_number_of_hashes = file_tracker.expected_chunks

      # We just hash ALL the chunks in the file now. NOTE: This maximizes client
      # VFS cache hit rate and is far more efficient than launching multiple
      # GetFile flows.
      self.store.num_files_to_fetch += 1

      for i in range(expected_number_of_hashes):
        if i == expected_number_of_hashes - 1:
          # The last chunk is short.
          length = file_tracker.size_to_download % self.CHUNK_SIZE
        else:
          length = self.CHUNK_SIZE

        pathspec = file_tracker.stat_entry.pathspec

        # Support for `get_file_sha256` was introduced in RRG in version 0.0.5.
        if self.rrg_version >= (0, 0, 5) and pathspec.pathtype in [
            jobs_pb2.PathSpec.OS,
            jobs_pb2.PathSpec.TMPFILE,
        ]:
          path = pathspec.path
          # TODO: Sometimes GRR "fixes" Windows paths and inserts
          # a leading '/' in front (e.g. to have `/C:/Windows`). RRG does not
          # treat it as a valid absolute path and so we need to "unfix" it here.
          #
          # We should fix GRR not to do this path fixing.
          if self.rrg_os_type == rrg_os_pb2.WINDOWS:
            path = path.removeprefix("/")

          get_file_sha256 = rrg_stubs.GetFileSha256()
          get_file_sha256.args.path.raw_bytes = path.encode()
          get_file_sha256.args.length = length
          get_file_sha256.args.offset = i * self.CHUNK_SIZE
          get_file_sha256.context["index"] = str(index)
          get_file_sha256.Call(self._ProcessGetFileSha256)
        else:
          self.CallClientProto(
              server_stubs.HashBuffer,
              jobs_pb2.BufferReference(
                  length=length,
                  offset=i * self.CHUNK_SIZE,
                  pathspec=pathspec,
              ),
              next_state=self._CheckHash.__name__,
              request_data=dict(index=index),
          )

    if self.store.num_files_hashed % 100 == 0:
      self.Log(
          "Hashed %d files, skipped %s already stored.",
          self.store.num_files_hashed,
          self.store.num_files_skipped,
      )

  @flow_base.UseProto2AnyResponses
  def _ProcessGetFileSha256(
      self,
      responses: flow_responses.Responses[any_pb2.Any],
  ) -> None:
    index = int(responses.request_data["index"])

    index_to_tracker = _FindIndexToTracker(self.store.pending_files, index)
    if index_to_tracker is None:
      # This file was already removed from the queue (e.g. because of a failure)
      # and we are no longer interested in the hash. We exit early even if the
      # action failed to avoid duplicated errors.
      return

    if not responses.success or not responses:
      self.Log("Failed to collect file hash: %s", responses.status)
      self._FileFetchFailed(index)
      return

    if len(responses) != 1:
      raise flow_base.FlowError(
          f"Unexpected number of responses: {len(responses)}",
      )

    response = rrg_get_file_sha256_pb2.Result()
    response.ParseFromString(list(responses)[0].value)

    blob_ref = index_to_tracker.tracker.hash_list.add()
    blob_ref.pathspec.CopyFrom(self.store.indexed_pathspecs[index])
    blob_ref.offset = response.offset
    blob_ref.length = response.length
    blob_ref.data = response.sha256

    self.store.blob_hashes_pending += 1
    if self.store.blob_hashes_pending > self.MIN_CALL_TO_FILE_STORE:
      self._FetchFileContent()

  @flow_base.UseProto2AnyResponses
  def _CheckHash(self, responses: flow_responses.Responses[any_pb2.Any]):
    """Adds the block hash to the file tracker responsible for this vfs URN."""
    index = responses.request_data["index"]

    index_to_tracker = _FindIndexToTracker(self.store.pending_files, index)
    if index_to_tracker is None:
      # This is a blobhash for a file we already failed to read and logged as
      # below, check here to avoid logging dups.
      return

    file_tracker = index_to_tracker.tracker

    hash_response = responses.First()
    if not responses.success or not hash_response:
      urn = mig_paths.ToRDFPathSpec(file_tracker.stat_entry.pathspec).AFF4Path(
          self.client_urn
      )
      self.Log("Failed to read %s: %s", urn, responses.status)
      self._FileFetchFailed(index)
      return

    hash_response_proto = jobs_pb2.BufferReference()
    hash_response_proto.ParseFromString(hash_response.value)
    file_tracker.hash_list.append(hash_response_proto)

    self.store.blob_hashes_pending += 1

    if self.store.blob_hashes_pending > self.MIN_CALL_TO_FILE_STORE:
      self._FetchFileContent()

  def _FetchFileContent(self):
    """Fetch as much as the file's content as possible.

    This drains the pending_files store by checking which blobs we already have
    in the store and issuing calls to the client to receive outstanding blobs.
    """
    if not self.store.pending_files:
      return

    # Check what blobs we already have in the blob store.
    blob_ids = []
    for index_to_tracker in self.store.pending_files:
      for hash_response in index_to_tracker.tracker.hash_list:
        blob_ids.append(models_blobs.BlobID(hash_response.data))

    # This is effectively a BlobStore call.
    existing_blobs = data_store.BLOBS.CheckBlobsExist(blob_ids)

    self.store.blob_hashes_pending = 0

    # If we encounter hashes that we already have, we will update
    # self.store.pending_files right away.
    for index_to_tracker in self.store.pending_files:
      for i, hash_response in enumerate(index_to_tracker.tracker.hash_list):
        # Make sure we read the correct pathspec on the client.
        hash_response.pathspec.CopyFrom(
            index_to_tracker.tracker.stat_entry.pathspec
        )

        if existing_blobs[models_blobs.BlobID(hash_response.data)]:
          _BLOBSTORE_HIT.Increment()
          logging.info(
              "`MultiGetFile` %s/%s blobstore hit for %s",
              self.rdf_flow.client_id,
              self.rdf_flow.flow_id,
              hash_response,
          )

          # If we have the data we may call our state directly.
          self.CallStateInlineProto(
              messages=[hash_response],
              next_state=self._WriteBuffer.__name__,
              request_data=dict(index=index_to_tracker.index, blob_index=i),
          )
        else:
          _BLOBSTORE_MISS.Increment()
          logging.info(
              "`MultiGetFile` %s/%s blobstore miss for %s",
              self.rdf_flow.client_id,
              self.rdf_flow.flow_id,
              hash_response,
          )

          # We dont have this blob - ask the client to transmit it.
          if self.rrg_support and hash_response.pathspec.pathtype in [
              jobs_pb2.PathSpec.OS,
              jobs_pb2.PathSpec.TMPFILE,
          ]:
            get_file_contents = rrg_stubs.GetFileContents()

            path = get_file_contents.args.paths.add()
            path.raw_bytes = hash_response.pathspec.path.encode()
            # TODO: Sometimes GRR "fixes" Windows paths and
            # inserts a leading '/' in front (e.g. to have `/C:/Windows`). RRG
            # does not treat it as a valid absolute path and so we need to
            # "unfix" it here.
            #
            # We should fix GRR not to do this path fixing.
            if self.rrg_os_type == rrg_os_pb2.WINDOWS:
              path.raw_bytes = path.raw_bytes.removeprefix(b"/")

            get_file_contents.args.offset = hash_response.offset
            get_file_contents.args.length = hash_response.length
            get_file_contents.context["index"] = str(index_to_tracker.index)
            get_file_contents.context["blob_index"] = str(i)
            get_file_contents.Call(self._ProcessGetFileContents)
          else:
            self.CallClientProto(
                server_stubs.TransferBuffer,
                hash_response,
                next_state=self._WriteBuffer.__name__,
                request_data=dict(index=index_to_tracker.index, blob_index=i),
            )

  @flow_base.UseProto2AnyResponses
  def _ProcessGetFileContents(
      self,
      responses: flow_responses.Responses[any_pb2.Any],
  ) -> None:
    index = int(responses.request_data["index"])

    index_to_tracker = _FindIndexToTracker(self.store.pending_files, index)
    if index_to_tracker is None:
      # This file was already removed from the queue (e.g. because of a failure)
      # and we are no longer interested in the content. We exit early even if
      # the action failed to avoid duplicated errors.
      return

    if not responses.success or not responses:
      self.Log("Failed to collect file contents: %s", responses.status)
      self._FileFetchFailed(index)
      return

    response = rrg_get_file_contents_pb2.Result()
    response.ParseFromString(list(responses)[0].value)

    if response.error:
      self.Log("Failed to collect file contents: %s", response.error)
      self._FileFetchFailed(index)
      return

    blob_ref = jobs_pb2.BufferReference()
    blob_ref.pathspec.CopyFrom(self.store.indexed_pathspecs[index])
    blob_ref.offset = response.offset
    blob_ref.length = response.length
    blob_ref.data = response.blob_sha256

    blob_dict = _BuildBlobDict(index_to_tracker.tracker.index_to_buffers)
    blob_dict[int(responses.request_data["blob_index"])] = blob_ref

    if len(blob_dict) != index_to_tracker.tracker.expected_chunks:
      # TODO: Replace with `clear()` once upgraded in open-source.
      del index_to_tracker.tracker.index_to_buffers[:]
      index_to_tracker.tracker.index_to_buffers.extend(
          _BuildIndexToBuffers(blob_dict)
      )
      return

    blob_refs = []
    for index in sorted(blob_dict):
      blob_ref = objects_pb2.BlobReference()
      blob_ref.blob_id = blob_dict[index].data
      blob_ref.offset = blob_dict[index].offset
      blob_ref.size = blob_dict[index].length

      blob_refs.append(mig_objects.ToRDFBlobReference(blob_ref))

    path_info = rdf_objects.PathInfo.FromStatEntry(
        mig_client_fs.ToRDFStatEntry(index_to_tracker.tracker.stat_entry)
    )
    client_path = db.ClientPath.FromPathInfo(self.client_id, path_info)
    path_info = mig_objects.ToProtoPathInfo(path_info)

    if self.proto_args.HasField("use_external_stores"):
      use_external_stores = self.proto_args.use_external_stores
    else:
      use_external_stores = True

    hash_id = file_store.AddFileWithUnknownHash(
        client_path,
        blob_refs,
        use_external_stores=use_external_stores,
    )
    hash_id_bytes = hash_id.AsBytes()

    if hash_id_bytes == index_to_tracker.tracker.hash_obj.sha256:
      path_info.hash_entry.CopyFrom(index_to_tracker.tracker.hash_obj)
    else:
      self.Log(
          "File SHA-256 mismatch: %s and %s",
          hash_id_bytes,
          index_to_tracker.tracker.hash_obj.sha256,
      )
      path_info.hash_entry.sha256 = hash_id_bytes

    data_store.REL_DB.WritePathInfos(self.client_id, [path_info])

    # TODO: Replace with `clear()` once upgraded in open-source.
    del index_to_tracker.tracker.index_to_buffers[:]
    del index_to_tracker.tracker.hash_list[:]

    self._ReceiveFetchedFile(index_to_tracker.tracker)
    self.store.num_files_fetched += 1
    if self.store.num_files_fetched % 100 == 0:
      self.Log(
          "Fetched %d of %d files",
          self.store.num_files_fetched,
          self.store.num_files_to_fetch,
      )

  @flow_base.UseProto2AnyResponses
  def _WriteBuffer(self, responses: flow_responses.Responses[any_pb2.Any]):
    """Write the hash received to the blob image."""

    index = responses.request_data["index"]
    index_to_tracker = _FindIndexToTracker(self.store.pending_files, index)
    if index_to_tracker is None:
      return

    # Failed to read the file - ignore it.
    if not responses.success:
      self._FileFetchFailed(index)
      return

    response_any = responses.First()
    assert response_any is not None
    response = jobs_pb2.BufferReference()
    response.ParseFromString(response_any.value)

    file_tracker = index_to_tracker.tracker

    # Map of {index: BufferReference}.
    blob_dict = _BuildBlobDict(file_tracker.index_to_buffers)
    blob_index = responses.request_data["blob_index"]
    blob_dict[blob_index] = response

    if len(blob_dict) != file_tracker.expected_chunks:
      # We need more data before we can write the file.
      # TODO: Replace with `clear()` once upgraded in OpenSource.
      del file_tracker.index_to_buffers[:]
      file_tracker.index_to_buffers.extend(_BuildIndexToBuffers(blob_dict))
      return

    # Write the file to the data store.
    stat_entry = mig_client_fs.ToRDFStatEntry(file_tracker.stat_entry)
    path_info = rdf_objects.PathInfo.FromStatEntry(stat_entry)

    blob_refs = []
    offset = 0
    for index in sorted(blob_dict):
      digest, size = blob_dict[index].data, blob_dict[index].length
      blob_refs.append(
          rdf_objects.BlobReference(offset=offset, size=size, blob_id=digest)
      )
      offset += size

    hash_obj = mig_crypto.ToRDFHash(file_tracker.hash_obj)

    client_path = db.ClientPath.FromPathInfo(self.client_id, path_info)
    if self.proto_args.HasField("use_external_stores"):
      use_external_stores = self.proto_args.use_external_stores
    else:
      use_external_stores = True
    hash_id = file_store.AddFileWithUnknownHash(
        client_path,
        blob_refs,
        use_external_stores=use_external_stores,
    )
    # If the hash that we've calculated matches what we got from the
    # client, then simply store the full hash entry.
    # Otherwise store just the hash that we've calculated.
    if hash_id.AsBytes() == hash_obj.sha256:
      path_info.hash_entry = hash_obj
    else:
      path_info.hash_entry.sha256 = hash_id.AsBytes()
      path_info.hash_entry.num_bytes = offset

    proto_path_info = mig_objects.ToProtoPathInfo(path_info)
    data_store.REL_DB.WritePathInfos(self.client_id, [proto_path_info])

    # Save some space.
    file_tracker.ClearField("index_to_buffers")
    file_tracker.ClearField("hash_list")

    # File done, remove from the store and close it.
    self._ReceiveFetchedFile(file_tracker)

    self.store.num_files_fetched += 1

    if not self.store.num_files_fetched % 100:
      self.Log(
          "Fetched %d of %d files.",
          self.store.num_files_fetched,
          self.store.num_files_to_fetch,
      )

  def _ReceiveFetchedFile(self, tracker, is_duplicate=False):
    """Remove pathspec for this index and call the ReceiveFetchedFile method."""
    index = tracker.index

    self._RemoveCompletedPathspec(index)

    # Report the request_data for this flow's caller.
    self.ReceiveFetchedFile(
        tracker.stat_entry,
        tracker.hash_obj,
        index,
        is_duplicate=is_duplicate,
    )

  def ReceiveFetchedFile(
      self,
      stat_entry,
      unused_hash_obj,
      index,
      is_duplicate=False,
  ):
    """This method will be called for each new file successfully fetched."""
    if is_duplicate:
      status = PathSpecProgress.Status.SKIPPED
    else:
      status = PathSpecProgress.Status.COLLECTED
    self.store.pathspecs_progress[index].status = status

    self.SendReplyProto(stat_entry)

  def _FileFetchFailed(self, index: int) -> None:
    """Remove pathspec for this index and call the FileFetchFailed method."""

    pathspec = self._RemoveCompletedPathspec(index)
    # RemoveCompletedPathspec returns an empty pathspec if the pathspec was
    # already removed (rather than None). This is because the code relies on
    # `indexed_pathspecs` having a set number of elements (we rely on the slice
    # index). To save space we set the pathspec to an empty proto when removed.
    if not pathspec.ListFields():
      # This was already reported as failed.
      return

    self.store.num_files_failed += 1

    # Report the request_data for this flow's caller.
    self.FileFetchFailed(index)

  def FileFetchFailed(self, index: int) -> None:
    """This method will be called when stat or hash requests fail."""
    self.store.pathspecs_progress[index].status = PathSpecProgress.Status.FAILED

  def End(self) -> None:
    # There are some files still in flight.
    if self.store.pending_hashes or self.store.pending_files:
      self._CheckHashesWithFileStore()
      self._FetchFileContent()

    if not self.outstanding_requests:
      super().End()


def _BuildBlobDict(
    index_to_buffers: flows_pb2.IndexToBufferReference,
) -> dict[int, jobs_pb2.BufferReference]:
  """Builds a dictionary of index to buffer reference."""
  return {
      index_to_buffer.index: index_to_buffer.buffer_reference
      for index_to_buffer in index_to_buffers
  }


def _BuildIndexToBuffers(
    blob_dict: dict[int, jobs_pb2.BufferReference],
) -> flows_pb2.IndexToBufferReference:
  """Builds a list of index to buffer reference."""
  return [
      flows_pb2.IndexToBufferReference(
          index=index, buffer_reference=buffer_reference
      )
      for index, buffer_reference in blob_dict.items()
  ]


class GetMBRArgs(rdf_structs.RDFProtoStruct):
  protobuf = flows_pb2.GetMBRArgs


class GetMBR(
    flow_base.FlowBase[
        flows_pb2.GetMBRArgs,
        flows_pb2.GetMBRStore,
        flows_pb2.DefaultFlowProgress,
    ]
):
  """A flow to retrieve the MBR.

  Returns to parent flow:
    The retrieved MBR.
  """

  category = "/Filesystem/"
  args_type = GetMBRArgs
  behaviours = flow_base.BEHAVIOUR_BASIC
  result_types = (rdf_wrappers.BytesValue,)

  proto_args_type = flows_pb2.GetMBRArgs
  proto_result_types = [config_pb2.BytesValue]
  proto_store_type = flows_pb2.GetMBRStore

  only_protos_allowed = True

  DEFAULT_MBR_LENGTH = 4096

  def Start(self):
    """Schedules the ReadBuffer client action."""
    pathspec = jobs_pb2.PathSpec(
        path="\\\\.\\PhysicalDrive0\\",
        pathtype=jobs_pb2.PathSpec.PathType.OS,
        path_options=jobs_pb2.PathSpec.Options.CASE_LITERAL,
    )

    self.store.bytes_downloaded = 0
    # An array to collect buffers. This is not very efficient, MBR
    # data should be kept short though so this is not a big deal.
    # TODO: Replace with `clear()` once upgraded.
    del self.store.buffers[:]

    if not self.proto_args.length:
      self.proto_args.length = self.DEFAULT_MBR_LENGTH

    buffer_size = constants.CLIENT_MAX_BUFFER_SIZE
    buffers_we_need = self.proto_args.length // buffer_size
    if self.proto_args.length % buffer_size:
      buffers_we_need += 1

    bytes_we_need = self.proto_args.length

    for i in range(buffers_we_need):
      request = jobs_pb2.BufferReference(
          pathspec=pathspec,
          offset=i * buffer_size,
          length=min(bytes_we_need, buffer_size),
      )
      self.CallClientProto(
          server_stubs.ReadBuffer, request, next_state=self.StoreMBR.__name__
      )
      bytes_we_need -= buffer_size

  @flow_base.UseProto2AnyResponses
  def StoreMBR(self, responses: flow_responses.Responses[any_pb2.Any]) -> None:
    """This method stores the MBR."""

    if not responses.success or not list(responses):
      msg = "Could not retrieve MBR: %s" % responses.status
      self.Log(msg)
      raise flow_base.FlowError(msg)

    response_any = list(responses)[0]
    response = jobs_pb2.BufferReference()
    response.ParseFromString(response_any.value)

    self.store.buffers.append(response.data)
    self.store.bytes_downloaded += len(response.data)

    if self.store.bytes_downloaded >= self.proto_args.length:
      mbr_data = b"".join(self.store.buffers)
      # TODO: Replace with `clear()` once upgraded.
      del self.store.buffers[:]

      self.Log("Successfully collected the MBR (%d bytes)." % len(mbr_data))
      self.SendReplyProto(config_pb2.BytesValue(value=mbr_data))


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
