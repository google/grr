/**
 * Test helpers to mock Stores.
 */
// tslint:disable:no-any

import {Type, signal} from '@angular/core';

import {ApprovalConfig} from '../lib/models/client';
import {
  ArtifactDescriptor,
  Flow,
  FlowDescriptor,
  FlowResult,
} from '../lib/models/flow';
import {newGrrUser} from '../lib/models/model_test_util';
import {PayloadType} from '../lib/models/result';
import {File, FileContent, PathSpecPathType} from '../lib/models/vfs';
import {ApprovalRequestStore} from './approval_request_store';
import {ClientSearchStore} from './client_search_store';
import {ClientStore, FlowResults} from './client_store';
import {FileExplorerStore} from './file_explorer_store';
import {FileStore} from './file_store';
import {FleetCollectionStore} from './fleet_collection_store';
import {FleetCollectionsStore} from './fleet_collections_store';
import {FlowStore} from './flow_store';
import {GlobalStore} from './global_store';
import {NewFleetCollectionStore} from './new_fleet_collection_store';

function unWrapType<T>(input: Type<T>): T {
  return {} as T;
}
type Writeable<T> = {-readonly [P in keyof T]: T[P]};

// GlobalStore

const unwrappedGlobalStore = unWrapType(GlobalStore);
/** Type of a mocked GlobalStore. */
export type GlobalStoreMock = Partial<Writeable<typeof unwrappedGlobalStore>>;

/** Mock for GlobalStore. */
export function newGlobalStoreMock(): GlobalStoreMock {
  return {
    currentUser: signal(newGrrUser({})),
    uiConfig: signal(null),
    allLabels: signal([]),
    flowDescriptors: signal([]),
    flowDescriptorsMap: signal(new Map<string, FlowDescriptor>()),
    artifactDescriptorMap: signal(new Map<string, ArtifactDescriptor>()),
    binaries: signal([]),
    executables: signal([]),
    pythonHacks: signal([]),
    approvalConfig: signal({} as ApprovalConfig),
    exportCommandPrefix: signal(null),
    outputPluginDescriptors: signal([]),
    webAuthType: signal(null),

    initialize: jasmine.createSpy('initialize'),
    fetchCurrentUser: jasmine.createSpy('fetchCurrentUser'),
    fetchUiConfig: jasmine.createSpy('fetchUiConfig'),
    fetchApprovalConfig: jasmine.createSpy('fetchApprovalConfig'),
    fetchAllLabels: jasmine.createSpy('fetchAllLabels'),
    fetchFlowDescriptors: jasmine.createSpy('fetchFlowDescriptors'),
    fetchBinaryNames: jasmine.createSpy('fetchBinaryNames'),
    getArtifactDescriptorMap: jasmine.createSpy('getArtifactDescriptorMap'),
    fetchWebAuthType: jasmine.createSpy('fetchWebAuthType'),
    fetchExportCommandPrefix: jasmine.createSpy('fetchExportCommandPrefix'),
    fetchOutputPluginDescriptors: jasmine.createSpy(
      'fetchOutputPluginDescriptors',
    ),
  };
}

// ClientSearchStore

const unwrappedClientSearchStore = unWrapType(ClientSearchStore);
/** Type of a mocked ClientSearchStore. */
export type ClientSearchStoreMock = Partial<
  Writeable<typeof unwrappedClientSearchStore>
>;

/**
 * Creates a mock ClientSearchStore for testing.
 */
export function newClientSearchStoreMock(): ClientSearchStoreMock {
  return {
    clients: signal([]),
    recentApprovals: signal([]),

    fetchRecentClientApprovals: jasmine.createSpy('fetchRecentClientApprovals'),
    searchClients: jasmine.createSpy('searchClients') as any,
  };
}

// ClientStore

const unwrappedClientStore = unWrapType(ClientStore);
/** Type of a mocked ClientStore. */
export type ClientStoreMock = Partial<Writeable<typeof unwrappedClientStore>>;

/**
 * Creates a mock ClientStore for testing.
 */
