#!/usr/bin/env python
"""A builder implementation for windows clients."""
from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

import ctypes
import io
import logging
import os
import re
import shutil
import subprocess
import sys
from typing import List
import zipfile

import win32process

from grr_response_client_builder import build
from grr_response_client_builder import build_helpers
from grr_response_core import config
from grr_response_core.lib import package
from grr_response_core.lib import utils


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
    r"Lib\site-packages\pythonwin\mfc90u.dll",
    # TODO(user): check if building/repacking works without lines below.
    r"Lib\site-packages\pythonwin\mfc140.dll",
    r"Lib\site-packages\pythonwin\mfcm140u.dll"
]

PROCESS_QUERY_INFORMATION = 0x400
PROCESS_VM_READ = 0x10


def _EnumMissingModules():
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
  process_handle = ctypes.windll.kernel32.OpenProcess(
      PROCESS_QUERY_INFORMATION
      | PROCESS_VM_READ, 0, os.getpid())
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
    path = os.path.join(sys.prefix, venv_file)
    if os.path.exists(path):
      yield path


def _MakeZip(input_dir, output_path):
  """Creates a ZIP archive of the files in the input directory.

  Args:
    input_dir: the name of the input directory.
    output_path: path to the output ZIP archive without extension.
  """
  logging.info("Generating zip template file at %s", output_path)
  basename, _ = os.path.splitext(output_path)
  # TODO(user):pytype: incorrect make_archive() definition in typeshed.
  # pytype: disable=wrong-arg-types
  shutil.make_archive(
      basename, "zip", base_dir=".", root_dir=input_dir, verbose=True)
  # pytype: enable=wrong-arg-types


def _MakeMsi(input_dir: str, output_path: str) -> None:
  """Packages the PyInstaller files as MSI."""
  wxs_file = package.ResourcePath("grr-response-core",
                                  "install_data/windows/grr.wxs")

  fleetspeak_wxs_lib = os.path.join(
      config.CONFIG["ClientBuilder.fleetspeak_install_dir"],
      "fleetspeak_lib.wxs")

  # Don't automatically harvest these files using heat.exe, since they
  # are treated specially in grr.wxs.

  exclude_files = [
      "grr-client.exe",
      "dbg_grr-client.exe",
      "GRRservice.exe",
      "dbg_GRRservice.exe",
      "fleetspeak-client.exe",
      "grr-client.exe.manifest",
  ]

  def Run(args: List[str]):
    logging.info("Running: %s.", args)
    subprocess.check_call(args)

  with utils.TempDirectory() as temp_dir:
    for exclude_file in exclude_files:
      shutil.move(
          os.path.join(input_dir, exclude_file),
          os.path.join(temp_dir, exclude_file))
    Run([
        os.path.join(config.CONFIG["ClientBuilder.wix_tools_path"], "bin",
                     "heat.exe"),
        "dir",
        input_dir,
        "-sfrag",
        "-srd",
        "-cg",
        "CompGrrAutoFiles",
        "-ag",
        "-var",
        "var.InputDir",
        "-dr",
        "INSTALLDIR",
        "-out",
        os.path.join(temp_dir, "heat.wxs"),
    ])
    for exclude_file in exclude_files:
      shutil.move(
          os.path.join(temp_dir, exclude_file),
          os.path.join(input_dir, exclude_file))

    for placeholder_file in [
        "grr-config.yaml", "fleetspeak-client.config",
        "fleetspeak-service-config.txt"
    ]:
      with open(os.path.join(input_dir, placeholder_file), "w", newline="\n"):
        pass

    # Due to a limitation in the olefile library, at repacking time, the CAB
    # in the MSI file needs to be repacked to a CAB file of same size.
    # To do so, we add 3 MB of random (uncompressable) data into a padding
    # file.
    # At repacking time, the padding file will get truncated to make space for
    # other files (config files, signed EXE and DLL files) to grow.
    with open(os.path.join(input_dir, "padding-file.bin"), "wb") as f:
      for _ in range(3):
        f.write(os.urandom(1024 * 1024))

    object_files = []
    for source_file in (wxs_file, fleetspeak_wxs_lib,
                        os.path.join(temp_dir, "heat.wxs")):
      object_file = os.path.join(temp_dir,
                                 os.path.basename(source_file) + ".wxobj")
      Run([
          os.path.join(config.CONFIG["ClientBuilder.wix_tools_path"], "bin",
                       "candle.exe"),
          source_file,
          "-arch",
          "x64",
          "-ext",
          "WixUtilExtension",
          "-dFLEETSPEAK_EXECUTABLE=" +
          os.path.join(input_dir, "fleetspeak-client.exe"),
          "-dVERSION=" + config.CONFIG["Source.version_string"],
          "-sw1150",
          f"-dInputDir={input_dir}",
          "-out",
          object_file,
      ])
      object_files.append(object_file)
    Run([
        os.path.join(config.CONFIG["ClientBuilder.wix_tools_path"], "bin",
                     "light.exe"),
    ] + object_files + [
        "-ext",
        "WixUtilExtension",
        "-sw1076",
        "-out",
        os.path.join(temp_dir, "installer.msi"),
    ])
    with zipfile.ZipFile(output_path, "w") as zip_output:
      zip_output.write(os.path.join(temp_dir, "installer.msi"), "installer.msi")
      zip_output.write(os.path.join(input_dir, "build.yaml"), "build.yaml")


