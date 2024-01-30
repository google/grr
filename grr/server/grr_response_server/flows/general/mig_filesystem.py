#!/usr/bin/env python
"""Provides conversion functions to be used during RDFProtoStruct migration."""
from grr_response_proto import flows_pb2
from grr_response_server.flows.general import filesystem


def ToProtoListDirectoryArgs(
    rdf: filesystem.ListDirectoryArgs,
) -> flows_pb2.ListDirectoryArgs:
  return rdf.AsPrimitiveProto()


def ToRDFListDirectoryArgs(
    proto: flows_pb2.ListDirectoryArgs,
) -> filesystem.ListDirectoryArgs:
  return filesystem.ListDirectoryArgs.FromSerializedBytes(
      proto.SerializeToString()
  )


def ToProtoRecursiveListDirectoryArgs(
    rdf: filesystem.RecursiveListDirectoryArgs,
) -> flows_pb2.RecursiveListDirectoryArgs:
  return rdf.AsPrimitiveProto()


def ToRDFRecursiveListDirectoryArgs(
    proto: flows_pb2.RecursiveListDirectoryArgs,
) -> filesystem.RecursiveListDirectoryArgs:
  return filesystem.RecursiveListDirectoryArgs.FromSerializedBytes(
      proto.SerializeToString()
  )


def ToProtoGlobArgs(rdf: filesystem.GlobArgs) -> flows_pb2.GlobArgs:
  return rdf.AsPrimitiveProto()


def ToRDFGlobArgs(proto: flows_pb2.GlobArgs) -> filesystem.GlobArgs:
  return filesystem.GlobArgs.FromSerializedBytes(proto.SerializeToString())


def ToProtoDiskVolumeInfoArgs(
    rdf: filesystem.DiskVolumeInfoArgs,
) -> flows_pb2.DiskVolumeInfoArgs:
  return rdf.AsPrimitiveProto()


def ToRDFDiskVolumeInfoArgs(
    proto: flows_pb2.DiskVolumeInfoArgs,
) -> filesystem.DiskVolumeInfoArgs:
  return filesystem.DiskVolumeInfoArgs.FromSerializedBytes(
      proto.SerializeToString()
  )
