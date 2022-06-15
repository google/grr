import {fakeAsync, TestBed} from '@angular/core/testing';
import {firstValueFrom} from 'rxjs';
import {filter} from 'rxjs/operators';

import {HttpApiService} from '../lib/api/http_api_service';
import {HttpApiServiceMock, mockHttpApiService} from '../lib/api/http_api_service_test_util';
import {isNonNull} from '../lib/preconditions';
import {initTestEnvironment} from '../testing';

import {HuntPageLocalStore, RESULTS_BATCH_SIZE} from './hunt_page_local_store';

initTestEnvironment();


describe('HuntPageLocalStore', () => {
  let httpApiService: HttpApiServiceMock;
  let huntPageLocalStore: HuntPageLocalStore;

  beforeEach(() => {
    httpApiService = mockHttpApiService();
    TestBed
        .configureTestingModule({
          imports: [],
          providers: [
            HuntPageLocalStore,
            {provide: HttpApiService, useFactory: () => httpApiService},
          ],
          teardown: {destroyAfterEach: false}
        })
        .compileComponents();

    huntPageLocalStore = TestBed.inject(HuntPageLocalStore);
  });

  it('fetches hunt from api', fakeAsync(() => {
       const sub = huntPageLocalStore.selectedHunt$.subscribe();
       httpApiService.mockedObservables.subscribeToHunt.next({
         huntId: '1984',
         description: 'Ghost',
         creator: 'buster',
       });

       huntPageLocalStore.selectHunt('1984');
       expect(httpApiService.subscribeToHunt).toHaveBeenCalledWith('1984');
       sub.unsubscribe();
     }));

  it('emits updated data', fakeAsync(async () => {
       const promise = firstValueFrom(
           huntPageLocalStore.selectedHunt$.pipe(filter(isNonNull)));

       huntPageLocalStore.selectHunt('1984');
       expect(await firstValueFrom(huntPageLocalStore.selectedHuntId$))
           .toEqual('1984');
       expect(httpApiService.subscribeToHunt).toHaveBeenCalledWith('1984');

       httpApiService.mockedObservables.subscribeToHunt.next({
         huntId: '1984',
         description: 'Ghost',
         creator: 'buster',
       });
       expect(await promise).toEqual(jasmine.objectContaining({
         huntId: '1984',
         description: 'Ghost',
         creator: 'buster',
       }));
     }));

  it('loadMoreResults fetches hunt results from api', fakeAsync(() => {
       const sub = huntPageLocalStore.huntResults$.subscribe();
       huntPageLocalStore.selectHunt('456');
       httpApiService.subscribeToResultsForHunt.calls.reset();
       httpApiService.mockedObservables.subscribeToResultsForHunt.next([
         {'clientId': 'C.1234', 'payloadType': 'foo'},
         {'clientId': 'C.5678', 'payloadType': 'bar'}
       ]);

       huntPageLocalStore.loadMoreResults();
       expect(httpApiService.subscribeToResultsForHunt)
           .toHaveBeenCalledWith({huntId: '456', count: RESULTS_BATCH_SIZE});
       sub.unsubscribe();
     }));

  it('loadMoreResults emits huntResults$ with fetched data', (async () => {
       // Skip the first emitted entry, which is {isLoading: true, results:
       // undefined}.
       const promise = firstValueFrom(huntPageLocalStore.huntResults$.pipe(
           filter(data => isNonNull(data.results))));

       huntPageLocalStore.selectHunt('456');
       httpApiService.subscribeToResultsForHunt.calls.reset();
       httpApiService.mockedObservables.subscribeToResultsForHunt.next([
         {'clientId': 'C.1234', 'payloadType': 'foo'},
         {'clientId': 'C.5678', 'payloadType': 'bar'}
       ]);
       huntPageLocalStore.loadMoreResults();

       expect(await promise).toEqual(jasmine.objectContaining({
         results: [
           {'clientId': 'C.1234', 'payloadType': 'foo'},
           {'clientId': 'C.5678', 'payloadType': 'bar'}
         ]
       }));
     }));

  it('emits isLoading: true in flowListEntries$ while loading entries',
     fakeAsync(async () => {
       huntPageLocalStore.huntResults$.subscribe();
       huntPageLocalStore.loadMoreResults();

       expect(await firstValueFrom(huntPageLocalStore.huntResults$))
           .toEqual(jasmine.objectContaining({isLoading: true}));

       httpApiService.mockedObservables.subscribeToResultsForHunt.next([]);

       expect(await firstValueFrom(huntPageLocalStore.huntResults$))
           .toEqual(jasmine.objectContaining({isLoading: false}));
     }));
});
