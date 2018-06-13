#!/usr/bin/env python
"""Simple parsers for configuration files."""

from grr.lib import parser
from grr.lib.parsers import config_file
from grr.lib.rdfvalues import protodict as rdf_protodict


class ProcSysParser(parser.FileParser):
  """Parser for /proc/sys entries."""

  output_types = ["AttributedDict"]
  supported_artifacts = ["LinuxProcSysHardeningSettings"]
  process_together = True

  def _Parse(self, stat, file_obj):
    # Remove /proc/sys
    key = stat.pathspec.path.replace("/proc/sys/", "", 1)
    key = key.replace("/", "_")
    value = file_obj.read().split()
    if len(value) == 1:
      value = value[0]
    return key, value

  def ParseMultiple(self, stats, file_objs, _):
    config = {}
    for stat, file_obj in zip(stats, file_objs):
      k, v = self._Parse(stat, file_obj)
      config[k] = v
    return [rdf_protodict.AttributedDict(config)]


class SysctlCmdParser(parser.CommandParser):
  """Parser for sysctl -a output."""

  output_types = ["AttributedDict"]
  supported_artifacts = ["LinuxSysctlCmd"]

  def __init__(self, *args, **kwargs):
    super(SysctlCmdParser, self).__init__(*args, **kwargs)
    self.lexer = config_file.KeyValueParser()

  def Parse(self, cmd, args, stdout, stderr, return_val, time_taken,
            knowledge_base):
    """Parse the sysctl output."""
    _ = stderr, time_taken, args, knowledge_base  # Unused.
    self.CheckReturn(cmd, return_val)
    result = rdf_protodict.AttributedDict()
    # The KeyValueParser generates an ordered dict by default. The sysctl vals
    # aren't ordering dependent, but there's no need to un-order it.
    for k, v in self.lexer.ParseToOrderedDict(stdout).iteritems():
      key = k.replace(".", "_")
      if len(v) == 1:
        v = v[0]
      result[key] = v
    return [result]
