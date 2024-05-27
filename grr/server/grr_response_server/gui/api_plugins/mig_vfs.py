#!/usr/bin/env python
"""Provides conversion functions to be used during RDFProtoStruct migration."""

from grr_response_proto.api import vfs_pb2
from grr_response_server.gui.api_plugins import vfs


def ToProtoApiAff4ObjectAttributeValue(
    rdf: vfs.ApiAff4ObjectAttributeValue,
) -> vfs_pb2.ApiAff4ObjectAttributeValue:
  return rdf.AsPrimitiveProto()


def ToRDFApiAff4ObjectAttributeValue(
    proto: vfs_pb2.ApiAff4ObjectAttributeValue,
) -> vfs.ApiAff4ObjectAttributeValue:
  return vfs.ApiAff4ObjectAttributeValue.FromSerializedBytes(
      proto.SerializeToString()
  )


def ToProtoApiAff4ObjectAttribute(
    rdf: vfs.ApiAff4ObjectAttribute,
) -> vfs_pb2.ApiAff4ObjectAttribute:
  return rdf.AsPrimitiveProto()


def ToRDFApiAff4ObjectAttribute(
    proto: vfs_pb2.ApiAff4ObjectAttribute,
) -> vfs.ApiAff4ObjectAttribute:
  return vfs.ApiAff4ObjectAttribute.FromSerializedBytes(
      proto.SerializeToString()
  )


def ToProtoApiAff4ObjectType(
    rdf: vfs.ApiAff4ObjectType,
) -> vfs_pb2.ApiAff4ObjectType:
  return rdf.AsPrimitiveProto()


def ToRDFApiAff4ObjectType(
    proto: vfs_pb2.ApiAff4ObjectType,
) -> vfs.ApiAff4ObjectType:
  return vfs.ApiAff4ObjectType.FromSerializedBytes(proto.SerializeToString())


def ToProtoApiAff4ObjectRepresentation(
    rdf: vfs.ApiAff4ObjectRepresentation,
) -> vfs_pb2.ApiAff4ObjectRepresentation:
  return rdf.AsPrimitiveProto()


def ToRDFApiAff4ObjectRepresentation(
    proto: vfs_pb2.ApiAff4ObjectRepresentation,
) -> vfs.ApiAff4ObjectRepresentation:
  return vfs.ApiAff4ObjectRepresentation.FromSerializedBytes(
      proto.SerializeToString()
  )


def ToProtoApiFile(rdf: vfs.ApiFile) -> vfs_pb2.ApiFile:
  return rdf.AsPrimitiveProto()


def ToRDFApiFile(proto: vfs_pb2.ApiFile) -> vfs.ApiFile:
  return vfs.ApiFile.FromSerializedBytes(proto.SerializeToString())


def ToProtoApiGetFileDetailsArgs(
    rdf: vfs.ApiGetFileDetailsArgs,
) -> vfs_pb2.ApiGetFileDetailsArgs:
  return rdf.AsPrimitiveProto()


def ToRDFApiGetFileDetailsArgs(
    proto: vfs_pb2.ApiGetFileDetailsArgs,
) -> vfs.ApiGetFileDetailsArgs:
  return vfs.ApiGetFileDetailsArgs.FromSerializedBytes(
      proto.SerializeToString()
  )


def ToProtoApiGetFileDetailsResult(
    rdf: vfs.ApiGetFileDetailsResult,
) -> vfs_pb2.ApiGetFileDetailsResult:
  return rdf.AsPrimitiveProto()


def ToRDFApiGetFileDetailsResult(
    proto: vfs_pb2.ApiGetFileDetailsResult,
) -> vfs.ApiGetFileDetailsResult:
  return vfs.ApiGetFileDetailsResult.FromSerializedBytes(
      proto.SerializeToString()
  )


def ToProtoApiListFilesArgs(
    rdf: vfs.ApiListFilesArgs,
) -> vfs_pb2.ApiListFilesArgs:
  return rdf.AsPrimitiveProto()


def ToRDFApiListFilesArgs(
    proto: vfs_pb2.ApiListFilesArgs,
) -> vfs.ApiListFilesArgs:
  return vfs.ApiListFilesArgs.FromSerializedBytes(proto.SerializeToString())


def ToProtoApiListFilesResult(
    rdf: vfs.ApiListFilesResult,
) -> vfs_pb2.ApiListFilesResult:
  return rdf.AsPrimitiveProto()


def ToRDFApiListFilesResult(
    proto: vfs_pb2.ApiListFilesResult,
) -> vfs.ApiListFilesResult:
  return vfs.ApiListFilesResult.FromSerializedBytes(proto.SerializeToString())


