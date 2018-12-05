#!/usr/bin/env python
"""Windows specific actions.

Most of these actions share an interface (in/out rdfvalues) with linux actions
of the same name. Windows-only actions are registered with the server via
libs/server_stubs.py
"""
from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

import binascii
import ctypes
import logging
import _winreg

import pythoncom
import win32api
import win32com.client
import win32file
import win32service
import win32serviceutil
import wmi

from grr_response_client import actions
from grr_response_client.client_actions import standard

from grr_response_core import config
from grr_response_core.lib import rdfvalue
from grr_response_core.lib.rdfvalues import client_action as rdf_client_action
from grr_response_core.lib.rdfvalues import client_fs as rdf_client_fs
from grr_response_core.lib.rdfvalues import client_network as rdf_client_network
from grr_response_core.lib.rdfvalues import protodict as rdf_protodict

# Properties to remove from results sent to the server.
# These properties are included with nearly every WMI object and use space.
IGNORE_PROPS = [
    "CSCreationClassName", "CreationClassName", "OSName", "OSCreationClassName",
    "WindowsVersion", "CSName", "__NAMESPACE", "__SERVER", "__PATH"
]


def UnicodeFromCodePage(string):
  """Attempt to coerce string into a unicode object."""
  # get the current code page
  codepage = ctypes.windll.kernel32.GetOEMCP()
  try:
    return string.decode("cp%s" % codepage)
  except UnicodeError:
    try:
      return string.decode("utf16", "ignore")
    except UnicodeError:
      # Fall back on utf8 but ignore errors
      return string.decode("utf8", "ignore")


class GetInstallDate(actions.ActionPlugin):
  """Estimate the install date of this system."""
  out_rdfvalues = [rdf_protodict.DataBlob]

  def Run(self, unused_args):
    """Estimate the install date of this system."""
    # Don't use _winreg.KEY_WOW64_64KEY since it breaks on Windows 2000
    subkey = _winreg.OpenKey(_winreg.HKEY_LOCAL_MACHINE,
                             "Software\\Microsoft\\Windows NT\\CurrentVersion",
                             0, _winreg.KEY_READ)
    install_date = _winreg.QueryValueEx(subkey, "InstallDate")
    self.SendReply(rdfvalue.RDFDatetime.FromSecondsSinceEpoch(install_date[0]))


def EnumerateInterfacesFromClient(args):
  """Enumerate all MAC addresses of all NICs.

  Args:
    args: Unused.

  Yields:
    `rdf_client_network.Interface` instances.
  """
  del args  # Unused.

  pythoncom.CoInitialize()
  for interface in (wmi.WMI().Win32_NetworkAdapterConfiguration() or []):
    addresses = []
    for ip_address in interface.IPAddress or []:
      addresses.append(
          rdf_client_network.NetworkAddress(human_readable_address=ip_address))

    response = rdf_client_network.Interface(ifname=interface.Description)
    if interface.MACAddress:
      response.mac_address = binascii.unhexlify(
          interface.MACAddress.replace(":", ""))
    if addresses:
      response.addresses = addresses

    yield response


class EnumerateInterfaces(actions.ActionPlugin):
  """Enumerate all MAC addresses of all NICs.

  Win32_NetworkAdapterConfiguration definition:
    http://msdn.microsoft.com/en-us/library/aa394217(v=vs.85).aspx
  """
  out_rdfvalues = [rdf_client_network.Interface]

  def Run(self, args):
    for res in EnumerateInterfacesFromClient(args):
      self.SendReply(res)


def EnumerateFilesystemsFromClient(args):
  """List all local filesystems mounted on this system."""
  del args  # Unused.
  for drive in win32api.GetLogicalDriveStrings().split("\x00"):
    if not drive:
      continue
    try:
      volume = win32file.GetVolumeNameForVolumeMountPoint(drive).rstrip("\\")

      label, _, _, _, fs_type = win32api.GetVolumeInformation(drive)
    except win32api.error:
      continue
    yield rdf_client_fs.Filesystem(
        device=volume,
        mount_point="/%s:/" % drive[0],
        type=fs_type,
        label=UnicodeFromCodePage(label))


