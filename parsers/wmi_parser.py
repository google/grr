#!/usr/bin/env python
"""Simple parsers for the output of WMI queries."""

from grr.lib import parsers
from grr.lib import rdfvalue
from grr.lib import time_utils


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


class WMIHotfixesSoftwareParser(parsers.WMIQueryParser):
  """Parser for WMI output. Yields SoftwarePackage rdfvalues."""

  output_types = ["SoftwarePackage"]
  supported_artifacts = ["WindowsHotFixes"]

  def Parse(self, query, result, knowledge_base):
    """Parse the wmi packages output."""
    _ = query, knowledge_base
    status = rdfvalue.SoftwarePackage.InstallState.INSTALLED
    result = result.ToDict()

    # InstalledOn comes back in a godawful format such as '7/10/2013'.
    installed_on = time_utils.AmericanDateToEpoch(result.get("InstalledOn", ""))
    soft = rdfvalue.SoftwarePackage(
        name=result.get("HotFixID"),
        description=result.get("Caption"),
        installed_by=result.get("InstalledBy"),
        install_state=status,
        installed_on=installed_on)
    yield soft


class WMIUserAccountParser(parsers.WMIQueryParser):
  """Parser for WMI Win32_UserAccount output."""

  output_types = ["KnowledgeBaseUser"]
  supported_artifacts = ["WindowsWMIProfileUsers"]

  account_mapping = {
      "Name": "username",
      "Domain": "userdomain",
      "SID": "sid"
      }

  def Parse(self, query, result, knowledge_base):
    """Parse the wmi Win32_UserAccount output."""
    _ = query, knowledge_base
    kb_user = rdfvalue.KnowledgeBaseUser()
    for wmi_key, kb_key in self.account_mapping.items():
      try:
        kb_user.Set(kb_key, result[wmi_key])
      except KeyError:
        pass
    yield kb_user
