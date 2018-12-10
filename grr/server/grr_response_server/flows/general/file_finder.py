#!/usr/bin/env python
"""Search for certain files, filter them by given criteria and do something."""
from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

import stat

from grr_response_core.lib import artifact_utils
from grr_response_core.lib import rdfvalue
from grr_response_core.lib.rdfvalues import client_fs as rdf_client_fs
from grr_response_core.lib.rdfvalues import file_finder as rdf_file_finder
from grr_response_core.lib.rdfvalues import paths as rdf_paths
from grr_response_server import aff4
from grr_response_server import data_store
from grr_response_server import events
from grr_response_server import file_store
from grr_response_server import flow
from grr_response_server import flow_base
from grr_response_server import server_stubs
from grr_response_server.aff4_objects import aff4_grr
from grr_response_server.flows.general import filesystem
from grr_response_server.flows.general import fingerprint
from grr_response_server.flows.general import transfer
from grr_response_server.rdfvalues import objects as rdf_objects


@flow_base.DualDBFlow
class FileFinderMixin(transfer.MultiGetFileLogic,
                      fingerprint.FingerprintFileLogic, filesystem.GlobLogic):
  """This flow looks for files matching given criteria and acts on them.

  FileFinder searches for files that match glob expressions.  The "action"
  (e.g. Download) is applied to files that match all given "conditions".
  Matches are then written to the results collection. If there are no
  "conditions" specified, "action" is just applied to all found files.
  """
  friendly_name = "File Finder"
  category = "/Filesystem/"
  args_type = rdf_file_finder.FileFinderArgs
  behaviours = flow.GRRFlow.behaviours + "BASIC"

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
          type_enum.CONTENTS_LITERAL_MATCH: (self.ContentsLiteralMatchCondition,
                                             1)
      }
    return self._condition_handlers

  def _ConditionWeight(self, condition_options):
    _, condition_weight = self._GetConditionHandlers()[
        condition_options.condition_type]
    return condition_weight

  def Start(self):
    """Issue the find request."""
    super(FileFinderMixin, self).Start()

    if not self.args.paths:
      # Nothing to do.
      return

    self.state.files_found = 0

    # Do not access `conditions`, if it has never been set before. Otherwise,
    # the field is replaced with the default value `[]`, which breaks equality
    # in unsuspected ways. Also, see the comment below.
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

    self.GlobForPaths(
        self.args.paths,
        pathtype=self.args.pathtype,
        process_non_regular_files=self.args.process_non_regular_files,
        collect_ext_attrs=action.stat.collect_ext_attrs)

  def GlobReportMatch(self, response):
    """This method is called by the glob mixin when there is a match."""
    super(FileFinderMixin, self).GlobReportMatch(response)

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
            stat.S_ISREG(response.stat_entry.st_mode)):
      return

    if (condition_options.size.min_file_size <= response.stat_entry.st_size <=
        condition_options.size.max_file_size):
      self.ApplyCondition(response, condition_index + 1)

  def ContentsRegexMatchCondition(self, response, condition_options,
                                  condition_index):
    """Applies contents regex condition to responses."""
    if not (self.args.process_non_regular_files or
            stat.S_ISREG(response.stat_entry.st_mode)):
      return

    options = condition_options.contents_regex_match
    grep_spec = rdf_client_fs.GrepSpec(
        target=response.stat_entry.pathspec,
        regex=options.regex,
        mode=options.mode,
        start_offset=options.start_offset,
        length=options.length,
        bytes_before=options.bytes_before,
        bytes_after=options.bytes_after)

    self.CallClient(
        server_stubs.Grep,
        request=grep_spec,
        next_state="ProcessGrep",
        request_data=dict(
            original_result=response, condition_index=condition_index + 1))

  def ContentsLiteralMatchCondition(self, response, condition_options,
                                    condition_index):
    """Applies literal match condition to responses."""
    if not (self.args.process_non_regular_files or
            stat.S_ISREG(response.stat_entry.st_mode)):
      return

    options = condition_options.contents_literal_match
    grep_spec = rdf_client_fs.GrepSpec(
        target=response.stat_entry.pathspec,
        literal=options.literal,
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
        next_state="ProcessGrep",
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
      # If action is STAT, we already have all the data we need to send the
      # response.
      self.state.files_found += 1
      self.SendReply(response)
    elif (self.args.process_non_regular_files or
          stat.S_ISREG(response.stat_entry.st_mode)):
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
          self.StartFileFetch(
              response.stat_entry.pathspec,
              request_data=dict(original_result=response))

  def ReceiveFileFingerprint(self, urn, hash_obj, request_data=None):
    """Handle hash results from the FingerprintFileLogic."""
    if "original_result" in request_data:
      result = request_data["original_result"]
      result.hash_entry = hash_obj
      self.SendReply(result)
    else:
      raise RuntimeError("Got a fingerprintfileresult, but original result "
                         "is missing")

  def ReceiveFetchedFile(self, unused_stat_entry, file_hash, request_data=None):
    """Handle downloaded file from MultiGetFileLogic."""
    if "original_result" not in request_data:
      raise RuntimeError("Got fetched file data, but original result "
                         "is missing")

    result = request_data["original_result"]
    result.hash_entry = file_hash
    self.SendReply(result)

  def End(self, responses):
    super(FileFinderMixin, self).End(responses)

    self.Log("Found and processed %d files.", self.state.files_found)


@flow_base.DualDBFlow
class ClientFileFinderMixin(object):
  """A client side file finder flow."""

  friendly_name = "Client Side File Finder"
  category = "/Filesystem/"
  args_type = rdf_file_finder.FileFinderArgs
  behaviours = flow.GRRFlow.behaviours + "BASIC"

  def Start(self):
    """Issue the find request."""
    super(ClientFileFinderMixin, self).Start()

    if self.args.pathtype != "OS":
      raise ValueError("Only supported pathtype is OS.")

    self.args.paths = list(self._InterpolatePaths(self.args.paths))

    self.CallClient(
        server_stubs.FileFinderOS, request=self.args, next_state="StoreResults")

  def _InterpolatePaths(self, globs):

    kb = self.client_knowledge_base

    for glob in globs:
      param_path = glob.SerializeToString()
      for path in artifact_utils.InterpolateKbAttributes(param_path, kb):
        yield path

  def StoreResults(self, responses):
    """Stores the results returned by the client to the db."""
    if not responses.success:
      raise flow.FlowError(responses.status)

    self.state.files_found = len(responses)
    files_to_publish = []
    with data_store.DB.GetMutationPool() as pool:
      for response in responses:
        if response.HasField("transferred_file"):
          self._WriteFileContent(response, mutation_pool=pool)
        elif response.HasField("stat_entry"):
          self._WriteFileStatEntry(response, mutation_pool=pool)

        self.SendReply(response)

        if stat.S_ISREG(response.stat_entry.st_mode):
          files_to_publish.append(
              response.stat_entry.pathspec.AFF4Path(self.client_urn))

    if files_to_publish:
      events.Events.PublishMultipleEvents(
          {"LegacyFileStore.AddFileToStore": files_to_publish})

  def _WriteFileContent(self, response, mutation_pool=None):
    """Writes file content to the db."""
    urn = response.stat_entry.pathspec.AFF4Path(self.client_urn)

    if data_store.AFF4Enabled():
      with aff4.FACTORY.Create(
          urn,
          aff4_grr.VFSBlobImage,
          token=self.token,
          mutation_pool=mutation_pool) as filedesc:
        filedesc.SetChunksize(response.transferred_file.chunk_size)
        filedesc.Set(filedesc.Schema.STAT, response.stat_entry)

        chunks = sorted(
            response.transferred_file.chunks, key=lambda _: _.offset)
        for chunk in chunks:
          filedesc.AddBlob(
              rdf_objects.BlobID.FromBytes(chunk.digest), chunk.length)

        filedesc.Set(filedesc.Schema.CONTENT_LAST, rdfvalue.RDFDatetime.Now())

    if data_store.RelationalDBWriteEnabled():
      path_info = rdf_objects.PathInfo.FromStatEntry(response.stat_entry)

      # Adding files to filestore requires reading data from RELDB,
      # thus protecting this code with a filestore-read-enabled check.
      if data_store.RelationalDBReadEnabled("filestore"):
        blob_ids = [rdf_objects.BlobID.FromBytes(c.digest) for c in chunks]
        hash_id = file_store.AddFileWithUnknownHash(blob_ids)
        path_info.hash_entry.sha256 = hash_id.AsBytes()

      data_store.REL_DB.WritePathInfos(self.client_id, [path_info])

  def _WriteFileStatEntry(self, response, mutation_pool=None):
    filesystem.WriteStatEntries([response.stat_entry],
                                client_id=self.client_id,
                                token=self.token,
                                mutation_pool=mutation_pool)

  def End(self, responses):
    super(ClientFileFinderMixin, self).End(responses)

    self.Log("Found and processed %d files.", self.state.files_found)
