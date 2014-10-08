#!/usr/bin/env python
# Copyright 2010 Google Inc. All Rights Reserved.
"""Windows specific actions."""


import binascii
import ctypes
import exceptions
import logging
import os
import struct
import tempfile
import _winreg

import pythoncom
import pywintypes
import win32api
import win32com.client
import win32file
import win32service
import win32serviceutil
import winerror
import wmi

from grr.client import actions
from grr.client.client_actions import standard

from grr.lib import config_lib
from grr.lib import constants
from grr.lib import rdfvalue


# Properties to remove from results sent to the server.
# These properties are included with nearly every WMI object and use space.
IGNORE_PROPS = ["CSCreationClassName", "CreationClassName", "OSName",
                "OSCreationClassName", "WindowsVersion", "CSName"]

DRIVER_MAX_SIZE = 1024 * 1024 * 20  # 20MB


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
  out_rdfvalue = rdfvalue.DataBlob

  def Run(self, unused_args):
    """Estimate the install date of this system."""
    # Don't use _winreg.KEY_WOW64_64KEY since it breaks on Windows 2000
    subkey = _winreg.OpenKey(
        _winreg.HKEY_LOCAL_MACHINE,
        "Software\\Microsoft\\Windows NT\\CurrentVersion",
        0, _winreg.KEY_READ)
    install_date = _winreg.QueryValueEx(subkey, "InstallDate")
    self.SendReply(integer=install_date[0])


class EnumerateUsers(actions.ActionPlugin):
  """Enumerates all the users on this system."""
  out_rdfvalue = rdfvalue.User

  def GetUsersAndHomeDirs(self):
    """Gets the home directory from the registry for all users on the system.

    Returns:
      A list of tuples containing (username, sid, homedirectory) for each user.
    """

    profiles_key = r"SOFTWARE\Microsoft\Windows NT\CurrentVersion\ProfileList"
    results = []

    try:
      # Don't use _winreg.KEY_WOW64_64KEY since it breaks on Windows 2000
      user_key = _winreg.OpenKey(
          _winreg.HKEY_LOCAL_MACHINE, profiles_key, 0,
          _winreg.KEY_ENUMERATE_SUB_KEYS)
      try:
        index = 0
        while True:
          sid = _winreg.EnumKey(user_key, index)
          index += 1

          # Don't use _winreg.KEY_WOW64_64KEY since it breaks on Windows 2000
          homedir_key = _winreg.OpenKey(
              _winreg.HKEY_LOCAL_MACHINE, profiles_key + "\\" + sid, 0,
              _winreg.KEY_QUERY_VALUE)

          (homedir, _) = _winreg.QueryValueEx(homedir_key, "ProfileImagePath")

          username = os.path.basename(homedir)
          results.append((username, sid, homedir))

          _winreg.CloseKey(homedir_key)

      except exceptions.WindowsError:
        # No more values.
        pass

      _winreg.CloseKey(user_key)

    except exceptions.WindowsError:
      logging.error("Could not enumerate users.")

    return results

  def GetSpecialFolders(self, sid):
    """Retrieves all the special folders from the registry."""
    folders_key = (r"%s\Software\Microsoft\Windows"
                   r"\CurrentVersion\Explorer\Shell Folders")
    try:
      key = _winreg.OpenKey(_winreg.HKEY_USERS, folders_key % sid)
    except exceptions.WindowsError:
      # For users that are not logged in this key will not exist. If we return
      # None here, they will be guessed for now.
      return

    response = {}

    for (reg_key, _, pb_field) in self.special_folders:
      try:
        (folder, _) = _winreg.QueryValueEx(key, reg_key)
        if folder:
          response[pb_field] = folder
      except exceptions.WindowsError:
        pass
    return rdfvalue.FolderInformation(**response)

  def GetWMIAccount(self, result, sid, homedir, known_sids):

    if result["SID"] not in known_sids:
      # There could be a user in another domain with the same name,
      # we just ignore this.
      return None

    response = {"username": result["Name"],
                "domain": result["Domain"],
                "sid": result["SID"],
                "homedir": homedir}

    profile_folders = self.GetSpecialFolders(sid)
    if not profile_folders:
      # TODO(user): The user's registry file is not mounted. The right
      # way would be to open the ntuser.dat and parse the keys from there
      # but we don't have registry file reading capability yet. For now,
      # we just try to guess the folders.
      folders_found = {}
      for (_, folder, field) in self.special_folders:
        path = os.path.join(homedir, folder)
        try:
          os.stat(path)
          folders_found[field] = path
        except exceptions.WindowsError:
          pass
      profile_folders = rdfvalue.FolderInformation(**folders_found)

    response["special_folders"] = profile_folders
    return response

  def Run(self, unused_args):
    """Enumerate all users on this machine."""

    self.special_folders = constants.profile_folders
    homedirs = self.GetUsersAndHomeDirs()
    known_sids = [sid for (_, sid, _) in homedirs]

    for (user, sid, homedir) in homedirs:
      # This query determines if the sid corresponds to a real user account.
      for result in RunWMIQuery("SELECT * FROM Win32_UserAccount "
                                "WHERE name=\"%s\"" % user):
        response = self.GetWMIAccount(result, sid, homedir, known_sids)
        if response:
          self.SendReply(**response)


