#!/usr/bin/env python
"""Output plugins used for testing."""

from __future__ import annotations

from collections.abc import Callable, Iterable
import functools
import os
from typing import Any, ClassVar

from google.protobuf import message

from google.protobuf import any_pb2
from grr_response_core.lib.rdfvalues import client as rdf_client
from grr_response_proto import flows_pb2
from grr_response_server import instant_output_plugin
from grr_response_server import instant_output_plugin_registry
from grr_response_server import output_plugin
from grr_response_server import output_plugin_registry
from grr.test_lib import test_lib


def WithInstantOutputPluginProto(
    plugin_cls: type[instant_output_plugin.InstantOutputPluginProto],
) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
  """Makes given function execute with specified instant output plugin registered."""

  def Decorator(func: Callable[..., Any]) -> Callable[..., Any]:

    @functools.wraps(func)
    def Wrapper(*args: Any, **kwargs: Any) -> None:
      with _InstantOutputPluginProtoContext(plugin_cls):
        func(*args, **kwargs)

    return Wrapper

  return Decorator


class _InstantOutputPluginProtoContext:
  """A context manager for execution with a certain InstantOutputPlugin registered."""

  def __init__(
      self, plugin_cls: type[instant_output_plugin.InstantOutputPluginProto]
  ):
    self._plugin_cls = plugin_cls

  def __enter__(self) -> None:
    instant_output_plugin_registry.RegisterInstantOutputPluginProto(
        self._plugin_cls
    )

  def __exit__(self, exc_type: Any, exc_value: Any, traceback: Any) -> None:
    del exc_type, exc_value, traceback  # Unused.

    assert self._plugin_cls.plugin_name is not None
    instant_output_plugin_registry.UnregisterInstantOutputPluginProto(
        self._plugin_cls.plugin_name
    )


def WithOutputPluginProto(
    plugin_cls: type[output_plugin.OutputPluginProto[Any]],
) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
  """Makes given function execute with specified output plugin registered."""

  def Decorator(func: Callable[..., Any]) -> Callable[..., Any]:

    @functools.wraps(func)
    def Wrapper(*args: Any, **kwargs: Any) -> None:
      with _OutputPluginProtoContext(plugin_cls):
        func(*args, **kwargs)

    return Wrapper

  return Decorator


class _OutputPluginProtoContext:
  """A context manager for execution with a certain OutputPluginProto registered."""

  def __init__(self, plugin_cls: type[output_plugin.OutputPluginProto[Any]]):
    self._plugin_cls = plugin_cls

  def __enter__(self) -> None:
    output_plugin_registry.RegisterOutputPluginProto(self._plugin_cls)

  def __exit__(self, exc_type: Any, exc_value: Any, traceback: Any) -> None:
    del exc_type, exc_value, traceback  # Unused.

    output_plugin_registry.UnregisterOutputPluginProto(self._plugin_cls)


class InstantOutputPluginTestBase(test_lib.GRRBaseTest):
  """Mixing with helper methods."""

  plugin_cls: ClassVar[
      type[instant_output_plugin.InstantOutputPluginProto] | None
  ] = None

  def setUp(self):
    super().setUp()

    self.client_id = self.SetupClient(0)
    self.results_urn = rdf_client.ClientURN(self.client_id).Add("foo/bar")

    assert self.__class__.plugin_cls is not None
    self.plugin: instant_output_plugin.InstantOutputPluginProto = (
        self.__class__.plugin_cls(source_urn=self.results_urn)
    )

  def ProcessValuesProto(
      self,
      values_by_cls: dict[type[message.Message], Iterable[message.Message]],
  ) -> str:
    chunks = []

    chunks.extend(list(self.plugin.Start()))

    for value_cls in sorted(values_by_cls, key=lambda cls: cls.__name__):
      values = values_by_cls[value_cls]
      flow_results = []
      type_url = ""
      for value in values:
        packed_value = any_pb2.Any()
        packed_value.Pack(value)
        flow_results.append(
            flows_pb2.FlowResult(client_id=self.client_id, payload=packed_value)
        )
        if not type_url:
          type_url = packed_value.type_url

      # pylint: disable=cell-var-from-loop
      chunks.extend(
          list(self.plugin.ProcessValuesOfType(type_url, lambda: flow_results))
      )
      # pylint: enable=cell-var-from-loop

    chunks.extend(list(self.plugin.Finish()))

    fd_path = os.path.join(self.temp_dir, self.plugin.output_file_name)
    with open(fd_path, "wb") as fd:
      for chunk in chunks:
        fd.write(chunk)

    return fd_path
