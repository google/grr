import {EventEmitter} from '@angular/core';

import {isNonNull} from '../preconditions';

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
  readonly resultCounts: ReadonlyArray<FlowResultCount>|undefined;
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
  readonly urls: ReadonlyArray<string>;
  readonly provides: ReadonlyArray<string>;
  readonly sources: ReadonlyArray<ArtifactSource>;
  readonly dependencies: ReadonlyArray<string>;
  readonly pathDependencies: ReadonlyArray<string>;
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
  readonly conditions: ReadonlyArray<string>;
  readonly returnedTypes: ReadonlyArray<string>;
  readonly supportedOs: ReadonlySet<OperatingSystem>;
}

/** Generic Map with unknown, mixed, key and value types. */
export type AnyMap = ReadonlyMap<unknown, unknown>;

/** Artifact source that delegates to other artifacts. */
export interface ChildArtifactSource extends BaseArtifactSource {
  readonly type: SourceType.ARTIFACT_GROUP|SourceType.ARTIFACT_FILES;
  readonly names: ReadonlyArray<string>;
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
  readonly paths: ReadonlyArray<string>;
}

/** Artifact source that reads Windows Registry keys. */
export interface RegistryKeySource extends BaseArtifactSource {
  readonly type: SourceType.REGISTRY_KEY;
  readonly keys: ReadonlyArray<string>;
}

/** Artifact source that reads Windows Registry values. */
export interface RegistryValueSource extends BaseArtifactSource {
  readonly type: SourceType.REGISTRY_VALUE;
  readonly values: ReadonlyArray<string>;
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
  readonly args: ReadonlyArray<string>;
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
export const hashName = (hashKey: keyof HexHash|string) => {
  return HASH_NAMES[hashKey as keyof HexHash] ?? hashKey;
};

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
    resultCounts: ReadonlyArray<FlowResultCount>,
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

/**
 * An interface for @Component()s that can render flow/hunt results.
 * These components expect results to be preloaded and assigned to `data`.
 */
export interface PreloadedResultView<T> {
  /** @Input() */
  data: readonly T[];
}

/**
 * An interface for @Component()s that query and render flow results.
 *
 * These components expect `totalCount` to be provided. No results should be
 * preloaded. Instead, the component initiates loading results by emitting
 * loadResults.
 */
export interface PaginatedResultView<T> {
  /** @Input(): The results loaded with the query emitted from loadResults. */
  results?: readonly FlowResult[];

  /** @Input(): The total count of results that can be loaded. */
  totalCount: number;

  /** @Output(): Emits queries to initiate loading results. */
  readonly loadResults: EventEmitter<ResultQuery>;
}

/**
 * Returns true if the given view is a PaginatedResultView, meaning it triggers
 * loading its own results. This is unlike PreloadedResultView, that expects all
 * results to be provided up front.
 */
export function viewQueriesResults<T>(
    view: PreloadedResultView<T>|
    PaginatedResultView<T>): view is PaginatedResultView<T> {
  return isNonNull((view as PaginatedResultView<T>).loadResults);
}
