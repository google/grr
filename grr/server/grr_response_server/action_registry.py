#!/usr/bin/env python
"""A mapping of client action id strings to action stub classes."""

from grr_response_server import server_stubs

ACTION_STUB_BY_ID = {
    "CollectLargeFile": server_stubs.CollectLargeFile,
    "CheckFreeGRRTempSpace": server_stubs.CheckFreeGRRTempSpace,
    "DeleteGRRTempFiles": server_stubs.DeleteGRRTempFiles,
    "Dummy": server_stubs.Dummy,
    "Echo": server_stubs.Echo,
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
    "ListContainers": server_stubs.ListContainers,
    "ListDirectory": server_stubs.ListDirectory,
    "ListNamedPipes": server_stubs.ListNamedPipes,
    "ListNetworkConnections": server_stubs.ListNetworkConnections,
    "ListProcesses": server_stubs.ListProcesses,
    "ReadLowLevel": server_stubs.ReadLowLevel,
    "OSXEnumerateRunningServices": server_stubs.OSXEnumerateRunningServices,
    "Osquery": server_stubs.Osquery,
    "ReadBuffer": server_stubs.ReadBuffer,
    "SendStartupInfo": server_stubs.SendStartupInfo,
    "StatFS": server_stubs.StatFS,
    "TransferBuffer": server_stubs.TransferBuffer,
    "Timeline": server_stubs.Timeline,
    "UpdateAgent": server_stubs.UpdateAgent,
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
