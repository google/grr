#!/usr/bin/env python
# Copyright 2011 Google Inc. All Rights Reserved.
"""AFF4 object representing processes."""


from grr.lib import aff4
from grr.lib import rdfvalue
from grr.lib.aff4_objects import standard


class Process(aff4.AFF4Image):
  """A class abstracting a Process on the client."""

  class SchemaCls(aff4.AFF4Image.SchemaCls):
    """We try to break down all the fields we are likely to search on."""
    PID = aff4.Attribute("aff4:process/pid", rdfvalue.RDFInteger,
                         "The process ID.", "pid")

    PPID = aff4.Attribute("aff4:process/ppid", rdfvalue.RDFInteger,
                          "The parent process ID.", "ppid")

    CMDLINE = aff4.Attribute("aff4:process/cmdline", rdfvalue.RDFString,
                             "Process command line.", "cmdline")

    EXE = aff4.Attribute("aff4:process/exe", rdfvalue.RDFString,
                         "Process Executable Path.", "exe")

    CREATED = aff4.Attribute("aff4:process/ctime", rdfvalue.RDFDatetime,
                             "Process creation time.", "created")


class ProcessListing(standard.VFSDirectory):
  """A container for all process listings."""

  _behaviours = frozenset()

  class SchemaCls(standard.VFSDirectory.SchemaCls):
    PROCESSES = aff4.Attribute("aff4:processes", rdfvalue.Processes,
                               "Process Listing.", default=rdfvalue.Processes())

  def ListChildren(self):
    """Virtualizes all processes as children."""
    result = {}
    processes = self.Get(self.Schema.PROCESSES)
    for process in processes:
      result[self.urn.Add(str(process.pid))] = "Process"

    return result, self.urn.age

  def Open(self, urn, mode="r"):
    """Opens a direct child of this object."""
    if not isinstance(urn, rdfvalue.RDFURN):
      # Interpret as a relative path.
      urn = self.urn.Add(urn)

    components = urn.RelativeName(self.urn).split("/")
    if len(components) > 1 or not components[0].isnumeric():
      raise IOError("Component %s not found." % components[0])

    pid = int(components[0])
    processes = self.Get(self.Schema.PROCESSES) or []
    for process in processes:
      if pid == process.pid:
        result = Process(self.urn.Add(str(pid)), parent=self, clone={},
                         mode="rw")
        result.Set(result.Schema.PID(process.pid))
        result.Set(result.Schema.PPID(process.ppid))
        result.Set(result.Schema.CMDLINE(" ".join(process.cmdline)))
        result.Set(result.Schema.EXE(process.exe))
        result.Set(result.Schema.CREATED(process.ctime))

        return result

    raise IOError("%s not found" % pid)

  def OpenChildren(self, children=None, mode="r"):
    """Opens the children of this object."""
    if children is None:
      children = self.ListChildren()[0]

    for child in children:
      try:
        yield self.Open(child, mode)
      except IOError:
        pass
