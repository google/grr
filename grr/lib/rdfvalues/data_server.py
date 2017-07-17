#!/usr/bin/env python
"""RDFValues for the data server."""

import hashlib

from grr.lib.rdfvalues import crypto
from grr.lib.rdfvalues import data_store
from grr.lib.rdfvalues import structs as rdf_structs
from grr.proto import data_server_pb2


class DataStoreCommand(rdf_structs.RDFProtoStruct):
  protobuf = data_server_pb2.DataStoreCommand
  rdf_deps = [
      data_store.DataStoreRequest,
  ]


class DataServerState(rdf_structs.RDFProtoStruct):
  protobuf = data_server_pb2.DataServerState


class DataServerInterval(rdf_structs.RDFProtoStruct):
  protobuf = data_server_pb2.DataServerInterval


class DataServerInformation(rdf_structs.RDFProtoStruct):
  protobuf = data_server_pb2.DataServerInformation
  rdf_deps = [
      DataServerInterval,
      DataServerState,
  ]


class DataServerMapping(rdf_structs.RDFProtoStruct):
  protobuf = data_server_pb2.DataServerMapping
  rdf_deps = [
      DataServerInformation,
  ]


class DataServerClientInformation(rdf_structs.RDFProtoStruct):
  protobuf = data_server_pb2.DataServerClientInformation


class DataServerEncryptedCreds(rdf_structs.RDFProtoStruct):
  """Protobuf to transport encrypted messages."""

  protobuf = data_server_pb2.DataServerEncryptedCreds
  rdf_deps = [
      crypto.AES128Key,
  ]

  # TODO(user): Use a proper key derivation function instead of this.
  def _MakeEncryptKey(self, username, password):
    digest = hashlib.md5(username + password).hexdigest()
    return crypto.AES128Key.FromHex(digest)

  def SetPayload(self, payload, username, password):
    key = self._MakeEncryptKey(username, password)
    self.sha256 = hashlib.sha256(payload).digest()

    self.init_vector = crypto.AES128Key.GenerateRandomIV()

    encryptor = crypto.AES128CBCCipher(key, self.init_vector)

    self.ciphertext = encryptor.Encrypt(payload)

  def GetPayload(self, username, password):
    # Use the same key used in SetPayload()
    key = self._MakeEncryptKey(username, password)

    decryptor = crypto.AES128CBCCipher(key, self.init_vector)

    # Decrypt credentials information and set the required fields.
    plain = decryptor.Decrypt(self.ciphertext)

    hasher = hashlib.sha256(plain)
    if hasher.digest() != self.sha256:
      raise crypto.CipherError("Hash does not match")

    return plain


class DataServerClientCredentials(rdf_structs.RDFProtoStruct):
  protobuf = data_server_pb2.DataServerClientCredentials
  rdf_deps = [
      DataServerClientInformation,
  ]


class DataServerFileCopy(rdf_structs.RDFProtoStruct):
  protobuf = data_server_pb2.DataServerFileCopy


class DataServerRebalance(rdf_structs.RDFProtoStruct):
  protobuf = data_server_pb2.DataServerRebalance
  rdf_deps = [
      DataServerMapping,
  ]


class DataStoreAuthToken(rdf_structs.RDFProtoStruct):
  protobuf = data_server_pb2.DataStoreAuthToken


class DataStoreRegistrationRequest(rdf_structs.RDFProtoStruct):
  protobuf = data_server_pb2.DataStoreRegistrationRequest
  rdf_deps = [
      DataStoreAuthToken,
  ]
