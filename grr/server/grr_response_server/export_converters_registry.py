#!/usr/bin/env python
"""A mapping of export converters name and implementation."""

import collections
from typing import Set, Type

from google.protobuf import message

from grr_response_server.export_converters import base


# Maps proto message type to a set of export converters that can convert it.
_EXPORT_CONVERTER_BY_TYPE_URL: dict[
    str, Set[Type[base.ExportConverterProto]]
] = collections.defaultdict(set)


def RegisterProto(cls: Type[base.ExportConverterProto[message.Message]]):
  """Registers an ExportConversion class.

  Args:
    cls: ExportConversion class.
  """
  if cls.input_proto_type is None:  # pyrefly: ignore[missing-attribute]
    raise ValueError(
        "ExportConverterProto class %s has no input_proto_type attribute." % cls
    )

  _EXPORT_CONVERTER_BY_TYPE_URL[_GetTypeUrl(cls.input_proto_type)].add(cls)  # pyrefly: ignore[bad-argument-type]


def UnregisterProto(cls: Type[base.ExportConverterProto[message.Message]]):
  """Unregisters an ExportConversion class.

  Args:
    cls: ExportConversion class.
  """
  type_url = _GetTypeUrl(cls.input_proto_type)  # pyrefly: ignore[missing-attribute]
  if type_url in _EXPORT_CONVERTER_BY_TYPE_URL:
    _EXPORT_CONVERTER_BY_TYPE_URL[type_url].discard(cls)


def ClearExportConvertersProto():
  """Clears converters registry for protos and its cached values."""
  _EXPORT_CONVERTER_BY_TYPE_URL.clear()


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
