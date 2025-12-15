#!/usr/bin/env python
"""A mapping of export converters name and implementation."""

from grr_response_server import export_converters_registry
from grr_response_server.export_converters import auto_export_converters
from grr_response_server.export_converters import buffer_reference
from grr_response_server.export_converters import client_summary
from grr_response_server.export_converters import cron_tab_file
from grr_response_server.export_converters import dict as dict_converter
from grr_response_server.export_converters import execute_response
from grr_response_server.export_converters import file
from grr_response_server.export_converters import grr_message
from grr_response_server.export_converters import launchd_plist
from grr_response_server.export_converters import log_message
from grr_response_server.export_converters import memory
from grr_response_server.export_converters import network
from grr_response_server.export_converters import osquery
from grr_response_server.export_converters import process
from grr_response_server.export_converters import proto_wrappers
from grr_response_server.export_converters import rdf_dict
from grr_response_server.export_converters import rdf_primitives
from grr_response_server.export_converters import software_package


# TODO: Test that this function contains all inheritors.
def RegisterExportConverters():
  """Registers all ExportConverters."""
  export_converters_registry.Register(
      buffer_reference.BufferReferenceToExportedMatchConverter
  )
  export_converters_registry.RegisterProto(
      buffer_reference.BufferReferenceToExportedMatchConverterProto
  )
  export_converters_registry.Register(
      client_summary.ClientSummaryToExportedClientConverter
  )
  export_converters_registry.RegisterProto(
      client_summary.ClientSummaryToExportedClientConverterProto
  )
  export_converters_registry.Register(
      client_summary.ClientSummaryToExportedNetworkInterfaceConverter
  )
  export_converters_registry.RegisterProto(
      client_summary.ClientSummaryToExportedNetworkInterfaceConverterProto
  )
  export_converters_registry.Register(cron_tab_file.CronTabFileConverter)
  export_converters_registry.RegisterProto(
      cron_tab_file.CronTabFileToExportedCronTabEntryProto
  )
  export_converters_registry.RegisterProto(
      dict_converter.DictToExportedDictItemsConverterProto
  )
  export_converters_registry.Register(execute_response.ExecuteResponseConverter)
  export_converters_registry.RegisterProto(
      execute_response.ExecuteResponseConverterProto
  )
  export_converters_registry.Register(file.FileFinderResultConverter)
  export_converters_registry.RegisterProto(file.FileFinderResultConverterProto)
  export_converters_registry.Register(file.StatEntryToExportedFileConverter)
  export_converters_registry.RegisterProto(
      file.StatEntryToExportedFileConverterProto
  )
  export_converters_registry.Register(
      file.StatEntryToExportedRegistryKeyConverter
  )
  export_converters_registry.RegisterProto(
      file.StatEntryToExportedRegistryKeyConverterProto
  )
  export_converters_registry.RegisterProto(
      file.CollectMultipleFilesResultToExportedFileConverterProto
  )
  export_converters_registry.RegisterProto(
      file.CollectFilesByKnownPathResultToExportedFileConverterProto
  )
  export_converters_registry.Register(grr_message.GrrMessageConverter)
  export_converters_registry.Register(launchd_plist.LaunchdPlistConverter)
  export_converters_registry.RegisterProto(
      launchd_plist.LaunchdPlistConverterProto
  )
  export_converters_registry.RegisterProto(
      log_message.LogMessageToExportedStringConverter
  )
  export_converters_registry.Register(memory.ProcessMemoryErrorConverter)
  export_converters_registry.RegisterProto(
      memory.ProcessMemoryErrorConverterProto
  )
  export_converters_registry.Register(memory.YaraProcessScanMatchConverter)
  export_converters_registry.RegisterProto(
      memory.YaraProcessScanMatchConverterProto
  )
  export_converters_registry.Register(
      network.DNSClientConfigurationToExportedDNSClientConfiguration
  )
  export_converters_registry.RegisterProto(
      network.DNSClientConfigurationToExportedDNSClientConfigurationProto
  )
  export_converters_registry.Register(
      network.InterfaceToExportedNetworkInterfaceConverter
  )
  export_converters_registry.RegisterProto(
      network.InterfaceToExportedNetworkInterfaceConverterProto
  )
  export_converters_registry.Register(
      network.NetworkConnectionToExportedNetworkConnectionConverter
  )
  export_converters_registry.Register(osquery.OsqueryExportConverter)
  export_converters_registry.RegisterProto(
      osquery.OsqueryTableExportConverterProto
  )
  export_converters_registry.RegisterProto(
      osquery.OsqueryResultExportConverterProto
  )
  export_converters_registry.Register(
      process.ProcessToExportedNetworkConnectionConverter
  )
  export_converters_registry.RegisterProto(
      process.ProcessToExportedNetworkConnectionConverterProto
  )
  export_converters_registry.Register(
      process.ProcessToExportedOpenFileConverter
  )
  export_converters_registry.RegisterProto(
      process.ProcessToExportedOpenFileConverterProto
  )
  export_converters_registry.RegisterProto(
      process.ProcessToExportedProcessConverterProto
  )
  export_converters_registry.RegisterProto(
      proto_wrappers.BytesValueToExportedBytesConverter
  )
  export_converters_registry.RegisterProto(
      proto_wrappers.StringValueToExportedStringConverter
  )
  export_converters_registry.Register(process.ProcessToExportedProcessConverter)
  export_converters_registry.Register(rdf_dict.DictToExportedDictItemsConverter)
  export_converters_registry.Register(
      rdf_primitives.RDFBytesToExportedBytesConverter
  )
  export_converters_registry.Register(
      rdf_primitives.RDFStringToExportedStringConverter
  )
  export_converters_registry.Register(software_package.SoftwarePackageConverter)
  export_converters_registry.RegisterProto(
      software_package.SoftwarePackageConverterProto
  )
  export_converters_registry.Register(
      software_package.SoftwarePackagesConverter
  )
  export_converters_registry.RegisterProto(
      software_package.SoftwarePackagesConverterProto
  )


