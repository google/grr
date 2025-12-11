import {Any, DataBlob, FlowContext} from '../api/api_interfaces';
import {CollectionResult} from './result';

/** Flow type identificators */
export enum FlowType {
  // TODO: re-enable clang format when solved.
  // prettier-ignore
  // keep-sorted start block=yes
  ARTIFACT_COLLECTOR_FLOW = 'ArtifactCollectorFlow',
  CLIENT_FILE_FINDER = 'ClientFileFinder',
  CLIENT_REGISTRY_FINDER = 'ClientRegistryFinder',
  COLLECT_BROWSER_HISTORY = 'CollectBrowserHistory',
  COLLECT_CLOUD_VM_METADATA = 'CollectCloudVMMetadata',
  COLLECT_DISTRO_INFO = 'CollectDistroInfo',
  COLLECT_FILES_BY_KNOWN_PATH = 'CollectFilesByKnownPath',
  COLLECT_HARDWARE_INFO = 'CollectHardwareInfo',
  COLLECT_INSTALLED_SOFTWARE = 'CollectInstalledSoftware',
  COLLECT_LARGE_FILE_FLOW = 'CollectLargeFileFlow',
  COLLECT_MULTIPLE_FILES = 'CollectMultipleFiles',
  DELETE_GRR_TEMP_FILES = 'DeleteGRRTempFiles',
  DUMP_PROCESS_MEMORY = 'DumpProcessMemory',
  EXECUTE_PYTHON_HACK = 'ExecutePythonHack',
  FILE_FINDER = 'FileFinder',
  GET_CROWDSTRIKE_AGENT_ID = 'GetCrowdStrikeAgentID',
  GET_MBR = 'GetMBR',
  GET_MEMORY_SIZE = 'GetMemorySize',
  HASH_MULTIPLE_FILES = 'HashMultipleFiles',
  INTERROGATE = 'Interrogate',
  KILL = 'Kill',
  KNOWLEDGE_BASE_INITIALIZATION_FLOW = 'KnowledgeBaseInitializationFlow',
  LAUNCH_BINARY = 'LaunchBinary',
  LIST_CONTAINERS = 'ListContainers',
  LIST_DIRECTORY = 'ListDirectory',
  LIST_NAMED_PIPES_FLOW = 'ListNamedPipesFlow',
  LIST_PROCESSES = 'ListProcesses',
  LIST_RUNNING_SERVICES = 'ListRunningServices',
  LIST_VOLUME_SHADOW_COPIES = 'ListVolumeShadowCopies',
  MULTI_GET_FILE = 'MultiGetFile',
  NETSTAT = 'Netstat',
  ONLINE_NOTIFICATION = 'OnlineNotification',
  OS_QUERY_FLOW = 'OsqueryFlow',
  READ_LOW_LEVEL = 'ReadLowLevel',
  RECURSIVE_LIST_DIRECTORY = 'RecursiveListDirectory',
  REGISTRY_FINDER = 'RegistryFinder',
  STAT_MULTIPLE_FILES = 'StatMultipleFiles',
  TIMELINE_FLOW = 'TimelineFlow',
  UPDATE_CLIENT = 'UpdateClient',
  YARA_PROCESS_SCAN = 'YaraProcessScan',
  // keep-sorted end
}

/** Descriptor containing information about a flow class. */
export declare interface FlowDescriptor {
  readonly name: string;
  readonly friendlyName: string;
  readonly category: string;
  readonly defaultArgs: unknown;
  readonly blockHuntCreation: boolean;
}

/** Flow state enum to be used inside the Flow. */
export enum FlowState {
  UNSET = 0,
  RUNNING = 1,
  FINISHED = 2,
  ERROR = 3,
}

/** A Flow is a server-side process that collects data from clients. */
export declare interface Flow<Args extends {} | unknown = unknown> {
  readonly flowId: string;
  readonly clientId: string;
  readonly lastActiveAt: Date;
  readonly startedAt: Date;
  readonly name: string;
  readonly flowType: FlowType | undefined;
  readonly creator: string;
  readonly args: Args | undefined;
  readonly progress: unknown | undefined;
  readonly state: FlowState;
  readonly errorDescription: string | undefined;
  readonly isRobot: boolean;
  /**
   * Counts of flow Results. undefined for legacy flows where we don't know
   * about result metadata.
   */
  readonly resultCounts: readonly FlowResultCount[] | undefined;
  readonly nestedFlows: readonly Flow[] | undefined;

  readonly context: FlowContext | undefined;

  readonly store: Any | undefined;
}

/** FlowResultCount proto mapping. */
export declare interface FlowResultCount {
  readonly type: string;
  readonly tag?: string;
  readonly count: number;
}

/** FlowResult represents a single flow result. */
export declare interface FlowResult extends CollectionResult {
  readonly tag: string;
}

/**
 * Type guard for FlowResult.
 */
export function isFlowResult(result: CollectionResult): result is FlowResult {
  return (result as FlowResult).tag !== undefined;
}

/**
 * ListFlowResultsResult represents a list of flow results and the total count.
 */
export declare interface ListFlowResultsResult {
  readonly totalCount: number | undefined;
  readonly results: readonly FlowResult[];
}

