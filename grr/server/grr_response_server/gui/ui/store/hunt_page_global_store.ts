import {Injectable} from '@angular/core';
import {ComponentStore} from '@ngrx/component-store';
import {combineLatest, merge, Observable, of} from 'rxjs';
import {distinctUntilChanged, filter, map, scan, shareReplay, startWith, switchMap, tap, withLatestFrom} from 'rxjs/operators';

import {ApiHuntError, ApiHuntResult} from '../lib/api/api_interfaces';
import {HttpApiService} from '../lib/api/http_api_service';
import {RequestStatus, RequestStatusType, trackRequest} from '../lib/api/track_request';
import {getHuntResultKey, toApiHuntState, translateHunt} from '../lib/api_translation/hunt';
import {Hunt, HuntState} from '../lib/models/hunt';
import {isNonNull} from '../lib/preconditions';

interface HuntPageState {
  readonly huntId?: string;

  readonly listResultsCount: number;
  readonly listErrorsCount: number;

  readonly allResults: AllHuntResultsState;

  readonly selectedHuntResultKey: string;

  readonly patchHuntRequestStatus?: RequestStatus<Hunt>;
}

/**
 * HuntResultsState holds the results for the hunt (partial or complete), as
 * well as metadata regarding whether more results are being loaded from the
 * backend or whether the list is complete.
 */
export interface AllHuntResultsState {
  /**
   * True, whenever new flows are being loaded, e.g. upon page load and when
   * more flows are being loaded. This stays false during the re-polling of
   * already loaded flows.
   */
  isLoading: boolean;
  results?: {[key: string]: ApiHuntResult};

  /** Number of results already loaded. */
  loadedCount?: number;

  /**
   * Indicates whether all results are already fetched (in `results`), or more
   * results can be loaded.
   */
  hasMore?: boolean;
}

/**
 * HuntErrorsState holds the errors for the hunt (partial or complete), as
 * well as metadata regarding whether more errors are being loaded from the
 * backend or whether the list is complete.
 */
export interface HuntErrorsState {
  /**
   * True, whenever new errors are being loaded. This stays false during the
   * re-polling of already loaded errors.
   */
  isLoading: boolean;
  errors?: readonly ApiHuntError[];

  /** Number of errors already loaded. */
  loadedCount?: number;

  /**
   * Indicates whether all errors are already fetched (in `errors`), or more
   * errors can be loaded.
   */
  hasMore?: boolean;
}

/** Number of results to fetch per request. */
export const RESULTS_BATCH_SIZE = 50;
/** Number of errors to fetch per request. */
export const ERRORS_BATCH_SIZE = 50;

/** ComponentStore implementation used by the GlobalStore. */
class HuntPageComponentStore extends ComponentStore<HuntPageState> {
  constructor(private readonly httpApiService: HttpApiService) {
    super({
      // Start without results and let the hunt results component `loadMore`.
      listResultsCount: 0,
      listErrorsCount: 0,
      allResults: {isLoading: false},
      selectedHuntResultKey: '',
    });
  }

  readonly listResultsCount$ = this.select(state => state.listResultsCount);
  readonly listErrorsCount$ = this.select(state => state.listErrorsCount);

  // Controls listResultsCount$, which effectively controls the huntResults$.
  readonly loadMoreResults = this.updater<void>(
      (state) => {
        return ({
          ...state,
          listResultsCount: state.listResultsCount + RESULTS_BATCH_SIZE,
        });
      },
  );
  // Controls listErrorsCount$, which effectively controls the huntResults$.
  readonly loadMoreErrors = this.updater<void>(
      (state) => {
        return ({
          ...state,
          listErrorsCount: state.listErrorsCount + ERRORS_BATCH_SIZE,
        });
      },
  );

  /** Reducer resetting the store and setting the huntId. */
  readonly selectHunt = this.updater<string>((state, huntId) => {
    // Clear complete state when new hunt is selected to prevent stale
    // information.
    return {
      huntId,
      listResultsCount: 0,
      listErrorsCount: 0,
      allResults: {isLoading: false},
      selectedHuntResultKey: '',
    };
  });

  /** An observable emitting the hunt id of the selected hunt. */
  readonly selectedHuntId$: Observable<string|null> =
      this.select(state => state.huntId ?? null)
          .pipe(
              distinctUntilChanged(),
              shareReplay({bufferSize: 1, refCount: true}),
          );

  private readonly periodicallyPolledHunt$ = this.selectedHuntId$.pipe(
      switchMap(
          huntId => huntId ? this.httpApiService.subscribeToHunt(huntId).pipe(
                                 startWith(null),
                                 ) :
                             of(null)),
      map(hunt => hunt ? translateHunt(hunt) : null),
      shareReplay({bufferSize: 1, refCount: true}),
  );

  readonly patchHuntRequestStatus$ =
      this.select(state => state.patchHuntRequestStatus);

  private readonly patchedHunt$ = this.patchHuntRequestStatus$.pipe(
      map(req => req?.status === RequestStatusType.SUCCESS ? req.data : null),
      filter(isNonNull),
  );

  /** An observable emitting the hunt loaded by `selectHunt`. */
  readonly selectedHunt$: Observable<Hunt|null> = merge(
      this.periodicallyPolledHunt$,
      this.patchedHunt$,
  );

