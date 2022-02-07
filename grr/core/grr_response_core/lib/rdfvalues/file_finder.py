#!/usr/bin/env python
"""The various FileFinder rdfvalues."""

from grr_response_core.lib import rdfvalue
from grr_response_core.lib.rdfvalues import client as rdf_client
from grr_response_core.lib.rdfvalues import client_fs as rdf_client_fs
from grr_response_core.lib.rdfvalues import crypto as rdf_crypto
from grr_response_core.lib.rdfvalues import paths as rdf_paths
from grr_response_core.lib.rdfvalues import structs as rdf_structs
from grr_response_proto import flows_pb2


class FileFinderModificationTimeCondition(rdf_structs.RDFProtoStruct):
  protobuf = flows_pb2.FileFinderModificationTimeCondition
  rdf_deps = [
      rdfvalue.RDFDatetime,
  ]


class FileFinderAccessTimeCondition(rdf_structs.RDFProtoStruct):
  protobuf = flows_pb2.FileFinderAccessTimeCondition
  rdf_deps = [
      rdfvalue.RDFDatetime,
  ]


class FileFinderInodeChangeTimeCondition(rdf_structs.RDFProtoStruct):
  protobuf = flows_pb2.FileFinderInodeChangeTimeCondition
  rdf_deps = [
      rdfvalue.RDFDatetime,
  ]


class FileFinderSizeCondition(rdf_structs.RDFProtoStruct):
  protobuf = flows_pb2.FileFinderSizeCondition


class FileFinderExtFlagsCondition(rdf_structs.RDFProtoStruct):

  protobuf = flows_pb2.FileFinderExtFlagsCondition

  def __init__(self, *args, **kwargs):
    super().__init__(*args, **kwargs)
    self.linux_bits_set = self.linux_bits_set or 0
    self.linux_bits_unset = self.linux_bits_unset or 0
    self.osx_bits_set = self.osx_bits_set or 0
    self.osx_bits_unset = self.osx_bits_unset or 0


class FileFinderContentsRegexMatchCondition(rdf_structs.RDFProtoStruct):
  protobuf = flows_pb2.FileFinderContentsRegexMatchCondition

  rdf_deps = [rdfvalue.RDFBytes]


class FileFinderContentsLiteralMatchCondition(rdf_structs.RDFProtoStruct):
  """An RDF value representing file finder contents literal match conditions."""

  protobuf = flows_pb2.FileFinderContentsLiteralMatchCondition

  rdf_deps = [rdfvalue.RDFBytes]

  def Validate(self):
    """Check the literal match condition is well constructed."""
    super().Validate()

    # The literal must not be empty in the literal match condition.
    if not self.HasField("literal") or not self.literal:
      raise ValueError(
          "No literal provided to FileFinderContentsLiteralMatchCondition.")


class FileFinderCondition(rdf_structs.RDFProtoStruct):
  """An RDF value representing file finder conditions."""

  protobuf = flows_pb2.FileFinderCondition
  rdf_deps = [
      FileFinderAccessTimeCondition,
      FileFinderContentsLiteralMatchCondition,
      FileFinderContentsRegexMatchCondition,
      FileFinderInodeChangeTimeCondition,
      FileFinderModificationTimeCondition,
      FileFinderSizeCondition,
      FileFinderExtFlagsCondition,
  ]

  @classmethod
  def AccessTime(cls, **kwargs):
    condition_type = cls.Type.ACCESS_TIME
    opts = FileFinderAccessTimeCondition(**kwargs)
    return cls(condition_type=condition_type, access_time=opts)

  @classmethod
  def ModificationTime(cls, **kwargs):
    condition_type = cls.Type.MODIFICATION_TIME
    opts = FileFinderModificationTimeCondition(**kwargs)
    return cls(condition_type=condition_type, modification_time=opts)

  @classmethod
  def InodeChangeTime(cls, **kwargs):
    condition_type = cls.Type.INODE_CHANGE_TIME
    opts = FileFinderInodeChangeTimeCondition(**kwargs)
    return cls(condition_type=condition_type, inode_change_time=opts)

  @classmethod
  def Size(cls, **kwargs):
    condition_type = cls.Type.SIZE
    opts = FileFinderSizeCondition(**kwargs)
    return cls(condition_type=condition_type, size=opts)

  @classmethod
  def ExtFlags(cls, **kwargs):
    condition_type = cls.Type.EXT_FLAGS
    opts = FileFinderExtFlagsCondition(**kwargs)
    return cls(condition_type=condition_type, ext_flags=opts)

  @classmethod
  def ContentsLiteralMatch(cls, **kwargs):
    condition_type = cls.Type.CONTENTS_LITERAL_MATCH
    opts = FileFinderContentsLiteralMatchCondition(**kwargs)
    return cls(condition_type=condition_type, contents_literal_match=opts)

  @classmethod
  def ContentsRegexMatch(cls, **kwargs):
    condition_type = cls.Type.CONTENTS_REGEX_MATCH
    opts = FileFinderContentsRegexMatchCondition(**kwargs)
    return cls(condition_type=condition_type, contents_regex_match=opts)

  def Validate(self):
    super().Validate()

    if self.HasField("modification_time"):
      self.modification_time.Validate()
    if self.HasField("access_time"):
      self.access_time.Validate()
    if self.HasField("inode_change_time"):
      self.inode_change_time.Validate()
    if self.HasField("size"):
      self.size.Validate()
    if self.HasField("ext_flags"):
      self.ext_flags.Validate()
    if self.HasField("contents_regex_match"):
      self.contents_regex_match.Validate()
    if self.HasField("contents_literal_match"):
      self.contents_literal_match.Validate()


