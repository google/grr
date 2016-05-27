#!/usr/bin/env python
"""A generic serializer for python dictionaries."""


import collections

from grr.lib import rdfvalue
from grr.lib import utils
from grr.lib.rdfvalues import structs as rdf_structs
from grr.proto import jobs_pb2


class KeyValue(rdf_structs.RDFProtoStruct):
  protobuf = jobs_pb2.KeyValue


class DataBlob(rdf_structs.RDFProtoStruct):
  """Wrapper class for DataBlob protobuf."""
  protobuf = jobs_pb2.DataBlob

  def SetValue(self, value, raise_on_error=True):
    """Receives a value and fills it into a DataBlob.

    Args:
      value: value to set
      raise_on_error: if True, raise if we can't serialize.  If False, set the
        key to an error string.
    Returns:
      self
    Raises:
      TypeError: if the value can't be serialized and raise_on_error is True
    """
    type_mappings = [(unicode, "string"), (str, "data"), (bool, "boolean"),
                     (int, "integer"), (long, "integer"), (dict, "dict"),
                     (float, "float")]

    if value is None:
      self.none = "None"

    elif isinstance(value, rdfvalue.RDFValue):
      self.rdf_value.data = value.SerializeToString()
      self.rdf_value.age = int(value.age)
      self.rdf_value.name = value.__class__.__name__

    elif isinstance(value, (list, tuple)):
      self.list.content.Extend([DataBlob().SetValue(
          v, raise_on_error=raise_on_error) for v in value])

    elif isinstance(value, dict):
      self.dict.FromDict(value, raise_on_error=raise_on_error)

    else:
      for type_mapping, member in type_mappings:
        if isinstance(value, type_mapping):
          setattr(self, member, value)

          return self

      message = "Unsupported type for ProtoDict: %s" % type(value)
      if raise_on_error:
        raise TypeError(message)

      setattr(self, "string", message)

    return self

  def GetValue(self, ignore_error=True):
    """Extracts and returns a single value from a DataBlob."""
    if self.HasField("none"):
      return None

    field_names = ["integer", "string", "data", "boolean", "list", "dict",
                   "rdf_value", "float"]

    values = [getattr(self, x) for x in field_names if self.HasField(x)]

    if len(values) != 1:
      return None

    if self.HasField("boolean"):
      return bool(values[0])

    # Unpack RDFValues.
    if self.HasField("rdf_value"):
      try:
        return rdfvalue.RDFValue.classes[self.rdf_value.name](
            initializer=self.rdf_value.data,
            age=self.rdf_value.age)
      except (ValueError, KeyError) as e:
        if ignore_error:
          return e

        raise

    elif self.HasField("list"):
      return [x.GetValue() for x in self.list.content]

    else:
      return values[0]


class Dict(rdf_structs.RDFProtoStruct):
  """A high level interface for protobuf Dict objects.

  This effectively converts from a dict to a proto and back.
  The dict may contain strings (python unicode objects), int64,
  or binary blobs (python string objects) as keys and values.
  """
  protobuf = jobs_pb2.Dict

  def __init__(self, initializer=None, age=None, **kwarg):
    super(Dict, self).__init__(initializer=None, age=age)

    # Support initializing from a mapping
    if isinstance(initializer, dict):
      self.FromDict(initializer)

    # Initialize from a serialized string.
    elif isinstance(initializer, str):
      self.ParseFromString(initializer)

    # Can be initialized from kwargs (like a dict).
    elif initializer is None:
      self.FromDict(kwarg)

    # Initialize from another Dict.
    elif isinstance(initializer, Dict):
      self.SetRawData(initializer.GetRawData())
      self.age = initializer.age

    else:
      raise rdfvalue.InitializeError("Invalid initializer for ProtoDict.")

  def ToDict(self):
    result = {}
    for x in self.dat:
      result[x.k.GetValue()] = x.v.GetValue()

    return result

  def FromDict(self, dictionary, raise_on_error=True):
    # First clear and then set the dictionary.
    self.dat = None
    for key, value in dictionary.iteritems():
      self.dat.Append(
          k=DataBlob().SetValue(key, raise_on_error=raise_on_error),
          v=DataBlob().SetValue(value, raise_on_error=raise_on_error))
    return self

  def __getitem__(self, key):
    for x in self.dat:
      if x.k.GetValue() == key:
        return x.v.GetValue()

    raise KeyError("%s not found" % key)

  def __contains__(self, key):
    if self.get(key):
      return True
    return False

  def GetItem(self, key, default=None):
    try:
      return self[key]
    except KeyError:
      return default

  def Items(self):
    for x in self.dat:
      yield x.k.GetValue(), x.v.GetValue()

  def Values(self):
    for x in self.dat:
      yield x.v.GetValue()

  def Keys(self):
    for x in self.dat:
      yield x.k.GetValue()

  get = utils.Proxy("GetItem")
  items = utils.Proxy("Items")
  keys = utils.Proxy("Keys")
  values = utils.Proxy("Values")

  def __delitem__(self, key):
    for i, x in enumerate(self.dat):
      if x.k.GetValue() == key:
        self.dat.Pop(i)

  def __len__(self):
    return len(self.dat)

  def SetItem(self, key, value, raise_on_error=True):
    """Alternative to __setitem__ that can ignore errors.

    Sometimes we want to serialize a structure that contains some simple
    objects, and some that can't be serialized.  This method gives the caller a
    way to specify that they don't care about values that can't be
    serialized.

    Args:
      key: dict key
      value: dict value
      raise_on_error: if True, raise if we can't serialize.  If False, set the
        key to an error string.
    """
    del self[key]
    self.dat.Append(
        k=DataBlob().SetValue(key, raise_on_error=raise_on_error),
        v=DataBlob().SetValue(value, raise_on_error=raise_on_error))

  def __setitem__(self, key, value):
    del self[key]
    self.dat.Append(k=DataBlob().SetValue(key), v=DataBlob().SetValue(value))

  def __iter__(self):
    for x in self.dat:
      yield x.k.GetValue()

  def __eq__(self, other):
    if isinstance(other, dict):
      return self.ToDict() == other

    return super(Dict, self).__eq__(other)


