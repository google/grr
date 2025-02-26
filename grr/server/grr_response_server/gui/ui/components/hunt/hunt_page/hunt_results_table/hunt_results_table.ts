import {CommonModule, KeyValue} from '@angular/common';
import {
  ChangeDetectionStrategy,
  Component,
  EventEmitter,
  Input,
  OnChanges,
  OnDestroy,
  Output,
  SimpleChanges,
} from '@angular/core';
import {MatButtonModule} from '@angular/material/button';
import {MatIconModule} from '@angular/material/icon';
import {MatProgressSpinnerModule} from '@angular/material/progress-spinner';
import {MatTableDataSource, MatTableModule} from '@angular/material/table';
import {distinctUntilChanged, map, takeUntil} from 'rxjs/operators';

import {ApiHuntResult} from '../../../../lib/api/api_interfaces';
import {
  HUNT_RESULT_COLUMNS,
  orderApiHuntResultColumns,
  PAYLOAD_TYPE_TRANSLATION,
  toHuntResultRow,
} from '../../../../lib/api_translation/result';
import {
  CellComponent,
  CellData,
  ColumnDescriptor,
  HuntResultOrError,
  PayloadType,
} from '../../../../lib/models/result';
import {isNonNull} from '../../../../lib/preconditions';
import {observeOnDestroy} from '../../../../lib/reactive';
import {HuntResultsLocalStore} from '../../../../store/hunt_results_local_store';
import {FileModeModule} from '../../../data_renderers/file_mode/file_mode_module';
import {ExpandableHashModule} from '../../../expandable_hash/module';
import {HelpersModule} from '../../../flow_details/helpers/module';
import {CopyButtonModule} from '../../../helpers/copy_button/copy_button_module';
import {FilterPaginate} from '../../../helpers/filter_paginate/filter_paginate';
import {HumanReadableSizeModule} from '../../../human_readable_size/module';
import {TimestampModule} from '../../../timestamp/module';
import {UserImageModule} from '../../../user_image/module';

declare interface ResultTableRow<T extends HuntResultOrError> {
  resultOrError: T;
  rowData: CellData<{[key: string]: ColumnDescriptor}>;
}

function hasInputChanged(inputKey: string, changes: SimpleChanges): boolean {
  const change = changes[inputKey];

  if (!change) return false;

  return change.currentValue !== change.previousValue;
}

/** Number of results to fetch per request by default. */
export const RESULTS_BATCH_SIZE = 50;

const NO_MORE_ITEMS_TO_LOAD_TEXT = 'Nothing more to load';

/**
 * Shows a table with Hunt Results of a certain type (payloadType).
 */
