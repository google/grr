#!/usr/bin/env python
# Copyright 2011 Google Inc.
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""RDFValue implementations related to flow scheduling."""


from grr.lib import rdfvalue
from grr.proto import jobs_pb2


class GRRMessage(rdfvalue.RDFProto):
  """An RDFValue class to manage GRR messages."""
  _proto = jobs_pb2.GrrMessage

  rdf_map = dict(args_age=rdfvalue.RDFDatetime)

  def __init__(self, initializer=None, payload=None, **kwarg):
    super(GRRMessage, self).__init__(initializer=initializer, **kwarg)
    if payload:
      self.payload = payload

  @property
  def payload(self):
    """The payload property automatically decodes the encapsulated data."""
    if self.args_rdf_name:
      # Now try to create the correct RDFValue.
      result_cls = self.classes.get(self.args_rdf_name, rdfvalue.RDFString)

      result = result_cls(age=self.args_age)
      result.ParseFromString(self.args)

      return result

  @payload.setter
  def payload(self, value):
    """Automatically encode RDFValues into the message."""
    if not isinstance(value, rdfvalue.RDFValue):
      raise RuntimeError("Published event must be an RDFValue.")

    self.args = value.SerializeToString()
    self.args_age = int(value.age)
    self.args_rdf_name = value.__class__.__name__


class GrrStatus(rdfvalue.RDFProto):
  """The client status message.

  When the client responds to a request, it sends a series of response messages,
  followed by a single status message. The GrrStatus message contains error and
  traceback information for any failures on the client.
  """
  _proto = jobs_pb2.GrrStatus

  rdf_map = dict(cpu_used=rdfvalue.CpuSeconds)


class Backtrace(rdfvalue.RDFString):
  """A special type representing a backtrace."""


class RequestState(rdfvalue.RDFProto):
  _proto = jobs_pb2.RequestState

  rdf_map = dict(request=rdfvalue.GRRMessage,
                 status=rdfvalue.GrrStatus,
                 data=rdfvalue.RDFProtoDict)


class Flow(rdfvalue.RDFProto):
  """A Flow protobuf.

  The flow protobuf holds metadata about the flow, as well as the pickled flow
  itself.
  """
  _proto = jobs_pb2.FlowPB

  def ParseFromString(self, string):
    """The real flow protobuf is wrapped in a Task proto."""
    task = jobs_pb2.Task()
    task.ParseFromString(string)

    self._data = self._proto()
    self._data.ParseFromString(task.value)
    self._data.ts_id = task.id

    return self._data

  def SerializeToString(self):
    task = jobs_pb2.Task(value=super(Flow, self).SerializeToString())
    task.id = self._data.ts_id
    return task.SerializeToString()

  rdf_map = dict(create_time=rdfvalue.RDFDatetime,
                 request_state=RequestState,
                 backtrace=Backtrace,
                 args=rdfvalue.RDFProtoDict)


class TaskSchedulerTask(rdfvalue.RDFProto):
  """An RDFValue for Task scheduler tasks."""
  _proto = jobs_pb2.Task


class Notification(rdfvalue.RDFProto):
  """A notification is used in the GUI to alert users.

  Usually the notification means that some operation is completed, and provides
  a link to view the results.
  """
  _proto = jobs_pb2.Notification

  rdf_map = dict(timestamp=rdfvalue.RDFDatetime,
                 subject=rdfvalue.RDFURN)

  notification_types = ["Discovery",  # Link to the client object
                        "ViewObject",       # Link to any URN
                        "FlowStatus",       # Link to a flow
                        "GrantAccess"]      # Link to an access grant page


class FlowNotification(rdfvalue.RDFProto):
  _proto = jobs_pb2.FlowNotification


class NotificationList(rdfvalue.RDFValueArray):
  """A List of notifications for this user."""
  rdf_type = Notification


class SignedMessageList(rdfvalue.RDFProto):
  _proto = jobs_pb2.SignedMessageList


class MessageList(rdfvalue.RDFProto):
  _proto = jobs_pb2.MessageList

  rdf_map = dict(job=GRRMessage)


class HuntError(rdfvalue.RDFProto):
  """An RDFValue class representing a hunt error."""
  _proto = jobs_pb2.HuntError


class HuntLog(rdfvalue.RDFProto):
  """An RDFValue class representing the hunt log entries."""
  _proto = jobs_pb2.HuntLog


class HttpRequest(rdfvalue.RDFProto):
  _proto = jobs_pb2.HttpRequest


class ClientCommunication(rdfvalue.RDFProto):
  _proto = jobs_pb2.ClientCommunication

  rdf_map = dict(orig_request=HttpRequest)