class EnumerateInterfaces(actions.ActionPlugin):
  """Enumerate all MAC addresses of all NICs.

  Win32_NetworkAdapterConfiguration definition:
    http://msdn.microsoft.com/en-us/library/aa394217(v=vs.85).aspx
  """
  out_rdfvalue = rdfvalue.Interface

  def RunNetAdapterWMIQuery(self):
    pythoncom.CoInitialize()
    for interface in wmi.WMI().Win32_NetworkAdapterConfiguration(IPEnabled=1):
      addresses = []
      for ip_address in interface.IPAddress:
        addresses.append(rdfvalue.NetworkAddress(
            human_readable_address=ip_address))

      args = {"ifname": interface.Description}
      args["mac_address"] = binascii.unhexlify(
          interface.MACAddress.replace(":", ""))
      if addresses:
        args["addresses"] = addresses

      yield args

  def Run(self, unused_args):
    """Enumerate all MAC addresses."""
    for interface_dict in self.RunNetAdapterWMIQuery():
      self.SendReply(**interface_dict)


class EnumerateFilesystems(actions.ActionPlugin):
  """Enumerate all unique filesystems local to the system."""
  out_rdfvalue = rdfvalue.Filesystem

  def Run(self, unused_args):
    """List all local filesystems mounted on this system."""
    for drive in win32api.GetLogicalDriveStrings().split("\x00"):
      if drive:
        try:
          volume = win32file.GetVolumeNameForVolumeMountPoint(
              drive).rstrip("\\")

          label, _, _, _, fs_type = win32api.GetVolumeInformation(drive)
          self.SendReply(device=volume,
                         mount_point="/%s:/" % drive[0],
                         type=fs_type, label=UnicodeFromCodePage(label))
        except win32api.error:
          pass


class Uninstall(actions.ActionPlugin):
  """Remove the service that starts us at startup."""
  out_rdfvalue = rdfvalue.DataBlob

  def Run(self, unused_arg):
    """This kills us with no cleanups."""
    logging.debug("Disabling service")

    win32serviceutil.ChangeServiceConfig(
        None, config_lib.CONFIG["Nanny.service_name"],
        startType=win32service.SERVICE_DISABLED)
    svc_config = QueryService(config_lib.CONFIG["Nanny.service_name"])
    if svc_config[1] == win32service.SERVICE_DISABLED:
      logging.info("Disabled service successfully")
      self.SendReply(string="Service disabled.")
    else:
      self.SendReply(string="Service failed to disable.")


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


