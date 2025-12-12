#!/usr/bin/env python
"""Flows for handling the collection for artifacts."""
from collections.abc import Sequence
import hashlib
import itertools
import logging
import pathlib
import stat
from typing import Optional

from google.protobuf import any_pb2
from grr_response_core import config
from grr_response_core.lib import artifact_utils
from grr_response_core.lib import rdfvalue
from grr_response_core.lib.rdfvalues import artifacts as rdf_artifacts
from grr_response_core.lib.rdfvalues import client_action as rdf_client_action
from grr_response_core.lib.rdfvalues import client_fs as rdf_client_fs
from grr_response_core.lib.rdfvalues import file_finder as rdf_file_finder
from grr_response_core.lib.rdfvalues import mig_artifacts
from grr_response_core.lib.rdfvalues import mig_client
from grr_response_core.lib.rdfvalues import mig_client_fs
from grr_response_core.lib.rdfvalues import mig_file_finder
from grr_response_core.lib.rdfvalues import paths as rdf_paths
from grr_response_core.lib.rdfvalues import protodict as rdf_protodict
from grr_response_proto import artifact_pb2
from grr_response_proto import flows_pb2
from grr_response_proto import jobs_pb2
from grr_response_proto import objects_pb2
from grr_response_proto import signed_commands_pb2
from grr_response_server import artifact
from grr_response_server import artifact_registry
from grr_response_server import data_store
from grr_response_server import file_store
from grr_response_server import flow_base
from grr_response_server import flow_responses
from grr_response_server import rrg_fs
from grr_response_server import rrg_glob
from grr_response_server import rrg_path
from grr_response_server import rrg_stubs
from grr_response_server import rrg_winreg
from grr_response_server import server_stubs
from grr_response_server.databases import db as abstract_db
from grr_response_server.flows.general import discovery
from grr_response_server.flows.general import file_finder
from grr_response_server.flows.general import filesystem
from grr_response_server.flows.general import mig_transfer
from grr_response_server.flows.general import transfer
from grr_response_server.models import blobs as models_blobs
from grr_response_server.rdfvalues import mig_objects
from grr_response_proto.rrg import fs_pb2 as rrg_fs_pb2
from grr_response_proto.rrg import os_pb2 as rrg_os_pb2
from grr_response_proto.rrg import winreg_pb2 as rrg_winreg_pb2
from grr_response_proto.rrg.action import execute_signed_command_pb2 as rrg_execute_signed_command_pb2
from grr_response_proto.rrg.action import get_file_contents_pb2 as rrg_get_file_contents_pb2
from grr_response_proto.rrg.action import get_file_metadata_pb2 as rrg_get_file_metadata_pb2
from grr_response_proto.rrg.action import list_winreg_keys_pb2 as rrg_list_winreg_keys_pb2
from grr_response_proto.rrg.action import list_winreg_values_pb2 as rrg_list_winreg_values_pb2
from grr_response_proto.rrg.action import query_wmi_pb2 as rrg_query_wmi_pb2


def _ReadClientKnowledgeBase(client_id, allow_uninitialized=False):
  client = data_store.REL_DB.ReadClientSnapshot(client_id)
  if client is not None:
    client = mig_objects.ToRDFClientSnapshot(client)
  return artifact.GetKnowledgeBase(
      client, allow_uninitialized=allow_uninitialized
  )


