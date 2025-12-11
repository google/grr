import {fakeAsync, TestBed, tick} from '@angular/core/testing';
import {patchState} from '@ngrx/signals';
import {unprotected} from '@ngrx/signals/testing';

import {ApiListHuntsArgsRobotFilter} from '../lib/api/api_interfaces';
import {DEFAULT_POLLING_INTERVAL} from '../lib/api/http_api_service';
import {HttpApiWithTranslationService} from '../lib/api/http_api_with_translation_service';
import {
  HttpApiWithTranslationServiceMock,
  mockHttpApiWithTranslationService,
} from '../lib/api/http_api_with_translation_test_util';
import {HuntState} from '../lib/models/hunt';
import {newHunt} from '../lib/models/model_test_util';
import {FleetCollectionsStore} from './fleet_collections_store';

describe('Fleet Collections Store', () => {
  let httpApiService: HttpApiWithTranslationServiceMock;

  beforeEach(() => {
    httpApiService = mockHttpApiWithTranslationService();

    TestBed.configureTestingModule({
      providers: [
        FleetCollectionsStore,
        {
          provide: HttpApiWithTranslationService,
          useFactory: () => httpApiService,
        },
      ],
    });
  });

  it('calls api to fetch fleet collections and updates store when `pollFleetCollections` is called', fakeAsync(() => {
    const store = TestBed.inject(FleetCollectionsStore);

    store.pollFleetCollections({
      count: 100,
      robotFilter: ApiListHuntsArgsRobotFilter.NO_ROBOTS,
      stateFilter: HuntState.NOT_STARTED,
    });
    tick();
    const listHuntsResult = {hunts: [newHunt({}), newHunt({})], totalCount: 2};
    httpApiService.mockedObservables.listHunts.next(listHuntsResult);

    expect(httpApiService.listHunts).toHaveBeenCalledWith(
      {
        count: 100,
        robotFilter: ApiListHuntsArgsRobotFilter.NO_ROBOTS,
        stateFilter: HuntState.NOT_STARTED,
      },
      DEFAULT_POLLING_INTERVAL,
    );
    expect(store.fleetCollections()).toEqual(listHuntsResult.hunts);
    expect(store.totalFleetCollectionsCount()).toEqual(
      listHuntsResult.totalCount,
    );
  }));

  it('returns false for `hasMoreFleetCollections` when there are no more fleet collections than the store holds', () => {
    const store = TestBed.inject(FleetCollectionsStore);
    patchState(unprotected(store), {
      fleetCollections: [newHunt({}), newHunt({})],
    });
    patchState(unprotected(store), {totalFleetCollectionsCount: 2});

    expect(store.hasMoreFleetCollections()).toBeFalse();
  });

  it('returns true for `hasMoreFleetCollections` when there are more fleet collections than the store holds', () => {
    const store = TestBed.inject(FleetCollectionsStore);
    patchState(unprotected(store), {
      fleetCollections: [newHunt({}), newHunt({})],
    });
    patchState(unprotected(store), {totalFleetCollectionsCount: 3});

    expect(store.hasMoreFleetCollections()).toBeTrue();
  });
});
