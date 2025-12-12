#!/usr/bin/env python
"""Provides conversion functions to be used during RDFProtoStruct migration."""

from typing import Any

from grr_response_core.lib.rdfvalues import protodict as rdf_protodict
from grr_response_proto import jobs_pb2


def ToProtoEmbeddedRDFValue(
    rdf: rdf_protodict.EmbeddedRDFValue,
) -> jobs_pb2.EmbeddedRDFValue:
  return rdf.AsPrimitiveProto()


def ToRDFEmbeddedRDFValue(
    proto: jobs_pb2.EmbeddedRDFValue,
) -> rdf_protodict.EmbeddedRDFValue:
  return rdf_protodict.EmbeddedRDFValue.FromSerializedBytes(
      proto.SerializeToString()
  )


def ToProtoDataBlob(rdf: rdf_protodict.DataBlob) -> jobs_pb2.DataBlob:
  return rdf.AsPrimitiveProto()


def ToRDFDataBlob(proto: jobs_pb2.DataBlob) -> rdf_protodict.DataBlob:
  return rdf_protodict.DataBlob.FromSerializedBytes(proto.SerializeToString())


def ToProtoKeyValue(rdf: rdf_protodict.KeyValue) -> jobs_pb2.KeyValue:
  return rdf.AsPrimitiveProto()


def ToRDFKeyValue(proto: jobs_pb2.KeyValue) -> rdf_protodict.KeyValue:
  return rdf_protodict.KeyValue.FromSerializedBytes(proto.SerializeToString())


def ToProtoDict(rdf: rdf_protodict.Dict) -> jobs_pb2.Dict:
  return rdf.AsPrimitiveProto()


def ToRDFDict(proto: jobs_pb2.Dict) -> rdf_protodict.Dict:
  return rdf_protodict.Dict.FromSerializedBytes(proto.SerializeToString())


def FromProtoDictToNativeDict(proto: jobs_pb2.Dict) -> dict[Any, Any]:
  rdf_dict = ToRDFDict(proto)
  return rdf_dict.ToDict()


def FromNativeDictToProtoDict(dictionary: dict[Any, Any]) -> jobs_pb2.Dict:
  rdf_dict = rdf_protodict.Dict().FromDict(dictionary)
  return ToProtoDict(rdf_dict)


def ToProtoAttributedDict(
    rdf: rdf_protodict.AttributedDict,
) -> jobs_pb2.AttributedDict:
  return rdf.AsPrimitiveProto()


def ToRDFAttributedDict(
    proto: jobs_pb2.AttributedDict,
) -> rdf_protodict.AttributedDict:
  return rdf_protodict.AttributedDict.FromSerializedBytes(
      proto.SerializeToString()
  )


def FromProtoAttributedDictToNativeDict(
    proto: jobs_pb2.AttributedDict,
) -> dict[Any, Any]:
  rdf_dict = ToRDFAttributedDict(proto)
  return rdf_dict.ToDict()


def FromNativeDictToProtoAttributedDict(
    dictionary: dict[Any, Any],
) -> jobs_pb2.AttributedDict:
  rdf_dict = rdf_protodict.AttributedDict().FromDict(dictionary)
  return ToProtoAttributedDict(rdf_dict)


def ToProtoBlobArrayFromBlobArray(
    rdf: rdf_protodict.BlobArray,
) -> jobs_pb2.BlobArray:
  return rdf.AsPrimitiveProto()


def ToRDFBlobArray(proto: jobs_pb2.BlobArray) -> rdf_protodict.BlobArray:
  return rdf_protodict.BlobArray.FromSerializedBytes(proto.SerializeToString())