def RegisterAutoGeneratedExportConverters():
  """Registers all auto-generated ExportConverters."""
  export_converters_registry.RegisterProto(
      auto_export_converters.BytesValueToAutoGeneratedExportedBytesValue1Converter
  )
  export_converters_registry.RegisterProto(
      auto_export_converters.ClientSnapshotToAutoGeneratedExportedClientSnapshot1Converter
  )
  export_converters_registry.RegisterProto(
      auto_export_converters.CollectBrowserHistoryResultToAutoGeneratedExportedCollectBrowserHistoryResult1Converter
  )
  export_converters_registry.RegisterProto(
      auto_export_converters.CollectCloudVMMetadataResultToAutoGeneratedExportedCollectCloudVMMetadataResult1Converter
  )
  export_converters_registry.RegisterProto(
      auto_export_converters.CollectDistroInfoResultToAutoGeneratedExportedCollectDistroInfoResult1Converter
  )
  export_converters_registry.RegisterProto(
      auto_export_converters.CollectLargeFileFlowResultToAutoGeneratedExportedCollectLargeFileFlowResult1Converter
  )
  export_converters_registry.RegisterProto(
      auto_export_converters.DummyFlowResultToAutoGeneratedExportedDummyFlowResult1Converter
  )
  export_converters_registry.RegisterProto(
      auto_export_converters.ExecuteBinaryResponseToAutoGeneratedExportedExecuteBinaryResponse1Converter
  )
  export_converters_registry.RegisterProto(
      auto_export_converters.ExecutePythonHackResultToAutoGeneratedExportedExecutePythonHackResult1Converter
  )
  export_converters_registry.RegisterProto(
      auto_export_converters.GetCrowdstrikeAgentIdResultToAutoGeneratedExportedGetCrowdstrikeAgentIdResult1Converter
  )
  export_converters_registry.RegisterProto(
      auto_export_converters.GetMemorySizeResultToAutoGeneratedExportedGetMemorySizeResult1Converter
  )
  export_converters_registry.RegisterProto(
      auto_export_converters.HardwareInfoToAutoGeneratedExportedHardwareInfo1Converter
  )
  export_converters_registry.RegisterProto(
      auto_export_converters.KnowledgeBaseToAutoGeneratedExportedKnowledgeBase1Converter
  )
  export_converters_registry.RegisterProto(
      auto_export_converters.ListContainersFlowResultToAutoGeneratedExportedListContainersFlowResult1Converter
  )
  export_converters_registry.RegisterProto(
      auto_export_converters.ListNamedPipesFlowResultToAutoGeneratedExportedListNamedPipesFlowResult1Converter
  )
  export_converters_registry.RegisterProto(
      auto_export_converters.NetworkConnectionToAutoGeneratedExportedNetworkConnection1Converter
  )
  export_converters_registry.RegisterProto(
      auto_export_converters.OSXServiceInformationToAutoGeneratedExportedOSXServiceInformation1Converter
  )
  export_converters_registry.RegisterProto(
      auto_export_converters.ReadLowLevelFlowResultToAutoGeneratedExportedReadLowLevelFlowResult1Converter
  )
  export_converters_registry.RegisterProto(
      auto_export_converters.TimelineResultToAutoGeneratedExportedTimelineResult1Converter
  )
  export_converters_registry.RegisterProto(
      auto_export_converters.YaraProcessDumpResponseToAutoGeneratedExportedYaraProcessDumpResponse1Converter
  )
  export_converters_registry.RegisterProto(
      auto_export_converters.YaraProcessScanMissToAutoGeneratedExportedYaraProcessScanMiss1Converter
  )