/** FlowLogs represents a list and count of flow logs. */
export declare interface FlowLogs {
  readonly items: readonly FlowLog[];
  readonly totalCount: number | undefined;
}

/** FlowLog represents a single flow log. */
export declare interface FlowLog {
  readonly timestamp: Date;
  readonly logMessage: string | undefined;
}

/** OutputPluginLogEntryType model. */
export enum OutputPluginLogEntryType {
  UNSET = 'UNSET',
  LOG = 'LOG',
  ERROR = 'ERROR',
}

/** OutputPluginLogEntry model. */
export interface OutputPluginLogEntry {
  readonly flowId?: string;
  readonly clientId?: string;
  readonly huntId?: string;
  readonly outputPluginId?: string;
  readonly logEntryType?: OutputPluginLogEntryType;
  readonly timestamp?: Date;
  readonly message?: string;
}

/** List of output plugin logs. */
export interface ListAllOutputPluginLogsResult {
  readonly items: readonly OutputPluginLogEntry[];
  readonly totalCount?: number;
}

/**
 * FlowResultQuery encapsulates details of a flow results query. Queries
 * are used by flow details components to request data to show.
 */
export declare interface FlowResultsQuery {
  readonly flow: {
    readonly clientId: string;
    readonly flowId: string;
    readonly state?: FlowState;
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
  readonly flowType: FlowType | undefined;
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
  readonly dependencies: readonly string[];
  readonly pathDependencies: readonly string[];
  readonly sourceDescriptions: readonly ArtifactSourceDescription[];
  readonly artifacts: readonly ArtifactDescriptor[];
  readonly isCustom?: boolean;
}

/** Artifact Source information. */
export declare interface ArtifactSourceDescription {
  readonly type: SourceType;
  readonly supportedOs: ReadonlySet<OperatingSystem>;
  // Strings that describe the sources for display in the UI.
  readonly collections: string[];
}

/** SourceType proto mapping. */
export enum SourceType {
  COLLECTOR_TYPE_UNKNOWN,
  FILE,
  REGISTRY_KEY,
  REGISTRY_VALUE,
  WMI,
  PATH,
  COMMAND,
}

/** Operating systems. */
export enum OperatingSystem {
  LINUX = 'Linux',
  WINDOWS = 'Windows',
  DARWIN = 'Darwin',
}

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
  /** Lines of the standard output. */
  readonly stdout: string[];
  /** Lines of the standard error output. */
  readonly stderr: string[];
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

/** CollectLargeFileFlowResult proto mapping. */
export declare interface CollectLargeFileFlowResult {
  readonly sessionUri: string;
  readonly totalBytesSent: bigint | undefined;
}

/** ContainerDetails.ContainerState proto mapping. */
export enum ContainerState {
  UNKNOWN = 'UNKNOWN',
  CREATED = 'CREATED',
  RUNNING = 'RUNNING',
  PAUSED = 'PAUSED',
  EXITED = 'EXITED',
}

/** ContainerDetails.ContainerLabel proto mapping. */
export declare interface ContainerLabel {
  readonly key: string;
  readonly value: string;
}

/** ContainerDetails.ContainerCli proto mapping. */
export enum ContainerCli {
  UNSUPPORTED = 'UNSUPPORTED',
  CRICTL = 'CRICTL',
  DOCKER = 'DOCKER',
}

/** ContainerDetails proto mapping. */
export declare interface ContainerDetails {
  readonly containerId?: string;
  readonly imageName?: string;
  readonly command?: string;
  readonly createdAt?: Date;
  readonly status?: string;
  readonly ports?: readonly string[];
  readonly names?: readonly string[];
  readonly labels?: readonly ContainerLabel[];
  readonly localVolumes?: string;
  readonly mounts?: readonly string[];
  readonly networks?: readonly string[];
  readonly runningSince?: Date;
  readonly state?: ContainerState;
  readonly containerCli?: ContainerCli;
}

/** SoftwarePackage.InstallState proto mapping. */
export enum SoftwarePackageInstallState {
  INSTALLED = 'INSTALLED',
  PENDING = 'PENDING',
  UNINSTALLED = 'UNINSTALLED',
  UNKNOWN = 'UNKNOWN',
}

/** SoftwarePackage proto mapping. */
export declare interface SoftwarePackage {
  readonly name?: string;
  readonly version?: string;
  readonly architecture?: string;
  readonly publisher?: string;
  readonly installState?: SoftwarePackageInstallState;
  readonly description?: string;
  readonly installedOn?: Date;
  readonly installedBy?: string;
  readonly epoch?: number;
  readonly sourceRpm?: string;
  readonly sourceDeb?: string;
}

/** GetMemorySizeResult proto mapping. */
export declare interface GetMemorySizeResult {
  readonly totalBytes: bigint | undefined;
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
  readonly value: DataBlob;
}

const HASH_NAMES: {readonly [key in keyof HexHash]: string} = {
  'md5': 'MD5',
  'sha1': 'SHA-1',
  'sha256': 'SHA-256',
};

/**
 * Returns a readable name (e.g. SHA-256) of an internal hash name ("sha256").
 */
export function hashName(hashKey: keyof HexHash | string): string {
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
  readonly size?: bigint;
  readonly timestamp?: Date;
}
