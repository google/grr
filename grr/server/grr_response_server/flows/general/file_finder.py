#!/usr/bin/env python
"""Search for certain files, filter them by given criteria and do something."""

import stat
from typing import Collection, Optional, Sequence, Set, Tuple

from grr_response_core.lib import artifact_utils
from grr_response_core.lib import interpolation
from grr_response_core.lib import rdfvalue
from grr_response_core.lib.rdfvalues import client_action as rdf_client_action
from grr_response_core.lib.rdfvalues import client_fs as rdf_client_fs
from grr_response_core.lib.rdfvalues import file_finder as rdf_file_finder
from grr_response_core.lib.rdfvalues import paths as rdf_paths
from grr_response_proto import flows_pb2
from grr_response_proto import knowledge_base_pb2
from grr_response_server import data_store
from grr_response_server import file_store
from grr_response_server import flow_base
from grr_response_server import flow_responses
from grr_response_server import server_stubs
from grr_response_server.databases import db
from grr_response_server.flows.general import filesystem
from grr_response_server.flows.general import fingerprint
from grr_response_server.flows.general import transfer
from grr_response_server.models import blobs
from grr_response_server.rdfvalues import mig_objects
from grr_response_server.rdfvalues import objects as rdf_objects


class LegacyFileFinder(
    transfer.MultiGetFileLogic,
    fingerprint.FingerprintFileLogic,
    filesystem.GlobLogic,
    flow_base.FlowBase,
):
  """This flow looks for files matching given criteria and acts on them.

  LegacyFileFinder searches for files that match glob expressions.  The "action"
  (e.g. Download) is applied to files that match all given "conditions".
  Matches are then written to the results collection. If there are no
  "conditions" specified, "action" is just applied to all found files.

  TODO: remove by EOY2024.

  This flow is scheduled for removal and is no longer tested (all file finder
  related tests are using the ClientFileFinder or FileFinder, which is now
  an alias to ClientFileFinder).
  """

  friendly_name = "Legacy File Finder (deprecated)"
  category = "/Filesystem/"
  args_type = rdf_file_finder.FileFinderArgs
  result_types = (rdf_file_finder.FileFinderResult,)
  behaviours = flow_base.BEHAVIOUR_DEBUG

  # Will be used by FingerprintFileLogic.
  fingerprint_file_mixin_client_action = server_stubs.HashFile

  _condition_handlers = None

  def _GetConditionHandlers(self):

    if self._condition_handlers is None:
      type_enum = rdf_file_finder.FileFinderCondition.Type
      # For every condition type we specify a tuple (handle, weight).
      # Conditions will be sorted by weight, so that the ones with the minimal
      # weight will be executed earlier.
      self._condition_handlers = {
          type_enum.MODIFICATION_TIME: (self.ModificationTimeCondition, 0),
          type_enum.ACCESS_TIME: (self.AccessTimeCondition, 0),
          type_enum.INODE_CHANGE_TIME: (self.InodeChangeTimeCondition, 0),
          type_enum.SIZE: (self.SizeCondition, 0),
          type_enum.CONTENTS_REGEX_MATCH: (self.ContentsRegexMatchCondition, 1),
          type_enum.CONTENTS_LITERAL_MATCH:
              (self.ContentsLiteralMatchCondition, 1)
      }
    return self._condition_handlers

  def _ConditionWeight(self, condition_options):
    _, condition_weight = self._GetConditionHandlers()[
        condition_options.condition_type]
    return condition_weight

  def Start(self):
    """Issue the find request."""
    download = rdf_file_finder.FileFinderAction.Action.DOWNLOAD
    if self.args.action.action_type == download:
      use_external_stores = self.args.action.download.use_external_stores
    else:
      use_external_stores = False

    super().Start(use_external_stores=use_external_stores)

    self.state.files_found = 0

    if not self.args.paths:
      # Nothing to do.
      return

    # Do not access `conditions`, if it has never been set before. Otherwise,
    # the field is replaced with the default value `[]`, which breaks equality
    # in unsuspected ways. Also, see the comment below.
    # TODO
    if self.args.HasField("conditions"):
      self.state.sorted_conditions = sorted(
          self.args.conditions, key=self._ConditionWeight)
    else:
      self.state.sorted_conditions = []

    # TODO(user): We may change self.args just by accessing self.args.action
    # (a nested message will be created). Therefore we should be careful
    # about not modifying self.args: they will be written as FLOW_ARGS attribute
    # and will be different from what the user has actually passed in.
    # We need better semantics for RDFStructs - creating a nested field on
    # read access is totally unexpected.
    if self.args.HasField("action"):
      action = self.args.action.Copy()
    else:
      action = rdf_file_finder.FileFinderAction()

    # This is used by MultiGetFileLogic.
    if action.action_type == rdf_file_finder.FileFinderAction.Action.HASH:
      self.state.file_size = action.hash.max_size
    elif action.action_type == rdf_file_finder.FileFinderAction.Action.DOWNLOAD:
      self.state.file_size = action.download.max_size

    if self.args.pathtype == rdf_paths.PathSpec.PathType.REGISTRY:
      # Registry StatEntries won't pass the file type check.
      self.args.process_non_regular_files = True

    if self.args.HasField("implementation_type"):
      implementation_type = self.args.implementation_type
    else:
      implementation_type = None

    self.GlobForPaths(
        self.args.paths,
        pathtype=self.args.pathtype,
        implementation_type=implementation_type,
        process_non_regular_files=self.args.process_non_regular_files,
        collect_ext_attrs=action.stat.collect_ext_attrs)

  def GlobReportMatch(self, response):
    """This method is called by the glob mixin when there is a match."""
    super().GlobReportMatch(response)

    self.ApplyCondition(
        rdf_file_finder.FileFinderResult(stat_entry=response),
        condition_index=0)

  def ModificationTimeCondition(self, response, condition_options,
                                condition_index):
    """Applies modification time condition to responses."""
    settings = condition_options.modification_time
    if (settings.min_last_modified_time.AsSecondsSinceEpoch() <=
        response.stat_entry.st_mtime <=
        settings.max_last_modified_time.AsSecondsSinceEpoch()):

      self.ApplyCondition(response, condition_index + 1)

  def AccessTimeCondition(self, response, condition_options, condition_index):
    """Applies access time condition to responses."""
    settings = condition_options.access_time
    if (settings.min_last_access_time.AsSecondsSinceEpoch() <=
        response.stat_entry.st_atime <=
        settings.max_last_access_time.AsSecondsSinceEpoch()):
      self.ApplyCondition(response, condition_index + 1)

  def InodeChangeTimeCondition(self, response, condition_options,
                               condition_index):
    """Applies inode change time condition to responses."""
    settings = condition_options.inode_change_time
    if (settings.min_last_inode_change_time.AsSecondsSinceEpoch() <=
        response.stat_entry.st_ctime <=
        settings.max_last_inode_change_time.AsSecondsSinceEpoch()):
      self.ApplyCondition(response, condition_index + 1)

  def SizeCondition(self, response, condition_options, condition_index):
    """Applies size condition to responses."""
    if not (self.args.process_non_regular_files or
            stat.S_ISREG(int(response.stat_entry.st_mode))):
      return

    if (condition_options.size.min_file_size <= response.stat_entry.st_size <=
        condition_options.size.max_file_size):
      self.ApplyCondition(response, condition_index + 1)

  def ContentsRegexMatchCondition(self, response, condition_options,
                                  condition_index):
    """Applies contents regex condition to responses."""
    if not (self.args.process_non_regular_files or
            stat.S_ISREG(int(response.stat_entry.st_mode))):
      return

    options = condition_options.contents_regex_match
    grep_spec = rdf_client_fs.GrepSpec(
        target=response.stat_entry.pathspec,
        regex=options.regex.AsBytes(),
        mode=options.mode,
        start_offset=options.start_offset,
        length=options.length,
        bytes_before=options.bytes_before,
        bytes_after=options.bytes_after)

    self.CallClient(
        server_stubs.Grep,
        request=grep_spec,
        next_state=self.ProcessGrep.__name__,
        request_data=dict(
            original_result=response, condition_index=condition_index + 1))

  def ContentsLiteralMatchCondition(self, response, condition_options,
                                    condition_index):
    """Applies literal match condition to responses."""
    if not (self.args.process_non_regular_files or
            stat.S_ISREG(int(response.stat_entry.st_mode))):
      return

    options = condition_options.contents_literal_match
    grep_spec = rdf_client_fs.GrepSpec(
        target=response.stat_entry.pathspec,
        literal=options.literal.AsBytes(),
        mode=options.mode,
        start_offset=options.start_offset,
        length=options.length,
        bytes_before=options.bytes_before,
        bytes_after=options.bytes_after,
        xor_in_key=options.xor_in_key,
        xor_out_key=options.xor_out_key)

    self.CallClient(
        server_stubs.Grep,
        request=grep_spec,
        next_state=self.ProcessGrep.__name__,
        request_data=dict(
            original_result=response, condition_index=condition_index + 1))

  def ProcessGrep(self, responses):
    for response in responses:
      if "original_result" not in responses.request_data:
        raise RuntimeError("Got a buffer reference, but original result "
                           "is missing")

      condition_index = responses.request_data["condition_index"]
      original_result = responses.request_data["original_result"]
      original_result.matches.append(response)

      self.ApplyCondition(original_result, condition_index)

  def ApplyCondition(self, response, condition_index):
    """Applies next condition to responses."""
    if condition_index >= len(self.state.sorted_conditions):
      # All conditions satisfied, do the action now.
      self.ProcessAction(response)

    else:
      # Apply the next condition handler.
      condition_options = self.state.sorted_conditions[condition_index]
      condition_handler, _ = self._GetConditionHandlers()[
          condition_options.condition_type]

      condition_handler(response, condition_options, condition_index)

  def ProcessAction(self, response):
    """Applies action specified by user to responses."""
    action = self.args.action.action_type

    if action == rdf_file_finder.FileFinderAction.Action.STAT:
      # If we are dealing with the operating system file api, the stat action
      # might need to collect extended attributes or gather information about
      # links instead of their targets. In those cases, we need to issue more
      # GetFileStatRequest client requests. In all other cases, we already have
      # all the data we need to send the response.
      s = self.args.action.stat
      if (self.args.pathtype != rdf_paths.PathSpec.PathType.OS or
          (s.resolve_links and not s.collect_ext_attrs)):
        self.state.files_found += 1
        self.SendReply(response)
      else:
        if self.client_version and self.client_version < 3221:
          self.Error("Client is too old to get requested stat information.")
        request = rdf_client_action.GetFileStatRequest(
            pathspec=response.stat_entry.pathspec,
            collect_ext_attrs=s.collect_ext_attrs,
            follow_symlink=s.resolve_links)
        self.CallClient(
            server_stubs.GetFileStat,
            request,
            next_state=self.ReceiveFileStat.__name__,
            request_data=dict(original_result=response))

    elif (self.args.process_non_regular_files or
          stat.S_ISREG(int(response.stat_entry.st_mode))):
      # Hashing and downloading are only safe for regular files. User has to
      # explicitly set args.process_non_regular_files to True to make
      # FileFinder look into non-regular files.
      # In both cases (regular and non-regular files) max_size limit is applied
      # (either action.hash.max_size or action.download.max_size, depending on
      # the action type).
      # Reply is sent only when we get file's hash.
      self.state.files_found += 1

      if action == rdf_file_finder.FileFinderAction.Action.HASH:
        hash_file = False
        file_size = response.stat_entry.st_size
        if file_size > self.args.action.hash.max_size:
          policy = self.args.action.hash.oversized_file_policy
          options = rdf_file_finder.FileFinderHashActionOptions
          if policy == options.OversizedFilePolicy.SKIP:
            self.Log(
                "%s too large to hash, skipping according to SKIP "
                "policy. Size=%d", response.stat_entry.pathspec.CollapsePath(),
                file_size)
          elif policy == options.OversizedFilePolicy.HASH_TRUNCATED:
            self.Log(
                "%s too large to hash, hashing its first %d bytes "
                "according to HASH_TRUNCATED policy. Size=%d",
                response.stat_entry.pathspec.CollapsePath(),
                self.args.action.download.max_size, file_size)
            hash_file = True
        else:
          hash_file = True

        if hash_file:
          self.FingerprintFile(
              response.stat_entry.pathspec,
              max_filesize=self.args.action.hash.max_size,
              request_data=dict(original_result=response))

      elif action == rdf_file_finder.FileFinderAction.Action.DOWNLOAD:
        fetch_file = False
        # If the binary is too large we don't download it, but take a
        # fingerprint instead.
        file_size = response.stat_entry.st_size
        if file_size > self.args.action.download.max_size:
          policy = self.args.action.download.oversized_file_policy
          options = rdf_file_finder.FileFinderDownloadActionOptions
          if policy == options.OversizedFilePolicy.SKIP:
            self.Log(
                "%s too large to fetch, skipping according to SKIP "
                "policy. Size=%d", response.stat_entry.pathspec.CollapsePath(),
                file_size)
          elif policy == options.OversizedFilePolicy.HASH_TRUNCATED:
            self.Log(
                "%s too large to fetch, hashing its first %d bytes "
                "according to HASH_TRUNCATED policy. Size=%d",
                response.stat_entry.pathspec.CollapsePath(),
                self.args.action.download.max_size, file_size)
            self.FingerprintFile(
                response.stat_entry.pathspec,
                max_filesize=self.args.action.download.max_size,
                request_data=dict(original_result=response))
          elif policy == "DOWNLOAD_TRUNCATED":
            fetch_file = True
        else:
          fetch_file = True

        if fetch_file:
          pathspec = response.stat_entry.pathspec.Copy()
          # If the file size is reported as zero and we're processing
          # non-regular files, let's assume we're dealing with a
          # device file and use download.max_size as a size override.
          if (not response.stat_entry.st_size and
              self.args.process_non_regular_files):
            pathspec.file_size_override = self.args.action.download.max_size
          self.StartFileFetch(
              pathspec, request_data=dict(original_result=response))

  def ReceiveFileStat(self, responses):
    if "original_result" not in responses.request_data:
      raise RuntimeError("Got stat information, but original result "
                         "is missing")

    for response in responses:
      result = responses.request_data["original_result"]
      result.stat_entry = response
      self.SendReply(result)

  def ReceiveFileFingerprint(self, urn, hash_obj, request_data=None):
    """Handle hash results from the FingerprintFileLogic."""
    if "original_result" not in request_data:
      raise RuntimeError("Got a fingerprintfileresult, but original result "
                         "is missing")

    result = request_data["original_result"]
    result.hash_entry = hash_obj
    self.SendReply(result)

  def ReceiveFetchedFile(self,
                         unused_stat_entry,
                         file_hash,
                         request_data=None,
                         is_duplicate=False):
    """Handle downloaded file from MultiGetFileLogic."""
    del is_duplicate  # Unused.

    if "original_result" not in request_data:
      raise RuntimeError("Got fetched file data, but original result "
                         "is missing")

    result = request_data["original_result"]
    result.hash_entry = file_hash
    self.SendReply(result)

  def End(self, responses):
    super().End(responses)

    self.Log("Found and processed %d files.", self.state.files_found)


