import {Directive, Injectable} from '@angular/core';
import {Observable} from 'rxjs';

/** Flow type identificators */
export enum FlowType {
  ARTIFACT_COLLECTOR_FLOW = 'ArtifactCollectorFlow',
  OS_QUERY_FLOW = 'OsqueryFlow',
  COLLECT_BROWSER_HISTORY = 'CollectBrowserHistory',
  COLLECT_EFI_HASHES = 'CollectEfiHashes',
  DUMP_ACPI_TABLE = 'DumpACPITable',
  DUMP_EFI_IMAGE = 'DumpEfiImage',
  DUMP_FLASH_IMAGE = 'DumpFlashImage',
  GET_MBR = 'GetMBR',
  COLLECT_FILES_BY_KNOWN_PATH = 'CollectFilesByKnownPath',
  COLLECT_MULTIPLE_FILES = 'CollectMultipleFiles',
  LIST_DIRECTORY = 'ListDirectory',
  TIMELINE_FLOW = 'TimelineFlow',
  READ_LOW_LEVEL = 'ReadLowLevel',
  ONLINE_NOTIFICATION = 'OnlineNotification',
  EXECUTE_PYTHON_HACK = 'ExecutePythonHack',
  INTERROGATE = 'Interrogate',
  KILL = 'Kill',
  LAUNCH_BINARY = 'LaunchBinary',
  LIST_PROCESSES = 'ListProcesses',
  LIST_NAMED_PIPES_FLOW = 'ListNamedPipesFlow',
  DUMP_PROCESS_MEMORY = 'DumpProcessMemory',
  YARA_PROCESS_SCAN = 'YaraProcessScan',
  NETSTAT = 'Netstat',
  COLLECT_SINGLE_FILE = 'CollectSingleFile',
  COLLECT_RUNKEY_BINARIES = 'CollectRunKeyBinaries',
  GET_CLIENT_STATS = 'GetClientStats',
  LIST_VOLUME_SHADOW_COPIES = 'ListVolumeShadowCopies',
  CLIENT_FILE_FINDER = 'ClientFileFinder',
  FILE_FINDER = 'FileFinder',
  MULTI_GET_FILE = 'MultiGetFile',
  RECURSIVE_LIST_DIRECTORY = 'RecursiveListDirectory',
  YARA_PROCESS_SCAN_WITH_PMI_EXPORT = 'YaraProcessScanWithPMIExport',
}

/**
 * FlowListItem encapsulates flow-related information.
 */
export interface FlowListItem {
  readonly type: FlowType;
  readonly friendlyName: string;
  readonly description: string;
  readonly enabled: boolean;
}

function fli(
    type: FlowType, friendlyName: string, description = ''): FlowListItem {
  return {
    type,
    friendlyName,
    description,
    enabled: true,
  };
}

/**
 * Map of flow types to flow list items.
 */
export type FlowsByTypeMap = {
  [key in FlowType]?: FlowListItem
};

/**
 * Flow list items, indexed by their names.
 */
