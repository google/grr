#!/usr/bin/env python
"""Search for certain files, filter them by given criteria and do something."""

from typing import Optional, Sequence, Set, Tuple, cast

from google.protobuf import any_pb2
from grr_response_core.lib import artifact_utils
from grr_response_core.lib import rdfvalue
from grr_response_core.lib.rdfvalues import file_finder as rdf_file_finder
from grr_response_core.lib.rdfvalues import mig_client_fs
from grr_response_core.lib.rdfvalues import mig_file_finder
from grr_response_core.lib.rdfvalues import mig_paths
from grr_response_proto import flows_pb2
from grr_response_proto import jobs_pb2
from grr_response_proto import knowledge_base_pb2
from grr_response_server import data_store
from grr_response_server import file_store
from grr_response_server import flow_base
from grr_response_server import flow_responses
from grr_response_server import server_stubs
from grr_response_server.databases import db
from grr_response_server.flows.general import filesystem
from grr_response_server.models import blobs as models_blobs
from grr_response_server.rdfvalues import mig_objects
from grr_response_server.rdfvalues import objects as rdf_objects


def _GetPendingBlobIDs(
    responses: Sequence[flows_pb2.FileFinderResult],
) -> Sequence[Tuple[flows_pb2.FileFinderResult, Set[models_blobs.BlobID]]]:
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
    flow_base.FlowBase[flows_pb2.FileFinderArgs, flows_pb2.FileFinderStore]
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
      interpolated_args.ClearField("paths")
      interpolated_args.paths.extend(paths)
      self.CallClientProto(
          stub,
          action_args=interpolated_args,
          next_state=self.StoreResultsWithoutBlobs.__name__,
      )
    self.store.num_blob_waits = 0

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
