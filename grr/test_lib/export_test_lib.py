#!/usr/bin/env python
"""Classes for export-related tests."""

from __future__ import annotations

import collections
from collections.abc import Callable
import functools
import types
from typing import Any
from unittest import mock

from grr_response_server import export_converters_registry
from grr_response_server.export_converters import base
from grr_response_server.export_converters import registry_init as ec_registry_init


def WithExportConverterProto(
    export_converter_cls: type[base.ExportConverterProto[Any]],
) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
  """Makes given function execute with specified export converter registered.

  Args:
    export_converter_cls: A ExportConverterProto class object.

  Returns:
    A decorator function that registers and unregisters the ExportConverter.
  """

  def Decorator(func: Callable[..., Any]) -> Callable[..., Any]:

    @functools.wraps(func)
    def Wrapper(*args: Any, **kwargs: Any) -> None:
      with _ExportConverterContextProto(export_converter_cls):
        func(*args, **kwargs)

    return Wrapper

  return Decorator


def WithAllExportConverters(func: Callable[..., Any]) -> Callable[..., Any]:
  """Makes given function execute with all known ExportConverter registered."""

  @functools.wraps(func)
  def Wrapper(*args: Any, **kwargs: Any) -> None:
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

  def __init__(
      self, export_converter_cls: type[base.ExportConverterProto[Any]]
  ):
    self._export_converter = export_converter_cls

  def __enter__(self) -> None:
    export_converters_registry.RegisterProto(self._export_converter)

  def __exit__(
      self,
      exc_type: type[BaseException] | None,
      exc_value: BaseException | None,
      traceback: types.TracebackType | None,
  ) -> None:
    del exc_type, exc_value, traceback  # Unused.

    export_converters_registry.UnregisterProto(self._export_converter)
