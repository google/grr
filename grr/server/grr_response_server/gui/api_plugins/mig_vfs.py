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

