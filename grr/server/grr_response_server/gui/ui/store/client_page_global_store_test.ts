import {HttpErrorResponse} from '@angular/common/http';
import {discardPeriodicTasks, fakeAsync, TestBed, tick} from '@angular/core/testing';
import {BehaviorSubject, firstValueFrom} from 'rxjs';
import {filter} from 'rxjs/operators';

import {ApiFlow, ApiFlowState} from '../lib/api/api_interfaces';
import {HttpApiService} from '../lib/api/http_api_service';
import {HttpApiServiceMock, mockHttpApiService} from '../lib/api/http_api_service_test_util';
import {RequestStatusType} from '../lib/api/track_request';
import {ClientApproval} from '../lib/models/client';
import {Flow, FlowState} from '../lib/models/flow';
import {newClient, newFlow, newFlowDescriptorMap} from '../lib/models/model_test_util';
import {isNonNull} from '../lib/preconditions';
import {initTestEnvironment, removeUndefinedKeys} from '../testing';

import {ClientPageGlobalStore, FLOWS_PAGE_SIZE} from './client_page_global_store';
import {ConfigGlobalStore} from './config_global_store';
import {ConfigGlobalStoreMock, mockConfigGlobalStore} from './config_global_store_test_util';
import {UserGlobalStore} from './user_global_store';
import {mockUserGlobalStore, UserGlobalStoreMock} from './user_global_store_test_util';


initTestEnvironment();


function makeApiFlow(flow?: Partial<ApiFlow>): ApiFlow {
  return {
    flowId: '1',
    clientId: 'C.1234',
    lastActiveAt: '999000',
    startedAt: '123000',
    creator: 'rick',
    name: 'ListProcesses',
    state: ApiFlowState.RUNNING,
    isRobot: false,
    ...flow,
  };
}

