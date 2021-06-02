import {discardPeriodicTasks, fakeAsync, TestBed, tick} from '@angular/core/testing';
import {ConfigService} from '@app/components/config/config';
import {ApiScheduledFlow} from '@app/lib/api/api_interfaces';
import {HttpApiService} from '@app/lib/api/http_api_service';
import {ScheduledFlow} from '@app/lib/models/flow';
import {initTestEnvironment} from '@app/testing';
import {of, Subject} from 'rxjs';

import {ConfigGlobalStore} from './config_global_store';
import {ConfigGlobalStoreMock, mockConfigGlobalStore} from './config_global_store_test_util';
import {ScheduledFlowGlobalStore} from './scheduled_flow_global_store';

initTestEnvironment();


describe('ScheduledFlowGlobalStore', () => {
  let httpApiService: Partial<HttpApiService>;
  let scheduledFlowGlobalStore: ScheduledFlowGlobalStore;
  let configService: ConfigService;
  let apiListScheduledFlows$: Subject<ReadonlyArray<ApiScheduledFlow>>;
  let configGlobalStore: ConfigGlobalStoreMock;

  beforeEach(() => {
    apiListScheduledFlows$ = new Subject();
    httpApiService = {
      listScheduledFlows: jasmine.createSpy('listScheduledFlows')
                              .and.returnValue(apiListScheduledFlows$),
    };

    configGlobalStore = mockConfigGlobalStore();

    TestBed
        .configureTestingModule({
          imports: [],
          providers: [
            ScheduledFlowGlobalStore,
            {provide: HttpApiService, useFactory: () => httpApiService},
            {provide: ConfigGlobalStore, useFactory: () => configGlobalStore},
          ],
        })
        .compileComponents();

    scheduledFlowGlobalStore = TestBed.inject(ScheduledFlowGlobalStore);
    configService = TestBed.inject(ConfigService);
  });

  it('calls the listScheduledFlows API on scheduledFlows$ subscription',
     fakeAsync(() => {
       scheduledFlowGlobalStore.selectSource(
           {clientId: 'C.1234', creator: 'testuser'});
       scheduledFlowGlobalStore.scheduledFlows$.subscribe();

       // This is needed since flow list entries are updated in a timer loop
       // and the first call is scheduled after 0 milliseconds (meaning it
       // will happen right after it was scheduled, but still asynchronously).
       tick(1);
       discardPeriodicTasks();

       expect(httpApiService.listScheduledFlows)
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

       apiListScheduledFlows$.next([
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
       apiListScheduledFlows$.complete();
       expect(results).toEqual(expected);
     }));

  it('polls and updates scheduledFlows$ periodically', fakeAsync(() => {
       httpApiService.listScheduledFlows =
           jasmine.createSpy('listScheduledFlows').and.callFake(() => of([]));

       scheduledFlowGlobalStore.selectSource(
           {clientId: 'C.1234', creator: 'testuser'});
       scheduledFlowGlobalStore.scheduledFlows$.subscribe();

       tick(configService.config.flowListPollingIntervalMs * 2 + 1);
       discardPeriodicTasks();

       // First call happens at 0, next one at flowListPollingIntervalMs
       // and the next one at flowListPollingIntervalMs * 2.
       expect(httpApiService.listScheduledFlows).toHaveBeenCalledTimes(3);
     }));
});
