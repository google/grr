#!/usr/bin/env python
"""RDFValues for the data server."""


from grr.lib.rdfvalues import structs as rdf_structs
from grr.proto import data_server_pb2


class DataStoreCommand(rdf_structs.RDFProtoStruct):
  protobuf = data_server_pb2.DataStoreCommand


class DataServerState(rdf_structs.RDFProtoStruct):
  protobuf = data_server_pb2.DataServerState


class DataServerInterval(rdf_structs.RDFProtoStruct):
  protobuf = data_server_pb2.DataServerInterval


class DataServerInformation(rdf_structs.RDFProtoStruct):
  protobuf = data_server_pb2.DataServerInformation


class DataServerMapping(rdf_structs.RDFProtoStruct):
  protobuf = data_server_pb2.DataServerMapping


class DataServerClientInformation(rdf_structs.RDFProtoStruct):
  protobuf = data_server_pb2.DataServerClientInformation


class DataServerClientCredentials(rdf_structs.RDFProtoStruct):
  protobuf = data_server_pb2.DataServerClientCredentials


class DataServerFileCopy(rdf_structs.RDFProtoStruct):
  protobuf = data_server_pb2.DataServerFileCopy


class DataServerRebalance(rdf_structs.RDFProtoStruct):
  protobuf = data_server_pb2.DataServerRebalance


class DataStoreRegistrationRequest(rdf_structs.RDFProtoStruct):
  protobuf = data_server_pb2.DataStoreRegistrationRequest


class DataStoreAuthToken(rdf_structs.RDFProtoStruct):
  protobuf = data_server_pb2.DataStoreAuthToken
