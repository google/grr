#!/usr/bin/env python
"""Repacks a Windows MSI template."""

import contextlib
import os
import shutil
import struct
import subprocess
from typing import Tuple, Dict, Any
import uuid

import olefile

from grr_response_client_builder import build
from grr_response_client_builder import build_helpers
from grr_response_client_builder.repackers import cab_utils
from grr_response_core import config
from grr_response_core.lib import utils

# The prefix of the value of the magic MSI property used for padding.
# This is the prefix of a value in the string pool.
MAGIC_VALUE_FOR_PADDING = b"MagicPropertyValueForPadding"

# Encoded names of OLE streams in the MSI file.
GRR_CAB_STREAM_NAME = "䕪䞵䄦䠥"
FEATURE_STREAM_NAME = "䡀䈏䗤䕸䠨"
STRING_POOL_STREAM_NAME = "䡀㼿䕷䑬㹪䒲䠯"
STRING_DATA_STREAM_NAME = "䡀㼿䕷䑬㭪䗤䠤"
SUMMARY_INFORMATION_STREAM_NAME = "\x05SummaryInformation"


class Error(Exception):
  pass


class StringEntry:
  """Entry in the String pool."""

  def __init__(self, value: bytes, refcount: int):
    self.value = value
    self.refcount = refcount

  def __repr__(self):
    return repr(self.value)

  def Size(self):
    return len(self.value)


class StringPool:
  """In-memory representation of the string pool."""

  _pool_struct = struct.Struct("<HH")

  def __init__(self, pool: bytes, data: bytes):
    header_struct = struct.Struct("<HH")
    self._header = pool[:4]
    self._data_size = len(data)
    _, header = header_struct.unpack(self._header)
    if (header & 0x8000) != 0:
      raise Error("String reference size is 3. This is not supported.")

    self._strings = {}
    self._strings_reverse = {}

    pool_offset = self._pool_struct.size
    data_offset = 0
    string_id = 1

    while pool_offset < len(pool):
      size, refcount = self._pool_struct.unpack(pool[pool_offset:pool_offset +
                                                     4])
      if size == 0 and refcount != 0:
        raise Error(">64kB strings are not supported.")
      value = data[data_offset:data_offset + size]
      self._strings[string_id] = StringEntry(value, refcount)
      self._strings_reverse[value] = string_id
      string_id += 1
      data_offset += size
      pool_offset += self._pool_struct.size

    if data_offset != len(data):
      raise Error("String data hasn't been fully consumed.")
    if pool_offset != len(pool):
      raise Error("String pool hasn't been fully consumed.")

  def Serialize(self) -> Tuple[bytes, bytes]:
    """Serializes the string pool.

    Returns:
      A tuple (string pool, string data).
    """
    pool = [self._header]
    data = []

    new_data_size = sum(
        [string_entry.Size() for string_entry in self._strings.values()])

    for _, string_entry in sorted(self._strings.items()):
      if string_entry.value.startswith(MAGIC_VALUE_FOR_PADDING):
        padding_size = self._data_size - new_data_size
        string_entry.value = b"_" * (len(string_entry.value) + padding_size)
      pool.append(
          self._pool_struct.pack(
              len(string_entry.value), string_entry.refcount))
      data.append(string_entry.value)

    return (b"".join(pool), b"".join(data))

  def GetById(self, string_id: int) -> bytes:
    return self._strings[string_id].value

  def GetId(self, value: bytes) -> int:
    return self._strings_reverse[value]

  def Replace(self, old_value: bytes, new_value: bytes) -> None:
    string_id = self._strings_reverse[old_value]
    self._strings[string_id].value = new_value
    del self._strings_reverse[old_value]
    self._strings_reverse[new_value] = string_id

  def RenameFile(self, old_name: bytes, new_name: bytes) -> None:
    suffix = b"|" + old_name
    for value in self._strings_reverse:
      if value.endswith(suffix):
        new_value = value.replace(suffix, b"|" + new_name)
        self.Replace(value, new_value)
        return
    raise Error("Not found")


class FeatureTable:
  """In-memory representation of the Feature table."""

  def __init__(self, data: bytes, string_pool: StringPool):
    self._data = data
    self._level_offset: Dict[bytes, int] = {}

    row_count = len(data) // 16

    feature_offset = 0
    level_offset = row_count * 10

    for _ in range(row_count):
      feature_id, = struct.unpack("<H", data[feature_offset:feature_offset + 2])
      level, = struct.unpack("<H", data[level_offset:level_offset + 2])
      # Integers in the database are encoded as value + 0x8000
      level -= 0x8000
      feature_name = string_pool.GetById(feature_id)

      self._level_offset[feature_name] = level_offset

      feature_offset += 2
      level_offset += 2

  def SetLevel(self, feature_name: bytes, level: int) -> None:
    """Sets the level of a Feature."""
    offset = self._level_offset[feature_name]
    # Integers in the database are encoded as value + 0x8000
    level_raw = struct.pack("<H", level + 0x8000)
    self._data = self._data[:offset] + level_raw + self._data[offset + 2:]

  def Serialize(self) -> bytes:
    return self._data


