import {discardPeriodicTasks, fakeAsync, TestBed, tick} from '@angular/core/testing';
import {ConfigService} from '@app/components/config/config';
import {ApiClient, ApiClientApproval, ApiFlow, ApiFlowState} from '@app/lib/api/api_interfaces';
import {HttpApiService} from '@app/lib/api/http_api_service';
import {ClientApproval} from '@app/lib/models/client';
import {FlowListEntry, flowListEntryFromFlow, FlowState} from '@app/lib/models/flow';
import {newFlowDescriptorMap, newFlowListEntry} from '@app/lib/models/model_test_util';
import {ClientPageFacade} from '@app/store/client_page_facade';
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
    };

    configFacade = mockConfigFacade();

    TestBed
        .configureTestingModule({
          imports: [],
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

    clientPageFacade.selectClient('C.1234');
    apiFetchClient$.next({
      clientId: 'C.1234',
    });
  });

  it('calls the API on latestApproval$ subscription', () => {
    clientPageFacade.latestApproval$.subscribe();
    expect(httpApiService.listApprovals).toHaveBeenCalledWith('C.1234');
  });

  it('emits latest pending approval in latestApproval$', (done) => {
    const expected: ClientApproval = {
      status: {type: 'pending', reason: 'Need at least 1 more approvers.'},
      reason: 'Pending reason',
      clientId: 'C.1234',
      approvalId: '2',
      requestedApprovers: ['b', 'c'],
      approvers: [],
    };

    clientPageFacade.latestApproval$.subscribe(approval => {
      if (approval !== undefined) {
        expect(approval).toEqual(expected);
        done();
      }
    });

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
  });

  it('calls the listFlow API on flowListEntries$ subscription',
     fakeAsync(() => {
       clientPageFacade.flowListEntries$.subscribe();

       // This is needed since flow list entries are updated in a timer loop
       // and the first call is scheduled after 0 milliseconds (meaning it
       // will happen right after it was scheduled, but still asynchronously).
       tick(1);
       discardPeriodicTasks();

       expect(httpApiService.listFlowsForClient).toHaveBeenCalledWith('C.1234');
     }));

  it('emits FlowListEntries in reverse-chronological order', fakeAsync(() => {
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

       let numCalls = 0;
       clientPageFacade.flowListEntries$.subscribe(flowListEntries => {
         // Skipping the initial value.
         numCalls += 1;
         if (flowListEntries.length > 0) {
           expect(flowListEntries).toEqual(expected);
         }
       });
       tick(1);
       discardPeriodicTasks();

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
       apiListFlowsForClient$.complete();

       expect(numCalls).toBe(2);
     }));

  it('polls and updates flowListEntries$ periodically', fakeAsync(() => {
       httpApiService.listFlowsForClient =
           jasmine.createSpy('listFlowsForClient').and.callFake(() => of([]));
       clientPageFacade.flowListEntries$.subscribe();

       tick(configService.config.flowListPollingIntervalMs * 2 + 1);
       discardPeriodicTasks();

       // First call happens at 0, next one at flowListPollingIntervalMs
       // and the next one at flowListPollingIntervalMs * 2.
       expect(httpApiService.listFlowsForClient).toHaveBeenCalledTimes(3);
     }));

  it('updates flow list entries results periodically', fakeAsync(() => {
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
       tick(1);

       // Ensure that there's a results query to be updated.
       clientPageFacade.queryFlowResults({
         flowId: '1',
         offset: 0,
         count: 100,
       });

       httpApiService.listResultsForFlow =
           jasmine.createSpy('listResultsForFlow').and.callFake(() => of([]));

       tick(configService.config.flowResultsPollingIntervalMs * 2 + 1);
       discardPeriodicTasks();

       expect(httpApiService.listResultsForFlow).toHaveBeenCalledTimes(3);
     }));

  it('does not update flow list entries results when queryFlowResults wasn\'t called',
     fakeAsync(() => {
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
       tick(1);

       httpApiService.listResultsForFlow =
           jasmine.createSpy('listResultsForFlow').and.callFake(() => of([]));

       tick(configService.config.flowResultsPollingIntervalMs * 2 + 1);
       discardPeriodicTasks();

       expect(httpApiService.listResultsForFlow).not.toHaveBeenCalled();
     }));

  it('updates flowListEntry\'s result set on queryFlowResults()',
     fakeAsync(() => {
       let numCalls = 0;
       clientPageFacade.flowListEntries$.subscribe((fle) => {
         numCalls += 1;
         // Take into account the initial empty list that will be emitted
         // first.
         if (numCalls === 4) {
           expect(fle[0].resultSets.length).toBeGreaterThan(0);
         }
       });
       tick(1);

       apiListFlowsForClient$.next([{
         flowId: '1',
         clientId: 'C.1234',
         lastActiveAt: '999000',
         startedAt: '123000',
         creator: 'rick',
         name: 'ListProcesses',
         state: ApiFlowState.RUNNING,
       }]);
       apiListFlowsForClient$.complete();

       clientPageFacade.queryFlowResults({
         flowId: '1',
         offset: 0,
         count: 100,
         withType: 'someType',
         withTag: 'someTag',
       });
       tick(1);
       discardPeriodicTasks();

       // Initial, then first fetched, then query flow results.
       expect(numCalls).toBe(3);
     }));

  it('calls the API on startFlow', () => {
    clientPageFacade.startFlowConfiguration('ListProcesses');
    clientPageFacade.startFlow({foo: 1});
    expect(httpApiService.startFlow)
        .toHaveBeenCalledWith('C.1234', 'ListProcesses', {foo: 1});
  });

  it('emits the started flow in flowListEntries$', (done) => {
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
    clientPageFacade.cancelFlow('5678');
    expect(httpApiService.cancelFlow).toHaveBeenCalledWith('C.1234', '5678');
  });

  it('emits the cancelled flow in flowListEntries$', (done) => {
    clientPageFacade.cancelFlow('5678');

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

  it('fetches client data only after selectedClient$ is subscribed to', fakeAsync(() => {
    expect(httpApiService.fetchClient).not.toHaveBeenCalled();
    clientPageFacade.selectedClient$.subscribe();

    // This is needed since selected client is updated in a timer loop
    // and the first call is scheduled after 0 milliseconds (meaning it
    // will happen right after it was scheduled, but still asynchronously).
    tick(1);
    discardPeriodicTasks();
    expect(httpApiService.fetchClient).toHaveBeenCalledWith('C.1234');
  }));

  it('polls and updates selectedClient$ periodically', fakeAsync(() => {
    clientPageFacade.selectedClient$.subscribe();

    tick(configService.config.selectedClientPollingIntervalMs * 2 + 1);
    discardPeriodicTasks();

    // First call happens at 0, next one at selectedClientPollingIntervalMs
    // and the next one at selectedClientPollingIntervalMs * 2.
    expect(httpApiService.fetchClient).toHaveBeenCalledTimes(3);
  }));

  it('polls and updates selectedClient$ when another client is selected', fakeAsync(() => {
    clientPageFacade.selectedClient$.subscribe();

    // This is needed since selected client is updated in a timer loop
    // and the first call is scheduled after 0 milliseconds (meaning it
    // will happen right after it was scheduled, but still asynchronously).
    tick(1);
    expect(httpApiService.fetchClient).toHaveBeenCalledWith('C.1234');

    clientPageFacade.selectClient('C.5678');
    tick(1);
    discardPeriodicTasks();

    expect(httpApiService.fetchClient).toHaveBeenCalledWith('C.5678');
  }));

  it('stops updating selectedClient$ when unsubscribed from it', fakeAsync(() => {
    const subscribtion = clientPageFacade.selectedClient$.subscribe();

    // This is needed since selected client is updated in a timer loop
    // and the first call is scheduled after 0 milliseconds (meaning it
    // will happen right after it was scheduled, but still asynchronously).
    tick(1);
    expect(httpApiService.fetchClient).toHaveBeenCalledTimes(1);

    subscribtion.unsubscribe();
    // Fast forward for another 2 polling intervals, to check if
    // the client is still fetched or not after unsubscribe.
    // The number of calls to fetchClient() should stay the same
    tick(configService.config.selectedClientPollingIntervalMs * 2 + 1);
    discardPeriodicTasks();

    expect(httpApiService.fetchClient).toHaveBeenCalledTimes(1);
  }));
});
