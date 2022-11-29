import {fakeAsync, TestBed} from '@angular/core/testing';
import {firstValueFrom} from 'rxjs';
import {filter} from 'rxjs/operators';

import {ApiFlowState} from '../lib/api/api_interfaces';
import {HttpApiService} from '../lib/api/http_api_service';
import {HttpApiServiceMock, mockHttpApiService} from '../lib/api/http_api_service_test_util';
import {Flow, FlowState} from '../lib/models/flow';
import {newFlow} from '../lib/models/model_test_util';
import {isNonNull} from '../lib/preconditions';
import {initTestEnvironment} from '../testing';

import {RecentClientFlowsLocalStore} from './recent_client_flows_local_store';

initTestEnvironment();

describe('RecentClientFlowsLocalStore', () => {
  let httpApiService: HttpApiServiceMock;
  let recentClientFlowsLocalStore: RecentClientFlowsLocalStore;

  beforeEach(() => {
    httpApiService = mockHttpApiService();
    TestBed
        .configureTestingModule({
          imports: [],
          providers: [
            RecentClientFlowsLocalStore,
            {provide: HttpApiService, useFactory: () => httpApiService},
          ],
          teardown: {destroyAfterEach: false}
        })
        .compileComponents();

    recentClientFlowsLocalStore = TestBed.inject(RecentClientFlowsLocalStore);
    recentClientFlowsLocalStore.selectClient('C.1234');
  });

  it('fetches flows from the API if the client access is valid',
     fakeAsync(() => {
       recentClientFlowsLocalStore.flowListEntries$.subscribe();

       httpApiService.mockedObservables.subscribeToVerifyClientAccess.next(
           true);

       expect(httpApiService.subscribeToFlowsForClient).toHaveBeenCalledWith({
         clientId: 'C.1234',
         count: '3',
         topFlowsOnly: true,
         humanFlowsOnly: true,
       });
     }));

  it('no flows fetched from the API if the client access is invalid',
     fakeAsync(async () => {
       recentClientFlowsLocalStore.flowListEntries$.subscribe();

       httpApiService.mockedObservables.subscribeToVerifyClientAccess.next(
           false);

       expect(httpApiService.subscribeToFlowsForClient).not.toHaveBeenCalled();
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

       // Skip the first emitted entry, which is {flows: []}.
       const promise =
           firstValueFrom(recentClientFlowsLocalStore.flowListEntries$.pipe(
               filter(data => isNonNull(data.flows) && data.flows.length > 0)));

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
});