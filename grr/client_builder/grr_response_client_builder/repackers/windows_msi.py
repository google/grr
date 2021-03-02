#!/usr/bin/env python
"""Repacks a Windows MSI template."""

import contextlib
import os
import shutil
import struct
import subprocess
from typing import Tuple, Dict, Any, Callable

import olefile

from grr_response_client_builder import build
from grr_response_client_builder import build_helpers
from grr_response_core import config
from grr_response_core.lib import utils

# The prefix of the value of the magic MSI property used for padding.
# This is the prefix of a value in the string pool.
MAGIC_VALUE_FOR_PADDING = b"MagicPropertyValueForPadding"

# Encoded names of OLE streams in the MSI file.
FLEETSPEAK_CAB_STREAM_NAME = "䏩䈨䖷䈳䎤䆾䅤"
FLEETSPEAK_CONFIG_CAB_STREAM_NAME = "䏩䈨䖷䈳䎤䆿䑲䌩䞪䄦䠥"
FLEETSPEAK_SERVICE_CONFIG_CAB_STREAM_NAME = "䏩䈨䖷䈳䎤䖿䕨䌹䈦䆿䑲䌩䞪䄦䠥"
GRR_CONFIG_CAB_STREAM_NAME = "䕪䟵䒦䉱䊬䆾䅤"
FEATURE_STREAM_NAME = "䡀䈏䗤䕸䠨"
STRING_POOL_STREAM_NAME = "䡀㼿䕷䑬㹪䒲䠯"
STRING_DATA_STREAM_NAME = "䡀㼿䕷䑬㭪䗤䠤"

# Magic values in placeholder config files.
CAB_BEGIN = b"__BEGIN__"
CAB_END = b"__END__"


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
    self._level_offset = {}  # type: Dict[bytes, int]

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


class ConfigFileCab:
  """CAB archive containing a config file to be patched."""

  def __init__(self, data: str):
    self._data = data

  def SetConfigFile(self, value: bytes) -> None:  # pylint: disable=unused-argument
    """Sets the value of the config file within this archive."""
    self._ClearChecksums()

    def WriteBlock(start: int, end: int) -> None:
      nonlocal value
      block_size = end - start
      value_size = min(len(value), block_size)
      padding = b"\n" * (block_size - value_size)
      self._SetData(start, end, value[:value_size] + padding)
      value = value[value_size:]

    self._IterateFile(WriteBlock)

  def _IterateFile(self, callback: Callable[[int, int], None]) -> None:
    """Iterates through the CFDATA blocks of the CAB file."""
    pos = self._data.find(CAB_BEGIN)
    while True:
      data_length, = struct.unpack("<H", self._data[pos - 2:pos])
      is_last = self._data[pos:pos + data_length].endswith(CAB_END)
      callback(pos, pos + data_length)
      if is_last:
        break
      pos += data_length + 8

  def _ClearChecksums(self) -> None:
    """Clears the checksums of the CFDATA blocks."""

    def ClearChecksum(start: int, end: int) -> None:
      del end
      self._SetData(start - 8, start - 4, b"\x00\x00\x00\x00")

    self._IterateFile(ClearChecksum)

  def _SetData(self, start: int, end: int, data: bytes) -> None:
    """Sets a range of data in the CAB file."""
    if len(data) != end - start:
      raise ValueError("Wrong length of data.")
    self._data = self._data[:start] + data + self._data[end:]

  def Serialize(self) -> bytes:
    return self._data


class MsiFile:
  """A MSI file."""

  def __init__(self, path: str):
    self._olefile = olefile.OleFileIO(path, write_mode=True)

    def ReadStream(name):
      with self._olefile.openstream(name) as stream:
        return stream.read(self._olefile.get_size(name))

    string_pool_raw = ReadStream(STRING_POOL_STREAM_NAME)
    string_data_raw = ReadStream(STRING_DATA_STREAM_NAME)
    self._string_pool = StringPool(string_pool_raw, string_data_raw)
    feature_raw = ReadStream(FEATURE_STREAM_NAME)
    self._feature_table = FeatureTable(feature_raw, self._string_pool)
    fleetspeak_config_raw = ReadStream(FLEETSPEAK_CONFIG_CAB_STREAM_NAME)
    self._fleetspeak_config = ConfigFileCab(fleetspeak_config_raw)
    grr_config_raw = ReadStream(GRR_CONFIG_CAB_STREAM_NAME)
    self._grr_config = ConfigFileCab(grr_config_raw)
    fleetspeak_service_config_raw = ReadStream(
        FLEETSPEAK_SERVICE_CONFIG_CAB_STREAM_NAME)
    self._fleetspeak_service_config = ConfigFileCab(
        fleetspeak_service_config_raw)

  def ReplaceString(self, old_value: bytes, new_value: bytes) -> None:
    self._string_pool.Replace(old_value, new_value)

  def RenameFile(self, old_name: bytes, new_name: bytes) -> None:
    self._string_pool.RenameFile(old_name, new_name)

  def SetFleetspeakConfig(self, value: bytes) -> None:
    self._fleetspeak_config.SetConfigFile(value)

  def SetGrrConfig(self, value: bytes) -> None:
    self._grr_config.SetConfigFile(value)

  def SetFleetspeakServiceConfig(self, value: bytes) -> None:
    self._fleetspeak_service_config.SetConfigFile(value)

  def EnableFeature(self, feature_name: bytes) -> None:
    self._feature_table.SetLevel(feature_name, 1)

  def Write(self) -> None:
    """Writes the in-memory representation back to the file."""
    string_pool_raw, string_data_raw = self._string_pool.Serialize()
    self._olefile.write_stream(STRING_POOL_STREAM_NAME, string_pool_raw)
    self._olefile.write_stream(STRING_DATA_STREAM_NAME, string_data_raw)
    self._olefile.write_stream(FEATURE_STREAM_NAME,
                               self._feature_table.Serialize())
    self._olefile.write_stream(FLEETSPEAK_CONFIG_CAB_STREAM_NAME,
                               self._fleetspeak_config.Serialize())
    self._olefile.write_stream(GRR_CONFIG_CAB_STREAM_NAME,
                               self._grr_config.Serialize())
    self._olefile.write_stream(FLEETSPEAK_SERVICE_CONFIG_CAB_STREAM_NAME,
                               self._fleetspeak_service_config.Serialize())

  def Close(self) -> None:
    self._olefile.close()


