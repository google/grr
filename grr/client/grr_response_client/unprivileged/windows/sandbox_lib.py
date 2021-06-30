#!/usr/bin/env python
"""Windows Sandboxing library based on AppContainers.

See
https://docs.microsoft.com/en-us/windows/win32/secauthz/appcontainer-for-legacy-applications-
for details about AppContainers.

This module works only on Windows >= 8.
"""

import contextlib
import ctypes
# pylint:disable=g-importing-member
from ctypes import HRESULT
from ctypes.wintypes import BOOL
from ctypes.wintypes import DWORD
from ctypes.wintypes import HLOCAL
from ctypes.wintypes import LPCWSTR
from ctypes.wintypes import LPVOID
from ctypes.wintypes import LPWSTR
# pylint:enable=g-importing-member
from typing import Iterable, Optional

import ntsecuritycon
import pywintypes
import win32api
import win32file
import win32security
import win32service
import winerror

userenv = ctypes.WinDLL("userenv")
kernel32 = ctypes.WinDLL("kernel32")
advapi32 = ctypes.WinDLL("advapi32")

PCWSTR = LPCWSTR
PSID_AND_ATTRIBUTES = LPVOID  # pylint:disable=invalid-name
PSID = LPVOID
PVOID = LPVOID

CreateAppContainerProfile = userenv.CreateAppContainerProfile
CreateAppContainerProfile.argtypes = [
    PCWSTR,
    PCWSTR,
    PCWSTR,
    PSID_AND_ATTRIBUTES,
    DWORD,
    PSID,
]
CreateAppContainerProfile.restype = HRESULT

DeriveAppContainerSidFromAppContainerName = userenv.DeriveAppContainerSidFromAppContainerName
DeriveAppContainerSidFromAppContainerName.argtypes = [
    PCWSTR,
    PSID,
]
DeriveAppContainerSidFromAppContainerName.restype = HRESULT

ConvertSidToStringSidW = advapi32.ConvertSidToStringSidW
ConvertSidToStringSidW.argtypes = [
    PSID,
    ctypes.POINTER(LPWSTR),
]
ConvertSidToStringSidW.restype = BOOL

FreeSid = advapi32.FreeSid
FreeSid.argtypes = [PSID]
FreeSid.restype = PVOID

LocalFree = kernel32.LocalFree
LocalFree.argtypes = [HLOCAL]
LocalFree.restype = HLOCAL

WINSTA_READATTRIBUTES = 0x0002
WINSTA_CREATEDESKTOP = 0x0008

DESKTOP_CREATEWINDOW = 0x0002
DESKTOP_READOBJECTS = 0x0001

NO_MULTIPLE_TRUSTEE = 0


class Error(Exception):
  pass


def _FormatDacl(dacl) -> str:
  res = [[str(x) for x in dacl.GetAce(i)] for i in range(dacl.GetAceCount())]
  res = [" * " + str(x) for x in res]
  return "\n".join(res)


def _AddPermissionToDacl(dacl, sid, access_permissions: int) -> None:
  """Adds a permission for a SID to a DACL.

  Args:
    dacl: `PyACL` representing the DACL.
    sid: `PySID` representing the SID to add permission for.
    access_permissions: The permissions as a set of biflags using the
      `ACCESS_MASK` format.
  """
  dacl.AddAccessAllowedAceEx(
      win32security.ACL_REVISION_DS,
      win32security.OBJECT_INHERIT_ACE | win32security.CONTAINER_INHERIT_ACE,
      access_permissions, sid)


def _AllowObjectAccess(sid, handle, object_type: int,
                       access_permissions: int) -> None:
  """Allows access to an object by handle.

  Args:
    sid: A `PySID` representing the SID to grant access to.
    handle: A handle to an object.
    object_type: A `SE_OBJECT_TYPE` enum value.
    access_permissions: The permissions as a set of biflags using the
      `ACCESS_MASK` format.
  """
  info = win32security.GetSecurityInfo(handle, object_type,
                                       win32security.DACL_SECURITY_INFORMATION)
  dacl = info.GetSecurityDescriptorDacl()
  _AddPermissionToDacl(dacl, sid, access_permissions)
  win32security.SetSecurityInfo(handle, object_type,
                                win32security.DACL_SECURITY_INFORMATION, None,
                                None, dacl, None)


