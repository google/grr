#!/usr/bin/env python
"""Provides conversion functions to be used during RDFProtoStruct migration."""

from grr_response_proto import objects_pb2
from grr_response_server.rdfvalues import objects as rdf_objects


def ToProtoClientLabel(rdf: rdf_objects.ClientLabel) -> objects_pb2.ClientLabel:
  return rdf.AsPrimitiveProto()


def ToRDFClientLabel(proto: objects_pb2.ClientLabel) -> rdf_objects.ClientLabel:
  return rdf_objects.ClientLabel.FromSerializedBytes(proto.SerializeToString())


def ToProtoStringMapEntry(
    rdf: rdf_objects.StringMapEntry,
) -> objects_pb2.StringMapEntry:
  return rdf.AsPrimitiveProto()


def ToRDFStringMapEntry(
    proto: objects_pb2.StringMapEntry,
) -> rdf_objects.StringMapEntry:
  return rdf_objects.StringMapEntry.FromSerializedBytes(
      proto.SerializeToString()
  )


def ToProtoClientSnapshotMetadata(
    rdf: rdf_objects.ClientSnapshotMetadata,
) -> objects_pb2.ClientSnapshotMetadata:
  return rdf.AsPrimitiveProto()


def ToRDFClientSnapshotMetadata(
    proto: objects_pb2.ClientSnapshotMetadata,
) -> rdf_objects.ClientSnapshotMetadata:
  return rdf_objects.ClientSnapshotMetadata.FromSerializedBytes(
      proto.SerializeToString()
  )


def ToProtoClientSnapshot(
    rdf: rdf_objects.ClientSnapshot,
) -> objects_pb2.ClientSnapshot:
  return rdf.AsPrimitiveProto()


def ToRDFClientSnapshot(
    proto: objects_pb2.ClientSnapshot,
) -> rdf_objects.ClientSnapshot:
  return rdf_objects.ClientSnapshot.FromSerializedBytes(
      proto.SerializeToString()
  )


def ToProtoClientMetadata(
    rdf: rdf_objects.ClientMetadata,
) -> objects_pb2.ClientMetadata:
  return rdf.AsPrimitiveProto()


def ToRDFClientMetadata(
    proto: objects_pb2.ClientMetadata,
) -> rdf_objects.ClientMetadata:
  return rdf_objects.ClientMetadata.FromSerializedBytes(
      proto.SerializeToString()
  )


def ToProtoClientFullInfo(
    rdf: rdf_objects.ClientFullInfo,
) -> objects_pb2.ClientFullInfo:
  return rdf.AsPrimitiveProto()


def ToRDFClientFullInfo(
    proto: objects_pb2.ClientFullInfo,
) -> rdf_objects.ClientFullInfo:
  return rdf_objects.ClientFullInfo.FromSerializedBytes(
      proto.SerializeToString()
  )


def ToProtoGRRUser(rdf: rdf_objects.GRRUser) -> objects_pb2.GRRUser:
  return rdf.AsPrimitiveProto()


def ToRDFGRRUser(proto: objects_pb2.GRRUser) -> rdf_objects.GRRUser:
  return rdf_objects.GRRUser.FromSerializedBytes(proto.SerializeToString())


def ToProtoApprovalGrant(
    rdf: rdf_objects.ApprovalGrant,
) -> objects_pb2.ApprovalGrant:
  return rdf.AsPrimitiveProto()


def ToRDFApprovalGrant(
    proto: objects_pb2.ApprovalGrant,
) -> rdf_objects.ApprovalGrant:
  return rdf_objects.ApprovalGrant.FromSerializedBytes(
      proto.SerializeToString()
  )


def ToProtoApprovalRequest(
    rdf: rdf_objects.ApprovalRequest,
) -> objects_pb2.ApprovalRequest:
  return rdf.AsPrimitiveProto()


def ToRDFApprovalRequest(
    proto: objects_pb2.ApprovalRequest,
) -> rdf_objects.ApprovalRequest:
  return rdf_objects.ApprovalRequest.FromSerializedBytes(
      proto.SerializeToString()
  )


def ToProtoPathInfo(rdf: rdf_objects.PathInfo) -> objects_pb2.PathInfo:
  return rdf.AsPrimitiveProto()


def ToRDFPathInfo(proto: objects_pb2.PathInfo) -> rdf_objects.PathInfo:
  return rdf_objects.PathInfo.FromSerializedBytes(proto.SerializeToString())


def ToProtoClientReference(
    rdf: rdf_objects.ClientReference,
) -> objects_pb2.ClientReference:
  return rdf.AsPrimitiveProto()


def ToRDFClientReference(
    proto: objects_pb2.ClientReference,
) -> rdf_objects.ClientReference:
  return rdf_objects.ClientReference.FromSerializedBytes(
      proto.SerializeToString()
  )


def ToProtoHuntReference(
    rdf: rdf_objects.HuntReference,
) -> objects_pb2.HuntReference:
  return rdf.AsPrimitiveProto()


def ToRDFHuntReference(
    proto: objects_pb2.HuntReference,
) -> rdf_objects.HuntReference:
  return rdf_objects.HuntReference.FromSerializedBytes(
      proto.SerializeToString()
  )


def ToProtoCronJobReference(
    rdf: rdf_objects.CronJobReference,
) -> objects_pb2.CronJobReference:
  return rdf.AsPrimitiveProto()