def ToProtoApiBrowseFilesystemArgs(
    rdf: vfs.ApiBrowseFilesystemArgs,
) -> vfs_pb2.ApiBrowseFilesystemArgs:
  return rdf.AsPrimitiveProto()


def ToRDFApiBrowseFilesystemArgs(
    proto: vfs_pb2.ApiBrowseFilesystemArgs,
) -> vfs.ApiBrowseFilesystemArgs:
  return vfs.ApiBrowseFilesystemArgs.FromSerializedBytes(
      proto.SerializeToString()
  )


def ToProtoApiBrowseFilesystemEntry(
    rdf: vfs.ApiBrowseFilesystemEntry,
) -> vfs_pb2.ApiBrowseFilesystemEntry:
  return rdf.AsPrimitiveProto()


def ToRDFApiBrowseFilesystemEntry(
    proto: vfs_pb2.ApiBrowseFilesystemEntry,
) -> vfs.ApiBrowseFilesystemEntry:
  return vfs.ApiBrowseFilesystemEntry.FromSerializedBytes(
      proto.SerializeToString()
  )


def ToProtoApiBrowseFilesystemResult(
    rdf: vfs.ApiBrowseFilesystemResult,
) -> vfs_pb2.ApiBrowseFilesystemResult:
  return rdf.AsPrimitiveProto()


def ToRDFApiBrowseFilesystemResult(
    proto: vfs_pb2.ApiBrowseFilesystemResult,
) -> vfs.ApiBrowseFilesystemResult:
  return vfs.ApiBrowseFilesystemResult.FromSerializedBytes(
      proto.SerializeToString()
  )


def ToProtoApiGetFileTextArgs(
    rdf: vfs.ApiGetFileTextArgs,
) -> vfs_pb2.ApiGetFileTextArgs:
  return rdf.AsPrimitiveProto()


def ToRDFApiGetFileTextArgs(
    proto: vfs_pb2.ApiGetFileTextArgs,
) -> vfs.ApiGetFileTextArgs:
  return vfs.ApiGetFileTextArgs.FromSerializedBytes(proto.SerializeToString())


def ToProtoApiGetFileTextResult(
    rdf: vfs.ApiGetFileTextResult,
) -> vfs_pb2.ApiGetFileTextResult:
  return rdf.AsPrimitiveProto()


def ToRDFApiGetFileTextResult(
    proto: vfs_pb2.ApiGetFileTextResult,
) -> vfs.ApiGetFileTextResult:
  return vfs.ApiGetFileTextResult.FromSerializedBytes(proto.SerializeToString())


def ToProtoApiGetFileBlobArgs(
    rdf: vfs.ApiGetFileBlobArgs,
) -> vfs_pb2.ApiGetFileBlobArgs:
  return rdf.AsPrimitiveProto()


def ToRDFApiGetFileBlobArgs(
    proto: vfs_pb2.ApiGetFileBlobArgs,
) -> vfs.ApiGetFileBlobArgs:
  return vfs.ApiGetFileBlobArgs.FromSerializedBytes(proto.SerializeToString())


def ToProtoApiGetFileVersionTimesArgs(
    rdf: vfs.ApiGetFileVersionTimesArgs,
) -> vfs_pb2.ApiGetFileVersionTimesArgs:
  return rdf.AsPrimitiveProto()


def ToRDFApiGetFileVersionTimesArgs(
    proto: vfs_pb2.ApiGetFileVersionTimesArgs,
) -> vfs.ApiGetFileVersionTimesArgs:
  return vfs.ApiGetFileVersionTimesArgs.FromSerializedBytes(
      proto.SerializeToString()
  )


def ToProtoApiGetFileVersionTimesResult(
    rdf: vfs.ApiGetFileVersionTimesResult,
) -> vfs_pb2.ApiGetFileVersionTimesResult:
  return rdf.AsPrimitiveProto()


def ToRDFApiGetFileVersionTimesResult(
    proto: vfs_pb2.ApiGetFileVersionTimesResult,
) -> vfs.ApiGetFileVersionTimesResult:
  return vfs.ApiGetFileVersionTimesResult.FromSerializedBytes(
      proto.SerializeToString()
  )


def ToProtoApiGetFileDownloadCommandArgs(
    rdf: vfs.ApiGetFileDownloadCommandArgs,
) -> vfs_pb2.ApiGetFileDownloadCommandArgs:
  return rdf.AsPrimitiveProto()


