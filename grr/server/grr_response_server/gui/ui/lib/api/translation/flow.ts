import {
  ArtifactCollectorFlowProgress,
  ArtifactProgress,
  Binary,
  BinaryType,
  CollectLargeFileFlowResult,
  ContainerCli,
  ContainerDetails,
  ContainerLabel,
  ContainerState,
  ExecuteBinaryResponse,
  ExecuteResponse,
  Flow,
  FlowDescriptor,
  FlowLog,
  FlowLogs,
  FlowResult,
  FlowResultCount,
  FlowState,
  FlowType,
  GetMemorySizeResult,
  HexHash,
  ListAllOutputPluginLogsResult,
  ListFlowResultsResult,
  OperatingSystem,
  OutputPluginLogEntry,
  OutputPluginLogEntryType,
  RegistryKey,
  RegistryType,
  RegistryValue,
  ScheduledFlow,
  SoftwarePackage,
  SoftwarePackageInstallState,
} from '../../models/flow';
import {typeUrlToPayloadType} from '../../models/result';
import {PathSpec, PathSpecSegment, StatEntry} from '../../models/vfs';
import {
  PreconditionError,
  assertEnum,
  assertKeyNonNull,
  assertNonNull,
  isEnum,
} from '../../preconditions';
import {checkExhaustive} from '../../utils';
import * as apiInterfaces from '../api_interfaces';
import {
  bytesToHex,
  createDate,
  createOptionalBigInt,
  createOptionalDateSeconds,
  createUnknownObject,
  decodeBase64,
} from './primitive';

/** Constructs a FlowDescriptor from the corresponding API data structure */
export function translateFlowDescriptor(
  fd: apiInterfaces.ApiFlowDescriptor,
): FlowDescriptor {
  assertKeyNonNull(fd, 'name');
  assertKeyNonNull(fd, 'category');
  assertKeyNonNull(fd, 'defaultArgs');
  assertKeyNonNull(fd, 'blockHuntCreation');

  const result = {
    name: fd.name,
    friendlyName: fd.friendlyName || fd.name,
    blockHuntCreation: fd.blockHuntCreation,
    category: fd.category,
    defaultArgs: {...fd.defaultArgs},
  };
  // The protobuf type URL is an implementation detail of the API, thus we
  // remove if from defaultArgs.
  delete result.defaultArgs['@type'];
  return result;
}

function translateApiFlowState(state: apiInterfaces.ApiFlowState): FlowState {
  if (state === apiInterfaces.ApiFlowState.RUNNING) {
    return FlowState.RUNNING;
  } else if (state === apiInterfaces.ApiFlowState.TERMINATED) {
    return FlowState.FINISHED;
  } else {
    // Map ERROR, CLIENT_CRASHED, and any future enum addition to ERROR.
    return FlowState.ERROR;
  }
}

/** Translates an API flow name to a FlowType. */
export function translateApiFlowType(flowName: string): FlowType | undefined {
  if (Object.values(FlowType).includes(flowName as FlowType)) {
    return flowName as FlowType;
  }
  return undefined;
}