class AttributedDict(Dict):
  """A Dict that supports attribute indexing."""

  protobuf = jobs_pb2.AttributedDict

  def __getattr__(self, item):
    return self.GetItem(item)


# Old clients still send back "RDFProtoDicts" so we need to keep this around.
class RDFProtoDict(Dict):
  pass


class BlobArray(rdf_structs.RDFProtoStruct):
  protobuf = jobs_pb2.BlobArray


class RDFValueArray(rdf_structs.RDFProtoStruct):
  """A type which serializes a list of RDFValue instances.

  TODO(user): This needs to be deprecated in favor of just defining a
  protobuf with a repeated field (This can be now done dynamically, which is the
  main reason we used this in the past).
  """
  protobuf = jobs_pb2.BlobArray

  # Set this to an RDFValue class to ensure all members adhere to this type.
  rdf_type = None

  def __init__(self, initializer=None, age=None):
    super(RDFValueArray, self).__init__(age=age)

    if self.__class__ == initializer.__class__:
      self.content = initializer.Copy().content
      self.age = initializer.age

    # Initialize from a serialized protobuf.
    elif isinstance(initializer, str):
      self.ParseFromString(initializer)

    else:
      try:
        for item in initializer:
          self.Append(item)
      except TypeError:
        if initializer is not None:
          raise rdfvalue.InitializeError("%s can not be initialized from %s" %
                                         (self.__class__.__name__,
                                          type(initializer)))

  def Append(self, value=None, **kwarg):
    """Add another member to the array.

    Args:
      value: The new data to append to the array.
      **kwarg:  Create a new element from these keywords.

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
        value = self.rdf_type(value, **kwarg)  # pylint: disable=not-callable
      except (TypeError, ValueError):
        raise ValueError("Unable to initialize %s from type %s" %
                         (self.__class__.__name__, type(value)))

    self.content.Append(DataBlob().SetValue(value))

  def Extend(self, values):
    for v in values:
      self.Append(v)

  def __getitem__(self, item):
    return self.content[item].GetValue()

  def __len__(self):
    return len(self.content)

  def __iter__(self):
    for blob in self.content:
      yield blob.GetValue()

  def __nonzero__(self):
    return bool(self.content)

  def Pop(self, index=0):
    return self.content.Pop(index).GetValue()


class EmbeddedRDFValue(rdf_structs.RDFProtoStruct):
  """An object that contains a serialized RDFValue."""

  protobuf = jobs_pb2.EmbeddedRDFValue

  def __init__(self, initializer=None, payload=None, *args, **kwargs):
    if (not payload and isinstance(initializer, rdfvalue.RDFValue) and
        not isinstance(initializer, EmbeddedRDFValue)):
      # The initializer is an RDFValue object that we can use as payload.
      payload = initializer
      initializer = None

    super(EmbeddedRDFValue, self).__init__(initializer=initializer,
                                           *args,
                                           **kwargs)
    if payload is not None:
      self.payload = payload

  @property
  def payload(self):
    """Extracts and returns the serialized object."""
    try:
      rdf_cls = self.classes.get(self.name)
      value = rdf_cls(self.data)
      value.age = self.embedded_age

      return value
    except TypeError:
      return None

  @payload.setter
  def payload(self, payload):
    self.name = payload.__class__.__name__
    self.embedded_age = payload.age
    self.data = payload.SerializeToString()


collections.Mapping.register(Dict)
