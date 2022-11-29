import {fakeAsync, TestBed} from '@angular/core/testing';
import {BehaviorSubject, firstValueFrom, of} from 'rxjs';
import {filter} from 'rxjs/operators';

import {ApiHuntResult, ApiHuntState} from '../lib/api/api_interfaces';
import {HttpApiService} from '../lib/api/http_api_service';
import {HttpApiServiceMock, mockHttpApiService} from '../lib/api/http_api_service_test_util';
import {HuntState} from '../lib/models/hunt';
import {isNonNull} from '../lib/preconditions';
import {initTestEnvironment} from '../testing';

import {HuntPageGlobalStore, RESULTS_BATCH_SIZE} from './hunt_page_global_store';

initTestEnvironment();


describe('HuntPageGlobalStore', () => {
  let httpApiService: HttpApiServiceMock;
  let huntPageGlobalStore: HuntPageGlobalStore;

  beforeEach(() => {
    httpApiService = mockHttpApiService();
    TestBed
        .configureTestingModule({
          imports: [],
          providers: [
            HuntPageGlobalStore,
            {provide: HttpApiService, useFactory: () => httpApiService},
          ],
          teardown: {destroyAfterEach: false}
        })
        .compileComponents();

    huntPageGlobalStore = TestBed.inject(HuntPageGlobalStore);
  });

  it('fetches hunt from api', fakeAsync(() => {
       const sub = huntPageGlobalStore.selectedHunt$.subscribe();
       httpApiService.mockedObservables.subscribeToHunt.next({
         huntId: '1984',
         description: 'Ghost',
         creator: 'buster',
       });

       huntPageGlobalStore.selectHunt('1984');
       expect(httpApiService.subscribeToHunt).toHaveBeenCalledWith('1984');
       sub.unsubscribe();
     }));

  it('emits updated data', fakeAsync(async () => {
       const promise = firstValueFrom(
           huntPageGlobalStore.selectedHunt$.pipe(filter(isNonNull)));

       huntPageGlobalStore.selectHunt('1984');
       expect(await firstValueFrom(huntPageGlobalStore.selectedHuntId$))
           .toEqual('1984');
       expect(httpApiService.subscribeToHunt).toHaveBeenCalledWith('1984');

       httpApiService.mockedObservables.subscribeToHunt.next({
         huntId: '1984',
         description: 'Ghost',
         creator: 'buster',
         name: 'Name',
         created: '123456789',
         state: ApiHuntState.STARTED,
         huntRunnerArgs: {clientRate: 0},
       });
       expect(await promise).toEqual(jasmine.objectContaining({
         huntId: '1984',
         description: 'Ghost',
         creator: 'buster',
       }));
     }));

  it('loadMoreResults fetches hunt results from api', fakeAsync(() => {
       const sub = huntPageGlobalStore.huntResults$.subscribe();
       huntPageGlobalStore.selectHunt('456');
       httpApiService.subscribeToResultsForHunt.calls.reset();
       httpApiService.mockedObservables.subscribeToResultsForHunt.next([
         {'clientId': 'C.1234', 'payloadType': 'foo'},
         {'clientId': 'C.5678', 'payloadType': 'bar'}
       ]);

       huntPageGlobalStore.loadMoreResults();
       expect(httpApiService.subscribeToResultsForHunt).toHaveBeenCalledWith({
         huntId: '456',
         count: RESULTS_BATCH_SIZE.toString()
       });

       sub.unsubscribe();
     }));

  it('loadMoreResults emits huntResults$ with fetched data', (async () => {
       // Skip the first emitted entry, which is {isLoading: true, results:
       // undefined}.
       const promise = firstValueFrom(huntPageGlobalStore.huntResults$.pipe(
           filter(data => isNonNull(data.results))));

       huntPageGlobalStore.selectHunt('456');
       httpApiService.subscribeToResultsForHunt.calls.reset();
       httpApiService.mockedObservables.subscribeToResultsForHunt.next([
         {'clientId': 'C.1234', 'payloadType': 'foo'},
         {'clientId': 'C.5678', 'payloadType': 'bar'}
       ]);
       huntPageGlobalStore.loadMoreResults();

       expect(await promise).toEqual(jasmine.objectContaining({
         results: {
           'C.1234-456-': {'clientId': 'C.1234', 'payloadType': 'foo'},
           'C.5678-456-': {'clientId': 'C.5678', 'payloadType': 'bar'}
         }
       }));
     }));

  it('emits isLoading: true in flowListEntries$ while loading entries',
     fakeAsync(async () => {
       huntPageGlobalStore.huntResults$.subscribe();
       huntPageGlobalStore.loadMoreResults();

       expect(await firstValueFrom(huntPageGlobalStore.huntResults$))
           .toEqual(jasmine.objectContaining({isLoading: true}));

       httpApiService.mockedObservables.subscribeToResultsForHunt.next([]);

       expect(await firstValueFrom(huntPageGlobalStore.huntResults$))
           .toEqual(jasmine.objectContaining({isLoading: false}));
     }));

  it('returns hunt result when key is selected', fakeAsync(async () => {
       // Skip the first emitted entry, which is undefined.
       const promise = firstValueFrom(
           huntPageGlobalStore.selectedHuntResult$.pipe(filter(isNonNull)));

       huntPageGlobalStore.selectHunt('XXX');
       huntPageGlobalStore.selectResult('C.1234-XXX-');

       httpApiService.mockedObservables.subscribeToResultsForHunt.next([
         {'clientId': 'C.1234', 'payloadType': 'foo'},
         {'clientId': 'C.5678', 'payloadType': 'bar'}
       ]);
       huntPageGlobalStore.loadMoreResults();

       expect(await promise)
           .toEqual({'clientId': 'C.1234', 'payloadType': 'foo'});
     }));

  it('loads more results when selected result is on a different page',
     fakeAsync(async () => {
       const onePage = RESULTS_BATCH_SIZE;
       const twoPages = RESULTS_BATCH_SIZE * 2;

       const subscribeToResultsForHunt:
           HttpApiService['subscribeToResultsForHunt'] = (params) => {
             switch (params.count) {
               case onePage.toString():
                 return of([...Array.from({length: onePage}).keys()].map(
                     () => ({'clientId': 'C.1234', 'payloadType': 'foo'})));
               case twoPages.toString():
                 return of([...Array.from({length: twoPages}).keys()].map(
                     () => ({'clientId': 'C.5678', 'payloadType': 'bar'})));
               default:
                 return of([]);
             }
           };
       httpApiService.subscribeToResultsForHunt =
           jasmine.createSpy('subscribeToResultsForHunt')
               .and.callFake(subscribeToResultsForHunt);

       // Skip the first emitted entry, which is undefined.
       const promise = firstValueFrom(
           huntPageGlobalStore.selectedHuntResult$.pipe(filter(isNonNull)));

       huntPageGlobalStore.selectHunt('XXX');
       huntPageGlobalStore.selectResult('C.5678-XXX-');

       expect(await promise)
           .toEqual({'clientId': 'C.5678', 'payloadType': 'bar'});

       const totalCalls =
           httpApiService.subscribeToResultsForHunt.calls.count();
       expect(totalCalls).toBeGreaterThanOrEqual(2);

       const nextToLastCallArgs =
           httpApiService.subscribeToResultsForHunt.calls.argsFor(
               totalCalls - 2);
       expect(nextToLastCallArgs).toEqual([
         {huntId: 'XXX', count: onePage.toString()}
       ]);

       const lastCallArgs =
           httpApiService.subscribeToResultsForHunt.calls.argsFor(
               totalCalls - 1);
       expect(lastCallArgs).toEqual([
         {huntId: 'XXX', count: twoPages.toString()}
       ]);
     }));

  it('throws error if result not found', fakeAsync(async () => {
       // Always emit the same single result.
       httpApiService.mockedObservables.subscribeToResultsForHunt =
           new BehaviorSubject(
               [{'clientId': 'C.5678', 'payloadType': 'bar'}] as
               readonly ApiHuntResult[]);

       // Skip the first emitted entry, which is undefined.
       const promise = firstValueFrom(
           huntPageGlobalStore.selectedHuntResult$.pipe(filter(isNonNull)));

       huntPageGlobalStore.selectHunt('XXX');
       huntPageGlobalStore.selectResult('C.1234-XXX-');

       await expectAsync(promise).toBeRejectedWithError(
           'Result not found: C.1234-XXX-');
     }));

  it('stopHunt calls http api service', fakeAsync(() => {
       huntPageGlobalStore.selectHunt('456');
       huntPageGlobalStore.stopHunt();
       expect(httpApiService.patchHunt)
           .toHaveBeenCalledWith(
               '456',
               {state: HuntState.STOPPED},
           );
     }));
});
