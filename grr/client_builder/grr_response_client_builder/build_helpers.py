#!/usr/bin/env python
"""Helper functions used by client building/repacking process."""


from collections.abc import Sequence
import datetime
import io
import logging
import os
import shutil
import struct
import tempfile


from typing import Optional

import yaml

from grr_response_client_builder import build
from grr_response_core import config
from grr_response_core import version
from grr_response_core.config import contexts
from grr_response_core.lib import rdfvalue
from grr_response_core.lib import utils
# pylint: disable=unused-import
# Pull in local config validators.
from grr_response_core.lib.rdfvalues import client as rdf_client
from grr_response_core.lib.rdfvalues import crypto as rdf_crypto
# pylint: enable=unused-import

# pylint: disable=g-import-not-at-top,unused-import
# This is a workaround so we don't need to maintain the whole PyInstaller
# codebase as a full-fledged dependency.
try:
  # pytype: disable=import-error
  from PyInstaller import __main__ as PyInstallerMain
  # pytype: enable=import-error
except ImportError:
  # We ignore this failure since most people running the code don't build their
  # own clients and printing an error message causes confusion.  Those building
  # their own clients will need PyInstaller installed.
  pass
# pylint: enable=g-import-not-at-top,unused-import

Context = Sequence[str]


def GenerateDirectory(
    input_dir: Optional[str] = None,
    output_dir: Optional[str] = None,
    replacements: Optional[Sequence[tuple[str, str]]] = None,
    context: Optional[Context] = None,
) -> None:
  """Copies an a directory rewriting file names according to spec."""
  if context is None:
    raise ValueError("context must be provided")

  input_dir = utils.NormalizePath(input_dir)
  output_dir = utils.NormalizePath(output_dir)
  replacements = replacements or []

  for (root, _, files) in os.walk(input_dir):
    for filename in files:
      in_file = utils.JoinPath(root, filename)
      out_file = in_file.replace(input_dir, output_dir)
      for (s, replacement) in replacements:
        out_file = out_file.replace(s, replacement)
      utils.EnsureDirExists(os.path.dirname(out_file))
      GenerateFile(in_file, out_file, context=context)


def GenerateFile(
    input_filename: Optional[str] = None,
    output_filename: Optional[str] = None,
    context: Optional[Context] = None,
) -> None:
  """Generates a file from a template, interpolating config values."""
  if context is None:
    raise ValueError("context must be provided.")

  if input_filename is None:
    input_filename = output_filename + ".in"
  if output_filename[-3:] == ".in":
    output_filename = output_filename[:-3]
  logging.debug("Generating file %s from %s", output_filename, input_filename)

  with io.open(input_filename, "r") as fd:
    data = fd.read()

  with io.open(output_filename, "w") as fd:
    fd.write(config.CONFIG.InterpolateValue(data, context=context))


def CleanDirectory(directory: str):
  logging.info("Clearing directory %s", directory)
  try:
    shutil.rmtree(directory)
  except OSError:
    pass

  utils.EnsureDirExists(directory)


def MakeBuildDirectory(context=None):
  """Prepares the build and work directories."""
  if context is None:
    raise ValueError("context can't be None")

  build_dir = config.CONFIG.Get("PyInstaller.build_dir", context=context)
  work_path = config.CONFIG.Get("PyInstaller.workpath_dir", context=context)

  CleanDirectory(build_dir)
  CleanDirectory(work_path)


