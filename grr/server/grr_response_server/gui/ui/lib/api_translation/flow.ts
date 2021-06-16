import {ApiFlow, ApiFlowDescriptor, ApiFlowResult, ApiFlowState, ApiScheduledFlow, ArtifactCollectorFlowArgs, ArtifactCollectorFlowProgress as ApiArtifactCollectorFlowProgress, ByteString, ExecuteResponse as ApiExecuteResponse, Hash, PathSpecPathType, StatEntry} from '@app/lib/api/api_interfaces';
import {bytesToHex, createDate, createUnknownObject, decodeBase64} from '@app/lib/api_translation/primitive';
import {ArtifactCollectorFlowProgress, ArtifactProgress, ExecuteResponse, Flow, FlowDescriptor, FlowResult, FlowState, HexHash, OperatingSystem, RegistryKey, RegistryValue, ScheduledFlow} from '@app/lib/models/flow';

import {assertKeyNonNull, assertNonNull, isNonNull, PreconditionError} from '../preconditions';

/** Constructs a FlowDescriptor from the corresponding API data structure */
export function translateFlowDescriptor(fd: ApiFlowDescriptor): FlowDescriptor {
  assertKeyNonNull(fd, 'name');
  assertKeyNonNull(fd, 'category');
  assertKeyNonNull(fd, 'defaultArgs');

  const result = {
    name: fd.name,
    friendlyName: fd.friendlyName || fd.name,
    category: fd.category,
    defaultArgs: {...fd.defaultArgs},
  };
  // The protobuf type URL is an implementation detail of the API, thus we
  // remove if from defaultArgs.
  delete result.defaultArgs['@type'];
  return result;
}

function translateApiFlowState(state: ApiFlowState): FlowState {
  if (state === ApiFlowState.RUNNING) {
    return FlowState.RUNNING;
  } else if (state === ApiFlowState.ERROR) {
    return FlowState.ERROR;
  } else {
    return FlowState.FINISHED;
  }
}

/** Constructs a Flow from the corresponding API data structure. */
export function translateFlow(apiFlow: ApiFlow): Flow {
  assertKeyNonNull(apiFlow, 'flowId');
  assertKeyNonNull(apiFlow, 'clientId');
  assertKeyNonNull(apiFlow, 'lastActiveAt');
  assertKeyNonNull(apiFlow, 'startedAt');
  assertKeyNonNull(apiFlow, 'name');
  assertKeyNonNull(apiFlow, 'state');

  return {
    flowId: apiFlow.flowId,
    clientId: apiFlow.clientId,
    lastActiveAt: createDate(apiFlow.lastActiveAt),
    startedAt: createDate(apiFlow.startedAt),
    name: apiFlow.name,
    creator: apiFlow.creator || 'unknown',
    args: createUnknownObject(apiFlow.args),
    progress: createUnknownObject(apiFlow.progress),
    state: translateApiFlowState(apiFlow.state),
  };
}

/** Construct a FlowResult model object, corresponding to ApiFlowResult.  */
export function translateFlowResult(apiFlowResult: ApiFlowResult): FlowResult {
  assertKeyNonNull(apiFlowResult, 'payload');
  assertKeyNonNull(apiFlowResult, 'payloadType');
  assertKeyNonNull(apiFlowResult, 'timestamp');

  return {
    payload: createUnknownObject(apiFlowResult.payload),
    payloadType: apiFlowResult.payloadType,
    tag: apiFlowResult.tag ?? '',
    timestamp: createDate(apiFlowResult.timestamp),
  };
}

/** Constructs a ScheduledFlow from the corresponding API data structure. */
export function translateScheduledFlow(apiSF: ApiScheduledFlow): ScheduledFlow {
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
    flowArgs: createUnknownObject(apiSF.flowArgs),
    createTime: createDate(apiSF.createTime),
    error: apiSF.error,
  };
}

function byteStringToHex(byteString?: ByteString): string|undefined {
  if (byteString === undefined) {
    return undefined;
  }
  return bytesToHex(decodeBase64(byteString)).toLowerCase();
}

/** Translates base64-encoded hashes to hex-encoding. */
export function translateHashToHex(hash: Hash): HexHash {
  return {
    sha256: byteStringToHex(hash.sha256),
    sha1: byteStringToHex(hash.sha1),
    md5: byteStringToHex(hash.md5),
  };
}

function translateOperatingSystem(str: string): OperatingSystem {
  if (!Object.values(OperatingSystem).includes(str as OperatingSystem)) {
    throw new PreconditionError(
        `OperatingSystem enum does not include "${str}".`);
  }
  return str as OperatingSystem;
}

/** Translates a String to OperatingSystem, returning undefined on error. */
export function safeTranslateOperatingSystem(str: string|undefined):
    OperatingSystem|undefined {
  if (str === undefined) {
    return undefined;
  }

  try {
    return translateOperatingSystem(str);
  } catch (e: unknown) {
    return undefined;
  }
}

/** Constructs an ExecuteResponse from the corresponding API data structure. */
export function translateExecuteResponse(er: ApiExecuteResponse):
    ExecuteResponse {
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
    timeUsedSeconds: (er.timeUsed ?? 0) / 1e6
  };
}

/**
 * Constructs internal ArtifactCollectorFlowProgress from an ArtifactCollector.
 */
export function translateArtifactCollectorFlowProgress(flow: Flow):
    ArtifactCollectorFlowProgress {
  const progressAritfacts =
      (flow.progress as ApiArtifactCollectorFlowProgress)?.artifacts ?? [];

  const argumentArtifacts =
      (flow.args as ArtifactCollectorFlowArgs)?.artifactList ?? [];

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
 * Parses a StatEntry to a RegistryKey/Value if possible. As fallback, returns
 * the original StatEntry.
 */
export function translateStatEntry(statEntry: StatEntry): StatEntry|RegistryKey|
    RegistryValue {
  assertKeyNonNull(statEntry, 'pathspec');
  assertKeyNonNull(statEntry.pathspec, 'path');

  const path = statEntry.pathspec.path;

  if (statEntry.registryType) {
    return {
      path,
      type: statEntry.registryType,
      size: BigInt(statEntry.stSize ?? 0),
    };
  } else if (statEntry.pathspec.pathtype === PathSpecPathType.REGISTRY) {
    return {
      path,
      type: 'REG_KEY',
    };
  } else {
    return statEntry;
  }
}

/**
 * Returns true if the returned value of translateStatEntry() is a StatEntry.
 */
export function isStatEntry(entry: StatEntry|RegistryKey|
                            RegistryValue): entry is StatEntry {
  return isNonNull((entry as StatEntry).pathspec);
}

/**
 * Returns true if the returned value of translateStatEntry() is a Registry key
 * or value.
 */
export function isRegistryEntry(entry: StatEntry|RegistryKey|RegistryValue):
    entry is RegistryKey|RegistryValue {
  return isNonNull((entry as RegistryKey).type);
}
