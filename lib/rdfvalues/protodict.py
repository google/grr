#!/usr/bin/env python
# Copyright 2012 Google Inc.
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

"""A generic serializer for python dictionaries."""


from google.protobuf import message
from google.protobuf import text_format

from grr.lib import rdfvalue
from grr.lib import utils
from grr.proto import jobs_pb2


class DataBlob(rdfvalue.RDFProto):
  """Wrapper class for DataBlob protobuf."""
  _proto = jobs_pb2.DataBlob

  def SetValue(self, value):
    """Receives a value and fills it into a DataBlob."""
    type_mappings = [(unicode, "string"), (str, "data"), (bool, "boolean"),
                     (int, "integer"), (long, "integer"), (dict, "dict")]

    if value is None:
      self._data.none = "None"

    elif isinstance(value, rdfvalue.RDFValue):
      self._data.rdf_value.data = value.SerializeToString()
      self._data.rdf_value.age = int(value.age)
      self._data.rdf_value.name = value.__class__.__name__

    elif isinstance(value, message.Message):
      # If we have a protobuf save the type and serialized data.
      self._data.data = value.SerializeToString()
      self._data.proto_name = value.__class__.__name__

    elif isinstance(value, (list, tuple)):
      self._data.list.content.extend([DataBlob().SetValue(v) for v in value])

    elif isinstance(value, dict):
      pdict = RDFProtoDict()
      pdict.FromDict(value)
      self._data.dict.MergeFrom(pdict.ToProto())

    else:
      for type_mapping, member in type_mappings:
        if isinstance(value, type_mapping):
          setattr(self._data, member, value)
          return self._data

      raise RuntimeError("Unsupported type for ProtoDict: %s" % type(value))

    return self._data

  def GetValue(self):
    """Extracts and returns a single value from a DataBlob."""
    if self._data.HasField("none"):
      return None

    field_names = ["integer", "string", "data", "boolean", "list", "dict",
                   "rdf_value"]
    values = [getattr(self._data, x) for x in field_names
              if self._data.HasField(x)]

    if len(values) != 1:
      raise RuntimeError("DataBlob must contain exactly one entry.")

    # Unpack RDFValues.
    if self._data.rdf_value.name:
      return rdfvalue.RDFValue.classes[self._data.rdf_value.name](
          initializer=self._data.rdf_value.data,
          age=self._data.rdf_value.age)

    elif self._data.HasField("proto_name"):
      try:
        pb = getattr(jobs_pb2, self._data.proto_name)()
        pb.ParseFromString(self._data.data)

        return pb
      except AttributeError:
        raise RuntimeError("Datablob has unknown protobuf.")

    elif self._data.HasField("list"):
      return [DataBlob(x).GetValue() for x in self._data.list.content]

    elif self._data.HasField("dict"):
      return RDFProtoDict(values[0]).ToDict()

    else:
      return values[0]


class RDFProtoDict(rdfvalue.RDFProto):
  """A high level interface for protobuf Dict objects.

  This effectively converts from a dict to a proto and back.
  The dict may contain strings (python unicode objects), int64,
  or binary blobs (python string objects) as keys and values.
  """
  _proto = jobs_pb2.Dict

  def __init__(self, initializer=None, age=None, **kwarg):
    super(RDFProtoDict, self).__init__(initializer=None, age=age)

    # Support initializing from a mapping
    if isinstance(initializer, dict):
      self._data = self._proto()
      for key in initializer:
        new_proto = self._data.dat.add()
        DataBlob(new_proto.k).SetValue(key)
        DataBlob(new_proto.v).SetValue(initializer[key])

    # Initialize from a protobuf by taking a reference.
    elif isinstance(initializer, message.Message):
      self._data = initializer

    # Initialize from a serialized string.
    elif isinstance(initializer, str):
      self._data = self._proto()
      self.ParseFromString(initializer)

    # Can be initialized from kwargs (like a dict).
    elif initializer is None:
      self._data = self._proto()
      self.FromDict(kwarg)

    # Initialize from another RDFProtoDict.
    elif isinstance(initializer, RDFProtoDict):
      self._data = initializer._data  # pylint: disable=protected-access
      self.age = initializer.age

    else:
      raise RuntimeError("Invalid initializer for ProtoDict.")

  def ToDict(self):
    result = {}
    for x in self._data.dat:
      value = DataBlob(x.v).GetValue()
      result[DataBlob(x.k).GetValue()] = value

    return result

  def FromDict(self, dictionary):
    for k, v in dictionary.items():
      self[k] = v

  def ToProto(self):
    return self._data

  def __getitem__(self, key):
    for kv in self._data.dat:
      if DataBlob(kv.k).GetValue() == key:
        return DataBlob(kv.v).GetValue()

    raise KeyError("%s not found" % key)

  def Get(self, key, default=None):
    try:
      return self[key]
    except KeyError:
      return default

  def Items(self):
    for kv in self._data.dat:
      yield DataBlob(kv.k).GetValue(), DataBlob(kv.v).GetValue()

  get = utils.Proxy("Get")
  items = utils.Proxy("Items")

  def __delitem__(self, key):
    proto = jobs_pb2.Dict()
    for kv in self._data.dat:
      if DataBlob(kv.k).GetValue() != key:
        proto.dat.add(k=kv.k, v=kv.v)

    self._data.ClearField("dat")
    self._data.MergeFrom(proto)

  def __setitem__(self, key, value):
    del self[key]
    new_proto = self._data.dat.add()
    DataBlob(new_proto.k).SetValue(key)
    DataBlob(new_proto.v).SetValue(value)

  def __str__(self):
    return utils.SmartStr(self.ToDict())

  def __iter__(self):
    for kv in self._data.dat:
      yield DataBlob(kv.k).GetValue()


