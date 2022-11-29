import {Injectable, OnDestroy} from '@angular/core';
import {ComponentStore} from '@ngrx/component-store';
import {merge, Observable} from 'rxjs';
import {distinctUntilChanged, filter, shareReplay, switchMap, take, tap, withLatestFrom} from 'rxjs/operators';

import {HttpApiService} from '../lib/api/http_api_service';
import {observeOnDestroy} from '../lib/reactive';


// Dependency injection in constructor seems to not work without @Injectable()
// annotation.
/** A Store that loads data from the API. */
@Injectable()
export abstract class ApiStore<Result, Args extends {} = {}> {
  constructor(protected readonly httpApiService: HttpApiService) {}

  protected readonly store = new ComponentStore<Args>();

  setArgs(args: Args) {
    this.store.setState(args);
  }

  patchArgs(args: Partial<Args>) {
    this.store.patchState(args);
  }

  abstract loadResults(args: Args): Observable<Result>;

  results$: Observable<Result> = this.store.state$.pipe(
      switchMap(args => this.loadResults(args)),
      shareReplay({bufferSize: 1, refCount: true}),
  );
}

interface CollectionStoreState<R, A> {
  readonly args: A;
  readonly results: readonly R[];
  readonly isLoading: boolean;
  readonly totalLoadingCount: number;
}

/** Arguments for Pagination. */
export interface PaginationArgs {
  count: number;
  offset: number;
}

/** A Store that loads a collection of items from the API. */
@Injectable()
export abstract class ApiCollectionStore<Result, Args extends {} = {}>
    implements OnDestroy {
  constructor(protected readonly httpApiService: HttpApiService) {}

  readonly ngOnDestroy = observeOnDestroy(this);

  protected readonly store =
      new ComponentStore<CollectionStoreState<Result, Args>>();

  setArgs(args: Args) {
    this.store.setState({
      args,
      results: [],
      isLoading: true,
      totalLoadingCount: this.INITIAL_LOAD_COUNT,
    });
  }

  readonly loadMore = this.store.effect<number|undefined>(
      (obs$) => obs$.pipe(
          withLatestFrom(this.store.state$),
          // Turn loadMore() calls into no-nop if we're already loading results.
          filter(([, state]) => !state.isLoading),
          tap(([count, {results}]) => {
            this.store.patchState({
              isLoading: true,
              totalLoadingCount:
                  results.length + (count ?? this.INITIAL_LOAD_COUNT),
            });
          }),
          switchMap(
              ([count, state]) => this.loadResults(state.args, {
                                        count: count ?? this.INITIAL_LOAD_COUNT,
                                        offset: state.results.length
                                      })
                                      .pipe(take(1))),
          tap(results => {
            this.store.patchState(
                state => ({
                  isLoading: false,
                  results: this.mergeResults(state.results, results)
                }));
          }),
          ));

  /**
   * Loads an array of results from the API.
   *
   * loadResults() is called upon subscription to `results$` after
   * setArgs() has been called at least once. If your API does not take
   * any arguments, you can call setArgs({}). You can access
   * `this.httpApiService` to easily query the API. If your returned
   * Observable emits multiple arrays (e.g. from periodic polling) all
   * results will be merged.
   *
   * loadResults() is also called upon loadMore() calls. After the first
   * emitted result array, the Observable is unsubscribed to prevent
   * concurrent polling for different pages.
   */
  protected abstract loadResults(args: Args, paginationArgs: PaginationArgs):
      Observable<ReadonlyArray<Result>>;

  /**
   * Compares two result items for ordering of the results$ array.
   *
   * E.g. to have items ordered by date descending in the results$
   * array:
   *
   * ```
   *   protected readonly compareItems =
   *     compareDateNewestFirst<Hunt>(hunt => hunt.created)
   * ```
   */
  protected abstract compareItems(a: Result, b: Result): number;

  /**
   * Checks if two items are equal to only show unique items in
   * results$.
   */
  protected abstract areItemsEqual(a: Result, b: Result): boolean;

  protected areArgsEqual(a: Args, b: Args): boolean {
    return a === b;
  }

  readonly INITIAL_LOAD_COUNT: number = 50;

  private mergeResults(existing: readonly Result[], added: readonly Result[]) {
    return [...existing, ...added]
        .sort((a, b) => this.compareItems(a, b))
        .filter((item, i, items) => this.keepItem(items, i));
  }

  /**
   * Returns true if `item` should be kept in the results array.
   *
   * The default implementation returns true if `item` is unique, by
   * comparing it with `areItemsEqual` to all preceding items that are
   * have the same order determined by `compareItems`.
   *
   * Edge case: items that are deleted from the backend are still kept
   * in this store until the page is reloaded.
   */
  protected keepItem(items: Result[], itemIndex: number) {
    const currentItem = items[itemIndex];
    // Compare the current item with items preceding it.
    for (let i = itemIndex - 1; i >= 0; i--) {
      const precedingItem = items[i];
      if (this.compareItems(precedingItem, currentItem) !== 0) {
        // If the preceding item has a different order index and no
        // equal item has been found yet, the current item is unique.
        return true;
      } else if (this.areItemsEqual(precedingItem, currentItem)) {
        // If the preceding item has the same order index and is equal,
        // the current item is not unique and should not be included in
        // the array!
        return false;
      }
    }
    return true;
  }

  private readonly latestResultsEffect$ =
      this.store.select(state => state.args)
          .pipe(
              tap(() => {
                this.store.patchState({isLoading: true});
              }),
              switchMap(
                  args => this.loadResults(
                      args, {count: this.INITIAL_LOAD_COUNT, offset: 0})),
              tap(results => {
                this.store.patchState(
                    state => ({
                      isLoading: false,
                      results: this.mergeResults(results, state.results)
                    }));
              }),
              filter(() => false),
          );

  readonly results$: Observable<readonly Result[]> =
      merge(
          this.store.select(state => state.results),
          this.latestResultsEffect$,
          )
          .pipe(
              distinctUntilChanged(),

          );

  readonly isLoading$: Observable<boolean> =
      this.store.select(state => state.isLoading);

  readonly hasMore$ = this.store.select(
      state => state.totalLoadingCount <= state.results.length);
}