export function newClientStoreMock(): ClientStoreMock {
  return {
    clientId: signal(null),
    client: signal(null),
    hasAccess: signal(null),
    clientApprovals: signal([]),
    clientSnapshots: signal([]),
    clientStartupInfos: signal([]),
    flowsCount: signal(0),
    flows: signal([]),
    flowsByFlowId: signal(new Map<string, Flow>()),
    flowResultsByFlowId: signal(new Map<string, FlowResults>()),
    clientHistory: signal([]),
    latestApproval: signal(null),

    hasMoreFlows: signal(true),

    scheduledFlows: signal([]),
    triggerFetchScheduledFlows: signal(0),

    initialize: jasmine.createSpy('initialize'),

    requestClientApproval: jasmine.createSpy('requestClientApproval'),

    pollFlow: jasmine.createSpy('pollFlow') as any,
    pollFlowResults: jasmine.createSpy('pollFlowResults') as any,
    pollFlows: jasmine.createSpy('pollFlows') as any,
    pollScheduledFlows: jasmine.createSpy('pollScheduledFlows') as any,
    pollClientApprovals: jasmine.createSpy('pollClientApprovals'),
    scheduleOrStartFlow: jasmine.createSpy('scheduleOrStartFlow'),
  };
}

// FlowStore

const unwrappedFlowStore = unWrapType(FlowStore);
/** Type of a mocked FlowStore. */
export type FlowStoreMock = Partial<Writeable<typeof unwrappedFlowStore>>;

/**
 * Creates a mock FlowStore for testing.
 */
export function newFlowStoreMock(): FlowStoreMock {
  return {
    clientId: signal(undefined),
    flowId: signal(undefined),
    flow: signal(undefined),
    flowResultsByPayloadType: signal(new Map<PayloadType, FlowResult[]>()),
    countLoadedResults: signal(0),
    countTotalResults: signal(undefined),
    logs: signal([]),
    outputPluginLogs: signal([]),

    initialize: jasmine.createSpy('initialize'),
    fetchFlow: jasmine.createSpy('fetchFlow'),
    fetchFlowResults: jasmine.createSpy('fetchFlowResults'),
    fetchFlowLogs: jasmine.createSpy('fetchFlowLogs'),
    fetchAllFlowOutputPluginLogs: jasmine.createSpy(
      'fetchAllFlowOutputPluginLogs',
    ),
  };
}

// FileExplorerStore

const unwrappedFileExplorerStore = unWrapType(FileExplorerStore);
/** Type of a mocked FileExplorerStore. */
export type FileExplorerStoreMock = Partial<
  Writeable<typeof unwrappedFileExplorerStore>
>;

/**
 * Creates a mock FileExplorerStore for testing.
 */
export function newFileExplorerStoreMock(): FileExplorerStoreMock {
  return {
    clientId: signal(undefined),
    fileSystemTree: signal(undefined),
    currentlyRefreshingPaths: signal(new Set<string>()),

    initialize: jasmine.createSpy('initialize'),
    fetchChildren: jasmine.createSpy('fetchChildren'),
    refreshVfsFolder: jasmine.createSpy('refreshVfsFolder'),
  };
}

// FileStore

const unwrappedFileStore = unWrapType(FileStore);
/** Type of a mocked FileStore. */
export type FileStoreMock = Partial<Writeable<typeof unwrappedFileStore>>;

/**
 * Creates a mock FileStore for testing.
 */
export function newFileStoreMock(): FileStoreMock {
  return {
    fileContentAccessMap: signal(
      new Map<string, Map<PathSpecPathType, Map<string, boolean>>>(),
    ),
    fileDetailsMap: signal(
      new Map<string, Map<PathSpecPathType, Map<string, File>>>(),
    ),
    fileBlobMap: signal(
      new Map<string, Map<PathSpecPathType, Map<string, FileContent>>>(),
    ),
    fileTextMap: signal(
      new Map<string, Map<PathSpecPathType, Map<string, FileContent>>>(),
    ),
    isRecollecting: signal(false),

    fetchFileContentAccess: jasmine.createSpy('fetchFileContentAccess') as any,
    fetchFileDetails: jasmine.createSpy('fetchFileDetails') as any,
    fetchTextFile: jasmine.createSpy('fetchTextFile') as any,
    fetchBinaryFile: jasmine.createSpy('fetchBinaryFile') as any,

    recollectFile: jasmine.createSpy('recollectFile'),
  };
}

// FleetCollectionsStore

const unwrappedFleetCollectionsStore = unWrapType(FleetCollectionsStore);
/** Type of a mocked FleetCollectionsStore. */
export type FleetCollectionsStoreMock = Partial<
  Writeable<typeof unwrappedFleetCollectionsStore>
>;

/**
 * Creates a mock FleetCollectionsStore for testing.
 */
