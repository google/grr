#!/usr/bin/env python
"""Search for certain files, filter them by given criteria and do something."""



import stat

from grr.lib import aff4
from grr.lib import flow
from grr.lib import utils
from grr.lib.flows.general import filesystem
from grr.lib.flows.general import fingerprint
from grr.lib.flows.general import transfer
from grr.lib.rdfvalues import client as rdf_client
from grr.lib.rdfvalues import paths as rdf_paths
from grr.lib.rdfvalues import structs as rdf_structs
from grr.proto import flows_pb2


class FileFinderModificationTimeCondition(rdf_structs.RDFProtoStruct):
  protobuf = flows_pb2.FileFinderModificationTimeCondition


class FileFinderAccessTimeCondition(rdf_structs.RDFProtoStruct):
  protobuf = flows_pb2.FileFinderAccessTimeCondition


class FileFinderInodeChangeTimeCondition(rdf_structs.RDFProtoStruct):
  protobuf = flows_pb2.FileFinderInodeChangeTimeCondition


class FileFinderSizeCondition(rdf_structs.RDFProtoStruct):
  protobuf = flows_pb2.FileFinderSizeCondition


class FileFinderContentsRegexMatchCondition(rdf_structs.RDFProtoStruct):
  protobuf = flows_pb2.FileFinderContentsRegexMatchCondition


class FileFinderContentsLiteralMatchCondition(rdf_structs.RDFProtoStruct):
  protobuf = flows_pb2.FileFinderContentsLiteralMatchCondition


class FileFinderCondition(rdf_structs.RDFProtoStruct):
  protobuf = flows_pb2.FileFinderCondition


class FileFinderDownloadActionOptions(rdf_structs.RDFProtoStruct):
  protobuf = flows_pb2.FileFinderDownloadActionOptions


class FileFinderAction(rdf_structs.RDFProtoStruct):
  protobuf = flows_pb2.FileFinderAction


class FileFinderArgs(rdf_structs.RDFProtoStruct):
  protobuf = flows_pb2.FileFinderArgs


class FileFinderResult(rdf_structs.RDFProtoStruct):
  protobuf = flows_pb2.FileFinderResult


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
  args_type = FileFinderArgs
  behaviours = flow.GRRFlow.behaviours + "BASIC"

  @classmethod
  def GetDefaultArgs(cls, token=None):
    _ = token
    return cls.args_type(paths=[r"c:\windows\system32\notepad.*"])

  def Initialize(self):
    super(FileFinder, self).Initialize()
    type_enum = FileFinderCondition.Type
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

    self.state.Register("files_found", 0)
    self.state.Register("sorted_conditions",
                        sorted(self.args.conditions,
                               key=self._ConditionWeight))

    self.state.file_size = self.args.file_size

    if self.args.pathtype in (rdf_paths.PathSpec.PathType.MEMORY,
                              rdf_paths.PathSpec.PathType.REGISTRY):
      # Memory and Registry StatEntries won't pass the file type check.
      self.args.no_file_type_check = True

    if self.args.pathtype == rdf_paths.PathSpec.PathType.MEMORY:
      # If pathtype is MEMORY, we're treating provided paths not as globs,
      # but as paths to memory devices.
      for path in self.args.paths:
        pathspec = rdf_paths.PathSpec(
            path=utils.SmartUnicode(path),
            pathtype=rdf_paths.PathSpec.PathType.MEMORY)

        aff4path = aff4.AFF4Object.VFSGRRClient.PathspecToURN(pathspec,
                                                              self.client_id)

        stat_entry = rdf_client.StatEntry(aff4path=aff4path, pathspec=pathspec)
        self.ApplyCondition(
            FileFinderResult(stat_entry=stat_entry),
            condition_index=0)

    else:
      self.GlobForPaths(self.args.paths,
                        pathtype=self.args.pathtype,
                        no_file_type_check=self.args.no_file_type_check)

  def GlobReportMatch(self, response):
    """This method is called by the glob mixin when there is a match."""
    super(FileFinder, self).GlobReportMatch(response)

    self.ApplyCondition(
        FileFinderResult(stat_entry=response),
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
    if not (self.args.no_file_type_check or
            stat.S_ISREG(response.stat_entry.st_mode)):
      return

    if (condition_options.size.min_file_size <= response.stat_entry.st_size <=
        condition_options.size.max_file_size):
      self.ApplyCondition(response, condition_index + 1)

  def ContentsRegexMatchCondition(self, response, condition_options,
                                  condition_index):
    """Applies contents regex condition to responses."""
    if not (self.args.no_file_type_check or
            stat.S_ISREG(response.stat_entry.st_mode)):
      return

    options = condition_options.contents_regex_match
    grep_spec = rdf_client.GrepSpec(target=response.stat_entry.pathspec,
                                    regex=options.regex,
                                    mode=options.mode,
                                    start_offset=options.start_offset,
                                    length=options.length,
                                    bytes_before=options.bytes_before,
                                    bytes_after=options.bytes_after)

    self.CallClient("Grep",
                    request=grep_spec,
                    next_state="ProcessGrep",
                    request_data=dict(original_result=response,
                                      condition_index=condition_index + 1))

  def ContentsLiteralMatchCondition(self, response, condition_options,
                                    condition_index):
    """Applies literal match condition to responses."""
    if not (self.args.no_file_type_check or
            stat.S_ISREG(response.stat_entry.st_mode)):
      return

    options = condition_options.contents_literal_match
    grep_spec = rdf_client.GrepSpec(target=response.stat_entry.pathspec,
                                    literal=options.literal,
                                    mode=options.mode,
                                    start_offset=options.start_offset,
                                    length=options.length,
                                    bytes_before=options.bytes_before,
                                    bytes_after=options.bytes_after,
                                    xor_in_key=options.xor_in_key,
                                    xor_out_key=options.xor_out_key)

    self.CallClient("Grep",
                    request=grep_spec,
                    next_state="ProcessGrep",
                    request_data=dict(original_result=response,
                                      condition_index=condition_index + 1))

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
    action = self.state.args.action.action_type

    if action == FileFinderAction.Action.STAT:
      # If action is STAT, we already have all the data we need to send the
      # response.
      self.state.files_found += 1
      self.SendReply(response)
    elif (self.args.no_file_type_check or
          stat.S_ISREG(response.stat_entry.st_mode)):
      # Hashing and downloading only makes sense for regular files. Reply is
      # sent only when we get file's hash.
      self.state.files_found += 1

      if action == FileFinderAction.Action.HASH:
        self.FingerprintFile(response.stat_entry.pathspec,
                             request_data=dict(original_result=response))

      elif action == FileFinderAction.Action.DOWNLOAD:
        # If the binary is too large we don't download it, but take a
        # fingerprint instead.
        file_size = response.stat_entry.st_size
        if file_size > self.args.action.download.max_size:
          self.Log("%s too large to fetch. Size=%d",
                   response.stat_entry.pathspec.CollapsePath(), file_size)
          self.FingerprintFile(response.stat_entry.pathspec,
                               request_data=dict(original_result=response))
        else:
          self.StartFileFetch(response.stat_entry.pathspec,
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

  @flow.StateHandler()
  def End(self, responses):
    super(FileFinder, self).End()

    self.Log("Found and processed %d files.", self.state.files_found)
    if self.runner.output is not None:
      urn = self.runner.output.urn
    else:
      urn = self.client_id

    self.Notify("ViewObject", urn,
                "Found and processed %d files." % self.state.files_found)
