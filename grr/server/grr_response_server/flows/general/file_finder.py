#!/usr/bin/env python
"""Search for certain files, filter them by given criteria and do something."""
from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

import stat

from future.builtins import str
from future.utils import iteritems
from future.utils import itervalues

from grr_response_core.lib import artifact_utils
from grr_response_core.lib.rdfvalues import client_action as rdf_client_action
from grr_response_core.lib.rdfvalues import client_fs as rdf_client_fs
from grr_response_core.lib.rdfvalues import file_finder as rdf_file_finder
from grr_response_core.lib.rdfvalues import paths as rdf_paths
from grr_response_core.lib.util import compatibility
from grr_response_server import data_store
from grr_response_server import file_store
from grr_response_server import flow_base
from grr_response_server import server_stubs
from grr_response_server.databases import db
from grr_response_server.flows.general import filesystem
from grr_response_server.flows.general import fingerprint
from grr_response_server.flows.general import transfer
from grr_response_server.rdfvalues import objects as rdf_objects


class FileFinder(transfer.MultiGetFileLogic, fingerprint.FingerprintFileLogic,
                 filesystem.GlobLogic, flow_base.FlowBase):
  """This flow looks for files matching given criteria and acts on them.

  FileFinder searches for files that match glob expressions.  The "action"
  (e.g. Download) is applied to files that match all given "conditions".
  Matches are then written to the results collection. If there are no
  "conditions" specified, "action" is just applied to all found files.
  """
  friendly_name = "File Finder"
  category = "/Filesystem/"
  args_type = rdf_file_finder.FileFinderArgs
  behaviours = flow_base.BEHAVIOUR_BASIC

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

    super(FileFinder, self).Start(use_external_stores=use_external_stores)

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

    self.GlobForPaths(
        self.args.paths,
        pathtype=self.args.pathtype,
        process_non_regular_files=self.args.process_non_regular_files,
        collect_ext_attrs=action.stat.collect_ext_attrs)

  def GlobReportMatch(self, response):
    """This method is called by the glob mixin when there is a match."""
    super(FileFinder, self).GlobReportMatch(response)

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
        next_state=compatibility.GetName(self.ProcessGrep),
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
        next_state=compatibility.GetName(self.ProcessGrep),
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
        if self.client_version < 3221:
          self.Error("Client is too old to get requested stat information.")
        request = rdf_client_action.GetFileStatRequest(
            pathspec=response.stat_entry.pathspec,
            collect_ext_attrs=s.collect_ext_attrs,
            follow_symlink=s.resolve_links)
        self.CallClient(
            server_stubs.GetFileStat,
            request,
            next_state=compatibility.GetName(self.ReceiveFileStat),
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
          self.StartFileFetch(
              response.stat_entry.pathspec,
              request_data=dict(original_result=response))

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

  def ReceiveFetchedFile(self, unused_stat_entry, file_hash, request_data=None):
    """Handle downloaded file from MultiGetFileLogic."""
    if "original_result" not in request_data:
      raise RuntimeError("Got fetched file data, but original result "
                         "is missing")

    result = request_data["original_result"]
    result.hash_entry = file_hash
    self.SendReply(result)

  def End(self, responses):
    super(FileFinder, self).End(responses)

    self.Log("Found and processed %d files.", self.state.files_found)


class ClientFileFinder(flow_base.FlowBase):
  """A client side file finder flow."""

  friendly_name = "Client Side File Finder"
  category = "/Filesystem/"
  args_type = rdf_file_finder.FileFinderArgs
  behaviours = flow_base.BEHAVIOUR_BASIC

  def Start(self):
    """Issue the find request."""
    super(ClientFileFinder, self).Start()

    if self.args.pathtype == rdf_paths.PathSpec.PathType.OS:
      stub = server_stubs.FileFinderOS
    else:
      stub = server_stubs.VfsFileFinder

    interpolated_args = self.args.Copy()
    interpolated_args.paths = list(
        self._InterpolatePaths(interpolated_args.paths))

    self.CallClient(
        stub,
        request=interpolated_args,
        next_state=compatibility.GetName(self.StoreResults))

  def _InterpolatePaths(self, globs):

    kb = self.client_knowledge_base

    for glob in globs:
      param_path = str(glob)
      for path in artifact_utils.InterpolateKbAttributes(param_path, kb):
        yield path

  def StoreResults(self, responses):
    """Stores the results returned by the client to the db."""
    if not responses.success:
      raise flow_base.FlowError(responses.status)

    self.state.files_found = len(responses)
    transferred_file_responses = []
    stat_entries = []
    for response in responses:
      if response.HasField("transferred_file"):
        transferred_file_responses.append(response)
      elif response.HasField("stat_entry"):
        stat_entries.append(response.stat_entry)

    self._WriteFilesContent(transferred_file_responses)

    self._WriteStatEntries(stat_entries)

    for response in responses:
      self.SendReply(response)

  def _WriteFilesContent(self, responses):
    """Writes file contents of multiple files to the relational database."""
    client_path_blob_refs = dict()
    client_path_path_info = dict()
    client_path_sizes = dict()

    for response in responses:
      path_info = rdf_objects.PathInfo.FromStatEntry(response.stat_entry)

      chunks = response.transferred_file.chunks
      chunks = sorted(chunks, key=lambda _: _.offset)

      client_path = db.ClientPath.FromPathInfo(self.client_id, path_info)
      blob_refs = []
      file_size = 0
      for c in chunks:
        blob_refs.append(
            rdf_objects.BlobReference(
                offset=c.offset,
                size=c.length,
                blob_id=rdf_objects.BlobID.FromSerializedBytes(c.digest)))
        file_size += c.length

      client_path_path_info[client_path] = path_info
      client_path_blob_refs[client_path] = blob_refs
      client_path_sizes[client_path] = file_size

    if client_path_blob_refs:
      use_external_stores = self.args.action.download.use_external_stores
      client_path_hash_id = file_store.AddFilesWithUnknownHashes(
          client_path_blob_refs, use_external_stores=use_external_stores)
      for client_path, hash_id in iteritems(client_path_hash_id):
        path_info = client_path_path_info[client_path]
        path_info.hash_entry.sha256 = hash_id.AsBytes()
        path_info.hash_entry.num_bytes = client_path_sizes[client_path]

    path_infos = list(itervalues(client_path_path_info))
    data_store.REL_DB.WritePathInfos(self.client_id, path_infos)

  def _WriteStatEntries(self, stat_entries):
    filesystem.WriteStatEntries(stat_entries, client_id=self.client_id)

  def End(self, responses):
    super(ClientFileFinder, self).End(responses)

    self.Log("Found and processed %d files.", self.state.files_found)
