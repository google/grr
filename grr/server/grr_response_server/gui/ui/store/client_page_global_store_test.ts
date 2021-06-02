import {HttpErrorResponse} from '@angular/common/http';
import {discardPeriodicTasks, fakeAsync, TestBed, tick} from '@angular/core/testing';
import {ConfigService} from '@app/components/config/config';
import {ApiClient, ApiClientApproval, ApiFlow, ApiFlowState, ApiScheduledFlow, ApproverSuggestion} from '@app/lib/api/api_interfaces';
import {HttpApiService, MissingApprovalError} from '@app/lib/api/http_api_service';
import {Client, ClientApproval} from '@app/lib/models/client';
import {Flow, FlowState} from '@app/lib/models/flow';
import {newClient, newFlow, newFlowDescriptorMap} from '@app/lib/models/model_test_util';
import {ClientPageGlobalStore} from '@app/store/client_page_global_store';
import {initTestEnvironment, removeUndefinedKeys} from '@app/testing';
import {firstValueFrom, of, Subject, throwError} from 'rxjs';

import {ConfigGlobalStore} from './config_global_store';
import {ConfigGlobalStoreMock, mockConfigGlobalStore} from './config_global_store_test_util';
import {UserGlobalStore} from './user_global_store';
import {mockUserGlobalStore, UserGlobalStoreMock} from './user_global_store_test_util';


initTestEnvironment();