export const FLOW_LIST_ITEMS_BY_TYPE: FlowsByTypeMap = {
  [FlowType.ARTIFACT_COLLECTOR_FLOW]:
      fli(FlowType.ARTIFACT_COLLECTOR_FLOW, 'Collect forensic artifacts'),
  [FlowType.OS_QUERY_FLOW]:
      fli(FlowType.OS_QUERY_FLOW, 'Osquery', 'Execute a query using osquery'),
  [FlowType.COLLECT_BROWSER_HISTORY]: fli(
      FlowType.COLLECT_BROWSER_HISTORY, 'Collect browser history',
      'Collect browsing and download history from Chrome, Firefox, Edge & Safari'),
  [FlowType.COLLECT_EFI_HASHES]:
      fli(FlowType.COLLECT_EFI_HASHES, 'Collect EFI hashes',
          'Collect EFI volume hashes on macOS using eficheck'),
  [FlowType.DUMP_ACPI_TABLE]:
      fli(FlowType.DUMP_ACPI_TABLE, 'Dump ACPI table',
          'Dump ACPI tables using chipsec'),
  [FlowType.DUMP_EFI_IMAGE]:
      fli(FlowType.DUMP_EFI_IMAGE, 'Dump EFI image',
          'Dump the flash image on macOS using eficheck'),
  [FlowType.DUMP_FLASH_IMAGE]:
      fli(FlowType.DUMP_FLASH_IMAGE, 'Dump flash image',
          'Dump the flash image (BIOS)'),
  [FlowType.GET_MBR]: fli(
      FlowType.GET_MBR, 'Dump MBR', 'Dump the Master Boot Record on Windows'),
  [FlowType.COLLECT_FILES_BY_KNOWN_PATH]: fli(
      FlowType.COLLECT_FILES_BY_KNOWN_PATH, 'Collect files from exact paths',
      'Collect one or more files based on their absolute paths'),
  [FlowType.COLLECT_MULTIPLE_FILES]:
      fli(FlowType.COLLECT_MULTIPLE_FILES, 'Collect files by search criteria',
          'Search for and collect files based on their path, content or stat'),
  [FlowType.LIST_DIRECTORY]:
      fli(FlowType.LIST_DIRECTORY, 'List directory',
          'Lists and stats all immediate files in directory'),
  [FlowType.TIMELINE_FLOW]: fli(
      FlowType.TIMELINE_FLOW, 'Collect path timeline',
      'Collect metadata information for all files under the specified directory'),
  [FlowType.READ_LOW_LEVEL]:
      fli(FlowType.READ_LOW_LEVEL, 'Read raw bytes from device',
          'Read raw data from a device - e.g. from a particular disk sector'),
  [FlowType.ONLINE_NOTIFICATION]:
      fli(FlowType.ONLINE_NOTIFICATION, 'Online notification',
          'Notify via email when the client comes online'),
  [FlowType.EXECUTE_PYTHON_HACK]:
      fli(FlowType.EXECUTE_PYTHON_HACK, 'Execute Python hack',
          'Execute a one-off Python script'),
  [FlowType.INTERROGATE]: fli(
      FlowType.INTERROGATE, 'Interrogate',
      'Collect general metadata about the client (e.g. operating system details, users, ...)'),
  [FlowType.KILL]: fli(FlowType.KILL, 'Kill GRR process'),
  [FlowType.LAUNCH_BINARY]:
      fli(FlowType.LAUNCH_BINARY, 'Execute binary hack',
          'Executes a binary from an allowlisted path'),
  [FlowType.LIST_PROCESSES]:
      fli(FlowType.LIST_PROCESSES, 'List processes',
          'Collects metadata about running processes'),
  [FlowType.LIST_NAMED_PIPES_FLOW]:
      fli(FlowType.LIST_NAMED_PIPES_FLOW, 'List named pipes',
          'Collects metadata about named pipes open on the system'),
  [FlowType.DUMP_PROCESS_MEMORY]:
      fli(FlowType.DUMP_PROCESS_MEMORY, 'Dump process memory',
          'Dump the process memory of one ore more processes'),
  [FlowType.YARA_PROCESS_SCAN]:
      fli(FlowType.YARA_PROCESS_SCAN, 'Scan process memory with YARA',
          'Scan and optionally dump process memory using Yara'),
  [FlowType.NETSTAT]: fli(
      FlowType.NETSTAT, 'Netstat', 'Enumerate all open network connections'),
};

/** Unknown flow title, used as fallback in case there is no name. */
export const UNKNOWN_FLOW_TITLE = 'Unknown flow';

/** Gets the flow title to be displayed across different pages */
export function getFlowTitleFromFlowName(
    flowName: string|undefined, desc?: FlowDescriptor|null): string {
  const flowItem = FLOW_LIST_ITEMS_BY_TYPE[flowName as FlowType];

  return flowItem?.friendlyName || desc?.friendlyName || flowName ||
      UNKNOWN_FLOW_TITLE;
}

