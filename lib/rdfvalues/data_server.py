#!/usr/bin/env python
"""RDFValues for the data server."""


from grr.lib import rdfvalue
from grr.proto import data_server_pb2


class DataStoreCommand(rdfvalue.RDFProtoStruct):
  protobuf = data_server_pb2.DataStoreCommand


class DataServerState(rdfvalue.RDFProtoStruct):
  protobuf = data_server_pb2.DataServerState


class DataServerInterval(rdfvalue.RDFProtoStruct):
  protobuf = data_server_pb2.DataServerInterval


class DataServerInformation(rdfvalue.RDFProtoStruct):
  protobuf = data_server_pb2.DataServerInformation


class DataServerMapping(rdfvalue.RDFProtoStruct):
  protobuf = data_server_pb2.DataServerMapping


class DataServerClientInformation(rdfvalue.RDFProtoStruct):
  protobuf = data_server_pb2.DataServerClientInformation


class DataServerClientCredentials(rdfvalue.RDFProtoStruct):
  protobuf = data_server_pb2.DataServerClientCredentials


class DataServerFileCopy(rdfvalue.RDFProtoStruct):
  protobuf = data_server_pb2.DataServerFileCopy


class DataServerRebalance(rdfvalue.RDFProtoStruct):
  protobuf = data_server_pb2.DataServerRebalance

