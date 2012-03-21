#!/usr/bin/env python

# Copyright 2010 Google Inc.
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Windows specific actions."""


import binascii
import ctypes
import exceptions
import hashlib
import logging
import os
import sys
import _winreg

import pythoncom
import win32api
import win32com.client
import win32file
import win32service
import win32serviceutil
import wmi

from grr.client import actions
from grr.client import client_config
from grr.client import client_utils_common
from grr.client import client_utils_windows
from grr.client import comms
from grr.client import conf
from grr.lib import constants
from grr.lib import utils
from grr.proto import jobs_pb2
from grr.proto import sysinfo_pb2

FLAGS = conf.PARSER.flags

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
  out_protobuf = jobs_pb2.DataBlob

  def Run(self, unused_args):
    # We need to turn on 64 bit access as per
    # http://msdn.microsoft.com/en-us/library/aa384129(v=VS.85).aspx
    subkey = _winreg.OpenKey(
        _winreg.HKEY_LOCAL_MACHINE,
        "Software\\Microsoft\\Windows NT\\CurrentVersion",
        0,
        0x100 | _winreg.KEY_READ)
    install_date = _winreg.QueryValueEx(subkey, "InstallDate")
    self.SendReply(integer=install_date[0])


class EnumerateUsers(actions.ActionPlugin):
  """Enumerates all the users on this system."""
  out_protobuf = jobs_pb2.UserAccount

  def GetUsersAndHomeDirs(self):
    """Gets the home directory from the registry for all users on the system.

    Returns:
      A list of tuples containing (username, sid, homedirectory) for each user.
    """

    profiles_key = r"SOFTWARE\Microsoft\Windows NT\CurrentVersion\ProfileList"
    results = []

    try:
      user_key = _winreg.OpenKey(_winreg.HKEY_LOCAL_MACHINE,
                                 profiles_key,
                                 0, _winreg.KEY_WOW64_64KEY |
                                 _winreg.KEY_ENUMERATE_SUB_KEYS)
      try:
        index = 0
        while True:
          sid = _winreg.EnumKey(user_key, index)
          index += 1

          homedir_key = _winreg.OpenKey(_winreg.HKEY_LOCAL_MACHINE,
                                        profiles_key + "\\" + sid,
                                        0, _winreg.KEY_WOW64_64KEY |
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
                   "\CurrentVersion\Explorer\Shell Folders")
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
    return jobs_pb2.FolderInformation(**response)

  def Run(self, unused_args):
    """Enumerate all users on this machine."""

    self.special_folders = constants.profile_folders
    homedirs = self.GetUsersAndHomeDirs()
    known_sids = [sid for (_, sid, _) in homedirs]

    for (user, sid, homedir) in homedirs:

      # This query determines if the sid corresponds to a real user account.
      for acc in RunWMIQuery("SELECT * FROM Win32_UserAccount "
                             "WHERE name=\"%s\"" % user):

        if acc["SID"] not in known_sids:
          # There could be a user in another domain with the same name,
          # we just ignore this.
          continue

        response = {"username": acc["Name"],
                    "domain": acc["Domain"],
                    "sid": acc["SID"],
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
          profile_folders = jobs_pb2.FolderInformation(**folders_found)

        response["special_folders"] = profile_folders

        self.SendReply(**response)


class EnumerateInterfaces(actions.ActionPlugin):
  """Enumerate all MAC addresses of all NICs."""
  out_protobuf = jobs_pb2.Interface

  def Run(self, unused_args):
    """Enumerate all MAC addresses."""

    for interface in wmi.WMI().Win32_NetworkAdapterConfiguration(IPEnabled=1):
      addresses = []
      for ip_address in interface.IPAddress:
        if ":" in ip_address:
          # IPv6
          address_type = jobs_pb2.NetworkAddress.INET6
        else:
          # IPv4
          address_type = jobs_pb2.NetworkAddress.INET

        addresses.append(jobs_pb2.NetworkAddress(human_readable=ip_address,
                                                 address_type=address_type))

      args = {"ifname": interface.Description}
      args["mac_address"] = binascii.unhexlify(
          interface.MACAddress.replace(":", ""))
      if addresses:
        args["addresses"] = addresses
      self.SendReply(**args)


class EnumerateFilesystems(actions.ActionPlugin):
  """Enumerate all unique filesystems local to the system."""
  out_protobuf = sysinfo_pb2.Filesystem

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
  out_protobuf = jobs_pb2.DataBlob

  def Run(self, unused_arg):
    """This kills us with no cleanups."""
    logging.debug("Disabling service")
    if conf.RUNNING_AS_SERVICE:
      # Import here as we only want it if we're running as a service.
      from grr.client import win32grr

      win32serviceutil.ChangeServiceConfig(
          "win32grr.GRRMonitor", client_config.SERVICE_NAME,
          startType=win32service.SERVICE_DISABLED)
      svc_config = QueryService(client_config.SERVICE_NAME)
      if svc_config[1] == win32service.SERVICE_DISABLED:
        logging.info("Disabled service successfully")
        self.SendReply(string="Service disabled.")
      else:
        self.SendReply(string="Service failed to disable.")
    else:
      self.SendReply(string="Not running as service.")


class Kill(actions.ActionPlugin):
  """This ourselves with no cleanups."""
  out_protobuf = jobs_pb2.GrrMessage

  def Run(self, unused_arg):
    """Run the kill."""
    if isinstance(self.grr_context, comms.SlaveContext):
      sys.exit(242)
    else:
      # Kill off children if we are running separated.
      if isinstance(self.grr_context, comms.ProcessSeparatedContext):
        logging.info("Requesting termination of slaves.")
        self.grr_context.Terminate()

      # Send a message back to the service to say that we are about to shutdown.
      reply = jobs_pb2.GrrStatus()
      reply.status = jobs_pb2.GrrStatus.OK
      # Queue up the response message.
      self.SendReply(reply, message_type=jobs_pb2.GrrMessage.STATUS,
                     jump_queue=True)
      # Force a comms run.
      status = self.grr_context.RunOnce()
      if status.code != 200:
        logging.error("Could not communicate our own death, re-death predicted")

      if conf.RUNNING_AS_SERVICE:
        # Terminate service
        win32serviceutil.StopService(client_config.SERVICE_NAME)
      else:
        # Die ourselves.
        logging.info("Dying on request.")
        sys.exit(242)


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
  in_protobuf = jobs_pb2.WmiRequest
  out_protobuf = jobs_pb2.Dict

  def Run(self, args):
    """Run the WMI query and return the data."""
    query = args.query

    # Now return the data to the server
    for response_dict in RunWMIQuery(query):
      response = utils.ProtoDict(response_dict)
      self.SendReply(response.ToProto())


def RunWMIQuery(query, baseobj=r"winmgmts:\root\cimv2"):
  """Run a WMI query and return a result.

  Args:
    query: the WMI query to run.
    baseobj: the base object for the WMI query.

  Yields:
    A dict containing a list of key value pairs.
  """
  pythoncom.CoInitialize()   # Needs to be called if using com from a thread.
  wmi_obj = win32com.client.GetObject(baseobj)
  # This allows our WMI to do some extra things, in particular
  # it gives it access to find the executable path for all processes.
  wmi_obj.Security_.Privileges.AddAsString("SeDebugPrivilege")

  # Run query
  try:
    query_results = wmi_obj.ExecQuery(query)
  except pythoncom.com_error, e:
    raise RuntimeError("Failed to run WMI query \'%s\' err was %s" %
                       (query, e))

  # Extract results
  try:
    for result in query_results:
      response = {}
      for prop in result.Properties_:
        if prop.Name not in IGNORE_PROPS:
          if prop.Value is None:
            response[prop.Name] = u""
          else:
            # Values returned by WMI
            # We always want to return unicode strings.
            if isinstance(prop.Value, unicode):
              response[prop.Name] = prop.Value
            elif isinstance(prop.Value, str):
              response[prop.Name] = prop.Value.decode("utf8")
            else:
              # Int or other, convert it to a unicode string
              response[prop.Name] = unicode(prop.Value)

      yield response

  except pythoncom.com_error, e:
    raise RuntimeError("WMI query data error on query \'%s\' err was %s" %
                       (e, query))


class InstallDriver(actions.ActionPlugin):
  """Installs a driver.

  Note that only drivers with a signature that validates with
  client_config.DRIVER_SIGNING_CERT can be loaded.
  """
  in_protobuf = jobs_pb2.InstallDriverRequest

  def Run(self, args):
    """Initializes the driver."""
    if not args.driver:
      raise IOError("No driver supplied.")

    if not client_utils_common.VerifySignedDriver(args.driver):
      raise OSError("Driver signature signing failure.")

    # Allow for overriding the default driver display name from the server.
    driver_display_name = (args.driver_display_name or
                           client_config.DRIVER_DISPLAY_NAME)

    # Allow for overriding the default driver name from the server.
    driver_name = args.driver_name or client_config.DRIVER_NAME
    driver_path = args.write_path or client_config.DRIVER_FILE_PATH

    # TODO(user): What should we do if it fails to uninstall?
    if args.force_reload:
      client_utils_windows.UninstallDriver(driver_path, driver_name,
                                           delete_file=True)

    # TODO(user): Ensure we have lock here, no races
    logging.info("Writing driver to %s", driver_path)

    # TODO(user): Handle SysWOW64, if we are 32 bit we will actually
    # write to SysWOW64 if we try and write to system32 and the service
    # will fail.
    try:
      # Note permissions default to global read, user only write.
      with open(driver_path, "wb") as fd:
        fd.write(args.driver.data)
    except IOError, e:
      raise IOError("Failed to write driver file %s" % e)

    try:
      client_utils_windows.InstallDriver(driver_path, driver_name,
                                         driver_display_name)
    except OSError:
      raise IOError("Failed to install driver, may already be installed.")


class InitializeMemoryDriver(actions.ActionPlugin):
  """Loads the driver for memory access and returns a Stat for the device."""

  in_protobuf = jobs_pb2.Path
  out_protobuf = jobs_pb2.StatResponse

  def Run(self, args):
    """Run."""
    device_name = args.path or client_config.DRIVER_DEVICE_NAME

    # Do any initialization we need to do.
    logging.debug("Initializing %s", device_name)
    #TODO(user): Add init code for our driver.

    #TODO(user): Add IOCTL call to get memory size.
    mem_size = 4 * 1024 * 1024 * 1024   # 4GB

    # Send a reply telling the server we succeeded and where it
    # can find the path it should read.
    self.SendReply(pathspec=args.path, st_size=mem_size)


class UninstallDriver(actions.ActionPlugin):
  """Unloads and deletes a memory driver.

  Note that only drivers with a signature that validates with
  client_config.DRIVER_SIGNING_CERT can be uninstalled.
  """

  in_protobuf = jobs_pb2.InstallDriverRequest

  def Run(self, args):
    """Unloads a driver."""

    # Allow for overriding the default driver name from the server.
    driver_name = args.driver_name or client_config.DRIVER_NAME
    driver_path = args.write_path or client_config.DRIVER_FILE_PATH

    # First check the drver they sent us validates.
    client_utils_common.VerifySignedDriver(args.driver, verify_data=False)

    # Confirm the digest in the driver matches what we are about to remove.
    digest = hashlib.sha256(open(driver_path).read(DRIVER_MAX_SIZE)).digest()
    if digest != args.digest:
      # Driver we are uninstalling has been modified from original or we
      # sent the wrong one.
      raise RuntimeError("Failed driver sig validation on UninstallDriver")

    # Do the unload.
    result, err = client_utils_windows.UnloadDriver(driver_name, driver_path,
                                                    delete_driver=True)
    if not result:
      raise RuntimeError(err)