  private subscribeToResultsForHunt(huntId: string):
      Observable<AllHuntResultsState> {
    return this.listResultsCount$.pipe(
        switchMap<number, Observable<AllHuntResultsState>>(
            (count) => merge(
                // Whenever more results are requested, listFlowsCount changes
                // and we emit `isLoading: true` immediately.
                of<AllHuntResultsState>({isLoading: true}),
                this.httpApiService
                    // TODO: fetch delta only (populate offset).
                    .subscribeToResultsForHunt(
                        {huntId, count: count.toString()})
                    .pipe(
                        map((apiHuntResults: ReadonlyArray<ApiHuntResult>) => {
                          const res: {[key: string]: ApiHuntResult} = {};
                          for (const result of apiHuntResults) {
                            res[getHuntResultKey(result, huntId)] = result;
                          }

                          return ({
                            isLoading: false,
                            results: res,
                            loadedCount: apiHuntResults.length,
                            hasMore: count <= apiHuntResults.length,
                          });
                        }),
                        ))),
        // Re-emit old results while new results are being loaded to prevent the
        // UI from showing a blank state after triggering loading of more flows.
        scan<AllHuntResultsState, AllHuntResultsState>(
            (acc, next) => ({...next, results: next.results ?? acc.results}),
            {isLoading: false}),
    );
  }

  /**
   * An observable emitting the hunt results after `loadMoreResults` is called.
   */
  readonly huntResults$: Observable<AllHuntResultsState> =
      this.selectedHuntId$.pipe(
          switchMap(
              (huntId: string|null) =>
                  this.subscribeToResultsForHunt(huntId ?? '')),
          shareReplay({bufferSize: 1, refCount: true}),
      );

  readonly selectedHuntResultId$ =
      this.select(state => state.selectedHuntResultKey)
          .pipe(distinctUntilChanged());

  readonly selectedHuntResult$: Observable<ApiHuntResult|null> =
      combineLatest([
        this.huntResults$, this.selectedHuntResultId$
      ]).pipe(map(([resultState, resultId]) => {
        // No need to fetch if there is no selected key.
        if (!resultId) {
          return null;
        }

        // If the selected result is already on the map, simply return it.
        if (resultState.results && resultState.results[resultId]) {
          return resultState.results[resultId];
        }

        // If we're already loading, wait a little longer.
        if (resultState.isLoading) {
          return null;
        }

        // If all results are loaded and the key is not there, return.
        if (resultState.results && !resultState.hasMore &&
            !resultState.results[resultId]) {
          throw new Error(`Result not found: ${resultId}`);
        }

        // If not, then we fetch more results.
        this.loadMoreResults();
        return null;
      }));

  readonly selectResult = this.updater<string>(
      (state, key) => {
        return ({
          ...state,
          selectedHuntResultKey: key,
        });
      },
  );

  private subscribeToErrorsForHunt(huntId: string):
      Observable<HuntErrorsState> {
    return this.listErrorsCount$.pipe(
        switchMap<number, Observable<HuntErrorsState>>(
            (count) => merge(
                // Whenever more results are requested, listFlowsCount changes
                // and we emit `isLoading: true` immediately.
                of<HuntErrorsState>({isLoading: true}),
                this.httpApiService
                    .subscribeToErrorsForHunt({huntId, count: count.toString()})
                    .pipe(
                        map((apiHuntErrors: readonly ApiHuntError[]) => ({
                              isLoading: false,
                              errors: apiHuntErrors,
                              loadedCount: apiHuntErrors.length,
                              hasMore: count <= apiHuntErrors.length,
                            })),
                        ))),
        // Re-emit old results while new results are being loaded to prevent the
        // UI from showing a blank state after triggering loading of more flows.
        scan<HuntErrorsState, HuntErrorsState>(
            (acc, next) => ({...next, errors: next.errors ?? acc.errors}),
            {isLoading: false}),
    );
  }

  /**
   * An observable emitting the hunt results after `loadMoreErrors` is called.
   */
  readonly huntErrors$: Observable<HuntErrorsState> = this.selectedHuntId$.pipe(
      switchMap(
          (huntId: string|null) => this.subscribeToErrorsForHunt(huntId ?? '')),
      shareReplay({bufferSize: 1, refCount: true}),
  );

  /**
   * An effect requesting to update the hunt state.
   */
  readonly patchHunt = this.effect<{state: HuntState}>(
      obs$ => obs$.pipe(
          withLatestFrom(this.state$),
          switchMap(
              ([patch, storeState]) =>
                  trackRequest(this.httpApiService
                                   .patchHunt(
                                       storeState.huntId ?? '',
                                       {state: toApiHuntState(patch.state)})
                                   .pipe(map(hunt => translateHunt(hunt)))),
              ),
          tap((patchHuntRequestStatus) => {
            this.patchState({patchHuntRequestStatus});
          }),
          ));
}

/** GlobalStore for hunt page related API calls. */
@Injectable({
  providedIn: 'root',
})
export class HuntPageGlobalStore {
  constructor(private readonly httpApiService: HttpApiService) {}

  private readonly store = new HuntPageComponentStore(this.httpApiService);

  /** Selects a hunt with a given id. */
  selectHunt(huntId: string): void {
    this.store.selectHunt(huntId);
  }

  readonly selectedHuntId$ = this.store.selectedHuntId$;
  readonly selectedHunt$ = this.store.selectedHunt$;

  readonly selectedHuntResultId$ = this.store.selectedHuntResultId$;
  readonly selectedHuntResult$ = this.store.selectedHuntResult$;

  readonly huntResults$ = this.store.huntResults$;
  readonly huntErrors$ = this.store.huntErrors$;

  // TODO: Stop leaking implementation details - unify loadMore
  // function and let the store manage the calls to different apis.
  loadMoreResults() {
    this.store.loadMoreResults();
  }
  loadMoreErrors() {
    this.store.loadMoreErrors();
  }

  selectResult(key: string) {
    this.store.selectResult(key);
  }

  stopHunt() {
    this.store.patchHunt({state: HuntState.STOPPED});
  }
}