/** Gets the flow title to be displayed across different pages */
export function getFlowTitleFromFlow(
    flow: Flow|null, desc: FlowDescriptor|null): string {
  return getFlowTitleFromFlowName(flow?.name, desc);
}

/** Descriptor containing information about a flow class. */
export declare interface FlowDescriptor {
  readonly name: string;
  readonly friendlyName: string;
  readonly category: string;
  readonly defaultArgs: unknown;
}

/** Map from Flow name to FlowDescriptor. */
export type FlowDescriptorMap = ReadonlyMap<string, FlowDescriptor>;

/** Flow state enum to be used inside the Flow. */
export enum FlowState {
  UNSET = 0,
  RUNNING = 1,
  FINISHED = 2,
  ERROR = 3,
}

/** A Flow is a server-side process that collects data from clients. */
export declare interface Flow<Args extends {}|unknown = unknown> {
  readonly flowId: string;
  readonly clientId: string;
  readonly lastActiveAt: Date;
  readonly startedAt: Date;
  readonly name: string;
  readonly creator: string;
  readonly args: Args|undefined;
  readonly progress: unknown|undefined;
  readonly state: FlowState;
  readonly errorDescription: string|undefined;
  readonly isRobot: boolean;
  /**
   * Counts of flow Results. undefined for legacy flows where we don't know
   * about result metadata.
   */
  readonly resultCounts: readonly FlowResultCount[]|undefined;
}

/**
 * FlowWithDescriptor holds flow and descriptor which are necessary for a flow
 * card.
 */
export interface FlowWithDescriptor {
  readonly flow: Flow;
  readonly descriptor?: FlowDescriptor;
  readonly flowArgType?: string;
}

/** FlowResultCount proto mapping. */
export declare interface FlowResultCount {
  readonly type: string;
  readonly tag?: string;
  readonly count: number;
}

/** FlowResult represents a single flow result. */
export declare interface FlowResult {
  readonly payloadType: string;
  readonly payload: unknown;
  readonly tag: string;
  readonly timestamp: Date;
}

/**
 * FlowResultQuery encapsulates details of a flow results query. Queries
 * are used by flow details components to request data to show.
 */
export declare interface FlowResultsQuery {
  readonly flow : {
    readonly clientId: string,
    readonly flowId: string,
    readonly state?: FlowState,
  };
  readonly withTag?: string;
  readonly withType?: string;
  readonly offset?: number;
  readonly count?: number;
}

/** A scheduled flow, to be executed after approval has been granted. */
export declare interface ScheduledFlow {
  readonly scheduledFlowId: string;
  readonly clientId: string;
  readonly creator: string;
  readonly flowName: string;
  readonly flowArgs: unknown;
  readonly createTime: Date;
  readonly error?: string;
}

/** Hex-encoded hashes. */
export declare interface HexHash {
  readonly sha256?: string;
  readonly sha1?: string;
  readonly md5?: string;
}


/** Map from Artifact name to ArtifactDescriptor. */
export type ArtifactDescriptorMap = ReadonlyMap<string, ArtifactDescriptor>;

/** Combine both Artifact and ArtifactDescriptor from the backend */
export interface ArtifactDescriptor {
  readonly name: string;
  readonly doc?: string;
  readonly supportedOs: ReadonlySet<OperatingSystem>;
  readonly urls: readonly string[];
  readonly provides: readonly string[];
  readonly sources: readonly ArtifactSource[];
  readonly dependencies: readonly string[];
  readonly pathDependencies: readonly string[];
  readonly isCustom?: boolean;
}

/** SourceType proto mapping. */
export enum SourceType {
  COLLECTOR_TYPE_UNKNOWN,
  FILE,
  REGISTRY_KEY,
  REGISTRY_VALUE,
  WMI,
  ARTIFACT,
  PATH,
  DIRECTORY,
  ARTIFACT_GROUP,
  GRR_CLIENT_ACTION,
  LIST_FILES,
  ARTIFACT_FILES,
  GREP,
  COMMAND,
  REKALL_PLUGIN,
}

