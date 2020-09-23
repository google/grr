import {ApiFlow, ApiFlowDescriptor, ApiFlowResult, ApiFlowState, ApiScheduledFlow} from '@app/lib/api/api_interfaces';
import {createDate, createUnknownObject} from '@app/lib/api_translation/primitive';
import {Flow, FlowDescriptor, FlowResult, FlowState, ScheduledFlow} from '@app/lib/models/flow';
import {assertKeyNonNull} from '../preconditions';

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