describe('ClientPageGlobalStore', () => {
  let httpApiService: HttpApiServiceMock;
  let clientPageGlobalStore: ClientPageGlobalStore;
  let configGlobalStore: ConfigGlobalStoreMock;
  let userGlobalStore: UserGlobalStoreMock;

  beforeEach(() => {
    httpApiService = mockHttpApiService();
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
          teardown: {destroyAfterEach: false}
        })
        .compileComponents();

    clientPageGlobalStore = TestBed.inject(ClientPageGlobalStore);

    clientPageGlobalStore.selectClient('C.1234');
    httpApiService.mockedObservables.subscribeToClient.next({
      clientId: 'C.1234',
    });
    userGlobalStore.mockedObservables.currentUser$.next(
        {name: 'testuser', canaryMode: false, huntApprovalRequired: false});
  });

  it('queries the API on latestApproval$ subscription ', fakeAsync(() => {
       expect(httpApiService.subscribeToListApprovals).not.toHaveBeenCalled();

       const sub = clientPageGlobalStore.latestApproval$.subscribe();

       expect(httpApiService.subscribeToListApprovals).toHaveBeenCalledTimes(1);
       sub.unsubscribe();
     }));

  it('emits latest pending approval in latestApproval$', fakeAsync(async () => {
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

       const promise = firstValueFrom(
           clientPageGlobalStore.latestApproval$.pipe(filter(isNonNull)));

       httpApiService.mockedObservables.subscribeToListApprovals.next([
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

       expect(removeUndefinedKeys(await promise)).toEqual(expected);
     }));

  it('queries the API on hasAccess$ subscription', fakeAsync(() => {
       expect(httpApiService.subscribeToVerifyClientAccess)
           .not.toHaveBeenCalled();

       const sub = clientPageGlobalStore.hasAccess$.subscribe();

       expect(httpApiService.subscribeToVerifyClientAccess)
           .toHaveBeenCalledTimes(1);

       sub.unsubscribe();
     }));

  it('emits latest access value in hasAccess$', fakeAsync(async () => {
       const promise = firstValueFrom(
           clientPageGlobalStore.hasAccess$.pipe(filter(isNonNull)));
       httpApiService.mockedObservables.subscribeToVerifyClientAccess.next(
           true);
       expect(await promise).toBeTrue();
     }));

  it('approvalsEnabled$ emits true if access is false', fakeAsync(async () => {
       const promise = firstValueFrom(
           clientPageGlobalStore.approvalsEnabled$.pipe(filter(isNonNull)));
       httpApiService.mockedObservables.subscribeToVerifyClientAccess.next(
           false);
       httpApiService.mockedObservables.subscribeToListApprovals.next([]);
       expect(await promise).toBeTrue();
     }));

  it('approvalsEnabled$ emits true if access is true and approval is granted',
     fakeAsync(async () => {
       const promise = firstValueFrom(
           clientPageGlobalStore.approvalsEnabled$.pipe(filter(isNonNull)));
       httpApiService.mockedObservables.subscribeToVerifyClientAccess.next(
           false);
       httpApiService.mockedObservables.subscribeToListApprovals.next([{
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
       const promise = firstValueFrom(
           clientPageGlobalStore.approvalsEnabled$.pipe(filter(isNonNull)));
       httpApiService.mockedObservables.subscribeToVerifyClientAccess.next(
           true);
       httpApiService.mockedObservables.subscribeToListApprovals.next([]);
       expect(await promise).toBeFalse();
     }));

  it('calls the subscribeToFlowsForClient API on flowListEntries$ subscription',
     fakeAsync(() => {
       clientPageGlobalStore.flowListEntries$.subscribe();

       httpApiService.mockedObservables.subscribeToVerifyClientAccess.next(
           true);

       expect(httpApiService.subscribeToFlowsForClient).toHaveBeenCalledWith({
         clientId: 'C.1234',
         count: FLOWS_PAGE_SIZE.toString(),
         topFlowsOnly: true,
       });
     }));

  it('queries more flows after calling loadMore', fakeAsync(() => {
       clientPageGlobalStore.flowListEntries$.subscribe();

       httpApiService.mockedObservables.subscribeToVerifyClientAccess.next(
           true);

       expect(httpApiService.subscribeToFlowsForClient)
           .toHaveBeenCalledOnceWith({
             clientId: 'C.1234',
             count: FLOWS_PAGE_SIZE.toString(),
             topFlowsOnly: true,
           });
       httpApiService.subscribeToFlowsForClient.calls.reset();

       clientPageGlobalStore.loadMoreFlows();

       expect(httpApiService.subscribeToFlowsForClient)
           .toHaveBeenCalledOnceWith({
             clientId: 'C.1234',
             count: String(FLOWS_PAGE_SIZE * 2),
             topFlowsOnly: true,
           });
     }));

  it('emits isLoading: true in flowListEntries$ while loading entries',
     fakeAsync(async () => {
       expect(await firstValueFrom(clientPageGlobalStore.flowListEntries$))
           .toEqual(jasmine.objectContaining({isLoading: false}));

       clientPageGlobalStore.flowListEntries$.subscribe();

       httpApiService.mockedObservables.subscribeToVerifyClientAccess.next(
           true);

       expect(await firstValueFrom(clientPageGlobalStore.flowListEntries$))
           .toEqual(jasmine.objectContaining({isLoading: true}));

       httpApiService.mockedObservables.subscribeToFlowsForClient.next([]);

       expect(await firstValueFrom(clientPageGlobalStore.flowListEntries$))
           .toEqual(jasmine.objectContaining({isLoading: false}));
     }));

  it('emits hasMore: true in flowListEntries$ when more flows can be loaded',
     fakeAsync(async () => {
       expect((await firstValueFrom(clientPageGlobalStore.flowListEntries$))
                  .hasMore)
           .toBeUndefined();

       clientPageGlobalStore.flowListEntries$.subscribe();

       httpApiService.mockedObservables.subscribeToVerifyClientAccess.next(
           true);


       httpApiService.mockedObservables.subscribeToFlowsForClient.next(
           Array.from({length: FLOWS_PAGE_SIZE - 1}).map(() => makeApiFlow()));

       expect(await firstValueFrom(clientPageGlobalStore.flowListEntries$))
           .toEqual(jasmine.objectContaining({hasMore: false}));

       httpApiService.mockedObservables.subscribeToFlowsForClient.next(
           Array.from({length: FLOWS_PAGE_SIZE}).map(() => makeApiFlow()));

       expect(await firstValueFrom(clientPageGlobalStore.flowListEntries$))
           .toEqual(jasmine.objectContaining({hasMore: true}));
     }));

  it('emits FlowListEntries in reverse-chronological order',
     fakeAsync(async () => {
       const expected: Flow[] = [
         {
           flowId: '2',
           clientId: 'C.1234',
           lastActiveAt: new Date(999),
           startedAt: new Date(789),
           creator: 'morty',
           name: 'GetFile',
           state: FlowState.RUNNING,
           isRobot: false,
         },
         {
           flowId: '3',
           clientId: 'C.1234',
           lastActiveAt: new Date(999),
           startedAt: new Date(456),
           creator: 'morty',
           name: 'KeepAlive',
           state: FlowState.FINISHED,
           isRobot: false,
         },
         {
           flowId: '1',
           clientId: 'C.1234',
           lastActiveAt: new Date(999),
           startedAt: new Date(123),
           creator: 'rick',
           name: 'ListProcesses',
           state: FlowState.RUNNING,
           isRobot: false,
         },
       ].map(f => newFlow(f));

       // Skip the first emitted entry, which is {isLoading: true, flows:
       // undefined}.
       const promise =
           firstValueFrom(clientPageGlobalStore.flowListEntries$.pipe(
               filter(data => isNonNull(data.flows))));

       httpApiService.mockedObservables.subscribeToVerifyClientAccess.next(
           true);

       httpApiService.mockedObservables.subscribeToFlowsForClient.next([
         {
           flowId: '1',
           clientId: 'C.1234',
           lastActiveAt: '999000',
           startedAt: '123000',
           creator: 'rick',
           name: 'ListProcesses',
           state: ApiFlowState.RUNNING,
           isRobot: false,
         },
         {
           flowId: '2',
           clientId: 'C.1234',
           lastActiveAt: '999000',
           startedAt: '789000',
           creator: 'morty',
           name: 'GetFile',
           state: ApiFlowState.RUNNING,
           isRobot: false,
         },
         {
           flowId: '3',
           clientId: 'C.1234',
           lastActiveAt: '999000',
           startedAt: '456000',
           creator: 'morty',
           name: 'KeepAlive',
           state: ApiFlowState.TERMINATED,
           isRobot: false,
         },
       ]);

       expect(await promise).toEqual(jasmine.objectContaining({
         flows: expected
       }));
     }));

  it('queries flowListEntries$', fakeAsync(() => {
       clientPageGlobalStore.flowListEntries$.subscribe();

       httpApiService.mockedObservables.subscribeToVerifyClientAccess.next(
           true);
       expect(httpApiService.subscribeToFlowsForClient)
           .toHaveBeenCalledTimes(1);
     }));

  it('calls the API on startFlow', () => {
    clientPageGlobalStore.startFlowConfiguration('ListProcesses');
    clientPageGlobalStore.startFlow({foo: 1});
    expect(httpApiService.startFlow)
        .toHaveBeenCalledWith('C.1234', 'ListProcesses', {foo: 1});
  });

  it('calls the API on scheduleFlow', () => {
    clientPageGlobalStore.startFlowConfiguration('ListProcesses');
    clientPageGlobalStore.scheduleFlow({foo: 1});
    expect(httpApiService.scheduleFlow)
        .toHaveBeenCalledWith('C.1234', 'ListProcesses', {foo: 1});
    expect(httpApiService.startFlow).not.toHaveBeenCalled();
  });

  it('calls the startFlow API on scheduleOrStartFlow with access', () => {
    httpApiService.mockedObservables.subscribeToVerifyClientAccess =
        new BehaviorSubject(true);
    clientPageGlobalStore.startFlowConfiguration('ListProcesses');
    clientPageGlobalStore.scheduleOrStartFlow({foo: 1});
    expect(httpApiService.startFlow)
        .toHaveBeenCalledWith('C.1234', 'ListProcesses', {foo: 1});
    expect(httpApiService.scheduleFlow).not.toHaveBeenCalled();
  });

  it('calls the scheduleFlow API on scheduleOrStartFlow without access', () => {
    httpApiService.mockedObservables.subscribeToVerifyClientAccess =
        new BehaviorSubject(false);
    clientPageGlobalStore.startFlowConfiguration('ListProcesses');
    clientPageGlobalStore.scheduleOrStartFlow({foo: 1});
    expect(httpApiService.scheduleFlow)
        .toHaveBeenCalledWith('C.1234', 'ListProcesses', {foo: 1});
    expect(httpApiService.startFlow).not.toHaveBeenCalled();
  });

  it('emits the error in startFlowState', async () => {
    clientPageGlobalStore.startFlowConfiguration('ListProcesses');
    clientPageGlobalStore.startFlow({});
    httpApiService.mockedObservables.startFlow.error(new HttpErrorResponse(
        {error: {message: 'foobazzle rapidly disintegrated'}}));

    expect(await firstValueFrom(clientPageGlobalStore.startFlowStatus$))
        .toEqual({
          status: RequestStatusType.ERROR,
          error: 'foobazzle rapidly disintegrated'
        });
  });

  it('emits the request_sent in startFlowState after starting the flow',
     async () => {
       clientPageGlobalStore.startFlowConfiguration('ListProcesses');
       clientPageGlobalStore.startFlow({});

       expect(await firstValueFrom(clientPageGlobalStore.startFlowStatus$))
           .toEqual({status: RequestStatusType.SENT});
     });

  it('emits the request_sent in startFlowState after scheduling the flow',
     async () => {
       clientPageGlobalStore.startFlowConfiguration('ListProcesses');
       clientPageGlobalStore.scheduleFlow({});

       expect(await firstValueFrom(clientPageGlobalStore.startFlowStatus$))
           .toEqual({status: RequestStatusType.SENT});
     });

  it('stops flow configuration after successful started flow', (done) => {
    clientPageGlobalStore.startFlowConfiguration('ListProcesses');
    clientPageGlobalStore.startFlow({});

    httpApiService.mockedObservables.startFlow.next({
      flowId: '1',
      clientId: 'C.1234',
      lastActiveAt: '999000',
      startedAt: '123000',
      creator: 'rick',
      name: 'ListProcesses',
      state: ApiFlowState.RUNNING,
      isRobot: false,
    });

    clientPageGlobalStore.selectedFlowDescriptor$.subscribe(fd => {
      expect(fd).toBeNull();
      done();
    });
  });

  it('stops flow configuration after successfully scheduling a flow',
     (done) => {
       clientPageGlobalStore.startFlowConfiguration('ListProcesses');
       clientPageGlobalStore.scheduleFlow({});

       httpApiService.mockedObservables.scheduleFlow.next({
         scheduledFlowId: '1',
         clientId: 'C.1234',
         creator: 'testuser',
         createTime: '999000',
         flowName: 'ListProcesses',
         flowArgs: {foobar: 9000},
       });

       clientPageGlobalStore.selectedFlowDescriptor$.subscribe(fd => {
         expect(fd).toBeNull();
         done();
       });
     });

  it('calls the API on cancelFlow', () => {
    clientPageGlobalStore.cancelFlow('5678');
    expect(httpApiService.cancelFlow).toHaveBeenCalledWith('C.1234', '5678');
  });

  it('emits null as selectedFlowDescriptor$ initially', done => {
    clientPageGlobalStore.selectedFlowDescriptor$.subscribe(flow => {
      expect(flow).toBeNull();
      done();
    });
  });

  it('emits the selected flow in selectedFlowDescriptor$', done => {
    configGlobalStore.mockedObservables.flowDescriptors$.next(
        newFlowDescriptorMap(
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
    configGlobalStore.mockedObservables.flowDescriptors$.next(
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
    configGlobalStore.mockedObservables.flowDescriptors$.next(
        newFlowDescriptorMap(
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

  it('emits null in selectedFlowDescriptor$ after unselectFlow()', done => {
    configGlobalStore.mockedObservables.flowDescriptors$.next(
        newFlowDescriptorMap(
            {name: 'ClientSideFileFinder'},
            {name: 'KeepAlive'},
            ));

    clientPageGlobalStore.startFlowConfiguration('KeepAlive');
    clientPageGlobalStore.stopFlowConfiguration();
    clientPageGlobalStore.selectedFlowDescriptor$.subscribe(flow => {
      expect(flow).toBeNull();
      done();
    });
  });

  it('fetches client data only after selectedClient$ is subscribed to',
     fakeAsync(() => {
       expect(httpApiService.subscribeToClient).not.toHaveBeenCalled();
       clientPageGlobalStore.selectedClient$.subscribe();

       // This is needed since selected client is updated in a timer loop
       // and the first call is scheduled after 0 milliseconds (meaning it
       // will happen right after it was scheduled, but still asynchronously).
       tick(1);
       discardPeriodicTasks();
       expect(httpApiService.subscribeToClient).toHaveBeenCalledWith('C.1234');
     }));

  it('polls and updates selectedClient$ periodically', fakeAsync(() => {
       clientPageGlobalStore.selectedClient$.subscribe();
       expect(httpApiService.subscribeToClient).toHaveBeenCalledTimes(1);
     }));

  it('polls and updates selectedClient$ when another client is selected',
     fakeAsync(() => {
       clientPageGlobalStore.selectedClient$.subscribe();

       // This is needed since selected client is updated in a timer loop
       // and the first call is scheduled after 0 milliseconds (meaning it
       // will happen right after it was scheduled, but still asynchronously).

       clientPageGlobalStore.selectClient('C.5678');
       tick(1);
       discardPeriodicTasks();

       expect(httpApiService.subscribeToClient).toHaveBeenCalledWith('C.5678');
     }));

  it('stops updating selectedClient$ when unsubscribed from it',
     fakeAsync(() => {
       const subscribtion = clientPageGlobalStore.selectedClient$.subscribe();

       // This is needed since selected client is updated in a timer loop
       // and the first call is scheduled after 0 milliseconds (meaning it
       // will happen right after it was scheduled, but still asynchronously).
       tick(1);
       expect(httpApiService.subscribeToClient).toHaveBeenCalledTimes(1);
       subscribtion.unsubscribe();

       expect(httpApiService.subscribeToClient).toHaveBeenCalledTimes(1);
     }));

  it('shares polling between subscriptions to selectedClient$',
     fakeAsync(() => {
       const subscribtion = clientPageGlobalStore.selectedClient$.subscribe();
       const subscribtion2 = clientPageGlobalStore.selectedClient$.subscribe();

       // This is needed since selected client is updated in a timer loop
       // and the first call is scheduled after 0 milliseconds (meaning it
       // will happen right after it was scheduled, but still asynchronously).
       tick(1);
       expect(httpApiService.subscribeToClient).toHaveBeenCalledTimes(1);
       subscribtion.unsubscribe();
       subscribtion2.unsubscribe();

       expect(httpApiService.subscribeToClient).toHaveBeenCalledTimes(1);
     }));

  it('does not poll prior to subscription to selectedClient$', fakeAsync(() => {
       expect(httpApiService.subscribeToClient).toHaveBeenCalledTimes(0);
     }));

  it('updates selectedClient$ with changed client data when underlying API client data changes.',
     async () => {
       const sub = clientPageGlobalStore.selectedClient$.subscribe();

       httpApiService.mockedObservables.subscribeToClient.next({
         clientId: 'C.5678',
         fleetspeakEnabled: false,
         age: '1',
       });

       expect(await firstValueFrom(clientPageGlobalStore.selectedClient$.pipe(
                  filter(isNonNull))))
           .toEqual(jasmine.objectContaining({
             clientId: 'C.5678',
             fleetspeakEnabled: false,
           }));

       httpApiService.mockedObservables.subscribeToClient.next({
         clientId: 'C.5678',
         fleetspeakEnabled: true,
         age: '1',
       });

       expect(await firstValueFrom(clientPageGlobalStore.selectedClient$.pipe(
                  filter(isNonNull))))
           .toEqual(jasmine.objectContaining({
             clientId: 'C.5678',
             fleetspeakEnabled: true,
           }));

       sub.unsubscribe();
     });

  it('calls API to remove a client label', () => {
    expect(httpApiService.removeClientLabel).toHaveBeenCalledTimes(0);
    clientPageGlobalStore.removeClientLabel('label1');
    expect(httpApiService.removeClientLabel).toHaveBeenCalledTimes(1);
  });

  it('emits which labels were removed successfully', () => {
    const lastRemovedClientLabels: string[] = [];

    clientPageGlobalStore.lastRemovedClientLabel$.pipe(filter(isNonNull))
        .subscribe(label => {
          lastRemovedClientLabels.push(label);
        });

    clientPageGlobalStore.removeClientLabel('testlabel');
    httpApiService.mockedObservables.removeClientLabel.next('testlabel');

    clientPageGlobalStore.removeClientLabel('testlabel2');
    httpApiService.mockedObservables.removeClientLabel.next('testlabel2');

    expect(lastRemovedClientLabels).toEqual(['testlabel', 'testlabel2']);
  });

  it('calls the API when suggestApprovers is called', () => {
    clientPageGlobalStore.suggestApprovers('ba');
    expect(httpApiService.suggestApprovers).toHaveBeenCalledWith('ba');
  });

  it('emits approver autocomplete in approverSuggestions$', async () => {
    clientPageGlobalStore.suggestApprovers('ba');

    const promise = firstValueFrom(
        clientPageGlobalStore.approverSuggestions$.pipe(filter(isNonNull)));

    httpApiService.mockedObservables.suggestApprovers.next(
        [{username: 'bar'}, {username: 'baz'}]);

    expect(await promise).toEqual(['bar', 'baz']);
  });
});
