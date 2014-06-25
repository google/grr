#!/usr/bin/env python
"""Parsers for handling volatility output."""

from grr.lib import artifact_lib
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


class VolatilityVADParser(parsers.VolatilityPluginParser):
  output_types = ["PathSpec"]
  supported_artifacts = ["FullVADBinaryList"]
  # Required for environment variable expansion
  knowledgebase_dependencies = ["environ_systemdrive", "environ_systemroot"]

  def Parse(self, result, knowledge_base):
    binaries = set()
    for section in result.sections:
      table = section.table

      # Find indices of "protection" and "filename" columns
      indexed_headers = dict([(header.name, i)
                              for i, header in enumerate(table.headers)])
      try:
        protection_col_index = indexed_headers["protection"]
        filename_col_index = indexed_headers["filename"]
      except KeyError:
        # If we can't find "protection" and "filename" columns, just skip
        # this section
        continue

      for row in table.rows:
        protection_attr = row.values[protection_col_index]
        filename_attr = row.values[filename_col_index]

        if protection_attr.svalue in ("EXECUTE_READ",
                                      "EXECUTE_READWRITE",
                                      "EXECUTE_WRITECOPY"):
          if filename_attr.svalue and filename_attr.svalue not in binaries:
            binaries.add(filename_attr.svalue)
            system_drive = artifact_lib.ExpandWindowsEnvironmentVariables(
                "%systemdrive%", knowledge_base)
            path = rdfvalue.PathSpec(
                path=system_drive + "\\" + filename_attr.svalue.lstrip("\\"),
                pathtype=rdfvalue.PathSpec.PathType.OS)
            yield path
