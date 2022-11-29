/** Test helpers. */
// tslint:disable:enforce-comments-on-exported-symbols

import {Client, ClientApproval} from '../../lib/models/client';
import {Duration} from '../date_time';

import {ArtifactDescriptor, ArtifactDescriptorMap, Flow, FlowDescriptor, FlowResult, FlowState, OperatingSystem, ScheduledFlow} from './flow';
import {Hunt, HuntApproval, HuntState, HuntType, SafetyLimits} from './hunt';
import {OutputPluginDescriptor} from './output_plugin';
import {GrrUser} from './user';
import {File, PathSpec, PathSpecPathType, StatEntry} from './vfs';



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
    errorDescription: args.errorDescription ?? undefined,
    resultCounts: args.resultCounts ?? undefined,
    isRobot: false,
    ...args,
  };
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

export function newFlowResult(result: Partial<FlowResult>): FlowResult {
  return {
    payloadType: 'Foobar',
    payload: {foobar: 42},
    tag: '',
    timestamp: new Date(),
    ...result,
  };
}

export function newArtifactDescriptor(args: Partial<ArtifactDescriptor>):
    ArtifactDescriptor {
  return {
    dependencies: [],
    doc: 'Description of test artifact',
    isCustom: false,
    name: 'TestAritfact',
    pathDependencies: [],
    provides: [],
    sources: [],
    supportedOs: new Set([OperatingSystem.LINUX]),
    urls: [],
    ...args,
  };
}

export function newOutputPluginDescriptor(
    args: Partial<OutputPluginDescriptor>): OutputPluginDescriptor {
  return {
    name: 'PluginName',
    description: 'Plugin description',
    argsType: 'PluginArgs',
    ...args,
  };
}

export function newArtifactDescriptorMap(
    descriptors: Array<Partial<ArtifactDescriptor>>): ArtifactDescriptorMap {
  return new Map(
      descriptors.map(newArtifactDescriptor).map(ad => ([ad.name, ad])));
}

export function newPathSpec(pathSpec: Partial<PathSpec> = {}): PathSpec {
  return {
    path: '/foo/bar',
    pathtype: PathSpecPathType.OS,
    segments: [
      {
        path: pathSpec.path ?? '/foo/bar',
        pathtype: pathSpec.pathtype ?? PathSpecPathType.OS,
      },
    ],
    ...pathSpec,
  };
}

export function newStatEntry(statEntry: Partial<StatEntry> = {}): StatEntry {
  return {
    pathspec: newPathSpec(statEntry.pathspec ?? {}),
    ...statEntry,
  };
}

export function newFile(file: Partial<File>): File {
  return {
    name: 'bar',
    isDirectory: false,
    path: 'fs/os/foo/bar',
    pathtype: PathSpecPathType.OS,
    lastMetadataCollected: new Date(123),
    stat: newStatEntry(file.stat ?? {}),
    ...file,
  };
}

export function newGrrUser(user: Partial<GrrUser>): GrrUser {
  return {
    name: 'currentuser',
    huntApprovalRequired: true,
    canaryMode: false,
    ...user,
  };
}

export function newSafetyLimits(limits: Partial<SafetyLimits>): SafetyLimits {
  return {
    cpuLimit: limits.cpuLimit ?? BigInt(33),
    networkBytesLimit: limits.networkBytesLimit ?? BigInt(345),
    clientRate: limits.clientRate ?? 60,
    clientLimit: limits.clientLimit ?? BigInt(200),
    crashLimit: limits.crashLimit ?? BigInt(55),
    avgResultsPerClientLimit: limits.cpuLimit ?? BigInt(99),
    avgCpuSecondsPerClientLimit: limits.cpuLimit ?? BigInt(20),
    avgNetworkBytesPerClientLimit: limits.cpuLimit ?? BigInt(59),
    expiryTime: limits.expiryTime ?? BigInt(32),
    ...limits,
  };
}

export function newHunt(hunt: Partial<Hunt>): Hunt {
  return {
    allClientsCount: hunt.allClientsCount ?? BigInt(123),
    clientsWithResultsCount: hunt.clientsWithResultsCount ?? BigInt(10),
    completedClientsCount: hunt.completedClientsCount ?? BigInt(5),
    created: hunt.created ?? new Date(),
    creator: hunt.creator ?? 'foouser',
    description: hunt.description ?? 'test',
    duration: hunt.duration ?? Duration.fromObject({seconds: 86400}),
    flowArgs: hunt.flowArgs,
    flowName: hunt.flowName,
    huntId: hunt.huntId ?? '123',
    huntType: hunt.huntType ?? HuntType.STANDARD,
    initStartTime: hunt.initStartTime ?? new Date(),
    internalError: hunt.internalError,
    isRobot: hunt.isRobot ?? false,
    lastStartTime: hunt.lastStartTime ?? new Date(),
    name: hunt.name ?? 'GenericHunt',
    remainingClientsCount: hunt.remainingClientsCount ?? BigInt(190),
    resultsCount: hunt.resultsCount ?? BigInt(55),
    state: hunt.state ?? HuntState.STARTED,
    totalCpuUsage: hunt.totalCpuUsage ?? 0,
    totalNetUsage: hunt.totalNetUsage ?? BigInt(0),
    safetyLimits: newSafetyLimits(hunt.safetyLimits ?? {}),
    ...hunt,
  };
}

export function newHuntApproval(args: Partial<HuntApproval> = {}):
    HuntApproval {
  const huntId = args.huntId ?? args.subject?.huntId ?? `C.${randomHex(16)}`;

  return {
    approvalId: randomHex(8),
    huntId,
    requestor: 'msan',
    reason: 't/1234',
    status: {type: 'pending', reason: 'Need 1 more approver'},
    requestedApprovers: ['rsanchez'],
    approvers: ['msan'],
    subject: newHunt({huntId, ...args.subject}),
    ...args,
  };
}