class SummaryInformation:
  """Represents the Summary Information OLE stream."""

  def __init__(self, data: bytes) -> None:
    self._data = data

  def Replace(self, old_value: bytes, new_value: bytes) -> None:
    """Replaces a string with a string of the same size."""
    if old_value not in self._data:
      raise Error(f"Value {old_value} not found in summary information.")
    if len(old_value) != len(new_value):
      raise Error("Replacement must be of same size as original.")
    self._data = self._data.replace(old_value, new_value)

  def Serialize(self) -> bytes:
    return self._data


def _SignCabFiles(directory_path: str, signer):
  """Signs EXE and DLL files in `directory_path`."""
  file_paths = []
  for file_name in os.listdir(directory_path):
    if file_name in (".", ".."):
      continue
    file_path = os.path.join(directory_path, file_name)
    with open(file_path, "rb") as f:
      header = f.read(2)
      if header == b"MZ":
        file_paths.append(file_path)
  signer.SignFiles(file_paths)


class MsiFile:
  """A MSI file."""

  def __init__(self, path: str):
    self._olefile = olefile.OleFileIO(path, write_mode=True)
    self._stack = contextlib.ExitStack()
    self._tmp_dir = self._stack.enter_context(utils.TempDirectory())

    def ReadStream(name):
      with self._olefile.openstream(name) as stream:
        return stream.read(self._olefile.get_size(name))

    string_pool_raw = ReadStream(STRING_POOL_STREAM_NAME)
    string_data_raw = ReadStream(STRING_DATA_STREAM_NAME)
    self._string_pool = StringPool(string_pool_raw, string_data_raw)
    feature_raw = ReadStream(FEATURE_STREAM_NAME)
    self._feature_table = FeatureTable(feature_raw, self._string_pool)
    summary_information_raw = ReadStream(SUMMARY_INFORMATION_STREAM_NAME)
    self._summary_information = SummaryInformation(summary_information_raw)

    cab_path = os.path.join(self._tmp_dir, "input.cab")
    cab_tmp_path = os.path.join(self._tmp_dir, "cab_tmp_dir")
    with open(cab_path, "wb") as f:
      f.write(ReadStream(GRR_CAB_STREAM_NAME))
    self._cab = cab_utils.Cab(cab_path, cab_tmp_path)
    self._cab.ExtractFiles()
    self._cab.WriteFile("PaddingFile", b"")

  def ReplaceString(self, old_value: bytes, new_value: bytes) -> None:
    self._string_pool.Replace(old_value, new_value)

  def RenameFile(self, old_name: bytes, new_name: bytes) -> None:
    self._string_pool.RenameFile(old_name, new_name)

  def WriteCabFile(self, key: str, data: bytes) -> None:
    self._cab.WriteFile(key, data)

  def CabFilesDirectory(self) -> str:
    return self._cab.file_path_base

  def EnableFeature(self, feature_name: bytes) -> None:
    self._feature_table.SetLevel(feature_name, 1)

  def ReplaceSummaryInformation(self, old_value: bytes,
                                new_value: bytes) -> None:
    self._summary_information.Replace(old_value, new_value)

  def Write(self) -> None:
    """Writes the in-memory representation back to the file."""
    string_pool_raw, string_data_raw = self._string_pool.Serialize()
    self._olefile.write_stream(STRING_POOL_STREAM_NAME, string_pool_raw)
    self._olefile.write_stream(STRING_DATA_STREAM_NAME, string_data_raw)
    self._olefile.write_stream(FEATURE_STREAM_NAME,
                               self._feature_table.Serialize())
    self._olefile.write_stream(SUMMARY_INFORMATION_STREAM_NAME,
                               self._summary_information.Serialize())
    cab_path = os.path.join(self._tmp_dir, "output.cab")
    cab_padded_path = os.path.join(self._tmp_dir, "output_padded.cab")
    self._cab.Pack(cab_path)
    cab_utils.PadCabFile(cab_path, cab_padded_path,
                         self._olefile.get_size(GRR_CAB_STREAM_NAME))
    with open(cab_padded_path, "rb") as f:
      self._olefile.write_stream(GRR_CAB_STREAM_NAME, f.read())

  def Close(self) -> None:
    self._olefile.close()
    self._stack.close()


