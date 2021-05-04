/** Test helpers. */
// tslint:disable:enforce-comments-on-exported-symbols

import {Client, ClientApproval} from '@app/lib/models/client';
import {ArtifactDescriptor, ArtifactDescriptorMap, Flow, FlowDescriptor, FlowListEntry, flowListEntryFromFlow, FlowResultSet, FlowResultSetState, FlowState, OperatingSystem, ScheduledFlow} from './flow';



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
    osInfo: {},
    agentInfo: {},
    volumes: [],
    users: [],
    networkInterfaces: [],
    labels: [],
    age: new Date(0),
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

export function newScheduledFlow(args: Partial<ScheduledFlow> = {}):
    ScheduledFlow {
  return {
    scheduledFlowId: randomHex(8),
    clientId: `C.${randomHex(16)}`,
    creator: 'rsanchez',
    flowName: 'FileFinder',
    flowArgs: {},
    createTime: new Date(Date.now() - 60000),
    ...args,
  };
}

export function newClientApproval(args: Partial<ClientApproval> = {}):
    ClientApproval {
  const clientId =
      args.clientId ?? args.subject?.clientId ?? `C.${randomHex(16)}`;

  return {
    approvalId: randomHex(8),
    clientId,
    requestor: 'msan',
    reason: 't/1234',
    status: {type: 'pending', reason: 'Need 1 more approver'},
    requestedApprovers: ['rsanchez'],
    approvers: ['msan'],
    subject: newClient({clientId, ...args.subject}),
    ...args,
  };
}

export function newFlowResultSet(
    payload = {}, payloadType: string = 'Unknown'): FlowResultSet {
  return {
    items: [{
      payloadType,
      payload,
      tag: '',
      timestamp: new Date(),
    }],
    sourceQuery: {
      flowId: '',
      offset: 0,
      count: 0,
    },
    state: FlowResultSetState.FETCHED,
  };
}

export function newArtifactDescriptor(args: Partial<ArtifactDescriptor>):
    ArtifactDescriptor {
  return {
    dependencies: [],
    doc: 'Description of test artifact',
    isCustom: false,
    labels: ['Browsers'],
    name: 'TestAritfact',
    pathDependencies: [],
    provides: [],
    sources: [],
    supportedOs: new Set([OperatingSystem.LINUX]),
    urls: [],
    ...args,
  };
}

export function newArtifactDescriptorMap(
    descriptors: Array<Partial<ArtifactDescriptor>>): ArtifactDescriptorMap {
  return new Map(
      descriptors.map(newArtifactDescriptor).map(ad => ([ad.name, ad])));
}
