#!/usr/bin/env python
"""AFF4 stats objects."""
from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

from grr_response_core.lib.rdfvalues import client_stats as rdf_client_stats
from grr_response_core.lib.rdfvalues import stats as rdf_stats
from grr_response_server import aff4
from grr_response_server.aff4_objects import standard


class ClientStats(standard.VFSDirectory):
  """A container for all client statistics."""

  class SchemaCls(standard.VFSDirectory.SchemaCls):
    STATS = aff4.Attribute(
        "aff4:stats",
        rdf_client_stats.ClientStats,
        "Client Stats.",
        "Client stats",
        creates_new_object_version=False)


class ClientFleetStats(aff4.AFF4Object):
  """AFF4 object for storing client statistics."""

  class SchemaCls(aff4.AFF4Object.SchemaCls):
    """Schema for ClientFleetStats object."""

    GRRVERSION_HISTOGRAM = aff4.Attribute(
        "aff4:stats/grrversion", rdf_stats.GraphSeries,
        "GRR version statistics for active "
        "clients.")

    OS_HISTOGRAM = aff4.Attribute(
        "aff4:stats/os_type", rdf_stats.GraphSeries,
        "Operating System statistics for active clients.")

    RELEASE_HISTOGRAM = aff4.Attribute(
        "aff4:stats/release", rdf_stats.GraphSeries,
        "Release statistics for active clients.")

    LAST_CONTACTED_HISTOGRAM = aff4.Attribute(
        "aff4:stats/last_contacted", rdf_stats.Graph, "Last contacted time")
