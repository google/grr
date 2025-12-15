import {Injector} from '@angular/core';
import {fakeAsync, TestBed, tick} from '@angular/core/testing';
import {patchState} from '@ngrx/signals';
import {unprotected} from '@ngrx/signals/testing';

import {DEFAULT_POLLING_INTERVAL} from '../lib/api/http_api_service';
import {HttpApiWithTranslationService} from '../lib/api/http_api_with_translation_service';
import {
  HttpApiWithTranslationServiceMock,
  mockHttpApiWithTranslationService,
} from '../lib/api/http_api_with_translation_test_util';
import {StartupInfo} from '../lib/models/client';
import {FlowResult, FlowState} from '../lib/models/flow';
import {
  newClient,
  newClientApproval,
  newClientLabel,
  newClientSnapshot,
  newFlow,
  newFlowDescriptor,
  newFlowResult,
  newGrrUser,
  newListFlowResultsResult,
  newScheduledFlow,
} from '../lib/models/model_test_util';
import {PayloadType} from '../lib/models/result';
import {GlobalStore} from '../store/global_store';
import {initTestEnvironment} from '../testing';
import {ClientStore, FlowResults, FLOWS_PAGE_SIZE} from './client_store';

initTestEnvironment();

describe('ClientStore', () => {
  let httpApiService: HttpApiWithTranslationServiceMock;
  let injector: Injector;

  beforeEach(() => {
    httpApiService = mockHttpApiWithTranslationService();

    TestBed.configureTestingModule({
      providers: [
        ClientStore,
        {
          provide: HttpApiWithTranslationService,
          useFactory: () => httpApiService,
        },
      ],
      teardown: {destroyAfterEach: true},
    });
    injector = TestBed.inject(Injector);
  });

  it('initialize sets clientId', () => {
    const store = TestBed.inject(ClientStore);
    store.initialize('C.1234');
    expect(store.clientId()).toEqual('C.1234');
  });

  it('initialize() calls api to pollClient and updates the store', () => {
    const store = TestBed.inject(ClientStore);
    expect(store.client()).toBeNull();

    store.initialize('C.1234');
    const client = newClient({clientId: 'C.1234'});
    httpApiService.mockedObservables.fetchClient.next(client);

    expect(httpApiService.fetchClient).toHaveBeenCalledWith(
      'C.1234',
      DEFAULT_POLLING_INTERVAL,
    );
    expect(store.client()).toEqual(client);
  });

  it('polls for access when client is initialized', () => {
    const store = TestBed.inject(ClientStore);
    store.initialize('C.1234');
    expect(store.hasAccess()).toBeNull();

    httpApiService.mockedObservables.verifyClientAccess.next(false);
    expect(store.hasAccess()).toBeFalse();

    httpApiService.mockedObservables.verifyClientAccess.next(false);
    expect(store.hasAccess()).toBeFalse();

    httpApiService.mockedObservables.verifyClientAccess.next(true);
    expect(store.hasAccess()).toBeTrue();
  });

  it('calls api to listClientApprovals and updates store when pollClientApprovals is called', () => {
    const store = TestBed.inject(ClientStore);
    store.initialize('C.1234');

    expect(store.clientApprovals()).toHaveSize(0);

    store.pollClientApprovals();
    const pendingApproval = newClientApproval({
      clientId: 'C.1234',
      status: {type: 'pending', reason: 'Need 1 more approver'},
    });
    httpApiService.mockedObservables.listClientApprovals.next([
      pendingApproval,
    ]);
    expect(store.clientApprovals()).toEqual([pendingApproval]);

    const grantedApproval = newClientApproval({
      clientId: 'C.1234',
      status: {type: 'valid'},
    });
    httpApiService.mockedObservables.listClientApprovals.next([
      grantedApproval,
    ]);
    expect(store.clientApprovals()).toEqual([grantedApproval]);
  });

  it('returns null for latestApproval if there are no approvals', () => {
    const store = TestBed.inject(ClientStore);
    patchState(unprotected(store), {clientId: 'C.1234'});

    store.pollClientApprovals(0);
    httpApiService.mockedObservables.listClientApprovals.next([]);

    expect(store.latestApproval()).toBeNull();
  });

  it('returns null for latestApproval if there are only expired approvals', () => {
    const store = TestBed.inject(ClientStore);
    patchState(unprotected(store), {clientId: 'C.1234'});

    store.pollClientApprovals(0);
    const expiredApproval = newClientApproval({
      clientId: 'C.1234',
      status: {type: 'expired', reason: 'Expired'},
    });
    httpApiService.mockedObservables.listClientApprovals.next([
      expiredApproval,
    ]);
    expect(store.latestApproval()).toBeNull();
  });

  it('returns the latest not expired approval for latestApproval', () => {
    const store = TestBed.inject(ClientStore);
    patchState(unprotected(store), {clientId: 'C.1234'});

    store.pollClientApprovals(0);
    const pendingApproval = newClientApproval({
      clientId: 'C.1234',
      status: {type: 'pending', reason: 'Need 1 more approver'},
    });
    const expiredApproval = newClientApproval({
      clientId: 'C.1234',
      status: {type: 'expired', reason: 'Expired'},
    });

    httpApiService.mockedObservables.listClientApprovals.next([
      expiredApproval,
      pendingApproval,
    ]);

    expect(store.latestApproval()).toEqual(pendingApproval);
  });

  it('immediately polls client approvals after requestClientApproval was called', fakeAsync(() => {
    jasmine.clock().mockDate(new Date('2020-07-01T13:00:00.000+00:00'));
    const store = TestBed.inject(ClientStore);
    patchState(unprotected(store), {clientId: 'C.1234'});

    store.pollClientApprovals();

    store.requestClientApproval('reason', ['approver'], 1000, ['cc']);
    httpApiService.mockedObservables.requestClientApproval.next(
      newClientApproval({
        clientId: 'C.1234',
        status: {type: 'pending', reason: 'Need 1 more approver'},
      }),
    );
    expect(httpApiService.requestClientApproval).toHaveBeenCalledWith({
      clientId: 'C.1234',
      reason: 'reason',
      approvers: ['approver'],
      cc: ['cc'],
      expirationTimeUs: '1593609400000000',
    });

    // Additional call to listClientApprovals with polling interval 0, to
    // immediately fetch the pending approval after it was requested.
    expect(httpApiService.listClientApprovals).toHaveBeenCalledWith(
      'C.1234',
      0,
    );
  }));

  it('calls api to removeClientLabel and updates client when removeClientLabel() is called', () => {
    const store = TestBed.inject(ClientStore);
    patchState(unprotected(store), {clientId: 'C.1234'});
    patchState(unprotected(store), {
      client: newClient({
        clientId: 'C.1234',
        labels: [
          newClientLabel({name: 'label1'}),
          newClientLabel({name: 'label2'}),
        ],
      }),
    });
    const updatedClient = newClient({
      clientId: 'C.1234',
      labels: [newClientLabel({name: 'label2'})],
    });

    store.removeClientLabel('label1');
    httpApiService.mockedObservables.removeClientLabel.next('label1');
    httpApiService.mockedObservables.fetchClient.next(updatedClient);

    expect(httpApiService.fetchClient).toHaveBeenCalledWith('C.1234');
    expect(store.client()).toEqual(updatedClient);
  });

  it('addClientLabel() calls api to addClientLabel and updates client', () => {
    const store = TestBed.inject(ClientStore);
    patchState(unprotected(store), {clientId: 'C.1234'});
    patchState(unprotected(store), {
      client: newClient({
        clientId: 'C.1234',
        labels: [newClientLabel({name: 'label1'})],
      }),
    });
    const updatedClient = newClient({
      clientId: 'C.1234',
      labels: [
        newClientLabel({name: 'label1'}),
        newClientLabel({name: 'label2'}),
      ],
    });

    store.addClientLabel('label2');
    httpApiService.mockedObservables.addClientLabel.next({});
    httpApiService.mockedObservables.fetchClient.next(updatedClient);

    expect(httpApiService.addClientLabel).toHaveBeenCalledWith(
      'C.1234',
      'label2',
    );
    expect(httpApiService.fetchClient).toHaveBeenCalledWith('C.1234');
    expect(store.client()).toEqual(updatedClient);
  });

  it('initialize() calls api to fetchClientSnapshots and updates store', () => {
    const store = TestBed.inject(ClientStore);

    expect(store.clientSnapshots()).toHaveSize(0);

    store.initialize('C.1234');

    const snapshots = [
      newClientSnapshot({clientId: 'C.1234', timestamp: new Date(1)}),
    ];
    httpApiService.mockedObservables.fetchClientSnapshots.next(snapshots);

    expect(httpApiService.fetchClientSnapshots).toHaveBeenCalledWith('C.1234');
    expect(store.clientSnapshots()).toEqual(snapshots);
  });

  it('calling fetchClientSnapshots() stores snapshots in reverse order', fakeAsync(() => {
    const store = TestBed.inject(ClientStore);
    patchState(unprotected(store), {clientId: 'C.1234'});

    expect(store.clientSnapshots()).toHaveSize(0);
    const snapshots = [
      newClientSnapshot({
        clientId: 'C.1234',
        memorySize: BigInt(2),
        timestamp: new Date(2),
      }),
      newClientSnapshot({
        clientId: 'C.1234',
        memorySize: BigInt(1),
        timestamp: new Date(1),
      }),
    ];
    store.fetchClientSnapshots();
    httpApiService.mockedObservables.fetchClientSnapshots.next(snapshots);
    tick();

    expect(store.clientSnapshots()).toHaveSize(2);
    expect(store.clientSnapshots()).toEqual(snapshots.reverse());
  }));

  it('initialize() calls api to fetchClientStartupInfos and updates store', () => {
    const store = TestBed.inject(ClientStore);

    expect(store.clientStartupInfos()).toHaveSize(0);

    store.initialize('C.1234');

    const startupInfos = [
      {clientInfo: {clientName: 'test-client'}} as StartupInfo,
    ];
    httpApiService.mockedObservables.fetchClientStartupInfos.next(startupInfos);

    expect(httpApiService.fetchClientStartupInfos).toHaveBeenCalledWith(
      'C.1234',
    );
    expect(store.clientStartupInfos()).toEqual(startupInfos);
  });

  it('calling fetchClientStartupInfos() stores startupInfos in reverse order', fakeAsync(() => {
    const store = TestBed.inject(ClientStore);
    patchState(unprotected(store), {clientId: 'C.1234'});

    expect(store.clientStartupInfos()).toHaveSize(0);
    const startupInfos = [
      {
        clientInfo: {clientName: 'test-client-2'},
        timestamp: new Date(2),
      } as StartupInfo,
      {
        clientInfo: {clientName: 'test-client-1'},
        timestamp: new Date(1),
      } as StartupInfo,
    ];
    store.fetchClientStartupInfos();
    httpApiService.mockedObservables.fetchClientStartupInfos.next(startupInfos);
    tick();

    expect(store.clientStartupInfos()).toHaveSize(2);
    expect(store.clientStartupInfos()).toEqual(startupInfos.reverse());
  }));

  it('updates store when `pollFlows` is called', fakeAsync(() => {
    const store = TestBed.inject(ClientStore);
    patchState(unprotected(store), {clientId: 'C.1234'});
    patchState(unprotected(store), {hasAccess: true});

    expect(store.flows()).toHaveSize(0);

    store.pollFlows(FLOWS_PAGE_SIZE);
    tick();

    const flows = [newFlow({clientId: 'C.1234'})];
    httpApiService.mockedObservables.listFlowsForClient.next(flows);

    expect(httpApiService.listFlowsForClient).toHaveBeenCalledWith(
      {
        clientId: 'C.1234',
        count: FLOWS_PAGE_SIZE.toString(),
        topFlowsOnly: false,
      },
      DEFAULT_POLLING_INTERVAL,
    );
    expect(store.flows()).toEqual(flows);
  }));

  it('does not poll flows if access is not granted', fakeAsync(() => {
    const store = TestBed.inject(ClientStore);
    patchState(unprotected(store), {clientId: 'C.1234'});
    patchState(unprotected(store), {hasAccess: false});

    store.pollFlows(FLOWS_PAGE_SIZE);
    tick();

    expect(httpApiService.listFlowsForClient).not.toHaveBeenCalled();
  }));

  it('calling `pollScheduledFlows` updates store with scheduled flows', fakeAsync(() => {
    const store = TestBed.inject(ClientStore);
    const globalStore = TestBed.inject(GlobalStore);
    patchState(unprotected(globalStore), {
      currentUser: newGrrUser({name: 'testuser'}),
    });
    patchState(unprotected(store), {clientId: 'C.1234'});
    expect(store.scheduledFlows()).toHaveSize(0);

    store.pollScheduledFlows(0);
    tick();
    const scheduledFlows = [newScheduledFlow({clientId: 'C.1234'})];
    httpApiService.mockedObservables.listScheduledFlows.next(scheduledFlows);

    expect(httpApiService.listScheduledFlows).toHaveBeenCalledWith(
      'C.1234',
      'testuser',
      DEFAULT_POLLING_INTERVAL,
    );
    expect(store.scheduledFlows()).toEqual(scheduledFlows);
  }));

  it('initiallizes `flowByFlowId` to an empty map', () => {
    const store = TestBed.inject(ClientStore);
    patchState(unprotected(store), {clientId: 'C.1234'});

    expect(store.flowsByFlowId()).toHaveSize(0);
  });

  it('updates store with the flow when calling `pollFlow`', fakeAsync(() => {
    const store = TestBed.inject(ClientStore);
    patchState(unprotected(store), {clientId: 'C.1234'});
    patchState(unprotected(store), {hasAccess: true});

    store.pollFlow('f.ABCD');
    tick();
    const flow = newFlow({clientId: 'C.1234', flowId: 'f.ABCD'});
    httpApiService.mockedObservables.pollFlow.next(flow);

    expect(httpApiService.pollFlow).toHaveBeenCalledWith(
      'C.1234',
      'f.ABCD',
      DEFAULT_POLLING_INTERVAL,
    );
    expect(store.flowsByFlowId()).toEqual(new Map([['f.ABCD', flow]]));
  }));

  it('adjusts number of flows to poll when increaseFlowsCount() is called', fakeAsync(() => {
    const store = TestBed.inject(ClientStore);
    patchState(unprotected(store), {clientId: 'C.1234'});
    patchState(unprotected(store), {hasAccess: true});

    let expectedFlowCount = FLOWS_PAGE_SIZE;
    expect(store.flowsCount()).toEqual(expectedFlowCount);
    store.pollFlows(store.flowsCount, {injector});
    tick();
    expect(httpApiService.listFlowsForClient).toHaveBeenCalledOnceWith(
      {
        clientId: 'C.1234',
        count: expectedFlowCount.toString(),
        topFlowsOnly: false,
      },
      DEFAULT_POLLING_INTERVAL,
    );

    store.increaseFlowsCount(FLOWS_PAGE_SIZE);
    expectedFlowCount = FLOWS_PAGE_SIZE * 2;
    tick();

    expect(store.flowsCount()).toEqual(expectedFlowCount);
    expect(httpApiService.listFlowsForClient).toHaveBeenCalledWith(
      {
        clientId: 'C.1234',
        count: expectedFlowCount.toString(),
        topFlowsOnly: false,
      },
      DEFAULT_POLLING_INTERVAL,
    );
  }));

  it('returns false for hasMoreFlows when there are less flows than requested', fakeAsync(() => {
    const store = TestBed.inject(ClientStore);
    patchState(unprotected(store), {clientId: 'C.1234'});

    expect(store.flowsCount()).toBeGreaterThan(0);
    store.pollFlows(store.flowsCount());
    tick();
    httpApiService.mockedObservables.listFlowsForClient.next([]);

    expect(store.hasMoreFlows()).toBeFalse();
  }));

  it('returns true for hasMoreFlows when there are as many flows returned as requested', fakeAsync(() => {
    const store = TestBed.inject(ClientStore);
    patchState(unprotected(store), {clientId: 'C.1234'});
    patchState(unprotected(store), {hasAccess: true});

    store.pollFlows(store.flowsCount());
    tick();
    const flows = [];
    for (let i = 0; i < store.flowsCount(); i++) {
      flows.push(newFlow({flowId: `f.${i}`}));
    }
    httpApiService.mockedObservables.listFlowsForClient.next(flows);
    expect(store.flows().length).toEqual(FLOWS_PAGE_SIZE);
    expect(store.hasMoreFlows()).toBeTrue();
  }));

  it('calls api to startFlow when scheduleOrStartFlow() is called with client access', () => {
    const store = TestBed.inject(ClientStore);
    patchState(unprotected(store), {clientId: 'C.1234'});
    patchState(unprotected(store), {hasAccess: true});
    expect(store.triggerFetchFlows()).toEqual(0);

    const flowDescriptor = newFlowDescriptor({name: 'AmazingFlow'});
    const flowArgs = {
      'value': '/foo/bar',
    };
    store.scheduleOrStartFlow(flowDescriptor.name, flowArgs, false);
    httpApiService.mockedObservables.startFlow.next(newFlow());

    expect(httpApiService.startFlow).toHaveBeenCalledWith(
      'C.1234',
      flowDescriptor.name,
      flowArgs,
      false,
    );
    expect(store.flowsCount()).toEqual(FLOWS_PAGE_SIZE + 1);
    expect(store.triggerFetchFlows()).toEqual(1);
  });

  it('calls api to scheduleFlow when scheduleOrStartFlow() is called without client access', () => {
    const store = TestBed.inject(ClientStore);
    patchState(unprotected(store), {clientId: 'C.1234'});
    patchState(unprotected(store), {hasAccess: false});
    expect(store.triggerFetchScheduledFlows()).toEqual(0);

    const flowDescriptor = newFlowDescriptor({
      name: 'Kill',
      friendlyName: 'Kill',
      category: 'Kill',
    });
    const flowArgs = {
      '@type': 'example.com/grr.Args',
      'value': '/foo/bar',
    };
    store.scheduleOrStartFlow(flowDescriptor.name, flowArgs, true);
    httpApiService.mockedObservables.scheduleFlow.next(newScheduledFlow());

    expect(httpApiService.scheduleFlow).toHaveBeenCalledWith(
      'C.1234',
      flowDescriptor.name,
      flowArgs,
    );
    expect(store.triggerFetchScheduledFlows()).toEqual(1);
  });

  it('calls api to cancelFlow when cancelFlow() is called and increases trigger to poll of the flow list', () => {
    const store = TestBed.inject(ClientStore);
    patchState(unprotected(store), {clientId: 'C.1234'});
    expect(store.triggerFetchFlows()).toEqual(0);

    const flowId = 'f.1234';
    store.cancelFlow(flowId);
    httpApiService.mockedObservables.cancelFlow.next(newFlow({flowId}));

    expect(httpApiService.cancelFlow).toHaveBeenCalledWith('C.1234', flowId);
    expect(store.triggerFetchFlows()).toEqual(1);
  });

  it('initiallizes `flowResultsByFlowId` to an empty map', () => {
    const store = TestBed.inject(ClientStore);
    patchState(unprotected(store), {clientId: 'C.1234'});

    expect(store.flowResultsByFlowId()).toHaveSize(0);
  });

  it('updates store with the flow when calling `pollFlowResults`', fakeAsync(() => {
    const store = TestBed.inject(ClientStore);
    patchState(unprotected(store), {clientId: 'C.1234'});

    store.pollFlowResults({
      flowId: 'f.ABCD',
      offset: 0,
      count: 3,
      withTag: '',
      withType: '',
    });
    tick();
    const listFlowResultsResult = newListFlowResultsResult({
      totalCount: 3,
      results: [
        newFlowResult({
          payloadType: PayloadType.STAT_ENTRY,
        }),
        newFlowResult({
          payloadType: PayloadType.STAT_ENTRY,
        }),
        newFlowResult({
          payloadType: PayloadType.STAT_ENTRY,
        }),
      ],
    });
    httpApiService.mockedObservables.listResultsForFlow.next(
      listFlowResultsResult,
    );

    expect(httpApiService.listResultsForFlow).toHaveBeenCalledWith(
      {
        clientId: 'C.1234',
        flowId: 'f.ABCD',
        offset: 0,
        count: 3,
        withTag: '',
        withType: '',
      },
      DEFAULT_POLLING_INTERVAL,
    );

    const expectedFlowResults: FlowResults = {
      totalCount: 3,
      countLoaded: 3,
      flowResultsByPayloadType: new Map<PayloadType, FlowResult[]>([
        [PayloadType.STAT_ENTRY, [...listFlowResultsResult.results]],
      ]),
    };
    expect(store.flowResultsByFlowId()).toEqual(
      new Map([['f.ABCD', expectedFlowResults]]),
    );
  }));

  it('correctly groups results by type', fakeAsync(async () => {
    const store = TestBed.inject(ClientStore);
    patchState(unprotected(store), {clientId: 'C.1234'});
    store.pollFlowResults({
      flowId: 'f.ABCD',
      offset: 0,
      count: 3,
      withTag: '',
      withType: '',
    });
    tick();
    const listFlowResultsResult = newListFlowResultsResult({
      totalCount: 3,
      results: [
        newFlowResult({
          payloadType: PayloadType.STAT_ENTRY,
        }),
        newFlowResult({
          payloadType: PayloadType.EXECUTE_RESPONSE,
        }),
        newFlowResult({
          payloadType: PayloadType.STAT_ENTRY,
        }),
      ],
    });
    httpApiService.mockedObservables.listResultsForFlow.next(
      listFlowResultsResult,
    );

    const expectedFlowResults: FlowResults = {
      totalCount: 3,
      countLoaded: 3,
      flowResultsByPayloadType: new Map<PayloadType, FlowResult[]>([
        [
          PayloadType.STAT_ENTRY,
          [listFlowResultsResult.results[0], listFlowResultsResult.results[2]],
        ],
        [PayloadType.EXECUTE_RESPONSE, [listFlowResultsResult.results[1]]],
      ]),
    };
    expect(store.flowResultsByFlowId()).toEqual(
      new Map([['f.ABCD', expectedFlowResults]]),
    );
  }));

  it('repeatedly polls for flow results when flow is not finished', fakeAsync(() => {
    const store = TestBed.inject(ClientStore);
    patchState(unprotected(store), {clientId: 'C.1234'});
    const flow = newFlow({
      clientId: 'C.1234',
      flowId: 'f.ABCD',
      state: FlowState.RUNNING,
    });
    patchState(unprotected(store), {
      flowsByFlowId: new Map([['f.ABCD', flow]]),
    });

    store.pollFlowResults({
      flowId: 'f.ABCD',
      offset: 0,
      count: 3,
      withTag: '',
      withType: '',
    });
    tick();
    const listFlowResultsResult = newListFlowResultsResult({});
    httpApiService.mockedObservables.listResultsForFlow.next(
      listFlowResultsResult,
    );
    tick(DEFAULT_POLLING_INTERVAL);
    const listFlowResultsResultNew = newListFlowResultsResult({
      totalCount: 3,
      results: [
        newFlowResult({
          payloadType: PayloadType.STAT_ENTRY,
        }),
        newFlowResult({
          payloadType: PayloadType.STAT_ENTRY,
        }),
        newFlowResult({
          payloadType: PayloadType.STAT_ENTRY,
        }),
      ],
    });
    httpApiService.mockedObservables.listResultsForFlow.next(
      listFlowResultsResultNew,
    );

    const expectedFlowResults: FlowResults = {
      totalCount: 3,
      countLoaded: 3,
      flowResultsByPayloadType: new Map<PayloadType, FlowResult[]>([
        [PayloadType.STAT_ENTRY, [...listFlowResultsResultNew.results]],
      ]),
    };
    expect(store.flowResultsByFlowId()).toEqual(
      new Map([['f.ABCD', expectedFlowResults]]),
    );
  }));

  it('stops polling for flow results when flow is finished', fakeAsync(() => {
    const store = TestBed.inject(ClientStore);
    patchState(unprotected(store), {clientId: 'C.1234'});
    const flow = newFlow({
      clientId: 'C.1234',
      flowId: 'f.ABCD',
      state: FlowState.FINISHED,
    });
    patchState(unprotected(store), {
      flowsByFlowId: new Map([['f.ABCD', flow]]),
    });

    store.pollFlowResults({
      flowId: 'f.ABCD',
      offset: 0,
      count: 3,
      withTag: '',
      withType: '',
    });
    tick();
    const listFlowResultsResult = newListFlowResultsResult({});
    httpApiService.mockedObservables.listResultsForFlow.next(
      listFlowResultsResult,
    );
    tick(DEFAULT_POLLING_INTERVAL);
    const listFlowResultsResultNew = newListFlowResultsResult({
      totalCount: 3,
      results: [newFlowResult({}), newFlowResult({}), newFlowResult({})],
    });
    httpApiService.mockedObservables.listResultsForFlow.next(
      listFlowResultsResultNew,
    );

    const expectedFlowResults: FlowResults = {
      totalCount: 0,
      countLoaded: 0,
      flowResultsByPayloadType: new Map<PayloadType, FlowResult[]>([]),
    };
    expect(store.flowResultsByFlowId()).toEqual(
      new Map([['f.ABCD', expectedFlowResults]]),
    );
  }));

  it('skips startup info if timestamp is missing for `clientHistory`', fakeAsync(() => {
    const store = TestBed.inject(ClientStore);
    patchState(unprotected(store), {
      clientStartupInfos: [{timestamp: undefined}],
    });
    tick();
    expect(store.clientHistory()).toEqual([]);
  }));

  it('merges snapshot and startup by timestamp as `clientHistory`', fakeAsync(() => {
    const store = TestBed.inject(ClientStore);

    const historySnapshot5 = newClientSnapshot({timestamp: new Date(500)});
    const historySnapshot4 = newClientSnapshot({timestamp: new Date(400)});
    const historySnapshot1 = newClientSnapshot({timestamp: new Date(100)});
    patchState(unprotected(store), {
      clientSnapshots: [historySnapshot5, historySnapshot1, historySnapshot4],
    });
    const historyStartup3: StartupInfo = {timestamp: new Date(300)};
    const historyStartup2: StartupInfo = {timestamp: new Date(200)};
    patchState(unprotected(store), {
      clientStartupInfos: [historyStartup2, historyStartup3],
    });
    tick();

    expect(store.clientHistory()).toEqual([
      {snapshot: historySnapshot5},
      {snapshot: historySnapshot4},
      {startupInfo: historyStartup3},
      {startupInfo: historyStartup2},
      {snapshot: historySnapshot1},
    ]);
  }));
});
