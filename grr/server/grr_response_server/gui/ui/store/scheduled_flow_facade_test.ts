import {discardPeriodicTasks, fakeAsync, TestBed, tick} from '@angular/core/testing';
import {ConfigService} from '@app/components/config/config';
import {ApiScheduledFlow} from '@app/lib/api/api_interfaces';
import {HttpApiService} from '@app/lib/api/http_api_service';
import {ScheduledFlow} from '@app/lib/models/flow';
import {initTestEnvironment} from '@app/testing';
import {of, Subject} from 'rxjs';

import {ConfigFacade} from './config_facade';
import {ConfigFacadeMock, mockConfigFacade} from './config_facade_test_util';
import {ScheduledFlowFacade} from './scheduled_flow_facade';

initTestEnvironment();


describe('ScheduledFlowFacade', () => {
  let httpApiService: Partial<HttpApiService>;
  let scheduledFlowFacade: ScheduledFlowFacade;
  let configService: ConfigService;
  let apiListScheduledFlows$: Subject<ReadonlyArray<ApiScheduledFlow>>;
  let configFacade: ConfigFacadeMock;

  beforeEach(() => {
    apiListScheduledFlows$ = new Subject();
    httpApiService = {
      listScheduledFlows: jasmine.createSpy('listScheduledFlows')
                              .and.returnValue(apiListScheduledFlows$),
    };

    configFacade = mockConfigFacade();

    TestBed
        .configureTestingModule({
          imports: [],
          providers: [
            ScheduledFlowFacade,
            {provide: HttpApiService, useFactory: () => httpApiService},
            {provide: ConfigFacade, useFactory: () => configFacade},
          ],
        })
        .compileComponents();

    scheduledFlowFacade = TestBed.inject(ScheduledFlowFacade);
    configService = TestBed.inject(ConfigService);
  });

  it('calls the listScheduledFlows API on scheduledFlows$ subscription',
     fakeAsync(() => {
       scheduledFlowFacade.selectSource(
           {clientId: 'C.1234', creator: 'testuser'});
       scheduledFlowFacade.scheduledFlows$.subscribe();

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

       scheduledFlowFacade.selectSource(
           {clientId: 'C.1234', creator: 'testuser'});

       let results: ReadonlyArray<ScheduledFlow> = [];
       scheduledFlowFacade.scheduledFlows$.subscribe(scheduledFlows => {
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

       scheduledFlowFacade.selectSource(
           {clientId: 'C.1234', creator: 'testuser'});
       scheduledFlowFacade.scheduledFlows$.subscribe();

       tick(configService.config.flowListPollingIntervalMs * 2 + 1);
       discardPeriodicTasks();

       // First call happens at 0, next one at flowListPollingIntervalMs
       // and the next one at flowListPollingIntervalMs * 2.
       expect(httpApiService.listScheduledFlows).toHaveBeenCalledTimes(3);
     }));
});
