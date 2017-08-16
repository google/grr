#!/usr/bin/env python
"""AFF4 objects for describing software."""


from grr.lib.rdfvalues import client
from grr.server import aff4


class InstalledSoftwarePackages(aff4.AFF4Object):
  """Models installed software."""

  class SchemaCls(aff4.AFF4Object.SchemaCls):
    INSTALLED_PACKAGES = aff4.Attribute(
        "aff4:info/packages",
        client.SoftwarePackages,
        "Installed software packages.",
        default="")
