#!/usr/bin/env python
# Copyright 2012 Google Inc. All Rights Reserved.
"""AFF4 object representing client stats."""


from grr.lib import aff4
from grr.lib import rdfvalue
from grr.lib.aff4_objects import standard


class ClientStats(standard.VFSDirectory):
  """A container for all client statistics."""

  class SchemaCls(standard.VFSDirectory.SchemaCls):
    STATS = aff4.Attribute("aff4:stats", rdfvalue.ClientStats,
                           "Client Stats.", "Client stats")