export function newFleetCollectionsStoreMock(): FleetCollectionsStoreMock {
  return {
    fleetCollections: signal([]),

    pollFleetCollections: jasmine.createSpy('pollFleetCollections') as any,

    // computed
    hasMoreFleetCollections: signal(false),
  };
}

// FleetCollectionStore

const unwrappedFleetCollectionStore = unWrapType(FleetCollectionStore);
/** Type of a mocked FleetCollectionStore. */
export type FleetCollectionStoreMock = Partial<
  Writeable<typeof unwrappedFleetCollectionStore>
>;

/**
 * Creates a mock FleetCollectionStore for testing.
 */
export function newFleetCollectionStoreMock(): FleetCollectionStoreMock {
  return {
    fleetCollection: signal(null),
    hasAccess: signal(null),
    fleetCollectionApprovals: signal([]),
    fleetCollectionResults: signal([]),
    totalResultsCount: signal(0),
    fleetCollectionErrors: signal([]),
    totalErrorsCount: signal(0),
    fleetCollectionProgress: signal(null),
    fleetCollectionLogs: signal([]),
    totalFleetCollectionLogsCount: signal(0),

    initialize: jasmine.createSpy('initialize'),
    pollUntilAccess: jasmine.createSpy('pollUntilAccess') as any,
    pollFleetCollectionApprovals: jasmine.createSpy(
      'pollFleetCollectionApprovals',
    ) as any,
    pollFleetCollection: jasmine.createSpy('pollFleetCollection') as any,
    pollFleetCollectionResults: jasmine.createSpy(
      'pollFleetCollectionResults',
    ) as any,
    getFleetCollectionErrors: jasmine.createSpy(
      'getFleetCollectionErrors',
    ) as any,
    startFleetCollection: jasmine.createSpy('startFleetCollection'),
    cancelFleetCollection: jasmine.createSpy('cancelFleetCollection'),
    updateFleetCollection: jasmine.createSpy('updateFleetCollection'),
    requestFleetCollectionApproval: jasmine.createSpy(
      'requestFleetCollectionApproval',
    ),
    pollFleetCollectionProgress: jasmine.createSpy(
      'pollFleetCollectionProgress',
    ) as any,
    fetchFleetCollectionLogs: jasmine.createSpy('fetchFleetCollectionLogs'),

    // computed
    latestApproval: signal(null),
    hasMoreResults: signal(false),
    fleetCollectionResultsPerClientAndType: signal([]),
    hasMoreErrors: signal(false),
  };
}

// NewFleetCollectionStore

const unwrappedNewFleetCollectionStore = unWrapType(NewFleetCollectionStore);
/** Type of a mocked NewFleetCollectionStore. */
export type NewFleetCollectionStoreMock = Partial<
  Writeable<typeof unwrappedNewFleetCollectionStore>
>;

/**
 * Creates a mock NewFleetCollectionStore for testing.
 */
export function newNewFleetCollectionStoreMock(): NewFleetCollectionStoreMock {
  return {
    originalFleetCollectionRef: signal(undefined),
    originalFlowRef: signal(undefined),
    originalFleetCollection: signal(undefined),
    originalFlow: signal(undefined),
    newFleetCollection: signal(undefined),

    initialize: jasmine.createSpy('initialize'),
    fetchRef: jasmine.createSpy('fetchRef'),
    createFleetCollection: jasmine.createSpy('createFleetCollection'),

    flowArgs: signal(undefined),
    flowType: signal(undefined),
  };
}

// ApprovalRequestStore

const unwrappedApprovalRequestStore = unWrapType(ApprovalRequestStore);
/** Type of a mocked ApprovalRequestStore. */
export type ApprovalRequestStoreMock = Partial<
  Writeable<typeof unwrappedApprovalRequestStore>
>;

/**
 * Creates a mock ApprovalRequestStore for testing.
 */
export function newApprovalRequestStoreMock(): ApprovalRequestStoreMock {
  return {
    requestedClientApproval: signal(null),
    requestedFleetCollectionApproval: signal(null),
    fetchClientApproval: jasmine.createSpy('fetchClientApproval'),
    grantClientApproval: jasmine.createSpy('grantClientApproval'),
    fetchFleetCollectionApproval: jasmine.createSpy(
      'fetchFleetCollectionApproval',
    ),
    grantFleetCollectionApproval: jasmine.createSpy(
      'grantFleetCollectionApproval',
    ),
  };
}
