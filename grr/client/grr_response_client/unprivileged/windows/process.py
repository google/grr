#!/usr/bin/env python
"""Process management on Windows.

On Windows, we want to create a subprocess such that:

* We can share a pair of named pipes with the subprocess for communication.
* We can share an open file handle with the subprocess.
* We can avoid implicitly sharing (leaking) any other handles.

This would normally be done as follows:

```
subprocess.Popen(
   close_fds=True,
   startupinfo=subprocess.STARTUPINFO(lpAttributeList={
      "handle_list": [ pipe_input, pipe_output, extra_file_handle ]
      })
```

However, on Python 3.6, the `subprocess` module doesn't support
the member `handle_list` in `STARTUPINFO.lpAttributeList`.

So for Python 3.6 we implement the `Process` class emulating that behavior.

Once we migrate to Python 3.7, this custom code can be removed.
"""

# win32 api types and class members violate naming conventions.
# pylint: disable=invalid-name

import contextlib
import ctypes
# pylint: disable=g-importing-member
from ctypes.wintypes import BOOL
from ctypes.wintypes import DWORD
from ctypes.wintypes import HANDLE
from ctypes.wintypes import LPBYTE
from ctypes.wintypes import LPCWSTR
from ctypes.wintypes import LPVOID
from ctypes.wintypes import LPWSTR
from ctypes.wintypes import WORD
# pylint: enable=g-importing-member
import os
import subprocess
from typing import List, Optional, NamedTuple

import win32api
import win32con
import win32event
import win32process

from grr_response_client.unprivileged.windows import sandbox

kernel32 = ctypes.WinDLL("kernel32")
advapi32 = ctypes.WinDLL("advapi32")

PSID_AND_ATTRIBUTES = LPVOID
PSID = LPVOID


class SECURITY_CAPABILITIES(ctypes.Structure):
  _fields_ = [
      ("AppContainerSid", PSID),
      ("Capabilities", PSID_AND_ATTRIBUTES),
      ("CapabilityCount", DWORD),
      ("Reserved", DWORD),
  ]


class SECURITY_ATTRIBUTES(ctypes.Structure):
  _fields_ = [
      ("nLength", DWORD),
      ("lpSecurityDescriptor", LPVOID),
      ("bInheritHandle", BOOL),
  ]


LPSECURITY_ATTRIBUTES = ctypes.POINTER(SECURITY_ATTRIBUTES)


class STARTUPINFOW(ctypes.Structure):
  _fields_ = [
      ("cb", DWORD),
      ("lpReserved", LPWSTR),
      ("lpDesktop", LPWSTR),
      ("lpTitle", LPWSTR),
      ("dwX", DWORD),
      ("dwY", DWORD),
      ("dwXSize", DWORD),
      ("dwYSize", DWORD),
      ("dwXCountChars", DWORD),
      ("dwYCountChars", DWORD),
      ("dwFillAttribute", DWORD),
      ("dwFlags", DWORD),
      ("wShowWindow", WORD),
      ("cbReserved2", WORD),
      ("lpReserved2", LPBYTE),
      ("hStdInput", HANDLE),
      ("hStdOutput", HANDLE),
      ("hStdError", HANDLE),
  ]


LPSTARTUPINFOW = ctypes.POINTER(STARTUPINFOW)

LPPROC_THREAD_ATTRIBUTE_LIST = LPVOID


class STARTUPINFOEXW(ctypes.Structure):
  _fields_ = [
      ("StartupInfo", STARTUPINFOW),
      ("lpAttributeList", LPPROC_THREAD_ATTRIBUTE_LIST),
  ]


class PROCESS_INFORMATION(ctypes.Structure):
  _fields_ = [
      ("hProcess", HANDLE),
      ("hThread", HANDLE),
      ("dwProcessId", DWORD),
      ("dwThreadId", DWORD),
  ]


LPPROCESS_INFORMATION = ctypes.POINTER(PROCESS_INFORMATION)

CreateProcessW = kernel32.CreateProcessW
CreateProcessW.argtypes = [
    LPCWSTR,
    LPWSTR,
    LPSECURITY_ATTRIBUTES,
    LPSECURITY_ATTRIBUTES,
    BOOL,
    DWORD,
    LPVOID,
    LPCWSTR,
    LPSTARTUPINFOW,
    LPPROCESS_INFORMATION,
]
CreateProcessW.restype = BOOL

if ctypes.sizeof(ctypes.c_void_p) == 8:
  ULONG_PTR = ctypes.c_ulonglong
else:
  ULONG_PTR = ctypes.c_ulong

SIZE_T = ULONG_PTR
PSIZE_T = ctypes.POINTER(SIZE_T)

InitializeProcThreadAttributeList = kernel32.InitializeProcThreadAttributeList
InitializeProcThreadAttributeList.argtypes = [
    LPPROC_THREAD_ATTRIBUTE_LIST,
    DWORD,
    DWORD,
    PSIZE_T,
]
InitializeProcThreadAttributeList.restype = BOOL

DWORD_PTR = ULONG_PTR
PVOID = LPVOID

UpdateProcThreadAttribute = kernel32.UpdateProcThreadAttribute
UpdateProcThreadAttribute.argtypes = [
    LPPROC_THREAD_ATTRIBUTE_LIST,
    DWORD,
    DWORD_PTR,
    PVOID,
    SIZE_T,
    PVOID,
    PSIZE_T,
]
UpdateProcThreadAttribute.restype = BOOL

