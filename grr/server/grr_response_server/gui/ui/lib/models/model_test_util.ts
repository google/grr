/** Test helpers. */
// tslint:disable:enforce-comments-on-exported-symbols

import {Client} from '@app/lib/models/client';

import {Flow, FlowDescriptor, FlowListEntry, flowListEntryFromFlow, FlowState} from './flow';


function randomHex(length: number): string {
  let result = '';
  while (result.length < length) {
    result += Math.random().toString(16).slice(2).toUpperCase();
  }
  return result.slice(0, length);
}

export function newClient(args: Partial<Client> = {}): Client {
  return {
    clientId: 'C.1234567890',
    fleetspeakEnabled: true,
    knowledgeBase: {},
    labels: [],
    ...args,
  };
}

export function newFlow(args: Partial<Flow> = {}): Flow {
  return {
    flowId: randomHex(8),
    clientId: `C.${randomHex(16)}`,
    lastActiveAt: new Date(),
    startedAt: new Date(Date.now() - 60000),
    name: 'FileFinder',
    creator: 'rsanchez',
    args: undefined,
    progress: undefined,
    state: args.state || FlowState.UNSET,
    ...args,
  };
}

export function newFlowListEntry(partialFlow: Partial<Flow> = {}):
    FlowListEntry {
  return flowListEntryFromFlow(newFlow(partialFlow));
}

export function newFlowDescriptor(args: Partial<FlowDescriptor> = {}):
    FlowDescriptor {
  return {
    name: 'FileFinder',
    friendlyName: 'Collect Files',
    category: 'Filesystem',
    defaultArgs: {},
    ...args,
  };
}

export function newFlowDescriptorMap(...fds: Array<Partial<FlowDescriptor>>):
    Map<string, FlowDescriptor> {
  return new Map(fds.map(newFlowDescriptor).map(fd => ([fd.name, fd])));
}
