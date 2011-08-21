#!/usr/bin/env python

# Copyright 2010 Google Inc.
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

"""This file contains various utility classes used by GRR."""


import struct

from google.protobuf import message
from grr.proto import jobs_pb2


def Proxy(f):
  """A helper to create a proxy method in a class."""

  def Wrapped(self, *args):
    return getattr(self, f)(*args)
  return Wrapped


class FastStore(object):
  """This is a cache which expires objects in oldest first manner.

  This implementation first appeared in PyFlag.
  """

  def __init__(self, max_size=0, kill_cb=None):
    """Constructor.

    Args:
       max_size: The maximum number of objects held in cache.
       kill_cb: An optional function which will be called on each
                object terminated from cache.
    """
    self._age = []
    self._hash = {}
    self._limit = max_size
    self._kill_cb = kill_cb

  def Expire(self):
    """Expires old cache entries."""
    while len(self._age) > self._limit:
      x = self._age.pop(0)

      try:
      ## Kill the object if needed
        if self._kill_cb is not None:
          self._kill_cb(self._hash[x])

        del self._hash[x]
      except (KeyError, TypeError):
        pass

  def Put(self, key, obj):
    """Add the object to the cache."""
    try:
      idx = self._age.index(key)
      self._age.pop(idx)
    except ValueError:
      pass

    self._hash[key] = obj
    self._age.append(key)

    self.Expire()

    return key

  def ExpireObject(self, key):
    """Expire a specific object from cache."""
    obj = self._hash.pop(key)

    if self._kill_cb:
      self._kill_cb(obj)

  def Get(self, key):
    """Fetch the object from cache.

    Objects may be flushed from cache at any time. Callers must always
    handle the possibility of KeyError raised here.

    Args:
      key: The key used to access the object.

    Returns:
      Cached object.

    Raises:
      KeyError: If the object is not present in the cache.
    """
    # Remove the item and put to the end of the age list
    try:
      idx = self._age.index(key)
      self._age.pop(idx)
      self._age.append(key)
    except ValueError:
      raise KeyError()

    return self._hash[key]

  def __contains__(self, obj):
    return obj in self._hash

  def __getitem__(self, key):
    return self.Get(key)

  def Flush(self):
    """Flush all items from cache."""

    if self._kill_cb:
      for x in self._hash.values():
        self._kill_cb(x)

    self._hash = {}
    self._age = []


# TODO(user): Eventually slot in Volatility parsing system in here
class Struct(object):
  """A baseclass for parsing binary Structs."""

  # Derived classes must initialize this into an array of (format,
  # name) tuples.
  _fields = None

  def __init__(self, data):
    """Parses ourselves from data."""
    format_str = "".join([x[0] for x in self._fields])
    self.size = struct.calcsize(format_str)

    try:
      parsed_data = struct.unpack(format_str, data[:self.size])

    except struct.error:
      raise RuntimeError("Unable to parse")

    for i in range(len(self._fields)):
      setattr(self, self._fields[i][1], parsed_data[i])

  def __repr__(self):
    """Produce useful text representation of the Struct."""
    dat = []
    for _, name in self._fields:
      dat.append("%s=%s" % (name, getattr(self, name)))
    return "%s(%s)" % (self.__class__.__name__, ", ".join(dat))

  @classmethod
  def GetSize(cls):
    """Calculate the size of the struct."""
    format_str = "".join([x[0] for x in cls._fields])
    return struct.calcsize(format_str)


class ProtoDict(object):
  """A high level interface for protobuf Dict objects.

  This effectively converts from a dict to a proto and back.
  The dict may contain strings (python unicode objects), int64,
  or binary blobs (python string objects) as keys and values.
  """

  def SetBlobValue(self, value):
    """Receives a value and fills it into a DataBlob."""
    type_mappings = {unicode: "string", str: "data", int: "integer",
                     long: "integer", bool: "boolean"}
    blob = jobs_pb2.DataBlob()
    if value is None:
      blob.none = "None"
    elif type(value) in type_mappings:
      setattr(blob, type_mappings[type(value)], value)
    elif isinstance(value, message.Message):
      # If we have a protobuf save the type and serialized data.
      blob.data = value.SerializeToString()
      blob.proto_name = value.__class__.__name__
    else:
      raise RuntimeError("Unsupported type for ProtoDict: %s" % type(value))
    return blob

  def GetBlobValue(self, blob):
    """Extracts and returns a single value from a DataBlob."""
    if blob.HasField("none"):
      return None
    field_names = ["integer", "string", "data", "boolean"]
    values = [getattr(blob, x) for x in field_names if blob.HasField(x)]
    if len(values) != 1:
      raise RuntimeError("DataBlob must contain exactly one entry.")
    if blob.HasField("proto_name"):
      try:
        pb = getattr(jobs_pb2, blob.proto_name)()
        pb.ParseFromString(blob.data)
        return pb
      except AttributeError:
        raise RuntimeError("Datablob has unknown protobuf.")
    else:
      return values[0]

  def __init__(self, initializer=None):
    # Support initializing from a mapping
    self._proto = jobs_pb2.Dict()
    if initializer is not None:
      try:
        for key in initializer:
          self._proto.dat.add(k=self.SetBlobValue(key),
                              v=self.SetBlobValue(initializer[key]))
      except (TypeError, AttributeError):
        # String initializer
        if type(initializer) == str:
          self._proto.ParseFromString(initializer)
        else:
          # Support initializing from a protobuf
          self._proto = initializer

  def ToDict(self):
    return dict([(self.GetBlobValue(x.k), self.GetBlobValue(x.v))
                 for x in self._proto.dat])

  def FromDict(self, dictionary):
    for k, v in dictionary.items():
      self[k] = v

  def ToProto(self):
    return self._proto

  def __getitem__(self, key):
    for kv in self._proto.dat:
      if self.GetBlobValue(kv.k) == key:
        return self.GetBlobValue(kv.v)

    raise KeyError("%s Not found" % key)

  def Get(self, key, default=None):
    try:
      return self[key]
    except KeyError:
      return default

  get = Proxy("Get")

  def __delitem__(self, key):
    proto = jobs_pb2.Dict()
    for kv in self._proto.dat:
      if self.GetBlobValue(kv.k) != key:
        proto.dat.add(k=kv.k, v=kv.v)

    self._proto.CopyFrom(proto)

  def __setitem__(self, key, value):
    del self[key]
    self._proto.dat.add(k=self.SetBlobValue(key), v=self.SetBlobValue(value))

  def __str__(self):
    return self._proto.SerializeToString()

  def __iter__(self):
    for kv in self._proto.dat:
      yield self.GetBlobValue(kv.k)


