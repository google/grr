#!/usr/bin/env python
"""Simple parsers for the output of WMI queries."""


from grr.lib import parsers
from grr.lib import rdfvalue


class WMIInstalledSoftwareParser(parsers.WMIQueryParser):
  """Parser for WMI output. Yields SoftwarePackage rdfvalues."""

  output_types = ["SoftwarePackage"]
  supported_artifacts = ["WindowsWMIInstalledSoftware"]

  def Parse(self, query, result, knowledge_base):
    """Parse the wmi packages output."""
    _ = query, knowledge_base
    status = rdfvalue.SoftwarePackage.InstallState.INSTALLED
    soft = rdfvalue.SoftwarePackage(
        name=result["Name"],
        description=result["Description"],
        version=result["Version"],
        install_state=status)

    yield soft
