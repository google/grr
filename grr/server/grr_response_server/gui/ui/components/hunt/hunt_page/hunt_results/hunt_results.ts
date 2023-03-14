import {Clipboard} from '@angular/cdk/clipboard';
import {KeyValue} from '@angular/common';
import {ChangeDetectionStrategy, Component, OnDestroy} from '@angular/core';
import {MatTableDataSource} from '@angular/material/table';
import {combineLatest, Observable} from 'rxjs';
import {filter, map, startWith, takeUntil} from 'rxjs/operators';

import {ExportMenuItem} from '../../../../components/flow_details/plugins/plugin';
import {ApiHuntError, ApiHuntResult} from '../../../../lib/api/api_interfaces';
import {getHuntExportedResultsCsvUrl, getHuntExportedResultsSqliteUrl, getHuntExportedResultsYamlUrl, getHuntFilesArchiveTarGzUrl, getHuntFilesArchiveZipUrl} from '../../../../lib/api/http_api_service';
import {ERROR_TAB, orderApiHuntResultColumns, PAYLOAD_TYPE_TRANSLATION, PayloadType, toHuntResultRow} from '../../../../lib/api_translation/result';
import {CellComponent, ColumnDescriptor} from '../../../../lib/models/result';
import {isNonNull, isNull} from '../../../../lib/preconditions';
import {observeOnDestroy} from '../../../../lib/reactive';
import {HuntPageGlobalStore} from '../../../../store/hunt_page_global_store';

/** Describes for a particular PayloadType, its render information. */
export declare interface ResultsDescriptor {
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

function fillWithResults(
    res: {[key: string]: ResultsDescriptor}, huntId: string,
    results: {[key: string]: ApiHuntResult}) {
  for (const [, result] of Object.entries(results)) {
    const pt = result.payloadType as keyof typeof PAYLOAD_TYPE_TRANSLATION;
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
        columns:
            {...PAYLOAD_TYPE_TRANSLATION[PayloadType.API_HUNT_RESULT].columns},
        dataSource: new MatTableDataSource(),
        tabName: curTab,
      };
    }
    // Start with basic fields for every ApiHuntResult
    const row: {[key: string]: unknown} = toHuntResultRow(result, huntId);

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
}

