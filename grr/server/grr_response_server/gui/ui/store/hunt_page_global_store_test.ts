import {TestBed} from '@angular/core/testing';
import {firstValueFrom} from 'rxjs';
import {filter} from 'rxjs/operators';

import {ApiHuntState} from '../lib/api/api_interfaces';
import {HttpApiService} from '../lib/api/http_api_service';
import {HttpApiServiceMock, mockHttpApiService} from '../lib/api/http_api_service_test_util';
import {HuntState} from '../lib/models/hunt';
import {isNonNull} from '../lib/preconditions';
import {initTestEnvironment} from '../testing';

import {ConfigGlobalStore} from './config_global_store';
import {ConfigGlobalStoreMock, mockConfigGlobalStore} from './config_global_store_test_util';
import {HuntPageGlobalStore} from './hunt_page_global_store';

initTestEnvironment();

describe('HuntPageGlobalStore', () => {
  let httpApiService: HttpApiServiceMock;
  let huntPageGlobalStore: HuntPageGlobalStore;
  let configGlobalStore: ConfigGlobalStoreMock;

  beforeEach(() => {
    httpApiService = mockHttpApiService();
    configGlobalStore = mockConfigGlobalStore();
    TestBed
        .configureTestingModule({
          imports: [],
          providers: [
            HuntPageGlobalStore,
            {provide: HttpApiService, useFactory: () => httpApiService},
            {provide: ConfigGlobalStore, useFactory: () => configGlobalStore},
          ],
          teardown: {destroyAfterEach: false}
        })
        .compileComponents();

    huntPageGlobalStore = TestBed.inject(HuntPageGlobalStore);
  });

  it('fetches hunt from api',
     () => {
       const sub = huntPageGlobalStore.selectedHunt$.subscribe();
       httpApiService.mockedObservables.subscribeToHunt.next({
         huntId: '1984',
         description: 'Ghost',
         creator: 'buster',
       });

       huntPageGlobalStore.selectHunt('1984');
       expect(httpApiService.subscribeToHunt).toHaveBeenCalledWith('1984');
       sub.unsubscribe();
     });

  it('emits updated data',
     async () => {
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
     });

  it('stopHunt calls http api service',
     () => {
       huntPageGlobalStore.selectHunt('456');
       huntPageGlobalStore.cancelHunt();
       expect(httpApiService.patchHunt)
           .toHaveBeenCalledWith(
               '456',
               {state: HuntState.CANCELLED},
           );
     });

  it('startHunt calls http api service',
     () => {
       huntPageGlobalStore.selectHunt('456');
       huntPageGlobalStore.startHunt();
       expect(httpApiService.patchHunt)
           .toHaveBeenCalledWith(
               '456',
               {state: HuntState.RUNNING},
           );
     });

  it('modifyAndStartHunt calls http api service',
     () => {
       huntPageGlobalStore.selectHunt('456');
       huntPageGlobalStore.modifyAndStartHunt(
           {clientRate: 123, clientLimit: BigInt(456)});
       expect(httpApiService.patchHunt)
           .toHaveBeenCalledWith(
               '456',
               {
                 clientRate: 123,
                 clientLimit: BigInt(456),
                 state: HuntState.RUNNING
               },
           );
     });

  it('fetches hunt progress data from api',
     () => {
       const sub = huntPageGlobalStore.huntProgress$.subscribe();
       httpApiService.mockedObservables.subscribeToHuntClientCompletionStats
           .next({
             startPoints: [
               {xValue: 1669026000, yValue: 10},
             ],
             completePoints: [
               {xValue: 1669026000, yValue: 5},
             ],
           });

       huntPageGlobalStore.selectHunt('1984');
       expect(httpApiService.subscribeToHuntClientCompletionStats)
           .toHaveBeenCalledWith({huntId: '1984', size: '1000'});
       sub.unsubscribe();
     });

  describe('Hunt result counts per type', () => {
    it('Tries to fetch Hunt results count if the Hunt has started', () => {
      huntPageGlobalStore.selectedHunt$.subscribe();
      huntPageGlobalStore.huntResultTabs$.subscribe();

      huntPageGlobalStore.selectHunt('1984');

      httpApiService.mockedObservables.subscribeToHunt.next({
        huntId: '1984',
        description: 'Ghost',
        creator: 'buster',
        name: 'Name',
        created: '123456789',
        state: ApiHuntState.STARTED,
        huntRunnerArgs: {clientRate: 0},
      });

      expect(httpApiService.subscribeToHunt).toHaveBeenCalledWith('1984');

      expect(httpApiService.subscribeToHuntResultsCountByType)
          .toHaveBeenCalledWith('1984');
    });

    it('Does not try to fetch Hunt results count if the Hunt has not started',
       () => {
         huntPageGlobalStore.huntResultTabs$.subscribe();

         huntPageGlobalStore.selectHunt('1984');

         httpApiService.mockedObservables.subscribeToHunt.next({
           huntId: '1984',
           description: 'Ghost',
           creator: 'buster',
           name: 'Name',
           created: '123456789',
           state: ApiHuntState.PAUSED,
           huntRunnerArgs: {clientRate: 0},
         });

         expect(httpApiService.subscribeToHuntResultsCountByType)
             .not.toHaveBeenCalled();
       });
  });

  it('loading state is reflected when fetching Results Count by type',
     async () => {
       huntPageGlobalStore.selectedHunt$.subscribe();
       huntPageGlobalStore.huntResultTabs$.subscribe();

       huntPageGlobalStore.selectHunt('1984');

       httpApiService.mockedObservables.subscribeToHunt.next({
         huntId: '1984',
         description: 'Ghost',
         creator: 'buster',
         name: 'Name',
         created: '123456789',
         state: ApiHuntState.STARTED,
         huntRunnerArgs: {clientRate: 0},
       });

       expect(httpApiService.subscribeToHunt).toHaveBeenCalledWith('1984');

       expect(httpApiService.subscribeToHuntResultsCountByType)
           .toHaveBeenCalledWith('1984');

       const isLoadingBeforeResponse = await firstValueFrom(
           huntPageGlobalStore.huntResultsByTypeCountLoading$);

       expect(isLoadingBeforeResponse).toBe(true);

       httpApiService.mockedObservables.subscribeToHuntResultsCountByType.next(
           {items: []});

       const isLoadingAfterResponse = await firstValueFrom(
           huntPageGlobalStore.huntResultsByTypeCountLoading$);

       expect(isLoadingAfterResponse).toBe(false);
     });
});
