#!/usr/bin/env python
"""RDFValue implementations related to flow scheduling."""


import cPickle
import pickle
import StringIO
import threading
import time

from grr.lib import rdfvalue
from grr.lib import utils
from grr.proto import jobs_pb2


# Maintaining the reference so that DataObject can be unpickled from old
# hunts and flows.
# pylint: disable=invalid-name
DataObject = utils.DataObject


class GrrMessage(rdfvalue.RDFProtoStruct):
  """An RDFValue class to manage GRR messages."""
  protobuf = jobs_pb2.GrrMessage

  lock = threading.Lock()
  next_id_base = 0
  max_ttl = 5
  # We prefix the task id with the encoded priority of the message so it gets
  # read first from data stores that support sorted reads. We reserve 3 bits
  # for this so there can't be more than 8 different levels of priority.
  max_priority = 7

  def __init__(self, initializer=None, age=None, payload=None, **kwarg):
    super(GrrMessage, self).__init__(initializer=initializer, age=age, **kwarg)

    if payload is not None:
      self.payload = payload

      # If the payload has a priority, the GrrMessage inherits it.
      try:
        self.priority = payload.priority
      except AttributeError:
        pass

    if not self.task_id:
      self.task_id = self.GenerateTaskID()

  def GenerateTaskID(self):
    """Generates a new, unique task_id."""
    # Random number can not be zero since next_id_base must increment.
    random_number = utils.PRNG.GetUShort() + 1

    # 16 bit random numbers
    with Task.lock:
      next_id_base = Task.next_id_base

      id_base = (next_id_base + random_number) & 0xFFFFFFFF
      if id_base < next_id_base:
        time.sleep(0.001)

      Task.next_id_base = id_base

    # 32 bit timestamp (in 1/1000 second resolution)
    time_base = (long(time.time() * 1000) & 0x1FFFFFFF) << 32

    priority_prefix = self.max_priority - self.priority
    # Prepend the priority so the messages stay sorted.
    task_id = time_base | id_base
    task_id |= priority_prefix << 61

    return task_id

  @property
  def payload(self):
    """The payload property automatically decodes the encapsulated data."""
    if self.args_rdf_name:
      # Now try to create the correct RDFValue.
      result_cls = self.classes.get(self.args_rdf_name, rdfvalue.RDFString)

      result = result_cls(self.args, age=self.args_age)
      return result

  @payload.setter
  def payload(self, value):
    """Automatically encode RDFValues into the message."""
    if not isinstance(value, rdfvalue.RDFValue):
      raise RuntimeError("Payload must be an RDFValue.")

    self.args = value.SerializeToString()

    # pylint: disable=protected-access
    if value._age is not None:
      self.args_age = value._age
    # pylint: enable=protected-access

    self.args_rdf_name = value.__class__.__name__


class GrrStatus(rdfvalue.RDFProtoStruct):
  """The client status message.

  When the client responds to a request, it sends a series of response messages,
  followed by a single status message. The GrrStatus message contains error and
  traceback information for any failures on the client.
  """
  protobuf = jobs_pb2.GrrStatus

  rdf_map = dict(cpu_used=rdfvalue.CpuSeconds)


class GrrNotification(rdfvalue.RDFProtoStruct):
  """A flow notification."""
  protobuf = jobs_pb2.GrrNotification


class Backtrace(rdfvalue.RDFString):
  """A special type representing a backtrace."""


class RequestState(rdfvalue.RDFProtoStruct):
  protobuf = jobs_pb2.RequestState


class Flow(rdfvalue.RDFProtoStruct):
  """A Flow protobuf.

  The flow protobuf holds metadata about the flow, as well as the pickled flow
  itself.
  """
  protobuf = jobs_pb2.Flow

  # Reference to an AFF4 object where this flow was read from. Note that this
  # is a runtime-only attribute and is not serialized.
  aff4_object = None


class UnknownObject(object):
  """A placeholder for class instances that can not be unpickled."""

  def __str__(self):
    return "Unknown Object"


