#!/usr/bin/env python
"""RDFValue implementations related to flow scheduling."""

from grr_response_core.lib import rdfvalue
from grr_response_core.lib.rdfvalues import client as rdf_client
from grr_response_core.lib.rdfvalues import client_stats as rdf_client_stats
from grr_response_core.lib.rdfvalues import crypto as rdf_crypto
from grr_response_core.lib.rdfvalues import structs as rdf_structs
from grr_response_proto import flows_pb2
from grr_response_proto import jobs_pb2


class GrrMessage(rdf_structs.RDFProtoStruct):
  """An RDFValue class to manage GRR messages."""

  protobuf = jobs_pb2.GrrMessage
  rdf_deps = [
      rdfvalue.FlowSessionID,
      rdfvalue.RDFDatetime,
      rdfvalue.Duration,
      rdfvalue.RDFURN,
  ]

  def __init__(self, initializer=None, payload=None, **kwarg):
    super().__init__(initializer=initializer, **kwarg)

    if payload is not None:
      self.payload = payload

  @property
  def args(self):
    raise RuntimeError(
        "Direct access to serialized args is not permitted! Use payload field."
    )

  @args.setter
  def args(self, value):
    raise RuntimeError(
        "Direct access to serialized args is not permitted! Use payload field."
    )

  @property
  def payload(self):
    """The payload property automatically decodes the encapsulated data."""
    if self.args_rdf_name:
      # Now try to create the correct RDFValue.
      result_cls = self.classes.get(self.args_rdf_name, rdfvalue.RDFString)

      return result_cls.FromSerializedBytes(self.Get("args"))


  @payload.setter
  def payload(self, value):
    """Automatically encode RDFValues into the message."""
    if not isinstance(value, rdfvalue.RDFValue):
      raise RuntimeError("Payload must be an RDFValue.")

    self.Set("args", value.SerializeToBytes())
    self.args_rdf_name = value.__class__.__name__

  #   /grr/server/grr_response_server/models/clients.py)

  def ClearPayload(self):
    self.args_rdf_name = None
    self.Set("args", None)


class GrrStatus(rdf_structs.RDFProtoStruct):
  """The client status message.

  When the client responds to a request, it sends a series of response messages,
  followed by a single status message. The GrrStatus message contains error and
  traceback information for any failures on the client.
  """

  protobuf = jobs_pb2.GrrStatus
  rdf_deps = [
      rdf_client_stats.CpuSeconds,
      rdfvalue.SessionID,
      rdfvalue.Duration,
  ]


class FlowProcessingRequest(rdf_structs.RDFProtoStruct):
  protobuf = flows_pb2.FlowProcessingRequest
  rdf_deps = [
      rdfvalue.RDFDatetime,
  ]


class Notification(rdf_structs.RDFProtoStruct):
  """A notification is used in the GUI to alert users.

  Usually the notification means that some operation is completed, and provides
  a link to view the results.
  """

  protobuf = jobs_pb2.Notification
  rdf_deps = [
      rdfvalue.RDFDatetime,
      rdfvalue.RDFURN,
  ]

  notification_types = [
      "Discovery",  # Link to the client object
      "ViewObject",  # Link to any URN
      "FlowStatus",  # Link to a flow
      "GrantAccess",  # Link to an access grant page
      "ArchiveGenerationFinished",
      "Error",
  ]


class FlowNotification(rdf_structs.RDFProtoStruct):
  protobuf = jobs_pb2.FlowNotification
  rdf_deps = [
      rdf_client.ClientURN,
      rdfvalue.SessionID,
  ]


class PackedMessageList(rdf_structs.RDFProtoStruct):
  protobuf = jobs_pb2.PackedMessageList
  rdf_deps = [
      rdfvalue.RDFDatetime,
      rdfvalue.RDFURN,
  ]


class MessageList(rdf_structs.RDFProtoStruct):
  protobuf = jobs_pb2.MessageList
  rdf_deps = [
      GrrMessage,
  ]

  def __len__(self):
    return len(self.job)


class CipherProperties(rdf_structs.RDFProtoStruct):
  """Contains information about a cipher and keys."""

  protobuf = jobs_pb2.CipherProperties
  rdf_deps = [
      rdf_crypto.EncryptionKey,
  ]

  @classmethod
  def GetInializedKeys(cls):
    result = cls()
    result.name = "AES128CBC"
    result.key = rdf_crypto.EncryptionKey().GenerateKey()
    result.metadata_iv = rdf_crypto.EncryptionKey().GenerateKey()
    result.hmac_key = rdf_crypto.EncryptionKey().GenerateKey()
    result.hmac_type = "FULL_HMAC"

    return result

  def GetHMAC(self):
    return rdf_crypto.HMAC(self.hmac_key.RawBytes())

  def GetCipher(self):
    if self.name == "AES128CBC":
      return rdf_crypto.AES128CBCCipher(self.key, self.metadata_iv)


class CipherMetadata(rdf_structs.RDFProtoStruct):
  protobuf = jobs_pb2.CipherMetadata
  rdf_deps = [
      rdfvalue.RDFURN,
  ]


class FlowLog(rdf_structs.RDFProtoStruct):
  """An RDFValue class representing flow log entries."""

  protobuf = jobs_pb2.FlowLog
  rdf_deps = [
      rdf_client.ClientURN,
      rdfvalue.RDFURN,
  ]


class HttpRequest(rdf_structs.RDFProtoStruct):
  protobuf = jobs_pb2.HttpRequest
  rdf_deps = [
      rdfvalue.RDFDatetime,
  ]


class ClientCommunication(rdf_structs.RDFProtoStruct):
  protobuf = jobs_pb2.ClientCommunication
  rdf_deps = [
      rdf_crypto.EncryptionKey,
      HttpRequest,
  ]

  num_messages = 0


class EmptyFlowArgs(rdf_structs.RDFProtoStruct):
  """Some flows do not take arguments."""

  protobuf = flows_pb2.EmptyFlowArgs
