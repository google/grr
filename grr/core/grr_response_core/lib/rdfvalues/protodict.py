#!/usr/bin/env python
"""A generic serializer for python dictionaries."""

from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

import collections


from future.utils import iteritems
from future.utils import itervalues
from past.builtins import long
from typing import cast, List, Union

from grr_response_core.lib import rdfvalue
from grr_response_core.lib import utils
from grr_response_core.lib.rdfvalues import structs as rdf_structs
from grr_response_proto import jobs_pb2


class EmbeddedRDFValue(rdf_structs.RDFProtoStruct):
  """An object that contains a serialized RDFValue."""

  protobuf = jobs_pb2.EmbeddedRDFValue
  rdf_deps = [
      rdfvalue.RDFDatetime,
  ]

  def __init__(self, initializer=None, payload=None, *args, **kwargs):
    if (not payload and isinstance(initializer, rdfvalue.RDFValue) and
        not isinstance(initializer, EmbeddedRDFValue)):
      # The initializer is an RDFValue object that we can use as payload.
      payload = initializer
      initializer = None

    super(EmbeddedRDFValue, self).__init__(
        initializer=initializer, *args, **kwargs)
    if payload is not None:
      self.payload = payload

  @property
  def payload(self):
    """Extracts and returns the serialized object."""
    try:
      rdf_cls = self.classes.get(self.name)
      if rdf_cls:
        value = rdf_cls.FromSerializedString(self.data)
        value.age = self.embedded_age

        return value
    except TypeError:
      return None

  @payload.setter
  def payload(self, payload):
    self.name = payload.__class__.__name__
    self.embedded_age = payload.age
    self.data = payload.SerializeToString()


class DataBlob(rdf_structs.RDFProtoStruct):
  """Wrapper class for DataBlob protobuf."""
  protobuf = jobs_pb2.DataBlob
  rdf_deps = [
      "BlobArray",  # TODO(user): dependency loop.
      "Dict",  # TODO(user): dependency loop.
      EmbeddedRDFValue,
  ]

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
      self.list.content.Extend([
          DataBlob().SetValue(v, raise_on_error=raise_on_error) for v in value
      ])

    elif isinstance(value, set):
      self.set.content.Extend([
          DataBlob().SetValue(v, raise_on_error=raise_on_error) for v in value
      ])

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

    field_names = [
        "integer", "string", "data", "boolean", "list", "dict", "rdf_value",
        "float", "set"
    ]

    values = [getattr(self, x) for x in field_names if self.HasField(x)]

    if len(values) != 1:
      return None

    if self.HasField("boolean"):
      return bool(values[0])

    # Unpack RDFValues.
    if self.HasField("rdf_value"):
      try:
        rdf_class = rdfvalue.RDFValue.classes[self.rdf_value.name]
        return rdf_class.FromSerializedString(
            self.rdf_value.data, age=self.rdf_value.age)
      except (ValueError, KeyError) as e:
        if ignore_error:
          return e

        raise

    elif self.HasField("list"):
      return [x.GetValue() for x in self.list.content]

    elif self.HasField("set"):
      return set([x.GetValue() for x in self.set.content])

    else:
      return values[0]


class KeyValue(rdf_structs.RDFProtoStruct):
  protobuf = jobs_pb2.KeyValue
  rdf_deps = [
      DataBlob,
  ]


