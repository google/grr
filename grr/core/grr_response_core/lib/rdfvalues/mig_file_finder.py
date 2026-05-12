#!/usr/bin/env python
"""Provides conversion functions to be used during RDFProtoStruct migration."""

from grr_response_core.lib.rdfvalues import file_finder as rdf_file_finder
from grr_response_proto import flows_pb2


def ToProtoFileFinderModificationTimeCondition(
    rdf: rdf_file_finder.FileFinderModificationTimeCondition,
) -> flows_pb2.FileFinderModificationTimeCondition:
  return rdf.AsPrimitiveProto()


def ToRDFFileFinderModificationTimeCondition(
    proto: flows_pb2.FileFinderModificationTimeCondition,
) -> rdf_file_finder.FileFinderModificationTimeCondition:
  return (
      rdf_file_finder.FileFinderModificationTimeCondition.FromSerializedBytes(
          proto.SerializeToString()
      )
  )


def ToProtoFileFinderAccessTimeCondition(
    rdf: rdf_file_finder.FileFinderAccessTimeCondition,
) -> flows_pb2.FileFinderAccessTimeCondition:
  return rdf.AsPrimitiveProto()


def ToRDFFileFinderAccessTimeCondition(
    proto: flows_pb2.FileFinderAccessTimeCondition,
) -> rdf_file_finder.FileFinderAccessTimeCondition:
  return rdf_file_finder.FileFinderAccessTimeCondition.FromSerializedBytes(
      proto.SerializeToString()
  )


def ToProtoFileFinderInodeChangeTimeCondition(
    rdf: rdf_file_finder.FileFinderInodeChangeTimeCondition,
) -> flows_pb2.FileFinderInodeChangeTimeCondition:
  return rdf.AsPrimitiveProto()


def ToRDFFileFinderInodeChangeTimeCondition(
    proto: flows_pb2.FileFinderInodeChangeTimeCondition,
) -> rdf_file_finder.FileFinderInodeChangeTimeCondition:
  return rdf_file_finder.FileFinderInodeChangeTimeCondition.FromSerializedBytes(
      proto.SerializeToString()
  )


def ToProtoFileFinderSizeCondition(
    rdf: rdf_file_finder.FileFinderSizeCondition,
) -> flows_pb2.FileFinderSizeCondition:
  return rdf.AsPrimitiveProto()


def ToRDFFileFinderSizeCondition(
    proto: flows_pb2.FileFinderSizeCondition,
) -> rdf_file_finder.FileFinderSizeCondition:
  return rdf_file_finder.FileFinderSizeCondition.FromSerializedBytes(
      proto.SerializeToString()
  )


def ToProtoFileFinderExtFlagsCondition(
    rdf: rdf_file_finder.FileFinderExtFlagsCondition,
) -> flows_pb2.FileFinderExtFlagsCondition:
  return rdf.AsPrimitiveProto()


def ToRDFFileFinderExtFlagsCondition(
    proto: flows_pb2.FileFinderExtFlagsCondition,
) -> rdf_file_finder.FileFinderExtFlagsCondition:
  return rdf_file_finder.FileFinderExtFlagsCondition.FromSerializedBytes(
      proto.SerializeToString()
  )


def ToProtoFileFinderContentsRegexMatchCondition(
    rdf: rdf_file_finder.FileFinderContentsRegexMatchCondition,
) -> flows_pb2.FileFinderContentsRegexMatchCondition:
  return rdf.AsPrimitiveProto()


def ToRDFFileFinderContentsRegexMatchCondition(
    proto: flows_pb2.FileFinderContentsRegexMatchCondition,
) -> rdf_file_finder.FileFinderContentsRegexMatchCondition:
  return (
      rdf_file_finder.FileFinderContentsRegexMatchCondition.FromSerializedBytes(
          proto.SerializeToString()
      )
  )


