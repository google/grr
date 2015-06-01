#!/usr/bin/env python
"""AFF4 objects for managing Rekall responses."""

from grr.lib.aff4_objects import collections
from grr.lib.rdfvalues import rekall_types as rdf_rekall_types


class RekallResponseCollection(collections.RDFValueCollection):
  """A collection of Rekall results."""
  _rdf_type = rdf_rekall_types.RekallResponse

  renderer = "GRRRekallRenderer"
