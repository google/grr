import {HttpErrorResponse} from '@angular/common/http';
import {DestroyRef, inject} from '@angular/core';
import {takeUntilDestroyed} from '@angular/core/rxjs-interop';
import {tapResponse} from '@ngrx/operators';
import {
  patchState,
  signalStore,
  withMethods,
  withProps,
  withState,
} from '@ngrx/signals';
import {rxMethod} from '@ngrx/signals/rxjs-interop';
import {of, pipe} from 'rxjs';
import {switchMap} from 'rxjs/operators';

import {HttpApiWithTranslationService} from '../lib/api/http_api_with_translation_service';
import {Client, ClientApproval} from '../lib/models/client';

const DEFAULT_COUNT = 256;
const DEFAULT_CONTENT_OFFSET = 0;

const DEFAULT_RECENT_APPROVALS_COUNT = 20;

interface ClientSearchStoreState {
  readonly clients: readonly Client[];
  readonly recentApprovals: readonly ClientApproval[];
}

const initialState: ClientSearchStoreState = {
  clients: [],
  recentApprovals: [],
};

/**
 * Store for client search.
 * The lifecycle of this store is tied to the ClientSearch component.
 */
// tslint:disable-next-line:enforce-name-casing
export const ClientSearchStore = signalStore(
  withState<ClientSearchStoreState>(initialState),
  withProps(() => ({
    httpApiService: inject(HttpApiWithTranslationService),
    destroyRef: inject(DestroyRef),
  })),
  withMethods(({httpApiService, destroyRef, ...store}) => ({
    searchClients: rxMethod<string>(
      pipe(
        switchMap((query: string) => {
          query = query.trim();
          if (query === '') {
            return of([]);
          }
          return httpApiService
            .searchClients({
              query,
              count: String(DEFAULT_COUNT),
              offset: String(DEFAULT_CONTENT_OFFSET),
            })
            .pipe(
              tapResponse({
                next: (clients: Client[]) => {
                  patchState(store, {clients});
                },
                error: (err: HttpErrorResponse) => {
                  // TODO: Revisit this once errors are handled.
                  throw err;
                },
              }),
            );
        }),
      ),
    ),
    fetchRecentClientApprovals() {
      return httpApiService
        .listRecentClientApprovals({
          count: DEFAULT_RECENT_APPROVALS_COUNT,
        })
        .pipe(takeUntilDestroyed(destroyRef))
        .subscribe((approvals: readonly ClientApproval[]) => {
          patchState(store, {
            recentApprovals: approvals,
          });
        });
    },
  })),
);