def _GetPendingBlobIDs(
    responses: Collection[rdf_file_finder.FileFinderResult],
) -> Sequence[Tuple[rdf_file_finder.FileFinderResult, Set[blobs.BlobID]]]:
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
      blob_id = blobs.BlobID(c.digest)
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


class ClientFileFinder(flow_base.FlowBase):
  """A client side file finder flow."""

  friendly_name = "Client Side File Finder"
  category = "/Filesystem/"
  args_type = rdf_file_finder.FileFinderArgs
  behaviours = flow_base.BEHAVIOUR_BASIC

  BLOB_CHECK_DELAY = rdfvalue.Duration("60s")
  MAX_BLOB_CHECKS = 60

  def Start(self):
    """Issue the find request."""
    super().Start()

    # Do not do anything if no paths are specified in the arguments.
    if not self.args.paths:
      self.Log("No paths provided, finishing.")
      self.state.files_found = 0
      return

    if self.args.pathtype == rdf_paths.PathSpec.PathType.OS:
      stub = server_stubs.FileFinderOS
    else:
      stub = server_stubs.VfsFileFinder

    # TODO: Remove this workaround once sandboxing issues are
    # resolved and NTFS paths work it again.
    if (
        self.args.pathtype == rdf_paths.PathSpec.PathType.NTFS
        and not self.args.HasField("implementation_type")
    ):
      self.Log("Using unsandboxed NTFS access")
      self.args.implementation_type = (
          rdf_paths.PathSpec.ImplementationType.DIRECT
      )

    if (paths := self._InterpolatePaths(self.args.paths)) is not None:
      interpolated_args = self.args.Copy()
      interpolated_args.paths = paths
      self.CallClient(
          stub,
          request=interpolated_args,
          next_state=self.StoreResultsWithoutBlobs.__name__,
      )

    self.state.num_blob_waits = 0

  def _InterpolatePaths(self, globs: Sequence[str]) -> Optional[Sequence[str]]:
    kb: Optional[knowledge_base_pb2.ClientKnowledgeBase] = (
        self.client_knowledge_base
    )

    paths = list()
    missing_attrs = list()
    unknown_attrs = list()

    for glob in globs:
      # Only fail hard on missing knowledge base if there's actual
      # interpolation to be done.
      if kb is None:
        interpolator = interpolation.Interpolator(str(glob))
        if interpolator.Vars() or interpolator.Scopes():
          self.Log(
              f"Skipping glob '{glob}': can't interpolate with an "
              "empty knowledge base"
          )
          continue

      try:
        paths.extend(artifact_utils.InterpolateKbAttributes(str(glob), kb))
      except artifact_utils.KbInterpolationMissingAttributesError as error:
        missing_attrs.extend(error.attrs)
        self.Log("Missing knowledgebase attributes: %s", error.attrs)
      except artifact_utils.KbInterpolationUnknownAttributesError as error:
        unknown_attrs.extend(error.attrs)
        self.Log("Unknown knowledgebase attributes: %s", error.attrs)

    if missing_attrs:
      self.Error(f"Missing knowledgebase attributes: {missing_attrs}")
      return None
    if unknown_attrs:
      self.Error(f"Unknown knowledgebase attributes: {unknown_attrs}")
      return None

    if not paths:
      self.Error(
          "All globs skipped, as there's no knowledgebase available for"
          " interpolation"
      )
      return None

    return paths

  def StoreResultsWithoutBlobs(
      self,
      responses: flow_responses.Responses[rdf_file_finder.FileFinderResult],
  ) -> None:
    """Stores the results returned by the client to the db."""
    if not responses.success:
      raise flow_base.FlowError(responses.status)

    self.state.files_found = len(responses)
    transferred_file_responses = []
    stat_entry_responses = []
    # Split the responses into the ones that just contain file stats
    # and the ones actually referencing uploaded chunks.
    for response in responses:
      if response.HasField("transferred_file"):
        transferred_file_responses.append(response)
      elif response.HasField("stat_entry"):
        stat_entry_responses.append(response)

    filesystem.WriteFileFinderResults(stat_entry_responses, self.client_id)
    for r in stat_entry_responses:
      self.SendReply(r)

    if transferred_file_responses:
      self.CallStateInline(
          next_state=self.StoreResultsWithBlobs.__name__,
          messages=transferred_file_responses,
      )

  def StoreResultsWithBlobs(
      self,
      responses: flow_responses.Responses[rdf_file_finder.FileFinderResult],
  ) -> None:
    """Stores the results returned by the client to the db."""
    complete_responses = []
    incomplete_responses = []

    response_pending_blob_ids = _GetPendingBlobIDs(list(responses))
    # Needed in case we need to report an error (see below).
    sample_pending_blob_id: Optional[blobs.BlobID] = None
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
      client_path = db.ClientPath.FromPathSpec(self.client_id, pathspec)

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

      self.SendReply(response)

    if incomplete_responses:
      self.state.num_blob_waits += 1

      self.Log(
          "Waiting for blobs to be written to the blob store. Iteration: %d out"
          " of %d. Blobs pending: %d",
          self.state.num_blob_waits,
          self.MAX_BLOB_CHECKS,
          num_pending_blobs,
      )

      if self.state.num_blob_waits > self.MAX_BLOB_CHECKS:
        self.Error(
            "Could not find one of referenced blobs "
            f"(sample id: {sample_pending_blob_id}). "
            "This is a sign of datastore inconsistency."
        )
        return

      start_time = rdfvalue.RDFDatetime.Now() + self.BLOB_CHECK_DELAY
      self.CallState(
          next_state=self.StoreResultsWithBlobs.__name__,
          responses=incomplete_responses,
          start_time=start_time,
      )

  def _WriteFilesContent(
      self,
      complete_responses: list[rdf_file_finder.FileFinderResult],
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
      path_info = rdf_objects.PathInfo.FromStatEntry(response.stat_entry)

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
          client_path_blob_refs, use_external_stores=use_external_stores)
      for client_path, hash_id in client_path_hash_id.items():
        path_info = client_path_path_info[client_path]
        path_info.hash_entry.sha256 = hash_id.AsBytes()
        path_info.hash_entry.num_bytes = client_path_sizes[client_path]

    path_infos = list(client_path_path_info.values())
    proto_path_infos = [mig_objects.ToProtoPathInfo(pi) for pi in path_infos]
    data_store.REL_DB.WritePathInfos(self.client_id, proto_path_infos)

    return client_path_hash_id

  def End(self, responses):
    super().End(responses)

    if self.rdf_flow.flow_state != flows_pb2.Flow.ERROR:
      self.Log("Found and processed %d files.", self.state.files_found)


# TODO decide on the FileFinder name and remove the legacy alias.
class FileFinder(ClientFileFinder):
  """An alias for ClientFileFinder."""

  friendly_name = "File Finder"
  behaviours = flow_base.BEHAVIOUR_BASIC