class WmiQuery(actions.ActionPlugin):
  """Runs a WMI query and returns the results to a server callback."""
  in_rdfvalue = rdfvalue.WMIRequest
  out_rdfvalue = rdfvalue.Dict

  def Run(self, args):
    """Run the WMI query and return the data."""
    query = args.query
    base_object = args.base_object or r"winmgmts:\root\cimv2"

    if not query.upper().startswith("SELECT "):
      raise RuntimeError("Only SELECT WMI queries allowed.")

    for response_dict in RunWMIQuery(query, baseobj=base_object):
      self.SendReply(response_dict)


def RunWMIQuery(query, baseobj=r"winmgmts:\root\cimv2"):
  """Run a WMI query and return a result.

  Args:
    query: the WMI query to run.
    baseobj: the base object for the WMI query.

  Yields:
    rdfvalue.Dicts containing key value pairs from the resulting COM objects.
  """
  pythoncom.CoInitialize()   # Needs to be called if using com from a thread.
  wmi_obj = win32com.client.GetObject(baseobj)
  # This allows our WMI to do some extra things, in particular
  # it gives it access to find the executable path for all processes.
  wmi_obj.Security_.Privileges.AddAsString("SeDebugPrivilege")

  # Run query
  try:
    query_results = wmi_obj.ExecQuery(query)
  except pythoncom.com_error as e:
    raise RuntimeError("Failed to run WMI query \'%s\' err was %s" %
                       (query, e))

  # Extract results from the returned COMObject and return dicts.
  try:
    for result in query_results:
      response = rdfvalue.Dict()
      for prop in result.Properties_:
        if prop.Name not in IGNORE_PROPS:
          # Protodict can handle most of the types we care about, but we may
          # get some objects that we don't know how to serialize, so we tell the
          # dict to set the value to an error message and keep going
          response.SetItem(prop.Name, prop.Value, raise_on_error=False)
      yield response

  except pythoncom.com_error as e:
    raise RuntimeError("WMI query data error on query \'%s\' err was %s" %
                       (e, query))


def CtlCode(device_type, function, method, access):
  """Prepare an IO control code."""
  return (device_type<<16) | (access << 14) | (function << 2) | method


# IOCTLS for interacting with the driver.
INFO_IOCTRL = CtlCode(0x22, 0x100, 0, 3)  # Get information.
CTRL_IOCTRL = CtlCode(0x22, 0x101, 0, 3)  # Set acquisition modes.


class GetMemoryInformation(actions.ActionPlugin):
  """Loads the driver for memory access and returns a Stat for the device."""

  in_rdfvalue = rdfvalue.PathSpec
  out_rdfvalue = rdfvalue.MemoryInformation

  def Run(self, args):
    """Run."""
    # This action might crash the box so we need to flush the transaction log.
    self.SyncTransactionLog()

    # Do any initialization we need to do.
    logging.debug("Querying device %s", args.path)

    fd = win32file.CreateFile(
        args.path,
        win32file.GENERIC_READ | win32file.GENERIC_WRITE,
        win32file.FILE_SHARE_READ | win32file.FILE_SHARE_WRITE,
        None,
        win32file.OPEN_EXISTING,
        win32file.FILE_ATTRIBUTE_NORMAL,
        None)

    data = win32file.DeviceIoControl(fd, INFO_IOCTRL, "", 1024, None)
    fmt_string = "QQl"
    cr3, _, number_of_runs = struct.unpack_from(fmt_string, data)

    result = rdfvalue.MemoryInformation(
        cr3=cr3,
        device=rdfvalue.PathSpec(
            path=args.path,
            pathtype=rdfvalue.PathSpec.PathType.MEMORY))

    offset = struct.calcsize(fmt_string)
    for x in range(number_of_runs):
      start, length = struct.unpack_from("QQ", data, x * 16 + offset)
      result.runs.Append(offset=start, length=length)

    self.SendReply(result)


