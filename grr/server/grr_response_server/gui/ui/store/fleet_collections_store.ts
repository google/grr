import {computed, DestroyRef, inject} from '@angular/core';
import {takeUntilDestroyed} from '@angular/core/rxjs-interop';
import {tapResponse} from '@ngrx/operators';
import {
  patchState,
  signalStore,
  withComputed,
  withMethods,
  withProps,
  withState,
} from '@ngrx/signals';
import {rxMethod} from '@ngrx/signals/rxjs-interop';
import {pipe} from 'rxjs';
import {switchMap} from 'rxjs/operators';

import {DEFAULT_POLLING_INTERVAL} from '../lib/api/http_api_service';
import {HttpApiWithTranslationService} from '../lib/api/http_api_with_translation_service';
import {Hunt, ListHuntsArgs, ListHuntsResult} from '../lib/models/hunt';

interface FleetCollectionsStoreState {
  fleetCollections: Hunt[];
  totalFleetCollectionsCount: number;
}

function getInitialState(): FleetCollectionsStoreState {
  return {
    fleetCollections: [],
    totalFleetCollectionsCount: 0,
  };
}

/**
 * Store for fleet collections data displayed in the FleetCollectionsPage.
 * The lifecycle of this store is tied to the FleetCollectionsPage.
 */
// tslint:disable-next-line:enforce-name-casing
export const FleetCollectionsStore = signalStore(
  withState<FleetCollectionsStoreState>(getInitialState),
  withProps(() => ({
    httpApiService: inject(HttpApiWithTranslationService),
    destroyRef: inject(DestroyRef),
  })),
  withMethods(({httpApiService, destroyRef, ...store}) => ({
    pollFleetCollections: rxMethod<ListHuntsArgs>(
      pipe(
        switchMap((args: ListHuntsArgs) => {
          return httpApiService.listHunts(args, DEFAULT_POLLING_INTERVAL).pipe(
            takeUntilDestroyed(destroyRef),
            tapResponse({
              next: (fleetCollections: ListHuntsResult) => {
                patchState(store, {
                  fleetCollections: fleetCollections.hunts,
                  totalFleetCollectionsCount: fleetCollections.totalCount,
                });
              },
              error: (err) => {
                // TODO: Revisit this once approvals are
                // implemented.
                throw err;
              },
            }),
          );
        }),
      ),
    ),
  })),
  withComputed((store) => ({
    hasMoreFleetCollections: computed(
      () =>
        store.fleetCollections().length < store.totalFleetCollectionsCount(),
    ),
  })),
);