def ToRDFApiGetFileDownloadCommandArgs(
    proto: vfs_pb2.ApiGetFileDownloadCommandArgs,
) -> vfs.ApiGetFileDownloadCommandArgs:
  return vfs.ApiGetFileDownloadCommandArgs.FromSerializedBytes(
      proto.SerializeToString()
  )


def ToProtoApiGetFileDownloadCommandResult(
    rdf: vfs.ApiGetFileDownloadCommandResult,
) -> vfs_pb2.ApiGetFileDownloadCommandResult:
  return rdf.AsPrimitiveProto()


def ToRDFApiGetFileDownloadCommandResult(
    proto: vfs_pb2.ApiGetFileDownloadCommandResult,
) -> vfs.ApiGetFileDownloadCommandResult:
  return vfs.ApiGetFileDownloadCommandResult.FromSerializedBytes(
      proto.SerializeToString()
  )


def ToProtoApiListKnownEncodingsResult(
    rdf: vfs.ApiListKnownEncodingsResult,
) -> vfs_pb2.ApiListKnownEncodingsResult:
  return rdf.AsPrimitiveProto()


def ToRDFApiListKnownEncodingsResult(
    proto: vfs_pb2.ApiListKnownEncodingsResult,
) -> vfs.ApiListKnownEncodingsResult:
  return vfs.ApiListKnownEncodingsResult.FromSerializedBytes(
      proto.SerializeToString()
  )


def ToProtoApiCreateVfsRefreshOperationArgs(
    rdf: vfs.ApiCreateVfsRefreshOperationArgs,
) -> vfs_pb2.ApiCreateVfsRefreshOperationArgs:
  return rdf.AsPrimitiveProto()


def ToRDFApiCreateVfsRefreshOperationArgs(
    proto: vfs_pb2.ApiCreateVfsRefreshOperationArgs,
) -> vfs.ApiCreateVfsRefreshOperationArgs:
  return vfs.ApiCreateVfsRefreshOperationArgs.FromSerializedBytes(
      proto.SerializeToString()
  )


def ToProtoApiCreateVfsRefreshOperationResult(
    rdf: vfs.ApiCreateVfsRefreshOperationResult,
) -> vfs_pb2.ApiCreateVfsRefreshOperationResult:
  return rdf.AsPrimitiveProto()


def ToRDFApiCreateVfsRefreshOperationResult(
    proto: vfs_pb2.ApiCreateVfsRefreshOperationResult,
) -> vfs.ApiCreateVfsRefreshOperationResult:
  return vfs.ApiCreateVfsRefreshOperationResult.FromSerializedBytes(
      proto.SerializeToString()
  )


def ToProtoApiGetVfsRefreshOperationStateArgs(
    rdf: vfs.ApiGetVfsRefreshOperationStateArgs,
) -> vfs_pb2.ApiGetVfsRefreshOperationStateArgs:
  return rdf.AsPrimitiveProto()


def ToRDFApiGetVfsRefreshOperationStateArgs(
    proto: vfs_pb2.ApiGetVfsRefreshOperationStateArgs,
) -> vfs.ApiGetVfsRefreshOperationStateArgs:
  return vfs.ApiGetVfsRefreshOperationStateArgs.FromSerializedBytes(
      proto.SerializeToString()
  )


def ToProtoApiGetVfsRefreshOperationStateResult(
    rdf: vfs.ApiGetVfsRefreshOperationStateResult,
) -> vfs_pb2.ApiGetVfsRefreshOperationStateResult:
  return rdf.AsPrimitiveProto()


def ToRDFApiGetVfsRefreshOperationStateResult(
    proto: vfs_pb2.ApiGetVfsRefreshOperationStateResult,
) -> vfs.ApiGetVfsRefreshOperationStateResult:
  return vfs.ApiGetVfsRefreshOperationStateResult.FromSerializedBytes(
      proto.SerializeToString()
  )


def ToProtoApiVfsTimelineItem(
    rdf: vfs.ApiVfsTimelineItem,
) -> vfs_pb2.ApiVfsTimelineItem:
  return rdf.AsPrimitiveProto()


def ToRDFApiVfsTimelineItem(
    proto: vfs_pb2.ApiVfsTimelineItem,
) -> vfs.ApiVfsTimelineItem:
  return vfs.ApiVfsTimelineItem.FromSerializedBytes(proto.SerializeToString())


def ToProtoApiGetVfsTimelineArgs(
    rdf: vfs.ApiGetVfsTimelineArgs,
) -> vfs_pb2.ApiGetVfsTimelineArgs:
  return rdf.AsPrimitiveProto()


