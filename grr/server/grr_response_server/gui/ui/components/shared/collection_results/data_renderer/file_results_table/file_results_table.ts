

import {LiveAnnouncer} from '@angular/cdk/a11y';
import {CommonModule} from '@angular/common';
import {
  AfterViewInit,
  ChangeDetectionStrategy,
  Component,
  computed,
  effect,
  inject,
  Injector,
  input,
  OnInit,
  runInInjectionContext,
  ViewChild,
} from '@angular/core';
import {MatButtonModule} from '@angular/material/button';
import {MatIconModule} from '@angular/material/icon';
import {MatProgressSpinnerModule} from '@angular/material/progress-spinner';
import {MatSort, MatSortModule, Sort} from '@angular/material/sort';
import {MatTableDataSource, MatTableModule} from '@angular/material/table';
import {MatTabsModule} from '@angular/material/tabs';
import {MatTooltipModule} from '@angular/material/tooltip';

import {HexHash} from '../../../../../lib/models/flow';
import {isSymlink, StatEntry} from '../../../../../lib/models/vfs';
import {HumanReadableByteSizePipe} from '../../../../../pipes/human_readable/human_readable_byte_size_pipe';
import {HumanReadableFileModePipe} from '../../../../../pipes/human_readable/human_readable_file_mode_pipe';
import {CopyButton} from '../../../copy_button';
import {ExpandableHash} from '../../../expandable_hash';
import {FilterPaginate} from '../../../filter_paginate';
import {Timestamp} from '../../../timestamp';
import {FileContent} from './file_content';

/**
 * FlowFileResult represents a single result to be displayed in the file
 * results table.
 */
export declare interface FlowFileResult {
  readonly clientId: string;
  readonly statEntry: StatEntry;
  readonly hashes?: HexHash;
  readonly status?: CollectionStatus;
  readonly isFile?: boolean;
  readonly isDirectory?: boolean;
}

/**
 * CollectionStatus represents the state of a collection with an optional message.
 */
export declare interface CollectionStatus {
  readonly state: CollectionState;
  readonly message?: string;
}

/**
 * StatusState represents the collection state of a file.
 */
export enum CollectionState {
  UNKNOWN = 0,
  IN_PROGRESS,
  SUCCESS,
  WARNING,
  ERROR,
}

const BASE_COLUMNS: readonly string[] = [
  'ficon',
  'path',
  'mode',
  'size',
  'atime',
  'mtime',
  'ctime',
  'btime',
  'details',
];

/**
 * Component that displays a file table.
 */
