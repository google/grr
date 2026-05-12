#!/usr/bin/env python
"""Classes for export-related tests."""

import collections
import functools
from typing import Any, Callable
from unittest import mock

from grr_response_server import export_converters_registry
from grr_response_server.export_converters import base
from grr_response_server.export_converters import registry_init as ec_registry_init


def WithExportConverterProto(
    export_converter_cls: type[base.ExportConverterProto],
) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
  """Makes given function execute with specified export converter registered.

  Args:
    export_converter_cls: A ExportConverterProto class object.

  Returns:
    A decorator function that registers and unregisters the ExportConverter.
  """

  def Decorator(func):

    @functools.wraps(func)
    def Wrapper(*args, **kwargs):
      with _ExportConverterContextProto(export_converter_cls):
        func(*args, **kwargs)

    return Wrapper

  return Decorator


def WithAllExportConverters(func):
  """Makes given function execute with all known ExportConverter registered."""

  @functools.wraps(func)
  def Wrapper(*args, **kwargs):
    with mock.patch.object(
        export_converters_registry,
        "_EXPORT_CONVERTER_REGISTRY_BY_PROTO_CLS",
        collections.defaultdict(set),
    ):
      with mock.patch.object(
          export_converters_registry,
          "_EXPORT_CONVERTER_BY_TYPE_URL",
          collections.defaultdict(set),
      ):
        ec_registry_init.RegisterExportConverters()
        func(*args, **kwargs)

  return Wrapper


class _ExportConverterContextProto(object):
  """A context manager for execution with certain ExportConverter registered."""

  def __init__(self, export_converter_cls: base.ExportConverterProto):
    self._export_converter = export_converter_cls

  def __enter__(self):
    export_converters_registry.RegisterProto(self._export_converter)

  def __exit__(self, exc_type, exc_value, traceback):
    del exc_type, exc_value, traceback  # Unused.

    export_converters_registry.UnregisterProto(self._export_converter)
