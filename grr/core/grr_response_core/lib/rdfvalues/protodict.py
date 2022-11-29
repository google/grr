#!/usr/bin/env python
"""A generic serializer for python dictionaries."""

from collections import abc
import logging
from typing import List, Text, Union, cast

from grr_response_core.lib import rdfvalue
from grr_response_core.lib import serialization
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

    super().__init__(initializer=initializer, *args, **kwargs)
    if payload is not None:
      self.payload = payload

  @property
  def payload(self):
    """Extracts and returns the serialized object."""
    try:
      rdf_cls = self.classes.get(self.name)
      if rdf_cls:
        value = rdf_cls.FromSerializedBytes(self.data)

        return value
    except TypeError:
      logging.exception("Error during decoding %s", self)
      return None

  @payload.setter
  def payload(self, payload):
    self.name = payload.__class__.__name__
    self.data = serialization.ToBytes(payload)


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
    type_mappings = [(Text, "string"), (bytes, "data"), (bool, "boolean"),
                     (int, "integer"), (dict, "dict"), (float, "float")]

    if value is None:
      self.none = "None"

    elif isinstance(value, rdfvalue.RDFValue):
      self.rdf_value.data = value.SerializeToBytes()
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

      message = "Unsupported type for ProtoDict: %s of type %s" % (value,
                                                                   type(value))
      if raise_on_error:
        raise TypeError(message)

      logging.error(message)
      setattr(self, "string", message)

    return self

  # TODO: Defaulting to ignoring errors is unexpected and
  #  problematic.
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
        return serialization.FromBytes(rdf_class, self.rdf_value.data)
      except (ValueError, KeyError) as e:
        if ignore_error:
          logging.exception("Error during GetValue() of %s", self)
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

  def __init__(self, initializer=None, **kwargs):
    super().__init__(initializer=None)

    self.dat = None  # type: Union[List[KeyValue], rdf_structs.RepeatedFieldHelper]

    # Support initializing from a mapping
    if isinstance(initializer, dict):
      self.FromDict(initializer)

    # Can be initialized from kwargs (like a dict).
    elif initializer is None:
      self.FromDict(kwargs)

    # Initialize from another Dict.
    elif isinstance(initializer, Dict):
      self.FromDict(initializer.ToDict())

    else:
      raise rdfvalue.InitializeError("Invalid initializer for ProtoDict.")

  def ToDict(self):

    def _Convert(obj):
      if isinstance(obj, Dict):
        return {key: _Convert(value) for key, value in obj.items()}
      if isinstance(obj, list):
        return [_Convert(item) for item in obj]
      return obj

    return _Convert(self)

  def FromDict(self, dictionary, raise_on_error=True):
    # First clear and then set the dictionary.
    self._values = {}
    for key, value in dictionary.items():
      self._values[key] = KeyValue(
          k=DataBlob().SetValue(key, raise_on_error=raise_on_error),
          v=DataBlob().SetValue(value, raise_on_error=raise_on_error))
    self.dat = self._values.values()  # pytype: disable=annotation-type-mismatch
    return self

  def __getitem__(self, key):
    return self._values[key].v.GetValue()

  def __contains__(self, key):
    return key in self._values

  # TODO: This implementation is flawed. It returns a new instance
  # on each invocation, effectively preventing changes to mutable
  # datastructures, e.g. `dct["key"] = []; dct["key"].append(5)`.
  def GetItem(self, key, default=None):
    if key in self._values:
      return self._values[key].v.GetValue()
    return default

  def Items(self):
    for x in self._values.values():
      yield x.k.GetValue(), x.v.GetValue()

  def Values(self):
    for x in self._values.values():
      yield x.v.GetValue()

  def Keys(self):
    for x in self._values.values():
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
    for x in self._values.values():
      yield x.k.GetValue()

  # Required, because in Python 3 overriding `__eq__` nullifies `__hash__`.
  __hash__ = rdf_structs.RDFProtoStruct.__hash__

  def __eq__(self, other):
    if isinstance(other, dict):
      return self.ToDict() == other
    elif isinstance(other, Dict):
      return self.ToDict() == other.ToDict()
    else:
      return False

  def GetRawData(self):
    self.dat = self._values.values()  # pytype: disable=annotation-type-mismatch
    return super().GetRawData()

  def _CopyRawData(self):
    self.dat = self._values.values()  # pytype: disable=annotation-type-mismatch
    return super()._CopyRawData()

  def SetRawData(self, raw_data):
    super().SetRawData(raw_data)
    self._values = {}
    for d in self.dat:
      self._values[d.k.GetValue()] = d

  def SerializeToBytes(self):
    self.dat = self._values.values()  # pytype: disable=annotation-type-mismatch
    return super().SerializeToBytes()

  def __str__(self) -> Text:
    return str(self.ToDict())


