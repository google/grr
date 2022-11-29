import {KeyValue} from '@angular/common';
import {ChangeDetectionStrategy, Component, OnDestroy} from '@angular/core';
import {MatTableDataSource} from '@angular/material/table';
import {combineLatest, Observable} from 'rxjs';
import {map, startWith} from 'rxjs/operators';

import {ApiHuntError} from '../../../../lib/api/api_interfaces';
import {orderApiHuntResultColumns, PAYLOAD_TYPE_TRANSLATION, toHuntResultRow} from '../../../../lib/api_translation/result';
import {CellComponent, ColumnDescriptor} from '../../../../lib/models/result';
import {isNull} from '../../../../lib/preconditions';
import {observeOnDestroy} from '../../../../lib/reactive';
import {HuntPageGlobalStore} from '../../../../store/hunt_page_global_store';

/** Describes for a particular PayloadType, its render information. */
declare interface ResultsDescriptor {
  tabName?: string;
  columns: {[key: string]: ColumnDescriptor};
  displayedColumns?: string[];
  dataSource: MatTableDataSource<{[key: string]: unknown}>;
}

enum LoadMoreState {
  LOADING,
  HAS_MORE,
  ALL_LOADED,
}

declare interface ItemState {
  isLoading?: boolean;
  hasMore?: boolean;
}

function getLoadMoreState(state: ItemState): LoadMoreState {
  if (state.isLoading || state.hasMore === undefined) {
    return LoadMoreState.LOADING;
  } else if (state.hasMore) {
    return LoadMoreState.HAS_MORE;
  } else {
    return LoadMoreState.ALL_LOADED;
  }
}

/**
 * Provides the forms for new hunt configuration.
 */
@Component({
  selector: 'app-hunt-results',
  templateUrl: './hunt_results.ng.html',
  styleUrls: ['./hunt_results.scss'],
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class HuntResults implements OnDestroy {
  readonly CellComponent = CellComponent;

  readonly ngOnDestroy = observeOnDestroy(this);

  constructor(
      private readonly huntPageGlobalStore: HuntPageGlobalStore,
  ) {
    huntPageGlobalStore.loadMoreResults();
    huntPageGlobalStore.loadMoreErrors();
  }

  readonly LoadMoreState = LoadMoreState;

  readonly resultsLoadMoreState$ =
      this.huntPageGlobalStore.huntResults$.pipe(map(getLoadMoreState));
  readonly errorsLoadMoreState$ =
      this.huntPageGlobalStore.huntErrors$.pipe(map(getLoadMoreState));

  // Maps payloadType to dataSource and columns.
  readonly resultsMap$: Observable<{[key: string]: ResultsDescriptor}|null> =
      combineLatest([
        this.huntPageGlobalStore.selectedHuntId$,
        this.huntPageGlobalStore.huntResults$
      ]).pipe(map(([huntId, state]) => {
        if (isNull(state?.results) || Object.keys(state.results).length === 0) {
          return null;
        }
        // TODO: persist `res` and dataSources in HuntResults,
        // refreshing only the `data` attribute on subscription.
        const res: {[key: string]: ResultsDescriptor} = {};

        for (const [, result] of Object.entries(state.results)) {
          const pt =
              result.payloadType as keyof typeof PAYLOAD_TYPE_TRANSLATION;
          const curTab = PAYLOAD_TYPE_TRANSLATION[pt]?.tabName ?? pt;

          // Start with default values for all ApiHuntResults.
          if (!res[curTab]) {
            res[curTab] = {
              // `columns` type will always be "the sum" of all possible
              // columns in PAYLOAD_TYPE_TRANSLATION values. Since we want to
              // define them as constants, typescript is not picking up that
              // they're all strings. Creating yet another type abstraction
              // layer will make this code even harder to read, so we're keeping
              // ResultsDescriptor.columns keys as string for simplicity.
              // tslint:disable-next-line:quoted-properties-on-dictionary
              columns: {...PAYLOAD_TYPE_TRANSLATION['ApiHuntResult'].columns},
              dataSource: new MatTableDataSource(),
              tabName: curTab,
            };
          }
          // Start with basic fields for every ApiHuntResult
          const row: {[key: string]: unknown} =
              toHuntResultRow(result, huntId ?? '');

          // Now add complementary information if we have it (based on
          // type).
          if (PAYLOAD_TYPE_TRANSLATION[pt]) {
            res[curTab].columns = {
              ...res[curTab].columns,
              ...PAYLOAD_TYPE_TRANSLATION[pt].columns
            };
            if (PAYLOAD_TYPE_TRANSLATION[pt].tabName) {
              res[curTab].tabName = PAYLOAD_TYPE_TRANSLATION[pt].tabName;
            }

            const translateFunc = PAYLOAD_TYPE_TRANSLATION[pt].translateFn;
            const trans = translateFunc(result.payload);
            for (const [key, value] of Object.entries(trans)) {
              row[key] = value;
            }
          }

          // Update tab data
          res[curTab].dataSource.data.push(row);
          res[curTab].displayedColumns =
              orderApiHuntResultColumns(res[curTab].columns);
        }

        return res;
      }));

  readonly displayErrorColumns =
      ['clientId', 'collectedAt', 'logMessage', 'backtrace'];
  readonly errorsDataSource$:
      Observable<MatTableDataSource<ApiHuntError>|null> =
          this.huntPageGlobalStore.huntErrors$.pipe(map(state => {
            if (isNull(state?.errors) || state.errors.length === 0) return null;
            const errorData: ApiHuntError[] = [];
            const errorDataSource = new MatTableDataSource(errorData);
            errorDataSource.data = state.errors as ApiHuntError[];
            return errorDataSource;
          }));

  readonly loadedResultsDesc$ = combineLatest([
                                  this.huntPageGlobalStore.huntResults$.pipe(
                                      map(state => state?.loadedCount)),
                                  this.huntPageGlobalStore.selectedHunt$.pipe(
                                      map((hunt) => hunt?.resultsCount))
                                ]).pipe(map(([loaded, resultsCount]) => {
    if (isNull(loaded) || isNull(resultsCount)) {
      return '';
    }
    // Sometimes the reported resultsCount in the ApiHunt is smaller than the
    // slice received in the store. Thus, we get the highest one to present.
    const total = Math.max(loaded ?? 0, Number(resultsCount) ?? 0);
    return `(displaying ${loaded} out of ${total})`;
  }));

  readonly allLoading$ =
      combineLatest([
        this.huntPageGlobalStore.huntResults$.pipe(
            map(state => state.isLoading), startWith(true)),
        this.huntPageGlobalStore.huntErrors$.pipe(
            map(state => state.isLoading), startWith(true))
      ]).pipe(map(([loadingResults,
                    loadingErrors]) => loadingResults && loadingErrors));

  trackByIndex(index: number) {
    return index;
  }

  trackByKey(index: number, pair: KeyValue<string, ColumnDescriptor>) {
    return pair.key;
  }

  loadMoreResults() {
    this.huntPageGlobalStore.loadMoreResults();
  }
  loadMoreErrors() {
    this.huntPageGlobalStore.loadMoreErrors();
  }
}