class RDFValueArray(rdfvalue.RDFProto):
  """A type which serializes a list of RDFValue instances."""
  _proto = jobs_pb2.BlobArray

  # Set this to an RDFValue class to ensure all members adhere to this type.
  rdf_type = None

  def __init__(self, initializer=None, age=None):
    super(RDFValueArray, self).__init__(age=age)

    self._data = []
    if self.__class__ == initializer.__class__:
      self._data = initializer._data[:]  # pylint: disable=protected-access
      self.age = initializer.age

    # Allow ourselves to be instantiated from a protobuf
    elif isinstance(initializer, self._proto):
      self._data = [DataBlob(x).GetValue() for x in initializer.content]

    # Initialize from a serialized protobuf.
    elif isinstance(initializer, str):
      self.ParseFromString(initializer)

    else:
      try:
        for item in initializer:
          self.Append(item)
      except TypeError:
        if initializer is not None:
          raise ValueError("%s can not be initialized from %s" % (
              self.__class__.__name__, type(initializer)))

  def ParseFromTextDump(self, dump):
    new_object = self._proto()
    text_format.Merge(dump, new_object)
    for item in new_object.content:
      self.Append(DataBlob(item).GetValue())

  def Append(self, value=None, **kwarg):
    """Add another member to the array.

    Args:
      value: The new data to append to the array.

    Returns:
      The value which was added. This can be modified further by the caller and
      changes will be propagated here.

    Raises:
      ValueError: If the value to add is not allowed.
    """
    if self.rdf_type is not None:
      if (isinstance(value, rdfvalue.RDFValue) and
          value.__class__ != self.rdf_type):
        raise ValueError("Can only accept %s" % self.rdf_type)

      try:
        # Try to coerce the value.
        value = self.rdf_type(value, **kwarg)   # pylint: disable=not-callable
      except (TypeError, ValueError):
        raise ValueError("Unable to initialize %s from type %s" % (
            self.__class__.__name__, type(value)))

    self._data.append(value)

    return value

  def Extend(self, values):
    for v in values:
      self.Append(v)

  def __getitem__(self, item):
    return self._data[item]

  def __len__(self):
    return len(self._data)

  def __iter__(self):
    return iter(self._data)

  def ToProto(self):
    result = jobs_pb2.BlobArray()
    for member in self._data:
      DataBlob(result.content.add()).SetValue(member)

    return result

  def SerializeToString(self):
    return self.ToProto().SerializeToString()

  def ParseFromString(self, string):
    data = jobs_pb2.BlobArray()
    data.ParseFromString(string)

    # Parse the protobuf into a list of RDFValues and return that.
    self._data = [DataBlob(x).GetValue() for x in data.content]

    if self.rdf_type:
      # pylint: disable=not-callable
      self._data = [self.rdf_type(x) for x in self._data]
      # pylint: enable=not-callable

  def __nonzero__(self):
    return bool(self._data)

  def Pop(self, index=0):
    self._data.pop(index)

  def __str__(self):
    results = [str(x) for x in self._data]
    return "\n\n".join(results)

  def GetFields(self, field_names):
    """Recurse into an attribute to get sub fields by name."""
    result = []

    for value in self._data:
      for field_name in field_names:
        value = getattr(value, field_name, None)
        if value is None:
          break

      if value is not None:
        result.append(value)

    return result
