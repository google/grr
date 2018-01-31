#!/usr/bin/env python
"""The various FileFinder rdfvalues."""

from grr.lib import rdfvalue
from grr.lib.rdfvalues import client
from grr.lib.rdfvalues import crypto
from grr.lib.rdfvalues import paths
from grr.lib.rdfvalues import standard
from grr.lib.rdfvalues import structs as rdf_structs
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


class FileFinderContentsRegexMatchCondition(rdf_structs.RDFProtoStruct):
  protobuf = flows_pb2.FileFinderContentsRegexMatchCondition
  rdf_deps = [
      standard.RegularExpression,
  ]


class FileFinderContentsLiteralMatchCondition(rdf_structs.RDFProtoStruct):
  protobuf = flows_pb2.FileFinderContentsLiteralMatchCondition
  rdf_deps = [
      standard.LiteralExpression,
  ]


class FileFinderCondition(rdf_structs.RDFProtoStruct):
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
      client.UploadToken,
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
      paths.GlobExpression,
  ]


class FileFinderResult(rdf_structs.RDFProtoStruct):
  protobuf = flows_pb2.FileFinderResult
  rdf_deps = [
      client.BufferReference,
      crypto.Hash,
      client.StatEntry,
      client.UploadedFile,
  ]
