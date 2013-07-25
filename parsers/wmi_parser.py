#!/usr/bin/env python
"""Simple parsers for the output of WMI queries."""


from grr.lib import parsers
from grr.lib import rdfvalue


class WMIInstalledSoftwareParser(parsers.WMIQueryParser):
  """Parser for WMI output. Yields SoftwarePackage rdfvalues."""

  out_type = "SoftwarePackage"

  def Parse(self, query, result):
    """Parse the wmi packages output."""
    _ = query
    status = rdfvalue.SoftwarePackage.InstallState.INSTALLED
    soft = rdfvalue.SoftwarePackage(
        name=result["Name"],
        description=result["Description"],
        version=result["Version"],
        install_state=status)

    yield soft
