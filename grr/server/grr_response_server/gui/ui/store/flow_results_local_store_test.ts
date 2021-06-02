import {discardPeriodicTasks, fakeAsync, TestBed, tick} from '@angular/core/testing';
import {ConfigService} from '@app/components/config/config';
import {HttpApiService} from '@app/lib/api/http_api_service';
import {FlowResultsLocalStore} from '@app/store/flow_results_local_store';
import {initTestEnvironment} from '@app/testing';
import {firstValueFrom, Subject} from 'rxjs';

import {ApiFlowResult} from '../lib/api/api_interfaces';

import {ConfigGlobalStore} from './config_global_store';
import {ConfigGlobalStoreMock, mockConfigGlobalStore} from './config_global_store_test_util';


initTestEnvironment();


describe('FlowResultsLocalStore', () => {
  let httpApiService: Partial<HttpApiService>;
  let flowResultsLocalStore: FlowResultsLocalStore;
  let configService: ConfigService;

  let configGlobalStore: ConfigGlobalStoreMock;

  let apiListResultsForFlow$: Subject<ReadonlyArray<ApiFlowResult>>;

  beforeEach(() => {
    apiListResultsForFlow$ = new Subject();
    httpApiService = {
      listResultsForFlow: jasmine.createSpy('listResultsForFlow')
                              .and.returnValue(apiListResultsForFlow$),
    };

    configGlobalStore = mockConfigGlobalStore();

    TestBed
        .configureTestingModule({
          imports: [],
          providers: [
            FlowResultsLocalStore,
            {provide: HttpApiService, useFactory: () => httpApiService},
            {provide: ConfigGlobalStore, useFactory: () => configGlobalStore},
          ],
        })
        .compileComponents();

    flowResultsLocalStore = TestBed.inject(FlowResultsLocalStore);
    configService = TestBed.inject(ConfigService);
  });

  it('polls the API on results$ subscription', fakeAsync(() => {
       flowResultsLocalStore.query({
         flow: {clientId: 'C', flowId: '1'},
         offset: 0,
         count: 100,
       });

       tick(configService.config.flowResultsPollingIntervalMs * 2 + 1);
       expect(httpApiService.listResultsForFlow).not.toHaveBeenCalled();

       flowResultsLocalStore.results$.subscribe();

       tick(configService.config.flowResultsPollingIntervalMs * 2 + 1);
       discardPeriodicTasks();

       // 3 queries from polling, one from the query changed. This could be
       // optimized to re-start polling with an initial delay after the query
       // changes.
       expect(httpApiService.listResultsForFlow).toHaveBeenCalledTimes(4);
     }));

  it('emits latest results in results$', fakeAsync(async () => {
       const promise = firstValueFrom(flowResultsLocalStore.results$);
       flowResultsLocalStore.query({
         flow: {clientId: 'C', flowId: '1'},
         offset: 0,
         count: 100,
       });

       tick(configService.config.flowResultsPollingIntervalMs + 1);
       apiListResultsForFlow$.next([{
         payload: {foo: 42},
         payloadType: 'foobar',
         tag: '',
         timestamp: '1',
       }]);
       expect(await promise).toEqual([jasmine.objectContaining({
         payload: {foo: 42},
         payloadType: 'foobar',
       })]);
     }));

  it('merges queries with missing count', fakeAsync(() => {
       flowResultsLocalStore.query(
           {flow: {clientId: 'C', flowId: '1'}, withTag: 'foo'});
       flowResultsLocalStore.queryMore(10);
       flowResultsLocalStore.query(
           {flow: {clientId: 'C', flowId: '1'}, withTag: 'foo'});

       expect(httpApiService.listResultsForFlow).not.toHaveBeenCalled();

       flowResultsLocalStore.results$.subscribe();

       tick(configService.config.flowResultsPollingIntervalMs * 2 + 1);
       discardPeriodicTasks();

       expect(httpApiService.listResultsForFlow)
           .toHaveBeenCalledWith(jasmine.objectContaining({
             clientId: 'C',
             flowId: '1',
             count: 10,
           }));
     }));
});