def ToProtoFileFinderContentsLiteralMatchCondition(
    rdf: rdf_file_finder.FileFinderContentsLiteralMatchCondition,
) -> flows_pb2.FileFinderContentsLiteralMatchCondition:
  return rdf.AsPrimitiveProto()


def ToRDFFileFinderContentsLiteralMatchCondition(
    proto: flows_pb2.FileFinderContentsLiteralMatchCondition,
) -> rdf_file_finder.FileFinderContentsLiteralMatchCondition:
  return rdf_file_finder.FileFinderContentsLiteralMatchCondition.FromSerializedBytes(
      proto.SerializeToString()
  )


def ToProtoFileFinderCondition(
    rdf: rdf_file_finder.FileFinderCondition,
) -> flows_pb2.FileFinderCondition:
  return rdf.AsPrimitiveProto()


def ToRDFFileFinderCondition(
    proto: flows_pb2.FileFinderCondition,
) -> rdf_file_finder.FileFinderCondition:
  return rdf_file_finder.FileFinderCondition.FromSerializedBytes(
      proto.SerializeToString()
  )


def ToProtoFileFinderStatActionOptions(
    rdf: rdf_file_finder.FileFinderStatActionOptions,
) -> flows_pb2.FileFinderStatActionOptions:
  return rdf.AsPrimitiveProto()


def ToRDFFileFinderStatActionOptions(
    proto: flows_pb2.FileFinderStatActionOptions,
) -> rdf_file_finder.FileFinderStatActionOptions:
  return rdf_file_finder.FileFinderStatActionOptions.FromSerializedBytes(
      proto.SerializeToString()
  )


def ToProtoFileFinderHashActionOptions(
    rdf: rdf_file_finder.FileFinderHashActionOptions,
) -> flows_pb2.FileFinderHashActionOptions:
  return rdf.AsPrimitiveProto()


def ToRDFFileFinderHashActionOptions(
    proto: flows_pb2.FileFinderHashActionOptions,
) -> rdf_file_finder.FileFinderHashActionOptions:
  return rdf_file_finder.FileFinderHashActionOptions.FromSerializedBytes(
      proto.SerializeToString()
  )


def ToProtoFileFinderDownloadActionOptions(
    rdf: rdf_file_finder.FileFinderDownloadActionOptions,
) -> flows_pb2.FileFinderDownloadActionOptions:
  return rdf.AsPrimitiveProto()


def ToRDFFileFinderDownloadActionOptions(
    proto: flows_pb2.FileFinderDownloadActionOptions,
) -> rdf_file_finder.FileFinderDownloadActionOptions:
  return rdf_file_finder.FileFinderDownloadActionOptions.FromSerializedBytes(
      proto.SerializeToString()
  )


def ToProtoFileFinderAction(
    rdf: rdf_file_finder.FileFinderAction,
) -> flows_pb2.FileFinderAction:
  return rdf.AsPrimitiveProto()


def ToRDFFileFinderAction(
    proto: flows_pb2.FileFinderAction,
) -> rdf_file_finder.FileFinderAction:
  return rdf_file_finder.FileFinderAction.FromSerializedBytes(
      proto.SerializeToString()
  )


def ToProtoFileFinderArgs(
    rdf: rdf_file_finder.FileFinderArgs,
) -> flows_pb2.FileFinderArgs:
  return rdf.AsPrimitiveProto()


def ToRDFFileFinderArgs(
    proto: flows_pb2.FileFinderArgs,
) -> rdf_file_finder.FileFinderArgs:
  return rdf_file_finder.FileFinderArgs.FromSerializedBytes(
      proto.SerializeToString()
  )


def ToProtoFileFinderResult(
    rdf: rdf_file_finder.FileFinderResult,
) -> flows_pb2.FileFinderResult:
  return rdf.AsPrimitiveProto()


def ToRDFFileFinderResult(
    proto: flows_pb2.FileFinderResult,
) -> rdf_file_finder.FileFinderResult:
  return rdf_file_finder.FileFinderResult.FromSerializedBytes(
      proto.SerializeToString()
  )
