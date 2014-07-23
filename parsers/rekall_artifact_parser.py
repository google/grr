#!/usr/bin/env python
"""Parsers for handling rekall output."""

import json

from rekall import session
from rekall.ui import renderer

from grr.lib import artifact_lib
from grr.lib import parsers
from grr.lib import rdfvalue


class PslistParsingRenderer(renderer.BaseRenderer):
  """A renderer that parses responses of the pslist plugin."""

  processes = []
  indexes = {}

  def section(self, *args, **kw):
    pass

  def table_header(self, *args, **kw):
    try:
      descriptions = [c[1] for c in kw["columns"]]
      for column_name, index_name in [
          ("file_name", "exe"),
          ("pid", "pid"),
          ("ppid", "ppid"),
          ("thread_count", "num_threads"),
          ("process_create_time", "ctime"),
          ]:
        self.indexes[index_name] = descriptions.index(column_name)
    except ValueError:
      raise ValueError("Could not find all needed columns.")

  def table_row(self, *args, **kw):
    result = rdfvalue.Process()
    result.exe = unicode(args[self.indexes["exe"]])
    result.pid = int(args[self.indexes["pid"]])
    result.ppid = int(args[self.indexes["ppid"]])
    result.num_threads = int(args[self.indexes["num_threads"]])
    result.ctime = int(args[self.indexes["ctime"]])
    self.processes.append(result)


class RekallPsListParser(parsers.RekallPluginParser):
  """Parser for Rekall PsList results."""

  output_types = ["Process"]
  supported_artifacts = ["RekallPsList"]

  process_together = True

  def ParseMultiple(self, results, unused_knowledge_base):
    """Parse the key pslist plugin output."""
    s = session.Session()
    plugin = s.plugins.json_render()

    pslist_renderer = PslistParsingRenderer(session=s)
    with pslist_renderer.start():
      for response in results:
        for json_message in json.loads(response.json_messages):
          plugin.RenderStatement(json_message, pslist_renderer)

    for p in pslist_renderer.processes:
      yield p


class VADParsingRenderer(renderer.BaseRenderer):
  """A renderer that parses responses of the vad plugin."""

  def __init__(self, *args, **kw):
    super(VADParsingRenderer, self).__init__(*args, **kw)
    self.binaries = set()

  def section(self, *args, **kw):
    pass

  def table_header(self, *args, **kw):
    try:
      descriptions = [c[1] for c in kw["columns"]]
      self.protection_idx = descriptions.index("protection")
      self.filename_idx = descriptions.index("filename")
    except ValueError:
      raise ValueError("Could not find protection and filename columns.")

  def table_row(self, *args, **kw):
    if not args[self.filename_idx]:
      return

    protection_attr = unicode(args[self.protection_idx])
    if protection_attr in ("EXECUTE_READ",
                           "EXECUTE_READWRITE",
                           "EXECUTE_WRITECOPY"):
      self.binaries.add(args[self.filename_idx])

  def format(self, *args, **kw):
    pass


class RekallVADParser(parsers.RekallPluginParser):
  output_types = ["PathSpec"]
  supported_artifacts = ["FullVADBinaryList"]
  # Required for environment variable expansion
  knowledgebase_dependencies = ["environ_systemdrive", "environ_systemroot"]

  def ParseMultiple(self, results, knowledge_base):
    s = session.Session()
    plugin = s.plugins.json_render()

    vad_renderer = VADParsingRenderer(session=s)
    with vad_renderer.start():
      for response in results:
        for json_message in json.loads(response.json_messages):
          plugin.RenderStatement(json_message, vad_renderer)

    system_drive = artifact_lib.ExpandWindowsEnvironmentVariables(
        "%systemdrive%", knowledge_base)
    for path in vad_renderer.binaries:
      yield rdfvalue.PathSpec(
          path=system_drive + "\\" + path.lstrip("\\"),
          pathtype=rdfvalue.PathSpec.PathType.OS)
