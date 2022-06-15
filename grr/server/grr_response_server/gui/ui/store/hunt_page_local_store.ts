import {Injectable} from '@angular/core';
import {ComponentStore} from '@ngrx/component-store';
import {merge, Observable, of} from 'rxjs';
import {distinctUntilChanged, map, scan, shareReplay, startWith, switchMap} from 'rxjs/operators';

import {ApiHunt, ApiHuntResult} from '../lib/api/api_interfaces';
import {HttpApiService} from '../lib/api/http_api_service';

interface HuntPageState {
  readonly huntId?: string;

  listResultsCount: number;
}
/**
 * HuntResultsState holds the results for the hunt (partial or complete), as
 * well as metadata regarding whether more results are being loaded from the
 * backend or whether the list is complete.
 */
export interface HuntResultsState {
  /**
   * True, whenever new flows are being loaded, e.g. upon page load and when
   * more flows are being loaded. This stays false during the re-polling of
   * already loaded flows.
   */
  isLoading: boolean;
  results?: ReadonlyArray<ApiHuntResult>;

  // TODO: add `hasMore?: boolean` for knowing when it is possible
  // to loadMoreResults().
}

/** Number of results to fetch per request. */
export const RESULTS_BATCH_SIZE = 50;

/** ComponentStore implementation used by the GlobalStore. */
class HuntPageComponentStore extends ComponentStore<HuntPageState> {
  constructor(private readonly httpApiService: HttpApiService) {
    super({
      // Start without results and let the hunt results component `loadMore`.
      listResultsCount: 0,
    } as HuntPageState);
  }

  /** Reducer resetting the store and setting the huntId. */
  readonly selectHunt = this.updater<string>((state, huntId) => {
    // Clear complete state when new hunt is selected to prevent stale
    // information.
    return {
      huntId,
      listResultsCount: 0,
    } as HuntPageState;
  });

  /** An observable emitting the hunt id of the selected hunt. */
  readonly selectedHuntId$: Observable<string|null> =
      this.select(state => state.huntId ?? null)
          .pipe(
              distinctUntilChanged(),
          );

  /** An observable emitting the hunt loaded by `selectHunt`. */
  readonly selectedHunt$: Observable<ApiHunt|null> = this.selectedHuntId$.pipe(
      switchMap(
          huntId => huntId ? this.httpApiService.subscribeToHunt(huntId).pipe(
                                 startWith(null),
                                 ) :
                             of(null)),
      shareReplay({bufferSize: 1, refCount: true}),
  );

  readonly listResultsCount$ = this.select(state => state.listResultsCount);

  // Controls listResultsCount$, which effectively controls the huntResults$.
  readonly loadMoreResults = this.updater<void>(
      (state) => {
        return ({
          ...state,
          listResultsCount: state.listResultsCount + RESULTS_BATCH_SIZE,
        });
      },
  );

  private subscribeToResultsForHunt(huntId: string):
      Observable<HuntResultsState> {
    return this.listResultsCount$.pipe(
        switchMap<number, Observable<HuntResultsState>>(
            (count) => merge(
                // Whenever more results are requested, listFlowsCount changes
                // and we emit `isLoading: true` immediately.
                of<HuntResultsState>({isLoading: true} as HuntResultsState),
                this.httpApiService
                    // TODO: fetch delta only (populate offset).
                    .subscribeToResultsForHunt({huntId, count})
                    .pipe(
                        map((apiHuntResults: ReadonlyArray<ApiHuntResult>) => {
                          return ({
                                   isLoading: false,
                                   results: apiHuntResults,
                                 }) as HuntResultsState;
                        }),
                        ))),
        // Re-emit old results while new results are being loaded to prevent the
        // UI from showing a blank state after triggering loading of more flows.
        scan<HuntResultsState, HuntResultsState>(
            (acc, next) => ({...next, results: next.results ?? acc.results}),
            {isLoading: false} as HuntResultsState),
    );
  }

  /**
   * An observable emitting the hunt results after `loadMoreResults` is called.
   */
  readonly huntResults$: Observable<HuntResultsState> =
      this.selectedHuntId$.pipe(
          switchMap(
              (huntId: string|null) =>
                  this.subscribeToResultsForHunt(huntId ?? '')),
          shareReplay({bufferSize: 1, refCount: true}),
      );
}

/** LocalStore for new hunt related API calls. */
@Injectable()
export class HuntPageLocalStore {
  constructor(private readonly httpApiService: HttpApiService) {}

  private readonly store = new HuntPageComponentStore(this.httpApiService);

  /** Selects a hunt with a given id. */
  selectHunt(huntId: string): void {
    this.store.selectHunt(huntId);
  }

  readonly selectedHuntId$ = this.store.selectedHuntId$;

  readonly selectedHunt$ = this.store.selectedHunt$;

  readonly huntResults$ = this.store.huntResults$;

  loadMoreResults() {
    this.store.loadMoreResults();
  }
}
