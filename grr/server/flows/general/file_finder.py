#!/usr/bin/env python
"""Search for certain files, filter them by given criteria and do something."""


import stat

from grr import config
from grr.lib import rdfvalue
from grr.lib import utils
from grr.lib.rdfvalues import client as rdf_client
from grr.lib.rdfvalues import file_finder as rdf_file_finder
from grr.lib.rdfvalues import flows as rdf_flows
from grr.lib.rdfvalues import paths as rdf_paths
from grr.server import data_store
from grr.server import file_store
from grr.server import flow
from grr.server import server_stubs
from grr.server.flows.general import filesystem
from grr.server.flows.general import fingerprint
from grr.server.flows.general import transfer


class FileFinder(transfer.MultiGetFileMixin, fingerprint.FingerprintFileMixin,
                 filesystem.GlobMixin, flow.GRRFlow):
  """This flow looks for files matching given criteria and acts on them.

  FileFinder searches for files that match glob expressions.  The "action"
  (e.g. Download) is applied to files that match all given "conditions".
  Matches are then written to the results collection. If there are no
  "conditions" specified, "action" is just applied to all found files.

  FileFinder replaces these deprecated flows: FetchFiles, FingerprintFile
  and SearchFileContent.
  """
  friendly_name = "File Finder"
  category = "/Filesystem/"
  args_type = rdf_file_finder.FileFinderArgs
  behaviours = flow.GRRFlow.behaviours + "BASIC"

  # Will be used by FingerprintFileMixin.
  fingerprint_file_mixin_client_action = server_stubs.HashFile

  def Initialize(self):
    super(FileFinder, self).Initialize()
    type_enum = rdf_file_finder.FileFinderCondition.Type
    # For every condition type we specify a tuple (handle, weight).
    # Conditions will be sorted by weight, so that the ones with the minimal
    # weight will be executed earlier.
    self.condition_handlers = {
        type_enum.MODIFICATION_TIME: (self.ModificationTimeCondition, 0),
        type_enum.ACCESS_TIME: (self.AccessTimeCondition, 0),
        type_enum.INODE_CHANGE_TIME: (self.InodeChangeTimeCondition, 0),
        type_enum.SIZE: (self.SizeCondition, 0),
        type_enum.CONTENTS_REGEX_MATCH: (self.ContentsRegexMatchCondition, 1),
        type_enum.CONTENTS_LITERAL_MATCH: (self.ContentsLiteralMatchCondition,
                                           1)
    }

  def _ConditionWeight(self, condition_options):
    _, condition_weight = self.condition_handlers[
        condition_options.condition_type]
    return condition_weight

  @flow.StateHandler()
  def Start(self):
    """Issue the find request."""
    super(FileFinder, self).Start()

    if not self.args.paths:
      # Nothing to do.
      return

    self.state.files_found = 0
    self.state.sorted_conditions = sorted(
        self.args.conditions, key=self._ConditionWeight)

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

    # This is used by MultiGetFileMixin.
    if action.action_type == rdf_file_finder.FileFinderAction.Action.HASH:
      self.state.file_size = action.hash.max_size
    elif action.action_type == rdf_file_finder.FileFinderAction.Action.DOWNLOAD:
      self.state.file_size = action.download.max_size

    if self.args.pathtype in (rdf_paths.PathSpec.PathType.MEMORY,
                              rdf_paths.PathSpec.PathType.REGISTRY):
      # Memory and Registry StatEntries won't pass the file type check.
      self.args.process_non_regular_files = True

    if self.args.pathtype == rdf_paths.PathSpec.PathType.MEMORY:
      # If pathtype is MEMORY, we're treating provided paths not as globs,
      # but as paths to memory devices.
      for path in self.args.paths:
        pathspec = rdf_paths.PathSpec(
            path=utils.SmartUnicode(path),
            pathtype=rdf_paths.PathSpec.PathType.MEMORY)

        stat_entry = rdf_client.StatEntry(pathspec=pathspec)
        self.ApplyCondition(
            rdf_file_finder.FileFinderResult(stat_entry=stat_entry),
            condition_index=0)

    else:
      self.GlobForPaths(
          self.args.paths,
          pathtype=self.args.pathtype,
          process_non_regular_files=self.args.process_non_regular_files)

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
    if (settings.min_last_modified_time.AsSecondsFromEpoch() <=
        response.stat_entry.st_mtime <=
        settings.max_last_modified_time.AsSecondsFromEpoch()):

      self.ApplyCondition(response, condition_index + 1)

  def AccessTimeCondition(self, response, condition_options, condition_index):
    """Applies access time condition to responses."""
    settings = condition_options.access_time
    if (settings.min_last_access_time.AsSecondsFromEpoch() <=
        response.stat_entry.st_atime <=
        settings.max_last_access_time.AsSecondsFromEpoch()):
      self.ApplyCondition(response, condition_index + 1)

  def InodeChangeTimeCondition(self, response, condition_options,
                               condition_index):
    """Applies inode change time condition to responses."""
    settings = condition_options.inode_change_time
    if (settings.min_last_inode_change_time.AsSecondsFromEpoch() <=
        response.stat_entry.st_ctime <=
        settings.max_last_inode_change_time.AsSecondsFromEpoch()):
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
    grep_spec = rdf_client.GrepSpec(
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
    grep_spec = rdf_client.GrepSpec(
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

  @flow.StateHandler()
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
      condition_handler, _ = self.condition_handlers[
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
            self.Log("%s too large to hash, skipping according to SKIP "
                     "policy. Size=%d",
                     response.stat_entry.pathspec.CollapsePath(), file_size)
          elif policy == options.OversizedFilePolicy.HASH_TRUNCATED:
            self.Log("%s too large to hash, hashing its first %d bytes "
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
            self.Log("%s too large to fetch, skipping according to SKIP "
                     "policy. Size=%d",
                     response.stat_entry.pathspec.CollapsePath(), file_size)
          elif policy == options.OversizedFilePolicy.HASH_TRUNCATED:
            self.Log("%s too large to fetch, hashing its first %d bytes "
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
    """Handle hash results from the FingerprintFileMixin."""
    if "original_result" in request_data:
      result = request_data["original_result"]
      result.hash_entry = hash_obj
      self.SendReply(result)
    else:
      raise RuntimeError("Got a fingerprintfileresult, but original result "
                         "is missing")

  def ReceiveFetchedFile(self, unused_stat_entry, file_hash, request_data=None):
    """Handle downloaded file from MultiGetFileMixin."""
    if "original_result" not in request_data:
      raise RuntimeError("Got fetched file data, but original result "
                         "is missing")

    result = request_data["original_result"]
    result.hash_entry = file_hash
    self.SendReply(result)

  def NotifyAboutEnd(self):
    files_found = self.state.get("files_found", 0)

    self.Notify("ViewObject", self.urn,
                "Found and processed %d files." % files_found)

  @flow.StateHandler()
  def End(self, responses):
    super(FileFinder, self).End()

    self.Log("Found and processed %d files.", self.state.files_found)


class ClientFileFinder(flow.GRRFlow):
  """A client side file finder flow."""

  friendly_name = "Client Side File Finder"
  category = "/Filesystem/"
  args_type = rdf_file_finder.FileFinderArgs

  @flow.StateHandler()
  def Start(self):
    """Issue the find request."""
    super(ClientFileFinder, self).Start()

    if self.args.pathtype != "OS":
      raise ValueError("Only supported pathtype is OS.")

    action = self.args.action
    if action.action_type == "DOWNLOAD":
      policy = rdf_client.UploadPolicy(
          client_id=self.client_id,
          expires=rdfvalue.RDFDatetime.Now() + rdfvalue.Duration("7d"))
      upload_token = rdf_client.UploadToken()
      upload_token.SetPolicy(policy)
      upload_token.GenerateHMAC()
      action.download.upload_token = upload_token

    self.CallClient(
        server_stubs.FileFinderOS, request=self.args, next_state="StoreResults")

  def _CreateAFF4ObjectForUploadedFile(self, uploaded_file):
    upload_store = file_store.UploadFileStore.GetPlugin(
        config.CONFIG["Frontend.upload_store"])()
    urn = uploaded_file.stat_entry.pathspec.AFF4Path(self.client_id)

    with upload_store.Aff4ObjectForFileId(
        urn, uploaded_file.file_id, token=self.token) as fd:
      fd.Set(fd.Schema.STAT, uploaded_file.stat_entry)
      fd.Set(fd.Schema.SIZE(uploaded_file.bytes_uploaded))
      fd.Set(fd.Schema.HASH(uploaded_file.hash))

  @flow.StateHandler()
  def StoreResults(self, responses):
    if not responses.success:
      raise flow.FlowError(responses.status)

    self.state.files_found = len(responses)
    with data_store.DB.GetMutationPool() as pool:
      for response in responses:
        if response.uploaded_file.file_id:
          self._CreateAFF4ObjectForUploadedFile(response.uploaded_file)
          # TODO(amoser): Make the export support UploadedFile directly.
          # This fixes the export which expects the stat_entry in
          # response.stat_entry only.
          response.stat_entry = response.uploaded_file.stat_entry
        elif response.stat_entry:
          filesystem.CreateAFF4Object(
              response.stat_entry, self.client_id, pool, token=self.token)
        self.SendReply(response)

        if stat.S_ISREG(response.stat_entry.st_mode):
          # Publish the new file event to cause the file to be added to the
          # filestore. This is not time critical so do it when we have spare
          # capacity.
          self.Publish(
              "FileStore.AddFileToStore",
              response.stat_entry.pathspec.AFF4Path(self.client_id),
              priority=rdf_flows.GrrMessage.Priority.LOW_PRIORITY)

  @flow.StateHandler()
  def End(self, responses):
    super(ClientFileFinder, self).End()

    self.Log("Found and processed %d files.", self.state.files_found)
