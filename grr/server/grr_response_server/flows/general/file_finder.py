#!/usr/bin/env python
"""Search for certain files, filter them by given criteria and do something."""

from collections.abc import Sequence
import itertools
import math
import re
import stat
from typing import Optional, cast

from google.protobuf import any_pb2
from google.protobuf import timestamp_pb2
from grr_response_core.lib import artifact_utils
from grr_response_core.lib import rdfvalue
from grr_response_core.lib.rdfvalues import file_finder as rdf_file_finder
from grr_response_core.lib.rdfvalues import mig_client_fs
from grr_response_core.lib.rdfvalues import mig_file_finder
from grr_response_core.lib.rdfvalues import mig_paths
from grr_response_proto import flows_pb2
from grr_response_proto import jobs_pb2
from grr_response_proto import knowledge_base_pb2
from grr_response_proto import objects_pb2
from grr_response_server import data_store
from grr_response_server import file_store
from grr_response_server import flow_base
from grr_response_server import flow_responses
from grr_response_server import rrg_fs
from grr_response_server import rrg_glob
from grr_response_server import rrg_path
from grr_response_server import rrg_stubs
from grr_response_server import server_stubs
from grr_response_server.databases import db
from grr_response_server.flows.general import filesystem
from grr_response_server.models import blobs as models_blobs
from grr_response_server.rdfvalues import mig_objects
from grr_response_server.rdfvalues import objects as rdf_objects
from grr_response_proto.rrg import fs_pb2 as rrg_fs_pb2
from grr_response_proto.rrg import os_pb2 as rrg_os_pb2
from grr_response_proto.rrg.action import get_file_contents_pb2 as rrg_get_file_contents_pb2
from grr_response_proto.rrg.action import get_file_metadata_pb2 as rrg_get_file_metadata_pb2


def _GetPendingBlobIDs(
    responses: Sequence[flows_pb2.FileFinderResult],
) -> Sequence[tuple[flows_pb2.FileFinderResult, set[models_blobs.BlobID]]]:
  """For each FileFinderResult get reported but not yet stored blobs.

  Args:
    responses: A collection of FileFinderResults containing transferred file
      chunks.

  Returns:
      A sequence of tuples (<FileFinderResult, set of pending blob ids>).
      Even though returning a dict would be more correct conceptually, this
      is not possible as FileFinderResult is not hashable and can't be used
      as a key.
  """
  response_blob_ids = {}
  blob_id_responses = {}
  blob_ids = set()
  for idx, r in enumerate(responses):
    # Store the total number of chunks per response.
    response_blob_ids[idx] = set()
    for c in r.transferred_file.chunks:
      blob_id = models_blobs.BlobID(c.digest)
      blob_ids.add(blob_id)
      response_blob_ids[idx].add(blob_id)

      # For each blob store a set of indexes of responses that have it.
      # Note that the same blob may be present in more than one response
      # (blobs are just data).
      blob_id_responses.setdefault(blob_id, set()).add(idx)

  blobs_present = data_store.BLOBS.CheckBlobsExist(blob_ids)
  for blob_id, is_present in blobs_present.items():
    if not is_present:
      continue

    # If the blob is present, decrement counters for relevant responses.
    for response_idx in blob_id_responses[blob_id]:
      response_blob_ids[response_idx].remove(blob_id)

  return [
      (responses[idx], blob_ids) for idx, blob_ids in response_blob_ids.items()
  ]