def _AllowNamedObjectAccess(sid, name: str, object_type: int,
                            access_permissions: int) -> None:
  """Allows access to a named object.

  Args:
    sid: A `PySID` representing the SID to grant access to.
    name: Name of the object.
    object_type: A `SE_OBJECT_TYPE` enum value.
    access_permissions: The permissions as a set of biflags using the
      `ACCESS_MASK` format.
  """
  info = win32security.GetNamedSecurityInfo(
      name, object_type, win32security.DACL_SECURITY_INFORMATION)
  dacl = info.GetSecurityDescriptorDacl()
  _AddPermissionToDacl(dacl, sid, access_permissions)
  win32security.SetNamedSecurityInfo(
      name, object_type, win32security.DACL_SECURITY_INFORMATION
      | win32security.UNPROTECTED_DACL_SECURITY_INFORMATION, None, None, dacl,
      None)


def _CreateOrOpenAppContainer(name: str):
  """Creates or opens a Windows app container.

  Args:
    name: Name of the app container.

  Returns:
    A `PySID` representing the SID of the AppContainer.

  Raises:
    Error: On failure.
  """
  with contextlib.ExitStack() as stack:
    psid = PSID()
    try:
      res = CreateAppContainerProfile(name, name, name, None, 0,
                                      ctypes.byref(psid))
      if res != winerror.S_OK:
        raise Error(f"CreateAppContainerProfile returned: {res}")
      stack.callback(FreeSid, psid)
    except OSError as e:
      if e.winerror != winerror.HRESULT_FROM_WIN32(
          winerror.ERROR_ALREADY_EXISTS):
        raise
      res = DeriveAppContainerSidFromAppContainerName(name, ctypes.byref(psid))
      if res != winerror.S_OK:
        raise Error(
            f"DeriveAppContainerSidFromAppContainerName returned: {res}")
      stack.callback(FreeSid, psid)
    str_sid = LPWSTR()
    res = ConvertSidToStringSidW(psid, ctypes.byref(str_sid))
    if res == 0:
      raise Error(f"ConvertSidToStringSidW failed: {res}")
    stack.callback(LocalFree, str_sid)
    return win32security.ConvertStringSidToSid(str_sid.value)


def _GetSecurityAttributes(handle) -> win32security.SECURITY_ATTRIBUTES:
  """Returns the security attributes for a handle.

  Args:
    handle: A handle to an object.
  """
  security_descriptor = win32security.GetSecurityInfo(
      handle, win32security.SE_WINDOW_OBJECT,
      win32security.DACL_SECURITY_INFORMATION)
  result = win32security.SECURITY_ATTRIBUTES()
  result.SECURITY_DESCRIPTOR = security_descriptor
  return result


def _CreateWindowStation(name: Optional[str], access: int):
  """Creates a window station.

  Args:
    name: Name of the window station.
    access: The type of access the returned handle has to the window station.

  Returns:
    A handle to the created window station.
  """
  current_station = win32service.GetProcessWindowStation()
  security_attributes = _GetSecurityAttributes(current_station)
  # The try/except originates from the Chromium sandbox code.
  # They try to create the window station with various level of privilege.
  try:
    return win32service.CreateWindowStation(
        name, 0, access | win32file.GENERIC_READ | WINSTA_CREATEDESKTOP,
        security_attributes)
  except pywintypes.error as e:
    if e.winerror != winerror.ERROR_ACCESS_DENIED:
      raise
    return win32service.CreateWindowStation(
        name, 0, access | WINSTA_READATTRIBUTES | WINSTA_CREATEDESKTOP,
        security_attributes)