class RobustUnpickler(pickle.Unpickler):
  """A special unpickler we can use when there are errors in the pickle.

  Due to code changes, sometime existing pickles in the data store can not be
  restored - e.g. if one of the embedded objects is an instance of a class which
  was renamed or moved. This pickler replaces these instances with the
  UnknownObject() instance. This way some of the properies of old pickles can
  still be seen in the UI. It is generally not safe to rely on the data if
  errors are encountered.
  """
  # pylint: disable=invalid-name, broad-except
  dispatch = pickle.Unpickler.dispatch.copy()

  def load_reduce(self):
    try:
      pickle.Unpickler.load_reduce(self)
    except Exception:
      self.stack[-1] = UnknownObject()
  dispatch[pickle.REDUCE] = load_reduce

  def load_global(self):
    try:
      pickle.Unpickler.load_global(self)
    except Exception:
      self.append(UnknownObject)
  dispatch[pickle.GLOBAL] = load_global
  # pylint: enable=invalid-name, broad-except


class FlowState(rdfvalue.RDFValue):
  """The state of a running flow.

  The Flow object can use the state to persist data structures between state
  method execution. The FlowState is serialized by the flow machinery when not
  needed.

  The FlowRunner() also uses the flow's state to persist internal flow state
  related variables - although the flow itself has no access to these. The
  runner context is stored in our context parameter.

  """
  data_store_type = "bytes"
  data = None

  # If there were errors in unpickling this object, we note them in here.
  errors = None

  def __init__(self, initializer=None, age=None):
    self.data = utils.DataObject()
    super(FlowState, self).__init__(initializer=initializer, age=age)

  def ParseFromString(self, string):
    try:
      # Try to unpickle using the fast unpickler. This is the most common case.
      self.data = cPickle.loads(string)
    except Exception as e:  # pylint: disable=broad-except
      # If an error occurs we try to use the more robust version to at least
      # salvage some data. This could happen if an old version of the pickle is
      # stored in the data store.
      self.errors = e
      try:
        self.data = RobustUnpickler(StringIO.StringIO(string)).load()
      except Exception as e:  # pylint: disable=broad-except
        raise rdfvalue.DecodeError(e)

  def SerializeToString(self):
    return cPickle.dumps(self.data)

  def Empty(self):
    return not bool(self.data)

  def __len__(self):
    return len(self.data)

  def get(self, item, default=None):  # pylint: disable=g-bad-name
    return self.data.get(item, default)

  def Register(self, item, value=None):
    setattr(self.data, item, value)

  def __setattr__(self, item, value):
    # Existing class or instance members are assigned to normally.
    if getattr(self.__class__, item, -1) != -1 or item in self.__dict__:
      object.__setattr__(self, item, value)

    elif item in self.data:
      setattr(self.data, item, value)
    else:
      raise AttributeError(
          "Can not assign to state without calling Register() first")

  def __getattr__(self, item):
    return getattr(self.data, item)

  def __str__(self):
    result = []
    for k, v in self.data.items():
      tmp = "  %s = " % k
      for line in utils.SmartUnicode(v).splitlines():
        tmp += "    %s\n" % line

      result.append(tmp)

    return "{\n%s}\n" % "".join(result)

  def __eq__(self, other):
    """Implement equality operator."""
    return (isinstance(other, self.__class__) and
            self.SerializeToString() == other.SerializeToString())

  def __dir__(self):
    return dir(self.data) + dir(self.__class__)


class Notification(rdfvalue.RDFProtoStruct):
  """A notification is used in the GUI to alert users.

  Usually the notification means that some operation is completed, and provides
  a link to view the results.
  """
  protobuf = jobs_pb2.Notification

  notification_types = ["Discovery",        # Link to the client object
                        "ViewObject",       # Link to any URN
                        "FlowStatus",       # Link to a flow
                        "GrantAccess",      # Link to an access grant page
                        "DownloadFile"]     # Directly download a file.


class FlowNotification(rdfvalue.RDFProtoStruct):
  protobuf = jobs_pb2.FlowNotification


class NotificationList(rdfvalue.RDFValueArray):
  """A List of notifications for this user."""
  rdf_type = Notification


class SignedMessageList(rdfvalue.RDFProtoStruct):
  protobuf = jobs_pb2.SignedMessageList


class MessageList(rdfvalue.RDFProtoStruct):
  protobuf = jobs_pb2.MessageList

  def __len__(self):
    return len(self.job)


