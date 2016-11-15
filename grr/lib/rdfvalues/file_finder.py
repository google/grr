#!/usr/bin/env python
"""The various FileFinder rdfvalues."""

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


class FileFinderHashActionOptions(rdf_structs.RDFProtoStruct):
  protobuf = flows_pb2.FileFinderHashActionOptions


class FileFinderDownloadActionOptions(rdf_structs.RDFProtoStruct):
  protobuf = flows_pb2.FileFinderDownloadActionOptions


class FileFinderStatActionOptions(rdf_structs.RDFProtoStruct):
  protobuf = flows_pb2.FileFinderStatActionOptions


class FileFinderAction(rdf_structs.RDFProtoStruct):
  protobuf = flows_pb2.FileFinderAction


class FileFinderArgs(rdf_structs.RDFProtoStruct):
  protobuf = flows_pb2.FileFinderArgs


class FileFinderResult(rdf_structs.RDFProtoStruct):
  protobuf = flows_pb2.FileFinderResult
