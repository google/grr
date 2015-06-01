#!/usr/bin/env python
"""AFF4 object representing network data."""


from grr.lib import aff4
from grr.lib.aff4_objects import collections
from grr.lib.rdfvalues import client as rdf_client


class Network(collections.AFF4Collection):
  """A class abstracting Network information on the client."""

  class SchemaCls(collections.AFF4Collection.SchemaCls):
    """Schema of the network object."""

    INTERFACES = aff4.Attribute("aff4:interfaces", rdf_client.Interfaces,
                                "Network interfaces.", "Interfaces")

    CONNECTIONS = aff4.Attribute("aff4:connections",
                                 rdf_client.Connections,
                                 "Network Connections", "Connections")