class WindowsClientRepacker(build.ClientRepacker):
  """Repacker for a template containing a Windows MSI."""

  def MakeDeployableBinary(self, template_path: str, output_path: str) -> str:
    context = self.context + ["Client Context"]
    utils.EnsureDirExists(os.path.dirname(output_path))

    def GetConfig(name: str) -> Any:
      return config.CONFIG.Get(name, context=self.context)

    fleetspeak_bundled = GetConfig("ClientBuilder.fleetspeak_bundled")

    with contextlib.ExitStack() as stack:
      tmp_dir = stack.enter_context(utils.TempDirectory())
      shutil.unpack_archive(template_path, tmp_dir, format="zip")
      msi_file = MsiFile(os.path.join(tmp_dir, "installer.msi"))

      def EnableFeature(name: str) -> None:
        msi_file.EnableFeature(name.encode("utf-8"))

      def ReplaceString(src: str, dst: str) -> None:
        msi_file.ReplaceString(src.encode("utf-8"), dst.encode("utf-8"))

      def RenameFile(src: str, dst: str) -> None:
        msi_file.RenameFile(src.encode("utf-8"), dst.encode("utf-8"))

      def ReplaceStringConfig(src: str, dst: str) -> None:
        ReplaceString(src, GetConfig(dst))

      def RenameFileConfig(src: str, dst: str) -> None:
        RenameFile(src, GetConfig(dst))

      def ReplaceSummaryInformation(src: str, dst: str) -> None:
        msi_file.ReplaceSummaryInformation(
            src.encode("utf-8"), dst.encode("utf-8"))

      # Set product information

      ReplaceStringConfig("__ProductName", "Client.name")
      ReplaceStringConfig("__ProductManufacturer", "Client.company_name")

      # Product and Package ID must be replaced with unique ones.
      # Otherwise a newly repackaged MSI isn't considered a different package
      # and installing it over and existing MSI with the same IDs doesn't work
      # as expected.
      # See https://docs.microsoft.com/en-us/windows/win32/msi/major-upgrades

      ReplaceString("{66666666-6666-6666-6666-666666666666}",
                    f"{{{uuid.uuid4()}}}")
      ReplaceSummaryInformation("{77777777-7777-7777-7777-777777777777}",
                                f"{{{uuid.uuid4()}}}")

      # Enable features

      if GetConfig("ClientBuilder.console"):
        EnableFeature("DbgGrrExe")
      else:
        EnableFeature("GrrExe")

      EnableFeature("FleetspeakServiceRegistryEntry")
      EnableFeature("NannyServiceRemove")
      if fleetspeak_bundled:
        EnableFeature("FleetspeakClient")
      else:
        EnableFeature("FleetspeakServiceRestart")

      # Rename directories

      RenameFileConfig("__GrrDirectory", "Client.name")
      RenameFileConfig("__GrrVersion", "Source.version_string")

      # Rename files

      if GetConfig("ClientBuilder.console"):
        RenameFileConfig("__dbg_grr-client.exe", "Client.binary_name")
      else:
        RenameFileConfig("__grr-client.exe", "Client.binary_name")

      # Write Configs

      if fleetspeak_bundled:
        with open(GetConfig("ClientBuilder.fleetspeak_client_config"),
                  "rb") as f:
          msi_file.WriteCabFile("FileFleetspeakConfig", f.read())

      RenameFileConfig("grr-config.yaml", "ClientBuilder.config_filename")
      msi_file.WriteCabFile(
          "FileGrrConfig",
          build_helpers.GetClientConfig(context).encode("utf-8"))

      # Write Fleetspeak service registry data
      key_name = GetConfig("Client.fleetspeak_unsigned_services_regkey")
      key_name = key_name.replace("HKEY_LOCAL_MACHINE\\", "")
      ReplaceString("__FleetspeakServiceRegistryKey", key_name)
      ReplaceStringConfig("__FleetspeakServiceRegistryName", "Client.name")
      ReplaceString(
          "__FleetspeakServiceRegistryValue",
          f"[INSTALLDIR]{GetConfig('Client.fleetspeak_unsigned_config_fname')}")
      ReplaceStringConfig("FleetspeakClientService",
                          "Client.fleetspeak_service_name")

      # Write Fleetspeak service config

      # If we don't need to re-write the file after installation, just run
      # a dummy command.
      gen_fleespeak_service_file_cmd = "cmd.exe /c exit"

      path = GetConfig("ClientBuilder.fleetspeak_config_path")
      with open(path, "rb") as f:
        msi_file.WriteCabFile("FileFleetspeakServiceConfig", f.read())
      RenameFileConfig("fleetspeak-service-config.txt",
                       "Client.fleetspeak_unsigned_config_fname")
      if path.endswith(".in"):
        args = [
            "[INSTALLDIR]" + GetConfig("Client.binary_name"),
            "--config",
            "[INSTALLDIR]" + GetConfig("ClientBuilder.config_filename"),
            "-p",
            "Client.install_path=[INSTALLDIR]",
            "--install",
            "--interpolate_fleetspeak_service_config",
            "[INSTALLDIR]" +
            GetConfig("Client.fleetspeak_unsigned_config_fname"),
        ]
        gen_fleespeak_service_file_cmd = subprocess.list2cmdline(args)

      ReplaceString("__GenFleetspeakServiceFileCmd",
                    gen_fleespeak_service_file_cmd)

      ReplaceStringConfig("__NannyServiceNameToRemove", "Nanny.service_name")

      if self.signer:
        _SignCabFiles(msi_file.CabFilesDirectory(), self.signer)

      msi_file.Write()
      msi_file.Close()

      if self.signer:
        self.signer.SignFile(os.path.join(tmp_dir, "installer.msi"))

      if os.path.exists(output_path):
        os.remove(output_path)
      shutil.move(os.path.join(tmp_dir, "installer.msi"), output_path)

    return output_path
