#!/usr/bin/env python
"""A mapping of client action id strings to action stub classes."""

from grr_response_server import server_stubs

ACTION_STUB_BY_ID = {
    "ArtifactCollector": server_stubs.ArtifactCollector,
    "CollectLargeFile": server_stubs.CollectLargeFile,
    "CheckFreeGRRTempSpace": server_stubs.CheckFreeGRRTempSpace,
    "DeleteGRRTempFiles": server_stubs.DeleteGRRTempFiles,
    "DumpACPITable": server_stubs.DumpACPITable,
    "DumpFlashImage": server_stubs.DumpFlashImage,
    "Echo": server_stubs.Echo,
    "EficheckCollectHashes": server_stubs.EficheckCollectHashes,
    "EficheckDumpImage": server_stubs.EficheckDumpImage,
    "EnumerateFilesystems": server_stubs.EnumerateFilesystems,
    "EnumerateInterfaces": server_stubs.EnumerateInterfaces,
    "EnumerateRunningServices": server_stubs.EnumerateRunningServices,
    "EnumerateUsers": server_stubs.EnumerateUsers,
    "ExecuteBinaryCommand": server_stubs.ExecuteBinaryCommand,
    "ExecuteCommand": server_stubs.ExecuteCommand,
    "ExecutePython": server_stubs.ExecutePython,
    "FileFinderOS": server_stubs.FileFinderOS,
    "Find": server_stubs.Find,
    "FingerprintFile": server_stubs.FingerprintFile,
    "GetClientInfo": server_stubs.GetClientInfo,
    "GetClientStats": server_stubs.GetClientStats,
    "GetCloudVMMetadata": server_stubs.GetCloudVMMetadata,
    "GetConfiguration": server_stubs.GetConfiguration,
    "GetFileStat": server_stubs.GetFileStat,
    "GetHostname": server_stubs.GetHostname,
    "GetInstallDate": server_stubs.GetInstallDate,
    "GetLibraryVersions": server_stubs.GetLibraryVersions,
    "GetMemorySize": server_stubs.GetMemorySize,
    "GetPlatformInfo": server_stubs.GetPlatformInfo,
    "Grep": server_stubs.Grep,
    "HashBuffer": server_stubs.HashBuffer,
    "HashFile": server_stubs.HashFile,
    "Kill": server_stubs.Kill,
    "ListDirectory": server_stubs.ListDirectory,
    "ListNamedPipes": server_stubs.ListNamedPipes,
    "ListNetworkConnections": server_stubs.ListNetworkConnections,
    "ListProcesses": server_stubs.ListProcesses,
    "ReadLowLevel": server_stubs.ReadLowLevel,
    "OSXEnumerateRunningServices": server_stubs.OSXEnumerateRunningServices,
    "Osquery": server_stubs.Osquery,
    "PlistQuery": server_stubs.PlistQuery,
    "ReadBuffer": server_stubs.ReadBuffer,
    "Segfault": server_stubs.Segfault,
    "SendFile": server_stubs.SendFile,
    "SendStartupInfo": server_stubs.SendStartupInfo,
    "StatFS": server_stubs.StatFS,
    "StatFile": server_stubs.StatFile,
    "TransferBuffer": server_stubs.TransferBuffer,
    "Timeline": server_stubs.Timeline,
    "Uninstall": server_stubs.Uninstall,
    "UpdateAgent": server_stubs.UpdateAgent,
    "UpdateConfiguration": server_stubs.UpdateConfiguration,
    "VfsFileFinder": server_stubs.VfsFileFinder,
    "WmiQuery": server_stubs.WmiQuery,
    "YaraProcessDump": server_stubs.YaraProcessDump,
    "YaraProcessScan": server_stubs.YaraProcessScan,
}

ID_BY_ACTION_STUB = {stub: name for name, stub in ACTION_STUB_BY_ID.items()}


def RegisterAdditionalTestClientAction(action_cls):
  action_name = action_cls.__name__
  if action_name in ACTION_STUB_BY_ID:
    raise ValueError("Action identifier %s already taken." % action_name)

  ACTION_STUB_BY_ID[action_name] = action_cls
  ID_BY_ACTION_STUB[action_cls] = action_name