class ClientFileFinder(
    flow_base.FlowBase[
        flows_pb2.FileFinderArgs,
        flows_pb2.FileFinderStore,
        flows_pb2.FileFinderProgress,
    ]
):
  """A client side file finder flow."""

  friendly_name = "Client Side File Finder"
  category = "/Filesystem/"
  args_type = rdf_file_finder.FileFinderArgs
  result_types = (rdf_file_finder.FileFinderResult,)
  behaviours = flow_base.BEHAVIOUR_BASIC

  BLOB_CHECK_DELAY = rdfvalue.Duration("60s")
  MAX_BLOB_CHECKS = 60

  proto_args_type = flows_pb2.FileFinderArgs
  proto_store_type = flows_pb2.FileFinderStore
  proto_progress_type = flows_pb2.FileFinderProgress
  proto_result_types = (flows_pb2.FileFinderResult,)

  only_protos_allowed = True

  def Start(self):
    """Issue the find request."""
    super().Start()

    self.GetProgressProto().files_found = 0

    # Do not do anything if no paths are specified in the arguments.
    if not self.proto_args.paths:
      self.Log("No paths provided, finishing.")
      return

    if (
        # `get_file_metadata` with support for multiple files was introduced in
        # version 0.0.3.
        self.rrg_version >= (0, 0, 3)
        # RRG at version at least 0.0.7 is required as previous ones might trip
        # over Fleetspeak message limit when calling `get_file_contents`.
        and (
            self.proto_args.action.action_type
            != flows_pb2.FileFinderAction.DOWNLOAD
            or self.rrg_version >= (0, 0, 7)
        )
        and self.proto_args.pathtype
        in [
            jobs_pb2.PathSpec.PathType.OS,
            jobs_pb2.PathSpec.PathType.TMPFILE,
        ]
        and all(
            (
                _.condition_type
                in [
                    flows_pb2.FileFinderCondition.MODIFICATION_TIME,
                    flows_pb2.FileFinderCondition.ACCESS_TIME,
                    flows_pb2.FileFinderCondition.SIZE,
                ]
            )
            or (
                # `get_file_metadata` support for content regex matching was
                # introduced in version 0.0.6.
                self.rrg_version >= (0, 0, 6)
                and _.condition_type
                in [
                    flows_pb2.FileFinderCondition.CONTENTS_LITERAL_MATCH,
                    flows_pb2.FileFinderCondition.CONTENTS_REGEX_MATCH,
                ]
            )
            for _ in self.proto_args.conditions
        )
    ):
      return self._StartRRG()

    if self.proto_args.pathtype == jobs_pb2.PathSpec.PathType.OS:
      stub = server_stubs.FileFinderOS
    else:
      stub = server_stubs.VfsFileFinder

    # TODO: Remove this workaround once sandboxing issues are
    # resolved and NTFS paths work it again.
    if (
        self.proto_args.pathtype == jobs_pb2.PathSpec.PathType.NTFS
        and not self.proto_args.HasField("implementation_type")
    ):
      self.Log("Using unsandboxed NTFS access")
      self.proto_args.implementation_type = (
          jobs_pb2.PathSpec.ImplementationType.DIRECT
      )

    if (paths := self._InterpolatePaths(self.proto_args.paths)) is not None:
      interpolated_args = flows_pb2.FileFinderArgs()
      interpolated_args.CopyFrom(self.proto_args)
      # TODO: Replace with `clear()` once upgraded.
      del interpolated_args.paths[:]
      interpolated_args.paths.extend(paths)
      self.CallClientProto(
          stub,
          action_args=interpolated_args,
          next_state=self.StoreResultsWithoutBlobs.__name__,
      )
    self.store.num_blob_waits = 0

  def _StartRRG(self) -> None:
    paths = self._InterpolatePaths(self.proto_args.paths)
    if not paths:
      return

    action = rrg_stubs.GetFileMetadata()
    path_regexes = []
    path_pruning_regexes = []

    for path in paths:
      glob = rrg_glob.Glob(rrg_path.PurePath.For(self.rrg_os_type, path))

      action.args.paths.add().raw_bytes = bytes(glob.root)
      action.args.max_depth = max(action.args.max_depth, glob.root_level)

      path_regexes.append(glob.regex.pattern)
      path_pruning_regexes.append(glob.pruning_regex.pattern)

      if (
          self.proto_args.action.action_type
          in [
              flows_pb2.FileFinderAction.HASH,
              flows_pb2.FileFinderAction.DOWNLOAD,
          ]
          # Note that we do not want to hash within a single action call if we
          # have some conditions, as RRG filters are applied as the last step
          # of action execution and thus we could end up excessively digesting
          # unnecessary files.
          and not self.proto_args.conditions
      ):
        action.args.md5 = True
        action.args.sha1 = True
        action.args.sha256 = True

    if action.args.max_depth > 0:
      action.args.path_pruning_regex = "|".join(path_pruning_regexes)

      # Path pruning can yield additional entries (as it is used to guide the
      # search, not to filter results). Thus, we use filter to only return what
      # we are actually interested in.
      #
      # Note that we use this only in case there are any pruning regexes. If
      # there are none, there are no globs and thus we do not need to filter
      # anything.
      path_filter = action.AddFilter()
      for path_regex in path_regexes:
        path_cond = path_filter.conditions.add()
        path_cond.field.extend([
            rrg_get_file_metadata_pb2.Result.PATH_FIELD_NUMBER,
            rrg_fs_pb2.Path.RAW_BYTES_FIELD_NUMBER,
        ])
        path_cond.bytes_match = path_regex

    for cond in self.proto_args.conditions:
      # TODO: Simplify condition creation with wrappers.
      cond_type = cond.condition_type
      if cond_type == flows_pb2.FileFinderCondition.MODIFICATION_TIME:
        if cond.modification_time.HasField("min_last_modified_time"):
          rrg_cond = action.AddFilter().conditions.add()
          rrg_cond.field.extend([
              rrg_get_file_metadata_pb2.Result.METADATA_FIELD_NUMBER,
              rrg_fs_pb2.FileMetadata.MODIFICATION_TIME_FIELD_NUMBER,
              timestamp_pb2.Timestamp.SECONDS_FIELD_NUMBER,
          ])
          rrg_cond.int64_less = math.floor(
              cond.modification_time.min_last_modified_time / 1e6,
          )
          rrg_cond.negated = True
        if cond.modification_time.HasField("max_last_modified_time"):
          rrg_cond = action.AddFilter().conditions.add()
          rrg_cond.field.extend([
              rrg_get_file_metadata_pb2.Result.METADATA_FIELD_NUMBER,
              rrg_fs_pb2.FileMetadata.MODIFICATION_TIME_FIELD_NUMBER,
              timestamp_pb2.Timestamp.SECONDS_FIELD_NUMBER,
          ])
          rrg_cond.int64_less = math.ceil(
              # `*_less` means "strictly less" so we add 1 to account for that.
              (cond.modification_time.max_last_modified_time + 1)
              / 1e6,
          )
      elif cond_type == flows_pb2.FileFinderCondition.ACCESS_TIME:
        if cond.access_time.HasField("min_last_access_time"):
          rrg_cond = action.AddFilter().conditions.add()
          rrg_cond.field.extend([
              rrg_get_file_metadata_pb2.Result.METADATA_FIELD_NUMBER,
              rrg_fs_pb2.FileMetadata.ACCESS_TIME_FIELD_NUMBER,
              timestamp_pb2.Timestamp.SECONDS_FIELD_NUMBER,
          ])
          rrg_cond.int64_less = math.floor(
              cond.access_time.min_last_access_time / 1e6,
          )
          rrg_cond.negated = True
        if cond.access_time.HasField("max_last_access_time"):
          rrg_cond = action.AddFilter().conditions.add()
          rrg_cond.field.extend([
              rrg_get_file_metadata_pb2.Result.METADATA_FIELD_NUMBER,
              rrg_fs_pb2.FileMetadata.ACCESS_TIME_FIELD_NUMBER,
              timestamp_pb2.Timestamp.SECONDS_FIELD_NUMBER,
          ])
          # `*_less` means "strictly less" so we add 1 to account for that.
          rrg_cond.int64_less = math.ceil(
              cond.access_time.max_last_access_time + 1 / 1e6,
          )
      elif cond_type == flows_pb2.FileFinderCondition.SIZE:
        if cond.size.HasField("min_file_size"):
          rrg_cond = action.AddFilter().conditions.add()
          rrg_cond.field.extend([
              rrg_get_file_metadata_pb2.Result.METADATA_FIELD_NUMBER,
              rrg_fs_pb2.FileMetadata.SIZE_FIELD_NUMBER,
          ])
          rrg_cond.uint64_less = cond.size.min_file_size
          rrg_cond.negated = True
        if cond.size.HasField("max_file_size"):
          rrg_cond = action.AddFilter().conditions.add()
          rrg_cond.field.extend([
              rrg_get_file_metadata_pb2.Result.METADATA_FIELD_NUMBER,
              rrg_fs_pb2.FileMetadata.SIZE_FIELD_NUMBER,
          ])
          # `*_less` means "strictly less" so we add 1 to account for that.
          rrg_cond.uint64_less = cond.size.max_file_size + 1
      elif cond_type == flows_pb2.FileFinderCondition.CONTENTS_REGEX_MATCH:
        if action.args.contents_regex:
          raise flow_base.FlowError(
              "Multiple content conditions not permitted (try rewriting regex)",
          )
        action.args.contents_regex = cond.contents_regex_match.regex
      elif cond_type == flows_pb2.FileFinderCondition.CONTENTS_LITERAL_MATCH:
        if action.args.contents_regex:
          raise flow_base.FlowError(
              "Multiple content conditions not permitted (try using regex)",
          )
        action.args.contents_regex = re.escape(
            cond.contents_literal_match.literal,
        )
      else:
        raise ValueError(f"Unsupported condition: {cond.condition_type}")

    action.Call(self._ProcessGetFileMetadata)

  @flow_base.UseProto2AnyResponses
  def _ProcessGetFileMetadata(
      self,
      responses: flow_responses.Responses[any_pb2.Any],
  ) -> None:
    if not responses.success:
      raise flow_base.FlowError(
          f"Failed to collect file metadata: {responses.status}",
      )

    self.GetProgressProto().files_found += len(responses)

    action_type = self.proto_args.action.action_type

    # Used if we need to compute file digest but we postponed it because of
    # conditions and need to call the action again (only on a subset of files).
    get_file_metadata = rrg_stubs.GetFileMetadata()
    get_file_metadata.args.md5 = True
    get_file_metadata.args.sha1 = True
    get_file_metadata.args.sha256 = True

    get_file_contents_paths = set()

    path_infos_by_path: dict[rrg_path.PurePath, objects_pb2.PathInfo] = {}
    for response_any in responses:
      response = rrg_get_file_metadata_pb2.Result()
      response.ParseFromString(response_any.value)

      path = rrg_path.PurePath.For(self.rrg_os_type, response.path)
      symlink = rrg_path.PurePath.For(self.rrg_os_type, response.symlink)

      path_info = rrg_fs.PathInfo(response.metadata)
      path_info.path_type = objects_pb2.PathInfo.PathType.OS
      path_info.components.extend(path.components)

      path_info.stat_entry.pathspec.pathtype = self.proto_args.pathtype
      path_info.stat_entry.pathspec.path = str(path)
      # TODO: Fix path separator in stat entries.
      if self.rrg_os_type == rrg_os_pb2.WINDOWS:
        path_info.stat_entry.pathspec.path = str(path).replace("\\", "/")

      if response.metadata.type == rrg_fs_pb2.FileMetadata.SYMLINK:
        path_info.stat_entry.symlink = str(symlink)
        # TODO: Add support for resolving symlinks (if required by
        # the action arguments).

      if response.md5:
        path_info.hash_entry.md5 = response.md5
      if response.sha1:
        path_info.hash_entry.sha1 = response.sha1
      if response.sha256:
        path_info.hash_entry.sha256 = response.sha256

      result = flows_pb2.FileFinderResult()
      result.stat_entry.CopyFrom(path_info.stat_entry)
      result.hash_entry.CopyFrom(path_info.hash_entry)

      if (
          action_type == flows_pb2.FileFinderAction.HASH
          and self.proto_args.conditions
          and response.metadata.type == rrg_fs_pb2.FileMetadata.FILE
      ):
        get_file_metadata.args.paths.add().raw_bytes = bytes(path)
        self.GetProgressProto().files_found -= 1
      elif (
          action_type == flows_pb2.FileFinderAction.DOWNLOAD
          and response.metadata.type == rrg_fs_pb2.FileMetadata.FILE
      ):
        get_file_contents_paths.add(path)
        self.store.results_pending_content.add().CopyFrom(result)
      else:
        path_infos_by_path[path] = path_info
        self.SendReplyProto(result)

    assert data_store.REL_DB is not None
    data_store.REL_DB.WritePathInfos(
        client_id=self.client_id,
        path_infos=list(path_infos_by_path.values()),
    )

    if get_file_metadata.args.paths:
      get_file_metadata.Call(self._ProcessGetFileMetadataHash)
    if action_type == flows_pb2.FileFinderAction.DOWNLOAD:
      get_file_contents = rrg_stubs.GetFileContents()

      for path in get_file_contents_paths:
        get_file_contents.args.paths.add().raw_bytes = bytes(path)

      get_file_contents.Call(self._ProcessGetFileContents)

  @flow_base.UseProto2AnyResponses
  def _ProcessGetFileMetadataHash(
      self,
      responses: flow_responses.Responses[any_pb2.Any],
  ) -> None:
    if not responses.success:
      raise flow_base.FlowError(
          f"Failed to collect file digests: {responses.status}",
      )

    self.GetProgressProto().files_found += len(responses)

    path_infos_by_path: dict[rrg_path.PurePath, objects_pb2.PathInfo] = {}
    for response_any in responses:
      response = rrg_get_file_metadata_pb2.Result()
      response.ParseFromString(response_any.value)

      path = rrg_path.PurePath.For(self.rrg_os_type, response.path)

      path_info = rrg_fs.PathInfo(response.metadata)
      path_info.path_type = objects_pb2.PathInfo.PathType.OS
      path_info.components.extend(path.components)

      path_info.stat_entry.pathspec.pathtype = self.proto_args.pathtype
      path_info.stat_entry.pathspec.path = str(path)
      # TODO: Fix path separator in stat entries.
      if self.rrg_os_type == rrg_os_pb2.WINDOWS:
        path_info.stat_entry.pathspec.path = str(path).replace("\\", "/")

      path_info.hash_entry.md5 = response.md5
      path_info.hash_entry.sha1 = response.sha1
      path_info.hash_entry.sha256 = response.sha256

      path_infos_by_path[path] = path_info

      result = flows_pb2.FileFinderResult()
      result.stat_entry.CopyFrom(path_info.stat_entry)
      result.hash_entry.CopyFrom(path_info.hash_entry)
      self.SendReplyProto(result)

    assert data_store.REL_DB is not None
    data_store.REL_DB.WritePathInfos(
        client_id=self.client_id,
        path_infos=list(path_infos_by_path.values()),
    )

  @flow_base.UseProto2AnyResponses
  def _ProcessGetFileContents(
      self,
      responses: flow_responses.Responses[any_pb2.Any],
  ) -> None:
    if not responses.success:
      raise flow_base.FlowError(
          f"Failed to collect file contents: {responses.status}",
      )

    results_by_path: dict[str, flows_pb2.FileFinderResult] = {}
    for result in self.store.results_pending_content:
      results_by_path[result.stat_entry.pathspec.path] = result

    responses_by_path = dict()
    blob_ids = set()

    for response_any in responses:
      response = rrg_get_file_contents_pb2.Result()
      response.ParseFromString(response_any.value)

      if response.error:
        self.Log(
            "Failed to collect content for '%s': %s",
            response.path,
            response.error,
        )

      path = rrg_path.PurePath.For(self.rrg_os_type, response.path)
      responses_by_path.setdefault(path, []).append(response)

      blob_ids.add(models_blobs.BlobID(response.blob_sha256))

    blob_ids_exist = data_store.BLOBS.CheckBlobsExist(blob_ids)

    blob_refs_by_client_path = {}

    responses_pending = list()

    # We use extra `list` call to get all the items upfront as we delete items
    # for which we still have pending blobs. The deletion happens as we iterate
    # which is not allowed in general. Since we delete an item only after it has
    # "been iterated", this is fine and we can list items upfront.
    for path, responses in list(responses_by_path.items()):
      client_path = db.ClientPath.OS(self.client_id, path.components)

      if not all(
          blob_ids_exist[models_blobs.BlobID(response.blob_sha256)]
          for response in responses
      ):
        responses_pending.extend(responses)
        del responses_by_path[path]
        continue

      path_str = str(path)
      # TODO: Fix path separator in stat entries.
      if self.rrg_os_type == rrg_os_pb2.WINDOWS:
        path_str = str(path).replace("\\", "/")

      result = results_by_path[path_str]

      responses.sort(key=lambda response: response.offset)

      for response, response_next in itertools.pairwise(responses):
        if response.offset + response.length != response_next.offset:
          raise flow_base.FlowError(
              f"Missing file content for {path!r}: "
              f"response at {response.offset} of length {response.length} "
              f"followed by response at {response_next.offset}"
          )

      for response in responses:
        result_chunk = result.transferred_file.chunks.add()
        result_chunk.offset = response.offset
        result_chunk.length = response.length
        result_chunk.digest = response.blob_sha256

        # We use length of the first response as the chunk size. They should all
        # (except the last one) should be of the same size, but determining the
        # first one is trivial and knowing whether any other is not-last is not.
        if response.offset == 0:
          result.transferred_file.chunk_size = response.length

        blob_ref = rdf_objects.BlobReference()
        blob_ref.offset = response.offset
        blob_ref.size = response.length
        blob_ref.blob_id = response.blob_sha256
        blob_refs_by_client_path.setdefault(client_path, []).append(blob_ref)

      self.SendReplyProto(result)

    hash_id_by_client_path = file_store.AddFilesWithUnknownHashes(
        blob_refs_by_client_path,
        use_external_stores=self.proto_args.action.download.use_external_stores,
    )

    path_infos = []

    for path in responses_by_path:
      client_path = db.ClientPath.OS(self.client_id, path.components)

      path_str = str(path)
      # TODO: Fix path separator in stat entries.
      if self.rrg_os_type == rrg_os_pb2.WINDOWS:
        path_str = str(path).replace("\\", "/")

      result = results_by_path[path_str]

      path_info = objects_pb2.PathInfo()
      path_info.path_type = objects_pb2.PathInfo.PathType.OS
      path_info.components.extend(path.components)
      path_info.directory = stat.S_ISDIR(result.stat_entry.st_mode)
      path_info.stat_entry.CopyFrom(result.stat_entry)
      path_info.hash_entry.CopyFrom(result.hash_entry)
      path_info.hash_entry.sha256 = hash_id_by_client_path[
          client_path
      ].AsBytes()
      path_infos.append(path_info)

    data_store.REL_DB.WritePathInfos(
        self.client_id,
        path_infos,
    )

    if responses_pending:
      self.store.num_blob_waits += 1
      if self.store.num_blob_waits > self.MAX_BLOB_CHECKS:
        raise flow_base.FlowError(
            f"Blob wait limit ({self.MAX_BLOB_CHECKS} attempts) reached "
            f"({len(responses_pending)} responses still pending)"
        )

      self.Log(
          "Waiting for blobs of %d responses to arrive in blobstore "
          "(attempt %d out of %d)",
          len(responses_pending),
          self.store.num_blob_waits,
          self.MAX_BLOB_CHECKS,
      )

      self.CallStateProto(
          next_state=self._ProcessGetFileContents.__name__,
          responses=responses_pending,
          start_time=rdfvalue.RDFDatetime.Now() + self.BLOB_CHECK_DELAY,
      )
    else:
      # TODO: For the time being we only clear this once all the
      # blobs arrived. We could do it more granularly as blobs can arrive part-
      # ially but deleting from a repeated Protocl Buffers field is not trivial
      # so we skip it for now.
      # TODO: Replace with `clear()` once upgraded.
      del self.store.results_pending_content[:]

  def _InterpolatePaths(self, globs: Sequence[str]) -> Optional[Sequence[str]]:
    kb: knowledge_base_pb2.KnowledgeBase = (
        self.client_knowledge_base or knowledge_base_pb2.KnowledgeBase()
    )

    paths = list()

    for glob in globs:
      interpolation = artifact_utils.KnowledgeBaseInterpolation(
          pattern=str(glob),
          kb=kb,
      )

      for log in interpolation.logs:
        self.Log("knowledgebase interpolation: %s", log)

      paths.extend(interpolation.results)

    if not paths:
      self.Error(
          "All globs skipped, as there's no knowledgebase available for"
          " interpolation"
      )
      return None

    return paths

  @flow_base.UseProto2AnyResponses
  def StoreResultsWithoutBlobs(
      self,
      responses: flow_responses.Responses[any_pb2.Any],
  ) -> None:
    """Stores the results returned by the client to the db."""
    if not responses.success:
      raise flow_base.FlowError(responses.status)

    self.GetProgressProto().files_found = len(responses)
    transferred_file_responses = []
    stat_entry_responses = []
    # Split the responses into the ones that just contain file stats
    # and the ones actually referencing uploaded chunks.
    for response_any in responses:
      response = flows_pb2.FileFinderResult()
      response_any.Unpack(response)

      if response.HasField("transferred_file"):
        transferred_file_responses.append(response)
      elif response.HasField("stat_entry"):
        stat_entry_responses.append(response)

    rdf_stat_entry_responses = [
        mig_file_finder.ToRDFFileFinderResult(r) for r in stat_entry_responses
    ]
    filesystem.WriteFileFinderResults(rdf_stat_entry_responses, self.client_id)
    for r in stat_entry_responses:
      self.SendReplyProto(r)

    if transferred_file_responses:
      self.CallStateInlineProto(
          next_state=self.StoreResultsWithBlobs.__name__,
          messages=transferred_file_responses,
      )

  @flow_base.UseProto2AnyResponses
  def StoreResultsWithBlobs(
      self,
      responses: flow_responses.Responses[any_pb2.Any],
  ) -> None:
    """Stores the results returned by the client to the db."""
    complete_responses: list[flows_pb2.FileFinderResult] = []
    incomplete_responses: list[flows_pb2.FileFinderResult] = []

    unpacked_responses: list[flows_pb2.FileFinderResult] = []
    for response in responses:
      res = flows_pb2.FileFinderResult()
      response.Unpack(res)
      unpacked_responses.append(res)

    response_pending_blob_ids = _GetPendingBlobIDs(unpacked_responses)
    # Needed in case we need to report an error (see below).
    sample_pending_blob_id: Optional[models_blobs.BlobID] = None
    num_pending_blobs = 0
    for response, pending_blob_ids in response_pending_blob_ids:
      if not pending_blob_ids:
        complete_responses.append(response)
      else:
        incomplete_responses.append(response)
        sample_pending_blob_id = list(pending_blob_ids)[0]
        num_pending_blobs += len(pending_blob_ids)

    client_path_hash_id = self._WriteFilesContent(complete_responses)

    for response in complete_responses:
      pathspec = response.stat_entry.pathspec
      rdf_pathspec = mig_paths.ToRDFPathSpec(pathspec)
      client_path = db.ClientPath.FromPathSpec(self.client_id, rdf_pathspec)

      try:
        # For files written to the file store we have their SHA-256 hash and can
        # put it into the response (as some systems depend on this information).
        #
        # Note that it is possible (depending on the agent implementation) that
        # the response already contains a SHA-256: in that case, it will just
        # get overridden which should not do any harm. In fact, it is better not
        # to trust the endpoint with this as the hash might have changed during
        # the transfer procedure and we will end up with inconsistent data.
        response.hash_entry.sha256 = client_path_hash_id[client_path].AsBytes()
      except KeyError:
        pass

      self.SendReplyProto(response)

    if incomplete_responses:
      self.store.num_blob_waits += 1

      self.Log(
          "Waiting for blobs to be written to the blob store. Iteration: %d out"
          " of %d. Blobs pending: %d",
          self.store.num_blob_waits,
          self.MAX_BLOB_CHECKS,
          num_pending_blobs,
      )

      if self.store.num_blob_waits > self.MAX_BLOB_CHECKS:
        self.Error(
            "Could not find one of referenced blobs "
            f"(sample id: {sample_pending_blob_id}). "
            "This is a sign of datastore inconsistency."
        )
        return

      start_time = rdfvalue.RDFDatetime.Now() + self.BLOB_CHECK_DELAY
      self.CallStateProto(
          next_state=self.StoreResultsWithBlobs.__name__,
          responses=incomplete_responses,
          start_time=start_time,
      )

  def _WriteFilesContent(
      self,
      complete_responses: list[flows_pb2.FileFinderResult],
  ) -> dict[db.ClientPath, rdf_objects.SHA256HashID]:
    """Writes file contents of multiple files to the relational database.

    Args:
      complete_responses: A list of file finder results to write to the file
        store.

    Returns:
        A mapping from paths to the SHA-256 hashes of the files written
        to the file store.
    """
    client_path_blob_refs = dict()
    client_path_path_info = dict()
    client_path_hash_id = dict()
    client_path_sizes = dict()

    for response in complete_responses:
      stat_entry = mig_client_fs.ToRDFStatEntry(response.stat_entry)
      path_info = rdf_objects.PathInfo.FromStatEntry(stat_entry)

      chunks = response.transferred_file.chunks
      chunks = sorted(chunks, key=lambda _: _.offset)

      client_path = db.ClientPath.FromPathInfo(self.client_id, path_info)
      blob_refs = []
      file_size = 0
      for c in chunks:
        blob_refs.append(
            rdf_objects.BlobReference(
                offset=c.offset, size=c.length, blob_id=c.digest
            )
        )
        file_size += c.length

      client_path_path_info[client_path] = path_info
      client_path_blob_refs[client_path] = blob_refs
      client_path_sizes[client_path] = file_size

    if client_path_blob_refs:
      use_external_stores = self.args.action.download.use_external_stores
      client_path_hash_id = file_store.AddFilesWithUnknownHashes(
          client_path_blob_refs, use_external_stores=use_external_stores
      )
      for client_path, hash_id in client_path_hash_id.items():
        path_info = client_path_path_info[client_path]
        path_info.hash_entry.sha256 = hash_id.AsBytes()
        path_info.hash_entry.num_bytes = client_path_sizes[client_path]

    path_infos = list(client_path_path_info.values())
    proto_path_infos = [mig_objects.ToProtoPathInfo(pi) for pi in path_infos]
    data_store.REL_DB.WritePathInfos(self.client_id, proto_path_infos)

    return client_path_hash_id

  def End(self) -> None:
    if self.GetProgressProto().files_found > 0:
      self.Log(
          "Found and processed %d files.", self.GetProgressProto().files_found
      )

  def GetProgressProto(self) -> flows_pb2.FileFinderProgress:
    return cast(flows_pb2.FileFinderProgress, self.progress)


# TODO decide on the FileFinder name and remove the legacy alias.
class FileFinder(ClientFileFinder):
  """An alias for ClientFileFinder."""

  friendly_name = "File Finder"
  behaviours = flow_base.BEHAVIOUR_BASIC
