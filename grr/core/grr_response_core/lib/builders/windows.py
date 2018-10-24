#!/usr/bin/env python
"""A builder implementation for windows clients."""
from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

import ctypes
import logging
import os
import re
import shutil
import subprocess
import sys


import win32process

from grr_response_core import config
from grr_response_core.lib import build

MODULE_PATTERNS = [
    # Visual Studio runtime libs.
    re.compile("msvcr.+.dll", re.I),
    re.compile("msvcp.+.dll", re.I)
]

# We copy these files manually because pyinstaller destroys them to the point
# where they can't be signed. They don't ever seem to be loaded but they are
# part of the VC90 manifest.
FILES_FROM_VIRTUALENV = [
    r"Lib\site-packages\pythonwin\mfc90.dll",
    r"Lib\site-packages\pythonwin\mfc90u.dll"
]

PROCESS_QUERY_INFORMATION = 0x400
PROCESS_VM_READ = 0x10


def EnumMissingModules():
  """Enumerate all modules which match the patterns MODULE_PATTERNS.

  PyInstaller often fails to locate all dlls which are required at
  runtime. We import all the client modules here, we simply introspect
  all the modules we have loaded in our current running process, and
  all the ones matching the patterns are copied into the client
  package.

  Yields:
    a source file for a linked dll.
  """
  module_handle = ctypes.c_ulong()
  count = ctypes.c_ulong()
  process_handle = ctypes.windll.kernel32.OpenProcess(PROCESS_QUERY_INFORMATION
                                                      | PROCESS_VM_READ, 0,
                                                      os.getpid())
  ctypes.windll.psapi.EnumProcessModules(process_handle,
                                         ctypes.byref(module_handle),
                                         ctypes.sizeof(module_handle),
                                         ctypes.byref(count))

  # The size of a handle is pointer size (i.e. 64 bit of amd64 and 32 bit on
  # i386).
  if sys.maxsize > 2**32:
    handle_type = ctypes.c_ulonglong
  else:
    handle_type = ctypes.c_ulong

  module_list = (handle_type * (count.value // ctypes.sizeof(handle_type)))()

  ctypes.windll.psapi.EnumProcessModulesEx(process_handle,
                                           ctypes.byref(module_list),
                                           ctypes.sizeof(module_list),
                                           ctypes.byref(count), 2)

  for x in module_list:
    module_filename = win32process.GetModuleFileNameEx(process_handle, x)
    for pattern in MODULE_PATTERNS:
      if pattern.match(os.path.basename(module_filename)):
        yield module_filename

  for venv_file in FILES_FROM_VIRTUALENV:
    yield os.path.join(sys.prefix, venv_file)


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
    self.nanny_dir = os.path.join(self.build_dir, "grr", "client",
                                  "grr_response_client", "nanny")
    nanny_src_dir = config.CONFIG.Get(
        "ClientBuilder.nanny_source_dir", context=self.context)
    logging.info("Copying Nanny build files from %s to %s", nanny_src_dir,
                 self.nanny_dir)

    shutil.copytree(
        config.CONFIG.Get(
            "ClientBuilder.nanny_source_dir", context=self.context),
        self.nanny_dir)

    build_type = config.CONFIG.Get(
        "ClientBuilder.build_type", context=self.context)

    vs_arch = config.CONFIG.Get(
        "ClientBuilder.vs_arch", default=None, context=self.context)

    # We have to set up the Visual Studio environment first and then call
    # msbuild.
    env_script = config.CONFIG.Get(
        "ClientBuilder.vs_env_script", default=None, context=self.context)

    if vs_arch is None or env_script is None or not os.path.exists(env_script):
      # Visual Studio is not installed. We just use pre-built binaries in that
      # case.
      logging.warn("Visual Studio does not appear to be installed, "
                   "Falling back to prebuilt GRRNanny binaries."
                   "If you want to build it you must have VS 2012 installed.")

      binaries_dir = config.CONFIG.Get(
          "ClientBuilder.nanny_prebuilt_binaries", context=self.context)

      shutil.copy(
          os.path.join(binaries_dir, "GRRNanny_%s.exe" % vs_arch),
          os.path.join(self.output_dir, "GRRservice.exe"))

    else:
      # Lets build the nanny with the VS env script.
      subprocess.check_call(
          "cmd /c \"\"%s\" && msbuild /p:Configuration=%s;Platform=%s\"" %
          (env_script, build_type, vs_arch),
          cwd=self.nanny_dir)

      # The templates always contain the same filenames - the repack step might
      # rename them later.
      shutil.copy(
          os.path.join(self.nanny_dir, vs_arch, build_type, "GRRNanny.exe"),
          os.path.join(self.output_dir, "GRRservice.exe"))

  def MakeExecutableTemplate(self, output_file=None):
    """Windows templates also include the nanny."""
    super(WindowsClientBuilder,
          self).MakeExecutableTemplate(output_file=output_file)

    self.MakeBuildDirectory()
    self.BuildWithPyInstaller()

    # Get any dll's that pyinstaller forgot:
    for module in EnumMissingModules():
      logging.info("Copying additional dll %s.", module)
      shutil.copy(module, self.output_dir)

    self.BuildNanny()

    # Generate a prod and a debug version of nanny executable.
    shutil.copy(
        os.path.join(self.output_dir, "GRRservice.exe"),
        os.path.join(self.output_dir, "dbg_GRRservice.exe"))
    with open(os.path.join(self.output_dir, "GRRservice.exe"), "r+") as fd:
      build.SetPeSubsystem(fd, console=False)
    with open(os.path.join(self.output_dir, "dbg_GRRservice.exe"), "r+") as fd:
      build.SetPeSubsystem(fd, console=True)

    # Generate a prod and a debug version of client executable.
    shutil.copy(
        os.path.join(self.output_dir, "grr-client.exe"),
        os.path.join(self.output_dir, "dbg_grr-client.exe"))
    with open(os.path.join(self.output_dir, "grr-client.exe"), "r+") as fd:
      build.SetPeSubsystem(fd, console=False)
    with open(os.path.join(self.output_dir, "dbg_grr-client.exe"), "r+") as fd:
      build.SetPeSubsystem(fd, console=True)

    self.MakeZip(self.output_dir, self.template_file)


def CopyFileInZip(from_zip, from_name, to_zip, to_name=None):
  """Read a file from a ZipFile and write it to a new ZipFile."""
  data = from_zip.read(from_name)
  if to_name is None:
    to_name = from_name
  to_zip.writestr(to_name, data)