/** Constructs a Flow from the corresponding API data structure. */
export function translateFlow(apiFlow: apiInterfaces.ApiFlow): Flow {
  assertKeyNonNull(apiFlow, 'flowId');
  assertKeyNonNull(apiFlow, 'clientId');
  assertKeyNonNull(apiFlow, 'lastActiveAt');
  assertKeyNonNull(apiFlow, 'startedAt');
  assertKeyNonNull(apiFlow, 'name');
  assertKeyNonNull(apiFlow, 'state');
  assertKeyNonNull(apiFlow, 'isRobot');

  let resultCounts: readonly FlowResultCount[] | undefined;

  // For legacy flows where isMetadataSet is unset, we need to be careful to
  // differentiate between a flow that has no numResultsPerTypeTag because it
  // has 0 results and a flow that has results but has numResultsPerTypeTag
  // unset because it was executed before we added this field. Thus, only set
  // resultCounts if it contains results OR we are sure that missing
  // numResultsPerTypeTag really means the flow has 0 results.
  if (
    apiFlow.resultMetadata?.isMetadataSet ||
    apiFlow.resultMetadata?.numResultsPerTypeTag?.length
  ) {
    resultCounts = (apiFlow.resultMetadata.numResultsPerTypeTag ?? []).map(
      (rc) => {
        assertKeyNonNull(rc, 'type');
        return {
          type: rc.type,
          tag: rc.tag,
          count: Number(rc.count),
        };
      },
    );
  }

  return {
    flowId: apiFlow.flowId,
    clientId: apiFlow.clientId,
    lastActiveAt: createDate(apiFlow.lastActiveAt),
    startedAt: createDate(apiFlow.startedAt),
    name: apiFlow.name,
    flowType: translateApiFlowType(apiFlow.name),
    creator: apiFlow.creator || 'unknown',
    args: createUnknownObject(apiFlow.args),
    progress: createUnknownObject(apiFlow.progress),
    state: translateApiFlowState(apiFlow.state),
    errorDescription: apiFlow.errorDescription ?? undefined,
    resultCounts,
    isRobot: apiFlow.isRobot,
    nestedFlows:
      apiFlow.nestedFlows?.map((apiFlow) => translateFlow(apiFlow)) ??
      undefined,
    context: apiFlow.context,
    store: apiFlow.store ?? undefined,
  };
}

/** Construct a FlowResult model object, corresponding to ApiFlowResult.  */
export function translateFlowResult(
  clientId: string,
  apiFlowResult: apiInterfaces.ApiFlowResult,
): FlowResult {
  assertKeyNonNull(apiFlowResult, 'payload');
  assertKeyNonNull(apiFlowResult, 'timestamp');

  return {
    clientId,
    payload: createUnknownObject(apiFlowResult.payload),
    payloadType:
      typeUrlToPayloadType(apiFlowResult.payload?.['@type']) ?? undefined,
    tag: apiFlowResult.tag ?? '',
    timestamp: createDate(apiFlowResult.timestamp),
  };
}

/**
 * Constructs a ListFlowResultsResult from the corresponding
 * ApiListFlowResultsResult.
 */
export function translateListFlowResultsResult(
  clientId: string,
  apiListFlowResultsResult: apiInterfaces.ApiListFlowResultsResult,
): ListFlowResultsResult {
  const totalCount = apiListFlowResultsResult.totalCount;
  return {
    totalCount: totalCount ? Number(totalCount) : undefined,
    results:
      apiListFlowResultsResult.items?.map((result) => {
        return translateFlowResult(clientId, result);
      }) ?? [],
  };
}

/**
 * Constructs a FlowLogs from the corresponding ApiListFlowLogsResult.
 */
export function translateFlowLogs(
  apiFlowLog: apiInterfaces.ApiListFlowLogsResult,
): FlowLogs {
  return {
    items: apiFlowLog.items?.map(translateFlowLog) ?? [],
    totalCount: apiFlowLog.totalCount
      ? Number(apiFlowLog.totalCount)
      : undefined,
  };
}

/**
 * Constructs a FlowLog from the corresponding ApiFlowLog.
 */
export function translateFlowLog(
  apiFlowLog: apiInterfaces.ApiFlowLog,
): FlowLog {
  assertKeyNonNull(apiFlowLog, 'timestamp');

  return {
    timestamp: createDate(apiFlowLog.timestamp),
    logMessage: apiFlowLog.logMessage,
  };
}

/**
 * Translates an API FlowOutputPluginLogEntryLogEntryType to an
 * OutputPluginLogEntryType.
 */
export function translateOutputPluginLogEntryType(
  t: apiInterfaces.FlowOutputPluginLogEntryLogEntryType,
): OutputPluginLogEntryType {
  switch (t) {
    case apiInterfaces.FlowOutputPluginLogEntryLogEntryType.UNSET:
      return OutputPluginLogEntryType.UNSET;
    case apiInterfaces.FlowOutputPluginLogEntryLogEntryType.LOG:
      return OutputPluginLogEntryType.LOG;
    case apiInterfaces.FlowOutputPluginLogEntryLogEntryType.ERROR:
      return OutputPluginLogEntryType.ERROR;
    default:
      checkExhaustive(t);
  }
}