DeleteProcThreadAttributeList = kernel32.DeleteProcThreadAttributeList
DeleteProcThreadAttributeList.argtypes = [LPPROC_THREAD_ATTRIBUTE_LIST]

GetProcessId = kernel32.GetProcessId
GetProcessId.argtypes = [HANDLE]
GetProcessId.restype = DWORD

ConvertStringSidToSidW = advapi32.ConvertStringSidToSidW
ConvertStringSidToSidW.argtypes = [LPCWSTR, ctypes.POINTER(PSID)]
ConvertStringSidToSidW.restype = BOOL

FreeSid = advapi32.FreeSid
FreeSid.argtypes = [PSID]
FreeSid.restype = PVOID


class Error(Exception):
  pass


EXTENDED_STARTUPINFO_PRESENT = 0x00080000

PROC_THREAD_ATTRIBUTE_HANDLE_LIST = 0x20002
PROC_THREAD_ATTRIBUTE_SECURITY_CAPABILITIES = 0x20009


class CpuTimes(NamedTuple):
  cpu_time: float
  sys_time: float


class Process:
  """A subprocess.

  A pair of pipes is created and shared with the subprocess.
  """

  def __init__(self,
               args: List[str],
               extra_handles: Optional[List[int]] = None):
    """Constructor.

    Args:
      args: Command line to run, in argv format.
      extra_handles: Optional list of extra handles to share with the
        subprocess.

    Raises:
      Error: if a win32 call fails.
    """

    # Stack for resources which are needed by this instance.
    self._exit_stack = contextlib.ExitStack()

    # Stack for resources which are needed only during this method.
    with contextlib.ExitStack() as stack:
      sandbox_obj = self._exit_stack.enter_context(sandbox.CreateSandbox())

      size = SIZE_T()
      InitializeProcThreadAttributeList(None, 2, 0, ctypes.byref(size))
      attr_list = ctypes.create_string_buffer(size.value)
      res = InitializeProcThreadAttributeList(attr_list, 2, 0,
                                              ctypes.byref(size))
      if not res:
        raise Error("InitializeProcThreadAttributeList failed.")
      stack.callback(DeleteProcThreadAttributeList, attr_list)

      if extra_handles is None:
        extra_handles = []

      for extra_handle in extra_handles:
        os.set_handle_inheritable(extra_handle, True)

      handle_list_size = len(extra_handles)
      handle_list = (HANDLE * handle_list_size)(
          *[HANDLE(handle) for handle in extra_handles])
      if handle_list:
        res = UpdateProcThreadAttribute(attr_list, 0,
                                        PROC_THREAD_ATTRIBUTE_HANDLE_LIST,
                                        handle_list, ctypes.sizeof(handle_list),
                                        None, None)
        if not res:
          raise Error("UpdateProcThreadAttribute failed.")

      if sandbox_obj.sid_string is not None:
        psid = PSID()
        if not ConvertStringSidToSidW(sandbox_obj.sid_string,
                                      ctypes.byref(psid)):
          raise Error("ConvertStringSidToSidW")
        stack.callback(FreeSid, psid)
        security_capabilities = SECURITY_CAPABILITIES()
        security_capabilities.AppContainerSid = psid
        res = UpdateProcThreadAttribute(
            attr_list, 0, PROC_THREAD_ATTRIBUTE_SECURITY_CAPABILITIES,
            ctypes.byref(security_capabilities),
            ctypes.sizeof(security_capabilities), None, None)
        if not res:
          raise Error("UpdateProcThreadAttribute failed.")

      siex = STARTUPINFOEXW()
      si = siex.StartupInfo
      si.cb = ctypes.sizeof(siex)
      si.wShowWindow = False
      siex.lpAttributeList = ctypes.cast(attr_list,
                                         LPPROC_THREAD_ATTRIBUTE_LIST)

      if sandbox_obj.desktop_name is not None:
        si.lpDesktop = sandbox_obj.desktop_name

      pi = PROCESS_INFORMATION()

      command_line = subprocess.list2cmdline(args)

      res = CreateProcessW(
          None,
          command_line,
          None,
          None,
          True,
          EXTENDED_STARTUPINFO_PRESENT,
          None,
          None,
          ctypes.byref(si),
          ctypes.byref(pi),
      )

      if not res:
        raise Error("CreateProcessW failed.")

      self._handle = pi.hProcess
      self._exit_stack.callback(win32api.CloseHandle, pi.hProcess)
      win32api.CloseHandle(pi.hThread)

      self.pid = GetProcessId(self._handle)
      if self.pid == 0:
        raise Error("GetProcessId failed.")

  def Stop(self) -> int:
    """Terminates the process and waits for the process to exit.

    Returns:
      The exit code.
    """
    exit_code = win32process.GetExitCodeProcess(self._handle)
    if exit_code == win32con.STILL_ACTIVE:
      win32process.TerminateProcess(self._handle, -1)
    return self.Wait()

  def Wait(self) -> int:
    """Waits for the process to exit.

    Returns:
      The exit code.

    Raises:
      Error: on system error.
    """
    res = win32event.WaitForSingleObject(self._handle, win32event.INFINITE)
    if res == win32event.WAIT_FAILED:
      raise Error("WaitForSingleObject failed.")
    exit_code = win32process.GetExitCodeProcess(self._handle)
    self._exit_stack.close()
    return exit_code

  def GetCpuTimes(self) -> CpuTimes:
    times = win32process.GetProcessTimes(self._handle)
    return CpuTimes(
        cpu_time=times["UserTime"] / 10000000.0,
        sys_time=times["KernelTime"] / 10000000.0)
