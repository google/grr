#!/usr/bin/env python
"""The various FileFinder rdfvalues."""

from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

from grr_response_core.lib import rdfvalue
from grr_response_core.lib.rdfvalues import client as rdf_client
from grr_response_core.lib.rdfvalues import client_fs as rdf_client_fs
from grr_response_core.lib.rdfvalues import crypto as rdf_crypto
from grr_response_core.lib.rdfvalues import paths as rdf_paths
from grr_response_core.lib.rdfvalues import standard as rdf_standard
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
    super(FileFinderExtFlagsCondition, self).__init__(*args, **kwargs)
    self.linux_bits_set = self.linux_bits_set or 0
    self.linux_bits_unset = self.linux_bits_unset or 0
    self.osx_bits_set = self.osx_bits_set or 0
    self.osx_bits_unset = self.osx_bits_unset or 0


class FileFinderContentsRegexMatchCondition(rdf_structs.RDFProtoStruct):
  protobuf = flows_pb2.FileFinderContentsRegexMatchCondition
  rdf_deps = [
      rdf_standard.RegularExpression,
  ]


class FileFinderContentsLiteralMatchCondition(rdf_structs.RDFProtoStruct):
  protobuf = flows_pb2.FileFinderContentsLiteralMatchCondition
  rdf_deps = [
      rdf_standard.LiteralExpression,
  ]


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


class FileFinderStatActionOptions(rdf_structs.RDFProtoStruct):
  protobuf = flows_pb2.FileFinderStatActionOptions


class FileFinderHashActionOptions(rdf_structs.RDFProtoStruct):
  protobuf = flows_pb2.FileFinderHashActionOptions
  rdf_deps = [
      rdfvalue.ByteSize,
  ]


class FileFinderDownloadActionOptions(rdf_structs.RDFProtoStruct):
  protobuf = flows_pb2.FileFinderDownloadActionOptions
  rdf_deps = [
      rdfvalue.ByteSize,
  ]


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
  protobuf = flows_pb2.FileFinderArgs
  rdf_deps = [
      FileFinderAction,
      FileFinderCondition,
      rdf_paths.GlobExpression,
  ]


class FileFinderResult(rdf_structs.RDFProtoStruct):
  protobuf = flows_pb2.FileFinderResult
  rdf_deps = [
      rdf_client.BufferReference,
      rdf_crypto.Hash,
      rdf_client_fs.StatEntry,
      rdf_client_fs.BlobImageDescriptor,
  ]