/**
 * Constructs an OutputPluginLogEntry from the corresponding
 * FlowOutputPluginLogEntry.
 */
export function translateOutputPluginLog(
  apiOutputPluginLog: apiInterfaces.FlowOutputPluginLogEntry,
): OutputPluginLogEntry {
  return {
    flowId: apiOutputPluginLog.flowId,
    clientId: apiOutputPluginLog.clientId,
    huntId: apiOutputPluginLog.huntId,
    outputPluginId: apiOutputPluginLog.outputPluginId,
    logEntryType: apiOutputPluginLog.logEntryType
      ? translateOutputPluginLogEntryType(apiOutputPluginLog.logEntryType)
      : undefined,
    timestamp: apiOutputPluginLog.timestamp
      ? createDate(apiOutputPluginLog.timestamp)
      : undefined,
    message: apiOutputPluginLog.message,
  };
}

/**
 * Constructs a ListAllOutputPluginLogsResult from the corresponding
 * ApiListAllFlowOutputPluginLogsResult.
 */
export function translateListAllOutputPluginLogsResult(
  apiResult: apiInterfaces.ApiListAllFlowOutputPluginLogsResult,
): ListAllOutputPluginLogsResult {
  return {
    items: apiResult.items?.map(translateOutputPluginLog) ?? [],
    totalCount: apiResult.totalCount ? Number(apiResult.totalCount) : undefined,
  };
}

/** Constructs a ScheduledFlow from the corresponding API data structure. */
export function translateScheduledFlow(
  apiSF: apiInterfaces.ApiScheduledFlow,
): ScheduledFlow {
  assertKeyNonNull(apiSF, 'scheduledFlowId');
  assertKeyNonNull(apiSF, 'clientId');
  assertKeyNonNull(apiSF, 'creator');
  assertKeyNonNull(apiSF, 'flowName');
  assertKeyNonNull(apiSF, 'flowArgs');
  assertKeyNonNull(apiSF, 'createTime');

  return {
    scheduledFlowId: apiSF.scheduledFlowId,
    clientId: apiSF.clientId,
    creator: apiSF.creator,
    flowName: apiSF.flowName,
    flowType: translateApiFlowType(apiSF.flowName),
    flowArgs: createUnknownObject(apiSF.flowArgs),
    createTime: createDate(apiSF.createTime),
    error: apiSF.error,
  };
}

function byteStringToHex(
  byteString?: apiInterfaces.ProtoBytes,
): string | undefined {
  if (byteString === undefined) {
    return undefined;
  }
  return bytesToHex(decodeBase64(byteString)).toLowerCase();
}

/** Translates base64-encoded hashes to hex-encoding. */
export function translateHashToHex(hash: apiInterfaces.Hash): HexHash {
  return {
    sha256: byteStringToHex(hash.sha256),
    sha1: byteStringToHex(hash.sha1),
    md5: byteStringToHex(hash.md5),
  };
}

/** Translates a String to OperatingSystem, throwing an Error if unknown. */
export function translateOperatingSystem(str: string): OperatingSystem {
  if (!isEnum(str, OperatingSystem)) {
    throw new PreconditionError(
      `OperatingSystem enum does not include "${str}".`,
    );
  }

  return str;
}

/** Translates a String to OperatingSystem, returning null if unknown. */
export function safeTranslateOperatingSystem(
  str: string | undefined | null,
): OperatingSystem | null {
  if (str == null || !isEnum(str, OperatingSystem)) {
    return null;
  }

  return str;
}