class EnumerateFilesystems(actions.ActionPlugin):
  """Enumerate all unique filesystems local to the system."""
  out_rdfvalues = [rdf_client_fs.Filesystem]

  def Run(self, args):
    for res in EnumerateFilesystemsFromClient(args):
      self.SendReply(res)


class Uninstall(actions.ActionPlugin):
  """Remove the service that starts us at startup."""
  out_rdfvalues = [rdf_protodict.DataBlob]

  def Run(self, unused_arg):
    """This kills us with no cleanups."""
    logging.debug("Disabling service")

    win32serviceutil.ChangeServiceConfig(
        None,
        config.CONFIG["Nanny.service_name"],
        startType=win32service.SERVICE_DISABLED)
    svc_config = QueryService(config.CONFIG["Nanny.service_name"])
    if svc_config[1] == win32service.SERVICE_DISABLED:
      logging.info("Disabled service successfully")
      self.SendReply(rdf_protodict.DataBlob(string="Service disabled."))
    else:
      self.SendReply(
          rdf_protodict.DataBlob(string="Service failed to disable."))


def QueryService(svc_name):
  """Query service and get its config."""
  hscm = win32service.OpenSCManager(None, None,
                                    win32service.SC_MANAGER_ALL_ACCESS)
  result = None
  try:
    hs = win32serviceutil.SmartOpenService(hscm, svc_name,
                                           win32service.SERVICE_ALL_ACCESS)
    result = win32service.QueryServiceConfig(hs)
    win32service.CloseServiceHandle(hs)
  finally:
    win32service.CloseServiceHandle(hscm)

  return result


def WmiQueryFromClient(args):
  """Run the WMI query and return the data."""
  query = args.query
  base_object = args.base_object or r"winmgmts:\root\cimv2"

  if not query.upper().startswith("SELECT "):
    raise RuntimeError("Only SELECT WMI queries allowed.")

  for response_dict in RunWMIQuery(query, baseobj=base_object):
    yield response_dict


class WmiQuery(actions.ActionPlugin):
  """Runs a WMI query and returns the results to a server callback."""
  in_rdfvalue = rdf_client_action.WMIRequest
  out_rdfvalues = [rdf_protodict.Dict]

  def Run(self, args):
    for res in WmiQueryFromClient(args):
      self.SendReply(res)


def RunWMIQuery(query, baseobj=r"winmgmts:\root\cimv2"):
  """Run a WMI query and return a result.

  Args:
    query: the WMI query to run.
    baseobj: the base object for the WMI query.

  Yields:
    rdf_protodict.Dicts containing key value pairs from the resulting COM
    objects.
  """
  pythoncom.CoInitialize()  # Needs to be called if using com from a thread.
  wmi_obj = win32com.client.GetObject(baseobj)
  # This allows our WMI to do some extra things, in particular
  # it gives it access to find the executable path for all processes.
  wmi_obj.Security_.Privileges.AddAsString("SeDebugPrivilege")

  # Run query
  try:
    query_results = wmi_obj.ExecQuery(query)
  except pythoncom.com_error as e:
    raise RuntimeError("Failed to run WMI query \'%s\' err was %s" % (query, e))

  # Extract results from the returned COMObject and return dicts.
  try:
    for result in query_results:
      response = rdf_protodict.Dict()
      properties = (
          list(result.Properties_) +
          list(getattr(result, "SystemProperties_", [])))

      for prop in properties:
        if prop.Name not in IGNORE_PROPS:
          # Protodict can handle most of the types we care about, but we may
          # get some objects that we don't know how to serialize, so we tell the
          # dict to set the value to an error message and keep going
          response.SetItem(prop.Name, prop.Value, raise_on_error=False)
      yield response

  except pythoncom.com_error as e:
    raise RuntimeError("WMI query data error on query \'%s\' err was %s" %
                       (e, query))


class UpdateAgent(standard.ExecuteBinaryCommand):
  """Updates the GRR agent to a new version."""

  # For Windows this is just an alias to ExecuteBinaryCommand.