def ToRDFCronJobReference(
    proto: objects_pb2.CronJobReference,
) -> rdf_objects.CronJobReference:
  return rdf_objects.CronJobReference.FromSerializedBytes(
      proto.SerializeToString()
  )


def ToProtoFlowReference(
    rdf: rdf_objects.FlowReference,
) -> objects_pb2.FlowReference:
  return rdf.AsPrimitiveProto()


def ToRDFFlowReference(
    proto: objects_pb2.FlowReference,
) -> rdf_objects.FlowReference:
  return rdf_objects.FlowReference.FromSerializedBytes(
      proto.SerializeToString()
  )


def ToProtoVfsFileReference(
    rdf: rdf_objects.VfsFileReference,
) -> objects_pb2.VfsFileReference:
  return rdf.AsPrimitiveProto()


def ToRDFVfsFileReference(
    proto: objects_pb2.VfsFileReference,
) -> rdf_objects.VfsFileReference:
  return rdf_objects.VfsFileReference.FromSerializedBytes(
      proto.SerializeToString()
  )


def ToProtoApprovalRequestReference(
    rdf: rdf_objects.ApprovalRequestReference,
) -> objects_pb2.ApprovalRequestReference:
  return rdf.AsPrimitiveProto()


def ToRDFApprovalRequestReference(
    proto: objects_pb2.ApprovalRequestReference,
) -> rdf_objects.ApprovalRequestReference:
  return rdf_objects.ApprovalRequestReference.FromSerializedBytes(
      proto.SerializeToString()
  )


def ToProtoObjectReference(
    rdf: rdf_objects.ObjectReference,
) -> objects_pb2.ObjectReference:
  return rdf.AsPrimitiveProto()


def ToRDFObjectReference(
    proto: objects_pb2.ObjectReference,
) -> rdf_objects.ObjectReference:
  return rdf_objects.ObjectReference.FromSerializedBytes(
      proto.SerializeToString()
  )


def ToProtoUserNotification(
    rdf: rdf_objects.UserNotification,
) -> objects_pb2.UserNotification:
  return rdf.AsPrimitiveProto()


def ToRDFUserNotification(
    proto: objects_pb2.UserNotification,
) -> rdf_objects.UserNotification:
  return rdf_objects.UserNotification.FromSerializedBytes(
      proto.SerializeToString()
  )


def ToProtoMessageHandlerRequest(
    rdf: rdf_objects.MessageHandlerRequest,
) -> objects_pb2.MessageHandlerRequest:
  return rdf.AsPrimitiveProto()


def ToRDFMessageHandlerRequest(
    proto: objects_pb2.MessageHandlerRequest,
) -> rdf_objects.MessageHandlerRequest:
  return rdf_objects.MessageHandlerRequest.FromSerializedBytes(
      proto.SerializeToString()
  )


def ToProtoClientPathID(
    rdf: rdf_objects.ClientPathID,
) -> objects_pb2.ClientPathID:
  return rdf.AsPrimitiveProto()


def ToRDFClientPathID(
    proto: objects_pb2.ClientPathID,
) -> rdf_objects.ClientPathID:
  return rdf_objects.ClientPathID.FromSerializedBytes(proto.SerializeToString())


def ToProtoBlobReference(
    rdf: rdf_objects.BlobReference,
) -> objects_pb2.BlobReference:
  return rdf.AsPrimitiveProto()


def ToRDFBlobReference(
    proto: objects_pb2.BlobReference,
) -> rdf_objects.BlobReference:
  return rdf_objects.BlobReference.FromSerializedBytes(
      proto.SerializeToString()
  )


def ToProtoBlobReferences(
    rdf: rdf_objects.BlobReferences,
) -> objects_pb2.BlobReferences:
  return rdf.AsPrimitiveProto()


def ToRDFBlobReferences(
    proto: objects_pb2.BlobReferences,
) -> rdf_objects.BlobReferences:
  return rdf_objects.BlobReferences.FromSerializedBytes(
      proto.SerializeToString()
  )


def ToProtoSerializedValueOfUnrecognizedType(
    rdf: rdf_objects.SerializedValueOfUnrecognizedType,
) -> objects_pb2.SerializedValueOfUnrecognizedType:
  return rdf.AsPrimitiveProto()


def ToRDFSerializedValueOfUnrecognizedType(
    proto: objects_pb2.SerializedValueOfUnrecognizedType,
) -> rdf_objects.SerializedValueOfUnrecognizedType:
  return rdf_objects.SerializedValueOfUnrecognizedType.FromSerializedBytes(
      proto.SerializeToString()
  )


def ToProtoAPIAuditEntry(
    rdf: rdf_objects.APIAuditEntry,
) -> objects_pb2.APIAuditEntry:
  return rdf.AsPrimitiveProto()


def ToRDFAPIAuditEntry(
    proto: objects_pb2.APIAuditEntry,
) -> rdf_objects.APIAuditEntry:
  return rdf_objects.APIAuditEntry.FromSerializedBytes(
      proto.SerializeToString()
  )


def ToProtoSignedBinaryID(
    rdf: rdf_objects.SignedBinaryID,
) -> objects_pb2.SignedBinaryID:
  return rdf.AsPrimitiveProto()


def ToRDFSignedBinaryID(
    proto: objects_pb2.SignedBinaryID,
) -> rdf_objects.SignedBinaryID:
  return rdf_objects.SignedBinaryID.FromSerializedBytes(
      proto.SerializeToString()
  )
