import {discardPeriodicTasks, fakeAsync, TestBed, tick} from '@angular/core/testing';
import {firstValueFrom, Subject} from 'rxjs';

import {HttpApiService} from '../lib/api/http_api_service';
import {HttpApiServiceMock, mockHttpApiService} from '../lib/api/http_api_service_test_util';
import {initTestEnvironment} from '../testing';

import {FlowResultsLocalStore} from './flow_results_local_store';


initTestEnvironment();


describe('FlowResultsLocalStore', () => {
  let httpApiService: HttpApiServiceMock;
  let flowResultsLocalStore: FlowResultsLocalStore;

  beforeEach(() => {
    httpApiService = mockHttpApiService();

    TestBed
        .configureTestingModule({
          imports: [],
          providers: [
            FlowResultsLocalStore,
            {provide: HttpApiService, useFactory: () => httpApiService},
          ],
          teardown: {destroyAfterEach: false}
        })
        .compileComponents();

    flowResultsLocalStore = TestBed.inject(FlowResultsLocalStore);
  });

  it('calls the API on results$ subscription', fakeAsync(() => {
       flowResultsLocalStore.results$.subscribe();

       expect(httpApiService.subscribeToResultsForFlow).not.toHaveBeenCalled();

       flowResultsLocalStore.query({
         flow: {clientId: 'C', flowId: '11'},
       });

       expect(httpApiService.subscribeToResultsForFlow).not.toHaveBeenCalled();

       flowResultsLocalStore.queryMore(100);

       expect(httpApiService.subscribeToResultsForFlow).toHaveBeenCalled();

       flowResultsLocalStore.results$.subscribe();

       discardPeriodicTasks();

       expect(httpApiService.subscribeToResultsForFlow.calls.count()).toBe(1);
     }));

  it('replays latest value before new data is polled', fakeAsync(async () => {
       httpApiService.mockedObservables.subscribeToResultsForFlow =
           new Subject();

       flowResultsLocalStore.query({
         flow: {clientId: 'C', flowId: '11'},
         count: 10,
       });

       flowResultsLocalStore.results$.subscribe();

       httpApiService.mockedObservables.subscribeToResultsForFlow.next([{
         payload: {foo: 42},
         payloadType: 'foobar',
         tag: '',
         timestamp: '1',
       }]);

       // Calling unsubscribe() on the above subscription clears
       // the cached value -- ideally, FlowResultsLocalStore should cache
       // indefinitely even when no subscribers are subscribed any longer.

       expect(await firstValueFrom(flowResultsLocalStore.results$)).toEqual([
         jasmine.objectContaining({
           payload: {foo: 42},
           payloadType: 'foobar',
         })
       ]);
     }));

  it('unsubscribes from polling when last observer unsubscribes',
     fakeAsync(async () => {
       httpApiService.mockedObservables.subscribeToResultsForFlow =
           new Subject();

       flowResultsLocalStore.query({
         flow: {clientId: 'C', flowId: '11'},
         count: 10,
       });

       expect(
           httpApiService.mockedObservables.subscribeToResultsForFlow.observed)
           .toBeFalse();

       const subscription = flowResultsLocalStore.results$.subscribe();

       expect(
           httpApiService.mockedObservables.subscribeToResultsForFlow.observed)
           .toBeTrue();

       subscription.unsubscribe();

       tick();

       expect(
           httpApiService.mockedObservables.subscribeToResultsForFlow.observed)
           .toBeFalse();
     }));

  it('emits latest results in results$', fakeAsync(async () => {
       const promise = firstValueFrom(flowResultsLocalStore.results$);
       flowResultsLocalStore.query({
         flow: {clientId: 'C', flowId: '1'},
         offset: 0,
         count: 100,
       });

       httpApiService.mockedObservables.subscribeToResultsForFlow.next([{
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

       expect(httpApiService.subscribeToResultsForFlow).not.toHaveBeenCalled();

       flowResultsLocalStore.results$.subscribe();

       expect(httpApiService.subscribeToResultsForFlow)
           .toHaveBeenCalledWith(jasmine.objectContaining({
             clientId: 'C',
             flowId: '1',
             count: 10,
           }));
       discardPeriodicTasks();
     }));
});
