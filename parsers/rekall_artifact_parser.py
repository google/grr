#!/usr/bin/env python
"""Parsers for handling rekall output."""

import json
import ntpath

from grr.lib import artifact_lib
from grr.lib import parsers
from grr.lib import rdfvalue


class RekallPsListParser(parsers.RekallPluginParser):
  """Parser for Rekall PsList results."""

  output_types = ["Process"]
  supported_artifacts = ["RekallPsList"]

  def ParseProcess(self, item):
    cybox = item.get("_EPROCESS", {}).get("Cybox", {})
    result = rdfvalue.Process(
        exe=cybox.get("Name"),
        pid=cybox.get("PID"),
        ppid=cybox.get("Parent_PID"),
        num_threads=item.get("thread_count"),
        ctime=item.get("process_create_time", {}).get("epoch"),
    )

    return result

  def Parse(self, response, unused_knowledge_base):
    """Parse the key pslist plugin output."""
    for message in json.loads(response.json_messages):
      if message[0] == "r":
        yield self.ParseProcess(message[1])


class RekallVADParser(parsers.RekallPluginParser):
  output_types = ["PathSpec"]
  supported_artifacts = ["FullVADBinaryList"]

  # Required for environment variable expansion
  knowledgebase_dependencies = ["environ_systemdrive", "environ_systemroot"]

  def Parse(self, response, knowledge_base):
    system_drive = artifact_lib.ExpandWindowsEnvironmentVariables(
        "%systemdrive%", knowledge_base)

    for message in json.loads(response.json_messages):
      if message[0] == "r":
        protection = message[1].get("protection", {}).get("enum", "")
        if "EXECUTE" not in protection:
          continue

        filename = message[1].get("filename", "")
        if filename and filename != "Pagefile-backed section":
          yield rdfvalue.PathSpec(
              path=ntpath.normpath(ntpath.join(system_drive, filename)),
              pathtype=rdfvalue.PathSpec.PathType.OS)
