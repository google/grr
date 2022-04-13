import {discardPeriodicTasks, fakeAsync, TestBed, tick} from '@angular/core/testing';

import {HttpApiService} from '../lib/api/http_api_service';
import {HttpApiServiceMock, mockHttpApiService} from '../lib/api/http_api_service_test_util';
import {ScheduledFlow} from '../lib/models/flow';
import {initTestEnvironment} from '../testing';

import {ConfigGlobalStore} from './config_global_store';
import {ConfigGlobalStoreMock, mockConfigGlobalStore} from './config_global_store_test_util';
import {ScheduledFlowGlobalStore} from './scheduled_flow_global_store';

initTestEnvironment();


describe('ScheduledFlowGlobalStore', () => {
  let httpApiService: HttpApiServiceMock;
  let scheduledFlowGlobalStore: ScheduledFlowGlobalStore;
  let configGlobalStore: ConfigGlobalStoreMock;

  beforeEach(() => {
    httpApiService = mockHttpApiService();
    configGlobalStore = mockConfigGlobalStore();

    TestBed
        .configureTestingModule({
          imports: [],
          providers: [
            ScheduledFlowGlobalStore,
            {provide: HttpApiService, useFactory: () => httpApiService},
            {provide: ConfigGlobalStore, useFactory: () => configGlobalStore},
          ],
          teardown: {destroyAfterEach: false}
        })
        .compileComponents();

    scheduledFlowGlobalStore = TestBed.inject(ScheduledFlowGlobalStore);
  });

  it('calls the listScheduledFlows API on scheduledFlows$ subscription',
     fakeAsync(() => {
       scheduledFlowGlobalStore.selectSource(
           {clientId: 'C.1234', creator: 'testuser'});
       scheduledFlowGlobalStore.scheduledFlows$.subscribe();
       expect(httpApiService.subscribeToScheduledFlowsForClient)
           .toHaveBeenCalledWith('C.1234', 'testuser');
     }));

  it('emits ScheduledFlows', fakeAsync(() => {
       const expected: ScheduledFlow[] = [
         {
           scheduledFlowId: '1',
           clientId: 'C.1234',
           creator: 'testuser',
           createTime: new Date(999),
           flowName: 'ListProcesses',
           flowArgs: {foobar: 9000},
           error: undefined,
         },
         {
           scheduledFlowId: '2',
           clientId: 'C.1234',
           creator: 'testuser',
           createTime: new Date(999),
           flowName: 'GetFile',
           flowArgs: {foobar: 5},
           error: 'foobazzle invalid',
         },
       ];

       scheduledFlowGlobalStore.selectSource(
           {clientId: 'C.1234', creator: 'testuser'});

       let results: ReadonlyArray<ScheduledFlow> = [];
       scheduledFlowGlobalStore.scheduledFlows$.subscribe(scheduledFlows => {
         results = scheduledFlows;
       });
       tick(1);
       discardPeriodicTasks();

       httpApiService.mockedObservables.subscribeToScheduledFlowsForClient.next(
           [
             {
               scheduledFlowId: '1',
               clientId: 'C.1234',
               creator: 'testuser',
               createTime: '999000',
               flowName: 'ListProcesses',
               flowArgs: {foobar: 9000},
             },
             {
               scheduledFlowId: '2',
               clientId: 'C.1234',
               creator: 'testuser',
               createTime: '999000',
               flowName: 'GetFile',
               flowArgs: {foobar: 5},
               error: 'foobazzle invalid',
             },
           ]);
       expect(results).toEqual(expected);
     }));
});
