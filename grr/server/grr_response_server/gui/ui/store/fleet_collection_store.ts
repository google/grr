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
import {of, pipe} from 'rxjs';
import {switchMap, takeWhile} from 'rxjs/operators';
import {ApiGetHuntClientCompletionStatsResult} from '../lib/api/api_interfaces';

import {DEFAULT_POLLING_INTERVAL} from '../lib/api/http_api_service';
import {HttpApiWithTranslationService} from '../lib/api/http_api_with_translation_service';
import {
  Hunt,
  HuntApproval,
  HuntError,
  HuntLog,
  HuntResult,
  HuntState,
  ListHuntErrorsArgs,
  ListHuntErrorsResult,
  ListHuntLogsResult,
  ListHuntResultsArgs,
  ListHuntResultsResult,
} from '../lib/models/hunt';
import {PayloadType} from '../lib/models/result';

const MAX_HUNT_COMPLETION_PROGRESS_DATAPOINTS = 100;

/**
 * Collection result of a fleet collection a single client and payload type.
 */
export interface PerClientAndTypeFleetCollectionResults {
  clientId: string;
  resultType: PayloadType;
  results: HuntResult[];
}

interface FleetCollectionStoreState {
  fleetCollectionId: string | null;
  fleetCollection: Hunt | null;
  hasAccess: boolean | null;
  fleetCollectionApprovals: HuntApproval[];
  fleetCollectionResults: readonly HuntResult[];
  totalResultsCount: number;
  fleetCollectionErrors: readonly HuntError[];
  totalErrorsCount: number;
  fleetCollectionProgress: ApiGetHuntClientCompletionStatsResult | null;
  fleetCollectionLogs: readonly HuntLog[];
  totalFleetCollectionLogsCount: number;
}

function getInitialState(): FleetCollectionStoreState {
  return {
    fleetCollectionId: null,
    fleetCollection: null,
    hasAccess: false,
    fleetCollectionApprovals: [],
    fleetCollectionResults: [],
    totalResultsCount: 0,
    fleetCollectionErrors: [],
    totalErrorsCount: 0,
    fleetCollectionProgress: null,
    fleetCollectionLogs: [],
    totalFleetCollectionLogsCount: 0,
  };
}

/**
 * Store for data of a single fleet collection.
 * The lifecycle of this store is tied to the FleetCollectionDetails component.
 */