class Dict(rdf_structs.RDFProtoStruct):
  """A high level interface for protobuf Dict objects.

  This effectively converts from a dict to a proto and back.
  The dict may contain strings (python unicode objects), int64,
  or binary blobs (python string objects) as keys and values.
  """
  protobuf = jobs_pb2.Dict
  rdf_deps = [
      KeyValue,
  ]

  _values = None

  def __init__(self, initializer=None, age=None, **kwarg):
    super(Dict, self).__init__(initializer=None, age=age)

    self.dat = None  # type: Union[List[KeyValue], rdf_structs.RepeatedFieldHelper]

    # Support initializing from a mapping
    if isinstance(initializer, dict):
      self.FromDict(initializer)

    # Can be initialized from kwargs (like a dict).
    elif initializer is None:
      self.FromDict(kwarg)

    # Initialize from another Dict.
    elif isinstance(initializer, Dict):
      self.FromDict(initializer.ToDict())
      self.age = initializer.age

    else:
      raise rdfvalue.InitializeError("Invalid initializer for ProtoDict.")

  def ToDict(self):
    result = {}
    for x in itervalues(self._values):
      key = x.k.GetValue()
      result[key] = x.v.GetValue()
      try:
        # Try to unpack nested AttributedDicts
        result[key] = result[key].ToDict()
      except AttributeError:
        pass

    return result

  def FromDict(self, dictionary, raise_on_error=True):
    # First clear and then set the dictionary.
    self._values = {}
    for key, value in iteritems(dictionary):
      self._values[key] = KeyValue(
          k=DataBlob().SetValue(key, raise_on_error=raise_on_error),
          v=DataBlob().SetValue(value, raise_on_error=raise_on_error))
    self.dat = itervalues(self._values)
    return self

  def __getitem__(self, key):
    return self._values[key].v.GetValue()

  def __contains__(self, key):
    return key in self._values

  def GetItem(self, key, default=None):
    if key in self._values:
      return self._values[key].v.GetValue()
    return default

  def Items(self):
    for x in itervalues(self._values):
      yield x.k.GetValue(), x.v.GetValue()

  def Values(self):
    for x in itervalues(self._values):
      yield x.v.GetValue()

  def Keys(self):
    for x in itervalues(self._values):
      yield x.k.GetValue()

  get = utils.Proxy("GetItem")
  items = utils.Proxy("Items")
  keys = utils.Proxy("Keys")
  values = utils.Proxy("Values")

  def __delitem__(self, key):
    # TODO(user):pytype: assigning "dirty" here is a hack. The assumption
    # that self.dat is RepeatedFieldHelper may not hold. For some reason the
    # type checker doesn not respect the isinstance check below and explicit
    # cast is required.
    if not isinstance(self.dat, rdf_structs.RepeatedFieldHelper):
      raise TypeError("self.dat has an unexpected type %s" % self.dat.__class__)
    cast(rdf_structs.RepeatedFieldHelper, self.dat).dirty = True
    del self._values[key]

  def __len__(self):
    return len(self._values)

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
    # TODO(user):pytype: assigning "dirty" here is a hack. The assumption
    # that self.dat is RepeatedFieldHelper may not hold. For some reason the
    # type checker doesn not respect the isinstance check below and explicit
    # cast is required.
    if not isinstance(self.dat, rdf_structs.RepeatedFieldHelper):
      raise TypeError("self.dat has an unexpected type %s" % self.dat.__class__)
    cast(rdf_structs.RepeatedFieldHelper, self.dat).dirty = True
    self._values[key] = KeyValue(
        k=DataBlob().SetValue(key, raise_on_error=raise_on_error),
        v=DataBlob().SetValue(value, raise_on_error=raise_on_error))

  def __setitem__(self, key, value):
    # TODO(user):pytype: assigning "dirty" here is a hack. The assumption
    # that self.dat is RepeatedFieldHelper may not hold. For some reason the
    # type checker doesn not respect the isinstance check below and explicit
    # cast is required.
    if not isinstance(self.dat, rdf_structs.RepeatedFieldHelper):
      raise TypeError("self.dat has an unexpected type %s" % self.dat.__class__)
    cast(rdf_structs.RepeatedFieldHelper, self.dat).dirty = True
    self._values[key] = KeyValue(
        k=DataBlob().SetValue(key), v=DataBlob().SetValue(value))

  def __iter__(self):
    for x in itervalues(self._values):
      yield x.k.GetValue()

  def __eq__(self, other):
    if isinstance(other, dict):
      return self.ToDict() == other
    elif isinstance(other, Dict):
      return self.ToDict() == other.ToDict()
    else:
      return False

  def GetRawData(self):
    self.dat = itervalues(self._values)
    return super(Dict, self).GetRawData()

  def _CopyRawData(self):
    self.dat = itervalues(self._values)
    return super(Dict, self)._CopyRawData()

  def SetRawData(self, raw_data):
    super(Dict, self).SetRawData(raw_data)
    self._values = {}
    for d in self.dat:
      self._values[d.k.GetValue()] = d

  def SerializeToString(self):
    self.dat = itervalues(self._values)
    return super(Dict, self).SerializeToString()

  def ParseFromString(self, value):
    super(Dict, self).ParseFromString(value)
    self._values = {}
    for d in self.dat:
      self._values[d.k.GetValue()] = d

  def __str__(self):
    return str(self.ToDict())


class AttributedDict(Dict):
  """A Dict that supports attribute indexing."""

  protobuf = jobs_pb2.AttributedDict
  rdf_deps = [
      KeyValue,
  ]

  def __getattr__(self, item):
    # Pickle is checking for the presence of overrides for various builtins.
    # Without this check we swallow the error and return None, which confuses
    # pickle protocol version 2.
    if item.startswith("__"):
      raise AttributeError()
    return self.GetItem(item)

  def __setattr__(self, item, value):
    # Existing class or instance members are assigned to normally.
    if hasattr(self.__class__, item) or item in self.__dict__:
      object.__setattr__(self, item, value)
    else:
      self.SetItem(item, value)


class BlobArray(rdf_structs.RDFProtoStruct):
  protobuf = jobs_pb2.BlobArray
  rdf_deps = [
      DataBlob,
  ]


class RDFValueArray(rdf_structs.RDFProtoStruct):
  """A type which serializes a list of RDFValue instances.

  TODO(user): This needs to be deprecated in favor of just defining a
  protobuf with a repeated field (This can be now done dynamically, which is the
  main reason we used this in the past).
  """
  protobuf = jobs_pb2.BlobArray
  rdf_deps = [
      DataBlob,
  ]

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
          raise rdfvalue.InitializeError(
              "%s can not be initialized from %s" % (self.__class__.__name__,
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


# TODO(user):pytype: Mapping is likely using abc.ABCMeta that provides a
# "register" method. Type checker doesn't see this, unfortunately.
collections.Mapping.register(Dict)  # pytype: disable=attribute-error