/** Constructs an ExecuteResponse from the corresponding API data structure. */
export function translateExecuteResponse(
  er: apiInterfaces.ExecuteResponse,
): ExecuteResponse {
  assertKeyNonNull(er, 'request');

  return {
    request: {
      cmd: er.request.cmd ?? '',
      args: er.request.args ?? [],
      timeLimitSeconds: er.request.timeLimit ?? 0,
    },
    exitStatus: er.exitStatus ?? -1,
    stdout: atob(er.stdout ?? ''),
    stderr: atob(er.stderr ?? ''),
    timeUsedSeconds: (er.timeUsed ?? 0) / 1e6,
  };
}

/**
 * Constructs an ExecuteBinaryResponse from the corresponding API data
 * structure.
 */
export function translateExecuteBinaryResponse(
  er: apiInterfaces.ExecuteBinaryResponse,
): ExecuteBinaryResponse {
  return {
    exitStatus: er.exitStatus ?? -1,
    stdout: er.stdout ? atob(er.stdout).split('\n') : [],
    stderr: er.stderr ? atob(er.stderr).split('\n') : [],
    timeUsedSeconds: (er.timeUsed ?? 0) / 1e6,
  };
}

/**
 * Constructs internal ArtifactCollectorFlowProgress from an ArtifactCollector.
 */
export function translateArtifactCollectorFlowProgress(
  flow: Flow,
): ArtifactCollectorFlowProgress {
  const progressAritfacts =
    (flow.progress as apiInterfaces.ArtifactCollectorFlowProgress)?.artifacts ??
    [];

  const argumentArtifacts =
    (flow.args as apiInterfaces.ArtifactCollectorFlowArgs)?.artifactList ?? [];

  const artifacts = new Map<string, ArtifactProgress>();

  for (const name of argumentArtifacts) {
    artifacts.set(name, {name, numResults: undefined});
  }

  for (const art of progressAritfacts) {
    assertNonNull(art.name, 'ArtifactProgress.name');
    artifacts.set(art.name, {name: art.name, numResults: art.numResults ?? 0});
  }

  return {artifacts};
}

/**
 * Constructs internal CollectLargeFileFlowResult from an
 * apiInterfaces.CollectLargeFileFlowResult.
 */
export function translateCollectLargeFileFlowResult(
  result: apiInterfaces.CollectLargeFileFlowResult,
): CollectLargeFileFlowResult {
  return {
    sessionUri: result.sessionUri ?? '',
    totalBytesSent: result.totalBytesSent
      ? BigInt(result.totalBytesSent)
      : undefined,
  };
}

/**
 * Constructs internal ContainerLabel from an apiInterfaces.ContainerLabel.
 */
export function translateContainerLabel(
  label: apiInterfaces.ContainerLabel,
): ContainerLabel {
  return {
    key: label.label ?? '',
    value: label.value ?? '',
  };
}

/**
 * Constructs internal ContainerState from an
 * apiInterfaces.ContainerDetailsContainerState.
 */
export function translateContainerState(
  state: apiInterfaces.ContainerDetailsContainerState,
): ContainerState {
  switch (state) {
    case apiInterfaces.ContainerDetailsContainerState.CONTAINER_UNKNOWN:
      return ContainerState.UNKNOWN;
    case apiInterfaces.ContainerDetailsContainerState.CONTAINER_CREATED:
      return ContainerState.CREATED;
    case apiInterfaces.ContainerDetailsContainerState.CONTAINER_RUNNING:
      return ContainerState.RUNNING;
    case apiInterfaces.ContainerDetailsContainerState.CONTAINER_PAUSED:
      return ContainerState.PAUSED;
    case apiInterfaces.ContainerDetailsContainerState.CONTAINER_EXITED:
      return ContainerState.EXITED;
    default:
      checkExhaustive(state);
  }
}

/**
 * Constructs internal ContainerDetailsContainerCli from an
 * apiInterfaces.ContainerDetailsContainerCli.
 */
export function translateContainerCli(
  cli: apiInterfaces.ContainerDetailsContainerCli,
): ContainerCli {
  switch (cli) {
    case apiInterfaces.ContainerDetailsContainerCli.UNSUPPORTED:
      return ContainerCli.UNSUPPORTED;
    case apiInterfaces.ContainerDetailsContainerCli.CRICTL:
      return ContainerCli.CRICTL;
    case apiInterfaces.ContainerDetailsContainerCli.DOCKER:
      return ContainerCli.DOCKER;
    default:
      checkExhaustive(cli);
  }
}

