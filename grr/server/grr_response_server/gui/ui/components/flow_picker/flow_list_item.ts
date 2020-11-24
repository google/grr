import {Injectable} from '@angular/core';
import {from, Observable} from 'rxjs';

/**
 * FlowListItem encapsulates flow-related information used by the
 * flow picker component and its subcomponents.
 */
export interface FlowListItem {
  readonly name: string;
  readonly friendlyName: string;
  readonly description: string;
}

function fli(name: string, friendlyName: string, description: string = ''):
    FlowListItem {
  return {
    name,
    friendlyName,
    description,
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
    fli('CollectMultipleFiles', 'Collect multiple files',
        'Search for and collect files based on their path, content or stat'),
    fli('CollectSingleFile', 'Collect file',
        'Collect a single file from a well-defined path'),
    fli('ListDirectory', 'List directory',
        'Lists and stats all immediate files in directory'),
    fli('ListVolumeShadowCopies', 'List volume shadow copies'),
    fli('RecursiveListDirectory', 'List directory recursively',
        'Lists and stats all files in directory and its subdirectories'),
    fli('SendFile', 'Send file over network'),
    fli('TimelineFlow', 'Collect path timeline',
        'Collect metadata information for all files under the specified directory'),
  ],
  'Memory': [
    fli('DumpProcessMemory', 'Dump process memory',
        'Dump the process memory of one ore more processes'),
    fli('YaraProcessScan', 'Scan process memory with YARA',
        'Scan and optionally dump process memory using Yara'),
  ],
  'Administrative': [
    fli('ExecutePythonHack', 'Execute Python hack',
        'Execute a one-off Python script'),
    fli('Interrogate', 'Interrogate',
        'Collect general metadata about the client (e.g. operating system details, users, ...)'),
    fli('GetClientStats', 'Collect GRR statistics',
        'Collect agent statistics including processor, memory, and network usage'),
    fli('Kill', 'Kill GRR process'),
    fli('LaunchBinary', 'Execute binary hack',
        'Executes a binary from an allowlisted path'),
    fli('OnlineNotification', 'Notify when online',
        'Send an email notification when the GRR agent comes online'),
    fli('Uninstall', 'Uninstall GRR',
        'Permanently uninstall GRR from the host'),
    fli('UpdateClient', 'Update GRR client',
        'Update GRR on the host to the latest version'),
  ],
  'Processes': [
    fli('ListProcesses', 'List processes',
        'Collects metadata about running processes'),
  ],
  'Network': [
    fli('Netstat', 'Netstat', 'Enumerate all open network connections'),
  ],
  'Registry': [
    fli('RegistryFinder', 'Find registry keys/values'),
  ],
}));

/**
 * List of commonly used flow names.
 */
const COMMON_FLOW_NAMES: ReadonlyArray<string> = [
  'ArtifactCollectorFlow',
  'CollectBrowserHistory',
  'CollectMultipleFiles',
  'CollectSingleFile',
  'Interrogate',
  'OsqueryFlow',
  'TimelineFlow',
  'YaraProcessScan',
];


/**
 * Singleton providing access to global configuration settings.
 */
@Injectable({
  providedIn: 'root',
})
export class FlowListItemService {
  readonly flowsByCategory$: Observable<FlowsByCategory> =
      from([FLOWS_BY_CATEGORY]);
  readonly commonFlowNames$: Observable<ReadonlyArray<string>> =
      from([COMMON_FLOW_NAMES]);
}
