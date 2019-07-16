#!/usr/bin/env python
# -*- encoding: utf-8 -*-
"""OutputPlugin that processes aggregated Yara Memory Dumps."""
from __future__ import absolute_import
from __future__ import division

from __future__ import unicode_literals

import abc
import collections
import threading

from future.utils import iteritems
from future.utils import with_metaclass

from typing import Iterable, Iterator, List, Text

from grr_response_core.lib import utils
from grr_response_core.lib.rdfvalues import client_fs as rdf_client_fs
from grr_response_core.lib.rdfvalues import memory as rdf_memory
from grr_response_core.lib.rdfvalues import paths as rdf_paths
from grr_response_core.lib.rdfvalues import structs as rdf_structs
from grr_response_proto import flows_pb2
from grr_response_server import output_plugin


class MemoryDumpOutputPluginState(rdf_structs.RDFProtoStruct):
  """Internal state of AbstractMemoryDumpOutputPlugin."""

  protobuf = flows_pb2.MemoryDumpOutputPluginState
  rdf_deps = [rdf_memory.YaraProcessDumpInformation, rdf_paths.PathSpec]


def _PathSpecToId(pathspec):
  """Extracts the filename out of a PathSpec in a robust way."""
  return pathspec.Basename().replace("\\", "/").split("/")[-1]


# TODO: Fix Windows PathSpec inconsistency and remove helper again.
def _NormalizePaths(
    real_paths,
    flawed_paths):
  """Returns all `real_paths` whose filename is present in `flawed_paths`.

  Args:
    real_paths: An Iterable of PathSpecs, representing the source of truth.
    flawed_paths: An Iterable of PathSpecs, representing a subset of real_paths
      with slightly different path components, but matching filenames.

  Raises:
    KeyError: If one flawed_path has a filename not found in real_paths.

  Returns:
    A List of PathSpecs from real_paths whose filenames match flawed_paths.
  """
  paths_lookup = {_PathSpecToId(ps): ps for ps in real_paths}
  return [paths_lookup[_PathSpecToId(ps)] for ps in flawed_paths]


class AbstractMemoryDumpOutputPlugin(
    with_metaclass(abc.ABCMeta, output_plugin.OutputPlugin)):
  """Abstract OutputPlugin that aggregates Yara Memory Dumps.

  This OutputPlugin works on YaraProcessDump results, waiting until all memory
  areas of a process dump have been received, then calling OutputMemoryDump().

  This plugin needs to keep internal state, because memory areas are collected
  asynchronously.

  Attributes:
    lock: Lock required by the utils.Synchronized decorator.
  """

  def __init__(self, source_urn=None, args=None, token=None):
    """See base class."""
    super(AbstractMemoryDumpOutputPlugin,
          self).__init__(source_urn, args, token)
    self._state = None
    self.lock = threading.RLock()

  def InitializeState(self, state):
    """See base class."""
    super(AbstractMemoryDumpOutputPlugin, self).InitializeState(state)
    state["clients"] = {}

  def UpdateState(self, state):
    """See base class."""
    super(AbstractMemoryDumpOutputPlugin, self).UpdateState(state)
    state["clients"] = self._state

  @utils.Synchronized
  def _ReInitializeLocalState(self, state):
    """Overwrites local state from persistent state."""
    # This is required in case Plugin execution moves from one worker to
    # another.
    if self._state is not None:
      return
    self._state = collections.defaultdict(MemoryDumpOutputPluginState)

    for client_id, client_state in iteritems(state["clients"]):
      local_client_state = self._GetOrInitClientState(client_id)
      local_client_state.dumps.Extend(client_state.dumps)
      local_client_state.paths.Extend(client_state.paths)
      local_client_state.completed.Extend(client_state.completed)

  @utils.Synchronized
  def _GetOrInitClientState(self,
                            client_id):
    return self._state[client_id]

  def _IterateReadyProcessDumpsOnce(
      self, client_state
  ):
    """Yields YaraProcessDumpInformation that is ready to submit exactly once.

    Args:
      client_state: MemoryDumpOutputPluginState of a client that sent a message
        for processing.

    Yields:
      YaraProcessDumpInformation instances, exactly once as soon all their paths
      are available, marking them as completed in `client_state` to not yield
      them again.
    """
    for pd in list(client_state.dumps):
      try:
        _NormalizePaths(client_state.paths, pd.dump_files)
      except KeyError:
        continue  # At least one PathSpec has not been received yet.

      # TODO: Sets would be nicer here, but ProtoStructs are
      # mutable and their __hash__ changes during read access (ಠ益ಠ).
      if self._PutIfAbsent(client_state.completed, pd):
        yield pd

  @utils.Synchronized
  def _PutIfAbsent(self, lst, obj):
    """Puts `obj` in `lst` in an atomical step if not yet present.

    Args:
      lst: the list to be extended
      obj: the object to put into `lst`

    Returns:
      True, if `obj` was added. False, if `obj` was already present.
    """
    if obj in lst:
      return False
    lst.append(obj)
    return True

  def ProcessResponses(self, state, responses):
    """Processes Yara memory dumps and collected memory areas.

    Args:
      state: persistent plugin state
      responses: GrrMessages, containing YaraProcessDumpResponse, StatEntry, and
        other RDFValues
    """

    # This Plugin keeps local state, grouped by the client id that sent the
    # Yara dump:
    # - `dumps` is a list of all seen YaraProcessDumpInformation
    # - `paths` is a list of all collected memory areas
    # - `completed` is a list of all exported YaraProcessDumpInformation
    self._ReInitializeLocalState(state)

    for response in responses:
      client_id = response.source.Basename()
      client_state = self._GetOrInitClientState(client_id)

      # First, add the data that came in to the Plugin's state.
      if isinstance(response.payload, rdf_memory.YaraProcessDumpResponse):
        client_state.dumps.Extend(response.payload.dumped_processes)
      elif isinstance(response.payload, rdf_client_fs.StatEntry):
        client_state.paths.Append(response.payload.pathspec)

      # Second, iterate through the state and process all Yara dumps whose
      # memory areas have been fully collected.
      for process_dump in self._IterateReadyProcessDumpsOnce(client_state):
        # TODO: Fix Windows PathSpec inconsistency.
        paths = _NormalizePaths(client_state.paths, process_dump.dump_files)
        fixed_pd = rdf_memory.YaraProcessDumpInformation(process_dump)
        fixed_pd.dump_files = paths
        self.OutputMemoryDump(fixed_pd, client_id)

  @abc.abstractmethod
  def OutputMemoryDump(self,
                       process_dump,
                       client_id):
    """Processes a YaraProcessDumpInformation further.

    This method is called at most once per YaraProcessDumpInformation. It is
    called when a YaraProcessDumpInformation and all its memory areas have been
    received.

    Args:
      process_dump: The YaraProcessDumpInformation dumped by the client.
      client_id: ID of the client that dumped the YaraProcessDumpInformation.
    """
    pass
