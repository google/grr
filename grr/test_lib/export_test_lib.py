#!/usr/bin/env python
"""Classes for export-related tests."""

import collections
import functools
from typing import Any, Callable
from unittest import mock

from grr_response_core.lib import rdfvalue
from grr_response_core.lib.rdfvalues import client as rdf_client
from grr_response_core.lib.rdfvalues import structs as rdf_structs
from grr_response_proto import export_pb2
from grr_response_proto import tests_pb2
from grr_response_server import export_converters_registry
from grr_response_server.export_converters import base
from grr_response_server.export_converters import registry_init as ec_registry_init
from grr.test_lib import test_lib


class ExportTestBase(test_lib.GRRBaseTest):
  """Base class for the export tests."""

  def setUp(self):
    super().setUp()
    self.client_id = self.SetupClient(0)
    self.metadata = base.ExportedMetadata(client_urn=self.client_id)
    self.metadata_proto = export_pb2.ExportedMetadata(
        client_urn=rdf_client.ClientURN(self.client_id).SerializeToWireFormat()
    )


class DataAgnosticConverterTestValue(rdf_structs.RDFProtoStruct):
  protobuf = tests_pb2.DataAgnosticConverterTestValue
  rdf_deps = [base.ExportedMetadata, rdfvalue.RDFDatetime, rdfvalue.RDFURN]


class DataAgnosticConverterTestValueWithMetadata(rdf_structs.RDFProtoStruct):
  protobuf = tests_pb2.DataAgnosticConverterTestValueWithMetadata


def WithExportConverter(export_converter_cls):
  """Makes given function execute with specified export converter registered.

  Args:
    export_converter_cls: A ExportConverter class object.

  Returns:
    A decorator function that registers and unregisters the ExportConverter.
  """

  def Decorator(func):

    @functools.wraps(func)
    def Wrapper(*args, **kwargs):
      with _ExportConverterContext(export_converter_cls):
        func(*args, **kwargs)

    return Wrapper

  return Decorator


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
        export_converters_registry, "_EXPORT_CONVERTER_REGISTRY", set()
    ):
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


class _ExportConverterContext(object):
  """A context manager for execution with certain ExportConverter registered."""

  def __init__(self, export_converter_cls):
    self._export_converter = export_converter_cls

  def __enter__(self):
    export_converters_registry.Register(self._export_converter)

  def __exit__(self, exc_type, exc_value, traceback):
    del exc_type, exc_value, traceback  # Unused.

    export_converters_registry.Unregister(self._export_converter)


class _ExportConverterContextProto(object):
  """A context manager for execution with certain ExportConverter registered."""

  def __init__(self, export_converter_cls: base.ExportConverterProto):
    self._export_converter = export_converter_cls

  def __enter__(self):
    export_converters_registry.RegisterProto(self._export_converter)

  def __exit__(self, exc_type, exc_value, traceback):
    del exc_type, exc_value, traceback  # Unused.

    export_converters_registry.UnregisterProto(self._export_converter)
