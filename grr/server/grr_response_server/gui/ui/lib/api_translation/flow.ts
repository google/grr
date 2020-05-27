import {ApiFlow, ApiFlowDescriptor, ApiFlowResult, ApiFlowState} from '@app/lib/api/api_interfaces';
import {createDate, createUnknownObject} from '@app/lib/api_translation/primitive';
import {Flow, FlowDescriptor, FlowResult, FlowState} from '@app/lib/models/flow';

/** Constructs a FlowDescriptor from the corresponding API data structure */
export function translateFlowDescriptor(fd: ApiFlowDescriptor): FlowDescriptor {
  if (!fd.name) throw new Error('name attribute is missing.');
  if (!fd.category) throw new Error('category attribute is missing.');
  if (!fd.defaultArgs) throw new Error('defaultArgs attribute is missing.');
  if (!fd.defaultArgs['@type']) {
    throw new Error('defaultArgs["@type"] attribute is missing.');
  }

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
  } else {
    return FlowState.FINISHED;
  }
}

/** Constructs a Flow from the corresponding API data structure. */
export function translateFlow(apiFlow: ApiFlow): Flow {
  if (!apiFlow.flowId) throw new Error('flowId attribute is missing.');
  if (!apiFlow.clientId) throw new Error('clientId attribute is missing.');
  if (!apiFlow.lastActiveAt) {
    throw new Error('lastActiveAt attribute is missing.');
  }
  if (!apiFlow.startedAt) throw new Error('startedAt attribute is missing.');
  if (!apiFlow.name) throw new Error('name attribute is missing.');
  if (!apiFlow.state) throw new Error('state attribute missing');

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
  if (!apiFlowResult.payload) throw new Error('payload attribute is missing.');
  if (!apiFlowResult.timestamp) {
    throw new Error('timestamp attribute is missing.');
  }

  return {
    payload: createUnknownObject(apiFlowResult.payload),
    tag: apiFlowResult.tag ?? '',
    timestamp: createDate(apiFlowResult.timestamp),
  };
}