class ArtifactCollectorFlow(
    flow_base.FlowBase[
        flows_pb2.ArtifactCollectorFlowArgs,
        flows_pb2.ArtifactCollectorFlowStore,
        flows_pb2.ArtifactCollectorFlowProgress,
    ]
):
  """Flow that takes a list of artifacts and collects them.

  This flow is the core of the Artifact implementation for GRR. Artifacts are
  defined using a standardized data format that includes what to collect and
  how to process the things collected. This flow takes that data driven format
  and makes it useful.

  The core functionality of Artifacts is split into ArtifactSources and
  Processors.

  An Artifact defines a set of ArtifactSources that are used to retrieve data
  from the client. These can specify collection of files, registry keys, command
  output and others. The first part of this flow "Collect" handles running those
  collections by issuing GRR flows and client actions.

  The results of those are then collected and GRR searches for Processors that
  know how to process the output of the ArtifactSources.

  So this flow hands off the collected rdfvalue results to the Processors which
  then return modified or different rdfvalues. These final results are then
  either:
  1. Sent to the calling flow.
  2. Written to a collection.
  """

  category = "/Collectors/"
  args_type = rdf_artifacts.ArtifactCollectorFlowArgs
  proto_args_type = flows_pb2.ArtifactCollectorFlowArgs

  progress_type = rdf_artifacts.ArtifactCollectorFlowProgress
  proto_progress_type = flows_pb2.ArtifactCollectorFlowProgress

  proto_store_type = flows_pb2.ArtifactCollectorFlowStore

  only_protos_allowed = True

  result_types = (
      rdf_protodict.Dict,
      rdf_client_fs.StatEntry,
      rdf_client_action.ExecuteResponse,
      # ArtifactCollectorFlow has many more result types. For now, only result
      # types required for UI type generation are captured here, add other
      # types when needed.
      rdfvalue.RDFValue,
  )
  proto_result_types = (
      jobs_pb2.StatEntry,
      jobs_pb2.ExecuteResponse,
      jobs_pb2.Dict,
  )
  behaviours = flow_base.BEHAVIOUR_BASIC

  _BLOB_WAIT_DELAY = rdfvalue.Duration.From(60, rdfvalue.SECONDS)
  _BLOB_WAIT_COUNT_LIMIT = 5

  def Start(self):
    """For each artifact, create subflows for each collector."""
    # We only want to copy if it is set and not empty.
    # ListFields returns a list of fields that are set (if empty list, we copy).
    if (
        self.proto_args.HasField("knowledge_base")
        and self.proto_args.knowledge_base.ListFields()
    ):
      self.store.knowledge_base.CopyFrom(self.proto_args.knowledge_base)
    self.progress = flows_pb2.ArtifactCollectorFlowProgress()

    if not self.store.HasField("knowledge_base"):
      # If not provided, get a knowledge base from the client.
      try:
        kb = mig_client.ToProtoKnowledgeBase(
            _ReadClientKnowledgeBase(self.client_id)
        )
        self.store.knowledge_base.CopyFrom(kb)
      except artifact_utils.KnowledgeBaseUninitializedError:
        # If no-one has ever initialized the knowledge base, we should do so
        # now.
        self.CallFlowProto(
            discovery.Interrogate.__name__,
            next_state=self.StartCollection.__name__,
        )
        return

    # In all other cases start the collection state.
    self.CallStateProto(next_state=self.StartCollection.__name__)

  def _GetArtifactFromName(self, name):
    """Gets an artifact from the registry, refreshing the registry if needed."""
    try:
      return artifact_registry.REGISTRY.GetArtifact(name)
    except rdf_artifacts.ArtifactNotRegisteredError:
      # If we don't have an artifact, things shouldn't have passed validation
      # so we assume it's a new one in the datastore.
      artifact_registry.REGISTRY.ReloadDatastoreArtifacts()
      return artifact_registry.REGISTRY.GetArtifact(name)

  @flow_base.UseProto2AnyResponses
  def StartCollection(
      self, responses: flow_responses.Responses[any_pb2.Any]
  ) -> None:
    """Start collecting."""
    if not responses.success:
      raise artifact_utils.KnowledgeBaseUninitializedError(
          "Attempt to initialize Knowledge Base failed."
      )

    if not self.store.knowledge_base:
      self.store.knowledge_base.CopyFrom(
          mig_client.ToProtoKnowledgeBase(
              _ReadClientKnowledgeBase(self.client_id, allow_uninitialized=True)
          )
      )

    for artifact_name in self.proto_args.artifact_list:
      artifact_obj = self._GetArtifactFromName(artifact_name)

      # Ensure artifact has been written sanely. Note that this could be
      # removed if it turns out to be expensive. Artifact tests should catch
      # these.
      artifact_registry.Validate(artifact_obj)

      self._Collect(artifact_obj)

  def _Collect(self, artifact_obj: rdf_artifacts.Artifact) -> None:
    """Collect the raw data from the client for this artifact."""
    artifact_name = str(artifact_obj.name)

    # Ensure attempted artifacts are shown in progress, even with 0 results.
    progress = self._GetOrInsertArtifactProgress(artifact_name)

    if not MeetsOSConditions(self.store.knowledge_base, artifact_obj):
      logging.debug(
          "%s: Artifact %s not supported on os %s (options %s)",
          self.client_id,
          artifact_name,
          self.store.knowledge_base.os,
          artifact_obj.supported_os,
      )
      progress.status = (
          flows_pb2.ArtifactProgress.Status.SKIPPED_DUE_TO_OS_CONDITION
      )
      return

    sources_ran = 0
    # Call the source defined action for each source.
    for source in artifact_obj.sources:
      if not MeetsOSConditions(self.store.knowledge_base, source):
        continue

      sources_ran += 1

      type_name = source.type
      source_type = rdf_artifacts.ArtifactSource.SourceType
      self.current_artifact_name = artifact_name
      if type_name == source_type.COMMAND:
        self._RunCommand(source)
      elif type_name == source_type.PATH:
        self._GetPaths(
            source,
            flows_pb2.FileFinderAction(
                action_type=flows_pb2.FileFinderAction.Action.STAT
            ),
        )
      elif type_name == source_type.FILE:
        self._GetPaths(
            source,
            flows_pb2.FileFinderAction(
                action_type=flows_pb2.FileFinderAction.Action.DOWNLOAD,
                download=flows_pb2.FileFinderDownloadActionOptions(
                    max_size=self.proto_args.max_file_size
                    if self.proto_args.HasField("max_file_size")
                    else 500000000,  # Defaults to 500 MB
                ),
            ),
        )
      elif type_name == source_type.REGISTRY_KEY:
        self._GetRegistryKey(source)
      elif type_name == source_type.REGISTRY_VALUE:
        self._GetRegistryValue(source)
      elif type_name == source_type.WMI:
        self._WMIQuery(source)
      elif type_name == source_type.ARTIFACT_GROUP:
        self._CollectArtifacts(source)
      else:
        raise RuntimeError("Invalid type %s in %s" % (type_name, artifact_name))

    if sources_ran == 0:
      logging.debug(
          "Artifact %s no sources run due to all sources "
          "having failing conditions on %s",
          artifact_name,
          self.client_id,
      )

  def _GetPaths(
      self,
      source: rdf_artifacts.ArtifactSource,
      action: flows_pb2.FileFinderAction,
  ):
    """Get a set of files."""
    if (
        # RRG at version at least 0.0.3 is required as previous ones do not
        # support collection of multiple files.
        self.rrg_version >= (0, 0, 3)
        # RRG at version at least 0.0.7 is required as previous ones might trip
        # over Fleetspeak message limit when calling `get_file_contents`.
        and (
            source.type != artifact_pb2.ArtifactSource.FILE
            or self.rrg_version >= (0, 0, 7)
        )
        # Raw filesystem access is not supported in RRG yet.
        and not self.args.use_raw_filesystem_access
    ):
      if self.client_os in ["Linux", "Darwin"]:
        path_cls = pathlib.PurePosixPath
      elif self.client_os == "Windows":
        path_cls = pathlib.PureWindowsPath
      else:
        raise flow_base.FlowError(f"Unexpected OS: {self.client_os}")

      action = rrg_stubs.GetFileMetadata()

      path_regexes = []
      path_pruning_regexes = []

      for path in self._InterpolateList(source.attributes.get("paths", [])):
        glob = rrg_glob.Glob(path_cls(path))

        action.args.paths.add().raw_bytes = bytes(glob.root)
        action.args.max_depth = max(action.args.max_depth, glob.root_level)

        path_regexes.append(glob.regex.pattern)
        path_pruning_regexes.append(glob.pruning_regex.pattern)

      if action.args.max_depth > 0:
        action.args.path_pruning_regex = "|".join(path_pruning_regexes)

        # Path pruning can yield additional entries (as it is used to guide the
        # search, not to filter results). Thus, we use filter to only return
        # what we are actually interested in.
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

      action.context["artifact_name"] = str(self.current_artifact_name)
      if source.type == artifact_pb2.ArtifactSource.PATH:
        action.Call(self._ProcessRRGGetFileMetadata)
      elif source.type == artifact_pb2.ArtifactSource.FILE:
        action.Call(self._ProcessRRGGetFileMetadataThenCollect)

      return

    flow_args = flows_pb2.FileFinderArgs(
        paths=self._InterpolateList(source.attributes.get("paths", [])),
        action=action,
    )

    if self.args.use_raw_filesystem_access:
      if self.client_os == "Windows":
        flow_args.pathtype = config.CONFIG[
            "Server.raw_filesystem_access_pathtype"
        ]
      else:
        flow_args.pathtype = jobs_pb2.PathSpec.PathType.TSK
    else:
      flow_args.pathtype = jobs_pb2.PathSpec.PathType.OS

    if self.args.HasField("implementation_type"):
      flow_args.implementation_type = self.args.implementation_type

    self.CallFlowProto(
        file_finder.ClientFileFinder.__name__,
        flow_args=flow_args,
        request_data={
            "artifact_name": self.current_artifact_name,
            "source": source.ToPrimitiveDict(),
        },
        next_state=self.ProcessFileFinderResults.__name__,
    )

  @flow_base.UseProto2AnyResponses
  def _ProcessRRGGetFileMetadata(
      self,
      responses: flow_responses.Responses[any_pb2.Any],
  ) -> None:
    artifact_name = responses.request_data["artifact_name"]
    artifact_progress = self._GetOrInsertArtifactProgress(artifact_name)

    if not responses.success:
      self.Log(
          "File metadata collection for artifact %r failed : %s",
          artifact_name,
          responses.status,
      )
      artifact_progress.status = flows_pb2.ArtifactProgress.Status.FAILURE
      return

    artifact_progress.status = flows_pb2.ArtifactProgress.Status.SUCCESS
    artifact_progress.num_results += len(responses)

    path_infos = self._ParseRRGGetFileMetadataResponses(responses)
    data_store.REL_DB.WritePathInfos(self.client_id, path_infos)

  @flow_base.UseProto2AnyResponses
  def _ProcessRRGGetFileMetadataThenCollect(
      self,
      responses: flow_responses.Responses[any_pb2.Any],
  ) -> None:
    artifact_name = responses.request_data["artifact_name"]
    artifact_progress = self._GetOrInsertArtifactProgress(artifact_name)

    if not responses.success:
      self.Log(
          "File metadata collection for artifact %r failed : %s",
          artifact_name,
          responses.status,
      )
      artifact_progress.status = flows_pb2.ArtifactProgress.Status.FAILURE
      return

    path_infos = self._ParseRRGGetFileMetadataResponses(responses)

    # We won't get any blobs for empty files and thus we do not need to even
    # make an additional action call for them. We just prefill their hash and
    # write them to the filestore right away.
    empty_path_infos = []
    empty_client_paths = []

    for path_info in path_infos:
      if (
          stat.S_ISREG(path_info.stat_entry.st_mode)
          and path_info.stat_entry.st_size == 0
      ):
        empty_path_infos.append(path_info)
        empty_client_paths.append(
            abstract_db.ClientPath.OS(
                client_id=self.client_id,
                components=path_info.components,
            )
        )

    if empty_client_paths:
      empty_blob_id = data_store.BLOBS.WriteBlobWithUnknownHash(b"")

      empty_blob_ref = objects_pb2.BlobReference()
      empty_blob_ref.offset = 0
      empty_blob_ref.size = 0
      empty_blob_ref.blob_id = bytes(empty_blob_id)
      empty_blob_ref = mig_objects.ToRDFBlobReference(empty_blob_ref)

      file_store.AddFilesWithUnknownHashes(
          {client_path: [empty_blob_ref] for client_path in empty_client_paths},
          use_external_stores=False,
      )

      for path_info in empty_path_infos:
        path_info.hash_entry.sha256 = hashlib.sha256(b"").digest()

    data_store.REL_DB.WritePathInfos(self.client_id, path_infos)

    get_file_contents_paths_bytes = set()

    for response_any in responses:
      response = rrg_get_file_metadata_pb2.Result()
      response.ParseFromString(response_any.value)

      if response.metadata.type == rrg_fs_pb2.FileMetadata.Type.FILE:
        get_file_contents_paths_bytes.add(response.path.raw_bytes)

    self.store.blob_wait_count = 0
    self.store.path_infos.extend(path_infos)

    if get_file_contents_paths_bytes:
      get_file_contents = rrg_stubs.GetFileContents()
      get_file_contents.context["artifact_name"] = artifact_name

      for path_bytes in get_file_contents_paths_bytes:
        get_file_contents.args.paths.add().raw_bytes = path_bytes

      get_file_contents.Call(self._ProcessRRGGetFileContents)

  def _ParseRRGGetFileMetadataResponses(
      self,
      responses: flow_responses.Responses[any_pb2.Any],
  ) -> Sequence[objects_pb2.PathInfo]:
    artifact_name = responses.request_data["artifact_name"]
    artifact_progress = self._GetOrInsertArtifactProgress(artifact_name)

    if not responses.success:
      self.Log(
          "File content collection for artifact %r failed : %s",
          artifact_name,
          responses.status,
      )
      artifact_progress.status = flows_pb2.ArtifactProgress.Status.FAILURE
      return []

    artifact_progress.status = flows_pb2.ArtifactProgress.Status.SUCCESS
    artifact_progress.num_results += len(responses)

    # It is possible to receive duplicated entries in case the action invocation
    # had some overlapping paths (e.g. the same path twice). Thus we accumulate
    # responses into a dictionary indexed by path to collapse these.
    responses_by_path = {}

    for response_any in responses:
      response = rrg_get_file_metadata_pb2.Result()
      response.ParseFromString(response_any.value)

      # TODO: For now we return all responses but this way we will
      # also return results the user did not ask about because of the way
      # globbing works. Returning more than necessary is not wrong per se, but
      # we should filter responses to retain only those that the user expects.

      path = rrg_path.PurePath.For(self.rrg_os_type, response.path)

      # In case of duplicate path generally the entries should be the same, but
      # it is possible that e.g. the file was modified inbetween two stat calls.
      # We retain the last entry but log that we did discard a different record.
      if path in responses_by_path and responses_by_path[path] != response:
        self.Log(
            "Duplicated metadata for '%s', discarding: %r",
            path,
            responses_by_path[path],
        )

      responses_by_path[path] = response

    path_infos: list[objects_pb2.PathInfo] = []

    for path, response in responses_by_path.items():
      symlink = rrg_path.PurePath.For(self.rrg_os_type, response.symlink)

      result = rrg_fs.StatEntry(response.metadata)
      result.pathspec.pathtype = jobs_pb2.PathSpec.PathType.OS
      result.pathspec.path = str(path)
      # TODO: Fix path separator in stat entries.
      if self.rrg_os_type == rrg_os_pb2.WINDOWS:
        result.pathspec.path = str(path).replace("\\", "/")

      if response.metadata.type == rrg_fs_pb2.FileMetadata.Type.SYMLINK:
        result.symlink = str(symlink)

      self.SendReplyProto(result, tag=f"artifact:{artifact_name}")

      path_info = objects_pb2.PathInfo()
      path_info.path_type = objects_pb2.PathInfo.PathType.OS
      path_info.components.extend(path.components)

      if response.metadata.type == rrg_fs_pb2.FileMetadata.DIR:
        path_info.directory = True

      path_info.stat_entry.CopyFrom(result)
      path_infos.append(path_info)

    return path_infos

  @flow_base.UseProto2AnyResponses
  def _ProcessRRGGetFileContents(
      self,
      responses: flow_responses.Responses[any_pb2.Any],
  ) -> None:
    artifact_name = responses.request_data["artifact_name"]
    artifact_progress = self._GetOrInsertArtifactProgress(artifact_name)

    if not responses.success:
      self.Log(
          "File content collection for artifact %r failed: %s",
          artifact_name,
          responses.status,
      )
      artifact_progress.status = flows_pb2.ArtifactProgress.Status.FAILURE
      return

    responses_by_path = {}

    for response_any in responses:
      response = rrg_get_file_contents_pb2.Result()
      response.ParseFromString(response_any.value)

      path = rrg_path.PurePath.For(self.rrg_os_type, response.path)

      if response.error:
        self.Log(
            "File content collection for path %r (artifact %r) failed: %s",
            path,
            artifact_name,
            response.error,
        )
        continue

      responses_by_path.setdefault(path, []).append(response)

    # First we verify that the results are "complete", that is: there are no
    # gaps in the content we collected. We do it be ensuring that all responses
    # for particular file form a continuous sequence. This should always be the
    # case or otherwise the action should have reported an error, so we fail
    # hard in case the assumption does not hold.

    for path, responses in responses_by_path.items():
      responses.sort(key=lambda _: _.offset)

      for response, response_next in itertools.pairwise(responses):
        if response.offset + response.length != response_next.offset:
          raise flow_base.FlowError(
              f"Missing file content for {path!r}: "
              f"response at {response.offset} of length {response.length} "
              f"followed by response at {response_next.offset}"
          )

      # TODO: We verified all the responses pairwise but we did
      # not check that the last response matches the whole expected file size.
      # This we could get from the file metadata collection. It's not a big deal
      # so we skip it for now.

    # Now we verify that blobs arrived in blobstore. It is okay if this is not
    # the case (as they are sent through a separate channel and flow processing
    # might have kicked in before blobstore accepted them).

    blob_ids_pending: set[models_blobs.BlobID] = set()

    for responses in responses_by_path.values():
      for response in responses:
        blob_ids_pending.add(models_blobs.BlobID(response.blob_sha256))

    for blob_id, exists in data_store.BLOBS.CheckBlobsExist(
        blob_ids_pending
    ).items():
      if exists:
        blob_ids_pending.remove(blob_id)

    if blob_ids_pending:
      self.store.blob_wait_count += 1
      if self.store.blob_wait_count > self._BLOB_WAIT_COUNT_LIMIT:
        raise flow_base.FlowError(
            f"Reached blob wait limit ({len(blob_ids_pending)} blobs pending)",
        )

      self.Log(
          "Waiting for %d blobs to arrive in blobstore (attempt %d out of %d)",
          len(blob_ids_pending),
          self.store.blob_wait_count,
          self._BLOB_WAIT_COUNT_LIMIT,
      )

      self.CallStateProto(
          next_state=self._ProcessRRGGetFileContents.__name__,
          responses=list(
              itertools.chain.from_iterable(responses_by_path.values())
          ),
          request_data={"artifact_name": artifact_name},
          start_time=rdfvalue.RDFDatetime.Now() + self._BLOB_WAIT_DELAY,
      )
      return

    # Finally, we build association between collected blobs and paths that is to
    # be stored in the file store.

    blob_refs_by_client_path = {}

    for path, responses in responses_by_path.items():
      blob_refs = blob_refs_by_client_path.setdefault(
          abstract_db.ClientPath.OS(self.client_id, path.components),
          [],
      )

      for response in responses:
        blob_ref = objects_pb2.BlobReference()
        blob_ref.offset = response.offset
        blob_ref.size = response.length
        blob_ref.blob_id = response.blob_sha256

        blob_refs.append(mig_objects.ToRDFBlobReference(blob_ref))

    hash_ids_by_client_path = file_store.AddFilesWithUnknownHashes(
        blob_refs_by_client_path,
        use_external_stores=False,
    )

    path_infos_with_content = []
    path_infos_without_content = []

    for path_info in self.store.path_infos:
      client_path = abstract_db.ClientPath.OS(
          client_id=self.client_id,
          components=path_info.components,
      )

      try:
        hash_id = hash_ids_by_client_path[client_path]
      except KeyError:
        path_infos_without_content.append(path_info)
      else:
        path_info.hash_entry.sha256 = hash_id.AsBytes()
        path_infos_with_content.append(path_info)

    # `path_infos_with_content` can contain duplicated values (if the artifact
    # specifies the same file twice or multiple artifacts have a file overlap),
    # so we need to de-duplicate them by path.
    path_infos_with_content = {
        tuple(path_info.components): path_info
        for path_info in path_infos_with_content
    }.values()

    data_store.REL_DB.WritePathInfos(
        self.client_id,
        path_infos_with_content,
    )

    # We delete path infos from the store to free up space since they will be of
    # no use anymore. We only delete paths for which we collected content.
    #
    # For efficiency reasons, we clear the list and re-add path infos that are
    # still missing content.
    # TODO: Replace with `clear()` once upgraded.
    del self.store.path_infos[:]
    self.store.path_infos.extend(path_infos_without_content)

  @flow_base.UseProto2AnyResponses
  def ProcessFileFinderResults(
      self, responses: flow_responses.Responses[any_pb2.Any]
  ) -> None:
    """Process the results of a file finder flow."""
    if not responses.success:
      self.Log(
          "Failed to fetch files %s" % responses.request_data["artifact_name"]
      )
    else:
      stat_entries = []
      for r in responses:
        result = flows_pb2.FileFinderResult()
        r.Unpack(result)
        if result.HasField("stat_entry"):
          stat_entries.append(result.stat_entry)
      self.CallStateInlineProto(
          next_state=self.ProcessCollected.__name__,
          request_data=responses.request_data,
          messages=stat_entries,
      )

  def _GetRegistryKey(self, source: rdf_artifacts.ArtifactSource) -> None:
    artifact_name = str(self.current_artifact_name)

    if self.rrg_support:
      source = mig_artifacts.ToProtoArtifactSource(source)

      for attr_kv in source.attributes.dat:
        if attr_kv.k.string != "keys":
          raise flow_base.FlowError(f"Non-keys attribute: {attr_kv}")
        if not attr_kv.v.list.content:
          raise flow_base.FlowError(f"Invalid keys attribute: {attr_kv}")

        for attr_key in attr_kv.v.list.content:
          if not attr_key.string:
            raise flow_base.FlowError(f"Invalid key attribute: {attr_key}")

          for key in self._Interpolate(attr_key.string):
            # Despite a slightly confusing name of the source (`REGISTRY_KEY`,
            # not `REGISTRY_VALUE`) we are interested in _subkeys_ and _values_
            # (all!) of the _key_.
            #
            # Thus we need to use `list_winreg_values` and `list_winreg_keys`.
            list_winreg_values = rrg_stubs.ListWinregValues()
            list_winreg_keys = rrg_stubs.ListWinregKeys()

            try:
              hkey, key = key.split("\\", 1)
            except ValueError as error:
              raise flow_base.FlowError(
                  f"Invalid registry key: {key}",
              ) from error

            try:
              list_winreg_values.args.root = rrg_winreg.HKEY_ENUM[hkey]
              list_winreg_keys.args.root = rrg_winreg.HKEY_ENUM[hkey]
            except KeyError as error:
              raise flow_base.FlowError(
                  f"Unexpected root key: {hkey}",
              ) from error

            key_glob = rrg_winreg.KeyGlob(key)

            list_winreg_values.args.key = key_glob.root
            list_winreg_values.args.max_depth = key_glob.root_level

            list_winreg_keys.args.key = key_glob.root
            # Subkeys are counted as one level deeper, so we need to have an
            # extra `+ 1` compared to values.
            list_winreg_keys.args.max_depth = key_glob.root_level + 1

            # Because walking can return excessive entries, we use RRG filters
            # to skip those keys that do not match the glob exactly.
            key_glob_cond = list_winreg_values.AddFilter().conditions.add()
            key_glob_cond.string_match = key_glob.regex.pattern
            key_glob_cond.field.extend([
                rrg_list_winreg_values_pb2.Result.KEY_FIELD_NUMBER,
            ])

            list_winreg_values.context["artifact_name"] = artifact_name
            list_winreg_values.Call(self._ProcessRRGListWinregValues)

            # We only need to do extra filtering if there is a glob. If there is
            # no globbing, we simply return all subkeys.
            if key != key_glob.root:
              # `list_winreg_keys` reports the result by splitting the key into
              # the root key and a subkey. We want to match only on the subkey
              # as this is the globbed part.
              key_suffix = key.removeprefix(key_glob.root).removeprefix("\\")
              key_suffix_glob = rrg_winreg.KeyGlob(key_suffix + "\\*")

              subkey_glob_cond = list_winreg_keys.AddFilter().conditions.add()
              subkey_glob_cond.string_match = key_suffix_glob.regex.pattern
              subkey_glob_cond.field.extend([
                  rrg_list_winreg_keys_pb2.Result.SUBKEY_FIELD_NUMBER,
              ])
              list_winreg_keys.AddFilter().conditions.append(subkey_glob_cond)

            list_winreg_keys.context["artifact_name"] = artifact_name
            list_winreg_keys.Call(self._ProcessRRGListWinregKeys)

      return

    self.CallFlowProto(
        file_finder.ClientFileFinder.__name__,
        flow_args=mig_file_finder.ToProtoFileFinderArgs(
            rdf_file_finder.FileFinderArgs(
                paths=self._InterpolateList(source.attributes.get("keys", [])),
                pathtype=rdf_paths.PathSpec.PathType.REGISTRY,
                action=rdf_file_finder.FileFinderAction.Stat(),
            )
        ),
        request_data={
            "artifact_name": self.current_artifact_name,
            "source": source.ToPrimitiveDict(),
        },
        next_state=self.ProcessFileFinderKeys.__name__,
    )

  @flow_base.UseProto2AnyResponses
  def _ProcessRRGListWinregValues(
      self,
      responses: flow_responses.Responses[any_pb2.Any],
  ) -> None:
    artifact_name = responses.request_data["artifact_name"]
    artifact_progress = self._GetOrInsertArtifactProgress(artifact_name)

    if not responses.success:
      self.Log(
          "Registry values collection for artifact %s failed: %s",
          artifact_name,
          responses.status,
      )
      return

    artifact_progress.status = flows_pb2.ArtifactProgress.Status.SUCCESS
    artifact_progress.num_results += len(responses)

    for response_any in responses:
      response = rrg_list_winreg_values_pb2.Result()
      response.ParseFromString(response_any.value)

      self.SendReplyProto(
          rrg_winreg.StatEntryOfValueResult(response),
          tag=f"artifact:{artifact_name}",
      )

  @flow_base.UseProto2AnyResponses
  def _ProcessRRGListWinregKeys(
      self,
      responses: flow_responses.Responses[any_pb2.Any],
  ) -> None:
    artifact_name = responses.request_data["artifact_name"]
    artifact_progress = self._GetOrInsertArtifactProgress(artifact_name)

    if not responses.success:
      self.Log(
          "Registry subkeys collection for artifact %s failed: %s",
          artifact_name,
          responses.status,
      )
      return

    artifact_progress.status = flows_pb2.ArtifactProgress.Status.SUCCESS
    artifact_progress.num_results += len(responses)

    for response_any in responses:
      response = rrg_list_winreg_keys_pb2.Result()
      response.ParseFromString(response_any.value)

      self.SendReplyProto(
          rrg_winreg.StatEntryOfKeyResult(response),
          tag=f"artifact:{artifact_name}",
      )

  def _GetRegistryValue(self, source: rdf_artifacts.ArtifactSource) -> None:
    """Retrieve directly specified registry values, returning Stat objects."""
    if self.rrg_support:
      source = mig_artifacts.ToProtoArtifactSource(source)

      if len(source.attributes.dat) != 1:
        raise flow_base.FlowError(
            f"Unexpected attributes: {source.attributes.dat}",
        )

      attr_kv = source.attributes.dat[0]
      if attr_kv.k.string != "key_value_pairs":
        raise flow_base.FlowError(f"Non key value pairs attribute: {attr_kv}")
      if not attr_kv.v.list.content:
        raise flow_base.FlowError(f"Invalid key value pairs: {attr_kv}")

      for kv_pair in attr_kv.v.list.content:
        if not kv_pair.dict.dat:
          raise flow_base.FlowError(f"Invalid key value pair: {kv_pair}")

        attr_key: Optional[str] = None
        attr_value: Optional[str] = None

        for attr_kv in kv_pair.dict.dat:
          if attr_kv.k.string == "key":
            if not attr_kv.v.string:
              raise flow_base.FlowError(f"Invalid key attribute: {attr_kv.v}")
            attr_key = attr_kv.v.string
          elif attr_kv.k.string == "value":
            if not attr_kv.v.string:
              raise flow_base.FlowError(f"Invalid value attribute: {attr_kv.v}")
            attr_value = attr_kv.v.string
          else:
            raise flow_base.FlowError(f"Unexpected attribute: {attr_kv}")

        if attr_key is None:
          raise flow_base.FlowError("Missing key attribute")
        if attr_value is None:
          raise flow_base.FlowError("Missing value attribute")

        for key in self._Interpolate(attr_key):
          action = rrg_stubs.ListWinregValues()

          try:
            hkey, key = key.split("\\", 1)
          except ValueError as error:
            raise flow_base.FlowError(f"Invalid registry key: {key}") from error

          try:
            action.args.root = rrg_winreg.HKEY_ENUM[hkey]
          except KeyError as error:
            raise flow_base.FlowError(f"Unexpected root key: {hkey}") from error

          key_glob = rrg_winreg.KeyGlob(key)
          action.args.key = key_glob.root
          action.args.max_depth = key_glob.root_level

          # Because walking can return excessive entries, we use RRG filters
          # to skip those keys that do not match the glob exactly.
          glob_cond = action.AddFilter().conditions.add()
          glob_cond.string_match = key_glob.regex.pattern
          glob_cond.field.extend([
              rrg_list_winreg_values_pb2.Result.KEY_FIELD_NUMBER,
          ])

          value_cond = action.AddFilter().conditions.add()
          value_cond.string_equal = attr_value
          value_cond.field.extend([
              rrg_list_winreg_values_pb2.Result.VALUE_FIELD_NUMBER,
              rrg_winreg_pb2.Value.NAME_FIELD_NUMBER,
          ])

          action.context["artifact_name"] = str(self.current_artifact_name)
          action.Call(self._ProcessRRGListWinregValues)

      return

    new_paths = set()
    has_glob = False
    for kvdict in source.attributes["key_value_pairs"]:
      if "*" in kvdict["key"] or rdf_paths.GROUPING_PATTERN.search(
          kvdict["key"]
      ):
        has_glob = True

      if kvdict["value"]:
        # This currently only supports key value pairs specified using forward
        # slash.
        path = "\\".join((kvdict["key"], kvdict["value"]))
      else:
        # If value is not set, we want to get the default value. In
        # GRR this is done by specifying the key only, so this is what
        # we do here.
        path = kvdict["key"]

      interpolation = artifact_utils.KnowledgeBaseInterpolation(
          pattern=path,
          kb=self.store.knowledge_base,
      )

      for log in interpolation.logs:
        self.Log("knowledgebase registry path interpolation: %s", log)

      if (
          not interpolation.results
          and not self.proto_args.ignore_interpolation_errors
      ):
        raise flow_base.FlowError(f"Registry path {path!r} interpolation error")

      new_paths.update(interpolation.results)

    if has_glob:
      self.CallFlowProto(
          file_finder.ClientFileFinder.__name__,
          flow_args=mig_file_finder.ToProtoFileFinderArgs(
              rdf_file_finder.FileFinderArgs(
                  paths=new_paths,
                  pathtype=rdf_paths.PathSpec.PathType.REGISTRY,
                  action=rdf_file_finder.FileFinderAction.Stat(),
              )
          ),
          request_data={
              "artifact_name": self.current_artifact_name,
              "source": source.ToPrimitiveDict(),
          },
          next_state=self.ProcessFileFinderKeys.__name__,
      )
    else:
      # We call statfile directly for keys that don't include globs because it
      # is faster and some artifacts rely on getting an IOError to trigger
      # fallback processing.
      for new_path in new_paths:
        pathspec = jobs_pb2.PathSpec(
            path=new_path, pathtype=jobs_pb2.PathSpec.PathType.REGISTRY
        )

        self.CallClientProto(
            server_stubs.GetFileStat,
            jobs_pb2.GetFileStatRequest(pathspec=pathspec),
            request_data={
                "artifact_name": self.current_artifact_name,
                "source": source.ToPrimitiveDict(),
            },
            next_state=self.ProcessCollectedRegistryStatEntry.__name__,
        )

  @flow_base.UseProto2AnyResponses
  def ProcessFileFinderKeys(
      self,
      responses: flow_responses.Responses[any_pb2.Any],
  ) -> None:
    if not responses.success:
      self.Log(
          "Failed to fetch keys %s" % responses.request_data["artifact_name"]
      )
    # We're only interested in the `StatEntry`s, not  `FileFinderResult`s.
    stat_entries = []
    for r in responses:
      result = flows_pb2.FileFinderResult()
      r.Unpack(result)
      if result.HasField("stat_entry"):
        stat_entries.append(result.stat_entry)
    if stat_entries:
      self.CallStateInlineProto(
          next_state=self.ProcessCollected.__name__,
          request_data=responses.request_data,
          messages=stat_entries,
      )

  def _StartSubArtifactCollector(
      self,
      artifact_list: Sequence[rdf_artifacts.ArtifactName],
      source: rdf_artifacts.ArtifactSource,
      next_state: str,
  ) -> None:
    self.CallFlowProto(
        ArtifactCollectorFlow.__name__,
        flow_args=mig_artifacts.ToProtoArtifactCollectorFlowArgs(
            rdf_artifacts.ArtifactCollectorFlowArgs(
                artifact_list=artifact_list,
                use_raw_filesystem_access=self.args.use_raw_filesystem_access,
                implementation_type=self.args.implementation_type,
                max_file_size=self.args.max_file_size,
                ignore_interpolation_errors=self.args.ignore_interpolation_errors,
                knowledge_base=self.args.knowledge_base,
            )
        ),
        request_data={
            "artifact_name": self.current_artifact_name,
            "source": source.ToPrimitiveDict(),
        },
        next_state=next_state,
    )

  def _CollectArtifacts(self, source: rdf_artifacts.ArtifactSource) -> None:
    self._StartSubArtifactCollector(
        artifact_list=source.attributes["names"],
        source=source,
        next_state=self.ProcessCollected.__name__,
    )

  def _RunCommand(self, source: rdf_artifacts.ArtifactSource) -> None:
    """Run a command."""
    if self.rrg_support:
      if self.client_os == "Linux":
        operating_system = signed_commands_pb2.SignedCommand.OS.LINUX
      elif self.client_os == "Darwin":
        operating_system = signed_commands_pb2.SignedCommand.OS.MACOS
      elif self.client_os == "Windows":
        operating_system = signed_commands_pb2.SignedCommand.OS.WINDOWS
      else:
        raise flow_base.FlowError(
            f"Unsupported operating system: {self.client_os}"
        )

      command = data_store.REL_DB.LookupSignedCommand(
          operating_system=operating_system,
          path=source.attributes["cmd"],
          args=source.attributes.get("args", []),
      )

      action = rrg_stubs.ExecuteSignedCommand()
      action.args.command = command.command
      action.args.command_ed25519_signature = command.ed25519_signature
      action.args.timeout.seconds = 30
      action.context["artifact_name"] = str(self.current_artifact_name)
      action.Call(self._ProcessRRGCommand)
    else:
      self.CallClientProto(
          server_stubs.ExecuteCommand,
          jobs_pb2.ExecuteRequest(
              cmd=source.attributes["cmd"],
              args=source.attributes.get("args", []),
          ),
          request_data={
              "artifact_name": self.current_artifact_name,
              "source": source.ToPrimitiveDict(),
          },
          next_state=self.ProcessCollected.__name__,
      )

  def _WMIQuery(self, source: rdf_artifacts.ArtifactSource) -> None:
    """Run a Windows WMI Query."""
    query = source.attributes["query"]
    queries = self._Interpolate(query)
    base_object = source.attributes.get("base_object")
    for query in queries:
      if self.rrg_support:
        action = rrg_stubs.QueryWmi()
        action.args.query = query

        if not base_object:
          action.args.namespace = "root\\cimv2"
        elif base_object.startswith("winmgmts:\\"):
          action.args.namespace = base_object.removeprefix("winmgmts:\\")
        else:
          raise flow_base.FlowError(f"Invalid WMI base object: {base_object}")

        action.context["artifact_name"] = str(self.current_artifact_name)
        action.Call(self._ProcessRRGWMIQuery)
      else:
        self.CallClientProto(
            server_stubs.WmiQuery,
            jobs_pb2.WMIRequest(
                query=query,
                base_object=base_object,
            ),
            request_data={
                "artifact_name": self.current_artifact_name,
                "source": source.ToPrimitiveDict(),
            },
            next_state=self.ProcessCollected.__name__,
        )

  def _InterpolateList(self, input_list: Sequence[str]):
    """Interpolate all items from a given source array.

    Args:
      input_list: list of values to interpolate

    Returns:
      original list of values extended with strings interpolated
    """
    new_args = []
    for value in input_list:
      if isinstance(value, str) or isinstance(value, bytes):
        results = self._Interpolate(value)

        new_args.extend(results)
      else:
        new_args.extend(value)
    return new_args

  def _Interpolate(
      self,
      pattern: str,
  ) -> Sequence[str]:
    """Performs a knowledgebase interpolation.

    Args:
      pattern: A pattern to interpolate.

    Returns:
      A list of possible interpolation results.
    """
    interpolation = artifact_utils.KnowledgeBaseInterpolation(
        pattern=pattern,
        kb=self.store.knowledge_base,
    )

    for log in interpolation.logs:
      self.Log("knowledgebase interpolation: %s", log)

    if not interpolation.results:
      if not self.proto_args.ignore_interpolation_errors:
        raise flow_base.FlowError(f"{pattern} interpolation error")

    return interpolation.results

  @flow_base.UseProto2AnyResponses
  def ProcessCollected(
      self, responses: flow_responses.Responses[any_pb2.Any]
  ) -> None:
    """Each individual collector will call back into here.

    Args:
      responses: Responses from the collection.

    Raises:
      artifact_utils.ArtifactDefinitionError: On bad definition.
      artifact_utils.ArtifactProcessingError: On failure to process.
    """
    flow_name = self.__class__.__name__
    artifact_name = str(responses.request_data["artifact_name"])

    progress = self._GetOrInsertArtifactProgress(artifact_name)

    if responses.success:
      self.Log(
          "Artifact data collection %s completed successfully in flow %s "
          "with %d responses",
          artifact_name,
          flow_name,
          len(responses),
      )
      progress.status = flows_pb2.ArtifactProgress.Status.SUCCESS
    else:
      self.Log(
          "Artifact %s data collection failed. Status: %s.",
          artifact_name,
          responses.status,
      )
      progress.status = flows_pb2.ArtifactProgress.Status.FAILURE

    # Increment artifact result count in flow progress.
    progress.num_results += len(responses)

    skipped_result_types = set()

    for result in responses:
      # All paths should lead to this "sink" state. Right now, we are not sure
      # from which path we were called, so we need to check the type of the
      # result and unpack it before moving on.
      # Here's the current map of callers:
      #   * CollectArtifacts (sub artifact collector) - One of the ones below
      #   * ProcessFileFinderResults - jobs_pb2.StatEntry
      #   * ProcessFileFinderKeys - jobs_pb2.StatEntry
      #   * RunCommand - jobs_pb2.ExecuteResponse
      #   * WMIQuery - jobs_pb2.Dict
      #   * ProcessCollectedRegistryStatEntry - jobs_pb2.StatEntry
      #   * ProcessCollectedArtifactFiles/MultiGetFile - jobs_pb2.StatEntry
      if result.Is(jobs_pb2.StatEntry.DESCRIPTOR):
        unpacked_result = jobs_pb2.StatEntry()
      elif result.Is(jobs_pb2.ExecuteResponse.DESCRIPTOR):
        unpacked_result = jobs_pb2.ExecuteResponse()
      elif result.Is(jobs_pb2.Dict.DESCRIPTOR):
        unpacked_result = jobs_pb2.Dict()
      else:
        skipped_result_types.add(result.type_url)
        continue

      result.Unpack(unpacked_result)
      self.SendReplyProto(unpacked_result, tag=f"artifact:{artifact_name}")

    if skipped_result_types:
      self.Error(
          "Skipped unrecognized result types: %s",
          ", ".join(skipped_result_types),
      )

  @flow_base.UseProto2AnyResponses
  def _ProcessRRGCommand(
      self,
      responses: flow_responses.Responses[any_pb2.Any],
  ) -> None:
    artifact_name = responses.request_data["artifact_name"]
    artifact_progress = self._GetOrInsertArtifactProgress(artifact_name)

    if not responses.success:
      self.Log(
          "Signed command execution for artifact %r failed: %s",
          artifact_name,
          responses.status,
      )
      artifact_progress.status = flows_pb2.ArtifactProgress.Status.FAILURE
      return

    if len(responses) != 1:
      raise flow_base.FlowError(
          "Unexpected number of signed command execution responses: "
          f"{len(responses)}"
      )

    artifact_progress.status = flows_pb2.ArtifactProgress.Status.SUCCESS
    artifact_progress.num_results += len(responses)

    for response_any in responses:
      response = rrg_execute_signed_command_pb2.Result()
      response.ParseFromString(response_any.value)

      result = jobs_pb2.ExecuteResponse()
      result.exit_status = response.exit_code
      result.stdout = response.stdout
      result.stderr = response.stderr

      if response.stdout_truncated:
        self.Log("Signed command stdout truncated for %r", artifact_name)
      if response.stderr_truncated:
        self.Log("Signed command stderr truncated for %r", artifact_name)

      self.SendReplyProto(result, tag=f"artifact:{artifact_name}")

  @flow_base.UseProto2AnyResponses
  def _ProcessRRGWMIQuery(
      self,
      responses: flow_responses.Responses[any_pb2.Any],
  ) -> None:
    artifact_name = responses.request_data["artifact_name"]
    artifact_progress = self._GetOrInsertArtifactProgress(artifact_name)

    if not responses.success:
      self.Log(
          "WMI query for artifact %r failed: %s",
          artifact_name,
          responses.status,
      )
      artifact_progress.status = flows_pb2.ArtifactProgress.Status.FAILURE
      return

    artifact_progress.status = flows_pb2.ArtifactProgress.Status.SUCCESS
    artifact_progress.num_results += len(responses)

    for response_any in responses:
      response = rrg_query_wmi_pb2.Result()
      response.ParseFromString(response_any.value)

      result = jobs_pb2.Dict()

      for column in response.row:
        kv = result.dat.add()
        kv.k.string = column

        value = response.row[column]
        if value.HasField("bool"):
          kv.v.boolean = value.bool
        elif value.HasField("uint"):
          kv.v.integer = value.uint
        elif value.HasField("int"):
          kv.v.integer = value.int
        elif value.HasField("float"):
          kv.v.float = value.float
        elif value.HasField("double"):
          kv.v.float = value.double
        elif value.HasField("string"):
          kv.v.string = value.string
        else:
          self.Log("Unexpected value %r for column %r", value, column)

      self.SendReplyProto(result, tag=f"artifact:{artifact_name}")

  @flow_base.UseProto2AnyResponses
  def ProcessCollectedRegistryStatEntry(
      self, responses: flow_responses.Responses[any_pb2.Any]
  ) -> None:
    """Create AFF4 objects for registry statentries.

    We need to do this explicitly because we call StatFile client action
    directly for performance reasons rather than using one of the flows that do
    this step automatically.

    Args:
      responses: Response objects from the artifact source.
    """
    if not responses.success:
      self.CallStateInlineProtoWithResponses(
          next_state=self.ProcessCollected.__name__, responses=responses
      )
      return

    stat_entries = []
    rdf_stat_entries = []
    for response in responses:
      result = jobs_pb2.StatEntry()
      response.Unpack(result)
      stat_entries.append(result)
      rdf_stat_entries.append(mig_client_fs.ToRDFStatEntry(result))
    filesystem.WriteStatEntries(rdf_stat_entries, client_id=self.client_id)

    self.CallStateInlineProto(
        next_state=self.ProcessCollected.__name__,
        request_data=responses.request_data,
        messages=stat_entries,
    )

  def ProcessCollectedArtifactFiles(self, responses):
    """Schedule files for download based on pathspec attribute.

    Args:
      responses: Response objects from the artifact source.

    Raises:
      RuntimeError: if pathspec value is not a PathSpec instance and not
                    a str.
    """
    self.download_list = []
    for response in responses:
      pathspec = response

      # Check the default .pathspec attribute.
      if not isinstance(pathspec, rdf_paths.PathSpec):
        try:
          pathspec = response.pathspec
        except AttributeError:
          pass

      if isinstance(pathspec, str):
        pathspec = rdf_paths.PathSpec(path=pathspec)

      if isinstance(pathspec, rdf_paths.PathSpec):
        if not pathspec.path:
          self.Log("Skipping empty pathspec.")
          continue
        if self.proto_args.use_raw_filesystem_access:
          pathspec.pathtype = rdf_paths.PathSpec.PathType.TSK
        else:
          pathspec.pathtype = rdf_paths.PathSpec.PathType.OS

        self.download_list.append(pathspec)

      else:
        raise RuntimeError(
            "Response must be a string path, a pathspec, or have "
            "pathspec_attribute set. Got: %s" % pathspec
        )

    if self.download_list:
      request_data = responses.request_data.ToDict()
      self.CallFlowProto(
          transfer.MultiGetFile.__name__,
          flow_args=mig_transfer.ToProtoMultiGetFileArgs(
              transfer.MultiGetFileArgs(
                  pathspecs=self.download_list,
                  request_data=request_data,
              )
          ),
          next_state=self.ProcessCollected.__name__,
      )
    else:
      self.Log("No files to download")

  # TODO: Remove this method.
  def GetProgress(self) -> rdf_artifacts.ArtifactCollectorFlowProgress:
    return mig_artifacts.ToRDFArtifactCollectorFlowProgress(self.progress)

  def GetProgressProto(self) -> flows_pb2.ArtifactCollectorFlowProgress:
    return self.progress

  def _GetOrInsertArtifactProgress(
      self,
      name: str,
  ) -> flows_pb2.ArtifactProgress:
    try:
      return next(
          a for a in self.GetProgressProto().artifacts if a.name == name
      )
    except StopIteration:
      progress = flows_pb2.ArtifactProgress(name=name)
      self.GetProgressProto().artifacts.append(progress)
      return progress

  def _ReceivedAnyResult(self) -> bool:
    for artifact_progress in self.GetProgressProto().artifacts:
      if artifact_progress.num_results > 0:
        return True
    return False

  def End(self) -> None:
    # If we got no responses, and user asked for it, we error out.
    if self.proto_args.error_on_no_results and not self._ReceivedAnyResult():
      raise artifact_utils.ArtifactProcessingError(
          "Artifact collector returned 0 responses."
      )


def MeetsOSConditions(knowledge_base, source):
  """Check supported OS on the source."""
  if source.supported_os and knowledge_base.os not in source.supported_os:
    return False

  return True