function fillWithErrors(
    res: {[key: string]: ResultsDescriptor}, huntId: string,
    errors: {[key: string]: ApiHuntError}) {
  const pt = PayloadType.API_HUNT_ERROR;
  const tab = PAYLOAD_TYPE_TRANSLATION[pt].tabName;
  const columns = PAYLOAD_TYPE_TRANSLATION[pt].columns;
  const translateFn = PAYLOAD_TYPE_TRANSLATION[pt].translateFn;

  if (!res[tab]) {
    res[tab] = {
      columns: {...columns},
      dataSource: new MatTableDataSource(),
      tabName: tab,
    };
  }

  for (const [, error] of Object.entries(errors)) {
    const row: {[key: string]: unknown} = translateFn(error, huntId);
    // Update tab data
    res[tab].dataSource.data.push(row);
  }

  res[tab].displayedColumns = orderApiHuntResultColumns(res[tab].columns);
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
  readonly ERROR_TAB = ERROR_TAB;

  readonly ngOnDestroy = observeOnDestroy(this);

  private huntId = '';
  protected copied = false;

  constructor(
      private readonly huntPageGlobalStore: HuntPageGlobalStore,
      private readonly clipboard: Clipboard,
  ) {
    huntPageGlobalStore.loadMoreResults();
    huntPageGlobalStore.loadMoreErrors();
    huntPageGlobalStore.selectedHuntId$
        .pipe(
            takeUntil(this.ngOnDestroy.triggered$),
            filter(isNonNull),
            )
        .subscribe(id => {
          this.huntId = id;
        });
  }

  readonly LoadMoreState = LoadMoreState;

  readonly resultsLoadMoreState$ = this.huntPageGlobalStore.huntResults$.pipe(
      map(getLoadMoreState), startWith(LoadMoreState.LOADING));
  readonly errorsLoadMoreState$ = this.huntPageGlobalStore.huntErrors$.pipe(
      map(getLoadMoreState), startWith(LoadMoreState.LOADING));
  readonly combinedLoadMoreState$ = combineLatest([
                                      this.resultsLoadMoreState$,
                                      this.errorsLoadMoreState$
                                    ]).pipe(map(([res, errs]) => {
    if (res === LoadMoreState.ALL_LOADED && errs === LoadMoreState.ALL_LOADED) {
      return LoadMoreState.ALL_LOADED;
    }
    if (res === LoadMoreState.LOADING || errs === LoadMoreState.LOADING) {
      return LoadMoreState.LOADING;
    }
    if (res === LoadMoreState.HAS_MORE || errs === LoadMoreState.HAS_MORE) {
      return LoadMoreState.HAS_MORE;
    }
    // Should be unreachable, all cases expliticly covered above.
    return LoadMoreState.HAS_MORE;
  }));

  // Maps payloadType to dataSource and columns.
  readonly resultsMap$: Observable<{[key: string]: ResultsDescriptor}|null> =
      combineLatest([
        this.huntPageGlobalStore.selectedHuntId$,
        this.huntPageGlobalStore.huntResults$.pipe(startWith(null)),
        this.huntPageGlobalStore.huntErrors$.pipe(startWith(null)),
      ]).pipe(map(([huntId, resState, errState]) => {
        if (!huntId) {
          return null;
        }
        // TODO: persist `res` and dataSources in HuntResults,
        // refreshing only the `data` attribute on subscription.
        const res: {[key: string]: ResultsDescriptor} = {};
        if (isNonNull(resState?.results) &&
            Object.keys(resState!.results).length > 0) {
          fillWithResults(res, huntId, resState!.results);
        }
        if (isNonNull(errState?.errors) &&
            Object.keys(errState!.errors).length > 0) {
          fillWithErrors(res, huntId, errState!.errors);
        }

        return Object.keys(res).length === 0 ? null : res;
      }));

  readonly loadedDesc$ =
      combineLatest([
        this.huntPageGlobalStore.huntResults$.pipe(
            map(state => state?.loadedCount)),
        this.huntPageGlobalStore.selectedHunt$.pipe(
            map((hunt) => hunt?.resultsCount)),
        this.huntPageGlobalStore.huntErrors$.pipe(
            map(state => state?.loadedCount)),
        this.huntPageGlobalStore.selectedHunt$.pipe(
            map((hunt) => (hunt?.failedClientsCount ?? BigInt(0)) +
                    (hunt?.crashedClientsCount ?? BigInt(0))))
      ]).pipe(map(([loadedRes, resultsCount, loadedErr, errorsCount]) => {
        if (isNull(loadedRes) || isNull(resultsCount) || isNull(loadedErr) ||
            isNull(errorsCount)) {
          return '';
        }
        // Sometimes the reported resultsCount in the ApiHunt is smaller than
        // the slice received in the store. Thus, we get the highest one to
        // present.
        const totalRes = Math.max(loadedRes ?? 0, Number(resultsCount) ?? 0);
        const totalErr = Math.max(loadedErr ?? 0, Number(errorsCount) ?? 0);
        return `(displaying ${loadedRes} out of ${totalRes} results, and ${
            loadedErr} out of ${totalErr} errors)`;
      }));

  readonly allLoading$ =
      combineLatest([
        this.huntPageGlobalStore.huntResults$.pipe(
            map(state => state.isLoading), startWith(true)),
        this.huntPageGlobalStore.huntErrors$.pipe(
            map(state => state.isLoading), startWith(true))
      ]).pipe(map(([loadingResults,
                    loadingErrors]) => loadingResults && loadingErrors));

  get exportMenuItems(): readonly ExportMenuItem[] {
    return [
      {
        title: 'Download files (TAR GZ)',
        url: getHuntFilesArchiveTarGzUrl(this.huntId),
        downloadName: `results_hunt_${this.huntId}.tar.gz`,
      },
      {
        title: 'Download files (ZIP)',
        url: getHuntFilesArchiveZipUrl(this.huntId),
        downloadName: `results_hunt_${this.huntId}.zip`,
      },
      {
        title: 'Download (CSV)',
        url: getHuntExportedResultsCsvUrl(this.huntId),
        downloadName: `hunt_${this.huntId}.csv.zip`,
      },
      {
        title: 'Download (YAML)',
        url: getHuntExportedResultsYamlUrl(this.huntId),
        downloadName: `hunt_${this.huntId}.yaml.zip`,
      },
      {
        title: 'Download (SQLite)',
        url: getHuntExportedResultsSqliteUrl(this.huntId),
        downloadName: `hunt_${this.huntId}.sql.zip`,
      },
    ];
  }

  exportCommand() {
    const cmd = `/usr/bin/grr_api_shell 'http://localhost:8081' --exec_code` +
        `'grrapi.Hunt("${this.huntId}").GetFilesArchive().WriteToFile(` +
        `"./hunt_results_${this.huntId}.zip")'`;
    this.copied = this.clipboard.copy(cmd);
  }

  trackByIndex(index: number) {
    return index;
  }
  trackByKey(index: number, pair: KeyValue<string, ColumnDescriptor>) {
    return pair.key;
  }
  trackExportMenuItem(index: number, entry: ExportMenuItem) {
    return entry.title;
  }

  loadMoreResults() {
    this.huntPageGlobalStore.loadMoreResults();
  }
  loadMoreErrors() {
    this.huntPageGlobalStore.loadMoreErrors();
  }
  loadMoreResultsAndErrors() {
    this.huntPageGlobalStore.loadMoreResults();
    this.huntPageGlobalStore.loadMoreErrors();
  }
}
