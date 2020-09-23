#!/usr/bin/env python
# Lint as: python3
"""Simple parsers for configuration files."""

from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

from typing import IO
from typing import Iterable
from typing import Iterator

from grr_response_core.lib import parser
from grr_response_core.lib import parsers
from grr_response_core.lib.parsers import config_file
from grr_response_core.lib.rdfvalues import client as rdf_client
from grr_response_core.lib.rdfvalues import paths as rdf_paths
from grr_response_core.lib.rdfvalues import protodict as rdf_protodict


class ProcSysParser(parsers.MultiFileParser[rdf_protodict.AttributedDict]):
  """Parser for /proc/sys entries."""

  output_types = [rdf_protodict.AttributedDict]
  supported_artifacts = ["LinuxProcSysHardeningSettings"]

  def _Parse(self, pathspec, file_obj):
    # Remove /proc/sys
    key = pathspec.path.replace("/proc/sys/", "", 1)
    key = key.replace("/", "_")
    value = file_obj.read().decode("utf-8").split()
    if len(value) == 1:
      value = value[0]
    return key, value

  def ParseFiles(
      self,
      knowledge_base: rdf_client.KnowledgeBase,
      pathspecs: Iterable[rdf_paths.PathSpec],
      filedescs: Iterable[IO[bytes]],
  ) -> Iterator[rdf_protodict.AttributedDict]:
    del knowledge_base  # Unused.

    config = {}
    for pathspec, file_obj in zip(pathspecs, filedescs):
      k, v = self._Parse(pathspec, file_obj)
      config[k] = v
    yield rdf_protodict.AttributedDict(config)


class SysctlCmdParser(parser.CommandParser):
  """Parser for sysctl -a output."""

  output_types = [rdf_protodict.AttributedDict]
  supported_artifacts = ["LinuxSysctlCmd"]

  def __init__(self, *args, **kwargs):
    super().__init__(*args, **kwargs)
    self.lexer = config_file.KeyValueParser()

  def Parse(self, cmd, args, stdout, stderr, return_val, knowledge_base):
    """Parse the sysctl output."""
    _ = stderr, args, knowledge_base  # Unused.
    self.CheckReturn(cmd, return_val)
    result = rdf_protodict.AttributedDict()
    # The KeyValueParser generates an ordered dict by default. The sysctl vals
    # aren't ordering dependent, but there's no need to un-order it.
    for k, v in self.lexer.ParseToOrderedDict(stdout).items():
      key = k.replace(".", "_")
      if len(v) == 1:
        v = v[0]
      result[key] = v
    return [result]
