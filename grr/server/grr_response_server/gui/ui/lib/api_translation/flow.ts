import {ApiFlow, ApiFlowDescriptor} from '@app/lib/api/api_interfaces';
import {createDate, createUnknownObject} from '@app/lib/api_translation/primitive';
import {Flow, FlowDescriptor} from '@app/lib/models/flow';

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

/** Constructs a Flow from the corresponding API data structure. */
export function translateFlow(apiFlow: ApiFlow): Flow {
  if (!apiFlow.flowId) throw new Error('flowId attribute is missing.');
  if (!apiFlow.clientId) throw new Error('clientId attribute is missing.');
  if (!apiFlow.lastActiveAt) {
    throw new Error('lastActiveAt attribute is missing.');
  }
  if (!apiFlow.startedAt) throw new Error('startedAt attribute is missing.');
  if (!apiFlow.name) throw new Error('name attribute is missing.');

  return {
    flowId: apiFlow.flowId,
    clientId: apiFlow.clientId,
    lastActiveAt: createDate(apiFlow.lastActiveAt),
    startedAt: createDate(apiFlow.startedAt),
    name: apiFlow.name,
    creator: apiFlow.creator || 'unknown',
    args: createUnknownObject(apiFlow.args),
    progress: createUnknownObject(apiFlow.progress),
  };
}
