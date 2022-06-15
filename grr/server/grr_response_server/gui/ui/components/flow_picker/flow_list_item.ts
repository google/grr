import {Injectable} from '@angular/core';
import {Observable} from 'rxjs';
import {map} from 'rxjs/operators';

import {transformMapValues} from '../../lib/type_utils';
import {ConfigGlobalStore} from '../../store/config_global_store';

/**
 * FlowListItem encapsulates flow-related information used by the
 * flow picker component and its subcomponents.
 */
export interface FlowListItem {
  readonly name: string;
  readonly friendlyName: string;
  readonly description: string;
  readonly enabled: boolean;
}

function fli(name: string, friendlyName: string, description: string = ''):
    FlowListItem {
  return {
    name,
    friendlyName,
    description,
    enabled: true,
  };
}

/**
 * Map of flow categories to flow list items.
 */
export type FlowsByCategory = ReadonlyMap<string, FlowListItem[]>;

/**
 * Flows, split by category, to be displayed by the flow picker.
 */
const FLOWS_BY_CATEGORY: FlowsByCategory = new Map(Object.entries({
  // TODO: Commented out flows do not have a proper flow form yet.
  // Hide them, to not show users an option that they cannot use.
  'Collectors': [
    fli('ArtifactCollectorFlow', 'Collect forensic artifacts'),
    fli('OsqueryFlow', 'Osquery', 'Execute a query using osquery'),
  ],
  'Browser': [
    fli('CollectBrowserHistory', 'Collect browser history',
        'Collect browsing and download history from Chrome, Firefox, Edge & Safari'),
  ],
  'Hardware': [
    fli('CollectEfiHashes', 'Collect EFI hashes',
        'Collect EFI volume hashes on macOS using eficheck'),
    fli('DumpACPITable', 'Dump ACPI table', 'Dump ACPI tables using chipsec'),
    fli('DumpEfiImage', 'Dump EFI image',
        'Dump the flash image on macOS using eficheck'),
    fli('DumpFlashImage', 'Dump flash image', 'Dump the flash image (BIOS)'),
    fli('GetMBR', 'Dump MBR', 'Dump the Master Boot Record on Windows'),
  ],
  'Filesystem': [
    fli('CollectFilesByKnownPath', 'Collect files from exact paths',
        'Collect one or more files based on their absolute paths'),
    fli('CollectMultipleFiles', 'Collect files by search criteria',
        'Search for and collect files based on their path, content or stat'),
    fli('ListDirectory', 'List directory',
        'Lists and stats all immediate files in directory'),
    // TODO:
    // fli('ListVolumeShadowCopies', 'List volume shadow copies'),
    // fli('RecursiveListDirectory', 'List directory recursively',
    // 'Lists and stats all files in directory and its subdirectories'),
    // fli('SendFile', 'Send file over network'),
    fli('TimelineFlow', 'Collect path timeline',
        'Collect metadata information for all files under the specified directory'),
    fli('ReadLowLevel', 'Read raw bytes from device',
        'Read raw data from a device - e.g. from a particular disk sector'),
  ],
  'Administrative': [
    fli('OnlineNotification', 'Online notification',
        'Notify via email when the client comes online'),
    fli('ExecutePythonHack', 'Execute Python hack',
        'Execute a one-off Python script'),
    fli('Interrogate', 'Interrogate',
        'Collect general metadata about the client (e.g. operating system details, users, ...)'),
    // TODO:
    // fli('GetClientStats', 'Collect GRR statistics',
    //     'Collect agent statistics including processor, memory, and network
    //     usage'),
    fli('Kill', 'Kill GRR process'),
    fli('LaunchBinary', 'Execute binary hack',
        'Executes a binary from an allowlisted path'),
    // TODO:
    // fli('OnlineNotification', 'Notify when online',
    //     'Send an email notification when the GRR agent comes online'),
    // fli('Uninstall', 'Uninstall GRR',
    //     'Permanently uninstall GRR from the host'),
    // fli('UpdateClient', 'Update GRR client',
    //     'Update GRR on the host to the latest version'),
  ],
  'Processes': [
    fli('ListProcesses', 'List processes',
        'Collects metadata about running processes'),
    fli('ListNamedPipesFlow', 'List named pipes',
        'Collects metadata about named pipes open on the system'),
    fli('DumpProcessMemory', 'Dump process memory',
        'Dump the process memory of one ore more processes'),
    fli('YaraProcessScan', 'Scan process memory with YARA',
        'Scan and optionally dump process memory using Yara'),
  ],
  'Network': [
    fli('Netstat', 'Netstat', 'Enumerate all open network connections'),
  ],
  // TODO:
  // 'Registry': [
  //   fli('RegistryFinder', 'Find registry keys/values'),
  // ],
}));

/**
 * List of commonly used flow names.
 */
const COMMON_FLOW_NAMES: ReadonlyArray<string> = [
  'ArtifactCollectorFlow',
  'CollectBrowserHistory',
  'Interrogate',
  'OsqueryFlow',
  'TimelineFlow',
];

const COMMON_FILE_FLOWS: ReadonlyArray<FlowListItem> = [
  fli('CollectFilesByKnownPath', 'Collect files from exact paths',
      'Collect one or more files based on their absolute paths'),
  fli('CollectMultipleFiles', 'Collect files by search criteria',
      'Search for and collect files based on their path, content or stat'),
];

/**
 * Singleton providing access to global configuration settings.
 */
@Injectable({
  providedIn: 'root',
})
export class FlowListItemService {
  constructor(private readonly configGlobalStore: ConfigGlobalStore) {}

  // TODO: Update the way "allowed flows" are computed,
  // once all FlowDescriptors, including restricted, are always returned from
  // ListFlowDescriptors API endpoint.
  readonly allowedFlowDescriptorNames$: Observable<ReadonlySet<string>> =
      this.configGlobalStore.flowDescriptors$.pipe(
          map(fds => new Set(Array.from(fds.values()).map(fd => fd.name))));

  readonly flowsByCategory$: Observable<FlowsByCategory> =
      this.allowedFlowDescriptorNames$.pipe(
          map(allowedNames => transformMapValues(
                  FLOWS_BY_CATEGORY,
                  entries => entries.map(
                      fli => ({...fli, enabled: allowedNames.has(fli.name)})))),
      );

  readonly commonFlowNames$: Observable<ReadonlyArray<string>> =
      this.allowedFlowDescriptorNames$.pipe(
          map(allowedNames =>
                  COMMON_FLOW_NAMES.filter(name => allowedNames.has(name))));

  readonly commonFileFlows$: Observable<ReadonlyArray<FlowListItem>> =
      this.allowedFlowDescriptorNames$.pipe(
          map(allowedNames =>
                  COMMON_FILE_FLOWS.filter(fli => allowedNames.has(fli.name))));
}