/**
 * Constructs internal ContainerDetails from an
 * apiInterfaces.ContainerDetails.
 */
export function translateContainerDetails(
  containerDetails: apiInterfaces.ContainerDetails,
): ContainerDetails {
  return {
    containerId: containerDetails.containerId,
    imageName: containerDetails.imageName,
    command: containerDetails.command,
    createdAt: containerDetails.createdAt
      ? createDate(containerDetails.createdAt)
      : undefined,
    status: containerDetails.status,
    ports: containerDetails.ports,
    names: containerDetails.names,
    labels: (containerDetails.labels ?? []).map(translateContainerLabel),
    localVolumes: containerDetails.localVolumes,
    mounts: containerDetails.mounts,
    networks: containerDetails.networks,
    runningSince: containerDetails.runningSince
      ? createDate(containerDetails.runningSince)
      : undefined,
    state: containerDetails.state
      ? translateContainerState(containerDetails.state)
      : undefined,
    containerCli: containerDetails.containerCli
      ? translateContainerCli(containerDetails.containerCli)
      : undefined,
  };
}

/**
 * Constructs internal SoftwarePackageInstallState from an
 * apiInterfaces.SoftwarePackageInstallState.
 */
export function translateSoftwarePackageInstallState(
  installState: apiInterfaces.SoftwarePackageInstallState,
): SoftwarePackageInstallState {
  switch (installState) {
    case apiInterfaces.SoftwarePackageInstallState.UNKNOWN:
      return SoftwarePackageInstallState.UNKNOWN;
    case apiInterfaces.SoftwarePackageInstallState.INSTALLED:
      return SoftwarePackageInstallState.INSTALLED;
    case apiInterfaces.SoftwarePackageInstallState.PENDING:
      return SoftwarePackageInstallState.PENDING;
    case apiInterfaces.SoftwarePackageInstallState.UNINSTALLED:
      return SoftwarePackageInstallState.UNINSTALLED;
    default:
      checkExhaustive(installState);
  }
}

/**
 * Constructs internal SoftwarePackage from an
 * apiInterfaces.SoftwarePackage.
 */
export function translateSoftwarePackage(
  softwarePackage: apiInterfaces.SoftwarePackage,
): SoftwarePackage {
  return {
    name: softwarePackage.name,
    version: softwarePackage.version,
    architecture: softwarePackage.architecture,
    publisher: softwarePackage.publisher,
    installState: softwarePackage.installState
      ? translateSoftwarePackageInstallState(softwarePackage.installState)
      : undefined,
    description: softwarePackage.description,
    installedOn: softwarePackage.installedOn
      ? createDate(softwarePackage.installedOn)
      : undefined,
    installedBy: softwarePackage.installedBy,
    epoch: softwarePackage.epoch,
    sourceRpm: softwarePackage.sourceRpm,
    sourceDeb: softwarePackage.sourceDeb,
  };
}

/**
 * Constructs internal GetMemorySizeResult from an
 * apiInterfaces.GetMemorySizeResult.
 */
export function translateGetMemorySizeResult(
  result: apiInterfaces.GetMemorySizeResult,
): GetMemorySizeResult {
  return {
    totalBytes: createOptionalBigInt(result.totalBytes),
  };
}

/** Parses an API PathSpec. */
export function translatePathSpec(ps: apiInterfaces.PathSpec): PathSpec {
  assertEnum(ps.pathtype, apiInterfaces.PathSpecPathType);

  const pathspec = {
    path: '',
    pathtype: ps.pathtype,
    segments: [] as PathSpecSegment[],
  };
  let currentPathSpec: apiInterfaces.PathSpec | undefined = ps;

  while (currentPathSpec) {
    assertEnum(currentPathSpec.pathtype, apiInterfaces.PathSpecPathType);
    assertKeyNonNull(currentPathSpec, 'path');

    pathspec.path += currentPathSpec.path;
    pathspec.pathtype = currentPathSpec.pathtype;
    pathspec.segments.push({
      path: currentPathSpec.path,
      pathtype: currentPathSpec.pathtype,
    });

    currentPathSpec = currentPathSpec.nestedPath;
  }

  return pathspec;
}

