#!/usr/bin/env python
"""Search for certain files, filter them by given criteria and do something."""



import stat

from grr.lib import aff4
from grr.lib import flow
from grr.lib import rdfvalue
from grr.lib import utils
from grr.proto import flows_pb2


class FileFinderModificationTimeCondition(rdfvalue.RDFProtoStruct):
  protobuf = flows_pb2.FileFinderModificationTimeCondition


class FileFinderAccessTimeCondition(rdfvalue.RDFProtoStruct):
  protobuf = flows_pb2.FileFinderAccessTimeCondition


class FileFinderInodeChangeTimeCondition(rdfvalue.RDFProtoStruct):
  protobuf = flows_pb2.FileFinderInodeChangeTimeCondition


class FileFinderSizeCondition(rdfvalue.RDFProtoStruct):
  protobuf = flows_pb2.FileFinderSizeCondition


class FileFinderContentsRegexMatchCondition(rdfvalue.RDFProtoStruct):
  protobuf = flows_pb2.FileFinderContentsRegexMatchCondition


class FileFinderContentsLiteralMatchCondition(rdfvalue.RDFProtoStruct):
  protobuf = flows_pb2.FileFinderContentsLiteralMatchCondition


class FileFinderCondition(rdfvalue.RDFProtoStruct):
  protobuf = flows_pb2.FileFinderCondition


class FileFinderDownloadActionOptions(rdfvalue.RDFProtoStruct):
  protobuf = flows_pb2.FileFinderDownloadActionOptions


class FileFinderAction(rdfvalue.RDFProtoStruct):
  protobuf = flows_pb2.FileFinderAction


class FileFinderArgs(rdfvalue.RDFProtoStruct):
  protobuf = flows_pb2.FileFinderArgs


class FileFinderResult(rdfvalue.RDFProtoStruct):
  protobuf = flows_pb2.FileFinderResult