def BuildWithPyInstaller(context=None):
  """Use pyinstaller to build a client package."""
  if context is None:
    raise ValueError("context has to be specified")

  CleanDirectory(config.CONFIG.Get("PyInstaller.distpath", context=context))

  logging.info("Copying pyinstaller support files")

  build_dir = config.CONFIG.Get("PyInstaller.build_dir", context=context)
  spec_file = os.path.join(build_dir, "grr.spec")

  with io.open(spec_file, "w") as fd:
    fd.write(config.CONFIG.Get("PyInstaller.spec", context=context))

  with io.open(os.path.join(build_dir, "version.txt"), "w") as fd:
    fd.write(config.CONFIG.Get("PyInstaller.version", context=context))

  shutil.copy(
      src=config.CONFIG.Get("PyInstaller.icon_path", context=context),
      dst=os.path.join(build_dir, "grr.ico"))

  # We expect the onedir (a one-folder bundle containing an executable) output
  # at this location.
  output_dir = os.path.join(
      config.CONFIG.Get("PyInstaller.distpath", context=context), "grr-client")

  args = [
      "--distpath",
      config.CONFIG.Get("PyInstaller.distpath", context=context),
      "--workpath",
      config.CONFIG.Get("PyInstaller.workpath_dir", context=context),
      spec_file,
  ]
  logging.info("Running pyinstaller: %s", args)
  PyInstallerMain.run(pyi_args=args)

  # Clear out some crud that pyinstaller includes.
  for path in ["tcl", "tk", "pytz"]:
    dir_path = os.path.join(output_dir, path)
    try:
      shutil.rmtree(dir_path)
    except OSError:
      logging.error("Unable to remove directory: %s", dir_path)

    try:
      os.mkdir(dir_path)
    except OSError:
      logging.error("Unable to create directory: %s", dir_path)

    file_path = os.path.join(dir_path, path)
    try:
      # Create an empty file so the directories get put in the installers.
      with io.open(file_path, "wb"):
        pass
    except IOError:
      logging.error("Unable to create file: %s", file_path)

  version_ini = config.CONFIG.Get(
      "ClientBuilder.version_ini_path", default=version.VersionPath())
  shutil.copy(version_ini, os.path.join(output_dir, "version.ini"))

  build_yaml_path = os.path.join(output_dir, "build.yaml")
  with io.open(build_yaml_path, mode="w", encoding="utf-8") as fd:
    WriteBuildYaml(fd, context=context)

  return output_dir


def WriteBuildYaml(fd, build_timestamp=True, context=None):
  """Write build spec to fd."""
  if context is None:
    raise ValueError("context has to be specified")

  output = {
      "Client.build_environment":
          rdf_client.Uname.FromCurrentSystem().signature(),
      "Template.build_type":
          config.CONFIG.Get("ClientBuilder.build_type", context=context),
      "Template.version_major":
          config.CONFIG.Get("Source.version_major", context=context),
      "Template.version_minor":
          config.CONFIG.Get("Source.version_minor", context=context),
      "Template.version_revision":
          config.CONFIG.Get("Source.version_revision", context=context),
      "Template.version_release":
          config.CONFIG.Get("Source.version_release", context=context),
      "Template.arch":
          config.CONFIG.Get("Client.arch", context=context)
  }

  yaml_keys = set(build.REQUIRED_BUILD_YAML_KEYS)
  if build_timestamp:
    now = datetime.datetime.now(datetime.timezone.utc)
    output["Client.build_time"] = now.isoformat()
  else:
    yaml_keys.remove("Client.build_time")

  for key, value in output.items():
    output[key] = str(value)

  output["Template.build_context"] = context

  output_keys = set(output.keys())
  if output_keys != yaml_keys:
    raise RuntimeError("Bad build.yaml: expected %s, got %s" %
                       (yaml_keys, output_keys))

  for k, v in output.items():
    if v is None:
      raise RuntimeError("Bad build.yaml: expected %s to be not None" % k)

  fd.write(yaml.safe_dump(output))


def ValidateEndConfig(config_obj, errors_fatal=True, context=None):
  """Given a generated client config, attempt to check for common errors."""
  if context is None:
    raise ValueError("context can't be None")

  errors = []

  if not config_obj.Get(
      "Client.executable_signing_public_key", context=context
  ):
    errors.append("Missing Client.executable_signing_public_key.")

  if errors_fatal and errors:
    for error in errors:
      logging.error("Build Config Error: %s", error)
    raise RuntimeError("Bad configuration generated. Terminating.")
  else:
    return errors


