#!/usr/bin/env python
"""RDFValues for the data server."""

import hashlib

from grr.lib.rdfvalues import crypto
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


class DataServerEncryptedCreds(rdf_structs.RDFProtoStruct):
  """Protobuf to transport encrypted messages."""

  protobuf = data_server_pb2.DataServerEncryptedCreds

  def _MakeEncryptKey(self, username, password):
    data = hashlib.md5(username + password).hexdigest()
    return crypto.AES128Key(data)

  def _MakeInitVector(self):
    init_vector = crypto.AES128Key()
    init_vector.Generate()
    return init_vector

  def SetPayload(self, payload, username, password):
    key = self._MakeEncryptKey(username, password)
    hasher = hashlib.sha256(payload)
    self.sha256 = hasher.digest()

    self.init_vector = self._MakeInitVector()
    encryptor = crypto.AES128CBCCipher(key, self.init_vector,
                                       crypto.Cipher.OP_ENCRYPT)

    self.ciphertext = encryptor.Encrypt(payload)

  def GetPayload(self, username, password):
    # Use the same key used in SetPayload()
    key = self._MakeEncryptKey(username, password)

    decryptor = crypto.AES128CBCCipher(key, self.init_vector,
                                       crypto.Cipher.OP_DECRYPT)

    # Decrypt credentials information and set the required fields.
    plain = decryptor.Update(self.ciphertext)
    plain += decryptor.Final()

    hasher = hashlib.sha256(plain)
    if hasher.digest() != self.sha256:
      raise crypto.CipherError("Hash does not match")

    return plain


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