class FileFinder(flow.GRRFlow):
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
  args_type = FileFinderArgs
  behaviours = flow.GRRFlow.behaviours + "BASIC"

  @classmethod
  def GetDefaultArgs(cls, token=None):
    _ = token
    return cls.args_type(paths=[r"c:\windows\system32\notepad.*"])

  def Initialize(self):
    super(FileFinder, self).Initialize()
    type_enum = rdfvalue.FileFinderCondition.Type
    # For every condition type we specify a tuple (handle, weight).
    # Conditions will be sorted by weight, so that the ones with the minimal
    # weight will be executed earlier.
    self.condition_handlers = {
        type_enum.MODIFICATION_TIME: (self.ModificationTimeCondition, 0),
        type_enum.ACCESS_TIME: (self.AccessTimeCondition, 0),
        type_enum.INODE_CHANGE_TIME: (self.InodeChangeTimeCondition, 0),
        type_enum.SIZE: (self.SizeCondition, 0),
        type_enum.CONTENTS_REGEX_MATCH: (self.ContentsRegexMatchCondition, 1),
        type_enum.CONTENTS_LITERAL_MATCH: (
            self.ContentsLiteralMatchCondition, 1)
        }

  def _ConditionWeight(self, condition_options):
    _, condition_weight = self.condition_handlers[
        condition_options.condition_type]
    return condition_weight

  @flow.StateHandler(next_state=["ProcessConditions"])
  def Start(self):
    """Issue the find request."""
    self.state.Register("files_to_fetch", [])
    self.state.Register("files_found", 0)
    self.state.Register("sorted_conditions",
                        sorted(self.args.conditions, key=self._ConditionWeight))

    if self.args.pathtype in (rdfvalue.PathSpec.PathType.MEMORY,
                              rdfvalue.PathSpec.PathType.REGISTRY):
      # Memory and Registry StatEntries won't pass the file type check.
      self.args.no_file_type_check = True

    if self.args.pathtype == rdfvalue.PathSpec.PathType.MEMORY:
      # If pathtype is MEMORY, we're treating provided paths not as globs,
      # but as paths to memory devices.
      memory_devices = []
      for path in self.args.paths:
        pathspec = rdfvalue.PathSpec(
            path=utils.SmartUnicode(path),
            pathtype=rdfvalue.PathSpec.PathType.MEMORY)
        aff4path = aff4.AFF4Object.VFSGRRClient.PathspecToURN(
            pathspec, self.client_id)
        stat_entry = rdfvalue.StatEntry(aff4path=aff4path, pathspec=pathspec)
        memory_devices.append(stat_entry)

      self.CallStateInline(messages=memory_devices,
                           next_state="ProcessConditions")
    else:
      self.CallFlow("Glob", next_state="ProcessConditions",
                    paths=self.args.paths, pathtype=self.args.pathtype)

  @flow.StateHandler(next_state=["ApplyCondition"])
  def ProcessConditions(self, responses):
    """Iterate through glob responses, and filter each hit."""
    if not responses.success:
      # Glob failing is fatal here.
      return self.Error("Failed Glob: %s", responses.status)

    results = []
    for response in responses:
      # Only process regular files.
      if self.args.no_file_type_check or stat.S_ISREG(response.st_mode):
        results.append(rdfvalue.FileFinderResult(stat_entry=response))

    self.CallStateInline(messages=results, next_state="ApplyCondition",
                         request_data=dict(condition_index=0))

  def ModificationTimeCondition(self, responses, condition_options,
                                condition_index):
    """Applies modification time condition to responses."""
    results = []
    for response in responses:
      settings = condition_options.modification_time
      if (settings.min_last_modified_time.AsSecondsFromEpoch() <=
          response.stat_entry.st_mtime <=
          settings.max_last_modified_time.AsSecondsFromEpoch()):
        results.append(response)

    self.CallStateInline(messages=results, next_state="ApplyCondition",
                         request_data=dict(condition_index=condition_index + 1))

  def AccessTimeCondition(self, responses, condition_options, condition_index):
    """Applies access time condition to responses."""
    results = []
    for response in responses:
      settings = condition_options.access_time
      if (settings.min_last_access_time.AsSecondsFromEpoch() <=
          response.stat_entry.st_atime <=
          settings.max_last_access_time.AsSecondsFromEpoch()):
        results.append(response)

    self.CallStateInline(messages=results, next_state="ApplyCondition",
                         request_data=dict(condition_index=condition_index + 1))

  def InodeChangeTimeCondition(self, responses, condition_options,
                               condition_index):
    """Applies inode change time condition to responses."""
    results = []
    for response in responses:
      settings = condition_options.inode_change_time
      if (settings.min_last_inode_change_time.AsSecondsFromEpoch() <=
          response.stat_entry.st_ctime <=
          settings.max_last_inode_change_time.AsSecondsFromEpoch()):
        results.append(response)

    self.CallStateInline(messages=results, next_state="ApplyCondition",
                         request_data=dict(condition_index=condition_index + 1))

  def SizeCondition(self, responses, condition_options, condition_index):
    """Applies size condition to responses."""
    results = []
    for response in responses:
      if (condition_options.size.min_file_size <=
          response.stat_entry.st_size <=
          condition_options.size.max_file_size):
        results.append(response)

    self.CallStateInline(messages=results, next_state="ApplyCondition",
                         request_data=dict(condition_index=condition_index + 1))

  def ContentsRegexMatchCondition(self, responses, condition_options,
                                  condition_index):
    """Applies contents regex condition to responses."""
    options = condition_options.contents_regex_match
    for response in responses:
      grep_spec = rdfvalue.GrepSpec(
          target=response.stat_entry.pathspec,
          regex=options.regex,
          mode=options.mode,
          start_offset=options.start_offset,
          length=options.length,
          bytes_before=options.bytes_before,
          bytes_after=options.bytes_after)

      self.CallClient(
          "Grep", request=grep_spec, next_state="ApplyCondition",
          request_data=dict(
              original_result=response,
              condition_index=condition_index + 1))

  def ContentsLiteralMatchCondition(self, responses, condition_options,
                                    condition_index):
    """Applies literal match condition to responses."""
    options = condition_options.contents_literal_match
    for response in responses:
      grep_spec = rdfvalue.GrepSpec(
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
          "Grep", request=grep_spec, next_state="ApplyCondition",
          request_data=dict(
              original_result=response,
              condition_index=condition_index + 1))

  @flow.StateHandler(next_state=["ProcessAction", "ApplyCondition"])
  def ApplyCondition(self, responses):
    """Applies next condition to responses or calls ProcessAction."""
    # We filtered out everything, no need to continue
    if not responses:
      return

    messages = []
    for response in responses:
      if isinstance(response, rdfvalue.BufferReference):
        if "original_result" not in responses.request_data:
          raise RuntimeError("Got a buffer reference, but original result "
                             "is missing")

        if not messages:
          messages.append(responses.request_data["original_result"])

        messages[0].matches.append(response)
      else:
        messages.append(response)

    condition_index = responses.request_data["condition_index"]

    if condition_index >= len(self.state.sorted_conditions):
      self.CallStateInline(messages=messages, next_state="ProcessAction")
    else:
      condition_options = self.state.sorted_conditions[condition_index]
      condition_handler, _ = self.condition_handlers[
          condition_options.condition_type]
      condition_handler(messages, condition_options, condition_index)

  @flow.StateHandler(next_state=["HandleFingerprintResults", "Done"])
  def ProcessAction(self, responses):
    """Applies action specified by user to responses."""
    self.state.files_found += len(responses)

    action = self.state.args.action.action_type
    # For stat and download we can sendreply now, for hash we need to call
    # fingerprint file first.
    if action != rdfvalue.FileFinderAction.Action.HASH:
      for response in responses:
        self.SendReply(response)

    if action == rdfvalue.FileFinderAction.Action.STAT:
      self.StatAction(responses)
    elif action == rdfvalue.FileFinderAction.Action.HASH:
      self.HashAction(responses)
    elif action == rdfvalue.FileFinderAction.Action.DOWNLOAD:
      self.DownloadAction(responses)

  def StatAction(self, responses):
    # No need to do anything here, we already have StatEntries for all the files
    pass

  def HashAction(self, responses):
    """Calls FingerprintFile for every response."""
    for response in responses:
      self.CallFlow("FingerprintFile", pathspec=response.stat_entry.pathspec,
                    request_data=dict(original_result=response),
                    next_state="HandleFingerprintResults")

  def DownloadAction(self, responses):
    """Downloads files corresponding to all the responses."""
    files_to_fetch = []

    for response in responses:
      # If the binary is too large we just ignore it.
      file_size = response.stat_entry.st_size
      if file_size > self.args.action.download.max_size:
        self.Log("%s too large to fetch. Size=%d",
                 response.stat_entry.pathspec.CollapsePath(), file_size)
      else:
        files_to_fetch.append(response.stat_entry.pathspec)

    if files_to_fetch:
      use_stores = self.args.action.download.use_external_stores
      self.CallFlow(
          "MultiGetFile", pathspecs=files_to_fetch,
          use_external_stores=use_stores, next_state="Done")

  @flow.StateHandler(next_state=["Done"])
  def HandleFingerprintResults(self, responses):
    """Handle hash results."""
    if "original_result" in responses.request_data:
      result = responses.request_data["original_result"]
      result.hash_entry = responses.First().hash_entry
      self.SendReply(result)
    else:
      raise RuntimeError("Got a fingerprintfileresult, but original result "
                         "is missing")

  @flow.StateHandler()
  def Done(self, responses):
    pass

  @flow.StateHandler()
  def End(self, responses):
    self.Log("Found and processed %d files.", self.state.files_found)
    if self.runner.output:
      urn = self.runner.output.urn
    else:
      urn = self.client_id

    self.Notify("ViewObject", urn,
                "Found and processed %d files." % self.state.files_found)
