import {TestBed} from '@angular/core/testing';
import {Subject} from 'rxjs';

import {ApiHuntResult} from '../lib/api/api_interfaces';
import {HttpApiService} from '../lib/api/http_api_service';
import {HttpApiServiceMock, injectHttpApiServiceMock, mockHttpApiService} from '../lib/api/http_api_service_test_util';
import {HuntResultOrError} from '../lib/models/result';
import {latestValueFrom} from '../lib/reactive';
import {initTestEnvironment} from '../testing';

import {HuntResultsLocalStore} from './hunt_results_local_store';

/**
 * Generates a list of Hunt Results from a base Hunt Result object, by only
 * changes the timestamp property of each.
 *
 * @param result: Base result object to use to generate the output list.
 * @param size: The number of results to be returned.
 */
function generateResultListFromResult<T extends HuntResultOrError>(
    result: T,
    size: number,
    ): T[] {
  const timeDeltaBetweenResults = 1_000_000;

  const res: T[] = [];

  for (let i = 1; i <= size; i++) {
    res.push({
      ...result,
      timestamp: `${Number(result.timestamp) + (timeDeltaBetweenResults * i)}`,
    });
  }

  return res;
}

const mockHuntResult: ApiHuntResult = {
  'clientId': 'mockClientId',
  'payloadType': 'SomeResultType',
  'timestamp': '1669027009243432'
};

initTestEnvironment();

describe('HuntResultsLocalStore', () => {
  let huntResultsLocalStore: HuntResultsLocalStore<HuntResultOrError>;
  let httpApiService: HttpApiServiceMock;

  beforeEach(() => {
    TestBed
        .configureTestingModule({
          imports: [],
          providers: [
            HuntResultsLocalStore,
            {provide: HttpApiService, useFactory: mockHttpApiService},
          ],
          teardown: {destroyAfterEach: false}
        })
        .compileComponents();

    huntResultsLocalStore =
        TestBed.inject(HuntResultsLocalStore<HuntResultOrError>);
    httpApiService = injectHttpApiServiceMock();
  });

  describe('Fetching Hunt results', () => {
    it('fetches results of the correct type', () => {
      const sub = huntResultsLocalStore.results$.subscribe();

      httpApiService.mockedObservables.listResultsForHunt.next([]);

      huntResultsLocalStore.setArgs({
        huntId: '1984',
        withType: 'SomeResultType',
      });

      expect(httpApiService.listResultsForHunt).toHaveBeenCalledWith({
        huntId: '1984',
        withType: 'SomeResultType',
        count: '50',
        offset: '0',
      });

      sub.unsubscribe();
    });

    it('fetches more results when calling loadMore()', async () => {
      httpApiService.mockedObservables.listResultsForHunt = new Subject();
      const mockResults = generateResultListFromResult(mockHuntResult, 60);

      huntResultsLocalStore.setArgs({
        huntId: '1984',
        withType: 'SomeResultType',
      });

      const results = latestValueFrom(huntResultsLocalStore.results$);

      // Next call to HttpService will return 50 mock elements:
      httpApiService.mockedObservables.listResultsForHunt.next(
          mockResults.slice(0, 50),
      );

      expect(results.get().length).toEqual(50);

      // Next call to HttpService will return 10 mock elements:
      httpApiService.mockedObservables.listResultsForHunt.next(
          mockResults.slice(50, 60),
      );

      huntResultsLocalStore.loadMore(10);

      expect(results.get().length).toEqual(60);
    });

    it('resets the results when the Hunt Result type changes', async () => {
      httpApiService.mockedObservables.listResultsForHunt = new Subject();

      huntResultsLocalStore.setArgs({
        huntId: '1984',
        withType: 'SomeResultType',
      });

      const results = latestValueFrom(huntResultsLocalStore.results$);

      // Next call to HttpService will return 50 mock elements:
      httpApiService.mockedObservables.listResultsForHunt.next(
          generateResultListFromResult(mockHuntResult, 50),
      );

      expect(results.get().length).toEqual(50);

      huntResultsLocalStore.setArgs({
        huntId: '1984',
        withType: 'SomeOtherType',
      });

      // Resets the result list to 0
      expect(results.get().length).toEqual(0);
    });

    it('resets the results when the Hunt ID changes', async () => {
      httpApiService.mockedObservables.listResultsForHunt = new Subject();

      huntResultsLocalStore.setArgs({
        huntId: '1984',
        withType: 'SomeResultType',
      });

      const results = latestValueFrom(huntResultsLocalStore.results$);

      // Next call to HttpService will return 50 mock elements:
      httpApiService.mockedObservables.listResultsForHunt.next(
          generateResultListFromResult(mockHuntResult, 50),
      );

      expect(results.get().length).toEqual(50);

      huntResultsLocalStore.setArgs({
        huntId: '1234567890',
        withType: 'SomeResultType',
      });

      // Resets the result list to 0
      expect(results.get().length).toEqual(0);
    });

    it('After changing arguments, it is possible to load more results',
       async () => {
         httpApiService.mockedObservables.listResultsForHunt = new Subject();
         const mockResults = generateResultListFromResult(mockHuntResult, 80);

         huntResultsLocalStore.setArgs({
           huntId: '1984',
           withType: 'SomeResultType',
         });

         const results = latestValueFrom(huntResultsLocalStore.results$);

         // Next call to HttpService will return 50 mock elements:
         httpApiService.mockedObservables.listResultsForHunt.next(
             mockResults.slice(0, 50),
         );

         expect(results.get().length).toEqual(50);

         // Next call to HttpService will return 10 mock elements:
         httpApiService.mockedObservables.listResultsForHunt.next(
             mockResults.slice(50, 60),
         );

         huntResultsLocalStore.loadMore(10);

         expect(results.get().length).toEqual(60);

         httpApiService.mockedObservables.listResultsForHunt = new Subject();

         // Resets the result list to 0
         huntResultsLocalStore.setArgs({
           huntId: '1234567890',
           withType: 'SomeResultType',
         });

         expect(results.get().length).toEqual(0);

         // Next call to HttpService will return 50 mock elements:
         httpApiService.mockedObservables.listResultsForHunt.next(
             mockResults.slice(0, 50),
         );

         expect(results.get().length).toEqual(50);

         // Next call to HttpService will return 30 mock elements:
         httpApiService.mockedObservables.listResultsForHunt.next(
             mockResults.slice(50, 90),
         );

         huntResultsLocalStore.loadMore(30);

         expect(results.get().length).toEqual(80);
       });
  });
});
