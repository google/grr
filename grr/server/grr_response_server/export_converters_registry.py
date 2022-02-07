#!/usr/bin/env python
"""A mapping of export converters name and implementation."""
from typing import Set, Type

from grr_response_server.export_converters import base
from grr_response_server.export_converters import data_agnostic

_EXPORT_CONVERTER_REGISTRY: Set[Type[base.ExportConverter]] = set()


def Register(cls: Type[base.ExportConverter]):
  """Registers an ExportConversion class.

  Args:
    cls: ExportConversion class.
  """
  _EXPORT_CONVERTER_REGISTRY.add(cls)


def Unregister(cls: Type[base.ExportConverter]):
  """Unregisters an ExportConversion class.

  Args:
    cls: ExportConversion class to be unregistered.
  """
  _EXPORT_CONVERTER_REGISTRY.remove(cls)


def ClearExportConverters():
  """Clears converters registry and its cached values."""
  _EXPORT_CONVERTER_REGISTRY.clear()


def GetConvertersByClass(value_cls):
  """Returns all converters that take given value as an input value."""
  results = [
      cls for cls in _EXPORT_CONVERTER_REGISTRY
      if cls.input_rdf_type == value_cls
  ]
  if not results:
    results = [data_agnostic.DataAgnosticExportConverter]

  return results


def GetConvertersByValue(value):
  """Returns all converters that take given value as an input value."""
  return GetConvertersByClass(value.__class__)
