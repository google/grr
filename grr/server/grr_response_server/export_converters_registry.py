#!/usr/bin/env python
"""A mapping of export converters name and implementation."""

import collections
from typing import Set, Type

from google.protobuf import message
from grr_response_server.export_converters import base
from grr_response_server.export_converters import data_agnostic


_EXPORT_CONVERTER_REGISTRY: Set[Type[base.ExportConverter]] = set()

# Maps proto message type to a set of export converters that can convert it.
_EXPORT_CONVERTER_REGISTRY_BY_PROTO_CLS: dict[
    type[message.Message], Set[Type[base.ExportConverterProto]]
] = collections.defaultdict(set)
_EXPORT_CONVERTER_BY_TYPE_URL: dict[
    str, Set[Type[base.ExportConverterProto]]
] = collections.defaultdict(set)


def Register(cls: Type[base.ExportConverter]):
  """Registers an ExportConversion class.

  Args:
    cls: ExportConversion class.
  """
  _EXPORT_CONVERTER_REGISTRY.add(cls)


def RegisterProto(cls: Type[base.ExportConverterProto[message.Message]]):
  """Registers an ExportConversion class.

  Args:
    cls: ExportConversion class.
  """
  if cls.input_proto_type is None:
    raise ValueError(
        "ExportConverterProto class %s has no input_proto_type attribute." % cls
    )

  _EXPORT_CONVERTER_REGISTRY_BY_PROTO_CLS[cls.input_proto_type].add(cls)
  _EXPORT_CONVERTER_BY_TYPE_URL[_GetTypeUrl(cls.input_proto_type)].add(cls)


def Unregister(cls: Type[base.ExportConverter]):
  """Unregisters an ExportConversion class.

  Args:
    cls: ExportConversion class to be unregistered.
  """
  _EXPORT_CONVERTER_REGISTRY.remove(cls)


def UnregisterProto(cls: Type[base.ExportConverterProto[message.Message]]):
  """Unregisters an ExportConversion class.

  Args:
    cls: ExportConversion class.
  """
  input_proto = cls.input_proto_type
  if input_proto in _EXPORT_CONVERTER_REGISTRY_BY_PROTO_CLS:
    _EXPORT_CONVERTER_REGISTRY_BY_PROTO_CLS[input_proto].discard(cls)

  type_url = _GetTypeUrl(cls.input_proto_type)
  if type_url in _EXPORT_CONVERTER_BY_TYPE_URL:
    _EXPORT_CONVERTER_BY_TYPE_URL[type_url].discard(cls)


def ClearExportConverters():
  """Clears converters registry and its cached values."""
  _EXPORT_CONVERTER_REGISTRY.clear()


def ClearExportConvertersProto():
  """Clears converters registry for protos and its cached values."""
  _EXPORT_CONVERTER_REGISTRY_BY_PROTO_CLS.clear()
  _EXPORT_CONVERTER_BY_TYPE_URL.clear()


def GetConvertersByClass(value_cls):
  """Returns all converters that take given value as an input value."""
  results = [
      cls
      for cls in _EXPORT_CONVERTER_REGISTRY
      if cls.input_rdf_type == value_cls
  ]
  if not results:
    results = [data_agnostic.DataAgnosticExportConverter]

  return results


def GetConvertersByClassProto(
    value_cls: type[message.Message],
) -> Set[Type[base.ExportConverterProto[message.Message]]]:
  """Returns all converters that take given value as an input value."""
  # Will return an empty set if the class is not registered.
  return _EXPORT_CONVERTER_REGISTRY_BY_PROTO_CLS[value_cls]


def GetConvertersByValue(value):
  """Returns all converters that take given value as an input value."""
  return GetConvertersByClass(value.__class__)


def GetConvertersByValueProto(
    value: message.Message,
) -> Set[Type[base.ExportConverterProto]]:
  """Returns all converters that take given proto value as an input value."""
  return GetConvertersByClassProto(value.__class__)


def GetConvertersByTypeUrl(
    type_url: str,
) -> Set[Type[base.ExportConverterProto]]:
  """Returns all converters that take given value of the given type_url type."""
  # Will return an empty set if the class is not registered.
  return _EXPORT_CONVERTER_BY_TYPE_URL[type_url]


def _GetTypeUrl(proto_cls: Type[message.Message]):
  # This prefix is based on the default used by any proto packing.
  # An alternative would be to build an instance, pack it, and then
  # get the type_url from the result. Seems like an overkill in this case,
  # especially considering that sometimes we build this url by hand
  # given the RDFValue type name.
  return f"type.googleapis.com/{proto_cls.DESCRIPTOR.full_name}"