def _CreateAltWindowStation(name: str):
  """Creates an alternate window station.

  The function first tries to create a named Window station using `name`. Since
  that is a privileged operation, upon failure, the function retries with name
  set to `None`.

  Args:
    name: Name of the window station.

  Returns:
    A handle to the created window station.
  """
  try:
    return _CreateWindowStation(
        name, ntsecuritycon.READ_CONTROL | ntsecuritycon.WRITE_DAC)
  except pywintypes.error as e:
    if e.winerror != winerror.ERROR_ACCESS_DENIED:
      raise
    # Only the Administrator can create a named window station.
    # If the call fails with access denied, retry with name = None.
    return _CreateWindowStation(
        None, ntsecuritycon.READ_CONTROL | ntsecuritycon.WRITE_DAC)


def _CreateAltDesktop(window_station, name: str):
  """Creates an alternate desktop.

  Args:
    window_station: Handle to window station.
    name: Name of the desktop.

  Returns:
    A handle to the alternate desktop.
  """
  current_desktop = win32service.GetThreadDesktop(win32api.GetCurrentThreadId())
  security_attributes = _GetSecurityAttributes(current_desktop)
  current_station = win32service.GetProcessWindowStation()
  window_station.SetProcessWindowStation()
  desktop = win32service.CreateDesktop(
      name, 0,
      (DESKTOP_CREATEWINDOW | DESKTOP_READOBJECTS | ntsecuritycon.READ_CONTROL
       | ntsecuritycon.WRITE_DAC | ntsecuritycon.WRITE_OWNER),
      security_attributes)
  current_station.SetProcessWindowStation()
  return desktop


def _GetFullDesktopName(window_station, desktop) -> str:
  """Returns a full name to a desktop.

  Args:
    window_station: Handle to window station.
    desktop: Handle to desktop.
  """
  return "\\".join([
      win32service.GetUserObjectInformation(handle, win32service.UOI_NAME)
      for handle in [window_station, desktop]
  ])


def InitSandbox(name: str, paths_read_only: Iterable[str]) -> None:
  """Initializes a sandbox.

  Args:
    name: The unique name of the Sandbox. Windows will create unique state
      (directory tree, regisry tree and a SID) based on the name.
    paths_read_only: Lists of paths which will be shared in read-only and
      execute mode with the Sandbox SID.
  """
  sandbox_sid = _CreateOrOpenAppContainer(name)
  for path_read_only in paths_read_only:
    _AllowNamedObjectAccess(
        sandbox_sid, path_read_only, win32security.SE_FILE_OBJECT,
        ntsecuritycon.GENERIC_READ | ntsecuritycon.GENERIC_EXECUTE)


class Sandbox:
  """Wraps the state of a Sandbox.

  The state consists of an alternate desktop and window station which should be
  kept open while the sandbox is running.
  """

  sid_string: Optional[str] = None
  """Stringified SID of the Sandbox."""

  desktop_name: Optional[str] = None
  """Full name of the alternate desktop of the sandbox."""

  def __init__(self, name: str) -> None:
    """Constructor.

    Args:
      name: Name of the sandbox. See `InitSandbox` for details.
    """
    self._name = name
    self._exit_stack = contextlib.ExitStack()

  def __enter__(self) -> "Sandbox":
    self.Open()
    return self

  def __exit__(self, exc_type, exc_value, traceback) -> None:
    self.Close()

  def Open(self) -> None:
    """Creates the state of the sandbox."""
    sandbox_sid = _CreateOrOpenAppContainer(self._name)
    window_station_name = f"{self._name}_wsta"
    h_window_station = _CreateAltWindowStation(window_station_name)
    self._exit_stack.callback(h_window_station.CloseWindowStation)
    desktop_name = f"{self._name}_desktop"
    h_desktop = _CreateAltDesktop(h_window_station, desktop_name)
    self._exit_stack.callback(h_desktop.CloseDesktop)
    for handle in (h_window_station, h_desktop):
      _AllowObjectAccess(sandbox_sid, handle, win32security.SE_KERNEL_OBJECT,
                         ntsecuritycon.GENERIC_ALL)
    self.sid_string = win32security.ConvertSidToStringSid(sandbox_sid)
    self.desktop_name = _GetFullDesktopName(h_window_station, h_desktop)

  def Close(self) -> None:
    """Releases the sate of the sandbox."""
    self._exit_stack.close()
