#!/usr/bin/env python
"""AFF4 objects for managing Chipsec responses."""
from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

from grr_response_core.lib.rdfvalues import chipsec_types as rdf_chipsec_types

from grr_response_server import sequential_collection


class ACPITableDataCollection(
    sequential_collection.IndexedSequentialCollection):
  """A collection of ACPI table data."""
  RDF_TYPE = rdf_chipsec_types.ACPITableData
