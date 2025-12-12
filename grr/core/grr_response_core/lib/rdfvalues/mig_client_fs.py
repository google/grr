#!/usr/bin/env python
"""Provides conversion functions to be used during RDFProtoStruct migration."""

from grr_response_core.lib.rdfvalues import client_fs as rdf_client_fs
from grr_response_proto import flows_pb2
from grr_response_proto import jobs_pb2
from grr_response_proto import sysinfo_pb2


def ToProtoFilesystem(rdf: rdf_client_fs.Filesystem) -> sysinfo_pb2.Filesystem:
  return rdf.AsPrimitiveProto()


def ToRDFFilesystem(proto: sysinfo_pb2.Filesystem) -> rdf_client_fs.Filesystem:
  return rdf_client_fs.Filesystem.FromSerializedBytes(proto.SerializeToString())


def ToProtoWindowsVolume(
    rdf: rdf_client_fs.WindowsVolume,
) -> sysinfo_pb2.WindowsVolume:
  return rdf.AsPrimitiveProto()


def ToRDFWindowsVolume(
    proto: sysinfo_pb2.WindowsVolume,
) -> rdf_client_fs.WindowsVolume:
  return rdf_client_fs.WindowsVolume.FromSerializedBytes(
      proto.SerializeToString()
  )


def ToProtoUnixVolume(rdf: rdf_client_fs.UnixVolume) -> sysinfo_pb2.UnixVolume:
  return rdf.AsPrimitiveProto()


def ToRDFUnixVolume(proto: sysinfo_pb2.UnixVolume) -> rdf_client_fs.UnixVolume:
  return rdf_client_fs.UnixVolume.FromSerializedBytes(proto.SerializeToString())


def ToProtoVolume(rdf: rdf_client_fs.Volume) -> sysinfo_pb2.Volume:
  return rdf.AsPrimitiveProto()


def ToRDFVolume(proto: sysinfo_pb2.Volume) -> rdf_client_fs.Volume:
  return rdf_client_fs.Volume.FromSerializedBytes(proto.SerializeToString())


def ToProtoDiskUsage(rdf: rdf_client_fs.DiskUsage) -> sysinfo_pb2.DiskUsage:
  return rdf.AsPrimitiveProto()


def ToRDFDiskUsage(proto: sysinfo_pb2.DiskUsage) -> rdf_client_fs.DiskUsage:
  return rdf_client_fs.DiskUsage.FromSerializedBytes(proto.SerializeToString())


def ToProtoExtAttr(rdf: rdf_client_fs.ExtAttr) -> jobs_pb2.StatEntry.ExtAttr:
  return rdf.AsPrimitiveProto()


def ToRDFExtAttr(proto: jobs_pb2.StatEntry.ExtAttr) -> rdf_client_fs.ExtAttr:
  return rdf_client_fs.ExtAttr.FromSerializedBytes(proto.SerializeToString())


def ToProtoStatEntry(rdf: rdf_client_fs.StatEntry) -> jobs_pb2.StatEntry:
  return rdf.AsPrimitiveProto()


def ToRDFStatEntry(proto: jobs_pb2.StatEntry) -> rdf_client_fs.StatEntry:
  return rdf_client_fs.StatEntry.FromSerializedBytes(proto.SerializeToString())


def ToProtoFindSpec(rdf: rdf_client_fs.FindSpec) -> jobs_pb2.FindSpec:
  return rdf.AsPrimitiveProto()


def ToRDFFindSpec(proto: jobs_pb2.FindSpec) -> rdf_client_fs.FindSpec:
  return rdf_client_fs.FindSpec.FromSerializedBytes(proto.SerializeToString())


def ToProtoBareGrepSpec(
    rdf: rdf_client_fs.BareGrepSpec,
) -> flows_pb2.BareGrepSpec:
  return rdf.AsPrimitiveProto()


def ToRDFBareGrepSpec(
    proto: flows_pb2.BareGrepSpec,
) -> rdf_client_fs.BareGrepSpec:
  return rdf_client_fs.BareGrepSpec.FromSerializedBytes(
      proto.SerializeToString()
  )


def ToProtoGrepSpec(rdf: rdf_client_fs.GrepSpec) -> jobs_pb2.GrepSpec:
  return rdf.AsPrimitiveProto()


def ToRDFGrepSpec(proto: jobs_pb2.GrepSpec) -> rdf_client_fs.GrepSpec:
  return rdf_client_fs.GrepSpec.FromSerializedBytes(proto.SerializeToString())


def ToProtoBlobImageChunkDescriptor(
    rdf: rdf_client_fs.BlobImageChunkDescriptor,
) -> jobs_pb2.BlobImageChunkDescriptor:
  return rdf.AsPrimitiveProto()


def ToRDFBlobImageChunkDescriptor(
    proto: jobs_pb2.BlobImageChunkDescriptor,
) -> rdf_client_fs.BlobImageChunkDescriptor:
  return rdf_client_fs.BlobImageChunkDescriptor.FromSerializedBytes(
      proto.SerializeToString()
  )


def ToProtoBlobImageDescriptor(
    rdf: rdf_client_fs.BlobImageDescriptor,
) -> jobs_pb2.BlobImageDescriptor:
  return rdf.AsPrimitiveProto()


def ToRDFBlobImageDescriptor(
    proto: jobs_pb2.BlobImageDescriptor,
) -> rdf_client_fs.BlobImageDescriptor:
  return rdf_client_fs.BlobImageDescriptor.FromSerializedBytes(
      proto.SerializeToString()
  )