/**
 * Parses a StatEntry to a RegistryKey/Value if possible. As fallback, returns
 * the original StatEntry.
 */
export function translateVfsStatEntry(
  statEntry: apiInterfaces.StatEntry,
): StatEntry | RegistryKey | RegistryValue {
  assertKeyNonNull(statEntry, 'pathspec');
  assertKeyNonNull(statEntry.pathspec, 'path');

  const path = statEntry.pathspec.path;

  if (statEntry.registryType) {
    assertEnum(statEntry.registryType, RegistryType);
    return {
      path,
      type: statEntry.registryType,
      value: statEntry.registryData,
    };
  }

  if (statEntry.pathspec.pathtype === apiInterfaces.PathSpecPathType.REGISTRY) {
    return {
      path,
      type: 'REG_KEY',
    };
  }

  return translateStatEntry(statEntry);
}

/** Parses a StatEntry. */
export function translateStatEntry(
  statEntry: apiInterfaces.StatEntry,
): StatEntry {
  assertKeyNonNull(statEntry, 'pathspec');

  return {
    stMode: createOptionalBigInt(statEntry.stMode),
    stIno: createOptionalBigInt(statEntry.stIno),
    stDev: createOptionalBigInt(statEntry.stDev),
    stNlink: createOptionalBigInt(statEntry.stNlink),
    stUid: statEntry.stUid,
    stGid: statEntry.stGid,
    stSize: createOptionalBigInt(statEntry.stSize),
    stAtime: createOptionalDateSeconds(statEntry.stAtime),
    stMtime: createOptionalDateSeconds(statEntry.stMtime),
    stCtime: createOptionalDateSeconds(statEntry.stCtime),
    stBtime: createOptionalDateSeconds(statEntry.stBtime),
    stBlocks: createOptionalBigInt(statEntry.stBlocks),
    stBlksize: createOptionalBigInt(statEntry.stBlksize),
    stRdev: createOptionalBigInt(statEntry.stRdev),
    stFlagsOsx: statEntry.stFlagsOsx,
    stFlagsLinux: statEntry.stFlagsLinux,
    symlink: statEntry.symlink,
    pathspec: translatePathSpec(statEntry.pathspec),
  };
}

/**
 * Returns true if the returned value of translateVfsStatEntry() is a StatEntry.
 */
export function isStatEntry(
  entry: StatEntry | RegistryKey | RegistryValue,
): entry is StatEntry {
  return (entry as StatEntry).pathspec != null;
}

/**
 * Returns true if the entry is a Registry key or value.
 */
export function isRegistryEntry(
  entry: StatEntry | RegistryKey | RegistryValue,
): entry is RegistryKey | RegistryValue {
  return (entry as RegistryKey).type != null;
}

/**
 * Returns true if the entry is a Registry value.
 */
export function isRegistryValue(
  entry: RegistryKey | RegistryValue,
): entry is RegistryValue {
  return entry.type !== 'REG_KEY';
}

/** Translates an ApiGrrBinary, raising if legacy types are used. */
export function translateBinary(b: apiInterfaces.ApiGrrBinary): Binary {
  assertKeyNonNull(b, 'path');
  assertKeyNonNull(b, 'type');
  assertEnum(b.type, BinaryType);

  return {
    path: b.path,
    size: b.size ? BigInt(b.size) : undefined,
    type: b.type,
    timestamp: b.timestamp ? createDate(b.timestamp) : undefined,
  };
}

/** Translates an ApiGrrBinary, returning null if legacy types are used. */
export function safeTranslateBinary(
  b: apiInterfaces.ApiGrrBinary,
): Binary | null {
  try {
    return translateBinary(b);
  } catch (e: unknown) {
    return null;
  }
}