# Config options that have to make it to a deployable binary.
_CONFIG_SECTIONS = [
    "Client",
    "ClientRepacker",
    "Logging",
    "Config",
    "Osquery",
    "Installer",
    "Template",
]


def GetClientConfig(context, validate=True, deploy_timestamp=True):
  """Generates the client config file for inclusion in deployable binaries."""
  with utils.TempDirectory() as tmp_dir:
    # Make sure we write the file in yaml format.
    filename = os.path.join(
        tmp_dir,
        config.CONFIG.Get("ClientBuilder.config_filename", context=context))

    new_config = config.CONFIG.MakeNewConfig()
    new_config.Initialize(reset=True, data="")
    new_config.SetWriteBack(filename)

    # Only copy certain sections to the client. We enumerate all
    # defined options and then resolve those from the config in the
    # client's context. The result is the raw option as if the
    # client read our config file.
    client_context = context[:]
    while contexts.CLIENT_BUILD_CONTEXT in client_context:
      client_context.remove(contexts.CLIENT_BUILD_CONTEXT)
    for descriptor in sorted(config.CONFIG.type_infos, key=lambda x: x.name):
      if descriptor.section in _CONFIG_SECTIONS:
        value = config.CONFIG.GetRaw(
            descriptor.name, context=client_context, default=None)

        if value is not None:
          logging.debug("Copying config option to client: %s", descriptor.name)

          new_config.SetRaw(descriptor.name, value)

    if deploy_timestamp:
      deploy_time_string = str(rdfvalue.RDFDatetime.Now())
      new_config.Set("Client.deploy_time", deploy_time_string)
    new_config.Write()

    if validate:
      ValidateEndConfig(new_config, context=context)

    return io.open(filename, "r").read()


def CopyFileInZip(from_zip, from_name, to_zip, to_name=None, signer=None):
  """Read a file from a ZipFile and write it to a new ZipFile."""
  data = from_zip.read(from_name)
  if to_name is None:
    to_name = from_name
  if signer:
    logging.debug("Signing %s", from_name)
    data = signer.SignBuffer(data)
  to_zip.writestr(to_name, data)


def CreateNewZipWithSignedLibs(z_in,
                               z_out,
                               ignore_files=None,
                               signer=None,
                               skip_signing_files=None):
  """Copies files from one zip to another, signing all qualifying files."""
  ignore_files = ignore_files or []
  skip_signing_files = skip_signing_files or []
  extensions_to_sign = [".sys", ".exe", ".dll", ".pyd"]
  to_sign = []
  for template_file in z_in.namelist():
    if template_file not in ignore_files:
      extension = os.path.splitext(template_file)[1].lower()
      if (signer and template_file not in skip_signing_files and
          extension in extensions_to_sign):
        to_sign.append(template_file)
      else:
        CopyFileInZip(z_in, template_file, z_out)

  temp_files = {}
  for filename in to_sign:
    fd, path = tempfile.mkstemp()
    with os.fdopen(fd, "wb") as temp_fd:
      temp_fd.write(z_in.read(filename))
    temp_files[filename] = path

  try:
    signer.SignFiles(temp_files.values())
  except AttributeError:
    for f in temp_files.values():
      signer.SignFile(f)

  for filename, tempfile_path in temp_files.items():
    with io.open(tempfile_path, "rb") as fd:
      z_out.writestr(filename, fd.read())


def SetPeSubsystem(fd, console=True):
  """Takes file like obj and returns (offset, value) for the PE subsystem."""
  current_pos = fd.tell()
  fd.seek(0x3c)  # _IMAGE_DOS_HEADER.e_lfanew
  header_offset = struct.unpack("<I", fd.read(4))[0]
  # _IMAGE_NT_HEADERS.OptionalHeader.Subsystem ( 0x18 + 0x44)
  subsystem_offset = header_offset + 0x5c
  fd.seek(subsystem_offset)
  if console:
    fd.write(b"\x03")
  else:
    fd.write(b"\x02")
  fd.seek(current_pos)
