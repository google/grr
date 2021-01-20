

import {ChangeDetectionStrategy, Component, EventEmitter, Input, Output} from '@angular/core';
import {StatEntry} from '@app/lib/api/api_interfaces';
import {createOptionalDateSeconds} from '@app/lib/api_translation/primitive';
import {combineLatest, Observable, ReplaySubject} from 'rxjs';
import {map} from 'rxjs/operators';
import {HexHash} from '../../../lib/models/flow';

/**
 * FlowFileResult represents a single result to be displayed in the file
 * results table.
 */
export declare interface FlowFileResult {
  readonly statEntry: StatEntry;
  readonly hashes: HexHash;
}

/**
 * To make the file results component more generic and easier to reuse,
 * it accepts entries of type FlowFileResult, defined above. For convenience,
 * a StatEntry->FlowFileResult conversion function is provided.
 */
export function flowFileResultFromStatEntry(
    statEntry: StatEntry, hashes: HexHash = {}): FlowFileResult {
  return {
    statEntry,
    hashes,
  };
}

declare interface TableRow {
  readonly path: string;
  readonly hashes: HexHash;
  readonly mode?: string;
  readonly uid: string;
  readonly gid: string;
  readonly size: string;
  readonly atime?: Date;
  readonly mtime?: Date;
  readonly ctime?: Date;
  readonly btime?: Date;
}


/**
 * Component that displays a file table.
 */
@Component({
  selector: 'file-results-table',
  templateUrl: './file_results_table.ng.html',
  styleUrls: ['./file_results_table.scss'],
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class FileResultsTable {
  private resultsValue?: ReadonlyArray<FlowFileResult>;
  private totalCountValue?: number;

  /** Subject corresponding to "results" binding. */
  results$ = new ReplaySubject<ReadonlyArray<FlowFileResult>>(1);

  /** Subject corresponding to "totalCount" binding. */
  totalCount$ = new ReplaySubject<number>(1);

  /**
   * Subject producting table rows.
   */
  rows$: Observable<ReadonlyArray<TableRow>> =
      this.results$.pipe(map((entries) => {
        return entries.map((e) => {
          return {
            path: e.statEntry.pathspec?.path ?? '',
            hashes: e.hashes,
            mode: e.statEntry.stMode,  // formatting will be handled by the pipe
            uid: e.statEntry.stUid?.toString() ?? '',
            gid: e.statEntry.stGid?.toString() ?? '',
            size: e.statEntry.stSize?.toString() ?? '',
            atime: createOptionalDateSeconds(e.statEntry.stAtime),
            mtime: createOptionalDateSeconds(e.statEntry.stMtime),
            ctime: createOptionalDateSeconds(e.statEntry.stCtime),
            btime: createOptionalDateSeconds(e.statEntry.stCrtime),
          };
        });
      }));

  /**
   * Subject indicating whether a "Load more" button has to be shown.
   */
  shouldShowLoadMoreButton$: Observable<boolean> =
      combineLatest([
        this.results$, this.totalCount$
      ]).pipe(map(([results, count]) => results.length < count));

  @Input()
  set results(value: ReadonlyArray<FlowFileResult>) {
    this.resultsValue = value;
    this.results$.next(value);
  }

  get results(): ReadonlyArray<FlowFileResult> {
    return this.resultsValue!;
  }

  @Input()
  set totalCount(value: number) {
    this.totalCountValue = value;
    this.totalCount$.next(value);
  }

  get totalCount(): number {
    return this.totalCountValue!;
  }

  @Output() readonly loadMore = new EventEmitter<void>();

  loadMoreClicked() {
    this.loadMore.emit();
  }


  trackByRowIndex(index: number, item: TableRow) {
    return index;
  }
}
