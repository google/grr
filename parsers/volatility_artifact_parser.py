#!/usr/bin/env python
"""Parsers for handling volatility output."""

from grr.lib import parsers
from grr.lib import rdfvalue


class VolatilityPsListParser(parsers.VolatilityPluginParser):
  """Parser for Volatility PsList results."""

  output_types = ["Process"]
  supported_artifacts = ["VolatilityPsList"]

  mapping = {"ppid": "ppid",
             "pid": "pid",
             "file_name": "exe",
             "thread_count": "num_threads",
             "process_create_time": "ctime"
            }

  def Parse(self, result, unused_knowledge_base):
    """Parse the key pslist plugin output."""
    for value_dict in self.IterateSections(result, "pslist"):
      process = rdfvalue.Process()
      for key, value in value_dict.iteritems():
        if key in self.mapping:
          attr = self.mapping[key]
          if isinstance(getattr(process, attr), basestring):
            setattr(process, attr, value.svalue)
          else:
            setattr(process, attr, value.value)
      yield process
