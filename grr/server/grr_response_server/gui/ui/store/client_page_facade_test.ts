import {discardPeriodicTasks, fakeAsync, TestBed, tick} from '@angular/core/testing';
import {ConfigService} from '@app/components/config/config';
import {ApiClient, ApiClientApproval, ApiFlow, ApiFlowState} from '@app/lib/api/api_interfaces';
import {HttpApiService} from '@app/lib/api/http_api_service';
import {ClientApproval} from '@app/lib/models/client';
import {FlowListEntry, flowListEntryFromFlow, FlowState} from '@app/lib/models/flow';
import {newFlowDescriptorMap, newFlowListEntry} from '@app/lib/models/model_test_util';
import {ClientPageFacade} from '@app/store/client_page_facade';
import {GrrStoreModule} from '@app/store/store_module';
import {initTestEnvironment} from '@app/testing';
import {of, Subject} from 'rxjs';

import {ConfigFacade} from './config_facade';
import {ConfigFacadeMock, mockConfigFacade} from './config_facade_test_util';

initTestEnvironment();

describe('ClientPageFacade', () => {
  let httpApiService: Partial<HttpApiService>;
  let clientPageFacade: ClientPageFacade;
  let configService: ConfigService;
  let apiListApprovals$: Subject<ReadonlyArray<ApiClientApproval>>;
  let apiFetchClient$: Subject<ApiClient>;
  let apiListFlowsForClient$: Subject<ReadonlyArray<ApiFlow>>;
  let apiStartFlow$: Subject<ApiFlow>;
  let apiCancelFlow$: Subject<ApiFlow>;
  let configFacade: ConfigFacadeMock;

  beforeEach(() => {
    apiListApprovals$ = new Subject();
    apiFetchClient$ = new Subject();
    apiListFlowsForClient$ = new Subject();
    apiStartFlow$ = new Subject();
    apiCancelFlow$ = new Subject();
    httpApiService = {
      listApprovals:
          jasmine.createSpy('listApprovals').and.returnValue(apiListApprovals$),
      fetchClient:
          jasmine.createSpy('fetchClient').and.returnValue(apiFetchClient$),
      listFlowsForClient: jasmine.createSpy('listFlowsForClient')
                              .and.returnValue(apiListFlowsForClient$),
      startFlow: jasmine.createSpy('startFlow').and.returnValue(apiStartFlow$),
      cancelFlow:
          jasmine.createSpy('cancelFlow').and.returnValue(apiCancelFlow$),
      listResultsForFlow:
          jasmine.createSpy('listResultsForFlow').and.returnValue(of([])),
      batchListResultsForFlow: jasmine.createSpy('listResultsForMultipleFlows')
                                   .and.returnValue(of([])),
    };

    configFacade = mockConfigFacade();

    TestBed
        .configureTestingModule({
          imports: [
            GrrStoreModule,
          ],
          providers: [
            ClientPageFacade,
            // Apparently, useValue creates a copy of the object. Using
            // useFactory, to make sure the instance is shared.
            {provide: HttpApiService, useFactory: () => httpApiService},
            {provide: ConfigFacade, useFactory: () => configFacade},
          ],
        })
        .compileComponents();

    clientPageFacade = TestBed.inject(ClientPageFacade);
    configService = TestBed.inject(ConfigService);
  });

  it('calls the API on listClientApprovals', () => {
    clientPageFacade.listClientApprovals('C.1234');
    expect(httpApiService.listApprovals).toHaveBeenCalledWith('C.1234');
  });

  it('emits the latest pending approval in latestApproval$', (done) => {
    clientPageFacade.selectClient('C.1234');
    apiFetchClient$.next({
      clientId: 'C.1234',
    });

    clientPageFacade.listClientApprovals('C.1234');
    apiListApprovals$.next([
      {
        subject: {clientId: 'C.1234'},
        id: '1',
        reason: 'Old reason',
        isValid: false,
        isValidMessage: 'Approval request is expired.',
        approvers: ['me', 'b'],
        notifiedUsers: ['b', 'c'],
      },
      {
        subject: {clientId: 'C.1234'},
        id: '2',
        reason: 'Pending reason',
        isValid: false,
        isValidMessage: 'Need at least 1 more approvers.',
        approvers: ['me'],
        notifiedUsers: ['b', 'c'],
      },
    ]);

    const expected: ClientApproval = {
      status: {type: 'pending', reason: 'Need at least 1 more approvers.'},
      reason: 'Pending reason',
      clientId: 'C.1234',
      approvalId: '2',
      requestedApprovers: ['b', 'c'],
      approvers: [],
    };

    clientPageFacade.latestApproval$.subscribe(approval => {
      expect(approval).toEqual(expected);
      done();
    });
  });

  it('calls the listFlow API on select()', () => {
    clientPageFacade.selectClient('C.1234');
    expect(httpApiService.listFlowsForClient).toHaveBeenCalledWith('C.1234');
  });

  it('emits FlowListEntries in reverse-chronological order', done => {
    clientPageFacade.selectClient('C.1234');

    apiListFlowsForClient$.next([
      {
        flowId: '1',
        clientId: 'C.1234',
        lastActiveAt: '999000',
        startedAt: '123000',
        creator: 'rick',
        name: 'ListProcesses',
        state: ApiFlowState.RUNNING,
      },
      {
        flowId: '2',
        clientId: 'C.1234',
        lastActiveAt: '999000',
        startedAt: '789000',
        creator: 'morty',
        name: 'GetFile',
        state: ApiFlowState.RUNNING,
      },
      {
        flowId: '3',
        clientId: 'C.1234',
        lastActiveAt: '999000',
        startedAt: '456000',
        creator: 'morty',
        name: 'KeepAlive',
        state: ApiFlowState.TERMINATED,
      },
    ]);

    const expected: FlowListEntry[] = [
      {
        flowId: '2',
        clientId: 'C.1234',
        lastActiveAt: new Date(999),
        startedAt: new Date(789),
        creator: 'morty',
        name: 'GetFile',
        state: FlowState.RUNNING,
      },
      {
        flowId: '3',
        clientId: 'C.1234',
        lastActiveAt: new Date(999),
        startedAt: new Date(456),
        creator: 'morty',
        name: 'KeepAlive',
        state: FlowState.FINISHED,
      },
      {
        flowId: '1',
        clientId: 'C.1234',
        lastActiveAt: new Date(999),
        startedAt: new Date(123),
        creator: 'rick',
        name: 'ListProcesses',
        state: FlowState.RUNNING,
      },
    ].map(f => newFlowListEntry(f));

    clientPageFacade.flowListEntries$.subscribe(flowListEntries => {
      expect(flowListEntries).toEqual(expected);
      done();
    });
  });

  it('polls and updates flowListEntries$ periodically', fakeAsync(() => {
       clientPageFacade.selectClient('C.1234');

       httpApiService.listFlowsForClient =
           jasmine.createSpy('listFlowsForClient').and.callFake(() => of([]));
       clientPageFacade.flowListEntries$.subscribe();

       tick(configService.config.flowListPollingIntervalMs * 2 + 1);
       discardPeriodicTasks();

       expect(httpApiService.listFlowsForClient).toHaveBeenCalledTimes(2);
     }));

  it('updates flow list entries results periodically', fakeAsync(() => {
       clientPageFacade.selectClient('C.1234');
       clientPageFacade.flowListEntries$.subscribe();

       httpApiService.listFlowsForClient =
           jasmine.createSpy('listFlowsForClient')
               .and.callFake(() => of([
                               {
                                 flowId: '1',
                                 clientId: 'C.1234',
                                 lastActiveAt: '999000',
                                 startedAt: '123000',
                                 creator: 'rick',
                                 name: 'ListProcesses',
                                 state: ApiFlowState.RUNNING,
                               },
                             ]));
       // Make sure flows are polled twice. Flow results updates are only
       // triggered when there are 2 flow list entries snapshots buffered.
       tick(configService.config.flowListPollingIntervalMs * 2 + 1);

       // Ensure that there's a results query to be updated.
       clientPageFacade.queryFlowResults({
         flowId: '1',
         offset: 0,
         count: 100,
       });

       httpApiService.batchListResultsForFlow =
           jasmine.createSpy('batchListResultsForFlow')
               .and.callFake(() => of([]));

       tick(configService.config.flowResultsPollingIntervalMs * 2 + 1);
       discardPeriodicTasks();

       expect(httpApiService.batchListResultsForFlow).toHaveBeenCalledTimes(2);
     }));

  it('does not update flow list entries results when no existing result sets',
     fakeAsync(() => {
       clientPageFacade.selectClient('C.1234');
       clientPageFacade.flowListEntries$.subscribe();

       httpApiService.listFlowsForClient =
           jasmine.createSpy('listFlowsForClient')
               .and.callFake(() => of([
                               {
                                 flowId: '1',
                                 clientId: 'C.1234',
                                 lastActiveAt: '999000',
                                 startedAt: '123000',
                                 creator: 'rick',
                                 name: 'ListProcesses',
                                 state: ApiFlowState.RUNNING,
                               },
                             ]));
       // Make sure flows are polled twice. Flow results updates are only
       // triggered when there are 2 flow list entries snapshots buffered.
       tick(configService.config.flowListPollingIntervalMs * 2 + 1);

       httpApiService.batchListResultsForFlow =
           jasmine.createSpy('batchListResultsForFlow')
               .and.callFake(() => of([]));

       tick(configService.config.flowResultsPollingIntervalMs * 2 + 1);
       discardPeriodicTasks();

       expect(httpApiService.batchListResultsForFlow).not.toHaveBeenCalled();
     }));

  it('updates flowListEntry\'s result set on queryFlowResults()', (done) => {
    clientPageFacade.selectClient('C.1234');
    apiListFlowsForClient$.next([{
      flowId: '1',
      clientId: 'C.1234',
      lastActiveAt: '999000',
      startedAt: '123000',
      creator: 'rick',
      name: 'ListProcesses',
      state: ApiFlowState.RUNNING,
    }]);

    clientPageFacade.queryFlowResults({
      flowId: '1',
      offset: 0,
      count: 100,
      withType: 'someType',
      withTag: 'someTag',
    });

    clientPageFacade.flowListEntries$.subscribe((fle) => {
      if (fle[0].resultSets.length > 0) {
        done();
      }
    });
  });

  it('calls the API on startFlow', () => {
    clientPageFacade.selectClient('C.1234');
    clientPageFacade.startFlowConfiguration('ListProcesses');
    clientPageFacade.startFlow({foo: 1});
    expect(httpApiService.startFlow)
        .toHaveBeenCalledWith('C.1234', 'ListProcesses', {foo: 1});
  });

  it('emits the started flow in flowListEntries$', (done) => {
    clientPageFacade.selectClient('C.1234');
    clientPageFacade.startFlowConfiguration('ListProcesses');
    clientPageFacade.startFlow({});

    apiStartFlow$.next({
      flowId: '1',
      clientId: 'C.1234',
      lastActiveAt: '999000',
      startedAt: '123000',
      creator: 'rick',
      name: 'ListProcesses',
      state: ApiFlowState.RUNNING,
    });

    const expected: FlowListEntry[] = [
      flowListEntryFromFlow({
        flowId: '1',
        clientId: 'C.1234',
        lastActiveAt: new Date(999),
        startedAt: new Date(123),
        creator: 'rick',
        name: 'ListProcesses',
        args: undefined,
        progress: undefined,
        state: FlowState.RUNNING,
      }),
    ];

    clientPageFacade.flowListEntries$.subscribe(flows => {
      expect(flows).toEqual(expected);
      done();
    });
  });

  it('emits the error in startFlowState', (done) => {
    clientPageFacade.selectClient('C.1234');
    clientPageFacade.startFlowConfiguration('ListProcesses');
    clientPageFacade.startFlow({});
    apiStartFlow$.error(new Error('foobazzle rapidly disintegrated'));

    clientPageFacade.startFlowState$.subscribe(state => {
      expect(state).toEqual(
          {state: 'error', error: 'foobazzle rapidly disintegrated'});
      done();
    });
  });

  it('stops flow configuration after successful started flow', (done) => {
    clientPageFacade.selectClient('C.1234');
    clientPageFacade.startFlowConfiguration('ListProcesses');
    clientPageFacade.startFlow({});

    apiStartFlow$.next({
      flowId: '1',
      clientId: 'C.1234',
      lastActiveAt: '999000',
      startedAt: '123000',
      creator: 'rick',
      name: 'ListProcesses',
      state: ApiFlowState.RUNNING,
    });

    clientPageFacade.selectedFlowDescriptor$.subscribe(fd => {
      expect(fd).toBeUndefined();
      done();
    });
  });

  it('calls the API on cancelFlow', () => {
    clientPageFacade.cancelFlow('C.1234', '5678');
    expect(httpApiService.cancelFlow).toHaveBeenCalledWith('C.1234', '5678');
  });

  it('emits the cancelled flow in flowListEntries$', (done) => {
    clientPageFacade.selectClient('C.1234');
    clientPageFacade.cancelFlow('C.1234', '5678');

    apiCancelFlow$.next({
      flowId: '5678',
      clientId: 'C.1234',
      lastActiveAt: '999000',
      startedAt: '123000',
      creator: 'rick',
      name: 'ListProcesses',
      state: ApiFlowState.TERMINATED,
    });

    const expected: FlowListEntry[] = [
      flowListEntryFromFlow({
        flowId: '5678',
        clientId: 'C.1234',
        lastActiveAt: new Date(999),
        startedAt: new Date(123),
        creator: 'rick',
        name: 'ListProcesses',
        args: undefined,
        progress: undefined,
        state: FlowState.FINISHED,
      }),
    ];

    clientPageFacade.flowListEntries$.subscribe(flows => {
      expect(flows).toEqual(expected);
      done();
    });
  });


  it('emits undefined as selectedFlowDescriptor$ initially', done => {
    clientPageFacade.selectedFlowDescriptor$.subscribe(flow => {
      expect(flow).toBeUndefined();
      done();
    });
  });

  it('emits the selected flow in selectedFlowDescriptor$', done => {
    configFacade.flowDescriptorsSubject.next(newFlowDescriptorMap(
        {name: 'ClientSideFileFinder'},
        {name: 'KeepAlive', defaultArgs: {foo: 1}},
        ));
    clientPageFacade.startFlowConfiguration('KeepAlive');
    clientPageFacade.selectedFlowDescriptor$.subscribe(flow => {
      expect(flow!.name).toEqual('KeepAlive');
      expect(flow!.defaultArgs).toEqual({foo: 1});
      done();
    });
  });

  it('emits the supplied args in selectedFlowDescriptor$', done => {
    configFacade.flowDescriptorsSubject.next(
        newFlowDescriptorMap({name: 'KeepAlive', defaultArgs: {foo: 1}}));
    clientPageFacade.startFlowConfiguration('KeepAlive', {foo: 42});
    clientPageFacade.selectedFlowDescriptor$.subscribe(flow => {
      expect(flow!.name).toEqual('KeepAlive');
      expect(flow!.defaultArgs).toEqual({foo: 42});
      done();
    });
  });

  it('fails when selecting unknown flow', done => {
    configFacade.flowDescriptorsSubject.next(newFlowDescriptorMap(
        {name: 'KeepAlive'},
        ));

    clientPageFacade.startFlowConfiguration('unknown');
    clientPageFacade.selectedFlowDescriptor$.subscribe(
        () => {},
        err => {
          done();
        },
    );
  });


  it('emits undefined in selectedFlowDescriptor$ after unselectFlow()',
     done => {
       configFacade.flowDescriptorsSubject.next(newFlowDescriptorMap(
           {name: 'ClientSideFileFinder'},
           {name: 'KeepAlive'},
           ));

       clientPageFacade.startFlowConfiguration('KeepAlive');
       clientPageFacade.stopFlowConfiguration();
       clientPageFacade.selectedFlowDescriptor$.subscribe(flow => {
         expect(flow).toBeUndefined();
         done();
       });
     });
});
