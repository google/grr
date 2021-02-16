import * as api from '@app/lib/api/api_interfaces';
import {ApiFlow, ApiFlowDescriptor, ApiFlowResult, ApiFlowState, ApiScheduledFlow, ByteString, Hash} from '@app/lib/api/api_interfaces';
import {bytesToHex, createDate, createUnknownObject, decodeBase64, translateDict} from '@app/lib/api_translation/primitive';
import {ArtifactDescriptor, ArtifactSource, Flow, FlowDescriptor, FlowResult, FlowState, HexHash, OperatingSystem, ScheduledFlow} from '@app/lib/models/flow';

import {assertKeyNonNull, PreconditionError} from '../preconditions';

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
  assertKeyNonNull(apiFlowResult, 'timestamp');

  return {
    payload: createUnknownObject(apiFlowResult.payload),
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

/**
 * Flattens an API ArtifactDescriptor and its contained Artifact into one
 * object.
 */
export function translateArtifactDescriptor(ad: api.ArtifactDescriptor):
    ArtifactDescriptor {
  assertKeyNonNull(ad, 'artifact');
  const artifact = ad.artifact ?? {};

  assertKeyNonNull(artifact, 'name');

  return {
    name: artifact.name,
    doc: artifact.doc,
    labels: [...artifact.labels ?? []],
    supportedOs:
        new Set([...artifact.supportedOs ?? []].map(translateOperatingSystem)),
    urls: [...artifact.urls ?? []],
    provides: [...artifact.provides ?? []],
    dependencies: [...ad.dependencies ?? []],
    pathDependencies: [...ad.pathDependencies ?? []],
    isCustom: ad.isCustom ?? false,
    sources: [...artifact.sources ?? []].map(translateArtifactSource),
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

function translateArtifactSource(source: api.ArtifactSource): ArtifactSource {
  assertKeyNonNull(source, 'type');

  const attributes =
      translateDict(source.attributes ?? {}) as ReadonlyMap<string, unknown>;
  return {
    type: source.type,
    attributes,
    conditions: [...source.conditions ?? []],
    returnedTypes: [...source.returnedTypes ?? []],
    supportedOs:
        new Set([...source.supportedOs ?? []].map(translateOperatingSystem)),
  };
}