/** Operating systems. */
export enum OperatingSystem {
  LINUX = 'Linux',
  WINDOWS = 'Windows',
  DARWIN = 'Darwin',
}

/** Artifact source. */
interface BaseArtifactSource {
  readonly type: SourceType;
  readonly conditions: readonly string[];
  readonly returnedTypes: readonly string[];
  readonly supportedOs: ReadonlySet<OperatingSystem>;
}

/** Generic Map with unknown, mixed, key and value types. */
export type AnyMap = ReadonlyMap<unknown, unknown>;

/** Artifact source that delegates to other artifacts. */
export interface ChildArtifactSource extends BaseArtifactSource {
  readonly type: SourceType.ARTIFACT_GROUP|SourceType.ARTIFACT_FILES;
  readonly names: readonly string[];
}

/** Artifact source that delegates to a ClientAction. */
export interface ClientActionSource extends BaseArtifactSource {
  readonly type: SourceType.GRR_CLIENT_ACTION;
  readonly clientAction: string;
}

/** Artifact source that delegates to a shell command. */
export interface CommandSource extends BaseArtifactSource {
  readonly type: SourceType.COMMAND;
  readonly cmdline: string;
}

/** Artifact source that reads files. */
export interface FileSource extends BaseArtifactSource {
  readonly type: SourceType.DIRECTORY|SourceType.FILE|SourceType.GREP|
      SourceType.PATH;
  readonly paths: readonly string[];
}

/** Artifact source that reads Windows Registry keys. */
export interface RegistryKeySource extends BaseArtifactSource {
  readonly type: SourceType.REGISTRY_KEY;
  readonly keys: readonly string[];
}

/** Artifact source that reads Windows Registry values. */
export interface RegistryValueSource extends BaseArtifactSource {
  readonly type: SourceType.REGISTRY_VALUE;
  readonly values: readonly string[];
}

/** Artifact source that queries WMI. */
export interface WmiSource extends BaseArtifactSource {
  readonly type: SourceType.WMI;
  readonly query: string;
}

/** Unknown artifact source. */
export interface UnknownSource extends BaseArtifactSource {
  readonly type: SourceType.COLLECTOR_TYPE_UNKNOWN;
}

/** Artifact source. */
export type ArtifactSource =
    ChildArtifactSource|ClientActionSource|CommandSource|FileSource|
    RegistryKeySource|RegistryValueSource|WmiSource|UnknownSource;

/** ExecuteRequest proto mapping. */
export declare interface ExecuteRequest {
  readonly cmd: string;
  readonly args: readonly string[];
  readonly timeLimitSeconds: number;
}

/** ExecuteResponse proto mapping. */
export declare interface ExecuteResponse {
  readonly request: ExecuteRequest;
  readonly exitStatus: number;
  readonly stdout: string;
  readonly stderr: string;
  readonly timeUsedSeconds: number;
}

/** ExecuteBinaryResponse proto mapping. */
export declare interface ExecuteBinaryResponse {
  readonly exitStatus: number;
  readonly stdout: string;
  readonly stderr: string;
  readonly timeUsedSeconds: number;
}

/** ArtifactProgress proto mapping. */
export declare interface ArtifactProgress {
  readonly name: string;
  // For legacy reasons, numResults can be unknown.
  readonly numResults?: number;
}

/** ArtifactCollectorFlowProgress proto mapping. */
export declare interface ArtifactCollectorFlowProgress {
  readonly artifacts: ReadonlyMap<string, ArtifactProgress>;
}

/** A Windows Registry Key. */
export declare interface RegistryKey {
  readonly path: string;
  readonly type: 'REG_KEY';
}