// tslint:disable-next-line:enforce-name-casing
export const FleetCollectionStore = signalStore(
  withState<FleetCollectionStoreState>(getInitialState),
  withProps(() => ({
    httpApiService: inject(HttpApiWithTranslationService),
    destroyRef: inject(DestroyRef),
  })),
  withMethods(({httpApiService, destroyRef, ...store}) => ({
    initialize(fleetCollectionId: string) {
      patchState(store, {...getInitialState(), fleetCollectionId});
    },
    pollUntilAccess: rxMethod<string | undefined>(
      pipe(
        switchMap((fleetCollectionId: string | undefined) => {
          if (!fleetCollectionId) {
            return of(false);
          }
          return httpApiService
            .verifyHuntAccess(fleetCollectionId, DEFAULT_POLLING_INTERVAL)
            .pipe(
              // We are only polling until access is granted, if a user loses
              // access during the session the state of `hasAccess` will not be
              // updated. This only has an effect on the UI state showing the
              // access, as API calls will still fail.
              takeWhile((hasAccess) => !hasAccess, true),
              tapResponse({
                next: (hasAccess: boolean) => {
                  patchState(store, {hasAccess});
                },
                error: (err) => {
                  throw new Error(
                    `Failed to verify fleet collection access: ${err}`,
                  );
                },
              }),
            );
        }),
      ),
    ),
    pollFleetCollectionApprovals: rxMethod<string | undefined>(
      pipe(
        switchMap((fleetCollectionId: string | undefined) => {
          if (!fleetCollectionId) {
            return of([]);
          }
          return httpApiService
            .listHuntApprovals(fleetCollectionId, DEFAULT_POLLING_INTERVAL)
            .pipe(
              takeWhile(
                (approvals: HuntApproval[]) =>
                  !approvals?.find(
                    (approval) => approval.status.type === 'valid',
                  ),
                true,
              ),
              tapResponse({
                next: (approvals: HuntApproval[]) => {
                  patchState(store, {fleetCollectionApprovals: approvals});
                },
                error: (err) => {
                  throw new Error(
                    `Failed to fetch fleet collection approvals: ${err}`,
                  );
                },
              }),
            );
        }),
      ),
    ),
    pollFleetCollection: rxMethod<string | undefined>(
      pipe(
        switchMap((fleetCollectionId: string | undefined) => {
          if (!fleetCollectionId) {
            return of(null);
          }
          return httpApiService
            .fetchHunt(fleetCollectionId, DEFAULT_POLLING_INTERVAL)
            .pipe(
              tapResponse({
                next: (fleetCollection: Hunt) => {
                  patchState(store, {
                    fleetCollection,
                  });
                },
                error: (err) => {
                  throw new Error(`Failed to fetch fleet collection: ${err}`);
                },
              }),
            );
        }),
      ),
    ),
    pollFleetCollectionResults: rxMethod<ListHuntResultsArgs | undefined>(
      pipe(
        switchMap((args: ListHuntResultsArgs | undefined) => {
          if (!args) {
            return of([]);
          }
          return httpApiService.listResultsForHunt(args).pipe(
            takeUntilDestroyed(destroyRef),
            tapResponse({
              next: (fleetCollectionResults: ListHuntResultsResult) => {
                patchState(store, {
                  fleetCollectionResults: fleetCollectionResults.results,
                  totalResultsCount: fleetCollectionResults.totalCount,
                });
              },
              error: (err) => {
                // TODO: Revisit this once approvals are
                // implemented.
                throw new Error(
                  `Failed to fetch fleet collection results: ${err}`,
                );
              },
            }),
          );
        }),
      ),
    ),
    getFleetCollectionErrors: rxMethod<ListHuntErrorsArgs | undefined>(
      pipe(
        switchMap((args: ListHuntResultsArgs | undefined) => {
          if (!args) {
            return of([]);
          }
          return httpApiService.listErrorsForHunt(args).pipe(
            takeUntilDestroyed(destroyRef),
            tapResponse({
              next: (result: ListHuntErrorsResult) => {
                patchState(store, {
                  fleetCollectionErrors: result.errors,
                  totalErrorsCount: result.totalCount,
                });
              },
              error: (err) => {
                throw new Error(
                  `Failed to fetch fleet collection errors: ${err}`,
                );
              },
            }),
          );
        }),
      ),
    ),
    pollFleetCollectionProgress: rxMethod<string | undefined>(
      pipe(
        switchMap((fleetCollectionId: string | undefined) => {
          if (!fleetCollectionId) {
            return of(null);
          }
          return httpApiService
            .getHuntClientCompletionStats(
              {
                huntId: fleetCollectionId,
                size: `${MAX_HUNT_COMPLETION_PROGRESS_DATAPOINTS}`,
              },
              DEFAULT_POLLING_INTERVAL,
            )
            .pipe(
              tapResponse({
                next: (progressData: ApiGetHuntClientCompletionStatsResult) => {
                  patchState(store, {
                    fleetCollectionProgress: progressData,
                  });
                },
                error: (err) => {
                  // TODO: Revisit this once approvals are
                  // implemented.
                  throw new Error(
                    `Failed to fetch fleet collection results: ${err}`,
                  );
                },
              }),
            );
        }),
      ),
    ),
    requestFleetCollectionApproval(
      fleetCollectionId: string,
      reason: string,
      approvers: string[],
      ccEmail: string[],
    ) {
      httpApiService
        .requestHuntApproval({
          huntId: fleetCollectionId,
          reason,
          approvers,
          cc: ccEmail,
        })
        .pipe(takeUntilDestroyed(destroyRef))
        .subscribe((approval: HuntApproval) => {
          httpApiService
            .listHuntApprovals(fleetCollectionId, 0)
            .pipe(takeUntilDestroyed(destroyRef))
            .subscribe((approvals: HuntApproval[]) => {
              patchState(store, {fleetCollectionApprovals: approvals});
            });
        });
    },
    startFleetCollection: () => {
      const fleetCollectionId = store.fleetCollectionId();
      if (!fleetCollectionId) {
        throw new Error('Fleet collection is not initialized');
      }
      httpApiService
        .patchHunt(fleetCollectionId, {state: HuntState.RUNNING})
        .pipe(takeUntilDestroyed(destroyRef))
        .subscribe((fleetCollection: Hunt) => {
          patchState(store, {
            fleetCollection,
          });
        });
    },
    cancelFleetCollection: () => {
      if (store.fleetCollection()?.state === HuntState.CANCELLED) {
        return;
      }
      const fleetCollectionId = store.fleetCollectionId();
      if (!fleetCollectionId) {
        throw new Error('Fleet collection is not initialized');
      }
      httpApiService
        .patchHunt(fleetCollectionId, {state: HuntState.CANCELLED})
        .pipe(takeUntilDestroyed(destroyRef))
        .subscribe((fleetCollection: Hunt) => {
          patchState(store, {
            fleetCollection,
          });
        });
    },
    updateFleetCollection: (clientLimit: bigint, clientRate: number) => {
      const fleetCollectionId = store.fleetCollectionId();
      if (!fleetCollectionId) {
        throw new Error('Fleet collection is not initialized');
      }
      httpApiService
        .patchHunt(fleetCollectionId, {clientLimit, clientRate})
        .pipe(takeUntilDestroyed(destroyRef))
        .subscribe((fleetCollection: Hunt) => {
          patchState(store, {
            fleetCollection,
          });
        });
    },
    fetchFleetCollectionLogs(fleetCollectionId: string) {
      httpApiService
        .fetchHuntLogs(fleetCollectionId)
        .pipe(takeUntilDestroyed(destroyRef))
        .subscribe((result: ListHuntLogsResult) => {
          patchState(store, {
            fleetCollectionLogs: result.logs,
            totalFleetCollectionLogsCount: result.totalCount,
          });
        });
    },
  })),
  withComputed((store) => ({
    latestApproval: computed(
      () =>
        store
          .fleetCollectionApprovals()
          ?.find((approval) => approval?.status.type !== 'expired') ?? null,
    ),
    hasMoreResults: computed(
      () => store.fleetCollectionResults().length < store.totalResultsCount(),
    ),
    hasMoreErrors: computed(
      () => store.fleetCollectionErrors().length < store.totalErrorsCount(),
    ),
    fleetCollectionResultsPerClientAndType: computed<
      PerClientAndTypeFleetCollectionResults[]
    >(() => {
      // Temporary map to group results: clientId -> payloadType -> HuntResult[]
      const resultsPerClientByType = new Map<
        string,
        Map<PayloadType, HuntResult[]>
      >();

      for (const result of store.fleetCollectionResults()) {
        const {clientId, payloadType} = result;

        if (!payloadType) {
          continue;
        }

        let clientResults = resultsPerClientByType.get(clientId);
        if (!clientResults) {
          clientResults = new Map<PayloadType, HuntResult[]>();
          resultsPerClientByType.set(clientId, clientResults);
        }

        let typeResults = clientResults.get(payloadType);
        if (!typeResults) {
          typeResults = [];
          clientResults.set(payloadType, typeResults);
        }

        typeResults.push(result);
      }

      return Array.from(resultsPerClientByType.values()).flatMap(
        (resultsByType) =>
          Array.from(resultsByType.entries()).map(([payloadType, results]) => ({
            clientId: results[0].clientId,
            resultType: payloadType,
            results,
          })),
      );
    }),
  })),
);