class UninstallDriver(actions.ActionPlugin):
  """Unloads and deletes a memory driver.

  Note that only drivers with a signature that validates with
  Client.driver_signing_public_key can be uninstalled.
  """

  in_rdfvalue = rdfvalue.DriverInstallTemplate

  @staticmethod
  def UninstallDriver(driver_path, service_name, delete_file=False):
    """Unloads the driver and delete the driver file.

    Args:
      driver_path: Full path name to the driver file.
      service_name: Name of the service the driver is loaded as.
      delete_file: Should we delete the driver file after removing the service.

    Raises:
      OSError: On failure to uninstall or delete.
    """

    try:
      win32serviceutil.StopService(service_name)
    except pywintypes.error as e:
      if e[0] not in [winerror.ERROR_SERVICE_NOT_ACTIVE,
                      winerror.ERROR_SERVICE_DOES_NOT_EXIST]:
        raise OSError("Could not stop service: {0}".format(e))

    try:
      win32serviceutil.RemoveService(service_name)
    except pywintypes.error as e:
      if e[0] != winerror.ERROR_SERVICE_DOES_NOT_EXIST:
        raise OSError("Could not remove service: {0}".format(e))

    if delete_file:
      try:
        if os.path.exists(driver_path):
          os.remove(driver_path)
      except (OSError, IOError) as e:
        raise OSError("Driver deletion failed: " + str(e))

  def Run(self, args):
    """Unloads a driver."""
    # This is kind of lame because we dont really check the driver is
    # the same as the one that we are going to uninstall.
    args.driver.Verify(config_lib.CONFIG["Client.driver_signing_public_key"])

    self.UninstallDriver(driver_path=None, service_name=args.driver_name,
                         delete_file=False)


class InstallDriver(UninstallDriver):
  """Installs a driver.

  Note that only drivers with a signature that validates with
  Client.driver_signing_public_key can be loaded.
  """
  in_rdfvalue = rdfvalue.DriverInstallTemplate

  @staticmethod
  def InstallDriver(driver_path, service_name, driver_display_name):
    """Loads a driver and start it."""
    hscm = win32service.OpenSCManager(None, None,
                                      win32service.SC_MANAGER_ALL_ACCESS)
    try:
      win32service.CreateService(hscm,
                                 service_name,
                                 driver_display_name,
                                 win32service.SERVICE_ALL_ACCESS,
                                 win32service.SERVICE_KERNEL_DRIVER,
                                 win32service.SERVICE_DEMAND_START,
                                 win32service.SERVICE_ERROR_IGNORE,
                                 driver_path,
                                 None,  # No load ordering
                                 0,     # No Tag identifier
                                 None,  # Service deps
                                 None,  # User name
                                 None)  # Password
      win32serviceutil.StartService(service_name)
    except pywintypes.error as e:
      # The following errors are expected:
      if e[0] not in [winerror.ERROR_SERVICE_EXISTS,
                      winerror.ERROR_SERVICE_MARKED_FOR_DELETE]:
        raise RuntimeError("StartService failure: {0}".format(e))

  def Run(self, args):
    """Initializes the driver."""
    self.SyncTransactionLog()

    # This will raise if the signature is bad.
    args.driver.Verify(config_lib.CONFIG["Client.driver_signing_public_key"])

    if args.force_reload:
      try:
        self.UninstallDriver(None, args.driver_name, delete_file=False)
      except Exception as e:  # pylint: disable=broad-except
        logging.debug("Error uninstalling driver: %s", e)

    path_handle, path_name = tempfile.mkstemp(suffix=".sys")
    try:
      # TODO(user): Ensure we have lock here, no races
      logging.info("Writing driver to %s", path_name)

      # Note permissions default to global read, user only write.
      try:
        os.write(path_handle, args.driver.data)
      finally:
        os.close(path_handle)

      self.InstallDriver(path_name, args.driver_name, args.driver_display_name)

    finally:
      os.unlink(path_name)


class UpdateAgent(standard.ExecuteBinaryCommand):
  """Updates the GRR agent to a new version."""

  # For Windows this is just an alias to ExecuteBinaryCommand.

  suffix = "exe"