@Component({
  selector: 'file-results-table',
  templateUrl: './file_results_table.ng.html',
  styleUrls: ['./file_results_table.scss'],
  imports: [
    CommonModule,
    CopyButton,
    ExpandableHash,
    FileContent,
    FilterPaginate,
    HumanReadableByteSizePipe,
    HumanReadableFileModePipe,
    MatButtonModule,
    MatIconModule,
    MatProgressSpinnerModule,
    MatSortModule,
    MatTableModule,
    MatTabsModule,
    MatTooltipModule,
    Timestamp,
  ],
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class FileResultsTable implements AfterViewInit, OnInit {
  private readonly liveAnnouncer = inject(LiveAnnouncer);
  private readonly injector: Injector = inject(Injector);
  @ViewChild(MatSort) sort!: MatSort;

  protected readonly isSymlink = isSymlink;

  /** Loaded results to display in the table. */
  readonly results = input.required<readonly FlowFileResult[]>();
  readonly isHuntResult = input.required<boolean>();

  // tslint:disable-next-line:enforce-name-casing
  protected readonly CollectionState = CollectionState;

  readonly dataSource = new MatTableDataSource<FlowFileResult>();
  protected readonly displayedColumns = computed(() => {
    const columns = [...BASE_COLUMNS];
    const availableResults = this.results();

    if (this.isHuntResult()) {
      columns.splice(1, 0, 'clientId');
    }
    if (
      availableResults.some(
        (res) => res.hashes && Object.keys(res.hashes).length > 0,
      )
    ) {
      columns.splice(2, 0, 'hashes');
    }
    if (availableResults.some((res) => res.status)) {
      columns.splice(columns.length - 1, 0, 'status');
    }
    return columns;
  });

  ngOnInit() {
    runInInjectionContext(this.injector, () => {
      effect(() => {
        if (this.dataSource.data.length !== this.results().length) {
          this.dataSource.data = (this.results() ?? []).slice();
          return;
        }

        const currentPaths = this.dataSource.data
          .filter((entry) => entry.statEntry.pathspec !== undefined)
          .map((entry) => entry.statEntry.pathspec!.path)
          .sort((a, b) => {
            return a.localeCompare(b);
          });
        const newPaths = (this.results() ?? [])
          .filter((entry) => entry.statEntry.pathspec !== undefined)
          .map((entry) => entry.statEntry.pathspec!.path)
          .sort((a, b) => {
            return a.localeCompare(b);
          });

        const hasDifferentPaths = currentPaths
          .map((currentPath, i) => {
            const newPath = newPaths[i];
            return currentPath !== newPath;
          })
          .some((diff) => diff);

        if (hasDifferentPaths) {
          this.dataSource.data = (this.results() ?? []).slice();
        }
      });
    });
  }

  ngAfterViewInit() {
    this.dataSource.sort = this.sort;
    // Conversion from table column name to the data accessor, this is required
    // for sorting and filtering.
    this.dataSource.sortingDataAccessor = (item, property) => {
      if (property === 'ficon') {
        if (isSymlink(item.statEntry)) {
          return 'symlink';
        } else if (item.isDirectory) {
          return 'folder';
        } else if (item.isFile) {
          return 'file';
        } else {
          return '';
        }
      }
      if (property === 'clientId') {
        return item.clientId;
      }
      if (property === 'path') {
        return item.statEntry.pathspec?.path ?? '';
      }
      if (property === 'size') {
        return Number(item.statEntry.stSize ?? BigInt(0));
      }
      if (property === 'atime') {
        return (item.statEntry.stAtime ?? new Date(0)).getTime();
      }
      if (property === 'mtime') {
        return (item.statEntry.stMtime ?? new Date(0)).getTime();
      }
      if (property === 'ctime') {
        return (item.statEntry.stCtime ?? new Date(0)).getTime();
      }
      if (property === 'btime') {
        return (item.statEntry.stBtime ?? new Date(0)).getTime();
      }
      if (property === 'mode') {
        return Number(item.statEntry.stMode ?? BigInt(0));
      }
      if (property === 'status') {
        return item.status?.state ?? CollectionState.UNKNOWN;
      } else {
        return '';
      }
    };
    this.dataSource.filterPredicate = (
      data: FlowFileResult,
      filter: string,
    ) => {
      return (
        (data.isFile && filter.includes('file')) ||
        (data.isDirectory && filter.includes('folder')) ||
        data.clientId.includes(filter) ||
        data.statEntry.pathspec?.path?.includes(filter) ||
        data.statEntry.stSize?.toString().includes(filter) ||
        data.statEntry.stAtime?.getTime().toString().includes(filter) ||
        data.statEntry.stAtime?.toUTCString().includes(filter) ||
        data.statEntry.stMtime?.getTime().toString().includes(filter) ||
        data.statEntry.stMtime?.toUTCString().includes(filter) ||
        data.statEntry.stCtime?.getTime().toString().includes(filter) ||
        data.statEntry.stCtime?.toUTCString().includes(filter) ||
        data.statEntry.stBtime?.getTime().toString().includes(filter) ||
        data.statEntry.stBtime?.toUTCString().includes(filter) ||
        data.statEntry.stMode?.toString().includes(filter) ||
        data.hashes?.sha256?.includes(filter) ||
        data.hashes?.sha1?.includes(filter) ||
        data.hashes?.md5?.includes(filter) ||
        false
      );
    };
  }

  protected expandedRow: FlowFileResult | null = null;

  protected isRowExpanded(row: FlowFileResult) {
    return this.expandedRow === row;
  }

  protected toggleExpandedRow(row: FlowFileResult) {
    if (this.isRowExpanded(row)) {
      this.expandedRow = null;
    } else {
      this.expandedRow = row;
    }
  }

  /** Announce the change in sort state for assistive technology. */
  protected announceSortChange(sortState: Sort) {
    if (sortState.direction) {
      this.liveAnnouncer.announce(`Sorted ${sortState.direction}`);
    } else {
      this.liveAnnouncer.announce('Sorting cleared');
    }
  }
}