def ToRDFApiGetVfsTimelineArgs(
    proto: vfs_pb2.ApiGetVfsTimelineArgs,
) -> vfs.ApiGetVfsTimelineArgs:
  return vfs.ApiGetVfsTimelineArgs.FromSerializedBytes(
      proto.SerializeToString()
  )


def ToProtoApiGetVfsTimelineResult(
    rdf: vfs.ApiGetVfsTimelineResult,
) -> vfs_pb2.ApiGetVfsTimelineResult:
  return rdf.AsPrimitiveProto()


def ToRDFApiGetVfsTimelineResult(
    proto: vfs_pb2.ApiGetVfsTimelineResult,
) -> vfs.ApiGetVfsTimelineResult:
  return vfs.ApiGetVfsTimelineResult.FromSerializedBytes(
      proto.SerializeToString()
  )


def ToProtoApiGetVfsTimelineAsCsvArgs(
    rdf: vfs.ApiGetVfsTimelineAsCsvArgs,
) -> vfs_pb2.ApiGetVfsTimelineAsCsvArgs:
  return rdf.AsPrimitiveProto()


def ToRDFApiGetVfsTimelineAsCsvArgs(
    proto: vfs_pb2.ApiGetVfsTimelineAsCsvArgs,
) -> vfs.ApiGetVfsTimelineAsCsvArgs:
  return vfs.ApiGetVfsTimelineAsCsvArgs.FromSerializedBytes(
      proto.SerializeToString()
  )


def ToProtoApiUpdateVfsFileContentArgs(
    rdf: vfs.ApiUpdateVfsFileContentArgs,
) -> vfs_pb2.ApiUpdateVfsFileContentArgs:
  return rdf.AsPrimitiveProto()


def ToRDFApiUpdateVfsFileContentArgs(
    proto: vfs_pb2.ApiUpdateVfsFileContentArgs,
) -> vfs.ApiUpdateVfsFileContentArgs:
  return vfs.ApiUpdateVfsFileContentArgs.FromSerializedBytes(
      proto.SerializeToString()
  )


def ToProtoApiUpdateVfsFileContentResult(
    rdf: vfs.ApiUpdateVfsFileContentResult,
) -> vfs_pb2.ApiUpdateVfsFileContentResult:
  return rdf.AsPrimitiveProto()


def ToRDFApiUpdateVfsFileContentResult(
    proto: vfs_pb2.ApiUpdateVfsFileContentResult,
) -> vfs.ApiUpdateVfsFileContentResult:
  return vfs.ApiUpdateVfsFileContentResult.FromSerializedBytes(
      proto.SerializeToString()
  )


def ToProtoApiGetVfsFileContentUpdateStateArgs(
    rdf: vfs.ApiGetVfsFileContentUpdateStateArgs,
) -> vfs_pb2.ApiGetVfsFileContentUpdateStateArgs:
  return rdf.AsPrimitiveProto()


def ToRDFApiGetVfsFileContentUpdateStateArgs(
    proto: vfs_pb2.ApiGetVfsFileContentUpdateStateArgs,
) -> vfs.ApiGetVfsFileContentUpdateStateArgs:
  return vfs.ApiGetVfsFileContentUpdateStateArgs.FromSerializedBytes(
      proto.SerializeToString()
  )


def ToProtoApiGetVfsFileContentUpdateStateResult(
    rdf: vfs.ApiGetVfsFileContentUpdateStateResult,
) -> vfs_pb2.ApiGetVfsFileContentUpdateStateResult:
  return rdf.AsPrimitiveProto()


def ToRDFApiGetVfsFileContentUpdateStateResult(
    proto: vfs_pb2.ApiGetVfsFileContentUpdateStateResult,
) -> vfs.ApiGetVfsFileContentUpdateStateResult:
  return vfs.ApiGetVfsFileContentUpdateStateResult.FromSerializedBytes(
      proto.SerializeToString()
  )


def ToProtoApiGetVfsFilesArchiveArgs(
    rdf: vfs.ApiGetVfsFilesArchiveArgs,
) -> vfs_pb2.ApiGetVfsFilesArchiveArgs:
  return rdf.AsPrimitiveProto()


def ToRDFApiGetVfsFilesArchiveArgs(
    proto: vfs_pb2.ApiGetVfsFilesArchiveArgs,
) -> vfs.ApiGetVfsFilesArchiveArgs:
  return vfs.ApiGetVfsFilesArchiveArgs.FromSerializedBytes(
      proto.SerializeToString()
  )
