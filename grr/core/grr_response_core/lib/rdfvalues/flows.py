#!/usr/bin/env python
"""RDFValue implementations related to flow scheduling."""

from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

import threading
import time

from grr_response_core.lib import rdfvalue
from grr_response_core.lib.rdfvalues import client as rdf_client
from grr_response_core.lib.rdfvalues import client_stats as rdf_client_stats
from grr_response_core.lib.rdfvalues import crypto as rdf_crypto
from grr_response_core.lib.rdfvalues import protodict as rdf_protodict
from grr_response_core.lib.rdfvalues import structs as rdf_structs
from grr_response_core.lib.util import random
from grr_response_proto import flows_pb2
from grr_response_proto import jobs_pb2


class GrrMessage(rdf_structs.RDFProtoStruct):
  """An RDFValue class to manage GRR messages."""
  protobuf = jobs_pb2.GrrMessage
  rdf_deps = [
      rdf_protodict.EmbeddedRDFValue,
      rdfvalue.FlowSessionID,
      rdfvalue.RDFDatetime,
      rdfvalue.RDFURN,
  ]

  lock = threading.Lock()
  next_id_base = 0
  max_ttl = 5

  def __init__(self,
               initializer=None,
               age=None,
               payload=None,
               generate_task_id=False,
               **kwarg):
    super(GrrMessage, self).__init__(initializer=initializer, age=age, **kwarg)

    if payload is not None:
      self.payload = payload

    if generate_task_id:
      self.GenerateTaskID()

  def GenerateTaskID(self):
    """Generates a new, unique task_id."""
    # Random number can not be zero since next_id_base must increment.
    random_number = random.PositiveUInt16()

    # 16 bit random numbers
    with GrrMessage.lock:
      next_id_base = GrrMessage.next_id_base

      id_base = (next_id_base + random_number) & 0xFFFFFFFF
      if id_base < next_id_base:
        time.sleep(0.001)

      GrrMessage.next_id_base = id_base

    # 32 bit timestamp (in 1/1000 second resolution)
    time_base = (int(time.time() * 1000) & 0x1FFFFFFF) << 32

    task_id = time_base | id_base

    self.Set("task_id", task_id)
    return task_id

  @property
  def task_id(self):
    res = self.Get("task_id")
    if res:
      return res
    raise ValueError("No task id set.")

  @task_id.setter
  def task_id(self, value):
    self.Set("task_id", value)

  def HasTaskID(self):
    return bool(self.Get("task_id"))

  @property
  def args(self):
    raise RuntimeError("Direct access to serialized args is not permitted! "
                       "Use payload field.")

  @args.setter
  def args(self, value):
    raise RuntimeError("Direct access to serialized args is not permitted! "
                       "Use payload field.")

  @property
  def payload(self):
    """The payload property automatically decodes the encapsulated data."""
    if self.args_rdf_name:
      # Now try to create the correct RDFValue.
      result_cls = self.classes.get(self.args_rdf_name, rdfvalue.RDFString)

      result = result_cls.FromSerializedString(
          self.Get("args"), age=self.args_age)
      return result

  @payload.setter
  def payload(self, value):
    """Automatically encode RDFValues into the message."""
    if not isinstance(value, rdfvalue.RDFValue):
      raise RuntimeError("Payload must be an RDFValue.")

    self.Set("args", value.SerializeToString())

    # pylint: disable=protected-access
    if value._age is not None:
      self.args_age = value._age
    # pylint: enable=protected-access

    self.args_rdf_name = value.__class__.__name__

  def ClearPayload(self):
    self.args_rdf_name = None
    self.Set("args", None)
    self.args_age = None


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
  ]


class GrrNotification(rdf_structs.RDFProtoStruct):
  """A flow notification."""
  protobuf = jobs_pb2.GrrNotification
  rdf_deps = [
      rdfvalue.RDFDatetime,
      rdfvalue.SessionID,
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
      "Error"
  ]


class FlowNotification(rdf_structs.RDFProtoStruct):
  protobuf = jobs_pb2.FlowNotification
  rdf_deps = [
      rdf_client.ClientURN,
      rdfvalue.SessionID,
  ]


class NotificationList(rdf_protodict.RDFValueArray):
  """A List of notifications for this user."""
  rdf_type = Notification


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
