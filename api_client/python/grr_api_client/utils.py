#!/usr/bin/env python
"""Utility functions and classes for GRR API client library."""
from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

import time


from builtins import map  # pylint: disable=redefined-builtin

from google.protobuf import wrappers_pb2

from google.protobuf import symbol_database

from grr_api_client import errors

from grr_response_proto import checks_pb2
from grr_response_proto import deprecated_pb2
from grr_response_proto import flows_pb2
from grr_response_proto import jobs_pb2
from grr_response_proto import rekall_pb2

from grr_response_proto.api import artifact_pb2
from grr_response_proto.api import client_pb2
from grr_response_proto.api import config_pb2
from grr_response_proto.api import cron_pb2
from grr_response_proto.api import flow_pb2
from grr_response_proto.api import hunt_pb2
from grr_response_proto.api import output_plugin_pb2
from grr_response_proto.api import reflection_pb2
from grr_response_proto.api import stats_pb2
from grr_response_proto.api import user_pb2
from grr_response_proto.api import vfs_pb2


class ProtobufTypeNotFound(errors.Error):
  pass


class ItemsIterator(object):
  """Iterator object with a total_count property."""

  def __init__(self, items=None, total_count=None):
    super(ItemsIterator, self).__init__()

    self.items = items
    self.total_count = total_count

  def __iter__(self):
    for i in self.items:
      yield i

  def next(self):
    return self.items.next()


def MapItemsIterator(function, items):
  """Maps ItemsIterator via given function."""
  return ItemsIterator(
      items=map(function, items), total_count=items.total_count)


class BinaryChunkIterator(object):
  """Iterator object for binary streams."""

  def __init__(self, chunks=None, total_size=None, on_close=None):
    super(BinaryChunkIterator, self).__init__()

    self.chunks = chunks
    self.total_size = total_size
    self.on_close = on_close

  def Close(self):
    if self.on_close:
      self.on_close()
      self.on_close = None

  def __exit__(self, unused_type, unused_value, unused_traceback):
    self.Close()

  def __iter__(self):
    for c in self.chunks:
      yield c
    self.Close()

  def next(self):
    try:
      return self.chunks.next()
    except StopIteration:
      self.Close()
      raise

  def WriteToStream(self, out):
    for c in self.chunks:
      out.write(c)
    self.Close()

  def WriteToFile(self, file_name):
    with open(file_name, "wb") as fd:
      self.WriteToStream(fd)


# Default poll interval in seconds.
DEFAULT_POLL_INTERVAL = 15

# Default poll timeout in seconds.
DEFAULT_POLL_TIMEOUT = 3600


def Poll(generator=None, condition=None, interval=None, timeout=None):
  """Periodically calls generator function until a condition is satisfied."""

  if not generator:
    raise ValueError("generator has to be a lambda")

  if not condition:
    raise ValueError("condition has to be a lambda")

  if interval is None:
    interval = DEFAULT_POLL_INTERVAL

  if timeout is None:
    timeout = DEFAULT_POLL_TIMEOUT

  started = time.time()
  while True:
    obj = generator()
    check_result = condition(obj)
    if check_result:
      return obj

    if timeout and (time.time() - started) > timeout:
      raise errors.PollTimeoutError(
          "Polling on %s timed out after %ds." % (obj, timeout))
    time.sleep(interval)


AFF4_PREFIX = "aff4:/"


def UrnStringToClientId(urn):
  """Converts given URN string to a client id string."""
  if urn.startswith(AFF4_PREFIX):
    urn = urn[len(AFF4_PREFIX):]

  components = urn.split("/")
  return components[0]


def UrnStringToHuntId(urn):
  """Converts given URN string to a flow id string."""
  if urn.startswith(AFF4_PREFIX):
    urn = urn[len(AFF4_PREFIX):]

  components = urn.split("/")
  if len(components) != 2 or components[0] != "hunts":
    raise ValueError("Invalid hunt URN: %s" % urn)

  return components[-1]


TYPE_URL_PREFIX = "type.googleapis.com/"


def GetTypeUrl(proto):
  """Returns type URL for a given proto."""

  return TYPE_URL_PREFIX + proto.DESCRIPTOR.full_name


def TypeUrlToMessage(type_url):
  """Returns a message instance corresponding to a given type URL."""

  if not type_url.startswith(TYPE_URL_PREFIX):
    raise ValueError("Type URL has to start with a prefix %s: %s" %
                     (TYPE_URL_PREFIX, type_url))

  full_name = type_url[len(TYPE_URL_PREFIX):]
  try:
    return symbol_database.Default().GetSymbol(full_name)()
  except KeyError as e:
    raise ProtobufTypeNotFound(e.message)


def CopyProto(proto):
  new_proto = proto.__class__()
  new_proto.ParseFromString(proto.SerializeToString())
  return new_proto


class UnknownProtobuf(object):

  def __init__(self, proto_type, proto_any):
    super(UnknownProtobuf, self).__init__()

    self.type = proto_type
    self.original_value = proto_any


def UnpackAny(proto_any):
  try:
    proto = TypeUrlToMessage(proto_any.type_url)
  except ProtobufTypeNotFound as e:
    return UnknownProtobuf(e.message, proto_any)

  proto_any.Unpack(proto)
  return proto


def RegisterProtoDescriptors(db, *additional_descriptors):
  """Registers all API-releated descriptors in a given symbol DB."""
  db.RegisterFileDescriptor(artifact_pb2.DESCRIPTOR)
  db.RegisterFileDescriptor(client_pb2.DESCRIPTOR)
  db.RegisterFileDescriptor(config_pb2.DESCRIPTOR)
  db.RegisterFileDescriptor(cron_pb2.DESCRIPTOR)
  db.RegisterFileDescriptor(flow_pb2.DESCRIPTOR)
  db.RegisterFileDescriptor(hunt_pb2.DESCRIPTOR)
  db.RegisterFileDescriptor(output_plugin_pb2.DESCRIPTOR)
  db.RegisterFileDescriptor(reflection_pb2.DESCRIPTOR)
  db.RegisterFileDescriptor(stats_pb2.DESCRIPTOR)
  db.RegisterFileDescriptor(user_pb2.DESCRIPTOR)
  db.RegisterFileDescriptor(vfs_pb2.DESCRIPTOR)

  db.RegisterFileDescriptor(checks_pb2.DESCRIPTOR)
  db.RegisterFileDescriptor(deprecated_pb2.DESCRIPTOR)
  db.RegisterFileDescriptor(flows_pb2.DESCRIPTOR)
  db.RegisterFileDescriptor(jobs_pb2.DESCRIPTOR)
  db.RegisterFileDescriptor(wrappers_pb2.DESCRIPTOR)
  db.RegisterFileDescriptor(rekall_pb2.DESCRIPTOR)

  for d in additional_descriptors:
    db.RegisterFileDescriptor(d)
