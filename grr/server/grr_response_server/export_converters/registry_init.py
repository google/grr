#!/usr/bin/env python
"""A mapping of export converters name and implementation."""

from grr_response_server import export_converters_registry
from grr_response_server.export_converters import buffer_reference
from grr_response_server.export_converters import check_result
from grr_response_server.export_converters import client_summary
from grr_response_server.export_converters import cron_tab_file
from grr_response_server.export_converters import execute_response
from grr_response_server.export_converters import file
from grr_response_server.export_converters import grr_message
from grr_response_server.export_converters import launchd_plist
from grr_response_server.export_converters import memory
from grr_response_server.export_converters import network
from grr_response_server.export_converters import osquery
from grr_response_server.export_converters import process
from grr_response_server.export_converters import rdf_dict
from grr_response_server.export_converters import rdf_primitives
from grr_response_server.export_converters import software_package
from grr_response_server.export_converters import windows_service_info


# TODO: Test that this function contains all inheritors.
def RegisterExportConverters():
  """Registers all ExportConverters."""
  # keep-sorted start
  export_converters_registry.Register(
      buffer_reference.BufferReferenceToExportedMatchConverter)
  export_converters_registry.Register(check_result.CheckResultConverter)
  export_converters_registry.Register(
      client_summary.ClientSummaryToExportedClientConverter)
  export_converters_registry.Register(
      client_summary.ClientSummaryToExportedNetworkInterfaceConverter)
  export_converters_registry.Register(cron_tab_file.CronTabFileConverter)
  export_converters_registry.Register(execute_response.ExecuteResponseConverter)
  export_converters_registry.Register(
      file.ArtifactFilesDownloaderResultConverter)
  export_converters_registry.Register(file.FileFinderResultConverter)
  export_converters_registry.Register(file.StatEntryToExportedFileConverter)
  export_converters_registry.Register(
      file.StatEntryToExportedRegistryKeyConverter)
  export_converters_registry.Register(grr_message.GrrMessageConverter)
  export_converters_registry.Register(launchd_plist.LaunchdPlistConverter)
  export_converters_registry.Register(memory.ProcessMemoryErrorConverter)
  export_converters_registry.Register(memory.YaraProcessScanMatchConverter)
  export_converters_registry.Register(
      network.DNSClientConfigurationToExportedDNSClientConfiguration)
  export_converters_registry.Register(
      network.InterfaceToExportedNetworkInterfaceConverter)
  export_converters_registry.Register(
      network.NetworkConnectionToExportedNetworkConnectionConverter)
  export_converters_registry.Register(osquery.OsqueryExportConverter)
  export_converters_registry.Register(
      process.ProcessToExportedNetworkConnectionConverter)
  export_converters_registry.Register(
      process.ProcessToExportedOpenFileConverter)
  export_converters_registry.Register(process.ProcessToExportedProcessConverter)
  export_converters_registry.Register(rdf_dict.DictToExportedDictItemsConverter)
  export_converters_registry.Register(
      rdf_primitives.RDFBytesToExportedBytesConverter)
  export_converters_registry.Register(
      rdf_primitives.RDFStringToExportedStringConverter)
  export_converters_registry.Register(software_package.SoftwarePackageConverter)
  export_converters_registry.Register(
      software_package.SoftwarePackagesConverter)
  export_converters_registry.Register(
      windows_service_info.WindowsServiceInformationConverter)
  # keep-sorted end
