import {Injectable} from '@angular/core';
import {ComponentStore} from '@ngrx/component-store';
import {combineLatest, merge, Observable, of} from 'rxjs';
import {distinctUntilChanged, filter, map, scan, shareReplay, startWith, switchMap, tap, withLatestFrom} from 'rxjs/operators';

import {ApiHuntError, ApiHuntResult} from '../lib/api/api_interfaces';
import {HttpApiService} from '../lib/api/http_api_service';
import {RequestStatus, RequestStatusType, trackRequest} from '../lib/api/track_request';
import {translateFlow} from '../lib/api_translation/flow';
import {getHuntResultKey, translateHunt} from '../lib/api_translation/hunt';
import {FlowWithDescriptor} from '../lib/models/flow';
import {Hunt, HuntState} from '../lib/models/hunt';
import {toResultKey} from '../lib/models/result';
import {isNonNull} from '../lib/preconditions';

import {ConfigGlobalStore} from './config_global_store';


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
  errors?: {[key: string]: ApiHuntError};

  /** Number of errors already loaded. */
  loadedCount?: number;

  /**
   * Indicates whether all errors are already fetched (in `errors`), or more
   * errors can be loaded.
   */
  hasMore?: boolean;
}

// TODO: Refactor HuntResultsState and HuntErrorsState into a
// common interface. Consider using and extending `ApiStore`.
/** Gets selected data (result or error) from a state. */
function getSelectedData(
    key: string, state: {isLoading: boolean, hasMore?: boolean},
    dataMap: {[key: string]: ApiHuntResult|ApiHuntError}|undefined,
    loadMore: Function): ApiHuntResult|ApiHuntError|null {
  // No need to fetch if there is no selected key.
  if (!key) {
    return null;
  }

  // If the selected data is already on the map, simply return it.
  if (dataMap && dataMap[key]) {
    return dataMap[key];
  }

  // If we're already loading, wait a little longer.
  if (state.isLoading) {
    return null;
  }

  // If all results are loaded and the key is not there, return.
  if (dataMap && !state.hasMore && !dataMap[key]) {
    return null;
  }

  // If not, then we fetch more results.
  loadMore();
  return null;
}

/** Number of results to fetch per request. */
export const RESULTS_BATCH_SIZE = 50;
/** Number of errors to fetch per request. */
export const ERRORS_BATCH_SIZE = 50;

/** Maximum number of progress data-points to fetch per Hunt */
const MAX_HUNT_COMPLETION_PROGRESS_DATAPOINTS = 1_000;

/** ComponentStore implementation used by the GlobalStore. */
class HuntPageComponentStore extends ComponentStore<HuntPageState> {
  constructor(
      private readonly httpApiService: HttpApiService,
      private readonly configGlobalStore: ConfigGlobalStore,
  ) {
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

  private readonly filteredSelectedHuntId$ =
      this.selectedHuntId$.pipe(filter(isNonNull));

  private readonly periodicallyPolledHunt$ = this.selectedHuntId$.pipe(
      switchMap(
          huntId => huntId ? this.httpApiService.subscribeToHunt(huntId).pipe(
                                 startWith(null),
                                 ) :
                             of(null)),
      map(hunt => hunt ? translateHunt(hunt) : null),
      shareReplay({bufferSize: 1, refCount: true}),
  );

  private readonly periodicallyPolledHuntProgress$ =
      this.filteredSelectedHuntId$.pipe(
          switchMap(
              huntId =>
                  this.httpApiService.subscribeToHuntClientCompletionStats({
                    huntId,
                    size: `${MAX_HUNT_COMPLETION_PROGRESS_DATAPOINTS}`
                  })),
      );

  readonly huntProgress$ = this.periodicallyPolledHuntProgress$;

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
                        map((apiHuntResults: readonly ApiHuntResult[]) => {
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
      combineLatest([this.huntResults$, this.selectedHuntResultId$])
          .pipe(
              map(([resultState, resultId]) => getSelectedData(
                      resultId, resultState, resultState.results,
                      this.loadMoreResults)));

  readonly selectedResultFlowWithDescriptor$:
      Observable<FlowWithDescriptor|null> =
          combineLatest([
            this.selectedHuntResultId$.pipe(
                filter(key => key ? true : false), map(id => toResultKey(id))),
            this.configGlobalStore.flowDescriptors$
          ])
              .pipe(
                  switchMap(([resultKey, fds]) => {
                    return this.httpApiService
                        .fetchFlow(resultKey.clientId, resultKey.flowId)
                        .pipe(
                            map(apiFlow => {
                              if (apiFlow) {
                                const type = apiFlow.args?.['@type'];
                                return {
                                  flow: translateFlow(apiFlow),
                                  descriptor: fds.get(apiFlow.name ?? ''),
                                  flowArgType: typeof type === 'string' ?
                                      type :
                                      undefined,
                                };
                              }
                              return null;
                            }),
                        );
                  }),
                  startWith(null),
              );

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
                        map((apiHuntErrors: readonly ApiHuntError[]) => {
                          const errors: {[key: string]: ApiHuntResult} = {};
                          for (const error of apiHuntErrors) {
                            errors[getHuntResultKey(error, huntId)] = error;
                          }
                          return {
                            isLoading: false,
                            errors,
                            loadedCount: apiHuntErrors.length,
                            hasMore: count <= apiHuntErrors.length,
                          };
                        }),
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

  readonly selectedHuntError$: Observable<ApiHuntError|null> =
      combineLatest([this.huntErrors$, this.selectedHuntResultId$])
          .pipe(
              map(([errorState, resultId]) => getSelectedData(
                      resultId, errorState, errorState.errors,
                      this.loadMoreResults)));

  /**
   * An effect requesting to update the hunt state.
   */
  readonly patchHunt = this.effect<
      {state?: HuntState, clientLimit?: bigint, clientRate?: number}>(
      obs$ => obs$.pipe(
          withLatestFrom(this.state$),
          switchMap(
              ([patch, storeState]) => trackRequest(
                  this.httpApiService.patchHunt(storeState.huntId ?? '', patch)
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
  constructor(
      private readonly httpApiService: HttpApiService,
      private readonly configGlobalStore: ConfigGlobalStore,
  ) {}

  private readonly store = new HuntPageComponentStore(
      this.httpApiService,
      this.configGlobalStore,
  );

  /** Selects a hunt with a given id. */
  selectHunt(huntId: string): void {
    this.store.selectHunt(huntId);
  }

  readonly selectedHuntId$ = this.store.selectedHuntId$;
  readonly selectedHunt$ = this.store.selectedHunt$;

  readonly selectedHuntResultId$ = this.store.selectedHuntResultId$;
  readonly selectedHuntResult$ = this.store.selectedHuntResult$;
  readonly selectedHuntError$ = this.store.selectedHuntError$;
  readonly selectedResultFlowWithDescriptor$ =
      this.store.selectedResultFlowWithDescriptor$;
  readonly huntProgress$ = this.store.huntProgress$;

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

  cancelHunt() {
    this.store.patchHunt({state: HuntState.CANCELLED});
  }

  startHunt() {
    this.store.patchHunt({state: HuntState.RUNNING});
  }

  modifyAndStartHunt(params: {clientLimit: bigint, clientRate: number}) {
    this.store.patchHunt({...params, state: HuntState.RUNNING});
  }
}
