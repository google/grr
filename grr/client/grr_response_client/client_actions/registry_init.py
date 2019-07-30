#!/usr/bin/env python
"""Register all available client actions."""
from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

import platform
import sys

from grr_response_client import client_actions
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


def RegisterClientActions():
  """Registers all client actions."""

  client_actions.Register("ArtifactCollector",
                          artifact_collector.ArtifactCollector)
  client_actions.Register("Bloat", admin.Bloat)
  client_actions.Register("CheckFreeGRRTempSpace",
                          tempfiles.CheckFreeGRRTempSpace)
  client_actions.Register("DeleteGRRTempFiles", tempfiles.DeleteGRRTempFiles)
  client_actions.Register("Echo", admin.Echo)
  client_actions.Register("ExecuteBinaryCommand", standard.ExecuteBinaryCommand)
  client_actions.Register("ExecuteCommand", standard.ExecuteCommand)
  client_actions.Register("ExecutePython", standard.ExecutePython)
  client_actions.Register("FileFinderOS", file_finder.FileFinderOS)
  client_actions.Register("Find", searching.Find)
  client_actions.Register("FingerprintFile", file_fingerprint.FingerprintFile)
  client_actions.Register("GetClientInfo", admin.GetClientInfo)
  client_actions.Register("GetClientStats", admin.GetClientStats)
  client_actions.Register("GetCloudVMMetadata", cloud.GetCloudVMMetadata)
  client_actions.Register("GetConfiguration", admin.GetConfiguration)
  client_actions.Register("GetFileStat", standard.GetFileStat)
  client_actions.Register("GetHostname", admin.GetHostname)
  client_actions.Register("GetLibraryVersions", admin.GetLibraryVersions)
  client_actions.Register("GetMemorySize", standard.GetMemorySize)
  client_actions.Register("GetPlatformInfo", admin.GetPlatformInfo)
  client_actions.Register("Grep", searching.Grep)
  client_actions.Register("Hang", admin.Hang)
  client_actions.Register("HashBuffer", standard.HashBuffer)
  client_actions.Register("HashFile", standard.HashFile)
  client_actions.Register("Kill", admin.Kill)
  client_actions.Register("ListDirectory", standard.ListDirectory)
  client_actions.Register("ListNetworkConnections",
                          network.ListNetworkConnections)
  client_actions.Register("ListProcesses", standard.ListProcesses)
  client_actions.Register("Osquery", osquery.Osquery)
  client_actions.Register("PlistQuery", plist.PlistQuery)
  client_actions.Register("ReadBuffer", standard.ReadBuffer)
  client_actions.Register("Segfault", standard.Segfault)
  client_actions.Register("SendFile", standard.SendFile)
  client_actions.Register("SendStartupInfo", admin.SendStartupInfo)
  client_actions.Register("StatFS", standard.StatFS)
  client_actions.Register("TransferBuffer", standard.TransferBuffer)
  client_actions.Register("UpdateConfiguration", admin.UpdateConfiguration)
  client_actions.Register("VfsFileFinder", vfs_file_finder.VfsFileFinder)
  client_actions.Register("YaraProcessDump", memory.YaraProcessDump)
  client_actions.Register("YaraProcessScan", memory.YaraProcessScan)

  if platform.system() == "Linux":
    from grr_response_client.client_actions.linux import linux  # pylint: disable=g-import-not-at-top
    client_actions.Register("EnumerateFilesystems", linux.EnumerateFilesystems)
    client_actions.Register("EnumerateInterfaces", linux.EnumerateInterfaces)
    client_actions.Register("EnumerateRunningServices",
                            linux.EnumerateRunningServices)
    client_actions.Register("EnumerateUsers", linux.EnumerateUsers)
    client_actions.Register("GetInstallDate", linux.GetInstallDate)
    client_actions.Register("Uninstall", linux.Uninstall)
    client_actions.Register("UpdateAgent", linux.UpdateAgent)

    if hasattr(sys, "frozen"):
      from grr_response_client.components.chipsec_support.actions import grr_chipsec  # pylint: disable=g-import-not-at-top
      client_actions.Register("DumpACPITable", grr_chipsec.DumpACPITable)
      client_actions.Register("DumpFlashImage", grr_chipsec.DumpFlashImage)

  elif platform.system() == "Windows":
    from grr_response_client.client_actions.windows import windows  # pylint: disable=g-import-not-at-top
    client_actions.Register("EnumerateFilesystems",
                            windows.EnumerateFilesystems)
    client_actions.Register("EnumerateInterfaces", windows.EnumerateInterfaces)
    client_actions.Register("GetInstallDate", windows.GetInstallDate)
    client_actions.Register("WmiQuery", windows.WmiQuery)
    client_actions.Register("Uninstall", windows.Uninstall)
    client_actions.Register("UpdateAgent", windows.UpdateAgent)

  elif platform.system() == "Darwin":
    from grr_response_client.client_actions.osx import osx  # pylint: disable=g-import-not-at-top
    client_actions.Register("EnumerateFilesystems", osx.EnumerateFilesystems)
    client_actions.Register("EnumerateInterfaces", osx.EnumerateInterfaces)
    client_actions.Register("GetInstallDate", osx.GetInstallDate)
    client_actions.Register("OSXEnumerateRunningServices",
                            osx.OSXEnumerateRunningServices)
    client_actions.Register("Uninstall", osx.Uninstall)
    client_actions.Register("UpdateAgent", osx.UpdateAgent)

