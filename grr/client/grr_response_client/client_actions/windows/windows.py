#!/usr/bin/env python
"""Windows specific actions.

Most of these actions share an interface (in/out rdfvalues) with linux actions
of the same name. Windows-only actions are registered with the server via
libs/server_stubs.py
"""

import binascii
import itertools
import logging
import os
import subprocess
import time
import winreg

import pythoncom
import win32api
import win32com.client
import win32file
import win32service
import win32serviceutil
import wmi

from grr_response_client import actions
from grr_response_client.client_actions import standard
from grr_response_client.client_actions import tempfiles
from grr_response_core.lib import rdfvalue
from grr_response_core.lib.rdfvalues import client_action as rdf_client_action
from grr_response_core.lib.rdfvalues import client_fs as rdf_client_fs
from grr_response_core.lib.rdfvalues import client_network as rdf_client_network
from grr_response_core.lib.rdfvalues import protodict as rdf_protodict


# Properties to remove from results sent to the server.
# These properties are included with nearly every WMI object and use space.
IGNORE_PROPS = [
    "CSCreationClassName",
    "CreationClassName",
    "OSName",
    "OSCreationClassName",
    "WindowsVersion",
    "CSName",
    "__NAMESPACE",
    "__SERVER",
    "__PATH",
    "__RELPATH",
    "__PROPERTY_COUNT",
    "__DERIVATION",
    "__CLASS",
    "__SUPERCLASS",
    "__GENUS",
    "__DYNASTY",
]


class GetInstallDate(actions.ActionPlugin):
  """Estimate the install date of this system."""

  out_rdfvalues = [rdf_protodict.DataBlob]

  def Run(self, unused_args):
    """Estimate the install date of this system."""
    # Don't use winreg.KEY_WOW64_64KEY since it breaks on Windows 2000
    subkey = winreg.OpenKey(
        winreg.HKEY_LOCAL_MACHINE,
        "Software\\Microsoft\\Windows NT\\CurrentVersion",
        0,
        winreg.KEY_READ,
    )
    install_date = winreg.QueryValueEx(subkey, "InstallDate")
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
  for interface in wmi.WMI().Win32_NetworkAdapterConfiguration() or []:
    addresses = []
    for ip_address in interface.IPAddress or []:
      addresses.append(
          rdf_client_network.NetworkAddress(human_readable_address=ip_address)
      )

    response = rdf_client_network.Interface(ifname=interface.Description)
    if interface.MACAddress:
      response.mac_address = binascii.unhexlify(
          interface.MACAddress.replace(":", "")
      )
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
        device=volume, mount_point="/%s:/" % drive[0], type=fs_type, label=label
    )


class EnumerateFilesystems(actions.ActionPlugin):
  """Enumerate all unique filesystems local to the system."""

  out_rdfvalues = [rdf_client_fs.Filesystem]

  def Run(self, args):
    for res in EnumerateFilesystemsFromClient(args):
      self.SendReply(res)


def QueryService(svc_name):
  """Query service and get its config."""
  hscm = win32service.OpenSCManager(
      None, None, win32service.SC_MANAGER_ALL_ACCESS
  )
  result = None
  try:
    hs = win32serviceutil.SmartOpenService(
        hscm, svc_name, win32service.SERVICE_ALL_ACCESS
    )
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
    raise RuntimeError(
        "Failed to run WMI query '%s' err was %s" % (query, e)
    ) from e

  # Extract results from the returned COMObject and return dicts.
  try:
    for result in query_results:
      response = rdf_protodict.Dict()
      prop_iter = itertools.chain(
          result.Properties_,
          getattr(result, "SystemProperties_", []),
      )
      for prop in prop_iter:
        if prop.Name in IGNORE_PROPS:
          continue
        # Protodict can handle most of the types we care about, but we may
        # get some objects that we don't know how to serialize, so we tell the
        # dict to set the value to an error message and keep going
        response.SetItem(prop.Name, prop.Value, raise_on_error=False)
      yield response

  except pythoncom.com_error as e:
    raise RuntimeError(
        "WMI query data error on query '%s' err was %s" % (e, query)
    ) from e


class UpdateAgent(standard.ExecuteBinaryCommand):
  """Updates the GRR agent to a new version."""

  def ProcessFile(self, path, args):
    if path.endswith(".msi"):
      self._InstallMsi(path)
    else:
      raise ValueError(f"Unknown suffix for file {path}.")

  def _InstallMsi(self, path: bytes):
    # misexec won't log to stdout/stderr. Write to a log file insetad.
    with tempfiles.CreateGRRTempFile(filename="GRRInstallLog.txt") as f:
      log_path = f.name

    try:
      start = time.monotonic()
      cmd = ["msiexec", "/i", path, "/qn", "/l*", log_path]
      # Detach from process group and console session to help ensure the child
      # process won't die when the parent process dies.
      creationflags = (
          subprocess.DETACHED_PROCESS | subprocess.CREATE_NEW_PROCESS_GROUP
      )
      p = subprocess.run(cmd, check=False, creationflags=creationflags)

      with open(log_path, "rb") as f:
        # Limit output to fit within 2MiB fleetspeak message limit.
        msiexec_log_output = f.read(512 * 1024)
    finally:
      os.remove(log_path)
    logging.error("Installer ran, but the old GRR client is still running")

    self.SendReply(
        rdf_client_action.ExecuteBinaryResponse(
            stdout=b"",
            stderr=msiexec_log_output,
            exit_status=p.returncode,
            # We have to return microseconds.
            time_used=int(1e6 * time.monotonic() - start),
        )
    )