class WindowsMsiClientRepacker(build.ClientRepacker):
  """Repacker for a template containing a Windows MSI."""

  def MakeDeployableBinary(self, template_path: str, output_path: str) -> str:
    context = self.context + ["Client Context"]
    utils.EnsureDirExists(os.path.dirname(output_path))

    def GetConfig(name: str) -> Any:
      return config.CONFIG.Get(name, context=self.context)

    fleetspeak_enabled = GetConfig("Client.fleetspeak_enabled")
    fleetspeak_bundled = GetConfig("ClientBuilder.fleetspeak_bundled")

    legacy = not (fleetspeak_enabled or fleetspeak_bundled)

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

      # Set product information

      ReplaceStringConfig("__ProductName", "Client.name")
      ReplaceStringConfig("__ProductManufacturer", "Client.company_name")

      # Enable features

      if GetConfig("ClientBuilder.console"):
        EnableFeature("DbgGrrExe")
      else:
        EnableFeature("GrrExe")

      if legacy:
        if GetConfig("ClientBuilder.console"):
          EnableFeature("DbgNanny")
        else:
          EnableFeature("Nanny")

      if fleetspeak_bundled:
        EnableFeature("FleetspeakClient")

      if fleetspeak_enabled or fleetspeak_bundled:
        EnableFeature("FleetspeakServiceRegistryEntry")

      # Rename directories

      RenameFileConfig("__GrrDirectory", "Client.name")
      RenameFileConfig("__GrrVersion", "Source.version_string")

      # Rename files

      if GetConfig("ClientBuilder.console"):
        RenameFileConfig("__dbg_grr-client.exe", "Client.binary_name")
        RenameFileConfig("__dbg_GRRService.exe", "Nanny.service_binary_name")
      else:
        RenameFileConfig("__grr-client.exe", "Client.binary_name")
        RenameFileConfig("__GRRService.exe", "Nanny.service_binary_name")

      # Write Configs

      if fleetspeak_bundled:
        with open(GetConfig("ClientBuilder.fleetspeak_client_config"),
                  "rb") as f:
          msi_file.SetFleetspeakConfig(f.read())

      RenameFileConfig("grr-config.yaml", "ClientBuilder.config_filename")
      msi_file.SetGrrConfig(
          build_helpers.GetClientConfig(context).encode("utf-8"))

      # Write Fleetspeak service registry data

      if fleetspeak_enabled or fleetspeak_bundled:
        key_name = GetConfig("Client.fleetspeak_unsigned_services_regkey")
        key_name = key_name.replace("HKEY_LOCAL_MACHINE\\", "")
        ReplaceString("__FleetspeakServiceRegistryKey", key_name)
        ReplaceStringConfig("__FleetspeakServiceRegistryName", "Client.name")
        ReplaceString(
            "__FleetspeakServiceRegistryValue",
            f"[INSTALLDIR]{GetConfig('Client.fleetspeak_unsigned_config_fname')}"
        )

      if fleetspeak_bundled:
        ReplaceStringConfig("FleetspeakClientService",
                            "Client.fleetspeak_service_name")

      # Write Fleetspeak service config

      # If we don't need to re-write the file after installation, just run
      # a dummy command.
      gen_fleespeak_service_file_cmd = "cmd.exe /c exit"

      if fleetspeak_enabled or fleetspeak_bundled:
        path = GetConfig("ClientBuilder.fleetspeak_config_path")
        with open(path, "rb") as f:
          msi_file.SetFleetspeakServiceConfig(f.read())
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

      # Configure nanny service

      if legacy:
        nanny_args = ["--service_key", GetConfig("Client.config_key")]
        ReplaceString("__NannyArguments", subprocess.list2cmdline(nanny_args))
        ReplaceStringConfig("__NannyServiceDescription",
                            "Nanny.service_description")
        if GetConfig("ClientBuilder.console"):
          ReplaceStringConfig("__DbgNannyRegistryKey", "Client.config_key")
          ReplaceStringConfig("__DbgNannyServiceName", "Nanny.service_name")

        else:
          ReplaceStringConfig("__NannyRegistryKey", "Client.config_key")
          ReplaceStringConfig("__NannyServiceName", "Nanny.service_name")
        grr_binary = GetConfig("Client.binary_name")
        grr_config = GetConfig("ClientBuilder.config_filename")
        ReplaceString("__NannyChildBinary", f"[INSTALLDIR]{grr_binary}")
        child_args = [
            f"[INSTALLDIR]{grr_binary}", "--config", f"[INSTALLDIR]{grr_config}"
        ]
        ReplaceString("__NannyChildCommandLine",
                      subprocess.list2cmdline(child_args))

      msi_file.Write()
      msi_file.Close()

      if os.path.exists(output_path):
        os.remove(output_path)
      shutil.move(os.path.join(tmp_dir, "installer.msi"), output_path)

    return output_path
