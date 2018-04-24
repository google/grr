#!/usr/bin/env python
"""RDFValues for the remote data_store."""
import json

from grr.lib import rdfvalue
from grr.lib import utils
from grr.lib.rdfvalues import protodict
from grr.lib.rdfvalues import structs
from grr_response_proto import data_store_pb2
from grr.server.grr_response_server import access_control


class TimestampSpec(structs.RDFProtoStruct):
  protobuf = data_store_pb2.TimestampSpec
  rdf_deps = [
      rdfvalue.RDFDatetime,
  ]


class DataStoreValue(structs.RDFProtoStruct):
  protobuf = data_store_pb2.DataStoreValue
  rdf_deps = [
      protodict.DataBlob,
      TimestampSpec,
  ]


class ResultSet(structs.RDFProtoStruct):
  """DataStore result set."""

  protobuf = data_store_pb2.ResultSet
  rdf_deps = [
      DataStoreValue,
      rdfvalue.RDFURN,
  ]

  @property
  def payload(self):
    return json.loads(self.serialized_result)

  @payload.setter
  def payload(self, value):
    # ensure_ascii is set to False to avoid problems with malformed unicode
    # strings. json library successfully encodes them, but then fails to
    # parse. If we do the utf-8 encoding with SmartStr *after* the JSON
    # encoding is done, everything gets parsed successfully.
    # Example:
    # utils.SmartStr(json.dumps(u'\udc7c', ensure_ascii=False) produces:
    #   '"\xed\xb1\xbc"'
    # and json.loads('"\xed\xb1\xbc"') produces: u'\udc7c'
    #
    # But json.dumps(u'\udc7c') produces:
    #   '"\\udc7c"'
    # and json.loads('"\\udc7c"') raises "Unpaired low surrogate" error.
    self.serialized_result = utils.SmartStr(
        json.dumps(value, ensure_ascii=False))


class DataStoreRequest(structs.RDFProtoStruct):
  protobuf = data_store_pb2.DataStoreRequest
  rdf_deps = [
      access_control.ACLToken,
      DataStoreValue,
      rdfvalue.RDFURN,
      TimestampSpec,
  ]


class DataStoreResponse(structs.RDFProtoStruct):
  protobuf = data_store_pb2.DataStoreResponse
  rdf_deps = [
      DataStoreRequest,
      ResultSet,
  ]
