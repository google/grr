#!/usr/bin/env python
"""Simple parsers for configuration files."""

from grr.lib import parsers
from grr.lib import rdfvalue


class ProcSysParser(parsers.FileParser):
  """Parser for /proc/sys entries."""

  output_types = ["KeyValue"]
  supported_artifacts = ["LinuxProcSysHardeningSettings"]
  process_together = True

  def _Parse(self, stat, file_obj):
    # Remove /proc/sys
    key = stat.pathspec.path.replace("/proc/sys/", "", 1)
    key = key.replace("/", "_")
    value = file_obj.read(100000).split()
    if len(value) == 1:
      value = value[0]
    return key, value

  def ParseMultiple(self, stats, file_objs, _):
    config = {}
    for stat, file_obj in zip(stats, file_objs):
      k, v = self._Parse(stat, file_obj)
      config[k] = v
    return rdfvalue.AttributedDict(config)
