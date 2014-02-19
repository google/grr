#!/usr/bin/env python
"""Search for certain files, filter them by given criteria and do something."""



import stat

from grr.lib import aff4
from grr.lib import flow
from grr.lib import rdfvalue
from grr.lib import utils
from grr.proto import flows_pb2


class FileFinderModificationTimeFilter(rdfvalue.RDFProtoStruct):
  protobuf = flows_pb2.FileFinderModificationTimeFilter


class FileFinderAccessTimeFilter(rdfvalue.RDFProtoStruct):
  protobuf = flows_pb2.FileFinderAccessTimeFilter


class FileFinderInodeChangeTimeFilter(rdfvalue.RDFProtoStruct):
  protobuf = flows_pb2.FileFinderInodeChangeTimeFilter


class FileFinderSizeFilter(rdfvalue.RDFProtoStruct):
  protobuf = flows_pb2.FileFinderSizeFilter


class FileFinderContentsRegexMatchFilter(rdfvalue.RDFProtoStruct):
  protobuf = flows_pb2.FileFinderContentsRegexMatchFilter


class FileFinderContentsLiteralMatchFilter(rdfvalue.RDFProtoStruct):
  protobuf = flows_pb2.FileFinderContentsLiteralMatchFilter


class FileFinderFilter(rdfvalue.RDFProtoStruct):
  protobuf = flows_pb2.FileFinderFilter


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
  """
  friendly_name = "File Finder"
  category = "/Filesystem/"
  args_type = FileFinderArgs
  # TODO(user): move to BASIC as soon as this flow is properly
  # tested and benchmarked. Remove Fetch Files and Find Files at the
  # same moment.
  behaviours = flow.GRRFlow.behaviours + "ADVANCED"

  @classmethod
  def GetDefaultArgs(cls, token=None):
    _ = token
    return cls.args_type(paths=[r"c:\windows\system32\notepad.*"])

  def Initialize(self):
    super(FileFinder, self).Initialize()
    type_enum = rdfvalue.FileFinderFilter.Type
    # For every filter type we specify a tuple (handle, weight).
    # Filters will be sorted by weight, so that the ones with the minimal
    # weight will be executed earlier.
    self.filter_handlers = {
        type_enum.MODIFICATION_TIME: (self.ModificationTimeFilter, 0),
        type_enum.ACCESS_TIME: (self.AccessTimeFilter, 0),
        type_enum.INODE_CHANGE_TIME: (self.InodeChangeTimeFilter, 0),
        type_enum.SIZE: (self.SizeFilter, 0),
        type_enum.CONTENTS_REGEX_MATCH: (self.ContentsRegexMatchFilter, 1),
        type_enum.CONTENTS_LITERAL_MATCH: (self.ContentsLiteralMatchFilter, 1)
        }

  def _FilterWeight(self, filter_options):
    _, filter_weight = self.filter_handlers[filter_options.filter_type]
    return filter_weight

  @flow.StateHandler(next_state=["ProcessFilters"])
  def Start(self):
    """Issue the find request."""
    self.state.Register("files_to_fetch", [])
    self.state.Register("files_found", 0)
    self.state.Register("sorted_filters",
                        sorted(self.args.filters, key=self._FilterWeight))

    if self.args.pathtype == rdfvalue.PathSpec.PathType.MEMORY:
      # We construct StatEntries ourselves and there's no way they can
      # pass the file type check.
      self.args.no_file_type_check = True

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
                           next_state="ProcessFilters")
    else:
      self.CallFlow("Glob", next_state="ProcessFilters", paths=self.args.paths,
                    pathtype=self.args.pathtype)

  @flow.StateHandler(next_state=["ApplyFilter"])
  def ProcessFilters(self, responses):
    """Iterate through glob responses, and filter each hit."""
    if not responses.success:
      # Glob failing is fatal here.
      return self.Error("Failed Glob: %s", responses.status)

    results = []
    for response in responses:
      # Only process regular files.
      if self.args.no_file_type_check or stat.S_ISREG(response.st_mode):
        results.append(rdfvalue.FileFinderResult(stat_entry=response))

    self.CallStateInline(messages=results, next_state="ApplyFilter",
                         request_data=dict(filter_index=0))

  def ModificationTimeFilter(self, responses, filter_options, filter_index):
    """Applies modification time filter to responses."""
    results = []
    for response in responses:
      settings = filter_options.modification_time
      if (settings.min_last_modified_time.AsSecondsFromEpoch() <=
          response.stat_entry.st_mtime <=
          settings.max_last_modified_time.AsSecondsFromEpoch()):
        results.append(response)

    self.CallStateInline(messages=results, next_state="ApplyFilter",
                         request_data=dict(filter_index=filter_index + 1))

  def AccessTimeFilter(self, responses, filter_options, filter_index):
    """Applies access time filter to responses."""
    results = []
    for response in responses:
      settings = filter_options.access_time
      if (settings.min_last_access_time.AsSecondsFromEpoch() <=
          response.stat_entry.st_atime <=
          settings.max_last_access_time.AsSecondsFromEpoch()):
        results.append(response)

    self.CallStateInline(messages=results, next_state="ApplyFilter",
                         request_data=dict(filter_index=filter_index + 1))

  def InodeChangeTimeFilter(self, responses, filter_options, filter_index):
    """Applies inode change time filter to responses."""
    results = []
    for response in responses:
      settings = filter_options.inode_change_time
      if (settings.min_last_inode_change_time.AsSecondsFromEpoch() <=
          response.stat_entry.st_ctime <=
          settings.max_last_inode_change_time.AsSecondsFromEpoch()):
        results.append(response)

    self.CallStateInline(messages=results, next_state="ApplyFilter",
                         request_data=dict(filter_index=filter_index + 1))

  def SizeFilter(self, responses, filter_options, filter_index):
    """Applies size filter to responses."""
    results = []
    for response in responses:
      if (filter_options.size.min_file_size <=
          response.stat_entry.st_size <=
          filter_options.size.max_file_size):
        results.append(response)

    self.CallStateInline(messages=results, next_state="ApplyFilter",
                         request_data=dict(filter_index=filter_index + 1))

  def ContentsRegexMatchFilter(self, responses, filter_options, filter_index):
    """Applies contents regex filter to responses."""
    options = filter_options.contents_regex_match
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
          "Grep", request=grep_spec, next_state="ApplyFilter",
          request_data=dict(
              original_result=response,
              filter_index=filter_index + 1))

  def ContentsLiteralMatchFilter(self, responses, filter_options, filter_index):
    """Applies literal match filter to responses."""
    options = filter_options.contents_literal_match
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
          "Grep", request=grep_spec, next_state="ApplyFilter",
          request_data=dict(
              original_result=response,
              filter_index=filter_index + 1))

  @flow.StateHandler(next_state=["ProcessAction", "ApplyFilter"])
  def ApplyFilter(self, responses):
    """Applies next filter to responses or calls ProcessAction."""
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

    filter_index = responses.request_data["filter_index"]

    if filter_index >= len(self.state.sorted_filters):
      self.CallStateInline(messages=messages, next_state="ProcessAction")
    else:
      filter_options = self.state.sorted_filters[filter_index]
      filter_handler, _ = self.filter_handlers[filter_options.filter_type]
      filter_handler(messages, filter_options, filter_index)

  @flow.StateHandler(next_state=["Done"])
  def ProcessAction(self, responses):
    """Applies action specified by user to responses."""
    self.state.files_found += len(responses)
    for response in responses:
      self.SendReply(response)

    action = self.state.args.action.action_type
    if action == rdfvalue.FileFinderAction.Action.DO_NOTHING:
      self.DoNothingAction(responses)
    elif action == rdfvalue.FileFinderAction.Action.HASH:
      self.HashAction(responses)
    elif action == rdfvalue.FileFinderAction.Action.DOWNLOAD:
      self.DownloadAction(responses)

  def DoNothingAction(self, responses):
    pass

  def HashAction(self, responses):
    """Calls FingerprintFile for every response."""
    for response in responses:
      self.CallFlow("FingerprintFile", pathspec=response.stat_entry.pathspec,
                    next_state="Done")

  def DownloadAction(self, responses):
    """Downloads files corresponding to all the responses."""
    files_to_fetch = []

    for response in responses:
      # If the binary is too large we just ignore it.
      file_size = response.stat_entry.st_size
      if file_size > self.args.action.download.max_size:
        self.Log("%s too large to fetch. Size=%d",
                 response.stat_entry.pathspec.CollapsePath(), file_size)

      files_to_fetch.append(response.stat_entry.pathspec)

    if files_to_fetch:
      use_stores = self.args.action.download.use_external_stores
      self.CallFlow(
          "MultiGetFile", pathspecs=files_to_fetch,
          use_external_stores=use_stores, next_state="Done")

  @flow.StateHandler()
  def Done(self, responses):
    pass

  @flow.StateHandler()
  def End(self, responses):
    self.Log("Found and processed %d files.", self.state.files_found)