class WindowsClientBuilder(build.ClientBuilder):
  """Builder class for the Windows client."""

  BUILDER_CONTEXT = "Target:Windows"

  def BuildNanny(self, dest_dir: str):
    """Use VS2010 to build the windows Nanny service."""
    # When running under cygwin, the following environment variables are not set
    # (since they contain invalid chars). Visual Studio requires these or it
    # will fail.
    os.environ["ProgramFiles(x86)"] = r"C:\Program Files (x86)"
    with utils.TempDirectory() as temp_dir:
      nanny_dir = os.path.join(temp_dir, "grr", "client", "grr_response_client",
                               "nanny")
      nanny_src_dir = config.CONFIG.Get(
          "ClientBuilder.nanny_source_dir", context=self.context)
      logging.info("Copying Nanny build files from %s to %s", nanny_src_dir,
                   nanny_dir)

      shutil.copytree(
          config.CONFIG.Get(
              "ClientBuilder.nanny_source_dir", context=self.context),
          nanny_dir)

      build_type = config.CONFIG.Get(
          "ClientBuilder.build_type", context=self.context)

      vs_arch = config.CONFIG.Get(
          "ClientBuilder.vs_arch", default=None, context=self.context)

      # We have to set up the Visual Studio environment first and then call
      # msbuild.
      env_script = config.CONFIG.Get(
          "ClientBuilder.vs_env_script", default=None, context=self.context)

      if vs_arch is None or env_script is None or not os.path.exists(
          env_script) or config.CONFIG.Get(
              "ClientBuilder.use_prebuilt_nanny", context=self.context):
        # Visual Studio is not installed. We just use pre-built binaries in that
        # case.
        logging.warning(
            "Visual Studio does not appear to be installed, "
            "Falling back to prebuilt GRRNanny binaries."
            "If you want to build it you must have VS 2012 installed.")

        binaries_dir = config.CONFIG.Get(
            "ClientBuilder.nanny_prebuilt_binaries", context=self.context)

        shutil.copy(
            os.path.join(binaries_dir, "GRRNanny_%s.exe" % vs_arch),
            os.path.join(dest_dir, "GRRservice.exe"))

      else:
        # Lets build the nanny with the VS env script.
        subprocess.check_call(
            "cmd /c \"\"%s\" && msbuild /p:Configuration=%s;Platform=%s\"" %
            (env_script, build_type, vs_arch),
            cwd=nanny_dir)

        # The templates always contain the same filenames - the repack step
        # might rename them later.
        shutil.copy(
            os.path.join(nanny_dir, vs_arch, build_type, "GRRNanny.exe"),
            os.path.join(dest_dir, "GRRservice.exe"))

  def CopyBundledFleetspeak(self, output_dir):
    src_dir = config.CONFIG.Get(
        "ClientBuilder.fleetspeak_install_dir", context=self.context)
    shutil.copy(os.path.join(src_dir, "fleetspeak-client.exe"), output_dir)

  def _CreateOutputDir(self):
    """Windows templates also include the nanny."""
    build_helpers.MakeBuildDirectory(context=self.context)
    output_dir = build_helpers.BuildWithPyInstaller(context=self.context)

    # Get any dll's that pyinstaller forgot:
    for module in _EnumMissingModules():
      logging.info("Copying additional dll %s.", module)
      shutil.copy(module, output_dir)

    self.BuildNanny(output_dir)

    # Generate a prod and a debug version of nanny executable.
    shutil.copy(
        os.path.join(output_dir, "GRRservice.exe"),
        os.path.join(output_dir, "dbg_GRRservice.exe"))
    with io.open(os.path.join(output_dir, "GRRservice.exe"), "rb+") as fd:
      build_helpers.SetPeSubsystem(fd, console=False)
    with io.open(os.path.join(output_dir, "dbg_GRRservice.exe"), "rb+") as fd:
      build_helpers.SetPeSubsystem(fd, console=True)

    # Generate a prod and a debug version of client executable.
    shutil.copy(
        os.path.join(output_dir, "grr-client.exe"),
        os.path.join(output_dir, "dbg_grr-client.exe"))
    with io.open(os.path.join(output_dir, "grr-client.exe"), "rb+") as fd:
      build_helpers.SetPeSubsystem(fd, console=False)
    with io.open(os.path.join(output_dir, "dbg_grr-client.exe"), "rb+") as fd:
      build_helpers.SetPeSubsystem(fd, console=True)

    self.CopyBundledFleetspeak(output_dir)

    return output_dir

  def MakeExecutableTemplate(self, output_path):
    output_dir = self._CreateOutputDir()
    if config.CONFIG["ClientBuilder.build_msi"]:
      _MakeMsi(output_dir, output_path)
    else:
      _MakeZip(output_dir, output_path)
