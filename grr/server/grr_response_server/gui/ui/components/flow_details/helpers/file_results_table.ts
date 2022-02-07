

import{
  AfterViewInit,
  ChangeDetectionStrategy,
  Component,
  EventEmitter,
  Input,
  Output,
  OnDestroy,
  ViewChild
} from '@angular/core';
import {MatSort} from '@angular/material/sort';
import {ActivatedRoute} from '@angular/router';
import {BehaviorSubject, combineLatest, Observable} from 'rxjs';
import {MatTableDataSource} from '@angular/material/table';
import {map, startWith, takeUntil} from 'rxjs/operators';
import {observeOnDestroy} from '../../../lib/reactive';

import {HexHash} from '../../../lib/models/flow';
import {StatEntry} from '../../../lib/models/vfs';

/**
 * FlowFileResult represents a single result to be displayed in the file
 * results table.
 */
export declare interface FlowFileResult {
  readonly statEntry: StatEntry;
  readonly hashes?: HexHash;
  readonly status?: string;
}

/**
 * To make the file results component more generic and easier to reuse,
 * it accepts entries of type FlowFileResult, defined above. For convenience,
 * a StatEntry->FlowFileResult conversion function is provided.
 */
export function flowFileResultFromStatEntry(
    statEntry: StatEntry, hashes?: HexHash, status?: string): FlowFileResult {
  return {
    statEntry,
    hashes,
    status,
  };
}

/**
 * TableRow represents a row containing file details to be displayed in the
 * file results table component.
 */
export declare interface TableRow {
  readonly path: string;
  readonly hashes?: HexHash;
  readonly mode?: bigint;
  readonly uid?: number;
  readonly gid?: number;
  readonly size?: bigint;
  readonly atime?: Date;
  readonly mtime?: Date;
  readonly ctime?: Date;
  readonly btime?: Date;
  readonly link: ReadonlyArray<string|undefined>;
  readonly status?: string;
}

const BASE_COLUMNS: ReadonlyArray<string> = [
  'ficon',
  'path',
  'mode',
  'size',
  'atime',
  'mtime',
  'ctime',
  'btime',
  'link',
];

/**
 * Component that displays a file table.
 */
@Component({
  selector: 'file-results-table',
  templateUrl: './file_results_table.ng.html',
  styleUrls: ['./file_results_table.scss'],
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class FileResultsTable implements OnDestroy, AfterViewInit {
  /** Subject corresponding to "results" binding. */
  readonly results$ = new BehaviorSubject<ReadonlyArray<FlowFileResult>>([]);

  /** Subject corresponding to "totalCount" binding. */
  readonly totalCount$ = new BehaviorSubject<number>(0);

  /** Subject the current dataSource.data length. */
  readonly dataLength$ = new BehaviorSubject<number>(0);

  /** Subject corresponding to "displayedColumns" binding. */
  readonly displayedColumns$ = this.results$.pipe(
      map(results => {
        const columns = [...BASE_COLUMNS];
        if (results.some(
                result =>
                    result.hashes && Object.keys(result.hashes).length > 0)) {
          columns.splice(2, 0, 'hashes');
        }
        if (results.some(result => result.status)) {
          columns.splice(2, 0, 'status');
        }
        return columns;
      }),
      startWith(BASE_COLUMNS),
  );

  @ViewChild(MatSort) sort!: MatSort;

  /** dataSource used as input for mat-table. */
  readonly dataSource = new MatTableDataSource<TableRow>();
  /** Subject producting table rows data provided to dataSource. */
  readonly rows$: Observable<ReadonlyArray<TableRow>> =
      this.results$.pipe(map((entries) => {
        return entries.map((e) => {
          return {
            path: e.statEntry.pathspec?.path ?? '',
            hashes: e.hashes,
            mode: e.statEntry.stMode,  // formatting will be handled by the pipe
            uid: e.statEntry.stUid,
            gid: e.statEntry.stGid,
            size: e.statEntry.stSize,
            atime: e.statEntry.stAtime,
            mtime: e.statEntry.stMtime,
            ctime: e.statEntry.stCtime,
            btime: e.statEntry.stBtime,
            link: [
              'files', e.statEntry.pathspec?.pathtype?.toLowerCase(),
              e.statEntry.pathspec?.path
            ],
            status: e.status,
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
  set results(value: ReadonlyArray<FlowFileResult>|null) {
    this.results$.next(value ?? []);
  }

  get results(): ReadonlyArray<FlowFileResult> {
    return this.results$.value;
  }

  @Input()
  set totalCount(value: number|null|undefined) {
    this.totalCount$.next(value ?? 0);
  }

  get totalCount(): number {
    return this.totalCount$.value;
  }

  @Output() readonly loadMore = new EventEmitter<void>();

  readonly ngOnDestroy = observeOnDestroy(this);

  constructor(readonly activatedRoute: ActivatedRoute) {
    this.rows$.pipe(takeUntil(this.ngOnDestroy.triggered$))
        .subscribe(results => {
          this.dataSource.data = results as TableRow[];
          this.dataLength$.next(this.dataSource.data.length);
        });
  }

  ngAfterViewInit() {
    this.dataSource.sort = this.sort;
  }

  loadMoreClicked() {
    this.loadMore.emit();
  }

  trackByRowIndex(index: number, item: TableRow) {
    return index;
  }
}
