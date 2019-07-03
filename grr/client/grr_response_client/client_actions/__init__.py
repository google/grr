#!/usr/bin/env python
"""Client actions root module."""
from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

import platform
import sys

from typing import Dict
from typing import Text
from typing import Type

from grr_response_client import actions
from grr_response_client.client_actions import admin
from grr_response_client.client_actions import artifact_collector
from grr_response_client.client_actions import cloud
from grr_response_client.client_actions import file_finder
from grr_response_client.client_actions import file_fingerprint
from grr_response_client.client_actions import memory
from grr_response_client.client_actions import network
from grr_response_client.client_actions import osquery
from grr_response_client.client_actions import plist
from grr_response_client.client_actions import searching
from grr_response_client.client_actions import standard
from grr_response_client.client_actions import tempfiles
from grr_response_client.client_actions import vfs_file_finder

REGISTRY = {
    "ArtifactCollector": artifact_collector.ArtifactCollector,
    "Bloat": admin.Bloat,
    "CheckFreeGRRTempSpace": tempfiles.CheckFreeGRRTempSpace,
    "DeleteGRRTempFiles": tempfiles.DeleteGRRTempFiles,
    "Echo": admin.Echo,
    "ExecuteBinaryCommand": standard.ExecuteBinaryCommand,
    "ExecuteCommand": standard.ExecuteCommand,
    "ExecutePython": standard.ExecutePython,
    "FileFinderOS": file_finder.FileFinderOS,
    "Find": searching.Find,
    "FingerprintFile": file_fingerprint.FingerprintFile,
    "GetClientInfo": admin.GetClientInfo,
    "GetClientStats": admin.GetClientStats,
    "GetCloudVMMetadata": cloud.GetCloudVMMetadata,
    "GetConfiguration": admin.GetConfiguration,
    "GetFileStat": standard.GetFileStat,
    "GetHostname": admin.GetHostname,
    "GetLibraryVersions": admin.GetLibraryVersions,
    "GetMemorySize": standard.GetMemorySize,
    "GetPlatformInfo": admin.GetPlatformInfo,
    "Grep": searching.Grep,
    "Hang": admin.Hang,
    "HashBuffer": standard.HashBuffer,
    "HashFile": standard.HashFile,
    "Kill": admin.Kill,
    "ListDirectory": standard.ListDirectory,
    "ListNetworkConnections": network.ListNetworkConnections,
    "ListProcesses": standard.ListProcesses,
    "Osquery": osquery.Osquery,
    "PlistQuery": plist.PlistQuery,
    "ReadBuffer": standard.ReadBuffer,
    "Segfault": standard.Segfault,
    "SendFile": standard.SendFile,
    "SendStartupInfo": admin.SendStartupInfo,
    "StatFS": standard.StatFS,
    "TransferBuffer": standard.TransferBuffer,
    "UpdateConfiguration": admin.UpdateConfiguration,
    "VfsFileFinder": vfs_file_finder.VfsFileFinder,
    "YaraProcessDump": memory.YaraProcessDump,
    "YaraProcessScan": memory.YaraProcessScan,
}  # type: Dict[Text, Type[actions.ActionPlugin]]

if platform.system() == "Linux":
  from grr_response_client.client_actions.linux import linux  # pylint: disable=g-import-not-at-top
  REGISTRY["EnumerateFilesystems"] = linux.EnumerateFilesystems
  REGISTRY["EnumerateInterfaces"] = linux.EnumerateInterfaces
  REGISTRY["EnumerateRunningServices"] = linux.EnumerateRunningServices
  REGISTRY["EnumerateUsers"] = linux.EnumerateUsers
  REGISTRY["GetInstallDate"] = linux.GetInstallDate
  REGISTRY["Uninstall"] = linux.Uninstall
  REGISTRY["UpdateAgent"] = linux.UpdateAgent

  if hasattr(sys, "frozen"):
    from grr_response_client.components.chipsec_support.actions import grr_chipsec  # pylint: disable=g-import-not-at-top
    REGISTRY["DumpACPITable"] = grr_chipsec.DumpACPITable,
    REGISTRY["DumpFlashImage"] = grr_chipsec.DumpFlashImage,

elif platform.system() == "Windows":
  from grr_response_client.client_actions.windows import windows  # pylint: disable=g-import-not-at-top
  REGISTRY["EnumerateFilesystems"] = windows.EnumerateFilesystems
  REGISTRY["EnumerateInterfaces"] = windows.EnumerateInterfaces
  REGISTRY["GetInstallDate"] = windows.GetInstallDate
  REGISTRY["WmiQuery"] = windows.WmiQuery
  REGISTRY["Uninstall"] = windows.Uninstall
  REGISTRY["UpdateAgent"] = windows.UpdateAgent

elif platform.system() == "Darwin":
  from grr_response_client.client_actions.osx import osx  # pylint: disable=g-import-not-at-top
  REGISTRY["EnumerateFilesystems"] = osx.EnumerateFilesystems
  REGISTRY["EnumerateInterfaces"] = osx.EnumerateInterfaces
  REGISTRY["GetInstallDate"] = osx.GetInstallDate
  REGISTRY["OSXEnumerateRunningServices"] = osx.OSXEnumerateRunningServices
  REGISTRY["Uninstall"] = osx.Uninstall
  REGISTRY["UpdateAgent"] = osx.UpdateAgent