@Component({
  selector: 'app-hunt-results-table',
  templateUrl: './hunt_results_table.ng.html',
  styleUrls: ['./hunt_results_table.scss'],
  changeDetection: ChangeDetectionStrategy.OnPush,
  standalone: true,
  imports: [
    CommonModule,
    MatButtonModule,
    MatIconModule,
    MatProgressSpinnerModule,
    MatTableModule,

    CopyButtonModule,
    ExpandableHashModule,
    FileModeModule,
    FilterPaginate,
    HelpersModule,
    HumanReadableSizeModule,
    TimestampModule,
    UserImageModule,
  ],
  providers: [HuntResultsLocalStore],
})
export class HuntResultsTable<T extends HuntResultOrError>
  implements OnChanges, OnDestroy
{
  @Input() huntId: string | undefined;
  @Input() totalResultsCount = 0;
  @Input() resultType: PayloadType | undefined;

  translateHuntResultFn:
    | ((...args: unknown[]) => CellData<{[key: string]: ColumnDescriptor}>)
    | undefined;
  translateHuntErrorFn =
    PAYLOAD_TYPE_TRANSLATION[PayloadType.API_HUNT_ERROR]!.translateFn;

  @Output() readonly selectedHuntResult = new EventEmitter<T>();

  get hasMore(): boolean {
    if (!this.totalResultsCount) return false;

    return this.totalResultsCount > this.dataSource.data.length;
  }

  get loadedResultsSubtitle(): string {
    // We cover against the case when the loaded results is higher than the
    // "totalResultsCount" given by the parent component. This should never
    // happen but we want to avoid showing "Displaying 20 of 10 results".
    const totalResults = Math.max(
      this.totalResultsCount,
      this.dataSource.data.length,
    );

    return `(displaying ${this.dataSource.data.length} out of ${totalResults} results)`;
  }

  get showTable(): boolean {
    return this.totalResultsCount > 0 && isNonNull(this.huntId);
  }

  columnDescriptors: {[key: string]: ColumnDescriptor} = {};
  orderedColumnKeys: string[] = [];
  /**
   * We automatically load up to "RESULT_BATCH_SIZE" results without requiring
   * user input.
   */
  private readonly automaticallyLoadUpTo = RESULTS_BATCH_SIZE;

  numberOfItemsToLoad = 0;
  loadMoreButtonText = NO_MORE_ITEMS_TO_LOAD_TEXT;

  readonly CellComponent = CellComponent;
  readonly dataSource = new MatTableDataSource<ResultTableRow<T>>();
  readonly isLoading$;
  readonly ngOnDestroy;

  constructor(
    private readonly huntResultsLocalStore: HuntResultsLocalStore<T>,
  ) {
    this.isLoading$ = this.huntResultsLocalStore.isLoading$;
    this.ngOnDestroy = observeOnDestroy(this);
    this.huntResultsLocalStore.results$
      .pipe(
        distinctUntilChanged(),
        map((results) =>
          results.map(
            (result): ResultTableRow<T> => ({
              resultOrError: result,
              rowData: this.toRowData(result),
            }),
          ),
        ),
        takeUntil(this.ngOnDestroy.triggered$),
      )
      .subscribe((translatedResults) => {
        this.dataSource.data = translatedResults;
        this.recalculateItemsToLoad();
        this.updateLoadMoreButtonText();
      });
  }

  ngOnChanges(changes: SimpleChanges) {
    const hasResultTypeChanged = hasInputChanged('resultType', changes);
    const hasHuntIdChanged = hasInputChanged('huntId', changes);
    const hasTotalCountChanged = hasInputChanged('totalResultsCount', changes);

    if (hasResultTypeChanged) {
      this.setTableColumns(this.resultType);
      this.setHuntResultTranslationFunction(this.resultType);
    }

    if (hasHuntIdChanged || hasResultTypeChanged) {
      this.resetTable();
    } else if (
      hasTotalCountChanged &&
      isNonNull(this.totalResultsCount) &&
      this.automaticallyLoadUpTo > this.dataSource.data.length &&
      this.totalResultsCount > this.dataSource.data.length
    ) {
      this.recalculateItemsToLoad();
      this.updateLoadMoreButtonText();
      this.loadMoreResults();
    }
  }

  loadMoreResults(): void {
    if (this.numberOfItemsToLoad > 0) {
      this.huntResultsLocalStore.loadMore(this.numberOfItemsToLoad);
    }
  }

  trackByIndex(index: number) {
    return index;
  }

  trackByKey(index: number, pair: KeyValue<string, ColumnDescriptor>) {
    return pair.key;
  }

  viewResultDetails(resultOrError: T): void {
    this.selectedHuntResult.emit(resultOrError);
  }

  private toRowData(resultOrError: T): ResultTableRow<T>['rowData'] {
    if (this.resultType === PayloadType.API_HUNT_ERROR) {
      return this.translateHuntErrorFn(resultOrError, this.huntId!);
    }

    // if Result is not an ApiHuntError, then it is an ApiHuntResult

    const translatedResult: ResultTableRow<T>['rowData'] = toHuntResultRow(
      resultOrError as ApiHuntResult,
      this.huntId!,
    );

    if (!this.translateHuntResultFn) return translatedResult;

    return {
      ...translatedResult,
      ...this.translateHuntResultFn((resultOrError as ApiHuntResult).payload),
    };
  }

  private setTableColumns(payloadType: PayloadType | undefined): void {
    const safePayloadType = payloadType || PayloadType.API_HUNT_RESULT;
    const payloadTypeTranslation = PAYLOAD_TYPE_TRANSLATION[safePayloadType];

    let columns = HUNT_RESULT_COLUMNS;

    if (isNonNull(payloadTypeTranslation)) {
      columns = {
        ...HUNT_RESULT_COLUMNS,
        ...payloadTypeTranslation.columns,
      };
    }

    this.columnDescriptors = columns;
    this.orderedColumnKeys = orderApiHuntResultColumns(columns);
  }

  private setHuntResultTranslationFunction(pt: PayloadType | undefined): void {
    if (isNonNull(pt)) {
      this.translateHuntResultFn = PAYLOAD_TYPE_TRANSLATION[pt]?.translateFn;

      return;
    }

    this.translateHuntResultFn = undefined;
  }

  private recalculateItemsToLoad(): void {
    const difference = this.totalResultsCount - this.dataSource.data.length;

    this.numberOfItemsToLoad =
      difference > 0 ? Math.min(difference, RESULTS_BATCH_SIZE) : 0;
  }

  private updateLoadMoreButtonText(): void {
    this.loadMoreButtonText =
      this.numberOfItemsToLoad > 0
        ? `Load ${this.numberOfItemsToLoad} more`
        : NO_MORE_ITEMS_TO_LOAD_TEXT;
  }

  private resetTable(): void {
    this.dataSource.data = [];

    this.recalculateItemsToLoad();
    this.updateLoadMoreButtonText();

    this.huntResultsLocalStore.setArgs({
      huntId: this.huntId,
      withType: this.resultType,
    });
  }
}
