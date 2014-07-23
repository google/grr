#!/usr/bin/env python
"""A builder implementation for windows clients."""
import ctypes
import logging
import os
import re
import shutil
import struct
import subprocess
import sys


import win32process

from grr.lib import build
from grr.lib import config_lib

MODULE_PATTERNS = [re.compile("distorm.*.dll", re.I),

                   # Visual Studio runtime libs.
                   re.compile("msvcr.+.dll", re.I),
                   re.compile("msvcp.+.dll", re.I)]

PROCESS_QUERY_INFORMATION = 0x400
PROCESS_VM_READ = 0x10


def EnumMissingModules():
  """Enumerate all modules which match the patterns MODULE_PATTERNS.

  PyInstaller often fails to locate all dlls which are required at
  runtime. We import all the client modules here, we simply introdpect
  all the modules we have loaded in our current running process, and
  all the ones matching the patterns are copied into the client
  package.

  Yields:
    a source file for a linked dll.
  """
  module_handle = ctypes.c_ulong()
  count = ctypes.c_ulong()
  process_handle = ctypes.windll.kernel32.OpenProcess(
      PROCESS_QUERY_INFORMATION | PROCESS_VM_READ, 0, os.getpid())
  ctypes.windll.psapi.EnumProcessModules(
      process_handle, ctypes.byref(module_handle), ctypes.sizeof(module_handle),
      ctypes. byref(count))

  # The size of a handle is pointer size (i.e. 64 bit of amd64 and 32 bit on
  # i386).
  if sys.maxsize > 2**32:
    handle_type = ctypes.c_ulonglong
  else:
    handle_type = ctypes.c_ulong

  module_list = (handle_type * (count.value / ctypes.sizeof(handle_type)))()

  ctypes.windll.psapi.EnumProcessModulesEx(
      process_handle, ctypes.byref(module_list), ctypes.sizeof(module_list),
      ctypes.byref(count), 2)

  for x in module_list:
    module_filename = win32process.GetModuleFileNameEx(process_handle, x)
    for pattern in MODULE_PATTERNS:
      if pattern.match(os.path.basename(module_filename)):
        yield module_filename


class WindowsClientBuilder(build.ClientBuilder):
  """Builder class for the Windows client."""

  def __init__(self, context=None):
    super(WindowsClientBuilder, self).__init__(context=context)
    self.context.append("Target:Windows")

  def BuildNanny(self):
    """Use VS2010 to build the windows Nanny service."""
    # When running under cygwin, the following environment variables are not set
    # (since they contain invalid chars). Visual Studio requires these or it
    # will fail.
    os.environ["ProgramFiles(x86)"] = r"C:\Program Files (x86)"
    logging.info("Copying Nanny build files.")
    self.nanny_dir = os.path.join(self.build_dir, "grr/client/nanny")

    shutil.copytree(config_lib.CONFIG.Get("ClientBuilder.nanny_source_dir",
                                          context=self.context), self.nanny_dir)

    build_type = config_lib.CONFIG.Get(
        "ClientBuilder.build_type", context=self.context)

    vs_arch = config_lib.CONFIG.Get("ClientBuilder.vs_arch", default=None,
                                    context=self.context)

    # We have to set up the Visual Studio environment first and then call
    # msbuild.
    env_script = config_lib.CONFIG.Get("ClientBuilder.vs_env_script",
                                       default=None, context=self.context)

    if vs_arch is None or env_script is None or not os.path.exists(env_script):
      raise RuntimeError("no such Visual Studio script: %s" % env_script)

    subprocess.check_call(
        "cmd /c \"\"%s\" && cd \"%s\" && msbuild /p:Configuration=%s\"" % (
            env_script, self.nanny_dir, build_type))

    # The templates always contain the same filenames - the deploy step might
    # rename them later.
    shutil.copy(
        os.path.join(self.nanny_dir, vs_arch, build_type, "GRRNanny.exe"),
        os.path.join(self.output_dir, "GRRservice.exe"))

  def MakeExecutableTemplate(self):
    """Windows templates also include the nanny."""
    self.MakeBuildDirectory()
    self.BuildWithPyInstaller()

    # Get any dll's that pyinstaller forgot:
    for module in EnumMissingModules():
      logging.info("Copying additional dll %s.", module)
      shutil.copy(module, self.output_dir)

    self.BuildNanny()

    self.EnsureDirExists(os.path.dirname(
        config_lib.CONFIG.Get("ClientBuilder.template_path",
                              context=self.context)))

    output_file = config_lib.CONFIG.Get("ClientBuilder.template_path",
                                        context=self.context)
    logging.info("Generating zip template file at %s", output_file)
    self.MakeZip(self.output_dir, output_file)


def CopyFileInZip(from_zip, from_name, to_zip, to_name=None):
  """Read a file from a ZipFile and write it to a new ZipFile."""
  data = from_zip.read(from_name)
  if to_name is None:
    to_name = from_name
  to_zip.writestr(to_name, data)


def SetPeSubsystem(fd, console=True):
  """Takes file like obj and returns (offset, value) for the PE subsystem."""
  current_pos = fd.tell()
  fd.seek(0x3c)  # _IMAGE_DOS_HEADER.e_lfanew
  header_offset = struct.unpack("<I", fd.read(4))[0]
  # _IMAGE_NT_HEADERS.OptionalHeader.Subsystem ( 0x18 + 0x44)
  subsystem_offset = header_offset + 0x5c
  fd.seek(subsystem_offset)
  if console:
    fd.write("\x03")
  else:
    fd.write("\x02")
  fd.seek(current_pos)