class AttributedDict(Dict):
  """A Dict that supports attribute indexing."""

  protobuf = jobs_pb2.AttributedDict
  rdf_deps = [
      KeyValue,
  ]

  def __init__(self, *args, **kwargs):
    super().__init__(*args, **kwargs)
    self._StringifyKeys()

  def SetRawData(self, raw_data):
    super().SetRawData(raw_data)
    self._StringifyKeys()

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

  def __setitem__(self, key, value):
    # TODO: This behavior should be removed once migration is done.
    if isinstance(key, bytes):
      key = key.decode("utf-8")

    if isinstance(key, Text):
      return super().__setitem__(key, value)

    raise TypeError("Non-string key: {!r}".format(key))

  def __getitem__(self, key):
    # TODO: This behavior should be removed once migration is done.
    if isinstance(key, bytes):
      key = key.decode("utf-8")

    if isinstance(key, Text):
      return super().__getitem__(key)

    raise TypeError("Non-string key: {!r}".format(key))

  # TODO: This behavior should be removed once migration is done.
  # Because of Python 3 migration and incompatibilities between Pythons in how
  # attributed dicts are serialized, we are forced to have this dirty hack in
  # here. Once migration is done and we are sure that the old serialized data
  # that is stored in the database does not need to be read anymore, these can
  # be removed.
  def _StringifyKeys(self):
    """Turns byte string keys into unicode string keys."""
    byte_keys = set()

    for key in self._values.keys():
      if isinstance(key, bytes):
        byte_keys.add(key)
      elif not isinstance(key, Text):
        raise TypeError("Non-string key: {!r}".format(key))

    for byte_key in byte_keys:
      value = self._values[byte_key].v
      del self._values[byte_key]

      string_key = byte_key.decode("utf-8")

      entry = KeyValue(k=DataBlob().SetValue(string_key), v=value)
      self._values[string_key] = entry

    # If we made any changes, update `self.dat` (whatever it is, but other
    # methods seem to do the same in case of modifying the internal state).
    if byte_keys:
      self.dat = list(self._values.values())


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
  allow_custom_class_name = True
  rdf_deps = [
      DataBlob,
  ]

  # Set this to an RDFValue class to ensure all members adhere to this type.
  rdf_type = None

  def __init__(self, initializer=None):
    super().__init__()

    if self.__class__ == initializer.__class__:
      self.content = initializer.Copy().content
    else:
      try:
        for item in initializer:
          self.Append(item)
      except TypeError:
        if initializer is not None:
          raise rdfvalue.InitializeError(
              "%s can not be initialized from %s" %
              (self.__class__.__name__, type(initializer)))

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

  def __bool__(self):
    return bool(self.content)

  # TODO: Remove after support for Python 2 is dropped.
  __nonzero__ = __bool__

  def Pop(self, index=0):
    return self.content.Pop(index).GetValue()


# TODO(user):pytype: Mapping is likely using abc.ABCMeta that provides a
# "register" method. Type checker doesn't see this, unfortunately.
abc.Mapping.register(Dict)  # pytype: disable=attribute-error