class CipherProperties(rdfvalue.RDFProtoStruct):
  protobuf = jobs_pb2.CipherProperties


class CipherMetadata(rdfvalue.RDFProtoStruct):
  protobuf = jobs_pb2.CipherMetadata


class HuntError(rdfvalue.RDFProtoStruct):
  """An RDFValue class representing a hunt error."""
  protobuf = jobs_pb2.HuntError


class FlowLog(rdfvalue.RDFProtoStruct):
  """An RDFValue class representing flow log entries."""
  protobuf = jobs_pb2.FlowLog


class HttpRequest(rdfvalue.RDFProtoStruct):
  protobuf = jobs_pb2.HttpRequest


class ClientCommunication(rdfvalue.RDFProtoStruct):
  protobuf = jobs_pb2.ClientCommunication

  num_messages = 0


class ProgressGraph(rdfvalue.RDFString):
  """A class that renders a button to show a progress graph."""


class Task(rdfvalue.RDFProtoStruct):
  """Tasks are scheduled on the task scheduler.

  This class is DEPRECATED! It only exists here so we can render flows stored
  in the old format in the GUI. Do not use this anymore, GrrMessage now contains
  all the fields necessary for scheduling already.
  """

  protobuf = jobs_pb2.Task

  lock = threading.Lock()
  next_id_base = 0
  max_ttl = 5
  payload = None

  def __init__(self, initializer=None, payload=None, *args, **kwargs):
    """Constructor.

    Args:
      initializer: passthrough, can also be used to pass the payload.
      payload: The rdfvalue object to store in this Task.
      *args: passthrough.
      **kwargs: passthrough.
    """
    if payload:
      self.payload = payload
    elif (isinstance(initializer, rdfvalue.RDFValue) and
          not isinstance(initializer, Task)):
      # This is an RDFValue object that we can use.
      self.payload = initializer
      initializer = None

    super(Task, self).__init__(initializer=initializer, *args, **kwargs)

    self.eta = 0

     # self.value now contains a serialized RDFValue protobuf.
    self.payload = rdfvalue.RDFValueObject(self.value).Payload()

    # If the payload has a priority, the task inherits it.
    try:
      self.priority = self.payload.priority
    except AttributeError:
      pass

    if not self.id:
      random_number = utils.PRNG.GetUShort() + 1

      with Task.lock:
        next_id_base = Task.next_id_base

        id_base = (next_id_base + random_number) & 0xFFFFFFFF
        if id_base < next_id_base:
          time.sleep(0.001)

        Task.next_id_base = id_base

      # 32 bit timestamp (in 1/1000 second resolution)
      time_base = (long(time.time() * 1000) & 0xFFFFFFFF) << 32

      self.id = time_base + id_base

  def SerializeToString(self):
    try:
      self.value = self.payload.SerializeToString()
    except AttributeError:
      pass

    return self._data.SerializeToString()

  def ParseFromString(self, string):
    super(Task, self).ParseFromString(string)

     # self.value now contains a serialized RDFValue protobuf.
    self.payload = rdfvalue.RDFValueObject(self.value).Payload()

  def __str__(self):
    result = ""
    for field in ["id", "value", "ttl", "eta", "queue", "priority"]:
      value = getattr(self, field)
      if field == "eta":
        value = time.ctime(self.eta / 1e6)
        lease = (self.eta / 1e6) - time.time()
        if lease < 0:
          value += ", available for leasing"
        else:
          value += ", leased for another %d seconds" % int(lease)

      result += u"%s: %s\n" % (field, utils.SmartUnicode(value))

    return result

  def __repr__(self):
    result = []
    for field in ["id", "ttl", "eta", "queue", "priority"]:
      value = getattr(self, field)
      if field == "eta":
        value = time.ctime(self.eta / 1e6)
        lease = (self.eta / 1e6) - time.time()
        if lease < 0:
          value += ", available for leasing."
        else:
          value += ", leased for another %d seconds." % int(lease)

      result.append(u"%s: %s" % (field, utils.SmartUnicode(value)))

    return u"<Task %s>" % u",". join(result)

  def __bool__(self):
    return bool(self.payload)