class FileFinderStatActionOptions(rdf_structs.RDFProtoStruct):
  """FileFinder stat action options RDFStruct."""

  protobuf = flows_pb2.FileFinderStatActionOptions

  def __init__(self, *args, **kwargs):
    super().__init__(*args, **kwargs)

    if not self.HasField("collect_ext_attrs"):
      self.collect_ext_attrs = False


class FileFinderHashActionOptions(rdf_structs.RDFProtoStruct):
  """FileFinder hash action options RDFStruct."""

  protobuf = flows_pb2.FileFinderHashActionOptions
  rdf_deps = [
      rdfvalue.ByteSize,
  ]

  def __init__(self, *args, **kwargs):
    super().__init__(*args, **kwargs)

    if not self.HasField("collect_ext_attrs"):
      self.collect_ext_attrs = False


class FileFinderDownloadActionOptions(rdf_structs.RDFProtoStruct):
  """FileFinder download action options RDFStruct."""

  protobuf = flows_pb2.FileFinderDownloadActionOptions
  rdf_deps = [
      rdfvalue.ByteSize,
  ]

  def __init__(self, *args, **kwargs):
    super().__init__(*args, **kwargs)

    if not self.HasField("collect_ext_attrs"):
      self.collect_ext_attrs = False


class FileFinderAction(rdf_structs.RDFProtoStruct):
  """An RDF value describing a file-finder action."""

  protobuf = flows_pb2.FileFinderAction
  rdf_deps = [
      FileFinderDownloadActionOptions,
      FileFinderHashActionOptions,
      FileFinderStatActionOptions,
  ]

  @classmethod
  def Stat(cls, **kwargs):
    action_type = cls.Action.STAT
    opts = FileFinderStatActionOptions(**kwargs)
    return FileFinderAction(action_type=action_type, stat=opts)

  @classmethod
  def Hash(cls, **kwargs):
    action_type = cls.Action.HASH
    opts = FileFinderHashActionOptions(**kwargs)
    return FileFinderAction(action_type=action_type, hash=opts)

  @classmethod
  def Download(cls, **kwargs):
    action_type = cls.Action.DOWNLOAD
    opts = FileFinderDownloadActionOptions(**kwargs)
    return FileFinderAction(action_type=action_type, download=opts)


class FileFinderArgs(rdf_structs.RDFProtoStruct):
  """An RDF value representing file finder flow arguments."""
  protobuf = flows_pb2.FileFinderArgs
  rdf_deps = [
      FileFinderAction,
      FileFinderCondition,
      rdf_paths.GlobExpression,
  ]

  def Validate(self):
    super().Validate()

    for condition in self.conditions:
      condition.Validate()


class FileFinderResult(rdf_structs.RDFProtoStruct):
  protobuf = flows_pb2.FileFinderResult
  rdf_deps = [
      rdf_client.BufferReference,
      rdf_crypto.Hash,
      rdf_client_fs.StatEntry,
      rdf_client_fs.BlobImageDescriptor,
  ]


class CollectSingleFileArgs(rdf_structs.RDFProtoStruct):
  """Arguments for CollectSingleFile."""
  protobuf = flows_pb2.CollectSingleFileArgs
  rdf_deps = [rdfvalue.ByteSize]


class CollectSingleFileResult(rdf_structs.RDFProtoStruct):
  """Result returned by CollectSingleFile."""
  protobuf = flows_pb2.CollectSingleFileResult
  rdf_deps = [
      rdf_crypto.Hash,
      rdf_client_fs.StatEntry,
  ]


class CollectSingleFileProgress(rdf_structs.RDFProtoStruct):
  """Progress returned by CollectSingleFile."""
  protobuf = flows_pb2.CollectSingleFileProgress
  rdf_deps = [
      CollectSingleFileResult,
  ]


class CollectFilesByKnownPathArgs(rdf_structs.RDFProtoStruct):
  """Arguments for CollectFilesByKnownPath."""
  protobuf = flows_pb2.CollectFilesByKnownPathArgs
  rdf_deps = []


class CollectFilesByKnownPathResult(rdf_structs.RDFProtoStruct):
  """Result returned by CollectFilesByKnownPath."""
  protobuf = flows_pb2.CollectFilesByKnownPathResult
  rdf_deps = [
      rdf_crypto.Hash,
      rdf_client_fs.StatEntry,
  ]


class CollectFilesByKnownPathProgress(rdf_structs.RDFProtoStruct):
  """Progress returned by CollectFilesByKnownPath."""
  protobuf = flows_pb2.CollectFilesByKnownPathProgress
  rdf_deps = []


class CollectMultipleFilesArgs(rdf_structs.RDFProtoStruct):
  """Arguments for CollectMultipleFiles."""
  protobuf = flows_pb2.CollectMultipleFilesArgs
  rdf_deps = [
      rdf_paths.GlobExpression,
      FileFinderModificationTimeCondition,
      FileFinderAccessTimeCondition,
      FileFinderInodeChangeTimeCondition,
      FileFinderSizeCondition,
      FileFinderExtFlagsCondition,
      FileFinderContentsRegexMatchCondition,
      FileFinderContentsLiteralMatchCondition,
  ]


class CollectMultipleFilesResult(rdf_structs.RDFProtoStruct):
  """Result returned by CollectMultipleFiles."""
  protobuf = flows_pb2.CollectMultipleFilesResult
  rdf_deps = [
      rdf_crypto.Hash,
      rdf_client_fs.StatEntry,
  ]


class CollectMultipleFilesProgress(rdf_structs.RDFProtoStruct):
  """Progress returned by CollectMultipleFiles."""
  protobuf = flows_pb2.CollectMultipleFilesProgress
  rdf_deps = []
