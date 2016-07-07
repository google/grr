#!/usr/bin/env python
"""AFF4 objects for managing Chipsec responses."""

from grr.client.components.chipsec_support.actions import chipsec_types

from grr.lib.aff4_objects import collects


class ACPITableDataCollection(collects.RDFValueCollection):
  """A collection of ACPI table data."""
  _rdf_type = chipsec_types.ACPITableData
