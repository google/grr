#!/usr/bin/env python
"""AFF4 object representing processes."""


from grr.lib import aff4
from grr.lib import rdfvalue
from grr.lib.aff4_objects import collections


class ProcessListing(collections.AFF4Collection):
  """A container for all process listings."""

  class SchemaCls(collections.AFF4Collection.SchemaCls):
    PROCESSES = aff4.Attribute("aff4:processes", rdfvalue.Processes,
                               "Process Listing.", default=rdfvalue.Processes())