/** RegistryType proto mapping. */
export enum RegistryType {
  REG_NONE = 'REG_NONE',
  REG_SZ = 'REG_SZ',
  REG_EXPAND_SZ = 'REG_EXPAND_SZ',
  REG_BINARY = 'REG_BINARY',
  REG_DWORD = 'REG_DWORD',
  REG_DWORD_LITTLE_ENDIAN = 'REG_DWORD_LITTLE_ENDIAN',
  REG_DWORD_BIG_ENDIAN = 'REG_DWORD_BIG_ENDIAN',
  REG_LINK = 'REG_LINK',
  REG_MULTI_SZ = 'REG_MULTI_SZ',
  REG_QWORD = 'REG_QWORD',
}

/** A Windows Registry Value. */
export declare interface RegistryValue {
  readonly path: string;
  readonly type: RegistryType;
  readonly size: BigInt;
}

const HASH_NAMES: {readonly[key in keyof HexHash]: string} = {
  'md5': 'MD5',
  'sha1': 'SHA-1',
  'sha256': 'SHA-256',
};

/**
 * Returns a readable name (e.g. SHA-256) of an internal hash name ("sha256").
 */
export function hashName(hashKey: keyof HexHash|string): string {
  return HASH_NAMES[hashKey as keyof HexHash] ?? hashKey;
}

/** Type of executable binaries. */
export enum BinaryType {
  PYTHON_HACK = 'PYTHON_HACK',
  EXECUTABLE = 'EXECUTABLE',
}

/** Executable files, e.g. Python hacks or uploaded executables. */
export declare interface Binary {
  readonly type: BinaryType;
  readonly path: string;
  readonly size: bigint;
  readonly timestamp: Date;
}

/** Counts flow results matching a type and/or tag. */
export function countFlowResults(
    resultCounts: readonly FlowResultCount[],
    match: {type?: string, tag?: string}) {
  let count = 0;

  for (const rc of resultCounts) {
    if ((match.tag && rc.tag !== match.tag) ||
        (match.type && rc.type !== match.type)) {
      continue;
    }

    count += rc.count;
  }

  return count;
}

/** Adds the corresponding FlowDescriptor to a Flow, if existent. */
export function withDescriptor(fds: FlowDescriptorMap):
    ((flow: Flow) => FlowWithDescriptor) {
  return flow => ({
           flow,
           descriptor: fds.get(flow.name),
         });
}


/** A query to load `count` results starting at `offset`. */
export interface ResultQuery {
  readonly offset: number;
  readonly count: number;
}

/** A query describing what type & tag of flow/hunt results to load. */
export interface ResultTypeQuery {
  readonly type?: string;
  readonly tag?: string;
}

/**
 * An interface for @Component()s that can render flow/hunt results.
 * These components expect results to be preloaded and assigned to `data`.
 */
export interface PreloadedResultView<T> {
  /** @Input() */
  data: readonly T[];
}

/**
 * A base class for @Component()s that query and render flow results.
 *
 * This Component injects ResultSource and handles initiates loading results,
 * e.g. based on pagination.
 */
@Directive()
export abstract class PaginatedResultView<T> {
  constructor(protected readonly resultSource: ResultSource<T>) {}
}

/**
 * An abstraction over flow and hunt result sources, e.g. delegating result
 * queries to FlowResultsLocalStore. Used by PaginatedResultView.
 */
@Injectable()
export abstract class ResultSource<T> {
  readonly abstract results$: Observable<readonly FlowResult[]>;
  readonly abstract totalCount$: Observable<number>;
  readonly abstract query$: Observable<ResultTypeQuery>;
  abstract loadResults(query: ResultQuery): void;
}

/**
 * Returns true if the given view is a PaginatedResultView, meaning it triggers
 * loading its own results. This is unlike PreloadedResultView, that expects all
 * results to be provided up front.
 */
export function viewQueriesResults<T>(
    view: PreloadedResultView<T>|
    PaginatedResultView<T>): view is PaginatedResultView<T> {
  return view instanceof PaginatedResultView;
}