def GroupBy(items, key):
  """A generator that groups all items by a key.

  Args:
    items:  A list of items.
    key: A function which given each item will return the key.

  Returns:
    Generator of tuples of (unique keys, list of items) where all items have the
    same key.  session id.
  """
  key_map = {}
  for item in items:
    key_id = key(item)
    key_map.setdefault(key_id, []).append(item)

  return key_map.iteritems()


def SmartStr(string):
  """Returns a string or encodes a unicode object.

  This function essentially will always return an encoded string. It should be
  used on an interface to the system which must accept a string and not unicode.

  Args:
    string: The string to convert.

  Returns:
    an encoded string.
  """
  if type(string) == unicode:
    return string.encode("utf8")

  return str(string)


def SmartUnicode(string):
  """Returns a unicode object.

  This function will always return a unicode object. It should be used to
  guarantee that something is always a unicode object.

  Args:
    string: The string to convert.

  Returns:
    a unicode object.
  """
  if type(string) != unicode:
    return str(string).decode("utf8")

  return string


def NormalizePath(path, sep="/"):
  """A sane implementation of os.path.normpath.

  The standard implementation treats leading / and // as different leading to
  incorrect normal forms.

  NOTE: Its ok to use a relative path here (without leading /) but any /../ will
  still be removed anchoring the path at the top level (e.g. foo/../../../../bar
  => bar).

  Args:
     path: The path to normalize.
     sep: Separator used.

  Returns:
     A normalized path. In this context normalized means that all input paths
     that would result in the system opening the same physical file will produce
     the same normalized path.
  """

  path = SmartUnicode(path)

  path_list = path.split(sep)

  # This is a relative path and the first element is . or ..
  if path_list[0] in [".", "..", ""]:
    path_list.pop(0)

  # Deliberately begin at index 1 to preserve a single leading /
  i = 0

  while True:
    list_len = len(path_list)

    # We begin at the last known good position so we never iterate over path
    # elements which are already examined
    for i in range(i, len(path_list)):
      # Remove /./ form
      if path_list[i] == "." or not path_list[i]:
        path_list.pop(i)
        break

      # Remove /../ form
      elif path_list[i] == "..":
        path_list.pop(i)
        # Anchor at the top level
        if (i == 1 and path_list[0]) or i > 1:
          i -= 1
          path_list.pop(i)
        break

    # If we didnt alter the path so far we can quit
    if len(path_list) == list_len:
      return sep + sep.join(path_list)


def JoinPath(*parts):
  """A sane version of os.path.join.

  The intention here is to append the stem to the path. The standard module
  removes the path if the stem begins with a /.

  Args:
     parts: parts of the path to join. The first arg is always the root and
        directory traversal is not allowed.

  Returns:
     a normalized path.
  """
  # Ensure all path components are unicode
  parts = [SmartUnicode(path) for path in parts]

  return NormalizePath(u"/".join(parts))


def Join(*parts):
  """Join (AFF4) paths without normalizing.

  A quick join method that can be used to express the precondition that
  the parts are already normalized.

  Args:
    parts: The parts to join

  Returns:
    The joined path.
  """

  return "/".join(parts)

AFF4_PREFIXES = {jobs_pb2.Path.OS: "/fs/os",
                 jobs_pb2.Path.TSK: "/fs/raw",
                 jobs_pb2.Path.REGISTRY: "/registry"}


def Aff4ToPathspec(aff4path):
  """Convert a AFF4 path string to a pathspec."""
  for pt, prefix in AFF4_PREFIXES.items():
    if aff4path.lower().startswith(prefix):
      return jobs_pb2.Path(pathtype=pt,
                           path=aff4path[len(prefix):])
  raise RuntimeError("Unknown prefix for Aff4 to pathspec conversion.")


def PathspecToAff4(pathspec):
  """Convert a pathspec to a AFF4 path string."""

  # Delete prefix for windows devices
  dev = pathspec.device.replace("\\\\.\\", "")
  dev = dev.replace("\\", "/")
  dev = dev.strip("/")

  path = pathspec.path.replace("\\", "/").lstrip("/")

  prefix = AFF4_PREFIXES[pathspec.pathtype]

  return Join(prefix, dev, path).replace("//", "/")