describe('ClientPageGlobalStore', () => {
  let httpApiService: Partial<HttpApiService>;
  let clientPageGlobalStore: ClientPageGlobalStore;
  let configService: ConfigService;
  let apiListApprovals$: Subject<ReadonlyArray<ApiClientApproval>>;
  let apiFetchClient$: Subject<ApiClient>;
  let apiListFlowsForClient$: Subject<ReadonlyArray<ApiFlow>>;
  let apiListScheduledFlows$: Subject<ReadonlyArray<ApiScheduledFlow>>;
  let apiStartFlow$: Subject<ApiFlow>;
  let apiScheduleFlow$: Subject<ApiScheduledFlow>;
  let apiCancelFlow$: Subject<ApiFlow>;
  let apiSuggestApprovers$: Subject<ReadonlyArray<ApproverSuggestion>>;
  let apiRemoveClientLabel$: Subject<string>;
  let configGlobalStore: ConfigGlobalStoreMock;
  let userGlobalStore: UserGlobalStoreMock;
  let apiVerifyClientAccess$: Subject<boolean>;

  beforeEach(() => {
    apiListApprovals$ = new Subject();
    apiFetchClient$ = new Subject();
    apiListFlowsForClient$ = new Subject();
    apiListScheduledFlows$ = new Subject();
    apiStartFlow$ = new Subject();
    apiScheduleFlow$ = new Subject();
    apiCancelFlow$ = new Subject();
    apiRemoveClientLabel$ = new Subject();
    apiSuggestApprovers$ = new Subject();
    apiVerifyClientAccess$ = new Subject();
    httpApiService = {
      listApprovals:
          jasmine.createSpy('listApprovals').and.returnValue(apiListApprovals$),
      fetchClient:
          jasmine.createSpy('fetchClient').and.returnValue(apiFetchClient$),
      listFlowsForClient: jasmine.createSpy('listFlowsForClient')
                              .and.returnValue(apiListFlowsForClient$),
      listScheduledFlows: jasmine.createSpy('listScheduledFlows')
                              .and.returnValue(apiListScheduledFlows$),
      startFlow: jasmine.createSpy('startFlow').and.returnValue(apiStartFlow$),
      scheduleFlow:
          jasmine.createSpy('scheduleFlow').and.returnValue(apiScheduleFlow$),
      cancelFlow:
          jasmine.createSpy('cancelFlow').and.returnValue(apiCancelFlow$),
      listResultsForFlow:
          jasmine.createSpy('listResultsForFlow').and.returnValue(of([])),
      suggestApprovers: jasmine.createSpy('suggestApprovers')
                            .and.returnValue(apiSuggestApprovers$),
      removeClientLabel: jasmine.createSpy('removeClientLabel')
                             .and.returnValue(apiRemoveClientLabel$),
      verifyClientAccess: jasmine.createSpy('verifyClientAccess')
                              .and.returnValue(apiVerifyClientAccess$),

    };

    configGlobalStore = mockConfigGlobalStore();
    userGlobalStore = mockUserGlobalStore();

    TestBed
        .configureTestingModule({
          imports: [],
          providers: [
            ClientPageGlobalStore,
            // Apparently, useValue creates a copy of the object. Using
            // useFactory, to make sure the instance is shared.
            {provide: HttpApiService, useFactory: () => httpApiService},
            {provide: ConfigGlobalStore, useFactory: () => configGlobalStore},
            {provide: UserGlobalStore, useFactory: () => userGlobalStore},
          ],
        })
        .compileComponents();

    clientPageGlobalStore = TestBed.inject(ClientPageGlobalStore);
    configService = TestBed.inject(ConfigService);

    clientPageGlobalStore.selectClient('C.1234');
    apiFetchClient$.next({
      clientId: 'C.1234',
    });
    userGlobalStore.currentUserSubject.next({name: 'testuser'});
  });

  it('polls the API on latestApproval$ subscription ', fakeAsync(() => {
       httpApiService.listApprovals =
           jasmine.createSpy('listApprovals').and.callFake(() => of([]));
       clientPageGlobalStore.latestApproval$.subscribe();

       tick(configService.config.approvalPollingIntervalMs * 2 + 1);
       discardPeriodicTasks();

       // First call happens at 0, next one at approvalPollingIntervalMs
       // and the next one at approvalPollingIntervalMs * 2.
       expect(httpApiService.listApprovals).toHaveBeenCalledTimes(3);
     }));

  it('emits latest pending approval in latestApproval$', fakeAsync(() => {
       const expected: ClientApproval = {
         status: {type: 'pending', reason: 'Need at least 1 more approvers.'},
         reason: 'Pending reason',
         requestor: 'testuser',
         clientId: 'C.1234',
         approvalId: '2',
         requestedApprovers: ['b', 'c'],
         approvers: [],
         subject: newClient({
           clientId: 'C.1234',
           fleetspeakEnabled: false,
         }),
       };

       let latestApproval: ClientApproval|undefined = undefined;
       clientPageGlobalStore.latestApproval$.subscribe(approval => {
         latestApproval = approval;
         if (approval !== undefined) {
           expect(removeUndefinedKeys(latestApproval)).toEqual(expected);
         }
       });

       tick(configService.config.approvalPollingIntervalMs * 2 + 1);


       apiListApprovals$.next([
         {
           subject: {
             clientId: 'C.1234',
             fleetspeakEnabled: false,
             knowledgeBase: {},
             labels: [],
             age: '0',
           },
           id: '1',
           reason: 'Old reason',
           requestor: 'testuser',
           isValid: false,
           isValidMessage: 'Approval request is expired.',
           approvers: ['testuser'],
           notifiedUsers: ['b', 'c'],
         },
         {
           subject: {
             clientId: 'C.1234',
             fleetspeakEnabled: false,
             knowledgeBase: {},
             labels: [],
             age: '0',
           },
           id: '2',
           reason: 'Pending reason',
           requestor: 'testuser',
           isValid: false,
           isValidMessage: 'Need at least 1 more approvers.',
           approvers: ['testuser'],
           notifiedUsers: ['b', 'c'],
         },
       ]);

       discardPeriodicTasks();
       expect(latestApproval).not.toBeUndefined();
     }));

  it('polls the API on hasAccess$ subscription', fakeAsync(() => {
       expect(httpApiService.verifyClientAccess).not.toHaveBeenCalled();

       clientPageGlobalStore.hasAccess$.subscribe();

       tick(configService.config.approvalPollingIntervalMs * 2 + 1);
       discardPeriodicTasks();

       // First call happens at 0, next one at approvalPollingIntervalMs
       // and the next one at approvalPollingIntervalMs * 2.
       expect(httpApiService.verifyClientAccess).toHaveBeenCalledTimes(3);
     }));

  it('emits latest access value in hasAccess$', fakeAsync(async () => {
       const promise = firstValueFrom(clientPageGlobalStore.hasAccess$);
       tick(configService.config.approvalPollingIntervalMs * 2 + 1);
       apiVerifyClientAccess$.next(true);
       expect(await promise).toBeTrue();
     }));

  it('approvalsEnabled$ emits true if access is false', fakeAsync(async () => {
       const promise = firstValueFrom(clientPageGlobalStore.approvalsEnabled$);
       tick(configService.config.approvalPollingIntervalMs * 2 + 1);
       apiVerifyClientAccess$.next(false);
       apiListApprovals$.next([]);
       expect(await promise).toBeTrue();
     }));

  it('approvalsEnabled$ emits true if access is true and approval is granted',
     fakeAsync(async () => {
       const promise = firstValueFrom(clientPageGlobalStore.approvalsEnabled$);
       tick(configService.config.approvalPollingIntervalMs * 2 + 1);
       apiVerifyClientAccess$.next(false);
       apiListApprovals$.next([{
         subject: {
           clientId: 'C.1234',
           fleetspeakEnabled: false,
           knowledgeBase: {},
           labels: [],
           age: '0',
         },
         id: '2',
         reason: '-',
         requestor: 'testuser',
         isValid: true,
         approvers: ['testuser1'],
         notifiedUsers: [],
       }]);
       expect(await promise).toBeTrue();
     }));

  it('approvalsEnabled$ emits false if access is true and no approval exists',
     fakeAsync(async () => {
       const promise = firstValueFrom(clientPageGlobalStore.approvalsEnabled$);
       tick(configService.config.approvalPollingIntervalMs * 2 + 1);
       apiVerifyClientAccess$.next(true);
       apiListApprovals$.next([]);
       expect(await promise).toBeFalse();
     }));

  it('calls the listFlow API on flowListEntries$ subscription',
     fakeAsync(() => {
       clientPageGlobalStore.flowListEntries$.subscribe();

       // This is needed since flow list entries are updated in a timer loop
       // and the first call is scheduled after 0 milliseconds (meaning it
       // will happen right after it was scheduled, but still asynchronously).
       tick(1);
       discardPeriodicTasks();

       expect(httpApiService.listFlowsForClient).toHaveBeenCalledWith('C.1234');
     }));

  it('emits FlowListEntries in reverse-chronological order', fakeAsync(() => {
       const expected: Flow[] = [
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
       ].map(f => newFlow(f));

       let numCalls = 0;
       clientPageGlobalStore.flowListEntries$.subscribe(flowListEntries => {
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
       clientPageGlobalStore.flowListEntries$.subscribe();

       tick(configService.config.flowListPollingIntervalMs * 2 + 1);
       discardPeriodicTasks();

       // First call happens at 0, next one at flowListPollingIntervalMs
       // and the next one at flowListPollingIntervalMs * 2.
       expect(httpApiService.listFlowsForClient).toHaveBeenCalledTimes(3);
     }));

  it('continues polling flowListEntries$ on error', fakeAsync(() => {
       httpApiService.listFlowsForClient =
           jasmine.createSpy('listFlowsForClient')
               .and.callFake(
                   () => throwError(
                       new MissingApprovalError(new HttpErrorResponse(
                           {error: {message: 'Approval missing'}}))));
       clientPageGlobalStore.flowListEntries$.subscribe();

       tick(configService.config.flowListPollingIntervalMs * 2 + 1);
       discardPeriodicTasks();

       // First call happens at 0, next one at flowListPollingIntervalMs
       // and the next one at flowListPollingIntervalMs * 2.
       expect(httpApiService.listFlowsForClient).toHaveBeenCalledTimes(3);
     }));

  it('calls the API on startFlow', () => {
    clientPageGlobalStore.startFlowConfiguration('ListProcesses');
    clientPageGlobalStore.startFlow({foo: 1});
    expect(httpApiService.startFlow)
        .toHaveBeenCalledWith('C.1234', 'ListProcesses', {foo: 1});
  });

  it('emits the started flow in flowListEntries$', (done) => {
    clientPageGlobalStore.startFlowConfiguration('ListProcesses');
    clientPageGlobalStore.startFlow({});

    apiStartFlow$.next({
      flowId: '1',
      clientId: 'C.1234',
      lastActiveAt: '999000',
      startedAt: '123000',
      creator: 'rick',
      name: 'ListProcesses',
      state: ApiFlowState.RUNNING,
    });

    const expected: Flow[] = [
      newFlow({
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

    clientPageGlobalStore.flowListEntries$.subscribe(flows => {
      expect(flows).toEqual(expected);
      done();
    });
  });

  it('preserves existing flowListEntries$ when starting flow', (done) => {
    clientPageGlobalStore.startFlowConfiguration('StartedFlow1');
    clientPageGlobalStore.startFlow({});

    apiStartFlow$.next({
      flowId: '1',
      clientId: 'C.1234',
      lastActiveAt: '2000',
      startedAt: '2000',
      creator: 'rick',
      name: 'StartedFlow1',
      state: ApiFlowState.RUNNING,
    });

    clientPageGlobalStore.startFlowConfiguration('StartedFlow2');
    clientPageGlobalStore.startFlow({});

    apiStartFlow$.next({
      flowId: '2',
      clientId: 'C.1234',
      lastActiveAt: '2000',
      startedAt: '2000',
      creator: 'rick',
      name: 'StartedFlow2',
      state: ApiFlowState.RUNNING,
    });

    clientPageGlobalStore.flowListEntries$.subscribe(flows => {
      expect(flows.map(flow => flow.name)).toEqual([
        'StartedFlow1', 'StartedFlow2'
      ]);
      done();
    });
  });

  it('calls the API on scheduleFlow', () => {
    clientPageGlobalStore.startFlowConfiguration('ListProcesses');
    clientPageGlobalStore.scheduleFlow({foo: 1});
    expect(httpApiService.scheduleFlow)
        .toHaveBeenCalledWith('C.1234', 'ListProcesses', {foo: 1});
  });

  it('emits the error in startFlowState', (done) => {
    clientPageGlobalStore.startFlowConfiguration('ListProcesses');
    clientPageGlobalStore.startFlow({});
    apiStartFlow$.error(new Error('foobazzle rapidly disintegrated'));

    clientPageGlobalStore.startFlowState$.subscribe(state => {
      expect(state).toEqual(
          {state: 'error', error: 'foobazzle rapidly disintegrated'});
      done();
    });
  });

  it('stops flow configuration after successful started flow', (done) => {
    clientPageGlobalStore.startFlowConfiguration('ListProcesses');
    clientPageGlobalStore.startFlow({});

    apiStartFlow$.next({
      flowId: '1',
      clientId: 'C.1234',
      lastActiveAt: '999000',
      startedAt: '123000',
      creator: 'rick',
      name: 'ListProcesses',
      state: ApiFlowState.RUNNING,
    });

    clientPageGlobalStore.selectedFlowDescriptor$.subscribe(fd => {
      expect(fd).toBeUndefined();
      done();
    });
  });

  it('stops flow configuration after successfully scheduling a flow',
     (done) => {
       clientPageGlobalStore.startFlowConfiguration('ListProcesses');
       clientPageGlobalStore.scheduleFlow({});

       apiScheduleFlow$.next({
         scheduledFlowId: '1',
         clientId: 'C.1234',
         creator: 'testuser',
         createTime: '999000',
         flowName: 'ListProcesses',
         flowArgs: {foobar: 9000},
       });

       clientPageGlobalStore.selectedFlowDescriptor$.subscribe(fd => {
         expect(fd).toBeUndefined();
         done();
       });
     });

  it('calls the API on cancelFlow', () => {
    clientPageGlobalStore.cancelFlow('5678');
    expect(httpApiService.cancelFlow).toHaveBeenCalledWith('C.1234', '5678');
  });

  it('emits the cancelled flow in flowListEntries$', (done) => {
    clientPageGlobalStore.cancelFlow('5678');

    apiCancelFlow$.next({
      flowId: '5678',
      clientId: 'C.1234',
      lastActiveAt: '999000',
      startedAt: '123000',
      creator: 'rick',
      name: 'ListProcesses',
      state: ApiFlowState.TERMINATED,
    });

    const expected: Flow[] = [
      newFlow({
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

    clientPageGlobalStore.flowListEntries$.subscribe(flows => {
      expect(flows).toEqual(expected);
      done();
    });
  });


  it('emits undefined as selectedFlowDescriptor$ initially', done => {
    clientPageGlobalStore.selectedFlowDescriptor$.subscribe(flow => {
      expect(flow).toBeUndefined();
      done();
    });
  });

  it('emits the selected flow in selectedFlowDescriptor$', done => {
    configGlobalStore.flowDescriptorsSubject.next(newFlowDescriptorMap(
        {name: 'ClientSideFileFinder'},
        {name: 'KeepAlive', defaultArgs: {foo: 1}},
        ));
    clientPageGlobalStore.startFlowConfiguration('KeepAlive');
    clientPageGlobalStore.selectedFlowDescriptor$.subscribe(flow => {
      // First value is expected to be undefined.
      if (!flow) {
        return;
      }

      expect(flow.name).toEqual('KeepAlive');
      expect(flow.defaultArgs).toEqual({foo: 1});
      done();
    });
  });

  it('emits the supplied args in selectedFlowDescriptor$', done => {
    configGlobalStore.flowDescriptorsSubject.next(
        newFlowDescriptorMap({name: 'KeepAlive', defaultArgs: {foo: 1}}));
    clientPageGlobalStore.startFlowConfiguration('KeepAlive', {foo: 42});
    clientPageGlobalStore.selectedFlowDescriptor$.subscribe(flow => {
      // First value is expected to be undefined.
      if (!flow) {
        return;
      }

      expect(flow.name).toEqual('KeepAlive');
      expect(flow.defaultArgs).toEqual({foo: 42});
      done();
    });
  });

  it('fails when selecting unknown flow', done => {
    configGlobalStore.flowDescriptorsSubject.next(newFlowDescriptorMap(
        {name: 'KeepAlive'},
        ));

    clientPageGlobalStore.startFlowConfiguration('unknown');
    clientPageGlobalStore.selectedFlowDescriptor$.subscribe(
        () => {},
        err => {
          expect(err).toBeTruthy();
          done();
        },
    );
  });

  it('emits undefined in selectedFlowDescriptor$ after unselectFlow()',
     done => {
       configGlobalStore.flowDescriptorsSubject.next(newFlowDescriptorMap(
           {name: 'ClientSideFileFinder'},
           {name: 'KeepAlive'},
           ));

       clientPageGlobalStore.startFlowConfiguration('KeepAlive');
       clientPageGlobalStore.stopFlowConfiguration();
       clientPageGlobalStore.selectedFlowDescriptor$.subscribe(flow => {
         expect(flow).toBeUndefined();
         done();
       });
     });

  it('fetches client data only after selectedClient$ is subscribed to',
     fakeAsync(() => {
       expect(httpApiService.fetchClient).not.toHaveBeenCalled();
       clientPageGlobalStore.selectedClient$.subscribe();

       // This is needed since selected client is updated in a timer loop
       // and the first call is scheduled after 0 milliseconds (meaning it
       // will happen right after it was scheduled, but still asynchronously).
       tick(1);
       discardPeriodicTasks();
       expect(httpApiService.fetchClient).toHaveBeenCalledWith('C.1234');
     }));

  it('polls and updates selectedClient$ periodically', fakeAsync(() => {
       clientPageGlobalStore.selectedClient$.subscribe();

       tick(configService.config.selectedClientPollingIntervalMs * 2 + 1);
       discardPeriodicTasks();

       // First call happens at 0, next one at selectedClientPollingIntervalMs
       // and the next one at selectedClientPollingIntervalMs * 2.
       expect(httpApiService.fetchClient).toHaveBeenCalledTimes(3);
     }));

  it('polls and updates selectedClient$ when another client is selected',
     fakeAsync(() => {
       clientPageGlobalStore.selectedClient$.subscribe();

       // This is needed since selected client is updated in a timer loop
       // and the first call is scheduled after 0 milliseconds (meaning it
       // will happen right after it was scheduled, but still asynchronously).
       tick(1);
       expect(httpApiService.fetchClient).toHaveBeenCalledWith('C.1234');

       clientPageGlobalStore.selectClient('C.5678');
       tick(1);
       discardPeriodicTasks();

       expect(httpApiService.fetchClient).toHaveBeenCalledWith('C.5678');
     }));

  it('stops updating selectedClient$ when unsubscribed from it',
     fakeAsync(() => {
       const subscribtion = clientPageGlobalStore.selectedClient$.subscribe();

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

  it('shares polling between subscriptions to selectedClient$',
     fakeAsync(() => {
       const subscribtion = clientPageGlobalStore.selectedClient$.subscribe();
       const subscribtion2 = clientPageGlobalStore.selectedClient$.subscribe();

       // This is needed since selected client is updated in a timer loop
       // and the first call is scheduled after 0 milliseconds (meaning it
       // will happen right after it was scheduled, but still asynchronously).
       tick(1);
       expect(httpApiService.fetchClient).toHaveBeenCalledTimes(1);
       subscribtion.unsubscribe();
       subscribtion2.unsubscribe();
       // Fast forward for another 2 polling intervals, to check if
       // the client is still fetched or not after unsubscribe.
       // The number of calls to fetchClient() should stay the same
       tick(configService.config.selectedClientPollingIntervalMs * 2 + 1);
       discardPeriodicTasks();

       expect(httpApiService.fetchClient).toHaveBeenCalledTimes(1);
     }));

  it('does not poll prior to subscription to selectedClient$', fakeAsync(() => {
       tick(configService.config.selectedClientPollingIntervalMs * 2 + 1);
       discardPeriodicTasks();
       expect(httpApiService.fetchClient).toHaveBeenCalledTimes(0);
     }));

  it('updates selectedClient$ with changed client data when underlying API client data changes.',
     fakeAsync((done: DoneFn) => {
       const expectedClients: Client[] = [
         newClient({
           clientId: 'C.1234',
           fleetspeakEnabled: false,
         }),
         newClient({
           clientId: 'C.5678',
           fleetspeakEnabled: true,
         }),
       ];

       apiFetchClient$.next({
         clientId: 'C.5678',
         fleetspeakEnabled: true,
       });

       let i = 0;
       clientPageGlobalStore.selectedClient$.subscribe(client => {
         expect(client).toEqual(expectedClients[i]);
         i++;
         if (i === expectedClients.length) {
           done();
         }
       });

       tick(
           configService.config.selectedClientPollingIntervalMs *
               (expectedClients.length - 1) +
           1);
       discardPeriodicTasks();
     }));

  it('calls API to remove a client label', () => {
    expect(httpApiService.removeClientLabel).toHaveBeenCalledTimes(0);
    clientPageGlobalStore.removeClientLabel('label1');
    expect(httpApiService.removeClientLabel).toHaveBeenCalledTimes(1);
  });

  it('refreshes client after calling API for removing label', () => {
    expect(httpApiService.fetchClient).toHaveBeenCalledTimes(0);
    clientPageGlobalStore.removeClientLabel('label1');
    apiRemoveClientLabel$.next('label1');
    expect(httpApiService.fetchClient).toHaveBeenCalledTimes(1);
  });

  it('emits which labels were removed successfully', (done) => {
    const expectedLabels = ['testlabel', 'testlabel2'];
    let i = 0;
    clientPageGlobalStore.lastRemovedClientLabel$.subscribe(label => {
      expect(label).toEqual(expectedLabels[i]);
      i++;
      if (i === expectedLabels.length) {
        done();
      }
    });

    clientPageGlobalStore.removeClientLabel('testlabel');
    apiRemoveClientLabel$.next('testlabel');

    clientPageGlobalStore.removeClientLabel('testlabel2');
    apiRemoveClientLabel$.next('testlabel2');
  });

  it('calls the API when suggestApprovers is called', () => {
    clientPageGlobalStore.suggestApprovers('ba');
    expect(httpApiService.suggestApprovers).toHaveBeenCalledWith('ba');
  });

  it('emits approver autocomplete in approverSuggestions$', (done) => {
    clientPageGlobalStore.suggestApprovers('ba');

    clientPageGlobalStore.approverSuggestions$.subscribe(
        approverSuggestions => {
          expect(approverSuggestions).toEqual(['bar', 'baz']);
          done();
        });

    apiSuggestApprovers$.next([{username: 'bar'}, {username: 'baz'}]);
  });
});
